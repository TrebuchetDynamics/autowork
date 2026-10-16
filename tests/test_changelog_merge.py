"""CHANGELOG.md entries added concurrently merge without a conflict; real Git only."""
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ChangelogMergeTests(unittest.TestCase):
    def git(self, *args):
        env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
        return subprocess.run(['git', '-C', str(self.repo), *args], env=env, capture_output=True, text=True)

    def entry(self, branch, text):
        self.git('switch', '-q', branch)
        path = self.repo / 'CHANGELOG.md'
        path.write_text(path.read_text().replace('### Fixed\n\n', f'### Fixed\n\n- {text}\n', 1))
        self.git('commit', '-qam', text)

    def test_two_entries_at_the_same_spot_both_survive_the_merge(self):
        with tempfile.TemporaryDirectory() as folder:
            self.repo = Path(folder)
            self.git('init', '-q', '-b', 'main')
            self.git('config', 'user.name', 'Fixture')
            self.git('config', 'user.email', 'fixture@example.invalid')
            shutil.copy(ROOT / '.gitattributes', self.repo / '.gitattributes')
            (self.repo / 'CHANGELOG.md').write_text('# Changelog\n\n## Unreleased\n\n### Fixed\n\n- Older entry.\n')
            self.git('add', '.')
            self.git('commit', '-qm', 'base')
            self.git('branch', 'other')
            self.entry('main', 'Entry from this session.')
            self.entry('other', 'Entry from another session.')
            self.git('switch', '-q', 'main')
            merged = self.git('merge', '--no-edit', 'other')
            self.assertEqual(merged.returncode, 0, merged.stdout + merged.stderr)
            text = (self.repo / 'CHANGELOG.md').read_text()
            for line in ('- Entry from this session.', '- Entry from another session.', '- Older entry.'):
                self.assertEqual(text.count(line), 1, text)
            self.assertNotIn('<<<<<<<', text)

    def test_only_the_changelog_merges_by_union(self):
        rules = (ROOT / '.gitattributes').read_text().splitlines()
        self.assertEqual([r for r in rules if 'merge=' in r and not r.startswith('#')], ['CHANGELOG.md merge=union'])


if __name__ == '__main__':
    unittest.main()
