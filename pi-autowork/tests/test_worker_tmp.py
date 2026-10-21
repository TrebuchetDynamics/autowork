"""The reviewer finds what the worker provisioned under its own $TMPDIR."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, main_check, worker  # noqa: E402


def setUpModule():
    """Reviews in these tests keep their scratch in a temporary folder, never the host's /var/tmp."""
    global _root, _environment
    _root = tempfile.TemporaryDirectory()
    _environment = patch.dict(os.environ, PI_AUTOWORK_REVIEW_ROOT=_root.name, PI_AUTOWORK_CHECK_ROOT=_root.name)
    _environment.start()


def tearDownModule():
    _environment.stop()
    _root.cleanup()


class WorkerTmpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.execution = self.repo / '.git' / 'autowork-execution'
        (self.execution / 'slots').mkdir(parents=True)

    def slot(self, **fields):
        (self.execution / 'slots' / 'T-1.json').write_text(json.dumps({'task_id': 'T-1', 'attempt': 2, **fields}))

    def test_full_suites_share_host_slots_without_spending_their_timeout_waiting(self):
        """A competing runner must wait, survive its outer timeout, and recover a killed holder."""
        component = str(Path(worker.__file__).resolve().parents[1])
        engine = str(Path(__file__).resolve().parents[2] / 'pi-autowork/engine')
        with patch.dict(os.environ, PI_AUTOWORK_CHECK_ROOT=self.temp.name):
            for slots, killed in [('1', False), ('1', True), ('0', False)]:
                with self.subTest(slots=slots, killed=killed):
                    root = self.repo / f'case-{slots}-{killed}'
                    root.mkdir()
                    self.slot(state='integrating')
                    env = dict(os.environ, PI_AUTOWORK_CHECK_SLOTS=slots)
                    script = ('import sys,json; from pathlib import Path; '
                              f'sys.path[:0] = {[component, engine]!r}; '
                              'from pi_autowork import worker; import task_execution as execution; ')
                    hold_command = ('echo $$ > holder.pid; exec sleep 30' if killed else
                                    'sleep 30 & echo $! > daemon.pid; echo $$ > holder.pid; wait')
                    holder = subprocess.Popen([sys.executable, '-c', script +
                        f'worker.run_suite({hold_command!r}, {str(root)!r}, 40, '
                        f'Path({str(root / "holder.log")!r}))'], env=env)
                    contender = None
                    try:
                        deadline = time.monotonic() + 10
                        while not (root / 'holder.pid').exists():
                            self.assertIsNone(holder.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        command = [sys.executable, '-c', script +
                            f'r = worker.run_suite("sleep .1; touch ran", {str(root)!r}, .5, '
                            f'Path({str(root / "full-check/second.log")!r}), '
                            f'Path({str(root / "full-check/T-1.status.json")!r})); sys.exit(r["code"])']
                        contender = subprocess.Popen([sys.executable, '-c', script +
                            f'r = execution.bounded_command({command!r}, Path({str(root)!r}), '
                            f'Path({str(root)!r}), "T", .6, check_slot_wait=True); '
                            f'Path({str(root / "result.json")!r}).write_text(json.dumps(r))'], env=env)
                        progress = root / 'full-check/T-1.status.json'
                        deadline = time.monotonic() + 10
                        while not progress.exists() and not (root / 'result.json').exists():
                            self.assertIsNone(contender.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        if slots == '1':
                            self.assertEqual(json.loads(progress.read_text())['ahead'], 1)
                            runner = fleet_view.Runner('fixture', repo=str(self.repo), state_dir=str(root))
                            lane = fleet_view.lanes(runner)[0]
                            self.assertEqual((lane.phase, lane.detail), ('waiting for a check slot', '1 ahead'))
                            self.assertEqual(fleet_view.doing(lane), 'waiting for a check slot, 1 ahead')
                            lane.activity_age = 600
                            self.assertEqual(fleet_view.quiet(lane), '')
                            time.sleep(.8)  # longer than both execution budgets
                            self.assertIsNone(contender.poll())
                            self.assertFalse((root / 'ran').exists())
                        else:
                            self.assertEqual(contender.wait(timeout=10), 0)
                            self.assertTrue((root / 'ran').exists())  # no slot even while holder runs
                        if killed:
                            os.kill(int((root / 'holder.pid').read_text()), signal.SIGKILL)
                        else:
                            os.kill(int((root / 'holder.pid').read_text()), signal.SIGTERM)
                        self.assertEqual(holder.wait(timeout=10), 0)
                        self.assertEqual(contender.wait(timeout=10), 0)
                        result = json.loads((root / 'result.json').read_text())
                        self.assertEqual(result['outcome'], 'EXECUTED')
                        self.assertTrue((root / 'ran').exists())
                    finally:
                        for name in ('holder.pid', 'daemon.pid'):
                            if (root / name).exists():
                                try:
                                    os.kill(int((root / name).read_text()), signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        for process in (holder, contender):
                            if process is not None and process.poll() is None:
                                process.kill()
                                process.wait()

    def test_the_gate_runs_once_per_merged_tree_and_the_reviewer_is_told_its_result(self):
        """TOOLSET-227-a8: one candidate's full suite ran four or five times."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'a.txt').write_text('base\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        (self.repo / 'a.txt').write_text('merged\n')
        git('commit', '-qam', 'merged')
        runs = Path(self.temp.name) / 'runs'
        state = Path(self.temp.name) / 'state'
        command = f'echo ran >> {runs}; printf "Ran 1 test in 0.1s\\n\\nOK\\n"'
        os.environ['PI_AUTOWORK_VALIDATE'] = command
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_VALIDATE', None)
        for _ in range(2):  # a re-review of the same tree, as after a reviewer change
            self.assertEqual(worker.full_suite_gate(state, 'T-1', str(self.repo)), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 1)
        note = worker.gate_note(state, 'T-1', str(self.repo))
        self.assertIn(f'`{command}`', note)
        self.assertIn('it passed', note)
        self.assertIn('all-green', note)
        self.assertIn(git('rev-parse', 'HEAD^{tree}').stdout.strip(), note)
        self.assertIn('Do not run the full check again', note)
        (self.repo / 'a.txt').write_text('changed\n')  # a new tree runs it again
        git('commit', '-qam', 'changed')
        worker.full_suite_gate(state, 'T-1', str(self.repo))
        self.assertEqual(runs.read_text().count('ran'), 2)
        os.environ['PI_AUTOWORK_VALIDATE'] = command + '; true'  # the command is part of the key
        self.assertIn('unavailable', worker.gate_note(state, 'T-1', str(self.repo)))
        worker.full_suite_gate(state, 'T-1', str(self.repo))
        self.assertEqual(runs.read_text().count('ran'), 3)
        os.environ.pop('PI_AUTOWORK_VALIDATE')
        self.assertEqual(worker.gate_note(state, 'T-1', str(self.repo)), '')

    def elsewhere(self):
        """A temporary directory beside the fixture repository, so the repository stays clean."""
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        return Path(folder.name)

    def committed_repo(self):
        """The fixture repository with a base commit and a merged commit, as the gate sees it."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'a.txt').write_text('base\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        (self.repo / 'a.txt').write_text('merged\n')
        git('commit', '-qam', 'merged')
        return git

    def test_a_directory_the_check_gave_up_on_is_never_excused_by_the_base(self):
        """check.py reports a directory it timed out as a failure, so a loaded host timed the same
        directory out on the base, nothing stayed new enough to reject, and the gate passed a
        tree whose full check never ran that directory."""
        self.committed_repo()
        state, runs = self.elsewhere() / 'state', self.elsewhere() / 'runs'
        timed = f'{self.repo}/tests'
        command = f'echo run >> {runs}; echo "TIMEOUT: {timed} after 1800s"; exit 1'
        ok, reason = worker.run_gate(state, 'T-1', str(self.repo), command)
        self.assertFalse(ok, 'a directory that never completed passed the gate')
        self.assertIn('did not complete', reason)
        self.assertIn(timed, reason)
        self.assertEqual(runs.read_text().count('run'), 1,
                         'the base suite is not worth running: no verdict can use it')

    def test_the_base_suite_runs_in_a_short_directory_and_not_under_the_state_dir(self):
        """Under the state directory this worktree path reached 87 characters before the suite
        added its own, past the 108-byte AF_UNIX limit that already moved review scratch."""
        self.committed_repo()
        state, runs = self.elsewhere() / 'state', self.elsewhere() / 'runs'
        command = f'pwd >> {runs}; echo "FAIL: test_x (m.T.test_x)"; exit 1'
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), command), (True, ''))
        seen = runs.read_text().split()
        self.assertEqual(len(seen), 2, seen)  # the merged tree, then the base
        self.assertEqual(Path(seen[0]).resolve(), Path(self.repo).resolve())
        base = Path(seen[1])
        self.assertEqual(base.parent.parent, Path(os.environ['PI_AUTOWORK_REVIEW_ROOT']))
        self.assertFalse(base.exists(), 'the base worktree goes with the holder it was made in')
        self.assertFalse((state / 'review-tmp').exists(), 'the state directory is not a suite path')

    def test_a_base_revision_that_cannot_be_resolved_is_a_hold_not_a_crash(self):
        """`base_rev or git(...HEAD^1)` yields None, and base_tree interpolated it into git."""
        self.committed_repo()
        state = self.elsewhere() / 'state'
        command = 'echo "FAIL: test_x (m.T.test_x)"; exit 1'
        ok, reason = worker.run_gate(state, 'T-1', str(self.repo), command, 'deadbeefdeadbeefdeadbeef')
        self.assertFalse(ok)
        self.assertIn('no base to compare with', reason)
        self.assertRaises(ValueError, worker.base_result, state, str(self.repo), command, '', 10)

    def test_a_cached_verdict_explains_its_producing_evidence_not_the_current_tasks_log(self):
        """Missing or stale task logs must not turn exception acceptance into all-green."""
        (self.repo / 'test_mod.py').write_text('import unittest\nclass T(unittest.TestCase):\n'
                                               '    def test_ok(self): pass\n'
                                               '    def test_red(self): self.fail()\n')
        git = self.committed_repo()
        tree = git('rev-parse', 'HEAD^{tree}').stdout.strip()
        for failures, kind, classification in (([], 'unittest', 'all-green'),
                                               ([], 'skipped', 'accepted with skipped tests'),
                                               ([], 'pytest', 'unavailable'), ([], 'mixed', 'unavailable'),
                                               ([], 'unknown', 'unavailable'),
                                               (['test_red'], 'unittest', 'baseline-equivalent'),
                                               (['test_ok'], 'unittest', 'isolated-rerun'),
                                               (['test_ok', 'test_red'], 'unittest', 'baseline-equivalent')):
            with self.subTest(failures=failures, kind=kind):
                state, runs = self.elsewhere() / 'state', self.elsewhere() / 'runs'
                lines = ['CHECK . (1 modules)'] + [f'FAIL: {f} (test_mod.T.{f})' for f in failures]
                lines += ['Ran 3 tests in 0.1s', '',
                          'FAILED (failures=1, skipped=1)' if failures else 'OK']
                if kind == 'skipped':
                    lines[-1] = 'OK (skipped=1)'
                elif kind in ('pytest', 'unknown'):
                    lines = ['1 passed, 1 skipped in 0.01s' if kind == 'pytest' else 'custom check completed']
                if kind == 'mixed':
                    lines += ['1 passed, 1 skipped in 0.01s']
                if failures:
                    lines += ['RESOURCE_GATE_SKIP: busy host']
                command = (f'echo ran >> {runs}; printf "%s\\n" ' +
                           ' '.join(repr(line) for line in lines) + f'; exit {int(bool(failures))}')
                with patch.dict(os.environ, PI_AUTOWORK_VALIDATE=command):
                    self.assertEqual(worker.full_suite_gate(state, 'T-1', str(self.repo)), (True, ''))
                    initial = worker.gate_note(state, 'T-1', str(self.repo))
                    self.assertIn(classification, initial)
                    self.assertEqual(worker.full_suite_gate(state, 'T-2', str(self.repo)), (True, ''))
                    log = worker.gate_log(state, 'T-2')
                    self.assertEqual(log.read_text(), worker.gate_log(state, 'T-1').read_text())
                    log.unlink()  # cross-task explanation needs no task-local log
                    worker.gate_log(state, 'T-1').write_text('OK\n')  # overwritten by a later task run
                    note = worker.gate_note(state, 'T-2', str(self.repo))
                    self.assertEqual(note, initial)
                    self.assertIn('T-1', note)
                    self.assertIn(tree, note)
                    self.assertIn(f'`{command}`', note)
                    self.assertIn('Do not run the full check again', note)
                    for failure in failures:
                        self.assertIn(f'test_mod.T.{failure}', note)
                    if failures:
                        self.assertNotIn('all-green', note)
                        self.assertIn('unittest skips: 1', note)
                        self.assertIn('resource-gate skips: 1', note)
                    if len(failures) == 2:
                        self.assertIn('isolated-rerun', note)
                    count = runs.read_text().count('ran')
                    self.assertEqual(count, 2 if 'test_red' in failures else 1)
                    cache = state / 'full-check' / f'tree-{tree}.json'
                    record = json.loads(cache.read_text())
                    evidence = Path(record['log'])
                    original = evidence.read_text()
                    for damage in ('absent', 'empty', 'unreadable', 'stale', 'foreign',
                                   'tree', 'command', 'legacy', 'no-record'):
                        with self.subTest(damage=damage):
                            value = dict(record)
                            if damage == 'absent':
                                evidence.unlink()
                            elif damage == 'empty':
                                evidence.write_text('')
                            elif damage == 'unreadable':
                                evidence.unlink()
                                evidence.mkdir()  # deterministic even when tests run as root
                            elif damage == 'stale':
                                evidence.write_text('Ran 1 test in 0.1s\n\nOK\n')
                            elif damage == 'foreign':
                                value['log'] = str(runs)
                            elif damage in ('tree', 'command'):
                                value[damage] = 'different'
                            elif damage == 'legacy':
                                value = {k: record[k] for k in ('command', 'ok', 'reason', 'task', 'log')}
                            cache.write_text(json.dumps(value))
                            if damage == 'no-record':
                                cache.unlink()
                            unavailable = worker.gate_note(state, 'T-2', str(self.repo))
                            self.assertIn('unavailable', unavailable)
                            self.assertNotIn('all-green', unavailable)
                            self.assertNotIn('it passed', unavailable)
                            if damage == 'legacy':
                                self.assertEqual(worker.full_suite_gate(state, 'T-2', str(self.repo)), (True, ''))
                                self.assertNotIn('already ran', unavailable)
                            if evidence.is_dir():
                                evidence.rmdir()
                            evidence.write_text(original)
                            cache.write_text(json.dumps(record))
                    self.assertEqual(runs.read_text().count('ran'), count, 'explanation ran another check')

    def test_an_empty_verify_timeout_keeps_the_documented_default(self):
        """A service config that sets the name to nothing became `timeout ''`, and float('')
        raised inside review_limit."""
        state = self.elsewhere() / 'state'
        head = worker.git(str(self.repo), 'rev-parse', 'HEAD')
        with patch.dict(os.environ, PI_AUTOWORK_VERIFY_TIMEOUT=''), \
                patch.object(worker.pi_runtime, 'job',
                             return_value={'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass'}) as job:
            self.assertEqual(worker.review(state, 'T-1', str(self.repo), head, ''), 0)
        self.assertEqual(job.call_args.args[6], '1800')

    def test_a_review_without_a_verdict_says_why_for_the_hold(self):
        """A reviewer that ran out of time left only "no verdict": held as a validation failure,
        the task was reimplemented by a fresh worker instead of reviewed again with more time."""
        import contextlib
        import io
        state = self.elsewhere() / 'state'
        head = worker.git(str(self.repo), 'rev-parse', 'HEAD')
        for result, reason in (({'ok': False, 'text': '', 'why': 'timeout'}, 'the review ran out of time after 1800 s'),
                               ({'ok': False, 'text': '', 'why': 'no_model'}, 'the reviewer did not finish (no_model)'),
                               ({'ok': True, 'text': 'Checked the files.'}, 'the reviewer gave no verdict')):
            with self.subTest(reason=reason), patch.dict(os.environ, PI_AUTOWORK_VERIFY_TIMEOUT='1800'), \
                    patch.object(worker.pi_runtime, 'job', return_value=result), \
                    contextlib.redirect_stdout(io.StringIO()) as out, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(worker.review(state, 'T-1', str(self.repo), head, ''), 1)
            self.assertIn(f'AUTOWORK_HOLD_REASON: {reason}\n', out.getvalue())

    def test_an_empty_task_timeout_keeps_the_documented_default(self):
        state = self.elsewhere() / 'state'
        prompt, report = state / 'prompt.md', state / 'attempt-1' / 'report.json'
        report.parent.mkdir(parents=True)
        prompt.write_text('Task: T-1\n')
        guard = ('GIT_CONFIG_COUNT', 'GIT_CONFIG_KEY_0', 'GIT_CONFIG_VALUE_0',
                 'GIT_CONFIG_KEY_1', 'GIT_CONFIG_VALUE_1')
        self.addCleanup(lambda: [os.environ.pop(name, None) for name in guard])
        with patch.dict(os.environ, PI_AUTOWORK_TASK_TIMEOUT=''), \
                patch.object(worker.pi_runtime, 'job', return_value={'ok': True, 'text': ''}) as job:
            worker.main(['--worker', str(state), str(self.repo), str(prompt), str(report)])
        self.assertEqual(job.call_args.args[6], '5400')

    def test_base_cache_reuses_only_planning_changes_under_the_same_command(self):
        """Planning commits must not repeat a base run; code and command changes must."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True,
                                        text=True).stdout.strip()
        (self.repo / 'source.py').write_text('base\n')
        (self.repo / 'tasks/items').mkdir(parents=True)
        (self.repo / 'tasks/items/T.md').write_text('base plan\n')
        (self.repo / 'BLOCKERS.md').write_text('base questions\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        base_rev = git('rev-parse', 'HEAD')
        state, runs = self.repo / '.git' / 'state', self.repo / '.git' / 'runs'
        command = f'echo ran >> {runs}'
        worker.base_result(state, self.repo, command, base_rev, 10)
        for path, expected_runs in (('BLOCKERS.md', 1), ('tasks/items/T.md', 1), ('TODO.archive.md', 1),
                                    ('todo.archive.md', 1), ('tasks/goals/G.md', 1), ('docs/nested/plan.md', 1),
                                    ('source.py', 2)):
            with self.subTest(path=path):
                target = self.repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text('changed\n')
                git('add', '-A')
                git('commit', '-qm', path)
                rev = git('rev-parse', 'HEAD')
                value = worker.base_result(state, self.repo, command, rev, 10)
                self.assertEqual(runs.read_text().count('ran'), expected_runs)
                self.assertEqual(value['code'], 0)
                self.assertEqual(value['rev'], base_rev if expected_runs == 1 else rev)
                saved = json.loads((state / 'full-check' / f'base-{rev}.json').read_text())
                self.assertEqual(saved['tree'], value['tree'])
        worker.base_result(state, self.repo, command + '; true', rev, 10)
        self.assertEqual(runs.read_text().count('ran'), 3)

    def test_failures_that_pass_alone_need_no_base_suite(self):
        """A base suite as long as the merged one ran on nearly every review, even when each failure
        passed when rerun alone; a failure that stays red still gets the base comparison."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'test_mod.py').write_text('import unittest\nclass T(unittest.TestCase):\n'
                                               '    def test_ok(self): pass\n'
                                               '    def test_red(self): self.fail()\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        runs = Path(self.temp.name) / 'runs'
        os.environ['PI_AUTOWORK_VALIDATE'] = f'echo ran >> {runs}; echo "CHECK . (1 modules)"; echo "FAIL: test_ok (test_mod.T.test_ok)"; printf "Ran 2 tests in 0.1s\\n\\nFAILED (failures=1)\\n"; exit 1'
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_VALIDATE', None)
        state = Path(self.temp.name) / 'flaky'
        (self.repo / 'a.txt').write_text('merged\n')
        git('add', '-A')
        git('commit', '-qm', 'merged')
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), os.environ['PI_AUTOWORK_VALIDATE']), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 1)  # the merged run only
        os.environ['PI_AUTOWORK_VALIDATE'] = f'echo ran >> {runs}; echo "CHECK . (1 modules)"; echo "FAIL: test_red (test_mod.T.test_red)"; printf "Ran 2 tests in 0.1s\\n\\nFAILED (failures=1)\\n"; exit 1'
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), os.environ['PI_AUTOWORK_VALIDATE']), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 3)  # red alone too: the base, red as well, decides

    def test_a_failure_from_a_loaded_host_is_rerun_alone_once_main_check_is_done(self):
        """Rerun side by side beside main's full suite, the engine tests timed out and held candidates
        whose trees pass them: what stays red is rerun one at a time once main's check has ended."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        busy = Path(self.temp.name) / 'busy'
        busy.write_text('main check running\n')
        (self.repo / 'test_mod.py').write_text('import unittest\nfrom pathlib import Path\n'
                                               'class T(unittest.TestCase):\n'
                                               f'    def test_loaded(self): self.assertFalse(Path({str(busy)!r}).exists())\n')
        git('add', '-A')
        git('commit', '-qm', 'merged')
        runs = Path(self.temp.name) / 'runs'
        command = (f'echo ran >> {runs}; echo "CHECK . (1 modules)"; echo "FAIL: test_loaded (test_mod.T.test_loaded)"; '
                   'printf "Ran 1 test in 0.1s\\n\\nFAILED (failures=1)\\n"; exit 1')
        state = Path(self.temp.name) / 'loaded'
        state.mkdir()
        main = subprocess.Popen(['sleep', '60'])
        self.addCleanup(lambda: (main.kill(), main.wait()))
        main_check.write(state, {'state': 'running', 'pid': main.pid, 'start_time': main_check.start_time(main.pid)})

        def main_check_ends():
            time.sleep(3)  # after the side-by-side reruns, which still see the load
            busy.unlink()
            main.kill()
            main.wait()
        ender = threading.Thread(target=main_check_ends)
        ender.start()
        self.addCleanup(ender.join)
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), command), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 1)  # no base suite was needed
        self.assertEqual(json.loads(worker.gate_log(state, 'T-1').with_suffix('.reruns.json').read_text())['flaky'], [])

    def test_the_gate_runs_the_full_check_with_a_private_tmpdir(self):
        """The runner has no $TMPDIR: a check that requires one crashed on every candidate and its base."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'a.txt').write_text('merged\n')
        git('add', '-A')
        git('commit', '-qm', 'merged')
        root = Path(self.temp.name) / 'review-root'
        root.mkdir()
        env = {k: v for k, v in os.environ.items() if k != 'TMPDIR'}
        env.update(PI_AUTOWORK_VALIDATE=': "${TMPDIR:?TMPDIR must be set}"; test -d "$TMPDIR"',
                   PI_AUTOWORK_REVIEW='0', PI_AUTOWORK_REVIEW_ROOT=str(root))
        cwd = os.getcwd()
        self.addCleanup(os.chdir, cwd)
        os.chdir(self.repo)
        with patch.dict(os.environ, env, clear=True):
            self.assertEqual(worker.verify(Path(self.temp.name) / 'state', 'T-1'), 0)
        self.assertEqual(list(root.iterdir()), [])  # and the scratch is gone

    def test_a_batch_verdict_is_used_once_for_its_tree_or_one_differing_only_in_planning_files(self):
        """TOOLSET-258-07: the engine lands a batched candidate on its recorded verdict."""
        git = lambda *a, cwd=self.repo: subprocess.run(['git', '-C', str(cwd), '-c', 'user.email=t@example.invalid',
                                                        '-c', 'user.name=T', *a], check=True, capture_output=True,
                                                       text=True).stdout.strip()
        (self.repo / 'a.txt').write_text('base\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        git('checkout', '-qb', 'task')
        (self.repo / 'a.txt').write_text('task\n')
        git('commit', '-qam', 'task')
        commit = git('rev-parse', 'HEAD')
        git('checkout', '-q', '-')
        git('merge', '--no-ff', '--no-edit', '-q', commit)
        state = Path(self.temp.name) / 'state'
        record = worker.batch_record(state, 'T-1')
        record.parent.mkdir(parents=True)
        write = lambda tree: record.write_text(json.dumps({'tree': tree, 'commit': commit, 'ok': True, 'reason': '', 'at': 0}))
        merged_tree = git('rev-parse', 'HEAD^{tree}')
        write(merged_tree)
        self.assertEqual(worker.batched_verdict(state, 'T-1', str(self.repo)), (True, ''))
        self.assertIsNone(worker.batched_verdict(state, 'T-1', str(self.repo)))  # used once
        (self.repo / 'BLOCKERS.md').write_text('planning\n')  # the session took a planning commit since
        git('add', 'BLOCKERS.md')
        git('commit', '-qm', 'questions')
        write(merged_tree)
        self.assertEqual(worker.batched_verdict(state, 'T-1', str(self.repo)), None)  # HEAD is not the merge any more
        git('reset', '-q', '--hard', 'HEAD~1')
        (self.repo / 'BLOCKERS.md').write_text('planning\n')
        git('add', 'BLOCKERS.md')
        git('commit', '-q', '--amend', '--no-edit')  # same merge, plus a planning file
        write(merged_tree)
        self.assertEqual(worker.batched_verdict(state, 'T-1', str(self.repo)), (True, ''))
        (self.repo / 'b.py').write_text('code\n')
        git('add', 'b.py')
        git('commit', '-q', '--amend', '--no-edit')  # same merge, plus code: not the tree that was checked
        write(merged_tree)
        self.assertIsNone(worker.batched_verdict(state, 'T-1', str(self.repo)))

    def test_a_suite_that_stops_partway_is_never_a_pass_and_a_crash_beside_a_red_base_is_its_own(self):
        """A killed suite whose named failure passed alone landed the unrun rest; a crash beside a
        main with ordinary failures was called the host's and provisioned for."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'test_mod.py').write_text('import unittest\nclass T(unittest.TestCase):\n'
                                               '    def test_ok(self): pass\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        (self.repo / 'a.txt').write_text('merged\n')
        git('add', '-A')
        git('commit', '-qm', 'merged')
        killed = 'echo "FAIL: test_ok (test_mod.T.test_ok)"; exit 137'  # no summary: it never finished
        ok, reason = worker.run_gate(Path(self.temp.name) / 'killed', 'T-1', str(self.repo), killed)
        self.assertEqual((ok, reason[:44]), (False, 'the full check stopped before its results we'))
        merged = self.root_head = subprocess.run(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'],
                                                 capture_output=True, text=True).stdout.strip()
        crash = (f'if [ "$(git rev-parse HEAD)" = {merged} ]; then echo "Segmentation fault"; exit 139; fi; '
                 'echo "FAIL: test_x (test_mod.T.test_x)"; printf \'Ran 1 test in 0.1s\\n\\nFAILED (failures=1)\\n\'; exit 1')
        ok, reason = worker.run_gate(Path(self.temp.name) / 'crash', 'T-1', str(self.repo), crash)
        self.assertFalse(ok)
        self.assertIn('where the base runs to its test results', reason)
        self.assertFalse(worker.environment_marker(Path(self.temp.name) / 'crash', 'T-1').exists())

    def test_the_worker_tmpdir_of_the_slot_attempt_is_found(self):
        self.slot()
        tmp = self.execution / 'slot-data' / 'T-1' / 'attempt-2' / 'tmp'
        (tmp / 'flutter-sdk').mkdir(parents=True)
        self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), tmp)

    def test_a_durable_allocation_is_authoritative_for_a_readopted_worker(self):
        self.slot(data_attempt=1)
        task_data = self.execution / 'slot-data' / 'T-1'
        (task_data / 'attempt-1' / 'tmp' / 'legacy-sdk').mkdir(parents=True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'allocated'
            record = task_data / 'tmp.json'
            record.write_text(json.dumps({'path': str(path), 'slot': 3}))
            for contents, expected in (('missing', None), ('empty', None), ('sdk', path)):
                with self.subTest(contents=contents):
                    if contents != 'missing':
                        path.mkdir(exist_ok=True)
                    if contents == 'sdk':
                        (path / 'sdk').mkdir()
                    self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), expected)

    def test_a_readopted_slot_uses_its_data_attempt(self):
        self.slot(data_attempt=1)
        tmp = self.execution / 'slot-data' / 'T-1' / 'attempt-1' / 'tmp'
        (tmp / 'sdk').mkdir(parents=True)
        self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), tmp)

    def test_nothing_is_offered_without_a_slot_or_provisioned_files(self):
        self.assertIsNone(worker.worker_tmp(str(self.repo), 'T-1'))
        self.slot()
        (self.execution / 'slot-data' / 'T-1' / 'attempt-2' / 'tmp').mkdir(parents=True)
        self.assertIsNone(worker.worker_tmp(str(self.repo), 'T-1'))  # empty: nothing to point at


class ReviewScratchTests(unittest.TestCase):
    """Reviewers copied whole repositories into RAM-backed /tmp and left them there."""

    def test_a_review_holds_a_port_block_of_its_own_until_it_ends(self):
        """A task whose checks bind $AUTOWORK_PORT_BASE failed its review for want of it."""
        import fcntl
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
            state.mkdir()
            dispatch, _, _ = worker.engine_modules()
            seen = {}

            def held(base):
                fd = os.open(dispatch.port_lease_dir() / str((base - 20100) // 100 + 1), os.O_RDWR)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    fcntl.flock(fd, fcntl.LOCK_UN)
                    return False
                except BlockingIOError:
                    return True
                finally:
                    os.close(fd)

            def job(settings, role, task, checkout, prompt, *rest):
                seen['base'] = int(os.environ['AUTOWORK_PORT_BASE'])
                seen['held'] = held(seen['base'])
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd = os.getcwd()
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []), \
                        patch.dict(os.environ, {'PI_AUTOWORK_REVIEW_ROOT': str(state)}):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
            self.assertTrue(seen['held'], 'the review ran without holding its port block')
            self.assertFalse(held(seen['base']), 'the block stayed leased after the review')

    def test_a_review_gets_its_own_tmpdir_which_is_removed_afterwards(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
            state.mkdir()
            seen = {}

            def job(settings, role, task, checkout, prompt, *rest):
                seen['tmp'] = Path(os.environ['TMPDIR'])
                seen['real'] = seen['tmp'].resolve()
                seen['prompt'] = prompt
                (seen['tmp'] / 'copy.txt').write_text('scratch')
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []), \
                        patch.dict(os.environ, {'PI_AUTOWORK_REVIEW_ROOT': str(state)}):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp
            # A real directory, not a link: code that resolves links must get the same short path,
            # so a socket under it fits the 108-byte AF_UNIX limit.
            self.assertEqual(seen['real'], seen['tmp'].absolute())
            self.assertEqual(seen['tmp'].parent, state)
            self.assertTrue(seen['tmp'].name.startswith(f'aw-r-{os.getpid()}-'), seen['tmp'])
            self.assertFalse(seen['tmp'].exists())
            self.assertIn('never directly under /tmp', seen['prompt'])
            cache = repo / '.git' / 'autowork-execution' / 'cache'
            self.assertIn(f'are in {cache} (AUTOWORK_CACHE', seen['prompt'])
            self.assertTrue(cache.is_dir())

    def test_a_review_unregisters_only_its_own_scratch_worktrees(self):
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            git = lambda *argv: subprocess.run(['git', '-C', str(repo), *argv], check=True,
                                               capture_output=True, text=True).stdout
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'base')
            state.mkdir()
            # Someone else's registration whose directory is gone: the runner restores such
            # worktrees, so a review must not prune it.
            other = Path(folder) / 'someone-else'
            git('worktree', 'add', '-q', '--detach', str(other), 'HEAD')
            shutil.rmtree(other)

            used = {}

            def job(settings, role, task, checkout, prompt, *rest):
                tmp = used['tmp'] = Path(os.environ['TMPDIR'])
                git('worktree', 'add', '-q', '--detach', str(tmp / 'copy'), 'HEAD')
                git('worktree', 'add', '-q', '--detach', str(tmp / 'gone'), 'HEAD')
                shutil.rmtree(tmp / 'gone')  # a reviewer that deleted its copy itself
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []), \
                        patch.dict(os.environ, {'PI_AUTOWORK_REVIEW_ROOT': str(state)}):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp
            registered = [Path(line[len('worktree '):]) for line in git('worktree', 'list', '--porcelain').splitlines()
                          if line.startswith('worktree ')]
            self.assertIn(other.resolve(), [p.resolve() for p in registered])
            # Only the review's own scratch counts: run inside a review, the test's own folder
            # lies under that review's `aw-r-` scratch too.
            scratch = used['tmp'].resolve()
            self.assertFalse([p for p in registered if p.resolve() == scratch or scratch in p.resolve().parents])


class DeadReviewScratchTests(unittest.TestCase):
    """A review killed at its timeout never runs its own cleanup."""

    def test_scratch_of_dead_reviews_goes_and_live_ones_stay(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, scratch = Path(folder) / 'repo', Path(folder) / 'review-tmp'
            git = lambda *argv: subprocess.run(['git', '-C', str(repo), *argv], check=True,
                                               capture_output=True, text=True).stdout
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'base')
            dead = subprocess.Popen(['true'])
            dead.wait()
            gone, live = scratch / f'aw-r-{dead.pid}-abc', scratch / f'aw-r-{os.getpid()}-def'
            for path in (gone, live):
                path.mkdir(parents=True)
            git('worktree', 'add', '-q', '--detach', str(gone / 'copy'), 'HEAD')
            worker.drop_dead_scratch(str(repo), scratch)
            self.assertFalse(gone.exists())
            self.assertTrue(live.exists())
            self.assertNotIn(str((gone / 'copy').resolve()), git('worktree', 'list', '--porcelain'))


class ReviewLimitTests(unittest.TestCase):
    """PI_AUTOWORK_VERIFY_TIMEOUT comes from a service settings file, so a name set to nothing
    must keep the documented limit: it reached float('') inside review_limit, which the run loop
    calls for every integration."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def limit(self, value):
        from pi_autowork.coordinator import Coordinator
        coordinator = Coordinator.__new__(Coordinator)
        coordinator.state, coordinator.timeout_limits = Path(self.temp.name), {}
        coordinator.verify_timeout = value
        return coordinator.review_limit()

    def test_a_misconfigured_review_limit_keeps_the_documented_default(self):
        for value in ('1800', '', 'nonsense'):
            with self.subTest(value=value):
                self.assertEqual(self.limit(value), 1800)

    def test_the_settings_read_keeps_the_default_for_a_name_set_to_nothing(self):
        from pi_autowork.coordinator import Coordinator
        cfg = dict(repo=self.temp.name, base='main', toolset=self.temp.name, toolset_rev='revision',
                   state=self.temp.name, mode='run', workers=1, interval='60', max_cycles='0', claim_idle='0')
        with patch.dict(os.environ, PI_AUTOWORK_VERIFY_TIMEOUT='', PI_AUTOWORK_TASK_TIMEOUT=''):
            coordinator = Coordinator(cfg)
        self.assertEqual((coordinator.verify_timeout, coordinator.task_timeout), ('1800', '5400'))
        self.assertEqual(coordinator.review_limit(), 1800)


class BatchFailureTests(unittest.TestCase):
    """A batch whose full check failed sends its candidates one at a time. That lived in memory and
    was keyed on the whole set, so a restart, or one more candidate, batched the same failing one again."""

    def coordinator(self, folder):
        from pi_autowork.coordinator import Coordinator
        coordinator = Coordinator.__new__(Coordinator)
        coordinator.state, coordinator.seen = Path(folder), {}
        coordinator.reexec_due = coordinator.batch_pending = lambda: False
        return coordinator

    def test_a_failed_batch_is_not_batched_again_after_a_restart_or_a_new_candidate(self):
        with tempfile.TemporaryDirectory() as folder:
            first = self.coordinator(folder)
            self.assertEqual(first.batch_due([('A', 'a1'), ('B', 'b1'), ('C', 'c1')]), ['A', 'B', 'C'])
            first.batch_done({'outcome': 'BATCH_GATE_FAILED', 'reason': 'new failures', 'tasks': ['A', 'B']})
            restarted = self.coordinator(folder)
            # C was past the batch size, never checked: it may still join a batch.
            self.assertEqual(restarted.batch_due([('A', 'a1'), ('B', 'b1'), ('C', 'c1'), ('D', 'd1')]), ['C', 'D'])
            # A new revision (the resolver merged it with the session) is a new candidate.
            self.assertEqual(self.coordinator(folder).batch_due([('A', 'a2'), ('B', 'b1')]), [])
            self.assertEqual(self.coordinator(folder).batch_due([('A', 'a2'), ('E', 'e1')]), ['A', 'E'])

    def test_a_failed_batch_of_four_or_more_is_split_in_halves_until_the_failing_one_is_alone(self):
        """23 commits waited: each failed batch of six sent all six to a review of their own."""
        reported = [(t, t.lower()) for t in 'ABCDEFG']
        with tempfile.TemporaryDirectory() as folder, patch('pi_autowork.coordinator.LOG'):
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('ABCDEFG'))
            runner.batch_done({'outcome': 'BATCH_GATE_FAILED', 'tasks': list('ABCDEF')})  # G was past the size
            self.assertEqual(self.coordinator(folder).batch_due(reported), list('ABC'))
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('DEF'))  # restarted between the halves
            runner.batch_done({'outcome': 'BATCH_GATE_FAILED', 'tasks': list('DEF')})  # three: one at a time
            landed = [r for r in reported if r[0] not in 'ABC']
            self.assertEqual(self.coordinator(folder).batch_due(landed), [])  # D, E and F alone; G waits for a pair
            # A half that shrinks to one candidate (the others landed) sends it alone too.
            Path(folder, 'batch-split.json').write_text(json.dumps([['G@g', 'H@h'], ['I@i', 'J@j']]))
            self.assertEqual(self.coordinator(folder).batch_due([('G', 'g'), ('I', 'i'), ('J', 'j')]), ['I', 'J'])
            self.assertIn('G@g', json.loads(Path(folder, 'batch-failed.json').read_text()))


    def test_failed_batch_commits_get_several_reviews_alone_between_two_batches(self):
        """One review alone per batch left five commits whose batch had failed waiting 6 to 23 hours."""
        reported = [(t, t.lower()) for t in 'ABCD']
        with tempfile.TemporaryDirectory() as folder, patch('pi_autowork.coordinator.LOG'), \
                patch.dict(os.environ, PI_AUTOWORK_SINGLES_PER_BATCH='2'):
            Path(folder, 'batch-failed.json').write_text(json.dumps(['A@a']))
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('BCD'))
            for extra in 'EF':  # new candidates arrive, yet two reviews alone come first
                reported.append((extra, extra.lower()))
                self.assertEqual(runner.batch_due(reported), [], extra)
                runner.single_started()
            reported.append(('G', 'g'))
            self.assertEqual(runner.batch_due(reported), list('BCDEFG'))  # their turns are used: a batch
            # With nothing whose batch failed waiting, turns left never hold a batch back.
            Path(folder, 'batch-failed.json').write_text('[]')
            reported.append(('H', 'h'))
            self.assertEqual(runner.batch_due(reported), list('ABCDEFGH'))

    def test_suspects_integrate_alone_and_the_rest_batch_again(self):
        """Halving cost a full check per round; the failing tests usually name the candidate."""
        reported = [(t, t.lower()) for t in 'ABCD']
        with tempfile.TemporaryDirectory() as folder, patch('pi_autowork.coordinator.LOG'):
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('ABCD'))
            runner.batch_done({'outcome': 'BATCH_GATE_FAILED', 'tasks': list('ABCD'), 'suspects': ['B']})
            self.assertFalse(Path(folder, 'batch-split.json').exists())
            self.assertEqual(json.loads(Path(folder, 'batch-failed.json').read_text()), ['B@b'])
            self.assertEqual(self.coordinator(folder).batch_due(reported), list('ACD'))
            # Every candidate a suspect tells nothing: halves, as before.
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('ACD'))
            runner.batch_done({'outcome': 'BATCH_GATE_FAILED', 'tasks': list('ACD'), 'suspects': list('ACD')})
            self.assertEqual(json.loads(Path(folder, 'batch-failed.json').read_text()), ['A@a', 'B@b', 'C@c', 'D@d'])
        # Suspects past half the batch: halves, not five reviews of their own.
        reported = [(t, t.lower()) for t in 'MNOPQR']
        with tempfile.TemporaryDirectory() as folder, patch('pi_autowork.coordinator.LOG'):
            runner = self.coordinator(folder)
            self.assertEqual(runner.batch_due(reported), list('MNOPQR'))
            runner.batch_done({'outcome': 'BATCH_GATE_FAILED', 'tasks': list('MNOPQR'), 'suspects': list('MNOPQ')})
            self.assertFalse(Path(folder, 'batch-failed.json').exists())
            self.assertEqual(json.loads(Path(folder, 'batch-split.json').read_text()),
                             [['M@m', 'N@n', 'O@o'], ['P@p', 'Q@q', 'R@r']])

    def test_the_failing_tests_point_at_the_candidates_whose_changes_they_import_or_read(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder, 'repo'), Path(folder, 'state')
            git = lambda *a: subprocess.run(['git', '-C', str(repo), *a], check=True, capture_output=True,
                                            text=True).stdout.strip()
            files = {'pkg/__init__.py': '', 'pkg/a.py': 'from . import helper\n', 'pkg/helper.py': 'X = 1\n',
                     'pkg/b.py': 'Y = 2\n', 'guide/GUIDE.md': 'text\n', 'tests/notes.md': 'n\n',
                     'tests/test_near.py': "ROOT.joinpath('notes.md')\n",
                     'tests/test_a.py': 'from pkg import a\n',
                     'tests/test_doc.py': "TEXT = open('guide/GUIDE.md').read()\n"}
            for name, text in files.items():
                (repo / name).parent.mkdir(parents=True, exist_ok=True)
                (repo / name).write_text(text)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            git('add', '.')
            git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qm', 'base')
            base, steps = git('rev-parse', 'HEAD'), []
            for task, name in (('A', 'pkg/helper.py'), ('B', 'pkg/b.py'), ('C', 'guide/GUIDE.md'), ('D', 'tests/notes.md')):
                (repo / name).write_text(task + '\n')
                git('-c', 'user.name=t', '-c', 'user.email=t@t', 'commit', '-qam', task)
                steps.append((task, git('rev-parse', 'HEAD')))
            record = state / 'full-check' / f"tree-{git('rev-parse', 'HEAD^{tree}')}.json"
            record.parent.mkdir(parents=True)

            def suspects(failures, excused=()):
                record.write_text(json.dumps({'result': {'failures': failures}, 'baseline_equivalent': list(excused)}))
                return worker.batch_suspects(str(state), str(repo), base, steps)

            self.assertEqual(suspects(['test_a.ATests.test_x']), ['A'])  # through pkg.a, which imports helper
            self.assertEqual(suspects(['test_doc.DocTests.test_y']), ['C'])  # it reads the file by name
            self.assertEqual(suspects(['test_near.T.test']), ['D'])  # a bare name, beside the test
            self.assertEqual(suspects(['test_a.ATests.test_x', 'test_doc.DocTests.test_y']), ['A', 'C'])
            self.assertEqual(suspects(['test_a.ATests.test_x', 'test_gone.T.test']), [])  # one unexplained
            self.assertEqual(suspects(['test_a.ATests.test_x'], excused=['test_a.ATests.test_x']), [])  # base fails it too
            # The traceback names the line: B wrote it, though the test imports only A's module.
            log = Path(folder, 'gate.log')
            log.write_text('ERROR: test_x (test_a.ATests.test_x)\n' + '-' * 70 + '\nTraceback (most recent call last):\n'
                           '  File "/var/tmp/aw-b-1-x/chain/tests/test_a.py", line 1, in test_x\n'
                           '  File "/var/tmp/aw-b-1-x/chain/pkg/b.py", line 1, in <module>\n'
                           '  File "/usr/lib/python3.12/unittest/case.py", line 58, in testPartExecutor\n'
                           "AttributeError: 'Coordinator' object has no attribute 'base'\n\n" + '-' * 70 + '\nRan 1 test\n')
            record.write_text(json.dumps({'result': {'failures': ['test_a.ATests.test_x']}, 'log': str(log)}))
            self.assertEqual(worker.batch_suspects(str(state), str(repo), base, steps), ['B'])
            # Only base lines in the traceback: the imports decide.
            log.write_text(log.read_text().replace('/pkg/b.py', '/pkg/a.py'))
            self.assertEqual(worker.batch_suspects(str(state), str(repo), base, steps), ['A'])
            record.unlink()
            self.assertEqual(worker.batch_suspects(str(state), str(repo), base, steps), [])  # no record

