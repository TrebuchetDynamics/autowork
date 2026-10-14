"""Offline real-Git regressions for the bounded behind-only helper."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/git-pull-merge/scripts/behind-only-realign.sh'


class BehindOnlyRealignTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.scratch = self.root / 'scratch'
        self.scratch.mkdir()
        self.env = {key: value for key, value in os.environ.items()
                    if not key.startswith('GIT_')}
        self.env.update(GIT_CONFIG_NOSYSTEM='1', GIT_CONFIG_GLOBAL=os.devnull,
                        TMPDIR=str(self.scratch), REALIGN_SAFETY_REF='safety/test-realign',
                        REALIGN_EXCLUDE_RE='^$')
        self.git('init', '--initial-branch=main')
        self.git('config', 'user.name', 'Offline Test')
        self.git('config', 'user.email', 'test@example.invalid')
        for name in ('clean.txt', 'dirty.txt', 'deleted.txt'):
            (self.repo / name).write_bytes(b'base\n')
        self.git('add', '.')
        self.git('commit', '-m', 'base')
        self.old = self.git('rev-parse', 'HEAD').stdout.strip()
        self.git('checkout', '-b', 'source')
        for name in ('clean.txt', 'dirty.txt', 'deleted.txt', 'collision.txt'):
            (self.repo / name).write_bytes(b'incoming\n')
        self.git('add', '.')
        self.git('commit', '-m', 'incoming')
        self.new = self.git('rev-parse', 'HEAD').stdout.strip()
        self.git('checkout', 'main')
        self.git('branch', '--set-upstream-to=source', 'main')
        (self.repo / 'dirty.txt').write_bytes(b'local tracked\x00bytes\n')
        (self.repo / 'deleted.txt').unlink()
        (self.repo / 'collision.txt').write_bytes(b'local untracked collision\n')
        (self.repo / 'untracked.txt').write_bytes(b'local untracked\x00bytes\n')
        self.dirty = self.snapshot()

    def git(self, *args):
        return subprocess.run(['git', *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, check=True)

    def snapshot(self):
        return {name: (self.repo / name).read_bytes() if (self.repo / name).exists() else None
                for name in ('dirty.txt', 'deleted.txt', 'collision.txt', 'untracked.txt')}

    def run_helper(self, *args):
        return subprocess.run(['bash', str(SCRIPT), *args], cwd=self.repo, env=self.env,
                              capture_output=True, text=True, timeout=30)

    def assert_success(self, *args):
        result = self.run_helper(*args)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout.strip(), self.new)
        self.assertEqual(self.git('rev-parse', 'safety/test-realign').stdout.strip(), self.old)
        self.assertEqual(self.snapshot(), self.dirty)
        self.assertEqual((self.repo / 'clean.txt').read_bytes(), b'incoming\n')
        self.assertIn('PROOF=ZERO_CHANGED', result.stdout)
        self.assertIn('NEW=' + self.new, result.stdout)

    def test_explicit_full_commit_preserves_writer_bytes(self):
        self.assert_success(self.new)

    def test_explicit_named_ref_preserves_writer_bytes(self):
        self.assert_success('refs/heads/source')

    def test_omitted_source_uses_configured_upstream(self):
        self.assert_success()

    def test_empty_source_uses_configured_upstream(self):
        self.assert_success('')

    def assert_refused(self, diagnostic):
        head = self.git('rev-parse', 'HEAD').stdout
        index = (self.repo / '.git/index').read_bytes()
        files = {path.name: path.read_bytes() for path in self.repo.iterdir() if path.is_file()}
        result = self.run_helper('refs/heads/source')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(diagnostic, result.stdout + result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout, head)
        self.assertEqual((self.repo / '.git/index').read_bytes(), index)
        self.assertEqual({path.name: path.read_bytes() for path in self.repo.iterdir()
                          if path.is_file()}, files)
        self.assertEqual(self.snapshot(), self.dirty)
        self.assertNotIn('refs/heads/safety/test-realign',
                         self.git('for-each-ref', '--format=%(refname)').stdout)

    def test_staged_changes_refuse_without_mutation(self):
        self.git('add', 'dirty.txt')
        self.assert_refused('ABORT: index not pristine')

    def test_diverged_history_refuses_without_mutation(self):
        (self.repo / 'local-only.txt').write_bytes(b'local commit\n')
        self.git('add', 'local-only.txt')
        self.git('commit', '-m', 'local-only')
        self.assert_refused('ABORT: local-only commits exist')

    def test_index_lock_refuses_without_mutation(self):
        lock = self.repo / '.git/index.lock'
        lock.write_bytes(b'writer lock\n')
        self.assert_refused('ABORT: index.lock present')
        self.assertEqual(lock.read_bytes(), b'writer lock\n')


if __name__ == '__main__':
    unittest.main()
