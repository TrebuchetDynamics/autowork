"""Main's full offline check after a landing (TOOLSET-176-98)."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import main_check  # noqa: E402


class MainCheckTests(unittest.TestCase):
    def test_failures_are_read_from_unittest_and_check_output(self):
        log = ('CHECK tests (50 modules)\n'
               'FAIL: test_core_plan (test_preflight.PreflightTests.test_core_plan)\n'
               'ERROR: test_bundle (test_ui_taste_bundle.UiTasteBundleTests.test_bundle)\n'
               'FAIL: test_core_plan (test_preflight.PreflightTests.test_core_plan)\n'
               'UNEXPECTED SUCCESS: test_fixed (test_other.OtherTests.test_fixed)\n'
               'TIMEOUT: /repo/tests after 1800s\n')
        self.assertEqual(main_check.failures(log), ['test_preflight.PreflightTests.test_core_plan',
                                                     'test_ui_taste_bundle.UiTasteBundleTests.test_bundle',
                                                     'test_other.OtherTests.test_fixed', '/repo/tests (timed out)'])

    def test_the_full_check_comes_from_validate_or_agents_md(self):
        """TOOLSET-180-72: the repository declares its whole offline suite once."""
        import tempfile
        with tempfile.TemporaryDirectory() as root:
            self.assertEqual(main_check.full_check(root, {}), '')
            Path(root, 'AGENTS.md').write_text('# Rules\n\n- Full check: `python3 scripts/check.py`\n')
            self.assertEqual(main_check.full_check(root, {}), 'python3 scripts/check.py')
            self.assertEqual(main_check.full_check(root, {'PI_AUTOWORK_VALIDATE': 'make test'}), 'make test')
            self.assertEqual(main_check.command({}, root), 'python3 scripts/check.py')  # main check falls back
            self.assertEqual(main_check.command({'PI_AUTOWORK_MAIN_CHECK': 'x'}, root), 'x')
        self.assertEqual(main_check.failures('FAILED tests/test_a.py::test_b - x\n    --- FAIL: TestC (0.1s)\n'),
                         ['tests/test_a.py::test_b', 'TestC'])

    def test_reruns_are_alone_in_their_directory_and_bounded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_sample.py').write_text(
                'from pathlib import Path\nimport time, unittest\n'
                'class Sample(unittest.TestCase):\n'
                '    def test_pass(self): Path("ran").touch()\n'
                '    def test_fail(self): self.fail("still broken")\n'
                '    @unittest.skip("not exercised")\n'
                '    def test_skip(self): pass\n'
                '    def test_slow(self): time.sleep(30)\n')
            log, receipt = root / 'check.log', root / 'reruns.json'
            for ids, want in [(['test_pass', 'test_fail', 'test_skip', 'test_slow'], ['test_pass']),
                              ([f'test_missing_{i}' for i in range(10)] + ['test_pass'], [])]:
                with self.subTest(ids=ids):
                    (tests / 'ran').unlink(missing_ok=True)
                    log.write_text('CHECK tests (1 modules)\n' + ''.join(
                        f'FAIL: {name} (test_sample.Sample.{name})\n' for name in ids)
                        + 'Ran 4 tests in 0.01s\n\nFAILED (failures=4)\n')
                    main_check.rerun_failures(log, root, receipt, 'abc123', timeout=1)
                    self.assertEqual(json.loads(receipt.read_text())['flaky'],
                                     [f'test_sample.Sample.{name}' for name in want])
                    self.assertEqual((tests / 'ran').exists(), bool(want))
                    self.assertFalse((root / 'ran').exists())

    def test_three_distinct_flaky_revisions_make_one_hardening_trigger(self):
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        test_id = 'test_sample.Sample.test_pass'
        with tempfile.TemporaryDirectory() as tmp:
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = Path(tmp), tmp
            runner.maintain = lambda **_: None
            (runner.state / 'main-check.exit').write_text('1\n')
            (runner.state / 'main-check.log').write_text(f'FAIL: test_pass ({test_id})\n')
            record = {}
            for rev, count in [('a', 1), ('a', 1), ('b', 2), ('c', 3), ('d', 3)]:
                (runner.state / 'main-check-reruns.json').write_text(json.dumps({'rev': rev, 'flaky': [test_id]}))
                runner.finish_main_check(dict(record, rev=rev))
                record = main_check.read(runner.state)
                self.assertEqual(record['state'], 'green')
                self.assertEqual(len(record['flaky_history'][test_id]), count)
                found = maintainer.triggers([], record,
                    reported_flakes=maintainer.last(runner.state).get('flaky_tests', []))
                self.assertEqual(len(found), int(rev == 'c'))
                if found:
                    self.assertEqual(found[0][:2], ('MAIN', 'flaky test'))
                    self.assertIn(test_id, maintainer.prompt(found, '/repo', 'goals.py'))
                    maintainer.remember(runner.state, trigger_key=maintainer.key(found),
                                        found=found, outcome='merged')

    def test_flaky_batches_handle_overflow_without_repeating_main_repairs(self):
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        for count, acknowledged, red, calls in [(1, 0, True, 1), (12, 12, True, 1),
                                                 (13, 12, False, 1), (12, 0, True, 2)]:
            with self.subTest(count=count, acknowledged=acknowledged), tempfile.TemporaryDirectory() as tmp:
                runner = Coordinator.__new__(Coordinator)
                runner.state, runner.repo, runner.integ, runner.stop = Path(tmp), tmp, tmp, False
                runner.in_flight = runner.session_busy = lambda: False
                runner.scratch_checkout, runner.drop_scratch = lambda _: tmp, lambda _: None
                runner.goals, runner.verify_timeout = 'goals.py', 1
                prompts = []
                runner.pi_job = lambda *args: (not prompts.append(args[3]), '')
                history = {f'test_sample.Sample.test_{i:02}': ['a', 'b', 'c'] for i in range(count)}
                if acknowledged:
                    previous = dict(list(history.items())[:acknowledged])
                    found = maintainer.triggers([], {'flaky_history': previous})
                    maintainer.remember(runner.state, trigger_key=maintainer.key(found),
                                        found=found, outcome='merged')
                main_check.write(runner.state, dict(state='red' if red else 'green', flaky_history=history,
                                                   failures=['test_other.Other.test_broken'] if red else []))
                with patch('pi_autowork.coordinator.dirty', return_value=False):
                    for _ in range(3):
                        runner.maintain(main_only=True)
                self.assertEqual(len(prompts), calls)
                if red:
                    self.assertIn('(main red)', prompts[-1])

    def test_unfinished_or_wrong_revision_reruns_cannot_excuse_main(self):
        from pi_autowork.coordinator import Coordinator

        test_id = 'test_sample.Sample.test_pass'
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            tests = root / 'tests'
            tests.mkdir()
            (tests / 'test_sample.py').write_text(
                'import os, unittest\nclass Sample(unittest.TestCase):\n'
                '    def test_pass(self): self.assertNotIn("FULL_RUN", os.environ)\n'
                '    @unittest.expectedFailure\n    def test_unexpected(self): pass\n')
            log = root / 'main-check.log'
            receipt = root / 'main-check-reruns.json'
            (root / 'main-check.exit').write_text('1\n')
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = root, tmp
            runner.maintain = lambda **_: None
            for modules in [1, 2]:
                with self.subTest(modules=modules), log.open('w') as output:
                    # modules=2 represents another process dying without a summary.
                    output.write(f'CHECK tests ({modules} modules)\n')
                    output.flush()
                    subprocess.run([sys.executable, '-m', 'unittest', 'test_sample'], cwd=tests,
                                   env=dict(os.environ, FULL_RUN='1'), stdout=output, stderr=output, check=False)
                main_check.rerun_failures(log, root, receipt, 'abc')
                for revision in ['abc', 'different']:
                    with self.subTest(revision=revision):
                        runner.finish_main_check({'rev': revision})
                        self.assertEqual(main_check.read(root)['state'], 'red')

    def test_a_check_that_crashes_before_any_result_is_broken_not_red(self):
        """TOOLSET-237-35: a tool crash made main red with placeholder 'failing tests'."""
        from pi_autowork import maintainer
        from pi_autowork.coordinator import Coordinator

        crash = ('[warn][wallpaper] Set wallpaper failed {"error":"Bad state: channel unavailable"}\n'
                 'Analyzing app...\nNo issues found! (ran in 24.5s)\n\n'
                 'Oops; flutter has exited unexpectedly: "Bad state: No element".\n'
                 'A crash report has been written to /x/flutter_01.log\n')
        self.assertEqual(main_check.crash_line(crash), 'Oops; flutter has exited unexpectedly: "Bad state: No element".')
        self.assertEqual(main_check.crash_line('a\nlast words\n'), 'last words')
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.repo = root, tmp
            maintained = []
            runner.maintain = lambda **_: maintained.append(main_check.read(root)['state'])
            (root / 'main-check.log').write_text(crash)
            (root / 'main-check.exit').write_text('1\n')
            runner.finish_main_check({'rev': 'abc123'})
            first = main_check.read(root)
            self.assertEqual((first['state'], first.get('crashed')), ('recheck', 'abc123'))  # once more
            self.assertEqual(maintained, [])
            runner.finish_main_check(dict(first, rev='abc123'))
            record = main_check.read(root)
            self.assertEqual(record['state'], 'broken')
            self.assertIn('Bad state: No element', record['crash'])
            self.assertFalse(record.get('failures'))  # no placeholder test IDs
            self.assertEqual(maintained, ['broken'])
            self.assertEqual(main_check.line(record), 'main check broken at abc123: ' + record['crash'])
            found = maintainer.triggers([], record)
            self.assertEqual([kind for _, kind, _ in found], ['check broken'])
            self.assertIn('Never add a repair task for test names', maintainer.prompt(found, '/repo', 'goals.py'))

    def test_crash_line_ranks_terminal_messages_and_uses_the_last_match(self):
        cases = [
            ('Bad state: earlier\nSegmentation fault\nreport saved\n', 'Segmentation fault'),
            ('Fatal error: first\nAborted\nreport saved\n', 'Fatal error: first'),
            ('panic: first\nKilled\nreport saved\n', 'Killed'),
            ('Aborted\nout of memory\nreport saved\n', 'out of memory'),
            ('Bad state: earlier\nTraceback (most recent call last):\n'
             '  File "check.py", line 1, in <module>\n'
             '    raise RuntimeError("broken")\nRuntimeError: broken\nreport saved\n',
             'RuntimeError: broken'),
            ('Traceback (most recent call last):\n  run()\nKeyboardInterrupt\nreport saved\n',
             'KeyboardInterrupt'),
            ('example.Error: not a traceback\nAborted\nreport saved\n', 'Aborted'),
        ]
        for prefix in ('[warn][wallpaper]', '[info]', 'WARNING:'):
            cases.append((f'{prefix} Fatal error: Bad state\nlast words\n\n', 'last words'))
            cases.append((f'core dumped\n{prefix} Killed\nreport saved\n', 'core dumped'))
        for log, expected in cases:
            with self.subTest(log=log):
                self.assertEqual(main_check.crash_line(log), expected)

    def test_alive_rejects_zombies_and_reused_pids(self):
        pid = os.fork()
        if pid == 0:
            os.kill(os.getpid(), signal.SIGSTOP)
            os._exit(0)
        try:
            os.waitpid(pid, os.WUNTRACED)
            start = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
            self.assertTrue(main_check.alive(pid))  # pre-upgrade records have no start time
            self.assertTrue(main_check.alive(pid, start))
            self.assertFalse(main_check.alive(pid, str(int(start) + 1)))
            os.kill(pid, signal.SIGCONT)
            deadline = time.monotonic() + 5
            while Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0] != 'Z':
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            self.assertFalse(main_check.alive(pid))
        finally:
            os.kill(pid, signal.SIGKILL)
            os.waitpid(pid, 0)
        self.assertFalse(main_check.alive(pid, start))

    def test_an_exit_receipt_finishes_even_while_the_pid_is_alive(self):
        from pi_autowork.coordinator import Coordinator

        read_fd, write_fd = os.pipe()
        pid = os.fork()
        if pid == 0:
            os.close(write_fd)
            os.read(read_fd, 1)
            os._exit(0)
        os.close(read_fd)
        try:
            with tempfile.TemporaryDirectory() as tmp:
                runner = Coordinator.__new__(Coordinator)
                runner.state, runner.stop = Path(tmp), False
                runner.repo, runner.base = tmp, 'main'
                main_check.write(runner.state, dict(state='running', rev='abcdef123', pid=pid,
                                                    start_time=main_check.start_time(pid)))
                (runner.state / 'main-check.exit').touch()  # shell redirection opens before echo writes
                with patch.dict(os.environ, PI_AUTOWORK_MAIN_CHECK='true'):
                    runner.check_main()
                    self.assertEqual(main_check.read(runner.state)['state'], 'running')
                    (runner.state / 'main-check.exit').write_text('0\n')
                    runner.check_main()
                    self.assertEqual(main_check.read(runner.state)['state'], 'green')
                    os.write(write_fd, b'x')  # bash may exit just after writing its receipt
                    os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)
                    runner.check_main()
                with self.assertRaises(ChildProcessError):
                    os.waitpid(pid, os.WNOHANG)
        finally:
            os.close(write_fd)
            try:
                os.kill(pid, signal.SIGKILL)
                os.waitpid(pid, 0)
            except ProcessLookupError:
                pass

    def test_the_status_line(self):
        self.assertEqual(main_check.line({'state': 'red', 'rev': 'abcdef123', 'failures': ['a', 'b']}),
                         'main red since abcdef1: 2 failing')
        self.assertEqual(main_check.line({'state': 'green', 'rev': 'abcdef123'}), 'main green at abcdef1')
        self.assertEqual(main_check.line({'state': 'green', 'rev': 'abcdef123', 'flaky': ['a']}),
                         'main green at abcdef1 (1 flaky)')
        self.assertEqual(main_check.line({'state': 'running', 'rev': 'abcdef123', 'started': 0}, now=600),
                         'main check running on abcdef1 (10m)')
        self.assertEqual(main_check.line({}), '')
        self.assertEqual(main_check.command({'PI_AUTOWORK_MAIN_CHECK': ' python3 scripts/check.py '}),
                         'python3 scripts/check.py')


if __name__ == '__main__':
    unittest.main()
