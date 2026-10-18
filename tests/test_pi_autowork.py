"""Offline tests for scripts/pi-autowork.sh: the real Parallel Autowork engine and Git,
with a fake Pi standing in for workers, the reviewer and merge resolution.

These prove the runner's control flow only; they do not show that a real model
executes tasks (docs/cross-host.md describes the live qualification).
"""
import hashlib
import json
import os
from pathlib import Path
import re
import shlex
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


def setUpModule():
    # The runner deliberately reads committed code only. Build one committed
    # fixture from this task's production edits, not a mutable checkout under it.
    global ROOT, RUNNER, ENGINE_DIR, _toolset_fixture
    source = ROOT
    _toolset_fixture = tempfile.TemporaryDirectory()
    ROOT = Path(_toolset_fixture.name) / 'toolset'
    subprocess.run(['git', '-C', str(source), 'worktree', 'add', '-q', '--detach', str(ROOT), 'HEAD'], check=True)
    paths = ['pi-autowork/pi_autowork/release.py', 'pi-autowork/pi_autowork/coordinator.py', 'scripts/pi-autowork.sh']
    patch = subprocess.run(['git', '-C', str(source), 'diff', '--binary', 'HEAD', '--', *paths],
                           check=True, capture_output=True).stdout
    if patch:
        subprocess.run(['git', '-C', str(ROOT), 'apply', '-'], input=patch, check=True)
        subprocess.run(['git', '-C', str(ROOT), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                        'commit', '-qam', 'production code under test'], check=True)
    RUNNER = ROOT / 'scripts/pi-autowork.sh'
    ENGINE_DIR = ROOT / 'skills/autowork/scripts'


def tearDownModule():
    subprocess.run(['git', '-C', str(ROOT), 'worktree', 'remove', '--force', str(ROOT)], check=True)
    _toolset_fixture.cleanup()


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
    if os.environ.get('FAKE_PI_LIST'):
        print(os.environ['FAKE_PI_LIST'])
        sys.exit(0)
    if os.environ.get('FAKE_PI_TOOLSET'):
        print('User packages:\n  ' + os.environ['FAKE_PI_TOOLSET'] + '\n    ' + os.environ['FAKE_PI_TOOLSET'])
    sys.exit(0)
if args[:1] == ['update']:  # a new toolset commit, as `pi update` brings in
    note({'update': args[1:]})
    package, kind = os.environ['FAKE_PI_TOOLSET'], os.environ.get('FAKE_PI_UPDATE', 'change')
    if not os.path.exists(os.path.join(package, '.updated')):
        open(os.path.join(package, '.updated'), 'w').write(kind)
        script = os.path.join(package, 'scripts/pi-autowork.sh')
        if kind == 'broken':
            open(script, 'a').write('\nif then fi\n')
        else:
            open(script, 'a').write('\n# updated\n')
        subprocess.run(['git', '-C', package, '-c', 'user.email=u@example.invalid', '-c', 'user.name=U',
                        'commit', '-qam', 'update'], check=True)
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
elif message.startswith('Plan the file scope of task'):
    role, task = 'touches', re.search(r'of task (\S+) ', message)[1]
elif message.startswith('/skill:git-commit-push'):
    role, task = 'merge', None
elif 'could not run its checks because this is missing' in message:
    role, task = 'provision', re.search(r'review of task (\S+) ', message)[1]
elif message.startswith('You are the DOCS-MAINTAINER'):
    role, task = 'maintainer', None
else:
    role, task = 'worker', field('Task')
key = role if role in ('merge', 'maintainer') else f'{role}:{task}'
with open(os.environ['FAKE_PI_PLAN'], 'r+') as stream:
    fcntl.flock(stream, fcntl.LOCK_EX)
    plan = json.load(stream)
    queue = plan.get(key) or []
    behavior = queue.pop(0) if queue else {'worker': 'complete', 'verify': 'pass', 'merge': 'resolve', 'touches': 'own',
                                           'maintainer': 'nothing', 'provision': 'block'}[role]
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
if role == 'touches':
    finish(text='PI_AUTOWORK_TOUCHES: ' + ('NONE - only a live device operation' if behavior == 'none' else task + '.txt'))
elif role == 'verify':
    if behavior == 'tamper':
        open('tampered.txt', 'w').write('x\n')
    if behavior == 'slow_review':  # a review that runs a long check
        time.sleep(8)
        finish(text='Checked.\nPI_AUTOWORK_VERIFY: pass all checks')
    elif behavior == 'env':  # a required check cannot run: a tool is missing here
        finish(text='Checked.\nPI_AUTOWORK_VERIFY: fail environment — fake-sdk 1.0 (docs/SETUP.md)')
    elif behavior == 'needs_cache':  # passes only once the runner installed the tool
        ok = os.path.isdir(os.path.join(os.environ.get('AUTOWORK_CACHE', '/nonexistent'), 'fake-sdk-1.0'))
        finish(text='Checked.\nPI_AUTOWORK_VERIFY: ' + ('pass all checks' if ok else 'fail environment — fake-sdk 1.0'))
    else:
        finish(text='Checked.\nPI_AUTOWORK_VERIFY: ' + ('fail acceptance not met' if behavior == 'fail' else 'pass all checks'))
elif role == 'maintainer':
    if behavior == 'add_checks':  # restate A's contract: the Checks line it was missing
        text = open('TODO.md').read().replace('  Acceptance: A.txt says done\n',
                                              '  Acceptance: A.txt says done\n  Checks: test -s A.txt\n', 1)
        open('TODO.md', 'w').write(text)
        git('commit', '-qam', 'docs(tasks): restate A with the Checks line its sources give')
    elif behavior == 'repair_main':  # the red main gets one repair task, first in its section
        text = open('TODO.md').read().replace('## Next\n\n', '## Next\n\n- [ ] FIX — Repair main\n'
            '  Scope: Fix test_broken.\n  Touches: FIX.txt\n  Acceptance: FIX.txt says done\n'
            '  Checks: test -s FIX.txt\n  Dependencies: None.\n  Status: open\n', 1)
        open('TODO.md', 'w').write(text)
        git('commit', '-qam', 'docs(tasks): FIX repairs the red main')
    elif behavior == 'code':  # oversteps: edits product code
        open('A.txt', 'w').write('maintainer wrote code\n')
        git('add', 'A.txt'); git('commit', '-qm', 'not allowed')
    finish(text='PI_AUTOWORK_RESULT: completed A')
elif role == 'provision':
    if behavior == 'install':
        os.makedirs(os.path.join(os.environ['AUTOWORK_CACHE'], 'fake-sdk-1.0'), exist_ok=True)
        finish(text='Installed.\nPI_AUTOWORK_RESULT: completed — use $AUTOWORK_CACHE/fake-sdk-1.0')
    else:
        finish(text='PI_AUTOWORK_RESULT: blocked — no setup doc names it')
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
elif behavior == 'move_session':  # the session branch changes the task's own file meanwhile
    work()
    listing = subprocess.run(['git', '-C', os.environ['FAKE_MAIN_REPO'], 'worktree', 'list', '--porcelain'],
                             capture_output=True, text=True).stdout
    session = next(b.split('\n')[0][len('worktree '):] for b in listing.split('\n\n')
                   if 'branch refs/heads/pi-autowork/' in b)
    open(os.path.join(session, task + '.txt'), 'w').write('from the session\n')
    subprocess.run(['git', '-C', session, 'add', '-A'])
    subprocess.run(['git', '-C', session, '-c', 'user.email=s@example.invalid', '-c', 'user.name=Session',
                    'commit', '-qm', 'session moved'])
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
elif behavior == 'nothing':  # stops with no commit, no change and no report
    finish(text='done')
elif behavior == 'extra':  # also changes a file its Touches did not foresee
    open(task + '.txt', 'w').write('done ' + task + '\n')
    open(task + '-extra.txt', 'w').write('helper\n')
    git('add', '-A')
    git('commit', '-qm', 'worker ' + task)
    with open(field('Report file'), 'w') as out:
        json.dump({'task': task, 'commit': git('rev-parse', 'HEAD').stdout.strip(),
                   'changed_files': [task + '-extra.txt', task + '.txt'], 'checks': [], 'blockers': [],
                   'changelog': ''}, out)
    finish(text='done')
elif behavior == 'live':  # offline work done; a device check is left for a live task
    work()
    with open(field('Report file')) as stream:
        data = json.load(stream)
    data['pending_live'] = ['MediaStore read-back on a physical Android device']
    with open(field('Report file'), 'w') as stream:
        json.dump(data, stream)
    finish(text='done')
elif behavior == 'needs_file':  # needs a file outside its Touches: stops and asks for it
    open(task + '.txt', 'w').write('half ' + task + '\n')
    open(task + '-extra.txt', 'w').write('helper\n')
    with open(field('Report file'), 'w') as out:
        json.dump({'task': task, 'commit': None, 'changed_files': [], 'checks': [],
                   'blockers': [task + '-extra.txt is outside Touches'], 'needs_touches': [task + '-extra.txt'],
                   'changelog': ''}, out)
    finish(text='blocked')
elif behavior == 'needs_vendor':  # builds only with the ignored vendor/ tree of the main checkout
    if os.path.exists('vendor/sdk.txt'):
        work(); finish(text='done')
    else:
        report(None, ['missing ignored dependency vendor/sdk.txt'])
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


