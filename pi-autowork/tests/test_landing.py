"""Landing planning commits while a review runs (TOOLSET-190-bf)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class Review:
    """A review still running: what `session_busy` polls."""
    def poll(self):
        return None


class LandingFixture(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        self.integ = Path(tmp.name) / 'session'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'base')
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'pi-autowork/s', str(self.integ), 'main')
        self.git(self.integ, 'commit', '-q', '--allow-empty', '-m', 'docs(blockers): questions for the owner')
        runner = Coordinator.__new__(Coordinator)
        runner.repo, runner.base, runner.integ, runner.integ_branch = str(self.repo), 'main', str(self.integ), 'pi-autowork/s'
        runner.integration, runner.child = {'proc': Review()}, None
        runner.land_soon, runner.landed_at, runner.land_every = True, time.monotonic(), 600
        self.runner = runner
        patcher = mock.patch.dict(os.environ, {'PI_AUTOWORK_PUSH': '0'})  # no upstream in this fixture
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, where, *args):
        return subprocess.run(['git', '-C', str(where), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    def head(self, ref):
        return self.git(self.repo, 'rev-parse', ref)


class LandingBesideReviewTests(LandingFixture):
    def test_a_landing_that_needs_no_merge_does_not_wait_for_the_review(self):
        session = self.head('pi-autowork/s')
        self.runner.land_planning()
        self.assertEqual(self.head('main'), session)
        self.assertEqual(self.head('pi-autowork/s'), session)  # the review's branch is untouched
        self.assertFalse(self.runner.land_soon)

    def test_with_the_base_moved_the_landing_waits_for_the_review(self):
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'an outside commit to main')
        main, session = self.head('main'), self.head('pi-autowork/s')
        with mock.patch.object(Coordinator, 'merge_main') as merge:
            self.runner.land_planning()
        merge.assert_not_called()  # a merge would move the session under the review
        self.assertEqual((self.head('main'), self.head('pi-autowork/s')), (main, session))
        self.assertTrue(self.runner.land_soon)  # still due: it lands after the review


class DirtyLandingTests(LandingFixture):
    # Exercise the public landing seam with real Git refs, index and working files.
    def setUp(self):
        super().setUp()
        self.git(self.repo, 'config', 'user.name', 'T')
        self.git(self.repo, 'config', 'user.email', 't@example.invalid')
        self.original = 'owner: old\n' + '\n'.join(f'section {i}' for i in range(20)) + '\nsession: old\n'
        self.note = self.repo / 'BLOCKERS.md'
        self.note.write_text(self.original)
        self.git(self.repo, 'add', 'BLOCKERS.md')
        self.git(self.repo, 'commit', '-qm', 'plan')
        self.git(self.integ, 'merge', '--no-edit', 'main')
        (self.integ / 'BLOCKERS.md').write_text(self.original.replace('session: old', 'session: new'))
        (self.integ / 'landed.txt').write_text('delivered\n')
        self.git(self.integ, 'add', '.')
        self.git(self.integ, 'commit', '-qm', 'session work')
        self.runner.integration = None
        self.runner.toolset = str(Path(__file__).resolve().parents[2])
        self.runner.state = self.repo.parent / 'state'
        self.runner.state.mkdir()
        self.runner.seen = {}
        self.runner.stop = False
        self.runner.resolved_for = ''
        self.parked = self.original.replace('owner: old', 'owner: parked')
        self.note.write_text(self.parked)

    def test_staged_session_bookkeeping_survives_a_refused_hook_and_then_lands(self):
        self.note.write_text(self.original)
        self.git(self.integ, 'reset', '--hard', 'main')  # no prior session commit may hide the main fix
        note = self.integ / 'BLOCKERS.md'
        edited = note.read_text() + 'new session question\n'
        note.write_text(edited)
        (self.repo / 'main-fix.txt').write_text('fix for the failing check\n')
        self.git(self.repo, 'add', 'main-fix.txt')
        self.git(self.repo, 'commit', '-qm', 'main fix')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\necho "pre-commit: checks failed" >&2\nexit 1\n')
        hook.chmod(0o755)
        with mock.patch('pi_autowork.coordinator.LOG.warn') as warning:
            self.assertFalse(self.runner.commit(['BLOCKERS.md'], 'docs(blockers): questions'))
        self.assertIn('pre-commit: checks failed', str(warning.call_args))
        self.assertEqual(self.git(self.integ, 'diff', '--cached', '--name-only'), 'BLOCKERS.md')
        self.runner.in_flight = lambda: False
        self.runner.merge_blocker = 'previous merge hold'
        self.runner.follow_base()
        self.assertEqual(self.runner.merge_blocker, '')
        self.assertEqual((self.integ / 'main-fix.txt').read_text(), 'fix for the failing check\n')
        self.assertTrue(hook.exists())
        self.assertEqual(self.git(self.integ, 'diff', '--cached', '--name-only'), '')
        self.assertEqual(note.read_text(), edited)
        self.assertEqual(self.head('main'), self.head('pi-autowork/s'))
        hook.unlink()
        self.assertTrue(self.runner.merge_main(), self.runner.merge_pending)
        self.assertEqual(self.git(self.integ, 'status', '--porcelain'), '')
        self.assertEqual(self.git(self.repo, 'show', 'main:BLOCKERS.md'), edited.strip())

    def test_refused_work_commit_stays_staged_and_does_not_land(self):
        self.note.write_text(self.original)
        work = self.integ / 'landed.txt'
        work.write_text('uncommitted code change\n')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\necho "pre-commit: checks failed" >&2\nexit 1\n')
        hook.chmod(0o755)
        main = self.head('main')
        self.assertFalse(self.runner.merge_main())
        self.assertIn('pre-commit: checks failed', self.runner.merge_pending)
        self.assertEqual(self.head('main'), main)
        self.assertEqual(self.git(self.integ, 'diff', '--cached', '--name-only'), 'landed.txt')
        self.assertEqual(work.read_text(), 'uncommitted code change\n')

    def test_merge_refused_before_conflicts_reports_git_diagnostic_without_a_resolver(self):
        self.note.write_text(self.original)
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'main moved')
        lock = Path(self.git(self.integ, 'rev-parse', '--path-format=absolute', '--git-path', 'index.lock'))
        lock.touch()
        self.addCleanup(lock.unlink, missing_ok=True)
        self.runner.tasks_cli, self.runner.verify_timeout = 'autowork tasks', 1
        with mock.patch.object(self.runner, 'pi_job', side_effect=AssertionError('not a merge conflict')):
            self.assertFalse(self.runner.merge_main())
        self.assertIn('Unable to write index', self.runner.merge_pending)
        self.assertNotIn('unknown files', self.runner.merge_pending)
        self.assertEqual(self.runner.resolved_for, '')

    def test_lands_around_an_uncommitted_edit_without_committing_it(self):
        permissions = self.note.stat().st_mode & 0o777
        (self.repo / 'other.txt').write_text('unrelated staged work\n')
        self.git(self.repo, 'add', 'other.txt')
        old_mask = os.umask(0o077)
        try:
            self.assertTrue(self.runner.merge_main(), self.runner.merge_pending)
        finally:
            os.umask(old_mask)
        self.assertEqual((self.repo / 'landed.txt').stat().st_mode & 0o777, 0o600)
        self.assertEqual(self.head('main'), self.head('pi-autowork/s'))
        self.assertEqual(self.git(self.repo, 'show', 'HEAD:BLOCKERS.md'),
                         self.original.replace('session: old', 'session: new').strip())
        self.assertEqual(self.note.read_text(), self.parked.replace('session: old', 'session: new'))
        self.assertEqual((self.repo / 'landed.txt').read_text(), 'delivered\n')
        self.assertEqual(self.note.stat().st_mode & 0o777, permissions)
        self.assertEqual(self.git(self.repo, 'diff', '--cached', '--name-only'), 'other.txt')
        self.assertEqual(self.git(self.repo, 'show', ':other.txt'), 'unrelated staged work')
        diff = self.git(self.repo, 'diff', '--', 'BLOCKERS.md')
        self.assertIn('+owner: parked', diff)
        self.assertNotIn('+session:', diff)

    def test_nonplanning_overlap_waits_even_when_the_edits_could_merge(self):
        self.note.write_text(self.original)  # no owner-planning edit in this case
        note = self.repo / 'notes.txt'
        note.write_text(self.original)
        self.git(self.repo, 'add', 'notes.txt')
        self.git(self.repo, 'commit', '-qm', 'owner file')
        self.git(self.integ, 'merge', '--no-edit', 'main')
        (self.integ / 'notes.txt').write_text(self.original.replace('session: old', 'session: new'))
        self.git(self.integ, 'commit', '-qam', 'session edit')
        note.write_text(self.parked)
        main = self.head('main')
        with mock.patch.dict(os.environ, {'PI_AUTOWORK_PLANNING_QUIET': '0'}):
            self.assertFalse(self.runner.merge_main())
        self.assertIn('notes.txt', self.runner.merge_pending)
        self.assertEqual(self.head('main'), main)
        self.assertEqual(note.read_text(), self.parked)
        self.assertEqual(self.git(self.repo, 'diff', '--cached', '--name-only'), '')

    def test_unsafe_edits_leave_the_ref_index_and_edit_untouched(self):
        real_run, real_fsync, real_read = subprocess.run, os.fsync, Path.read_bytes
        main = self.head('main')
        index = Path(self.git(self.repo, 'rev-parse', '--git-path', 'index'))
        if not index.is_absolute():
            index = self.repo / index
        for case in ('conflict', 'open', 'changed', 'vanished', 'merge', 'staged', 'conversion', 'index-full', 'cas'):
            with self.subTest(case=case):
                after_cas = False
                content = (self.original.replace('session: old', 'session: owner')
                           if case == 'conflict' else self.parked)
                self.note.write_text(content)
                if case == 'staged':
                    self.git(self.repo, 'add', 'BLOCKERS.md')
                if case == 'conversion':
                    self.git(self.repo, 'config', 'core.autocrlf', 'true')
                before_index = index.read_bytes()
                marker = self.repo / '.git/MERGE_HEAD'
                holder = self.note.open('a') if case == 'open' else None
                if case == 'merge':
                    marker.write_text(self.head('pi-autowork/s') + '\n')

                def racing_run(args, *a, **kw):
                    nonlocal after_cas
                    if 'update-ref' in args:
                        if case == 'changed':
                            self.note.write_text(content + 'new owner edit\n')
                        if case == 'cas':
                            return subprocess.CompletedProcess(args, 1)
                    result = real_run(args, *a, **kw)
                    if 'update-ref' in args and result.returncode == 0:
                        after_cas = True
                    return result

                def racing_read(file):
                    if case == 'vanished' and after_cas and file == self.note:
                        file.unlink()
                    return real_read(file)

                def failing_fsync(fd):
                    if case == 'index-full' and os.readlink(f'/proc/self/fd/{fd}') == str(index) + '.lock':
                        raise OSError('index disk full')
                    return real_fsync(fd)

                try:
                    with mock.patch('subprocess.run', side_effect=racing_run), \
                            mock.patch('os.fsync', side_effect=failing_fsync), \
                            mock.patch.object(Path, 'read_bytes', new=racing_read):
                        self.assertFalse(self.runner.merge_main())
                    self.assertEqual(self.head('main'), main)
                    self.assertEqual(index.read_bytes(), before_index)
                    if case == 'vanished':
                        self.assertFalse(self.note.exists())
                    else:
                        self.assertEqual(self.note.read_text(), content + ('new owner edit\n' if case == 'changed' else ''))
                    self.assertIn({'merge': 'progress', 'index-full': 'index', 'cas': 'compare-and-swap'}
                                  .get(case, 'BLOCKERS.md'), self.runner.merge_pending)
                    self.assertFalse((self.repo / 'landed.txt').exists())
                finally:
                    if holder:
                        holder.close()
                    marker.unlink(missing_ok=True)
                    if case == 'staged':
                        self.git(self.repo, 'restore', '--staged', 'BLOCKERS.md')
                    if case == 'conversion':
                        self.git(self.repo, 'config', '--unset', 'core.autocrlf')

    def test_identical_rewrites_become_quiet_but_new_content_restarts_the_clock(self):
        with mock.patch.dict(os.environ, {'PI_AUTOWORK_PLANNING_QUIET': '600'}):
            with mock.patch('pi_autowork.coordinator.time.time', return_value=1000):
                self.assertTrue(self.runner.commit_owner_changes())
            self.note.write_text(self.parked + 'another edit\n')
            with mock.patch('pi_autowork.coordinator.time.time', return_value=1500):
                self.assertTrue(self.runner.commit_owner_changes())
            for now in (1600, 2000):
                self.note.write_bytes(self.note.read_bytes())
                with mock.patch('pi_autowork.coordinator.time.time', return_value=now):
                    self.assertTrue(self.runner.commit_owner_changes())
            self.note.write_bytes(self.note.read_bytes())
            with mock.patch('pi_autowork.coordinator.time.time', return_value=2101):
                self.assertEqual(self.runner.commit_owner_changes(), '')
        self.assertEqual(self.git(self.repo, 'status', '--porcelain'), '')
        self.assertEqual(self.note.read_text(), self.parked + 'another edit\n')


if __name__ == '__main__':
    unittest.main()
