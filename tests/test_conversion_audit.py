"""Working-tree and retained-snapshot classification of legacy path references."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.legacy import conversion_audit  # noqa: E402


class ReferenceTests(unittest.TestCase):
    def test_git_metadata_classification_matches_for_worktree_and_retained_hits(self):
        cases = [
            ('.gitattributes', 'TODO.md merge=union\ngoals.json -diff\n', 'git_metadata',
             [(1, ['TODO.md']), (2, ['goals.json'])]),
            ('.gitignore', '# ignored paths\nTODO.md\n', 'git_metadata', [(2, ['TODO.md'])]),
            ('.git-blame-ignore-revs', '# TODO.md and goals.json\n', 'git_metadata',
             [(1, ['TODO.md', 'goals.json'])]),
            ('sub/.gitattributes', 'goals.json -diff\n', 'git_metadata', [(1, ['goals.json'])]),
            ('sub/.gitignore', 'TODO.md\n', 'git_metadata', [(1, ['TODO.md'])]),
            ('read_queue.py', '# queue reader\nopen("TODO.md")\n', 'consumers', [(2, ['TODO.md'])]),
            ('.gitconfig', '# TODO.md\n', 'consumers', [(1, ['TODO.md'])]),
            ('sub/.git-blame-ignore-revs', '# goals.json\n', 'consumers', [(1, ['goals.json'])]),
            ('README.md', 'See TODO.md and goals.json.\n', 'documentation_drift',
             [(1, ['TODO.md', 'goals.json'])]),
        ]
        expected = dict(consumers=[], documentation_drift=[], git_metadata=[])
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)

            def git(*args):
                return subprocess.run(['git', '-C', folder, '-c', 'user.email=f@example.invalid',
                                       '-c', 'user.name=F', *args], check=True, capture_output=True,
                                      text=True).stdout

            self.assertEqual(conversion_audit.references(repo, []), expected)
            self.assertEqual(conversion_audit.retained_references('', 'HEAD'), expected)
            for path, text, group, hits in sorted(cases):
                target = repo / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(text)
                expected[group].extend(dict(path=path, line=line, names=names) for line, names in hits)
            # Inputs/history stay excluded from both inventories.
            for path in ('TODO.md', 'goals.json', 'TODO.archive.md'):
                (repo / path).write_text('TODO.md goals.json\n')
            git('init', '-q')
            git('add', '--force', '.')
            git('commit', '-q', '-m', 'reference fixture')
            tracked = git('ls-files', '-z').split('\0')
            retained = git('grep', '-n', '-z', '-I', '-F', '-e', 'TODO.md', '-e', 'goals.json', 'HEAD', '--')
            self.assertEqual(conversion_audit.references(repo, tracked), expected)
            self.assertEqual(conversion_audit.retained_references(retained, 'HEAD'), expected)


if __name__ == '__main__':
    unittest.main()
