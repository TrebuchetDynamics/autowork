"""Offline tests for scripts/pi-autowork.sh: the real Parallel Autowork engine and Git,
with a fake Pi standing in for workers, the reviewer and merge resolution.

These prove the runner's control flow only; they do not show that a real model
executes tasks (docs/cross-host.md describes the live qualification).
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
ENGINE_DIR = ROOT / 'skills/autowork/scripts'


def todo(tasks):
    """TODO.md in the engine's contract format: (id, depends_on) pairs."""
    body = ''.join(
        f'- [ ] {t} — Task {t}\n  Scope: Complete {t}.txt\n  Touches: {t}.txt\n'
        f'  Acceptance: {t}.txt says done\n  Checks: test -s {t}.txt\n'
        f'  Dependencies: {dep or "None"}.\n  Status: open\n' for t, dep in tasks)
    return '# TODO\n\n## Next\n\n' + body


# A stand-in for the Pi CLI. Workers, the reviewer and the merge resolver take their
# next behavior from a per-role plan, under a lock because workers run concurrently.
FAKE_PI = r'''#!/usr/bin/env python3
import fcntl, json, os, re, signal, subprocess, sys, time
args = sys.argv[1:]
def note(record):
    with open(os.environ['FAKE_PI_LOG'], 'a') as stream:
        fcntl.flock(stream, fcntl.LOCK_EX)
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
message = args[-1]
files = [a[1:] for a in args if a.startswith('@')]
prompt = open(files[0]).read() if files else ''
field = lambda name: (re.search(rf'^{name}: (.+)$', prompt, re.M) or [None, None])[1]
if 'PI_AUTOWORK_VERIFY' in message:
    role, task = 'verify', re.search(r'verifying task (\S+) ', message)[1]
elif message.startswith('/skill:git-commit-push'):
    role, task = 'merge', None
else:
    role, task = 'worker', field('Task')
key = role if role == 'merge' else f'{role}:{task}'
with open(os.environ['FAKE_PI_PLAN'], 'r+') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    plan = json.load(stream)
    queue = plan.get(key) or []
    behavior = queue.pop(0) if queue else {'worker': 'complete', 'verify': 'pass', 'merge': 'resolve'}[role]
    plan[key] = queue
    stream.seek(0); stream.truncate(); json.dump(plan, stream)
note({'run': behavior, 'role': role, 'task': task, 'provider': opts.get('--provider'), 'model': opts.get('--model'),
      'session': opts.get('--session-id'), 'cwd': os.getcwd(), 'tools': opts.get('--tools'),
      'no_approve': '--no-approve' in args, 'message': message})
def emit(record):
    print(json.dumps(record), flush=True)
def finish(stop='stop', text='', error=None):
    message = {'role': 'assistant', 'content': [{'type': 'text', 'text': text}], 'stopReason': stop,
               'model': opts.get('--model'), 'usage': {'totalTokens': 10, 'cost': {'total': 0.01}}}
    if error:
        message['errorMessage'] = error
    emit({'type': 'message_end', 'message': message})
    emit({'type': 'agent_settled', 'aborted': False})
def git(*command):
    return subprocess.run(['git', '-c', 'user.email=fake@example.invalid', '-c', 'user.name=Fake', *command],
                          capture_output=True, text=True)
def report(commit, blockers=()):
    with open(field('Report file'), 'w') as out:
        json.dump({'task': task, 'commit': commit, 'changed_files': [task + '.txt'] if commit else [],
                   'checks': [{'command': f'test -s {task}.txt', 'result': 'pass', 'summary': 'ok'}] if commit else [],
                   'blockers': list(blockers), 'changelog': 'Complete ' + task}, out)
def work():
    open(task + '.txt', 'w').write('done ' + task + '\n')
    git('add', task + '.txt')
    git('commit', '-qm', 'worker ' + task)
    report(git('rev-parse', 'HEAD').stdout.strip())
emit({'type': 'session', 'version': 3, 'id': opts.get('--session-id'), 'cwd': os.getcwd()})
if role == 'verify':
    if behavior == 'tamper':
        open('tampered.txt', 'w').write('x\n')
    finish(text='Checked.\nPI_AUTOWORK_VERIFY: ' + ('fail acceptance not met' if behavior == 'fail' else 'pass all checks'))
elif role == 'merge':
    if behavior == 'resolve':
        git('checkout', '--ours', '.')
        git('add', '-A')
        git('commit', '-q', '--no-edit')
    finish(text='PI_AUTOWORK_RESULT: completed')
elif behavior == 'complete':
    work(); finish(text='done')
elif behavior == 'slow':  # busy for a few seconds, then finishes normally
    open(os.path.join(os.environ['FAKE_PI_ROOT'], 'busy-' + task), 'w').write(str(os.getpid()))
    subprocess.run(['sleep', '6'])  # a running tool command, as real Pi has: an active session
    work(); finish(text='done')
elif behavior == 'barrier':  # both A and B must be running at once
    mine = os.path.join(os.environ['FAKE_PI_ROOT'], 'ready-' + task)
    open(mine, 'w').write('ready')
    deadline = time.monotonic() + 20
    while not all(os.path.exists(os.path.join(os.environ['FAKE_PI_ROOT'], 'ready-' + t)) for t in ('A', 'B')):
        if time.monotonic() > deadline:
            sys.exit('barrier timed out')
        time.sleep(0.05)
    work(); finish(text='done')
elif behavior == 'move_main':  # another writer commits a conflicting file to main meanwhile
    work()
    main = os.environ['FAKE_MAIN_REPO']
    open(os.path.join(main, task + '.txt'), 'w').write('from main\n')
    subprocess.run(['git', '-C', main, 'add', '-A'])
    subprocess.run(['git', '-C', main, '-c', 'user.email=m@example.invalid', '-c', 'user.name=Main', 'commit', '-qm', 'main moved'])
    finish(text='done')
elif behavior == 'provider_error':
    open(task + '-partial.txt', 'w').write('half\n')
    finish(stop='error', error='429 rate limit exceeded (sk-secret123456789)')
elif behavior == 'no_key':
    sys.stderr.write('No API key found for openai-codex.\n\nUse /login to log into a provider via OAuth or API key.\n')
    sys.exit(1)
elif behavior == 'push':
    pushed = git('push', 'origin', 'HEAD:refs/heads/pushed')
    open(os.environ['FAKE_PI_ROOT'] + '/push.rc', 'w').write(str(pushed.returncode))
    work(); finish(text='done')
elif behavior == 'blocked':
    report(None, ['needs a device'])
    finish(text='blocked')
elif behavior == 'sleep':
    def stopped(*_):
        signal.signal(signal.SIGINT, signal.SIG_IGN)  # repeats arrive from the group and timeout
        note({'signal': 'INT', 'task': task})
        sys.exit(130)
    signal.signal(signal.SIGINT, stopped)
    open(os.path.join(os.environ['FAKE_PI_ROOT'], 'sleeping-' + task), 'w').write(str(os.getpid()))
    time.sleep(60)
    finish()
'''


