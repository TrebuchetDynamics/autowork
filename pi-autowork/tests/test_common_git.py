"""The runner's read-only Git calls never take the owner's index lock (CI, 2026-10-22).

The coordinator polls the main checkout's planning status every second while it waits.
`git status` refreshes stale stat information in the index when it can, which takes
`.git/index.lock`: an owner's (or a test fixture's) `git commit` at that moment failed with
"index.lock: File exists". Optional locks are for Git's own convenience; the runner's reads
must leave the owner's index alone.
"""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import common  # noqa: E402


class ReadOnlyGitTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        (self.repo / 'tasks').mkdir()
        (self.repo / 'tasks' / 'a.md').write_text('a\n')
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'plan'], check=True)
        self.index = self.repo / '.git' / 'index'

    def stale_stat(self):
        """Make the index's stat data for a clean file stale: a status that may refresh the
        index now rewrites it (and takes index.lock) unless told not to."""
        file = self.repo / 'tasks' / 'a.md'
        info = file.stat()
        os.utime(file, ns=(info.st_atime_ns, info.st_mtime_ns + 2_000_000_000))

    def test_status_poll_leaves_the_owner_index_untouched(self):
        self.stale_stat()
        before = self.index.read_bytes()
        self.assertEqual(common.git(self.repo, 'status', '--porcelain', '--untracked-files=all', '--', 'tasks'), '')
        self.assertEqual(self.index.read_bytes(), before, 'the status poll rewrote the owner index')
        self.assertFalse(self.index.with_name('index.lock').exists())

    def test_git_ok_reads_do_not_take_the_index_lock(self):
        self.stale_stat()
        before = self.index.read_bytes()
        self.assertTrue(common.git_ok(self.repo, 'status', '--porcelain', '--', 'tasks'))
        self.assertEqual(self.index.read_bytes(), before)

    def test_writes_still_lock_and_land(self):
        (self.repo / 'tasks' / 'b.md').write_text('b\n')
        self.assertTrue(common.git_ok(self.repo, 'add', '--', 'tasks/b.md'))
        self.assertEqual(common.git(self.repo, 'diff', '--cached', '--name-only'), 'tasks/b.md')


if __name__ == '__main__':
    unittest.main()
