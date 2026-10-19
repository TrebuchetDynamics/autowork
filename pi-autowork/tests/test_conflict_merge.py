"""A conflict-held commit is merged with the session in its worktree once (TOOLSET-157-cd)."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class ConflictMergeTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        self.task = Path(tmp.name) / 'task'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'base')
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'autowork/A', str(self.task), 'main')
        self.git(self.task, 'commit', '-q', '--allow-empty', '-m', 'A')
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'the session moved on')
        runner = Coordinator.__new__(Coordinator)
        runner.repo, runner.integ, runner.stop, runner.seen = str(self.repo), str(self.repo), False, {}
        self.calls = []
        runner.engine = lambda *args: self.calls.append(args) or {'outcome': 'MERGED'}
        self.runner = runner

    def git(self, where, *args):
        return subprocess.run(['git', '-C', str(where), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    def test_a_commit_adopted_once_gets_no_second_merge(self):
        """The engine refused it, and each session revision and reload added a merge commit."""
        head = self.git(self.task, 'rev-parse', 'HEAD')
        row = {'task': 'A', 'worktree': str(self.task), 'merged_base': True}
        self.assertFalse(self.runner.resolve_task_conflict(row))
        self.assertEqual((self.git(self.task, 'rev-parse', 'HEAD'), self.calls), (head, []))
        row['merged_base'] = False
        self.assertTrue(self.runner.resolve_task_conflict(row))
        self.assertEqual(self.calls, [('--parallel-merged', 'A')])
        self.assertNotEqual(self.git(self.task, 'rev-parse', 'HEAD'), head)


if __name__ == '__main__':
    unittest.main()
