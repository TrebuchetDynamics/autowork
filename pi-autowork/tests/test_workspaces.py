"""Linking ignored dependencies never shadows tracked content or leaves the checkout."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import workspaces  # noqa: E402


class LinkTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.main = root / 'main'
        self.main.mkdir()
        self.git('init', '-q', '-b', 'main')
        (self.main / '.gitignore').write_text('vendor/\nbuild.cfg\n')
        (self.main / 'src').mkdir()
        (self.main / 'src' / 'app.go').write_text('package app\n')
        self.git('add', '.')
        self.git('-c', 'user.email=f@example.invalid', '-c', 'user.name=F', 'commit', '-qm', 'base')
        (self.main / 'vendor' / 'sdk').mkdir(parents=True)
        (self.main / 'vendor' / 'sdk' / 'lib.c').write_text('int x;\n')
        (self.main / 'build.cfg').write_text('local\n')
        self.tree = root / 'tree'
        self.git('worktree', 'add', '-q', '--detach', str(self.tree))

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.main), *args], check=True, capture_output=True)

    def test_ignored_paths_are_linked_from_the_canonical_checkout(self):
        whole = Path(self.temp.name) / 'whole'
        self.git('worktree', 'add', '-q', '--detach', str(whole))
        self.assertEqual(workspaces.link_ignored(self.main, whole, 'vendor'), [('vendor', 'linked')])  # `vendor/` rule
        self.assertEqual((whole / 'vendor/sdk/lib.c').read_text(), 'int x;\n')
        status = subprocess.run(['git', '-C', str(whole), 'status', '--porcelain', '--untracked-files=all'],
                                capture_output=True, text=True).stdout
        self.assertEqual(status, '')  # a linked `vendor` must not look like a change
        result = dict(workspaces.link_ignored(self.main, self.tree, 'vendor/sdk, build.cfg'))
        self.assertEqual(result, {'vendor/sdk': 'linked', 'build.cfg': 'linked'})
        self.assertEqual((self.tree / 'vendor/sdk/lib.c').read_text(), 'int x;\n')
        self.assertTrue((self.tree / 'build.cfg').is_symlink())
        self.assertEqual(dict(workspaces.link_ignored(self.main, self.tree, 'build.cfg')), {'build.cfg': 'present'})

    def test_tracked_missing_or_escaping_paths_are_refused(self):
        (self.tree / 'src' / 'app.go').unlink()  # even if absent here, src/ is tracked content
        result = dict(workspaces.link_ignored(self.main, self.tree, 'src/app.go, vendor/none, ../x, /etc, .git'))
        self.assertTrue(result['src/app.go'].startswith('refused: not ignored'))
        self.assertEqual(result['vendor/none'], 'refused: missing in the canonical checkout')
        self.assertTrue(result['../x'].startswith('refused: not a plain'))
        self.assertTrue(result['/etc'].startswith('refused: not a plain'))
        self.assertTrue(result['.git'].startswith('refused: not a plain'))
        self.assertFalse((self.tree / 'src' / 'app.go').exists())


if __name__ == '__main__':
    unittest.main()