def host_environment():
    """os.environ without runner settings. A runner's settings reach every check it runs: a
    reviewer that inherited the service's PI_AUTOWORK_MAIN_CHECK and PI_AUTOWORK_NO_FALLBACK
    failed eight of these fixtures."""
    return {k: v for k, v in os.environ.items() if not k.startswith(('PI_AUTOWORK_', 'AUTOWORK_'))}


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
        self.env = {**host_environment(), 'PATH': f"{self.bin}:{os.environ['PATH']}", 'FAKE_PI_LOG': str(self.log),
                    'FAKE_PI_PLAN': str(self.plan_file), 'FAKE_PI_ROOT': str(self.root),
                    'FAKE_MAIN_REPO': str(self.repo),
                    'PI_AUTOWORK_TMP_STALE': '0',  # never sweep the host's real /tmp from a test
                    'PI_AUTOWORK_STATE_DIR': str(self.state), 'PI_AUTOWORK_HERMES_HOME': str(self.root / 'hermes'),
                    'PI_AUTOWORK_BACKOFF': '0', 'PI_AUTOWORK_MIN_FREE_MB': '0', 'XDG_STATE_HOME': str(self.root / 'xdg')}
        self.env.pop('GIT_CONFIG_COUNT', None)
        # The engine's load gate reads the real host: under a busy fleet it rightly starts
        # nothing and these runner scenarios fail for the wrong reason. As the engine's own
        # dispatch tests do, report an idle host to the engine processes the runner starts.
        shim = self.root / 'idle-host'
        shim.mkdir()
        (shim / 'sitecustomize.py').write_text('import os\nos.getloadavg = lambda: (0.0, 0.0, 0.0)\n')
        self.env['PYTHONPATH'] = os.pathsep.join(filter(None, [str(shim), os.environ.get('PYTHONPATH')]))
        self.plan({})
        self.addCleanup(self.remove_releases)
        self.addCleanup(self.stop_workers)

    def remove_releases(self):
        for path in (self.state / 'releases').glob('*/'):
            if (path / '.git').is_file():
                subprocess.run(['git', '-C', str(path), 'worktree', 'remove', '--force', str(path)],
                               capture_output=True)

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

    def run_runner(self, *args, script=None, cwd=None, env=None, timeout=120):
        return subprocess.run(['bash', str(script or RUNNER), *args], cwd=cwd or self.repo, env=env or self.env,
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
        # Seed the consumed artifacts of a completed A/B/C session, not another
        # worker/reviewer journey (covered by the parallel-and-merge test above).
        # A finished session has archived tasks, closed slots and no session.json;
        # the engine's detached integration worktree can still contain old tasks.
        archived = '# Completed tasks\n'
        for task, dependency in [('A', None), ('B', None), ('C', 'A')]:
            body = todo([(task, dependency)]).split('## Next\n\n', 1)[1]
            archived += ('\n\n<!-- archived from TODO.md -->\n\nSource section: Next\n\n'
                         + body.replace('- [ ]', '- [x]').replace('Status: open', 'Status: done'))
            (self.repo / f'{task}.txt').write_text(f'done {task}\n')
        (self.repo / 'TODO.md').write_text('# TODO\n\n[Completed tasks](TODO.archive.md)\n\n\n## Next\n\n\n')
        (self.repo / 'TODO.archive.md').write_text(archived)
        self.git(self.repo, 'add', 'TODO.md', 'TODO.archive.md', 'A.txt', 'B.txt', 'C.txt')
        self.git(self.repo, 'commit', '-qm', 'completed session fixture')
        common = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        state = self.state / hashlib.sha256(str(common).encode()).hexdigest()[:16]
        stale = state / 'worktrees/integration-autowork-integration'
        stale.parent.mkdir(parents=True)
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(stale), 'HEAD^')
        slots = common / 'autowork-execution/slots'
        slots.mkdir(parents=True)
        for task in 'ABC':
            (slots / f'{task}.json').write_text(json.dumps({
                'task_id': task, 'state': 'closed', 'attempt': 1,
                'worktree': str(state / f'worktrees/integration-autowork-{task}'),
                'branch': f'autowork/{task}', 'baseline': self.git(self.repo, 'rev-parse', 'HEAD^'),
                'started_at': 0,
            }))
        # The status consumer replays the prior coordinator's release as well as
        # the closed slots; no old lease or resumable Pi session remains.
        (common / 'autowork-execution/journal.jsonl').write_text(
            json.dumps({'timestamp': 0, 'event': 'coordinator_claimed',
                        'coordinator': {'max_workers': 2}}) + '\n'
            + json.dumps({'timestamp': 1, 'event': 'coordinator_released',
                          'coordinator': {'max_workers': 2}}) + '\n')
        status = self.run_runner('--status')
        self.assertEqual(status.returncode, 0, status.stdout + status.stderr)
        self.assertIn('0 running; 3 done', status.stdout)
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

    def test_invalid_touches_hold_the_task_while_independent_work_finishes(self):
        text = (self.repo / 'TODO.md').read_text().replace('Touches: A.txt', 'Touches: a/../b')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has invalid Touches')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertEqual([r['task'] for r in self.runs('worker')], ['B'])
        self.assertTrue(self.done('B'))
        self.assertIn('A: invalid Touches: a/../b', result.stdout)
        self.assertNotIn('engine needs attention', result.stdout)
        self.assertIn('invalid Touches: a/../b', self.run_runner('--status').stdout)

    def test_a_review_that_could_not_run_for_a_missing_tool_gets_it_installed_and_reviews_again(self):
        """TOOLSET-173-94: a commit was held on its last attempt for want of a pinned SDK."""
        self.plan({'verify:A': ['needs_cache', 'needs_cache'], 'provision:A': ['install']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its review could not run (fake-sdk 1.0); installing it into the toolchain cache', result.stdout)
        self.assertIn('A: installed what its review needed; verifying it again', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)  # no fresh attempt
        cache = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / \
            'autowork-execution' / 'cache'
        self.assertIn('for A (fake-sdk 1.0)', (cache / 'PROVISIONED.md').read_text())

    def test_a_missing_tool_that_cannot_be_installed_waits_for_a_person_without_pausing_the_runner(self):
        self.plan({'verify:A': ['env', 'env'], 'provision:A': ['block']})
        self.env['PI_AUTOWORK_MAX_FAILURES'] = '1'
        result = self.run_runner('--until-empty')
        self.assertIn('A: could not install what its review needs (fake-sdk 1.0 (docs/SETUP.md)); it waits for a person',
                      result.stdout)
        self.assertNotIn('in a row; pausing new tasks', result.stdout)
        self.assertTrue(self.done('B'))

    def unrunnable_a(self):
        text = (self.repo / 'TODO.md').read_text().replace('  Checks: test -s A.txt\n', '', 1)
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A lost its Checks line')

    def test_the_docs_maintainer_restates_a_task_that_is_not_runnable_as_written(self):
        """TOOLSET-164-f1: tasks the engine would not run waited hours for the owner."""
        self.unrunnable_a()
        self.plan({'maintainer': ['add_checks']})
        result = self.run_runner('--until-empty')
        self.assertIn('DOCS-MAINTAINER: repairing the task docs of A', result.stdout)
        self.assertIn('DOCS-MAINTAINER: merged; changed A', result.stdout)
        self.assertEqual(len(self.runs('maintainer')), 1)
        self.assertTrue(self.done('A', 'B', 'C'), result.stdout)
        self.assertIn('restate A with the Checks line', self.git(self.repo, 'log', '--format=%s'))

    def test_the_docs_maintainer_may_change_only_planning_files_and_runs_once_per_trigger_set(self):
        self.unrunnable_a()
        self.plan({'maintainer': ['code']})
        result = self.run_runner('--until-empty')
        self.assertIn('DOCS-MAINTAINER: refused: it changed more than planning files', result.stdout)
        self.assertFalse((self.repo / 'A.txt').exists() and 'maintainer wrote code' in (self.repo / 'A.txt').read_text())
        again = self.run_runner('--until-empty')  # the same trigger set: no second model call
        self.assertNotIn('DOCS-MAINTAINER: repairing', again.stdout)
        self.assertEqual(len(self.runs('maintainer')), 1)

    def main_record(self):
        found = list(self.state.glob('*/main_check.json'))
        return json.loads(found[0].read_text()) if found else {}

    def test_a_main_check_the_busy_host_cut_short_runs_again_before_green(self):
        """TOOLSET-193-54: tests the resource gate skipped are not checked, so main is not green yet."""
        self.env['PI_AUTOWORK_MAIN_CHECK'] = ("echo 'RESOURCE_GATE_SKIP: resource gate: load average 30.00 >= 24 CPUs'; "
                                              'true')
        (self.repo / 'TODO.md').write_text(todo([]))  # nothing lands, so main stays at one revision
        self.git(self.repo, 'commit', '-qam', 'nothing queued')
        runner = self.start_runner('--interval', '1')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 90
        while self.main_record().get('state') != 'green':
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        text = log()
        self.assertIn('the busy host skipped 1 test(s); checking it again when the load allows', text)
        self.assertEqual(text.count('Checking main at'), 2, text)  # once more, then green
        self.assertNotIn('Main is red', text)

    def test_a_main_check_finishes_and_is_reaped_after_a_reload(self):
        """A re-exec loses Popen, but the next cycle must consume and reap the finished check."""
        (self.repo / 'TODO.md').write_text(todo([]))
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        for code, result in [(0, 'green'), (1, 'red')]:
            with self.subTest(result=result):
                self.git(self.repo, 'commit', '-qam', 'empty queue', '--allow-empty')
                release = self.root / f'release-{code}'
                self.env['PI_AUTOWORK_MAIN_CHECK'] = (
                    f'while ! test -e {shlex.quote(str(release))}; do sleep 0.05; done; '
                    "echo 'FAIL: test_broken (test_other.OtherTests.test_broken)'; "
                    f'(exit {code})')
                runner = self.start_runner('--interval', '300')
                check_pid = None
                deadline = time.monotonic() + 60

                def wait_until(predicate):
                    while not predicate():
                        self.assertLess(time.monotonic(), deadline, log())
                        self.assertIsNone(runner.poll(), log())
                        time.sleep(0.05)

                try:
                    wait_until(lambda: self.main_record().get('state') == 'running')
                    record = self.main_record()
                    check_pid = record['pid']
                    self.assertIsNotNone(record.get('start_time'))
                    starts = log().count('Started (PID')
                    runner.send_signal(signal.SIGHUP)
                    wait_until(lambda: log().count('Started (PID') > starts)
                    # Keep the re-executed parent from cycling while its check becomes a zombie.
                    runner.send_signal(signal.SIGSTOP)
                    wait_until(lambda: Path(f'/proc/{runner.pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'T')
                    release.touch()
                    wait_until(lambda: Path(f'/proc/{check_pid}/stat').read_text().rsplit(')', 1)[1].split()[0] == 'Z')
                    self.assertEqual(Path(f'/proc/{check_pid}/stat').read_text().rsplit(')', 1)[1].split()[1],
                                     str(runner.pid))
                    runner.send_signal(signal.SIGHUP)  # wake its 300-second idle wait for one cycle
                    runner.send_signal(signal.SIGCONT)
                    wait_until(lambda: self.main_record().get('state') == result)
                    self.assertEqual(self.main_record()['rev'], record['rev'])
                    self.assertFalse(Path(f'/proc/{check_pid}').exists(), log())
                finally:
                    release.touch()
                    if runner.poll() is None:
                        runner.send_signal(signal.SIGCONT)
                        runner.send_signal(signal.SIGINT)
                    runner.communicate(timeout=60)
                    if check_pid and Path(f'/proc/{check_pid}').exists():
                        os.killpg(check_pid, signal.SIGKILL)

    def test_a_main_failure_that_passes_alone_is_green_without_a_maintainer(self):
        (self.repo / 'TODO.md').write_text(todo([]))
        tests = self.repo / 'tests'
        tests.mkdir()
        (tests / 'test_flaky.py').write_text(
            'import os, unittest\nclass Flaky(unittest.TestCase):\n'
            '    def test_flaky(self): self.assertNotIn("FULL_RUN", os.environ)\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'a test fails only in the full run')
        rev = self.git(self.repo, 'rev-parse', 'HEAD')
        self.env['PI_AUTOWORK_MAIN_CHECK'] = (
            'echo "CHECK tests (1 modules)"; cd tests; FULL_RUN=1 python3 -m unittest test_flaky')
        runner = self.start_runner('--interval', '1')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        try:
            deadline = time.monotonic() + 60
            while self.main_record().get('state') not in ('green', 'red'):
                self.assertLess(time.monotonic(), deadline, log())
                self.assertIsNone(runner.poll(), log())
                time.sleep(0.1)
            record = self.main_record()
            self.assertEqual(record['state'], 'green', log())
            self.assertEqual(record['flaky'], ['test_flaky.Flaky.test_flaky'])
            self.assertEqual(record['flaky_history'], {'test_flaky.Flaky.test_flaky': [rev]})
            self.assertFalse(self.runs('maintainer'), log())
        finally:
            runner.send_signal(signal.SIGINT)
            runner.communicate(timeout=60)

    def test_a_red_main_after_a_landing_gets_one_repair_task(self):
        """TOOLSET-176-98: a landing broke unrelated tests and nothing noticed."""
        tests = self.repo / 'tests'
        tests.mkdir()
        (tests / 'test_other.py').write_text(
            'from pathlib import Path\nimport unittest\nclass OtherTests(unittest.TestCase):\n'
            '    def test_broken(self): self.assertTrue(Path("../FIX.txt").is_file())\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'a genuinely broken test')
        self.env['PI_AUTOWORK_MAIN_CHECK'] = ('echo "CHECK tests (1 modules)"; '
                                              'cd tests; python3 -m unittest test_other')
        self.plan({'maintainer': ['repair_main']})
        runner = self.start_runner('--interval', '1')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 90
        while not ((self.repo / 'FIX.txt').exists() and self.done('FIX')):
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.5)
        while self.main_record().get('state') != 'green':  # FIX.txt now exists on main: green again
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        self.assertIn('Main is red at', log())
        self.assertIn('(test_other.OtherTests.test_broken)', log())
        self.assertIn('DOCS-MAINTAINER: repairing the task docs of MAIN', log())
        self.assertIn('Main is green again at', log())
        self.assertEqual(len(self.runs("maintainer")), 1, log())  # one repair for one set of failures

    def test_a_long_review_runs_beside_the_loop_so_other_work_starts(self):
        """TOOLSET-183-d6: a 25-minute review idled a whole runner: no dispatch, no status."""
        self.plan({'verify:A': ['slow_review']})
        runner = self.start_runner('--interval', '1')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'A: verifying' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        time.sleep(1)
        status = next(self.state.glob('*/status.json'))
        first = json.loads(status.read_text())['updated_at']
        # The review sleeps 8 s: the loop keeps cycling meanwhile, so status moves before A integrates.
        while json.loads(status.read_text())['updated_at'] <= first:
            self.assertNotIn('A: integrated', log())
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        self.assertNotIn('A: integrated', log())
        while not ((self.repo / 'C.txt').exists() and self.done('A', 'B', 'C')):
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        self.assertIn('A: integrated', log())

    def test_reloads_sent_while_the_runner_re_executes_never_end_it(self):
        """A SIGHUP sent while a runner re-executed, before its new handler existed, killed it,
        and systemd left the unit dead because death by SIGHUP is a clean exit."""
        (self.repo / 'TODO.md').write_text(todo([]))
        self.git(self.repo, 'commit', '-qam', 'nothing queued')
        runner = self.start_runner('--interval', '300')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'Queue empty; checking again in 300s' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        runner.send_signal(signal.SIGHUP)
        while 'Reloading' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.05)
        for _ in range(40):  # through the shell and Python start-up of the re-executed runner
            self.assertIsNone(runner.poll(), log())
            runner.send_signal(signal.SIGHUP)
            time.sleep(0.05)
        while log().count('Started (PID') < 2:
            self.assertIsNone(runner.poll(), log())
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        time.sleep(2)
        self.assertIsNone(runner.poll(), log())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)

    def test_a_reload_during_a_review_waits_until_its_answer_is_read(self):
        """TOOLSET-187-1d: a reload deferred behind a review re-executed as the review ended and
        lost its answer; the task failed as an abandoned integration and ran again."""
        self.plan({'verify:A': ['slow_review']})
        runner = self.start_runner('--interval', '1')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 90
        while 'A: verifying' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        runner.send_signal(signal.SIGHUP)
        while not ('Reloading' in log() and self.done('A', 'B', 'C')):
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        text = log()
        self.assertNotIn('abandoned integration', text)
        self.assertLess(text.index('A: integrated'), text.index('Reloading'), text)
        self.assertEqual(len([r for r in self.runs('verify') if r['task'] == 'A']), 1, text)

    def test_an_idle_runner_rests_when_only_other_refs_change(self):
        """TOOLSET-185-74: an idle runner started 213 sessions in 40 minutes: ending each empty
        session rewrote packed-refs, which counted as main changing."""
        (self.repo / 'TODO.md').write_text(todo([]))
        self.git(self.repo, 'commit', '-qam', 'nothing queued')
        runner = self.start_runner('--interval', '300')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'Queue empty; checking again in 300s' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        for n in range(4):  # packing and deleting other branches never moves main
            self.git(self.repo, 'branch', f'other-{n}')
            self.git(self.repo, 'pack-refs', '--all')
            self.git(self.repo, 'branch', '-D', f'other-{n}')
            time.sleep(1.5)
        time.sleep(4)  # past the settle time
        quiet = log()
        (self.repo / 'NOTE.md').write_text('a commit to main\n')
        self.git(self.repo, 'add', 'NOTE.md')
        self.git(self.repo, 'commit', '-qm', 'main moves')
        self.git(self.repo, 'pack-refs', '--all')  # moved, and recorded only in packed-refs
        while 'main changed; checking now' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        self.assertNotIn('changed; checking now', quiet)
        self.assertEqual(quiet.count('Queue empty'), 1, quiet)

    def test_a_review_that_runs_out_of_time_is_run_again_with_a_longer_limit(self):
        """TOOLSET-196-fb: a slow host spent a task's two attempts on review timeouts."""
        self.plan({'verify:A': ['slow_review']})  # 8 s against a 4 s limit; the second review is quick
        self.env['PI_AUTOWORK_VERIFY_TIMEOUT'] = '4'
        result = self.run_runner('--until-empty', timeout=180)
        self.assertTrue(self.done('A', 'B', 'C'), result.stdout)
        self.assertIn('A: its review ran out of time; reviewing the same commit again', result.stdout)
        self.assertEqual([r['task'] for r in self.runs('worker')].count('A'), 1)  # no second attempt
        self.assertNotIn('failed in a row', result.stdout)

    def test_a_reviewer_that_changes_files_fails_verification(self):
        self.plan({'verify:A': ['tamper', 'tamper']})
        result = self.run_runner('--once')
        self.assertNotEqual((self.repo / 'A.txt').read_text(), 'done A\n', result.stdout)
        self.assertFalse((self.repo / 'tampered.txt').exists())

    def test_a_service_waits_for_the_lock_instead_of_exiting(self):
        """Exit 3 is never restarted by systemd, so a service runner waits for the other runner to end."""
        self.run_runner('--once')  # creates the state folder
        lock = next(self.state.glob('*/lock'))
        holder = subprocess.Popen([sys.executable, '-c', 'import fcntl, sys, time; f = open(sys.argv[1], "a"); '
                                   'fcntl.flock(f, fcntl.LOCK_EX); print("held", flush=True); time.sleep(120)',
                                   str(lock)], stdout=subprocess.PIPE, text=True)
        self.addCleanup(lambda: (holder.kill(), holder.wait(), holder.stdout.close()))
        self.assertEqual(holder.stdout.readline().strip(), 'held')
        log = lock.parent / 'runner.log'
        runner = subprocess.Popen(['bash', str(RUNNER), '--interval', '1'], cwd=self.repo,
                                  env={**self.env, 'INVOCATION_ID': 'test'}, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        deadline = time.monotonic() + 60
        while 'waiting for it to exit' not in (log.read_text() if log.exists() else ''):
            self.assertIsNone(runner.poll(), runner.stderr.read() if runner.poll() is not None else '')
            self.assertLess(time.monotonic(), deadline, 'the service never waited')
            time.sleep(0.2)
        holder.kill()
        holder.wait()
        # Its SIGINT handler is installed once it has started; a stop before that, on a loaded
        # host, ended the process by the signal instead of its clean exit.
        while not re.search(r'The other runner exited; starting\.[\s\S]*Started \(PID', log.read_text()):
            self.assertLess(time.monotonic(), deadline + 30, log.read_text()[-1500:])
            time.sleep(0.2)
        runner.send_signal(signal.SIGINT)
        out, err = runner.communicate(timeout=120)
        self.assertEqual(runner.returncode, 130, out + err)

    def test_blocked_worker_is_held_not_merged(self):
        self.plan({'worker:A': ['blocked', 'blocked']})
        result = self.run_runner('--once')
        self.assertIn('A: failed', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), '')

    def test_the_hosts_runner_settings_never_reach_a_fixture(self):
        from unittest import mock
        with mock.patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='false', PI_AUTOWORK_NO_FALLBACK='1',
                             AUTOWORK_CACHE='/elsewhere', HOME_MARKER='kept'):
            env = host_environment()
        self.assertFalse({'PI_AUTOWORK_MAIN_CHECK', 'PI_AUTOWORK_NO_FALLBACK', 'AUTOWORK_CACHE'} & set(env))
        self.assertEqual(env['HOME_MARKER'], 'kept')

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
        # A deliberate stop pauses its workers: they resume the same attempt, retry intact.
        sessions = [r['session'] for r in self.runs('worker') if r['task'] in ('A', 'B')]
        self.assertEqual(len(sessions), 4, sessions)
        self.assertTrue(all(s.endswith('-attempt-1') for s in sessions), sessions)

    def test_a_restart_does_not_replay_earlier_results(self):
        """india: every start printed each finished task again, as if it were new."""
        self.plan({'worker:B': ['sleep', 'complete']})
        runner = self.start_runner()
        self.wait_for(self.root / 'sleeping-B')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'A: done' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertNotIn('A: done', result.stdout)
        self.assertIn('B: done', result.stdout)
        self.assertNotIn(': pending', result.stdout)

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

    def test_a_reload_keeps_the_runner_and_its_worker_and_applies_new_settings(self):
        """TOOLSET-174-1d: `autowork restart` paused every worker; one cost a 10-minute run."""
        self.plan({'worker:A': ['slow']})
        settings = self.root / 'india.env'
        settings.write_text('PI_AUTOWORK_COOLDOWN=0\n')
        self.env['PI_AUTOWORK_ENV_FILE'] = str(settings)
        self.env['FAKE_PI_CATALOG'] = 'openai-codex gpt-6.1-sol;openai-codex gpt-6-luna;openrouter deepseek/deepseek-v4.1-flash'
        runner = self.start_runner('--workers', '1', '--interval', '1')
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        self.wait_for(self.root / 'busy-A')
        worker = int((self.root / 'busy-A').read_text())
        settings.write_text('PI_AUTOWORK_PRIMARY=openai-codex/gpt-6-luna\n')  # as `autowork model` writes it
        runner.send_signal(signal.SIGHUP)
        deadline = time.monotonic() + 60
        while 'Reloading' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        os.kill(worker, 0)  # the worker runs on
        while not list(self.state.glob('*/runner.json')):  # written again by the re-executed runner
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        record = json.loads(next(self.state.glob('*/runner.json')).read_text())
        self.assertEqual((record['pid'], record['reloads']), (runner.pid, 1))
        while not self.done('A', 'B', 'C'):
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.5)
        self.assertNotIn('Stopping', log())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        workers = {r['task']: r['model'] for r in self.runs('worker')}
        self.assertEqual([r['task'] for r in self.runs('worker')].count('A'), 1, log())
        self.assertEqual((workers['A'], workers['B']), ('gpt-6.1-sol', 'gpt-6-luna'))

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

    def test_tasks_waiting_on_unfinished_dependencies_are_not_an_empty_queue(self):
        """india: every open task waited on human input, and the runner said "Queue empty"."""
        text = (self.repo / 'TODO.md').read_text().replace('Dependencies: None.', 'Dependencies: Z.')
        (self.repo / 'TODO.md').write_text(text + '\n- [ ] Z — Needs a device\n  Scope: Hardware check\n'
                                           '  Acceptance: A person confirms it\n  Checks: manual\n'
                                           '  Dependencies: H.\n  Status: open\n')
        self.git(self.repo, 'commit', '-qam', 'everything waits on Z, which waits on a human')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
        self.assertIn('No task can start now', result.stdout)
        self.assertNotIn('Queue empty', result.stdout)
        self.assertEqual(self.runs(), [])

    def test_a_waiting_runner_sees_tasks_committed_to_main_later(self):
        """india: tasks committed to main while the runner waited were never dispatched."""
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('Dependencies: None.', 'Dependencies: Z.'))
        self.git(self.repo, 'commit', '-qam', 'everything waits on a missing Z')
        runner = self.start_runner('--interval', '1')
        deadline = time.monotonic() + 30
        while 'No task can start now' not in (self.state.glob('*/runner.log').__next__().read_text()
                                               if list(self.state.glob('*/runner.log')) else ''):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.2)
        self.git(self.repo, 'checkout', '--', 'TODO.md')
        (self.repo / 'TODO.md').write_text(text)  # A and B become runnable on main
        self.git(self.repo, 'commit', '-qam', 'unblock')
        deadline = time.monotonic() + 60
        while not self.done('A'):
            self.assertLess(time.monotonic(), deadline, 'runner never picked up the new tasks')
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)

    def test_a_running_runner_restarts_on_an_updated_toolset(self):
        """A `pi update` under a live runner mixed the old script with the new engine."""
        toolset = self.root / 'toolset'
        self.git(ROOT, 'worktree', 'add', '-q', '--detach', str(toolset), 'HEAD')
        self.addCleanup(lambda: self.git(toolset, 'worktree', 'remove', '--force', str(toolset)))
        self.plan({'worker:A': ['sleep']})
        env = {**self.env, 'PI_AUTOWORK_TOOLSET': str(toolset)}
        runner = subprocess.Popen(['bash', str(toolset / 'scripts/pi-autowork.sh'), '--interval', '1', '--workers', '1'],
                                  cwd=self.repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: runner.poll() is None and (runner.kill(), runner.wait()))
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        self.wait_for(self.root / 'sleeping-A')
        worker_pid = int((self.root / 'sleeping-A').read_text())
        old_release = self.state / 'releases' / self.git(toolset, 'rev-parse', 'HEAD')
        self.assertTrue(old_release.is_dir())
        (toolset / 'NEW').write_text('update\n')
        self.git(toolset, 'add', 'NEW')
        self.git(toolset, '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-qm', 'update')
        rev = self.git(toolset, 'rev-parse', '--short', 'HEAD')
        deadline = time.monotonic() + 30
        while log().count('Started (PID') < 2:
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        self.assertIn(f'Toolset updated to {rev}; restarting on it', log())
        self.assertIsNone(runner.poll())
        new_release = self.state / 'releases' / self.git(toolset, 'rev-parse', 'HEAD')
        self.assertIn(os.fsencode(f'PI_AUTOWORK_TOOLSET={old_release}'),
                      Path(f'/proc/{worker_pid}/environ').read_bytes().split(b'\0'))
        self.assertIn(os.fsencode(f'PI_AUTOWORK_TOOLSET={new_release}'),
                      Path(f'/proc/{runner.pid}/environ').read_bytes().split(b'\0'))
        runner.send_signal(signal.SIGINT)
        out, err = runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130, out + err)
        self.assertIn(f'at {rev}', out)

    def test_a_tampering_reviewer_fails_once_and_never_wedges_integration(self):
        """The engine resets its own integration worktree, keeping the residue as a patch;
        nothing else is reset, and independent work keeps landing."""
        self.plan({'verify:A': ['tamper', 'tamper']})
        result = self.run_runner('--until-empty', '--workers', '1')
        self.assertIn('A: failed', result.stdout)
        self.assertTrue(self.done('B'), result.stdout)  # integrated after A's tampered review
        self.assertFalse((self.repo / 'tampered.txt').exists())
        common = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        patches = list((common / 'autowork-execution' / 'integration-residue').glob('*.patch'))
        self.assertTrue(patches)
        self.assertIn('tampered.txt', patches[0].read_text())

    def test_closing_commits_only_the_files_the_close_wrote(self):
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        closes = self.git(self.repo, 'log', '--format=%H', '--grep=^docs(tasks): close').split()
        self.assertTrue(closes)
        for commit in closes:
            files = set(self.git(self.repo, 'show', '--format=', '--name-only', commit).split())
            self.assertLessEqual(files, {'TODO.md', 'goals.json', 'TODO.archive.md'}, commit)

    def test_the_touches_pass_reads_a_disposable_copy_of_the_session(self):
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        cwd = self.runs('touches')[0]['cwd']
        self.assertEqual(Path(cwd).parent, self.repo / '.worktrees')
        self.assertTrue(Path(cwd).name.startswith('pi-scratch-touches-'))
        self.assertFalse(Path(cwd).exists())
        self.assertNotIn(cwd, self.git(self.repo, 'worktree', 'list'))

    def test_a_set_aside_request_lets_a_blocked_task_run_fresh(self):
        self.plan({'worker:A': ['blocked']})
        first = self.run_runner('--until-empty')
        self.assertIn('A: failed — worker reported a blocker', first.stdout)
        self.assertTrue(self.done('B'))  # the blocked task stops nothing independent
        request = self.run_runner('--set-aside', 'A')
        self.assertEqual(request.returncode, 0, request.stdout + request.stderr)
        self.assertIn('Requested: set aside A', request.stdout)
        second = self.run_runner('--until-empty')
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertIn('A: set aside on request', second.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertIn('autowork/A-set-aside-1', self.git(self.repo, 'branch', '--list', 'autowork/*'))

    def test_holds_found_at_start_do_not_count_toward_the_failure_streak(self):
        """flutter: three self-restarts re-counted the same old holds and the service quit."""
        self.plan({'worker:A': ['blocked']})
        self.run_runner('--until-empty')
        self.env['PI_AUTOWORK_MAX_FAILURES'] = '1'
        again = self.run_runner('--until-empty')
        self.assertNotIn('failed tasks in a row', again.stdout)

    def test_a_service_pauses_after_a_failure_streak_instead_of_exiting(self):
        # Workers that produce nothing, twice: something is broken for every task.
        self.plan({'worker:A': ['nothing', 'nothing'], 'worker:B': ['nothing', 'nothing']})
        env = {**self.env, 'PI_AUTOWORK_MAX_FAILURES': '1', 'PI_AUTOWORK_FAILURE_PAUSE': '3600'}
        runner = subprocess.Popen(['bash', str(RUNNER), '--interval', '1'], cwd=self.repo, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'pausing new tasks for 3600s' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.2)
        time.sleep(3)
        self.assertIsNone(runner.poll(), log())  # still serving, not finished
        self.assertNotIn('Finished.', log())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130)

    def test_holds_about_one_task_do_not_pause_the_runner(self):
        """Three overlap and validation holds in a row paused a whole runner for an hour."""
        self.plan({'worker:A': ['blocked'], 'worker:B': ['blocked']})
        self.env['PI_AUTOWORK_MAX_FAILURES'] = '1'
        result = self.run_runner('--until-empty')
        self.assertNotIn('in a row; pausing new tasks', result.stdout)
        self.assertIn('A: failed — worker reported a blocker', result.stdout)

    def test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why(self):
        """2026-10-16: four services sat idle for seven hours and only logged a poll line."""
        self.plan({'worker:A': ['blocked']})  # C depends on A: nothing can run once B is done
        env = {**self.env, 'PI_AUTOWORK_STALL_AFTER': '2'}
        runner = subprocess.Popen(['bash', str(RUNNER), '--interval', '1'], cwd=self.repo, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'STALLED' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        time.sleep(4)  # several more cycles: still announced only once
        self.assertEqual(log().count('STALLED'), 1, log())
        self.assertIn('Root blockers: A (held for a person: its worker reported a blocker, holds 1)', log())
        fleet = subprocess.run(['bash', str(RUNNER), '--fleet'], cwd=self.root, env=self.env,
                               capture_output=True, text=True, timeout=60)
        self.assertEqual(fleet.returncode, 0, fleet.stderr)
        self.assertIn(f'{self.repo.name}', fleet.stdout)
        self.assertIn('stalled for 0 min; 0 running, 1 waiting', fleet.stdout)
        self.assertIn('    blocked by A (held for a person: its worker reported a blocker, holds 1)', fleet.stdout)
        status = self.run_runner('--status')
        self.assertIn('Health:     stalled since', status.stdout)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)

    def test_a_claim_idle_long_enough_is_adopted_and_finished(self):
        text = (self.repo / 'TODO.md').read_text()
        text = text.replace('  Dependencies: None.\n  Status: open\n- [ ] B', '  Dependencies: None.\n  Status: in_progress\n- [ ] B', 1)
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A is claimed elsewhere')
        self.run_runner('--until-empty')  # default: a fresh claim is never adopted
        self.assertNotIn('A', [r['task'] for r in self.runs('worker')])
        time.sleep(2)
        self.env['PI_AUTOWORK_CLAIM_IDLE'] = '1'
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: running — worker started; adopted an idle claim', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def ledger_with_recorded_order(self):
        goals = str(ROOT / 'skills/docs-sync/scripts/goals.py')
        # Z waits in Needs decision, so the goal keeps an open task after A, B and C close.
        data = {'version': 1, 'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md', 'status': 'partial',
                                          'tasks': ['A', 'B', 'C', 'Z'], 'priority': 1, 'depends_on': []}],
                'tasks': [{'id': t, 'title': 'Task ' + t, 'goal': 'G', 'status': 'open',
                           'section': 'Needs decision' if t == 'Z' else 'Next',
                           'depends_on': ['A'] if t == 'C' else []} for t in 'ABCZ']}
        (self.repo / 'goals.json').write_text(json.dumps(data))
        with (self.repo / 'TODO.md').open('a') as todo_file:
            todo_file.write('\n## Needs decision\n\n- [ ] Z — Task Z\n  Scope: Z\n  Acceptance: a person decides\n'
                            '  Checks: manual\n  Dependencies: None.\n  Status: open\n')
        dry = json.loads(subprocess.run([sys.executable, goals, 'bootstrap-order', str(self.repo), '--dry-run'],
                                        check=True, capture_output=True, text=True).stdout)
        subprocess.run([sys.executable, goals, 'bootstrap-order', str(self.repo), '--expected-revision',
                        dry['revision']], check=True, capture_output=True, text=True)
        self.git(self.repo, 'add', '-A')
        self.git(self.repo, 'commit', '-qm', 'ledger with recorded order')

    def test_a_changed_todo_order_is_recorded_once_and_work_continues(self):
        """flutter: the runner said "run goals.py reorder" and waited; scheduled runs record it."""
        self.ledger_with_recorded_order()
        text = (self.repo / 'TODO.md').read_text()
        a, b = text.index('- [ ] A'), text.index('- [ ] B')
        c = text.index('- [ ] C')
        (self.repo / 'TODO.md').write_text(text[:a] + text[b:c] + text[a:b] + text[c:])  # a person puts B first
        self.git(self.repo, 'commit', '-qam', 'B first')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(result.stdout.count('recorded the new order'), 1, result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertIn('docs(tasks): record TODO.md priority order (pi-autowork)',
                      self.git(self.repo, 'log', '--format=%s'))

    def test_a_service_stays_up_and_reports_when_the_engine_needs_attention(self):
        """An invalid ledger made the runner exit, and systemd does not restart a deliberate exit."""
        (self.repo / 'goals.json').write_text('{"version": 1, "goals": [], "tasks": [{"id": "A"}]}')
        self.git(self.repo, 'add', 'goals.json')
        self.git(self.repo, 'commit', '-qm', 'broken ledger')
        env = {**self.env, 'PI_AUTOWORK_STALL_AFTER': '1'}
        runner = subprocess.Popen(['bash', str(RUNNER), '--interval', '1'], cwd=self.repo, env=env,
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'STALLED' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.2)
        self.assertEqual(log().count('The engine needs attention'), 1, log())
        self.assertIn('the engine needs attention: invalid goals.json', log())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130)

    def test_uncommitted_planning_waits_once_then_dispatches_after_commit(self):
        for stage_all in (False, True):
            with self.subTest(stage_all=stage_all):
                self.repo = self.make_repo(self.root / f'planning-{stage_all}', [('A', None), ('B', None), ('C', 'A')])
                self.env['FAKE_MAIN_REPO'] = str(self.repo)
                self.log.unlink(missing_ok=True)
                self.ledger_with_recorded_order()
                self.git(self.repo, 'rm', '--cached', 'TODO.md', 'goals.json')
                question = self.repo / 'BLOCKERS.md'
                question.write_text('# Blockers\n\n## Active\n\nOwner note: preserve me.\n')
                self.git(self.repo, 'add', 'BLOCKERS.md')
                self.git(self.repo, 'commit', '-qm', 'planning only on disk')
                self.env.update(PI_AUTOWORK_PLAN_SETTLE='0', PI_AUTOWORK_PLANNING_QUIET='600')
                if not stage_all:
                    # Interrupt recovery just before restoring owner prose; a restart must
                    # retain the receipt and finish restoration, not leave a dirty scaffold.
                    shim = self.root / 'idle-host' / 'sitecustomize.py'
                    with shim.open('a') as stream:
                        stream.write('\nfrom pathlib import Path\n'
                                     '_write_text = Path.write_text\n'
                                     'def write_text(path, data, *args, **kwargs):\n'
                                     '    insertion = Path(os.environ["FAKE_PI_ROOT"]) / "interrupt-insertion"\n'
                                     '    if path.name == "BLOCKERS.md" and "Q-RUNNER-PLANNING" in data and insertion.exists():\n'
                                     '        insertion.unlink()\n'
                                     '        os._exit(98)\n'
                                     '    marker = Path(os.environ["FAKE_PI_ROOT"]) / "interrupt-recovery"\n'
                                     '    if path.name == "BLOCKERS.md" and "Owner note:" in data '
                                     'and "pi-autowork:questions:start" not in data and marker.exists():\n'
                                     '        marker.unlink()\n'
                                     '        os._exit(99)\n'
                                     '    return _write_text(path, data, *args, **kwargs)\n'
                                     'Path.write_text = write_text\n')
                    (self.root / 'interrupt-insertion').touch()
                self.plan({'worker:A': ['blocked']})
                runner = self.start_runner('--interval', '1')
                self.addCleanup(lambda r=runner: r.poll() is None and r.kill())
                common = self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                folder = self.state / hashlib.sha256(common.encode()).hexdigest()[:16]
                log = lambda: (folder / 'runner.log').read_text() if (folder / 'runner.log').exists() else ''
                if not stage_all:
                    runner.communicate(timeout=30)
                    self.assertEqual(runner.returncode, 98, log())
                    self.assertTrue((folder / 'planning-question.json').exists())
                    time.sleep(1.1)  # cross a timestamp boundary before retrying the pending write
                    runner = self.start_runner('--interval', '1')
                    self.addCleanup(lambda r=runner: r.poll() is None and r.kill())
                deadline = time.monotonic() + 30
                while 'planning files are not committed on main' not in question.read_text():
                    self.assertLess(time.monotonic(), deadline, log())
                    self.assertIsNone(runner.poll(), log())
                    time.sleep(0.1)
                before = question.read_text()
                time.sleep(3)  # several cycles: neither the log nor the question repeats
                self.assertEqual(question.read_text(), before)
                self.assertEqual(log().count('Runner blocked:'), 1, log())
                status = json.loads((folder / 'status.json').read_text())
                self.assertEqual(len([r for r in status['roots'] if r['kind'] == 'runner']), 1)
                self.assertIn('planning files are not committed on main', status['blocker'])
                self.assertEqual(self.runs(), [])
                self.assertEqual(self.git(self.repo, 'ls-tree', '--name-only', 'main', 'TODO.md', 'goals.json'), '')
                self.git(self.repo, 'add', 'TODO.md')
                self.git(self.repo, 'commit', '-qm', 'commit TODO only')
                time.sleep(3)
                self.assertEqual(self.runs(), [])  # an uncommitted index still holds dispatch
                self.assertEqual(log().count('Runner blocked:'), 1, log())
                if not stage_all:
                    (self.root / 'interrupt-recovery').touch()
                self.git(self.repo, 'add', '-A' if stage_all else 'goals.json')
                self.git(self.repo, 'commit', '-qm', 'commit planning')
                if not stage_all:
                    runner.communicate(timeout=30)
                    self.assertEqual(runner.returncode, 99, log())
                    self.assertTrue((folder / 'planning-question.json').exists())
                    runner = self.start_runner('--interval', '1')
                    self.addCleanup(lambda r=runner: r.poll() is None and r.kill())
                deadline = time.monotonic() + 90
                while '### Q-A ' not in question.read_text():
                    self.assertLess(time.monotonic(), deadline, log())
                    self.assertIsNone(runner.poll(), log())
                    time.sleep(0.2)
                self.assertTrue(self.runs('worker'))
                runner.send_signal(signal.SIGINT)
                runner.communicate(timeout=120)
                self.assertNotIn('The engine needs attention', log())
                self.assertNotIn('planning files are not committed', question.read_text())
                self.assertIn('Owner note: preserve me.', question.read_text())

    def test_an_idle_runner_starts_new_work_as_soon_as_todo_changes(self):
        """The owner plans; the runner reacts to the plan, not to its polling interval."""
        (self.repo / 'TODO.md').write_text(todo([]))
        self.git(self.repo, 'commit', '-qam', 'nothing queued')
        runner = self.start_runner('--interval', '300')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 60
        while 'Queue empty; checking again in 300s' not in log():
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.2)
        (self.repo / 'D.txt').write_text('')
        (self.repo / 'TODO.md').write_text(todo([('D', None)]))
        self.git(self.repo, 'add', '-A')
        self.git(self.repo, 'commit', '-qm', 'plan D')
        changed = time.monotonic()
        while 'changed; checking now' not in log():
            self.assertLess(time.monotonic() - changed, 30, log())  # well inside the 300 s interval
            time.sleep(0.2)
        while not self.done('D'):
            self.assertLess(time.monotonic() - changed, 120, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.5)
        self.assertEqual(len([r for r in self.runs('worker') if r.get('task') == 'D']), 1, self.runs())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=120)

    def test_listed_ignored_dependencies_are_linked_into_task_worktrees(self):
        """sierra TASK-022: a gitignored source tree in the main checkout was missing in worktrees."""
        (self.repo / '.gitignore').write_text('vendor/\n')
        self.git(self.repo, 'add', '.gitignore')
        self.git(self.repo, 'commit', '-qm', 'ignore vendor')
        (self.repo / 'vendor').mkdir()
        (self.repo / 'vendor' / 'sdk.txt').write_text('sdk\n')
        self.plan({'worker:A': ['needs_vendor']})
        without = self.run_runner('--once')
        self.assertIn('A: failed — worker reported a blocker: missing ignored dependency', without.stdout)
        self.run_runner('--set-aside', 'A')
        self.plan({'worker:A': ['needs_vendor']})
        self.env['PI_AUTOWORK_LINK_PATHS'] = 'vendor'
        result = self.run_runner('--until-empty')
        logs = ''.join(p.read_text() for p in Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')).glob('autowork-execution/slot-data/A/attempt-*/worker.log'))
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr + logs)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')  # nothing linked is committed

    def test_a_commit_outside_inferred_touches_is_reverified_after_widening(self):
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        self.plan({'worker:A': ['extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its commit changed files outside the inferred Touches (A-extra.txt); widened them', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)  # same commit, no rerun
        self.assertEqual((self.repo / 'A-extra.txt').read_text(), 'helper\n')

    def test_a_commit_outside_authored_touches_is_widened_once_and_reverified(self):
        """TOOLSET-152-d4: the same commit is verified again, with no new attempt."""
        self.plan({'worker:A': ['extra', 'extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its commit changed files outside Touches (A-extra.txt); widened them once and verifying again',
                      result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)
    def test_a_worker_asking_for_files_outside_inferred_touches_resumes_after_widening(self):
        """sierra TASK-024, bravo TASK-005: a worker needed one more file and stopped."""
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        self.plan({'worker:A': ['needs_file', 'extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its worker needs files outside the inferred Touches (A-extra.txt); widened them and '
                      'resuming it in its worktree', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        workers = [r for r in self.runs('worker') if r['task'] == 'A']
        self.assertEqual(len(workers), 2)
        self.assertEqual(workers[0]['cwd'], workers[1]['cwd'])  # resumed in the same worktree
        self.assertEqual((self.repo / 'A-extra.txt').read_text(), 'helper\n')
        self.assertNotIn('A: failed', result.stdout)  # a request is not a failure

    def test_touches_an_older_run_inferred_are_recognized_from_its_commit(self):
        """Touches inferred before the runner kept a record (sierra TASK-024) can still be widened."""
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('  Touches: A.txt\n', ''))
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        (self.repo / 'TODO.md').write_text(text)  # as an earlier pi-autowork run recorded it
        self.git(self.repo, 'commit', '-qam', 'docs(tasks): declare Touches for A (pi-autowork)')
        self.plan({'worker:A': ['needs_file', 'extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its worker needs files outside the inferred Touches (A-extra.txt)', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_inferred_touches_a_person_edited_since_still_get_the_bounded_widening(self):
        """A held task's Touches were inferred once, then rewritten by hand: the inferred
        widening refused and nothing else was tried, so one file waited for the owner."""
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('  Touches: A.txt\n', ''))
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'docs(tasks): declare Touches for A (pi-autowork)')
        (self.repo / 'TODO.md').write_text(text.replace('  Touches: A.txt\n', '  Touches: A.txt, notes.md\n'))
        self.git(self.repo, 'commit', '-qam', 'a person edits A')
        self.plan({'worker:A': ['needs_file', 'extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its worker needs files outside Touches (A-extra.txt); widened them once', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_worker_asking_for_files_outside_authored_touches_resumes_after_one_widening(self):
        """TOOLSET-152-d4: the worker names the exact file, so no person is needed."""
        self.plan({'worker:A': ['needs_file', 'extra']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its worker needs files outside Touches (A-extra.txt); widened them once and resuming it '
                      'in its worktree', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        workers = [r for r in self.runs('worker') if r['task'] == 'A']
        self.assertEqual(len(workers), 2)
        self.assertEqual(workers[0]['cwd'], workers[1]['cwd'])
        self.assertNotIn('A: failed', result.stdout)
        self.assertIn('Touches widened by the runner from worker evidence: A-extra.txt',
                      self.git(self.repo, 'log', '-p', '-1', '--grep=widen Touches for A from worker evidence'))

    def test_a_second_request_after_one_widening_waits_for_a_person(self):
        text = (self.repo / 'TODO.md').read_text().replace(
            '  Touches: A.txt\n', '  Touches: A.txt\n  Touches widened by the runner from worker evidence: A.txt\n')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A was widened once')
        self.plan({'worker:A': ['needs_file']})
        result = self.run_runner('--until-empty')
        self.assertNotIn('widened them', result.stdout)
        self.assertIn('A: failed — worker reported a blocker: A-extra.txt is outside Touches', result.stdout)
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)

    def test_the_repository_settings_file_applies_to_every_launcher(self):
        """`tx autowork` runs in tmux without the service's environment: settings follow the repository."""
        envs = self.root / 'envs'
        envs.mkdir()
        self.env['PI_AUTOWORK_ENV_DIR'] = str(envs)
        (envs / 'project.env').write_text(f'PI_AUTOWORK_REPO={self.repo}\nPATH=/nowhere\nPI_AUTOWORK_WORKERS=3\n')
        self.assertIn('up to 3 worker(s)', self.run_runner('--dry-run').stdout)
        self.env['PI_AUTOWORK_WORKERS'] = '2'  # the environment wins
        self.assertIn('up to 2 worker(s)', self.run_runner('--dry-run').stdout)
        del self.env['PI_AUTOWORK_WORKERS']
        (envs / 'project.env').write_text('PI_AUTOWORK_REPO=/elsewhere/project\nPI_AUTOWORK_WORKERS=3\n')
        self.assertIn('up to 8 worker(s)', self.run_runner('--dry-run').stdout)  # another repository's file

    def test_a_pending_merge_names_the_files_that_block_it(self):
        """Every fleet main checkout had uncommitted TODO.md edits; the message stopped before the file names."""
        self.plan({'worker:A': ['slow']})
        runner = subprocess.Popen(['bash', str(RUNNER), '--until-empty'], cwd=self.repo, env=self.env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        busy = self.root / 'busy-A'
        deadline = time.monotonic() + 60
        while not busy.exists():
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.1)
        with (self.repo / 'TODO.md').open('a') as todo:  # a person edits the backlog meanwhile
            todo.write('\n<!-- a note being written -->\n')
        out, _ = runner.communicate(timeout=120)
        self.assertEqual(runner.returncode, 4, out)
        self.assertRegex(out, r'Merge pending: main in .* could not take pi-autowork/[0-9-]+: .*TODO\.md')

    def test_the_reviewer_is_told_which_live_checks_the_worker_left_pending(self):
        """flutter TASK-006: offline checks passed; the review failed for want of a device."""
        self.plan({'worker:A': ['live']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        reviews = {r['task']: r['message'] for r in self.runs('verify')}
        self.assertIn('MediaStore read-back on a physical Android device', reviews['A'])
        self.assertIn('Do not fail for those', reviews['A'])
        self.assertIn('recorded no pending live checks', reviews['B'])  # strict when nothing was recorded
        self.assertIn('A: done offline; its live checks are recorded as A-LIVE', result.stdout)

    def test_a_changed_reviewer_reviews_held_commits_again_by_itself(self):
        """flutter: three commits sat held after an older reviewer failed them; nobody should have to ask."""
        self.plan({'verify:A': ['fail', 'fail']})
        first = self.run_runner('--until-empty')
        self.assertIn('A: failed', first.stdout)
        reviews = lambda: len([r for r in self.runs('verify') if r['task'] == 'A'])
        self.assertEqual(reviews(), 2)  # the first attempt and its fresh retry
        same = self.run_runner('--until-empty')  # the same reviewer: nothing reviewed again
        self.assertNotIn('verifying it again', same.stdout)
        self.assertEqual(reviews(), 2)
        self.env['PI_AUTOWORK_VALIDATE'] = 'true'  # validation changed: a new reviewer version
        self.plan({'verify:A': ['pass']})
        changed = self.run_runner('--until-empty')
        self.assertEqual(changed.returncode, 0, changed.stdout + changed.stderr)
        self.assertIn('A: the reviewer changed since this commit was held; verifying it again', changed.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(reviews(), 3)

    def test_editing_a_held_tasks_entry_answers_it_and_the_runner_reruns_it(self):
        """TOOLSET-120-fc: the owner only answers; no --set-aside, no restart."""
        self.plan({'worker:A': ['blocked']})
        first = self.run_runner('--until-empty')
        self.assertIn('A: failed — worker reported a blocker: needs a device', first.stdout)
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)
        again = self.run_runner('--until-empty')  # no answer yet: nothing reruns
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('  Acceptance: A.txt says done\n',
                                                        '  Acceptance: A.txt says done; the emulator is enough\n', 1))
        self.git(self.repo, 'commit', '-qam', 'owner answers A')
        self.plan({})
        answered = self.run_runner('--until-empty')
        self.assertEqual(answered.returncode, 0, answered.stdout + answered.stderr)
        self.assertIn("A: its TODO entry changed while it was held; running it fresh (earlier work kept as "
                      "autowork/A-set-aside-1)", answered.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def owner_note(self):
        # The owner's own planning file; TODO.md edits would meet the session's archive edits,
        # which only the fake Pi's crude conflict resolution handles in these fixtures.
        (self.repo / 'BLOCKERS.md').write_text('# Blockers\n\n## Active\n\n- next week, add the export task\n')

    def test_uncommitted_owner_planning_is_committed_so_work_merges(self):
        """TOOLSET-120-fc (4): every fleet main checkout held uncommitted TODO.md edits."""
        self.owner_note()
        self.env['PI_AUTOWORK_PLANNING_QUIET'] = '0'
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Committed uncommitted changes in', result.stdout)
        self.assertIn('docs(tasks): owner planning (pi-autowork)', self.git(self.repo, 'log', '--format=%s'))
        self.assertIn('add the export task', (self.repo / 'BLOCKERS.md').read_text())
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')

    def test_other_quiet_uncommitted_work_is_committed_too_but_not_possible_secrets(self):
        """Owner direction (2026-10-16): auto work commits and merges all work, not only planning."""
        self.owner_note()
        (self.repo / 'scratch.py').write_text('print(1)\n')  # someone's quiet work
        (self.repo / '.env').write_text('TOKEN=x\n')
        self.env['PI_AUTOWORK_PLANNING_QUIET'] = '0'
        result = self.run_runner('--until-empty')
        self.assertTrue(self.done('A', 'B', 'C'), result.stdout)
        self.assertIn('chore: uncommitted work in the main checkout (pi-autowork)',
                      self.git(self.repo, 'log', '--format=%s'))
        self.assertIn('left untracked as possible secrets: .env', result.stdout)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '?? .env')

    def test_planning_held_open_for_writing_is_left_alone(self):
        self.owner_note()
        self.env['PI_AUTOWORK_PLANNING_QUIET'] = '0'
        holder = subprocess.Popen([sys.executable, '-c', 'import sys, time; f = open(sys.argv[1], "a"); time.sleep(60)',
                                   str(self.repo / 'BLOCKERS.md')])
        self.addCleanup(lambda: (holder.kill(), holder.wait()))
        time.sleep(0.5)
        result = self.run_runner('--until-empty')
        self.assertTrue(self.done('A', 'B', 'C'), result.stdout)
        self.assertNotIn('owner planning', self.git(self.repo, 'log', '--format=%s'))
        self.assertIn('?? BLOCKERS.md', self.git(self.repo, 'status', '--porcelain'))

    def test_questions_for_the_owner_land_in_blockers_md_without_a_model(self):
        """TOOLSET-120-fc (2): questions live in the repository; writing them costs no tokens."""
        (self.repo / 'BLOCKERS.md').write_text('# BLOCKERS\n\n## Active\n\n### BLK-1 — Owner entry\n')
        self.git(self.repo, 'add', 'BLOCKERS.md')
        self.git(self.repo, 'commit', '-qm', 'owner blockers')
        self.plan({'worker:A': ['blocked']})
        result = self.run_runner('--until-empty')
        self.assertIn('Questions for the owner in BLOCKERS.md: 1 open (easiest: A, input)', result.stdout)
        text = (self.repo / 'BLOCKERS.md').read_text()
        self.assertIn('### Q-A — USER_INPUT — effort input — unblocks 1', text)
        self.assertIn('- Needs: worker reported a blocker: needs a device', text)
        self.assertIn('### BLK-1 — Owner entry', text)  # the owner's own entries stay
        runs = len(self.runs())
        again = self.run_runner('--until-empty')  # nothing changed: no rewrite, no commit, no model call
        self.assertNotIn('Questions for the owner', again.stdout)
        self.assertEqual(len(self.runs()), runs)
        self.assertEqual(self.git(self.repo, 'log', '--format=%s').count('questions for the owner'), 1)

    def test_a_continuous_runner_waiting_on_the_owner_merges_its_questions_into_main(self):
        """Questions reached main only when the queue emptied, which a runner waiting on the
        owner never sees: india's stayed on its session branch for hours."""
        self.plan({'worker:A': ['blocked', 'blocked']})
        (self.repo / 'TODO.md').write_text(todo([('A', None), ('B', 'A'), ('C', 'A')]))
        self.git(self.repo, 'commit', '-qam', 'everything waits on A')
        runner = self.start_runner('--interval', '1')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        deadline = time.monotonic() + 90
        blockers = self.repo / 'BLOCKERS.md'
        while '### Q-A — ' not in (blockers.read_text() if blockers.exists() else ''):
            self.assertIsNone(runner.poll())
            self.assertLess(time.monotonic(), deadline, 'questions never reached main')
            time.sleep(0.5)
        self.assertIn('questions for the owner', self.git(self.repo, 'log', '-1', '--format=%s', 'main'))
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        time.sleep(3)  # a failed or done merge is not retried every cycle
        runner.send_signal(signal.SIGINT)
        out, err = runner.communicate(timeout=120)
        self.assertEqual(runner.returncode, 130, out + err)
        self.assertEqual(out.count('Merged pi-autowork/'), 1, out)

    def test_questions_land_on_main_while_other_workers_still_run(self):
        """TOOLSET-188-75: a session landed only when a task closed or the queue emptied; with
        every task running, waiting or held, its questions and repairs stayed off main for hours."""
        self.plan({'worker:A': ['blocked', 'blocked'], 'worker:B': ['slow']})
        bare = self.origin()
        runner = self.start_runner('--interval', '1')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        deadline = time.monotonic() + 90
        blockers = self.repo / 'BLOCKERS.md'
        while '### Q-A — ' not in (blockers.read_text() if blockers.exists() else ''):
            self.assertIsNone(runner.poll(), log())
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        self.assertFalse(self.done('B'), 'B finished first; the landing did not happen beside it')
        upstream = subprocess.run(['git', '--git-dir', str(bare), 'show', 'main:BLOCKERS.md'],
                                  capture_output=True, text=True).stdout
        while '### Q-A — ' not in upstream:  # and the push follows the landing
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
            upstream = subprocess.run(['git', '--git-dir', str(bare), 'show', 'main:BLOCKERS.md'],
                                      capture_output=True, text=True).stdout
        while not self.done('B'):
            self.assertIsNone(runner.poll(), log())
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=120)

    def test_bold_task_ids_close_into_a_linked_archive(self):
        """sierra: `- [ ] **T-1 — …**` never closed, and a linked docs/TODO-archive.md stayed dirty."""
        text = (self.repo / 'TODO.md').read_text().replace('# TODO\n', '# TODO\n\n[History](docs/TODO-archive.md)\n')
        for t in 'ABC':
            text = text.replace(f'- [ ] {t} — Task {t}', f'- [ ] **{t} — Task {t}**')
        (self.repo / 'TODO.md').write_text(text)
        (self.repo / 'docs').mkdir()
        (self.repo / 'docs/TODO-archive.md').write_text('# History\n')
        self.git(self.repo, 'add', '-A')
        self.git(self.repo, 'commit', '-qm', 'bold IDs, linked archive')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertIn('- [x] **A — Task A**', (self.repo / 'docs/TODO-archive.md').read_text())
        self.assertNotIn('Task A', (self.repo / 'TODO.md').read_text())
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')

    def test_tasks_without_touches_get_proposed_ones_and_run_in_parallel(self):
        """sierra: no task declared Touches, so everything ran one at a time."""
        text = (self.repo / 'TODO.md').read_text()
        for t in 'ABC':
            text = text.replace(f'  Touches: {t}.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'no Touches anywhere')
        self.plan({'worker:A': ['barrier'], 'worker:B': ['barrier']})  # both must run at once
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: can run beside others; Touches: A.txt', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertIn('  Touches: A.txt', (self.repo / 'TODO.md').read_text()
                      + ((self.repo / 'TODO.archive.md').read_text() if (self.repo / 'TODO.archive.md').exists() else ''))
        self.assertTrue(all(r['tools'] == 'read,grep,find,ls' for r in self.runs('touches')))
        # Device- or screenshot-verified work still has a bounded edit scope (TASK-013 answered NONE).
        prompt = self.runs('touches')[0]['message']
        self.assertIn('not how the result is checked', prompt)
        self.assertIn('NONE - reason', prompt)

    def test_an_unboundable_task_runs_alone_and_is_not_asked_again(self):
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        self.plan({'touches:A': ['none']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: runs alone (no Touches proposed: NONE - only a live device operation)', result.stdout)
        self.assertEqual(len(self.runs('touches')), 1)
        self.assertNotIn('Touches: NONE', (self.repo / 'TODO.md').read_text())
        caches = list(self.state.glob('*/touches-*.json'))
        self.assertEqual(len(caches), 1)
        self.assertIn('A', json.loads(caches[0].read_text()))

    def test_answers_from_an_older_prompt_do_not_hold_a_task(self):
        text = (self.repo / 'TODO.md').read_text().replace('  Touches: A.txt\n', '')
        (self.repo / 'TODO.md').write_text(text)
        self.git(self.repo, 'commit', '-qam', 'A has no Touches')
        common = self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        state = self.state / hashlib.sha256(common.encode()).hexdigest()[:16]
        state.mkdir(parents=True)
        (state / 'touches.json').write_text(json.dumps({'A': int(time.time()) + 86400}))
        (state / 'touches-000000000000.json').write_text(json.dumps({'A': int(time.time()) + 86400}))
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: can run beside others; Touches: A.txt', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_budget_persists_across_restarts(self):
        self.env['PI_AUTOWORK_MAX_COST'] = '0.05'
        self.run_runner('--status')  # materializes code only, not execution state
        self.run_runner('--once')
        key_dir, = (p.parent for p in self.state.glob('*/runs.jsonl'))
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

    def test_a_task_commit_that_conflicts_with_the_session_is_merged_not_reimplemented(self):
        """TOOLSET-157-cd (2): a conflict hold reran the whole task from scratch."""
        self.plan({'worker:A': ['move_session'], 'merge:A': ['resolve']})
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('A: its commit conflicts with the session in: A.txt; asking Pi to resolve the merge '
                      'in its worktree', result.stdout)
        self.assertIn('A: merged the session into its commit; verifying again', result.stdout)
        self.assertEqual(len([r for r in self.runs('worker') if r['task'] == 'A']), 1)  # no fresh attempt
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_waiting_runner_commits_the_owners_quiet_planning_without_a_merge(self):
        """TOOLSET-157-cd (5): answers to held tasks stayed uncommitted while nothing merged."""
        text = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(text.replace('Dependencies: None.', 'Dependencies: Z.'))
        self.git(self.repo, 'commit', '-qam', 'everything waits on a missing Z')
        self.env['PI_AUTOWORK_PLANNING_QUIET'] = '600'
        runner = self.start_runner('--interval', '1')
        deadline = time.monotonic() + 30
        while 'No task can start now' not in (self.state.glob('*/runner.log').__next__().read_text()
                                               if list(self.state.glob('*/runner.log')) else ''):
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.2)
        (self.repo / 'TODO.md').write_text(text)  # the owner's answer, left uncommitted
        os.utime(self.repo / 'TODO.md', (time.time() - 700,) * 2)  # quiet for longer than 600 s
        # Beside other work still being edited: one repository's plan never reached its runner,
        # because those files kept the planning-only commit from running at all.
        (self.repo / 'notes.md').write_text('work in progress\n')
        deadline = time.monotonic() + 60
        while not self.done('A'):
            self.assertLess(time.monotonic(), deadline, 'runner never saw the uncommitted answer')
            time.sleep(0.5)
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=60)
        planning = self.git(self.repo, 'log', '--format=%H', '--grep', '^docs(tasks): owner planning (pi-autowork)')
        self.assertTrue(planning, self.git(self.repo, 'log', '--format=%s'))
        self.assertEqual(self.git(self.repo, 'show', '--format=', '--name-only', planning.split()[-1]), 'TODO.md')
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--', 'notes.md'), '?? notes.md')

    def origin(self):
        """A bare upstream for main, as a real repository has."""
        bare = self.root / 'origin.git'
        subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True)
        self.git(self.repo, 'remote', 'add', 'origin', str(bare))
        self.git(self.repo, 'push', '-q', '-u', 'origin', 'main')
        return bare

    def test_merged_work_is_pushed_to_main_upstream(self):
        bare = self.origin()
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertIn('Pushed main to origin/main', result.stdout)
        self.assertEqual(self.git(self.repo, 'rev-parse', 'main'), self.git(bare, 'rev-parse', 'main'))
        self.assertFalse(any(b.endswith('pushed') for b in self.git(bare, 'branch').split()))  # workers never push

    def test_a_backlog_left_unpushed_is_published_at_start(self):
        """Owner direction (2026-10-17): push to upstream after every task; one runner had
        merged sixteen times without pushing."""
        bare = self.origin()
        (self.repo / 'local.txt').write_text('merged earlier, never pushed\n')
        self.git(self.repo, 'add', 'local.txt')
        self.git(self.repo, 'commit', '-qm', 'an earlier landing')
        self.env['PI_AUTOWORK_PUSH'] = '1'
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git(bare, 'rev-parse', 'main'), self.git(self.repo, 'rev-parse', 'main'))
        self.assertTrue(self.git(bare, 'log', '--format=%s', 'main').count('an earlier landing'))

    def test_upstream_commits_are_pulled_into_main_after_a_task_before_its_push(self):
        bare = self.origin()
        other = self.root / 'other'
        subprocess.run(['git', 'clone', '-q', str(bare), str(other)], check=True)
        (other / 'X.txt').write_text('from elsewhere\n')
        self.git(other, 'add', 'X.txt')
        self.git(other, 'commit', '-qm', 'someone else')
        self.git(other, 'push', '-q', 'origin', 'main')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertRegex(result.stdout, r'Pulled 1 commit\(s\) from origin/main into main|origin/main had moved')
        self.assertEqual((self.repo / 'X.txt').read_text(), 'from elsewhere\n')
        self.assertEqual(self.git(self.repo, 'rev-parse', 'main'), self.git(bare, 'rev-parse', 'main'))
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_rejected_push_merges_the_upstream_and_pushes_again(self):
        bare = self.origin()
        other = self.root / 'other'
        subprocess.run(['git', 'clone', '-q', str(bare), str(other)], check=True)
        (other / 'X.txt').write_text('from elsewhere\n')
        self.git(other, 'add', 'X.txt')
        self.git(other, 'commit', '-qm', 'someone else')
        self.git(other, 'push', '-q', 'origin', 'main')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        # Pulled before the push at start (owner direction 2026-10-17), or merged after a rejected push.
        self.assertRegex(result.stdout, r'origin/main had moved; merged it and pushing again|Pulled 1 commit')
        self.assertEqual(self.git(self.repo, 'rev-parse', 'main'), self.git(bare, 'rev-parse', 'main'))
        self.assertEqual((self.repo / 'X.txt').read_text(), 'from elsewhere\n')
        self.assertTrue(self.done('A', 'B', 'C'))

    def test_a_conflicting_owner_plan_is_landed_after_each_task(self):
        """india: the owner's plan commit conflicted with the session's own TODO.md commits, and
        the runner kept planning from its stale copy without saying so."""
        (self.repo / 'TODO.md').write_text(todo([('A', None), ('B', None)]))
        self.git(self.repo, 'commit', '-qam', 'A and B')
        self.plan({'worker:A': ['slow'], 'worker:B': ['blocked'] * 5})
        runner = self.start_runner('--interval', '300')
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        log = lambda: ''.join(p.read_text() for p in self.state.glob('*/runner.log'))
        self.wait_for(self.root / 'busy-A')
        session = json.loads(next(self.state.glob('*/session.json')).read_text())
        integ = Path(session['path'])
        with open(integ / 'TODO.md', 'a') as out:
            out.write('\nSession note.\n')
        self.git(integ, 'commit', '-qam', 'session bookkeeping')
        with open(self.repo / 'TODO.md', 'a') as out:
            out.write('\nOwner decision: A needs no device.\n')
        self.git(self.repo, 'commit', '-qam', 'owner plan')
        deadline = time.monotonic() + 60
        while log().count('Merged ') < 1:
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.2)
        self.assertTrue(self.done('A'))
        self.assertIn('session bookkeeping', self.git(self.repo, 'log', '--format=%s', 'main'))
        # A second conflict in the same runner process is resolved too, not left as a stale session.
        (self.root / 'busy-A').unlink()
        self.plan({'worker:C': ['slow'], 'worker:B': ['blocked'] * 5})
        entry = todo([('C', None)]).split('## Next\n\n')[1]
        current = (self.repo / 'TODO.md').read_text()
        (self.repo / 'TODO.md').write_text(current.replace('## Next\n\n', '## Next\n\n' + entry, 1))
        self.git(self.repo, 'commit', '-qam', 'add C')
        deadline = time.monotonic() + 60
        while not (self.root / 'busy-C').exists():
            self.assertLess(time.monotonic(), deadline, log())
            time.sleep(0.2)
        session = json.loads(next(self.state.glob('*/session.json')).read_text())
        integ = Path(session['path'])
        with open(integ / 'TODO.md', 'a') as out:
            out.write('\nSecond session note.\n')
        self.git(integ, 'commit', '-qam', 'second bookkeeping')
        with open(self.repo / 'TODO.md', 'a') as out:
            out.write('\nSecond owner decision.\n')
        self.git(self.repo, 'commit', '-qam', 'second owner plan')
        deadline = time.monotonic() + 60
        while 'second bookkeeping' not in self.git(self.repo, 'log', '--format=%s', 'main'):
            self.assertLess(time.monotonic(), deadline, log())
            self.assertIsNone(runner.poll(), log())
            time.sleep(0.2)
        self.assertEqual(log().count('asking Pi to resolve the merge'), 2, log())
        self.assertNotIn('Merge pending', log())
        runner.send_signal(signal.SIGINT)
        runner.communicate(timeout=120)
        self.assertIn('Not pushed: main has no upstream branch', log())

    def test_an_unresolved_conflict_keeps_the_session(self):
        self.plan({'worker:A': ['move_main'], 'merge': ['no_progress']})
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
        self.assertIn('Merge pending', result.stdout)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'from main\n')
        self.assertEqual(len([b for b in self.branches() if b.startswith('pi-autowork/')]), 1)
        status = self.run_runner('--status')
        self.assertIn('not yet merged into main', status.stdout)

    def stale_registration(self, name):
        """A worktree someone else registered whose directory has since gone missing."""
        path = self.root / name
        self.git(self.repo, 'worktree', 'add', '-q', '-b', name, str(path))
        shutil.rmtree(path)
        return path

    def registered(self, path):
        return f'worktree {path}' in self.git(self.repo, 'worktree', 'list', '--porcelain').splitlines()

    def test_other_stale_worktree_registrations_survive_a_session(self):
        other = self.stale_registration('someone-else')
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertTrue(self.registered(other))

    def test_a_missing_session_worktree_is_restored_without_pruning_others(self):
        self.plan({'worker:A': ['move_main'], 'merge': ['no_progress']})
        self.assertEqual(self.run_runner('--once').returncode, 4)
        session = json.loads(next(self.state.glob('*/session.json')).read_text())
        other = self.stale_registration('someone-else')
        shutil.rmtree(session['path'])
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(f'Merged {session["branch"]}', result.stdout)
        self.assertFalse(self.registered(session['path']))
        self.assertTrue(self.registered(other))

    def test_a_session_at_an_old_location_is_recreated_or_moved_without_losing_work(self):
        for contents in ('clean', 'committed', 'ignored'):
            with self.subTest(contents=contents):
                self.repo = self.make_repo(self.root / f'project-{contents}', [('A', None)])
                self.env['FAKE_MAIN_REPO'] = str(self.repo)
                # The runner's state key is the common Git directory's digest.
                common = self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
                folder = self.state / hashlib.sha256(common.encode()).hexdigest()[:16]
                folder.mkdir(parents=True, exist_ok=True)
                branch = f'pi-autowork/old-{contents}'
                old = self.root / f'old-{contents}'
                (self.repo / '.gitignore').write_text('private-note.txt\n')
                self.git(self.repo, 'add', '.gitignore')
                self.git(self.repo, 'commit', '-qm', 'ignored session data')
                self.git(self.repo, 'worktree', 'add', '-q', '-b', branch, str(old), 'main')
                saved = 'private-note.txt' if contents == 'ignored' else 'saved.txt'
                if contents != 'clean':
                    (old / saved).write_text('keep this work\n')
                if contents == 'committed':
                    self.git(old, 'add', saved)
                    self.git(old, 'commit', '-qm', 'session work')
                (folder / 'session.json').write_text(json.dumps({'branch': branch, 'path': str(old), 'base': 'main'}))
                # Hold the final merge so the relocated session remains inspectable.
                (self.repo / 'A.txt').write_text('owner edit\n')
                result = self.run_runner('--once')
                self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
                session = json.loads((folder / 'session.json').read_text())
                self.assertEqual(Path(session['path']).parent, self.repo / '.worktrees')
                self.assertFalse(old.exists())
                if contents != 'clean':
                    self.assertEqual(session['branch'], branch)
                    self.assertEqual((Path(session['path']) / saved).read_text(), 'keep this work\n')
                else:
                    self.assertNotEqual(session['branch'], branch)
                self.git(self.repo, 'checkout', '--', 'A.txt')
                self.assertEqual(self.run_runner('--until-empty').returncode, 0)
                if contents == 'ignored':
                    self.assertEqual((Path(session['path']) / saved).read_text(), 'keep this work\n')

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

    def test_changes_left_uncommitted_in_the_session_are_committed_and_merged(self):
        """bravo: a failed close left TODO.md edits in the session worktree; every merge refused them."""
        (self.repo / 'A.txt').write_text('my note\n')  # keeps the first run's session from merging
        self.assertEqual(self.run_runner('--once').returncode, 4)
        self.git(self.repo, 'checkout', '--', 'A.txt')
        session = Path(json.loads(next(self.state.glob('*/session.json')).read_text())['path'])
        (session / 'left-behind.txt').write_text('a write no close commits\n')  # no task close sweeps it in
        result = self.run_runner('--until-empty')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('Committed uncommitted changes left in the session worktree', result.stdout)
        self.assertTrue(self.done('A', 'B', 'C'))
        self.assertEqual((self.repo / 'left-behind.txt').read_text(), 'a write no close commits\n')

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
            self.assertIn('Engine:     Parallel Autowork, up to 8 worker(s)', result.stdout)
            self.assertIn('Runner:     not running', result.stdout)
        self.assertEqual(self.git(self.repo, 'status', '--porcelain', '--untracked-files=all'), before)
        self.assertEqual({p.name for p in self.state.iterdir()}, {'releases'})  # only immutable code cache
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
        shutil.copytree(ROOT / 'pi-autowork', package / 'pi-autowork', ignore=shutil.ignore_patterns('__pycache__'))
        self.git(package, 'init', '-q')
        self.git(package, 'add', '-A')
        self.git(package, 'commit', '-qm', 'installed package')
        self.env['FAKE_PI_TOOLSET'] = str(package)
        selected = self.state / 'releases' / self.git(package, 'rev-parse', 'HEAD')
        result = self.run_runner('--dry-run')
        self.assertIn(f'Toolset:    {selected} at ', result.stdout)
        self.env.pop('FAKE_PI_TOOLSET')
        result = self.run_runner('--dry-run')
        self.assertIn('(not a Pi package)', result.stdout)
        # A copied launcher must reach the canonical bootstrap before importing
        # an older package whose release helper does not support `launch`.
        old = self.root / 'hermes-toolset/pi-autowork/pi_autowork'
        old.mkdir(parents=True)
        (old / 'cli.py').touch()
        (old / 'release.py').write_text('raise SystemExit(2)\n')
        self.env['FAKE_PI_LIST'] = (f'git:github.com/TrebuchetDynamics/hermes-toolset\n  {old.parents[1]}\n'
                                    f'git:github.com/TrebuchetDynamics/autowork\n  {package}\n')
        copied = self.repo / 'pi-autowork.sh'
        shutil.copy(RUNNER, copied)
        result = self.run_runner('--dry-run', script=copied)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn(f'Toolset:    {selected} at ', result.stdout)

    def installed_package(self):
        """A disposable autowork Pi package whose local origin holds one newer,
        compatible release, so the update check passes and `pi update` applies."""
        package = self.root / 'pi-package'
        for part in ('skills', 'adapters', 'scripts', 'pi-autowork'):
            shutil.copytree(ROOT / part, package / part, ignore=shutil.ignore_patterns('__pycache__'))
        (package / '.gitignore').write_text('.updated\n')
        self.git(package, 'init', '-q', '-b', 'main')
        self.git(package, 'add', '-A')
        self.git(package, 'commit', '-qm', 'package')
        self.origin = self.root / 'origin.git'
        self.git(self.root, 'clone', '-q', '--bare', str(package), str(self.origin))
        self.git(package, 'remote', 'add', 'origin', str(self.origin))
        self.publish(lambda tree: (tree / 'RELEASE').write_text('2\n'), 'release 2')
        self.env.update(FAKE_PI_TOOLSET=str(package), PI_AUTOWORK_UPDATE_INTERVAL='1')
        return package

    def publish(self, change, message):
        """Push a new release to the package's origin, as upstream does."""
        tree = self.root / ('release-' + str(len(list(self.root.glob('release-*')))))
        self.git(self.root, 'clone', '-q', str(self.origin), str(tree))
        change(tree)
        self.git(tree, 'add', '-A')
        self.git(tree, 'commit', '-qm', message)
        self.git(tree, 'push', '-q', 'origin', 'HEAD:main')

    def run_until(self, script, text, timeout=60):
        runner = subprocess.Popen(['bash', str(script), '--interval', '1'], cwd=self.repo, env=self.env,
                                  stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        self.addCleanup(lambda: runner.poll() is None and runner.kill())
        deadline = time.monotonic() + timeout
        while not any(text in p.read_text() for p in self.state.glob('*/runner.log')):
            if time.monotonic() > deadline or runner.poll() is not None:
                runner.kill()
                self.fail(f'{text!r} never logged: {runner.communicate()[0][-2000:]}')
            time.sleep(0.2)
        return runner

    def test_an_idle_runner_updates_its_toolset_and_restarts_on_the_new_code(self):
        package = self.installed_package()
        before = self.git(package, 'rev-parse', '--short', 'HEAD')
        runner = self.run_until(package / 'scripts/pi-autowork.sh', 'restarting on it')
        deadline = time.monotonic() + 30
        while next(self.state.glob('*/runner.log')).read_text().count('Started (PID') < 2:
            self.assertLess(time.monotonic(), deadline, 'the runner did not start again')
            time.sleep(0.2)
        while not self.done('A', 'B', 'C'):  # the restarted runner carries on with the queue
            self.assertLess(time.monotonic(), deadline + 60, 'the restarted runner did not finish the queue')
            time.sleep(0.2)
        runner.send_signal(signal.SIGINT)
        out, _ = runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130, out)
        after = self.git(package, 'rev-parse', '--short', 'HEAD')
        self.assertIn(f'Toolset updated to {after}; restarting on it', out)
        self.assertNotEqual(before, after)
        starts = re.findall(r'^\[(\d{2}:\d{2})\] Started \(PID (\d+)\)\. Stop with Ctrl\+C\.$',
                            out, re.MULTILINE)
        self.assertGreaterEqual(len(starts), 2, out)
        self.assertEqual({pid for _, pid in starts}, {str(runner.pid)}, out)  # exec keeps the PID
        updates = [json.loads(l) for l in self.log.read_text().splitlines() if '"update"' in l]
        self.assertEqual(updates[0]['update'], [str(self.origin)])

    def test_a_release_that_cannot_read_current_state_is_never_installed(self):
        package = self.installed_package()
        def schema_2_only(tree):
            state = tree / 'skills/autowork/scripts/parallel_state.py'
            state.write_text(state.read_text().replace('STATE_SCHEMA_READS = (1,)', 'STATE_SCHEMA_READS = (2,)'))
        self.publish(schema_2_only, 'reads only schema 2')
        runner = self.run_until(package / 'scripts/pi-autowork.sh', 'Toolset update deferred')
        time.sleep(3)
        runner.send_signal(signal.SIGINT)
        out, _ = runner.communicate(timeout=60)
        self.assertIn('Toolset update deferred: release', out)
        self.assertIn('cannot read this state (schema 1; it reads [2])', out)
        self.assertEqual(out.count('Toolset update deferred'), 1, out)  # said once, not every interval
        self.assertFalse([l for l in self.log.read_text().splitlines() if '"update"' in l])  # pi update never ran

    def test_a_broken_toolset_update_keeps_the_running_code(self):
        package = self.installed_package()
        self.env['FAKE_PI_UPDATE'] = 'broken'
        runner = self.run_until(package / 'scripts/pi-autowork.sh', 'does not parse')
        time.sleep(3)  # later idle cycles neither restart nor repeat the warning
        runner.send_signal(signal.SIGINT)
        out, _ = runner.communicate(timeout=60)
        self.assertEqual(runner.returncode, 130, out)
        self.assertNotIn('restarting on it', out)
        self.assertEqual(out.count('does not parse'), 1, out)

    def test_setup_errors(self):
        bare = self.root / 'bare'
        bare.mkdir()
        self.git(bare, 'init', '-q')
        self.assertIn('No TODO.md', self.run_runner('--once', cwd=bare).stderr)
        self.assertIn('Not inside a Git repository', self.run_runner('--once', cwd=self.root).stderr)
        self.env['PI_AUTOWORK_PRIMARY'] = 'openai-codex/gpt-nope'
        self.assertIn('not in Pi', self.run_runner('--once').stderr)
        self.env.pop('PI_AUTOWORK_PRIMARY')
        self.assertIn('--workers must be 1 to 8', self.run_runner('--workers', '9').stderr)
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
             'skills': ['autowork:autowork']},
            {'id': 'b2', 'name': 'Paused', 'workdir': str(self.repo), 'paused_at': 'x', 'skills': ['autowork']}]}))
        result = self.run_runner('--once')
        self.assertEqual(result.returncode, 4)
        self.assertIn('work: Work Autowork', result.stderr)
        self.assertNotIn('Paused', result.stderr)
        self.assertEqual(self.run_runner('--once', '--allow-hermes').returncode, 0)

    def test_hermes_profile_labels_ignore_profiles_in_installation_ancestors(self):
        home = self.root / 'profiles/outer/installation'
        self.env['PI_AUTOWORK_HERMES_HOME'] = str(home)
        for profile, relative in [('default', 'cron'), ('work', 'profiles/work/cron')]:
            with self.subTest(profile=profile):
                jobs = home / relative
                jobs.mkdir(parents=True)
                store = jobs / 'jobs.json'
                store.write_text(json.dumps({'jobs': [
                    {'id': 'active', 'name': 'Active Autowork', 'workdir': str(self.repo),
                     'enabled': True, 'skills': ['autowork:autowork']},
                    {'id': 'paused', 'name': 'Paused Autowork', 'workdir': str(self.repo),
                     'enabled': True, 'state': 'paused', 'skills': ['autowork:autowork']}]}))
                before = store.read_bytes()
                result = self.run_runner('--once')
                self.assertEqual(result.returncode, 4, result.stdout + result.stderr)
                self.assertIn(f'{profile}: Active Autowork', result.stderr)
                self.assertNotIn('outer: Active Autowork', result.stderr)
                self.assertNotIn('Paused Autowork', result.stderr)
                self.assertEqual(store.read_bytes(), before)
                store.unlink()


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

    def test_the_service_path_leaves_out_uvs_temporary_environments(self):
        """Installed from the TUI (`uv run`), a service kept uv's deleted build environment first."""
        cache = self.root / 'uv-cache'
        build = cache / 'builds-v0' / '.tmpabc' / 'bin'
        build.mkdir(parents=True)
        missing = self.root / '.tmp-gone' / 'bin'
        temporary = self.root / '.tmp-other-tool' / 'bin'
        temporary.mkdir(parents=True)
        gone = self.root / 'gone' / 'bin'
        archive = cache / 'archive-v0' / 'abc' / 'bin'
        archive.mkdir(parents=True)
        xdg_cache = self.root / 'xdg-cache'
        default_build = xdg_cache / 'uv' / 'builds-v0' / 'abc' / 'bin'
        default_build.mkdir(parents=True)
        self.env.update(UV_CACHE_DIR=str(cache), XDG_CACHE_HOME=str(xdg_cache),
                        PATH=f"{missing}:{build}:{temporary}:{gone}:{archive}:{default_build}:{self.bin}:{self.env['PATH']}")
        result = self.run_runner('--install-service')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        path = next(l for l in (self.envs / 'project.env').read_text().splitlines() if l.startswith('PATH='))
        for dropped in (missing, build, temporary, gone, archive, default_build):
            self.assertNotIn(str(dropped), path)
            self.assertIn(str(dropped), result.stdout)
        self.assertEqual(path.split('=', 1)[1].split(os.pathsep).count(str(self.bin)), 1)

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
