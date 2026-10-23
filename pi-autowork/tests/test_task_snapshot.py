"""Committed inventory and compatible runtime evidence at the public capture seam."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import store_fixture
import task_queue
from task_store import TaskStore, StoreError, edit
from pi_autowork import fleet_view, task_snapshot


class TaskSnapshotTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        store_fixture.write_todo(self.repo, '## Now\n- [ ] A — Alpha\n- [ ] B — Beta\n'
                                '## Next\n- [ ] C — Gamma\n## Needs decision\n- [ ] D — Decide\n')

    def observation(self, **updates):
        store = task_queue.store(self.repo)
        return dict(task_source=dict(workspace=str(self.repo), repository_identity=str(self.repo / '.git'),
                                     revision=store.rev, observed_at=time.time()),
                    tasks=[dict(task=t.id, state='waiting', contract_hash=t.contract_hash,
                                admitted_contract_hash=None) for t in store.tasks.values()], **updates)

    def test_membership_is_one_pinned_commit_not_pending_or_session_union(self):
        first = task_snapshot.capture(self.repo, engine_observation=None, generation=1)
        self.assertEqual(first.counts, (0, 0, 3, 0, 1, 4))
        self.assertEqual([r.task for r in first.rows], ['A', 'B', 'C', 'D'])
        self.assertTrue(all(r.why == 'ready; awaiting dispatch' for r in first.rows[:3]))
        path = self.repo / 'tasks/items/A.md'
        path.write_text(edit(path.read_text(), {'section': 'Needs decision'}))
        pending = task_snapshot.capture(self.repo, engine_observation=None, generation=2)
        self.assertEqual(pending.counts, first.counts)
        self.assertIn('tasks/items/A.md', pending.pending_paths)
        self.assertTrue(pending.rows[0].pending)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qam', 'decision'], check=True)
        changed = task_snapshot.capture(self.repo, engine_observation=None, generation=3)
        self.assertEqual(changed.counts, (0, 0, 2, 0, 2, 4))
        self.assertNotEqual(changed.revision, first.revision)
        store_fixture.write_todo(self.repo, '## Now\n- [ ] NEW — New committed task\n')
        final = task_snapshot.capture(self.repo, engine_observation=None, generation=4)
        self.assertEqual([r.task for r in final.rows], ['NEW'])
        self.assertEqual(final.counts, (0, 0, 1, 0, 0, 1))
        self.assertEqual(first.generation, 1)

    def test_only_compatible_current_observations_can_classify_inventory(self):
        path = self.repo / 'tasks/items/C.md'
        path.write_text(edit(path.read_text(), {'depends_on': ['D']}))
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qam', 'dependency'], check=True)
        obs = self.observation()
        by_id = {r['task']: r for r in obs['tasks']}
        by_id['A'].update(state='running', admitted_contract_hash=by_id['A']['contract_hash'], attempt=2)
        by_id['B'].update(state='integrated', admitted_contract_hash=by_id['B']['contract_hash'], attempt=1)
        by_id['C'].update(state='waiting', reason='dependency: D')
        obs['stopped_groups'] = [dict(label='D (outside Now/Next)', tasks=['C'], count=99)]
        obs['tasks'].append(dict(task='ORPHAN', state='integrated', contract_hash='old'))
        obs['task_source']['revision'] = 'session-revision'
        good = task_snapshot.capture(self.repo, engine_observation=obs, generation=1)
        self.assertEqual(good.counts, (1, 1, 0, 1, 1, 4))
        self.assertIn('session', ' '.join(good.annotations))
        self.assertIn('ORPHAN', ' '.join(good.annotations))
        # A raw slot/log may be stale even when today's observed current hash matches.
        for change in ('admitted', 'source', 'legacy', 'age', 'duplicate', 'slot'):
            with self.subTest(change=change):
                bad = json.loads(json.dumps(obs))
                if change == 'admitted':
                    for row in bad['tasks'][:2]:
                        row['admitted_contract_hash'] = 'old-contract'
                elif change == 'source':
                    bad['task_source']['repository_identity'] = '/another/.git'
                elif change == 'legacy':
                    for row in bad['tasks']:
                        row.pop('contract_hash', None)
                elif change == 'age':
                    bad['task_source']['observed_at'] = 1
                elif change == 'duplicate':
                    bad['tasks'] += bad['tasks'][:2]
                else:
                    bad['tasks'][0]['state'] = 'waiting'
                    bad['tasks'][1]['state'] = 'waiting'
                    bad['lanes'] = [fleet_view.Lane('A', 'implementing'), fleet_view.Lane('B', 'integrated')]
                result = task_snapshot.capture(self.repo, engine_observation=bad, generation=2)
                self.assertEqual(result.counts[:2], (0, 0))
                self.assertEqual(sum(result.counts[:5]), 4)

    def test_stale_log_phase_cannot_upgrade_a_current_reported_attempt(self):
        obs = self.observation()
        row = next(r for r in obs['tasks'] if r['task'] == 'A')
        row.update(state='reported', admitted_contract_hash=row['contract_hash'], attempt=2, started_at=time.time() - 60)
        slots = self.repo / '.git/autowork-execution/slots'
        slots.mkdir(parents=True)
        (slots / 'A.json').write_text(json.dumps(dict(task_id='A', state='reported', attempt=2, started_at=row['started_at'])))
        data = self.repo / '.git/autowork-execution/slot-data/A/attempt-2'
        data.mkdir(parents=True)
        (data / 'contract.json').write_text(json.dumps(dict(contract_hash=row['contract_hash'])))
        state = self.repo / 'runtime'
        state.mkdir()
        (state / 'runner.log').write_text('2020-01-01T00:00:00+00:00 A: landing\n')
        obs['lanes'] = fleet_view.lanes(fleet_view.Runner('repo', repo=str(self.repo), state_dir=str(state)))
        snapshot = task_snapshot.capture(self.repo, engine_observation=obs, generation=1)
        self.assertEqual(snapshot.counts, (0, 0, 3, 0, 1, 4))
        self.assertEqual(snapshot.rows[0].state, 'Waiting · Implemented')

    def test_rejected_execution_roots_do_not_stop_compatible_inventory(self):
        for kind in ('incompatible', 'duplicate', 'orphan', 'stale_state'):
            with self.subTest(kind=kind):
                obs = self.observation()
                root = next(r for r in obs['tasks'] if r['task'] == 'B')
                root.update(state='held', cause='blocker', admitted_contract_hash='old')
                if kind == 'duplicate':
                    root['admitted_contract_hash'] = root['contract_hash']
                    obs['tasks'].append(dict(root))
                if kind == 'orphan':
                    root['task'] = 'ORPHAN'
                if kind == 'stale_state':
                    root.update(state='waiting', admitted_contract_hash=None)
                obs['roots'] = [dict(id=root['task'], kind='held', cause='blocker', tasks=['A'], blocks=1)]
                obs['stopped_groups'] = [dict(label='old blockage', tasks=['A'], count=1)]
                snap = task_snapshot.capture(self.repo, engine_observation=obs, generation=1)
                self.assertEqual((snap.rows[0].bucket, snap.rows[0].why), ('Waiting', 'ready; awaiting dispatch'))

    def test_no_health_and_legacy_inventory_propagate_committed_stopping_dependencies(self):
        for task, dependency in (('A', 'B'), ('B', 'D')):
            path = self.repo / f'tasks/items/{task}.md'
            path.write_text(edit(path.read_text(), {'depends_on': [dependency]}))
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qam', 'dependencies'], check=True)
        for observation in (None, {'tasks': [['A', 'waiting', '', '']]},
                            dict(self.observation(), task_source={'observed_at': 1})):
            with self.subTest(observation=observation):
                snap = task_snapshot.capture(self.repo, engine_observation=observation, generation=1)
                self.assertEqual(snap.counts, (0, 0, 1, 2, 1, 4))
                self.assertIn('D', snap.rows[0].why)

    def test_unavailable_is_not_empty_and_pending_failure_is_not_clean(self):
        observation = self.observation()
        good = task_snapshot.capture(self.repo, engine_observation=observation, generation=1)
        with mock.patch.object(TaskStore, 'pending', side_effect=StoreError('pending denied')):
            failed = task_snapshot.capture(self.repo, engine_observation=None, generation=2)
        self.assertIsNone(failed.pending_paths)
        self.assertIn('pending denied', ' '.join(failed.errors))
        with mock.patch.object(task_queue, 'store', side_effect=StoreError('read denied')):
            unavailable = task_snapshot.capture(self.repo, engine_observation=None, generation=3)
            stale = task_snapshot.capture(self.repo, engine_observation=None, generation=4, last_good=good)
        self.assertIsNone(unavailable.counts)
        self.assertIsNone(fleet_view.task_counts(fleet_view.Runner('unknown')))
        for invalid in ('invalid observation', {'task_source': 'invalid source'},
                        {'task_source': {'observed_at': 'not a timestamp'}}):
            with self.subTest(invalid=invalid):
                result = task_snapshot.capture(self.repo, engine_observation=invalid, generation=4)
                self.assertEqual(result.counts, good.counts)
                self.assertEqual(result.engine_freshness, 'unknown')
                self.assertTrue(result.errors)
        self.assertEqual(stale.counts, good.counts)
        self.assertEqual((stale.revision, stale.captured_at, stale.freshness),
                         (good.revision, good.captured_at, 'stale'))
        future = time.time() + fleet_view.health.STALE_AFTER + 1
        with mock.patch.object(task_snapshot.time, 'time', return_value=future), \
                mock.patch.object(task_queue, 'store', side_effect=StoreError('read denied')):
            for obs in (observation, dict(observation, status_unavailable_since=future - 1)):
                stale = task_snapshot.capture(self.repo, engine_observation=obs, generation=5, last_good=good)
                self.assertEqual(stale.engine_freshness, 'stale')
                self.assertEqual(stale.engine_source.observed_at, good.engine_source.observed_at)
        store_fixture.write_todo(self.repo, '')
        empty = task_snapshot.capture(self.repo, engine_observation=None, generation=5)
        self.assertEqual(empty.counts, (0, 0, 0, 0, 0, 0))


if __name__ == '__main__':
    unittest.main()