class BatchLandingTests(unittest.TestCase):
    """TOOLSET-281-0d: a reload 4 s after `landing them now` sent one batch-passed candidate back to
    a queue of single reviews for 15 hours. Until the passed candidates land, the runner neither
    re-executes nor merges code from main into the session their verdicts were reached on."""

    def runner(self, folder, states, record_age=0):
        from pi_autowork import coordinator
        runner = coordinator.Coordinator.__new__(coordinator.Coordinator)
        runner.state, runner.seen = Path(folder), {}
        runner.integration = runner.child = None
        (runner.state / 'batch').mkdir()
        for task in states:
            (runner.state / 'batch' / f'{task}.json').write_text(json.dumps({'at': time.time() - record_age}))
        (runner.state / 'batch-order.txt').write_text('\n'.join(states) + '\n')
        runner.tasks = lambda snapshot=None: [{'task': t, 'state': s} for t, s in states.items()]
        return runner, coordinator

    def test_a_reload_waits_for_batch_passed_candidates_to_land(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {'A': 'closed', 'B': 'integrating', 'C': 'reported'})
            said = []
            with patch.object(coordinator.LOG, 'say', side_effect=said.append), \
                    patch.object(coordinator.os, 'execv', side_effect=AssertionError('re-executed')):
                self.assertIsNone(runner.reexec('Toolset updated to abc; restarting on it'))
            self.assertEqual(said, ['Reload pending: waiting for B, C to land (passed in a batch)'])

    def test_landed_or_expired_batch_verdicts_hold_nothing(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, _ = self.runner(folder, {'A': 'closed', 'B': 'held'})
            self.assertEqual(runner.batch_landing(), [])  # landed, or held: nothing to wait for
        with tempfile.TemporaryDirectory() as folder:
            runner, _ = self.runner(folder, {'B': 'reported'}, record_age=7300)
            self.assertEqual(runner.batch_landing(), [])  # past the verdicts' two hours

    def test_the_session_takes_no_code_from_main_until_the_batch_lands(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {'B': 'reported'})
            runner.repo, runner.integ, runner.integ_branch, runner.base = '/repo', '/session', 'pi-autowork/s', 'main'
            runner.session_busy = lambda: False
            runner.commit_session_leftovers = lambda: self.fail('the session was touched')
            said = []
            with patch.object(coordinator.LOG, 'say', side_effect=said.append), \
                    patch.object(coordinator, 'git', return_value='pi-autowork/pi_autowork/worker.py\n'):
                self.assertFalse(runner.merge_main())
                self.assertFalse(runner.merge_main())
            self.assertEqual(said, ['Merge pending: B land first, on the trees their batch passed'])  # said once
            runner.commit_session_leftovers, runner.ahead = (lambda: None), (lambda: 0)
            with patch.object(coordinator, 'git', return_value='tasks/items/T.md\ndocs/plan.md\n'):
                self.assertTrue(runner.merge_main())  # planning and docs leave the verdicts valid

    def test_a_commit_at_the_merge_limit_runs_fresh_instead_of_asking_the_owner(self):
        """Peers landing in coordinator.py used up three merges, and the commit became an owner
        question with nothing to answer."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.stop, runner.reload = False, False
            runner.reexec_due = lambda: ''
            calls, said = [], []
            outcomes = iter([{'outcome': 'BUSY'}, {'outcome': 'SET_ASIDE', 'renamed': [{'branch_now': 'autowork/B-set-aside-1'}]}])
            runner.engine = lambda *args: calls.append(args) or next(outcomes)
            limit = {'allowed': False, 'merged_count': 3,
                     'reason': 'merge adoption limit reached; adopted 3 of 3; conflict in: a.py'}
            row = {'task': 'B', 'state': 'held', 'cause': 'conflict', 'worktree': folder, 'merge_adoption': limit}
            with patch.object(coordinator.LOG, 'say', side_effect=said.append):
                self.assertFalse(runner.resolve_task_conflict(row))  # a review holds the lock: next cycle
                self.assertTrue(runner.resolve_task_conflict(row))
                other = dict(row, merge_adoption={'allowed': False, 'reason': 'merged is only for an idle conflict-held commit'})
                self.assertFalse(runner.resolve_task_conflict(other))
            self.assertEqual(calls, [('--parallel-set-aside', 'B')] * 2)
            self.assertEqual(said[0], 'B: its commit conflicted with main after 3 merges; set aside as '
                                      'autowork/B-set-aside-1, and the task runs fresh on current main')
            self.assertIn('it waits for the owner', said[1])

    def test_a_candidate_landing_behind_a_busy_checkout_is_said_once(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            said = []
            with patch.object(coordinator.LOG, 'say', side_effect=said.append):
                for _ in range(3):
                    runner.note_state('B', 'reported')
                    runner.note_integrating('B', ['B'])
                runner.note_state('B', 'held', 'merge conflict')
            self.assertEqual(said, ['B: implemented', 'B: landing — passed in its batch; not reviewed again',
                                    'B: failed — merge conflict'])
            said.clear()
            busy = {'outcome': 'BUSY', 'reason': 'live session in the checkout'}
            with patch.object(coordinator.LOG, 'say', side_effect=said.append):
                for _ in range(3):  # a single review behind the same busy checkout
                    runner.note_state('C', 'reported')
                    runner.note_integrating('C', [])
                    runner.integrated('C', busy)
                runner.integrated('C', {'outcome': 'HELD', 'cause': 'conflict', 'reason': 'merge conflict'},
                                  resolve_conflicts=False)
                runner.note_state('C', 'reported')  # requeued after a real review: said again
            self.assertEqual(said, ['C: implemented', 'C: verifying',
                                    'C: waiting to integrate until another session leaves the main checkout '
                                    '(live session in the checkout)', 'C: failed — merge conflict', 'C: implemented'])

    def test_a_day_old_commit_is_set_aside_and_its_task_runs_fresh(self):
        """Twenty day-old commits conflicted with each other at every landing and held back every
        task that shared their files."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.stop = False
            calls, said = [], []
            runner.engine = lambda *args: calls.append(args) or (
                {'outcome': 'SET_ASIDE', 'renamed': [{'branch_now': f'autowork/{args[1]}-set-aside-1'}]}
                if args[1] != 'D' else {'outcome': 'REFUSED', 'reason': 'its interrupted integration already landed'})
            day, now = 25 * 3600, time.time()
            rows = [{'task': 'A', 'state': 'reported', 'elapsed_seconds': day, 'started_at': now - day},
                    # Young: it batches. Its task's first event was two days ago: a fresh rerun of a set-aside one.
                    {'task': 'B', 'state': 'reported', 'elapsed_seconds': 2 * day, 'started_at': now - 3600},
                    {'task': 'C', 'state': 'held', 'elapsed_seconds': day, 'started_at': now - day},  # held: the merge limit decides
                    {'task': 'D', 'state': 'integrating', 'elapsed_seconds': day, 'started_at': now - day},
                    {'task': 'E', 'state': 'running', 'elapsed_seconds': day, 'started_at': now - day}]
            with patch.object(coordinator.LOG, 'say', side_effect=said.append):
                self.assertTrue(runner.set_aside_stale(rows))
                self.assertFalse(runner.set_aside_stale(rows[3:4]))  # the refusal is said once
                runner.integration = {'task': 'X'}
                self.assertFalse(runner.set_aside_stale(rows))  # never beside a review or a batch
                runner.integration = None
                with patch.dict(os.environ, {'PI_AUTOWORK_STALE_HOURS': '0'}):
                    self.assertFalse(runner.set_aside_stale(rows))
            self.assertEqual(calls, [('--parallel-set-aside', 'A'), ('--parallel-set-aside', 'D'),
                                     ('--parallel-set-aside', 'D')])
            self.assertEqual(said, ['A: its commit waited 25 h to merge; set aside as autowork/A-set-aside-1, '
                                    'and the task runs fresh on current main',
                                    'D: could not set aside its day-old commit: its interrupted integration already landed'])

    def test_a_day_old_commit_that_still_merges_is_kept_for_its_review(self):
        """A commit that waited a day behind batches, yet merged cleanly, was about to be thrown away:
        its age was the runner's own queue. Only one that no longer merges is set aside."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            repo = Path(folder) / 'repo'
            git = lambda *a: subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@t', *a],
                                            check=True, capture_output=True, text=True).stdout.strip()
            repo.mkdir()
            git('init', '-q', '-b', 'main')
            (repo / 'f.txt').write_text('base\n')
            git('add', '.')
            git('commit', '-qm', 'base')
            commits = {}
            for task, text in (('A', 'its own file\n'), ('B', 'B changed f\n')):
                git('checkout', '-q', '-b', 'task-' + task, 'main')
                (repo / (task + '.txt' if task == 'A' else 'f.txt')).write_text(text)
                git('add', '.')
                git('commit', '-qm', task)
                commits[task] = git('rev-parse', 'HEAD')
            git('checkout', '-q', '-b', 'session', 'main')
            (repo / 'f.txt').write_text('the session changed f\n')
            git('commit', '-qam', 'session moved')
            runner.stop, runner.repo, runner.integ_branch, runner.base = False, str(repo), 'session', 'main'
            calls, said = [], []
            runner.engine = lambda *args: calls.append(args) or {'outcome': 'SET_ASIDE', 'renamed': []}
            day = 25 * 3600
            rows = [{'task': t, 'state': 'reported', 'started_at': time.time() - day, 'commit': c} for t, c in commits.items()]
            with patch.object(coordinator.LOG, 'say', side_effect=said.append):
                self.assertTrue(runner.set_aside_stale(rows))
                runner.set_aside_stale(rows[:1])  # said once
            self.assertEqual(calls, [('--parallel-set-aside', 'B')])  # B conflicts with the session
            self.assertEqual(said[0], 'A: its commit waited 25 h but still merges with session; kept for its review')
            self.assertEqual(sum('A:' in line for line in said), 1)

    def test_a_busy_checkout_ends_the_pass_so_the_batch_lands_in_order(self):
        """A session in the checkout answered BUSY for the first of three batch-passed candidates;
        the second was tried next, off its batch's order, and both were reviewed again."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.stop, runner.known_at_start, runner.once_task = False, True, None
            rows = [{'task': t, 'state': 'reported'} for t in ('A', 'B', 'C')]
            started = []
            for name, value in dict(finish_resolvers=lambda: None, status=lambda: {}, set_aside_stale=lambda r: False,
                                    session_busy=lambda: False, reverify_held=lambda r: None,
                                    batch_chain=lambda: ['A', 'B', 'C'], batch_conflicts=lambda: [],
                                    batch_due=lambda r: [], reexec_due=lambda: '', follow_base=lambda: None,
                                    resolve_deferred=lambda d: False, start_integration=started.append).items():
                setattr(runner, name, value)
            runner.tasks = lambda snapshot=None: rows
            runner.collect_integration = lambda wait=0: (
                (started[-1], {'outcome': 'BUSY', 'reason': 'live session in the checkout'}) if wait else None)
            with patch.object(coordinator.LOG, 'say'):
                runner.settle()
            self.assertEqual(started, ['A'])

    def test_the_overlap_re_cut_runs_at_most_once_per_interval(self):
        """Back-to-back re-cuts held the loop: no review, landing or dispatch for half an hour."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.workers = 8
            runner.tasks = lambda snapshot=None: [{'task': 'B', 'state': 'waiting',
                                                   'reason': 'shares a.py with A; starts after it lands'}]
            now = [1000.0]
            with patch.object(coordinator.time, 'monotonic', lambda: now[0]):
                self.assertTrue(runner.overlap_idles())
                now[0] += 600
                self.assertFalse(runner.overlap_idles())
                now[0] += 1200
                self.assertTrue(runner.overlap_idles())
                with patch.dict(os.environ, {'PI_AUTOWORK_OVERLAP_EVERY': '60'}):
                    now[0] += 61
                    self.assertTrue(runner.overlap_idles())

    def merge_train_runner(self, folder, ahead_running=True):
        """A runner with a batch of A and B checking, its tip published, and C and D reported."""
        runner, coordinator = self.runner(folder, {})  # no verdicts recorded yet
        rows = [{'task': t, 'state': 'reported', 'commit': f'{t.lower()}1'} for t in 'ABCD']
        runner.tasks = lambda snapshot=None: rows
        runner.stop = False
        runner.reexec_due = lambda: False
        tip = Path(folder) / 'ahead.tip'
        tip.write_text(json.dumps({'tip': 'abc123', 'tasks': ['A', 'B']}))
        ahead = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)' if ahead_running else 'pass'])
        self.addCleanup(lambda: ahead.poll() is None and ahead.kill())
        if not ahead_running:
            ahead.wait()
        runner.integration = {'task': runner.BATCH, 'proc': ahead, 'members': ['A', 'B'], 'tip': str(tip)}
        return runner, coordinator, rows

    def test_the_next_car_boards_on_the_tip_of_the_batch_still_checking(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator, rows = self.merge_train_runner(folder)
            started = []
            runner.start_batch = lambda tasks, on=None, revisions=None: started.append((tasks, on, revisions))
            runner.board_train(rows)
            self.assertEqual(started, [(['C', 'D'], 'abc123', ['C@c1', 'D@d1'])])
            started.clear()
            with patch.dict(os.environ, PI_AUTOWORK_TRAIN='0'):
                runner.board_train(rows)
            self.assertEqual(started, [])  # turned off
            Path(runner.integration['tip']).unlink()
            runner.board_train(rows)
            self.assertEqual(started, [])  # the batch ahead has no chain yet

    def test_a_car_on_a_batch_that_did_not_pass_is_stopped_and_its_verdicts_dropped(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator, _ = self.merge_train_runner(folder)
            car = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
            self.addCleanup(lambda: car.poll() is None and car.kill())
            out = Path(folder) / 'car.out'
            out.write_text('')
            runner.train = {'proc': car, 'out': str(out), 'tip': str(Path(folder) / 'car.tip'), 'members': ['C']}
            coordinator.worker.batch_record(runner.state, 'C').write_text(json.dumps({'ok': True, 'at': time.time()}))
            self.assertTrue(runner.batch_clean({'outcome': 'BATCH', 'tasks': ['A', 'B'], 'passed': ['A', 'B']}))
            for result in ({'outcome': 'BATCH', 'tasks': ['A', 'B'], 'passed': ['B'], 'held': ['A']},
                           {'outcome': 'BATCH_GATE_FAILED', 'tasks': ['A', 'B']}):
                self.assertFalse(runner.batch_clean(result))
            with patch.object(coordinator.LOG, 'say'):
                runner.stop_train('the batch ahead did not pass as checked')
            self.assertIsNotNone(car.poll())
            self.assertIsNone(runner.train)
            self.assertFalse(coordinator.worker.batch_record(runner.state, 'C').exists())

    def test_a_cars_verdicts_land_after_the_chain_ahead(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator, _ = self.merge_train_runner(folder, ahead_running=False)
            runner.integration = None
            for task in 'ABC':
                coordinator.worker.batch_record(runner.state, task).write_text(json.dumps({'ok': True, 'at': time.time()}))
            (runner.state / 'batch-order.txt').write_text('A\nB\n')
            car = subprocess.Popen([sys.executable, '-c', 'pass'])
            car.wait()
            out = Path(folder) / 'car.out'
            out.write_text(json.dumps({'outcome': 'BATCH', 'tasks': ['C'], 'passed': ['C'], 'held': [], 'skipped': []}))
            runner.train = {'proc': car, 'out': str(out), 'tip': str(Path(folder) / 'car.tip'), 'members': ['C'],
                            'revisions': ['C@c1']}
            runner.session_busy = lambda: True
            runner.finish_train()
            self.assertIsNotNone(runner.train)  # the batch ahead still running: its order comes first
            runner.session_busy = lambda: False
            with patch.object(coordinator.LOG, 'say') as said:
                runner.finish_train()
            self.assertIsNone(runner.train)
            self.assertEqual(runner.batch_chain(), ['A', 'B', 'C'])
            self.assertIn('landing them after the batch ahead', said.call_args[0][0])

    def test_no_overlap_re_cut_starts_while_a_reload_is_due(self):
        """A re-cut started just after a new release arrived: the due reload waited for it, and
        no review or batch started for its whole Pi job."""
        with tempfile.TemporaryDirectory() as folder:
            runner, _ = self.runner(folder, {})
            runner.integ, runner.stop = folder, False
            reached = []

            def validate_ledger(*_):
                reached.append(True)
                raise RuntimeError('stop here: the re-cut went ahead')
            runner.validate_ledger = validate_ledger
            runner.reexec_due = lambda: 'update'
            self.assertFalse(runner.maintain(overlap=True))
            self.assertEqual(reached, [])  # returned before any work
            runner.reexec_due = lambda: None
            with self.assertRaisesRegex(RuntimeError, 'went ahead'):
                runner.maintain(overlap=True)  # without a due reload it proceeds as before

    def test_the_overlap_re_cut_runs_beside_the_loop(self):
        """Its Pi job held reviews, landings and dispatch for five minutes at a time while workers
        were busy; it now runs beside the loop and merges once the session may move."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.integ, runner.stop, runner.settled = folder, False, False
            out = Path(folder) / 'maintainer.out'
            out.write_text(json.dumps({'ok': True, 'notes': []}))
            proc = subprocess.Popen([sys.executable, '-c', 'pass'])
            proc.wait()
            runner.maintainer_job = {'proc': proc, 'out': str(out), 'scratch': folder}
            judged = []
            runner.maintainer_result = lambda job, ok: judged.append(ok) or True
            busy = [True]
            runner.session_busy = lambda: busy[0]
            with patch.object(coordinator, 'dirty', return_value=False):
                self.assertFalse(runner.maintain(overlap=True))  # one maintainer at a time
                runner.finish_maintainer()
                self.assertEqual(judged, [])  # a review runs: its merge waits, the job is kept
                self.assertIsNotNone(runner.maintainer_job)
                said = []
                with patch.object(coordinator.LOG, 'say', side_effect=said.append), \
                        patch.object(coordinator.os, 'execv', side_effect=AssertionError('re-executed')):
                    runner.reexec('Toolset updated to abc; restarting on it')
                self.assertEqual(said, ['Reload pending: waiting for the DOCS-MAINTAINER re-cut to end'])
                busy[0] = False
                runner.finish_maintainer()
            self.assertEqual(judged, [True])
            self.assertIsNone(runner.maintainer_job)
            self.assertTrue(runner.settled)
            self.assertFalse(out.exists())

    def test_an_exit_stops_a_running_re_cut_and_drops_its_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            runner, _ = self.runner(folder, {})
            proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'])
            self.addCleanup(lambda: proc.poll() is None and proc.kill())
            out = Path(folder) / 'maintainer.out'
            out.write_text('')
            dropped = []
            runner.drop_scratch = dropped.append
            runner.maintainer_job = {'proc': proc, 'out': str(out), 'scratch': '/scratch'}
            runner.stop_maintainer()
            self.assertIsNotNone(proc.poll())
            self.assertEqual(dropped, ['/scratch'])
            self.assertIsNone(runner.maintainer_job)

    def test_a_due_reload_starts_no_merge_resolver(self):
        """Each new resolver kept the reload pending, and a due reload starts no batch: commits
        were resolved again and again for hours while none landed."""
        with tempfile.TemporaryDirectory() as folder:
            runner, coordinator = self.runner(folder, {})
            runner.stop, runner.reload = False, True
            row = {'task': 'B', 'state': 'held', 'cause': 'conflict', 'worktree': folder,
                   'merge_adoption': {'allowed': True, 'baseline': 'abc'}}
            with patch.object(coordinator, 'git', side_effect=AssertionError('resolution started')):
                self.assertFalse(runner.resolve_task_conflict(row))
            self.assertEqual(runner.resolvers, {})
class HeadlessApprovalTests(unittest.TestCase):
    """TOOLSET-282-43: a worker loaded an interactive design skill, ended its session with "Do you
    approve?" after 28 s, and the runner held the task as a dead worker for the owner to rescope."""

    def run_worker(self, replies):
        from pi_autowork import worker
        folder = tempfile.TemporaryDirectory()
        self.addCleanup(folder.cleanup)
        root = Path(folder.name)
        tree = root / 'tree'
        subprocess.run(['git', 'init', '-q', str(tree)], check=True)
        git = lambda *a: subprocess.run(['git', '-C', str(tree), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        git('commit', '-q', '--allow-empty', '-m', 'base')
        baseline = git('rev-parse', 'HEAD').stdout.strip()
        prompt, report = root / 'prompt.md', root / 'attempt-1' / 'report.json'
        report.parent.mkdir()
        prompt.write_text(f'Task: T-1\nBaseline: {baseline}\nReport file: {report}\n')
        calls = []

        def job(settings, role, task, directory, message, session, limit, extra):
            calls.append((message, session))
            reply = replies[len(calls) - 1]
            if reply == 'work':
                (tree / 'done.txt').write_text('done\n')
                git('add', 'done.txt')
                git('commit', '-qm', 'work')
                report.write_text(json.dumps({'task': 'T-1', 'commit': git('rev-parse', 'HEAD').stdout.strip()}))
                return {'ok': True, 'text': 'Committed.'}
            return {'ok': True, 'text': reply}

        with patch.object(worker.pi_runtime, 'job', side_effect=job), \
                patch.object(worker.pi_runtime, 'Settings', return_value=None):
            code = worker.worker(str(root / 'state'), str(tree), str(prompt), str(report), 60)
        return code, calls, report

    def test_a_worker_that_asks_for_approval_is_resumed_once_in_its_session(self):
        code, calls, report = self.run_worker(['Here is my design.\n\n**Do you approve?**', 'work'])
        self.assertEqual(code, 0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][1], calls[1][1])  # the same session, the same attempt
        self.assertIn('No person is attached', calls[1][0])
        self.assertIsNotNone(json.loads(report.read_text())['commit'])

    def test_a_worker_that_asks_twice_is_held_with_its_question(self):
        code, calls, report = self.run_worker(['Do you approve?', 'Which option do you prefer?'])
        self.assertEqual((code, len(calls)), (1, 2))
        self.assertEqual(json.loads(report.read_text())['blockers'],
                         ['the worker asked twice instead of implementing: Which option do you prefer?'])

    def test_a_finished_worker_or_a_plain_ending_is_not_resumed(self):
        self.assertEqual(len(self.run_worker(['work'])[1]), 1)
        self.assertEqual(len(self.run_worker(['I could not finish.'])[1]), 1)


class BatchableTests(unittest.TestCase):
    def test_a_review_a_restart_cut_short_joins_the_next_batch(self):
        """Left integrating by a restart, three commits waited behind every later batch, one
        for 16 hours: only reported commits were ever batched."""
        from pi_autowork.coordinator import batchable
        rows = [{'task': 'A', 'state': 'reported', 'commit': 'a'}, {'task': 'B', 'state': 'integrating', 'commit': 'b'},
                {'task': 'C', 'state': 'held', 'commit': 'c'}, {'task': 'D', 'state': 'running'}]
        self.assertEqual(batchable(rows), [('A', 'a'), ('B', 'b')])
        self.assertEqual(batchable(rows, {'A'}), [('B', 'b')])

    def test_a_commit_whose_batch_failed_gets_a_review_between_two_batches(self):
        """While resolutions kept producing fresh revisions a batch was always due first, and nine
        commits whose batch had failed waited for a review of their own, one for 15 hours."""
        from pi_autowork import coordinator
        with tempfile.TemporaryDirectory() as folder:
            runner = coordinator.Coordinator.__new__(coordinator.Coordinator)
            runner.state, runner.seen = Path(folder), {}
            runner.reexec_due, runner.batch_pending = (lambda: ''), (lambda: False)
            (runner.state / 'batch-failed.json').write_text(json.dumps(['F@f']))
            reported = [('A', 'a'), ('B', 'b'), ('F', 'f')]
            self.assertEqual(runner.batch_due(reported), ['A', 'B'])
            for _ in range(3):  # F's turns alone (PI_AUTOWORK_SINGLES_PER_BATCH, default 3)
                self.assertEqual(runner.batch_due(reported + [('C', 'c')]), [])
                runner.single_started()
            self.assertEqual(runner.batch_due(reported + [('C', 'c')]), ['A', 'B', 'C'])
            (runner.state / 'batch-failed.json').write_text('[]')
            self.assertEqual(runner.batch_due([('D', 'd'), ('E', 'e')]), ['D', 'E'])  # none failed: batches go on


class BusyLineTests(unittest.TestCase):
    """The wait for a session in the main checkout is said once per session: its changing status
    ("running command", "terminal used 2 min ago") repeated the line every minute."""

    def test_the_same_session_is_named_once_and_another_one_again(self):
        from pi_autowork import coordinator
        runner = coordinator.Coordinator.__new__(coordinator.Coordinator)
        runner.seen = {}
        said = []
        reason = 'live or unknown external writer/session; preserve canonical checkout: pid {} pi in /repo (session: {})'
        with patch.object(coordinator.LOG, 'say', side_effect=said.append):
            for pid, status in ((7, 'running command'), (7, 'terminal used 2 min ago'), (8, 'running command')):
                runner.integrated('A', {'outcome': 'BUSY', 'reason': reason.format(pid, status)})
        self.assertEqual(len(said), 2, said)
        self.assertIn('pid 8', said[1])


class EnvironmentMarkerTests(unittest.TestCase):
    """TOOLSET-173-94: 'could not check' is recorded apart from 'checked and wrong'."""

    def test_a_review_that_could_not_run_records_what_was_missing(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
            state.mkdir()
            verdicts = iter(['PI_AUTOWORK_VERIFY: fail environment — flutter SDK 3.44 (ENVIRONMENT.md)',
                             'PI_AUTOWORK_VERIFY: pass all good',
                             'PI_AUTOWORK_VERIFY: fail — the Back behaviour is not verified',
                             'PI_AUTOWORK_VERIFY: pass now'])
            job = lambda *a: {'ok': True, 'text': next(verdicts)}
            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 1)
                    marker = worker.environment_marker(state, 'T-1')
                    self.assertEqual(json.loads(marker.read_text())['missing'], 'flutter SDK 3.44 (ENVIRONMENT.md)')
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
                    self.assertFalse(marker.exists())
                    self.assertEqual(worker.review_findings(state, 'T-1'), '')  # an environment miss is no finding
                    self.assertEqual(worker.verify(str(state), 'T-1'), 1)
                    self.assertEqual(worker.review_findings(state, 'T-1'),
                                     'PI_AUTOWORK_VERIFY: fail — the Back behaviour is not verified')
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
                    self.assertEqual(worker.review_findings(state, 'T-1'), '')
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp


if __name__ == '__main__':
    unittest.main()
