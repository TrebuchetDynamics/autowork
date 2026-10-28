"""Headless TUI pilot, run by test_fleet_view under `uv run --with textual==8.2.8`."""
import asyncio
from contextlib import asynccontextmanager, contextmanager, ExitStack
from dataclasses import replace
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from pi_autowork import fleet_view, portal  # noqa: E402
from pi_autowork.processes import start_time  # noqa: E402
import store_fixture  # noqa: E402
from pi_autowork.tui import (REFRESH, BrowseScreen, Confirm, FleetApp, LogScreen, TaskScreen,  # noqa: E402
                             BlockersScreen, PickModel, PortalSetup, TasksScreen, WorkerScreen, doing)


class Result:
    returncode, stdout, stderr = 0, 'ok', ''


def read_state(app):
    def tokens(reads):
        return [(t.kind, t.generation, t.epoch, t.cancelled, t.done.done()) for t in reads.values()]
    return dict(epoch=app.read_epoch, applied=dict(app.reader.applied),
                active=tokens(app.reads.active), pending=tokens(app.reads.pending),
                errors=dict(app.__dict__.get('_read_errors', {})))


async def drain_reads(app):
    async def drained():
        while app.reads.active or app.reads.pending:
            await asyncio.sleep(0.01)
    try:
        await asyncio.wait_for(drained(), 10)
    except TimeoutError as exc:
        raise AssertionError(('physical readers did not drain', read_state(app))) from exc


@asynccontextmanager
async def run_pilot(app, **kwargs):
    """Keep real read timers paused except in the explicit timer case; join on failure too."""
    timers = {}
    set_interval = FleetApp.set_interval
    def paused_interval(owner, interval, callback, **options):
        options['pause'] = True
        timer = set_interval(owner, interval, callback, **options)
        timers[callback] = timer
        return timer
    with ExitStack() as patches:
        for cls in (FleetApp, LogScreen, WorkerScreen, TasksScreen, TaskScreen):
            patches.enter_context(mock.patch.object(cls, 'set_interval', new=paused_interval))
        try:
            async with app.run_test(**kwargs) as pilot:
                pilot.read_timers = timers
                try:
                    yield pilot
                finally:
                    for timer in timers.values():
                        timer.pause()
                    await drain_reads(app)
                    # Finish fixture commands while call_from_thread still has
                    # a live app; DirectoryTree workers are cancelled on unmount.
                    for worker in list(app.workers):
                        if worker.group in ('actions', 'prepare'):
                            await worker.wait()
                    await drain_reads(app)
        finally:
            for timer in timers.values():
                timer.pause()
            if hasattr(app, 'reads'):
                # Textual has unmounted/cancelled its workers. Subscription
                # cancellation alone does not finish the executor's physical reads.
                app.reads.close()
                try:
                    await drain_reads(app)
                finally:
                    await asyncio.to_thread(app.reads.executor.shutdown, wait=True)


@asynccontextmanager
async def patched_reads(app, *patches):
    """No physical reader may straddle a synthetic provider's lifetime."""
    await drain_reads(app)
    with ExitStack() as stack:
        for patch in patches:
            stack.enter_context(patch)
        try:
            yield
        finally:
            await drain_reads(app)


@contextmanager
def browser_readiness(root):
    """Serve detached real fixture facts; no preparation subprocess batch in UI readers.

    Reopening Browse otherwise probes every repository again. Capture before any
    reader starts, and recapture after fixture commands mutate a repository. The
    real ReadCoordinator and blocked-provider cases still own physical lifetimes.
    """
    original = fleet_view.readiness
    snapshots = {}
    def capture(path):
        snapshots[str(path)] = original(path)
    for path in (root, *sorted(root.iterdir())):
        capture(path)
    def read(path):
        ready = snapshots[str(path)]  # unexpected paths fail, never inspect the host
        return replace(ready, problems=list(ready.problems))
    with mock.patch.object(fleet_view, 'readiness', new=read):
        yield capture


async def refresh(app, pilot):
    # Explicit refresh invalidates subscriptions, not physical reads. Settle
    # the previous case first so its loader cannot consume this case's provider.
    await drain_reads(app)
    token = app.action_refresh()
    if token is not None:
        async def applied():
            while app.reader.applied.get('fleet', -1) < token.generation:
                await asyncio.sleep(0.01)
        try:
            await asyncio.wait_for(applied(), 10)
        except TimeoutError as exc:
            raise AssertionError(('fleet refresh not applied', token.generation,
                                  token.cancelled, read_state(app))) from exc
    await pilot.pause()
    await drain_reads(app)


