"""Real engine/Git/worker/reviewer over the SDK; fake Pi, never a model or service.

Reuses established task/report/check scenarios. The test-only RPC peer delegates
engineering actions to the JSON fixture; production does not implement RPC framing.
"""
import importlib.util
import json
import sys
import unittest
import test_pi_autowork as baseline

setUpModule=baseline.setUpModule
tearDownModule=baseline.tearDownModule

PEER=r'''#!/usr/bin/env python3
import json, os, re, subprocess, sys, tempfile
args=sys.argv[1:]
if '--version' in args: print('1.4.0'); sys.exit()
legacy=os.environ['FAKE_JSON_PI']
if '--mode' not in args: os.execv(sys.executable,[sys.executable,legacy,*args])
assert args[args.index('--mode')+1]=='rpc'
session=args[args.index('--session-id')+1]
def emit(value): print(json.dumps(value),flush=True)
def reply(req,data=None):
    out=dict(type='response',id=req['id'],command=req['type'],success=True)
    if data is not None: out['data']=data
    emit(out)
for line in sys.stdin:
    req=json.loads(line)
    if req['type']=='get_state':
        reply(req,dict(sessionId=session,isStreaming=False,isCompacting=False,pendingMessageCount=0))
    elif req['type']=='prompt':
        reply(req,{'disposition':'started'}); emit({'type':'agent_start'})
        message=req['message']
        cli=list(args); cli[cli.index('--mode')+1]='json'
        with tempfile.TemporaryDirectory() as root:
            if re.search(r'^Task: ',message,re.M):
                prompt=root+'/prompt.md'; open(prompt,'w').write(message)
                cli += ['@'+prompt]
            child=subprocess.Popen([sys.executable,legacy,*cli,'--',message],stdout=subprocess.PIPE,text=True)
            for event in child.stdout:
                value=json.loads(event)
                if value.get('type')=='session': continue
                if value.get('type')=='agent_settled': emit({'type':'agent_end','messages':[]})
                emit(value)
            if child.wait():
                emit({'type':'message_end','message':{'role':'assistant','stopReason':'error',
                      'content':[],'errorMessage':'fixture subprocess failed'}})
                emit({'type':'agent_settled','aborted':False})
    elif req['type']=='clear_queue': reply(req,{'steering':[],'followUp':[]})
    elif req['type']=='abort': reply(req)
'''


@unittest.skipUnless(importlib.util.find_spec('pi_agent'), 'pinned SDK interpreter required')
class RpcEngineTests(baseline.Fixture):
    def setUp(self):
        super().setUp()
        legacy=self.bin/'pi-json'; legacy.write_text(baseline.FAKE_PI); legacy.chmod(0o700)
        (self.bin/'pi').write_text(PEER)
        self.env.pop('PI_AUTOWORK_TRANSPORT',None)  # Exercise the actual new default.
        self.env.update(PI_AUTOWORK_RPC_PYTHON=sys.executable,FAKE_JSON_PI=str(legacy))

    def test_default_rpc_worker_independent_reviewer_and_verified_engine_close(self):
        baseline.EngineTests.test_once_runs_one_task(self)
        runs=[json.loads(line) for path in self.state.glob('*/runs.jsonl') for line in path.read_text().splitlines()]
        self.assertTrue(runs)
        self.assertTrue(all(row['transport']=='rpc' for row in runs))
        self.assertTrue(all(row['cleanup_complete'] for row in runs))
        workers={row['session_id'] for row in runs if row['role']=='worker'}
        reviewers={row['session_id'] for row in runs if row['role']=='verify'}
        self.assertTrue(workers and reviewers)
        self.assertFalse(workers & reviewers)

    def test_rpc_provider_fallback_preserves_existing_engine_attempt(self):
        baseline.EngineTests.test_provider_failure_falls_back_and_resumes_the_same_session(self)


if __name__=='__main__': unittest.main()
