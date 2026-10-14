"""Real Git owner-cycle fixtures; no live profiles, workers or model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('owner_cycle.py')


class OwnerCycleTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.state = self.root / 'state'

    def run_cycle(self, *extra, require_owner=True):
        r = subprocess.run([sys.executable,str(SCRIPT),str(self.repo),'--plan','SPEC.md#slice',
                            '--tasks','T1','--state-dir',str(self.state),
                            *(['--require-owner'] if require_owner else []),*extra],capture_output=True,text=True)
        self.assertTrue(r.stdout, r.stderr)
        return r, json.loads((self.state/'unblock-latest.json').read_text())

    def test_default_continues_locally_without_owner_route_or_request(self):
        _, receipt = self.run_cycle('--apply', require_owner=False)
        self.assertEqual(receipt['outcome'], 'ACTION_REQUIRED')
        self.assertEqual(receipt['action'], 'repair_local_inputs')
        self.assertNotIn('integration_request', receipt)
        self.assertNotIn('routing_gap', receipt)
        self.assertFalse((self.state / 'requests').exists())
        self.assertEqual(receipt['coordination_mode'], 'autonomous')

    def test_repository_scope_missing_ledger_saves_repair_receipt(self):
        result, receipt = self.run_cycle('--scope', 'repository', '--apply', require_owner=False)
        self.assertEqual(result.returncode, 1)
        self.assertEqual(receipt['outcome'], 'ACTION_REQUIRED')
        self.assertEqual(receipt['recovery']['gate'], 'ledger')
        self.assertIn('goals.json', str(receipt['work_search']))
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertFalse((self.repo / 'goals.json').exists())

    def test_default_open_task_does_not_wait_for_recorded_owner(self):
        self.ready_backlog()
        registry = self.repo / 'docs/coordination/worktree-registry.jsonl'
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({'task':'T1','owner':'old-writer',
            'worktree':'/fixture/writer','status':'ACTIVE'}) + '\n')
        _, receipt = self.run_cycle('--apply', '--integration-owner', 'old-writer', require_owner=False)
        self.assertTrue(receipt['backlog_ready'])
        self.assertEqual(receipt['action'], 'prepare_execution_handoff')
        self.assertNotIn('integration_request', receipt)
        self.assertNotIn('routing_gap', receipt)
        self.assertFalse(receipt['dispatch_attempted'])

    def test_missing_ledger_requests_integration_instead_of_validate_loop(self):
        r, receipt = self.run_cycle('--integration-owner','parent')
        self.assertEqual(r.returncode,1)
        self.assertEqual(receipt['outcome'],'BLOCKED')
        self.assertEqual(receipt['recovery']['gate'],'ledger')
        self.assertEqual(receipt['planning']['action'],'integrate_existing_inputs')
        request = json.loads(Path(receipt['integration_request']).read_text())
        self.assertEqual(request['owner'],'parent')
        self.assertEqual(request['status'],'pending')
        self.assertEqual(request['task_ids'],['T1'])
        self.assertFalse((self.repo/'goals.json').exists())
        self.assertIn('integration',receipt['next_action'])
        self.assertEqual(receipt['completed_tasks'],[])

    def test_unchanged_blocker_reuses_request_and_changes_action(self):
        _, first = self.run_cycle('--integration-owner','parent')
        _, second = self.run_cycle('--integration-owner','parent')
        self.assertEqual(first['integration_request'],second['integration_request'])
        self.assertEqual(second['unchanged_runs'],2)
        self.assertEqual(second['action'],'owner_followup_required')
        self.assertEqual(len(list((self.state/'requests').glob('*.json'))),1)
        self.assertEqual(len(list((self.state/'history').glob('*.json'))),2)
        self.assertNotIn('COMPLETED', (self.state/'report-latest.txt').read_text())

    def test_repository_scope_missing_route_does_not_end_independent_selection(self):
        self.ready_backlog()
        p=self.repo/'goals.json';data=json.loads(p.read_text())
        data['tasks'][0]['section']='Needs decision';p.write_text(json.dumps(data))
        todo=self.repo/'TODO.md';todo.write_text(todo.read_text().replace('## Now','## Needs decision'))
        before={p:p.read_bytes(),todo:todo.read_bytes()}
        for _ in range(2):
            result,receipt=self.run_cycle('--scope','repository','--apply','--integration-owner','parent')
        self.assertEqual(result.returncode,1)
        self.assertEqual(receipt['action'],'discover_repository_work')
        self.assertEqual(receipt['outcome'],'ACTION_REQUIRED')
        self.assertIn('routing_gap',receipt)
        self.assertEqual(receipt['completed_tasks'],[])
        self.assertFalse(receipt['dispatch_attempted'])
        for path,contents in before.items():self.assertEqual(path.read_bytes(),contents)

    def test_repository_cycle_searches_beyond_registered_writer(self):
        self.ready_backlog()
        registry = self.repo / 'docs/coordination/worktree-registry.jsonl'
        registry.parent.mkdir(parents=True)
        registry.write_text(json.dumps({'task':'T1','owner':'writer',
            'worktree':'/fixture/writer','status':'ACTIVE'}) + '\n')
        _, receipt = self.run_cycle('--scope', 'repository')
        self.assertFalse(receipt['backlog_ready'])
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertEqual(receipt['work_search']['state'], 'no_unclaimed_candidate')
        self.assertEqual(receipt['work_search']['held_claims'][0]['task'], 'T1')
        self.assertEqual(receipt['action'], 'discover_repository_work')
        ledger = self.repo / 'goals.json'; data = json.loads(ledger.read_text())
        data['goals'][0]['tasks'].append('T2')
        data['tasks'].append({'id':'T2','title':'Independent','goal':'G1','status':'open','section':'Now'})
        ledger.write_text(json.dumps(data))
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text() + '\n- [ ] T2: Independent\n  Goal: G1\n'
            '  Scope: independent\n  Acceptance: test passes\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Accepted](SPEC.md#slice)\n')
        _, receipt = self.run_cycle('--scope', 'repository')
        self.assertEqual(receipt['action'], 'prepare_independent_candidate')
        self.assertIn('T2', receipt['next_action'])
        self.assertFalse(receipt['dispatch_attempted'])

    def test_parent_session_is_bound_in_request_and_delivery(self):
        self.state.mkdir();owner=self.root/'parent';owner.mkdir()
        (self.state/'owner-route.json').write_text(json.dumps({'consumer':str(self.repo),
            'owner':'parent','state_dir':str(owner),'target_session':'parent-session'}))
        _,first=self.run_cycle('--apply','--integration-owner','parent')
        request=json.loads(Path(first['integration_request']).read_text())
        inbox=json.loads(Path(request['delivery']['inbox_path']).read_text())
        self.assertEqual(inbox['target_session'],'parent-session')
        self.assertEqual(request['delivery']['session_wakeup'],'not_attempted')
        reply=Path(request['delivery']['reply_path']);reply.parent.mkdir(exist_ok=True)
        reply.write_text(json.dumps({'request_id':request['request_id'],'owner':'parent',
             'status':'blocked','evidence':'cron observation','session_id':'cron-session'}))
        _,second=self.run_cycle('--apply','--integration-owner','parent')
        self.assertEqual(second['request_status'],'pending')
        self.assertIn('designated target session',second['routing_gap'])
        self.assertEqual(second['integration_request'],first['integration_request'])

    def test_ledger_input_change_resets_repetition(self):
        self.run_cycle()
        (self.repo/'TODO.md').write_text('# Changed owner inputs\n')
        _, receipt = self.run_cycle()
        self.assertEqual(receipt['unchanged_runs'],1)

    def ready_backlog(self):
        (self.repo/'SPEC.md').write_text('# Slice\nStatus: Accepted\n')
        (self.repo/'goals.json').write_text(json.dumps({'version':1,'primary_milestone':'G1',
          'goals':[{'id':'G1','title':'Slice','source':'SPEC.md#slice','status':'unmet','priority':1,'tasks':['T1']}],
          'tasks':[{'id':'T1','title':'Implement fixture','goal':'G1','status':'open','section':'Now'}]}))
        (self.repo/'TODO.md').write_text('# TODO\n\n## Now\n\n- [ ] T1: Implement fixture\n  Goal: G1\n  Scope: fixture\n  Acceptance: test passes\n  Dependencies: None\n  Ownership: fixture\n  Sources: [Accepted](SPEC.md#slice)\n')
    def test_ready_slice_without_handoff_requires_preparation_not_dispatch(self):
        self.ready_backlog()
        r, receipt = self.run_cycle()
        self.assertEqual(r.returncode,1,receipt)
        self.assertEqual(receipt['outcome'],'PREPARATION_REQUIRED')
        self.assertEqual(receipt['planning']['action'],'plan')
        self.assertEqual(receipt['action'],'plan_execution_recovery')
        self.assertIn('Run bounded planning now',receipt['next_action'])
        self.assertEqual(receipt['selected_task']['id'],'T1')
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertIn('Implement fixture', (self.state/'report-latest.txt').read_text())

    def test_saved_no_delta_does_not_restart_planning_or_dispatch(self):
        import backlog_plan
        self.ready_backlog()
        _, first = self.run_cycle(require_owner=False)
        path = backlog_plan.record(first, self.state, 'fixture://accounting-failure', 'no_supported_delta')
        before = Path(path).read_bytes()
        _, second = self.run_cycle(require_owner=False)
        self.assertEqual(second['action'], 'resolve_recorded_blocker')
        self.assertEqual(second['outcome'], 'ACTION_REQUIRED')
        self.assertFalse(second['dispatch_attempted'])
        self.assertEqual(second['planning']['evidence'], 'fixture://accounting-failure')
        self.assertIn('preserving consumed budget', second['next_action'])
        self.assertEqual(Path(path).read_bytes(), before)

    def test_ready_backlog_missing_handoff_routes_execution_inputs_to_owner(self):
        self.ready_backlog()
        owner=self.root/'owner';owner.mkdir();self.state.mkdir()
        (self.state/'owner-route.json').write_text(json.dumps({'consumer':str(self.repo),
            'owner':'parent','state_dir':str(owner)}))
        r,first=self.run_cycle('--apply','--integration-owner','parent')
        self.assertEqual(r.returncode,1)
        self.assertEqual(first['outcome'],'PREPARATION_REQUIRED')
        self.assertTrue(first['backlog_ready'])
        self.assertTrue(first['blocker'])
        self.assertEqual(first['planning']['action'],'plan')
        request=json.loads(Path(first['integration_request']).read_text())
        self.assertEqual(request['gate'],'handoff_preparation')
        self.assertEqual(request['delivery']['state'],'delivered')
        _,second=self.run_cycle('--apply','--integration-owner','parent')
        self.assertEqual(second['integration_request'],first['integration_request'])
        self.assertEqual(second['unchanged_runs'],2)
        self.assertEqual(second['resolved_requests'],[])
        self.assertFalse(second['dispatch_attempted'])

    def test_supported_repair_retries_and_records_progress_without_task_completion(self):
        import retry_selection
        self.ready_backlog()
        (self.repo/'README.md').write_text('Existing owner doc')
        p=self.repo/'TODO.md'; p.write_text(p.read_text().replace('[Accepted](SPEC.md#slice)','[Readme](README.md)'))
        authority={'version':1,'workspace':str(self.repo),'plan':'SPEC.md#slice','task_ids':['T1'],
                   'expected_revision':retry_selection.goals.revision(self.repo),'source_commit':None,
                   'owner':'fixture','evidence_ref':'fixture://accepted-owner','no_overlapping_writer':True}
        auth=self.root/'authority.json';auth.write_text(json.dumps(authority))
        r,receipt=self.run_cycle('--apply','--authority',str(auth))
        self.assertEqual(r.returncode,1,receipt)
        self.assertEqual(receipt['outcome'],'PREPARATION_REQUIRED')
        self.assertEqual(receipt['selected_task']['id'],'T1')
        self.assertEqual([s['stage'] for s in receipt['recovery']['stages']],['diagnose','repair','retry_selection'])
        self.assertEqual(receipt['completed_tasks'],[])

    def test_malformed_recovery_authority_preserves_refusal_receipt(self):
        self.ready_backlog()
        (self.repo/'README.md').write_text('Existing owner doc')
        p=self.repo/'TODO.md'
        p.write_text(p.read_text().replace('[Accepted](SPEC.md#slice)','[Readme](README.md)'))
        before=p.read_bytes()
        auth=self.root/'authority.json'; auth.write_text('[]')
        result,receipt=self.run_cycle('--apply','--authority',str(auth))
        self.assertEqual(result.returncode,1)
        self.assertEqual(receipt['recovery']['gate'],'refused')
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertEqual(p.read_bytes(),before)

    def test_owned_task_stays_held_and_no_handoff_is_attempted(self):
        self.ready_backlog()
        p=self.repo/'goals.json'; data=json.loads(p.read_text()); data['tasks'][0]['status']='in_progress';p.write_text(json.dumps(data))
        before=p.read_bytes()
        _,receipt=self.run_cycle('--apply','--handoff-request',str(self.root/'nonexistent.json'))
        self.assertEqual(receipt['recovery']['gate'],'ownership')
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertEqual(p.read_bytes(),before)

    def test_handoff_routes_only_explicit_same_task_request(self):
        import owner_cycle
        from types import SimpleNamespace
        from unittest.mock import patch
        request=self.root/'handoff.json'
        request.write_text(json.dumps({'consumer':str(self.repo),'task_id':'T1',
                                      'options':{'profile':'sample','title':'Fixture','contract-file':'/private/contract'}}))
        args=SimpleNamespace(consumer=str(self.repo),handoff_request=str(request))
        with patch.object(owner_cycle.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='{"outcome":"handed_off","task_id":"card"}')) as run:
            result=owner_cycle.handoff(args,{'id':'T1'})
        self.assertIn('start_goal.py',run.call_args.args[0][1])
        self.assertIn('--goal-task',run.call_args.args[0])
        self.assertEqual(result['result']['outcome'],'handed_off')
        with self.assertRaises(ValueError): owner_cycle.handoff(args,{'id':'OTHER'})

    def test_handoff_forwards_fallback_evidence_to_native_admission(self):
        import owner_cycle
        from types import SimpleNamespace
        from unittest.mock import patch
        request = self.root / 'handoff.json'
        fallback = str(self.root / 'fallback.json')
        request.write_text(json.dumps({'consumer': str(self.repo), 'task_id': 'T1',
                                      'options': {'fallback-file': fallback}}))
        args = SimpleNamespace(consumer=str(self.repo), handoff_request=str(request))
        # Admission owns validation: its refusal must survive the bridge unchanged.
        with patch.object(owner_cycle.subprocess, 'run', return_value=SimpleNamespace(
                returncode=1, stdout='{"outcome":"blocked"}')) as run:
            result = owner_cycle.handoff(args, {'id': 'T1'})
        self.assertEqual(run.call_args.args[0][-2:], ['--fallback-file', fallback])
        self.assertEqual(result['exit_code'], 1)
        self.assertEqual(result['result']['outcome'], 'blocked')

    def test_supplied_acknowledgement_is_distinct_from_request_creation(self):
        self.run_cycle('--integration-owner','parent')
        _,receipt=self.run_cycle('--integration-owner','parent','--apply','--acknowledge','--owner-evidence','fixture://actual-reply')
        request=json.loads(Path(receipt['integration_request']).read_text())
        self.assertEqual(request['status'],'acknowledged')
        self.assertEqual(request['acknowledgement']['evidence'],'fixture://actual-reply')
        self.assertFalse((self.repo/'goals.json').exists())

    def test_ready_task_prepares_directly_without_a_research_pass(self):
        self.ready_backlog()
        _, receipt = self.run_cycle('--apply', require_owner=False)
        self.assertTrue(receipt['backlog_ready'])
        self.assertEqual(receipt['action'], 'prepare_execution_handoff')
        self.assertEqual(receipt['planning']['action'], 'prepare_execution_handoff')
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertFalse((self.state / 'planning').exists())

    def test_notification_failure_preserves_successful_native_handoff(self):
        import owner_cycle
        from unittest.mock import patch
        self.ready_backlog()
        native = {'outcome': 'notification_blocked', 'task_id': 't_fixture',
                  'goal_mode': True, 'status': 'ready', 'notification_error': 'transport unavailable'}
        with patch.object(owner_cycle, 'handoff', return_value={'exit_code': 0, 'result': native}) as handoff:
            code = owner_cycle.main([str(self.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1',
                '--state-dir', str(self.state), '--apply', '--handoff-request', '/private/request'])
        receipt = json.loads((self.state/'unblock-latest.json').read_text())
        self.assertEqual(code, 0)
        self.assertEqual(receipt['outcome'], 'QUEUED')
        self.assertEqual(receipt['notification_warning'], 'transport unavailable')
        self.assertEqual(receipt['handoff']['result']['task_id'], 't_fixture')
        self.assertIn('original', receipt['next_action'])
        handoff.assert_called_once()

    def test_notification_error_without_recorded_card_is_not_success(self):
        import owner_cycle
        from unittest.mock import patch
        self.ready_backlog()
        for native in ({'outcome': 'notification_blocked'},
                       {'outcome': 'notification_blocked', 'task_id': 't_fixture', 'goal_mode': False}):
            with self.subTest(native=native), patch.object(owner_cycle, 'handoff',
                    return_value={'exit_code': 0, 'result': native}):
                code = owner_cycle.main([str(self.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1',
                    '--state-dir', str(self.state), '--apply', '--handoff-request', '/private/request'])
            receipt = json.loads((self.state/'unblock-latest.json').read_text())
            self.assertEqual(code, 1)
            self.assertEqual(receipt['outcome'], 'BLOCKED')
            self.assertNotIn('notification_warning', receipt)

    def test_failed_or_uncertain_handoff_persists_reconciliation_receipt(self):
        import owner_cycle
        from unittest.mock import patch
        self.ready_backlog()
        for value in ({'exit_code':1,'result':{'outcome':'partial'}},
                      subprocess.TimeoutExpired('native',120)):
            with self.subTest(value=type(value).__name__):
                kwargs={'side_effect':value} if isinstance(value,Exception) else {'return_value':value}
                with patch.object(owner_cycle,'handoff',**kwargs):
                    code=owner_cycle.main([str(self.repo),'--plan','SPEC.md#slice','--tasks','T1',
                        '--state-dir',str(self.state),'--apply','--handoff-request','/private/request'])
                receipt=json.loads((self.state/'unblock-latest.json').read_text())
                self.assertEqual(code,1)
                self.assertEqual(receipt['outcome'],'FAILED')
                self.assertIn('Reconcile native',receipt['next_action'])

    def test_bad_acknowledgement_refuses_before_recovery(self):
        import owner_cycle
        from types import SimpleNamespace
        from unittest.mock import patch
        with patch.object(owner_cycle.owner_unblock,'run') as recovery:
            with self.assertRaises(ValueError):
                owner_cycle.cycle(SimpleNamespace(acknowledge=True,apply=False))
        recovery.assert_not_called()

    def test_new_evidence_is_retained_without_duplicate_request(self):
        _,first=self.run_cycle('--integration-owner','parent','--proposal','/private/draft')
        _,second=self.run_cycle('--integration-owner','parent','--owner-evidence','fixture://owner-update')
        self.assertEqual(first['integration_request'],second['integration_request'])
        request=json.loads(Path(second['integration_request']).read_text())
        self.assertEqual(len(request['evidence_updates']),2)

    def test_saved_authority_is_reused_only_with_apply(self):
        import retry_selection
        self.ready_backlog()
        p=self.repo/'TODO.md';p.write_text(p.read_text().replace('[Accepted](SPEC.md#slice)','decision'))
        self.state.mkdir()
        authority={'version':1,'workspace':str(self.repo),'plan':'SPEC.md#slice','task_ids':['T1'],
                   'expected_revision':retry_selection.goals.revision(self.repo),'source_commit':None,
                   'owner':'fixture','evidence_ref':'fixture://existing-owner','no_overlapping_writer':True}
        (self.state/'recovery-authority.json').write_text(json.dumps(authority))
        _,before=self.run_cycle()
        self.assertEqual(before['recovery']['gate'],'accepted_body_repair')
        _,after=self.run_cycle('--apply')
        self.assertEqual(after['outcome'],'PREPARATION_REQUIRED')
        self.assertIn('Accepted plan',p.read_text())

    def test_ready_backlog_does_not_close_request_before_handoff_preparation(self):
        owner=self.root/'owner';owner.mkdir();self.state.mkdir()
        (self.state/'owner-route.json').write_text(json.dumps({'consumer':str(self.repo),
            'owner':'parent','state_dir':str(owner)}))
        _,first=self.run_cycle('--apply','--integration-owner','parent')
        request=json.loads(Path(first['integration_request']).read_text())
        self.assertEqual(request['delivery']['state'],'delivered')
        reply=Path(request['delivery']['reply_path']);reply.parent.mkdir()
        reply.write_text(json.dumps({'request_id':request['request_id'],'owner':'parent',
                                    'status':'resolved','evidence':'fixture://integrated'}))
        _,still=self.run_cycle('--apply','--integration-owner','parent')
        self.assertEqual(still['outcome'],'BLOCKED')
        self.assertEqual(json.loads(Path(first['integration_request']).read_text())['status'],'resolution_reported')
        self.ready_backlog()
        _,ready=self.run_cycle('--apply','--integration-owner','parent')
        self.assertEqual(ready['outcome'],'PREPARATION_REQUIRED')
        self.assertEqual(json.loads(Path(first['integration_request']).read_text())['status'],'resolution_reported')
        self.assertIn('resolved_requests',ready)

    def test_blocked_live_task_can_offer_three_offline_tasks_without_releasing_it(self):
        self.ready_backlog()
        ledger=self.repo/'goals.json'; data=json.loads(ledger.read_text())
        data['tasks'][0]['section']='Needs decision'
        todo=self.repo/'TODO.md'
        original=todo.read_text().replace('## Now','## Needs decision')
        extra='\n## Now\n'
        for task_id in ('T2','T3','T4'):
            data['goals'][0]['tasks'].append(task_id)
            data['tasks'].append({'id':task_id,'title':'Offline fixture '+task_id,
                                 'goal':'G1','status':'open','section':'Now'})
            extra += ('\n- [ ] '+task_id+': Offline fixture\n  Goal: G1\n  Scope: fixture\n'
                      '  Acceptance: test passes\n  Dependencies: None\n  Sources: [Accepted](SPEC.md#slice)\n')
        ledger.write_text(json.dumps(data));todo.write_text(original+extra)
        before=ledger.read_bytes()
        _,held=self.run_cycle()
        self.assertEqual(held['outcome'],'BLOCKED')
        _,ready=self.run_cycle('--allow-ready-fallback')
        self.assertEqual(ready['outcome'],'PREPARATION_REQUIRED')
        self.assertEqual(ready['selected_task']['id'],'T2')
        request=json.loads(Path(ready['integration_request']).read_text())
        self.assertEqual(request['task_ids'],['T2'])
        self.assertEqual([t['id'] for t in ready['ready_queue']],['T2','T3','T4'])
        self.assertEqual(ready['held_task_ids'],['T1'])
        self.assertEqual(ledger.read_bytes(),before)
        self.assertFalse(ready['dispatch_attempted'])
        self.assertIn('T1', (self.state/'report-latest.txt').read_text())
        _, autonomous = self.run_cycle('--allow-ready-fallback', require_owner=False)
        self.assertEqual(autonomous['action'], 'prepare_execution_handoff')
        self.assertEqual(autonomous['selected_task']['id'], 'T2')
        self.assertEqual(autonomous['held_task_ids'], ['T1'])
        self.assertFalse(autonomous['dispatch_attempted'])
        self.assertEqual(ledger.read_bytes(), before)

    def test_saved_native_handoff_is_used_for_ready_task(self):
        import owner_cycle
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        self.ready_backlog()
        path=self.state/'handoff-requests'/'T1.json';path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'consumer':str(self.repo),'task_id':'T1','options':{}}))
        with patch.object(owner_cycle,'handoff',return_value={'exit_code':0,'result':{'outcome':'handed_off'}}) as handoff:
            with redirect_stdout(io.StringIO()):
                code=owner_cycle.main([str(self.repo),'--plan','SPEC.md#slice','--tasks','T1',
                    '--state-dir',str(self.state),'--apply'])
        self.assertEqual(code,0)
        self.assertEqual(handoff.call_args.args[0].handoff_request,str(path))
        receipt=json.loads((self.state/'unblock-latest.json').read_text())
        self.assertEqual(receipt['outcome'],'QUEUED')
        self.assertEqual(receipt['completed_tasks'],[])

    def test_native_json_shapes_and_canonical_handoff_binding(self):
        import owner_cycle
        from types import SimpleNamespace
        from unittest.mock import patch
        request=self.root/'handoff.json'
        args=SimpleNamespace(consumer='/old/linked/path',handoff_request=str(request))
        request.write_text('[]')
        with self.assertRaises(ValueError): owner_cycle.handoff(args,{'id':'T1'})
        request.write_text(json.dumps({'consumer':str(self.repo),'task_id':'T1','options':{}}))
        with patch.object(owner_cycle.subprocess,'run',return_value=SimpleNamespace(returncode=0,stdout='[]',stderr='')):
            result=owner_cycle.handoff(args,{'id':'T1'},str(self.repo))
        self.assertEqual(result['result']['outcome'],'unverified')


class ComposedReadyTests(unittest.TestCase):
    """Only these additional tests opt into native composition; dispatch is mocked."""
    def test_local_policy_reaches_read_only_original_card_reconciliation(self):
        import owner_cycle
        from test_delivery_state import EvidenceFixture
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        with EvidenceFixture() as f:
            policy = f.local_integration()
            policy.update(task_id='original', run_id=9, implementer='fixture')
            f.evidence['integration']['provenance']['review']['implementer'] = 'fixture'
            policy_path = self.root / 'policy.json'
            policy_path.write_text(json.dumps(policy))
            snapshot = {'task': {'id': 'original', 'assignee': 'fixture', 'status': 'done'},
                        'runs': [{'id': 9, 'profile': 'fixture', 'status': 'completed',
                                  'metadata': {'delivery_evidence': f.evidence}}]}
            (self.root / 'autowork').mkdir()
            saved = self.root / 'autowork/goal-handoff.json'
            saved.write_text(json.dumps({'task_id': 'original'}))
            original = saved.read_bytes()
            with patch.object(owner_cycle.reconcile, 'profile_home', return_value=self.root), \
                    patch.object(owner_cycle.reconcile, 'run', return_value=json.dumps(snapshot)), \
                    patch.object(owner_cycle, 'handoff') as dispatch, \
                    patch.dict(owner_cycle.os.environ,
                        {k: v for k, v in owner_cycle.os.environ.items() if k != 'HERMES_KANBAN_TASK'},
                        clear=True), redirect_stdout(io.StringIO()):
                for options, delivered in [([], False), (['--local-policy', str(policy_path)], True)]:
                    owner_cycle.main([str(f.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1',
                        '--state-dir', str(self.state), '--profile', 'fixture', '--apply', *options])
                    receipt = json.loads((self.state / 'unblock-latest.json').read_text())
                    prior = receipt['reconciliation']
                    self.assertEqual(prior['delivery']['delivered'], delivered)
                    self.assertEqual(prior['task_id'], 'original')
                    self.assertEqual(prior['run_id'], 9)
                    self.assertEqual(receipt['completed_tasks'], [])
                    self.assertIsNone(prior['continuation_capability']['remaining'])
                dispatch.assert_not_called()
            self.assertEqual(saved.read_bytes(), original)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.state = self.root / 'state'

    def ready_backlog(self):
        (self.repo / 'SPEC.md').write_text('# Slice\nStatus: Accepted\n')
        (self.repo / 'goals.json').write_text(json.dumps({'version': 1,
            'goals': [{'id': 'G1', 'title': 'Slice', 'source': 'SPEC.md#slice', 'status': 'unmet', 'priority': 1, 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'title': 'Implement fixture', 'goal': 'G1', 'status': 'open', 'section': 'Now'}]}))
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Now\n\n- [ ] T1: Implement fixture\n'
            '  Goal: G1\n  Scope: fixture\n  Acceptance: test passes\n  Dependencies: None\n'
            '  Ownership: fixture\n  Sources: [Accepted](SPEC.md#slice)\n')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text() + '  Checks: python3 -m unittest\n')
        (self.repo / 'code.py').write_text('pass\n')
        import retry_selection
        retry_selection.goals.dump(self.repo, retry_selection.goals.load(self.repo))
        for argv in (['add', '.'], ['-c', 'user.name=Fixture', '-c', 'user.email=fixture@local', 'commit', '-qm', 'base']):
            subprocess.run(['git', '-C', str(self.repo), *argv], check=True, capture_output=True)

    def composed(self, native=None, prior=None, *extra):
        import owner_cycle
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        with patch.object(owner_cycle.reconcile, 'profile_home', return_value=self.root), \
                patch.object(owner_cycle.reconcile, 'reconcile', return_value=prior or {'outcome': 'no_handoff'}), \
                patch.object(owner_cycle, 'handoff', **({'side_effect': native} if isinstance(native, Exception) else
                    {'return_value': native or {'exit_code': 0, 'result': {'outcome': 'handed_off', 'task_id': 'original', 'goal_mode': True}}})) as dispatch, \
                patch.dict(owner_cycle.os.environ, {}, clear=True), \
                patch.object(owner_cycle.backlog_plan, 'decide', side_effect=AssertionError('no planning on ready path')), \
                redirect_stdout(io.StringIO()):
            code = owner_cycle.main([str(self.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1',
                '--state-dir', str(self.state), '--profile', 'fixture', '--apply', '--source-path', 'code.py', *extra])
        return code, json.loads((self.state / 'unblock-latest.json').read_text()), dispatch

    def test_complete_ready_composes_once_and_persists_bookkeeping(self):
        import start_goal
        self.ready_backlog()
        code, receipt, dispatch = self.composed()
        self.assertEqual(code, 0, receipt)
        dispatch.assert_called_once()
        preparation = receipt['preparation']
        self.assertEqual(preparation['budget'], 100)
        self.assertEqual(preparation['max_retries'], 1)
        self.assertEqual(preparation['usage'], 'unknown')
        fields = start_goal.validate_contract(Path(preparation['contract']).read_text())
        self.assertEqual(set(start_goal.CONTRACT_FIELDS) - set(fields), set())
        self.assertIn('fixture', fields['Source'])
        self.assertIn('python3 -m unittest', fields['Verification'])
        self.assertIn('immutable base', fields['Source'])
        self.assertEqual(json.loads((self.repo / 'goals.json').read_text())['tasks'][0]['status'], 'in_progress')
        self.assertEqual(receipt['completed_tasks'], [])
        self.assertFalse((self.state / 'planning').exists())
        self.assertTrue(preparation['dispatch_attempted'])

    def test_incomplete_ready_repairs_only_checks_without_planning(self):
        self.ready_backlog()
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('  Checks: python3 -m unittest\n', ''))
        code, receipt, dispatch = self.composed()
        self.assertEqual(code, 1)
        dispatch.assert_not_called()
        self.assertIn('missing task Checks', receipt['next_action'])
        self.assertFalse((self.state / 'ready-preflights').exists())

    def test_attempted_dispatch_never_recreates_or_resets_budget(self):
        self.ready_backlog()
        for native in (subprocess.TimeoutExpired('native', 120),
                       {'exit_code': 0, 'result': {'outcome': 'already_owned', 'task_id': 'original'}},
                       {'exit_code': 1, 'result': {'outcome': 'unverified'}}):
            with self.subTest(native=str(native)):
                import shutil
                if self.state.exists():
                    shutil.rmtree(self.state)
                _, first, dispatch = self.composed(native)
                dispatch.assert_called_once()
                preparation = self.state / 'ready-preflights/T1/preparation.json'
                before = preparation.read_bytes()
                code, second, retry = self.composed()
                self.assertEqual(code, 1)
                retry.assert_not_called()
                self.assertIn('prior dispatch attempted', second['next_action'])
                self.assertEqual(preparation.read_bytes(), before)
                self.assertIn('original', str(first))

    def test_missing_native_cap_is_reported_without_dispatch_or_replenishment(self):
        self.ready_backlog()
        capability = {'outcome': 'unavailable', 'reason': 'atomic cumulative cap unavailable'}
        code, receipt, dispatch = self.composed(prior={'task_id': 'original',
            'next_action': 'recover_original_card', 'continuation_capability': capability})
        self.assertEqual(code, 1)
        dispatch.assert_not_called()
        self.assertEqual(receipt['blocker'], ['atomic cumulative cap unavailable'])
        self.assertEqual(receipt['recovery'].get('continuation_capability'), capability)
        self.assertFalse((self.state / 'ready-preflights').exists())

    def test_capability_does_not_block_observation_or_closeout(self):
        self.ready_backlog()
        for action in ('reconcile_run_state', 'verify_and_integrate', 'observe_current_run'):
            _, receipt, dispatch = self.composed(prior={'task_id': 'original',
                'next_action': action, 'continuation_capability': {
                    'outcome': 'unavailable', 'reason': 'atomic cap unavailable'}})
            self.assertEqual(receipt['blocker'], [])
            self.assertEqual(receipt['next_action'], action)
            dispatch.assert_not_called()

    def test_prior_interrupted_or_review_card_precedes_selection(self):
        self.ready_backlog()
        before = (self.repo / 'goals.json').read_bytes()
        for action in ('reconcile_run_state', 'observe_current_run', 'verify_and_integrate', 'recover_original_card'):
            code, receipt, dispatch = self.composed(prior={'task_id': 'original', 'next_action': action})
            self.assertEqual(code, 1)
            dispatch.assert_not_called()
            self.assertEqual(receipt['reconciliation']['task_id'], 'original')
            self.assertEqual((self.repo / 'goals.json').read_bytes(), before)

    def test_stale_saved_preparation_never_refreshes(self):
        import owner_cycle, ready_preflight
        from types import SimpleNamespace
        self.ready_backlog()
        args = SimpleNamespace(profile='fixture', plan='SPEC.md#slice', source_path=['code.py'],
                               base=None, fallback_file=None, pass_root=None, ledger_mode='worker')
        receipt = ready_preflight.compose(args, {'id': 'T1', 'goal': 'G1', 'title': 'Implement fixture'},
                                          str(self.repo), self.state, owner_cycle.save)
        snapshot = Path(receipt['snapshot']).read_bytes()
        (self.repo / 'code.py').write_text('changed\n')
        code, refused, dispatch = self.composed()
        self.assertEqual(code, 1)
        dispatch.assert_not_called()
        self.assertIn('stale', refused['next_action'])
        self.assertEqual(Path(receipt['snapshot']).read_bytes(), snapshot)

    def test_unchanged_pre_dispatch_preparation_is_reused_and_tamper_refused(self):
        import owner_cycle, ready_preflight
        from types import SimpleNamespace
        from unittest.mock import patch
        self.ready_backlog()
        args = SimpleNamespace(profile='fixture', plan='SPEC.md#slice', source_path=['code.py'],
                               base=None, fallback_file=None, pass_root=None, ledger_mode='worker')
        task = {'id': 'T1', 'goal': 'G1', 'title': 'Implement fixture'}
        first = ready_preflight.compose(args, task, str(self.repo), self.state, owner_cycle.save)
        # check() internally fingerprints again; only contract preparation is reused.
        with patch.object(ready_preflight.start_goal, 'validate_contract', side_effect=AssertionError('no repeated contract preparation')):
            second = ready_preflight.compose(args, task, str(self.repo), self.state, owner_cycle.save)
        self.assertEqual(first, second)
        Path(first['contract']).write_text('Changed contract\n')
        with self.assertRaisesRegex(ValueError, 'artifact changed'):
            ready_preflight.compose(args, task, str(self.repo), self.state, owner_cycle.save)
        self.assertFalse(json.loads((self.state / 'ready-preflights/T1/preparation.json').read_text())['dispatch_attempted'])

    def test_default_held_selection_preserves_ledger_without_dispatch(self):
        import owner_cycle
        from unittest.mock import patch
        from contextlib import redirect_stdout
        import io
        self.ready_backlog()
        path = self.repo / 'goals.json'
        data = json.loads(path.read_text())
        data['tasks'][0]['status'] = 'in_progress'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        with patch.object(owner_cycle.reconcile, 'profile_home', return_value=self.root), \
                patch.object(owner_cycle.reconcile, 'reconcile', return_value={'outcome': 'no_handoff'}), \
                patch.object(owner_cycle, 'handoff') as dispatch, \
                patch.dict(owner_cycle.os.environ, {}, clear=True), redirect_stdout(io.StringIO()):
            code = owner_cycle.main([str(self.repo), '--profile', 'fixture', '--state-dir', str(self.state),
                                    '--apply', '--source-path', 'code.py'])
        self.assertEqual(code, 1)
        dispatch.assert_not_called()
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse((self.state / 'ready-preflights').exists())


if __name__ == '__main__': unittest.main()
