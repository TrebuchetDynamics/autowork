"""Headless TUI pilot, run by test_fleet_view under `uv run --with textual==8.2.8`."""
import asyncio
import json
import os
from pathlib import Path
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view  # noqa: E402
from pi_autowork.tui import FleetApp  # noqa: E402


class Result:
    returncode, stdout, stderr = 0, 'stopped india', ''


async def main():
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        state, env = base / 'state' / 'india', base / 'env'
        state.mkdir(parents=True)
        env.mkdir()
        (state / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': '/git/india'}))
        (state / 'status.json').write_text(json.dumps({
            'repo': '/git/india', 'state': 'stalled', 'since': time.time() - 3600, 'updated_at': time.time(), 'waiting': 23,
            'held': [{'task': 'T-9', 'cause': 'blocker'}],
            'roots': [{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19}]}))
        tmux = base / 'tmux'
        tmux.write_text('#!/usr/bin/env bash\n[[ $1 == list-sessions ]] && printf "pi-autowork-india\\t/git/india\\trunner\\n"\n'
                        '[[ $1 == capture-pane ]] && echo "[16:00] TASK-036: waiting"\nexit 0\n')
        tmux.chmod(0o755)
        calls = []

        def run(argv, **kwargs):
            calls.append(argv)
            return Result()

        app = FleetApp(tx='tx', script='pa.sh', state_root=base / 'state', env_dir=env, tmux=str(tmux),
                       systemctl='/nonexistent', journalctl='/nonexistent', agent=None, runner_cmd=run)
        async with app.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert app.query_one('#runners').row_count == 1
            assert app.sub_title == '1 runners: 1 stalled', app.sub_title
            detail = str(app.query_one('#detail').render())
            assert 'outside Now/Next: TASK-036 (19)' in detail and 'tx pi-autowork-india' in detail, detail
            await pilot.press('s')                       # stop asks first
            await pilot.pause()
            assert calls == [], calls
            await pilot.press('n')                       # declined: nothing runs
            await pilot.pause()
            assert calls == [], calls
            await pilot.press('s')
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            assert calls == [['tx', 'autowork', 'stop', 'india']], calls
            await pilot.press('x')                       # set aside: pick the held task, then confirm
            await pilot.pause()
            await pilot.press('enter')
            await pilot.pause()
            await pilot.press('y')
            await pilot.pause()
            assert calls[-1] == ['pa.sh', '--repo', '/git/india', '--set-aside', 'T-9'], calls
            await pilot.press('b')                       # no agent: nothing to run, a notice instead
            await pilot.pause()
            assert len(calls) == 2, calls
        viewer = FleetApp(tx='tx', script='pa.sh', state_root=base / 'state', env_dir=env, tmux=str(tmux),
                          systemctl='/nonexistent', journalctl='/nonexistent', agent=['claude'], runner_cmd=run,
                          view_only=True)
        async with viewer.run_test(size=(140, 40)) as pilot:
            await pilot.pause()
            assert 'view only' in str(viewer.query_one('#detail').render())
            for key in ('s', 'x', 'b', 'i', 'enter'):
                await pilot.press(key)
                await pilot.pause()
            assert len(calls) == 2, calls                # view-only: no key runs anything
    print('PILOT OK')


asyncio.run(main())
