"""Disposable Git fixtures for removing finished worktrees and keeping everything else."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
import unittest.mock

sys.path.insert(0, str(Path(__file__).parent))
import worktree_closeout as closeout  # noqa: E402

SCRIPT = Path(__file__).with_name('worktree_closeout.py')
LONG_AGO = time.time() + 2 * closeout.GRACE_SECONDS


class WorktreeCloseoutTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        self.repo = self.base / 'repo'
        self.repo.mkdir()
        self.git(self.repo, 'init', '-q', '-b', 'main')
        self.git(self.repo, 'config', 'user.name', 'Fixture')
        self.git(self.repo, 'config', 'user.email', 'fixture@example.invalid')
        (self.repo / '.gitignore').write_text('__pycache__/\nreceipts/\n')
        (self.repo / 'file').write_text('base\n')
        self.git(self.repo, 'add', '.')
        self.git(self.repo, 'commit', '-qm', 'base')
        os.environ['PI_AUTOWORK_STATE_DIR'] = str(self.base / 'pi-state')
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_STATE_DIR', None)

    def git(self, root, *args):
        return subprocess.check_output(['git', '-C', str(root), *args], text=True).strip()

    def worktree(self, name, *, commit=True, merge=True):
        path = self.base / name
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'autowork/' + name, str(path), 'main')
        if commit:
            (path / name).write_text(name + '\n')
            self.git(path, 'add', name)
            self.git(path, 'commit', '-qm', name)
        if merge:
            self.git(self.repo, 'merge', '-q', '--ff-only', 'autowork/' + name)
        return path

    def run_closeout(self, **kwargs):
        kwargs.setdefault('now', LONG_AGO)
        kwargs.setdefault('users', lambda paths: {})
        return closeout.closeout(self.repo, **kwargs)

    def kept(self, result, path):
        return next(k['reason'] for k in result['kept'] if k['path'] == str(path))

    def test_report_only_by_default(self):
        done = self.worktree('done')
        result = self.run_closeout()
        self.assertEqual([r['path'] for r in result['removable']], [str(done)])
        self.assertEqual(result['removed'], [])
        self.assertTrue(done.is_dir())

    def test_apply_removes_merged_clean_worktree_and_its_merged_branch(self):
        done = self.worktree('done')
        (done / '__pycache__').mkdir()
        (done / '__pycache__' / 'x.pyc').write_bytes(b'cache')
        result = self.run_closeout(apply=True)
        self.assertEqual(result['removed'], [{'path': str(done), 'branch': 'autowork/done',
                                              'head': self.git(self.repo, 'rev-parse', 'main'),
                                              'branch_deleted': True, 'archive': None}])
        self.assertFalse(done.exists())
        self.assertNotIn(str(done), self.git(self.repo, 'worktree', 'list', '--porcelain'))
        self.assertEqual(self.git(self.repo, 'branch', '--list', 'autowork/done'), '')
        self.assertEqual(self.git(self.repo, 'symbolic-ref', '--short', 'HEAD'), 'main')

    def test_keeps_unmerged_dirty_untracked_and_evidence_worktrees(self):
        unmerged = self.worktree('unmerged', merge=False)
        dirty = self.worktree('dirty')
        (dirty / 'file').write_text('edited\n')
        untracked = self.worktree('untracked')
        (untracked / 'notes').write_text('unfinished\n')
        evidence = self.worktree('evidence')
        (evidence / 'receipts').mkdir()
        (evidence / 'receipts' / 'check.json').write_text('{}')
        result = self.run_closeout(apply=True)
        self.assertEqual(result['removed'], [])
        self.assertIn('not integrated', self.kept(result, unmerged))
        self.assertIn('uncommitted', self.kept(result, dirty))
        self.assertIn('uncommitted', self.kept(result, untracked))
        self.assertIn('ignored files', self.kept(result, evidence))
        for path in (unmerged, dirty, untracked, evidence):
            self.assertTrue(path.is_dir())
        self.assertTrue(self.git(self.repo, 'branch', '--list', 'autowork/unmerged'))

    def test_keeps_locked_recent_and_used_worktrees(self):
        locked = self.worktree('locked')
        self.git(self.repo, 'worktree', 'lock', str(locked))
        recent = self.worktree('recent')
        used = self.worktree('used')
        result = closeout.closeout(self.repo, apply=True, now=time.time(),
                                   users=lambda paths: {str(used): ['pid 42 working directory']})
        self.assertIn('locked', self.kept(result, locked))
        self.assertIn('used', self.kept(result, recent))
        self.assertIn('pid 42', self.kept(result, used))
        self.assertTrue(all(p.is_dir() for p in (locked, recent, used)))

    def test_unknown_process_activity_keeps_everything(self):
        done = self.worktree('done')
        result = self.run_closeout(apply=True, users=lambda paths: None)
        self.assertIn('unknown', self.kept(result, done))
        self.assertTrue(done.is_dir())

    def test_real_process_scan_sees_a_shell_inside_the_worktree(self):
        done = self.worktree('done')
        shell = subprocess.Popen(['sleep', '60'], cwd=done)
        self.addCleanup(shell.wait)
        self.addCleanup(shell.kill)
        found = closeout.users([done])
        if found is None:
            self.skipTest('no /proc process table')
        self.assertTrue(any(f'pid {shell.pid}' in e for e in found.get(str(done), [])), found)

    def test_own_arguments_do_not_count_but_own_working_directory_does(self):
        done = self.worktree('done')
        self.assertEqual(closeout.users([done]).get(str(done)), None)
        here = os.getcwd()
        os.chdir(done)
        self.addCleanup(os.chdir, here)
        self.assertIn('working directory', closeout.users([done])[str(done)][0])

    def test_runner_owned_worktrees_are_left_to_their_runner(self):
        state = Path(os.environ['PI_AUTOWORK_STATE_DIR'])
        state.mkdir()
        pi = self.base / 'pi-state' / 'wt'
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(pi), 'main')
        slot_tree = self.worktree('slot')
        slots = Path(self.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')) / 'autowork-execution' / 'slots'
        slots.mkdir(parents=True)
        (slots / 'T-1.json').write_text(json.dumps({'task_id': 'T-1', 'state': 'integrated', 'attempt': 1,
                                                    'worktree': str(slot_tree)}))
        result = self.run_closeout(apply=True)
        self.assertIn('pi-autowork', self.kept(result, pi))
        self.assertIn('parallel', self.kept(result, slot_tree))
        self.assertEqual(result['removed'], [])

    def test_detached_merged_worktree_is_removed_without_touching_branches(self):
        path = self.base / 'scratch'
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(path), 'main')
        result = self.run_closeout(apply=True)
        self.assertEqual(result['removed'][0]['branch'], None)
        self.assertFalse(path.exists())

    def test_missing_directory_registration_is_forgotten_when_integrated(self):
        gone = self.worktree('gone')
        kept = self.worktree('gone-unmerged', merge=False)
        subprocess.check_call(['rm', '-rf', str(gone), str(kept)])
        result = self.run_closeout(apply=True)
        listing = self.git(self.repo, 'worktree', 'list', '--porcelain').splitlines()
        self.assertNotIn('worktree ' + str(gone), listing)
        self.assertIn('worktree ' + str(kept), listing)
        self.assertEqual([r['path'] for r in result['removed']], [str(gone)])

    def test_only_the_worktree_branch_is_deleted(self):
        done = self.worktree('done')
        self.git(self.repo, 'branch', '-f', 'autowork/other', 'autowork/done')
        result = self.run_closeout(apply=True)
        self.assertFalse(done.exists())
        self.assertTrue(result['removed'][0]['branch_deleted'])
        self.assertTrue(self.git(self.repo, 'branch', '--list', 'autowork/other'))

    def test_explicit_worktree_skips_grace_and_ignores_others(self):
        mine = self.worktree('mine')
        other = self.worktree('other')
        result = closeout.closeout(self.repo, worktrees=[mine], apply=True, now=time.time(),
                                   users=lambda paths: {})
        self.assertEqual([r['path'] for r in result['removed']], [str(mine)])
        self.assertTrue(other.is_dir())

    def test_explicit_path_must_be_a_registered_worktree(self):
        with self.assertRaisesRegex(ValueError, 'not a worktree'):
            self.run_closeout(worktrees=[self.base / 'nowhere'])
        with self.assertRaisesRegex(ValueError, 'canonical'):
            self.run_closeout(worktrees=[self.repo])

    def test_canonical_checkout_must_be_on_main_or_master(self):
        self.git(self.repo, 'switch', '-q', '-c', 'feature')
        with self.assertRaisesRegex(ValueError, 'main or master'):
            self.run_closeout()

    def archived(self, result, path):
        entry = next(r for r in result['removed'] if r['path'] == str(path))
        self.assertTrue(entry['archive'].startswith('refs/archive/worktrees/'), entry)
        return entry['archive']

    def test_archive_keeps_an_unmerged_detached_commit_reachable(self):
        path = self.base / 'pass'
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(path), 'main')
        (path / 'pass.txt').write_text('pass\n')
        self.git(path, 'add', 'pass.txt')
        self.git(path, 'commit', '-qm', 'detached pass')
        head = self.git(path, 'rev-parse', 'HEAD')
        self.assertIn('not integrated', self.kept(self.run_closeout(apply=True), path))
        ref = self.archived(self.run_closeout(apply=True, archive=True), path)
        self.assertFalse(path.exists())
        self.assertEqual(self.git(self.repo, 'rev-parse', ref), head)

    def test_archive_saves_uncommitted_and_untracked_work_as_a_commit(self):
        dirty = self.worktree('dirty', merge=False)
        head = self.git(dirty, 'rev-parse', 'HEAD')
        (dirty / 'file').write_text('edited\n')
        (dirty / 'notes').write_text('unfinished\n')
        result = self.run_closeout(apply=True, archive=True)
        ref = self.archived(result, dirty)
        self.assertFalse(dirty.exists())
        self.assertEqual(self.git(self.repo, 'rev-parse', ref + '^'), head)
        self.assertEqual(self.git(self.repo, 'show', ref + ':file'), 'edited')
        self.assertEqual(self.git(self.repo, 'show', ref + ':notes'), 'unfinished')
        self.assertIn(str(dirty), self.git(self.repo, 'log', '-1', '--format=%B', ref))
        self.assertTrue(self.git(self.repo, 'branch', '--list', 'autowork/dirty'))  # unmerged branch kept
        restored = self.base / 'restored'
        self.git(self.repo, 'worktree', 'add', '-q', '--detach', str(restored), ref)
        self.assertEqual((restored / 'notes').read_text(), 'unfinished\n')

    def test_archive_still_keeps_evidence_locked_used_and_recent_worktrees(self):
        evidence = self.worktree('evidence', merge=False)
        (evidence / 'receipts').mkdir()
        (evidence / 'receipts' / 'check.json').write_text('{}')
        locked = self.worktree('locked', merge=False)
        self.git(self.repo, 'worktree', 'lock', str(locked))
        used = self.worktree('used', merge=False)
        recent = self.worktree('recent', merge=False)
        result = closeout.closeout(self.repo, apply=True, archive=True, now=time.time(),
                                   users=lambda paths: {str(used): ['pid 42 working directory']})
        self.assertEqual(result['removed'], [])
        self.assertIn('ignored files', self.kept(result, evidence))
        self.assertIn('locked', self.kept(result, locked))
        self.assertIn('pid 42', self.kept(result, used))
        self.assertIn('used', self.kept(result, recent))
        self.assertEqual(self.git(self.repo, 'for-each-ref', 'refs/archive'), '')

    def test_archive_of_a_missing_directory_keeps_its_commit(self):
        gone = self.worktree('gone', merge=False)
        head = self.git(gone, 'rev-parse', 'HEAD')
        subprocess.check_call(['rm', '-rf', str(gone)])
        ref = self.archived(self.run_closeout(apply=True, archive=True), gone)
        self.assertEqual(self.git(self.repo, 'rev-parse', ref), head)
        self.assertNotIn('worktree ' + str(gone), self.git(self.repo, 'worktree', 'list', '--porcelain').splitlines())

    def test_archive_refuses_a_worktree_that_changed_after_its_snapshot(self):
        dirty = self.worktree('dirty', merge=False)
        (dirty / 'notes').write_text('first\n')
        real = closeout.snapshot

        def racing(root, head, message):
            ref = real(root, head, message)
            (Path(root) / 'notes').write_text('written after the snapshot\n')
            return ref

        with unittest.mock.patch.object(closeout, 'snapshot', side_effect=racing):
            result = self.run_closeout(apply=True, archive=True)
        self.assertIn('changed during archive', self.kept(result, dirty))
        self.assertEqual((dirty / 'notes').read_text(), 'written after the snapshot\n')

    def test_archive_report_lists_what_would_be_archived_without_writing(self):
        dirty = self.worktree('dirty', merge=False)
        (dirty / 'notes').write_text('x\n')
        result = self.run_closeout(archive=True)
        self.assertEqual([(r['path'], r['archive']) for r in result['removable']], [(str(dirty), True)])
        self.assertTrue(dirty.is_dir())
        self.assertEqual(self.git(self.repo, 'for-each-ref', 'refs/archive'), '')

    def test_cli_reports_json_and_applies(self):
        done = self.worktree('done')
        for name in ('HEAD', 'logs/HEAD', 'ORIG_HEAD'):
            p = Path(self.git(done, 'rev-parse', '--absolute-git-dir')) / name
            if p.exists():
                os.utime(p, (0, 0))
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.repo)], capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual([r['path'] for r in json.loads(out.stdout)['removable']], [str(done)], out.stdout)
        out = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--apply'],
                             capture_output=True, text=True, timeout=60)
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertEqual(json.loads(out.stdout)['removed'][0]['path'], str(done))
        self.assertFalse(done.exists())


if __name__ == '__main__':
    unittest.main()
