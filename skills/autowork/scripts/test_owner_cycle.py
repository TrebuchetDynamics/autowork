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

    def run_cycle(self, *extra):
        r = subprocess.run([sys.executable,str(SCRIPT),str(self.repo),'--plan','SPEC.md#slice',
                            '--tasks','T1','--state-dir',str(self.state),*extra],capture_output=True,text=True)
        self.assertTrue(r.stdout, r.stderr)
        return r, json.loads((self.state/'unblock-latest.json').read_text())

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
        self.assertEqual(receipt['planning']['action'],'repair_execution_inputs')
        self.assertEqual(receipt['selected_task']['id'],'T1')
        self.assertFalse(receipt['dispatch_attempted'])
        self.assertIn('Implement fixture', (self.state/'report-latest.txt').read_text())

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
        self.assertEqual(first['planning']['action'],'repair_execution_inputs')
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


if __name__ == '__main__': unittest.main()
