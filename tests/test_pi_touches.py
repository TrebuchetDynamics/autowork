"""Byte preservation through the Pi file-scope helper's public CLI."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/pi_autowork_touches.py'


class TouchesPreservationTests(unittest.TestCase):
    def test_insertion_preserves_existing_document_bytes(self):
        for newline in ('\n', '\r\n'):
            for spaced in (False, True):
                with self.subTest(newline=repr(newline), spaced=spaced), tempfile.TemporaryDirectory() as tmp:
                    repo = Path(tmp)
                    prefix = '' if spaced else '  '
                    separator = newline * (2 if spaced else 1)
                    target = separator.join([
                        '- [ ] T-1 — Résumé',
                        f'{prefix}Scope: Update café.py',
                        f'{prefix}Acceptance: Keep this text.  ',
                    ]) + newline
                    original = ('# Queue  \n\n## Next\n\n' + target
                                + '\n- [ ] T-2 — Sibling\r\n  Scope: untouched\r\n'
                                + '  Notes: trailing tabs\t\r\n').encode('utf-8')
                    todo = repo / 'TODO.md'
                    todo.write_bytes(original)
                    result = subprocess.run(
                        [sys.executable, str(SCRIPT), 'apply', str(repo), str(ROOT),
                         'T-1', 'café.py, tests/test_cafe.py'],
                        capture_output=True, text=True, timeout=15)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    actual = todo.read_bytes()
                    insertion = (f'{prefix}Touches: café.py, tests/test_cafe.py'
                                 + separator).encode('utf-8')
                    self.assertEqual(actual.count(insertion), 1)
                    self.assertEqual(actual.replace(insertion, b'', 1), original)
                    scope_line = f'{prefix}Scope: Update café.py'.encode('utf-8')
                    self.assertIn(insertion + scope_line, actual)


if __name__ == '__main__':
    unittest.main()