async def blocked_readers(app, pilot):
    """Keys are acknowledged before releasing each real reader seam; no latency claim."""
    from pi_autowork.tui import NewTask
    providers = (
        ('collect_for_tui', lambda: app.poll_refresh(), ('down',), None),
        ('logs', lambda: app.action_run('l'), ('s', 'escape'), LogScreen),
        ('action_log', lambda: app.push_screen(WorkerScreen(app.current(), 'TASK-036')), ('w', 'escape'), WorkerScreen),
        ('task_entry', lambda: app.push_screen(TaskScreen('india', 'T-9')), ('escape',), TaskScreen),
        ('open_goals', lambda: app.push_screen(NewTask([], runner=app.current())), ('escape',), NewTask),
        ('readiness', lambda: app.action_browse(), ('down', 'escape'), BrowseScreen),
        ('models', lambda: app.action_pick_model('model'), ('f', 'o', 'escape'), PickModel),
        ('code_stamp', lambda: app.reload_if_updated(), ('down',), None),
    )
    for name, opening, keys, screen_type in providers:
        await drain_reads(app)
        entered, release = threading.Event(), threading.Event()
        module = sys.modules['pi_autowork.tui'] if name == 'code_stamp' else fleet_view
        original = app.list_models if name == 'models' else getattr(module, name)
        context = {}
        def stalled(*args, **kwargs):
            entered.set()
            assert release.wait(10), 'blocked-reader watchdog: ' + name
            if name == 'models':
                context.update(kwargs)
                return original()
            return original(*args, **kwargs)
        # Default discovery must be fresh per opening and scoped to the service,
        # not the deliberately different PI_CODING_AGENT_DIR in the viewing shell.
        saved_models = app.list_models
        refreshing = None
        with mock.patch.object(module, name, side_effect=stalled) as provider:
            try:
                if name == 'models':
                    app.list_models = provider
                token = opening()
                assert await asyncio.to_thread(entered.wait, 5), name + ' not entered'
                if screen_type:
                    assert isinstance(app.screen, screen_type), (name, app.screen)
                if name == 'models':
                    await pilot.press(*keys[:-1])
                    assert app.screen.query_one('#filter').value == 'fo'
                    await pilot.press(keys[-1])
                else:
                    await pilot.press(*keys)
                await pilot.pause()
                if screen_type:
                    assert len(app.screen_stack) == 1, name + ' did not close'
                # Repeated cached layout never executes another synchronous provider.
                await pilot.resize_terminal(149, 45)
                await pilot.resize_terminal(150, 45)
                if name == 'collect_for_tui':
                    for _ in range(12):
                        app.poll_refresh()
                    # A fixture refresh must settle old physical work before it
                    # invalidates subscriptions or swaps the next case's provider.
                    started = asyncio.Event()
                    async def while_reading():
                        started.set()
                        await refresh(app, pilot)
                    refreshing = asyncio.create_task(while_reading())
                    await started.wait()
                    assert not token.cancelled, (
                        'refresh retired an outstanding reader', token.generation,
                        read_state(app))
            finally:
                release.set()
                try:
                    if refreshing is not None:
                        await refreshing
                    await drain_reads(app)
                finally:
                    app.list_models = saved_models
        if name == 'models':
            assert context['agent_dir'] == str(Path.home() / '.pi/agent'), context
        await pilot.pause()
    await refresh(app, pilot)
    original = app.current()
    other = replace(original, name='other', repo=original.repo + '-other')
    app.runners = [original, other]
    journal = app.query_one('#log')
    journal.clear()
    journal.write('a JOURNAL')
    entered, release = threading.Event(), threading.Event()
    def other_log(*args, **kwargs):
        entered.set()
        assert release.wait(10), 'journal-selection watchdog'
        return 'b JOURNAL'
    with mock.patch.object(fleet_view, 'logs', side_effect=other_log):
        try:
            app.selected = other.name
            token = app.refresh_log()
            assert await asyncio.to_thread(entered.wait, 5)
            assert 'a JOURNAL' not in '\n'.join(line.text for line in journal.lines), 'wrong runner journal retained'
        finally:
            release.set()
            await drain_reads(app)
        await token.wait()
    assert 'b JOURNAL' in '\n'.join(line.text for line in journal.lines)
    await refresh(app, pilot)


async def task_inventory_viewport(app, pilot):
    """Unknown must not paint empty counts; freshness/errors must occupy visible space."""
    original = app.current()
    good = original.snapshot
    cases = (
        ('unavailable', replace(good, counts=None, rows=(), closed_rows=(), question_rows=(),
                                freshness='unavailable', errors=('inventory read denied',))),
        ('empty', replace(good, counts=(0, 0, 0, 0, 0, 0), rows=(), closed_rows=(), question_rows=(),
                          freshness='fresh', errors=(), annotations=())),
        ('stale', replace(good, captured_at=time.time() - 900, freshness='stale',
                          errors=('inventory read denied: ' + 'unreadable task record ' * 28 + 'END OF INVENTORY ERROR',))),
    )
    def painted(widget):
        # Read only on-screen cell rows, not the underlying Static's unbounded Text.
        region = widget.region
        top, bottom = region.y, region.bottom
        left, right = region.x, region.right
        parent = widget.parent
        while parent is not None and parent is not app:
            clip = parent.content_region
            top, bottom = max(top, clip.y), min(bottom, clip.bottom)
            left, right = max(left, clip.x), min(right, clip.right)
            parent = parent.parent
        assert 0 <= top < bottom <= app.screen.region.bottom, (region, top, bottom)
        assert 0 <= left < right <= app.screen.region.right, (region, left, right)
        return ' '.join(' '.join(widget.render_line(y - region.y).text[left - region.x:right - region.x]
                                for y in range(top, bottom)).split())
    for state, snapshot in cases:
        selected = replace(original)
        selected.snapshot = snapshot
        envelope = fleet_view.FleetSnapshot((selected,), (snapshot,), 7, time.time())
        async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=envelope)):
            await refresh(app, pilot)
            app.push_screen(TasksScreen(selected.name))
            await pilot.pause()
            screen = app.screen
            # Include layout: a giant freshness field must not push the table/detail off-screen.
            table = screen.query_one('#tasks')
            assert table.region.height >= 3 and table.region.bottom <= screen.region.bottom, table.region
            widgets = [screen.query_one('#task-views'), screen.query_one('#task-detail'),
                       *screen.query('#task-freshness'), *screen.query('#task-provenance')]
            visible = ' '.join(painted(w) for w in widgets)
            assert snapshot.freshness in visible, (state, visible)
            if state != 'empty':
                assert 'inventory read denied' in visible, (state, visible)
            counts = painted(screen.query_one('#task-views'))
            for label in ('Open', 'Active', 'Blocker', 'Waiting', 'Questions', 'Closed'):
                if state == 'unavailable':
                    assert label + ' ?' in counts and label + ' 0' not in counts, counts
                elif state == 'empty':
                    assert label + ' 0' in counts, counts
            if state == 'unavailable':
                detail = painted(screen.query_one('#task-detail'))
                assert 'unavailable' in detail.lower() and 'No task in this view' not in detail, detail
                await pilot.press('4')  # filtering must preserve the unknown, not invent a verified empty view
                await pilot.pause()
                assert 'unavailable' in painted(screen.query_one('#task-detail')).lower()
            elif state == 'empty':
                assert table.row_count == 0
                assert 'No task in this view' in painted(screen.query_one('#task-detail'))
            else:
                assert snapshot.revision in visible and '15m ago' in visible, visible
                assert 'Open 3' in counts and table.row_count == 3, counts
                await pilot.press('i', 'end')  # keyboard users must reach the rest of a long acquisition error
                await pilot.pause()
                assert screen.query_one('#task-provenance').scroll_y > 0
                assert 'END OF INVENTORY ERROR' in painted(screen.query_one('#task-provenance'))
                pinned = painted(screen.query_one('#task-freshness'))
                assert snapshot.revision in pinned and '15m ago' in pinned, pinned
                await pilot.press('i')  # return to task navigation
                assert table.has_focus
            app.pop_screen()
            await pilot.pause()
    await refresh(app, pilot)


