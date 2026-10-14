"""Read-only reconciliation regressions: never launch workers or messages."""
import importlib.util
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from test_delivery_state import EvidenceFixture, SCRATCH

spec = importlib.util.spec_from_file_location('reconcile', Path(__file__).with_name('reconcile.py'))
m = importlib.util.module_from_spec(spec) if spec else None
if spec and spec.loader and Path(spec.origin).exists():
    spec.loader.exec_module(m)
else:
    m = None

class ReconcileTests(unittest.TestCase):
    def test_recovery_reports_missing_native_cap_without_treating_metadata_as_capability(self):
        snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'blocked'},
                    'runs': [{'id': 1, 'profile': 'fixture', 'status': 'blocked',
                              'metadata': {'continuation': {'atomic_continue': True, 'remaining': 100}}}]}
        with patch.object(m, 'run', return_value=json.dumps(snapshot)) as native:
            result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
        report = result.get('continuation_capability', {})
        self.assertEqual(report.get('outcome'), 'unavailable')
        self.assertIsNone(report['remaining'])
        self.assertEqual(native.call_count, 1)
        self.assertEqual(result['next_action'], 'recover_original_card')

    def test_terminal_run_behind_queued_card_requires_reconciliation(self):
        for card_status in ('todo', 'ready'):
            for run_status in ('blocked', 'failed', 'crashed', 'completed', 'cancelled', 'interrupted'):
                snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': card_status},
                            'runs': [{'id': 197, 'profile': 'fixture', 'status': run_status}]}
                with self.subTest(card=card_status, run=run_status), patch.object(m, 'run', return_value=json.dumps(snapshot)):
                    result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
                    self.assertEqual(result['next_action'], 'reconcile_run_state')

    def test_terminal_todo_escalates_without_changing_original_card(self):
        import contextlib, io
        snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'todo'},
                    'runs': [{'id': 197, 'profile': 'fixture', 'status': 'blocked',
                              'ended_at': 123, 'worker_pid': None}]}
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory, \
             patch.object(m, 'run', return_value=json.dumps(snapshot)), \
             patch.object(m, 'profile_home', return_value=Path(directory)), \
             patch('sys.argv', ['reconcile.py', '--profile', 'fixture', '--task-id', 't_fixture']):
            for index in range(2):
                output = io.StringIO()
                with contextlib.redirect_stdout(output): m.main()
                result = json.loads(output.getvalue())
                self.assertEqual(result['continuation']['unchanged_blocked_observations'], index + 1)
            self.assertTrue(result['attention_required'])
            self.assertEqual(result['continuation']['follow_up'], 'change_recovery_approach')
            self.assertIn('recovery', result['human_report'])
            self.assertEqual(result['task_id'], 't_fixture')
            self.assertEqual(result['status'], 'todo')

    def test_completed_card_supersedes_ready_creation_receipt(self):
        self.assertIsNotNone(m, 'Missing read-only reconciliation helper')
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home / 'autowork').mkdir()
            (home / 'autowork/goal-handoff.json').write_text(json.dumps({'task_id':'t_fixture','status':'ready'}))
            snapshot = {'task':{'id':'t_fixture','assignee':'fixture','status':'done'},'runs':[{'id':5,'profile':'fixture','outcome':'completed','summary':'five controls passed','metadata':{'report':'/evidence/report.md'}}],'events':[{'kind':'completed','created_at':123}]}
            with patch.object(m, 'run', return_value=json.dumps(snapshot)) as cli:
                result = m.reconcile(['hermes','-p','fixture'], home, 'fixture')
            self.assertEqual(result['status'], 'done')
            self.assertEqual(result['summary'], 'five controls passed')
            self.assertEqual(result['run_id'], 5)
            self.assertTrue(result['worker_observed'])
            self.assertEqual(result['run_ownership'], 'current_profile')
            self.assertEqual(result['metadata']['report'], '/evidence/report.md')
            self.assertEqual(cli.call_args.args[1:], ('kanban','--board','default','show','t_fixture','--json'))
            self.assertEqual(json.loads((home/'autowork/goal-handoff.json').read_text())['status'], 'ready')

    def test_reviewer_reassignment_keeps_original_coordinator_readback(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home / 'autowork').mkdir()
            (home / 'autowork/goal-handoff.json').write_text(json.dumps(
                {'task_id': 't_fixture', 'profile': 'fixture'}))
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'reviewer', 'status': 'done'},
                        'runs': [{'id': 7, 'profile': 'fixture', 'outcome': 'review_requested'},
                                 {'id': 8, 'profile': 'reviewer', 'outcome': 'completed'}]}
            receipt = home / 'autowork/goal-handoff.json'
            saved = json.loads(receipt.read_text())
            receipt.write_text(json.dumps({**saved, 'current_handoff':
                                           {'task_id': 't_other', 'profile': 'other'}}))
            with patch.object(m, 'run', return_value=json.dumps(snapshot)):
                result = m.reconcile([], home, 'fixture', 't_fixture')
            self.assertEqual(result['next_action'], 'verify_and_integrate')
            self.assertEqual(result['run_ownership'], 'other_profile')
            self.assertFalse(result['worker_observed'])
            self.assertFalse(result['delivery']['delivered'])

    def test_foreign_assignment_requires_saved_original_review_handoff(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home / 'autowork').mkdir()
            receipt = home / 'autowork/goal-handoff.json'
            original = {'task_id': 't_fixture', 'profile': 'fixture'}
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'reviewer', 'status': 'done'},
                        'runs': [{'id': 7, 'profile': 'fixture', 'outcome': 'review_requested'},
                                 {'id': 8, 'profile': 'reviewer', 'outcome': 'completed'}]}
            cases = [({'task_id': 't_other', 'profile': 'fixture'}, snapshot),
                     ({'task_id': 't_fixture', 'profile': 'other'}, snapshot),
                     ({'task_id': 't_other', 'profile': 'other',
                       'current_handoff': original}, snapshot),
                     (original, {**snapshot, 'runs': [snapshot['runs'][1]]}),
                     (original, {**snapshot, 'task': {**snapshot['task'], 'status': 'running'}}),
                     (original, {**snapshot, 'runs': [snapshot['runs'][0],
                                                    {**snapshot['runs'][1], 'profile': 'other'}]})]
            for saved, readback in cases:
                receipt.write_text(json.dumps(saved))
                with self.subTest(saved=saved, readback=readback), \
                     patch.object(m, 'run', return_value=json.dumps(readback)):
                    with self.assertRaisesRegex(RuntimeError, 'different profile'):
                        m.reconcile([], home, 'fixture', 't_fixture')

    def test_wrong_card_readback_is_rejected(self):
        snapshot = {'task': {'id': 't_other', 'assignee': 'fixture', 'status': 'done'},
                    'runs': [], 'events': []}
        with patch.object(m, 'run', return_value=json.dumps(snapshot)):
            with self.assertRaisesRegex(ValueError, 'task ID'):
                m.reconcile(['hermes', '-p', 'fixture'], Path('.'), 'fixture', 't_fixture')

    def test_unknown_snapshot_shapes_fail_with_schema_error(self):
        valid_task = {'id': 't_fixture', 'assignee': 'fixture', 'status': 'done'}
        cases = [[], None, 'text', {'task': []},
                 {'task': valid_task, 'runs': {}},
                 {'task': valid_task, 'runs': ['not a run']},
                 {'task': valid_task, 'events': {}},
                 {'task': valid_task, 'runs': [{'id': 'not numeric'}]},
                 {'task': {'id': 't_fixture', 'assignee': 'fixture'}}]
        for snapshot in cases:
            with self.subTest(snapshot=snapshot):
                with patch.object(m, 'run', return_value=json.dumps(snapshot)):
                    with self.assertRaisesRegex(ValueError, 'schema'):
                        m.reconcile(['hermes', '-p', 'fixture'], Path('.'), 'fixture', 't_fixture')

    def test_unknown_receipt_shapes_are_rejected_before_cli(self):
        for receipt in ([], None, 'text', {}, {'task_id': 12}, {'task_id': ''}):
            with self.subTest(receipt=receipt), tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
                home = Path(directory)
                (home / 'autowork').mkdir()
                path = home / 'autowork/goal-handoff.json'
                original = json.dumps(receipt)
                path.write_text(original)
                with patch.object(m, 'run') as cli:
                    with self.assertRaisesRegex(ValueError, 'receipt schema'):
                        m.reconcile(['hermes', '-p', 'fixture'], home, 'fixture')
                    cli.assert_not_called()
                self.assertEqual(path.read_text(), original)

    def test_explicit_nested_current_handoff_is_read_without_rewriting(self):
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home / 'autowork').mkdir()
            path = home / 'autowork/goal-handoff.json'
            original = json.dumps({'task_id': None, 'current_handoff': {'task_id': 't_fixture'}})
            path.write_text(original)
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'ready'},
                        'runs': [], 'events': []}
            with patch.object(m, 'run', return_value=json.dumps(snapshot)):
                result = m.reconcile(['hermes', '-p', 'fixture'], home, 'fixture')
            self.assertEqual(result['task_id'], 't_fixture')
            self.assertFalse(result['worker_observed'])
            self.assertEqual(path.read_text(), original)

    def test_wrong_card_run_is_rejected(self):
        snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'ready'},
                    'runs': [{'id': 9, 'task_id': 't_other', 'profile': 'fixture'}]}
        with patch.object(m, 'run', return_value=json.dumps(snapshot)):
            with self.assertRaisesRegex(ValueError, 'run task ID'):
                m.reconcile(['hermes', '-p', 'fixture'], Path('.'), 'fixture', 't_fixture')

    def test_prior_or_unknown_run_owner_is_not_current_worker_evidence(self):
        for owner, ownership in [('previous-owner', 'other_profile'), (None, 'unknown')]:
            with self.subTest(owner=owner):
                record = {'id': 9, 'outcome': 'completed'}
                if owner is not None:
                    record['profile'] = owner
                snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'ready'},
                            'runs': [record]}
                with patch.object(m, 'run', return_value=json.dumps(snapshot)):
                    result = m.reconcile(['hermes', '-p', 'fixture'], Path('.'), 'fixture', 't_fixture')
                self.assertFalse(result['worker_observed'])
                self.assertTrue(result['card_run_observed'])
                self.assertEqual(result['run_profile'], owner)
                self.assertEqual(result['run_ownership'], ownership)

    def test_foreign_or_unknown_run_delivery_evidence_is_not_current_profile_delivery(self):
        with EvidenceFixture() as f:
            evidence = f.integrated()
            for owner in ('previous-owner', None, 'fixture'):
                record = {'id': 9, 'metadata': {'delivery_evidence': evidence}}
                if owner is not None:
                    record['profile'] = owner
                snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'done'},
                            'runs': [record]}
                with self.subTest(owner=owner), patch.object(m, 'run', return_value=json.dumps(snapshot)):
                    result = m.reconcile(['hermes', '-p', 'fixture'], f.repo, 'fixture', 't_fixture', f.repo)
                    self.assertEqual(result['delivery']['delivered'], owner == 'fixture')
                    self.assertFalse(result['delivery']['milestone_complete'])
                    self.assertEqual(result['task_id'], 't_fixture')
                    self.assertEqual(result['run_id'], 9)
                    self.assertEqual(result['board_id'], 'default')
                    if owner != 'fixture':
                        self.assertEqual(result['delivery']['state'], 'unknown')
                        self.assertNotIn('merged', result['human_report'])

    def test_reviewed_card_remains_unknown_without_structured_delivery_evidence(self):
        snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'reviewed'},
                    'runs': [{'id': 7, 'profile': 'fixture', 'outcome': 'completed',
                              'summary': 'reviewed and merged'}]}
        with patch.object(m, 'run', return_value=json.dumps(snapshot)):
            result = m.reconcile(['hermes', '-p', 'fixture'], Path('.'), 'fixture', 't_fixture')
        self.assertEqual(result['delivery']['state'], 'unknown')
        self.assertFalse(result['delivery']['milestone_complete'])
        self.assertNotIn('merged', result['human_report'])
        self.assertEqual(result['board_id'], 'default')

    def test_phase_specific_next_action_does_not_claim_delivery(self):
        for status, action in [('running', 'observe_current_run'),
                               ('review', 'observe_current_run'),
                               ('ready', 'observe_queued_card'),
                               ('done', 'verify_and_integrate'),
                               ('changes_requested', 'recover_original_card'),
                               ('blocked', 'recover_original_card')]:
            snapshot = {'task': {'id':'t_fixture','assignee':'fixture','status':status},
                        'runs':[{'id':7,'profile':'fixture','outcome':'completed'}]}
            with self.subTest(status=status), patch.object(m, 'run', return_value=json.dumps(snapshot)):
                result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
            self.assertEqual(result['next_action'], action)
            self.assertFalse(result['delivery']['delivered'])

    def test_normal_ended_review_handoff_is_not_a_stale_running_card(self):
        snapshot = {'task':{'id':'t_fixture','assignee':'fixture','status':'review'},
                    'runs':[{'id':7,'profile':'fixture','status':'completed',
                             'outcome':'review_requested','ended_at':123}]}
        with patch.object(m, 'run', return_value=json.dumps(snapshot)):
            result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
        self.assertEqual(result['next_action'], 'observe_current_run')

    def test_terminal_run_on_running_card_requires_state_reconciliation(self):
        for status, outcome in [('blocked', 'blocked'), ('failed', 'failed'),
                                ('completed', 'completed')]:
            snapshot = {'task': {'id':'t_fixture','assignee':'fixture','status':'running'},
                        'runs':[{'id':7,'task_id':'t_fixture','profile':'fixture',
                                 'status':status,'outcome':outcome,'ended_at':123}]}
            with self.subTest(status=status), patch.object(m, 'run', return_value=json.dumps(snapshot)):
                result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
            self.assertEqual(result['next_action'], 'reconcile_run_state')
            self.assertEqual(result['run_status'], status)
            self.assertFalse(result['delivery']['delivered'])

    def test_ended_review_failure_needs_recovery_not_endless_observation(self):
        for outcome in ('failed', 'blocked', 'cancelled', 'completed'):
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'review'},
                        'runs': [{'id': 8, 'profile': 'fixture', 'status': 'completed',
                                  'outcome': outcome, 'ended_at': 123}]}
            with self.subTest(outcome=outcome), patch.object(m, 'run', return_value=json.dumps(snapshot)):
                result = m.reconcile([], Path('.'), 'fixture', 't_fixture')
            self.assertEqual(result['next_action'], 'reconcile_run_state')
            self.assertFalse(result['delivery']['delivered'])

    def test_report_projection_distinguishes_new_runs_and_outcomes(self):
        import contextlib, io
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home/'autowork').mkdir()
            (home/'autowork/goal-handoff.json').write_text(json.dumps({'task_id':'t_fixture'}))
            snapshots = [{'task':{'id':'t_fixture','assignee':'fixture','status':'review'},
                          'runs':[{'id':rid,'profile':'fixture','outcome':outcome}]}
                         for rid,outcome in [(7,'review_requested'),(8,'review_requested'),(8,'changes_requested'),(8,'completed')]]
            with patch.object(m,'run',side_effect=[json.dumps(s) for s in snapshots]), \
                 patch.object(m,'profile_home',return_value=home), \
                 patch('sys.argv',['reconcile.py','--profile','fixture']):
                for _ in snapshots:
                    buffer=io.StringIO()
                    with contextlib.redirect_stdout(buffer):m.main()
                    self.assertTrue(json.loads(buffer.getvalue())['report_changed'])

    def test_ended_run_change_is_visible_even_with_same_summary(self):
        import contextlib, io
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home/'autowork').mkdir()
            (home/'autowork/goal-handoff.json').write_text(json.dumps({'task_id':'t_fixture'}))
            snapshot = {'task':{'id':'t_fixture','assignee':'fixture','status':'running'},
                        'runs':[{'id':7,'profile':'fixture','status':'running','ended_at':None}]}
            outputs=[]
            with patch.object(m,'profile_home',return_value=home), \
                 patch('sys.argv',['reconcile.py','--profile','fixture','--compact']):
                for index in range(2):
                    if index:
                        snapshot['runs'][0].update(status='blocked', ended_at=123)
                    with patch.object(m,'run',return_value=json.dumps(snapshot)):
                        buffer=io.StringIO()
                        with contextlib.redirect_stdout(buffer):m.main()
                        outputs.append(json.loads(buffer.getvalue()))
            self.assertTrue(outputs[1]['report_changed'])
            self.assertIn('run_status', outputs[1]['changed_fields'])
            self.assertEqual(outputs[1]['continuation']['next_action'], 'reconcile_run_state')
            self.assertEqual(outputs[1]['continuation']['unchanged_blocked_observations'], 1)

    def test_compact_repeated_blocker_resets_on_changed_evidence(self):
        import contextlib, io
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory:
            home = Path(directory)
            (home/'autowork').mkdir()
            (home/'autowork/goal-handoff.json').write_text(json.dumps({'task_id':'t_fixture'}))
            snapshot = {'task':{'id':'t_fixture','assignee':'fixture','status':'blocked'},
                        'runs':[{'id':7,'profile':'fixture','error':'missing binding',
                                 'summary':'x'*3000, 'metadata':{'large':'y'*10000}}]}
            outputs=[]
            with patch.object(m,'profile_home',return_value=home), \
                 patch('sys.argv',['reconcile.py','--profile','fixture','--compact']):
                for index in range(4):
                    if index == 3:snapshot['runs'][0]['summary']='new recovery evidence'
                    if index == 2:snapshot['runs'][0]['error']='different failure'
                    with patch.object(m,'run',return_value=json.dumps(snapshot)):
                        buffer=io.StringIO()
                        with contextlib.redirect_stdout(buffer):m.main()
                        outputs.append(json.loads(buffer.getvalue()))
            self.assertEqual([o['continuation']['unchanged_blocked_observations'] for o in outputs],[1,2,1,1])
            self.assertEqual(outputs[1]['continuation']['follow_up'],'change_recovery_approach')
            self.assertNotIn('metadata',outputs[1])
            self.assertTrue(outputs[1]['summary_truncated'])
            self.assertLessEqual(len(outputs[1]['summary']),1200)
            self.assertIn('evidence_digest',outputs[2]['changed_fields'])

    def test_closeout_counter_resets_on_new_evidence_and_stops_when_delivered(self):
        import contextlib, io
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory, EvidenceFixture() as f:
            home = Path(directory)
            (home/'autowork').mkdir()
            (home/'autowork/goal-handoff.json').write_text(json.dumps({'task_id': 't_fixture'}))
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'done'},
                        'runs': [{'id': 7, 'profile': 'fixture', 'metadata': {}}]}
            outputs = []
            with patch.object(m, 'profile_home', return_value=home), \
                 patch('sys.argv', ['reconcile.py', '--profile', 'fixture', '--repo', str(f.repo)]):
                for index in range(5):
                    if index == 2:
                        snapshot['runs'][0]['metadata'] = {'new_evidence': 'candidate changed'}
                    if index == 3:
                        snapshot['runs'][0]['metadata'] = {'delivery_evidence': f.integrated()}
                    with patch.object(m, 'run', return_value=json.dumps(snapshot)):
                        buffer = io.StringIO()
                        with contextlib.redirect_stdout(buffer):
                            m.main()
                        outputs.append(json.loads(buffer.getvalue()))
            self.assertEqual([o['continuation']['unchanged_closeout_observations'] for o in outputs],
                             [1, 2, 1, 0, 0])
            self.assertEqual(outputs[3]['next_action'], 'reconcile_task_and_select')
            self.assertFalse(outputs[4]['attention_required'])
            self.assertIsNone(outputs[4]['human_report'])

    def test_pending_closeout_stays_visible_and_escalates_without_dispatch(self):
        import contextlib
        import io
        with tempfile.TemporaryDirectory(dir=SCRATCH) as directory, EvidenceFixture() as f:
            home = Path(directory)
            (home/'autowork').mkdir()
            receipt = home/'autowork/goal-handoff.json'
            receipt.write_text(json.dumps({'task_id': 't_fixture'}))
            original = receipt.read_text()
            snapshot = {'task': {'id': 't_fixture', 'assignee': 'fixture', 'status': 'done'},
                        'runs': [{'id': 7, 'profile': 'fixture', 'metadata': {
                            'delivery_evidence': {'candidate': f.identity,
                                                  'implementation': {'artifacts': ['a.py']}}}}]}
            outputs = []
            with patch.object(m, 'run', return_value=json.dumps(snapshot)) as cli, \
                 patch.object(m, 'profile_home', return_value=home), \
                 patch('sys.argv', ['reconcile.py', '--profile', 'fixture', '--repo', str(f.repo)]):
                for _ in range(2):
                    buffer = io.StringIO()
                    with contextlib.redirect_stdout(buffer):
                        m.main()
                    outputs.append(json.loads(buffer.getvalue()))
                self.assertEqual(cli.call_count, 2, 'Reporting cache must never skip live readback')
            self.assertEqual(outputs[0]['delivery']['state'], 'implemented')
            self.assertIsNotNone(outputs[0]['human_report'])
            self.assertIsNotNone(outputs[1]['human_report'])
            self.assertFalse(outputs[1]['report_changed'])
            self.assertTrue(outputs[1]['attention_required'])
            self.assertEqual(outputs[1]['continuation']['unchanged_closeout_observations'], 2)
            self.assertEqual(outputs[1]['continuation']['follow_up'], 'resolve_closeout_gap')
            self.assertTrue(outputs[1]['selection_required'])
            self.assertEqual(outputs[1]['continuation']['next_action'], 'verify_and_integrate')
            self.assertEqual(outputs[1]['changed_fields'], [])
            self.assertEqual(outputs[1]['continuation']['task_id'], 't_fixture')
            self.assertTrue(outputs[1]['continuation']['fresh_readback_required'])
            self.assertNotIn('discovery_required', outputs[1], 'Reconcile cannot decide backlog eligibility')
            self.assertEqual(outputs[0]['task_id'], outputs[1]['task_id'])
            self.assertEqual(outputs[0]['board_id'], outputs[1]['board_id'])
            self.assertEqual(receipt.read_text(), original)

if __name__ == '__main__':
    unittest.main()
