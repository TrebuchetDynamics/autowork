"""Headless pinned Textual qualification for planning controls, without a live model."""
from pathlib import Path
import shutil
import subprocess
import unittest


class PlanningUiTests(unittest.TestCase):
    def test_planning_chat_navigation_preview_and_apply(self):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', str(Path(__file__).with_name('planning_pilot.py'))],
                                capture_output=True, text=True, timeout=90)
        if result.returncode == 2 and 'offline' in result.stderr.lower() and 'textual' in result.stderr.lower():
            self.skipTest('textual==8.2.8 is not in the offline cache')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
