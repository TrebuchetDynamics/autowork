"""Offline parallel dispatch checks with a deterministic fake worker CLI."""
import contextlib
import errno
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from offline_fixtures import fixture_runtime_root
import parallel_dispatch as dispatch
import parallel_state as state
import store_fixture
import task_queue
import task_execution as execution

FAKE = SCRIPTS / 'fixtures' / 'fake_worker.py'


def task(tid, touches, depends='None'):
    lines = [f'- [ ] {tid} — Task {tid}', f'- Scope: change {touches}.', '- Acceptance: changed.',
             '- Checks: inspect.', f'- Dependencies: {depends}.']
    if touches:
        lines.append(f'- Touches: {touches}')
    return '\n'.join(lines) + '\n'


# A task that must run alone. A missing Touches no longer makes one (TOOLSET-161-17).
ALONE = task('S', 's.txt') + '- Resources: exclusive\n'


class DispatchTests(unittest.TestCase):
    def setUp(self):
        # Bootstrap independently of the invoking session's runtime dir and the worker's
        # inherited, potentially long TMPDIR.
        self.runtime = tempfile.TemporaryDirectory(prefix='awt-', dir=fixture_runtime_root())
        self.addCleanup(self.runtime.cleanup)
        runtime_env = patch.dict(os.environ, XDG_RUNTIME_DIR=self.runtime.name,
                                 PI_AUTOWORK_WORKER_ROOT=self.runtime.name)
        runtime_env.start()
        self.addCleanup(runtime_env.stop)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'), task('C', 'c.txt', 'A'),
                        task('E', 'e.txt'), task('D', 'a.txt'))
        self.git('add', '.')
        self.commit_if_changed('base')
        self.owner = os.getppid()
        self.common = state.common_dir(self.repo)
        self.spec = self.root / 'spec.json'
        self.log = self.root / 'workers.jsonl'
        self.log.touch()
        self.set_spec({})
        for patcher in (patch.dict(os.environ, FAKE_WORKER_SPEC=str(self.spec), FAKE_WORKER_LOG=str(self.log),
                                    PI_AUTOWORK_MIN_FREE_DISK_GB='0'),
                        patch.object(dispatch, 'available_memory_mb', return_value=10 ** 6),
                        patch.object(os, 'getloadavg', return_value=(0.0, 0.0, 0.0))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.stop_workers)

    def stop_workers(self):
        for slot in state.slots(self.common) if (self.common / 'slots').exists() else ():
            if state.worker_live(slot):
                dispatch.stop(slot['worker'], slot['worktree'])

    def git(self, *args, repo=None):
        return execution.git(repo or self.repo, *args)

    def write_todo(self, *bodies):
        """The queue as TODO-form text, converted to the tasks/ store and committed."""
        self.todo = '# Work queue\n\n## Next\n\n' + '\n'.join(bodies)
        self.git('add', '-A')
        store_fixture.write_todo(self.repo, self.todo)

    def commit_if_changed(self, message, repo=None):
        """A test's own commit: everything staged, and nothing when write_todo already committed it."""
        repo = repo or self.repo
        self.git('add', '-A', repo=repo)
        if subprocess.run(['git', '-C', str(repo), 'diff', '--cached', '--quiet']).returncode:
            self.git('commit', '-qm', message, repo=repo)

    def set_spec(self, spec):
        self.spec.write_text(json.dumps(spec))

    def run_cli(self, *args, worker=True):
        argv = [str(self.repo), '--owner-pid', str(self.owner), *args]
        if worker:
            argv += ['--worker-command', json.dumps([sys.executable, str(FAKE), '{prompt_file}', '{worktree}'])]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = execution.main(argv)
        return code, json.loads(out.getvalue())

    def apply(self, *extra):
        return self.run_cli('--apply', '--parallel', *extra)

    def wait(self, timeout=20, *extra):
        return self.run_cli('--parallel', '--wait', '--timeout', str(timeout), *extra)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def wait_until_idle(self):
        for _ in range(40):
            _, result = self.wait(20)
            if result['active_workers'] == 0:
                return result
        self.fail('workers did not finish')

    def test_under_a_gating_runner_the_worker_leaves_the_full_check_to_it(self):
        """TOOLSET-227-a8: workers ran the full suite two or three times before the runner's gate."""
        task = execution.select_all(self.repo, None, None)[0]
        plain = dispatch.prompt(task, self.repo, 'b', 'HEAD', self.root / 'r.json')
        self.assertIn('Run the full offline gate once', plain)
        with patch.dict(os.environ, AUTOWORK_RUNNER_FULL_CHECK='python3 scripts/check.py'):
            gated = dispatch.prompt(task, self.repo, 'b', 'HEAD', self.root / 'r.json')
        self.assertNotIn('Run the full offline gate once', gated)
        self.assertIn('No person is attached to this session', plain)  # TOOLSET-282-43
        self.assertIn('Do not run the full check (`python3 scripts/check.py`)', gated)
        self.assertIn('Leave the full check out of the report', gated)
        for text in ('autowork-run', 'more than two minutes', 'focused tests directly',
                     'worker_check_slot_wait_seconds'):
            self.assertIn(text, gated)
        for text in ('unrelated_failures', 'environment_failures', 'rerun each alone once',
                     'git worktree add --detach', 'commit anyway', 'never blockers'):
            self.assertIn(text, gated)

    def test_long_worker_checks_share_a_slot_and_keep_the_command_exit_code(self):
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(self.root / 'checks'),
                        PI_AUTOWORK_WORKER_CHECK_SLOTS='1'):
            checks = self.root / 'checks'
            checks.mkdir(mode=0o700)
            runner_slot = (checks / 'slot-0').open('a')
            self.addCleanup(runner_slot.close)
            fcntl.flock(runner_slot, fcntl.LOCK_EX)  # runner full checks use a separate pool
            workers = []
            for name in ('first', 'second'):
                data = self.common / 'slot-data' / name / 'attempt-1'
                data.mkdir(parents=True)
                prompt = data / 'prompt.md'
                prompt.write_text('fixture')
                code = ('import subprocess,sys; from pathlib import Path; '
                        'rc=subprocess.call(["autowork-run", *sys.argv[2:]]); '
                        'Path(sys.argv[1], "exit").write_text(str(rc))')
                check = ('from pathlib import Path; import sys,time; p=Path(sys.argv[1]); '
                         '(p/"started").touch(); '
                         'exec(\'while not (p/"release").exists(): time.sleep(.01)\'); sys.exit(23)')
                worker = dispatch.launch([sys.executable, '-c', code, str(data), sys.executable,
                                          '-c', check, str(data)], self.repo, data, 1, prompt)
                self.addCleanup(dispatch.stop, worker, str(self.repo))
                workers.append(data)
                target = data / ('started' if name == 'first' else 'worker.log')
                self.await_file(target, 'waiting for a worker check slot' if name == 'second' else None)
            first, second = workers
            self.assertFalse((second / 'started').exists())
            (first / 'release').touch()
            self.await_file(second / 'started')
            self.await_file(first / 'exit')
            self.assertEqual((first / 'exit').read_text(), '23')
            (second / 'release').touch()
            self.await_file(second / 'exit')
            self.assertEqual((second / 'exit').read_text(), '23')
            records = [json.loads(p.read_text()) for p in (second / 'worker-checks').glob('*.json')]
            self.assertEqual(len(records), 1)
            self.assertGreater(records[0]['wait_seconds'], 0)
            self.assertEqual((second / 'worker.log').read_text().count('waiting for a worker check slot'), 1)

    def await_file(self, path, text=None):
        deadline = time.monotonic() + 10
        while time.monotonic() < deadline:
            if path.exists() and (text is None or text in path.read_text()):
                return
            time.sleep(.01)
        self.fail(f'did not observe {text or path}: {path.parent}')

    def test_worker_report_sums_slot_waits_without_replacing_its_checks(self):
        import autowork_run
        directory = self.root / 'worker-checks'
        directory.mkdir()
        for index, seconds in enumerate((1.25, 2.0)):
            (directory / f'{index}.json').write_text(json.dumps(
                {'waiting_since': 1, 'updated': 9, 'wait_seconds': seconds}))
        report = self.root / 'report.json'
        report.write_text(json.dumps({'task': 'A', 'checks': [{'result': 'pass'}]}))
        autowork_run.report_wait(directory, report)
        self.assertEqual(json.loads(report.read_text()),
                         {'task': 'A', 'checks': [{'result': 'pass'}], 'worker_check_slot_wait_seconds': 3.25})

    def test_a_killed_worker_check_holder_releases_its_slot(self):
        import shlex
        env = dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(self.root / 'checks'),
                   PI_AUTOWORK_WORKER_CHECK_SLOTS='1')
        wrapper = [sys.executable, str(SCRIPTS / 'autowork_run.py')]
        for mode in ('killed', 'shell', 'python'):
            with self.subTest(mode=mode):
                env['PI_AUTOWORK_CHECK_ROOT'] = str(self.root / f'checks-{mode}')
                started = self.root / mode
                check = [sys.executable, '-c', 'import os,signal,sys,time; from pathlib import Path; '
                         'signal.signal(signal.SIGTERM, signal.SIG_IGN); '
                         'Path(sys.argv[1]).write_text(str(os.getpid())); time.sleep(30)', str(started)]
                command = (['bash', '-c', shlex.join(check) + '; :'] if mode == 'shell' else
                           [sys.executable, '-c',
                            'import subprocess,sys; subprocess.run(sys.argv[1:], start_new_session=True)', *check]
                           if mode == 'python' else check)
                holder = subprocess.Popen([*wrapper, *command], env=env, start_new_session=True)
                self.addCleanup(holder.wait)
                self.addCleanup(lambda h=holder: h.kill() if h.poll() is None else None)
                self.await_file(started)
                child = int(started.read_text())
                group = os.getpgid(child)
                def kill_survivors(group=group):
                    try:
                        os.killpg(group, 9)
                    except ProcessLookupError:
                        pass
                self.addCleanup(kill_survivors)
                if mode == 'killed':
                    holder.kill()
                    kill_survivors()
                else:
                    holder.terminate()
                self.assertEqual(holder.wait(timeout=5), -9 if mode == 'killed' else 143)
                result = subprocess.run([*wrapper, sys.executable, '-c', 'raise SystemExit(7)'],
                                        env=env, capture_output=True, timeout=5)
                self.assertEqual(result.returncode, 7, result.stderr)
                stat = Path(f'/proc/{child}/stat')
                if stat.exists():
                    self.assertEqual(stat.read_text().rsplit(')', 1)[1].split()[0], 'Z')

    def test_slot_waiting_is_not_a_stuck_command_but_running_still_is(self):
        sys.path.insert(0, str(SCRIPTS.parents[1] / 'pi-autowork'))
        from pi_autowork import pi_runtime
        checks = self.root / 'checks'
        checks.mkdir(mode=0o700)
        records = self.root / 'worker-checks'
        records.mkdir()
        env = dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(checks),
                   PI_AUTOWORK_WORKER_CHECK_SLOTS='1', AUTOWORK_WORKER_CHECK_DIR=str(records))
        started = self.root / 'started'
        command = [sys.executable, str(SCRIPTS / 'autowork_run.py'), sys.executable, '-c',
                   'from pathlib import Path; import sys,time; '
                   'Path(sys.argv[1]).touch(); time.sleep(30)', str(started)]
        import shlex
        # Preserve the shell ancestor: its age includes both queueing and execution.
        shell = shlex.join(command) + '; :'
        with (checks / 'worker-slot-0').open('a') as lease, patch.dict(os.environ, env):
            fcntl.flock(lease, fcntl.LOCK_EX)
            pi = subprocess.Popen([sys.executable, '-c',
                                   'import subprocess,sys; sys.exit(subprocess.call(["bash", "-c", sys.argv[1]]))',
                                   shell], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                                  start_new_session=True)
            self.addCleanup(pi.stdout.close)
            self.addCleanup(pi.wait)
            self.addCleanup(lambda: os.killpg(pi.pid, 9) if pi.poll() is None else None)
            self.assertIn(b'waiting for a worker check slot', pi.stdout.readline())
            time.sleep(.6)
            stopping = {}
            self.assertEqual(pi_runtime.stop_stuck_commands(os.getpid(), .4, stopping), [])
            self.assertIsNone(pi.poll())
            self.assertFalse(started.exists())
            fcntl.flock(lease, fcntl.LOCK_UN)
            self.await_file(started)
            self.assertEqual(pi_runtime.stop_stuck_commands(os.getpid(), .4, stopping), [])
            time.sleep(.6)
            self.assertTrue(pi_runtime.stop_stuck_commands(os.getpid(), .4, stopping))
            pi.wait(timeout=5)

    def test_a_resumed_attempt_relaunches_after_its_release_was_pruned(self):
        """A paused task failed to relaunch: its autowork-run link named a pruned release, so the
        dangling link read as missing and creating it again raised EEXIST."""
        data = self.common / 'slot-data/A/attempt-1'
        (data / 'bin').mkdir(parents=True)
        prompt = data / 'prompt.md'
        prompt.write_text('x')
        current = (SCRIPTS / 'autowork_run.py').resolve()
        for case, old in (('dangling', self.common / 'releases/gone/autowork_run.py'),
                          ('older release', SCRIPTS / 'parallel_state.py')):
            with self.subTest(case=case):
                link = data / 'bin/autowork-run'
                link.unlink(missing_ok=True)
                link.symlink_to(old)
                child = dispatch.launch([sys.executable, '-c', 'import time; time.sleep(30)'], self.repo, data, 1, prompt)
                dispatch.stop(child, str(self.repo))
                self.assertEqual(Path(os.readlink(link)), current)

    def test_a_worker_runs_below_the_coordinators_priority(self):
        """The integration check every finished task waits on ran at the same priority as eight
        workers' test runs; workers and everything they start now yield to it."""
        data = self.common / 'slot-data/A/attempt-1'
        data.mkdir(parents=True)
        prompt = data / 'prompt.md'
        prompt.write_text('x')
        output = data / 'niceness'
        script = 'import os, sys, time; open(sys.argv[1], "w").write(str(os.nice(0))); time.sleep(30)'
        child = dispatch.launch([sys.executable, '-c', script, str(output)], self.repo, data, 1, prompt)
        self.addCleanup(dispatch.stop, child, str(self.repo))
        for _ in range(200):
            if output.exists() and output.read_text():
                break
            time.sleep(.01)
        self.assertEqual(int(output.read_text()), os.nice(0) + dispatch.WORKER_NICE)

    def test_worker_gets_main_evidence_location_and_repair_instructions(self):
        data = self.common / 'slot-data/A/attempt-1'
        data.mkdir(parents=True)
        prompt = data / 'prompt.md'
        prompt.write_text(dispatch.prompt(execution.select_all(self.repo, None, None)[0],
                                         self.repo, 'b', 'HEAD', data / 'report.json'))
        output = data / 'evidence-path'
        script = ('import os, sys, time; from pathlib import Path; '
                  'Path(sys.argv[1]).write_text(os.environ.get("AUTOWORK_MAIN_EVIDENCE", "missing")); '
                  'time.sleep(30)')
        # An invoking runner/worker's repository must not leak into this repository's child.
        with patch.dict(os.environ, AUTOWORK_MAIN_EVIDENCE='/wrong/repository'):
            child = dispatch.launch([sys.executable, '-c', script, str(output)], self.repo, data, 1, prompt)
        self.addCleanup(dispatch.stop, child, str(self.repo))
        for _ in range(200):
            if output.exists():
                break
            time.sleep(.01)
        self.assertEqual(output.read_text(), str(self.common / 'main-evidence'))
        self.assertIn('$AUTOWORK_MAIN_EVIDENCE/<revision>/', prompt.read_text())
        self.assertIn('Never ask a person for these', prompt.read_text())

    def test_independent_tasks_run_together_in_separate_worktrees(self):
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 1.0},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 1.0}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['A', 'B'])
        # Only A and D name a.txt: cold overlap ranks D later, but capacity holds it.
        self.assertIn('all 2 worker slots busy', {w['id']: w['reason'] for w in result['waiting']}['D'])
        self.assertIn('all 2 worker slots busy', {w['id']: w['reason'] for w in result['waiting']}['E'])
        self.assertNotIn('C', [w['id'] for w in result['waiting']])  # C's dependency is unfinished
        _, again = self.apply()
        self.assertEqual((again['outcome'], again['dispatched']), ('WAITING', []))  # no duplicate start
        self.wait_until_idle()
        times = {(e['task'], e['event']): e for e in self.events()}
        self.assertLess(times['A', 'start']['time'], times['B', 'end']['time'])
        self.assertLess(times['B', 'start']['time'], times['A', 'end']['time'])
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 2)
        slots = {s['task_id']: s for s in state.slots(self.common)}
        for tid, slot_no in (('A', '1'), ('B', '2')):
            worktree = self.repo / '.worktrees' / f'autowork-{tid}'
            self.assertEqual(Path(times[tid, 'start']['cwd']), worktree)
            self.assertEqual(slots[tid]['state'], 'reported')
            self.assertEqual(slots[tid]['commit'], self.git('rev-parse', 'HEAD', repo=worktree))
            self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD', repo=worktree), 'autowork/' + tid)
            self.assertEqual(times[tid, 'start']['slot'], slot_no)
            self.assertEqual(int(times[tid, 'start']['port_base']) % 100, 0)  # a leased block, any free one
            self.assertLessEqual(len(times[tid, 'start']['tmpdir'].encode()), 48)
            # TOOLSET-169-1d: one toolchain cache for every task of the repository, kept after they close.
            self.assertEqual(times[tid, 'start']['cache'], str(self.common / 'cache'))
            self.assertFalse(times[tid, 'start']['marker'])
        self.assertNotEqual(times['A', 'start']['port_base'], times['B', 'start']['port_base'])
        self.assertTrue((self.common / 'cache').is_dir())
        prompt = (self.common / 'slot-data/A/attempt-1/prompt.md').read_text()
        for text in ('Task: A', 'Touches: a.txt', 'Never edit tasks/', 'Report file: ', '- Touches: a.txt'):
            self.assertIn(text, prompt)
        self.assertEqual(self.git('status', '--porcelain'), '')  # canonical checkout untouched
        journal = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        moment = {(e['task_id'], e['state']): e['timestamp'] for e in journal if e['event'] == 'slot_changed'}
        self.assertLess(moment['B', 'running'], moment['A', 'reported'])
        self.assertLess(moment['A', 'running'], moment['B', 'reported'])

    def launch_and_read_tmpdir(self, data):
        prompt = data / 'prompt.md'
        prompt.write_text('fixture')
        output = data / 'env.json'
        script = ('import json, os, socket, sys, time; '
                  'from pathlib import Path; '
                  'p = Path(os.environ["TMPDIR"]); '
                  's = socket.socket(socket.AF_UNIX); s.bind(str(p.resolve() / ("s" * 40))); '
                  'Path(sys.argv[1]).write_text(json.dumps([os.environ[k] for k in '
                  '("TMPDIR", "TMP", "TEMP")])); time.sleep(30)')
        worker = dispatch.launch([sys.executable, '-c', script, str(output)], self.repo, data, 1, prompt)
        self.addCleanup(dispatch.stop, worker, str(self.repo))
        for _ in range(200):
            if output.exists():
                break
            time.sleep(.01)
        values = json.loads(output.read_text())
        dispatch.stop(worker, str(self.repo))
        return worker, Path(values[0]), values

    def test_the_fixture_runtime_root_is_short_and_ignores_the_invoking_session(self):
        """$XDG_RUNTIME_DIR is whoever runs the suite's. On the fleet a stale value failed
        setUp outright, and a long one moved the fixture's $TMPDIR to the `/tmp` fallback
        silently: the usual `/run/user/1000` root leaves one byte of slack under the 47-byte
        worker temp path rule."""
        for ambient in ('/run/user/1000/' + 'long-' * 20, '/nonexistent/stale-runtime-dir'):
            with self.subTest(ambient=ambient), patch.dict(os.environ, XDG_RUNTIME_DIR=ambient):
                root = fixture_runtime_root()
                self.assertTrue(Path(root).is_dir(), root)
                made = tempfile.TemporaryDirectory(prefix='awt-', dir=root)
                self.addCleanup(made.cleanup)
                candidate = Path(made.name) / f'aw-{os.getuid()}-{"0" * 8}-1'
                self.assertLessEqual(len(os.fsencode(candidate)), 47, candidate)
        candidate = Path(self.runtime.name) / f'aw-{os.getuid()}-{"0" * 8}-1'
        self.assertLessEqual(len(os.fsencode(candidate)), 47, candidate)

    def test_launch_exports_a_private_socket_safe_directory_on_disk_with_a_tmp_fallback(self):
        """The runtime directory was a 6.3 GB RAM disk shared by every worker; the $TMPDIR is now
        a short directory on disk, socket-safe even when resolved, else the short /tmp fallback."""
        key = hashlib.sha256(str(self.common.parent).encode()).hexdigest()[:8]
        cases = [(self.runtime.name, None), (str(self.root / ('long-' * 20)), None),
                 (self.runtime.name, errno.ENOSPC), (self.runtime.name, errno.EDQUOT)]
        for case, (root, failure) in enumerate(cases):
            with self.subTest(root=root, failure=failure), patch.dict(os.environ, PI_AUTOWORK_WORKER_ROOT=root):
                Path(root).mkdir(parents=True, exist_ok=True)
                data = self.common / 'slot-data' / f'temp-{case}' / 'attempt-1'
                data.mkdir(parents=True)
                if failure is None and root == self.runtime.name:
                    existing = Path(root) / f'aw-{os.getuid()}-{key}-1'
                    existing.mkdir(mode=0o755)
                    existing.chmod(0o755)
                original_mkdir = Path.mkdir
                def disk_full(path, *args, **kwargs):
                    if failure and path.name.startswith('aw-') and path.parent == Path(self.runtime.name):
                        raise OSError(failure, 'fixture: disk full')
                    return original_mkdir(path, *args, **kwargs)
                with patch.object(Path, 'mkdir', disk_full):
                    _, path, values = self.launch_and_read_tmpdir(data)
                self.addCleanup(shutil.rmtree, path, True)
                self.assertEqual(values, [str(path)] * 3)
                self.assertLessEqual(len(os.fsencode(path)), 48)
                self.assertEqual(path.stat().st_mode & 0o777, 0o700)
                self.assertEqual(path.stat().st_uid, os.getuid())
                self.assertTrue(path.name.startswith(f'aw-{os.getuid()}-{key}-'), path)
                on_disk = root == self.runtime.name and failure is None
                self.assertEqual(path.parent, Path(root) if on_disk else Path('/tmp'))

    def test_an_allocation_on_the_runtime_disk_moves_to_disk_with_its_files(self):
        key = hashlib.sha256(str(self.common.parent).encode()).hexdigest()[:8]
        old = Path(self.runtime.name) / 'aw' / key / '3'
        old.mkdir(parents=True)
        (old / 'build').mkdir()
        (old / 'build' / 'kept.txt').write_text('evidence')
        data = self.common / 'slot-data' / 'M' / 'attempt-2'
        data.mkdir(parents=True)
        (data.parent / 'tmp.json').write_text(json.dumps({'path': str(old), 'slot': 3}))
        _, path, _ = self.launch_and_read_tmpdir(data)
        self.addCleanup(shutil.rmtree, path, True)
        self.assertEqual(path, Path(self.runtime.name) / f'aw-{os.getuid()}-{key}-3')
        self.assertEqual((path / 'build' / 'kept.txt').read_text(), 'evidence')
        self.assertFalse(old.exists())
        self.assertEqual(execution.read(data.parent / 'tmp.json'), {'path': str(path), 'slot': 3})

    def test_launch_refuses_foreign_owned_or_symlinked_temporary_directory(self):
        key = hashlib.sha256(str(self.common.parent).encode()).hexdigest()[:8]
        path = Path(self.runtime.name) / f'aw-{os.getuid()}-{key}-1'
        path.mkdir(parents=True)
        path.chmod(0o755)
        data = self.common / 'slot-data' / 'A' / 'attempt-1'
        data.mkdir(parents=True)
        prompt = data / 'prompt.md'
        prompt.write_text('fixture')
        original = os.fstat
        def foreign(fd):
            info = original(fd)
            if os.readlink(f'/proc/self/fd/{fd}') == str(path):
                fields = list(info)
                fields[4] = os.getuid() + 1
                return os.stat_result(fields)
            return info
        with patch.object(os, 'fstat', side_effect=foreign):
            with self.assertRaisesRegex(ValueError, 'owner'):
                dispatch.launch(['true'], self.repo, data, 1, prompt)
        self.assertEqual(path.stat().st_mode & 0o777, 0o755)  # foreign paths were not chmod'ed
        path.rmdir()
        path.symlink_to(self.repo, target_is_directory=True)
        with self.assertRaises((OSError, ValueError)):
            dispatch.launch(['true'], self.repo, data, 1, prompt)
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_two_repositories_first_workers_get_ports_no_one_else_holds(self):
        """Every runner's slot 1 got 20100..20199, and two repositories' fixtures collided."""
        leases = self.root / 'port-leases'  # private: live runners on this host lease the real blocks
        patcher = patch.object(dispatch, 'port_lease_dir', lambda: leases)
        patcher.start()
        self.addCleanup(patcher.stop)

        def start(name):
            data = self.common / 'slot-data' / name / 'attempt-1'
            data.mkdir(parents=True)
            (data / 'prompt.md').write_text('fixture')
            out = data / 'port'
            script = 'import os, sys, time; open(sys.argv[1], "w").write(os.environ["AUTOWORK_PORT_BASE"]); time.sleep(30)'
            worker = dispatch.launch([sys.executable, '-c', script, str(out)], self.repo, data, 1, data / 'prompt.md')
            self.addCleanup(dispatch.stop, worker, str(self.repo))
            for _ in range(200):
                if out.exists() and out.read_text():
                    return worker, int(out.read_text())
                time.sleep(.01)
            self.fail('the worker did not report its port base')
        first, a = start('P1')
        _, b = start('P2')
        self.assertNotEqual(a, b)
        for base in (a, b):
            self.assertEqual((base - 20100) % 100, 0)
            self.assertLess(base + 99, 32768)
        dispatch.stop(first, str(self.repo))
        base, lease = dispatch.port_lease(1 + (a - 20100) // 100)
        os.close(lease)
        self.assertEqual(base, a)  # the stopped worker's block is free again

    def test_directory_containing_manifest_is_serial_beside_independent_work(self):
        """TOOLSET-160-df: it never runs beside other serial work, but no longer alone."""
        for tracked in (True, False):
            with self.subTest(tracked=tracked):
                self.write_todo(task('A', 'component/'), task('B', 'other/'), task('C', 'go.sum'))
                (self.repo / 'component').mkdir(exist_ok=True)
                manifest = self.repo / 'component/go.mod'
                manifest.write_text('module example.invalid/component\n')
                if tracked:
                    self.git('add', 'component/go.mod')
                    self.commit_if_changed('protected manifest')
                else:
                    self.git('rm', '--cached', 'component/go.mod')
                self.assertEqual(dispatch.protected_files(self.repo), ['component/go.mod'])
                planned = dispatch.parallel_plan.plan(execution.select_all(self.repo),
                                                      protected_files=dispatch.protected_files(self.repo))
                self.assertEqual([t['id'] for t in planned['dispatch']], ['A', 'B'])
                self.assertEqual(planned['waiting'][0]['reason'], 'serial path shared with A')

    def test_eight_disjoint_directory_workers_launch_together(self):
        self.write_todo(*(task(f'T{i}', f'component{i}/') for i in range(8)))
        self.git('add', '-A')
        self.commit_if_changed('directory task scopes')
        self.set_spec({f'T{i}': {'sleep': 60} for i in range(8)})
        code, result = self.apply('8', '--max-workers', '8')
        self.assertEqual((code, result['active_workers']), (0, 8), result)
        self.assertEqual({s['slot'] for s in result['dispatched']}, set(range(1, 9)))

    def test_refill_starts_next_task_when_a_worker_finishes(self):
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.2},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 3.0},
                       'E': {'files': {'e.txt': 'e'}, 'sleep': 0.2}})
        self.apply()
        _, changed = self.wait(20)
        self.assertEqual([c['task'] for c in changed['changed']], ['A'])
        _, refill = self.apply()
        # E takes the free slot; D still overlaps A's unintegrated commit.
        self.assertEqual([s['task'] for s in refill['dispatched']], ['E'])
        self.assertEqual(refill['dispatched'][0]['slot'], 1)
        self.wait_until_idle()
        times = {(e['task'], e['event']): e['time'] for e in self.events()}
        self.assertLess(times['E', 'start'], times['B', 'end'])
        paths = {e['task']: e['tmpdir'] for e in self.events() if e['event'] == 'start'}
        self.assertEqual(len(set(paths.values())), 3)  # a reused worker lane is not a reused temp slot

    def test_a_planning_task_waits_for_its_batch_then_never_gets_a_worker(self):
        self.write_todo(task('A', 'a.txt'), task('PLAN', 'TODO.md', 'A') + '- Kind: plan\n')
        _, first = self.apply()
        self.assertEqual([s['task'] for s in first['dispatched']], ['A'])
        self.wait_until_idle()
        self.write_todo(task('A', 'a.txt').replace('- [ ]', '- [x]'),
                        task('PLAN', 'TODO.md', 'A') + '- Kind: plan\n')
        _, result = self.apply()
        self.assertEqual(result['dispatched'], [])
        self.assertEqual(next(w['reason'] for w in result['waiting'] if w['id'] == 'PLAN'),
                         'ready for planning')
        _, status = self.run_cli('--parallel-status', '--json', worker=False)
        self.assertEqual(next(r['reason'] for r in status['tasks'] if r['task'] == 'PLAN'),
                         'ready for planning')
        self.assertFalse((self.repo / '.worktrees/autowork-PLAN').exists())
        self.assertNotIn('PLAN', [s['task_id'] for s in state.slots(self.common)])
        with self.assertRaisesRegex(execution.NoEligibleTask, 'ready for planning'):
            execution.select(self.repo, 'PLAN', None)
    def test_merge_backlog_pauses_only_fresh_dispatch_until_it_drains(self):
        """Finished commits take precedence, without stopping interrupted work."""
        # An unset or invalid count defaults to half the pool, at least 2: 2 for these 2 workers.
        # As in the answered-question fixture, integration's subreaper is process-wide.
        import ctypes
        libc, subreaper = ctypes.CDLL(None), ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0), 0)
        self.addCleanup(lambda: libc.prctl(36, subreaper.value, 0, 0, 0))
        for number, (count, age, setting, after, paused) in enumerate(
                [(3, 1260, '3', '1200', True), (2, 1260, '3', '1200', False),
                 (3, 300, '3', '1200', False), (3, 1260, '0', '1200', False),
                 (3, 300, '3', '60', True), (2, 1260, '-1', '1200', True), (2, 1260, '', '1200', True),
                 (3, 300, '3', '-1', False)]):
            with self.subTest(count=count, age=age, setting=setting):
                self.repo = self.root / f'backlog-{number}'
                self.repo.mkdir()
                self.git('init', '-q')
                self.git('config', 'user.email', 'fixture@example.invalid')
                self.git('config', 'user.name', 'Fixture')
                self.write_todo(*(task(t, t.lower() + '.txt') for t in ('A', 'B', 'C', 'OLD', 'F')))
                self.git('add', '.')
                self.commit_if_changed('base')
                self.common = state.common_dir(self.repo)
                baseline = self.git('rev-parse', 'HEAD')
                now = time.time()
                with patch.object(time, 'time', return_value=now - age - 3600):
                    state.claim(self.repo, self.owner, max_workers=2)
                    for tid in ['A', 'B', 'C'][:count] + ['OLD']:
                        root, branch, base = dispatch.create_worktree(self.repo, self.common, tid, baseline)
                        state.create_slot(self.repo, self.owner, tid, worktree=str(root), branch=branch, baseline=base)
                # A long worker runtime is not time spent waiting to merge.
                with patch.object(time, 'time', return_value=now - age):
                    for slot in state.slots(self.common):
                        tid, root = slot['task_id'], Path(slot['worktree'])
                        if tid == 'OLD':
                            state.transition(self.repo, self.owner, tid, 'interrupted')
                        else:
                            (root / (tid.lower() + '.txt')).write_text(tid)
                            self.git('add', '.', repo=root)
                            self.commit_if_changed(tid, repo=root)
                            commit = self.git('rev-parse', 'HEAD', repo=root)
                            slot = state.transition(self.repo, self.owner, tid, 'reported', commit=commit)
                            execution.save(dispatch.data_dir(self.common, slot) / 'report.json',
                                           dict(task=tid, commit=commit, changed_files=[tid.lower() + '.txt'],
                                                blockers=[], checks=[], pending_live=[]))
                self.set_spec({'OLD': {'sleep': 60}, 'F': {'sleep': 60}})
                with patch.dict(os.environ, PI_AUTOWORK_MERGE_BACKLOG=setting,
                                PI_AUTOWORK_MERGE_BACKLOG_AFTER=after):
                    try:
                        _, result = self.apply('--tasks', 'OLD,F')
                        self.assertEqual([s['task'] for s in result['dispatched']],
                                         ['OLD'] if paused else ['OLD', 'F'])
                        if paused:
                            reason = f'wait for {count} finished commits to merge'
                            self.assertEqual(result['waiting'], [{'id': 'F', 'reason': reason, 'blocked_by': []}])
                            _, again = self.apply('--tasks', 'OLD,F')
                            self.assertEqual(again['dispatched'], [])
                            _, status = self.run_cli('--parallel-status', '--json', worker=False)
                            self.assertTrue(status['merge_backlog']['paused'])
                            self.assertEqual(next(t for t in status['tasks'] if t['task'] == 'F')['reason'], reason)
                            self.assertEqual(status['roots'], [])  # a wait, not a question
                            _, integrated = self.run_cli('--integrate', 'A', '--timeout', '10',
                                                         '--run', 'true', worker=False)
                            self.assertEqual(integrated['outcome'], 'INTEGRATED', integrated)
                            _, resumed = self.apply('--tasks', 'OLD,F')
                            self.assertEqual([s['task'] for s in resumed['dispatched']], ['F'])
                            _, status = self.run_cli('--parallel-status', '--json', worker=False)
                            self.assertFalse(status['merge_backlog']['paused'])
                    finally:
                        self.stop_workers()

    def test_finished_work_lands_before_more_starts(self):
        """Seven finished commits waited up to 1h39m while an 8-worker runner kept starting
        workers: two per worker (16) never paused it. Half the pool, at least 2, does."""
        now = time.time()
        for workers, waiting, paused in ((8, 3, False), (8, 4, True), (8, 7, True), (2, 2, True), (1, 1, False)):
            with self.subTest(workers=workers, waiting=waiting):
                current = [{'task_id': f'T{i}', 'state': 'reported', 'commit': f'c{i}'} for i in range(waiting)]
                events = [{'event': 'slot_changed', 'task_id': f'T{i}', 'state': 'reported', 'timestamp': now - 1500}
                          for i in range(waiting)]
                with patch.object(state.journal, 'read', return_value={'events': events}):
                    self.assertEqual(dispatch.merge_backlog(self.common, current, workers=workers, now=now, env={})['paused'],
                                     paused)

    def test_a_closed_writer_window_no_longer_explains_the_merge_backlog(self):
        """A reason kept on an integrating slot was replayed for hours after the session left,
        so the runner announced a writer that no longer held anything."""
        now = time.time()
        current = [dict(task_id='A', state='reported', commit='a' * 40,
                        writers_busy_reason='live writer', writers_busy_at=now - 3600),
                   dict(task_id='B', state='integrating', commit='b' * 40)]
        env = {'PI_AUTOWORK_MERGE_BACKLOG': '1', 'PI_AUTOWORK_MERGE_BACKLOG_AFTER': '1200'}
        self.assertNotIn('reason', dispatch.merge_backlog(self.common, current, workers=8, env=env))
        current[0]['writers_busy_at'] = now
        self.assertEqual(dispatch.merge_backlog(self.common, current, workers=8, env=env)['reason'],
                         'live writer')

    def test_dependent_task_waits_until_its_dependency_is_done(self):
        self.write_todo(task('A', 'a.txt'), task('C', 'c.txt', 'A'))
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.2}})
        _, result = self.apply()
        self.assertEqual([s['task'] for s in result['dispatched']], ['A'])
        self.wait_until_idle()
        _, result = self.apply()
        self.assertEqual(result['dispatched'], [])  # A is reported, not done

    def test_timed_out_worker_is_stopped_and_its_worktree_kept(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 60, 'commit': False}})
        # Exercise the Pi worker's session handoff, with a fake provider/tool instead of a model.
        launcher = self.root / 'session_worker.py'
        launcher.write_text(f'''import json, subprocess, sys
from datetime import datetime, timedelta, timezone
from pathlib import Path
sys.path.insert(0, {str(SCRIPTS.parents[1] / 'pi-autowork')!r})
from pi_autowork import worker

def fake_job(settings, role, task, directory, message, session, limit, extra):
    sessions = settings.state / 'sessions'
    sessions.mkdir(parents=True)
    stamp = (datetime.now(timezone.utc) - timedelta(minutes=14)).isoformat()
    def call(id, command):
        return {{'type': 'message', 'timestamp': stamp, 'message': {{'role': 'assistant', 'content': [
            {{'type': 'toolCall', 'id': id, 'name': 'bash', 'arguments': {{'command': command}}}}]}}}}
    events = [call('running', 'python3 -m unittest discover ' + 'x' * 150),
              call('done', 'completed command'),
              {{'type': 'message', 'message': {{'role': 'toolResult', 'toolCallId': 'done'}}}}]
    (sessions / ('2026-10-18T00-00-00-000Z_' + session + '.jsonl')).write_text(
        '\\n'.join(json.dumps(e) for e in events) + '\\n{{partial')
    subprocess.run([sys.executable, {str(FAKE)!r}, sys.argv[2], directory])
    return {{'ok': True}}
worker.pi_runtime.job = fake_job
worker.worker(sys.argv[1], sys.argv[3], sys.argv[2], sys.argv[4], '1')
''')
        self.run_cli('--apply', '--parallel', '--worker-timeout', '2', '--worker-command',
                     json.dumps([sys.executable, str(launcher), str(self.root / 'runner'),
                                 '{prompt_file}', '{worktree}', '{report_file}']), worker=False)
        started = time.time()
        _, result = self.wait(20, '--worker-timeout', '2')
        self.assertLess(time.time() - started, 15)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'interrupted')
        command = ('python3 -m unittest discover ' + 'x' * 150)[:120]
        self.assertEqual(slot['reason'], f'worker timeout after 2 s while running (14 min): {command}')
        self.assertFalse(state.worker_live(slot))
        self.assertEqual((self.repo / '.worktrees/autowork-A/a.txt').read_text(), 'partial')

    def test_a_worker_that_hangs_after_reporting_keeps_its_commit_at_the_timeout(self):
        """A worker passed every check, committed and wrote its report, then its session never
        exited: the timeout discarded the commit twice and asked the owner to rescope the task."""
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0, 'linger': 60}})
        self.run_cli('--apply', '--parallel', '--worker-timeout', '2')
        self.wait(20, '--worker-timeout', '2')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'reported')
        head = subprocess.run(['git', '-C', slot['worktree'], 'rev-parse', 'HEAD'], check=True,
                              capture_output=True, text=True).stdout.strip()
        self.assertEqual(slot['commit'], head)
        self.assertIn('kept running after reporting', slot['reason'])
        self.assertFalse(state.worker_live(slot))

    def test_crashed_worker_restarts_once_in_the_same_worktree(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('interrupted', 1))
        _, retry = self.apply()
        self.assertEqual([(s['task'], s['attempt']) for s in retry['dispatched']], [('A', 2)])
        self.assertEqual(retry['dispatched'][0]['worktree'], slot['worktree'])
        self.assertIn('previous attempt was interrupted', (self.common / 'slot-data/A/attempt-2/prompt.md')
                      .read_text().lower())
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'held')  # second failure stays held
        _, after = self.apply()
        self.assertEqual(after['dispatched'], [])
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 2)

    def test_a_held_slot_of_a_closed_task_stops_occupying(self):
        """india: Plan For Me superseded a held second attempt, and its must-run-alone
        successor waited beside the dead slot for ever."""
        self.write_todo(task('A', 'a.txt'), ALONE)
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        for _ in range(2):  # crash, restart once, crash again: held for good
            _, first = self.apply()
            self.assertEqual([d['task'] for d in first['dispatched']], ['A'])  # S must run alone
            self.wait_until_idle()
        self.assertEqual((state.slots(self.common)[0]['state'], state.slots(self.common)[0]['cause']), ('held', 'crash'))
        # An exhausted hold waits for a person, not the pool: S starts at once, and
        # closing A meanwhile keeps it out of the way too.
        _, freed = self.apply()
        self.assertEqual([d['task'] for d in freed['dispatched']], ['S'])
        self.assertEqual(next(s for s in state.slots(self.common) if s['task_id'] == 'A')['state'], 'held')

    def test_a_must_run_alone_task_starts_while_a_finished_commit_awaits_review(self):
        """One runner idled 54 minutes: S waited out A's review although A's worker had ended."""
        self.write_todo(task('A', 'a.txt'), ALONE)
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1}, 'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        _, first = self.apply()
        self.assertEqual([d['task'] for d in first['dispatched']], ['A'])  # S must run alone
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'reported')
        _, then = self.apply()
        self.assertEqual([d['task'] for d in then['dispatched']], ['S'])
        self.wait_until_idle()

    def test_a_retryable_slot_of_a_closed_task_stops_occupying(self):
        self.write_todo(task('A', 'a.txt'), ALONE)
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        self.apply()
        self.wait_until_idle()  # crashed once: interrupted, with its restart still to come
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('interrupted', 1))
        self.write_todo(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), ALONE)
        _, freed = self.apply()
        self.assertEqual([d['task'] for d in freed['dispatched']], ['S'])

    def close_on_base(self, *bodies):
        """Commit ``bodies`` as TODO.md on a separate base branch, ``trunk``, the way an owner
        closes tasks on main while the session's own ledger lags (TOOLSET-218-d0)."""
        base = self.root / 'base'
        if not base.exists():
            self.git('worktree', 'add', '-q', '-b', 'trunk', str(base), 'HEAD')
        store_fixture.write_todo(base, '# Work queue\n\n## Next\n\n' + '\n'.join(bodies))

    def test_a_task_deleted_from_the_queue_is_stopped_and_set_aside(self):
        """After the owner reset the queue, eight finished commits of deleted tasks asked to
        integrate every minute and were refused as 'first: None'; nothing set them aside."""
        self.set_spec({'A': {'files': {'a.txt': 'deleted work'}, 'sleep': 30},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 30}})
        _, first = self.apply()
        self.assertIn('A', [d['task'] for d in first['dispatched']])
        worker = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        store_fixture.write_todo(self.repo, self.todo.replace(task('A', 'a.txt'), ''))
        self.assertIsNone(task_queue.record(self.repo, 'A'))
        _, freed = self.apply()
        self.assertEqual(freed['closed_on_base'], ['A'], freed)
        self.assertFalse(state.worker_live(worker))
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])
        self.assertTrue(self.git('branch', '--list', 'autowork/A-set-aside-1'))  # its work is kept

    def test_a_worker_whose_task_closes_on_the_base_is_stopped_and_set_aside(self):
        self.set_spec({'A': {'files': {'a.txt': 'duplicate'}, 'sleep': 30},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 30}, 'D': {'files': {'a.txt': 'd'}, 'sleep': 30}})
        _, first = self.apply('--base-ref', 'trunk')  # no trunk yet: the session's ledger alone
        self.assertEqual([d['task'] for d in first['dispatched']], ['A', 'B'])
        worker = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        self.close_on_base(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('B', 'b.txt'),
                           task('C', 'c.txt', 'A'), task('E', 'e.txt'), task('D', 'a.txt'))
        _, freed = self.apply('--base-ref', 'trunk')
        self.assertEqual(freed['closed_on_base'], ['A'], freed)
        self.assertFalse(state.worker_live(worker))
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])
        self.assertEqual(len(freed['dispatched']), 1, freed)  # the freed slot starts the next task at once
        self.assertNotIn('A', [d['task'] for d in freed['dispatched']])
        history = json.loads((self.common / 'slot-history' / 'A' / '1' / 'slot.json').read_text())
        self.assertEqual(history['cause'], 'closed_on_base')
        kept = self.repo / '.worktrees' / 'autowork-A-set-aside-1'
        self.assertEqual((kept / 'a.txt').read_text(), 'duplicate')  # uncommitted work is kept
        self.assertTrue(self.git('branch', '--list', 'autowork/A-set-aside-1'))
        self.assertIn('B', [s['task_id'] for s in state.slots(self.common)])  # open on both: untouched

    def test_a_task_closed_on_the_base_during_a_review_reads_closing_until_set_aside(self):
        """TOOLSET-250-49: 270 done/implemented lines in 11 minutes while a review held the lock."""
        import parallel_status
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.1}, 'B': {'files': {'b.txt': 'b'}, 'sleep': 0.1}})
        self.apply('--base-ref', 'trunk')
        self.wait_until_idle()
        self.close_on_base(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('B', 'b.txt'))
        with execution.lock(self.common / 'integration.lock'):  # a review is running
            for _ in range(3):
                _, held = self.apply('--base-ref', 'trunk')
                self.assertEqual((held.get('closing'), held.get('closed_on_base')), (['A'], None))
            rows = {r['task']: r for r in parallel_status.snapshot(str(self.repo))['tasks']}
            self.assertEqual(rows['A']['state'], 'closing')
        _, freed = self.apply('--base-ref', 'trunk')
        self.assertEqual(freed['closed_on_base'], ['A'])
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])

    def test_a_held_slot_of_a_task_closed_on_the_base_is_set_aside_not_retried(self):
        """A held task closed on main kept its slot and was even retried fresh."""
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'blockers': ['needs a device']},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 0.1}})
        self.apply('--base-ref', 'trunk')
        self.wait_until_idle()
        self.assertEqual(next(s for s in state.slots(self.common) if s['task_id'] == 'A')['state'], 'held')
        self.close_on_base(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('B', 'b.txt'))
        _, freed = self.apply('--base-ref', 'trunk')
        self.assertEqual(freed.get('closed_on_base'), ['A'], freed)
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])
        self.assertNotIn('A', [d['task'] for d in freed.get('dispatched') or []])

    def test_closed_at_base_is_not_redispatched(self):
        """An older session still has A open; the base closed it: A never starts again."""
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.1}, 'B': {'files': {'b.txt': 'b'}, 'sleep': 0.1}})
        self.close_on_base(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('B', 'b.txt'),
                           task('C', 'c.txt', 'A'), task('E', 'e.txt'), task('D', 'a.txt'))
        self.assertEqual(task_queue.record(self.repo, 'A').status, 'open')  # the session's own store
        for _ in range(2):
            _, result = self.apply('--base-ref', 'trunk')
            self.assertNotIn('A', [d['task'] for d in result['dispatched']], result)
            self.wait_until_idle()
        self.assertNotIn('A', [e.get('task') for e in self.events()])

    def test_unconverted_repo_names_migrate(self):
        bare = self.root / 'unconverted'
        bare.mkdir()
        self.git('init', '-q', repo=bare)
        (bare / 'TODO.md').write_text('# Work queue\n\n## Next\n\n' + task('A', 'a.txt'))
        self.git('add', '-A', repo=bare)
        self.git('-c', 'user.email=f@example.invalid', '-c', 'user.name=F', 'commit', '-qm', 'old plan', repo=bare)
        argv = [str(bare), '--owner-pid', str(self.owner), '--apply', '--parallel', '--worker-command',
                json.dumps([sys.executable, str(FAKE), '{prompt_file}', '{worktree}'])]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = execution.main(argv)
        result = json.loads(out.getvalue())
        self.assertNotEqual(code, 0)
        self.assertIn(f'run `autowork migrate {bare}`', json.dumps(result))
        self.assertFalse(result.get('dispatched'))
        self.assertEqual(self.events(), [])  # no worker started

    def test_a_task_closed_only_on_the_base_never_starts(self):
        self.close_on_base(task('A', 'a.txt'), task('B', 'b.txt'), task('C', 'c.txt', 'A'),
                           task('E', 'e.txt').replace('- [ ] E', '- [x] E'), task('D', 'a.txt'))
        _, result = self.apply('4', '--base-ref', 'trunk')
        self.assertEqual(sorted(d['task'] for d in result['dispatched']), ['A', 'B', 'D'])
        self.assertNotIn('D', [w['id'] for w in result['waiting']])  # cold overlap can use a free slot
        self.assertNotIn('E', [w['id'] for w in result['waiting']])

    def test_an_unreadable_base_falls_back_to_the_session_ledger(self):
        _, result = self.apply('--base-ref', 'no-such-branch')
        self.assertEqual([d['task'] for d in result['dispatched']], ['A', 'B'])
        self.assertNotIn('closed_on_base', result)

    def test_a_reported_commit_of_a_task_closed_on_the_base_is_set_aside_not_integrated(self):
        import parallel_integrate as integrate
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.1}})
        self.apply('1')
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'reported')
        self.close_on_base(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('B', 'b.txt'),
                           task('C', 'c.txt', 'A'), task('E', 'e.txt'), task('D', 'a.txt'))
        result = integrate.integrate(self.repo, self.owner, 'A', ['false'], 60, None, 'trunk')
        self.assertEqual(result['outcome'], 'SET_ASIDE', result)
        self.assertIn('closed on trunk', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.git('rev-parse', 'trunk~1'))  # nothing merged
        self.assertTrue(self.git('branch', '--list', 'autowork/A-set-aside-1'))

    def test_a_worker_that_reports_a_blocker_is_held_for_a_person_not_resumed(self):
        """sierra TASK-022: a worker stopped on purpose with blockers, was read as a crash,
        resumed, and spent both attempts on the same wall."""
        self.write_todo(task('A', 'a.txt'), ALONE)
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Needs src/other.go, outside Touches']},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause'], slot['attempt']), ('held', 'blocker', 1))
        self.assertEqual(slot['reason'], 'worker reported a blocker: Needs src/other.go, outside Touches')
        self.assertEqual((Path(slot['worktree']) / 'a.txt').read_text(), 'partial')
        _, refill = self.apply()  # no resume, no fresh retry; the must-run-alone S proceeds
        self.assertEqual([d['task'] for d in refill['dispatched']], ['S'])
        self.wait_until_idle()
        self.assertEqual([e['task'] for e in self.events() if e['event'] == 'start'], ['A', 'S'])
        # Losing a report never authorizes resuming an already-held genuine request.
        (dispatch.data_dir(self.common, slot) / 'report.json').unlink()
        state.reconcile(self.repo, self.owner)
        self.assertEqual(state.slots(self.common)[0]['state'], 'held')

    def test_dirty_external_input_blockers_are_not_misread_as_host_only(self):
        self.write_todo(*(task(t, t.lower() + '.txt') for t in 'ABCD'))
        self.set_spec({t: {'files': {t.lower() + '.txt': 'partial'}, 'commit': False, 'blockers': [text]}
                       for t, text in [('A', 'Provide the SDK path to rerun the unrelated test'),
                                       ('B', 'Host load is high; provide an API key to finish the implementation'),
                                       ('C', 'Host load is high; need SSH access to the validation host'),
                                       ('D', 'Provide a quiet validation window and the database URL '
                                             'to run the flaky test')]})
        self.run_cli('--apply', '--parallel', '4')
        self.wait_until_idle()
        self.assertEqual([(s['state'], s['cause']) for s in state.slots(self.common)],
                         [('held', 'blocker'), ('held', 'blocker'), ('held', 'blocker'), ('held', 'blocker')])

    def test_a_dirty_host_check_blocker_resumes_once_then_waits_as_timeout(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'finished'}, 'commit': False,
                             'blockers': ['Provide a lower-load offline validation host or a quiet validation '
                                          'window to rerun the required full gate without the unrelated '
                                          'budget-controller timing failure and resource-gated skips']}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 1, True))
        self.apply()
        prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
        self.assertIn('commit the finished work', prompt)
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause'], slot['attempt']), ('held', 'timeout', 1))
        self.assertEqual((Path(slot['worktree']) / 'a.txt').read_text(), 'finished')
        self.set_spec({'A': {'files': {'a.txt': 'finished'}}})
        _, result = self.run_cli('--parallel-reverify', 'A', '--reviewer-version', 'quiet-host', worker=False)
        self.assertEqual(result['outcome'], 'REVERIFY', result)
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot['branch']), ('reported', 1, 'autowork/A'))

    def test_task_wait_frees_exclusive_work_and_resumes_only_after_all_land(self):
        a, b, e = task('A', 'a.txt'), task('B', 'b.txt') + '- Resources: exclusive\n', task('E', 'e.txt')
        self.write_todo(a, b, e)
        self.commit_if_changed('task wait fixture')
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Needs B and E to land.'],
                             'then': {'files': {'a.txt': 'done'}, 'ready': str(self.root / 'ready'),
                                      'release': str(self.root / 'continue')}},
                       'B': {'files': {'b.txt': 'landed B'}, 'sleep': 0.1},
                       'E': {'files': {'e.txt': 'landed E'}, 'sleep': 0.1}})
        self.apply('--tasks', 'A')
        self.wait_until_idle()
        original = state.slots(self.common)[0]
        self.assertEqual(original.get('waits_for'), ['B', 'E'])
        from parallel_status import snapshot
        sys.path.insert(0, str(SCRIPTS.parents[1] / 'pi-autowork'))
        from pi_autowork import questions
        self.assertEqual(questions.build(snapshot(self.repo), self.repo), [])
        _, refill = self.apply()
        self.assertEqual([d['task'] for d in refill['dispatched']], ['B'])
        self.wait_until_idle()
        self.git('merge', '--no-ff', '-m', 'land B', 'autowork/B')
        self.write_todo(a, b.replace('- [ ] B', '- [x] B'), e)
        self.commit_if_changed('close B locally')
        _, partial = self.apply()
        self.assertEqual([d['task'] for d in partial['dispatched']], ['E'])
        self.wait_until_idle()
        self.close_on_base(a, b.replace('- [ ] B', '- [x] B'), e.replace('- [ ] E', '- [x] E'))
        base = self.root / 'base'
        (base / 'e.txt').write_text('landed E')
        self.git('add', 'e.txt', repo=base)
        self.commit_if_changed('prerequisite code on base', repo=base)
        landed = self.git('rev-parse', 'trunk')
        _, resumed = self.apply('--base-ref', 'trunk')
        self.assertEqual((resumed['outcome'], resumed['task']), ('RESUMED', 'A'), resumed)
        _, restarted = self.apply('--base-ref', 'trunk')
        self.assertEqual([(d['task'], d['attempt']) for d in restarted['dispatched']], [('A', 1)])
        self.assertEqual(self.pause_and_stop(), ['A'])
        self.wait_until_idle()
        (self.root / 'continue').touch()
        _, restarted = self.apply('--base-ref', 'trunk')
        self.assertEqual([(d['task'], d['attempt']) for d in restarted['dispatched']], [('A', 1)])
        self.wait_until_idle()
        slot = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        self.assertEqual((slot['worktree'], slot['branch'], slot['baseline']),
                         (original['worktree'], original['branch'], original['baseline']))
        prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
        self.assertIn('Landed prerequisites: B, E', prompt)
        self.assertIn(landed, prompt)
        self.assertEqual(self.git('show', f'{landed}:e.txt', repo=slot['worktree']), 'landed E')
        self.assertNotIn('waits_for', slot)

    def test_a_paused_committed_task_wait_resumes_without_a_fresh_report(self):
        # As in the answered-question fixture, restore integration's process-wide subreaper.
        import ctypes
        libc, subreaper = ctypes.CDLL(None), ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0), 0)
        self.addCleanup(lambda: libc.prctl(36, subreaper.value, 0, 0, 0))
        a, b = task('A', 'a.txt'), task('B', 'b.txt')
        self.write_todo(a, b)
        self.commit_if_changed('committed wait fixture')
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1,
                             'blockers': ['Needs B to land.']}})
        self.apply('--tasks', 'A')
        self.wait_until_idle()
        _, held = self.run_cli('--integrate', 'A', '--timeout', '10', '--run', 'true', worker=False)
        self.assertEqual((held['cause'], held['waits_for']), ('task_wait', ['B']))
        original = state.slots(self.common)[0]
        self.write_todo(a, b.replace('- [ ] B', '- [x] B'))
        self.commit_if_changed('close prerequisite')
        self.assertEqual(self.apply()[1]['outcome'], 'RESUMED')
        ready, release = self.root / 'ready', self.root / 'continue'
        self.set_spec({'A': {'files': {'a.txt': 'reconciling'}, 'ready': str(ready), 'release': str(release)}})
        self.apply()
        slot = state.slots(self.common)[0]
        prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
        self.assertIn('Landed prerequisites: B', prompt)
        self.assertNotIn('Do not reimplement the task or make another commit', prompt)
        deadline = time.monotonic() + 5
        while not ready.exists() and time.monotonic() < deadline:
            time.sleep(0.01)
        self.assertTrue(ready.exists())
        self.assertEqual(self.pause_and_stop(), ['A'])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 1, True))
        release.touch()
        _, restarted = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in restarted['dispatched']], [('A', 1)])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['worktree'], slot['baseline']), (original['worktree'], original['baseline']))
        self.assertIn('Landed prerequisites: B', (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text())
        _, integrated = self.run_cli('--integrate', 'A', '--timeout', '10', '--run', 'true', worker=False)
        self.assertEqual(integrated['outcome'], 'INTEGRATED', integrated)
        self.assertEqual((self.repo / 'a.txt').read_text(), 'reconciling')

    def test_an_answered_blocker_resumes_its_attempt_with_the_answer_twice_at_most(self):
        """Most blockers asked the runner for what it already provides and waited hours for a person."""
        self.write_todo(task('A', 'a.txt'))
        self.commit_if_changed('A')
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Coordinator must provide an exclusive port receipt']}})
        self.apply()
        self.wait_until_idle()
        held = state.slots(self.common)[0]
        self.assertEqual((held['state'], held['cause']), ('held', 'blocker'))
        answer = self.root / 'answer.txt'
        answer.write_text('Your port range is leased to you alone on this host; no receipt exists.')
        for n in (1, 2):
            _, result = self.run_cli('--parallel-answer', 'A', '--answer-file', str(answer), worker=False)
            self.assertEqual((result['outcome'], result['answered']), ('ANSWERED', n))
            _, resumed = self.apply()
            self.assertEqual([d['task'] for d in resumed['dispatched']], ['A'])
            slot = state.slots(self.common)[0]
            self.assertEqual((slot['attempt'], slot['worktree']), (held['attempt'], held['worktree']))
            prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
            self.assertIn('the runner answered it', prompt)
            self.assertIn('no receipt exists', prompt)
            self.wait_until_idle()
        _, refused = self.run_cli('--parallel-answer', 'A', '--answer-file', str(answer), worker=False)
        self.assertEqual(refused['outcome'], 'ACTION_REQUIRED')  # a third time, it is the owner's

    def test_a_report_that_nothing_needed_changing_is_held_not_rerun(self):
        """One task ran three times in an hour: each worker found nothing to change and said so."""
        self.write_todo(task('A', 'a.txt'))
        self.commit_if_changed('A')
        self.set_spec({'A': {'sleep': 0.1, 'nothing': 'the flaky test no longer fails'}})
        self.apply()
        self.wait_until_idle()
        _, again = self.apply()
        self.assertEqual(again['dispatched'], [])
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause']), ('held', 'no_change'))
        self.assertIn('the flaky test no longer fails; full check: pass', slot['reason'])

    def test_a_held_scope_request_resumes_in_place_without_a_touches_check(self):
        """sierra TASK-024: a worker needed one test file outside Touches and could only stop.
        TOOLSET-161-17: a worker no longer asks; a request an older release held resumes in its
        own worktree on the same attempt, with no change to Touches."""
        self.write_todo(task('A', 'a.txt'))
        self.git('add', '.')
        self.commit_if_changed('A')
        self.set_spec({'A': {'files': {'a.txt': 'half', 'b.txt': 'needed'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['b.txt is outside Touches'], 'needs_touches': ['b.txt'],
                             'then': {'files': {'a.txt': 'done', 'b.txt': 'done'}, 'sleep': 0.1}}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause']), ('held', 'blocker'))  # needs_touches is not read
        state.write_slot(self.common, {**slot, 'cause': 'scope_request', 'requested': ['b.txt']}, slot)
        _, resumed = self.apply()
        self.assertEqual(resumed['outcome'], 'RESUMED')
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 1, True))
        self.assertEqual((Path(slot['worktree']) / 'b.txt').read_text(), 'needed')  # its work is intact
        _, dispatched = self.apply()
        self.assertEqual([d['task'] for d in dispatched['dispatched']], ['A'])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('reported', 1))  # same attempt, now committed
        prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
        self.assertIn('It guides scheduling, not a fence', prompt)
        self.assertNotIn('needs_touches', prompt)

    def test_an_answered_question_requeues_the_held_task_once(self):
        """An answered hold runs fresh and can continue its preserved candidate."""
        # Integration's bounded validator enables subreaping; do not leak that
        # process-wide setting into dispatch's later orphan-cleanup tests.
        import ctypes
        libc, subreaper = ctypes.CDLL(None), ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(subreaper), 0, 0, 0), 0)
        self.addCleanup(lambda: libc.prctl(36, subreaper.value, 0, 0, 0))
        self.write_todo(task('A', '*a.txt'), task('B', 'b.txt'))
        self.git('add', '.')
        self.commit_if_changed('A and B')
        self.set_spec({'A': {'files': {' a.txt': 'half'}, 'sleep': 0.1,
                             'blockers': ['Which unit should the output use?']},
                       'B': {'files': {'b.txt': 'half'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Needs a decision too']}})
        self.apply()
        self.wait_until_idle()
        _, held = self.run_cli('--integrate', 'A', '--timeout', '10', '--run', 'true', worker=False)
        self.assertEqual(held['outcome'], 'HELD', held)
        self.assertEqual({s['task_id']: s['cause'] for s in state.slots(self.common)}, {'A': 'blocker', 'B': 'blocker'})
        first = (self.common / 'slot-data/A/attempt-1/prompt.md').read_text()
        self.assertNotIn('Earlier task work:', first)
        candidate = self.git('rev-parse', 'autowork/A')
        date = self.git('show', '-s', '--format=%cI', candidate)
        # The same prompt builder also serves fresh -r2 retries of held integrations.
        entry = {'id': 'A', 'title': 'Task A', 'fields': {'Touches': '*a.txt'}, 'contract': ''}
        retry = dispatch.prompt(entry, self.repo, 'autowork/A-r2', self.git('rev-parse', 'HEAD'), 'report')
        self.assertIn(f'- branch autowork/A; tip {candidate}; date {date}', retry)
        _, unchanged = self.apply()
        self.assertEqual(unchanged['outcome'], 'IDLE')  # no answer yet: both stay held
        self.write_todo(task('A', '*a.txt').replace('- Acceptance: changed.',
                        '- Acceptance: keep the earlier candidate, in metres.'),
                        task('B', 'b.txt'))
        self.commit_if_changed('owner answers A')
        _, requeued = self.apply()
        self.assertEqual((requeued['outcome'], requeued['task'], requeued['requeued']), ('REQUEUED', 'A', True))
        self.assertIn('autowork/A-set-aside-1', self.git('branch', '--list', 'autowork/*'))
        older = subprocess.check_output(['git', '-C', str(self.repo), 'commit-tree',
                    self.git('rev-parse', 'HEAD^{tree}'), '-p', self.git('rev-parse', 'HEAD'), '-m', 'old retry'],
                    env={**os.environ, 'GIT_COMMITTER_DATE': '2000-01-01T00:00:00+00:00'}, text=True).strip()
        self.git('branch', 'autowork/A-r2-set-aside-1', older)
        self.git('branch', 'autowork/AB-set-aside-1', candidate)  # not this task
        # This worker can finish only by discovering and applying the named local tip.
        recover = self.root / 'recover.py'
        recover.write_text('''import json, re, subprocess, sys
from pathlib import Path
prompt = Path(sys.argv[1]).read_text()
repo = sys.argv[2]
def git(*args):
    return subprocess.check_output(['git', '-C', repo, *args], text=True).strip()
tip = re.search(r'^- branch autowork/A-set-aside-1; tip ([0-9a-f]+);', prompt, re.M)[1]
git('cherry-pick', '--no-commit', tip)
assert Path(repo, ' a.txt').read_text() == 'half'
Path(repo, ' a.txt').write_text('half, in metres')
git('commit', '-qam', 'continue retained candidate')
report = re.search(r'^Report file: (.+)$', prompt, re.M)[1]
Path(report).write_text(json.dumps({'task': 'A', 'commit': git('rev-parse', 'HEAD'),
    'changed_files': [' a.txt'], 'checks': [], 'blockers': [], 'changelog': ''}))
''')
        _, fresh = self.run_cli('--apply', '--parallel', '--worker-command',
                                json.dumps([sys.executable, str(recover), '{prompt_file}', '{worktree}']),
                                worker=False)
        self.assertEqual([d['task'] for d in fresh['dispatched']], ['A'])
        prompt = (self.common / 'slot-data/A/attempt-1/prompt.md').read_text()
        self.assertIn(f'- branch autowork/A-set-aside-1; tip {candidate}; date {date}', prompt)
        self.assertIn('changed files: [" a.txt"]', prompt)  # preserve leading filename whitespace
        self.assertLess(prompt.index('- branch autowork/A-set-aside-1;'),
                        prompt.index(f'- branch autowork/A-r2-set-aside-1; tip {older}; date 2000-01-01'))
        self.assertNotIn('- branch autowork/AB', prompt)
        self.assertNotIn('- branch autowork/A;', prompt)  # not the current attempt
        self.wait_until_idle()
        slots = {s['task_id']: s for s in state.slots(self.common)}
        self.assertEqual((slots['A']['state'], slots['A']['attempt']), ('reported', 1))
        self.assertEqual(slots['B']['state'], 'held')  # unchanged entry: still waiting for its answer
        _, integrated = self.run_cli('--integrate', 'A', '--timeout', '10', '--run', 'true', worker=False)
        self.assertEqual(integrated['outcome'], 'INTEGRATED', integrated)
        self.assertEqual((self.repo / ' a.txt').read_text(), 'half, in metres')
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), candidate)

    def test_a_held_task_whose_entry_is_removed_is_set_aside_without_requeue(self):
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        self.git('add', '.')
        self.commit_if_changed('A and B')
        self.set_spec({'A': {'files': {'a.txt': 'half'}, 'sleep': 0.1, 'commit': False, 'blockers': ['Drop this?']}})
        self.apply()
        self.wait_until_idle()
        self.write_todo(task('B', 'b.txt'))
        self.commit_if_changed('owner drops A')
        _, result = self.apply()
        self.assertEqual((result['outcome'], result['task'], result['requeued']), ('REQUEUED', 'A', False))
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])

    def pause_and_stop(self):
        """What a deliberate coordinator stop does: mark live workers, then interrupt them."""
        _, paused = self.run_cli('--parallel-pause', worker=False)
        self.assertEqual(paused['outcome'], 'PAUSED')
        for slot in state.slots(self.common):
            if state.worker_live(slot):
                dispatch.stop(slot['worker'], slot['worktree'])
        return paused['paused']

    def test_a_paused_worker_resumes_the_same_attempt(self):
        """india: a service restart interrupted attempt 2 of TASK-015 and held it for good."""
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.apply()
        self.wait_until_idle()  # a real crash: the retry is spent
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 30, 'commit': False}})
        _, second = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in second['dispatched']], [('A', 2)])
        temp = Path(execution.read(self.common / 'slot-data/A/tmp.json')['path'])
        (temp / 'keep').write_text('resume state')
        state.release(self.repo, self.owner)
        _, adopted = self.apply()
        self.assertEqual(adopted['dispatched'], [])  # live worker adopted, not duplicated
        self.assertEqual(self.pause_and_stop(), ['A'])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 2, True))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1}})
        # Runtime settings can change across a service restart: reuse the saved path.
        with patch.dict(os.environ, XDG_RUNTIME_DIR=''):
            _, resumed = self.apply()
        self.assertEqual(execution.read(self.common / 'slot-data/A/tmp.json')['path'], str(temp))
        self.assertEqual((temp / 'keep').read_text(), 'resume state')
        self.assertEqual([(d['task'], d['attempt']) for d in resumed['dispatched']], [('A', 2)])
        self.assertEqual(resumed['dispatched'][0]['worktree'], slot['worktree'])
        self.assertNotIn('paused', state.slots(self.common)[0])
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'reported')

    def test_a_paused_first_attempt_keeps_its_retry(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 30, 'commit': False}})
        self.apply()
        self.pause_and_stop()
        self.wait_until_idle()
        _, resumed = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in resumed['dispatched']], [('A', 1)])
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.stop_workers()
        self.wait_until_idle()  # this unpaused death spends attempt 1 as before
        _, retry = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in retry['dispatched']], [('A', 2)])

    def test_the_memory_gate_counts_only_what_one_more_worker_needs(self):
        """TOOLSET-162-d2: running workers' memory is already out of MemAvailable."""
        with patch.object(dispatch, 'available_memory_mb', return_value=7000), \
                patch.object(dispatch.os, 'getloadavg', return_value=(0.0, 0.0, 0.0)):
            self.assertEqual(dispatch.resource_gate(2, 3000), '')
            self.assertEqual(dispatch.resource_gate(7, 3000), '')
        with patch.object(dispatch, 'available_memory_mb', return_value=5900):
            self.assertEqual(dispatch.resource_gate(0, 3000),
                             'resource gate: 5900 MB available, need 6000 MB for one more worker')

    def test_a_nearly_full_disk_holds_dispatch(self):
        """TOOLSET-210-53: the disk filled and six runners died; dispatch now stops first."""
        with patch.dict(os.environ, PI_AUTOWORK_MIN_FREE_DISK_GB='1e9'), \
                patch.object(dispatch, 'available_memory_mb', return_value=99999):
            reason = dispatch.resource_gate(0, 3000, self.repo)
        self.assertRegex(reason, r'^resource gate: [\d.]+ GB free on the repository disk, need 1e\+09 GB$')
        with patch.dict(os.environ, PI_AUTOWORK_MIN_FREE_DISK_GB='0'), \
                patch.object(dispatch, 'available_memory_mb', return_value=99999), \
                patch.object(dispatch.os, 'getloadavg', return_value=(0.0, 0.0, 0.0)):
            self.assertEqual(dispatch.resource_gate(0, 3000, self.repo), '')

    def test_load_gates_only_workers_after_this_runners_first(self):
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        self.set_spec({'A': {'sleep': 60}, 'B': {'sleep': 60}})
        with patch.object(dispatch.os, 'getloadavg', return_value=(3.0, 0.0, 0.0)), \
                patch.dict(os.environ, AUTOWORK_GATE_CPUS='2'):
            _, first = self.apply()
            self.assertEqual([s['task'] for s in first['dispatched']], ['A'])
            self.assertEqual(first['waiting'], [dict(id='B', blocked_by=[],
                              reason='resource gate: load average 3.00 >= 2 CPUs')])
            _, again = self.apply()
            self.assertEqual((again['outcome'], again['dispatched']), ('WAITING', []))
            self.assertEqual(again['waiting'], first['waiting'])

    def test_low_memory_holds_dispatch(self):
        with patch.object(dispatch, 'available_memory_mb', return_value=1000), \
                patch.object(dispatch.os, 'getloadavg', return_value=(99999.0, 0.0, 0.0)):
            _, result = self.apply()
        self.assertEqual(result['outcome'], 'IDLE')
        self.assertEqual(result['dispatched'], [])
        self.assertTrue(all('resource gate' in w['reason'] for w in result['waiting']
                            if w['id'] in ('A', 'B')))
        self.assertFalse((self.common / 'slots').exists() and state.slots(self.common))

    def test_leftover_merged_branch_is_removed_before_dispatch(self):
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        baseline = self.git('rev-parse', 'HEAD')
        self.git('branch', 'autowork/A', baseline)
        self.set_spec({'A': {'sleep': 60}, 'B': {'sleep': 60}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['A', 'B'])
        journal = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        removed = [e for e in journal if e['event'] == 'stale_branch_removed']
        self.assertEqual([(e['task_id'], e['branch'], e['tip']) for e in removed],
                         [('A', 'autowork/A', baseline)])
        self.assertFalse(self.git('branch', '--list', 'autowork/A-set-aside-*'))

    def test_leftover_unique_branch_is_set_aside_before_dispatch(self):
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        baseline = self.git('rev-parse', 'HEAD')
        tree = self.git('rev-parse', 'HEAD^{tree}')
        tip = self.git('commit-tree', tree, '-p', baseline, '-m', 'prior task work')
        unrelated = self.git('commit-tree', tree, '-m', 'unrelated task work')
        self.git('branch', 'autowork/A', tip)
        self.git('branch', 'autowork/B', unrelated)
        self.git('branch', 'autowork/A-set-aside-1', baseline)
        self.set_spec({'A': {'sleep': 60}, 'B': {'sleep': 60}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['A', 'B'])
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-2'), tip)
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), baseline)
        self.assertEqual(self.git('rev-parse', 'autowork/B-set-aside-1'), unrelated)
        self.assertEqual(self.git('rev-parse', 'autowork/A'), baseline)
        self.assertEqual(self.git('rev-parse', 'autowork/B'), baseline)

    def test_unsafe_worktree_path_holds_only_its_task_untouched(self):
        folder = self.repo / '.worktrees/autowork-A'
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        folder.mkdir(parents=True)
        (folder / 'mine').write_text('user data')
        self.set_spec({'B': {'sleep': 60}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['B'])
        self.assertIn('A', [w['id'] for w in result['waiting']])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['mine'])
        self.assertFalse(self.git('branch', '--list', 'autowork/A'))

        # A registered worktree with uncommitted work is no safer to reclaim.
        (folder / 'mine').unlink()
        folder.rmdir()
        self.git('worktree', 'add', '-qb', 'autowork/A', str(folder))
        (folder / 'mine').write_text('unsaved work')
        for journaled in (False, True):
            with self.subTest(journaled=journaled):
                if journaled:
                    state.event(self.common, 'worktree_created', task_id='A', worktree=str(folder), branch='autowork/A')
                _, again = self.apply()
                self.assertEqual(again['dispatched'], [])
                self.assertIn('A', [w['id'] for w in again['waiting']])
                self.assertEqual((folder / 'mine').read_text(), 'unsaved work')
                self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD', repo=folder), 'autowork/A')
        (folder / 'mine').unlink()
        with patch.object(execution, 'external_workers', return_value=[{'workspaces': [str(folder)], 'active': True}]):
            _, busy = self.apply()
        self.assertEqual(busy['dispatched'], [])
        self.assertIn('A', [w['id'] for w in busy['waiting']])

    def test_clean_leftover_worktree_is_replaced_without_losing_its_commit(self):
        self.write_todo(task('A', 'a.txt'))
        baseline = self.git('rev-parse', 'HEAD')
        folder = self.repo / '.worktrees/autowork-A'
        self.git('worktree', 'add', '-qb', 'autowork/A', str(folder))
        (folder / 'a.txt').write_text('earlier work')
        self.git('add', 'a.txt', repo=folder)
        self.commit_if_changed('earlier work', repo=folder)
        tip = self.git('rev-parse', 'HEAD', repo=folder)
        self.set_spec({'A': {'sleep': 60}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['A'])
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), tip)
        self.assertEqual(self.git('rev-parse', 'HEAD', repo=folder), baseline)

    def test_unsupported_host_falls_back_to_the_sequential_contract(self):
        for args in (('--worker-host', 'claude'), ('--worker-host', 'hermes')):
            with self.subTest(args=args), patch.object(dispatch.shutil, 'which', return_value=None):
                code, result = self.run_cli('--apply', '--parallel', *args, worker=False)
                self.assertEqual((code, result['outcome']), (0, 'SEQUENTIAL_FALLBACK'))
                self.assertEqual(result['task']['id'], 'A')
                self.assertFalse((self.common / 'coordinator.json').exists())
        self.assertEqual(self.events(), [])

    def test_templates_never_bypass_approvals_and_use_scoped_write_roots(self):
        for host, template in dispatch.TEMPLATES.items():
            text = ' '.join(template)
            for flag in ('--yolo', 'bypass', 'danger', 'skip-permissions', '--approve'):
                self.assertNotIn(flag, text, host)
        self.assertIn('{git_common_dir}', dispatch.TEMPLATES['codex'])
        codex = type('Args', (), {'worker_command': None, 'worker_host': 'codex', 'worker_profile': None})
        with patch.object(dispatch.shutil, 'which', return_value='/bin/codex'):
            self.assertEqual(dispatch.worker_command(codex, self.owner)[0], None)  # not qualified live
            self.assertIn('read-only', dispatch.worker_command(codex, self.owner)[1])
        args = type('Args', (), {'worker_command': None, 'worker_host': 'hermes', 'worker_profile': 'work'})
        with patch.object(dispatch.shutil, 'which', return_value='/bin/hermes'):
            template, host = dispatch.worker_command(args, self.owner)
        self.assertEqual((template[:4], host), (['hermes', '-p', 'work', 'chat'], 'hermes'))

    def test_hermes_launcher_process_is_detected_as_the_coordinator_host(self):
        process = subprocess.Popen([sys.executable, '-I', '-c', 'import time  # hermes_cli.main\ntime.sleep(30)'])
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        time.sleep(0.2)
        self.assertEqual(dispatch.coordinator_host(process.pid), 'hermes')

    def test_worker_keeps_the_timeout_it_was_started_with(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 60, 'commit': False}})
        self.apply('--worker-timeout', '1')
        _, result = self.wait(20)  # default --worker-timeout 3600 on this call
        self.assertEqual(state.slots(self.common)[0]['state'], 'interrupted')

    def test_surviving_child_keeps_the_slot_live_until_the_group_is_stopped(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'orphan': True}})
        self.apply('--worker-timeout', '3')
        _, first = self.wait(1.5)
        self.assertEqual(first['outcome'], 'TIMEOUT')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'running')
        self.assertTrue(state.worker_live(slot))
        _, again = self.apply()
        self.assertEqual(again['dispatched'], [])  # no second writer beside the orphan
        _, stopped = self.wait(20)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'interrupted')
        self.assertFalse(state.group_alive(slot['worker']['pid']))
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 1)

    def test_dispatch_interrupted_before_its_slot_adopts_the_recorded_worktree(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.1}})
        with patch.object(state, 'create_slot', side_effect=ValueError('lost lease')):
            code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'))
        self.assertTrue((self.repo / '.worktrees/autowork-A').is_dir())
        _, result = self.apply()
        self.assertEqual([(s['task'], s['attempt']) for s in result['dispatched']], [('A', 1)])
        self.assertEqual(result['dispatched'][0]['worktree'], str(self.repo / '.worktrees/autowork-A'))

    def test_launch_failure_is_held_with_its_cause_without_a_retry(self):
        self.write_todo(task('A', 'a.txt'))
        code, result = self.run_cli('--apply', '--parallel', '--worker-command', json.dumps([str(self.root / 'missing')]),
                                    worker=False)
        self.assertEqual(result['dispatched'], [])
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('held', 1))
        self.assertIn('worker launch failed', slot['reason'])

    def test_malformed_queue_is_reported_not_treated_as_idle(self):
        record = self.repo / 'tasks/items/A.md'
        record.write_text(record.read_text().replace('rank = 1000', 'rank = ['))
        self.commit_if_changed('a malformed record')
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'))
        self.assertRegex(result['reason'], r'tasks/items/A.md:\d+: malformed TOML')

    def test_sequential_apply_is_unchanged_by_parallel_support(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = execution.main([str(self.repo), '--apply', '--owner-pid', str(self.owner)])
        result = json.loads(out.getvalue())
        self.assertEqual((code, result['outcome'], result['task']['id']), (0, 'EXECUTE', 'A'))
        self.assertFalse((self.common / 'coordinator.json').exists())
        self.assertFalse((self.common / 'journal.jsonl').exists())

    def test_parallel_needs_owner_and_valid_limits(self):
        for argv in ([str(self.repo), '--apply', '--parallel'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--apply', '--parallel', '5'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--apply', '--parallel', '3',
                      '--max-workers', '17'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--parallel', '--wait']):
            out = io.StringIO()
            with self.subTest(argv=argv[1:]), contextlib.redirect_stdout(out):
                self.assertEqual(execution.main(argv), 1)
            self.assertEqual(json.loads(out.getvalue())['outcome'], 'ACTION_REQUIRED')
        code, result = self.apply('5', '--max-workers', '6')
        self.assertEqual((code, result['max_workers']), (0, 5))


def contract(tid, touches):
    return {'id': tid, 'fields': {'Touches': touches, 'Status': 'open', 'Dependencies': 'None.'}}


class DrainClockTests(unittest.TestCase):
    def test_the_drain_clock_counts_only_waiting_as_a_task_that_must_run_alone(self):
        with tempfile.TemporaryDirectory() as folder:
            common = Path(folder)
            alone = {'id': 'X', 'reason': 'live/exclusive resource; must run alone (beside RUN)'}
            events = [(100, [{'id': 'X', 'reason': 'dependency: Y'}, {'id': 'B', 'reason': 'dependency: Y'}]),
                      (200, [alone]), (300, [alone]), (400, [{'id': 'B', 'reason': 'x'}, alone])]
            (common / 'journal.jsonl').write_text(''.join(
                json.dumps({'timestamp': t, 'event': 'dispatch_observed', 'waiting': w}) + '\n' for t, w in events))
            self.assertEqual(dispatch.waiting_streaks(common, now=1000), {'X': 800})
            with open(common / 'journal.jsonl', 'a') as journal:  # it ran: the streak ends
                journal.write(json.dumps({'timestamp': 500, 'event': 'dispatch_observed', 'waiting': []}) + '\n')
            self.assertEqual(dispatch.waiting_streaks(common, now=1000), {})
        self.assertEqual(dispatch.drain_after({'PI_AUTOWORK_DRAIN_AFTER': '60'}), 60)

    def test_the_drain_clock_survives_a_change_of_wait_reason(self):
        """The split task's reason alternated between running alone and a shared file with an
        unlanded commit; each switch restarted its clock and it never drained the pool."""
        with tempfile.TemporaryDirectory() as folder:
            common = Path(folder)
            alone = {'id': 'X', 'reason': 'live/exclusive resource; must run alone (beside RUN)'}
            shared = {'id': 'X', 'reason': 'shares coordinator.py with T; starts after it lands'}
            events = [(100, []), (200, [alone]), (300, [shared]), (400, [alone]), (450, [shared])]  # the first line is skipped as possibly cut
            (common / 'journal.jsonl').write_text(''.join(
                json.dumps({'timestamp': t, 'event': 'dispatch_observed', 'waiting': w}) + '\n' for t, w in events))
            self.assertEqual(dispatch.waiting_streaks(common, now=1000), {'X': 800})
        self.assertEqual(dispatch.drain_after({}), 1800)


class RetiredTmpTests(unittest.TestCase):
    """Closed and set-aside tasks keep their evidence, not their temp files."""

    def test_retired_attempt_tmpdirs_go_and_held_ones_stay(self):
        with tempfile.TemporaryDirectory() as folder:
            common = Path(folder)
            def attempt(base, n):
                tmp = base / f'attempt-{n}' / 'tmp'
                (tmp / 'sdk').mkdir(parents=True)
                (tmp.parent / 'report.json').write_text('{}')
                return tmp
            closed = [attempt(common / 'slot-data' / 'C', n) for n in (1, 2)]
            held = attempt(common / 'slot-data' / 'H', 1)
            history = common / 'slot-history' / 'S' / '1'
            aside = attempt(history / 'slot-data', 1)
            history.joinpath('slot.json').write_text(json.dumps({'task_id': 'S', 'attempt': 1, 'state': 'held'}))
            dispatch.sweep_retired_tmp(common, [{'task_id': 'C', 'attempt': 2, 'state': 'closed'},
                                                {'task_id': 'H', 'attempt': 1, 'state': 'held'}])
            self.assertEqual([p.exists() for p in (*closed, aside)], [False, False, False])
            self.assertTrue((closed[0].parent / 'report.json').exists())  # evidence stays
            self.assertTrue((held / 'sdk').exists())  # a held commit's review still uses it

    def test_a_read_only_module_cache_in_a_tmpdir_is_removed(self):
        """Go makes its module cache read-only; removing such a $TMPDIR stopped the engine."""
        with tempfile.TemporaryDirectory() as folder:
            tmp = Path(folder) / 'tmp'
            module = tmp / 'go/pkg/mod/golang.org/x/net@v0.23.0'
            module.mkdir(parents=True)
            (module / 'go.mod').write_text('module golang.org/x/net\n')
            for path in (module / 'go.mod', module, module.parent):
                path.chmod(0o444 if path.is_file() else 0o555)
            dispatch.remove_tree(tmp)
            self.assertFalse(tmp.exists())

    def test_a_live_worker_keeps_its_tmpdir(self):
        with tempfile.TemporaryDirectory() as folder:
            common = Path(folder)
            tmp = common / 'slot-data' / 'C' / 'attempt-1' / 'tmp'
            tmp.mkdir(parents=True)
            with patch.object(state, 'worker_live', lambda slot: True):
                dispatch.sweep_retired_tmp(common, [{'task_id': 'C', 'attempt': 1, 'state': 'closed'}])
            self.assertTrue(tmp.exists())


class AdmitTests(unittest.TestCase):
    """TOOLSET-157-cd: admission and integration agree about interrupted slots."""

    def admit(self, candidates, running=(), restartable=(), occupying=(), parked=()):
        return dispatch.admit(list(candidates), list(running), {t: {} for t in restartable},
                              [{'task_id': t} for t in occupying], everything=list(candidates) + list(running)
                              + list(parked), parked=list(parked), protected=None)

    def test_an_interrupted_candidate_resumes_first_beside_cold_overlap(self):
        """Resume priority is preserved without holding a two-task file overlap."""
        fresh, interrupted = contract('FRESH', 'lib/x.dart'), contract('OLD', 'lib/x.dart, test/x_test.dart')
        result = self.admit([fresh, interrupted], restartable={'OLD'}, occupying={'OLD'})
        self.assertEqual([t['id'] for t in result['dispatch']], ['OLD', 'FRESH'])
        self.assertEqual(result['waiting'], [])

    def test_a_commit_held_for_overlap_stops_nothing_but_its_dependents(self):
        held, interrupted = contract('HELD', 'lib/x.dart'), contract('OLD', 'lib/x.dart')
        fresh, other = contract('FRESH', 'lib/y.dart'), contract('DEP', 'z.py')
        other['fields']['Dependencies'] = 'HELD.'
        result = self.admit([interrupted, fresh, other], restartable={'OLD'}, occupying={'OLD', 'HELD'},
                            parked=[held])
        self.assertEqual([t['id'] for t in result['dispatch']], ['OLD', 'FRESH'])
        self.assertEqual(result['waiting'], [{'id': 'DEP', 'reason': 'dependency: held HELD', 'blocked_by': ['HELD']}])

    def test_only_a_commit_held_for_overlap_counts_as_overlap_held(self):
        self.assertTrue(state.overlap_held({'state': 'held', 'cause': 'overlap'}))
        for slot in ({'state': 'held', 'cause': 'scope'}, {'state': 'reported', 'cause': 'overlap'}):
            self.assertFalse(state.overlap_held(slot))


if __name__ == '__main__':
    unittest.main()
