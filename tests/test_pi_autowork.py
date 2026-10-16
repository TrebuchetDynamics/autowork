"""Offline tests for scripts/pi-autowork.sh with a fake Pi and disposable Git repositories.

These prove the runner's control flow only; they do not show that a real model
executes Autowork (see docs/pi-autowork.md for the live smoke test).
"""
import json
import os
from pathlib import Path
import shutil
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
RUNNER = ROOT / 'scripts/pi-autowork.sh'
GOALS = ROOT / 'skills/docs-sync/scripts/goals.py'
INTENT = {'version': 1, 'goals': [
    {'id': 'G1', 'title': 'Goal one', 'source': 'PLAN.md#goal-one', 'status': 'unmet',
     'tasks': ['T1', 'T2'], 'priority': 1}], 'tasks': [
    {'id': 'T1', 'goal': 'G1', 'title': 'First', 'status': 'open', 'section': 'Now'},
    {'id': 'T2', 'goal': 'G1', 'title': 'Second', 'status': 'open', 'section': 'Next', 'depends_on': ['T1']}]}
TODO = ('# TODO\n\n## Now\n\n- [ ] T1: First\n  Goal: G1\n  Scope: do it\n  Acceptance: it works\n'
        '  Dependencies: None\n  Sources: [Plan](PLAN.md#goal-one)\n  Ownership: unclaimed\n\n## Next\n\n'
        '- [ ] T2: Second\n  Goal: G1\n  Scope: do more\n  Acceptance: more works\n  Dependencies: T1\n'
        '  Sources: [Plan](PLAN.md#goal-one)\n  Ownership: unclaimed\n')

