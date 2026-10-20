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
from pi_autowork import fleet_view  # noqa: E402
from pi_autowork.tui import (REFRESH, BrowseScreen, FleetApp, LogScreen, TaskScreen, TasksScreen,  # noqa: E402
                             WorkerScreen, doing)


class Result:
    returncode, stdout, stderr = 0, 'ok', ''


async def main():
    # A worker's own words, without what its row already says; cut mid-word only to keep far more.
    lane = fleet_view.Lane(task='T-1', phase='verifying', detail='', attempt=1, minutes=1,
                           activity='said: T-1 committed as `abc`.', activity_age=1)
    assert doing(lane) == 'reviewer: committed as `abc`.', doing(lane)
    assert FleetApp.fit('reviewer: committed as abc', 16) == 'reviewer: commi…', FleetApp.fit('reviewer: committed as abc', 16)
    assert FleetApp.fit('one two three four', 15) == 'one two three…'
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        state, env = base / 'state' / 'india', base / 'env'
        state.mkdir(parents=True)
        env.mkdir()
        india = base / 'india'
        india.mkdir()
        (india / 'TODO.md').write_text('# TODO\n\n## Now\n\n- [ ] TASK-034 — Ship the thing\n- Short: Ship it\n\n'
                                       '- [ ] T-9 — Held task\n\n- [ ] TASK-040 — Waits\n')
        (india / 'goals.json').write_text(json.dumps({'goals': [{'id': 'G-1', 'title': 'Ship', 'status': 'unmet'}]}))
        (env / 'india.env').write_text(f'PI_AUTOWORK_REPO={india}\nPI_AUTOWORK_PRIMARY=openai-codex/gpt-6.1-sol\n')
        (state / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': str(india)}))
        (state / 'status.json').write_text(json.dumps({
            'repo': str(india), 'state': 'stalled', 'since': time.time() - 3600, 'updated_at': time.time(),
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
            subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                            'commit', '-qm', 'planning'], check=True)
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
            assert detail.lstrip().startswith('india  Waiting — 19 wait for TASK-036 (overlapping files)'), detail
            assert 'on you' not in detail and 'model gpt-6.1-sol' in detail, detail
            assert '23 waiting: 19 wait for TASK-036 (overlapping files) · 4 on dependencies' in detail, detail
            runners = app.query_one('#runners')
            assert [str(c.label) for c in runners.columns.values()] == ['Runner', 'State', 'Run', 'Land', 'Wait',
                                                                        'Held', 'Total', 'Needs', 'Now']
            assert [str(c) for c in runners.get_row_at(0)[2:7]] == ['0', '0', '23', '1', '24']
            assert '19 wait for TASK-036 (overlapping files)' in str(runners.get_row_at(0)[7])
            assert '24 open: 0 working · 0 to land · 23 waiting · 1 held' in detail, detail
            # The keys, each word's first letter highlighted in it; one key per action.
            hints = app.query_one('#detail').render()
            assert str(hints).rstrip().endswith('Log  Pause  Stop  Restart  Model  Fallback  Tasks  New  Quit'), str(hints)
            marked = {str(hints)[span.start:span.end] for span in hints.spans if 'underline' in str(span.style)}
            assert marked == set('LPSRMFTNQ'), marked
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
            # Its footer lists its own keys only, and the runner keys are off under it.
            shown = {b.binding.key for b in app.active_bindings.values() if b.binding.show}
            assert shown <= {'escape', 'q', 'ctrl+p'}, shown  # back (esc or q) only
            await pilot.press('s')
            await pilot.pause()
            assert isinstance(app.screen, LogScreen), app.screen  # no stop dialog over the log
            await pilot.press('escape')
            await pilot.pause()
            (india / 'BLOCKERS.md').write_text('<!-- pi-autowork:questions:start -->\n\n'
                                               '### Q-T-9 — USER_INPUT — effort input — unblocks 1\n\n'
                                               '- Needs: the worker asked for a key\n- Answer: Answer in T-9\'s entry.\n'
                                               '- Kind: held\n\n<!-- pi-autowork:questions:end -->\n')
            await pilot.press('t')                      # Tasks: every open task in TODO.md order
            await pilot.pause()
            assert isinstance(app.screen, TasksScreen), app.screen
            await pilot.pause(REFRESH + 0.5)            # the main screen's refresh runs beneath it
            tasks = app.screen.query_one('#tasks')
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['TASK-034', 'T-9', 'TASK-040']
            assert str(tasks.get_row_at(0)[2]) == 'Ship it'  # Short:, else the title
            await pilot.press('3')                      # the Held view
            await pilot.pause()
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['T-9'], tasks.row_count
            keys = str(app.screen.query_one('#task-detail').render())
            assert keys.rstrip().endswith('enter Open  Up  Down  Section  Clear  Aside  New  esc Back'), keys
            await pilot.press('u')                      # re-sort: an autowork move
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'move', 'T-9', 'up', 'india'], calls
            await pilot.press('c')                      # clear the hold, confirmed
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'clear-held', 'india', 'T-9'], calls
            await pilot.press('enter')                  # T-9's details: its question, entry and answers
            await pilot.pause()
            assert isinstance(app.screen, TaskScreen), app.screen
            body = str(app.screen.query_one('#task-body').render())
            assert 'the worker asked for a key' in body and '- [ ] T-9 — Held task' in body, body
            await pilot.press('w')                      # write a decision: typed, then Enter
            await pilot.pause()
            await pilot.press(*'use the test key')
            await pilot.press('enter')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1][:4] == ['aw', 'field', 'T-9', 'Owner decision'] and calls[-1][4].endswith(
                ': use the test key') and calls[-1][5] == 'india', calls
            await pilot.press('s')                      # another section
            await pilot.pause()
            await pilot.press('down', 'enter')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'place', 'T-9', 'Next', 'india'], calls
            await pilot.press('escape')                 # back to the Tasks window
            await pilot.pause()
            await pilot.press('n')                      # a new task, from the form
            await pilot.pause()
            form = app.screen
            form.query_one('#title').value = 'Add a thing'
            form.query_one('#short').value = 'A thing'
            form.query_one('#goal').value = 'G-1'
            form.query_one('#add').press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'add-task', '--title', 'Add a thing', '--short', 'A thing', '--goal', 'G-1',
                                 '--section', 'Next', 'india'], calls
            await pilot.press('escape')
            await pilot.pause()
            (india / 'BLOCKERS.md').unlink()            # the later views expect no question
            app.push_screen(WorkerScreen(app.current(), 'TASK-036'))  # a worker row's screen opens
            await pilot.pause()
            assert isinstance(app.screen, WorkerScreen) and app.screen.title == 'india: TASK-036', app.screen
            await pilot.press('escape')
            await pilot.pause()
            await pilot.press('n')                      # new: browse; half is not ready, ready plays after a yes
            await pilot.pause()
            assert isinstance(app.screen, BrowseScreen), app.screen
            screen = app.screen
            await pilot.press('down', 'down')
            await pilot.pause()
            path = screen.chosen.path if screen.chosen else ''
            if path.endswith('half'):
                await pilot.press('p')
                await pilot.pause()
                assert len(calls) == 2, calls          # not ready: nothing runs
                await pilot.press('down')
                await pilot.pause()
            assert screen.chosen and screen.chosen.ready and screen.chosen.path.endswith('ready'), screen.chosen
            await pilot.press('p')
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
            assert 'Waiting — 19 wait for TASK-036 (overlapping files)' in words and 'on you' not in words, words
            # Every count stays on screen: the text columns shrink instead (they scrolled off before).
            table = narrow.query_one('#runners')
            width = sum(c.get_render_width(table) for c in table.columns.values())
            assert width <= 80, (width, [str(c) for c in table.get_row_at(0)])
        viewer = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=['claude'], runner_cmd=run,
                          view_only=True)
        before = len(calls)
        async with viewer.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert 'view only' in str(viewer.query_one('#detail').render())
            for key in ('s', 'p', 'm', 'f', 'r', 'u', 'n'):
                await pilot.press(key)
                await pilot.pause()
            assert len(calls) == before, calls          # view-only: no key runs anything
            await pilot.press('l')
            await pilot.pause()
            assert isinstance(viewer.screen, LogScreen)  # but the log can be read
        # A TUI left open restarts itself on new code, but never over an open dialog.
        reloader = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                            systemctl=str(systemctl), journalctl=str(journal), agent=['claude'], runner_cmd=run,
                            view_only=True)
        async with reloader.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            reloader.reload_if_updated()
            await pilot.pause()
            assert reloader.return_value is None    # unchanged code: it stays
            await pilot.press('enter')
            await pilot.pause()
            reloader.code = -1                      # an update replaced the files
            reloader.reload_if_updated()
            await pilot.pause()
            assert reloader.return_value is None    # the log screen is open: not now
            await pilot.press('escape')
            await pilot.pause()
            reloader.reload_if_updated()
            await pilot.pause()
        assert reloader.return_value == 'reload'
    print('PILOT OK')


asyncio.run(main())
