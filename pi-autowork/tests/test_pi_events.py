"""Offline behavior tests for the bounded Pi 1.4 session-event projection."""
import json
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.pi_events import EventProjection, ProjectionOverflow


def usage(tokens, **extra):
    return dict(totalTokens=tokens, input=tokens - 1, output=1, **extra)


def assistant(tokens=7, text='done', **extra):
    return dict(type='message_end', message=dict(
        role='assistant', content=[dict(type='text', text=text)],
        stopReason='stop', usage=usage(tokens), **extra))


def settle(projection):
    projection.consume(dict(type='agent_settled', aborted=False))
    return projection.outcome()


class ProjectionTests(unittest.TestCase):
    def test_agent_end_is_not_terminal_and_continuations_replace_final_text(self):
        p = EventProjection()
        p.consume(dict(type='agent_start'))
        p.consume(assistant(text='first'))
        p.consume(dict(type='agent_end', messages=[assistant()['message']]))
        self.assertFalse(p.outcome()['settled'])
        self.assertEqual(p.progress()['phase'], 'continuing')
        p.consume(dict(type='agent_start'))
        p.consume(assistant(text='final'))
        self.assertEqual(settle(p)['text'], 'final')
        self.assertEqual(p.outcome()['tokens'], 14)

    def test_only_authoritative_surfaces_bill_7_plus_5_plus_11_once(self):
        p = EventProjection()
        p.consume(dict(type='message_update', usage=usage(700),
                       assistantMessageEvent=dict(type='text_delta', delta='not final')))
        p.consume(assistant())
        tool = dict(role='toolResult', toolCallId='one', usage=usage(5), content=[])
        p.consume(dict(type='tool_execution_start', toolCallId='one', toolName='bash'))
        p.consume(dict(type='tool_execution_end', toolCallId='one', result=tool, durationMs=20))
        p.consume(dict(type='message_end', message=tool))
        p.consume(dict(type='turn_end', message=assistant()['message'], toolResults=[tool]))
        p.consume(dict(type='agent_end', messages=[assistant()['message'], tool]))
        p.consume(dict(type='compaction_start', reason='threshold'))
        p.consume(dict(type='compaction_end', result=dict(usage=usage(11), summary='private')))
        result = settle(p)
        self.assertEqual((result['tokens'], result['input_tokens'], result['output_tokens']), (23, 20, 3))
        self.assertEqual(result['usage_coverage']['surfaces'], dict(assistant=1, tool=1, compaction=1))
        self.assertTrue(result['usage_coverage']['tokens_complete'])
        self.assertIsNone(result['cost'])  # catalog prices are not a bill
        self.assertEqual(result['text'], 'done')

    def test_missing_optional_usage_is_unknown_not_zero(self):
        for event in (dict(type='message_end', message=dict(role='assistant')),
                      dict(type='message_end', message=dict(role='toolResult', toolCallId='x')),
                      dict(type='compaction_end', result={})):
            with self.subTest(event=event):
                p = EventProjection()
                p.consume(assistant())
                p.consume(event)
                result = settle(p)
                self.assertIsNone(result['tokens'])
                self.assertFalse(result['usage_coverage']['tokens_complete'])
                self.assertEqual(result['usage_coverage']['missing'], 1)

    def test_partial_stream_never_uses_streaming_usage_as_final(self):
        p = EventProjection()
        p.consume(dict(type='message_start', message=dict(role='assistant')))
        p.consume(dict(type='message_update', usage=usage(100), assistantMessageEvent={}))
        self.assertIsNone(p.outcome()['tokens'])
        self.assertEqual(p.outcome()['text'], '')
        p.consume(dict(type='message_end', message=dict(role='assistant', stopReason='error',
                       errorMessage='provider unavailable', content=[dict(type='text', text='partial')],
                       usage=usage(3))))
        result = settle(p)
        self.assertEqual((result['stop'], result['error'], result['text'], result['tokens']),
                         ('error', 'provider unavailable', 'partial', 3))

    def test_unfinished_work_prevents_complete_coverage_even_after_settlement(self):
        for event in (dict(type='message_start', message=dict(role='assistant')),
                      dict(type='tool_execution_start', toolCallId='x', toolName='bash'),
                      dict(type='compaction_start')):
            with self.subTest(event=event):
                p = EventProjection()
                p.consume(assistant())
                p.consume(event)
                self.assertIsNone(settle(p)['tokens'])

    def test_provider_money_partial_subscription_and_zero(self):
        for source, billing, cost, expected in (
                (None, 'api', 3, None), ('provider_reported', 'api', 0, 0),
                ('provider_reported', 'api', 3, 3), ('provider_reported', 'subscription', 3, None)):
            with self.subTest(source=source, billing=billing, cost=cost):
                p = EventProjection()
                event = assistant()
                event['message']['usage'].update(cost_source=source, billing=billing, cost=dict(total=cost))
                p.consume(event)
                result = settle(p)
                self.assertEqual(result['cost'], expected)
                self.assertEqual(result['measured_cost_usd'], expected or 0)
        p = EventProjection()
        for billing, amount in (('api', 3), ('subscription', 0)):
            event = assistant()
            event['message']['usage'].update(cost_source='provider_reported', billing=billing, cost=dict(total=amount))
            p.consume(event)
        result = settle(p)
        self.assertEqual((result['cost'], result['measured_cost_usd'], result['billing']), (None, 3, 'mixed'))
        self.assertEqual(result['cost_source'], 'provider_reported')

    def test_provider_costs_include_tool_and_compaction_but_not_duplicate_surfaces(self):
        p = EventProjection()
        billed = dict(cost_source='provider_reported', billing='api', cost=dict(total=2))
        message = assistant(responseId='response-1')
        message['message']['usage'].update(billed)
        tool = dict(role='toolResult', toolCallId='tool-1', usage=usage(5, **billed))
        p.consume(message)
        p.consume(message)
        p.consume(dict(type='message_end', message=tool))
        p.consume(dict(type='message_end', message=tool))
        p.consume(dict(type='tool_execution_end', toolCallId='tool-1', result=tool))
        p.consume(dict(type='compaction_end', result=dict(usage=usage(11, **billed))))
        result = settle(p)
        self.assertEqual((result['tokens'], result['cost'], result['measured_cost_usd']), (23, 6, 6))
        self.assertTrue(result['usage_coverage']['complete'])

    def test_explicit_zero_is_known_but_empty_or_failed_work_is_not(self):
        p = EventProjection()
        self.assertIsNone(settle(p)['tokens'])
        p = EventProjection()
        event = assistant()
        event['message']['usage'] = dict(input=0, output=0, totalTokens=0)
        p.consume(event)
        self.assertEqual(settle(p)['tokens'], 0)
        p = EventProjection()
        p.consume(assistant())
        p.consume(dict(type='compaction_start'))
        p.consume(dict(type='compaction_end', aborted=False, errorMessage='summary failed'))
        result = settle(p)
        self.assertIsNone(result['tokens'])
        self.assertEqual(result['error'], 'summary failed')
        p = EventProjection()
        p.consume(dict(type='agent_settled', aborted=True))
        self.assertTrue(p.outcome()['aborted'])

    def test_retry_and_compaction_phases_and_unreported_retry_usage(self):
        p = EventProjection()
        p.consume(dict(type='auto_retry_start', attempt=1))
        self.assertEqual(p.progress()['phase'], 'retrying')
        p.consume(dict(type='auto_retry_end', success=False, finalError='gave up'))
        self.assertEqual(p.outcome()['error'], 'gave up')
        p.consume(dict(type='compaction_start'))
        self.assertEqual(p.progress()['phase'], 'compacting')
        p.consume(dict(type='summarization_retry_scheduled', attempt=1))
        self.assertEqual(p.progress()['phase'], 'retrying')
        p.consume(dict(type='summarization_retry_attempt_start', source='compaction'))
        self.assertEqual(p.progress()['phase'], 'compacting')
        p.consume(dict(type='summarization_retry_finished'))
        p.consume(dict(type='compaction_end', result=dict(usage=usage(11)), willRetry=True))
        p.consume(assistant())
        result = settle(p)
        self.assertEqual((result['retries'], result['compactions']), (3, 1))
        self.assertIsNone(result['tokens'])  # failed summarization attempts have no usage surface
        self.assertEqual(result['usage_coverage']['unreported_retries'], 1)
        self.assertIsNone(result['error'])  # successful continuation replaces previous retry failure

    def test_monotonic_timing_and_private_progress(self):
        now = [10.0]
        p = EventProjection(clock=lambda: now[0])
        self.assertEqual(p.progress()['phase'], 'starting')
        now[0] = 12.0
        p.consume(dict(type='agent_start'))
        self.assertEqual(p.progress()['phase'], 'model')
        now[0] = 15.0
        p.consume(dict(type='tool_execution_start', toolCallId='one', toolName='bash', args=dict(secret='SECRET')))
        progress = p.progress()
        self.assertEqual((progress['phase'], progress['current_tool'], progress['tool_count'],
                          progress['active_tool_count'], progress['last_tool_at']), ('tool', 'bash', 1, 1, 15.0))
        now[0] = 18.0
        p.consume(dict(type='tool_execution_update', toolCallId='one', partialResult=dict(secret='SECRET')))
        p.consume(dict(type='tool_execution_end', toolCallId='one', durationMs=2500, result=dict(secret='SECRET')))
        p.consume(dict(type='tool_execution_end', toolCallId='one', durationMs=2500))
        self.assertEqual(p.progress()['phase'], 'model')
        result = settle(p)
        self.assertEqual((result['startup_seconds'], result['first_tool_seconds'], result['tool_seconds']), (2, 5, 2.5))
        self.assertNotIn('SECRET', json.dumps(p.progress()))
        self.assertNotIn('SECRET', repr(vars(p)))
        self.assertEqual(p.progress()['phase'], 'settled')

    def test_unicode_text_blocks_only_and_returned_dicts_are_detached(self):
        p = EventProjection()
        event = assistant(text='hello\u2028世界\u2029🙂')
        event['message']['content'] += [dict(type='thinking', thinking='SECRET'),
                                       dict(type='text', text='next'), dict(type='toolCall', arguments={'secret': 'SECRET'})]
        p.consume(event)
        event['message']['content'][0]['text'] = 'mutated'
        result = settle(p)
        self.assertEqual(result['text'], 'hello\u2028世界\u2029🙂\nnext')
        result['usage_coverage']['surfaces']['assistant'] = 100
        self.assertEqual(p.outcome()['usage_coverage']['surfaces']['assistant'], 1)
        self.assertNotIn('SECRET', repr(vars(p)))

    def test_unknown_and_malformed_events_are_safe_and_bounded(self):
        p = EventProjection()
        for i in range(10000):
            p.consume(dict(type=f'future_{i}', secret='SECRET'))
        for raw in ({}, {'type': []}, {'type': 'message_end', 'message': []},
                    {'type': 'message_update', 'assistantMessageEvent': None}):
            p.consume(raw)
        p.consume(assistant())
        result = settle(p)
        self.assertEqual(result['unknown_events'], 10002)
        self.assertIsNone(result['tokens'])
        self.assertNotIn('future_9999', repr(vars(p)))
        self.assertNotIn('SECRET', repr(vars(p)))

    def test_invalid_numbers_are_not_zero_or_nonfinite_json(self):
        for value in (True, -1, float('nan'), float('inf'), '7', None):
            with self.subTest(value=value):
                p = EventProjection()
                event = assistant()
                event['message']['usage']['totalTokens'] = value
                p.consume(event)
                result = settle(p)
                self.assertIsNone(result['tokens'])
                json.dumps(result, allow_nan=False)

    def test_missing_duration_uses_observed_time_only_when_start_is_known(self):
        now = [0]
        p = EventProjection(clock=lambda: now[0])
        p.consume(dict(type='tool_execution_end', toolCallId='no-start'))
        self.assertIsNone(p.outcome()['tool_seconds'])
        p.consume(dict(type='tool_execution_start', toolCallId='started'))
        now[0] = 3
        p.consume(dict(type='tool_execution_end', toolCallId='started'))
        self.assertEqual(p.outcome()['tool_seconds'], 3)

    def test_oversize_error_response_identity_and_names_fail_closed(self):
        for event in (assistant(errorMessage='x' * 5000),
                      assistant(responseId='x' * 5000),
                      dict(type='tool_execution_start', toolCallId='one', toolName='x' * 5000)):
            with self.subTest(kind=event['type']):
                p = EventProjection()
                with self.assertRaises(ProjectionOverflow):
                    p.consume(event)
                self.assertEqual(p.progress()['phase'], 'overflow')
                with self.assertRaises(ProjectionOverflow):
                    p.consume(dict(type='agent_settled', aborted=False))

    def test_utf8_text_and_critical_state_overflow_fail_closed(self):
        p = EventProjection(max_text_bytes=4)
        p.consume(assistant(text='🙂'))
        with self.assertRaises(ProjectionOverflow):
            p.consume(assistant(text='🙂x'))
        with self.assertRaises(ProjectionOverflow):
            p.outcome()  # callers cannot accidentally accept the earlier final text
        p = EventProjection()
        with self.assertRaises(ProjectionOverflow):
            p.consume(dict(type='tool_execution_start', toolCallId='x' * 100000, toolName='bash'))
        p = EventProjection()
        with self.assertRaises(ProjectionOverflow):
            for i in range(10000):
                p.consume(dict(type='tool_execution_start', toolCallId=str(i), toolName='bash'))


if __name__ == '__main__':
    unittest.main()