# A stand-in for the Pi CLI. Each `--mode json` run takes the next behavior from the plan.
FAKE_PI = r'''#!/usr/bin/env python3
import json, os, re, signal, subprocess, sys, time
args = sys.argv[1:]
log = os.environ['FAKE_PI_LOG']
def note(record):
    with open(log, 'a') as stream:
        stream.write(json.dumps(record) + '\n')
if args[:1] == ['list']:
    if os.environ.get('FAKE_PI_TOOLSET'):
        print('User packages:\n  ' + os.environ['FAKE_PI_TOOLSET'] + '\n    ' + os.environ['FAKE_PI_TOOLSET'])
    sys.exit(0)
if args[:1] == ['--list-models']:
    print('provider      model                         context')
    for row in os.environ.get('FAKE_PI_CATALOG', 'openai-codex gpt-6.1-sol;openrouter deepseek/deepseek-v4.1-flash').split(';'):
        print(row.replace(' ', '  ') + '  500K')
    sys.exit(0)
if args[:2] == ['auth', 'check']:
    provider = args[args.index('--provider') + 1]
    sys.exit(1 if provider in os.environ.get('FAKE_PI_UNAUTH', '').split(',') else 0)
opts = {args[i]: args[i + 1] for i in range(len(args) - 1) if args[i].startswith('--')}
prompt = args[-1]
match = re.search(r'Execute exactly task (\S+) ', prompt)
task = match.group(1) if match else None
plan_path = os.environ['FAKE_PI_PLAN']
plan = json.load(open(plan_path))
behavior = plan.pop(0) if plan else 'no_progress'
json.dump(plan, open(plan_path, 'w'))
note({'run': behavior, 'provider': opts.get('--provider'), 'model': opts.get('--model'),
      'session': opts.get('--session-id'), 'task': task, 'prompt': prompt, 'cwd': os.getcwd(),
      'no_approve': '--no-approve' in args, 'skill': opts.get('--skill')})
def emit(record):
    print(json.dumps(record), flush=True)
def finish(stop='stop', text='', error=None):
    message = {'role': 'assistant', 'content': [{'type': 'text', 'text': text}], 'stopReason': stop,
               'model': opts.get('--model'), 'usage': {'totalTokens': 10, 'cost': {'total': 0.01}}}
    if error:
        message['errorMessage'] = error
    emit({'type': 'message_end', 'message': message})
    emit({'type': 'agent_end', 'messages': [], 'willRetry': False})
    emit({'type': 'agent_settled', 'aborted': False})
def git(*command):
    return subprocess.run(['git', *command], capture_output=True, text=True)
def commit(name):
    open(name, 'w').write(name + '\n')
    git('add', '-A')
    git('-c', 'user.email=fake@example.invalid', '-c', 'user.name=Fake', 'commit', '-qm', name)
emit({'type': 'session', 'version': 3, 'id': opts.get('--session-id'), 'cwd': os.getcwd()})
emit({'type': 'agent_start'})
if behavior == 'complete':
    subprocess.run([sys.executable, os.environ['FAKE_GOALS'], 'task', '.', task, 'done'], capture_output=True)
    commit(f'{task}.txt')
    finish(text=f'Done.\nPI_AUTOWORK_RESULT: completed {task} finished')
elif behavior == 'complete_and_move_main':  # another writer commits to main meanwhile
    subprocess.run([sys.executable, os.environ['FAKE_GOALS'], 'task', '.', task, 'done'], capture_output=True)
    commit(f'{task}.txt')
    main = os.environ['FAKE_MAIN_REPO']
    open(os.path.join(main, f'{task}.txt'), 'w').write('from main\n')
    subprocess.run(['git', '-C', main, 'add', '-A'], capture_output=True)
    subprocess.run(['git', '-C', main, '-c', 'user.email=m@example.invalid', '-c', 'user.name=Main', 'commit', '-qm', 'main moved'], capture_output=True)
    finish()
elif behavior == 'resolve':  # keep this branch's side of every conflict and conclude the merge
    git('checkout', '--ours', '.')
    git('add', '-A')
    git('-c', 'user.email=fake@example.invalid', '-c', 'user.name=Fake', 'commit', '-q', '--no-edit')
    finish(text='PI_AUTOWORK_RESULT: completed merge resolved')
elif behavior == 'progress':
    commit(f'{task}-part.txt')
    finish(text='PI_AUTOWORK_RESULT: partial first slice')
elif behavior == 'no_progress':
    finish(text='PI_AUTOWORK_RESULT: blocked needs a device')
elif behavior == 'provider_error':
    open('partial.txt', 'w').write('half done\n')
    finish(stop='error', error='429 rate limit exceeded (sk-secret123456789)')
elif behavior == 'no_key':  # Pi 1.2.0's wording when a provider has no credentials
    sys.stderr.write('No API key found for openai-codex.\n\nUse /login to log into a provider via OAuth or API key.\n')
    sys.exit(1)
elif behavior == 'crash':
    sys.stderr.write('pi: internal error\n')
    sys.exit(1)
elif behavior == 'push':
    pushed = git('push', 'origin', 'HEAD:refs/heads/pushed')
    open(os.environ['FAKE_PI_PUSH'], 'w').write(str(pushed.returncode))
    subprocess.run([sys.executable, os.environ['FAKE_GOALS'], 'task', '.', task, 'done'], capture_output=True)
    commit(f'{task}.txt')
    finish()
elif behavior in ('sleep', 'hang'):
    open('partial.txt', 'w').write('in progress\n')
    def stopped(*_):
        note({'signal': 'INT'})
        sys.exit(130)
    signal.signal(signal.SIGINT, stopped)
    open(os.environ['FAKE_PI_LOG'] + '.ready', 'w').write(str(os.getpid()))
    time.sleep(60)
    finish()
'''


class PiAutoworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.make_repo(self.root / 'project')
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.bin / 'pi').write_text(FAKE_PI)
        (self.bin / 'pi').chmod(0o755)
        self.log = self.root / 'pi.log'
        self.plan = self.root / 'plan.json'
        self.state = self.root / 'state'
        self.env = {**os.environ, 'PATH': f"{self.bin}:{os.environ['PATH']}", 'FAKE_PI_LOG': str(self.log),
                    'FAKE_MAIN_REPO': str(self.repo),
                    'FAKE_PI_PLAN': str(self.plan), 'FAKE_GOALS': str(GOALS),
                    'FAKE_PI_PUSH': str(self.root / 'push.rc'),
                    'PI_AUTOWORK_STATE_DIR': str(self.state), 'PI_AUTOWORK_HERMES_HOME': str(self.root / 'hermes'),
                    'PI_AUTOWORK_BACKOFF': '0', 'XDG_STATE_HOME': str(self.root / 'xdg')}
        for name in ('GIT_CONFIG_COUNT', 'PI_AUTOWORK_TOOLSET', 'PI_AUTOWORK_PRIMARY', 'PI_AUTOWORK_FALLBACK'):
            self.env.pop(name, None)
        self.set_plan([])

    def make_repo(self, repo):
        repo.mkdir()
        self.git(repo, 'init', '-q', '-b', 'main')
        (repo / 'PLAN.md').write_text('# Plan\n\n## Goal one\n\nStatus: Accepted\n\nBuild the thing.\n')
        intent, todo = self.root / f'{repo.name}-intent.json', self.root / f'{repo.name}-todo.md'
        intent.write_text(json.dumps(INTENT))
        todo.write_text(TODO)
        subprocess.run([sys.executable, str(GOALS), 'init', str(repo), '--intent', str(intent),
                        '--todo-file', str(todo)], check=True, capture_output=True)
        self.git(repo, 'add', '-A')
        self.git(repo, 'commit', '-qm', 'initial')
        return repo

    def git(self, repo, *args):
        return subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    def set_plan(self, plan):
        self.plan.write_text(json.dumps(plan))

    def worktrees(self):
        return [line for line in self.git(self.repo, 'worktree', 'list', '--porcelain').splitlines()
                if line.startswith('worktree ')]

    def branches(self):
        return self.git(self.repo, 'branch', '--format=%(refname:short)').splitlines()

    def runs(self):
        if not self.log.exists():
            return []
        return [r for r in map(json.loads, self.log.read_text().splitlines()) if 'run' in r]

    def records(self):
        found = list(self.state.glob('*/runs.jsonl'))
        return [json.loads(line) for line in found[0].read_text().splitlines()] if found else []

    def run_runner(self, *args, script=RUNNER, cwd=None, env=None, timeout=60):
        return subprocess.run(['bash', str(script), *args], cwd=cwd or self.repo, env=env or self.env,
                              capture_output=True, text=True, timeout=timeout)

    def start_runner(self, *args):
        process = subprocess.Popen(['bash', str(RUNNER), *args], cwd=self.repo, env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        ready = Path(str(self.log) + '.ready')
        for _ in range(200):
            if ready.exists():
                return process
            time.sleep(0.05)
        process.kill()
        self.fail('fake Pi never started: ' + process.communicate()[0])

    # 1, 2: copied into an unrelated repository and started from elsewhere.
    def test_copied_script_targets_its_repository_from_any_directory(self):
        shutil.copy(RUNNER, self.repo / 'pi-autowork.sh')
        self.env['FAKE_PI_TOOLSET'] = str(ROOT)  # found through `pi list`
        self.set_plan(['complete'])
        result = self.run_runner('--once', script=self.repo / 'pi-autowork.sh', cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'Repository: {self.repo}', result.stdout)
        run, = self.runs()
        self.assertEqual(run['task'], 'T1')
        self.assertTrue(run['cwd'].startswith(str(self.state)), run['cwd'])  # a task worktree
        self.assertIsNone(run['skill'])  # installed package: no explicit --skill
        self.assertTrue((self.repo / 'T1.txt').exists())  # merged into main at the end
        self.assertEqual(self.git(self.repo, 'branch', '--show-current'), 'main')
        self.assertEqual((len(self.worktrees()), self.branches()), (1, ['main']))

    def test_shipped_script_targets_the_current_or_named_repository(self):
        other = self.make_repo(self.root / 'other')
        result = self.run_runner('--dry-run', cwd=other)
        self.assertIn(f'Repository: {other}', result.stdout)
        result = self.run_runner('--dry-run', '--repo', str(self.repo), cwd=self.root)
        self.assertIn(f'Repository: {self.repo}', result.stdout)
        self.assertIn(f'Toolset:    {ROOT}', result.stdout)

    def test_the_pi_installed_package_wins_over_the_scripts_checkout(self):
        package = self.root / 'pi-package'
        shutil.copytree(ROOT / 'skills/docs-sync', package / 'skills/docs-sync')
        shutil.copytree(ROOT / 'adapters', package / 'adapters')
        self.env['FAKE_PI_TOOLSET'] = str(package)
        self.set_plan(['complete'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'Toolset:    {package} at unknown (Pi package)', result.stdout)
        self.assertIsNone(self.runs()[0]['skill'])  # Pi loads its own installed skills
        self.env.pop('FAKE_PI_TOOLSET')
        result = self.run_runner('--dry-run')
        self.assertIn('not a Pi package; skills loaded with --skill', result.stdout)
        self.assertIn('hermes-toolset is not installed in Pi', result.stderr)

    # 3
    def test_missing_todo_fails_clearly(self):
        bare = self.root / 'bare'
        bare.mkdir()
        self.git(bare, 'init', '-q')
        result = self.run_runner('--once', cwd=bare)
        self.assertEqual(result.returncode, 2)
        self.assertIn('No TODO.md', result.stderr)
        result = self.run_runner('--once', cwd=self.root)
        self.assertEqual(result.returncode, 2)
        self.assertIn('Not inside a Git repository', result.stderr)

    # 4
    def test_model_missing_from_the_catalog_is_rejected(self):
        self.env['PI_AUTOWORK_PRIMARY'] = 'openai-codex/gpt-nope'
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 2)
        self.assertIn('not in Pi', result.stderr)
        self.env['PI_AUTOWORK_PRIMARY'] = 'openai-codex/gpt-6.1-sol'
        self.env['FAKE_PI_CATALOG'] = 'openai-codex gpt-6.1-sol'
        self.assertEqual(self.run_runner('--once').returncode, 2)
        self.assertEqual(self.runs(), [])

    # 5, 9
    def test_explicit_models_and_each_task_runs_once(self):
        self.set_plan(['complete', 'complete'])
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        runs = self.runs()
        self.assertEqual([r['task'] for r in runs], ['T1', 'T2'])
        for run in runs:
            self.assertEqual((run['provider'], run['model']), ('openai-codex', 'gpt-6.1-sol'))
            self.assertTrue(run['no_approve'])
            self.assertEqual(run['skill'], str(ROOT / 'adapters/skills/git-commit-push'))  # last of two
            self.assertTrue(run['prompt'].startswith('/skill:autowork Execute exactly task'))
        self.assertEqual([r['outcome'] for r in self.records()], ['completed', 'completed'])
        self.assertIn('Queue empty', result.stdout)
        self.assertNotEqual(runs[0]['cwd'], runs[1]['cwd'])  # one worktree per task
        self.assertIn('Merged pi-autowork/', result.stdout)
        self.assertTrue((self.repo / 'T1.txt').exists() and (self.repo / 'T2.txt').exists())
        self.assertEqual((len(self.worktrees()), self.branches()), (1, ['main']))
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')

    # 6, 12, 14: a JSON-mode provider error with exit 0 switches models and resumes the same task.
    def test_provider_outage_falls_back_and_resumes_the_task(self):
        self.set_plan(['provider_error', 'complete'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first, second = self.runs()
        self.assertEqual((first['provider'], second['provider']), ('openai-codex', 'openrouter'))
        self.assertEqual(second['model'], 'deepseek/deepseek-v4.1-flash')
        self.assertEqual((first['session'], second['task']), (second['session'], 'T1'))
        self.assertIn('previous run of this task was interrupted', second['prompt'])
        failed, done = self.records()
        self.assertEqual((failed['outcome'], done['outcome']), ('provider_failure', 'completed'))
        self.assertIn('429 rate limit', failed['error'])
        self.assertNotIn('sk-secret', json.dumps(self.records()))
        self.assertIn('429', done['fallback_reason'])
        self.assertEqual(done['provider'], 'openrouter')

    def test_missing_credentials_at_run_time_fall_back(self):
        """TOOLSET-094-65 live finding: Pi exits 1 before any event when a provider has no key."""
        self.set_plan(['no_key', 'complete'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['provider'] for r in self.runs()], ['openai-codex', 'openrouter'])
        self.assertEqual(self.records()[0]['outcome'], 'provider_failure')

    def test_no_fallback_retries_the_primary_then_gives_up(self):
        self.set_plan(['provider_error', 'provider_error'])
        self.env['PI_AUTOWORK_MAX_RETRIES'] = '1'
        result = self.run_runner('--once', '--no-fallback')
        self.assertEqual(result.returncode, 1)
        self.assertEqual({r['provider'] for r in self.runs()}, {'openai-codex'})
        self.assertIn('unfinished work kept in', result.stdout)
        kept = Path(self.runs()[0]['cwd'])
        self.assertTrue((kept / 'partial.txt').exists())
        self.assertFalse((self.repo / 'partial.txt').exists())

    def test_unauthenticated_primary_uses_the_fallback(self):
        self.env['FAKE_PI_UNAUTH'] = 'openai-codex'
        self.set_plan(['complete'])
        self.assertEqual(self.run_runner('--once').returncode, 0)
        self.assertEqual(self.runs()[0]['provider'], 'openrouter')
        self.assertEqual(self.records()[0]['fallback_reason'], 'primary not authenticated')

    # 7
    def test_task_without_progress_does_not_switch_models(self):
        self.set_plan(['no_progress'])
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 1, result.stdout)
        run, = self.runs()
        self.assertEqual(run['provider'], 'openai-codex')
        self.assertEqual(self.records()[0]['outcome'], 'no_progress')
        self.assertIn('No task this runner can make progress on', result.stdout)

    def test_partial_progress_continues_the_same_task(self):
        self.set_plan(['progress', 'complete', 'complete'])
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual([r['task'] for r in self.runs()], ['T1', 'T1', 'T2'])
        self.assertEqual([r['outcome'] for r in self.records()], ['partial', 'completed', 'completed'])

    def test_crash_is_retried_with_the_same_model(self):
        self.set_plan(['crash', 'complete'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout)
        self.assertEqual([r['provider'] for r in self.runs()], ['openai-codex', 'openai-codex'])
        self.assertEqual(self.records()[0]['outcome'], 'crash_failure')

    # 8
    def test_empty_queue_idles_without_calling_a_model(self):
        for task in ('T1', 'T2'):
            subprocess.run([sys.executable, str(GOALS), 'task', str(self.repo), task, 'done'], capture_output=True)
        self.git(self.repo, 'commit', '-qam', 'close')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0)
        self.assertIn('Queue empty', result.stdout)
        self.assertEqual(self.runs(), [])

    def test_continuous_mode_idles_and_stops_promptly(self):
        for task in ('T1', 'T2'):
            subprocess.run([sys.executable, str(GOALS), 'task', str(self.repo), task, 'done'], capture_output=True)
        self.git(self.repo, 'commit', '-qam', 'close')
        process = subprocess.Popen(['bash', str(RUNNER), '--interval', '300'], cwd=self.repo, env=self.env,
                                   stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        time.sleep(2)
        process.terminate()
        out, _ = process.communicate(timeout=10)  # well before the 300 s interval
        self.assertEqual(process.returncode, 130, out)
        self.assertIn('Queue empty; checking again in 300s', out)
        self.assertEqual(self.runs(), [])

    # 10, 11, 12
    def test_lock_interrupt_and_resume(self):
        self.set_plan(['sleep', 'complete'])
        first = self.start_runner()
        second = self.run_runner('--once')
        self.assertEqual(second.returncode, 3)
        self.assertIn('Another pi-autowork runner', second.stderr)
        first.send_signal(signal.SIGINT)
        out, _ = first.communicate(timeout=30)
        self.assertEqual(first.returncode, 130, out)
        self.assertIn({'signal': 'INT'}, [json.loads(l) for l in self.log.read_text().splitlines()])
        self.assertEqual(self.records()[-1]['outcome'], 'interrupted')
        worktree = Path(self.runs()[0]['cwd'])
        self.assertTrue((worktree / 'partial.txt').exists())  # partial work kept in its worktree
        self.assertFalse((self.repo / 'partial.txt').exists())
        Path(str(self.log) + '.ready').unlink()
        result = self.run_runner('--once')  # the lock was released; resumes T1
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        interrupted, resumed = self.runs()
        self.assertEqual((resumed['session'], resumed['cwd']), (interrupted['session'], interrupted['cwd']))
        self.assertTrue((self.repo / 'T1.txt').exists())
        self.assertIn('previous run of this task was interrupted', resumed['prompt'])

    def test_task_timeout_stops_with_partial_work(self):
        self.set_plan(['hang'])
        self.env['PI_AUTOWORK_TASK_TIMEOUT'] = '2'
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 1)
        self.assertIn('exceeded PI_AUTOWORK_TASK_TIMEOUT', result.stdout)
        self.assertIn('unfinished work kept in', result.stdout)
        self.assertEqual(self.records()[0]['outcome'], 'timeout')

    # 13
    def test_pushes_are_blocked(self):
        remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
        self.git(self.repo, 'remote', 'add', 'origin', str(remote))
        self.set_plan(['push'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual((self.root / 'push.rc').read_text(), '0')
        refs = subprocess.run(['git', '-C', str(remote), 'for-each-ref'], capture_output=True, text=True).stdout
        self.assertEqual(refs, '')

    # 15
    def test_dry_run_changes_nothing(self):
        before = self.git(self.repo, 'status', '--porcelain', '--untracked-files=all')
        result = self.run_runner('--dry-run')
        self.assertEqual(result.returncode, 0, result.stderr)
        for part in ('Primary:    openai-codex/gpt-6.1-sol (ready)', 'Fallback:   openrouter/deepseek/deepseek-v4.1-flash',
                     'Queue:      1 runnable task(s)', 'Next:       T1 — First', 'Dry run: nothing was changed.'):
            self.assertIn(part, result.stdout)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--untracked-files=all'), before)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.runs(), [])

    def test_only_the_main_branch_is_accepted(self):
        self.git(self.repo, 'switch', '-q', '-c', 'feature')
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 2)
        self.assertIn('is on branch feature', result.stderr)
        self.assertEqual(self.runs(), [])

    def test_user_changes_in_main_block_only_the_final_merge(self):
        (self.repo / 'T1.txt').write_text('my note\n')  # untracked; the merge would overwrite it
        self.set_plan(['complete'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Merge pending', result.stdout)
        self.assertEqual((self.repo / 'T1.txt').read_text(), 'my note\n')  # untouched
        session, = [b for b in self.branches() if b.startswith('pi-autowork/')]
        self.assertIn('T1.txt', self.git(self.repo, 'show', '--name-only', '--format=', session))
        (self.repo / 'T1.txt').unlink()
        self.set_plan(['complete'])  # T2 runs on the kept session, then everything merges
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue((self.repo / 'T1.txt').exists() and (self.repo / 'T2.txt').exists())
        self.assertEqual(self.branches(), ['main'])

    def test_main_moving_meanwhile_is_merged_with_pi_resolving_conflicts(self):
        self.set_plan(['complete_and_move_main', 'resolve'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('asking Pi to resolve the merge', result.stdout)
        resolution = self.runs()[1]
        self.assertTrue(resolution['prompt'].startswith('/skill:git-commit-push'))
        self.assertIn('main moved', self.git(self.repo, 'log', '--format=%s'))
        self.assertEqual((self.repo / 'T1.txt').read_text(), 'T1.txt\n')
        self.assertEqual(self.branches(), ['main'])

    def test_an_unresolved_conflict_keeps_the_session(self):
        self.set_plan(['complete_and_move_main', 'no_progress'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Merge pending', result.stdout)
        self.assertEqual((self.repo / 'T1.txt').read_text(), 'from main\n')
        self.assertEqual(len([b for b in self.branches() if b.startswith('pi-autowork/')]), 1)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')

    def test_hermes_autowork_job_on_the_same_repository_refuses(self):
        jobs = self.root / 'hermes/profiles/work/cron'
        jobs.mkdir(parents=True)
        (jobs / 'jobs.json').write_text(json.dumps({'jobs': [
            {'id': 'a1', 'name': 'Work Autowork', 'workdir': str(self.repo), 'enabled': True,
             'skills': ['hermes-toolset:autowork']},
            {'id': 'b2', 'name': 'Paused', 'workdir': str(self.repo), 'enabled': True, 'paused_at': 'x',
             'skills': ['hermes-toolset:autowork']}]}))
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4)
        self.assertIn('work: Work Autowork', result.stderr)
        self.assertNotIn('Paused', result.stderr)
        self.env['PI_AUTOWORK_ALLOW_HERMES'] = '1'
        self.set_plan(['complete'])
        self.assertEqual(self.run_runner('--once').returncode, 0)

    def test_todo_only_repository_allows_once_only(self):
        plain = self.root / 'plain'
        plain.mkdir()
        self.git(plain, 'init', '-q')
        (plain / 'TODO.md').write_text('# TODO\n\n- [ ] Fix the thing\n')
        self.git(plain, 'add', '-A')
        self.git(plain, 'commit', '-qm', 'todo')
        result = self.run_runner(cwd=plain)
        self.assertEqual(result.returncode, 2)
        self.assertIn('No goals.json', result.stderr)
        self.set_plan(['no_progress'])
        result = self.run_runner('--once', cwd=plain)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Complete the next ready task', self.runs()[0]['prompt'])


if __name__ == '__main__':
    unittest.main()
