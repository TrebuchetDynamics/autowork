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
from pi_autowork import pi_runtime as runtime  # noqa: E402

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
        self.env = {'PI_BIN': str(pi), 'PI_AUTOWORK_BACKOFF': '0', 'PI_AUTOWORK_MAX_RETRIES': '2',
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
                         ('finished', 'openai-codex', 7, 0.25))
        self.assertEqual(row['result'], 'PI_AUTOWORK_RESULT: completed with key [redacted]')
        self.assertEqual(list((self.state / 'runs').iterdir()), [])  # the raw stream is gone

    def test_a_provider_failure_cools_the_primary_and_the_fallback_finishes(self):
        self.set_plan(['rate_limit', 'finish'])
        result = self.job()
        self.assertTrue(result['ok'])
        self.assertEqual([c['provider'] for c in self.calls()], ['openai-codex', 'openrouter'])
        self.assertEqual([r['outcome'] for r in self.records()], ['provider_failure', 'finished'])
        self.assertNotIn('secret123', json.dumps(self.records()))
        self.assertTrue(runtime.primary_cooling(runtime.Settings(self.state)))
        self.assertIn('reconcile its partial work', self.calls()[1]['message'])

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
