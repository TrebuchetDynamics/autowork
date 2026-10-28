"""Responsive TUI regression pilot; all acquisition and commands are fixture-only."""
import asyncio
from dataclasses import replace
from contextlib import asynccontextmanager
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'scripts'))
from offline_textual import textual_unavailable

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, task_snapshot, blockers_report


@asynccontextmanager
async def run_pilot(app, **kwargs):
    """Disable periodic acquisition; join physical readers before releasing fixtures."""
    timers = []
    original = app.set_interval
    def paused(interval, callback, **options):
        timer = original(interval, callback, **dict(options, pause=True))
        timers.append(timer)
        return timer
    with patch.object(app, 'set_interval', side_effect=paused):
        try:
            async with app.run_test(**kwargs) as pilot:
                try:
                    yield pilot
                finally:
                    for timer in timers:
                        timer.pause()
                    await settle(app, pilot)
        finally:
            if hasattr(app, 'reads'):
                app.reads.close()
                await asyncio.to_thread(app.reads.executor.shutdown, wait=True)


async def settle(app, pilot):
    async def drained():
        while app.reads.active or app.reads.pending:
            await asyncio.sleep(0.01)
    await asyncio.wait_for(drained(), 10)
    await pilot.pause()


async def layout_pilot():
    from pi_autowork.tui import FleetApp, BrowseScreen
    from textual.widgets import DataTable

    with tempfile.TemporaryDirectory() as folder:
        root = Path(folder)
        warning = '/private/state/' + 'long-path/' * 30 + 'status.json: invalid crashed: expected string'
        snap = task_snapshot.TaskSnapshot(str(root), str(root / '.git'), 'a' * 40, 1, time.time(),
            counts=(0, 0, 3, 1, 1, 5), freshness='fresh', engine_freshness='unknown',
            errors=(warning,), pending_paths=())
        lane = fleet_view.Lane('EXAMPLE-400-a1b2c3d4', 'running', minutes=11, activity_age=660)
        runner = fleet_view.Runner('example-data-pipeline', repo=str(root), state='unavailable',
            service='running', blocker=warning, prepare_state='converted', snapshot=snap, lanes=[lane],
            model='provider/model', toolset=str(root))
        runners = [runner, *(replace(runner, name=f'repository-{i}') for i in range(8))]
        envelope = fleet_view.FleetSnapshot(tuple(runners), (snap,), 1, time.time())
        def no_command(*args, **kwargs):
            raise AssertionError('presentation must not run a command')
        app = FleetApp(command='fixture', script='fixture', state_root=root, env_dir=root,
                       runner_cmd=no_command, browse_root=str(root), view_only=True)
        with patch.object(fleet_view, 'collect_for_tui', return_value=envelope), \
             patch.object(fleet_view, 'logs', return_value='[12:00] fixture journal'), \
             patch.object(fleet_view, 'readiness', side_effect=lambda p: fleet_view.Readiness(str(p))):
            async with run_pilot(app, size=(80, 24)) as pilot:
                await settle(app, pilot)
                # Long diagnostics must not consume the worker/log viewport.
                overview = app.query_one('#overview')
                assert overview.display and overview.region.height <= 6, overview.region
                shown = str(overview.render())
                assert 'unavailable' in shown.lower() and 'execution unknown' in shown, shown
                assert '3 waiting' in shown and '1 blocker' in shown, shown
                assert warning not in shown, 'raw paths belong in Details'
                assert app.query_one('#lanes').region.height >= 2
                log = app.query_one('#log')
                assert log.region.height >= 4 and log.region.bottom <= 24, log.region
                assert not app.query_one('#detail-scroll').display
                # Read-only Details must be keyboard-reachable and preserve full evidence.
                await pilot.press('i')
                await pilot.pause()
                pane = app.query_one('#detail-scroll')
                assert pane.display and app.focused is pane
                assert warning in str(app.query_one('#detail').render())
                await pilot.press('end')
                await pilot.pause()
                assert pane.scroll_y > 0
                await pilot.press('i')
                assert not pane.display and app.focused.id == 'runners'
                # Resize uses cached observations; names and worker IDs stay readable.
                with patch.object(fleet_view, 'collect_for_tui', side_effect=AssertionError('resize recollected')):
                    for width, height in ((60, 24), (80, 24), (120, 30), (150, 45), (80, 24)):
                        await pilot.resize_terminal(width, height)
                        await pilot.pause()
                        for selector in ('#runners', '#lanes'):
                            table = app.query_one(selector, DataTable)
                            total = sum(c.get_render_width(table) for c in table.columns.values())
                            assert total <= width - 2, (selector, width, total, [(str(c.label), c.get_render_width(table)) for c in table.columns.values()])
                            assert table.region.bottom <= height, (selector, table.region)
                        workers = app.query_one('#lanes', DataTable)
                        assert str(workers.get_row_at(0)[0]) == 'EXAMPLE-400-a1b2c3d4'
                        assert 'unmatched' in str(workers.get_row_at(0)[1]).lower()
                        assert app.current().name == 'example-data-pipeline'
                        assert app.query_one('#log').region.height >= 4
                # A full fleet and many annotations still leave a visible journal,
                # including when the larger control menu is enabled.
                app.view_only = False
                app.runners = [replace(r, lanes=[replace(lane, task=f'TASK-{i:03d}') for i in range(20)])
                               for r in runners]
                app.render_fleet()
                for height in (24, 18):
                    await pilot.resize_terminal(80, height)
                    await pilot.pause()
                    log = app.query_one('#log')
                    assert log.region.height >= 4 and log.region.bottom <= height, log.region
                    assert app.query_one('#lanes').region.height >= 2
                # Adverse main-check evidence must be painted, not just retained
                # beneath a five-line CSS crop on a short terminal.
                for state, label in (('red', 'red'), ('broken', 'broken'), ('running', 'interrupted')):
                    app.current().main_check = {'state': state, 'rev': 'b' * 40}
                    app.show_detail()
                    await pilot.pause()
                    summary = app.query_one('#overview')
                    painted = '\n'.join(summary.render_line(y).text for y in range(summary.content_size.height))
                    assert 'Main:' in painted and label in painted, (state, painted)
                # Fixed widths must share one budget, including the scrollbar.
                app.runners = [replace(r, name='long-repository-name-' + str(i) * 30,
                                       state='not cycling', minutes=12345) for i, r in enumerate(runners)]
                await pilot.resize_terminal(60, 24)
                app.render_fleet()
                await pilot.pause()
                table = app.query_one('#runners', DataTable)
                assert not table.show_horizontal_scrollbar, (table.max_scroll_x, table.columns)
                assert sum(c.get_render_width(table) for c in table.columns.values()) <= 58
                await pilot.resize_terminal(80, 24)
                # The Details binding must not leak into child screens.
                browser = BrowseScreen(str(root), lambda *args: no_command())
                await app.push_screen(browser)
                await pilot.pause()
                tree, info = browser.query_one('#tree'), browser.query_one('#info-scroll')
                assert info.region.y >= tree.region.bottom, (tree.region, info.region)
                assert info.region.width >= 76
                await pilot.press('i')
                assert not pane.display
                await pilot.resize_terminal(150, 40)
                await pilot.pause()
                assert info.region.x >= tree.region.right, (tree.region, info.region)
                await pilot.press('escape')
        print('LAYOUT PILOT OK')