class Fixture(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.make_repo(self.root / 'project', [('A', None), ('B', None), ('C', 'A')])
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        (self.bin / 'pi').write_text(FAKE_PI)
        (self.bin / 'pi').chmod(0o755)
        self.log = self.root / 'pi.log'
        self.plan_file = self.root / 'plan.json'
        self.state = self.root / 'state'
        self.env = {**os.environ, 'PATH': f"{self.bin}:{os.environ['PATH']}", 'FAKE_PI_LOG': str(self.log),
                    'FAKE_PI_PLAN': str(self.plan_file), 'FAKE_PI_ROOT': str(self.root),
                    'FAKE_MAIN_REPO': str(self.repo),
                    'PI_AUTOWORK_STATE_DIR': str(self.state), 'PI_AUTOWORK_HERMES_HOME': str(self.root / 'hermes'),
                    'PI_AUTOWORK_BACKOFF': '0', 'PI_AUTOWORK_MIN_FREE_MB': '0', 'XDG_STATE_HOME': str(self.root / 'xdg')}
        for name in ('GIT_CONFIG_COUNT', 'PI_AUTOWORK_TOOLSET', 'PI_AUTOWORK_PRIMARY', 'PI_AUTOWORK_FALLBACK',
                     'PI_AUTOWORK_WORKERS', 'PI_AUTOWORK_MAX_COST'):
            self.env.pop(name, None)
        self.plan({})
        self.addCleanup(self.stop_workers)

    def stop_workers(self):  # failures must not leave fake workers writing after cleanup
        slots = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / 'autowork-execution/slots'
        for path in slots.glob('*.json') if slots.exists() else []:
            pid = json.loads(path.read_text()).get('worker', {}).get('pid')
            if pid:
                try:
                    os.killpg(pid, signal.SIGKILL)
                except (ProcessLookupError, PermissionError):
                    pass

    def make_repo(self, repo, tasks):
        repo.mkdir()
        self.git(repo, 'init', '-q', '-b', 'main')
        (repo / 'TODO.md').write_text(todo(tasks))
        for t, _ in tasks:
            (repo / f'{t}.txt').write_text('')
        self.git(repo, 'add', '-A')
        self.git(repo, 'commit', '-qm', 'initial')
        return repo

    def git(self, repo, *args):
        return subprocess.run(['git', '-C', str(repo), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    def plan(self, plan):
        self.plan_file.write_text(json.dumps(plan))

    def runs(self, role=None):
        if not self.log.exists():
            return []
        rows = [r for r in map(json.loads, self.log.read_text().splitlines()) if 'run' in r]
        return [r for r in rows if role is None or r['role'] == role]

    def records(self):
        found = list(self.state.glob('*/runs.jsonl'))
        return [json.loads(line) for line in found[0].read_text().splitlines()] if found else []

    def run_runner(self, *args, script=RUNNER, cwd=None, env=None, timeout=120):
        return subprocess.run(['bash', str(script), *args], cwd=cwd or self.repo, env=env or self.env,
                              capture_output=True, text=True, timeout=timeout)

    def start_runner(self, *args):
        return subprocess.Popen(['bash', str(RUNNER), *args], cwd=self.repo, env=self.env,
                                stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

    def wait_for(self, path, timeout=30):
        deadline = time.monotonic() + timeout
        while not path.exists():
            if time.monotonic() > deadline:
                self.fail(f'{path} never appeared')
            time.sleep(0.05)

    def done(self, *tasks):
        return all((self.repo / f'{t}.txt').read_text() == f'done {t}\n' for t in tasks)

    def branches(self):
        return self.git(self.repo, 'branch', '--format=%(refname:short)').splitlines()


class EngineTests(Fixture):
    def test_independent_tasks_run_in_parallel_and_merge_verified_into_main(self):
        self.plan({'worker:A': ['barrier'], 'worker:B': ['barrier']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        workers = self.runs('worker')
        self.assertEqual(sorted(r['task'] for r in workers), ['A', 'B', 'C'])  # each once
        self.assertEqual(len({r['cwd'] for r in workers}), 3)  # one worktree each
        for run in workers:
            self.assertEqual((run['provider'], run['model']), ('openai-codex', 'gpt-6.1-sol'))
            self.assertTrue(run['no_approve'])
        reviews = self.runs('verify')
        self.assertEqual(sorted(r['task'] for r in reviews), ['A', 'B', 'C'])
        self.assertTrue(all(r['tools'] == 'read,bash,grep,find,ls' for r in reviews))
        for task in 'ABC':
            self.assertIn(f'{task}: done', result.stdout)
            self.assertIn(f'{task}: verifying', result.stdout)
        self.assertIn('Merged pi-autowork/', result.stdout)
        self.assertEqual(self.branches(), ['main'])
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        closed = (self.repo / 'TODO.md').read_text() + ((self.repo / 'TODO.archive.md').read_text()
                                                         if (self.repo / 'TODO.archive.md').exists() else '')
        self.assertTrue(all(f'- [x] {t}' in closed for t in 'ABC'), closed)
        roles = {r['role'] for r in self.records()}
        self.assertEqual(roles, {'worker', 'verify'})

    def test_once_runs_one_task(self):
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['task'] for r in self.runs('worker')], ['A'])
        self.assertTrue(self.done('A'))
        self.assertEqual((self.repo / 'B.txt').read_text(), '')

    def test_empty_queue_calls_no_model(self):
        self.run_runner('--until-empty')
        self.log.unlink()
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Queue empty', result.stdout)
        self.assertEqual(self.runs(), [])

    def test_provider_failure_falls_back_and_resumes_the_same_session(self):
        self.plan({'worker:A': ['provider_error', 'complete']})
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        first, second = self.runs('worker')
        self.assertEqual((first['provider'], second['provider']), ('openai-codex', 'openrouter'))
        self.assertEqual((first['session'], first['cwd']), (second['session'], second['cwd']))
        failed = next(r for r in self.records() if r['outcome'] == 'provider_failure')
        self.assertIn('429', failed['error'])
        self.assertNotIn('sk-secret', json.dumps(self.records()))
        self.assertTrue(self.done('A'))

    def test_missing_credentials_at_run_time_fall_back(self):
        self.plan({'worker:A': ['no_key', 'complete']})
        self.assertEqual(self.run_runner('--once').returncode, 0)
        self.assertEqual([r['provider'] for r in self.runs('worker')], ['openai-codex', 'openrouter'])

    def test_unauthenticated_primary_and_no_fallback(self):
        self.env['FAKE_PI_UNAUTH'] = 'openai-codex'
        self.assertEqual(self.run_runner('--once').returncode, 0)
        self.assertEqual(self.runs('worker')[0]['provider'], 'openrouter')
        self.log.unlink()
        self.env['FAKE_PI_UNAUTH'] = 'openai-codex,openrouter'
        result = self.run_runner('--once', '--no-fallback')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.runs(), [])

    def test_failed_review_holds_the_task_and_keeps_main_clean(self):
        self.plan({'verify:A': ['fail', 'fail']})
        result = self.run_runner('--until-empty', '--workers', '1')
        self.assertIn('A: failed', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), '')
        self.assertTrue(self.done('B'))  # independent work still lands
        self.assertNotIn('- [x] A', (self.repo / 'TODO.md').read_text())

    def test_a_reviewer_that_changes_files_fails_verification(self):
        self.plan({'verify:A': ['tamper', 'tamper']})
        result = self.run_runner('--once')
        self.assertNotEqual((self.repo / 'A.txt').read_text(), 'done A\n', result.stdout)
        self.assertFalse((self.repo / 'tampered.txt').exists())

    def test_blocked_worker_is_held_not_merged(self):
        self.plan({'worker:A': ['blocked', 'blocked']})
        result = self.run_runner('--once')
        self.assertIn('A: failed', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), '')

    def test_interrupt_and_resume(self):
        self.plan({'worker:A': ['sleep', 'complete'], 'worker:B': ['sleep', 'complete']})
        runner = self.start_runner()
        self.wait_for(self.root / 'sleeping-A')
        self.wait_for(self.root / 'sleeping-B')
        second = self.run_runner('--once')  # the lock holds
        self.assertEqual(second.returncode, 3, second.stderr)
        # Hermes Autowork's sequential claim goes through the same engine and is refused.
        sleeper = subprocess.Popen(['sleep', '30'])
        self.addCleanup(sleeper.kill)
        claim = subprocess.run([sys.executable, str(ENGINE_DIR / 'owner_cycle.py'), str(self.repo), '--apply',
                                '--owner-pid', str(sleeper.pid)], capture_output=True, text=True)
        self.assertEqual(json.loads(claim.stdout)['outcome'], 'BUSY', claim.stdout)
        self.assertIn('parallel coordinator', claim.stdout)
        runner.send_signal(signal.SIGINT)
        out, _ = runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130, out)
        signals = [json.loads(l) for l in self.log.read_text().splitlines() if '"signal"' in l]
        self.assertEqual(sorted(s['task'] for s in signals), ['A', 'B'], out + self.log.read_text()[-1500:])
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(self.branches(), ['main'])

    def test_a_killed_coordinator_restarts_at_once_and_adopts_live_workers(self):
        """Live qualification found a restart refused while a dead runner's helper held the lock."""
        self.plan({'worker:A': ['slow']})
        runner = self.start_runner('--workers', '1')
        self.wait_for(self.root / 'busy-A')
        runner.kill()
        runner.wait()
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual([r['task'] for r in self.runs('worker')].count('A'), 1)  # adopted, not restarted
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_task_integrates_while_another_worker_is_still_running(self):
        """Live qualification: a running worker's prompt path under .git made the engine
        treat it as a writer in the main checkout and hold every other integration."""
        self.plan({'worker:B': ['slow']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotIn('external writer', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_blocked_tasks_are_not_reported_as_an_empty_queue(self):
        """IDLE with tasks waiting is not an empty queue. An idle in_progress claim (A)
        is never dispatched and blocks its dependent (C) but not unrelated work (B)."""
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        text = text.replace('  Dependencies: None.\n  Status: open\n- [ ] B', '  Dependencies: None.\n  Status: in_progress\n- [ ] B', 1)
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A is claimed elsewhere')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('No task can start now', result.stdout)
        self.assertNotIn('Queue empty', result.stdout)
        self.assertEqual([r['task'] for r in self.runs('worker')], ['B'])
        self.assertTrue(self.done('B'))

    def test_budget_persists_across_restarts(self):
        self.env['PI_AUTOWORK_MAX_COST'] = '0.05'
        self.run_runner('--status')  # creates nothing
        key_dir = None
        self.run_runner('--once')
        key_dir, = self.state.iterdir()
        spent_now = sum(r['cost_usd'] for r in self.records())
        with (key_dir / 'runs.jsonl').open('a') as runs:
            runs.write(json.dumps({'time': '2026-01-01T00:00:00+00:00', 'cost_usd': 100}) + '\n')  # outside the window
            runs.write(json.dumps({'time': time.strftime('%Y-%m-%dT%H:%M:%S%z'), 'cost_usd': 0.05 - spent_now}) + '\n')
        self.log.unlink()
        result = self.run_runner('--until-empty')
        self.assertIn('Budget reached', result.stdout)
        self.assertEqual(self.runs(), [])

    def test_main_moving_meanwhile_is_merged_with_pi_resolving_conflicts(self):
        self.plan({'worker:A': ['move_main']})
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('asking Pi to resolve the merge', result.stdout)
        self.assertIn('main moved', self.git(self.repo, 'log', '--format=%s'))
        self.assertTrue(self.done('A'))
        self.assertEqual(self.branches(), ['main'])

    def test_an_unresolved_conflict_keeps_the_session(self):
        self.plan({'worker:A': ['move_main'], 'merge': ['no_progress']})
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Merge pending', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'from main\n')
        self.assertEqual(len([b for b in self.branches() if b.startswith('pi-autowork/')]), 1)
        status = self.run_runner('--status')
        self.assertIn('not yet merged into main', status.stdout)

    def test_user_changes_in_main_block_only_the_final_merge(self):
        (self.repo / 'A.txt').write_text('my note\n')  # uncommitted; the merge would overwrite it
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Merge pending', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'my note\n')
        self.git(self.repo, 'checkout', '--', 'A.txt')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_live_hermes_sequential_owner_keeps_pi_out(self):
        sys.path.insert(0, str(ENGINE_DIR))
        import task_execution
        sleeper = subprocess.Popen(['sleep', '60'])
        self.addCleanup(sleeper.kill)
        common = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        (common / 'autowork-execution').mkdir(exist_ok=True)
        (common / 'autowork-execution/active.json').write_text(json.dumps(
            {'task': 'A', 'owner': task_execution.identity(sleeper.pid), 'workspace': str(self.repo)}))
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Repository busy', result.stdout)
        self.assertEqual(self.runs(), [])

    def test_pushes_are_blocked_in_workers(self):
        remote = self.root / 'remote.git'
        subprocess.run(['git', 'init', '-q', '--bare', str(remote)], check=True)
        self.git(self.repo, 'remote', 'add', 'origin', str(remote))
        self.plan({'worker:A': ['push']})
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertNotEqual((self.root / 'push.rc').read_text(), '0')
        self.assertEqual(subprocess.run(['git', '-C', str(remote), 'for-each-ref'], capture_output=True, text=True).stdout, '')

    def test_status_and_dry_run_change_nothing(self):
        before = self.git(self.repo, 'status', '--porcelain', '--untracked-files=all')
        for option in ('--dry-run', '--status'):
            result = self.run_runner(option)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('Engine:     Parallel Autowork, up to 2 worker(s)', result.stdout)
            self.assertIn('Runner:     not running', result.stdout)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--untracked-files=all'), before)
        self.assertFalse(self.state.exists())
        self.assertEqual(self.runs(), [])


class SetupTests(Fixture):
    def test_copied_script_targets_its_repository_from_any_directory(self):
        shutil.copy(RUNNER, self.repo / 'pi-autowork.sh')
        self.git(self.repo, 'add', 'pi-autowork.sh')
        self.git(self.repo, 'commit', '-qm', 'runner copy')
        self.env['FAKE_PI_TOOLSET'] = str(ROOT)  # found through `pi list`
        result = self.run_runner('--once', script=self.repo / 'pi-autowork.sh', cwd=self.root)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'Repository: {self.repo}', result.stdout)
        self.assertTrue(self.done('A'))

    def test_the_pi_installed_package_wins_over_the_scripts_checkout(self):
        package = self.root / 'pi-package'
        shutil.copytree(ROOT / 'skills', package / 'skills', ignore=shutil.ignore_patterns('__pycache__'))
        shutil.copytree(ROOT / 'adapters', package / 'adapters')
        self.env['FAKE_PI_TOOLSET'] = str(package)
        result = self.run_runner('--dry-run')
        self.assertIn(f'Toolset:    {package} at unknown (Pi package)', result.stdout)
        self.env.pop('FAKE_PI_TOOLSET')
        result = self.run_runner('--dry-run')
        self.assertIn('(not a Pi package)', result.stdout)

    def test_setup_errors(self):
        bare = self.root / 'bare'
        bare.mkdir()
        self.git(bare, 'init', '-q')
        self.assertIn('No TODO.md', self.run_runner('--once', cwd=bare).stderr)
        self.assertIn('Not inside a Git repository', self.run_runner('--once', cwd=self.root).stderr)
        self.env['PI_AUTOWORK_PRIMARY'] = 'openai-codex/gpt-nope'
        self.assertIn('not in Pi', self.run_runner('--once').stderr)
        self.env.pop('PI_AUTOWORK_PRIMARY')
        self.assertIn('--workers must be 1 to 4', self.run_runner('--workers', '5').stderr)
        self.git(self.repo, 'switch', '-q', '-c', 'feature')
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 2)
        self.assertIn('is on branch feature', result.stderr)
        self.assertEqual(self.runs(), [])

    def test_hermes_autowork_job_on_the_same_repository_needs_allow(self):
        jobs = self.root / 'hermes/profiles/work/cron'
        jobs.mkdir(parents=True)
        (jobs / 'jobs.json').write_text(json.dumps({'jobs': [
            {'id': 'a1', 'name': 'Work Autowork', 'workdir': str(self.repo), 'enabled': True,
             'skills': ['hermes-toolset:autowork']},
            {'id': 'b2', 'name': 'Paused', 'workdir': str(self.repo), 'paused_at': 'x', 'skills': ['autowork']}]}))
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4)
        self.assertIn('work: Work Autowork', result.stderr)
        self.assertNotIn('Paused', result.stderr)
        self.assertEqual(self.run_runner('--once', '--allow-hermes').returncode, 0)


