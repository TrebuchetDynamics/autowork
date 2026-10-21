"""scripts/affected_tests.py selects the test modules a change can reach, with the reason."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import affected_tests  # noqa: E402


SELF = 'tests/test_affected_tests.py'  # names the paths below, so it is selected by them too


class AffectedTestsTests(unittest.TestCase):
    def test_a_document_selects_only_the_tests_that_read_it(self):
        tests, reasons, full = affected_tests.select(['docs/project.md'])
        self.assertFalse(full)
        self.assertEqual([t for t in tests if t != SELF], ['tests/test_project_status.py'])
        self.assertEqual(reasons['tests/test_project_status.py'], 'tests/test_project_status.py <- docs/project.md')

    def test_code_selects_its_importers_and_the_tests_that_run_it(self):
        """Today's real breakages: each change's selection holds the tests that failed."""
        for change, failed in (('pi-autowork/pi_autowork/task_commands.py', ['tests/test_task_commands.py']),
                               ('pi-autowork/pi_autowork/task_migrate.py', ['pi-autowork/engine/test_parallel_plan.py']),
                               ('pi-autowork/pi_autowork/worker.py', ['tests/test_pi_autowork.py']),
                               ('install_skills.py', ['tests/test_engineering_vendor.py'])):
            with self.subTest(change=change):
                tests, _, full = affected_tests.select([change])
                self.assertFalse(full)
                self.assertTrue(set(failed) <= set(tests), (failed, tests))
                self.assertLess(len(tests), 100)  # a selection, not the suite

    def test_a_changed_test_module_selects_itself_and_an_extensionless_script_its_tests(self):
        self.assertIn('tests/test_tx.py', affected_tests.select(['tests/test_tx.py'])[0])
        self.assertIn('tests/test_tx.py', affected_tests.select(['tmux/tx'])[0])

    def test_the_check_ci_and_packaging_select_the_whole_suite(self):
        for change in ('scripts/check.py', '.github/workflows/test.yml', 'requirements-test.txt'):
            with self.subTest(change=change):
                tests, _, full = affected_tests.select([change])
                self.assertTrue(full)
                self.assertGreater(len(tests), 100)

    def test_planning_records_select_nothing(self):
        tests, _, full = affected_tests.select(['tasks/items/TOOLSET-001-00.md'])
        self.assertEqual(([t for t in tests if t != SELF], full), ([], False))


if __name__ == '__main__':
    unittest.main()
