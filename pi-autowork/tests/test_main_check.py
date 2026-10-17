"""Main's full offline check after a landing (TOOLSET-176-98)."""
from pathlib import Path
import sys
import unittest

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
