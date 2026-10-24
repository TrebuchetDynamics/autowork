"""Rendered open/closed task navigation on pinned Textual; no live runners."""
import asyncio
from dataclasses import replace
from unittest.mock import Mock, patch

from test_task_history import TaskHistoryTests
from pi_autowork import fleet_view, tui
from textual.widgets import DataTable, Static, TextArea


async def main():
    for width in (80, 120):
        for view_only in (False, True):
            fixture = TaskHistoryTests()
            fixture.setUp()
            try:
                runner = fixture.runner
                runner.prepare_state = 'converted'
                runner.questions = [fleet_view.Question('LEGACY', 'input', 0, 'An independent planning question',
                                                        kind='outside')]
                annotation = fleet_view.TaskRow('LEGACY', 'Independent question', 'Annotation', 'Question',
                                                'annotation', question=True)
                runner.snapshot = replace(fixture.snap, question_rows=(annotation,), annotations=tuple(
                    f'Unmatched runtime observation TASK-{i}: older execution contract cannot join committed inventory.'
                    for i in range(20)))
                class FixtureApp(tui.FleetApp):
                    def refresh_fleet(self, cached):
                        self.runners = [runner]
                        self.selected = runner.name
                        self.show_detail()
                control = Mock(side_effect=AssertionError('history must not change tasks or runner'))
                app = FixtureApp(command='aw', script='pa', state_root='/missing', env_dir='/missing',
                                 view_only=view_only, agent='agent', runner_cmd=control)
                with patch.object(app, 'logs', return_value=''), \
                     patch.object(app, 'execute', side_effect=AssertionError('history executed an action')):
                    async with app.run_test(size=(width, 24)) as pilot:
                        await pilot.press('t')
                        await pilot.pause()
                        screen = app.screen
                        assert isinstance(screen, tui.TasksScreen)
                        assert screen.VIEW_NAMES['all'] == 'Open'
                        assert [r.task for r in screen.shown] == ['T-1']
                        tabs = screen.query_one('#task-views', Static)
                        assert '1 Open 1' in tabs.render().plain
                        assert '6 Closed 2' in tabs.render().plain
                        rendered = ''.join(tabs.render_line(i).text for i in range(tabs.size.height))
                        assert 'Closed 2' in rendered, 'closed tab must remain visible at narrow width'
                        assert screen.query_one('#tasks', DataTable).size.height >= 4, 'diagnostics hid the task rows'
                        info = screen.query_one('#task-provenance', TextArea)
                        assert 'TASK-19:' in info.text, 'full diagnostics must remain available'
                        assert info.size.height <= 3
                        await pilot.press('i')
                        assert info.has_focus
                        await pilot.press('tab')
                        assert screen.view == 'working', 'Tab should change views even from snapshot info'
                        await pilot.press('shift+tab')
                        assert screen.view == 'all'
                        await pilot.press('f7', 'ctrl+c')
                        assert app.clipboard == info.text, 'copy must retain the complete diagnostics'
                        await pilot.press('6')
                        assert screen.view == 'closed', 'number keys should work from snapshot info'
                        await pilot.press('i')
                        assert screen.query_one('#tasks', DataTable).has_focus
                        await pilot.press('6')
                        await pilot.pause()
                        assert [r.task for r in screen.shown] == ['LEGACY', 'MANUAL']
                        assert screen.current().state == 'Unknown closure'
                        assert [a.key for a in screen.actions(screen.current())] == ([] if view_only else ['x'])
                        await pilot.press('enter')
                        await pilot.pause()
                        assert isinstance(app.screen, tui.TaskScreen)
                        body = app.screen.query_one('#task-body', Static).render().plain
                        assert 'Unknown closure' in body
                        assert 'Closure provenance not recorded' in body
                        assert 'An independent planning question' in body
                        assert 'Task record (working tree;' in body
                        assert app.screen.answers() == []
                        assert 'Section' not in app.screen.query_one(tui.MenuBar).render().plain
                        await pilot.press('s', 'o', 'r', 'w', 'd', 'e')
                        assert isinstance(app.screen, tui.TaskScreen), 'history controls must not open mutation modals'
                        with patch.object(app, 'open_plan') as plan:
                            await pilot.press('g')
                            if view_only:
                                plan.assert_not_called()
                            else:
                                plan.assert_called_once_with(runner.repo, task='LEGACY', mode='discuss')
                        await pilot.press('escape', '1')
                        await pilot.pause()
                        assert app.screen is screen and [r.task for r in screen.shown] == ['T-1']
                        await pilot.press('shift+tab')
                        await pilot.pause()
                        assert screen.view == 'closed', 'backward tab must reach closed history'
                        await pilot.press('5', 'enter')
                        await pilot.pause()
                        assert isinstance(app.screen, tui.TaskScreen)
                        assert bool(app.screen.answers()) is not view_only, 'Questions retains independent answers'
                        await pilot.press('escape', '1', 'enter')
                        await pilot.pause()
                        assert isinstance(app.screen, tui.TaskScreen)
                        assert ('Section' in app.screen.query_one(tui.MenuBar).render().plain) is not view_only
                        control.assert_not_called()
                assert fixture.git('status', '--porcelain') == ''
            finally:
                fixture.doCleanups()
            print('PASS', width, 'view_only=' + str(view_only), 'open counts, closed history, readonly details and preserved records')


if __name__ == '__main__':
    asyncio.run(main())
