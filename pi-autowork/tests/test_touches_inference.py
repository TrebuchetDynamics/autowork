"""Widening Touches the runner inferred, and never a list a person wrote or edited."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
HELPER = ROOT / 'pi-autowork/pi_autowork/touches_inference.py'
SHIM = ROOT / 'scripts/pi_autowork_touches.py'


class WidenTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        self.todo = self.repo / 'TODO.md'
        self.todo.write_bytes('# Q\n\n## Next\n\n- [ ] T-1 — Café\n  Scope: x\n  Touches: a.py\n'
                              '  Acceptance: y\n\n- [ ] T-2 — Other\r\n  Touches: a.py\r\n'.encode())

    def run_helper(self, *args, script=HELPER):
        return subprocess.run([sys.executable, str(script), *args], capture_output=True, text=True)

    def test_widen_adds_paths_and_keeps_every_other_byte(self):
        before = self.todo.read_bytes()
        result = self.run_helper('widen', str(self.repo), str(ROOT), 'T-1', 'a.py', 'lib/b.py, a.py')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'a.py, lib/b.py')
        self.assertEqual(self.todo.read_bytes(), before.replace(b'  Touches: a.py\n  Acceptance',
                                                               b'  Touches: a.py, lib/b.py\n  Acceptance'))

    def test_touches_changed_since_recording_are_not_widened(self):
        before = self.todo.read_bytes()
        result = self.run_helper('widen', str(self.repo), str(ROOT), 'T-1', 'other.py', 'lib/b.py')
        self.assertEqual(result.returncode, 1)
        self.assertIn('changed since the runner recorded them', result.stderr)
        result = self.run_helper('widen', str(self.repo), str(ROOT), 'T-1', 'a.py', 'TODO.md')
        self.assertIn('coordinator-owned file', result.stderr)
        self.assertEqual(self.todo.read_bytes(), before)

    def test_the_old_script_path_still_works(self):
        result = self.run_helper('widen', str(self.repo), str(ROOT), 'T-1', 'a.py', 'c.py', script=SHIM)
        self.assertEqual((result.returncode, result.stdout.strip()), (0, 'a.py, c.py'), result.stderr)


if __name__ == '__main__':
    unittest.main()
