"""Rendered planning console with an offline controller; no model invocation."""
import asyncio
from pathlib import Path
import sys
import threading
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from textual.app import App
from textual.widgets import Input, Select, TextArea
from pi_autowork.planning_hub import PlanningHub
from pi_autowork.planning_ui import DecisionPrompt, PlanScreen


class FakePlanner:
    def __init__(self, repo, **kwargs):
        if repo == '/broken':
            raise RuntimeError('repository unavailable')
        self.repo, self.records, self.applied, self.sent = ('/repo' if repo == '/repo/sub' else repo), [], [], []
        self.release = threading.Event()
    def sessions(self):
        return list(self.records)
    def create(self, **kwargs):
        item = {'id': 'session-1', 'status': 'ready', **kwargs}
        self.records.append(item)
        return item
    def get(self, sid):
        return self.records[0]
    def history(self, sid):
        return [{'role': 'assistant', 'content': 'Saved conversation'}]
    def send(self, sid, message='', on_event=None, cancel=None):
        self.sent.append((sid, message))
        on_event({'type': 'message_update', 'assistantMessageEvent': {'type': 'text_delta', 'delta': 'Investigating'}})
        for _ in range(100):
            if self.release.wait(.01) or cancel.is_set():
                break
        return {'status': 'ready', 'text': 'Proposal ready'}
    def steer(self, sid, message):
        self.sent.append((sid, message))
        return {'disposition': 'queued'}
    def preview(self, sid):
        return {'id': sid, 'revision': 'review-123', 'files': ['docs/plans/p.md'], 'diff': '+ Proposal', 'valid': True, 'errors': []}
    def apply(self, sid, rev):
        self.applied.append((sid, rev))
        return {'commit': 'cafe123'}
    def roadmap(self, sid=None):
        return {'revision': 'base', 'goals': [{'id': 'G', 'title': 'Ship', 'status': 'unmet'}],
                'tasks': [{'id': 'T', 'title': 'Do it', 'goal': 'G', 'depends_on': [], 'status': 'open'}]}


async def main():
    for width in (80, 120):
        class Fixture(App):
            view_only = False
            state_root = '/unused'
            def on_mount(self):
                self.planning_hub = PlanningHub()
                self.push_screen(PlanScreen('/repo', task='T-1', mode='discuss', planner_factory=FakePlanner))
        app = Fixture()
        async with app.run_test(size=(width, 30)) as pilot:
            await pilot.pause()
            screen = app.screen
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert screen.query_one('#plan-chat', TextArea).size.height >= 3
            screen.query_one('#plan-input', TextArea).load_text('Improve reliability')
            await pilot.click('#plan-send')
            await app.workers.wait_for_complete()
            await pilot.pause()
            await pilot.pause(.1)
            assert screen.session_id == 'session-1'
            planner = screen.planner
            assert planner.sent
            # Navigation does not kill the app-owned physical turn.
            await pilot.press('escape')
            app.push_screen(PlanScreen('/repo/sub', planner_factory=FakePlanner))
            await pilot.pause()
            screen = app.screen
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert screen.planner is planner and screen.repo == '/repo'
            assert screen.query_one('#plan-mode', Select).value == 'discuss'
            assert screen.query_one('#plan-mode', Select).disabled
            assert screen.query_one('#plan-task', Input).value == 'T-1'
            planner.release.set()
            await asyncio.to_thread(app.planning_hub.turns[('/repo', 'session-1')].future.result, 3)
            await pilot.pause(.3)
            await pilot.click('#plan-review')
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert '+ Proposal' in screen.query_one('#plan-proposal', TextArea).text
            await pilot.click('#plan-apply')
            await pilot.pause()
            await pilot.press('n')
            assert planner.applied == []
            assert 'pi_autowork.tui' not in sys.modules, 'Planning confirmation must not load the fleet application'
            await pilot.click('#plan-apply')
            await pilot.pause()
            await pilot.press('y')
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert planner.applied == [('session-1', 'review-123')]
            # A failed project switch must not leave old apply authority behind a new name.
            await pilot.click('#plan-review')
            await app.workers.wait_for_complete()
            await pilot.pause()
            screen.query_one('#plan-repository', Input).value = '/broken'
            await pilot.click('#plan-load')
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert screen.planner is None and screen.session_id is None and screen.preview is None
            screen.action_apply()
            assert planner.applied == [('session-1', 'review-123')]
            app.view_only = True
            screen.action_send()
            screen.action_apply()
            assert len(planner.sent) == 1
            # The direct decision form requires text and returns explicit section intent.
            decisions = []
            app.push_screen(DecisionPrompt('T-1'), decisions.append)
            await pilot.pause()
            await pilot.click('#decision-save')
            assert isinstance(app.screen, DecisionPrompt) and not decisions
            app.screen.query_one('#decision-text', TextArea).load_text('Use the smaller design')
            app.screen.query_one('#decision-section', Select).value = 'Next'
            await pilot.pause(.4)
            await pilot.click('#decision-save')
            await pilot.pause()
            assert decisions == [{'text': 'Use the smaller design', 'section': 'Next'}], (decisions, app.screen)
        app.planning_hub.close()
        print('PASS planning', width)

if __name__ == '__main__':
    asyncio.run(main())
