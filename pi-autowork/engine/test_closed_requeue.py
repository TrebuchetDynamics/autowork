"""Closed execution slots follow proven committed reopenings, never an open-looking file."""
import json
import os
from pathlib import Path
import sys
import subprocess
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
import autowork_bootstrap

autowork_bootstrap.activate(ROOT)
sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_parallel_integrate as fixture
from pi_autowork import optimistic, task_commands
from pi_autowork.engine import parallel_dispatch as dispatch, parallel_state as state
from pi_autowork.engine import parallel_status as status, task_store


class ClosedRequeueTests(unittest.TestCase):
    # Reuse the real repository/worker/receipt fixture, not its inherited tests.
    for name in ('setUp', 'git', 'worker', 'pin_contract', 'record', 'module',
                 'close_committed', 'retry_args'):
        locals()[name] = getattr(fixture.IntegrationTests, name)

    def closed(self):
        self.worker()
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.close_committed()
        self.slot = state.slots(self.common)[0]
        self.merge = self.slot['integration']['commit']
        self.closed_revision = self.git('rev-parse', 'HEAD')

    def rollback(self):
        self.assertEqual(optimistic.revert(self.repo, ['A'], {'A': self.merge}, ['test_regression'],
                                          self.closed_revision, task_commands.reopen), ['A'])

    def dispatch(self, tasks='A'):
        args = self.retry_args()
        args.tasks = tasks
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(60)'])
        original = subprocess.Popen
        def tracked(*args, **kwargs):
            process = original(*args, **kwargs)
            def cleanup():
                if process.poll() is None:
                    process.terminate()
                process.wait(timeout=10)
            self.addCleanup(cleanup)
            return process
        with patch.object(dispatch, 'resource_gate', return_value=None), \
                patch.object(subprocess, 'Popen', side_effect=tracked):
            return dispatch.dispatch(args)

    def test_rollback_requeues_and_dispatches_once_with_history_and_kept_commit(self):
        self.closed()
        self.rollback()
        result = self.dispatch()
        self.assertEqual([s['task'] for s in result['dispatched']], ['A'], result)
        history = list((self.common / 'slot-history/A').glob('*/slot.json'))
        self.assertEqual(len(history), 1)
        old = json.loads(history[0].read_text())
        self.assertEqual((old['state'], old['commit']), ('closed', self.slot['commit']))
        self.assertTrue((history[0].parent / 'slot-data/attempt-1/report.json').exists())
        self.assertIn(self.slot['commit'], self.git('show-ref'))
        # Same owner after restart/reentry cannot retire the newly dispatched slot.
        self.assertEqual(self.dispatch()['dispatched'], [])
        self.assertEqual(len(list((self.common / 'slot-history/A').glob('*/slot.json'))), 1)

    def test_supported_set_aside_accepts_proven_reopen_only(self):
        self.closed()
        with self.assertRaises(ValueError):
            self.module().set_aside(self.repo, self.owner, 'A')
        self.rollback()
        result = self.module().set_aside(self.repo, self.owner, 'A')
        self.assertTrue(result['requeued'])
        self.assertEqual(state.slots(self.common), [])

    def test_open_slot_mismatch_is_visible_and_does_not_release_dependency(self):
        self.closed()
        self.rollback()
        path = self.repo / 'tasks/items/B.md'
        path.write_text(task_store.edit(path.read_text(), {'depends_on': ['A']}))
        self.git('commit', '-qam', 'dependent')
        view = status.snapshot(self.repo)
        rows = {r['task']: r for r in view['tasks']}
        self.assertEqual(rows['A']['state'], 'waiting')
        self.assertIn('requeue', rows['A']['reason'])
        self.assertEqual(view['completed'], 0)
        self.assertTrue(any(r['id'] == 'A' and 'B' in r['tasks'] for r in view['roots']), view)

    def test_pending_close_uncommitted_reopen_and_unproven_reopen_never_dispatch(self):
        self.closed()
        path = self.repo / 'tasks/items/A.md'
        task_commands.reopen(self.repo, 'A', 'reverted by optimistic landing')
        self.assertEqual(self.dispatch()['dispatched'], [])  # worktree is not authority
        self.git('commit', '-qam', 'unproven reopen')
        self.assertEqual(self.dispatch()['dispatched'], [])  # no rollback, just a note
        self.assertEqual(state.slots(self.common)[0]['state'], 'closed')

    def test_stale_contract_reopen_is_requeued_without_rollback(self):
        self.closed()
        path = self.repo / 'tasks/items/A.md'
        path.write_text(task_store.edit(path.read_text(), {'acceptance': ['new acceptance']}))
        self.git('commit', '-qam', 'changed contract after closure')
        task_commands.reopen(self.repo, 'A', '2026-10-25: its contract changed after its verified close '
                             '(receipt old, record new); verify it again')
        self.git('commit', '-qam', 'docs(tasks): reopen A (pi-autowork)')
        result = self.dispatch()
        self.assertEqual([s['task'] for s in result['dispatched']], ['A'], result)

    def test_archive_replays_after_data_move_and_after_ref_move(self):
        self.closed()
        self.rollback()
        # Retain dirty work; no bytes/commits may be lost.
        root = self.repo / '.worktrees/retained-A'
        self.git('worktree', 'add', '-qb', 'autowork/A', str(root), self.slot['commit'])
        (root / 'unsaved.txt').write_text('keep uncommitted work\n')
        old = state.slots(self.common)[0]
        state.write_slot(self.common, dict(old, worktree=str(root)), old)
        from pi_autowork.engine import closed_requeue
        original = closed_requeue.git
        failed = False
        def crash_after_branch(*args):
            nonlocal failed
            value = original(*args)
            if args[1:3] == ('branch', '-m') and not failed:
                failed = True
                raise RuntimeError('simulated crash after ref move')
            return value
        with patch.object(closed_requeue, 'git', side_effect=crash_after_branch):
            with self.assertRaisesRegex(RuntimeError, 'simulated crash'):
                self.module().set_aside(self.repo, self.owner, 'A')
        original_save = closed_requeue.execution.save
        def crash_after_data(path, value):
            if Path(path).name == 'slot.json':
                raise RuntimeError('simulated crash after data move')
            return original_save(path, value)
        with patch.object(closed_requeue.execution, 'save', side_effect=crash_after_data):
            with self.assertRaisesRegex(RuntimeError, 'simulated crash'):
                self.module().set_aside(self.repo, self.owner, 'A')
        result = self.module().set_aside(self.repo, self.owner, 'A')
        self.assertEqual(state.slots(self.common), [])
        self.assertEqual(len(list((self.common / 'slot-history/A').glob('*'))), 1)
        self.assertEqual(Path(result['renamed'][0]['worktree_now'], 'unsaved.txt').read_text(),
                         'keep uncommitted work\n')
        self.assertTrue((Path(result['history']) / 'slot-data/attempt-1/report.json').exists())
        self.assertEqual(self.git('rev-parse', result['renamed'][0]['branch_now']), self.slot['commit'])

    def test_pending_integrated_close_is_not_retired(self):
        self.worker()
        self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.module().close(self.repo, self.owner, 'A')  # uncommitted close, not a reopen
        self.assertEqual(self.dispatch()['dispatched'], [])
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrated')

    def test_wrong_receipt_and_manual_close_cannot_authorize_reopen(self):
        self.closed()
        self.rollback()
        from pi_autowork.engine import closed_requeue
        self.assertIsNotNone(closed_requeue.evidence(self.repo, self.slot))
        self.git('reset', '--hard', self.closed_revision)
        path = self.repo / 'tasks/items/A.md'
        path.write_text(task_store.edit(path.read_text(), {'closure': 'manual', 'closure_actor': 'owner',
                        'closure_timestamp': '2026-10-25T00:00:00+00:00',
                        'closure_reason': 'closed by owner', 'closure_evidence': None}))
        self.git('commit', '-qam', 'manual close')
        self.rollback()
        self.assertIsNone(closed_requeue.evidence(self.repo, self.slot))
        self.assertEqual(self.dispatch()['dispatched'], [])
        self.git('reset', '--hard', self.closed_revision)
        receipt = self.repo / 'tasks/evidence/A.toml'
        receipt.write_text(receipt.read_text().replace(self.merge, self.baseline))
        self.git('commit', '-qam', 'wrong receipt')
        self.rollback()
        self.assertIsNone(closed_requeue.evidence(self.repo, self.slot))

    def test_a_rollback_message_without_the_inverse_diff_does_not_authorize_requeue(self):
        self.closed()
        self.git('revert', '--no-edit', '-m', '1', self.merge)
        (self.repo / 'A.txt').write_text('not the pre-merge tree\n')
        self.git('add', 'A.txt')
        self.git('commit', '--amend', '-qm', 'revert(A): its landing broke the full check on main at '
                 + self.closed_revision[:7], '-m', f'This reverts commit {self.merge}.')
        task_commands.reopen(self.repo, 'A', 'reverted by optimistic landing')
        self.git('commit', '-qam', 'reopen A')
        self.assertEqual(self.dispatch()['dispatched'], [])

    def test_second_generation_can_integrate_and_close_without_old_cleanup_intent(self):
        self.closed()
        self.rollback()
        retired = self.module().set_aside(self.repo, self.owner, 'A')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker()
        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.close_committed()
        self.assertEqual(state.slots(self.common)[0]['state'], 'closed')
        self.assertTrue((Path(retired['history']) / 'cleanup-A-1.json').exists())

    def test_symlinked_archive_is_rejected_before_refs_or_data_move(self):
        self.closed()
        self.rollback()
        outside = self.repo.parent / 'outside'
        outside.mkdir()
        history = self.common / 'slot-history'
        history.mkdir()
        (history / 'A').symlink_to(outside, target_is_directory=True)
        before = self.git('show-ref')
        with self.assertRaisesRegex(ValueError, 'symlink'):
            self.module().set_aside(self.repo, self.owner, 'A')
        self.assertEqual(self.git('show-ref'), before)
        self.assertTrue((self.common / 'slot-data/A/attempt-1/report.json').exists())
        self.assertEqual(list(outside.iterdir()), [])

    def test_deleted_and_recreated_task_cannot_reuse_an_older_reopen(self):
        self.closed()
        self.rollback()
        path = self.repo / 'tasks/items/A.md'
        content = path.read_bytes()
        path.unlink()
        self.git('add', '-u')
        self.git('commit', '-qm', 'delete task')
        path.write_bytes(content)
        self.git('add', 'tasks/items/A.md')
        self.git('commit', '-qm', 'recreate task')
        self.assertEqual(self.dispatch()['dispatched'], [])

    def test_busy_integration_keeps_reopen_pending_but_dispatches_unrelated_work(self):
        self.closed()
        self.rollback()
        with dispatch.execution.lock(self.common / 'integration.lock'):
            result = self.dispatch(tasks=None)
        self.assertEqual([s['task'] for s in result['dispatched']], ['B'], result)
        self.assertEqual(next(s for s in state.slots(self.common) if s['task_id'] == 'A')['state'], 'closed')
        self.assertIn('integration', next(w['reason'] for w in result['waiting'] if w['id'] == 'A'))

    def test_no_reopen_does_not_need_integration_lock(self):
        self.closed()
        with dispatch.execution.lock(self.common / 'integration.lock'):
            result = self.dispatch(tasks=None)
        self.assertEqual([s['task'] for s in result['dispatched']], ['B'], result)

    def test_ref_namespace_collision_chooses_another_archive_number(self):
        self.closed()
        self.rollback()
        self.git('branch', 'autowork/A-set-aside-1/keep', self.baseline)
        result = self.module().set_aside(self.repo, self.owner, 'A')
        self.assertEqual(Path(result['history']).name, '2')
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1/keep'), self.baseline)
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-2'), self.slot['commit'])

    def test_tag_branch_ambiguity_cannot_hide_ref_namespace_collision(self):
        self.closed()
        self.rollback()
        name = 'autowork/A-set-aside-1/keep'
        self.git('branch', name, self.baseline)
        self.git('tag', name, self.baseline)
        result = self.module().set_aside(self.repo, self.owner, 'A')
        self.assertEqual(Path(result['history']).name, '2')
        self.assertEqual(self.git('rev-parse', 'refs/heads/' + name), self.baseline)
        self.assertEqual(self.git('rev-parse', 'refs/tags/' + name), self.baseline)
        self.assertEqual(self.git('rev-parse', 'refs/heads/autowork/A-set-aside-2'), self.slot['commit'])

    def test_repeated_evidence_reads_are_cached_but_new_head_and_slot_are_revalidated(self):
        self.closed()
        self.rollback()
        from pi_autowork.engine import closed_requeue
        with patch.object(closed_requeue, 'git', wraps=closed_requeue.git) as reads:
            first = closed_requeue.evidence(self.repo, self.slot)
            count = reads.call_count
            self.assertIsNotNone(first)
            self.assertEqual(closed_requeue.evidence(self.repo, self.slot), first)
            self.assertEqual(reads.call_count, count)
        wrong = dict(self.slot, integration=dict(self.slot['integration'], commit=self.baseline))
        self.assertIsNone(closed_requeue.evidence(self.repo, wrong))
        self.git('reset', '--hard', self.closed_revision)
        self.assertIsNone(closed_requeue.evidence(self.repo, self.slot))

    def test_retirement_preserves_every_previous_attempt_and_branch(self):
        self.closed()
        self.rollback()
        prior = dict(self.slot, branch='autowork/A-r1', worktree=str(self.repo / '.worktrees/prior-A'),
                     state='interrupted', commit=self.baseline)
        self.git('branch', prior['branch'], self.baseline)
        current = dict(self.slot, attempt=2, previous_attempts=[prior])
        state.write_slot(self.common, current, self.slot)
        data = self.common / 'slot-data/A/attempt-2'
        data.mkdir()
        (data / 'kept.txt').write_text('second attempt evidence\n')
        result = self.module().set_aside(self.repo, self.owner, 'A')
        archive = Path(result['history'])
        saved = json.loads((archive / 'slot.json').read_text())
        self.assertEqual(saved['previous_attempts'], [prior])
        self.assertEqual(self.git('rev-parse', 'autowork/A-r1-set-aside-1'), self.baseline)
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), self.slot['commit'])
        self.assertTrue((archive / 'slot-data/attempt-1/report.json').exists())
        self.assertEqual((archive / 'slot-data/attempt-2/kept.txt').read_text(), 'second attempt evidence\n')

    def test_wrong_owner_cannot_requeue(self):
        self.closed()
        self.rollback()
        with self.assertRaises(ValueError):
            self.module().set_aside(self.repo, os.getpid() + 999999, 'A')
        self.assertEqual(state.slots(self.common)[0]['state'], 'closed')

    def test_live_worker_and_missing_rollback_evidence_refuse_retirement(self):
        self.closed()
        self.rollback()
        with patch.object(state, 'worker_live', return_value=True):
            with self.assertRaises(ValueError):
                self.module().set_aside(self.repo, self.owner, 'A')
        self.git('reset', '--hard', self.closed_revision)
        task_commands.reopen(self.repo, 'A', 'its landing broke the full check on main; '
                             'reverted by optimistic landing. Fix those tests in the next attempt')
        self.git('commit', '-qam', 'docs(tasks): reopen A after reverting its landing (pi-autowork)')
        self.assertEqual(self.dispatch()['dispatched'], [])


if __name__ == '__main__':
    unittest.main()
