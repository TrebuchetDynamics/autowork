"""Main's full offline check after a landing (TOOLSET-176-98)."""
import os
from pathlib import Path
import signal
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
               'TIMEOUT: /repo/tests after 1800s\n')
        self.assertEqual(main_check.failures(log), ['test_preflight.PreflightTests.test_core_plan',
                                                     'test_ui_taste_bundle.UiTasteBundleTests.test_bundle',
                                                     '/repo/tests (timed out)'])

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
        self.assertEqual(main_check.line({'state': 'running', 'rev': 'abcdef123', 'started': 0}, now=600),
                         'main check running on abcdef1 (10m)')
        self.assertEqual(main_check.line({}), '')
        self.assertEqual(main_check.command({'PI_AUTOWORK_MAIN_CHECK': ' python3 scripts/check.py '}),
                         'python3 scripts/check.py')


if __name__ == '__main__':
    unittest.main()
