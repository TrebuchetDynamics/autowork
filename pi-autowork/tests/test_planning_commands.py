"""Planning CLI and read models: no live services, models or Textual dependency."""
import argparse
from unittest.mock import patch
import threading
from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class PlannerStub:
    def __init__(self, *args, **kwargs):
        self.calls = []
    def create(self, **kwargs):
        self.calls.append(('create', kwargs))
        return {'id': 'session-1'}
    def send(self, sid, message='', **kwargs):
        self.calls.append(('send', sid, message))
        return {'status': 'ready', 'text': 'Plan proposed.'}
    def preview(self, sid):
        return {'id': sid, 'revision': 'abc123', 'diff': '+ plan', 'files': ['docs/plans/p.md'],
                'valid': True, 'errors': []}
    def apply(self, sid, revision):
        self.calls.append(('apply', sid, revision))
        return {'commit': 'cafe'}
    def sessions(self):
        return [{'id': 'session-1', 'status': 'ready', 'objective': 'Quality'}]
    def history(self, sid):
        return [{'role': 'assistant', 'content': 'History kept'}]
    def roadmap(self, sid=None):
        return {'revision': 'HEAD', 'goals': [], 'tasks': [], 'errors': []}


class PlanningCommandTests(unittest.TestCase):
    def args(self, *argv):
        from pi_autowork import planning_commands
        parser = argparse.ArgumentParser()
        planning_commands.add_parser(parser.add_subparsers(dest='command'))
        return parser.parse_args(['plan', *argv])

    def invoke(self, *argv):
        from pi_autowork import planning_commands
        planner = PlannerStub()
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = planning_commands.run(self.args(*argv), '/repo', '/state',
                                          planner_factory=lambda *a, **k: planner)
        return code, out.getvalue(), err.getvalue(), planner.calls

    def test_bare_objective_starts_autonomous_plan(self):
        code, out, err, calls = self.invoke('/repo', '--json')
        self.assertEqual(code, 0, err)
        self.assertEqual(calls[0], ('create', {'objective': '', 'task': None, 'mode': 'plan'}))
        self.assertEqual(calls[1], ('send', 'session-1', ''))
        self.assertIn('session-1', out)

    def test_resume_does_not_create_a_second_session(self):
        code, out, err, calls = self.invoke('/repo', '--session', 'old', '--message', '/do not execute this', '--json')
        self.assertEqual(code, 0, err)
        self.assertEqual(calls, [('send', 'old', '/do not execute this')])

    def test_review_apply_and_history_do_not_prompt_model(self):
        for flag, extra, expected in [('--preview', [], []), ('--history', [], []),
                                      ('--apply', ['abc123'], [('apply', 'old', 'abc123')])]:
            with self.subTest(flag=flag):
                code, out, err, calls = self.invoke('/repo', '--session', 'old', flag, *extra, '--json')
                self.assertEqual(code, 0, err)
                self.assertEqual(calls, expected)
                self.assertTrue(out)

    def test_apply_without_session_refuses_before_any_mutation(self):
        code, out, err, calls = self.invoke('--apply', 'abc123')
        self.assertEqual(code, 1)
        self.assertIn('--session', err)
        self.assertEqual(calls, [])

    def test_empty_apply_revision_never_falls_through_to_model(self):
        for extra in ([], ['--session', 'old']):
            code, out, err, calls = self.invoke('--apply', '', *extra)
            self.assertEqual(code, 1)
            self.assertEqual(calls, [])

    def test_task_investigation_retains_scope(self):
        code, out, err, calls = self.invoke('--task', 'T-1', '--mode', 'investigate', '--objective', 'Why stalled?')
        self.assertEqual(code, 0, err)
        self.assertEqual(calls[0][1]['task'], 'T-1')
        self.assertEqual(calls[0][1]['mode'], 'investigate')

    def test_interactive_cli_can_steer_and_cancel_live_turn(self):
        from pi_autowork import planning_commands
        started = threading.Event()
        class LivePlanner(PlannerStub):
            def send(self, sid, message='', on_event=None, cancel=None):
                started.set()
                cancel.wait(3)
                self.calls.append(('cancelled', cancel.is_set()))
                return {'status': 'cancelled', 'text': 'cancelled'}
            def steer(self, sid, message):
                self.calls.append(('steer', sid, message))
                return {'disposition': 'queued'}
        planner = LivePlanner()
        replies = iter(['/steer Prefer option B', '/cancel', '/quit'])
        def answer(prompt):
            self.assertTrue(started.wait(2))
            return next(replies)
        with patch('builtins.input', side_effect=answer), redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            code = planning_commands._chat(planner, 'old', initial_message='Explore', start=True)
        self.assertEqual(code, 0)
        self.assertIn(('steer', 'old', 'Prefer option B'), planner.calls)
        self.assertIn(('cancelled', True), planner.calls)

    def test_roadmap_exposes_missing_and_cycle_without_recursion(self):
        from pi_autowork.planning_views import roadmap_text
        out = roadmap_text({'revision': 'abc', 'goals': [{'id': 'G', 'title': 'Ship', 'status': 'unmet'}],
                            'tasks': [{'id': 'A', 'title': 'First', 'goal': 'G', 'status': 'open',
                                       'depends_on': ['B', 'MISSING']},
                                      {'id': 'B', 'title': 'Second', 'goal': 'G', 'status': 'open',
                                       'depends_on': ['A']}], 'errors': []})
        self.assertIn('G', out)
        self.assertIn('MISSING', out)
        self.assertIn('cycle', out.lower())
        self.assertIn('A', out)
        self.assertIn('B', out)

    def test_streaming_text_and_tool_events_are_plain_text(self):
        from pi_autowork.planning_views import event_text
        self.assertEqual(event_text({'type': 'message_update', 'assistantMessageEvent':
                                     {'type': 'text_delta', 'delta': '[literal]'}}), '[literal]')
        self.assertIn('read', event_text({'type': 'tool_execution_start', 'toolName': 'read'}))
        self.assertEqual(event_text({'type': 'message_update', 'assistantMessageEvent':
                                     {'type': 'thinking_delta', 'delta': 'private'}}), '')


if __name__ == '__main__':
    unittest.main()