async def immediate_deletion():
    """Real CLI, unchanged HEAD, no timers, and a physically blocked old fleet read."""
    from pi_autowork import task_snapshot
    with tempfile.TemporaryDirectory() as folder:
        base = Path(folder)
        repo = base / 'repo'
        repo.mkdir()
        store_fixture.write_todo(repo, '## Now\n- [ ] T-1 — Only open task\n- [x] T-2 — Closed task\n')
        snap = task_snapshot.capture(repo, engine_observation={}, generation=1)
        runner = fleet_view.Runner('fixture', repo=str(repo), snapshot=snap, prepare_state='ready')
        other_repo = base / 'other'
        other_repo.mkdir()
        store_fixture.write_todo(other_repo, '## Now\n- [ ] T-1 — Same ID elsewhere\n')
        other_snap = task_snapshot.capture(other_repo, engine_observation={}, generation=1)
        other = fleet_view.Runner('other', repo=str(other_repo), snapshot=other_snap, prepare_state='ready')
        saved_record = (repo / 'tasks/items/T-1.md').read_bytes()
        envelope = fleet_view.FleetSnapshot((runner,), (snap,), 1, time.time())
        entered, release = threading.Event(), threading.Event()
        command = Path(__file__).resolve().parents[1] / 'pi_autowork/command.py'
        calls = []
        def run(argv, **kwargs):
            calls.append(argv)
            result = subprocess.run([sys.executable, str(command), *argv[1:]], **kwargs)
            return subprocess.CompletedProcess(argv, result.returncode, result.stdout + '; warning: retained worker evidence', result.stderr)
        blocked_calls = []
        def blocked(*args, **kwargs):
            blocked_calls.append(kwargs['generation'])
            entered.set()
            assert release.wait(20), 'delete fleet reader watchdog'
            return envelope
        app = FleetApp(command='aw', script='unused', state_root=base, env_dir=base,
                       runner_cmd=run, view_only=False)
        with mock.patch.object(fleet_view, 'collect_for_tui', return_value=envelope), \
                mock.patch.object(fleet_view, 'logs', return_value=''):
            async with run_pilot(app, size=(150, 45)) as pilot:
                await refresh(app, pilot)
                app.push_screen(TasksScreen('fixture'))
                await pilot.pause()
                screen = app.screen
                action = next(a for a in screen.actions(screen.current()) if a.key == 'x')
                assert action.argv[-1] == str(repo)
                await pilot.press('x', 'n')  # cancelled confirmation never reaches the command
                assert not calls and screen.query_one('#tasks').row_count == 1
                for result in (subprocess.CompletedProcess([], 1, '', 'refused'), OSError('command failed')):
                    with mock.patch.object(app, 'runner_cmd', side_effect=result if isinstance(result, Exception) else None,
                                           return_value=result):
                        app.execute(action)
                        await app.workers.wait_for_complete()
                        await pilot.pause()
                    assert screen.query_one('#tasks').row_count == 1 and not app.pending_deletions
                # A real delete may finish while its detail is open. Old detail reads
                # and a name retarget during confirmation cannot redirect its command.
                app.push_screen(TaskScreen('fixture', 'T-1'))
                await pilot.pause()
                detail_screen = app.screen
                await drain_reads(app)
                assert detail_screen.entry
                app.runners = [runner, other]
                async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', side_effect=blocked)):
                    try:
                        app.poll_refresh()
                        assert await asyncio.to_thread(entered.wait, 5)
                        app.execute(action)
                        await app.workers.wait_for_complete()
                        await pilot.pause()
                        assert 'Deletion pending commit' in str(detail_screen.query_one('#task-body').render())
                        assert 'Only open task' not in str(detail_screen.query_one('#task-body').render())
                        assert 'Section' not in str(detail_screen.query_one('#menubar').render())
                        assert not detail_screen.entry and not detail_screen.answers()
                        assert fleet_view.task_counts(app.runners[1])[-1] == 1
                        assert (other_repo / 'tasks/items/T-1.md').exists()
                        acknowledged = dict(app.pending_deletions)
                        app.action_completed(action, True)
                        assert app.pending_deletions == acknowledged, 'duplicate completion reset overlay'
                        assert len(app.reads.active) >= 1  # old physical reader still owns its slot
                        await pilot.press('escape')
                        await pilot.pause()
                        assert not (repo / 'tasks/items/T-1.md').exists()
                        assert 'T-1' in snap.store.tasks  # deletion has not changed HEAD
                        assert screen.query_one('#tasks').row_count == 0, 'successful delete retained row'
                        assert fleet_view.task_counts(app.current()) == (0, 0, 0, 0, 0, 0)
                        assert [str(c) for c in app.query_one('#runners').get_row_at(0)[2:8]] == ['0'] * 6
                        assert app.current().snapshot is snap
                        assert 'deletion pending commit' in str(screen.query_one('#task-provenance').text)
                        assert 'Deletion pending commit' in str(screen.query_one('#task-freshness').render())
                        assert 'No task in this view' in str(screen.query_one('#task-detail').render())
                        assert 'Delete' not in str(screen.query_one('#menubar').render())
                        await pilot.press('6')
                        assert screen.query_one('#tasks').row_count == 1  # closed history is independent
                        await pilot.press('x', 'y')
                        await app.workers.wait_for_complete()
                        await pilot.pause()
                        assert screen.query_one('#tasks').row_count == 0 and screen.view == 'closed'
                        assert fleet_view.task_counts(app.current())[-1] == 0
                        await pilot.press('escape')
                        app.push_screen(TasksScreen('fixture'))
                        await pilot.pause()
                        assert app.screen.query_one('#tasks').row_count == 0
                        assert len(blocked_calls) == 1, 'cancelled physical read admitted an overlapping replacement'
                    finally:
                        release.set()
                    await drain_reads(app)
                    await pilot.pause()
                    assert app.screen.query_one('#tasks').row_count == 0, 'old snapshot resurrected deletion'
                # Failed/last-good acquisition cannot acknowledge a committed deletion.
                stale = replace(snap, freshness='stale', errors=('inventory denied',))
                app.publish_fleet(fleet_view.FleetSnapshot((replace(runner, snapshot=stale),), (stale,), 9, time.time()),
                                  ((action.deletion, False, ''),), app.generation + 1)
                assert app.screen.query_one('#tasks').row_count == 0
                assert app.pending_deletions
                unknown = task_snapshot.capture(repo, engine_observation={}, generation=10)
                app.publish_fleet(fleet_view.FleetSnapshot((replace(runner, snapshot=unknown),), (unknown,), 10, time.time()),
                                  ((action.deletion, None, 'presence unavailable'),), app.generation + 1)
                assert app.pending_deletions and app.screen.query_one('#tasks').row_count == 0
                assert 'presence unavailable' in app.sub_title
                # Fresh restoration restores the original committed row, without a new HEAD.
                subprocess.run(['git', '-C', str(repo), 'restore', 'tasks'], check=True)
                fresh = task_snapshot.capture(repo, engine_observation={}, generation=10)
                restored = fleet_view.FleetSnapshot((replace(runner, snapshot=fresh),), (fresh,), 10, time.time())
                async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=restored)):
                    await refresh(app, pilot)
                assert app.screen.query_one('#tasks').row_count == 1
                assert not app.pending_deletions and fresh.revision == snap.revision
                # Delete once more, commit, then recreate before the next observation:
                # HEAD absence alone must not hide a pending-only record indefinitely.
                new_action = next(a for a in app.screen.actions(app.screen.current()) if a.key == 'x')
                retargeted_runner = replace(other, name='fixture')
                retargeted = fleet_view.FleetSnapshot((retargeted_runner,), (other_snap,), 11, time.time())
                async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=retargeted)):
                    app.push_screen(Confirm(new_action.confirm), lambda yes: yes and app.execute(new_action))
                    await pilot.pause()
                    app.runners = [retargeted_runner]  # retarget the name while confirmation is open
                    await pilot.press('y')
                    await app.workers.wait_for_complete()
                    await pilot.pause()
                    await drain_reads(app)
                    assert not (repo / 'tasks/items/T-1.md').exists()
                    assert (other_repo / 'tasks/items/T-1.md').exists()
                    assert fleet_view.task_counts(app.current())[-1] == 1
                    assert not app.current().display_deleted
                app.runners = [replace(runner, snapshot=fresh)]
                app.project_deletions()
                app.render_fleet()
                app.screen.refresh_tasks()
                subprocess.run(['git', '-C', str(repo), 'add', 'tasks'], check=True)
                subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture', '-c', 'user.email=f@example.invalid',
                                'commit', '-qm', 'delete'], check=True)
                (repo / 'tasks/items/T-1.md').write_bytes(saved_record)
                recreated = task_snapshot.capture(repo, engine_observation={}, generation=11)
                recreated_fleet = fleet_view.FleetSnapshot((replace(runner, snapshot=recreated),), (recreated,), 11, time.time())
                async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=recreated_fleet)):
                    await refresh(app, pilot)
                assert fleet_view.task_counts(app.current())[-1] == 0
                assert app.screen.query_one('#tasks').row_count == 0
                assert 'restored/recreated pending record' in fleet_view.freshness(app.current())
                (repo / 'tasks/items/T-1.md').unlink()
                committed = task_snapshot.capture(repo, engine_observation={}, generation=12)
                committed_fleet = fleet_view.FleetSnapshot((replace(runner, snapshot=committed),), (committed,), 12, time.time())
                # A poll queued before reconciliation may carry a pre-action
                # last-good capture. Retirement must invalidate that queued input.
                commit_entered, commit_release = threading.Event(), threading.Event()
                commit_calls, stale_generation = [], []
                def commit_read(*args, **kwargs):
                    commit_calls.append(kwargs['generation'])
                    if len(commit_calls) == 1:
                        commit_entered.set()
                        assert commit_release.wait(10), 'commit reconciliation watchdog'
                        return committed_fleet
                    return envelope if kwargs['generation'] in stale_generation else committed_fleet
                async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', side_effect=commit_read)):
                    try:
                        app.action_refresh()
                        assert await asyncio.to_thread(commit_entered.wait, 5)
                        queued = app.poll_refresh()
                        stale_generation.append(app.generation)
                    finally:
                        commit_release.set()
                    await drain_reads(app)
                    await pilot.pause()
                assert not app.pending_deletions and not app.current().display_deleted
                assert queued.cancelled, 'retirement retained a queued pre-reconciliation last-good input'
                assert app.screen.query_one('#tasks').row_count == 0


