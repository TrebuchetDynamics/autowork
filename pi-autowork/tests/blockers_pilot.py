"""Pinned Textual interaction checks; fixtures only, no real services or agents."""
import asyncio
from pathlib import Path
import sys
import threading
import time
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import tui, fleet_view, blockers_report
from textual.widgets import TextArea, Button


def collected(runners):
    """Use the current fleet envelope, retaining the production snapshot adapter."""
    snapshots = tuple(fleet_view.snapshot_for(r) for r in runners)
    return fleet_view.FleetSnapshot(tuple(runners), snapshots, 1, time.time())


async def main():
    for width in (80, 120):
        for view_only in (False, True):
            runner = fleet_view.Runner('example', repo='/repo/example', state='paused',
                                      service='dead', prepare_state='converted')
            report = 'Runner: example\nRepository: /repo/example\nQuestion: literal [red]text[/red]\n' + 'long reason ' * 60
            control = Mock(side_effect=AssertionError('a report must not execute a command'))
            app = tui.FleetApp(command='aw', script='pa', state_root='/missing', env_dir='/missing',
                               agent='agent', view_only=view_only, runner_cmd=control)
            with patch.object(fleet_view, 'collect_for_tui', return_value=collected([runner])), \
                 patch.object(app, 'logs', return_value=''), \
                 patch.object(blockers_report, 'build', return_value=report) as build, \
                 patch.object(app, 'copy_to_clipboard') as copy:
                async with app.run_test(size=(width, 30)) as pilot:
                    await pilot.pause()
                    assert any(b.key == 'b' and b.action == 'show_blockers' for b in app.BINDINGS)
                    await pilot.press('b')
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    assert isinstance(app.screen, tui.BlockersScreen)
                    area = app.screen.query_one(TextArea)
                    assert area.read_only and area.text == report
                    await pilot.press('x', 'ctrl+v', 'backspace')
                    assert area.text == report
                    await pilot.press('f7')
                    assert area.selected_text == report, 'the complete report must be selectable'
                    await pilot.press('ctrl+c')
                    copy.assert_called_with(report)
                    copy.reset_mock()
                    await pilot.press('c')
                    copy.assert_called_with(report)
                    await pilot.click('#copy-report')
                    assert copy.call_count == 2
                    await pilot.press('r')
                    await app.workers.wait_for_complete()
                    assert build.call_count == 2
                    assert area.text == report
                    await pilot.press('p', 's', 'g')
                    control.assert_not_called()
                    assert isinstance(app.screen, tui.BlockersScreen)
                    await pilot.press('escape')
                    await pilot.pause()
                    assert len(app.screen_stack) == 1
                    bar = app.query_one('#menubar', tui.MenuBar)
                    x = bar.render().plain.index('Blockers') + 2
                    await pilot.click('#menubar', offset=(x, 0))
                    await app.workers.wait_for_complete()
                    assert isinstance(app.screen, tui.BlockersScreen), 'click must open the same read-only report'
                    assert build.call_count == 3
                    assert app.screen.query_one(Button).disabled is False
                    await pilot.click('#refresh-report')
                    await app.workers.wait_for_complete()
                    assert build.call_count == 4
                    await pilot.click('#back-report')
                    assert len(app.screen_stack) == 1
            print('PASS', width, 'view_only=' + str(view_only), 'keyboard, mouse, copy, literal text, no controls')

    # Backlog remains setup-only, and uses g rather than the read-only b action.
    runner = fleet_view.Runner('setup', repo=str(Path(__file__).parent), prepare_state='none')
    app = tui.FleetApp(command='aw', script='pa', state_root='/missing', env_dir='/missing', agent='agent')
    with patch.object(fleet_view, 'collect_for_tui', return_value=collected([runner])), \
         patch.object(app, 'logs', return_value=''), patch.object(app, 'execute') as execute:
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press('g')
            assert execute.call_count == 1
            assert execute.call_args.args[0].argv == ['aw', 'plan', runner.repo]
            runner.prepare_state = 'converted'
            await pilot.press('g')
            assert execute.call_count == 1, 'Backlog must be setup-only'
    print('PASS setup-only Backlog on g')

    # Deterministic barrier: acknowledge Escape and another open while the reader is stalled.
    started, release = threading.Event(), threading.Event()
    calls = []
    def slow(runner):
        calls.append(runner.name)
        started.set()
        assert release.wait(10), 'test failed to release report reader'
        return 'Runner: ' + runner.name
    one = fleet_view.Runner('one', repo='/one', prepare_state='converted')
    two = fleet_view.Runner('two', repo='/two', prepare_state='converted')
    app = tui.FleetApp(command='aw', script='pa', state_root='/missing', env_dir='/missing')
    with patch.object(fleet_view, 'collect_for_tui', return_value=collected([one, two])), \
         patch.object(app, 'logs', return_value=''), patch.object(blockers_report, 'build', side_effect=slow):
        try:
            async with app.run_test(size=(80, 24)) as pilot:
                await pilot.press('b')
                assert await asyncio.to_thread(started.wait, 3)
                await pilot.press('escape')
                assert len(app.screen_stack) == 1, 'input must work before the reader returns'
                app.selected = 'two'
                app.show_detail()
                await pilot.press('b')
                assert len(app.screen_stack) == 2
                assert calls == ['one'], 'close/reopen must not create overlapping physical readers'
                release.set()
                await app.workers.wait_for_complete()
                await pilot.pause()
                await app.workers.wait_for_complete()
                assert calls == ['one', 'two']
                assert app.screen.query_one(TextArea).text == 'Runner: two', 'old runner result must not leak'
        finally:
            release.set()
    print('PASS stalled reader input barrier, physical serialization, closed-screen/selected-runner isolation')

    app = tui.FleetApp(command='aw', script='pa', state_root='/missing', env_dir='/missing')
    with patch.object(fleet_view, 'collect_for_tui', return_value=collected([])), patch.object(app, 'logs', return_value=''), \
         patch.object(blockers_report, 'build') as build:
        async with app.run_test(size=(80, 24)) as pilot:
            await pilot.press('b')
            assert len(app.screen_stack) == 1
            build.assert_not_called()
    print('PASS empty fleet does not open or read a report')


if __name__ == '__main__':
    asyncio.run(main())
