"""Default RPC contract tests. SDK subprocess tests require the pinned SDK interpreter."""
import asyncio
from dataclasses import replace
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import pi_runtime, pi_rpc, pi_run_support

FAKE = r'''#!/usr/bin/env python3
import json, os, sys, threading, time, subprocess
args=sys.argv[1:]
if '--version' in args:
    print(os.environ.get('FAKE_VERSION','1.4.0')); sys.exit()
if args[:2] == ['auth','check']: sys.exit()
assert args[args.index('--mode')+1] == 'rpc', args
session=args[args.index('--session-id')+1]
mode=os.environ.get('FAKE_BEHAVIOR','finish')
if mode=='fallback': mode='provider' if args[args.index('--provider')+1]=='primary' else 'finish'
lock=threading.Lock()
active=False
stop=threading.Event()
def emit(value):
    with lock: print(json.dumps(value, ensure_ascii=False),flush=True)
def response(req,data=None,success=True):
    out=dict(type='response',id=req['id'],command=req['type'],success=success)
    if data is not None: out['data']=data
    if not success: out['error']='rejected'
    emit(out)
def work():
    global active
    active=True
    emit(dict(type='agent_start'))
    emit(dict(type='tool_execution_start',toolCallId='t1',toolName='read',args={'secret':'not-for-progress'}))
    if mode in ('wait','hang'):
        stop.wait(30)
    tool_rc=0
    if mode=='command_hang':
        tool_rc=subprocess.Popen(['/bin/sh','-c','sleep 3']).wait()
    emit(dict(type='tool_execution_end',toolCallId='t1',toolName='read',result={'content':[]},isError=False))
    emit(dict(type='message_end',message=dict(role='assistant',content=[dict(type='text',text=('x'*300000 if mode=='overflow' else 'missed watchdog' if mode=='command_hang' and tool_rc==0 else 'hello\u2028world'))],stopReason='error' if mode in ('provider','aborted_provider') else 'stop',errorMessage='429 limited' if mode in ('provider','aborted_provider') else None,usage=dict(totalTokens=7,input=5,output=2,cost={'total':.25}))))
    emit(dict(type='agent_end',messages=[]))
    if mode=='early': time.sleep(.25)
    active=False
    emit(dict(type='agent_settled',aborted=stop.is_set() or mode=='aborted_provider'))
for line in sys.stdin:
    req=json.loads(line); kind=req['type']
    if kind=='get_state':
        response(req,dict(sessionId=session,isStreaming=active,isCompacting=False,pendingMessageCount=0))
    elif kind=='prompt':
        if os.environ.get('FAKE_LOG'):
            with open(os.environ['FAKE_LOG'],'a') as f: f.write(json.dumps({'session':session,'prompt':req['message'],'args':args})+'\n')
        if mode=='reject': response(req,success=False); continue
        if mode=='ack_timeout': continue
        if mode=='malformed': print('{bad',flush=True); continue
        if mode=='late_reject': work(); response(req,success=False); continue
        response(req,{'disposition':'started'})
        if mode!='no_start': threading.Thread(target=work,daemon=True).start()
    elif kind in ('steer','follow_up'):
        response(req,{'disposition':'queued'})
    elif kind=='clear_queue': response(req,{'steering':[],'followUp':[]})
    elif kind=='abort': stop.set(); response(req)
'''


