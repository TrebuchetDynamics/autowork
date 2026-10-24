"""Auxiliary technical failures do not consume completed verdict/install markers."""
import json
from pathlib import Path
from types import SimpleNamespace
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator
from pi_autowork import maintainer, pi_runtime
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import store_fixture


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.base=Path(self.tmp.name); self.repo=self.base/'repo'; self.repo.mkdir()
        self.state=self.base/'state'; self.state.mkdir(); (self.state/'runs').mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.calls=[]

    def runner(self):
        runner=Coordinator.__new__(Coordinator)
        runner.stop=False; runner.state=self.state; runner.repo=str(self.repo); runner.integ=str(self.repo)
        runner.cfg={'git_common':str(self.repo/'.git')}
        runner.last_pi_failure='toolchain'
        runner._scratch_cleanup={str(self.repo):True}
        runner.pi_job=lambda *args: (self.calls.append(args) or (False,''))
        return runner

    def maintainer_runner(self, state, background=False):
        if not (self.repo / 'tasks').exists():
            store_fixture.write_todo(self.repo, '- [ ] A — Repair\n  Scope: proof\n')
        state.mkdir(exist_ok=True); (state/'runs').mkdir(exist_ok=True)
        runner=self.runner(); runner.state=state
        runner.toolset=Path(__file__).resolve().parents[2]
        runner.tasks_cli='autowork tasks'; runner.verify_timeout=5; runner.integ_branch=''
        runner.in_flight=runner.session_busy=runner.reexec_due=lambda: False
        reason='shares x.py with B' if background else 'not runnable: missing Checks'
        runner.tasks=lambda: [dict(task='A',state='waiting',reason=reason)]
        runner.scratch_checkout=lambda _: str(self.repo)
        runner.restart_status=lambda **kwargs: None
        runner.pi_job=Coordinator.pi_job.__get__(runner)
        runner.engine=lambda *args: self.fail('maintainer must not reset engine budgets')
        return runner

    def test_maintainer_safe_failure_retries_with_durable_budget(self):
        real_popen=subprocess.Popen
        for background in (False,True,'stop'):
            for restored in (False,True):
                with self.subTest(background=background,restored=restored):
                    self.calls.clear(); dropped=[]
                    state=self.state/f'{background}-{restored}'
                    def launch(args, **kwargs):
                        if args[0] != sys.executable:
                            return real_popen(args, **kwargs)
                        self.calls.append(args)
                        payload={'ok':True,'text':'PI_AUTOWORK_RESULT: blocked'} if restored and len(self.calls)>1 else {
                            'ok':False,'why':'no_model'}
                        json.dump(payload,kwargs['stdout'])
                        return SimpleNamespace(wait=lambda:0,poll=lambda:0,returncode=0)
                    for at, count in ((100,1),(100,1),(159,1),(160,2),(279,2),(280,2 if restored else 3),
                                      (1000,2 if restored else 3)):
                        # A new coordinator must observe the same on-disk budget.
                        runner=self.maintainer_runner(state,background)
                        runner.drop_scratch=lambda path: dropped.append(path)
                        runner.last_pi_failure='uncertain_acceptance'  # Unrelated foreground job.
                        with patch('pi_autowork.coordinator.subprocess.Popen',side_effect=launch), \
                                patch('pi_autowork.coordinator.time.time',return_value=at):
                            self.assertFalse(runner.maintain(overlap=background,ledger_errors=[]))
                            if background:
                                if background == 'stop' and (not restored or len(self.calls) == 1):
                                    runner.stop_maintainer()
                                else:
                                    runner.finish_maintainer()
                        self.assertEqual(len(self.calls),count)
                    markers=json.loads((state/'maintainer-recovery.json').read_text())
                    self.assertEqual(markers['task:A']['attempts'],2 if restored else 3)
                    self.assertEqual(len(dropped),len(self.calls))
                    receipt=maintainer.last(state)
                    if restored:
                        self.assertEqual(receipt['tries'],1)
                        self.assertEqual(receipt['items']['task:A']['tries'],1)
                    else:
                        self.assertEqual(receipt['items'],{})
                        self.assertEqual(receipt['runtime']['why'],'no_model')

    def test_maintainer_uncertain_or_foreign_results_never_replay_or_delete_scratch(self):
        real_popen=subprocess.Popen
        for background in (False,True):
            for why in ('uncertain_acceptance','cleanup_unproven','runtime','lost','negative_cleanup'):
                with self.subTest(background=background,why=why):
                    self.calls.clear(); state=self.state/f'held-{background}-{why}'
                    runner=self.maintainer_runner(state,background)
                    runner._scratch_paths={str(self.repo)}
                    def launch(args, **kwargs):
                        if args[0] != sys.executable:
                            return real_popen(args, **kwargs)
                        self.calls.append(args)
                        if why == 'lost':
                            raise RuntimeError('lost after submission')
                        payload={'ok':True,'cleanup_complete':False} if why == 'negative_cleanup' else {
                            'ok':False,'why':why}
                        json.dump(payload,kwargs['stdout'])
                        return SimpleNamespace(wait=lambda:0,poll=lambda:0,returncode=0)
                    # A safe result from another role/checkout cannot authorize this retry.
                    runner.last_pi_failure='no_model'
                    runner.remember_job_cleanup(self.base/'other',{'ok':False,'why':'no_model'})
                    with patch('pi_autowork.coordinator.subprocess.Popen',side_effect=launch), \
                            patch('pi_autowork.coordinator.git_ok') as remove:
                        for at in (100,1000):
                            with patch('pi_autowork.coordinator.time.time',return_value=at):
                                try:
                                    runner.maintain(overlap=background,ledger_errors=[])
                                    if background: runner.finish_maintainer()
                                except RuntimeError:
                                    if why != 'lost': raise
                        remove.assert_not_called()
                    self.assertEqual(len(self.calls),1)
                    marker=json.loads((state/'maintainer-recovery.json').read_text())['task:A']
                    self.assertTrue(marker['replay_blocked'])
                    self.assertIn(str(self.repo),runner._scratch_paths)

    def test_triage_failure_remains_technical_with_durable_bounded_retry(self):
        for failure in ('toolchain','no_model','provider_failure','transport','timeout',
                        'interrupted','crash_failure'):
            with self.subTest(failure=failure):
                row=dict(task=failure,cause='blocker',worktree=str(self.repo),reason='needs diagnosis')
                self.calls.clear()
                for at, expected_calls in ((100,1),(100,1),(160,2),(279,2),(280,3),(1000,3)):
                    runner=self.runner(); runner.last_pi_failure=failure
                    with patch('pi_autowork.coordinator.time.time',return_value=at), \
                            patch('pi_autowork.coordinator.LOG.say') as log:
                        self.assertFalse(runner.triage_blocker(row))
                        self.assertEqual(len(self.calls),expected_calls)
                        messages=' '.join(str(call) for call in log.call_args_list)
                        self.assertNotIn('needs the owner',messages)
                        if at == 1000:  # Exhaustion remains actionable after coordinator restart.
                            self.assertIn('exhausted',messages)
                            self.assertIn(failure,messages)
                            self.assertIn(str(self.state/'triage.json'),messages)
                marker=json.loads((self.state/'triage.json').read_text())[failure]
                self.assertEqual(marker['attempts'],3)
                self.assertEqual(marker['failure'],failure)

    def test_missing_runtime_receipt_never_replays_triage(self):
        real_popen=subprocess.Popen
        for failure, payload, rc in (('runtime',None,1),('transport',{'why':'transport'},0)):
            with self.subTest(failure=failure):
                self.calls.clear()
                runner=self.runner(); runner.pi_job=Coordinator.pi_job.__get__(runner)
                runner.integ_branch=''; runner.restart_status=lambda **kwargs: None
                def launch(args, **kwargs):
                    if args[0] != sys.executable:
                        return real_popen(args, **kwargs)
                    self.calls.append(args)
                    if payload is not None:
                        json.dump(payload,kwargs['stdout'])  # Missing terminal ok/cleanup receipt.
                    return SimpleNamespace(wait=lambda: rc)
                row=dict(task=failure,cause='blocker',worktree=str(self.repo),reason='needs diagnosis')
                with patch('pi_autowork.coordinator.subprocess.Popen',side_effect=launch):
                    for at in (100,160):
                        with patch('pi_autowork.coordinator.time.time',return_value=at):
                            self.assertFalse(runner.triage_blocker(row))
                self.assertEqual(len(self.calls),1)
                self.assertFalse(runner._scratch_cleanup[str(self.repo)])
                marker=json.loads((self.state/'triage.json').read_text())[failure]
                self.assertEqual(marker['failure'],failure)
                self.assertTrue(marker['replay_blocked'])

    def test_lost_coordinator_reserves_triage_before_submission(self):
        row=dict(task='A',cause='blocker',worktree=str(self.repo),reason='needs diagnosis')
        def submitted(*args):
            self.calls.append(args)
            raise RuntimeError('coordinator lost after submission')
        for at in (100,1000,2000,3000):
            runner=self.runner(); runner.pi_job=submitted
            with patch('pi_autowork.coordinator.time.time',return_value=at):
                try: runner.triage_blocker(row)
                except RuntimeError: pass
        self.assertEqual(len(self.calls),1)
        marker=json.loads((self.state/'triage.json').read_text())['A']
        self.assertEqual(marker['attempts'],1)
        self.assertTrue(marker['replay_blocked'])

    def test_uncertain_triage_is_technical_but_never_automatically_replayed(self):
        runner=self.runner(); runner.last_pi_failure='uncertain_acceptance'
        row=dict(task='A',cause='blocker',worktree=str(self.repo),reason='needs diagnosis')
        for at in (100,1000,2000):
            with patch('pi_autowork.coordinator.time.time',return_value=at):
                self.assertFalse(runner.triage_blocker(row))
        self.assertEqual(len(self.calls),1)
        self.assertTrue(json.loads((self.state/'triage.json').read_text())['A']['replay_blocked'])

    def test_lost_coordinator_reserves_provisioning_before_submission(self):
        cache=self.base/'cache'; cache.mkdir()
        def submitted(*args):
            self.calls.append(args)
            raise RuntimeError('lost after submission')
        with patch('pi_autowork.coordinator.worker.repository_cache',return_value=cache):
            for at in (100,1000,2000):
                runner=self.runner(); runner.environment_hold=lambda _: 'missing tool'
                runner.scratch_checkout=lambda _: str(self.repo)
                runner.drop_scratch=lambda _: None; runner.verify_timeout=5; runner.pi_job=submitted
                with patch('pi_autowork.coordinator.time.time',return_value=at):
                    try: runner.provision_and_reverify('A','v1')
                    except RuntimeError: pass
        self.assertEqual(len(self.calls),1)
        marker=json.loads((self.state/'provisioned.json').read_text())['A']
        self.assertEqual(marker['attempts'],1)
        self.assertTrue(marker['replay_blocked'])

    def test_uncertain_provisioning_does_not_replay_partial_installation(self):
        runner=self.runner(); runner.last_pi_failure='cleanup_unproven'
        runner.environment_hold=lambda _: 'missing tool'
        runner.scratch_checkout=lambda _: str(self.repo)
        runner.drop_scratch=lambda _: None
        runner.verify_timeout=5
        cache=self.base/'cache'; cache.mkdir()
        with patch('pi_autowork.coordinator.worker.repository_cache',return_value=cache):
            for at in (100,1000,2000):
                with patch('pi_autowork.coordinator.time.time',return_value=at):
                    self.assertFalse(runner.provision_and_reverify('A','v1'))
        self.assertEqual(len(self.calls),1)
        self.assertTrue(json.loads((self.state/'provisioned.json').read_text())['A']['replay_blocked'])

    def test_unproven_cleanup_preserves_owned_scratch(self):
        runner=self.runner(); runner.last_pi_failure=''
        runner._scratch_paths={str(self.repo)}
        runner._scratch_cleanup={str(self.repo):False}
        with patch('pi_autowork.coordinator.git_ok') as remove:
            runner.drop_scratch(str(self.repo))
        remove.assert_not_called()
        self.assertIn(str(self.repo),runner._scratch_paths)

    def test_stop_and_timeout_never_hide_unproven_cleanup_from_scratch_policy(self):
        for code in (1,124):
            with self.subTest(code=code):
                outcome=dict(pi_runtime.analyse(''),rc=code,seconds=0,failure_kind='cleanup_unproven',
                             cleanup_complete=False,retry_safe=False)
                with patch.object(pi_runtime,'STOP',True), \
                        patch.object(pi_runtime,'choose',return_value=('offline/model','')), \
                        patch.object(pi_runtime,'run_pi',return_value=outcome), \
                        patch.object(pi_runtime,'record'), patch.object(pi_runtime.telemetry,'model_run'):
                    result=pi_runtime.job(pi_runtime.Settings(self.state,{}),'maintainer','M',self.repo,
                                          'accepted','session',5,[])
                runner=self.runner(); runner._scratch_paths={str(self.repo)}
                runner.remember_job_cleanup(str(self.repo),result)
                with patch('pi_autowork.coordinator.git_ok') as remove:
                    runner.drop_scratch(str(self.repo))
                remove.assert_not_called()
                self.assertEqual(result['why'],'cleanup_unproven')

    def test_cleanup_result_is_not_borrowed_from_an_unrelated_job(self):
        runner=self.runner(); runner._scratch_paths={str(self.repo)}
        runner.last_pi_failure='cleanup_unproven'
        runner.remember_job_cleanup(str(self.repo),{'ok':True})
        runner.remember_job_cleanup(str(self.base/'other'),{'ok':False,'why':'cleanup_unproven'})
        with patch('pi_autowork.coordinator.git_ok',return_value=True) as remove:
            runner.drop_scratch(str(self.repo))
        remove.assert_called_once()

    def test_background_and_stopped_jobs_bind_cleanup_to_their_scratch(self):
        for method in ('finish_maintainer','stop_maintainer'):
            for why in ('cleanup_unproven','uncertain_acceptance','runtime','negative_cleanup'):
                with self.subTest(method=method,why=why):
                    runner=self.runner(); runner.last_pi_failure=''
                    runner._scratch_paths={str(self.repo)}; runner.integ=None
                    output=self.state/'background.json'
                    payload={'ok':True,'cleanup_complete':False} if why == 'negative_cleanup' else {
                        'ok':False,'why':why}
                    output.write_text(json.dumps(payload))
                    job={'proc':SimpleNamespace(poll=lambda:0,returncode=0),'out':str(output),'scratch':str(self.repo)}
                    runner.maintainer_job=job
                    runner.maintainer_result=lambda job,ok: False
                    with patch('pi_autowork.coordinator.git_ok') as remove:
                        getattr(runner,method)()
                    remove.assert_not_called()
                    self.assertIn(str(self.repo),runner._scratch_paths)

    def test_missing_provisioning_scratch_is_not_a_completed_installation(self):
        cache=self.base/'cache'; cache.mkdir()
        with patch('pi_autowork.coordinator.worker.repository_cache',return_value=cache):
            for at, expected_calls in ((100,1),(100,1),(160,2),(279,2),(280,3),(1000,3)):
                runner=self.runner(); runner.environment_hold=lambda _: 'a missing test tool'
                runner.scratch_checkout=lambda _: (self.calls.append('scratch') or None)
                with patch('pi_autowork.coordinator.time.time',return_value=at), \
                        patch('pi_autowork.coordinator.LOG.say') as log:
                    self.assertFalse(runner.provision_and_reverify('A','review-v1'))
                    self.assertEqual(self.calls,['scratch']*expected_calls)
                    if at == 1000:
                        messages=' '.join(str(call) for call in log.call_args_list)
                        self.assertIn('exhausted',messages)
                        self.assertIn('scratch_unavailable',messages)
                        self.assertIn(str(self.state/'provisioned.json'),messages)
        marker=json.loads((self.state/'provisioned.json').read_text())['A']
        self.assertEqual(marker['attempts'],3)
        self.assertEqual(marker['failure'],'scratch_unavailable')

    def test_provisioning_recovers_missing_scratch_without_repeating_success(self):
        cache=self.base/'cache'; cache.mkdir()
        with patch('pi_autowork.coordinator.worker.repository_cache',return_value=cache):
            for at, scratch, expected in ((100,None,False),(160,str(self.repo),True),(1000,None,False)):
                runner=self.runner(); runner.environment_hold=lambda _: 'missing tool'
                runner.scratch_checkout=lambda _: scratch
                runner.drop_scratch=lambda _: None; runner.verify_timeout=5; runner.seen={}
                runner.pi_job=lambda *args: (self.calls.append(args) or (True,'PI_AUTOWORK_RESULT: completed\nUse cache.'))
                runner.engine=lambda *args: {'outcome':'REVERIFY'}
                with patch('pi_autowork.coordinator.time.time',return_value=at):
                    self.assertEqual(runner.provision_and_reverify('A','v1'),expected)
        self.assertEqual(len(self.calls),1)
        self.assertEqual(len((cache/'PROVISIONED.md').read_text().splitlines()),1)
        self.assertEqual(json.loads((self.state/'provisioned.json').read_text())['A'],'v1')

    def test_unapplied_triage_answer_is_retryable_not_a_completed_marker(self):
        runner=self.runner()
        runner.pi_job=lambda *args: (self.calls.append(args) or (True,'PI_AUTOWORK_TRIAGE: answer\nUse the provided local cache.'))
        runner.engine=lambda *args: {'outcome':'ERROR'}
        row=dict(task='A',cause='blocker',worktree=str(self.repo),reason='cache location')
        with patch('pi_autowork.coordinator.time.time',return_value=100):
            self.assertFalse(runner.triage_blocker(row))
        runner.engine=lambda *args: {'outcome':'ANSWERED'}
        with patch('pi_autowork.coordinator.time.time',return_value=1000):
            self.assertTrue(runner.triage_blocker(row))
        self.assertFalse(runner.triage_blocker(row))
        self.assertEqual(len(self.calls),2)

    def test_genuine_owner_verdict_stays_deduplicated(self):
        runner=self.runner()
        runner.pi_job=lambda *args: (self.calls.append(args) or (True,'PI_AUTOWORK_TRIAGE: owner\nreal external input'))
        row=dict(task='A',cause='blocker',worktree=str(self.repo),reason='needs account')
        self.assertFalse(runner.triage_blocker(row))
        self.assertFalse(runner.triage_blocker(row))
        self.assertEqual(len(self.calls),1)


if __name__=='__main__': unittest.main()
