"""Lifecycle observations at real Git / engine state seams, with no model calls."""
import json
import os
from pathlib import Path
import unittest
from unittest.mock import patch

import parallel_state as state
import parallel_status as status
import task_execution as execution
import test_parallel_state as fixture


class LifecycleTests(unittest.TestCase):
    def setUp(self):
        self.fx = fixture.StateTests()
        self.fx.setUp()
        self.addCleanup(self.fx.doCleanups)
        self.fx.claim()

    def test_retry_restart_and_replayed_close_keep_attempts_and_task_totals_distinct(self):
        fx = self.fx
        first = fx.slot()
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='validation', reason='failed')
        retry = Path(fx.tmp.name) / 'retry'
        fx.git('worktree', 'add', '-qb', 'autowork/A-r2', str(retry))
        state.transition(fx.repo, fx.owner, 'A', 'dispatched', worktree=str(retry),
                         branch='autowork/A-r2', baseline=fx.base)
        # A failed append must not change the transition; its saved facts replay later.
        with patch.object(state.journal.os, 'write', side_effect=OSError('journal unavailable')):
            state.transition(fx.repo, fx.owner, 'A', 'interrupted', paused=True)
        state.transition(fx.repo, fx.owner, 'A', 'dispatched')
        for target in ('reported', 'integrating', 'integrated', 'closed'):
            state.transition(fx.repo, fx.owner, 'A', target)
        state.observe_history(fx.repo)
        state.observe_history(fx.repo)
        events = state.lifecycle_events(fx.common)['events']
        self.assertEqual([e['event'] for e in events], [
            'accepted', 'admitted', 'dispatched', 'verification_failed', 'held',
            'retry', 'admitted', 'dispatched', 'interrupted', 'resumed',
            'reviewed', 'integrated', 'closed'])
        attempts = {e['attempt_id'] for e in events if e['scope'] == 'attempt'}
        self.assertEqual(len(attempts), 2)
        self.assertNotEqual(first['attempt_id'], next(s for s in state.slots(fx.common))['attempt_id'])

    def test_reader_counts_duplicate_and_torn_lines_without_losing_later_appends(self):
        fx = self.fx
        fx.slot()
        path = fx.common / 'journal.jsonl'
        line = path.read_bytes().splitlines(keepends=True)[-1]
        with path.open('ab') as stream:
            stream.write(line + b'{"event":')
        state.event(fx.common, 'observation')
        result = state.lifecycle_events(fx.common)
        self.assertEqual(result['skipped'], {'duplicate': 1, 'torn': 1})
        self.assertEqual(len([e for e in status.journal(fx.common) if e['event'] == 'slot_changed']), 1)
        self.assertEqual([e['event'] for e in result['events']], ['accepted', 'admitted', 'dispatched'])
        # Clock corrections must not poison execution readers or future appends.
        with path.open('ab') as stream:
            stream.write(b'{"timestamp":0,"event":"clock_correction"}\n')
        state.journal._known.clear()  # a new helper process has no cached index
        fact = state.journal.fact(state.journal.context(fx.common, {'task_id': 'A'}), 'model_finished')
        self.assertTrue(state.event(fx.common, 'task_lifecycle', lifecycle=[fact]))
        self.assertEqual(state.lifecycle_events(fx.common)['events'][-1]['event'], 'model_finished')

    def test_uncommitted_task_edits_are_not_acceptance_or_hand_closure(self):
        fx = self.fx
        path = fx.repo / 'tasks/items/A.md'
        path.write_text(path.read_text().replace('status = "open"', 'status = "done"'))
        state.observe_history(fx.repo)
        self.assertEqual([e['event'] for e in state.lifecycle_events(fx.common)['events']], ['accepted'])
        fx.git('commit', '-qam', 'owner closure')
        state.observe_history(fx.repo, delivered_rev='HEAD')
        state.observe_history(fx.repo, delivered_rev='HEAD')
        events = state.lifecycle_events(fx.common)['events']
        self.assertEqual([e['event'] for e in events], ['accepted', 'hand_closed', 'closed', 'delivered'])
        self.assertEqual(events[0]['revision'], fx.base)

    def test_owner_contract_edits_during_an_attempt_include_reverted_edits(self):
        import task_store
        fx = self.fx
        fx.slot()
        branch = Path(fx.tmp.name) / 'owner-edits'
        fx.git('worktree', 'add', '-qb', 'owner-edits', str(branch))
        path = branch / 'tasks/items/A.md'
        original = path.read_text()
        path.write_text(task_store.edit(original, {'scope': 'A revised owner contract'}))
        fx.git('commit', '-qam', 'owner changes contract', repo=branch)
        changed = fx.git('rev-parse', 'HEAD', repo=branch)
        path.write_text(original)
        fx.git('commit', '-qam', 'owner restores contract', repo=branch)
        restored = fx.git('rev-parse', 'HEAD', repo=branch)
        fx.git('merge', '--no-ff', '-qm', 'merge owner edits', 'owner-edits')
        for target in ('reported', 'integrating', 'integrated', 'closed'):
            state.transition(fx.repo, fx.owner, 'A', target)
        history = fx.common / 'slot-history/A/1'
        history.mkdir(parents=True)
        slot_path = fx.common / 'slots/A.json'
        execution.save(slot_path, dict(execution.read(slot_path), telemetry_end_revision=fx.git('rev-parse', 'HEAD')))
        slot_path.rename(history / 'slot.json')
        original_at = task_store.TaskStore.at
        def outside_writer_lock(*args):
            with execution.lock(fx.common / 'writer.lock'):
                pass
            return original_at(*args)
        with patch.object(task_store.TaskStore, 'at', side_effect=outside_writer_lock):
            state.observe_history(fx.repo)
        before = (fx.common / 'journal.jsonl').read_bytes()
        path = fx.repo / 'tasks/items/A.md'
        path.write_text(task_store.edit(original, {'scope': 'A future attempt contract'}))
        fx.git('commit', '-qam', 'owner edits after retirement')
        state.observe_history(fx.repo)
        edits = [e for e in state.lifecycle_events(fx.common)['events'] if e['event'] == 'contract_edited']
        self.assertEqual([e['revision'] for e in edits], [changed, restored])
        self.assertEqual((fx.common / 'journal.jsonl').read_bytes(), before)

    def test_bounded_history_pages_progress_across_merged_sibling_branches(self):
        import lifecycle_history
        import task_store
        fx = self.fx
        fx.slot()
        for name in ('left', 'right'):
            tree = Path(fx.tmp.name) / name
            fx.git('worktree', 'add', '-qb', name, str(tree), fx.base)
            path = tree / 'tasks/items/A.md'
            for number in range(6):
                path.write_text(task_store.edit(path.read_text(), {'scope': f'{name} change {number}'}))
                fx.git('commit', '-qam', f'owner {name} {number}', repo=tree)
            fx.git('merge', '--no-ff', '-s', 'ours', '-qm', 'merge ' + name, name)
        with patch.object(lifecycle_history, 'HISTORY_BUDGET', 6):
            for _ in range(10):
                state.observe_history(fx.repo)
        edits = [e for e in state.lifecycle_events(fx.common)['events'] if e['event'] == 'contract_edited']
        self.assertEqual(len(edits), 12)
        self.assertEqual(len({e['revision'] for e in edits}), 12)

    def test_restart_adopts_a_live_worker_without_another_dispatch(self):
        fx = self.fx
        slot = fx.slot(worker=execution.identity(fx.owner))
        lease = execution.read(fx.common / 'coordinator.json')
        lease['owner']['start_ticks'] += 1
        execution.save(fx.common / 'coordinator.json', lease)
        before = (fx.common / 'slots/A.json').read_bytes()
        with patch.object(state.journal.os, 'write', side_effect=OSError('lost claim append')):
            fx.claim()
            state.release(fx.repo, fx.owner)
        self.assertEqual((fx.common / 'slots/A.json').read_bytes(), before)
        state.observe_history(fx.repo)
        events = state.lifecycle_events(fx.common)['events']
        self.assertEqual([e['event'] for e in events],
                         ['accepted', 'admitted', 'dispatched', 'restart', 'worker_adopted'])
        self.assertEqual({e['attempt_id'] for e in events}, {slot['attempt_id']})

    def test_each_clear_and_answer_survives_a_failed_append(self):
        import parallel_integrate as integrate
        fx = self.fx
        fx.slot()
        state.transition(fx.repo, fx.owner, 'A', 'reported', commit=fx.base)
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='validation')
        for _ in range(2):
            with patch.object(state.journal.os, 'write', side_effect=OSError('lost append')):
                integrate.clear_held(fx.repo, fx.owner, 'A')
            state.observe_history(fx.repo)
            state.transition(fx.repo, fx.owner, 'A', 'integrating')
            state.transition(fx.repo, fx.owner, 'A', 'held', cause='validation')
        integrate.clear_held(fx.repo, fx.owner, 'A')
        state.transition(fx.repo, fx.owner, 'A', 'integrating')
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='blocker')
        (fx.common / 'slot-data/A').mkdir(parents=True)
        with patch.object(state.journal.os, 'write', side_effect=OSError('lost append')):
            integrate.answer(fx.repo, fx.owner, 'A', 'private answer text')
        state.observe_history(fx.repo)
        events = state.lifecycle_events(fx.common)['events']
        self.assertEqual(sum(e['event'] == 'clear_held' for e in events), 3)
        self.assertEqual(sum(e['event'] == 'blocker_answered' for e in events), 1)
        self.assertNotIn('private answer text', json.dumps(events))

    def test_lifecycle_envelopes_exclude_prose_credentials_and_paths(self):
        fx = self.fx
        with patch.dict(os.environ, AUTOWORK_TELEMETRY_MODEL='/private/sk-secret',
                        AUTOWORK_TELEMETRY_HOST='C:/Users/private/profile'):
            fx.slot()
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='blocker',
                         reason='prompt text password=secret /private/file')
        events = state.lifecycle_events(fx.common)['events']
        text = json.dumps(events)
        for private in ('/private', 'prompt text', 'password', 'sk-secret', str(fx.repo)):
            self.assertNotIn(private, text)
        self.assertNotIn('reason', events[-1])
        self.assertFalse(fx.git('status', '--porcelain'))