class ServiceTests(Fixture):
    """--install-service and --remove-service: pi-autowork@<repository name>.service."""
    def setUp(self):
        super().setUp()
        self.calls = self.root / 'systemctl.log'
        self.enabled = self.root / 'enabled'  # units the fake reports as enabled
        (self.bin / 'systemctl').write_text(
            '#!/bin/sh\necho "$@" >> ' + str(self.calls) + '\n'
            'if [ "$2" = is-enabled ]; then grep -qxF "$4" ' + str(self.enabled) + ' 2>/dev/null; exit $?; fi\n')
        (self.bin / 'systemctl').chmod(0o755)
        self.units, self.envs = self.root / 'units', self.root / 'envs'
        self.env.update(PI_AUTOWORK_UNIT_DIR=str(self.units), PI_AUTOWORK_ENV_DIR=str(self.envs),
                        PI_AUTOWORK_TASK_TIMEOUT='600')

    def legacy(self):
        return subprocess.run(['systemd-escape', '--path', str(self.repo)], capture_output=True, text=True).stdout.strip()

    def test_install_names_the_unit_after_the_repository(self):
        result = self.run_runner('--install-service', '--allow-hermes', '--workers', '3')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        unit = (self.units / 'pi-autowork@.service').read_text()
        for line in ('WorkingDirectory=~', f'ExecStart=/bin/bash {RUNNER} --repo ${{PI_AUTOWORK_REPO}}',
                     'KillSignal=SIGINT', 'KillMode=mixed', 'SuccessExitStatus=130', 'Restart=on-abnormal',
                     f'EnvironmentFile={self.envs}/%i.env', 'Description=pi-autowork for %i'):
            self.assertIn(line, unit)
        env = self.envs / 'project.env'
        lines = env.read_text().splitlines()
        for line in (f'PI_AUTOWORK_REPO={self.repo}', 'PI_AUTOWORK_ALLOW_HERMES=1', 'PI_AUTOWORK_TASK_TIMEOUT=600',
                     'PI_AUTOWORK_WORKERS=3'):
            self.assertIn(line, lines)
        self.assertTrue(any(l.startswith('PATH=') and str(self.bin) in l for l in lines))
        self.assertEqual(env.stat().st_mode & 0o777, 0o600)
        calls = self.calls.read_text().splitlines()
        self.assertEqual([c for c in calls if 'is-enabled' not in c],
                         ['--user daemon-reload', '--user enable pi-autowork@project.service',
                          '--user restart pi-autowork@project.service'])
        self.assertIn("journalctl --user -u 'pi-autowork@project.service'", result.stdout)
        self.assertEqual(self.runs(), [])
        if shutil.which('systemd-analyze'):  # systemd itself must accept the unit
            instance = self.root / 'verify' / 'pi-autowork@project.service'
            instance.parent.mkdir()
            instance.write_text(unit)
            check = subprocess.run(['systemd-analyze', '--user', 'verify', str(instance)], capture_output=True, text=True)
            self.assertEqual(check.returncode, 0, check.stdout + check.stderr)
            self.assertNotIn('bad unit file setting', check.stdout + check.stderr)

    def test_a_name_used_by_another_repository_is_refused(self):
        self.envs.mkdir()
        (self.envs / 'project.env').write_text('PI_AUTOWORK_REPO=/elsewhere/project\n')
        result = self.run_runner('--install-service')
        self.assertEqual(result.returncode, 2)
        self.assertIn('already runs /elsewhere/project', result.stderr)
        self.assertFalse(self.calls.exists())

    def test_an_earlier_path_named_unit_is_replaced(self):
        self.envs.mkdir()
        (self.envs / f'{self.legacy()}.env').write_text('PATH=/usr/bin\n')
        self.enabled.write_text(f'pi-autowork@{self.legacy()}.service\n')
        result = self.run_runner('--install-service')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'--user disable --now pi-autowork@{self.legacy()}.service', self.calls.read_text())
        self.assertFalse((self.envs / f'{self.legacy()}.env').exists())
        self.assertTrue((self.envs / 'project.env').exists())
        self.assertIn('Replaced the earlier unit', result.stdout)

    def test_remove_and_refusals(self):
        self.assertEqual(self.run_runner('--install-service').returncode, 0)
        result = self.run_runner('--remove-service')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.envs / 'project.env').exists())
        self.assertIn('--user disable --now pi-autowork@project.service', self.calls.read_text())
        self.assertEqual(self.run_runner('--install-service', '--dry-run').returncode, 2)


if __name__ == '__main__':
    unittest.main()
