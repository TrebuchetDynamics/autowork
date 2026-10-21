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

    def test_closed_offline_slice_keeps_live_prerequisite_ineligible(self):
        import retry_selection
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].extend(['OFFLINE', 'LIVE'])
        data['tasks'].extend([
            dict(id='OFFLINE', title='Reviewed offline slice', goal='G1', status='done', section='Done'),
            dict(id='LIVE', title='Live qualification', goal='G1', status='open', section='Needs decision')])
        data['tasks'][0]['depends_on'] = ['LIVE']
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('Dependencies: None', 'Dependencies: LIVE') +
            '\n## Needs decision\n\n- [ ] LIVE: Live qualification\n  Goal: G1\n'
            '  Scope: live provider\n  Acceptance: live journey passes\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Plan](SPEC.md#accepted)\n')
        before = {p: p.read_bytes() for p in (ledger, todo)}
        result = retry_selection.select(self.consumer, plan='SPEC.md#accepted', task_ids=['T1'])
        self.assertNotEqual(result['state'], 'ready_for_autowork')
        self.assertIn('T1: unmet task dependency LIVE', result['reasons'])
        self.assertEqual(retry_selection.goals.load(self.consumer)['goals'][0]['status'], 'unmet')
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_todo_only_dependency_prevents_selection(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append(dict(data['tasks'][0], id='T2', section='Next'))
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        body = todo.read_text()
        todo.write_text(body.replace('Dependencies: None', 'Dependencies: [T2](TODO.md)') +
                        body.replace('# TODO\n\n## Now', '## Next').replace('T1:', 'T2:'))
        before = {p: p.read_bytes() for p in (ledger, todo)}
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved', result)
        self.assertIn('T1: Dependencies name T2 absent from ledger', result['reasons'])
        for path, contents in before.items():
            self.assertEqual(path.read_bytes(), contents)

    def test_dependency_notes_do_not_create_undeclared_prerequisites(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append(dict(data['tasks'][0], id='T2', section='Next'))
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        body = todo.read_text()
        for declaration in (
                'None. Ownership: coordinate with the T2 owner before overlap.',
                'None at the ledger level. T2 is preferred first, not a prerequisite.',
                'None for offline work. Live qualification stays with T2.',
                'None. T2 is complete; do not repeat its implementation.'):
            with self.subTest(declaration=declaration):
                todo.write_text(body.replace('Dependencies: None', 'Dependencies: ' + declaration) +
                                body.replace('# TODO\n\n## Now', '## Next').replace('T1:', 'T2:'))
                result = self.retry()
                self.assertEqual(result['state'], 'ready_for_autowork', result)
                self.assertEqual(result['selected_task']['id'], 'T1')

    def test_dependency_identifiers_keep_exact_word_and_hyphen_boundaries(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].extend(['T2', 'T2-extra'])
        data['tasks'].extend(dict(data['tasks'][0], id=tid, section='Next')
                             for tid in ('T2', 'T2-extra'))
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        body = todo.read_text()
        rest = ''.join(body.replace('# TODO\n\n## Now', '## Next').replace('T1:', tid + ':')
                       for tid in ('T2', 'T2-extra'))
        cases = [
            ('T2', ['T2']),
            ('[T2](TODO.md), `T2-extra`; G1.', ['G1', 'T2', 'T2-extra']),
            ('T2-extra', ['T2-extra']),
            ('T20 preT2 T2post _T2 T2_ -T2 T2- αT2 T2é', []),
            ('T2/T2-extra', ['T2', 'T2-extra']),
            ('None. Coordinate with T2 and T2-extra.', []),
        ]
        for declaration, expected in cases:
            with self.subTest(declaration=declaration):
                todo.write_text(body.replace('Dependencies: None', 'Dependencies: ' + declaration) + rest)
                result = self.retry()
                reasons = [reason for reason in result['reasons'] if reason.startswith('T1: Dependencies')]
                self.assertEqual(reasons, [f'T1: Dependencies name {tid} absent from ledger' for tid in expected])
                self.assertEqual(result['state'], 'draft_saved' if expected else 'ready_for_autowork')

    def test_non_token_goal_dependencies_remain_binding(self):
        ledger = self.consumer / 'goals.json'
        original = json.loads(ledger.read_text())
        todo = self.consumer / 'TODO.md'
        original_body = todo.read_text()
        for goal_id in ('G.release', 'Release 1', 'G[release]', 'G.release.v2'):
            for declared in (False, True):
                with self.subTest(goal=goal_id, declared=declared):
                    data = json.loads(json.dumps(original))
                    data['goals'].append(dict(id=goal_id, title='Prerequisite', source='SPEC.md#accepted',
                                             status='unmet', tasks=['T2']))
                    data['tasks'].append(dict(id='T2', goal=goal_id, title='Prerequisite',
                                              status='open', section='Next'))
                    if declared:
                        data['goals'][0]['depends_on'] = [goal_id]
                    ledger.write_text(json.dumps(data))
                    todo.write_text(original_body.replace('Dependencies: None', 'Dependencies: ' + goal_id) +
                                    original_body.replace('# TODO\n\n## Now', '## Next')
                                    .replace('T1:', 'T2:').replace('Goal: G1', 'Goal: ' + goal_id))
                    result = self.retry(plan='SPEC.md#accepted', task_ids=['T1'])
                    if declared:
                        self.assertEqual(result['state'], 'backlog_reconciled_not_eligible', result)
                        self.assertIn('T1: unmet goal dependency ' + goal_id, result['reasons'])
                        self.assertNotIn('T1: Dependencies do not name ' + goal_id, result['reasons'])
                    else:
                        self.assertEqual(result['state'], 'draft_saved', result)
                        self.assertIn('T1: Dependencies name ' + goal_id + ' absent from ledger', result['reasons'])

    def test_dependency_notes_cannot_satisfy_missing_ledger_prerequisite(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append(dict(data['tasks'][0], id='T2', status='done', section='Done'))
        data['tasks'][0]['depends_on'] = ['T2']
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('Dependencies: None',
                        'Dependencies: None. Ownership: coordinate with T2.'))
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved', result)
        self.assertIn('T1: Dependencies do not name T2', result['reasons'])

    def test_dependency_lists_and_continued_requirements_remain_binding(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].extend(['T2', 'T3'])
        data['tasks'].extend([dict(data['tasks'][0], id=tid, section='Next') for tid in ('T2', 'T3')])
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        body = todo.read_text()
        for value in ('\n    1. T2\n    2. T3', '\n    - T2.\n    - T3',
                      'Required first. T2 must complete before starting; then T3.'):
            with self.subTest(value=value):
                todo.write_text(body.replace('Dependencies: None', 'Dependencies: ' + value) +
                                ''.join(body.replace('# TODO\n\n## Now', '## Next').replace('T1:', tid + ':')
                                        for tid in ('T2', 'T3')))
                result = self.retry()
                self.assertEqual(result['state'], 'draft_saved', result)
                for tid in ('T2', 'T3'):
                    self.assertIn(f'T1: Dependencies name {tid} absent from ledger', result['reasons'])

    def test_reopened_todo_task_prevents_selecting_another_task(self):
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append(dict(data['tasks'][0], id='T2'))
        data['tasks'][0].update(status='done', section='Done')
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        body = todo.read_text()
        todo.write_text(body + body.replace('T1:', 'T2:'))
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved', result)
        self.assertIn('T1: checkbox/section does not match done ledger task', result['reasons'])
        # Completed tasks may be archived entirely or retained as checked history.
        for history in ('', body.replace('## Now', '## Done').replace('[ ]', '[x]')):
            todo.write_text(history + body.replace('T1:', 'T2:'))
            result = self.retry()
            self.assertEqual(result['state'], 'ready_for_autowork', result)
            self.assertEqual(result['selected_task']['id'], 'T2')

    def claim(self, task='T1', status='ACTIVE', workspace='/fixture/writer'):
        path = self.consumer / 'docs/coordination/worktree-registry.jsonl'
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('a') as stream:
            stream.write(json.dumps({'task': task, 'owner': 'writer',
                                     'worktree': workspace, 'status': status}) + '\n')

    def registry_rows(self, rows):
        import retry_selection
        path = self.consumer / retry_selection.REGISTRY
        path.parent.mkdir(parents=True, exist_ok=True)
        blob = ''.join(json.dumps(row) + '\n' for row in rows).encode()
        path.write_bytes(blob)
        claims = retry_selection.registered_claims(self.consumer)[0]
        self.assertEqual(path.read_bytes(), blob)
        return claims

    def test_partial_update_retains_unique_original_claim_and_metadata(self):
        original = {'task': 'T1', 'owner': 'writer', 'worktree': '/fixture/one',
                    'status': 'ACTIVE', 'scope': ['source.rs'], 'initial_gate': 'not_observed'}
        claims = self.registry_rows([original,
            {'task': 'T1', 'owner': 'writer', 'status': 'INTEGRATED_VERIFIED', 'result': 'offline'}])
        self.assertEqual(claims, [dict(original, status='INTEGRATED_VERIFIED', result='offline')])
        self.assertEqual(self.retry(plan='SPEC.md#accepted', task_ids=['T1'])['state'],
                         'backlog_reconciled_not_eligible')

    def test_alias_claim_and_partial_update_bind_without_releasing_other_workspace(self):
        original = {'task_id': 'T1', 'owner': 'writer', 'workspace': '/fixture/one',
                    'status': 'ACTIVE', 'scope': ['source.rs']}
        other = {'task': 'T1', 'owner': 'other', 'worktree': '/fixture/two', 'status': 'ACTIVE'}
        claims = self.registry_rows([original, other,
            {'task': 'T1', 'owner': 'writer', 'status': 'INTEGRATED'}])
        self.assertEqual(claims, [other])
        self.assertEqual(self.retry(plan='SPEC.md#accepted', task_ids=['T1'])['state'],
                         'backlog_reconciled_not_eligible')

    def test_matching_aliases_and_explicit_release_are_supported(self):
        claims = self.registry_rows([
            {'task': 'T1', 'task_id': 'T1', 'owner': 'writer', 'worktree': '/fixture/one',
             'workspace': '/fixture/one', 'status': 'ACTIVE'},
            {'task_id': 'T1', 'owner': 'writer', 'workspace': '/fixture/one', 'status': 'RELEASED'}])
        self.assertEqual(claims, [])
        self.assertEqual(self.retry()['state'], 'ready_for_autowork')

    def test_alias_partial_live_claim_does_not_starve_disjoint_open_task(self):
        import retry_selection
        import progress_runtime
        self.registry_rows([
            {'task_id': 'T1', 'owner': 'writer', 'workspace': '/fixture/one', 'status': 'ACTIVE'},
            {'task_id': 'T1', 'owner': 'writer', 'status': 'REVIEW_APPROVED_UNINTEGRATED'}])
        ledger = self.consumer / 'goals.json'
        data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append(dict(data['tasks'][0], id='T2', title='Disjoint'))
        ledger.write_text(json.dumps(data))
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text() + '\n- [ ] T2: Disjoint\n  Goal: G1\n'
            '  Scope: other.rs only\n  Acceptance: tests pass\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Plan](SPEC.md#accepted)\n')
        before = {p: p.read_bytes() for p in (ledger, todo, self.consumer / retry_selection.REGISTRY)}
        self.assertEqual(self.retry()['selected_task']['id'], 'T2')
        self.assertEqual([c['task']['id'] for c in
            retry_selection.repository_frontier(self.consumer, require_owner=True)['candidates']], ['T2'])
        self.assertEqual([t['id'] for t in
            progress_runtime.ready_queue(self.consumer, require_owner=True)['tasks']], ['T2'])
        held = self.retry(plan='SPEC.md#accepted', task_ids=['T1'])
        self.assertEqual(held['state'], 'backlog_reconciled_not_eligible')
        self.assertEqual(held['held_claims'][0]['status'], 'REVIEW_APPROVED_UNINTEGRATED')
        for path, content in before.items():
            self.assertEqual(path.read_bytes(), content)

    def test_partial_update_does_not_guess_among_historical_workspaces(self):
        import retry_selection
        self.claim(status='RELEASED', workspace='/fixture/one')
        self.claim(workspace='/fixture/two')
        path = self.consumer / retry_selection.REGISTRY
        with path.open('a') as stream:
            stream.write(json.dumps({'task': 'T1', 'owner': 'writer', 'status': 'INTEGRATED'}) + '\n')
        before = path.read_bytes()
        with self.assertRaisesRegex(ValueError, 'ambiguous.*worktree'):
            retry_selection.registered_claims(self.consumer)
        self.assertEqual(path.read_bytes(), before)

    def test_registry_rejects_conflicting_aliases_missing_and_malformed_identities(self):
        import retry_selection
        original = {'task': 'T1', 'owner': 'writer', 'worktree': '/fixture/one', 'status': 'ACTIVE'}
        cases = [dict(original, task_id='T2'), dict(original, workspace='/fixture/two'),
                 dict(original, owner='other'), dict(original, task=' '),
                 dict(original, task='T 1'), dict(original, worktree='relative'),
                 dict(original, worktree=''), dict(original, workspace=None),
                 dict(original, owner=None), dict(original, status=''),
                 {'task': 'T1', 'owner': 'writer', 'status': 'RELEASED', 'worktree': None},
                 {'task': 'T2', 'owner': 'writer', 'status': 'INTEGRATED'},
                 {'owner': 'writer', 'status': 'INTEGRATED', 'worktree': '/fixture/one'},
                 {'task': 'T1', 'status': 'INTEGRATED'}]
        path = self.consumer / retry_selection.REGISTRY
        path.parent.mkdir(parents=True, exist_ok=True)
        for row in cases:
            with self.subTest(row=row):
                path.write_text(json.dumps(original) + '\n' + json.dumps(row) + '\n')
                before = path.read_bytes()
                with self.assertRaisesRegex(ValueError, 'invalid worktree registry.*:2:'):
                    retry_selection.registered_claims(self.consumer)
                self.assertEqual(path.read_bytes(), before)

    def test_completion_empty_release_fields_and_status_prefixes_keep_holds(self):
        for status in ('ACTIVE', 'COMPLETED', 'REVIEW_APPROVED_UNINTEGRATED',
                       'INTEGRATED_VERIFIED', 'INTEGRATED_OFFLINE', 'RELEASED_VERIFIED',
                       'RELEASED_NO_CHANGE', 'PLANNING_INTEGRATED', 'PREPARATION_FAILED'):
            with self.subTest(status=status):
                row = {'task_id': 'T1', 'owner': 'writer', 'workspace': '/fixture/one',
                       'status': status, 'created_at': '2000-01-01', 'removed_at': None,
                       'integrated_commit_sha': None, 'released_at': ''}
                self.assertEqual(self.registry_rows([row])[0]['status'], status)

    def test_duplicate_identity_json_keys_are_not_last_writer_wins(self):
        import retry_selection
        path = self.consumer / retry_selection.REGISTRY
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('{"task":"T1","task":"T2","owner":"writer",'
                        '"worktree":"/fixture/one","status":"ACTIVE"}\n')
        with self.assertRaisesRegex(ValueError, 'invalid worktree registry'):
            retry_selection.registered_claims(self.consumer)

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

    def test_registry_diagnostic_locates_bad_record_without_disclosing_contents(self):
        self.claim(status='INTEGRATED')
        path = self.consumer / 'docs/coordination/worktree-registry.jsonl'
        valid = path.read_text()
        for invalid, detail in (
                (json.dumps({'task': 'T1', 'owner': 'fixture', 'status': 'INTEGRATED'}), 'worktree'),
                ('{"private_note": "fixture-do-not-disclose",', 'malformed JSON'),
                ('[]', 'expected object')):
            with self.subTest(invalid=invalid):
                path.write_text(valid + '\n' + invalid + '\n')
                before = path.read_bytes()
                with self.assertRaises(ValueError) as raised:
                    self.retry()
                message = str(raised.exception)
                self.assertIn('docs/coordination/worktree-registry.jsonl:3', message)
                self.assertIn(detail, message)
                self.assertNotIn('fixture-do-not-disclose', message)
                self.assertEqual(path.read_bytes(), before)

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

    def test_task_plan_takes_precedence_over_unlinked_accepted_goal_plan(self):
        (self.consumer / 'SLICE.md').write_text('# Slice\n\nStatus: Accepted\n')
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('SPEC.md#accepted', 'SLICE.md#slice'))
        before = todo.read_bytes()
        result = self.retry()
        self.assertEqual(result['state'], 'ready_for_autowork', result)
        self.assertEqual(result['plan'], 'SLICE.md#slice')
        self.assertEqual(result['selected_task']['id'], 'T1')
        self.assertEqual(todo.read_bytes(), before)

    def test_equivalent_task_sources_are_one_plan(self):
        todo = self.consumer / 'TODO.md'
        todo.write_text(todo.read_text().replace('Sources: [Plan](SPEC.md#accepted)',
            'Sources: [Plan](SPEC.md#accepted), [Same](./SPEC.md#accepted)'))
        data_path = self.consumer / 'goals.json'
        data = json.loads(data_path.read_text())
        (self.consumer / 'README.md').write_text('Intent\n')
        data['goals'][0]['source'] = 'README.md'
        data_path.write_text(json.dumps(data))
        result = self.retry()
        self.assertEqual(result['state'], 'ready_for_autowork', result)
        self.assertEqual(result['plan'], 'SPEC.md#accepted')

    def test_conflicting_plan_status_is_not_ready(self):
        (self.consumer / 'SPEC.md').write_text('# Accepted\nStatus: Accepted\nStatus: Proposed\n')
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved', result)
        self.assertIsNone(result['selected_task'])
        self.assertIn('plan section has conflicting or duplicate Status metadata', result['reasons'])

    def test_dependency_cycle_is_reported_instead_of_empty_queue(self):
        path = self.consumer / 'goals.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['depends_on'] = ['T1']
        path.write_text(json.dumps(data))
        result = self.retry()
        self.assertEqual(result['state'], 'draft_saved', result)
        self.assertIn('task dependency cycle: T1 -> T1', result['reasons'])

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
