"""tree_guard refuses conflict markers, Python that does not compile and invalid JSON."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/tree_guard.py'
# Built here so this file never holds a marker line itself.
START, MIDDLE, END, BASE = '<' * 7, '=' * 7, '>' * 7, '|' * 7
CONFLICT = f'{START} HEAD\nx = 1\n{MIDDLE}\nx = 2\n{END} topic\n'


class TreeGuardTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory(prefix='tree guard ')
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name)
        self.git('init', '-q')
        self.write('ok.py', 'x = 1\n')
        self.write('data.json', '{"a": 1}\n')
        self.write('notes.md', 'plain text\n')
        self.commit('clean')

    def git(self, *args):
        return subprocess.run(['git', '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], cwd=self.repo, check=True, text=True,
                              capture_output=True).stdout

    def write(self, relative, content):
        target = self.repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(content)

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', 'HEAD').strip()

    def guard(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo), *args],
                              text=True, capture_output=True, timeout=30)

    def test_clean_repo_passes_with_one_line(self):
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(len(result.stdout.strip().splitlines()), 1)
        self.assertIn('OK', result.stdout)

    def test_markers_in_the_worktree_are_reported_with_lines(self):
        self.write('mod.py', CONFLICT)
        self.git('add', 'mod.py')
        result = self.guard()
        self.assertEqual(result.returncode, 1)
        for line in (1, 3, 5):
            self.assertIn(f'mod.py:{line}: conflict marker', result.stdout)

    def test_every_marker_kind_in_any_text_file(self):
        self.write('notes.md', f'a\n{START}\n{BASE} base\n{MIDDLE}\n{END}\n')
        result = self.guard()
        self.assertEqual(result.returncode, 1)
        for line in (2, 3, 4, 5):
            self.assertIn(f'notes.md:{line}: conflict marker', result.stdout)

    def test_lookalike_lines_are_not_markers(self):
        self.write('notes.md', f'{MIDDLE}=\n{START}x\nheading\n{MIDDLE} \n  {END} x\n')
        result = self.guard()
        self.assertEqual(result.returncode, 0, result.stdout)

    def test_untracked_files_are_ignored(self):
        self.write('stray.py', CONFLICT)
        self.assertEqual(self.guard().returncode, 0)

    def test_markers_in_a_commit_are_found_without_checkout(self):
        self.write('mod.py', CONFLICT)
        bad = self.commit('bad')
        self.write('mod.py', 'x = 2\n')
        self.commit('repair')
        self.assertEqual(self.guard().returncode, 0)
        result = self.guard('--rev', bad)
        self.assertEqual(result.returncode, 1)
        self.assertIn('mod.py:1: conflict marker', result.stdout)
        self.assertIn('mod.py:1: python', result.stdout)
        self.assertEqual(self.guard('--rev', 'HEAD').returncode, 0)

    def test_staged_content_is_checked_not_the_worktree(self):
        self.write('mod.py', CONFLICT)
        self.git('add', 'mod.py')
        self.write('mod.py', 'x = 3\n')
        self.assertEqual(self.guard().returncode, 0)
        result = self.guard('--staged')
        self.assertEqual(result.returncode, 1)
        self.assertIn('mod.py:1: conflict marker', result.stdout)

    def test_allowlisted_files_may_hold_markers(self):
        self.write('docs/example.md', '<!-- tree-guard: allow-markers -->\n' + CONFLICT)
        self.git('add', '-A')
        self.assertEqual(self.guard().returncode, 0, self.guard().stdout)
        self.write('docs/late.md', 'one\ntwo\nthree\nfour\nfive\nsix\n'
                   '<!-- tree-guard: allow-markers -->\n' + CONFLICT)
        self.git('add', '-A')
        result = self.guard()
        self.assertEqual(result.returncode, 1, 'the comment only counts near the top')
        self.assertIn('docs/late.md:8: conflict marker', result.stdout)

    def test_allowed_marker_files_still_compile(self):
        self.write('demo.py', '# tree-guard: allow-markers\ntext = """\n' + CONFLICT + '"""\n')
        self.git('add', '-A')
        self.assertEqual(self.guard().returncode, 0, self.guard().stdout)

    def test_syntax_error_is_reported_without_writing_bytecode(self):
        self.write('pkg/broken.py', 'def f(:\n    pass\n')
        self.git('add', '-A')
        result = self.guard()
        self.assertEqual(result.returncode, 1)
        self.assertIn('pkg/broken.py:1: python', result.stdout)
        self.assertFalse(any(self.repo.rglob('__pycache__')))

    def test_invalid_json_is_reported(self):
        self.write('data.json', '{"a": 1,\n}\n')
        result = self.guard()
        self.assertEqual(result.returncode, 1)
        self.assertIn('data.json:2: json', result.stdout)

    def test_binary_files_are_skipped(self):
        (self.repo / 'blob.bin').write_bytes(b'\0' + CONFLICT.encode())
        self.git('add', '-A')
        self.assertEqual(self.guard().returncode, 0)

    def test_paths_limit_the_check(self):
        self.write('a/bad.json', '{')
        self.write('b/ok.json', '{}')
        self.git('add', '-A')
        self.assertEqual(self.guard('b').returncode, 0)
        self.assertEqual(self.guard('a').returncode, 1)

    def test_this_repository_is_clean(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(ROOT)],
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
