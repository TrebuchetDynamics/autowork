"""fix_hotspots ranks files by fix commits and flags fix-of-a-fix chains."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'scripts/fix_hotspots.py'
DAY = 86400
NOW = 1_800_000_000  # fixed "today" for the fixture


class FixHotspotTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='fix hotspots ')
        cls.repo = Path(cls.tmp.name)
        cls.git('init', '-q')
        # (days before NOW, subject, files, body)
        history = [
            (40, 'fix: old fix outside the window', ['old.py'], ''),
            (10, 'feat: add engine', ['engine.py', 'util.py', 'TODO.md'], ''),
            (9, 'fix(engine): first repair', ['engine.py', 'TODO.md'], ''),
            (8.5, 'fix(engine): repair the repair', ['engine.py', 'CHANGELOG.md'], ''),
            (8, 'fix: third time', ['engine.py', 'goals.json'], ''),
            (7, 'docs: explain', ['util.py'], ''),
            (6, 'fix(util): one fix', ['util.py'], ''),
            (2, 'refactor: tidy', ['engine.py'], ''),
            (1, 'feat: follow-up', ['util.py'], 'Fixes: 1234567\n'),
            (0.5, 'prefix fix: not a fix subject', ['other.py'], ''),
            (0.2, 'fixup: not a conventional fix', ['other.py'], ''),
        ]
        for index, (days, subject, files, body) in enumerate(history):
            for name in files:
                path = cls.repo / name
                path.write_text(f'{path.read_text() if path.exists() else ""}{index}\n')
            cls.git('add', '-A')
            stamp = f'@{int(NOW - days * DAY)} +0000'
            message = subject + ('\n\n' + body if body else '')
            cls.git('commit', '-q', '-m', message,
                    env=dict(os.environ, GIT_AUTHOR_DATE=stamp, GIT_COMMITTER_DATE=stamp))

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @classmethod
    def git(cls, *args, env=None):
        return subprocess.run(['git', '-c', 'user.email=t@example.invalid', '-c', 'user.name=T', *args],
                              cwd=cls.repo, check=True, text=True, capture_output=True, env=env).stdout

    def run_tool(self, *args):
        since = f'@{NOW - 14 * DAY}'
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(self.repo), '--since', since,
                                 *args], text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        return result.stdout

    def report(self, *args):
        return json.loads(self.run_tool('--json', *args))

    def test_counts_fixes_and_ratio_per_file(self):
        files = {row['path']: row for row in self.report()['files']}
        self.assertEqual(files['engine.py']['fixes'], 3)
        self.assertEqual(files['engine.py']['commits'], 5)
        self.assertAlmostEqual(files['engine.py']['ratio'], 0.6)
        self.assertEqual(files['util.py']['fixes'], 2, 'the Fixes: trailer counts')
        self.assertEqual(files['util.py']['commits'], 4)

    def test_window_planning_files_and_non_fix_subjects_are_excluded(self):
        paths = {row['path'] for row in self.report()['files']}
        self.assertNotIn('old.py', paths)
        self.assertNotIn('other.py', paths)
        for planning in ('TODO.md', 'CHANGELOG.md', 'goals.json'):
            self.assertNotIn(planning, paths)

    def test_ranking_and_top(self):
        rows = self.report()['files']
        self.assertEqual([row['path'] for row in rows], ['engine.py', 'util.py'])
        self.assertEqual([row['path'] for row in self.report('--top', '1')['files']], ['engine.py'])

    def test_chains_need_three_fixes_within_chain_days(self):
        report = self.report()
        self.assertEqual([chain['path'] for chain in report['chains']], ['engine.py'])
        self.assertEqual(report['chains'][0]['fixes'], 3)
        self.assertTrue({row['path']: row for row in report['files']}['engine.py']['chain'])
        self.assertEqual(self.report('--chain-days', '0.25')['chains'], [])

    def test_table_output(self):
        out = self.run_tool()
        self.assertIn('engine.py', out)
        self.assertIn('chain', out.lower())
        lines = out.splitlines()
        self.assertLess(next(i for i, l in enumerate(lines) if 'engine.py' in l),
                        next(i for i, l in enumerate(lines) if 'util.py' in l))

    def test_runs_on_this_repository(self):
        result = subprocess.run([sys.executable, str(SCRIPT), '--repo', str(ROOT), '--json'],
                                text=True, capture_output=True, timeout=60)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('files', json.loads(result.stdout))


if __name__ == '__main__':
    unittest.main()
