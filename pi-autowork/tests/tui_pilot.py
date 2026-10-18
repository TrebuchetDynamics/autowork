"""Headless TUI pilot, run by test_fleet_view under `uv run --with textual==8.2.8`."""
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.tui import BrowseScreen, FleetApp, LogScreen, WorkerScreen  # noqa: E402


class Result:
    returncode, stdout, stderr = 0, 'ok', ''


async def main():
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        state, env = base / 'state' / 'india', base / 'env'
        state.mkdir(parents=True)
        env.mkdir()
        (env / 'india.env').write_text('PI_AUTOWORK_REPO=/git/india\nPI_AUTOWORK_PRIMARY=openai-codex/gpt-6.1-sol\n')
        (state / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': '/git/india'}))
        (state / 'status.json').write_text(json.dumps({
            'repo': '/git/india', 'state': 'stalled', 'since': time.time() - 3600, 'updated_at': time.time(),
            'waiting': 23, 'held': [{'task': 'T-9', 'cause': 'blocker'}],
            'roots': [{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19}],
            'waiting_groups': [{'label': 'wait for TASK-036 (overlapping files)', 'count': 19, 'tasks': ['TASK-040']},
                               {'label': 'on dependencies', 'count': 4, 'tasks': ['TASK-034']}]}))
        systemctl = base / 'systemctl'
        systemctl.write_text('#!/usr/bin/env bash\n'
                             '[[ $2 == list-units ]] && echo "pi-autowork@india.service loaded active running x"\n'
                             '[[ $2 == is-enabled ]] && exit 0\nexit 0\n')
        journal = base / 'journalctl'
        journal.write_text('#!/usr/bin/env bash\necho "[16:00] TASK-036: waiting"\n'
                           'echo "[16:00] TASK-034: pending — dependency: TASK-035"\n')
        for path in (systemctl, journal):
            path.chmod(0o755)
        tree = base / 'git'
        for name, files in (('ready', ('TODO.md', 'goals.json')), ('half', ('TODO.md',))):
            repo = tree / name
            repo.mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
            for f in files:
                (repo / f).write_text('x\n')
        calls, slow = [], {'seconds': 0}

        def run(argv, **kwargs):
            time.sleep(slow['seconds'])
            calls.append(argv)
            return Result()

        app = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                       systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run,
                       browse_root=str(tree), list_models=lambda: ['openai-codex/gpt-6-luna', 'openai-codex/gpt-6.1-sol'])
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            assert app.query_one('#runners').row_count == 1
            detail = str(app.query_one('#detail').render())
            # TOOLSET-166-b4: the verdict first, then why tasks wait, grouped.
            assert detail.lstrip().startswith('india  Stuck 1h00m — TASK-036'), detail
            assert 'holds 19' in detail and 'model openai-codex/gpt-6.1-sol' in detail, detail
            assert '23 waiting: 19 wait for TASK-036 (overlapping files) · 4 on dependencies' in detail, detail
            runners = app.query_one('#runners')
            assert [str(c.label) for c in runners.columns.values()] == ['Runner', 'State', 'Needs', 'Tasks', 'Now']
            assert 'outside Now/Next: TASK-036 (19)' in str(runners.get_row_at(0)[2])
            log = '\n'.join(line.text for line in app.query_one('#log').lines)
            assert 'TASK-036: waiting' in log and 'pending —' not in log, log
            await pilot.press('s')                      # stop asks first; n declines
            await pilot.pause()
            await pilot.press('n')
            await pilot.pause()
            assert calls == [], calls
            await pilot.press('p')                      # pause, confirmed
            await pilot.pause()
            started = time.monotonic()
            slow['seconds'] = 2                         # a restart waits for the runner to stop
            await pilot.press('y')
            await pilot.pause()
            assert time.monotonic() - started < 1.5, 'the action blocked the TUI'
            await app.workers.wait_for_complete()
            slow['seconds'] = 0
            assert calls == [['aw', 'pause', 'india']], calls
            await pilot.press('m')                      # model from Pi's list, filtered, then confirmed
            await pilot.pause()
            await pilot.press(*'luna')
            await pilot.pause()
            await pilot.press('enter')                  # Enter in the filter takes the first match
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'model', 'india', 'openai-codex/gpt-6-luna'], calls
            await pilot.press('enter')                  # Enter: the full-screen log
            await pilot.pause()
            assert isinstance(app.screen, LogScreen), app.screen
            await pilot.press('escape')
            await pilot.pause()
            app.push_screen(WorkerScreen(app.current(), 'TASK-036'))  # a worker row's screen opens
            await pilot.pause()
            assert isinstance(app.screen, WorkerScreen) and app.screen.title == 'india: TASK-036', app.screen
            await pilot.press('escape')
            await pilot.pause()
            await pilot.press('d')                      # browse: half is not ready, ready starts after a yes
            await pilot.pause()
            assert isinstance(app.screen, BrowseScreen), app.screen
            screen = app.screen
            await pilot.press('down', 'down')
            await pilot.pause()
            path = screen.chosen.path if screen.chosen else ''
            if path.endswith('half'):
                await pilot.press('s')
                await pilot.pause()
                assert len(calls) == 2, calls          # not ready: nothing runs
                await pilot.press('down')
                await pilot.pause()
            assert screen.chosen and screen.chosen.ready and screen.chosen.path.endswith('ready'), screen.chosen
            await pilot.press('s')
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'start', str(tree / 'ready')], calls
        narrow = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run)
        async with narrow.run_test(size=(80, 30)) as pilot:   # an 80-column terminal: wrapped, not cut
            await pilot.pause()
            words = ' '.join(str(narrow.query_one('#detail').render()).split())
            assert 'Stuck 1h00m — TASK-036' in words and 'holds 19' in words, words
        viewer = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=['claude'], runner_cmd=run,
                          view_only=True)
        before = len(calls)
        async with viewer.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert 'view only' in str(viewer.query_one('#detail').render())
            for key in ('s', 'p', 'm', 'x', 'b', 'd'):
                await pilot.press(key)
                await pilot.pause()
            assert len(calls) == before, calls          # view-only: no key runs anything
            await pilot.press('enter')
            await pilot.pause()
            assert isinstance(viewer.screen, LogScreen)  # but the log can be read
    print('PILOT OK')


asyncio.run(main())
