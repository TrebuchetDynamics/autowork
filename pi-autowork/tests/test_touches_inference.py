"""Widening Touches: the runner's own inferred list, and a bounded once-only grant from worker evidence."""
import json
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


class GrantTests(unittest.TestCase):
    """TOOLSET-152-d4: Touches a person wrote widen once by exact files a worker named."""

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.todo = self.repo / 'TODO.md'
        self.todo.write_text('# Q\n\n## Next\n\n- [ ] T-1 — One\n  Scope: x\n  Touches: a.py\n  Acceptance: y\n\n'
                             '- [ ] T-2 — Two\n  Touches: lib/\n  Acceptance: z\n')

    def grant(self, task, extra):
        return subprocess.run([sys.executable, str(HELPER), 'grant', str(self.repo), str(ROOT), task, extra],
                              capture_output=True, text=True)

    def slot(self, task, state='running'):
        folder = self.repo / '.git/autowork-execution/slots'
        folder.mkdir(parents=True, exist_ok=True)
        (folder / f'{task}.json').write_text(json.dumps({'task_id': task, 'state': state, 'attempt': 1}))

    def test_up_to_three_exact_files_are_added_once_with_a_note(self):
        result = self.grant('T-1', 'b.py, docs/c.md, build.gradle.kts')
        self.assertEqual((result.returncode, result.stdout.strip()), (0, 'b.py, docs/c.md, build.gradle.kts'),
                         result.stderr)
        self.assertIn('  Touches: a.py, b.py, docs/c.md, build.gradle.kts\n'
                      '  Touches widened by the runner from worker evidence: b.py, docs/c.md, build.gradle.kts\n'
                      '  Acceptance: y\n', self.todo.read_text())
        again = self.grant('T-1', 'd.py')
        self.assertEqual(again.returncode, 1)
        self.assertIn('already widened once', again.stderr)

    def test_anything_beyond_the_bounds_is_refused_and_left_unchanged(self):
        self.slot('T-2')
        before = self.todo.read_bytes()
        for extra, reason in (('b.py, c.py, d.py, e.py', 'at most 3'), ('src/*.py', 'not one exact file'),
                              ('src/', 'not one exact file'), ('BLOCKERS.md', 'coordinator-owned'),
                              ('goals.json', 'coordinator-owned'), ('../x.py', 'repository-relative'),
                              ('lib/x.py', 'may belong to T-2'), ('a.py', 'already in Touches')):
            with self.subTest(extra=extra):
                result = self.grant('T-1', extra)
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn(reason, result.stderr)
        self.assertEqual(self.todo.read_bytes(), before)

    def test_a_closed_slot_does_not_own_its_files(self):
        self.slot('T-2', 'closed')
        self.assertEqual(self.grant('T-1', 'lib/x.py').returncode, 0)


if __name__ == '__main__':
    unittest.main()
