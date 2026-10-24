"""Pinned Textual interaction checks; fixtures only, no real services or agents."""
import asyncio
import base64
import json
from pathlib import Path
import sys
import tempfile
import threading
import time
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import tui, fleet_view, blockers_report
from textual.widgets import TextArea, Button
from textual.drivers.web_driver import WebDriver
from textual._binary_encode import load as decode_packet


def collected(runners):
    """Use the current fleet envelope, retaining the production snapshot adapter."""
    snapshots = tuple(fleet_view.snapshot_for(r) for r in runners)
    return fleet_view.FleetSnapshot(tuple(runners), snapshots, 1, time.time())


async def report_actions():
    runner = fleet_view.Runner('example', repo='/repo/example', prepare_state='converted')
    concise = 'example — Awaiting owner decisions\nNeeds: autorización y corpus revisado\n'
    full = concise + '\n\n## Diagnostics\n' + 'source evidence ' * 400
    with tempfile.TemporaryDirectory() as folder:
        app = tui.FleetApp(command='aw', script='pa', state_root=folder, env_dir='/missing')
        with patch.object(fleet_view, 'collect_for_tui', return_value=collected([runner])), \
             patch.object(app, 'logs', return_value=''), \
             patch.object(blockers_report, 'build', return_value=full) as build, \
             patch.object(app, 'notify') as notify:
            async with app.run_test(size=(80, 30)) as pilot:
                await pilot.press('b')
                await app.workers.wait_for_complete()
                await pilot.pause()
                screen = app.screen
                area = screen.query_one(TextArea)
                assert area.text == concise, 'default report must omit optional diagnostics'
                for button in screen.query(Button):
                    assert button.region.right <= 80, 'all report actions must fit a narrow terminal'
                emitted = []
                with patch.object(app._driver, 'write', side_effect=emitted.append):
                    await pilot.press('c')
                    osc = [value for value in emitted if value.startswith('\x1b]52;c;')]
                    assert base64.b64decode(osc[-1][7:-1]).decode('utf-8') == concise
                    assert 'paste to verify' in str(notify.call_args).lower()
                    assert 'report copied' not in str(notify.call_args).lower()
                    await pilot.press('d')
                    assert area.text == full
                    assert build.call_count == 1, 'details toggle must use the frozen capture'
                    await pilot.click('#copy-report')
                    osc = [value for value in emitted if value.startswith('\x1b]52;c;')]
                    assert base64.b64decode(osc[-1][7:-1]).decode('utf-8') == full
                with patch.object(app._driver, 'write', side_effect=OSError('clipboard transport unavailable')):
                    screen.action_copy_report()
                    assert 'failed' in str(notify.call_args).lower()
                    assert 'export' in str(notify.call_args).lower()
                await pilot.press('d')
                await screen.action_export_report().wait()
                files = list(Path(folder).glob('reports/*.txt'))
                assert len(files) == 1 and files[0].read_text() == concise
                assert files[0].stat().st_mode & 0o777 == 0o600
                assert 'app host' in str(notify.call_args).lower()
                await screen.action_export_report().wait()
                assert len(list(Path(folder).glob('reports/*.txt'))) == 2, 'exports must not overwrite'
                with patch.object(tui, 'save_report', side_effect=PermissionError('fixture denied')):
                    await screen.action_export_report().wait()
                    assert 'failed' in str(notify.call_args).lower()
                assert area.text == concise
                # Real WebDriver protocol, only the external wire/input replaced. No browser/OS delivery claim.
                with patch('textual.drivers.web_driver.InputReader'):
                    web = WebDriver(app, size=(80, 30))
                packets = []
                with patch.object(web, '_write', side_effect=packets.append), patch.object(app, '_driver', web):
                    await screen.action_export_report().wait()
                    assert 'requested' in str(notify.call_args).lower()
                    starts = [json.loads(p[5:]) for p in packets if p[:1] == b'M']
                    start = next(p for p in starts if p['type'] == 'deliver_file_start')
                    assert start['mime_type'] == 'text/plain' and start['encoding'] == 'utf-8'
                    assert start['open_method'] == 'download' and start['name'] == 'blockers-report'
                    def transfer():
                        while start['key'] in web._deliveries:
                            web.on_meta('deliver_chunk_request', dict(key=start['key'], size=17, name=start['name']))
                    await asyncio.to_thread(transfer)
                    await pilot.pause()
                    chunks = [decode_packet(p[5:]) for p in packets if p[:1] == b'P']
                    assert ''.join(chunk[2] for chunk in chunks) == concise
                    assert 'transfer completed' in str(notify.call_args).lower()
                    assert all(int.from_bytes(p[1:5], 'big') == len(p[5:]) for p in packets)
                    for result in (None, OSError('fixture unavailable')):
                        kwargs = {'side_effect': result} if isinstance(result, Exception) else {'return_value': result}
                        with patch.object(app, 'deliver_text', **kwargs):
                            await screen.action_export_report().wait()
                            assert 'failed' in str(notify.call_args).lower()
                    await screen.action_export_report().wait()
                    key, stream = next(iter(web._deliveries.items()))
                    stream.close()  # actual asynchronous read failure at the driver boundary
                    await asyncio.to_thread(web.on_meta, 'deliver_chunk_request',
                                            dict(key=key, size=17, name='blockers-report'))
                    await pilot.pause()
                    assert 'download failed' in str(notify.call_args).lower()
                # A slow app-host save retains its capture without blocking Refresh or Escape.
                entered, release = threading.Event(), threading.Event()
                saved = tui.save_report
                def slow_save(text, directory):
                    entered.set()
                    if not release.wait(5):
                        raise TimeoutError('fixture release missing')
                    return saved(text, directory)
                with patch.object(tui, 'save_report', side_effect=slow_save):
                    await pilot.press('e')
                    assert await asyncio.to_thread(entered.wait, 2)
                    assert screen.exporting
                    refreshed = asyncio.Event()
                    present = screen.present_report
                    def present_refresh(text):
                        present(text)
                        refreshed.set()
                    build.return_value = 'newer capture'
                    with patch.object(screen, 'present_report', side_effect=present_refresh):
                        await pilot.press('r')
                        await asyncio.wait_for(refreshed.wait(), 2)
                    assert area.text == 'newer capture' and build.call_count == 2
                    assert screen.query_one('#export-report', Button).disabled
                    await pilot.press('escape')
                    assert not isinstance(app.screen, tui.BlockersScreen)
                    release.set()
                    await app.workers.wait_for_complete()
                assert len(list(Path(folder).glob('reports/*.txt'))) == 3
                assert all(file.read_text() == concise for file in Path(folder).glob('reports/*.txt'))
    print('PASS frozen views; real OSC52/native export/web protocol; failures; responsive in-flight export')


