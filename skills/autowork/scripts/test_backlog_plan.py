import tempfile
from pathlib import Path
import unittest
import backlog_plan

class BacklogPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)
        self.cycle={'consumer':'/fixture/repo','plan':'SPEC.md#accepted','task_ids':['T1'],
                    'fingerprint':'stable-inputs','unchanged_runs':2,'ready_queue':[],
                    'recovery':{'gate':'consumer_readiness'}}
    def test_repeated_hold_plans_once_until_inputs_change(self):
        first=backlog_plan.decide(self.cycle,self.state)
        self.assertEqual(first['action'],'plan')
        backlog_plan.record(self.cycle,self.state,'fixture://findings','no_supported_delta')
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'reuse')
        self.cycle['fingerprint']='changed-inputs'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'plan')
    def test_missing_canonical_inputs_need_integration_not_another_proposal(self):
        self.cycle['recovery']['gate']='ledger'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'integrate_existing_inputs')
    def test_ready_work_and_owned_work_skip_planning(self):
        self.cycle['ready_queue']=[{'id':'T2'}]
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'execute_ready_work')
        self.cycle['ready_queue']=[];self.cycle['recovery']['gate']='ownership'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'reconcile_owner')
    def test_repository_scope_keeps_deciding_beyond_cached_task_hold(self):
        self.cycle['scope']='repository'
        backlog_plan.record(self.cycle,self.state,'fixture://findings','no_supported_delta')
        for gate in ('consumer_readiness','prerequisites','candidate','source_freshness','owner_authority'):
            self.cycle['recovery']['gate']=gate
            result=backlog_plan.decide(self.cycle,self.state)
            self.assertEqual(result['action'],'discover_repository_work', gate)
            self.assertTrue(result['execution_required'])
        self.cycle['scope']='tasks'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'repair_execution_inputs')

    def test_repository_scope_does_not_bypass_ownership_or_canonical_integration(self):
        self.cycle['scope']='repository'
        for gate, action in [('ownership','reconcile_owner'),('ledger','integrate_existing_inputs')]:
            self.cycle['recovery']['gate']=gate
            self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],action)

    def test_observed_queue_does_not_hide_held_selected_task(self):
        self.cycle.update(scope='repository', backlog_ready=False, ready_queue=[{'id':'T2'}])
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'], 'discover_repository_work')

    def test_receipt_requires_actual_evidence_and_known_outcome(self):
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'','no_supported_delta')
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'fixture://receipt','completed')

if __name__=='__main__':unittest.main()
