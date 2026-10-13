"""Disposable Git fixtures for the worker's validation/commit gate."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


class FinishTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        (self.root / 'owned').write_text('base')
        (self.root / 'foreign').write_text('base')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        (self.root / 'owned').write_text('task')
        (self.root / 'foreign').write_text('someone else')
        self.git('add', 'foreign')
        self.index = (self.root / '.git/index').read_bytes()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True).strip()

    def finish(self, check='pass', files=('owned',), env=None):
        script = Path(__file__).with_name('finish_task.py')
        self.assertTrue(script.exists(), 'missing executable validation/commit completion gate')
        result = subprocess.run([sys.executable, str(script), '--repo', str(self.root),
            '--profile', 'fixture', '--card', 'one', '--message', 'Implement task',
            '--check-json', json.dumps([sys.executable, '-c', check]), '--', *files],
            text=True, capture_output=True, timeout=30, env=env)
        return result, json.loads(result.stdout)

    def preserved(self):
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.base)
        self.assertEqual((self.root / '.git/index').read_bytes(), self.index)
        self.assertEqual((self.root / 'foreign').read_text(), 'someone else')

    def test_pass_commits_only_owned_files_and_reports_exact_sha(self):
        result, receipt = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'committed')
        self.assertEqual(self.git('show', receipt['commit'] + ':owned'), 'task')
        self.assertEqual(self.git('show', receipt['commit'] + ':foreign'), 'base')
        self.assertEqual(self.git('rev-parse', receipt['branch']), receipt['commit'])
        self.preserved()

    def routed_repository(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        other = Path(temporary.name)
        for args in (('init', '-q'), ('config', 'user.name', 'Other'),
                     ('config', 'user.email', 'other@example.invalid')):
            subprocess.run(['git', '-C', str(other), *args], check=True)
        (other / 'owned').write_text('foreign base')
        subprocess.run(['git', '-C', str(other), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(other), 'commit', '-qm', 'foreign base'], check=True)
        (other / 'owned').write_text('unvalidated foreign edit')
        subprocess.run(['git', '-C', str(other), 'add', 'owned'], check=True)
        return other, dict(os.environ, GIT_DIR=str(other / '.git'),
                           GIT_WORK_TREE=str(other), GIT_INDEX_FILE=str(other / '.git/index'))

    def foreign_snapshot(self, other):
        refs = subprocess.check_output(['git', '-C', str(other), 'show-ref'])
        return refs, (other / '.git/index').read_bytes(), (other / 'owned').read_bytes()

    def test_wrapper_cannot_be_routed_to_foreign_repository(self):
        other, env = self.routed_repository()
        before = self.foreign_snapshot(other)
        result, receipt = self.finish(env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('rev-parse', receipt['branch']), receipt['commit'])
        self.assertEqual(self.git('show', receipt['commit'] + ':owned'), 'task')
        self.assertEqual(self.foreign_snapshot(other), before)
        self.preserved()

    def test_direct_script_cannot_be_routed_to_foreign_repository(self):
        other, env = self.routed_repository()
        before = self.foreign_snapshot(other)
        result = subprocess.run(['bash', str(Path(__file__).with_name('agent_commit.sh')),
            str(self.root), 'fixture', 'one', 'Implement task', 'owned'],
            env=env, text=True, capture_output=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        branch, sha = result.stdout.split()
        self.assertEqual(self.git('rev-parse', branch), sha)
        self.assertEqual(self.git('show', sha + ':owned'), 'task')
        self.assertEqual(self.foreign_snapshot(other), before)
        self.preserved()

    def test_acceptance_git_uses_requested_repository_and_its_real_index(self):
        other, env = self.routed_repository()
        before = self.foreign_snapshot(other)
        check = (
            'import subprocess; from pathlib import Path; '
            "assert Path(subprocess.check_output(['git', 'rev-parse', '--show-toplevel'], text=True).strip()) == Path.cwd(); "
            "assert subprocess.check_output(['git', 'show', ':foreign'], text=True) == 'someone else'"
        )
        result, receipt = self.finish(check, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'committed')
        self.assertEqual(self.foreign_snapshot(other), before)
        self.preserved()

    def test_index_override_alone_does_not_hijack_acceptance_or_commit(self):
        other, _ = self.routed_repository()
        before = self.foreign_snapshot(other)
        env = dict(os.environ, GIT_INDEX_FILE=str(other / '.git/index'))
        check = "import subprocess; assert subprocess.check_output(['git', 'show', ':foreign'], text=True) == 'someone else'"
        result, receipt = self.finish(check, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('show', receipt['commit'] + ':owned'), 'task')
        self.assertEqual(self.foreign_snapshot(other), before)
        self.preserved()

    def test_requested_repository_reference_hook_is_still_enforced(self):
        other, env = self.routed_repository()
        hook = self.root / '.git/hooks/reference-transaction'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        before = self.foreign_snapshot(other)
        result, receipt = self.finish(env=env)
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.assertEqual(self.foreign_snapshot(other), before)
        self.preserved()

    @unittest.skipUnless(os.name == 'posix', 'process group termination requires POSIX')
    def test_timed_out_acceptance_stops_child_writers(self):
        import time, finish_task
        child = 'import time; from pathlib import Path; time.sleep(0.4); Path("escaped").touch()'
        parent = f'import subprocess, sys, time; subprocess.Popen([sys.executable, "-c", {child!r}]); time.sleep(5)'
        receipt, code = finish_task.finish(self.root, 'fixture', 'one', 'Task', ['owned'],
                                           [[sys.executable, '-c', parent]], 0.15)
        self.assertEqual(code, 1)
        self.assertEqual(receipt['status'], 'validation_failed')
        time.sleep(0.5)
        self.assertFalse((self.root/'escaped').exists(), 'timed-out acceptance left a writer alive')
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.preserved()

    def test_failed_validation_never_creates_commit(self):
        result, receipt = self.finish('raise SystemExit(7)')
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'validation_failed')
        self.assertNotIn('commit', receipt)
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.preserved()

    def test_noop_is_explicit_and_does_not_claim_new_commit(self):
        (self.root / 'owned').write_text('base')
        result, receipt = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'no_changes')
        self.assertNotIn('commit', receipt)
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')

    def test_commit_failure_keeps_task_incomplete_and_preserves_index(self):
        (self.root / '.git/refs/heads/agent').write_text('prevent branch creation')
        result, receipt = self.finish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertNotIn('commit', receipt)
        self.preserved()

    def test_broad_path_refused_without_commit(self):
        result, receipt = self.finish(files=('.',))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.preserved()

    def test_check_changing_owned_source_requires_revalidation(self):
        result, receipt = self.finish("from pathlib import Path; Path('owned').write_text('changed by check')")
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'source_changed')
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')

    def test_missing_untracked_filename_is_not_a_noop(self):
        result, receipt = self.finish(files=('typo',))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertIn('does not exist', receipt['error'])
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.preserved()

    def test_deleted_owned_file_is_committed(self):
        (self.root / 'owned').unlink()
        result, receipt = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'committed')
        self.assertNotIn('owned', self.git('ls-tree', '--name-only', receipt['commit']))
        self.preserved()

    def test_repeated_deletion_is_noop_and_allows_review_fix(self):
        (self.root / 'owned').unlink()
        _, first = self.finish()
        result, receipt = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'no_changes')
        self.assertEqual(receipt['source_commit'], first['commit'])
        (self.root / 'review-fix').write_text('review correction')
        result, receipt = self.finish(files=('owned', 'review-fix'))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'committed')
        self.assertNotIn('owned', self.git('ls-tree', '--name-only', receipt['commit']))
        self.assertEqual(self.git('show', receipt['commit'] + ':review-fix'), 'review correction')
        self.preserved()

    def test_repeated_deletion_of_file_created_on_task_branch_is_noop(self):
        (self.root / 'created').write_text('task file')
        result, _ = self.finish(files=('created',))
        self.assertEqual(result.returncode, 0, result.stderr)
        (self.root / 'created').unlink()
        result, deleted = self.finish(files=('created',))
        self.assertEqual(result.returncode, 0, result.stderr)
        result, receipt = self.finish(files=('created',))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'no_changes')
        self.assertEqual(receipt['source_commit'], deleted['commit'])
        self.preserved()

    def test_repeated_gate_reports_no_changes_after_existing_commit(self):
        _, first = self.finish()
        result, receipt = self.finish()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(receipt['status'], 'no_changes')
        self.assertEqual(receipt['source_commit'], first['commit'])
        self.preserved()

    def test_checked_out_task_ref_is_not_moved(self):
        self.git('checkout', '-qb', 'agent/fixture/one')
        result, receipt = self.finish()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertEqual(self.git('rev-parse', 'agent/fixture/one'), self.base)
        self.preserved()

    def test_literal_pathspec_cannot_capture_foreign_files(self):
        result, receipt = self.finish(files=(':(glob)*',))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(receipt['status'], 'commit_failed')
        self.assertEqual(self.git('branch', '--list', 'agent/*'), '')
        self.preserved()

    def test_worker_definition_requires_commit_before_review(self):
        import start_goal
        body = start_goal.build_task_body('Fixture contract')
        self.assertIn('owned changes are committed', start_goal.REVIEW_DOD)
        self.assertIn('finish_task.py', body)
        self.assertIn('commit_failed', body)
        self.assertIn('Explicit no-commit instructions', body)


if __name__ == '__main__':
    unittest.main()
