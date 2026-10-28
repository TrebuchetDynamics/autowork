"""Headless pinned Textual qualification for planning controls, without a live model."""
from pathlib import Path
import shutil
import subprocess
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_textual import textual_unavailable


class PlanningUiTests(unittest.TestCase):
    def test_planning_chat_navigation_preview_and_apply(self):
        self.run_pilot('planning_pilot.py')

    def test_fleet_answers_preserve_authority_and_stale_edits(self):
        self.run_pilot('decision_pilot.py')

    def run_pilot(self, name):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', str(Path(__file__).with_name(name))],
                                capture_output=True, text=True, timeout=90)
        if textual_unavailable(result):
            self.skipTest('textual==8.2.8 is not in the offline cache')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
