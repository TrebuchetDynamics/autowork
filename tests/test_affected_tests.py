"""scripts/affected_tests.py selects the test modules a change can reach, with the reason."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

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
                self.assertLess(len(tests), len(affected_tests.check_module().discover_tests(ROOT)))  # not the suite

    def test_a_changed_test_module_selects_itself_and_an_extensionless_script_its_tests(self):
        self.assertIn('tests/test_tx.py', affected_tests.select(['tests/test_tx.py'])[0])
        self.assertIn('tests/test_tx.py', affected_tests.select(['tmux/tx'])[0])

    def test_the_check_ci_and_packaging_select_the_whole_suite(self):
        for change in ('scripts/check.py', '.github/workflows/test.yml', 'requirements-test.txt'):
            with self.subTest(change=change):
                tests, _, full = affected_tests.select([change])
                self.assertTrue(full)
                self.assertGreater(len(tests), 100)

    def test_src_relative_qualified_and_legacy_edges_do_not_confuse_duplicate_stems(self):
        files = {
            'Src/pi_autowork/__init__.py': '',
            'Src/pi_autowork/engine/__init__.py': '',
            'Src/pi_autowork/engine/owner.py': 'VALUE = 1\n',
            'Src/pi_autowork/engine/consumer.py': 'from .owner import VALUE\n',
            'Src/pi_autowork/command.py': 'from .engine import consumer\n',
            'pi-autowork/pi_autowork/command.py': '# old entry\n',
            'unrelated/owner.py': 'VALUE = 2\n',
            'tests/test_public.py': 'import pi_autowork.command\n',
            'tests/test_path.py': 'ENTRY = "pi-autowork/pi_autowork/command.py"\n',
            'tests/test_other.py': 'import unrelated.owner\n',
        }
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            for name, body in files.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(body)
            with patch.object(affected_tests, 'ROOT', root):
                graph = affected_tests.dependency_graph(list(files), conservative=True)
                self.assertIn('Src/pi_autowork/engine/owner.py', graph['Src/pi_autowork/engine/consumer.py'])
                self.assertIn('Src/pi_autowork/command.py', graph['pi-autowork/pi_autowork/command.py'])
                self.assertIn('Src/pi_autowork/__init__.py', graph['tests/test_public.py'])
                self.assertNotIn('unrelated/owner.py', graph['Src/pi_autowork/engine/consumer.py'])
                self.assertNotIn('Src/pi_autowork/engine/owner.py', graph['tests/test_other.py'])

    def test_planning_records_select_nothing(self):
        tests, _, full = affected_tests.select(['tasks/items/TOOLSET-001-00.md'])
        self.assertEqual(([t for t in tests if t != SELF], full), ([], False))


if __name__ == '__main__':
    unittest.main()
