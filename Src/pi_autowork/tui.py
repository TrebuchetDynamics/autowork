"""`autowork`: the live view of every pi-autowork runner, with controls.

Bare `autowork` on a terminal runs this through `uv run --with textual==8.2.8`, so the
runner itself stays standard-library only. It reads runner state (status.json, engine
slots, systemd, logs, Pi transcripts) every few seconds and calls no model. Every
action runs an `autowork` command (or the runner script); there is no second way to
change a runner. `d` browses directories and starts a service for a repository that
has its tasks/ store committed on its main branch.

    python3 tui.py --command PATH --script PATH [--view-only]
"""
from pi_autowork.layout import LAYOUT
import argparse
from copy import deepcopy as _deepcopy
import asyncio
from dataclasses import replace
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import uuid

from pi_autowork import fleet_view, portal, tui_reads, blockers_report  # noqa: E402
from pi_autowork.planning_ui import PlanScreen, DecisionPrompt, QuestionPicker  # noqa: E402
from pi_autowork.tui_dialogs import Confirm  # noqa: E402

from rich.text import Text  # noqa: E402  (installed with textual)
from rich.style import Style  # noqa: E402
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.screen import ModalScreen, Screen  # noqa: E402
from textual.widgets import (Button, DataTable, DirectoryTree, Header, Input, Label, OptionList,  # noqa: E402
                             RichLog, Select, Static, TextArea)

REFRESH = 3.0
LOG_REFRESH = 5.0
CODE_CHECK = 30.0
CODE = Path(__file__).resolve().parent


def code_stamp():
    """The newest change to the TUI's own code: an update replaces these files, and a TUI left
    open kept showing the old release's readings for hours."""
    try:
        return max(path.stat().st_mtime for path in CODE.glob('*.py'))
    except (OSError, ValueError):
        return 0
QUESTIONS_SHOWN = 3


def read_input(value):
    """Detach mutable runner data; frozen TaskSnapshots are safe to share with readers."""
    runners = value.runners if isinstance(value, fleet_view.FleetSnapshot) else (value,)
    snapshots = list(value.snapshots) if isinstance(value, fleet_view.FleetSnapshot) else []
    snapshots.extend(r.snapshot for r in runners if isinstance(r, fleet_view.Runner) and r.snapshot is not None)
    return _deepcopy(value, {id(snapshot): snapshot for snapshot in snapshots})


def hotkeys(text, keys, click_actions=None):
    """Append 'Log  Pause  Stop', each word's key letter highlighted in it (the first letter
    by convention; a key the word lacks is shown before it)."""
    for number, (key, label) in enumerate(keys):
        text.append('  ' if number else '')
        start = len(text)
        at = label.lower().find(key.lower())
        if at < 0:
            text.append(key, style='bold underline cyan')
            text.append(' ' + label)
        else:
            text.append(label[:at])
            text.append(label[at], style='bold underline cyan')
            text.append(label[at + 1:])
        if click_actions and key in click_actions:
            text.stylize(Style(meta={'@click': click_actions[key]}), start, len(text))


class MenuBar(Static):
    """A screen's keys on one line at the very top, under the title, as a GUI app's menu bar
    ("File Edit View"), each word's key letter highlighted; every screen has one."""
    DEFAULT_CSS = 'MenuBar { dock: top; height: 1; background: $boost; padding: 0 1; }'

    def show(self, keys, prefix='', click_actions=None):
        text = Text(no_wrap=True, overflow='ellipsis')
        if prefix:
            text.append(prefix + '  ', style='dim')
        hotkeys(text, keys, click_actions)
        self.update(text)


def detail_row(text, label, value, style=''):
    """One 'Label      value' line of a detail pane: the label dim in a fixed column."""
    text.append(f' {label:<11}', style='dim')
    text.append(value + '\n', style=style)


def tilde(path):
    home = str(Path.home())
    return '~' + path[len(home):] if path and (path == home or path.startswith(home + '/')) else path


def doing(lane):
    """What a worker is doing, without what the row already says: its own task ID after
    "said:", and "said:" after "reviewer:"."""
    text = ' '.join(fleet_view.doing(lane).split())
    text = text.replace('reviewer: said: ', 'reviewer: ', 1)
    for prefix in ('said: ', 'reviewer: '):
        if text.startswith(prefix + lane.task):
            text = prefix + text[len(prefix + lane.task):].lstrip(' :,')
    return text


class ReadScreen:
    """Owner-bound subscriptions; workers never receive widgets or the runner list."""
    def read(self, kind, identity, loader, apply, failed=None):
        if not self.is_current:
            return None
        if not hasattr(self, '_reader'):
            self._reader = self.app.reads.owner(self._read_done)
        token = self._reader.request(kind, identity, (self.app.read_epoch, getattr(self, '_read_epoch', 0)), loader)
        token.apply, token.failed = apply, failed
        return token

    def _read_done(self, token, value, error):
        if not self.app.is_running or not self.is_mounted or not self.is_current:
            return
        errors = self.__dict__.setdefault('_read_errors', {})
        if error:
            errors[token.kind] = str(error)
            self.sub_title = ' · '.join(f'{kind}: stale / unavailable: {message}' for kind, message in errors.items())
            self.notify(self.sub_title, severity='warning')
            if token.failed:
                token.failed(error)
        else:
            errors.pop(token.kind, None)
            self.sub_title = ' · '.join(f'{kind}: stale / unavailable: {message}' for kind, message in errors.items())
            token.apply(value)

    def invalidate_read(self):
        self._read_epoch = getattr(self, '_read_epoch', 0) + 1
        if hasattr(self, '_reader'):
            self._reader.invalidate()

    def on_screen_suspend(self):
        self.invalidate_read()

    def on_screen_resume(self):
        if self.is_mounted:
            for method in ('refresh_record', 'refresh_tasks', 'refresh_actions', 'refresh_log'):
                if hasattr(self, method):
                    getattr(self, method)()
                    break

    def on_unmount(self):
        if hasattr(self, '_reader'):
            self._reader.close()


class DecisionScreen(ReadScreen, DecisionPrompt):
    """Read the current record off-thread; save through the CLI with its exact revision."""
    def __init__(self, runner, task, question=None):
        context = (f'Question (displayed inventory): {question.needs}\n'
                   f'Unblocks {question.unblocks} task(s). Suggested answer: {question.answer or "None supplied"}'
                   if question else 'Owner direction for this task.')
        store = runner.snapshot.store if runner.snapshot is not None else None
        dependents = sorted(t.id for t in store.tasks.values() if t.status == 'open' and task in t.depends_on) if store else []
        context += '\nDependent tasks (committed snapshot): ' + (
            ', '.join(dependents) if dependents else ('None' if store else 'unavailable'))
        super().__init__(task, context, loading=True)
        self.runner_name, self.repo = runner.name, runner.repo
        self.record = None

    def on_mount(self):
        super().on_mount()
        self.refresh_record()

    def refresh_record(self):
        # Never rebind an edited draft to newer bytes; only replace an invalidated initial read.
        if self.record is not None or self.saving:
            return
        command, run, repo, task = self.app.command, self.app.runner_cmd, self.repo, self.task_id
        def load():
            result = run([command, 'tasks', 'show', task, '--worktree', repo],
                         capture_output=True, text=True, timeout=30)
            if result.returncode:
                raise ValueError((result.stderr or result.stdout or 'Task unavailable').strip())
            return json.loads(result.stdout)
        self.read('answer', (repo, task), load, self.loaded_record, self.load_failed)

    def load_failed(self, error):
        self.ready = False
        self.query_one('#decision-save', Button).disabled = True
        self.query_one('#decision-status', Static).update(f'Cannot answer: {error}. Close and reopen after refreshing.')

    def loaded_record(self, record):
        revision = record.get('record_revision') if isinstance(record, dict) else None
        if (not isinstance(revision, str) or len(revision) != 64
                or any(c not in '0123456789abcdef' for c in revision)
                or record.get('id') != self.task_id or record.get('status') != 'open'):
            self.load_failed('task is closed, missing, or its revision is unavailable')
            return
        self.record, self.ready = record, True
        previous = '\n'.join(line for line in record.get('notes', '').splitlines()
                             if line.startswith('- Owner decision:'))
        self.query_one('#decision-context', TextArea).load_text(
            self.context + f'\n\n{self.task_id}: {record.get("title", "")}\n'
            f'Current working record: {record.get("section", "unknown")} · '
            f'ownership {record.get("ownership", "unknown")} · live {record.get("live", "denied")}\n'
            + record.get('scope', '') + ('\n' + previous if previous else ''))
        self.query_one('#decision-save', Button).disabled = False
        self.query_one('#decision-status', Static).update(
            'Saves locally, pending commit. Does not grant live permission, clear holds or verify completion.')

    def submit(self, value):
        runner = next((r for r in self.app.runners if (r.name, r.repo) == (self.runner_name, self.repo)), None)
        if self.app.view_only or runner is None or self.app.deletion_pending(runner, self.task_id):
            self.load_failed('task actions are no longer available')
            return
        argv = [self.app.command, 'tasks', 'decide', self.task_id, value['text'], self.repo,
                '--expect', self.record['record_revision']]
        if value['section']:
            argv += ['--section', value['section']]
        self.saving = True
        self.query_one('#decision-text', TextArea).disabled = True
        self.query_one('#decision-section', Select).disabled = True
        self.query_one('#decision-save', Button).disabled = True
        self.query_one('#decision-cancel', Button).disabled = True
        self.query_one('#decision-status', Static).update('Saving locally… wait for the result; no commit or runner action.')
        self.app.execute(fleet_view.Action('e', f'Answer {self.task_id}', argv), on_complete=self.saved)

    def saved(self, ok, message):
        if not self.is_mounted:
            return
        self.saving = False
        if ok:
            self.dismiss(None)
        else:
            self.query_one('#decision-text', TextArea).disabled = False
            self.query_one('#decision-section', Select).disabled = False
            self.query_one('#decision-save', Button).disabled = False
            self.query_one('#decision-cancel', Button).disabled = False
            self.query_one('#decision-text', TextArea).focus()
            self.query_one('#decision-status', Static).update(
                f'Save failed: {message}. Draft kept; close and reopen if the record changed.')


