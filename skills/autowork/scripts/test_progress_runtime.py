"""Private request lifecycle and bounded continuation tests; no live profiles."""
import json
from pathlib import Path
import tempfile
import unittest

class ProgressRuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.state = self.root/'sender'
        self.owner = self.root/'owner'
        self.state.mkdir(); self.owner.mkdir()
        self.request = {'version':1,'request_id':'request-1','owner':'integration',
                        'consumer':str(self.root/'repo'),'plan':'SPEC.md#slice',
                        'task_ids':['T1'],'status':'pending','required_inputs':['accepted source']}

    def test_route_is_idempotent_and_not_acknowledgement(self):
        import progress_runtime as runtime
        first = runtime.route(self.request, self.owner)
        second = runtime.route(self.request, self.owner)
        self.assertEqual(first,second)
        self.assertEqual(first['state'],'delivered')
        self.assertEqual(len(list((self.owner/'inbox').glob('*.json'))),1)
        self.assertEqual(self.request['status'],'pending')

    def test_reply_requires_matching_request_and_owner(self):
        import progress_runtime as runtime
        delivery=runtime.route(self.request,self.owner)
        path=Path(delivery['reply_path'])
        path.parent.mkdir(exist_ok=True)
        reply={'request_id':'request-1','owner':'someone-else','status':'acknowledged','evidence':'actual reply'}
        path.write_text(json.dumps(reply))
        with self.assertRaises(ValueError): runtime.read_reply(self.request,delivery)
        reply['owner']='integration';path.write_text(json.dumps(reply))
        self.assertEqual(runtime.read_reply(self.request,delivery)['status'],'acknowledged')

    def test_same_profile_reply_must_bind_the_designated_owner_session(self):
        import progress_runtime as runtime
        self.request['target_session']='parent-session'
        delivery=runtime.route(self.request,self.owner)
        path=Path(delivery['reply_path']);path.parent.mkdir(exist_ok=True)
        reply={'request_id':'request-1','owner':'integration','status':'blocked','evidence':'cron inspected state'}
        for session in (None,'cron-session'):
            if session is not None:reply['session_id']=session
            path.write_text(json.dumps(reply))
            with self.assertRaises(ValueError):runtime.read_reply(self.request,delivery)
        reply['session_id']='parent-session';path.write_text(json.dumps(reply))
        self.assertEqual(runtime.read_reply(self.request,delivery)['status'],'blocked')
        self.assertEqual(delivery['session_wakeup'],'not_attempted')

    def test_route_cannot_retarget_an_existing_request_to_a_different_session(self):
        import progress_runtime as runtime
        self.request['target_session']='parent-session'
        runtime.route(self.request,self.owner)
        with self.assertRaises(ValueError):runtime.route(dict(self.request,target_session='other-session'),self.owner)

    def test_reply_cli_rejects_sibling_session_without_writing_outbox(self):
        import progress_runtime as runtime
        from contextlib import redirect_stderr
        import io
        self.request['target_session']='parent-session'
        delivery=runtime.route(self.request,self.owner)
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            runtime.main(['reply','--state-dir',str(self.owner),'--request-id','request-1',
                          '--owner','integration','--status','blocked','--evidence','fixture://cron',
                          '--session-id','cron-session'])
        self.assertFalse(Path(delivery['reply_path']).exists())

    def test_resolution_claim_is_not_consumer_readiness(self):
        import progress_runtime as runtime
        delivery=runtime.route(self.request,self.owner)
        path=Path(delivery['reply_path']);path.parent.mkdir(exist_ok=True)
        path.write_text(json.dumps({'request_id':'request-1','owner':'integration',
                                   'status':'resolved','evidence':'commit abc'}))
        reply=runtime.read_reply(self.request,delivery)
        self.assertEqual(reply['status'],'resolution_reported')

    def test_route_refuses_symlink_and_unknown_owner(self):
        import progress_runtime as runtime
        alias=self.root/'alias';alias.symlink_to(self.owner,target_is_directory=True)
        with self.assertRaises(ValueError): runtime.route(self.request,alias)
        self.request['owner']='unassigned'
        with self.assertRaises(ValueError): runtime.route(self.request,self.owner)

    def test_inbox_conflict_does_not_overwrite(self):
        import progress_runtime as runtime
        delivery=runtime.route(self.request,self.owner)
        changed=dict(self.request,consumer='/different/repo')
        with self.assertRaises(ValueError): runtime.route(changed,self.owner)
        self.assertEqual(json.loads(Path(delivery['inbox_path']).read_text())['consumer'],self.request['consumer'])

    def test_owner_cli_records_reply_with_evidence(self):
        import progress_runtime as runtime
        from contextlib import redirect_stdout
        import io
        delivery=runtime.route(self.request,self.owner)
        with redirect_stdout(io.StringIO()):
            code=runtime.main(['reply','--state-dir',str(self.owner),'--request-id','request-1',
                               '--owner','integration','--status','acknowledged',
                               '--evidence','fixture://owner-run'])
        self.assertEqual(code,0)
        self.assertEqual(runtime.read_reply(self.request,delivery)['evidence'],'fixture://owner-run')

if __name__=='__main__': unittest.main()
