import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from audit_profiles import backlog_readiness, inspect_profile, progress


class CorrectnessTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def repo(self):
        root = self.root / 'repo'
        root.mkdir()
        self.git(root, 'init')
        self.git(root, 'config', 'user.email', 'fixture@example.test')
        self.git(root, 'config', 'user.name', 'Fixture')
        ledger = {'version': 1, 'primary_milestone': 'G1', 'goals': [
            {'id': 'G1', 'title': 'fixture', 'source': 'PLAN.md#accepted', 'status': 'unmet', 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'title': 'fixture task', 'goal': 'G1', 'status': 'open', 'section': 'Now'}]}
        (root / 'goals.json').write_text(json.dumps(ledger))
        (root / 'PLAN.md').write_text('# Accepted\nStatus: Accepted\n')
        (root / 'TODO.md').write_text('## Now\n- [ ] T1: fixture\n  Goal: G1\n  Scope: one file\n  Acceptance: run test\n  Dependencies: none\n  Sources: [accepted](PLAN.md#accepted)\n')
        self.git(root, 'add', '.')
        self.git(root, 'commit', '-m', 'fixture')
        return root

    def git(self, root, *args):
        subprocess.run(['git', '-C', str(root), *args], check=True, capture_output=True)

    def test_body_readiness_and_missing_scope_gate(self):
        root = self.repo()
        gaps = []
        before = {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()}
        ready = backlog_readiness(root, gaps)
        self.assertIn('tasks', ready, 'ledger eligibility must include consumer readiness')
        self.assertEqual(ready['tasks'][0]['state'], 'ready_for_autogoal')
        self.assertEqual(ready['live_ownership'], 'unknown')
        self.assertEqual(before, {p.name: p.read_bytes() for p in root.iterdir() if p.is_file()})
        (root / 'TODO.md').write_text((root / 'TODO.md').read_text().replace('  Scope: one file\n', ''))
        held = backlog_readiness(root, [])
        self.assertEqual(held['eligible_task_ids'], ['T1'])
        self.assertIn('T1: missing Scope', held['tasks'][0]['reasons'])
        self.assertEqual(held['tasks'][0]['state'], 'draft_saved')

    def test_unbound_linked_worktree_is_held_not_canonical_ready(self):
        root = self.repo()
        child = self.root / 'child'
        self.git(root, 'worktree', 'add', '-b', 'fixture-child', str(child))
        held = backlog_readiness(child, [])
        self.assertIn('canonical_readiness', held, 'canonical authority must be qualified')
        self.assertEqual(held['canonical_readiness']['state'], 'unknown')
        self.assertIn('canonical authority unbound linked worktree', held['canonical_readiness']['gate'])
        self.assertNotEqual(held['state'], 'ready_for_autogoal')
        self.assertFalse((root / '.git/.repo-docs-goals.lock').exists())

    def test_current_handoff_matches_reconcile_top_level_precedence(self):
        home = self.root / 'home'
        (home / 'autogoal/handoffs').mkdir(parents=True)
        path = home / 'autogoal/goal-handoff.json'
        path.write_text(json.dumps({'task_id': 'top', 'profile': 'other', 'run_id': 7,
                                    'current_handoff': {'task_id': 'nested'}}))
        (home / 'autogoal/handoffs/archived.json').write_text(json.dumps({'task_id': 'old'}))
        before = {str(p): p.read_bytes() for p in home.rglob('*') if p.is_file()}
        row = inspect_profile('one', home, None)
        current = row['continuity']['goal-handoff.json']
        self.assertEqual(current['task_id'], 'top')
        self.assertEqual(current['run_id'], 7)
        self.assertEqual(current['owner_profile'], 'other')
        self.assertEqual(row['live_ownership'], 'unknown')
        self.assertEqual(row['handoff_history']['files_observed'], 1)
        self.assertEqual(before, {str(p): p.read_bytes() for p in home.rglob('*') if p.is_file()})
        path.write_text(json.dumps({'task_id': None, 'current_handoff': {'task_id': 'nested'}}))
        self.assertEqual(inspect_profile('one', home, None)['continuity']['goal-handoff.json']['task_id'], 'nested')

    def test_new_worker_run_id_alone_does_not_reset_stagnation(self):
        row = {'continuity': {'goal-handoff.json': {'task_id': 't1', 'run_id': 1}},
               'repo': {'state': 'observed'},
               'executions': [{'id': 'r1', 'status': 'completed', 'finished_at': '1'}], 'gaps': []}
        _, saved = progress(row, {})
        row['continuity']['goal-handoff.json']['run_id'] = 2
        row['executions'][0]['id'] = 'r2'
        result, _ = progress(row, saved)
        self.assertEqual(result['consecutive'], 1)

    def test_invalid_task_identity_stays_unknown(self):
        row = {'continuity': {'state.json': {'task_id': 23}}, 'repo': {'state': 'observed'},
               'executions': [{'id': 'r1', 'status': 'completed', 'finished_at': '1'}], 'gaps': []}
        result, _ = progress(row, {})
        self.assertEqual(result['state'], 'unknown')

    def test_compact_large_consumer_reasons_are_bounded_with_receipt_gap(self):
        from audit_profiles import compact_profile
        row = {'profile': 'one', 'gaps': [], 'repo': {'state': 'observed',
               'backlog_readiness': {'tasks': [{'task_id': 'T1', 'state': 'draft_saved',
               'reasons': ['missing source: ' + 'x' * 10000]}]}},
               'jobs': [], 'executions': [], 'logs': [], 'continuity': {},
               'no_progress': {'state': 'unknown'}}
        gates = compact_profile(row, None)['task_gates']
        self.assertLess(len(json.dumps(gates)), 1000)
        self.assertEqual(gates['reason_count'], 1)
        self.assertTrue(gates['details_omitted'])

    def test_compact_deduplicates_shared_consumer_blockers(self):
        from audit_profiles import compact_profile
        reason = 'T1: missing Scope'
        row = {'profile': 'one', 'gaps': [], 'repo': {'state': 'observed', 'backlog_readiness': {'tasks': [
            {'task_id': 'T1', 'state': 'draft_saved', 'reasons': [reason]},
            {'task_id': 'T2', 'state': 'draft_saved', 'reasons': [reason]}]}}, 'jobs': [], 'executions': [],
            'logs': [], 'continuity': {}, 'no_progress': {'state': 'unknown'}}
        self.assertEqual(json.dumps(compact_profile(row, None)).count(reason), 1)

    def test_previously_observed_completed_run_is_not_counted_again(self):
        row = {'continuity': {'state.json': {'task_id': 't1'}}, 'repo': {'state': 'observed'},
               'executions': [{'id': 'r1', 'status': 'completed', 'finished_at': '1'}], 'gaps': []}
        _, saved = progress(row, {})
        row['executions'][0]['id'] = 'r2'
        result, saved = progress(row, saved)
        self.assertEqual(result['consecutive'], 1)
        row['executions'][0]['id'] = 'r1'
        result, _ = progress(row, saved)
        self.assertEqual(result['consecutive'], 1)

    def test_unknown_execution_gap_does_not_recount_same_run(self):
        row = {'continuity': {'state.json': {'task_id': 't1'}}, 'repo': {'state': 'observed'},
               'executions': [{'id': 'r1', 'status': 'completed', 'finished_at': '1'}], 'gaps': []}
        _, saved = progress(row, {})
        row['executions'] = []
        result, saved = progress(row, saved)
        self.assertEqual(result['state'], 'unknown')
        row['executions'] = [{'id': 'r1', 'status': 'completed', 'finished_at': '1'}]
        result, _ = progress(row, saved)
        self.assertEqual(result['consecutive'], 0)

    def test_compact_unchanged_preserves_blockers_failures_and_coverage(self):
        row = {'profile': 'one', 'gaps': ['untracked content not inspected'], 'repo': {'state': 'observed', 'head': 'abc'},
               'jobs': [{'id': 'j', 'last_error': 'failed'}], 'executions': [], 'logs': [],
               'continuity': {'goal-handoff.json': {'task_id': 't', 'blocker': 'owner decision'}},
               'no_progress': {'state': 'unknown', 'consecutive': 0}, 'live_ownership': 'unknown'}
        import audit_profiles
        self.assertTrue(hasattr(audit_profiles, 'compact_profile'), 'compact stdout projection required')
        compact_profile = audit_profiles.compact_profile
        first = compact_profile(row, None)
        second = compact_profile(row, first)
        self.assertNotIn('head', second)
        self.assertIn('failed', json.dumps(second))
        self.assertIn('owner decision', json.dumps(second))
        self.assertIn('untracked content not inspected', json.dumps(second))


if __name__ == '__main__':
    unittest.main()