class TuiLayoutTests(unittest.TestCase):
    def test_responsive_layout_preserves_evidence_and_read_only_controls(self):
        result = subprocess.run(['uv', 'run', '--offline', '--quiet', '--no-project', '--with', 'textual==8.2.8',
                                 'python3', __file__, '--pilot'], capture_output=True, text=True, timeout=90)
        if textual_unavailable(result):
            self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('LAYOUT PILOT OK', result.stdout)

    def test_blocker_report_separates_runtime_decisions_and_waits(self):
        import json
        with tempfile.TemporaryDirectory() as folder:
            Path(folder, 'status.json').write_text(json.dumps({'task_observations': [
                {'task': 'WAIT-1', 'state': 'waiting', 'reason': 'dependency: INPUT-1'}]}))
            runner = fleet_view.Runner('demo', repo=folder, state_dir=folder, state='unavailable',
                blocker='status unreadable', acquisition_errors=['status unreadable'],
                questions=[fleet_view.Question('INPUT-1', 'E1', 1, 'Supply signed input')])
            with patch.object(fleet_view, 'task_store', return_value=None):
                report = blockers_report.summary(blockers_report.build(runner))
            assert 'Runtime and source health' in report, report
            assert 'Dependencies and waiting tasks' in report, report
            assert report.index('Runtime and source health') < report.index('Decisions and required inputs')
            assert report.index('Decisions and required inputs') < report.index('Dependencies and waiting tasks')
            assert report.count('status unreadable') == 1, report
            assert 'Supply signed input' in report and 'dependency: INPUT-1' in report


if __name__ == '__main__':
    if '--pilot' in sys.argv:
        asyncio.run(layout_pilot())
    else:
        unittest.main()
