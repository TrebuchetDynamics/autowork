"""Linking ignored dependencies never shadows tracked content or leaves the checkout."""
import os
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

    def test_runner_session_and_scratch_stay_in_canonical_worktree_directory(self):
        from pi_autowork.coordinator import Coordinator
        runner = Coordinator.__new__(Coordinator)
        runner.repo = str(self.main)
        runner.base = 'main'
        runner.toolset = str(Path(__file__).resolve().parents[2])
        runner.state = Path(self.temp.name) / 'state'
        runner.state.mkdir()
        runner.integ = runner.integ_branch = None
        runner.ensure_session()
        self.assertEqual(Path(runner.integ).parent, self.main / '.worktrees')
        scratch = runner.scratch_checkout('probe')
        self.assertEqual(Path(scratch).parent, self.main / '.worktrees')
        runner.drop_scratch(scratch)
        self.assertFalse(Path(scratch).exists())
        runner.drop_scratch(str(self.tree))
        self.assertTrue(self.tree.is_dir())

    def test_missing_legacy_session_restores_inside_canonical_repository(self):
        import json
        from pi_autowork.coordinator import Coordinator
        runner = Coordinator.__new__(Coordinator)
        runner.repo = str(self.main)
        runner.toolset = str(Path(__file__).resolve().parents[2])
        runner.state = Path(self.temp.name) / 'state'
        runner.state.mkdir()
        self.git('branch', 'pi-autowork/legacy')
        old = Path(self.temp.name) / 'old-checkout'
        session = runner.state / 'session.json'
        session.write_text(json.dumps({'branch': 'pi-autowork/legacy', 'path': str(old)}))
        self.assertTrue(runner.load_session())
        self.assertEqual(Path(runner.integ), self.main / '.worktrees/pi-autowork-legacy')
        self.assertFalse(old.exists())
        self.assertEqual(json.loads(session.read_text())['path'], runner.integ)

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
        self.assertEqual((self.tree / 'build.cfg').stat().st_ino, (self.main / 'build.cfg').stat().st_ino)  # hard link
        self.assertEqual(dict(workspaces.link_ignored(self.main, self.tree, 'build.cfg')), {'build.cfg': 'present'})

    def test_a_mirrored_tree_is_ordinary_to_find_and_keeps_inner_symlinks(self):
        """sierra TASK-026: a self-test ran `find` on a linked build directory and saw nothing."""
        (self.main / 'vendor' / 'build').mkdir()
        (self.main / 'vendor' / 'build' / 'srsenb').write_text('binary\n')
        os.symlink('build/srsenb', self.main / 'vendor' / 'current')
        self.assertEqual(dict(workspaces.link_ignored(self.main, self.tree, 'vendor')), {'vendor': 'linked'})
        found = subprocess.run(['find', str(self.tree / 'vendor'), '-type', 'f'], capture_output=True, text=True).stdout
        self.assertIn('vendor/build/srsenb', found)
        self.assertIn('vendor/sdk/lib.c', found)
        self.assertFalse((self.tree / 'vendor' / 'build').is_symlink())
        self.assertEqual(os.readlink(self.tree / 'vendor' / 'current'), 'build/srsenb')

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
