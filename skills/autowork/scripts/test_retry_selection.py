"""Retry uses the real consumer after fallback, never a docs-only scratch backlog."""
import importlib.util
import json
from pathlib import Path
import subprocess
import tempfile
import unittest


class RetrySelectionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.consumer = self.root / 'consumer'
        self.consumer.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.consumer)], check=True)
        (self.consumer / 'SPEC.md').write_text('# Accepted\n\nStatus: Accepted\n')
        (self.consumer / 'TODO.md').write_text('# TODO\n\n## Now\n\n- [ ] T1: Startup\n'
            '  Goal: G1\n  Scope: Startup\n  Acceptance: startup passes\n'
            '  Dependencies: None\n  Ownership: fixture\n  Sources: [Plan](SPEC.md#accepted)\n')
        (self.consumer / 'goals.json').write_text(json.dumps({'version': 1,
            'primary_milestone': 'G1', 'goals': [{'id': 'G1', 'title': 'Startup',
                'status': 'unmet', 'source': 'SPEC.md#accepted', 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'goal': 'G1', 'title': 'Startup', 'status': 'open', 'section': 'Now'}]}))

    def retry(self, consumer=None, **kwargs):
        self.assertIsNotNone(importlib.util.find_spec('retry_selection'), 'missing consumer retry helper')
        import retry_selection
        kwargs.setdefault('require_owner', True)
        return retry_selection.select(consumer or self.consumer, **kwargs)

    def test_default_requires_no_owner_release_for_open_task(self):
        import retry_selection
        self.claim()
        result = retry_selection.select(self.consumer)
        self.assertEqual(result['state'], 'ready_for_autowork')
        self.assertEqual(result['selected_task']['id'], 'T1')
        self.assertEqual(result['held_claims'], [])
        self.assertEqual(result['recorded_claims'][0]['owner'], 'writer')

    def claim(self, task='T1', status='ACTIVE', workspace='/fixture/writer'):
        path = self.consumer / 'docs/coordination/worktree-registry.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as stream:
            stream.write(json.dumps({'task': task, 'owner': 'writer',
                                     'worktree': workspace, 'status': status}) + '\n')

    def test_open_ledger_task_with_registered_writer_is_not_ready(self):
        self.claim()
        result = self.retry(plan='SPEC.md#accepted', task_ids=['T1'])
        self.assertEqual(result['state'], 'backlog_reconciled_not_eligible')
        self.assertIsNone(result['selected_task'])
        self.assertIn('registered writer', ' '.join(result['reasons']))

    def test_claimed_primary_does_not_hide_independent_frontier(self):
        import retry_selection
        self.claim()
        p = self.consumer / 'goals.json'; data = json.loads(p.read_text())
        data['goals'].append({'id':'G2','title':'Independent','status':'unmet',
                             'source':'SPEC.md#accepted','tasks':['T2']})
        data['tasks'].append({'id':'T2','goal':'G2','title':'Independent',
                             'status':'open','section':'Now'})
        p.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text() + '\n- [ ] T2: Independent\n  Goal: G2\n'
            '  Scope: independent files\n  Acceptance: test passes\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Plan](SPEC.md#accepted)\n')
        before = {p: p.read_bytes(), todo: todo.read_bytes()}
        result = retry_selection.repository_frontier(self.consumer, require_owner=True)
        self.assertEqual([r['task']['id'] for r in result['candidates']], ['T2'])
        self.assertTrue(result['candidates'][0]['requires_fallback_attestation'])
        self.assertEqual(result['held_claims'][0]['task'], 'T1')
        for path, content in before.items(): self.assertEqual(path.read_bytes(), content)
        # The same-milestone queue must not reinsert the excluded first writer.
        data['goals'].pop()
        data['goals'][0]['tasks'].append('T2')
        data['tasks'][1]['goal'] = 'G1'
        p.write_text(json.dumps(data))
        todo.write_text(todo.read_text().replace('Goal: G2', 'Goal: G1'))
        self.assertEqual(self.retry()['selected_task']['id'], 'T2')
        import progress_runtime
        self.assertEqual([t['id'] for t in progress_runtime.ready_queue(self.consumer, require_owner=True)['tasks']], ['T2'])

    def test_release_of_one_workspace_does_not_release_another(self):
        self.claim(workspace='/fixture/one'); self.claim(workspace='/fixture/two')
        self.claim(status='RELEASED', workspace='/fixture/one')
        self.assertEqual(self.retry(plan='SPEC.md#accepted', task_ids=['T1'])['state'],
                         'backlog_reconciled_not_eligible')
        self.claim(status='RELEASED', workspace='/fixture/two')
        self.assertEqual(self.retry()['state'], 'ready_for_autowork')

    def test_registry_change_during_check_invalidates_selection(self):
        import retry_selection
        from unittest.mock import patch
        original = retry_selection.goals.backlog_check
        def intervening_claim(args):
            self.claim()
            return original(args)
        with patch.object(retry_selection.goals, 'backlog_check', side_effect=intervening_claim):
            result = self.retry()
        self.assertEqual(result['state'], 'draft_saved')
        self.assertIsNone(result['selected_task'])
        self.assertIn('consumer changed during retry', result['reasons'])

    def test_malformed_registry_is_not_treated_as_no_claims(self):
        self.claim()
        (self.consumer / 'docs/coordination/worktree-registry.jsonl').write_text('{}\n')
        with self.assertRaisesRegex(ValueError, 'invalid worktree registry'):
            self.retry()

    def test_named_gated_task_still_reports_repairable_contract_defects(self):
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['section'] = 'Needs decision'
        path.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('## Now', '## Needs decision')
                        .replace('[Plan](SPEC.md#accepted)', 'existing decision'))
        before = todo.read_bytes()
        result = self.retry(plan='SPEC.md#accepted', task_ids=['T1'])
        self.assertIn('T1: Sources do not link accepted plan', result['reasons'])
        self.assertIsNone(result['selected_task'])
        self.assertEqual(todo.read_bytes(), before)
        todo.write_text(todo.read_text().replace('existing decision', '[Plan](SPEC.md#accepted)'))
        result = self.retry(plan='SPEC.md#accepted', task_ids=['T1'])
        self.assertEqual(result['state'], 'backlog_reconciled_not_eligible')
        self.assertTrue(any('section=Needs decision' in r for r in result['reasons']))
        self.assertIsNone(result['selected_task'])

    def test_multiple_accepted_task_sources_require_named_plan(self):
        (self.consumer / 'README.md').write_text('Product intent\n')
        (self.consumer / 'SECOND.md').write_text('# Accepted\n\nStatus: Accepted\n')
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['goals'][0]['source'] = 'README.md'
        path.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('Sources: [Plan](SPEC.md#accepted)',
                        'Sources: [Plan](SPEC.md#accepted), [Other accepted plan](SECOND.md#accepted)'))
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved')
        self.assertIsNone(result['selected_task'])
        self.assertIn('multiple accepted task-source plans', result['reasons'][0])
        self.assertEqual(self.retry(plan='SPEC.md#accepted', task_ids=['T1'])['state'], 'ready_for_autowork')

    def test_observed_concurrent_ledger_change_cannot_return_stale_selected_task(self):
        import retry_selection
        from unittest.mock import patch
        path = self.consumer / 'goals.json'
        original = retry_selection.goals.backlog_check
        def intervening_write(args):
            data = json.loads(path.read_text())
            data['tasks'][0]['title'] = 'Concurrent revised slice'
            path.write_text(json.dumps(data))
            return original(args)
        with patch.object(retry_selection.goals, 'backlog_check', side_effect=intervening_write):
            result = self.retry()
        self.assertEqual(result['state'], 'draft_saved')
        self.assertIsNone(result['selected_task'])
        self.assertIn('consumer changed during retry', result['reasons'])

    def test_retry_uses_unique_accepted_task_source_when_goal_source_is_not_a_plan(self):
        (self.consumer / 'README.md').write_text('Product intent\n')
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['goals'][0]['source'] = 'README.md'
        path.write_text(json.dumps(data))
        result = self.retry()
        self.assertEqual(result['state'], 'ready_for_autowork', result)
        self.assertEqual(result['plan'], 'SPEC.md#accepted')
        self.assertEqual(result['selected_task']['id'], 'T1')

    def test_absent_consumer_is_draft_even_when_docs_scratch_has_backlog(self):
        (self.consumer / 'goals.json').unlink()
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved')
        self.assertIsNone(result['selected_task'])
        self.assertIn('consumer backlog absent', result['reasons'][0])

    def test_in_progress_frontier_is_not_claimed_or_replaced(self):
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['status'] = 'in_progress'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        result = self.retry()
        self.assertEqual(result['state'], 'backlog_reconciled_not_eligible')
        self.assertIsNone(result['selected_task'])
        self.assertIn('T1: already in progress', result['reasons'])
        self.assertEqual(before, path.read_bytes())

    def test_in_progress_task_does_not_starve_independent_open_work(self):
        import retry_selection
        import progress_runtime
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['status'] = 'in_progress'
        data['goals'][0]['tasks'].extend(['T2', 'T3'])
        data['tasks'].extend([
            {'id': 'T2', 'goal': 'G1', 'title': 'Independent', 'status': 'open', 'section': 'Now'},
            {'id': 'T3', 'goal': 'G1', 'title': 'Dependent', 'status': 'open', 'section': 'Now',
             'depends_on': ['T1']}])
        path.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        for tid, deps in [('T2', 'None'), ('T3', 'T1')]:
            with todo.open('a') as stream:
                stream.write(f'\n- [ ] {tid}: Follow-up\n  Goal: G1\n'
                    f'  Scope: separate files\n  Acceptance: tests pass\n  Dependencies: {deps}\n'
                    '  Ownership: fixture\n  Sources: [Plan](SPEC.md#accepted)\n')
        before = {p: p.read_bytes() for p in (path, todo)}
        for require_owner in (False, True):
            with self.subTest(require_owner=require_owner):
                result = retry_selection.select(self.consumer, require_owner=require_owner)
                self.assertEqual(result['state'], 'ready_for_autowork', result)
                self.assertEqual(result['selected_task']['id'], 'T2')
                self.assertEqual(result['reconciliation_task_ids'], ['T1'])
                queue = progress_runtime.ready_queue(self.consumer, require_owner=require_owner)
                self.assertEqual([t['id'] for t in queue['tasks']], ['T2'])
                frontier = retry_selection.repository_frontier(self.consumer, require_owner=require_owner)
                self.assertEqual([c['task']['id'] for c in frontier['candidates']], ['T2'])
                dependent = retry_selection.select(self.consumer, plan='SPEC.md#accepted', task_ids=['T3'])
                self.assertNotEqual(dependent['state'], 'ready_for_autowork')
                duplicate = retry_selection.select(self.consumer, plan='SPEC.md#accepted', task_ids=['T1'])
                self.assertNotEqual(duplicate['state'], 'ready_for_autowork')
        for p, content in before.items():
            self.assertEqual(p.read_bytes(), content)

    def test_named_plan_cannot_substitute_unknown_requested_task(self):
        result = self.retry(plan='SPEC.md#accepted', task_ids=['T-not-here'])
        self.assertEqual(result['state'], 'draft_saved')
        self.assertIsNone(result['selected_task'])
        self.assertIn('unknown task T-not-here', result['reasons'])

    def test_consumer_retry_selects_new_backlog_without_cached_none(self):
        before = {p.name: p.read_bytes() for p in self.consumer.iterdir() if p.is_file()}
        docs_only = self.root / 'docs-only'
        docs_only.mkdir()
        (docs_only / 'goals.json').write_text('{"scratch":"not consumer"}')
        result = self.retry()
        self.assertEqual(result['state'], 'ready_for_autowork')
        self.assertEqual(result['selected_task']['id'], 'T1')
        self.assertEqual(result['authoritative_repo'], str(self.consumer))
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.consumer.iterdir() if p.is_file()})


if __name__ == '__main__':
    unittest.main()