async def main():
    await immediate_deletion()
    # A worker's own words, without what its row already says; cut mid-word only to keep far more.
    lane = fleet_view.Lane(task='T-1', phase='verifying', detail='', attempt=1, minutes=1,
                           activity='said: T-1 committed as `abc`.', activity_age=1)
    assert doing(lane) == 'reviewer: committed as `abc`.', doing(lane)
    assert FleetApp.fit('reviewer: committed as abc', 16) == 'reviewer: commi…', FleetApp.fit('reviewer: committed as abc', 16)
    assert FleetApp.fit('one two three four', 15) == 'one two three…'
    with tempfile.TemporaryDirectory() as folder, \
            mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=str(Path(folder) / 'agent')), \
            ExitStack() as fixtures:
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
        import task_queue
        store = task_queue.store(india)
        source = dict(workspace=str(india), repository_identity=str(india / '.git'),
                      revision=store.rev, observed_at=time.time())
        observations = [dict(task=t, state=s, cause=c, reason=r, contract_hash=store.tasks[t].contract_hash,
                             admitted_contract_hash=store.tasks[t].contract_hash, attempt=1)
                        for t, s, c, r in [('TASK-034', 'waiting', '', 'on dependencies'),
                                           ('T-9', 'held', 'blocker', ''),
                                           ('TASK-040', 'waiting', '', 'wait for TASK-036 (overlapping files)')]]
        (state / 'status.json').write_text(json.dumps({
            'task_source': source, 'task_observations': observations,
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
        capture_readiness = fixtures.enter_context(browser_readiness(tree))
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
                    capture_readiness(argv[-1])
                    report = json.loads(result.stdout)
                    report['forced'] = dict(step=dict(stopped=['T-001'], set_aside=['T-002'],
                                                      landed=False, committed=True, commit='abc123'))
                    return subprocess.CompletedProcess(argv, result.returncode, json.dumps(report), result.stderr)
                result = subprocess.run([sys.executable, str(command), *argv[1:]], **kwargs)
                capture_readiness(argv[-1])
                return result
            return Result()

        app = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                       systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run,
                       browse_root=str(tree), list_models=lambda: ['openai-codex/gpt-6-luna', 'openai-codex/gpt-6.1-sol'])
        async with run_pilot(app, size=(150, 45)) as pilot:
            # A resize can paint before the first fleet read returns: say loading, not "no runners".
            app.fleet_snapshot = None
            app.runners = []
            app.render_fleet()
            shown = str(app.query_one('#detail').render())
            assert 'Loading pi-autowork runners' in shown, shown
            assert 'No pi-autowork runners yet' not in shown, shown
            await refresh(app, pilot)
            # A late or doubled button event on an already-dismissed confirmation must be a
            # no-op, not pop the last screen and crash the TUI (ScreenStackError, 2026-10-22).
            late = Confirm('late confirmation')
            late.on_button_pressed(mock.Mock(button=mock.Mock(id='no')))
            late.action_answer(True)
            assert late.is_current is False
            assert app.query_one('#runners').row_count == 1
            detail = str(app.query_one('#detail').render())
            # TOOLSET-166-b4: the verdict first, then why tasks wait, grouped.
            assert detail.lstrip().startswith('india  Blocker — 1: T-9 Blocker · Agent repair'), detail
            assert 'on you' not in detail and 'Model      gpt-6.1-sol' in detail, detail
            assert 'Waiting    2: 1 on dependencies · 1 wait for TASK-036 (overlapping files)' in detail, detail
            # Needs-decision membership is not a count of unanswered owner questions.
            # A recorded deferral must not be advertised as a fresh request for approval.
            original_snapshot = app.current().snapshot
            app.current().snapshot = replace(original_snapshot, counts=(0, 0, 2, 1, 1, 4))
            app.show_detail()
            decision_detail = str(app.query_one('#detail').render())
            assert '1 in Needs decision' in decision_detail, decision_detail
            assert 'for your decision' not in decision_detail, decision_detail
            app.current().snapshot = original_snapshot
            app.show_detail()
            runners = app.query_one('#runners')
            # TOOLSET-289-71 (test_runner_columns): the owner's four headlines.
            assert [str(c.label) for c in runners.columns.values()] == ['Runner', 'State', 'Active', 'Mergeable',
                                                                        'Waiting', 'Blocker', 'Decision', 'Total',
                                                                        'Needs', 'Now']
            assert [str(c) for c in runners.get_row_at(0)[2:8]] == ['0', '0', '2', '1', '0', '3']
            assert '1 on dependencies' in str(runners.get_row_at(0)[8]), runners.get_row_at(0)
            assert 'Tasks      3 open · 0 active · 0 mergeable · 2 waiting · 1 blocker' in detail, detail
            assert 'revision ' + store.rev in detail and 'execution fresh' in detail, detail
            assert 'Push       disabled' in detail, detail  # no saved grant: local only
            await blocked_readers(app, pilot)
            # Label readers use real fixture snapshots, not repeated live preparation
            # probes whose subprocess cost depends on the rest of the offline suite.
            async with patched_reads(app, mock.patch.object(fleet_view.task_prepare, 'prepare',
                    side_effect=AssertionError('live preparation leaked into browser labels'))):
                await pilot.press('n')
                await pilot.pause()
                browser = app.screen
                assert isinstance(browser, BrowseScreen), browser
                labels = browser.query_one('#tree').readiness_cache
                async def labels_loaded():
                    # DirectoryTree's worker may not have submitted the label read
                    # yet: an empty physical queue alone is not label readiness.
                    while tree / 'ready' not in labels and not browser.__dict__.get('_read_errors'):
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(labels_loaded(), 10)
                await drain_reads(app)
                errors = browser.__dict__.get('_read_errors', {})
                assert not errors, errors
                assert labels[tree / 'ready'].ready, labels
                assert labels[tree / 'legacy'].problems == ['legacy planning'], labels
                await pilot.press('escape')
                await pilot.pause()
                # A directory-label read may finish while BrowseScreen is current but
                # still completing its Mount dispatch. Keep that accepted result for
                # post-mount publication instead of dropping it with the screen guard.
                forced = {}
                original_read_labels, original_mount = BrowseScreen.read_labels, BrowseScreen.on_mount
                def capture_labels(screen, paths):
                    forced['token'] = original_read_labels(screen, paths)
                    return forced['token']
                async def held_mount(screen):
                    original_mount(screen)
                    token = forced.get('token')
                    assert token is not None, 'directory-label read was not submitted while mounting'
                    await asyncio.wait_for(token.wait(), 10)
                    assert tree / 'ready' not in screen.query_one('#tree').readiness_cache, \
                        'directory labels published before the screen finished mounting'
                with mock.patch.object(BrowseScreen, 'read_labels', new=capture_labels), \
                        mock.patch.object(BrowseScreen, 'on_mount', new=held_mount):
                    await pilot.press('n')
                    await pilot.pause()
                    browser = app.screen
                    assert isinstance(browser, BrowseScreen), browser
                    forced_labels = browser.query_one('#tree').readiness_cache
                    async def forced_loaded():
                        while tree / 'ready' not in forced_labels and not browser.__dict__.get('_read_errors'):
                            await asyncio.sleep(0.01)
                    await asyncio.wait_for(forced_loaded(), 10)
                    await drain_reads(app)
                    assert not browser.__dict__.get('_read_errors'), browser.__dict__.get('_read_errors')
                    assert forced_labels[tree / 'ready'].ready, forced_labels
                    await pilot.press('escape')
                    await pilot.pause()
            # Blockers must accept a real immutable committed snapshot, while detaching
            # mutable runner data for its background report read.
            source = app.current()
            await pilot.press('b')
            await app.workers.wait_for_complete()
            await pilot.pause()
            assert isinstance(app.screen, BlockersScreen)
            assert app.screen.runner is not source and app.screen.runner.snapshot is source.snapshot
            report = app.screen.query_one('#blockers-text').text
            assert 'Repository: ' + source.repo in report and 'T-9' in report, report
            await pilot.press('escape')
            assert len(app.screen_stack) == 1
            # Raw orphan activity is visible, but cannot contradict committed counts
            # in the verdict or label an unmatched slot as verified/Mergeable.
            original_runner = app.current()
            observed = replace(original_runner, state='working', lanes=[fleet_view.Lane('ORPHAN', 'integrated')])
            fleet_view.snapshot_for(observed)
            envelope = fleet_view.FleetSnapshot((observed,), (observed.snapshot,), 7, time.time())
            async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=envelope)):
                await refresh(app, pilot)
                shown = str(app.query_one('#detail').render())
                assert '1 mergeable' not in shown and '2 waiting' in shown, shown
                assert str(app.query_one('#lanes').get_row_at(0)[1]).startswith('Annotation'), shown
                observed.snapshot = replace(observed.snapshot, counts=None, rows=(), freshness='unavailable',
                                            errors=('inventory read denied',))
                await refresh(app, pilot)
                shown = str(app.query_one('#detail').render())
                assert [str(c) for c in app.query_one('#runners').get_row_at(0)[2:8]] == ['?'] * 6
                assert 'unknown / unavailable' in shown and 'inventory read denied' in shown, shown
                observed.snapshot = replace(original_runner.snapshot, captured_at=time.time() - 900, freshness='stale')
                await refresh(app, pilot)
                shown = str(app.query_one('#detail').render())
                assert 'stale · revision ' + store.rev in shown and '15m' in shown, shown
            await refresh(app, pilot)
            await task_inventory_viewport(app, pilot)
            settings = env / 'india.env'
            saved = settings.read_text()
            for value, label in (('1', 'enabled'), ('0', 'disabled')):
                settings.write_text(saved + f'PI_AUTOWORK_PUSH={value}\n')
                await refresh(app, pilot)
                detail = str(app.query_one('#detail').render())
                assert f'Push       {label}' in detail, detail
                assert settings.read_text() == saved + f'PI_AUTOWORK_PUSH={value}\n'
            # The keys, in the menu bar at the top (a GUI app's "File Edit View"), each word's first
            # letter highlighted in it; one key per action. The detail pane holds no keys.
            assert 'Quit' not in detail, detail
            menubar = app.query_one('#menubar')
            assert menubar.region.y < app.query_one('#runners').region.y, 'the menu bar is above the runners'
            hints = menubar.render()
            assert str(hints).rstrip().endswith('Log  Pause  Stop  Restart  Model  Tasks  g Plan  Details  Blockers  New  Quit'), str(hints)
            marked = {str(hints)[span.start:span.end] for span in hints.spans if 'underline' in str(span.style)}
            assert marked == set('LPSRMTBNQgi'), marked
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
                            ('running', 'stalled', 'Log  Pause  Stop  Restart  Model  Tasks  g Plan  Details  Blockers  New  Quit'),
                            ('stopped', 'not running', 'Log  Play  Model  Tasks  Uninstall  g Plan  Details  Blockers  New  Quit'),
                            ('stopped', 'paused', 'Log  Play  Model  Tasks  Uninstall  g Plan  Details  Blockers  New  Quit'),
                            ('', '', 'g Plan  New  Quit')):
                        selected = replace(runner, service=service, state=state_name) if service else None
                        envelope = fleet_view.FleetSnapshot((selected,) if selected else (),
                            (fleet_view.snapshot_for(selected),) if selected else (), 1, time.time())
                        async with patched_reads(app, mock.patch.object(fleet_view, 'collect_for_tui', return_value=envelope),
                                mock.patch.object(portal, 'probe', side_effect=AssertionError('fleet key probed Portal'))):
                            await refresh(app, pilot)
                            expected = ('view only  Log  Details  Blockers  Quit' if selected else '') if view_only else menu
                            assert str(menubar.render()).strip() == expected, menubar.render()
                            painted = ' '.join(menubar.render_line(y).text for y in range(menubar.content_size.height))
                            assert ' '.join(painted.split()) == ' '.join(expected.split()), painted
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
            await refresh(app, pilot)
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
            await refresh(app, pilot)  # publish questions and rows in the same completed capture
            await pilot.press('t')                      # Tasks: every open task in priority order
            await pilot.pause()
            assert isinstance(app.screen, TasksScreen), app.screen
            fleet_timer = pilot.read_timers[app.poll_refresh]
            generation = app.reader.applied['fleet']
            try:
                fleet_timer.resume()
                await pilot.pause(REFRESH + 0.5)        # the main screen's refresh runs beneath it
            finally:
                fleet_timer.pause()
                await drain_reads(app)
            assert isinstance(app.screen, TasksScreen), app.screen
            assert app.reader.applied['fleet'] > generation, read_state(app)
            tasks = app.screen.query_one('#tasks')
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['TASK-034', 'T-9', 'TASK-040']
            assert str(tasks.get_row_at(0)[2]) == 'Ship it'  # its short name
            await pilot.press('3')                      # the Held view
            await pilot.pause()
            assert [str(tasks.get_row_at(i)[1]) for i in range(tasks.row_count)] == ['T-9'], tasks.row_count
            keys = str(app.screen.query_one('#menubar').render())
            assert keys.rstrip().endswith('enter Open  Decide  g Discuss  Investigate  Up  Down  Section  Clear  Aside  x Delete  New  Info  esc Back'), keys
            await pilot.press('x')                      # delete asks first; decline here
            await pilot.pause()
            assert isinstance(app.screen, Confirm), app.screen
            await pilot.press('n')
            await pilot.pause()
            assert isinstance(app.screen, TasksScreen), app.screen
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
            await drain_reads(app)
            shown = lines()  # a log: all 30 actions, oldest first, each with its time
            assert len(shown) == 30 and 'step 0' in shown[0] and 'step 29' in shown[-1], shown
            assert shown[0][:8].count(':') == 2, shown[0]
            with transcript.open('a') as stream:
                stream.write(step(30))
            await app.screen.refresh_actions().wait()
            await pilot.pause()
            after = lines()  # the new action is appended at the bottom; nothing above it is redrawn
            assert after[:30] == shown and 'step 30' in after[-1] and len(after) == 31, after
            await pilot.resize_terminal(80, 18)
            actions_log = app.screen.query_one('#worker-actions')
            actions_log.scroll_to(y=3, animate=False, force=True)
            await pilot.pause()
            at = actions_log.scroll_y
            assert at == 3 and not actions_log.is_vertical_scroll_end
            await pilot.press('w')
            await pilot.pause()
            assert actions_log.scroll_y == at, 'cached wrap lost scroll position'
            await pilot.resize_terminal(90, 18)
            await pilot.pause()
            assert actions_log.scroll_y == at, 'cached resize lost scroll position'
            await pilot.resize_terminal(150, 45)
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
                await pilot.pause()  # dispatch NodeHighlighted before waiting for its read
                await drain_reads(app)
                await pilot.pause()
                assert screen.chosen and not screen.chosen.ready, screen.chosen
                before = len(calls)
                task_files = lambda: {str(p): p.read_bytes() for p in (tree / name / 'tasks').rglob('*.md')}
                original_tasks = task_files()
                await pilot.press('p')
                await drain_reads(app)
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
                    await drain_reads(app)
                    await pilot.pause()
                if name == 'fresh':  # Embedded Plan opens without launching a model or service.
                    from pi_autowork.planning_ui import PlanScreen
                    app.screen.query_one('#plan').press()
                    await pilot.pause()
                    assert isinstance(app.screen, PlanScreen) and len(calls) == before, calls
                    assert task_files() == original_tasks
                    await pilot.press('escape')
                    await pilot.pause()
                    assert app.screen is screen
                    await pilot.press('p')
                    await drain_reads(app)
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
                    await drain_reads(app)
                    await pilot.pause()
                    app.screen.query_one('#force').press()
                    await pilot.pause()
                    await pilot.press('y')
                    await pilot.pause()
                # DirectoryTree keeps a loader worker alive while the browser is open.
                for worker in list(app.workers):
                    if worker.group == 'prepare':
                        await worker.wait()
                await drain_reads(app)
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
                        assert '/docs-sync' in info and 'no heading is marked Status: Accepted' in info, info
                    elif outcome == 'MIGRATION_DEFERRED':
                        assert 'conversion deferred' in info, info
                if starts:
                    await pilot.press('y')              # starting still asks for confirmation
                    await pilot.pause()
                    await drain_reads(app)             # confirmed Start first reads readiness
                    # Closing Browse cancels its DirectoryTree loader; only the
                    # action worker must complete, not that retired loader.
                    for worker in list(app.workers):
                        if worker.group == 'actions':
                            await worker.wait()
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
            await drain_reads(app)
            await pilot.pause()
            assert screen.chosen.ready, screen.chosen
            await pilot.press('p')
            await drain_reads(app)
            await pilot.pause()
            # A discarded confirmed readiness read must release duplicate-Start
            # protection, even if the browser closed before physical completion.
            entered, release = threading.Event(), threading.Event()
            original_readiness = fleet_view.readiness
            def stale_start(path):
                entered.set()
                assert release.wait(10), 'Start readiness watchdog'
                return original_readiness(path)
            with mock.patch.object(fleet_view, 'readiness', side_effect=stale_start):
                try:
                    await pilot.press('y')
                    assert await asyncio.to_thread(entered.wait, 5)
                    await pilot.press('escape')
                    assert len(app.screen_stack) == 1
                finally:
                    release.set()
                    await drain_reads(app)
                await pilot.pause()
            await pilot.press('n')
            await pilot.pause()
            screen = app.screen
            tree_widget = screen.query_one('#tree')
            tree_widget.select_node(next(n for n in tree_widget.root.children if n.data.path.name == 'ready'))
            await pilot.pause()
            await drain_reads(app)
            await pilot.pause()
            await pilot.press('p')
            await drain_reads(app)
            await pilot.pause()
            assert isinstance(app.screen, Confirm), 'closed readiness left Start permanently busy'
            await pilot.press('y')
            await pilot.pause()
            await drain_reads(app)
            for worker in list(app.workers):
                if worker.group == 'actions':
                    await worker.wait()
            assert calls[-1] == ['aw', 'start', str(tree / 'ready')], calls
        narrow = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=None, runner_cmd=run,
                          browse_root=str(tree))
        async with run_pilot(narrow, size=(80, 30)) as pilot:   # an 80-column terminal: wrapped, not cut
            await refresh(narrow, pilot)
            words = ' '.join(str(narrow.query_one('#detail').render()).split())
            assert 'Blocker — 1: T-9 Blocker · Agent repair' in words and 'on you' not in words, words
            assert 'Waiting 2: 1 on dependencies · 1 wait for TASK-036 (overlapping files)' in words, words
            # Every count stays on screen: the text columns shrink instead (they scrolled off before).
            table = narrow.query_one('#runners')
            width = sum(c.get_render_width(table) for c in table.columns.values())
            assert width <= 80, (width, [str(c) for c in table.get_row_at(0)])
            await task_inventory_viewport(narrow, pilot)
            await pilot.press('n')
            await pilot.pause()
            tree_widget = narrow.screen.query_one('#tree')
            tree_widget.select_node(next(n for n in tree_widget.root.children if n.data.path.name == 'busy'))
            await pilot.pause()
            await pilot.press('p')
            await drain_reads(narrow)
            await pilot.pause()
            dialog = narrow.screen.query_one('PrepareRepository > Vertical')
            assert dialog.region.x >= 0 and dialog.region.right <= 80, dialog.region
            for button in narrow.screen.query('Button'):
                assert button.region.right <= 80, button.region
            # A browser may reserve Tab for its own focus traversal; arrows must reach every choice.
            assert narrow.screen.focused.id == 'prepare', narrow.screen.focused
            await pilot.press('right')
            await pilot.pause()
            assert narrow.screen.focused.id == 'prepare-start', narrow.screen.focused
            await pilot.press('left')
            await pilot.pause()
            assert narrow.screen.focused.id == 'prepare', narrow.screen.focused
            await pilot.press('escape')
            await pilot.pause()
            screen = narrow.screen
            attempts = [f'TASK-{i:03d}' for i in range(20)]  # guarantee overflow at 80x30
            screen.prepared(str(tree / 'busy'), dict(
                outcome='MIGRATION_BLOCKED', refusals=['worker still recorded', 'consumer still tracked'],
                forced=dict(step=dict(stopped=attempts, set_aside=attempts, landed=False,
                                      committed=True, commit='abc123')),
                next='Resolve the preservation collision, then retry Force.'), False)
            await drain_reads(narrow)  # prepared() publishes its pane after the readiness read
            await pilot.pause()
            info = screen.query_one('#info')
            pane = info.parent
            await pilot.press('tab', 'end')  # keyboard users can reach the complete report
            await pilot.pause()
            assert pane.scroll_y > 0, ('long forced reports must be scroll-accessible',
                                       narrow.focused, pane.region, pane.max_scroll_y, info.region)
            assert pane.content_region.y < info.region.bottom <= pane.content_region.bottom, (
                info.region, pane.content_region)
            assert 'commit: abc123' in str(info.render()) and 'retry Force.' in str(info.render())
            await pilot.press('escape')
        viewer = FleetApp(command='aw', script='pa.sh', state_root=base / 'state', env_dir=env,
                          systemctl=str(systemctl), journalctl=str(journal), agent=['claude'], runner_cmd=run,
                          view_only=True)
        before = len(calls)
        async with run_pilot(viewer, size=(140, 40)) as pilot:
            await refresh(viewer, pilot)
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
        async with run_pilot(reloader, size=(140, 40)) as pilot:
            await refresh(reloader, pilot)
            await reloader.reload_if_updated().wait()
            await pilot.pause()
            assert reloader.return_value is None    # unchanged code: it stays
            await pilot.press('enter')
            await pilot.pause()
            reloader.code = -1                      # an update replaced the files
            await reloader.reload_if_updated().wait()
            await pilot.pause()
            assert reloader.return_value is None    # the log screen is open: not now
            await pilot.press('escape')
            await pilot.pause()
            await reloader.reload_if_updated().wait()
            await pilot.pause()
        assert reloader.return_value == 'reload'
    print('PILOT OK')


asyncio.run(main())
