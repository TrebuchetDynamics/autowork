"""Offline lease and recovery checks, using disposable real Git repositories."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import task_execution as execution
import parallel_state as state
import parallel_status as status


class StateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        (self.repo / 'file').write_text('base')
        (self.repo / 'TODO.md').write_text('''# Work queue
## Next
- [ ] A — Fixture
- Scope: Change file.
- Acceptance: File changed.
- Checks: Check file.
- Dependencies: None.
''')
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.base = self.git('rev-parse', 'HEAD')
        self.owner = os.getppid()
        self.common = state.common_dir(self.repo)

    def git(self, *args, repo=None):
        return execution.git(repo or self.repo, *args)

    def claim(self, repo=None):
        return state.claim(repo or self.repo, self.owner, profile='fixture')

    def slot(self, task='A', **kwargs):
        worktree = Path(self.tmp.name) / task
        self.git('worktree', 'add', '-qb', 'autowork/' + task, str(worktree))
        return state.create_slot(self.repo, self.owner, task, worktree=str(worktree),
                                 branch='autowork/' + task, baseline=self.base, **kwargs)

    def test_owner_required_and_live_lease_never_expires(self):
        for owner in (None, 1, os.getpid(), 99999999):
            with self.assertRaises(ValueError):
                state.claim(self.repo, owner)
        lease = self.claim()
        self.assertEqual(lease['outcome'], 'CLAIMED')
        saved = execution.read(self.common / 'coordinator.json')
        saved['started_at'] = 0
        execution.save(self.common / 'coordinator.json', saved)
        with patch.object(execution, 'owner_identity', return_value=execution.identity(os.getpid())):
            self.assertEqual(state.claim(self.repo, os.getpid())['outcome'], 'BUSY')
        self.assertEqual(self.claim()['outcome'], 'CLAIMED')
        state.release(self.repo, self.owner)
        self.assertFalse((self.common / 'coordinator.json').exists())

    def test_linked_worktrees_share_lease(self):
        linked = Path(self.tmp.name) / 'linked'
        self.git('worktree', 'add', '-q', '--detach', str(linked))
        self.claim()
        with patch.object(execution, 'owner_identity', return_value=execution.identity(os.getpid())):
            self.assertEqual(state.claim(linked, os.getpid())['outcome'], 'BUSY')
        self.assertEqual(state.common_dir(linked), self.common)

    def test_dead_coordinator_superseded_and_malformed_not_overwritten(self):
        self.claim()
        old = execution.read(self.common / 'coordinator.json')
        old['owner']['start_ticks'] += 1
        execution.save(self.common / 'coordinator.json', old)
        self.assertEqual(self.claim()['outcome'], 'CLAIMED')
        execution.save(self.common / 'coordinator.json', {})
        with self.assertRaises(ValueError):
            self.claim()

    def test_live_sequential_owner_blocks_even_same_owner(self):
        execution.save(self.common / 'active.json', {'owner': execution.identity(self.owner)})
        self.assertEqual(self.claim()['outcome'], 'BUSY')

    def test_parallel_blocks_sequential_execute(self):
        self.claim()
        result = subprocess.run([sys.executable, str(Path(execution.__file__).with_name('owner_cycle.py')), str(self.repo),
                                 '--apply', '--owner-pid', str(os.getpid())], capture_output=True, text=True)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'BUSY')
        self.assertFalse((self.common / 'active.json').exists())

    def test_reconcile_four_cases_idempotently(self):
        self.claim()
        live = self.slot('LIVE', worker=execution.identity(self.owner))
        committed = self.slot('COMMIT')
        worktree = Path(committed['worktree'])
        (worktree / 'file').write_text('commit')
        self.git('commit', '-qam', 'worker', repo=worktree)
        dirty = self.slot('DIRTY')
        (Path(dirty['worktree']) / 'new').write_text('keep me')
        self.slot('CLEAN')
        first = state.reconcile(self.repo, self.owner)
        self.assertEqual({s['task_id']: s['state'] for s in first},
                         {'CLEAN': 'released', 'COMMIT': 'reported', 'DIRTY': 'interrupted', 'LIVE': 'running'})
        self.assertEqual(next(s for s in first if s['task_id'] == 'COMMIT')['commit'],
                         self.git('rev-parse', 'HEAD', repo=worktree))
        journal = (self.common / 'journal.jsonl').read_bytes()
        self.assertEqual(first, state.reconcile(self.repo, self.owner))
        self.assertEqual(journal, (self.common / 'journal.jsonl').read_bytes())
        self.assertTrue((Path(dirty['worktree']) / 'new').exists())
        self.assertEqual(next(s for s in first if s['task_id'] == 'CLEAN')['reason'],
                         'dead worker without a commit or changes')

    def test_paused_workers_are_reaped_with_a_restart_reason_and_resume_the_same_attempt(self):
        self.claim()
        for attempt in (1, 2):
            for dirty in (False, True):
                with self.subTest(attempt=attempt, dirty=dirty):
                    task = f'PAUSED-{attempt}-{dirty}'
                    slot = self.slot(task)
                    if attempt == 2:
                        state.transition(self.repo, self.owner, task, 'released')
                        state.transition(self.repo, self.owner, task, 'dispatched')
                    worker = subprocess.Popen(['sleep', '30'], start_new_session=True)
                    self.addCleanup(lambda p=worker: p.poll() is None and p.kill())
                    state.transition(self.repo, self.owner, task, 'running',
                                     worker=execution.identity(worker.pid))
                    if dirty:
                        (Path(slot['worktree']) / 'new').write_text('keep me')
                    self.assertEqual(state.pause(self.repo, self.owner)['paused'], [task])
                    worker.terminate()
                    worker.wait(timeout=5)
                    reaped = next(s for s in state.reconcile(self.repo, self.owner) if s['task_id'] == task)
                    self.assertEqual(reaped['state'], 'interrupted' if dirty else 'released')
                    self.assertEqual(reaped['reason'], f'stopped by a runner restart; resumes on attempt {attempt}'
                                     + (' with uncommitted changes' if dirty else ''))
                    resumed = state.transition(self.repo, self.owner, task, 'dispatched')
                    self.assertEqual((resumed['attempt'], resumed['worktree']), (attempt, slot['worktree']))
                    # Retire the fixture before pausing the next worker.
                    state.transition(self.repo, self.owner, task, 'held')

    def test_report_only_resume_failures_keep_the_commit_and_never_start_a_fresh_attempt(self):
        import parallel_dispatch as dispatch
        self.claim()

        def time_out(task):
            proc = subprocess.Popen(['sleep', '30'], start_new_session=True)
            self.addCleanup(lambda p=proc: (p.kill(), p.wait()) if p.poll() is None else None)
            running = state.transition(self.repo, self.owner, task, 'running', worker=execution.identity(proc.pid))
            with patch.object(dispatch.time, 'time', return_value=running['started_at'] + 100):
                dispatch.enforce_timeouts(self.repo, self.owner, self.common, 1)

        for attempt in (1, 2):
            for failure in ('timeout', 'launch'):
                with self.subTest(attempt=attempt, failure=failure):
                    task = f'REPORT-{attempt}-{failure}'
                    slot = self.slot(task)
                    if attempt == 2:
                        state.transition(self.repo, self.owner, task, 'interrupted')
                        state.transition(self.repo, self.owner, task, 'dispatched')
                    root = Path(slot['worktree'])
                    (root / 'file').write_text('finished')
                    self.git('commit', '-qam', 'finished', repo=root)
                    commit = self.git('rev-parse', 'HEAD', repo=root)
                    if failure == 'timeout':
                        time_out(task)  # the original worker timed out after its commit, before its report
                    state.reconcile(self.repo, self.owner)
                    with execution.lock(self.common / 'writer.lock'):
                        state.recover_reports(self.common, state.slots(self.common))
                    resumed = state.transition(self.repo, self.owner, task, 'dispatched')
                    self.assertEqual((resumed['attempt'], resumed.get('commit')), (attempt, commit))
                    if failure == 'launch':
                        state.transition(self.repo, self.owner, task, 'held', cause='launch', reason='cannot launch')
                    else:
                        time_out(task)  # its bounded report-only resume timed out too
                    held = next(s for s in state.reconcile(self.repo, self.owner) if s['task_id'] == task)
                    self.assertEqual((held['state'], held['cause'], held['commit']), ('held', 'report', commit))
                    self.assertTrue(state.exhausted(held))
                    self.assertIn('report.json', held['reason'])
                    self.assertFalse((dispatch.data_dir(self.common, held) / 'report.json').exists())

    def test_timeout_of_an_unrelated_head_records_the_stopped_worker(self):
        import parallel_dispatch as dispatch
        self.claim()
        slot = self.slot()
        root = Path(slot['worktree'])
        tree = self.git('rev-parse', 'HEAD^{tree}', repo=root)
        orphan = self.git('commit-tree', tree, '-m', 'unrelated history', repo=root)
        self.git('update-ref', 'HEAD', orphan, repo=root)
        proc = subprocess.Popen(['sleep', '30'], start_new_session=True)
        self.addCleanup(lambda: (proc.kill(), proc.wait()) if proc.poll() is None else None)
        running = state.transition(self.repo, self.owner, 'A', 'running', worker=execution.identity(proc.pid))
        with patch.object(dispatch.time, 'time', return_value=running['started_at'] + 100):
            stopped = dispatch.enforce_timeouts(self.repo, self.owner, self.common, 1)
        self.assertEqual(stopped[0]['state'], 'interrupted')
        self.assertFalse(state.worker_live(stopped[0]))
        self.assertEqual(state.slots(self.common)[0]['state'], 'interrupted')

    def test_paused_status_keeps_one_row_with_its_waiting_reason_and_no_failure(self):
        self.claim()
        reason = 'stopped by a runner restart; resumes on attempt 1'
        for task, phase, paused in (('A', 'released', True), ('DIRTY', 'interrupted', True),
                                    ('DEAD', 'released', False), ('HELD', 'held', True)):
            self.slot(task)
            state.transition(self.repo, self.owner, task, phase, paused=paused, reason=reason)
        state.event(self.common, 'dispatch_observed', waiting=[
            dict(id='A', reason='overlapping paths with LIVE', blocked_by=['LIVE'])], max_workers=2)
        snapshot = status.snapshot(self.repo)
        self.assertEqual(snapshot['failed'], 2)  # unpaused death and a real hold still fail
        rows = [row for row in snapshot['tasks'] if row['task'] == 'A']
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0]['reason'], reason + '; waiting: overlapping paths with LIVE')
        self.assertEqual(rows[0]['state'], 'released')  # display must not change engine transitions
        rendered = status.render(snapshot)
        self.assertRegex(rendered, r'A\s+paused\s')
        self.assertRegex(rendered, r'DIRTY\s+paused\s')

    def test_ancestry_requires_each_intermediate_birth_identity_to_stay_live(self):
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'], start_new_session=True)
        self.addCleanup(lambda: (proc.kill(), proc.wait()))
        leader, found = execution.identity(os.getppid()), execution.identity(proc.pid)
        self.assertTrue(state.owns_process(leader, found))  # proc -> this test -> leader
        original = execution.identity
        intermediate = original(os.getpid())
        for changed in (None, dict(intermediate, start_ticks=intermediate['start_ticks'] + 1)):
            calls = 0
            def identity(pid):
                nonlocal calls
                if pid == os.getpid():
                    calls += 1
                    if calls >= 3:  # changed after reading the intermediate's parent
                        return changed
                return original(pid)
            with self.subTest(changed=changed), patch.object(execution, 'identity', side_effect=identity):
                self.assertFalse(state.owns_process(leader, found))

    def test_transitions_retry_once_and_preserve_previous_attempt(self):
        self.claim()
        slot = self.slot()
        with self.assertRaises(ValueError):
            state.transition(self.repo, self.owner, 'A', 'closed')
        state.transition(self.repo, self.owner, 'A', 'interrupted', reason='crashed')
        retry = state.transition(self.repo, self.owner, 'A', 'dispatched')
        self.assertEqual(retry['attempt'], 2)
        self.assertEqual(retry['worktree'], slot['worktree'])
        state.transition(self.repo, self.owner, 'A', 'interrupted')
        held = execution.read(self.common / 'slots/A.json')
        self.assertEqual(held['state'], 'held')
        with self.assertRaises(ValueError):
            state.transition(self.repo, self.owner, 'A', 'dispatched')

    def test_held_retry_requires_fresh_worktree(self):
        self.claim()
        slot = self.slot()
        state.transition(self.repo, self.owner, 'A', 'held', reason='validation')
        with self.assertRaises(ValueError):
            state.transition(self.repo, self.owner, 'A', 'dispatched')
        fresh = Path(self.tmp.name) / 'A-r2'
        self.git('worktree', 'add', '-qb', 'autowork/A-r2', str(fresh))
        retry = state.transition(self.repo, self.owner, 'A', 'dispatched',
                                 worktree=str(fresh), branch='autowork/A-r2', baseline=self.base)
        self.assertEqual(retry['attempt'], 2)
        self.assertEqual(retry['previous_attempts'][0]['worktree'], slot['worktree'])
        self.assertTrue(Path(slot['worktree']).exists())

    def test_review_retry_relative_path_recovers_from_another_cwd(self):
        self.claim()
        self.slot()
        state.transition(self.repo, self.owner, 'A', 'held')
        fresh = Path(self.tmp.name) / 'A-r2'
        self.git('worktree', 'add', '-qb', 'autowork/A-r2', str(fresh))
        retry = state.transition(self.repo, self.owner, 'A', 'dispatched',
                                 worktree=os.path.relpath(fresh), branch='autowork/A-r2', baseline=self.base)
        self.assertTrue(Path(retry['worktree']).is_absolute())
        previous = Path.cwd()
        try:
            os.chdir(self.repo)
            self.assertEqual(state.reconcile(self.repo, self.owner)[0]['state'], 'held')
        finally:
            os.chdir(previous)

    def test_review_dead_clean_second_attempt_stays_held(self):
        self.claim()
        self.slot()
        state.transition(self.repo, self.owner, 'A', 'interrupted')
        state.transition(self.repo, self.owner, 'A', 'dispatched')
        held = state.reconcile(self.repo, self.owner)[0]
        self.assertEqual((held['state'], held['cause']), ('held', 'empty'))
        journal = (self.common / 'journal.jsonl').read_bytes()
        state.reconcile(self.repo, self.owner)
        self.assertEqual(journal, (self.common / 'journal.jsonl').read_bytes())

    def test_held_retry_cannot_overlap_live_worker(self):
        # A missing Touches no longer makes a task run alone (TOOLSET-161-17); an exclusive one still does.
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text() + '- Touches: file\n- Resources: exclusive\n')
        self.claim()
        self.slot()
        state.transition(self.repo, self.owner, 'A', 'held')
        self.slot('LIVE', worker=execution.identity(self.owner))
        fresh = Path(self.tmp.name) / 'A-r2'
        self.git('worktree', 'add', '-qb', 'autowork/A-r2', str(fresh))
        with self.assertRaisesRegex(ValueError, 'conflicts with worker pool'):
            state.transition(self.repo, self.owner, 'A', 'dispatched',
                             worktree=str(fresh), branch='autowork/A-r2', baseline=self.base)

    def test_real_other_coordinator_cannot_claim_linked_worktree(self):
        self.claim()
        linked = Path(self.tmp.name) / 'linked'
        self.git('worktree', 'add', '-q', '--detach', str(linked))
        result = subprocess.run([sys.executable, '-c',
                                'import os,sys,json; sys.path.insert(0,sys.argv[1]); '
                                'import parallel_state as s; '
                                'print(json.dumps(s.claim(sys.argv[2],os.getppid(),profile="fixture")))',
                                str(Path(state.__file__).parent), str(linked)],
                                capture_output=True, text=True, check=True)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'BUSY')

    def test_unsafe_slot_and_foreign_owner_refused(self):
        self.claim()
        for task in ('../escape', 'a/b', ''):
            with self.assertRaises(ValueError):
                self.slot(task)
        self.slot()
        with patch.object(execution, 'owner_identity', return_value=execution.identity(os.getpid())):
            with self.assertRaises(ValueError):
                state.transition(self.repo, os.getpid(), 'A', 'running')
        with self.assertRaises(ValueError):
            state.transition(self.repo, self.owner, 'A', 'running', task_id='B')


if __name__ == '__main__':
    unittest.main()
