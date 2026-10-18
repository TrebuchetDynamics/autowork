"""Worktrees stay under the canonical checkout, including nested agent sessions."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import parallel_dispatch as dispatch
import parallel_state as state

HOOK = Path(__file__).with_name('worktree_paths.py')


class PlacementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo with spaces'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=f@example.invalid',
                 'commit', '--allow-empty', '-qm', 'base')

    def git(self, *args, cwd=None):
        return subprocess.run(['git', '-C', str(cwd or self.repo), *args],
                              check=True, capture_output=True, text=True).stdout.strip()

    def hook(self, event, **fields):
        return subprocess.run([sys.executable, str(HOOK)], input=json.dumps({
            'hook_event_name': event, 'cwd': str(self.repo), **fields}),
            capture_output=True, text=True)

    def test_dispatch_from_linked_checkout_uses_canonical_ignored_directory(self):
        session = self.repo / '.worktrees' / 'session'
        self.git('worktree', 'add', '-q', '--detach', str(session))
        path, branch, _ = dispatch.create_worktree(session, state.common_dir(session), 'A', 'HEAD')
        self.assertEqual(path, self.repo / '.worktrees' / 'autowork-A')
        self.assertEqual(self.git('branch', '--show-current', cwd=path), branch)
        self.assertEqual(self.git('status', '--porcelain', '--untracked-files=all'), '')

    def test_a_submodule_places_worktrees_in_its_checkout_not_its_git_directory(self):
        """A submodule's Git directory is .git/modules/NAME and `git worktree list` shows it as
        the main worktree; a runner's session was created inside it, with no TODO.md."""
        import worktree_paths
        child = Path(self.temp.name) / 'child'
        child.mkdir()
        self.git('init', '-q', '-b', 'main', cwd=child)
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=f@example.invalid',
                 'commit', '--allow-empty', '-qm', 'child', cwd=child)
        self.git('-c', 'protocol.file.allow=always', 'submodule', 'add', '-q', str(child), 'sub')
        sub = self.repo / 'sub'
        self.assertIn('/.git/modules/', self.git('rev-parse', '--path-format=absolute', '--git-common-dir', cwd=sub))
        self.assertEqual(worktree_paths.canonical_root(sub), sub.resolve())
        self.assertEqual(worktree_paths.worktree_path(sub, 'session'), sub.resolve() / '.worktrees' / 'session')

    def test_claude_from_linked_checkout_keeps_its_branch_baseline(self):
        caller = self.repo / '.worktrees' / 'caller'
        self.git('worktree', 'add', '-q', '-b', 'caller', str(caller))
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=f@example.invalid',
                 'commit', '--allow-empty', '-qm', 'caller work', cwd=caller)
        result = self.hook('WorktreeCreate', name='child', cwd=str(caller))
        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(result.stdout.strip())
        self.assertEqual(path, self.repo / '.worktrees' / 'claude-child')
        self.assertEqual(self.git('rev-parse', 'HEAD', cwd=path), self.git('rev-parse', 'HEAD', cwd=caller))

    def test_claude_create_and_remove_preserve_dirty_work(self):
        result = self.hook('WorktreeCreate', name='feature-one')
        self.assertEqual(result.returncode, 0, result.stderr)
        path = self.repo / '.worktrees' / 'claude-feature-one'
        self.assertEqual(result.stdout.strip(), str(path))
        self.assertEqual(self.git('status', '--porcelain'), '')
        (path / 'unfinished.txt').write_text('keep me')
        result = self.hook('WorktreeRemove', worktree_path=str(path))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual((path / 'unfinished.txt').read_text(), 'keep me')
        (path / 'unfinished.txt').unlink()
        self.assertEqual(self.hook('WorktreeRemove', worktree_path=str(path)).returncode, 0)
        self.assertFalse(path.exists())

    def test_claude_remove_keeps_unmerged_commits(self):
        result = self.hook('WorktreeCreate', name='unmerged')
        self.assertEqual(result.returncode, 0, result.stderr)
        path = Path(result.stdout.strip())
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=f@example.invalid',
                 'commit', '--allow-empty', '-qm', 'unfinished', cwd=path)
        self.assertNotEqual(self.hook('WorktreeRemove', worktree_path=str(path)).returncode, 0)
        self.assertTrue(path.exists())

    def test_claude_rejects_escaping_names_and_symlinked_root(self):
        for name in ('../escape', '.', '', '/tmp/escape'):
            self.assertNotEqual(self.hook('WorktreeCreate', name=name).returncode, 0)
        outside = Path(self.temp.name) / 'outside'
        outside.mkdir()
        (self.repo / '.worktrees').symlink_to(outside)
        self.assertNotEqual(self.hook('WorktreeCreate', name='escaped').returncode, 0)
        self.assertEqual(list(outside.iterdir()), [])

    def test_bash_guard_blocks_manual_creation_but_allows_inspection(self):
        for command in ('git worktree add ../repo-task -b task',
                        'git -C /some/repo worktree add /tmp/task',
                        'pwd && git worktree add .worktrees/task -b task'):
            result = self.hook('PreToolUse', tool_input={'command': command})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['hookSpecificOutput']['permissionDecision'], 'deny')
        for command in ('git worktree list', 'git diff', 'python3 -m unittest'):
            result = self.hook('PreToolUse', tool_input={'command': command})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, '')


if __name__ == '__main__':
    unittest.main()
