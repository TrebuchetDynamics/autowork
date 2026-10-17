"""Auto work never pins a submodule to a commit its remote does not have (TOOLSET-168-ff)."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import publishable  # noqa: E402


def git(*args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'protocol.file.allow=always',
                    *args], check=True, capture_output=True)


class PublishableTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        self.remote, seed, self.repo = root / 'sub.git', root / 'seed', root / 'repo'
        git('init', '-q', '--bare', '-b', 'main', str(self.remote))
        git('clone', '-q', str(self.remote), str(seed))
        git('-C', str(seed), 'commit', '-q', '--allow-empty', '-m', 'one')
        git('-C', str(seed), 'push', '-q', 'origin', 'HEAD:main')
        git('init', '-q', '-b', 'main', str(self.repo))
        git('-C', str(self.repo), 'submodule', 'add', '-q', str(self.remote), 'sub')
        git('-C', str(self.repo), 'commit', '-q', '-m', 'add sub')
        self.sub = self.repo / 'sub'
        (self.repo / 'notes.md').write_text('quiet owner work\n')

    def test_a_pointer_to_a_local_only_commit_stays_out_until_it_is_pushed(self):
        git('-C', str(self.sub), 'commit', '-q', '--allow-empty', '-m', 'local only')
        keep, held = publishable(self.repo, ['notes.md', 'sub'])
        self.assertEqual(keep, ['notes.md'])
        self.assertEqual(len(held), 1)
        self.assertIn('Left sub uncommitted: submodule commit', held[0][2])
        git('-C', str(self.sub), 'push', '-q', 'origin', 'HEAD:main')
        self.assertEqual(publishable(self.repo, ['notes.md', 'sub']), (['notes.md', 'sub'], []))

    def test_an_untracked_nested_repository_is_not_added(self):
        git('init', '-q', str(self.repo / 'other'))
        keep, held = publishable(self.repo, ['notes.md', 'other/'])
        self.assertEqual(keep, ['notes.md'])
        self.assertIn('separate Git repository', held[0][2])

    def test_ordinary_files_are_unchanged(self):
        self.assertEqual(publishable(self.repo, ['notes.md']), (['notes.md'], []))


if __name__ == '__main__':
    unittest.main()
