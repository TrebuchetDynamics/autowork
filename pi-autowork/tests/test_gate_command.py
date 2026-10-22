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
        # Its quiet rerun takes a check slot: a private pool, or inside a review it queued
        # behind every runner's full suite on the host.
        env['PI_AUTOWORK_CHECK_ROOT'] = str(self.repo / '.git' / 'check-slots')
        with patch.dict(os.environ, env, clear=True):
            command = main_check.full_check(str(self.repo))
            self.assertEqual(command, 'python3 -m unittest test_mod')
            self.assertEqual(worker.run_gate(self.state, 'T-1', str(self.repo), command), (True, ''))
            text = 'Ran 2 tests in 0.1s\n\nFAILED (failures=1)\n'
            self.assertTrue(main_check.complete_results(text, self.repo))
            self.assertFalse(main_check.complete_results(text, self.repo, env['PI_AUTOWORK_MAIN_CHECK']))
        self.assertTrue((self.repo / 'attempted').is_file())  # the merged run failed; the rerun alone passed

    def test_recorded_gate_results_keep_their_verdict_reasons(self):
        """Excusing named failures must not excuse an unfinished run or a shared crash.

        Receipt-shaped fixtures retain the result, isolated reruns and baseline fields
        produced by the real gate; transient crash/completeness evidence is supplied separately.
        """
        green = {'code': 0, 'failures': [], 'timed_out': False, 'skips': 0, 'resource_skips': 0}
        red = dict(green, code=1, failures=['m.T.test_red'])
        crash = dict(green, code=139)
        cases = [
            ('pass', {'result': green}, (True, '')),
            ('legacy result without skip metadata',
             {'result': {'code': 0, 'failures': [], 'timed_out': False}}, (True, '')),
            ('flaky excused', {'result': red, 'isolated_rerun': ['m.T.test_red']}, (True, '')),
            ('baseline equivalent', {'result': red, 'baseline': red}, (True, '')),
            ('new failure', {'result': red, 'baseline': green},
             (False, 'the full check has new failures the base does not: m.T.test_red')),
            ('partly excused', {'result': dict(red, failures=['m.T.test_flaky', 'm.T.test_red']),
                               'isolated_rerun': ['m.T.test_flaky'], 'baseline': green},
             (False, 'the full check has new failures the base does not: m.T.test_red')),
            ('time limit', {'result': dict(red, timed_out=True), 'limit': 12.5},
             (False, 'the full check ran out of time after 12.5 s')),
            ('incomplete receipt', {'result': red, 'isolated_rerun': ['m.T.test_red'], 'incomplete': True},
             (False, 'the full check stopped before its results were complete (exit 1); the rest never ran')),
            ('signal after named failures', {'result': dict(red, code=137), 'isolated_rerun': ['m.T.test_red']},
             (False, 'the full check stopped before its results were complete (exit 137); the rest never ran')),
            ('directory timeout', {'result': dict(red, failures=['tests (timed out)']), 'baseline': red},
             (False, 'the full check did not complete tests (timed out)')),
            ('missing base', {'result': red, 'base_error': 'unknown revision'},
             (False, 'the full check has no base to compare with: unknown revision')),
            ('unfinished base', {'result': red, 'baseline': dict(red, timed_out=True)},
             (False, 'the full check has no base to compare with: the base run did not complete')),
            ('directory timeout on base', {'result': red,
                                          'baseline': dict(red, failures=['tests (timed out)'])},
             (False, 'the full check has no base to compare with: the base run did not complete')),
            ('crash on green base', {'result': crash, 'baseline': green, 'crash': 'Segmentation fault'},
             (False, 'the full check exits 139 where the base passes: Segmentation fault')),
            ('crash on red base', {'result': crash, 'baseline': red, 'crash': 'Segmentation fault'},
             (False, 'the full check exits 139 where the base runs to its test results: Segmentation fault')),
            ('crash on base too', {'result': crash, 'baseline': crash, 'crash': 'Segmentation fault'},
             (False, 'the full check crashed before any test result, on the base too: Segmentation fault')),
        ]
        for name, receipt, expected in cases:
            with self.subTest(receipt=name):
                self.assertEqual(worker.gate_verdict(**receipt), expected)

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


    def test_failures_none_of_a_sample_excuses_are_not_rerun_one_at_a_time(self):
        """108 failures rerun alone, each to its 120 s limit, took three hours: every review that
        met a broken host ran out of time before its reviewer started."""
        tests = [f't.T.test_{n:03}' for n in range(20)]
        for passes, expected in ((False, [5]), (True, [5, 15])):
            sizes = []

            def rerun(log, checkout, receipt, rev, only=(), workers=None):
                sizes.append(len(only))
                Path(receipt).write_text(json.dumps({'rev': rev, 'flaky': sorted(only) if passes else []}))

            env = dict(os.environ, PI_AUTOWORK_CHECK_ROOT=str(self.repo / 'slots'), PI_AUTOWORK_QUIET_WAIT='0')
            with patch.dict(os.environ, env, clear=True), patch.object(main_check, 'rerun_failures', rerun):
                flaky = worker.quiet_reruns(self.state, 'T-1', self.repo / 'T-1-merged.log', str(self.repo),
                                            'abc', tests, 3600)
            self.assertEqual(sizes, expected)
            self.assertEqual(flaky, tests if passes else [])

if __name__ == '__main__':
    unittest.main()
