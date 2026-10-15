"""Offline real-Git regressions for the bounded behind-only helper."""
import os
from pathlib import Path
import subprocess
import tempfile
import unittest


SCRIPT = Path(__file__).resolve().parents[1] / 'skills/git-commit-push/scripts/behind-only-realign.sh'


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
        (self.repo / 'tracked-directory').mkdir()
        (self.repo / 'tracked-directory/base.txt').write_bytes(b'base\n')
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
        self.assert_index_matches_source()

    def test_explicit_full_commit_preserves_writer_bytes(self):
        self.assert_success(self.new)

    def test_explicit_named_ref_preserves_writer_bytes(self):
        self.assert_success('refs/heads/source')

    def test_omitted_source_uses_configured_upstream(self):
        self.assert_success()

    def test_empty_source_uses_configured_upstream(self):
        self.assert_success('')

    def extend_source(self, change):
        # A separate checkout keeps every local writer byte in the test repo.
        source = self.root / 'source'
        self.git('worktree', 'add', str(source), 'source')
        change(source)
        subprocess.run(['git', 'add', '-A'], cwd=source, env=self.env, check=True,
                       capture_output=True)
        subprocess.run(['git', 'commit', '-m', 'extra incoming'], cwd=source,
                       env=self.env, check=True, capture_output=True)
        self.new = self.git('rev-parse', 'source').stdout.strip()

    def assert_index_matches_source(self):
        self.assertEqual(self.git('write-tree').stdout.strip(),
                         self.git('rev-parse', self.new + '^{tree}').stdout.strip())

    def test_clean_addition_materializes(self):
        def change(source):
            (source / 'nested').mkdir()
            (source / 'nested/new.txt').write_bytes(b'new file\n')
        self.extend_source(change)
        self.assert_success(self.new)
        self.assertEqual((self.repo / 'nested/new.txt').read_bytes(), b'new file\n')
        self.assert_index_matches_source()

    def test_clean_deletion_disappears(self):
        self.extend_source(lambda source: (source / 'clean.txt').unlink())
        result = self.run_helper(self.new)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / 'clean.txt').exists())
        self.assertEqual(self.snapshot(), self.dirty)
        self.assert_index_matches_source()

    def test_dirty_incoming_deletions_preserve_bytes_and_absence(self):
        def change(source):
            (source / 'dirty.txt').unlink()
            (source / 'deleted.txt').unlink()
        self.extend_source(change)
        self.assert_success(self.new)
        self.assert_index_matches_source()

    def test_ignored_addition_collision_preserves_local_bytes(self):
        self.extend_source(lambda source: (source / 'ignored.txt').write_bytes(b'incoming'))
        (self.repo / '.git/info/exclude').write_text('ignored.txt\n')
        (self.repo / 'ignored.txt').write_bytes(b'local ignored')
        self.assert_success(self.new)
        self.assertEqual((self.repo / 'ignored.txt').read_bytes(), b'local ignored')
        self.assert_index_matches_source()

    def test_incoming_file_over_local_directory_refuses(self):
        self.extend_source(lambda source: (source / 'directory').write_bytes(b'incoming'))
        (self.repo / 'directory').mkdir()
        (self.repo / 'directory/local.txt').write_bytes(b'local')
        self.assert_refused('ABORT: unsupported collision')
        self.assertEqual((self.repo / 'directory/local.txt').read_bytes(), b'local')

    def test_incoming_directory_under_untracked_file_refuses(self):
        def change(source):
            (source / 'parent').mkdir()
            (source / 'parent/new.txt').write_bytes(b'incoming')
        self.extend_source(change)
        (self.repo / 'parent').write_bytes(b'local')
        self.assert_refused('ABORT: unsupported collision')

    def test_incoming_directory_under_symlink_refuses(self):
        def change(source):
            (source / 'parent').mkdir()
            (source / 'parent/new.txt').write_bytes(b'incoming')
        self.extend_source(change)
        target = self.root / 'outside'
        target.mkdir()
        (self.repo / 'parent').symlink_to(target, target_is_directory=True)
        self.assert_refused('ABORT: unsupported collision')
        self.assertEqual(list(target.iterdir()), [])

    def test_tracked_file_to_directory_refuses_before_mutation(self):
        def change(source):
            (source / 'clean.txt').unlink()
            (source / 'clean.txt').mkdir()
            (source / 'clean.txt/new.txt').write_bytes(b'incoming')
        self.extend_source(change)
        self.assert_refused('ABORT: unsupported collision')

    def test_unusual_added_path_is_literal(self):
        name = 'new\n[glob]*.txt'
        self.extend_source(lambda source: (source / name).write_bytes(b'incoming'))
        self.assert_success(self.new)
        self.assertEqual((self.repo / name).read_bytes(), b'incoming')
        self.assert_index_matches_source()

    def test_unusual_dirty_path_preserves_bytes(self):
        name = 'new\n[glob]*.txt'
        self.extend_source(lambda source: (source / name).write_bytes(b'incoming'))
        (self.repo / name).write_bytes(b'writer')
        self.assert_success(self.new)
        self.assertEqual((self.repo / name).read_bytes(), b'writer')
        self.assert_index_matches_source()

    def test_dangling_untracked_symlink_preserves_target(self):
        (self.repo / 'collision.txt').unlink()
        (self.repo / 'collision.txt').symlink_to('missing-target')
        self.dirty = self.snapshot()
        self.assert_success(self.new)
        self.assertEqual(os.readlink(self.repo / 'collision.txt'), 'missing-target')
        self.assert_index_matches_source()

    def test_clean_rename_materializes_destination_and_removes_source(self):
        self.extend_source(lambda source: (source / 'clean.txt').rename(source / 'renamed.txt'))
        result = self.run_helper(self.new)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertFalse((self.repo / 'clean.txt').exists())
        self.assertEqual((self.repo / 'renamed.txt').read_bytes(), b'incoming\n')
        self.assertEqual(self.snapshot(), self.dirty)
        self.assert_index_matches_source()

    def test_hidden_assume_unchanged_refuses(self):
        self.git('update-index', '--assume-unchanged', 'dirty.txt')
        self.assert_refused('ABORT: hidden index flags')

    def test_hidden_skip_worktree_refuses(self):
        self.git('update-index', '--skip-worktree', 'dirty.txt')
        self.assert_refused('ABORT: hidden index flags')

    def test_tracked_directory_to_file_refuses_even_when_locally_absent(self):
        def change(source):
            (source / 'tracked-directory/base.txt').unlink()
            (source / 'tracked-directory').rmdir()
            (source / 'tracked-directory').write_bytes(b'incoming')
        self.extend_source(change)
        (self.repo / 'tracked-directory/base.txt').unlink()
        (self.repo / 'tracked-directory').rmdir()
        self.assert_refused('ABORT: unsupported collision')

    def test_ignored_parent_file_refuses(self):
        def change(source):
            (source / 'parent').mkdir()
            (source / 'parent/new.txt').write_bytes(b'incoming')
        self.extend_source(change)
        (self.repo / '.git/info/exclude').write_text('parent\n')
        (self.repo / 'parent').write_bytes(b'ignored writer')
        self.assert_refused('ABORT: unsupported collision')

    def test_clean_added_symlink_materializes(self):
        self.extend_source(lambda source: (source / 'link').symlink_to('clean.txt'))
        self.assert_success(self.new)
        self.assertEqual(os.readlink(self.repo / 'link'), 'clean.txt')
        self.assert_index_matches_source()

    def test_preexisting_matching_safety_ref_is_retained(self):
        self.git('branch', 'safety/test-realign', self.old)
        self.assert_success(self.new)

    def test_preexisting_wrong_safety_ref_refuses(self):
        self.git('branch', 'safety/test-realign', self.new)
        self.assert_refused('ABORT: safety ref does not preserve OLD')

    def worktree_snapshot(self):
        result = {}
        for base, directories, files in os.walk(self.repo, followlinks=False):
            if Path(base) == self.repo:
                directories.remove('.git')
            for name in directories + files:
                path = Path(base) / name
                relative = str(path.relative_to(self.repo))
                if path.is_symlink():
                    result[relative] = ('symlink', os.readlink(path))
                elif path.is_dir():
                    result[relative] = ('directory',)
                else:
                    result[relative] = ('file', path.read_bytes(), path.stat().st_mode)
        return result

    def assert_refused(self, diagnostic):
        head = self.git('rev-parse', 'HEAD').stdout
        index = (self.repo / '.git/index').read_bytes()
        refs = self.git('for-each-ref', '--format=%(refname) %(objectname)').stdout
        files = self.worktree_snapshot()
        result = self.run_helper('refs/heads/source')
        self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn(diagnostic, result.stdout + result.stderr)
        self.assertEqual(self.git('rev-parse', 'HEAD').stdout, head)
        self.assertEqual((self.repo / '.git/index').read_bytes(), index)
        self.assertEqual(self.worktree_snapshot(), files)
        self.assertEqual(self.snapshot(), self.dirty)
        self.assertEqual(self.git('for-each-ref', '--format=%(refname) %(objectname)').stdout,
                         refs)

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
