"""Actual subprocess/pipe tests, never launch Pi or contact a provider."""
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import time
import unittest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.planning_rpc import RPC, RPCError, Cancelled

FAKE = r'''#!/usr/bin/env python3
import json, os, signal, sys, time
from pathlib import Path
mode = Path(__file__).stem
if '--version' in sys.argv:
    print('1.2.0' if mode == 'old_version' else '1.4.0')
    sys.exit(0)
if mode == 'hung':
    signal.signal(signal.SIGTERM, signal.SIG_IGN)
log = Path(__file__).with_suffix('.log')
with log.open('a') as out:
    out.write(json.dumps({'argv':sys.argv}) + '\n')

def emit(value):
    sys.stdout.buffer.write(json.dumps(value, ensure_ascii=False).encode() + b'\n')
    sys.stdout.buffer.flush()

for line in sys.stdin.buffer:
    cmd = json.loads(line)
    with log.open('a') as out:
        out.write(json.dumps(cmd) + '\n')
    name = cmd['type']
    data = {}
    if name == 'get_commands':
        data = {'commands': [] if mode == 'missing_commands' else [{'name': 'skill:plan-for-me', 'source': 'skill'}]}
    if name == 'get_state':
        data = {'isStreaming': False, 'sessionId': sys.argv[sys.argv.index('--session-id') + 1] if '--session-id' in sys.argv else 'test'}
    if name == 'steer':
        data = {'disposition': 'queued'}
    if name == 'prompt':
        if mode == 'eof':
            sys.exit(0)
        if mode == 'wrong_id':
            emit({'type':'response', 'id':'wrong', 'command':name, 'success':True})
            continue
        sys.stderr.write('private sk-not-for-stdout-test\n' * 20000)
        sys.stderr.flush()
        data = {'disposition': 'handled' if mode == 'handled' else 'queued' if mode == 'queued' else 'started'}
        if mode == 'early':
            emit({'type':'message_end', 'message': {'role':'assistant', 'content':[{'type':'text','text':'before response'}], 'stopReason':'stop'}})
            emit({'type':'agent_settled', 'aborted':False})
    emit({'type':'response', 'id':cmd['id'], 'command':name, 'success':True, 'data':data})
    if name == 'prompt' and mode == 'hung':
        time.sleep(30)
    if name == 'prompt' and mode not in ('handled', 'early', 'wait'):
        text = 'one\u2028two\u2029three'
        if mode == 'planner':
            text = 'A proposed plan.\n```autowork-plan\n' + json.dumps({'files': {'docs/plans/proposed.md': '# Proposed\n'}}) + '\n```'
        emit({'type':'message_update', 'assistantMessageEvent':{'type':'text_delta','delta':text}})
        emit({'type':'agent_end', 'messages':[]})
        if mode == 'agent_end':
            sys.exit(0)
        emit({'type':'message_end', 'message':{'role':'assistant','content':[{'type':'text','text':text}], 'stopReason':'error' if mode == 'error' else 'stop', 'errorMessage':'private-token' if mode == 'error' else ''}})
        emit({'type':'agent_settled', 'aborted':False})
    if name == 'abort':
        emit({'type':'agent_settled', 'aborted':True})
'''


class RPCTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)

    def client(self, mode, cancel=None, events=None):
        script = self.root / mode
        script.write_text(FAKE)
        script.chmod(0o700)
        client = RPC([str(script)], self.root, self.root / ('private-' + mode),
                     cancel=cancel, on_event=events.append if events is not None else None,
                     command_timeout=.5, run_timeout=3, shutdown_timeout=.2)
        self.addCleanup(client.close)
        return client

    def test_lf_framing_streaming_and_stderr_drain(self):
        events = []
        client = self.client('normal', events=events)
        self.assertEqual(client.request('get_commands')['commands'][0]['name'], 'skill:plan-for-me')
        result = client.turn('literal chat')
        self.assertEqual(result['text'], 'one\u2028two\u2029three')
        self.assertTrue(any(e['type'] == 'message_update' for e in events))
        client.close()
        self.assertIsNotNone(client.process.poll())
        self.assertEqual((self.root / 'private-normal').stat().st_mode & 0o777, 0o700)

    def test_dispositions_and_events_before_prompt_response(self):
        self.assertEqual(self.client('handled').turn('x')['status'], 'handled')
        self.assertEqual(self.client('queued').turn('x')['status'], 'ready')
        self.assertEqual(self.client('early').turn('x')['text'], 'before response')

    def test_eof_provider_error_and_agent_end_are_not_success(self):
        for mode in ('eof', 'error', 'agent_end', 'wrong_id'):
            with self.subTest(mode=mode), self.assertRaises(RPCError):
                self.client(mode).turn('x')

    def test_deadline_and_kill_escalation_are_bounded(self):
        client = self.client('hung')
        client.run_timeout = .15
        start = time.monotonic()
        with self.assertRaisesRegex(RPCError, 'deadline'):
            client.turn('wait forever')
        client.close(abort=True)
        self.assertLess(time.monotonic() - start, 3)
        self.assertIsNotNone(client.process.poll())
        self.assertFalse(client.reader.is_alive())
        self.assertFalse(client.stderr_reader.is_alive())

    def test_abort_response_is_correlated_during_shutdown(self):
        client = self.client('wait')
        client.request('get_state')
        client.close(abort=True)
        self.assertNotEqual(client.failure, 'uncorrelated Pi RPC response')
        records = [json.loads(line) for line in (self.root / 'wait.log').read_text().splitlines()]
        self.assertIn('abort', [r.get('type') for r in records])

    def test_cancellation_and_steering_same_process(self):
        cancel = threading.Event()
        client = self.client('wait', cancel=cancel)
        outcome = []
        def turn():
            try:
                client.turn('wait')
            except Cancelled:
                outcome.append('cancelled')
            finally:
                client.close()
        thread = threading.Thread(target=turn)
        thread.start()
        time.sleep(.15)
        self.assertEqual(client.request('steer', message='Literal user message:\n/ignore'), {'disposition': 'queued'})
        cancel.set()
        thread.join(5)
        self.assertFalse(thread.is_alive())
        self.assertEqual(outcome, ['cancelled'])
        self.assertIsNotNone(client.process.poll())


if __name__ == '__main__':
    unittest.main()