class TextPrompt(ModalScreen[str]):
    """One line of the owner's words; Enter saves, Escape cancels."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    TextPrompt { align: center middle; }
    TextPrompt > Vertical { width: 80; height: auto; border: thick $accent; background: $surface; padding: 1 2; }
    '''

    def __init__(self, title, hint):
        super().__init__()
        self.title_text, self.hint = title, hint

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(Text(self.title_text, style='bold'))
            yield Label(Text(self.hint, style='dim'))
            yield Input(placeholder='Enter saves, Esc cancels', id='words')

    def on_input_submitted(self, event):
        self.dismiss(' '.join(event.value.split()) or None)

    def action_cancel(self):
        self.dismiss(None)


class PickSection(ModalScreen[str]):
    """Now, Next or Needs decision."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    PickSection { align: center middle; }
    PickSection > Vertical { width: 50; height: auto; border: thick $accent; background: $surface; padding: 1 2; }
    '''
    SECTIONS = ('Now', 'Next', 'Needs decision')

    def __init__(self, task):
        super().__init__()
        self.task_id = task

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(f'Move {self.task_id} to:')
            yield OptionList(*self.SECTIONS)

    def on_option_list_option_selected(self, event):
        self.dismiss(self.SECTIONS[event.option_index])

    def action_cancel(self):
        self.dismiss(None)


class NewTask(ReadScreen, ModalScreen[dict]):
    """A new task's title, short title, goal and section, and optionally its scope and acceptance."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    NewTask { align: center middle; }
    NewTask > VerticalScroll { width: 90; height: auto; max-height: 90%; border: thick $accent; background: $surface; padding: 1 2; }
    NewTask Input, NewTask Select { margin-bottom: 1; }
    NewTask Horizontal { height: auto; align-horizontal: right; }
    NewTask Button { margin-left: 2; }
    '''

    def __init__(self, goals, runner=None):
        super().__init__()
        self.goals, self.goal_runner = goals, read_input(runner)

    def on_mount(self):
        if self.goal_runner:
            runner = self.goal_runner
            self.read('goals', runner.repo, lambda: fleet_view.open_goals(runner), self.loaded_goals)

    def loaded_goals(self, goals):
        self.goals = goals
        self.query_one('#goal', Select).set_options([(f'{gid}  {title}'[:70], gid) for gid, title in goals])

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label(Text('New task', style='bold'))
            yield Input(placeholder='Title: the outcome, in a sentence', id='title')
            yield Input(placeholder='Short title for task lists (at most 40 characters)', id='short', max_length=40)
            yield Select([(f'{gid}  {title}'[:70], gid) for gid, title in self.goals], prompt='Goal', id='goal')
            yield Select([(name, name) for name in PickSection.SECTIONS], value='Next', allow_blank=False, id='section')
            yield Input(placeholder='Scope (optional)', id='scope')
            yield Input(placeholder='Acceptance (optional): the test that proves it', id='acceptance')
            with Horizontal():
                yield Button('Add', variant='primary', id='add')
                yield Button('Cancel', id='cancel')

    def on_button_pressed(self, event):
        if event.button.id == 'cancel':
            self.dismiss(None)
            return
        value = {key: ' '.join(str(self.query_one(f'#{key}').value or '').split())
                 for key in ('title', 'short', 'scope', 'acceptance')}
        goal = self.query_one('#goal', Select).value
        if not value['title'] or not value['short'] or goal in (None, Select.BLANK):
            self.notify('A new task needs a title, a short title and a goal.', severity='warning')
            return
        self.dismiss(dict(value, goal=goal, section=self.query_one('#section', Select).value))

    def action_cancel(self):
        self.dismiss(None)


