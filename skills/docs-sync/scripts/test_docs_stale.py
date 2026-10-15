"""Stale document roles from covered-path Git history through the actual docs.py CLI."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('docs.py')
GIT_ENV = {key: value for key, value in os.environ.items() if not key.startswith('GIT_')}
GIT_ENV.update(GIT_AUTHOR_NAME='Fixture', GIT_AUTHOR_EMAIL='fixture@example.invalid',
               GIT_COMMITTER_NAME='Fixture', GIT_COMMITTER_EMAIL='fixture@example.invalid',
               GIT_CONFIG_GLOBAL=os.devnull, GIT_CONFIG_NOSYSTEM='1')


class DocsStaleTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.git('init', '-q', '-b', 'main')
        (self.repo / 'src').mkdir()
        (self.repo / 'docs').mkdir()
        (self.repo / 'src' / 'app.py').write_text('one\n')
        (self.repo / 'src' / 'other.py').write_text('one\n')
        (self.repo / 'README.md').write_text('# App\n')
        self.base = self.commit('base')
        self.roles = {
            'readme': {'status': 'maintained', 'path': 'README.md',
                       'covers': ['src/app.py'], 'verified_at': self.base},
            'architecture': {'status': 'maintained', 'path': 'README.md',
                             'covers': ['src/other.py'], 'verified_at': self.base},
            'changelog': {'status': 'maintained', 'path': 'README.md'},
        }
        self.write()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=GIT_ENV, check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit(self, message):
        self.git('add', '-A')
        self.git('commit', '-q', '-m', message)
        return self.git('rev-parse', '--short=12', 'HEAD')

    def write(self):
        (self.repo / 'docs').mkdir(exist_ok=True)
        (self.repo / 'docs' / 'roles.json').write_text(json.dumps({'version': 1, 'roles': self.roles}))

    def cli(self, expected=0, env=None):
        before = {p: p.read_bytes() for p in self.repo.rglob('*') if p.is_file() and '.git' not in p.parts}
        result = subprocess.run([sys.executable, str(SCRIPT), 'stale', str(self.repo)],
                                capture_output=True, text=True, timeout=20, env=env or GIT_ENV)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        self.assertNotIn('Traceback', result.stderr)
        self.assertEqual(before, {p: p.read_bytes() for p in self.repo.rglob('*')
                                  if p.is_file() and '.git' not in p.parts})
        return result.stdout + result.stderr

    def test_unchanged_covered_paths_report_nothing(self):
        (self.repo / 'unrelated.txt').write_text('x\n')
        self.commit('unrelated')
        self.assertEqual(self.cli().strip(), 'ok')

    def test_covered_change_after_verification_reports_role_and_commit(self):
        (self.repo / 'src' / 'app.py').write_text('two\n')
        changed = self.commit('change app')
        out = self.cli(expected=1)
        self.assertIn(f'readme: stale since {self.base}', out)
        self.assertIn(changed[:7], out)
        self.assertNotIn('architecture', out)

    def test_covered_directory_matches_nested_changes(self):
        self.roles['readme']['covers'] = ['src']
        self.write()
        self.commit('manifest')
        (self.repo / 'src' / 'other.py').write_text('two\n')
        self.commit('change other')
        out = self.cli(expected=1)
        self.assertIn('readme: stale', out)
        self.assertIn('architecture: stale', out)

    def test_unknown_and_non_ancestor_commits_are_unverifiable(self):
        self.git('checkout', '-q', '-b', 'side')
        (self.repo / 'side.txt').write_text('x\n')
        side = self.commit('side')
        self.git('checkout', '-q', 'main')
        self.roles['readme']['verified_at'] = side
        self.roles['architecture']['verified_at'] = 'abcdef1234567'
        self.write()
        out = self.cli(expected=1)
        self.assertIn(f'readme: unverifiable: {side} is not an ancestor of HEAD', out)
        self.assertIn('architecture: unverifiable: abcdef1234567 is not a known commit', out)

    def test_covered_role_without_verified_commit_is_unverifiable(self):
        del self.roles['readme']['verified_at']
        self.write()
        self.assertIn('readme: unverifiable: no verified_at commit', self.cli(expected=1))

    def test_git_environment_overrides_do_not_redirect_history(self):
        other = tempfile.TemporaryDirectory()
        self.addCleanup(other.cleanup)
        env = dict(GIT_ENV, GIT_DIR=str(Path(other.name) / 'missing.git'),
                   GIT_WORK_TREE=other.name)
        self.assertEqual(self.cli(env=env).strip(), 'ok')

    def test_non_git_repository_and_missing_manifest(self):
        plain = tempfile.TemporaryDirectory()
        self.addCleanup(plain.cleanup)
        (Path(plain.name) / 'docs').mkdir()
        (Path(plain.name) / 'docs' / 'roles.json').write_text(
            json.dumps({'version': 1, 'roles': self.roles}))
        result = subprocess.run([sys.executable, str(SCRIPT), 'stale', plain.name],
                                capture_output=True, text=True, timeout=20, env=GIT_ENV)
        self.assertEqual(result.returncode, 1)
        self.assertIn('not a Git repository', result.stdout + result.stderr)
        (self.repo / 'docs' / 'roles.json').unlink()
        self.assertIn('no manifest', self.cli())


if __name__ == '__main__':
    unittest.main()
