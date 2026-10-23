"""Headless TUI pilot, run by test_fleet_view under `uv run --with textual==8.2.8`."""
import asyncio
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from pi_autowork import fleet_view, portal  # noqa: E402
from pi_autowork.processes import start_time  # noqa: E402
import store_fixture  # noqa: E402
from pi_autowork.tui import (REFRESH, BrowseScreen, Confirm, FleetApp, LogScreen, TaskScreen,  # noqa: E402
                             PickModel, PortalSetup, TasksScreen, WorkerScreen, doing)


class Result:
    returncode, stdout, stderr = 0, 'ok', ''


async def main():
    # A worker's own words, without what its row already says; cut mid-word only to keep far more.
    lane = fleet_view.Lane(task='T-1', phase='verifying', detail='', attempt=1, minutes=1,
                           activity='said: T-1 committed as `abc`.', activity_age=1)
    assert doing(lane) == 'reviewer: committed as `abc`.', doing(lane)
    assert FleetApp.fit('reviewer: committed as abc', 16) == 'reviewer: commi…', FleetApp.fit('reviewer: committed as abc', 16)
    assert FleetApp.fit('one two three four', 15) == 'one two three…'
    with tempfile.TemporaryDirectory() as folder, \
            mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=str(Path(folder) / 'agent')):
        base = Path(folder)
        state, env = base / 'state' / 'india', base / 'env'
        state.mkdir(parents=True)
        env.mkdir()
        india = base / 'india'
        india.mkdir()
        store_fixture.write_todo(india, '# TODO\n\n## Now\n\n- [ ] TASK-034 — Ship the thing\n- Short: Ship it\n\n'
                                        '- [ ] T-9 — Held task\n\n- [ ] TASK-040 — Waits\n')
        (env / 'india.env').write_text(f'PI_AUTOWORK_REPO={india}\nPI_AUTOWORK_PRIMARY=openai-codex/gpt-6.1-sol\n')
        (state / 'runner.json').write_text(json.dumps(
            {'pid': os.getpid(), 'start_time': start_time(os.getpid()), 'repo': str(india)}))
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
        (state / 'sessions').mkdir()
        transcript = state / 'sessions' / '2026-10-21T08-00-00-000Z_pi-autowork-TASK-036-attempt-1.jsonl'

        def step(i):  # one worker action, i seconds after a fixed start
            stamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time() - 600 + i))
            return json.dumps({'type': 'message', 'timestamp': stamp, 'message': {'role': 'assistant', 'content': [
                {'type': 'toolCall', 'name': 'bash', 'arguments': json.dumps({'command': f'echo step {i}'})}]}}) + '\n'
        transcript.write_text(''.join(step(i) for i in range(30)))
        tree = base / 'git'
        legacy = Path(__file__).resolve().parents[2] / 'tests/fixtures/task_migrate'
        for name in ('ready', 'legacy', 'fresh', 'busy', 'startable', 'invalid', 'toolchain', 'forced', 'blocked'):
            repo = tree / name
            repo.mkdir(parents=True)
            subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
            for key, value in (('user.name', 'T'), ('user.email', 't@example.invalid')):
                subprocess.run(['git', '-C', str(repo), 'config', key, value], check=True)
            if name in ('ready', 'invalid'):
                store_fixture.write_todo(repo, '- [ ] T-1 — Ready task\n')
                if name == 'invalid':
                    (repo / 'tasks/items/T-1.md').write_text('not a task record\n')
            elif name == 'fresh':
                (repo / 'README.md').write_text('# Unplanned repository\n')
            else:
                for filename in ('TODO.md', 'TODO.archive.md', 'goals.json'):
                    (repo / filename).write_bytes((legacy / filename).read_bytes())
            subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
            subprocess.run(['git', '-C', str(repo), 'commit', '--allow-empty', '-qm', 'planning'], check=True)
        slots = tree / 'busy/.git/autowork-execution/slots'
        slots.mkdir(parents=True)
        (slots / 'T-001.json').write_text(json.dumps({'task_id': 'T-001', 'state': 'running', 'attempt': 1}))
        calls, slow = [], {'seconds': 0}

        def run(argv, **kwargs):
            time.sleep(slow['seconds'])
            calls.append(argv)
            if argv[1:3] == ['tasks', 'prepare']:
                if Path(argv[-1]).name == 'toolchain':
                    return subprocess.CompletedProcess(argv, 1, json.dumps(dict(
                        ok=False, outcome='TOOLCHAIN_MISMATCH', next='Run autowork update, then retry.')), '')
                if Path(argv[-1]).name == 'blocked':
                    return subprocess.CompletedProcess(argv, 1, json.dumps(dict(
                        ok=False, outcome='MIGRATION_BLOCKED', refusals=[
                            'worker T-001 is still recorded', 'consumer build.py:12 names TODO.md'])), '')
                command = Path(__file__).resolve().parents[1] / 'pi_autowork/command.py'
                if '--force' in argv:
                    # Exercise real conversion without contacting services or ending host workers.
                    result = subprocess.run([sys.executable, str(command), 'tasks', 'prepare', argv[-1]], **kwargs)
                    report = json.loads(result.stdout)
                    report['forced'] = dict(step=dict(stopped=['T-001'], set_aside=['T-002'],
                                                      landed=False, committed=True, commit='abc123'))
                    return subprocess.CompletedProcess(argv, result.returncode, json.dumps(report), result.stderr)
                return subprocess.run([sys.executable, str(command), *argv[1:]], **kwargs)
            return Result()

        app = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                       systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run,
                       browse_root=str(tree), list_models=lambda: ['openai-codex/gpt-6-luna', 'openai-codex/gpt-6.1-sol'])
        async with app.run_test(size=(150, 45)) as pilot:
            await pilot.pause()
            # A late or doubled button event on an already-dismissed confirmation must be a
            # no-op, not pop the last screen and crash the TUI (ScreenStackError, 2026-10-22).
            late = Confirm('late confirmation')
            late.on_button_pressed(mock.Mock(button=mock.Mock(id='no')))
            late.action_answer(True)
            assert late.is_current is False
            assert app.query_one('#runners').row_count == 1
            detail = str(app.query_one('#detail').render())
            # TOOLSET-166-b4: the verdict first, then why tasks wait, grouped.
            assert detail.lstrip().startswith('india  Waiting — 19 wait for TASK-036 (overlapping files)'), detail
            assert 'on you' not in detail and 'Model      gpt-6.1-sol' in detail, detail
            assert 'Waiting    23: 19 wait for TASK-036 (overlapping files) · 4 on dependencies' in detail, detail
            runners = app.query_one('#runners')
            # TOOLSET-289-71 (test_runner_columns): the owner's four headlines.
            assert [str(c.label) for c in runners.columns.values()] == ['Runner', 'State', 'Active', 'Mergeable',
                                                                        'Waiting', 'Blocker', 'Decision', 'Total',
                                                                        'Needs', 'Now']
            assert [str(c) for c in runners.get_row_at(0)[2:8]] == ['0', '0', '23', '1', '0', '24']
            assert '19 wait for TASK-036 (overlap' in str(runners.get_row_at(0)[8]), runners.get_row_at(0)  # cut to fit
            assert 'Tasks      24 open · 0 active · 0 mergeable · 23 waiting · 1 blocker' in detail, detail
            assert 'Push       disabled' in detail, detail  # no saved grant: local only
            settings = env / 'india.env'
            saved = settings.read_text()
            for value, label in (('1', 'enabled'), ('0', 'disabled')):
                settings.write_text(saved + f'PI_AUTOWORK_PUSH={value}\n')
                app.action_refresh()
                detail = str(app.query_one('#detail').render())
                assert f'Push       {label}' in detail, detail
                assert settings.read_text() == saved + f'PI_AUTOWORK_PUSH={value}\n'
            # The keys, in the menu bar at the top (a GUI app's "File Edit View"), each word's first
            # letter highlighted in it; one key per action. The detail pane holds no keys.
            assert 'Quit' not in detail, detail
            menubar = app.query_one('#menubar')
            assert menubar.region.y < app.query_one('#runners').region.y, 'the menu bar is above the runners'
            hints = menubar.render()
            assert str(hints).rstrip().endswith('Log  Pause  Stop  Restart  Model  Tasks  New  Quit'), str(hints)
            marked = {str(hints)[span.start:span.end] for span in hints.spans if 'underline' in str(span.style)}
            assert marked == set('LPSRMTNQ'), marked
            log = '\n'.join(line.text for line in app.query_one('#log').lines)
            assert 'TASK-036: waiting' in log and 'pending —' not in log, log
            agent = base / 'agent'
            agent.mkdir()
            config = agent / 'models.json'
            original = b'{"providers":{"other":{"apiKey":"DO-NOT-LOG"}}}\n'
            config.write_bytes(original)
            # Fleet controls omit Fallback/Portal for every runner state, including no runner.
            runner = app.current()
            for width in (80, 120):
                await pilot.resize_terminal(width, 45)
                for view_only in (False, True):
                    app.view_only = view_only
                    for service, state_name, menu in (
                            ('running', 'stalled', 'Log  Pause  Stop  Restart  Model  Tasks  New  Quit'),
                            ('stopped', 'not running', 'Log  Play  Model  Tasks  Uninstall  New  Quit'),
                            ('stopped', 'paused', 'Log  Play  Model  Tasks  Uninstall  New  Quit'),
                            ('', '', 'New  Quit')):
                        selected = replace(runner, service=service, state=state_name) if service else None
                        with mock.patch.object(fleet_view, 'collect', return_value=[selected] if selected else []), \
                                mock.patch.object(portal, 'probe', side_effect=AssertionError('fleet key probed Portal')):
                            app.action_refresh()
                            await pilot.pause()
                            expected = ('view only  Log  Quit' if selected else '') if view_only else menu
                            assert str(menubar.render()).strip() == expected, menubar.render()
                            assert menubar.render_line(0).text.strip() == expected, menubar.render_line(0).text
                            assert not {'f', 'o'} & app.active_bindings.keys(), app.active_bindings
                            if selected:
                                assert 'f' not in {a.key for a in app.available(selected)}
                                assert 'fallback ' in str(app.query_one('#detail').render())
                            screen = app.screen
                            before = {str(p): p.read_bytes() for p in base.rglob('*') if p.is_file()}
                            await pilot.press('f', 'o')
                            await pilot.pause()
                            assert app.screen is screen, app.screen
                            assert calls == [], calls
                            assert {str(p): p.read_bytes() for p in base.rglob('*') if p.is_file()} == before
                            if selected and not view_only and service == 'running':
                                await pilot.press('m')
                                await pilot.pause()
                                assert isinstance(app.screen, PickModel), app.screen
                                await pilot.press('f', 'o')  # child input must still accept these letters
                                assert app.screen.query_one('#filter').value == 'fo'
                                await pilot.press('escape', 'l')
                                await pilot.pause()
                                assert isinstance(app.screen, LogScreen), app.screen
                                await pilot.press('escape')
                                await pilot.pause()
                                assert app.screen is screen, app.screen
            app.view_only = False
            await pilot.resize_terminal(150, 45)
            app.action_refresh()
            await pilot.pause()
            # Test Portal's isolated preview/consent component, not a fleet shortcut.
            with mock.patch.object(portal, 'probe', return_value={'state': 'unavailable', 'message': 'Proxy unavailable; start it yourself.'}):
                app.push_screen(PortalSetup())
                await pilot.pause()
                app.screen.query_one('#portal-model').value = 'openai/example'
                await pilot.click('#portal-preview')
                await pilot.pause()
                question = str(app.screen.question)
                assert 'setup proposal' in question and 'nous-local/openai/example' in question, question
                assert 'Proxy unavailable' in question and 'DO-NOT-LOG' not in question, question
                assert config.read_bytes() == original
                await pilot.press('n')
                await pilot.pause()
                assert config.read_bytes() == original
                assert sorted(p.name for p in agent.iterdir()) == ['models.json']
                await pilot.click('#portal-preview')
                await pilot.pause()
                await pilot.press('y')
                await pilot.pause()
                assert json.loads(config.read_text())['providers']['nous-local']['models'] == [{'id': 'openai/example'}]
                assert json.loads(config.read_text())['providers']['other'] == {'apiKey': 'DO-NOT-LOG'}
                assert calls == [], calls
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
            await pilot.press('t')                      # Tasks: every open task in priority order
            await pilot.pause()
            assert isinstance(app.screen, TasksScreen), app.screen
            await pilot.pause(REFRESH + 0.5)            # the main screen's refresh runs beneath it
            tasks = app.screen.query_one('#tasks')
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['TASK-034', 'T-9', 'TASK-040']
            assert str(tasks.get_row_at(0)[2]) == 'Ship it'  # its short name
            await pilot.press('3')                      # the Held view
            await pilot.pause()
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['T-9'], tasks.row_count
            keys = str(app.screen.query_one('#menubar').render())
            assert keys.rstrip().endswith('enter Open  Up  Down  Section  Clear  Aside  New  esc Back'), keys
            await pilot.press('u')                      # re-sort: an autowork move
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'tasks', 'move', 'T-9', 'up', 'india'], calls
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
            assert 'the worker asked for a key' in body and 'title = "Held task"' in body, body
            await pilot.press('w')                      # write a decision: typed, then Enter
            await pilot.pause()
            await pilot.press(*'use fallback for other models')
            await pilot.press('enter')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1][:5] == ['aw', 'tasks', 'field', 'T-9', 'Owner decision'] and calls[-1][5].endswith(
                ': use fallback for other models') and calls[-1][6] == 'india', calls
            await pilot.press('s')                      # another section
            await pilot.pause()
            await pilot.press('down', 'enter')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'tasks', 'place', 'T-9', 'Next', 'india'], calls
            await pilot.press('escape')                 # back to the Tasks window
            await pilot.pause()
            await pilot.press('n')                      # a new task, from the form
            await pilot.pause()
            form = app.screen
            form.query_one('#title').value = 'Add a thing'
            form.query_one('#short').value = 'A thing'
            form.query_one('#goal').value = store_fixture.FIXTURE_GOAL
            form.query_one('#add').press()
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'tasks', 'add', '--title', 'Add a thing', '--short', 'A thing', '--goal', 'FIXTURE',
                                 '--section', 'Next', 'india'], calls
            await pilot.press('escape')
            await pilot.pause()
            (india / 'BLOCKERS.md').unlink()            # the later views expect no question
            app.push_screen(WorkerScreen(app.current(), 'TASK-036'))  # a worker row's screen opens
            await pilot.pause()
            assert isinstance(app.screen, WorkerScreen) and app.screen.title == 'india: TASK-036', app.screen
            lines = lambda: [''.join(seg.text for seg in strip) for strip in app.screen.query_one('#worker-actions').lines]
            shown = lines()  # a log: all 30 actions, oldest first, each with its time
            assert len(shown) == 30 and 'step 0' in shown[0] and 'step 29' in shown[-1], shown
            assert shown[0][:8].count(':') == 2, shown[0]
            with transcript.open('a') as stream:
                stream.write(step(30))
            app.screen.refresh_actions()
            await pilot.pause()
            after = lines()  # the new action is appended at the bottom; nothing above it is redrawn
            assert after[:30] == shown and 'step 30' in after[-1] and len(after) == 31, after
            await pilot.press('escape')
            await pilot.pause()
            # Play offers preparation, never starts on NO_STORE or an in-flight conversion.
            for name, button, outcome, starts in (
                    ('legacy', 'prepare', 'MIGRATED', False),
                    ('forced', 'force', 'MIGRATED', False),
                    ('blocked', 'prepare', 'MIGRATION_BLOCKED', False),
                    ('fresh', 'prepare-start', 'NO_STORE', False),
                    ('busy', 'prepare-start', 'MIGRATION_DEFERRED', False),
                    ('invalid', 'prepare-start', 'INVALID_STORE', False),
                    ('toolchain', 'prepare-start', 'TOOLCHAIN_MISMATCH', False),
                    ('startable', 'prepare-start', 'MIGRATED', True)):
                await pilot.press('n')
                await pilot.pause()
                assert isinstance(app.screen, BrowseScreen), app.screen
                screen = app.screen
                tree_widget = screen.query_one('#tree')
                node = next(n for n in tree_widget.root.children if n.data.path.name == name)
                tree_widget.select_node(node)
                await pilot.pause()
                assert screen.chosen and not screen.chosen.ready, screen.chosen
                before = len(calls)
                task_files = lambda: {str(p): p.read_bytes() for p in (tree / name / 'tasks').rglob('*.md')}
                original_tasks = task_files()
                await pilot.press('p')
                await pilot.pause()
                assert app.screen.query_one('#prepare').label.plain == 'Prepare'
                assert app.screen.query_one('#prepare-start').label.plain == 'Prepare and start'
                assert app.screen.query_one('#plan').label.plain == 'Plan'
                assert app.screen.query_one('#force').label.plain == 'Force'
                assert app.screen.query_one('#cancel').label.plain == 'Cancel'
                if name == 'legacy':
                    await pilot.press('escape')
                    await pilot.pause()
                    assert len(calls) == before, 'cancel must not prepare or start'
                    await pilot.press('p')
                    await pilot.pause()
                if name == 'fresh':  # Plan needs an agent; without one it says so and runs nothing
                    app.screen.query_one('#plan').press()
                    await pilot.pause()
                    assert app.screen is screen and len(calls) == before, calls
                    assert task_files() == original_tasks
                    await pilot.press('p')
                    await pilot.pause()
                app.screen.query_one('#' + button).press()
                await pilot.pause()
                if button == 'force':
                    assert isinstance(app.screen, Confirm), app.screen
                    question = str(app.screen.question)
                    for words in ('service', 'live workers', 'sets attempts aside', 'worktrees',
                                  'branches', 'files kept', 'commits planning edits', 'converts', 'restarts'):
                        assert words in question, question
                    assert str(tree / name) in question, question
                    assert len(calls) == before, 'Force must wait for consent'
                    await pilot.press('escape')
                    await pilot.pause()
                    assert app.screen is screen and len(calls) == before, 'cancel must not force'
                    await pilot.press('p')
                    await pilot.pause()
                    app.screen.query_one('#force').press()
                    await pilot.pause()
                    await pilot.press('y')
                    await pilot.pause()
                # DirectoryTree keeps a loader worker alive while the browser is open.
                for worker in list(app.workers):
                    if worker.group == 'prepare':
                        await worker.wait()
                await pilot.pause()
                info = str(screen.query_one('#info').render())
                assert outcome in info, info
                assert calls[before] == ['aw', 'tasks', 'prepare', *(['--force'] if button == 'force' else []),
                                          str(tree / name)], calls
                if button == 'force':
                    for field in ("stopped: ['T-001']", "set_aside: ['T-002']", 'landed: False',
                                  'committed: True', 'commit: abc123'):
                        assert field in info, info
                if outcome == 'MIGRATION_BLOCKED':
                    assert 'worker T-001 is still recorded\n' in info, info
                    assert 'consumer build.py:12 names TODO.md\n' in info, info
                if outcome == 'MIGRATED':
                    assert screen.chosen.ready and (tree / name / 'tasks/items/T-001.md').is_file(), info
                    assert 'ready' in tree_widget.render_line(node.line).text, 'node was not refreshed'
                else:
                    assert not screen.chosen.ready and task_files() == original_tasks, info
                    assert 'ready' not in tree_widget.render_line(node.line).text
                    if outcome == 'NO_STORE':
                        assert '/docs_sync' in info and 'no heading is marked Status: Accepted' in info, info
                    elif outcome == 'MIGRATION_DEFERRED':
                        assert 'conversion deferred' in info, info
                if starts:
                    await pilot.press('y')              # starting still asks for confirmation
                    await pilot.pause()
                    await app.workers.wait_for_complete()
                    assert calls[before + 1:] == [['aw', 'start', str(tree / name)]], calls
                else:
                    assert app.screen is screen, 'Prepare must not offer Start before readiness passes'
                    assert len(calls) == before + 1, calls
                    await pilot.press('escape')
                    await pilot.pause()
            await pilot.press('n')                      # already ready: Play still starts after a yes
            await pilot.pause()
            screen = app.screen
            tree_widget = screen.query_one('#tree')
            tree_widget.select_node(next(n for n in tree_widget.root.children if n.data.path.name == 'ready'))
            await pilot.pause()
            assert screen.chosen.ready, screen.chosen
            await pilot.press('p')
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            await app.workers.wait_for_complete()
            assert calls[-1] == ['aw', 'start', str(tree / 'ready')], calls
        narrow = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run,
                          browse_root=str(tree))
        async with narrow.run_test(size=(80, 30)) as pilot:   # an 80-column terminal: wrapped, not cut
            await pilot.pause()
            words = ' '.join(str(narrow.query_one('#detail').render()).split())
            assert 'Waiting — 19 wait for TASK-036 (overlapping files)' in words and 'on you' not in words, words
            # Every count stays on screen: the text columns shrink instead (they scrolled off before).
            table = narrow.query_one('#runners')
            width = sum(c.get_render_width(table) for c in table.columns.values())
            assert width <= 80, (width, [str(c) for c in table.get_row_at(0)])
            await pilot.press('n')
            await pilot.pause()
            tree_widget = narrow.screen.query_one('#tree')
            tree_widget.select_node(next(n for n in tree_widget.root.children if n.data.path.name == 'busy'))
            await pilot.pause()
            await pilot.press('p')
            await pilot.pause()
            dialog = narrow.screen.query_one('PrepareRepository > Vertical')
            assert dialog.region.x >= 0 and dialog.region.right <= 80, dialog.region
            for button in narrow.screen.query('Button'):
                assert button.region.right <= 80, button.region
            await pilot.press('escape')
            await pilot.pause()
            screen = narrow.screen
            attempts = [f'TASK-{i:03d}' for i in range(10)]
            screen.prepared(str(tree / 'busy'), dict(
                outcome='MIGRATION_BLOCKED', refusals=['worker still recorded', 'consumer still tracked'],
                forced=dict(step=dict(stopped=attempts, set_aside=attempts, landed=False,
                                      committed=True, commit='abc123')),
                next='Resolve the preservation collision, then retry Force.'), False)
            await pilot.pause()
            info = screen.query_one('#info')
            pane = info.parent
            await pilot.press('tab', 'end')  # keyboard users can reach the complete report
            await pilot.pause()
            assert pane.scroll_y > 0, 'long forced reports must be scroll-accessible'
            assert pane.content_region.y < info.region.bottom <= pane.content_region.bottom, (
                info.region, pane.content_region)
            assert 'commit: abc123' in str(info.render()) and 'retry Force.' in str(info.render())
            await pilot.press('escape')
        viewer = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=['claude'], runner_cmd=run,
                          view_only=True)
        before = len(calls)
        async with viewer.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert 'view only' in str(viewer.query_one('#menubar').render())
            for key in ('s', 'p', 'm', 'f', 'r', 'u', 'n', 'o'):
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