class PortalSetup(ModalScreen[dict]):
    """Preview a selected provider; a separate confirmation owns the write."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    PortalSetup { align: center middle; }
    PortalSetup > VerticalScroll { width: 86; height: auto; max-height: 95%; border: thick $accent; background: $surface; padding: 1 2; }
    PortalSetup Input { margin-bottom: 1; }
    PortalSetup Horizontal { height: auto; align-horizontal: right; }
    '''

    def compose(self) -> ComposeResult:
        with VerticalScroll():
            yield Label('Nous Portal through the local Hermes proxy')
            yield Label('No login, proxy start, model request or service change. Preview before consent.')
            yield Input(value='nous-local', placeholder='Selected Pi provider entry', id='portal-provider')
            yield Input(placeholder='Exact model ID from your Portal plan', id='portal-model')
            yield Input(value=portal.DEFAULT_ENDPOINT, placeholder='Loopback /v1 endpoint', id='portal-endpoint')
            yield Static('', id='portal-result', markup=False)
            with Horizontal():
                yield Button('Preview', id='portal-preview', variant='primary')
                yield Button('Cancel', id='portal-cancel')

    async def on_button_pressed(self, event):
        if event.button.id == 'portal-cancel':
            self.dismiss(None)
            return
        if event.button.id != 'portal-preview':
            return
        button = self.query_one('#portal-preview', Button)
        button.disabled = True
        try:
            proposal = await asyncio.to_thread(portal.propose,
                self.query_one('#portal-provider', Input).value,
                self.query_one('#portal-model', Input).value,
                self.query_one('#portal-endpoint', Input).value)
        except portal.SetupError as error:
            self.query_one('#portal-result', Static).update(str(error))
        else:
            self.query_one('#portal-result', Static).update(proposal.text())

            def consent(yes):
                if not yes:
                    self.query_one('#portal-result', Static).update(proposal.text() + '\nDeclined: no changes made.')
                    return
                try:
                    self.dismiss(portal.apply(proposal))
                except portal.SetupError as error:
                    self.query_one('#portal-result', Static).update(str(error))
            self.app.push_screen(Confirm(Text(proposal.text() + '\nApply this provider edit only?')), consent)
        finally:
            button.disabled = False

    def action_cancel(self):
        self.dismiss(None)


class PickModel(ReadScreen, ModalScreen[str]):
    """Choose a model from Pi's own list; type to filter."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    PickModel { align: center middle; }
    PickModel > Vertical { width: 80; height: 80%; border: thick $accent; background: $surface; padding: 1 2; }
    PickModel OptionList { height: 1fr; }
    '''

    def __init__(self, title, models, current, loader=None, identity=None):
        super().__init__()
        self.title_text, self.models, self.current = title, models, current
        self.loader, self.identity = loader, identity

    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        with Vertical():
            yield Label(f'{self.title_text} (now {self.current})')
            yield Input(placeholder='filter, e.g. india or deepseek', id='filter')
            yield OptionList(*self.models, id='models')

    def on_mount(self):
        self.shown = list(self.models)
        if self.loader:
            self.read('models', self.identity, self.loader, self.loaded_models)

    def loaded_models(self, models):
        self.models = models
        if not models:
            self.notify('Pi listed no models (pi --list-models).', severity='error')
        self.on_input_changed(self.query_one('#filter', Input))

    def on_input_changed(self, event):
        self.shown = [m for m in self.models if event.value.lower() in m.lower()]
        options = self.query_one('#models', OptionList)
        options.clear_options()
        options.add_options(self.shown)

    def on_input_submitted(self, event):
        """Enter in the filter takes the first match."""
        if self.shown:
            self.dismiss(self.shown[0])

    def on_key(self, event):
        if event.key == 'down' and self.focused is self.query_one('#filter'):
            self.query_one('#models', OptionList).focus()

    def on_option_list_option_selected(self, event):
        self.dismiss(str(event.option.prompt))

    def action_cancel(self):
        self.dismiss(None)


class LogScreen(ReadScreen, Screen):
    """A runner's output, full screen, refreshed."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'back')]

    def __init__(self, runner, logs):
        super().__init__()
        self.runner, self.logs = runner, logs

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield RichLog(id='full-log', wrap=True, highlight=False, markup=False)

    def on_mount(self):
        self.title = f'{self.runner.name}: log'
        self.query_one('#menubar', MenuBar).show([('esc', 'Back')])
        self.refresh_log()
        self.set_interval(LOG_REFRESH, self.refresh_log)

    def refresh_log(self):
        runner, logs = read_input(self.runner), self.logs
        return self.read('full-log', (runner.name, runner.repo),
                         lambda: fleet_view.log_lines(logs(runner, 1000)), self.show_log)

    def show_log(self, lines):
        if lines == getattr(self, '_lines', None):
            return
        self._lines = lines
        log = self.query_one('#full-log', RichLog)
        follow, at = log.is_vertical_scroll_end, log.scroll_y
        log.clear()
        for line, style in lines:
            log.write(Text(line, style=style), scroll_end=follow)
        if not lines:
            log.write('(no output yet)', scroll_end=follow)
        if not follow:
            log.call_after_refresh(log.scroll_to, y=at, animate=False, force=True)


def action_text(line, width=0, stamp=None):
    """One action as a colored line (fleet_view.action_style), cut to ``width`` (0: whole)."""
    text = Text()
    if stamp is not None:
        text.append(stamp + '  ', style='dim')
        width = max(0, width - len(stamp) - 2) if width else 0
    text.append(fleet_view.fit_line(line, width), style=fleet_view.action_style(line))
    return text


class WorkerScreen(ReadScreen, Screen):
    """One worker's actions as a log: oldest first, stamped with the time, new ones appended at the
    bottom so the view keeps its place while you scroll back; refreshed. Each action is colored by
    its kind and kept to one line; w shows long ones whole."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'back'), Binding('w', 'toggle_wrap', 'wrap')]

    def __init__(self, runner, task):
        super().__init__()
        self.runner, self.task_id = runner, task  # Screen.task is Textual's own, read-only
        self.shown = []
        self.cached_actions = []
        self.wrap = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield RichLog(id='worker-actions', wrap=True, highlight=False, markup=False)

    def action_toggle_wrap(self):
        self.wrap = not self.wrap
        self.shown = []  # rewrite cached lines, without a read
        self.show_actions(self.cached_actions)

    def on_resize(self, event):
        if not self.wrap:
            self.shown = []  # cut cached lines again to the new width
            self.show_actions(self.cached_actions)

    def on_mount(self):
        self.title = f'{self.runner.name}: {self.task_id}'
        self.query_one('#menubar', MenuBar).show([('w', 'Wrap'), ('esc', 'Back')])
        self.refresh_actions()
        self.set_interval(LOG_REFRESH, self.refresh_actions)

    def refresh_actions(self):
        runner, task = read_input(self.runner), self.task_id
        return self.read('actions', (runner.repo, task),
                         lambda: [(at, line) for line, _, at in fleet_view.action_log(runner, task)], self.show_actions)

    def show_actions(self, actions):
        self.cached_actions = actions
        if not self.is_mounted:
            return
        log = self.query_one('#worker-actions', RichLog)
        follow, at_row = log.is_vertical_scroll_end, log.scroll_y
        last = self.shown[-1] if self.shown else None
        if last in actions:  # append only what is new; a full redraw would lose the scroll position
            fresh = actions[len(actions) - actions[::-1].index(last):]
        else:
            log.clear()
            fresh = actions
            if not actions:
                log.write('No actions recorded yet.', scroll_end=follow)
        width = 0 if self.wrap else max(20, self.size.width - 4)  # border and scrollbar
        for at, line in fresh:
            stamp = time.strftime('%H:%M:%S', time.localtime(at)) if at is not None else '--:--:--'
            log.write(action_text(line, width, stamp), scroll_end=follow)
        if not follow:
            log.call_after_refresh(log.scroll_to, y=at_row, animate=False, force=True)
        if fresh:
            self.shown = actions


class TasksScreen(ReadScreen, Screen):
    """One runner's open tasks in priority (section, then rank) order: filter them, re-sort them, clear or
    set aside a hold, answer the owner's questions. Refreshed like the main screen."""
    VIEW_NAMES = {'all': 'Open', 'working': 'Active', 'held': 'Blocker', 'waiting': 'Waiting',
                  'questions': 'Questions', 'closed': 'Closed'}
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'Back', show=False),
                Binding('tab', 'step_view(1)', 'next view', show=False),
                Binding('shift+tab', 'step_view(-1)', 'previous view', show=False),
                *[Binding(str(n + 1), f'show_view("{view}")', view, show=False)
                  for n, view in enumerate(fleet_view.TASK_VIEWS)],
                *[Binding(key, f'task("{key}")', key, show=False) for key in 'udcabs'],
                Binding('n', 'new_task', 'New', show=False),
                Binding('x,delete', 'task("x")', 'Delete', show=False),
                Binding('g', 'plan("discuss")', 'Discuss', show=False),
                Binding('v', 'plan("investigate")', 'Investigate', show=False),
                Binding('e', 'decide', 'Decide', show=False),
                Binding('i', 'snapshot_info', 'Snapshot info', show=False, priority=True)]
    DEFAULT_CSS = '''
    #task-views { height: auto; max-height: 3; padding: 0 1; }
    #task-freshness { height: auto; padding: 0 1; }
    #task-provenance { height: 3; border: none; padding: 0 1; }
    #tasks { height: 1fr; }
    #task-detail { height: auto; max-height: 7; padding: 0 1; border-top: solid $panel; }
    '''
    # State and Why are cut to what the terminal has left; Why goes first on a narrow one.
    FIXED, TEXT = ('#', 'Task', 'Short'), ('State', 'Why')

    def __init__(self, runner_name):
        super().__init__()
        self.runner_name, self.view, self.rows, self.shown = runner_name, 'all', [], []
        self.history = []

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield Static(id='task-views')
        yield Static(id='task-freshness')
        yield TextArea(read_only=True, show_cursor=False, id='task-provenance')
        yield DataTable(id='tasks', cursor_type='row', zebra_stripes=True)
        yield Static(id='task-detail')

    def on_mount(self):
        self.title = f'{self.runner_name}: tasks'
        self.query_one('#tasks', DataTable).add_columns(*self.FIXED, *self.TEXT)
        self.refresh_tasks()
        self.query_one('#tasks', DataTable).focus()
        self.set_interval(REFRESH, self.refresh_tasks)

    def runner(self):
        return next((r for r in self.app.runners if r.name == self.runner_name), None)

    def view_rows(self, view):
        return self.history if view == 'closed' else fleet_view.task_view(self.rows, view)

    def action_snapshot_info(self):
        info = self.query_one('#task-provenance', TextArea)
        (self.query_one('#tasks', DataTable) if info.has_focus else info).focus()

    def refresh_tasks(self, follow=None):
        """``follow``: keep the cursor on this task wherever it moved (after a re-sort)."""
        runner = self.runner()
        self.rows = fleet_view.task_rows(runner, include_closed=True) if runner else []
        self.history = fleet_view.closed_task_rows(runner) if runner else []
        snapshot = fleet_view.snapshot_for(runner) if runner else None
        available = snapshot is not None and snapshot.counts is not None
        views = Text()
        for number, view in enumerate(fleet_view.TASK_VIEWS):
            count = len(self.view_rows(view)) if available else '?'
            label = f'{number + 1} {self.VIEW_NAMES[view]} {count}'
            views.append(('  ' if number else '') + label, style='bold reverse' if view == self.view else 'dim')
        views.append('   tab next view', style='dim')
        self.query_one('#task-views', Static).update(views)
        freshness = Text('Inventory ' + (snapshot.freshness if snapshot else 'unavailable'), style='bold')
        if snapshot:
            freshness.append(f' · revision {snapshot.revision or "unknown"}\n'
                             f'generation {snapshot.generation} · captured '
                             + fleet_view.ago(max(0, int(time.time() - snapshot.captured_at)))
                             + f' · execution {snapshot.engine_freshness}', style='dim')
        if runner and runner.display_deleted:
            freshness.append(f'\nDeletion pending commit: {len(runner.display_deleted)} record(s) (display only)', style='yellow')
        if runner and runner.display_recreated:
            freshness.append(f'\nRestored/recreated pending record(s): {len(runner.display_recreated)} (not committed inventory)',
                             style='yellow')
        self.query_one('#task-freshness', Static).update(freshness)
        provenance = fleet_view.freshness(runner) if runner else 'Runner unavailable.'
        info = self.query_one('#task-provenance', TextArea)
        if info.text != provenance:
            info.load_text(provenance)
        table = self.query_one('#tasks', DataTable)
        previous_row = table.cursor_row
        current = follow or (self.current().task if self.current() else None)
        self.shown = self.view_rows(self.view)
        position = {row.task: number + 1 for number, row in enumerate(self.rows)}
        cells = [{'#': (str(position[row.task]), 'dim'), 'Task': (row.task, 'bold'),
                  'Short': (row.short, ''),
                  'State': (row.state, fleet_view.state_style(row)),
                  'Why': (row.why, 'yellow' if row.question else 'dim')} for row in self.shown]
        self.app.fill(table, cells, self.FIXED, self.TEXT, minimum=10)
        tasks = [row.task for row in self.shown]
        target = tasks.index(current) if current in tasks else min(previous_row, len(tasks) - 1)
        if target >= 0 and table.cursor_row != target:
            table.move_cursor(row=target)
        self.show_task()

    def current(self):
        table = self.query_one('#tasks', DataTable)
        return self.shown[table.cursor_row] if 0 <= table.cursor_row < len(self.shown) else None

    def actions(self, row):
        runner = self.runner()
        if runner is None or row is None or self.app.view_only:
            return []
        return fleet_view.task_actions(runner, row, command=self.app.command, script=self.app.script,
                                       agent=self.app.agent)

    def show_task(self):
        row = self.current()
        text = Text()
        if row is None:
            runner = self.runner()
            snapshot = fleet_view.snapshot_for(runner) if runner else None
            if snapshot is None or snapshot.counts is None:
                text.append('Task inventory unavailable; task counts are unknown.\n', style='yellow')
            else:
                text.append('No task in this view.\n', style='dim')
        else:
            text.append(row.task, style='bold')
            text.append(f'  {row.short}\n')
            text.append(f'{row.section} · {row.state}\n', style=fleet_view.state_style(row) or 'dim')
            if row.why:
                text.append(row.why + '\n', style='yellow' if row.question else '')
        keys = [(a.key, a.label) for a in self.actions(row)]
        if not self.app.view_only:
            keys.append(('n', 'New'))
            if row:
                keys = ([('e', 'Decide')] if row.kind != 'closed' else []) + [('g', 'Discuss'), ('v', 'Investigate')] + keys
        self.query_one('#menubar', MenuBar).show(([('enter', 'Open')] if row else [])
                                                 + keys + [('i', 'Info'), ('esc', 'Back')])
        self.query_one('#task-detail', Static).update(text)

    def on_data_table_row_selected(self, event):
        row = self.current()
        if row is not None:
            self.app.push_screen(TaskScreen(self.runner_name, row.task, read_only=self.view == 'closed'))

    def action_plan(self, mode):
        runner, row = self.runner(), self.current()
        if runner and row and not self.app.view_only:
            self.app.open_plan(runner.repo, task=row.task, mode=mode)

    def action_decide(self):
        runner, row = self.runner(), self.current()
        if runner and row and row.kind != 'closed' and not self.app.view_only:
            self.app.decide_task(runner, row.task)

    def action_new_task(self):
        runner = self.runner()
        if runner is None or self.app.view_only:
            return

        def add(task):
            if not task:
                return
            argv = [self.app.command, 'tasks', 'add', '--title', task['title'], '--short', task['short'],
                    '--goal', task['goal'], '--section', task['section']]
            for key in ('scope', 'acceptance'):
                if task[key]:
                    argv += [f'--{key}', task[key]]
            self.app.execute(fleet_view.Action('n', f'New task in {runner.name}', argv + [runner.name]))
        self.app.push_screen(NewTask([], runner=runner), add)

    def on_data_table_row_highlighted(self, event):
        self.show_task()

    def action_show_view(self, view):
        self.view = view
        self.refresh_tasks()

    def action_step_view(self, step):
        views = fleet_view.TASK_VIEWS
        self.action_show_view(views[(views.index(self.view) + step) % len(views)])

    def action_task(self, key):
        row = self.current()
        action = next((a for a in self.actions(row) if a.key == key), None)
        if action is None:
            return
        self.follow = row.task
        if key == 's':
            runner = self.runner()
            self.app.push_screen(PickSection(row.task), lambda section: section and self.app.execute(
                fleet_view.Action('s', f'Section {row.task}', [self.app.command, 'tasks', 'place', row.task, section, runner.name])))
            return
        if action.confirm:
            self.app.push_screen(Confirm(action.confirm), lambda yes: yes and self.app.execute(action))
        else:
            self.app.execute(action)


class TaskScreen(ReadScreen, Screen):
    """One task: its question and the runner's suggested answer, its whole task record and
    its worker's last actions. Answer it here; refreshed like the main screen."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'Back', show=False),
                Binding('s', 'section', 'Section', show=False),
                Binding('e', 'decide', 'Decide', show=False),
                Binding('g', 'plan("discuss")', 'Discuss', show=False),
                Binding('v', 'plan("investigate")', 'Investigate', show=False),
                *[Binding(key, f'answer("{key}")', key, show=False) for key in 'ohrwd']]
    DEFAULT_CSS = '''
    #task-scroll { height: 1fr; padding: 0 1; }
    #task-answers { height: auto; padding: 0 1; border-top: solid $panel; }
    '''

    def __init__(self, runner_name, task, *, read_only=False):
        super().__init__()
        self.runner_name, self.task_id = runner_name, task
        self.read_only, self.closed = read_only, False
        self.entry, self.recent = '', []

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        with VerticalScroll(id='task-scroll'):
            yield Static(id='task-body')
        yield Static(id='task-answers')

    def on_mount(self):
        self.title = f'{self.runner_name}: {self.task_id}'
        self.refresh_tasks()
        self.set_interval(REFRESH, self.refresh_tasks)

    def runner(self):
        return next((r for r in self.app.runners if r.name == self.runner_name), None)

    def question(self):
        runner = self.runner()
        return next((q for q in runner.questions if q.id == self.task_id), None) if runner else None

    def answers(self):
        runner, question = self.runner(), self.question()
        if (runner is None or question is None or self.app.view_only or self.read_only
                or self.app.deletion_pending(runner, self.task_id)):
            return []
        return fleet_view.answers(runner, question, command=self.app.command)

    def refresh_tasks(self, follow=None):
        runner = read_input(self.runner())
        task = self.task_id
        if self.app.deletion_pending(runner, task):
            self.invalidate_read()
            self.entry, self.recent = '', []
            self.show_task()
            return
        self.show_task()
        if runner:
            return self.read('task-detail', (runner.repo, task),
                             lambda: (fleet_view.task_entry(runner, task), fleet_view.recent_actions(runner, task)),
                             self.loaded_task)

    def loaded_task(self, value):
        if not self.app.deletion_pending(self.runner(), self.task_id):
            self.entry, self.recent = value
        self.show_task()

    def show_task(self):
        runner, question = self.runner(), self.question()
        closed_row = next((r for r in fleet_view.closed_task_rows(runner) if r.task == self.task_id), None) if runner else None
        self.closed = closed_row is not None
        row = closed_row or (next((r for r in fleet_view.task_rows(runner, include_closed=True)
                                   if r.task == self.task_id), None) if runner else None)
        text = Text()
        text.append(self.task_id, style='bold')
        if row:
            text.append(f'  {row.short}\n')
            text.append(f'{row.section} · {row.state}\n', style=fleet_view.state_style(row) or 'dim')
        else:
            text.append('  (closed, or not in tasks/ now)\n', style='dim')
        if self.closed and row is not None and row.why:
            text.append(row.why + '\n')
        if question:
            text.append(f'\nQuestion for you ({question.effort}, unblocks {question.unblocks})\n', style='bold yellow')
            text.append(question.needs + '\n', style='yellow')
            if question.answer:
                text.append('The runner suggests: ', style='bold')
                text.append(question.answer + '\n', style='dim')
        elif row and row.why and not self.closed:
            text.append(row.why + '\n')
        pending_delete = self.app.deletion_pending(runner, self.task_id)
        if pending_delete:
            text.append('\nDeletion pending commit; task record/actions unavailable.\n', style='yellow')
        entry = '' if pending_delete else self.entry
        if entry:
            text.append('\nTask record (working tree; independent of committed inventory)\n', style='bold')
            text.append(entry + '\n')
        actions = [] if pending_delete else self.recent
        if actions:
            text.append('\nLast actions\n', style='bold')
            for line, age in actions:
                text.append(f'{fleet_view.ago(age):>9}  ', style='dim')
                text.append_text(action_text(line, max(20, self.size.width - 15)))
                text.append('\n')
        self.query_one('#task-body', Static).update(text)
        answers = self.answers()
        self.query_one('#menubar', MenuBar).show([(a.key, a.label) for a in answers]
                                                 + ([] if self.app.view_only or self.read_only or self.closed or pending_delete or row is None
                                                    else [('s', 'Section'), ('e', 'Decide')])
                                                 + ([] if self.app.view_only or pending_delete or row is None
                                                    else [('g', 'Discuss'), ('v', 'Investigate')])
                                                 + [('esc', 'Back')])
        explained = Text()  # what each answer does, under the task; the keys are in the menu bar
        for answer in answers:
            explained.append(f' {answer.label:<11}', style='bold')
            explained.append(f'{answer.explain}\n', style='dim')
        self.query_one('#task-answers', Static).update(explained)

    def action_answer(self, key):
        answer = next((a for a in self.answers() if a.key == key), None)
        if answer is None:
            return

        def run(words):
            if answer.needs_text and not words:
                return
            argv = [part.replace('{text}', words or '') for part in answer.argv]
            self.app.execute(fleet_view.Action(answer.key, f'{answer.label} {self.task_id}', argv))
        if answer.needs_text:
            self.app.push_screen(TextPrompt(f'{answer.label}: {self.task_id}', answer.explain), run)
        else:
            self.app.push_screen(Confirm(f'{answer.label} {self.task_id}: {answer.explain}?'), lambda yes: yes and run(''))

    def action_plan(self, mode):
        runner = self.runner()
        if (runner and not self.app.view_only and not self.app.deletion_pending(runner, self.task_id)
                and any(row.task == self.task_id for row in fleet_view.task_rows(runner, include_closed=True))):
            self.app.open_plan(runner.repo, task=self.task_id, mode=mode)

    def action_decide(self):
        runner = self.runner()
        if (runner and not self.app.view_only and not self.read_only and not self.closed
                and not self.app.deletion_pending(runner, self.task_id)
                and any(row.task == self.task_id for row in fleet_view.task_rows(runner))):
            self.app.decide_task(runner, self.task_id)

    def action_section(self):
        runner = self.runner()
        if (runner is None or self.app.view_only or self.read_only or self.closed
                or self.app.deletion_pending(runner, self.task_id)
                or not any(row.task == self.task_id for row in fleet_view.task_rows(runner))):
            return
        self.app.push_screen(PickSection(self.task_id), lambda section: section and self.app.execute(
            fleet_view.Action('s', f'Section {self.task_id}',
                              [self.app.command, 'tasks', 'place', self.task_id, section, runner.name])))


class PrepareRepository(ModalScreen[str]):
    """Preparation may commit a legacy conversion; starting is a separate choice."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel'),
                Binding('left', 'focus_previous', 'previous', show=False),
                Binding('right', 'focus_next', 'next', show=False)]
    DEFAULT_CSS = '''
    PrepareRepository { align: center middle; }
    PrepareRepository > Vertical { width: 84; max-width: 100%; height: auto; border: thick $warning; background: $surface; padding: 1 2; }
    PrepareRepository Horizontal { height: auto; margin-top: 1; }
    PrepareRepository Button { margin-right: 1; }
    '''

    def __init__(self, ready):
        super().__init__()
        self.ready = ready

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(Text(f'{self.ready.repo}\nNot ready: {", ".join(self.ready.problems)}'))
            yield Label('Run autowork tasks prepare? A legacy conversion makes one local commit.\n'
                        'Plan opens the embedded planning console; proposals require separate Review and Apply. '
                        'Neither opening Plan nor Prepare starts a model or invents goals/tasks.')
            yield Label(Text('Choose with ←/→ or Tab; Enter runs it; Esc cancels.', style='dim'))
            with Horizontal():
                yield Button('Prepare', variant='primary', id='prepare')
                yield Button('Prepare and start', id='prepare-start')
                yield Button('Plan', id='plan')
            with Horizontal():
                yield Button('Force', variant='warning', id='force')
                yield Button('Cancel', id='cancel')

    def on_button_pressed(self, event):
        self.dismiss(None if event.button.id == 'cancel' else event.button.id)

    def action_cancel(self):
        self.dismiss(None)

    def action_focus_next(self):
        self.focus_next()

    def action_focus_previous(self):
        self.focus_previous()


class RepoTree(DirectoryTree):
    """Directories only; a repository is marked ready (a committed tasks/ store) or not."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readiness_cache = {}

    def filter_paths(self, paths):
        return [p for p in paths if p.is_dir() and not p.name.startswith('.')]

    def _populate_node(self, node, content):
        # filter_paths ran on DirectoryTree's loader: every returned path is a
        # directory. Avoid its second synchronous is_dir() pass on the UI loop.
        paths = tuple(content)
        node.remove_children()
        for path in paths:
            node.add(path.name, data=type(node.data)(path), allow_expand=True)
        node.expand()
        self.screen.read_labels(paths)

    def update_readiness(self, ready):
        path = Path(ready.path)
        self.readiness_cache[path] = ready

        def repaint(node):
            if node.data and node.data.path == path:
                node.refresh()  # invalidate Textual's cached row, not just the widget's paint
            else:
                for child in node.children:
                    repaint(child)
        repaint(self.root)

    def render_label(self, node, base_style, style):
        label = super().render_label(node, base_style, style)
        path = node.data.path if node.data else None
        if path in self.readiness_cache:
            ready = self.readiness_cache[path]
            label.append('  ' + ready.mark, style='bold green' if ready.ready else 'yellow')
        return label


class BrowseScreen(ReadScreen, Screen):
    """Pick a repository and start its service."""
    BINDINGS = [Binding('p', 'start', 'Play'), Binding('g', 'plan_selected', 'Plan'),
                Binding('escape,q', 'app.pop_screen', 'back')]
    CSS = '''
    #tree, #info-scroll { width: 1fr; }
    #info { padding: 0 1; }
    '''

    def __init__(self, root, start):
        super().__init__()
        self.root, self.start = root, start
        self.chosen = None
        self.preparing = False
        self.prepare_result = None
        self.chosen_path = None
        self.starting = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        with Horizontal():
            yield RepoTree(self.root or str(Path.home()), id='tree')
            with VerticalScroll(id='info-scroll'):
                yield Static('Move to a repository; ready ones have a committed tasks/ store.', id='info')

    def on_mount(self):
        self.title = f'start a runner: {self.root or Path.home()}'
        self.query_one('#menubar', MenuBar).show([('p', 'Play'), ('g', 'Plan'), ('esc', 'Back')])
        if self.root is None:
            home = Path.home()
            def loaded(root):
                self.root = str(root)
                self.query_one('#tree', RepoTree).path = root
                self.title = f'start a runner: {root}'
            self.read('browse-root', str(home), lambda: home / 'git' if (home / 'git').is_dir() else home, loaded)

    def read_labels(self, paths):
        def load():
            return tuple(fleet_view.readiness(path) for path in paths if (path / '.git').exists())
        def loaded(results):
            tree = self.query_one('#tree', RepoTree)
            for ready in results:
                tree.update_readiness(ready)
        return self.read('directory-labels', tuple(map(str, paths)), load, loaded)

    def on_tree_node_highlighted(self, event):
        node = event.node
        if node.data is None:
            return
        self.show_repository(node.data.path)

    def show_repository(self, path, after=None, failed=None):
        if after:  # a pre-action check must not reuse any read admitted before consent
            self.invalidate_read()
        path = str(path)
        if self.chosen_path != path:
            self.chosen = None
            self.starting = False
        self.chosen_path = path
        self.query_one('#info', Static).update(f'{path}\nReading readiness…')
        def load():
            ready = fleet_view.readiness(path)
            root = bool(ready.repo and Path(ready.path).resolve() == Path(ready.repo).resolve())
            return ready, root
        def loaded(value):
            self.chosen, self.chosen_is_root = value
            self.render_repository(path)
            if after:
                after(self.chosen)
        def unavailable(error):
            self.starting = False
            self.query_one('#info', Static).update(f'{path}\nReadiness unavailable: {error}')
            if failed:
                failed(error)
        return self.read('readiness', path, load, loaded, unavailable)

    def render_repository(self, path):
        if not self.chosen:
            return
        tree = self.query_one('#tree', RepoTree)
        tree.update_readiness(self.chosen)
        info = Text()
        info.append(str(path) + '\n', style='bold')
        if self.chosen.ready:
            info.append('ready', style='bold green')
            info.append(f' on {self.chosen.branch}. Press p to play (start) its service.\n')
        elif not self.chosen.repo:
            info.append('not a Git repository\n', style='dim')
        else:
            info.append(f'not ready: needs {", ".join(self.chosen.problems)}\n', style='bold yellow')
            for hint in fleet_view.how_to_fix(self.chosen):
                info.append(f'  {hint}\n')
            info.append('Press p for Prepare, Prepare and start, Plan (an agent plans the tasks), or Force.\n')
        if self.preparing:
            info.append('\nPreparing repository…\n', style='yellow')
        if self.prepare_result and self.prepare_result[0] == str(path):
            report = self.prepare_result[1]
            info.append('\n' + report['outcome'] + '\n', style='bold')
            for refusal in report.get('refusals', []):
                info.append(str(refusal) + '\n')
            if report.get('forced'):
                info.append('Forced conversion:\n', style='bold')
                step = report['forced'].get('step', {})
                for key in ('stopped', 'set_aside', 'landed', 'committed', 'commit'):
                    if key in step:
                        info.append(f'{key}: {step[key]}\n')
            info.append((report.get('next') or 'Resolve the reported problem, then run Prepare again.') + '\n')
            if report['outcome'] == 'NO_STORE':
                info.append('Plan accepted intent with /docs_sync; no goals or tasks were created.\n')
        self.query_one('#info', Static).update(info)

    def action_start(self):
        if self.app.view_only or self.preparing or self.starting:
            return
        if self.chosen_path is None:
            self.notify('Choose a repository first.', severity='warning')
            return
        self.starting = True
        token = self.show_repository(self.chosen_path, self.ready_to_start)
        if token is not None:
            token.done.add_done_callback(lambda future: setattr(self, 'starting', False))

    def ready_to_start(self, ready):
        self.starting = False
        if not self.chosen_is_root:
            self.notify('Choose a Git repository root.', severity='warning')
        elif self.chosen.ready:
            self.start(self.chosen)
        else:
            ready = self.chosen
            self.app.push_screen(PrepareRepository(ready), lambda choice: choice and (
                self.plan(ready.path) if choice == 'plan' else
                self.confirm_force(ready.path) if choice == 'force' else
                self.prepare(ready.path, choice == 'prepare-start')))

    def action_plan_selected(self):
        if self.chosen and self.chosen.repo:
            self.plan(self.chosen.repo)

    def plan(self, path):
        """Open embedded planning, independent of execution readiness or service state."""
        if not self.app.view_only and not self.preparing:
            self.app.open_plan(str(path))

    def confirm_force(self, path):
        self.app.push_screen(Confirm(Text(
            f'Force conversion of {path}?\n'
            'Force stops the service and live workers, sets attempts aside with worktrees, '
            'branches and files kept, commits planning edits, converts, and restarts the service.')),
            lambda yes: yes and self.prepare(path, False, force=True))

    def prepare(self, path, start, force=False):
        if self.app.view_only or self.preparing:
            return
        self.preparing = True
        self.prepare_result = None
        self.show_repository(path)
        self.run_worker(lambda: self.run_prepare(path, start, force), thread=True, group='prepare')

    def run_prepare(self, path, start, force=False):
        """Run the supported CLI, not a second implementation of conversion or bootstrap."""
        try:
            result = self.app.runner_cmd([self.app.command, 'tasks', 'prepare', *(['--force'] if force else []), path],
                                         env=dict(os.environ), capture_output=True, text=True)
            try:
                report = json.loads(result.stdout)
                if not isinstance(report, dict) or not isinstance(report.get('outcome'), str) or not report['outcome']:
                    raise ValueError('missing preparation outcome')
            except ValueError:
                report = dict(outcome='PREPARE_FAILED', next=(result.stdout or '') + (result.stderr or ''))
            ok = result.returncode == 0 and report.get('ok') and report['outcome'] in ('READY', 'MIGRATED')
        except OSError as error:
            report, ok = dict(outcome='PREPARE_FAILED', next=str(error)), False
        self.app.call_from_thread(self.prepared, path, report, bool(start and ok))

    def prepared(self, path, report, start):
        self.preparing = False
        self.prepare_result = (str(path), report)
        if not self.is_mounted:  # leaving the browser does not undo a CLI conversion in flight
            return
        self.app.invalidate_reads()
        if self.chosen_path == str(path):
            self.show_repository(path, lambda ready: start and ready.ready and self.start(ready))


def save_report(text, directory):
    """Explicit export only: a unique private file, never the repository or clipboard."""
    directory = Path(directory)
    directory.mkdir(mode=0o700, parents=True, exist_ok=True)
    fd, filename = tempfile.mkstemp(prefix='blockers-', suffix='.txt', dir=directory)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            stream.write(text)
    except BaseException:
        Path(filename).unlink(missing_ok=True)
        raise
    return Path(filename)


class BlockersScreen(Screen):
    """A frozen, copyable report. Refresh is explicit so selection is not disturbed."""
    BINDINGS = [Binding('escape', 'back', 'Back'),
                Binding('c', 'copy_report', 'Copy report', priority=True),
                Binding('d', 'toggle_diagnostics', 'Details', priority=True),
                Binding('e', 'export_report', 'Export', priority=True),
                Binding('r', 'refresh_report', 'Refresh', priority=True)]
    DEFAULT_CSS = '''
    BlockersScreen #report-state { height: auto; padding: 0 1; }
    BlockersScreen TextArea { height: 1fr; }
    BlockersScreen Horizontal { height: 3; }
    BlockersScreen Button { margin-right: 1; min-width: 8; width: auto; padding: 0 1; }
    '''

    def __init__(self, runner):
        super().__init__()
        self.runner = read_input(runner)
        self.report_text = self.full_report_text = None
        self.diagnostics = self.exporting = False

    def compose(self):
        yield MenuBar(id='report-menu')
        yield Static(Text(f'{self.runner.name} — read only; loading…'), id='report-state')
        yield TextArea(read_only=True, show_cursor=False, id='blockers-text')
        with Horizontal():
            yield Button('Copy (c)', id='copy-report', disabled=True)
            yield Button('Details (d)', id='details-report', disabled=True)
            yield Button('Export (e)', id='export-report', disabled=True)
            yield Button('Refresh (r)', id='refresh-report')
            yield Button('Back (Esc)', id='back-report')

    def on_mount(self):
        self.query_one(MenuBar).show([('escape', 'Back'), ('c', 'Copy'), ('d', 'Details'),
                                      ('e', 'Export'), ('r', 'Refresh')], prefix='Blockers')
        self.action_refresh_report()

    def action_refresh_report(self):
        self.query_one('#report-state', Static).update(Text(f'{self.runner.name} — read only; loading…'))
        self.app.request_blockers(self)

    def present_report(self, text):
        self.full_report_text = text
        self.show_report()
        for name in ('copy', 'details', 'export'):
            self.query_one(f'#{name}-report', Button).disabled = name == 'export' and self.exporting

    def show_report(self):
        text = self.full_report_text
        self.report_text = (blockers_report.summary(text)
                            if not self.diagnostics and blockers_report.DIAGNOSTICS in text else text)
        self.query_one(TextArea).load_text(self.report_text)
        self.query_one('#details-report', Button).label = 'Summary (d)' if self.diagnostics else 'Details (d)'
        self.query_one('#report-state', Static).update(Text(
            f'{self.runner.name} — read only; {"full diagnostics" if self.diagnostics else "summary"}. '
            'Copy/export uses this view.'))

    def action_toggle_diagnostics(self):
        if self.full_report_text is not None:
            self.diagnostics = not self.diagnostics
            self.show_report()

    def action_copy_report(self):
        if self.report_text is not None:
            try:
                self.app.copy_to_clipboard(self.report_text)
            except Exception as error:
                self.notify(f'Clipboard request failed: {error}. Use Export (e).', severity='error')
            else:
                self.notify('Clipboard requested; paste to verify. If empty, use Export (e).')

    def action_export_report(self):
        if self.report_text is None or self.exporting:
            return
        self.exporting = True
        self.query_one('#export-report', Button).disabled = True
        # App-owned: Escape/Refresh remain responsive, without cancelling an in-flight file write.
        return self.app.run_worker(self._export_report(self.report_text))

    async def _export_report(self, text):
        try:
            if self.app.is_web:
                content = io.StringIO(text)
                try:
                    key = self.app.deliver_text(content, save_filename=f'blockers-{uuid.uuid4().hex}.txt',
                                                encoding='utf-8', mime_type='text/plain', name='blockers-report')
                except Exception:
                    content.close()
                    raise
                if key is None:
                    content.close()
                    raise OSError('no download transport available')
                self.notify('Download requested; completion is not yet confirmed.')
            else:
                path = await asyncio.to_thread(save_report, text, Path(self.app.state_root) / 'reports')
                self.notify(f'Saved on app host (not the SSH client): {path}', timeout=15)
        except Exception as error:
            self.notify(f'Export failed: {error}', severity='error')
        finally:
            self.exporting = False
            if self in self.app.screen_stack and self.is_mounted:
                self.query_one('#export-report', Button).disabled = False

    def action_back(self):
        self.app.pop_screen()

    def on_button_pressed(self, event):
        event.stop()
        {'copy-report': self.action_copy_report, 'details-report': self.action_toggle_diagnostics,
         'export-report': self.action_export_report, 'refresh-report': self.action_refresh_report,
         'back-report': self.action_back}[event.button.id]()


class FleetApp(App):
    TITLE = 'autowork'
    # Stacked, each part full width: a side-by-side split left a ~30-column pane on an
    # 80-column terminal, which wrapped the detail and cut the log.
    CSS = '''
    #runners { height: auto; max-height: 40%; }
    #detail { height: auto; max-height: 50%; padding: 0 1; border-top: solid $panel; }
    #lanes { height: auto; max-height: 12; border-top: solid $panel; }
    #log { height: 1fr; min-height: 4; border-top: solid $panel; }
    '''
    BINDINGS = [
        # One key per action, the first letter of its word, shown highlighted in the detail
        # pane (the footer repeated them, cut short). Enter on a runner opens its log too.
        # show=False: the log, worker and browse screens' footers list their own keys, not
        # these (the log's footer offered Play/Pause and Stop, cut off at 'Fallba').
        Binding('l', 'run("l")', 'Log', show=False),
        Binding('p', 'run("p")', 'Play/Pause', show=False),
        Binding('s', 'run("s")', 'Stop', show=False),
        Binding('r', 'run("r")', 'Restart', show=False),
        Binding('m', 'pick_model("model")', 'Model', show=False),
        Binding('t', 'run("t")', 'Tasks', show=False),
        Binding('e', 'answer_question', 'Answer', show=False),
        Binding('b', 'show_blockers', 'Blockers', show=False),
        Binding('g', 'run("g")', 'Plan', show=False),
        Binding('u', 'run("u")', 'Uninstall', show=False),
        Binding('n', 'browse', 'New', show=False),
        Binding('q', 'quit', 'Quit', show=False),
    ]
    CONTROL = {'run', 'browse', 'pick_model'}

    def __init__(self, *, command, script, state_root, env_dir, systemctl='systemctl',
                 journalctl='journalctl', agent=None, runner_cmd=subprocess.run, view_only=False, browse_root=None,
                 list_models=fleet_view.models):
        super().__init__()
        self.list_models = list_models
        self.command, self.script = command, script
        self.state_root, self.env_dir = state_root, env_dir
        self.systemctl, self.journalctl = systemctl, journalctl
        self.agent = agent
        self.runner_cmd = runner_cmd
        self.view_only = view_only
        self.browse_root = browse_root
        self.runners = []
        self.fleet_snapshot = None
        self.generation = 0
        self.read_epoch = 0
        self.selected = None
        self.starting_repositories = set()
        self.pending_deletions = {}  # captured identity -> (request generation, success time, recreated)
        self.completed_deletions = {}  # retain action objects: duplicate callbacks are harmless
        self._report_busy = False
        self._report_pending = None

    def check_action(self, action, parameters):
        """View-only (for example served to a browser on a shared network): no control keys."""
        if action == 'show_blockers':
            return len(self.screen_stack) == 1 and self.current() is not None
        if self.view_only and action in self.CONTROL and parameters not in (('l',), ('t',)):  # read-only views
            return False
        # Over the log, worker or browse screen, the runner keys are off: s while reading a log
        # asked to stop the runner, and p on the browse screen is its own Play.
        if len(self.screen_stack) > 1 and action in self.CONTROL:
            return False
        return True

    # -- layout -----------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield DataTable(id='runners', cursor_type='row', zebra_stripes=True)
        yield Static(id='detail')
        yield DataTable(id='lanes', cursor_type='row', zebra_stripes=True)
        yield RichLog(id='log', wrap=True, highlight=False, markup=False)

    # The counts come right after the name, as narrow columns that always show: after a
    # 44-column Needs they scrolled off an 80-column terminal. Needs and Now share the rest.
    # Every open task is in one count column, so they add up to Total; Decision is the
    # Needs-decision tasks, which wait for the owner.
    RUNNER_COLUMNS = ('Runner', 'State', 'Active', 'Mergeable', 'Waiting', 'Blocker', 'Decision', 'Total')
    RUNNER_TEXT = ('Needs', 'Now')
    LANE_COLUMNS = ('Task', 'Status', 'Try', 'For', 'Quiet')
    LANE_TEXT = ('Doing',)
    STATUS_STYLE = {fleet_view.ACTIVE: 'bold green', fleet_view.MERGEABLE: 'bold cyan',
                    fleet_view.WAITING: 'bold yellow', fleet_view.BLOCKER: 'bold red'}

    def on_mount(self):
        self.reads = tui_reads.ReadCoordinator()
        self.reader = self.reads.owner(self.read_done)
        table = self.query_one('#runners', DataTable)
        table.add_columns(*self.RUNNER_COLUMNS, *self.RUNNER_TEXT)
        self.query_one('#lanes', DataTable).add_columns(*self.LANE_COLUMNS, *self.LANE_TEXT)
        self.action_refresh()
        self.refresh_log()
        self.set_interval(REFRESH, self.poll_refresh)
        self.set_interval(LOG_REFRESH, self.refresh_log)
        self.code = None
        self.reload_if_updated()
        self.set_interval(CODE_CHECK, self.reload_if_updated)

    async def action_quit(self):
        if hasattr(self, 'planning_hub'):
            await asyncio.to_thread(self.planning_hub.close)
        self.exit()

    def on_unmount(self):
        self.reader.close()
        self.reads.close()
        if hasattr(self, 'planning_hub'):
            self.planning_hub.close()

    def read(self, kind, identity, loader, apply):
        token = self.reader.request(kind, identity, self.read_epoch, loader)
        token.apply = apply
        return token

    def read_done(self, token, value, error):
        if not self.is_running:
            return
        errors = self.__dict__.setdefault('_read_errors', {})
        if error:
            errors[token.kind] = str(error)
            self.sub_title = ' · '.join(f'{kind}: stale / unavailable: {message}' for kind, message in errors.items())
            self.notify(self.sub_title, severity='warning')
        else:
            errors.pop(token.kind, None)
            token.apply(value)

    def invalidate_reads(self):
        self.read_epoch += 1
        self.reader.invalidate()
        for screen in self.screen_stack:
            if hasattr(screen, '_reader'):
                screen._reader.invalidate()
            if isinstance(screen, DecisionScreen):
                screen.refresh_record()

    def action_completed(self, action=None, ok=False):
        if action is not None and action.deletion is not None and ok and id(action) not in self.completed_deletions:
            self.completed_deletions[id(action)] = action
            self.pending_deletions[action.deletion] = (self.generation, time.time(), False)
            self.project_deletions()
            self.render_fleet()
        # Invalidate subscriptions, not physically running slots. Feedback above is
        # already painted before any asynchronous replacement observation can finish.
        self.action_refresh()
        screen = self.screen
        if isinstance(screen, (TasksScreen, TaskScreen)):
            screen.refresh_tasks(getattr(screen, 'follow', None))

    def project_deletions(self):
        projected = []
        for runner in self.runners:
            snap = runner.snapshot
            matching = [(identity.task, state[2]) for identity, state in self.pending_deletions.items()
                        if snap is not None and identity.workspace == snap.workspace
                        and identity.repository_identity == snap.repository_identity]
            deleted = tuple(task for task, recreated in matching if not recreated)
            recreated = tuple(task for task, recreated in matching if recreated)
            projected.append(replace(runner, display_deleted=deleted, display_recreated=recreated)
                             if (deleted, recreated) != (runner.display_deleted, runner.display_recreated) else runner)
        self.runners = projected

    def deletion_pending(self, runner, task):
        return runner is not None and task in runner.display_deleted

    def on_resize(self, event):
        self._shown = {}  # the columns fit the new width
        if self.query_one('#runners', DataTable).columns:  # the first resize comes before on_mount
            self.render_fleet()  # cached layout only; resize never recollects

    @staticmethod
    def fit(text, room):
        """``text`` in ``room`` columns: cut at a word, or mid-word when that keeps far more."""
        if len(text) <= room:
            return text
        cut = text[:room - 1]
        words = cut.rsplit(' ', 1)[0]
        return (words if len(words) > room * 2 // 3 else cut).rstrip(' ,;:·') + '…'

    def fill(self, table, rows, fixed, text, minimum=16):
        """Show ``rows`` ({column: (text, style)}) in ``table``. The fixed columns always show,
        whole; the text columns share what the terminal has left, each cut to fit, and the last
        named goes first when fewer than ``minimum`` columns would be left for each. Redrawn only
        when something changed, since a clear-and-rewrite every refresh made the panes flicker."""
        width = lambda column: max([len(column), *(len(row[column][0]) for row in rows)]) + 2  # padding
        left = self.size.width - sum(width(c) for c in fixed) - 4  # border and scrollbar
        shown = list(text)
        while shown and left // len(shown) - 2 < minimum:
            shown.pop()
        room = left // max(1, len(shown)) - 2
        columns = (*fixed, *shown)
        cells = [tuple((self.fit(row[c][0], room) if c in shown else row[c][0], row[c][1]) for c in columns)
                 for row in rows]
        shown_before = self.__dict__.setdefault('_shown', {})
        if shown_before.get(table.id) == (columns, cells):
            return False
        shown_before[table.id] = (columns, cells)
        table.clear(columns=tuple(str(c.label) for c in table.columns.values()) != columns)
        if not table.columns:
            table.add_columns(*columns)
        for row, values in zip(rows, cells):
            table.add_row(*(Text(value, style=style) for value, style in values), key=row[columns[0]][0])
        return True

    def reload_if_updated(self):
        """Start again on new code, between actions and with no dialog open."""
        def loaded(stamp):
            if self.code is None:
                self.code = stamp
            elif stamp != self.code and len(self.screen_stack) == 1 and not any(w.is_running for w in self.workers):
                self.exit('reload')
        return self.read('code', str(CODE), code_stamp, loaded)

    # -- data -------------------------------------------------------------------
    def action_refresh(self):
        # Explicit refresh/action return invalidates diagnostics, not inventory authority.
        self.invalidate_reads()
        return self.refresh_fleet(None)

    def poll_refresh(self):
        return self.refresh_fleet(self.fleet_snapshot)

    def refresh_fleet(self, cached):
        self.generation += 1
        state, env, systemctl, generation = self.state_root, self.env_dir, self.systemctl, self.generation
        previous = read_input(self.fleet_snapshot)
        cached = read_input(cached)
        identities = tuple(self.pending_deletions)
        def load():
            snapshot = fleet_view.collect_for_tui(state, env, systemctl=systemctl, generation=generation,
                                                  cached_preparation=cached, last_good=previous)
            return snapshot, fleet_view.observe_deletions(identities)
        return self.read('fleet', (str(state), str(env), systemctl), load,
                         lambda value: self.publish_fleet(value[0], value[1], generation))

    def publish_fleet(self, snapshot, observations=(), generation=0):
        observation_errors = []
        reconciled = False
        for identity, present, error in observations:
            pending = self.pending_deletions.get(identity)
            if pending is not None and generation > pending[0] and error:
                observation_errors.append(f'{identity.task}: {error}')
            snap = next((s for s in snapshot.snapshots if s.workspace == identity.workspace
                         and s.repository_identity == identity.repository_identity), None)
            if (pending is None or generation <= pending[0] or snap is None
                    or snap.captured_at <= pending[1] or snap.freshness != 'fresh'
                    or snap.pending_paths is None or snap.store is None or present is None):
                continue
            if present and identity.task not in snap.store.tasks:
                # A working-only recreation is disclosed, never added to inventory.
                self.pending_deletions[identity] = (*pending[:2], True)
                reconciled |= not pending[2]
            elif present or identity.task not in snap.store.tasks:
                del self.pending_deletions[identity]
                reconciled = True
        errors = self.__dict__.setdefault('_read_errors', {})
        if observation_errors:
            errors['deletion observation'] = '; '.join(observation_errors)
        elif observations:
            errors.pop('deletion observation', None)
        self.fleet_snapshot = snapshot
        self.runners = list(snapshot.runners)
        self.project_deletions()
        self.render_fleet()
        if reconciled:
            # Pending reads captured their last-good input at request time. Once
            # an overlay retires, do not let those old inputs resurrect its row.
            # The replacement inherits this newly published committed snapshot.
            self.action_refresh()
        self.refresh_log()
        screen = self.screen
        if isinstance(screen, (TasksScreen, TaskScreen)):
            screen.refresh_tasks(getattr(screen, 'follow', None))

    def render_fleet(self):
        table = self.query_one('#runners', DataTable)
        keep = self.selected
        self.fill(table, fleet_view.runner_rows(self.runners), self.RUNNER_COLUMNS, self.RUNNER_TEXT)
        names = [r.name for r in self.runners]
        if names:
            row = names.index(keep) if keep in names else 0
            if table.cursor_row != row:
                table.move_cursor(row=row)
            self.selected = names[row]
        else:
            self.selected = None
        counts = ', '.join(f'{n} {state}' for state, n in fleet_view.summary(self.runners))
        errors = (*(self.fleet_snapshot.errors if self.fleet_snapshot else ()),
                  *(f'{kind}: stale / unavailable: {message}' for kind, message in self.__dict__.get('_read_errors', {}).items()))
        self.sub_title = ('discovery unavailable: ' + ' · '.join(errors)) if errors else (
            f'{len(self.runners)} runners: {counts}' if self.runners else
            ('loading runners…' if self.fleet_snapshot is None else 'no runners'))
        self.show_detail()

    def current(self):
        return next((r for r in self.runners if r.name == self.selected), None)

    def on_data_table_row_highlighted(self, event):
        if event.data_table.id == 'runners' and event.row_key is not None and event.row_key.value != self.selected:
            self.selected = event.row_key.value
            self.show_detail()
            self.refresh_log()

    def on_data_table_row_selected(self, event):
        """Enter on a runner (the table takes the key itself): its full-screen log; on a
        worker: its last actions."""
        if event.data_table.id == 'runners':
            self.action_run('l')
        elif event.data_table.id == 'lanes' and event.row_key is not None and self.current() is not None:
            self.push_screen(WorkerScreen(self.current(), event.row_key.value))

    def show_detail(self):
        detail = self.query_one('#detail', Static)
        runner = self.current()
        menubar = self.query_one('#menubar', MenuBar)
        if runner is None:
            errors = (*(self.fleet_snapshot.errors if self.fleet_snapshot else ()),
                      *(f'{kind}: stale / unavailable: {message}'
                        for kind, message in self.__dict__.get('_read_errors', {}).items()))
            if errors:
                detail.update('Discovery unavailable: ' + ' · '.join(errors))
            elif self.fleet_snapshot is None:
                detail.update('Loading pi-autowork runners…')
            else:
                detail.update('No pi-autowork runners yet. Press n for a new one: choose a repository and play its service.')
            self.query_one('#lanes', DataTable).display = False
            menubar.show([] if self.view_only else [('g', 'Plan'), ('n', 'New'), ('q', 'Quit')],
                         click_actions={'g': 'app.run("g")'})
            return
        # The keys go in the menu bar at the top, like a GUI app's menu; the pane holds the facts.
        if self.view_only:
            menubar.show([('l', 'Log'), ('b', 'Blockers'), ('q', 'Quit')], prefix='view only',
                         click_actions={'b': 'app.show_blockers'})
        else:
            menubar.show([(a.key, a.label) for a in self.available(runner)]
                         + [('b', 'Blockers'), ('n', 'New'), ('q', 'Quit')],
                         click_actions={'b': 'app.show_blockers', 'g': 'app.run("g")',
                                        'e': 'app.answer_question'})
        text = Text()
        # First the answer to "is it stuck, and why": one sentence, wrapped, never cut.
        sentence, style = fleet_view.verdict(runner)
        text.append(f'{runner.name}  ', style='bold')
        text.append(sentence + '\n', style=style)
        vector = fleet_view.task_counts(runner)
        if vector is None:
            detail_row(text, 'Tasks', 'unknown / unavailable', 'bold yellow')
        else:
            active, mergeable, waiting, blocker, decision, total = vector
            detail_row(text, 'Tasks', f'{total} open · {active} active · {mergeable} mergeable · {waiting} waiting · {blocker} blocker'
                       + f' · {decision} for your decision')
        detail_row(text, 'Inventory', fleet_view.freshness(runner), 'dim')
        if runner.preparation is not None:
            audit = runner.preparation
            detail_row(text, 'Preparation', f'{audit.state} · diagnostic audit {fleet_view.ago(max(0, int(time.time() - audit.observed_at)))}'
                       + ' (30s max cache; not Start authority)', 'dim')
        waiting = fleet_view.waiting_detail(runner)
        if waiting:
            detail_row(text, 'Waiting', waiting)
        blockers = fleet_view.blocker_parts(runner, {q.id for q in runner.questions})
        if blockers:
            detail_row(text, 'Blocker', blockers, 'bold red')
        if runner.questions:  # what the owner can answer, easiest first (BLOCKERS.md)
            count = len(runner.questions)
            detail_row(text, 'Questions', fleet_view.question_summary(runner)
                + '  (b shows the read-only report)', 'bold yellow')
            for q in runner.questions[:QUESTIONS_SHOWN]:
                text.append(' ' * 12)
                text.append(q.id, style='bold')
                text.append(f'  {q.effort}, unblocks {q.unblocks}\n', style='dim')
                text.append(' ' * 14 + q.needs + '\n')
            if count > QUESTIONS_SHOWN:
                text.append(' ' * 12 + f'+{count - QUESTIONS_SHOWN} more\n', style='dim')
        checked = fleet_view.main_check.line(runner.main_check)
        if checked:
            detail_row(text, 'Main', checked, 'bold red' if checked.startswith('main red') else '')
        repair = fleet_view.maintainer_line(runner)
        if repair:
            detail_row(text, 'Maintainer', repair, 'cyan')
        # Short model names; fallback remains read-only in the fleet.
        detail_row(text, 'Repository', tilde(runner.repo) or '(unknown)', 'dim')
        if runner.model:
            detail_row(text, 'Model', f'{runner.model.rsplit("/", 1)[-1]} · fallback {runner.fallback.rsplit("/", 1)[-1]}', 'dim')
        detail_row(text, 'Push', 'enabled' if runner.push else 'disabled', 'dim')
        if runner.toolset:  # a development checkout instead of the Pi package: say so
            detail_row(text, 'Toolset', f'{runner.toolset} (PI_AUTOWORK_TOOLSET, not the Pi package)', 'yellow')
        if text.plain != getattr(self, '_detail', None):
            self._detail = text.plain
            detail.update(text)
        self.show_lanes(runner)

    def show_lanes(self, runner):
        """One row per worker: phase, attempt, how long, and what it is doing in plain words."""
        table = self.query_one('#lanes', DataTable)
        rows = [{'Task': (lane.task if sum(l.task == lane.task for l in runner.lanes) == 1 else f'{lane.task} [{i + 1}]', ''),
                 'Status': fleet_view.lane_status(runner, lane),
                 'Try': (str(lane.attempt), ''), 'For': (fleet_view.duration(lane.minutes), ''),
                 'Quiet': (fleet_view.quiet(lane).removeprefix('quiet '), 'bold yellow'),
                 'Doing': (doing(lane), fleet_view.action_style(doing(lane)))} for i, lane in enumerate(runner.lanes)]
        keep = table.cursor_row
        if self.fill(table, rows, self.LANE_COLUMNS, self.LANE_TEXT) and rows:
            table.move_cursor(row=min(keep, len(rows) - 1))
        table.display = bool(runner.lanes)

    def logs(self, runner, lines=200, since=None):
        return fleet_view.logs(runner, lines=lines, journalctl=self.journalctl, since=since)

    def refresh_log(self):
        """The last hour, folded and counted (fleet_view.log_lines); rewritten only when it changed."""
        log = self.query_one('#log', RichLog)
        runner = self.current()
        if runner is None:
            self.reader.current.pop('journal', None)
            self.reads.retire()
            self._log_identity, self._log = None, None
            log.clear()
            return
        identity = (runner.name, runner.repo)
        if identity != getattr(self, '_log_identity', None):
            self._log_identity, self._log = identity, None
            log.clear()
            log.write(f'{runner.name}: reading journal…')
        runner, journal = read_input(runner), self.journalctl
        return self.read('journal', (runner.name, runner.repo),
                         lambda: fleet_view.log_lines(fleet_view.logs(runner, lines=400, journalctl=journal, since='-60min')),
                         lambda lines: self.show_log(runner.name, lines))

    def show_log(self, name, lines):
        log = self.query_one('#log', RichLog)
        key = (name, lines)
        if key == getattr(self, '_log', None):
            return
        self._log = key
        follow, at = log.is_vertical_scroll_end, log.scroll_y
        log.clear()
        for line, style in lines:
            log.write(Text(line, style=style), scroll_end=follow)
        if not lines:
            log.write('(nothing in the last hour; Enter shows the whole log)', scroll_end=follow)
        if not follow:
            log.call_after_refresh(log.scroll_to, y=at, animate=False, force=True)

    # -- actions ----------------------------------------------------------------
    def available(self, runner):
        answers = [fleet_view.Action('e', 'Answer', [])] if self.answerable_questions(runner) else []
        return answers + [action for action in fleet_view.actions(
            runner, command=self.command, script=self.script, agent=self.agent)
            if action.key not in ('f', 'b')] + [fleet_view.Action('g', 'Plan', [])]

    def answerable_questions(self, runner):
        editable = {row.task for row in fleet_view.inventory_rows(runner)}
        found = {}
        for question in runner.questions:
            if question.id in editable and not self.deletion_pending(runner, question.id):
                found.setdefault(question.id, question)
        return list(found.values())

    def action_answer_question(self):
        runner = self.current()
        if self.view_only or runner is None or len(self.screen_stack) != 1:
            return
        questions = self.answerable_questions(runner)
        if not questions:
            self.notify('No editable task question. Use Blockers (b) to inspect other questions.', severity='warning')
        elif len(questions) == 1:
            self.decide_task(runner, questions[0].id)
        else:
            self.push_screen(QuestionPicker(questions), lambda task: task and self.decide_task(runner, task))

    def open_plan(self, repo, task=None, mode='plan'):
        if not self.view_only:
            self.push_screen(PlanScreen(repo, task=task, mode=mode))

    def decide_task(self, runner, task):
        current = next((r for r in self.runners if (r.name, r.repo) == (runner.name, runner.repo)), None)
        if self.view_only or current is None or self.deletion_pending(current, task):
            return
        question = next((q for q in current.questions if q.id == task), None)
        self.push_screen(DecisionScreen(current, task, question))

    def on_delivery_complete(self, event):
        if event.name == 'blockers-report':
            event.prevent_default()
            self.notify('Report download transfer completed; check your browser downloads.')

    def on_delivery_failed(self, event):
        if event.name == 'blockers-report':
            event.prevent_default()
            self.notify(f'Report download failed: {event.exception}', severity='error')

    def action_show_blockers(self):
        runner = self.current()
        if runner is not None and len(self.screen_stack) == 1:
            self.push_screen(BlockersScreen(runner))

    def request_blockers(self, screen):
        # One app-owned physical read survives closing a screen. New requests coalesce;
        # cancelling/dismissing a screen must not pretend a blocking read has finished.
        runner = next((r for r in self.runners if (r.name, r.repo) ==
                       (screen.runner.name, screen.runner.repo)), screen.runner)
        self._report_pending = (screen, read_input(runner))
        if not self._report_busy:
            self._start_report()

    def _start_report(self):
        request = self._report_pending
        if request is None:
            return
        screen, runner = request
        self._report_pending = None
        self._report_busy = True
        self.run_worker(self._collect_report(screen, runner), group='blockers-report')

    async def _collect_report(self, screen, runner):
        try:
            text = await asyncio.to_thread(blockers_report.build, runner)
        except asyncio.CancelledError:
            # App shutdown may cancel the await, not the thread. Do not release its slot.
            raise
        except Exception as error:
            text = f'Report unavailable for {runner.name}: {error}\nNo runner action was taken.'
        self._report_busy = False  # the blocking read has actually returned
        if screen in self.screen_stack and screen.is_mounted:
            screen.present_report(text)
        if self._report_pending is not None:
            if self._report_pending[0] in self.screen_stack and self._report_pending[0].is_mounted:
                self._start_report()
            else:
                self._report_pending = None

    def action_run(self, key):
        runner = self.current()
        if key == 'g':
            self.open_plan(runner.repo if runner else str(Path.cwd()))
            return
        if runner is None:
            if key == 'p':
                self.action_browse()
            return
        if key == 'l':
            journal = self.journalctl
            self.push_screen(LogScreen(read_input(runner), lambda runner, lines: fleet_view.logs(
                runner, lines=lines, journalctl=journal)))
            return
        if key == 't':  # view-only shows the tasks too, without their actions
            self.push_screen(TasksScreen(runner.name))
            return
        if self.view_only:
            return
        action = next((a for a in self.available(runner) if a.key == key), None)
        if action is None:
            self.notify(f'Nothing to do with "{key}" for {runner.name} right now.', severity='warning')
            return
        if action.confirm:
            self.push_screen(Confirm(action.confirm), lambda yes: yes and self.execute(action))
        else:
            self.execute(action)

    def action_pick_model(self, which):
        runner = self.current()
        if runner is None or not runner.has_service:
            self.notify('Models are set per service; play one first (p, or n for a new one).', severity='warning')
            return
        settings_path = Path(self.env_dir) / f'{runner.name}.env'
        list_models, pi = self.list_models, os.environ.get('AUTOWORK_PI', 'pi')
        default_models = list_models is fleet_view.models
        def load():
            if default_models:
                settings = fleet_view.read_env(settings_path)
                return list_models(pi=pi, agent_dir=portal.service_agent_dir(settings))
            return list_models()
        current = runner.model if which == 'model' else runner.fallback
        title = f'{runner.name}: {"model" if which == "model" else "fallback model"}'

        def chosen(model):
            if not model or model == current:
                return
            argv = [self.command, 'model', runner.name] + ([model] if which == 'model' else ['--fallback', model])
            action = fleet_view.Action('m', f'{which} {model}', argv,
                                       confirm=f'Set {runner.name}\'s {which} to {model}'
                                               + ('? Its service restarts; workers resume on the same attempt.'
                                                  if runner.service == 'running' else '?'))
            self.push_screen(Confirm(action.confirm), lambda yes: yes and self.execute(action))
        self.push_screen(PickModel(title, [], current, loader=load, identity=(runner.name, str(settings_path))), chosen)

    def action_browse(self):
        self.push_screen(BrowseScreen(str(self.browse_root) if self.browse_root else None, self.start_repository))

    def start_repository(self, ready):
        if self.view_only or ready.repo in self.starting_repositories:
            return
        self.starting_repositories.add(ready.repo)
        browser = self.screen
        action = fleet_view.Action('a', f'start {Path(ready.repo).name}', [self.command, 'start', ready.repo],
                                   confirm=f'Start a pi-autowork service for {ready.repo}?')

        def go(yes):
            if not yes:
                self.starting_repositories.discard(ready.repo)
                return
            path = ready.path
            def checked(current):
                self.starting_repositories.discard(ready.repo)
                if not current.ready:
                    self.notify('Repository is no longer ready: ' + ', '.join(current.problems), severity='warning')
                    return
                if browser.is_mounted and self.screen is browser:
                    self.pop_screen()
                    self.execute(action)
            if browser.is_mounted and self.screen is browser:
                token = browser.show_repository(path, checked)
                if token is not None:
                    # Completion also releases reservations for discarded selection/
                    # owner/epoch results, whose publication callbacks never run.
                    token.done.add_done_callback(lambda future: self.starting_repositories.discard(ready.repo))
                else:
                    self.starting_repositories.discard(ready.repo)
            else:
                self.starting_repositories.discard(ready.repo)
        self.push_screen(Confirm(action.confirm), go)

    def execute(self, action, on_complete=None):
        env = {**os.environ, **action.env}
        if action.interactive:
            with self.suspend():
                self.runner_cmd(action.argv, env=env)
            self.action_refresh()
            return
        # A restart or stop waits for the runner to stop gracefully (up to the unit's 150 s):
        # run it off the event loop, or the whole TUI freezes and looks crashed.
        self.notify(f'{action.label}: running...', timeout=4)
        self.run_worker(lambda: self.finish_action(action, env, on_complete), thread=True, group='actions')

    def finish_action(self, action, env, on_complete=None):
        """In a worker thread: run the command, then report it on the event loop."""
        try:
            result = self.runner_cmd(action.argv, env=env, capture_output=True, text=True)
            output = ((result.stdout or '') + (result.stderr or '')).strip().splitlines()
            ok, message = result.returncode == 0, (output[-1] if output else action.label)
        except Exception as error:
            ok, message = False, str(error)
        decision = action.argv[1:3] == ['tasks', 'decide']
        if ok and decision:
            message = 'Saved locally — pending commit. This action did not commit or grant live authorization; inventory updates after commit.'
        self.call_from_thread(self.notify, message[:300], severity='information' if ok else 'error',
                              title=f'{action.label}: {"done" if ok else "failed"}', timeout=10 if decision else 3)
        if on_complete is not None:
            self.call_from_thread(on_complete, ok, message)
        self.call_from_thread(self.action_completed, action, ok)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--command', required=True, help='The autowork launcher, for every action.')
    parser.add_argument('--script', required=True, help='pi-autowork.sh, for set-aside.')
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    state = os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local' / 'state')
    parser.add_argument('--state-root', default=os.environ.get('PI_AUTOWORK_STATE_DIR') or f'{state}/pi-autowork')
    parser.add_argument('--env-dir', default=os.environ.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork')
    parser.add_argument('--browse-root', default=os.environ.get('AUTOWORK_BROWSE_ROOT'))
    parser.add_argument('--mouse', action='store_true', help='Capture mouse clicks instead of terminal text selection.')
    parser.add_argument('--view-only', action='store_true', help='Show runners; disable every control key.')
    args = parser.parse_args(argv)
    result = FleetApp(command=args.command, script=args.script, state_root=args.state_root, env_dir=args.env_dir,
                      systemctl=os.environ.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl'),
                      journalctl=os.environ.get('AUTOWORK_JOURNALCTL', 'journalctl'),
                      agent=fleet_view.blockers_agent(), view_only=args.view_only, browse_root=args.browse_root).run(mouse=args.mouse)
    if result == 'reload':  # the code was updated: the same view, on the new release
        os.execv(sys.executable, [sys.executable, str(LAYOUT.entrypoint('tui')),
                                  *(sys.argv[1:] if argv is None else argv)])
    return 0


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        raise SystemExit(main())
    finally:
        sys.argv = previous
