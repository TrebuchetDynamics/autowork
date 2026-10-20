"""The review gate judges completeness from the command that produced its log.

A repository may declare its full check in AGENTS.md rather than the environment: the command
then never enters the runner's environment, and deriving completeness from PI_AUTOWORK_* alone
rejected a merged run whose only failure passed when rerun alone.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import main_check, worker  # noqa: E402


class GateCommandTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.state = self.repo / '.git' / 'gate-state'

    def git(self, *args):
        return subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                               '-c', 'user.name=T', *args], check=True, capture_output=True, text=True)

    def test_a_full_check_declared_in_agents_md_proves_its_own_completeness(self):
        """The gate's check is in AGENTS.md, and main's own check is a different command: only
        the gate's command may explain its log."""
        (self.repo / 'test_mod.py').write_text(
            'import unittest\nfrom pathlib import Path\n'
            'class T(unittest.TestCase):\n'
            '    def test_flaky(self):\n'
            '        marker = Path(__file__).with_name("attempted")\n'
            '        if not marker.exists():\n'
            '            marker.write_text("x")\n'
            '            self.fail("first run only")\n')
        (self.repo / 'AGENTS.md').write_text('Full check: python3 -m unittest test_mod\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'base')
        (self.repo / 'a.txt').write_text('merged\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'merged')
        env = {k: v for k, v in os.environ.items()
               if k not in ('PI_AUTOWORK_VALIDATE', 'PI_AUTOWORK_MAIN_CHECK')}
        env['PI_AUTOWORK_MAIN_CHECK'] = 'python3 -m pytest -q'  # main's check, not the gate's
        with patch.dict(os.environ, env, clear=True):
            command = main_check.full_check(str(self.repo))
            self.assertEqual(command, 'python3 -m unittest test_mod')
            self.assertEqual(worker.run_gate(self.state, 'T-1', str(self.repo), command), (True, ''))
            text = 'Ran 2 tests in 0.1s\n\nFAILED (failures=1)\n'
            self.assertTrue(main_check.complete_results(text, self.repo))
            self.assertFalse(main_check.complete_results(text, self.repo, env['PI_AUTOWORK_MAIN_CHECK']))
        self.assertTrue((self.repo / 'attempted').is_file())  # the merged run failed; the rerun alone passed

    def test_explicit_main_check_command_still_judges_its_own_log(self):
        """Main's check passes its command: a complete unittest log is provable even when the
        repository's gate check is a different command."""
        (self.repo / 'AGENTS.md').write_text('Full check: ruff check . && python3 -m unittest\n')
        env = {k: v for k, v in os.environ.items()
               if k not in ('PI_AUTOWORK_VALIDATE', 'PI_AUTOWORK_MAIN_CHECK')}
        env['PI_AUTOWORK_MAIN_CHECK'] = 'python3 -m unittest discover'
        with patch.dict(os.environ, env, clear=True):
            text = 'Ran 2 tests in 0.1s\n\nOK\n'
            self.assertFalse(main_check.complete_results(text, self.repo))  # gate's shell command
            self.assertTrue(main_check.complete_results(text, self.repo, env['PI_AUTOWORK_MAIN_CHECK']))

    def test_a_quiet_rerun_never_waits_past_its_bound_for_a_host_check_slot(self):
        """Every host check slot is held by another runner's full suite: the two-minute rerun of a
        candidate's failures runs once PI_AUTOWORK_QUIET_WAIT has passed, instead of queueing for
        hours behind them."""
        slots = self.repo / 'slots'
        slots.mkdir(mode=0o700)
        holder = subprocess.Popen([sys.executable, '-c', (
            'import fcntl, os, sys, time\n'
            f'fd = os.open({str(slots / "slot-0")!r}, os.O_RDWR | os.O_CREAT, 0o600)\n'
            'fcntl.flock(fd, fcntl.LOCK_EX)\n'
            'print("held", flush=True)\n'
            'time.sleep(60)\n')], stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.stdout.close)
        self.addCleanup(holder.wait)
        self.addCleanup(holder.kill)
        self.assertEqual(holder.stdout.readline().strip(), 'held')
        calls = []

        def rerun(log, checkout, receipt, rev, only=(), workers=None):
            calls.append(workers)
            Path(receipt).write_text(json.dumps({'rev': rev, 'flaky': sorted(only)}))

        env = dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(slots), PI_AUTOWORK_CHECK_SLOTS='1',
                   PI_AUTOWORK_QUIET_WAIT='0.5')
        log = self.repo / 'T-1-merged.log'
        started = time.monotonic()
        with patch.dict(os.environ, env, clear=True), patch.object(main_check, 'rerun_failures', rerun):
            flaky = worker.quiet_reruns(self.state, 'T-1', log, str(self.repo), 'abc', ['t.T.test_a'], 3600)
        self.assertEqual(flaky, ['t.T.test_a'])
        self.assertEqual(calls, [1])  # still one at a time
        self.assertLess(time.monotonic() - started, 30)


if __name__ == '__main__':
    unittest.main()
