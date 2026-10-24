"""One Pi job: model choice, fallback, retries, timeouts, budget and redacted records."""
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import accounting, pi_runtime as runtime  # noqa: E402

# A fake `pi`: `auth check` reads FAKE_UNAUTH; a run pops its behavior from FAKE_PLAN.
FAKE = r'''#!/usr/bin/env python3
import json, os, sys, time
args = sys.argv[1:]
if args[:2] == ['auth', 'check']:
    sys.exit(1 if args[args.index('--provider') + 1] in os.environ.get('FAKE_UNAUTH', '').split(',') else 0)
plan = json.load(open(os.environ['FAKE_PLAN']))
behavior = plan.pop(0) if plan else 'finish'
json.dump(plan, open(os.environ['FAKE_PLAN'], 'w'))
with open(os.environ['FAKE_LOG'], 'a') as log:
    log.write(json.dumps({'provider': args[args.index('--provider') + 1], 'message': args[-1]}) + '\n')
def end(stop='stop', text='done', error=None, settled=True):
    message = {'role': 'assistant', 'stopReason': stop, 'content': [{'type': 'text', 'text': text}],
               'usage': {'totalTokens': 7, 'cost': {'total': 0.25}}}
    if error:
        message['errorMessage'] = error
    print(json.dumps({'type': 'message_end', 'message': message}))
    if settled:
        print(json.dumps({'type': 'agent_settled', 'aborted': False}))
if behavior == 'finish':
    end(text='work\nPI_AUTOWORK_RESULT: completed with key sk-abcdefghijkl')
elif behavior == 'rate_limit':
    end(stop='error', error='429 rate limit exceeded (sk-secret123456789)')
elif behavior == 'crash':
    end(settled=False)
elif behavior == 'hang':
    time.sleep(30)
elif behavior == 'overflow':
    end(text='before overflow', settled=False)
    end(text='x' * 262145)
'''


class RuntimeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.state = root / 'state'
        (self.state / 'runs').mkdir(parents=True)
        pi = root / 'pi'
        pi.write_text(FAKE)
        pi.chmod(pi.stat().st_mode | stat.S_IEXEC)
        self.plan, self.log = root / 'plan.json', root / 'log.jsonl'
        self.env = {'PI_AUTOWORK_TRANSPORT': 'json', 'PI_BIN': str(pi), 'PI_AUTOWORK_BACKOFF': '0', 'PI_AUTOWORK_MAX_RETRIES': '2',
                    'PI_AUTOWORK_PRIMARY': 'openai-codex/gpt-6.1-sol',
                    'PI_AUTOWORK_FALLBACK': 'openrouter/deepseek/deepseek-v4.1-flash',
                    'FAKE_PLAN': str(self.plan), 'FAKE_LOG': str(self.log)}
        self.patch = dict(os.environ)
        os.environ.update(self.env)
        self.addCleanup(lambda: (os.environ.clear(), os.environ.update(self.patch)))
        self.set_plan([])

    def set_plan(self, plan):
        self.plan.write_text(json.dumps(plan))

    def job(self, limit=60, **env):
        os.environ.update(env)
        return runtime.job(runtime.Settings(self.state), 'worker', 'T-1', self.temp.name, 'do it', 's1', limit, [])

    def records(self):
        return [json.loads(line) for line in (self.state / 'runs.jsonl').read_text().splitlines()]

    def calls(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()] if self.log.exists() else []

    def test_a_finished_run_is_recorded_once_with_secrets_redacted(self):
        result = self.job()
        self.assertTrue(result['ok'])
        self.assertIn('PI_AUTOWORK_RESULT: completed', result['text'])
        (row,) = self.records()
        self.assertEqual((row['outcome'], row['provider'], row['tokens'], row['cost_usd']),
                         ('finished', 'openai-codex', 7, None))
        self.assertEqual(row['cost_source'], 'missing')
        self.assertTrue(row['run_id'])
        self.assertEqual(row['host'], 'pi')
        self.assertEqual(row['result'], 'PI_AUTOWORK_RESULT: completed with key [redacted]')
        self.assertEqual(list((self.state / 'runs').iterdir()), [])  # the raw stream is gone

    def test_a_provider_failure_cools_the_primary_and_the_fallback_finishes(self):
        import subprocess
        from pi_autowork import telemetry
        root = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(root)], check=True)
        engine = telemetry.engine()
        common = engine.common_dir(root)
        engine.execution.save(engine.slot_path(common, 'T-1'), dict(
            task_id='T-1', state='running', attempt=1, attempt_id='fixture', host='pi', model='unknown'))
        self.set_plan(['rate_limit', 'finish'])
        result = self.job()
        self.assertTrue(result['ok'])
        self.assertEqual([c['provider'] for c in self.calls()], ['openai-codex', 'openrouter'])
        self.assertEqual([r['outcome'] for r in self.records()], ['provider_failure', 'finished'])
        self.assertEqual({r['attempt_id'] for r in self.records()}, {'fixture'})
        self.assertNotIn('secret123', json.dumps(self.records()))
        self.assertTrue(runtime.primary_cooling(runtime.Settings(self.state)))
        self.assertIn('reconcile its partial work', self.calls()[1]['message'])
        events = engine.lifecycle_events(common)['events']
        self.assertEqual([e['event'] for e in events],
                         ['model_selected', 'model_retry', 'model_selected', 'model_finished'])
        self.assertEqual(events[-1]['model'], 'openrouter/deepseek/deepseek-v4.1-flash')
        self.assertEqual({e['attempt_id'] for e in events}, {'fixture'})
        self.assertNotIn('secret123', json.dumps(events))

    def test_crashes_are_retried_then_given_up(self):
        self.set_plan(['crash', 'crash', 'crash'])
        result = self.job(PI_AUTOWORK_NO_FALLBACK='1')
        self.assertFalse(result['ok'])
        self.assertEqual([r['outcome'] for r in self.records()], ['crash_failure'] * 3)  # 1 + 2 retries

    def test_a_timeout_is_recorded_and_not_retried(self):
        self.set_plan(['hang'])
        started = time.monotonic()
        result = self.job(limit=1)
        self.assertFalse(result['ok'])
        self.assertLess(time.monotonic() - started, 20)
        self.assertEqual([r['outcome'] for r in self.records()], ['timeout'])

    def test_invocation_usage_counts_assistant_tool_and_compaction_once(self):
        assistant = dict(role='assistant', responseId='response-1', stopReason='stop',
                         content=[dict(type='text', text='done')],
                         usage=dict(totalTokens=7, input=6, output=1))
        tool = dict(role='toolResult', toolCallId='tool-1', content=[],
                    usage=dict(totalTokens=5, input=4, output=1))
        events = [dict(type='session', id='resumed-session'),
                  # Prior context/session totals are not invocation usage.
                  dict(type='response', command='get_messages', data=dict(messages=[
                      dict(role='assistant', usage=dict(totalTokens=900))])),
                  dict(type='response', command='get_session_stats', data=dict(tokens=dict(total=900))),
                  dict(type='message_update', usage=dict(totalTokens=700)),
                  dict(type='message_end', message=assistant),
                  dict(type='message_end', message=assistant),
                  dict(type='tool_execution_end', toolCallId='tool-1', result=tool),
                  dict(type='message_end', message=tool), dict(type='message_end', message=tool),
                  dict(type='turn_end', message=assistant, toolResults=[tool]),
                  dict(type='compaction_end', result=dict(usage=dict(totalTokens=11, input=10, output=1))),
                  dict(type='agent_end', messages=[assistant, tool]), dict(type='agent_settled')]
        run = runtime.analyse('\n'.join(map(json.dumps, events)))
        self.assertEqual((run['tokens'], run['input_tokens'], run['output_tokens']), (23, 20, 3))
        self.assertEqual(run['text'], 'done')
        self.assertTrue(run['usage_coverage']['tokens_complete'])
        runtime.record(runtime.Settings(self.state), 'worker', 'T-1', 'finished', 'p/m', '', run)
        (row,) = self.records()
        self.assertEqual((row['task'], row['role'], row['known_usage']['totalTokens']), ('T-1', 'worker', 23))

    def test_missing_or_interrupted_usage_retains_only_known_subtotals(self):
        for omitted in (dict(type='message_end', message=dict(role='toolResult', toolCallId='x')),
                        dict(type='compaction_end', result={}),
                        dict(type='summarization_retry_scheduled'),
                        dict(type='entry_appended', entry=None),
                        dict(type='entry_appended', entry={}),
                        dict(type='entry_appended', entry=dict(type='usage', id='entry')),
                        dict(type='entry_appended', entry=dict(type='future_usage')),
                        dict(type='message_start', message=dict(role='assistant'))):
            with self.subTest(omitted=omitted):
                events = [dict(type='message_end', message=dict(role='assistant', usage=dict(totalTokens=7))),
                          omitted, dict(type='agent_settled')]
                run = runtime.analyse('\n'.join(map(json.dumps, events)))
                self.assertIsNone(run['tokens'])
                self.assertEqual(run['known_usage']['totalTokens'], 7)
                self.assertFalse(run['usage_coverage']['tokens_complete'])

    def test_native_usage_entries_and_boundary_compactions_are_independent(self):
        for entry_type in ('usage', 'compaction'):
            with self.subTest(entry_type=entry_type):
                entry = dict(type=entry_type, id='entry-1', kind='cache_warm',
                             usage=dict(totalTokens=13, input=12, output=1))
                events = [dict(type='message_end', message=dict(role='assistant', usage=dict(totalTokens=7))),
                          dict(type='entry_appended', entry=entry), dict(type='entry_appended', entry=entry),
                          dict(type='entry_appended', entry=dict(type='custom', id='state', data=entry)),
                          dict(type='agent_settled')]
                run = runtime.analyse('\n'.join(map(json.dumps, events)))
                self.assertEqual(run['tokens'], 20)
                self.assertEqual(run['compactions'], int(entry_type == 'compaction'))
                self.assertIsNone(run['cost'])

    def test_projection_overflow_is_a_recorded_terminal_failure(self):
        self.set_plan(['overflow'])
        result = self.job()
        self.assertFalse(result['ok'])
        self.assertEqual(result['why'], 'projection_overflow')
        (row,) = self.records()
        self.assertEqual((row['task'], row['role'], row['outcome']), ('T-1', 'worker', 'projection_overflow'))
        self.assertIsNone(row['tokens'])
        self.assertTrue(row['usage_coverage']['overflow'])
        self.assertEqual(row['known_usage']['totalTokens'], 7)
        self.assertEqual(list((self.state / 'runs').iterdir()), [])

    def test_offline_replay_does_not_invent_execution_timings(self):
        events = [dict(type='agent_start'),
                  dict(type='tool_execution_start', toolCallId='x'),
                  dict(type='tool_execution_end', toolCallId='x'),
                  dict(type='agent_settled')]
        for duration, expected in ((None, None), (2500, 2.5)):
            with self.subTest(duration=duration):
                events[2]['durationMs'] = duration
                run = runtime.analyse('\n'.join(map(json.dumps, events)))
                self.assertIsNone(run['startup_seconds'])
                self.assertIsNone(run['first_tool_seconds'])
                self.assertEqual(run['tool_seconds'], expected)

    def test_usage_preserves_tokens_but_never_prices_missing_or_subscription_billing(self):
        for surface in ('assistant', 'toolResult', 'compaction'):
            for billing, source, cost, expected in (
                    ('api', None, 0.25, None), ('api', 'provider_reported', 0.25, 0.25),
                    ('api', 'provider_reported', 0, 0),
                    ('subscription', 'provider_reported', 0.25, None), ('api', None, None, None)):
                with self.subTest(surface=surface, billing=billing, source=source, cost=cost):
                    usage = dict(input=10, output=3, totalTokens=15, cacheRead=2, billing=billing,
                                 cost={'total': cost}, cost_source=source)
                    event = (dict(type='compaction_end', result=dict(usage=usage)) if surface == 'compaction'
                             else dict(type='message_end', message=dict(role=surface, toolCallId='x', usage=usage)))
                    run = runtime.analyse('\n'.join(map(json.dumps, [event, dict(type='agent_settled')])))
                    self.assertEqual((run['input_tokens'], run['output_tokens'], run['tokens']), (10, 3, 15))
                    self.assertEqual(run['cost'], expected)
                    self.assertEqual(run['measured_cost_usd'], expected)
        # A mixed run is still unknown overall, but its billed API subset must survive.
        messages = [dict(input=1, output=2, totalTokens=3, cost={'total': amount},
                         cost_source='provider_reported', billing=billing)
                    for amount, billing in ((3, 'api'), (0, 'subscription'))]
        events = [dict(type='message_end', message=dict(role=role, toolCallId='x', usage=usage))
                  for role, usage in zip(('assistant', 'toolResult'), messages)]
        events += [dict(type='compaction_end', result=dict(usage=dict(totalTokens=11, input=10, output=1))),
                   dict(type='agent_settled')]
        run = runtime.analyse('\n'.join(map(json.dumps, events)))
        runtime.record(runtime.Settings(self.state), 'merge', 'T-1', 'finished', 'p/m', '', run)
        (row,) = self.records()
        self.assertEqual(row['task'], 'T-1')
        total = accounting.bucket()
        accounting.add(total, row)
        self.assertIsNone(total['cost_usd'])
        self.assertEqual(total['measured_cost_usd'], 3)
        self.assertEqual((total['input_tokens'], total['output_tokens']), (12, 5))

    def test_model_choice_and_the_budget(self):
        settings = runtime.Settings(self.state)
        self.assertEqual(runtime.choose(settings), ('openai-codex/gpt-6.1-sol', ''))
        os.environ['FAKE_UNAUTH'] = 'openai-codex'
        self.assertEqual(runtime.choose(settings), ('openrouter/deepseek/deepseek-v4.1-flash', 'primary not authenticated'))
        os.environ['FAKE_UNAUTH'] = 'openai-codex,openrouter'
        self.assertEqual(runtime.choose(settings)[0], None)
        os.environ['FAKE_UNAUTH'] = ''
        (self.state / 'provider.json').unlink()
        self.job()  # costs 0.25: recorded, never a limit
        self.assertTrue(self.job()['ok'])
        self.assertEqual(len(self.calls()), 2)


if __name__ == '__main__':
    unittest.main()
