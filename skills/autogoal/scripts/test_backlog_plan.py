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
    def test_receipt_requires_actual_evidence_and_known_outcome(self):
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'','no_supported_delta')
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'fixture://receipt','completed')

if __name__=='__main__':unittest.main()
