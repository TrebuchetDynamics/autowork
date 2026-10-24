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
from pi_autowork import pi_runtime


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
        runner.pi_job=lambda *args: (self.calls.append(args) or (False,''))
        return runner

    def test_triage_failure_remains_technical_with_durable_bounded_retry(self):
        row=dict(task='A',cause='blocker',worktree=str(self.repo),reason='needs diagnosis')
        with patch('pi_autowork.coordinator.time.time',return_value=100), \
                patch('pi_autowork.coordinator.LOG.say') as log:
            self.assertFalse(self.runner().triage_blocker(row))
            self.assertFalse(self.runner().triage_blocker(row))
            self.assertEqual(len(self.calls),1)
            self.assertFalse(any('needs the owner' in str(call) for call in log.call_args_list))
        for at in (1000,2000,3000):
            with patch('pi_autowork.coordinator.time.time',return_value=at):
                self.assertFalse(self.runner().triage_blocker(row))
        self.assertEqual(len(self.calls),3)
        marker=json.loads((self.state/'triage.json').read_text())['A']
        self.assertEqual(marker['attempts'],3)
        self.assertEqual(marker['failure'],'toolchain')

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
            with self.subTest(method=method):
                runner=self.runner(); runner.last_pi_failure=''
                runner._scratch_paths={str(self.repo)}; runner.integ=None
                output=self.state/'background.json'
                output.write_text(json.dumps({'ok':False,'why':'cleanup_unproven'}))
                job={'proc':SimpleNamespace(poll=lambda:0,returncode=0),'out':str(output),'scratch':str(self.repo)}
                runner.maintainer_job=job
                runner.maintainer_result=lambda job,ok: runner.drop_scratch(job['scratch']) or False
                with patch('pi_autowork.coordinator.git_ok') as remove:
                    getattr(runner,method)()
                remove.assert_not_called()
                self.assertIn(str(self.repo),runner._scratch_paths)

    def test_missing_provisioning_scratch_is_not_a_completed_installation(self):
        runner=self.runner(); runner.environment_hold=lambda _: 'a missing test tool'
        runner.scratch_checkout=lambda _: (self.calls.append('scratch') or None)
        cache=self.base/'cache'; cache.mkdir()
        with patch('pi_autowork.coordinator.worker.repository_cache',return_value=cache):
            for at in (100,100,1000,2000,3000):
                with patch('pi_autowork.coordinator.time.time',return_value=at):
                    self.assertFalse(runner.provision_and_reverify('A','review-v1'))
        self.assertEqual(self.calls,['scratch']*3)
        marker=json.loads((self.state/'provisioned.json').read_text())['A']
        self.assertIsInstance(marker,dict)
        self.assertEqual(marker['failure'],'scratch_unavailable')

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
