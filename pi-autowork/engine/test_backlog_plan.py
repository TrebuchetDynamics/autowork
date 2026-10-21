import tempfile
import json
from pathlib import Path
import shutil
import subprocess
import sys
import unittest
import backlog_plan

FIXTURE = Path(__file__).parent / 'fixtures' / 'task_store'

class BacklogPlanTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.state=Path(self.tmp.name)
        self.cycle={'consumer':'/fixture/repo','plan':'SPEC.md#accepted','task_ids':['T1'],
                    'fingerprint':'stable-inputs','unchanged_runs':2,
                    'recovery':{'gate':'consumer_readiness'}}
    def test_repeated_hold_plans_once_until_inputs_change(self):
        first=backlog_plan.decide(self.cycle,self.state)
        self.assertEqual(first['action'],'plan')
        backlog_plan.record(self.cycle,self.state,'fixture://findings','no_supported_delta')
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'resolve_recorded_blocker')
        self.cycle['fingerprint']='changed-inputs'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'plan')
    def store(self, *, empty):
        """A converted consumer: one runnable task, or none (its only task closed)."""
        repo = Path(self.tmp.name) / ('empty' if empty else 'ready')
        shutil.copytree(FIXTURE, repo)
        if empty:
            path = repo / 'tasks/items/T-1.md'
            path.write_text(path.read_text().replace('status = "open"', 'status = "done"'))
        git = ['git', '-C', str(repo), '-c', 'user.email=f@example.invalid', '-c', 'user.name=F']
        subprocess.run([*git, 'init', '-q'], check=True)
        subprocess.run([*git, 'add', '-A'], check=True)
        subprocess.run([*git, 'commit', '-qm', 'tasks'], check=True)
        return repo

    def check(self):
        """The real entry point: backlog_plan.py check --cycle FILE, the queue read from the store."""
        path = Path(self.tmp.name) / 'cycle.json'
        path.write_text(json.dumps(self.cycle))
        out = subprocess.run([sys.executable, str(Path(backlog_plan.__file__)), 'check', '--cycle', str(path),
                              '--state-dir', str(self.state)], capture_output=True, text=True, check=True)
        return json.loads(out.stdout)

    def test_an_empty_store_plans_on_first_occurrence_then_reuses_receipt(self):
        self.cycle.update(consumer=str(self.store(empty=True)), unchanged_runs=0, task_ids=[],
                          ready_queue=[{'id': 'stale'}])  # a hand-written queue is ignored
        self.cycle['recovery']['gate']=None
        self.assertEqual(self.check()['action'], 'plan')
        backlog_plan.record(self.cycle,self.state,'fixture://empty-queue-plan','canonical_reconciled')
        self.assertEqual(self.check()['action'], 'reuse')

    def test_a_store_with_ready_work_executes_it(self):
        self.cycle.update(consumer=str(self.store(empty=False)), unchanged_runs=0, ready_queue=[])
        self.cycle['recovery']['gate']=None
        self.assertEqual(self.check()['action'], 'execute_ready_work')
        self.assertEqual(backlog_plan.ready_queue(self.cycle), [{'id': 'T-1', 'title': 'Read tasks', 'goal': 'G-1'}])

    def test_unknown_queue_does_not_count_as_observed_empty(self):
        self.cycle.update(unchanged_runs=0)  # /fixture/repo does not exist: the queue is unknown
        self.cycle['recovery']['gate']=None
        self.assertIsNone(backlog_plan.ready_queue(self.cycle))
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'], 'recover_first')

    def test_missing_canonical_inputs_need_integration_not_another_proposal(self):
        self.cycle['recovery']['gate']='ledger'
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'integrate_existing_inputs')
    def test_owned_work_skips_planning(self):
        self.cycle.update(consumer=str(self.store(empty=False)))
        self.cycle['recovery']['gate']='ownership'
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
        self.cycle.update(scope='repository', backlog_ready=False, consumer=str(self.store(empty=False)))
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'], 'discover_repository_work')

    def test_handoff_preparation_plans_without_waiting_for_user(self):
        self.cycle.update(scope='tasks', admission='handoff_preparation',
                          selected_task={'id':'T1'},
                          unchanged_runs=0)
        result=backlog_plan.decide(self.cycle,self.state)
        self.assertEqual(result['action'],'plan')
        self.assertEqual(result['skill'],'autowork:plan-for-me')
        self.assertTrue(result['execution_required'])
        backlog_plan.record(self.cycle,self.state,'fixture://recovery-plan','canonical_reconciled')
        self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],'reuse')

    def test_ready_preparation_skips_research_but_preserves_prior_failure(self):
        self.cycle.update(coordination_mode='autonomous', admission='handoff_preparation',
                          backlog_ready=True, selected_task={'id': 'T1'})
        self.cycle['recovery']['gate'] = 'ready_for_autowork'
        self.assertEqual(backlog_plan.decide(self.cycle, self.state)['action'], 'prepare_execution_handoff')
        path = backlog_plan.record(self.cycle, self.state, 'fixture://preserved-failure', 'no_supported_delta')
        before = Path(path).read_bytes()
        self.assertEqual(backlog_plan.decide(self.cycle, self.state)['action'], 'resolve_recorded_blocker')
        self.assertEqual(Path(path).read_bytes(), before)
        self.cycle['fingerprint'] = 'new-inputs'
        self.cycle['recovery']['gate'] = 'candidate'
        self.assertEqual(backlog_plan.decide(self.cycle, self.state)['action'], 'plan')

    def test_selected_task_with_unresolved_inputs_is_not_ready(self):
        self.cycle.update(scope='tasks', selected_task={'id':'T1'}, unchanged_runs=0)
        for gate in ('candidate','source_freshness','prerequisites'):
            self.cycle['recovery']['gate']=gate
            result=backlog_plan.decide(self.cycle,self.state)
            self.assertEqual(result['action'],'plan',gate)
            self.assertIn('scope',result['boundary'])

    def test_planning_does_not_override_refusal_or_live_writer(self):
        self.cycle.update(scope='tasks', admission='handoff_preparation', selected_task={'id':'T1'})
        for gate, expected in [('ownership','reconcile_owner'),('refused','repair_execution_inputs')]:
            self.cycle['recovery']['gate']=gate
            self.assertEqual(backlog_plan.decide(self.cycle,self.state)['action'],expected)

    def test_draft_saved_repairs_shared_backlog_before_unrelated_discovery(self):
        self.cycle.update(scope='repository', backlog_ready=False, unchanged_runs=0)
        self.cycle['recovery']['selection'] = {
            'state': 'draft_saved', 'reasons': ['T9: missing Acceptance']}
        result = backlog_plan.decide(self.cycle, self.state)
        self.assertEqual(result['action'], 'plan')
        self.assertIn('documentation', result['reason'])
        backlog_plan.record(self.cycle, self.state, 'fixture://repair', 'integration_pending')
        self.assertEqual(backlog_plan.decide(self.cycle, self.state)['action'], 'reuse')

    def test_no_delta_receipt_does_not_claim_an_executable_repair(self):
        backlog_plan.record(self.cycle, self.state, 'fixture://investigation', 'no_supported_delta')
        result = backlog_plan.decide(self.cycle, self.state)
        self.assertEqual(result['action'], 'resolve_recorded_blocker')
        self.assertEqual(result['outcome'], 'no_supported_delta')
        self.assertEqual(result['evidence'], 'fixture://investigation')
        self.assertNotIn('Resume the recorded repair', result['reason'])

    def test_corrupt_planning_receipt_requires_reinspection_not_a_new_plan(self):
        path = Path(backlog_plan.record(self.cycle, self.state, 'fixture://result', 'integration_pending'))
        valid = json.loads(path.read_text())
        invalid = [dict(valid, consumer='/different/repo'), dict(valid, outcome='completed'),
                   dict(valid, evidence=''), dict(valid, input_key='stale')]
        for raw in ('{broken', '[]', '{}', *(json.dumps(item) for item in invalid)):
            path.write_text(raw)
            result = backlog_plan.decide(self.cycle, self.state)
            self.assertEqual(result['action'], 'inspect_planning_receipt')
            self.assertEqual(path.read_text(), raw)

    def test_receipt_requires_actual_evidence_and_known_outcome(self):
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'','no_supported_delta')
        with self.assertRaises(ValueError):backlog_plan.record(self.cycle,self.state,'fixture://receipt','completed')

if __name__=='__main__':unittest.main()