class SpecTests(unittest.TestCase):
    def test_rpc_is_default_and_json_requires_explicit_selection(self):
        self.assertEqual(pi_runtime.Settings('/unused', {}).transport, 'rpc')
        self.assertEqual(pi_runtime.Settings('/unused', {'PI_AUTOWORK_TRANSPORT':'json'}).transport, 'json')

    def test_rpc_cancellation_observes_the_callers_live_stop_state(self):
        settings = pi_runtime.Settings('/unused', {})
        with patch.object(pi_runtime, 'STOP', False), patch.object(pi_rpc, 'run', return_value={}) as run:
            pi_runtime.run_pi(settings, '/unused', 'go', 's1', 'p/m', 10, [], 'worker')
            stopping = run.call_args.kwargs.get('stop_requested')
            self.assertTrue(callable(stopping), 'RPC must receive the caller-owned cancellation callback')
            self.assertFalse(stopping())
            pi_runtime.STOP = True
            self.assertTrue(stopping())

    def test_missing_sdk_returns_toolchain_failure_without_starting_a_run(self):
        with tempfile.TemporaryDirectory() as root:
            settings = pi_runtime.Settings(Path(root) / 'state', {
                'PI_AUTOWORK_RPC_PYTHON': str(Path(root) / 'missing-python')})
            result = pi_runtime.run_pi(settings, root, 'go', 's1', 'p/m', 10, [], 'worker')
            self.assertEqual((result['rc'], result['failure_kind']), (1, 'toolchain'))
            self.assertFalse(result['retry_safe'])
            self.assertFalse(result['settled'])
            self.assertIsNone(result['tokens'])
            self.assertIsNone(result['cost'])
            self.assertTrue(result['error'])
            self.assertFalse(settings.state.exists())

    def test_startup_prompt_file_is_expanded_exactly_and_bounded(self):
        with tempfile.TemporaryDirectory() as root:
            path=Path(root)/'prompt.md'; path.write_text('Task: T-1\nExact accepted scope\u2028retained')
            settings=pi_runtime.Settings(root, {'PI_BIN':'pi'})
            spec=pi_rpc.make_spec(settings,root,'follow the contract','s1','offline/fixture',10,[f'@{path}'],'worker')
            self.assertIn(path.read_text(),spec.prompt)
            self.assertIn('follow the contract',spec.prompt)
            self.assertNotIn(f'@{path}',spec.extra_args)
            self.assertEqual(len(spec.prompt_digest),64)
            path.write_bytes(b'x'*(pi_rpc.MAX_PROMPT_BYTES+1))
            with self.assertRaises(ValueError):
                pi_rpc.make_spec(settings,root,'go','s1','offline/fixture',10,[f'@{path}'],'worker')

    def test_fleet_uses_only_fresh_identity_bound_rpc_progress(self):
        from pi_autowork import fleet_view
        from pi_autowork.processes import start_time
        import time
        with tempfile.TemporaryDirectory() as root:
            path=pi_rpc.runtime_path(root,'worker:T-1','active.json')
            record=dict(task='T-1',role='worker',active=True,transport='rpc',phase='tool',current_tool='bash',
                        pid=os.getpid(),start_time=start_time(os.getpid()),updated_at=time.time(),
                        last_event_at=time.monotonic(),retries=0,compactions=0)
            pi_rpc.private_json(path,record)
            self.assertIn('RPC',fleet_view._activity(root,'T-1',time.time())[0])
            pi_rpc.private_json(path,dict(record,start_time='stale'))
            self.assertEqual(fleet_view._activity(root,'T-1',time.time())[0],'')
            pi_rpc.private_json(path,dict(record,updated_at=time.time()-30))
            self.assertEqual(fleet_view._activity(root,'T-1',time.time())[0],'')

    def test_watchdog_rejects_recycled_child_snapshot_with_unrelated_ancestry(self):
        import subprocess
        from pi_autowork import pi_process
        first=subprocess.Popen(['sleep','30']); unrelated=subprocess.Popen(['sleep','30'])
        try:
            children=lambda pid: [first.pid] if pid==os.getpid() else [unrelated.pid]
            with patch.object(pi_run_support,'_children',side_effect=children), \
                    patch.object(pi_process.signal,'pidfd_send_signal') as send:
                pi_runtime.stop_stuck_commands(os.getpid(),.000001,{})
                send.assert_not_called()
                pi_runtime.stop_stuck_commands(os.getpid(),.000001,{},pi_pid=first.pid,pi_started='stale')
                send.assert_not_called()
        finally:
            first.terminate(); unrelated.terminate(); first.wait(); unrelated.wait()

    def test_reviewer_excludes_mcp_and_rejects_worker_control(self):
        with tempfile.TemporaryDirectory() as root:
            spec=pi_rpc.make_spec(pi_runtime.Settings(root,{}),root,'review','review1','p/m',10,[],'verify')
            self.assertIn('--no-mcp',spec.extra_args)
            with self.assertRaises(ValueError):
                pi_rpc.authorize_control(spec, {'kind':'steer','message':'pass it'})