async def main():
    await report_actions()
    for width in (80, 120):
        for view_only in (False, True):
            runner = fleet_view.Runner('example', repo='/repo/example', state='paused',
                                      service='dead', prepare_state='converted')
            report = 'Runner: example\nRepository: /repo/example\nQuestion: literal [red]text[/red]\n' + 'long reason ' * 60 + '\n'
            capture = blockers_report.Report(report, 'Additional source diagnostics\n')
            control = Mock(side_effect=AssertionError('a report must not execute a command'))
            app = tui.FleetApp(command='aw', script='pa', state_root='/missing', env_dir='/missing',
                               agent='agent', view_only=view_only, runner_cmd=control)
            with patch.object(fleet_view, 'collect_for_tui', return_value=collected([runner])), \
                 patch.object(app, 'logs', return_value=''), \
                 patch.object(blockers_report, 'build', return_value=capture) as build, \
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
                    await pilot.click('#details-report')
                    assert area.text == str(capture)
                    assert build.call_count == 1
                    for button in app.screen.query(Button):
                        assert button.region.right <= width
                    await pilot.press('c')
                    copy.assert_called_with(capture)
                    await pilot.press('d')
                    assert area.text == report
                    with patch.object(tui, 'save_report', side_effect=OSError('fixture cannot save')) as export:
                        await pilot.click('#export-report')
                        await app.workers.wait_for_complete()
                        export.assert_called_once()
                        assert export.call_args.args[0] == report
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
