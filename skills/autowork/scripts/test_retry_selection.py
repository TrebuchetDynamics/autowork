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
        return retry_selection.select(consumer or self.consumer, **kwargs)

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