@unittest.skipUnless(importlib.util.find_spec('pi_agent'), 'install pi-autowork/requirements-rpc.txt in this Python')
class SdkTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name)
        self.pi=self.root/'pi'; self.pi.write_text(FAKE); self.pi.chmod(0o700)
        self.env={'PATH':os.environ['PATH'],'HOME':str(self.root),'FAKE_LOG':str(self.root/'calls')}
        self.settings=pi_runtime.Settings(self.root/'state',{'PI_BIN':str(self.pi),'PI_AUTOWORK_RPC_PYTHON':sys.executable})
        self.spec=pi_rpc.make_spec(self.settings,self.root,'do the accepted task','attempt1','offline/fixture',5,[],'worker')
        self.spec=replace(self.spec, environment=tuple(self.env.items()),command_timeout=.25)

    def execute(self,mode='finish'):
        spec=replace(self.spec,environment=tuple(dict(self.env,FAKE_BEHAVIOR=mode).items()))
        return asyncio.run(pi_rpc.PiRpcRuntime(spec).execute())

    def test_real_sdk_waits_for_settlement_and_preserves_unicode_and_usage(self):
        result=self.execute('early')
        self.assertTrue(result['settled']); self.assertEqual(result['rc'],0)
        self.assertEqual(result['text'],'hello\u2028world')
        self.assertEqual(result['sdk_version'],'0.2.6')
        self.assertEqual(result['pi_version'],'1.4.0')
        self.assertIsNone(result['cost'])
        self.assertGreaterEqual(result['seconds'],.25)

    def test_typed_failures_do_not_become_success_or_automatic_replay(self):
        for mode,expected in [('reject','rejected'),('ack_timeout','uncertain_acceptance'),
                              ('no_start','uncertain_acceptance'),('malformed','protocol'),
                              ('late_reject','rejected'),('overflow','overflow')]:
            with self.subTest(mode=mode):
                result=self.execute(mode)
                self.assertNotEqual(result['rc'],0)
                self.assertEqual(result['failure_kind'],expected)
                self.assertFalse(result['retry_safe'])
        calls=[json.loads(x) for x in (self.root/'calls').read_text().splitlines()]
        self.assertEqual(len(calls),6)

    def test_command_watchdog_stops_only_the_owned_tool_and_keeps_attempt(self):
        async def scenario():
            spec=replace(self.spec,timeout=200,
                         environment=tuple(dict(self.env,FAKE_BEHAVIOR='command_hang',
                                                PI_AUTOWORK_COMMAND_TIMEOUT='.1').items()))
            result=await asyncio.wait_for(pi_rpc.PiRpcRuntime(spec).execute(),10)
            self.assertTrue(result['settled'])
            self.assertEqual(result['rc'],0,result)
            self.assertEqual(result['text'],'hello\u2028world')
            self.assertEqual(result['command_interruptions'],1)
        asyncio.run(scenario())

    def test_mismatched_version_fails_before_prompt(self):
        self.env['FAKE_VERSION']='1.3.0'
        result=self.execute()
        self.assertEqual(result['failure_kind'],'toolchain')
        self.assertFalse((self.root/'calls').exists())

    def test_live_progress_and_state_are_visible_before_settlement(self):
        async def scenario():
            spec=replace(self.spec,environment=tuple(dict(self.env,FAKE_BEHAVIOR='wait').items()))
            runtime=pi_rpc.PiRpcRuntime(spec)
            task=asyncio.create_task(runtime.execute())
            for _ in range(100):
                if runtime.progress()['active_tool_count']: break
                await asyncio.sleep(.01)
            self.assertFalse(task.done())
            self.assertEqual(runtime.progress()['current_tool'],'read')
            self.assertNotIn('not-for-progress',json.dumps(runtime.progress()))
            self.assertTrue((await runtime.get_state())['isStreaming'])
            await runtime.abort()
            result=await task
            self.assertTrue(result['aborted']); self.assertNotEqual(result['rc'],0)
        asyncio.run(scenario())

    def test_guarded_default_seam_finishes_and_removes_private_transport_scratch(self):
        with patch.dict(os.environ,self.env,clear=True):
            result=pi_runtime.run_pi(self.settings,self.root,'exact input','guarded1','offline/fixture',5,[])
        self.assertEqual(result['rc'],0,result)
        self.assertTrue(result['cleanup_complete'])
        self.assertEqual(result['transport'],'rpc')
        self.assertEqual(list((self.settings.state/'runs').iterdir()),[])
        progress=json.loads(pi_rpc.runtime_path(self.settings.state,'guarded1').read_text())
        self.assertFalse(progress['active'])
        self.assertNotIn('exact input',json.dumps(progress))

    def test_uncertain_default_job_is_not_replayed_or_fallen_back(self):
        with patch.dict(os.environ,dict(self.env,FAKE_BEHAVIOR='ack_timeout'),clear=True):
            result=pi_runtime.job(self.settings,'worker','T-1',self.root,'go','uncertain1',.4,[])
        self.assertFalse(result['ok'])
        self.assertEqual(result['why'],'uncertain_acceptance')
        self.assertEqual(len((self.root/'calls').read_text().splitlines()),1)

    def test_aborted_provider_failure_never_replays_on_fallback(self):
        self.settings.backoff=0
        self.settings.max_retries=1
        with patch.dict(os.environ,dict(self.env,FAKE_BEHAVIOR='aborted_provider'),clear=True):
            result=pi_runtime.job(self.settings,'worker','T-1',self.root,'go','abort-provider',5,[])
        self.assertFalse(result['ok'])
        self.assertEqual(result['why'],'interrupted')
        self.assertEqual(len((self.root/'calls').read_text().splitlines()),1)

    def test_confirmed_provider_failure_falls_back_only_after_proven_cleanup(self):
        settings=pi_runtime.Settings(self.settings.state,{'PI_BIN':str(self.pi),
            'PI_AUTOWORK_RPC_PYTHON':sys.executable,'PI_AUTOWORK_PRIMARY':'primary/model',
            'PI_AUTOWORK_FALLBACK':'fallback/model','PI_AUTOWORK_BACKOFF':'0'})
        with patch.dict(os.environ,dict(self.env,FAKE_BEHAVIOR='fallback'),clear=True):
            result=pi_runtime.job(settings,'worker','T-1',self.root,'go','fallback1',5,[])
        self.assertTrue(result['ok'],result)
        rows=[json.loads(line) for line in (settings.state/'runs.jsonl').read_text().splitlines()]
        self.assertEqual([row['outcome'] for row in rows],['provider_failure','finished'])
        self.assertTrue(all(row['cleanup_complete'] for row in rows))

    def test_settlement_during_control_checks_refuses_late_submission(self):
        async def scenario():
            runtime=pi_rpc.PiRpcRuntime(replace(self.spec,task='T-1',attempt_id='attempt',
                                               contract_hash='a'*64,allow_steering=True))
            runtime.active=True; runtime.client=AsyncMock()
            runtime.client.request.return_value={'data':{'disposition':'queued'}}
            request=dict(kind='follow_up',action='reconcile',task='T-1',attempt_id='attempt',
                         contract_hash='a'*64,fingerprint='b'*64,generation=runtime.generation)
            def settles(): runtime.events.consume(dict(type='agent_settled',aborted=False))
            with patch.object(runtime,'_assert_binding',side_effect=settles):
                with self.assertRaisesRegex(ValueError,'run settled'):
                    await runtime.control(request)
            runtime.client.request.assert_not_awaited()
            history=json.loads(pi_rpc.runtime_path(runtime.spec.state,runtime.spec.session,'controls.json').read_text())
            self.assertEqual(len(history),1)
        asyncio.run(scenario())

    def test_controls_require_current_engine_binding_and_deduplicate_accepted_input(self):
        from pi_autowork import telemetry
        import subprocess
        subprocess.run(['git','init','-q',str(self.root)],check=True)
        engine=telemetry.engine(); common=engine.common_dir(self.root)
        sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
        import store_fixture
        from pi_autowork.engine import task_store
        store_fixture.write_todo(self.root, '# TODO\n\n## Next\n\n- [ ] T-1 — fixture\n'
                                 '  Scope: Complete marker\n  Touches: marker\n'
                                 '  Acceptance: marker exists\n  Checks: test -f marker\n'
                                 '  Dependencies: None\n  Status: open\n')
        accepted=task_store.TaskStore.at(self.root,'HEAD').tasks['T-1'].contract_hash
        slot={'task_id':'T-1','attempt_id':'attempt-id','attempt':1,'state':'running'}
        engine.execution.save(engine.slot_path(common,'T-1'),slot)
        contract=common/'slot-data/T-1/attempt-1/contract.json'
        engine.execution.save(contract,{'contract_hash':accepted})
        async def scenario():
            spec=replace(self.spec,task='T-1',attempt_id='attempt-id',contract_hash=accepted,allow_steering=True,
                         environment=tuple(dict(self.env,FAKE_BEHAVIOR='wait').items()))
            runtime=pi_rpc.PiRpcRuntime(spec); task=asyncio.create_task(runtime.execute())
            try:
                for _ in range(100):
                    if runtime.progress()['active_tool_count']: break
                    await asyncio.sleep(.01)
                request=dict(kind='steer',action='reconcile',task='T-1',attempt_id='attempt-id',
                             contract_hash=accepted,fingerprint='b'*64,generation=runtime.generation)
                receipt=await runtime.control(request)
                self.assertEqual(receipt['disposition'],'queued')
                with self.assertRaises(ValueError): await runtime.control(request)
                with self.assertRaises(ValueError): await runtime.control(dict(request,message='skip review'))
                task_path=self.root/'tasks/items/T-1.md'
                task_path.write_text(task_store.edit(task_path.read_text(),{'scope':'changed scope'}))
                with self.assertRaisesRegex(ValueError,'canonical contract'):
                    await runtime.control(dict(request,fingerprint='d'*64))
                subprocess.run(['git','-C',str(self.root),'add','tasks'],check=True)
                subprocess.run(['git','-C',str(self.root),'-c','user.name=Fixture',
                                '-c','user.email=fixture@example.invalid','commit','-qm','change scope'],check=True)
                with self.assertRaisesRegex(ValueError,'canonical contract'):
                    await runtime.control(dict(request,fingerprint='e'*64))
                engine.execution.save(contract,{'contract_hash':'c'*64})
                with self.assertRaisesRegex(ValueError,'engine attempt'):
                    await runtime.control(dict(request,fingerprint='f'*64))
            finally:
                await runtime.abort(); await task
        asyncio.run(scenario())

    def test_same_session_concurrent_owner_is_refused(self):
        async def scenario():
            spec=replace(self.spec,environment=tuple(dict(self.env,FAKE_BEHAVIOR='wait').items()))
            first=pi_rpc.PiRpcRuntime(spec); task=asyncio.create_task(first.execute())
            for _ in range(100):
                if first.progress()['active_tool_count']: break
                await asyncio.sleep(.01)
            second=await pi_rpc.PiRpcRuntime(spec).execute()
            self.assertEqual(second['failure_kind'],'session_busy')
            await first.abort(); await task
        asyncio.run(scenario())


if __name__=='__main__': unittest.main()
