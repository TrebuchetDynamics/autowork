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
        self.assertEqual(state.reconcile(self.repo, self.owner)[0]['state'], 'held')
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
