"""Discovery must never execute the standalone model-backed harness."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class LiveHarnessImportTests(unittest.TestCase):
    def test_import_skips_without_profile_writes(self):
        script = Path(__file__).with_name('test_goal_gap_regression.py')
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as home:
            env = dict(os.environ, HERMES_HOME=home, PYTHONDONTWRITEBYTECODE='1')
            code = ('import runpy, unittest\ntry:\n'
                    ' runpy.run_path(__import__("sys").argv[1], run_name="offline_import_probe")\n'
                    'except unittest.SkipTest:\n pass\n')
            result = subprocess.run([sys.executable, '-c', code, str(script)],
                                    env=env, capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(list(Path(home).iterdir()), [])
