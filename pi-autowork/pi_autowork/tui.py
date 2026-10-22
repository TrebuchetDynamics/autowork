"""`autowork`: the live view of every pi-autowork runner, with controls.

Bare `autowork` on a terminal runs this through `uv run --with textual==8.2.8`, so the
runner itself stays standard-library only. It reads runner state (status.json, engine
slots, systemd, logs, Pi transcripts) every few seconds and calls no model. Every
action runs an `autowork` command (or the runner script); there is no second way to
change a runner. `d` browses directories and starts a service for a repository that
has its tasks/ store committed on its main branch.

    python3 tui.py --command PATH --script PATH [--view-only]
"""
import argparse
import asyncio
import json
import os
from pathlib import Path
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, portal  # noqa: E402

from rich.text import Text  # noqa: E402  (installed with textual)
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical, VerticalScroll  # noqa: E402
from textual.screen import ModalScreen, Screen  # noqa: E402
from textual.widgets import (Button, DataTable, DirectoryTree, Header, Input, Label, OptionList,  # noqa: E402
                             RichLog, Select, Static)

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


def hotkeys(text, keys):
    """Append 'Log  Pause  Stop', each word's key letter highlighted in it (the first letter
    by convention; a key the word lacks is shown before it)."""
    for number, (key, label) in enumerate(keys):
        text.append('  ' if number else '')
        at = label.lower().find(key.lower())
        if at < 0:
            text.append(key, style='bold underline cyan')
            text.append(' ' + label)
        else:
            text.append(label[:at])
            text.append(label[at], style='bold underline cyan')
            text.append(label[at + 1:])


class MenuBar(Static):
    """A screen's keys on one line at the very top, under the title, as a GUI app's menu bar
    ("File Edit View"), each word's key letter highlighted; every screen has one."""
    DEFAULT_CSS = 'MenuBar { dock: top; height: 1; background: $boost; padding: 0 1; }'

    def show(self, keys, prefix=''):
        text = Text(no_wrap=True, overflow='ellipsis')
        if prefix:
            text.append(prefix + '  ', style='dim')
        hotkeys(text, keys)
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


class Confirm(ModalScreen[bool]):
    BINDINGS = [Binding('y', 'answer(True)', 'yes'), Binding('n,escape', 'answer(False)', 'no')]
    DEFAULT_CSS = '''
    Confirm { align: center middle; }
    Confirm > Vertical { width: 76; height: auto; border: thick $warning; background: $surface; padding: 1 2; }
    Confirm Horizontal { height: auto; align-horizontal: right; margin-top: 1; }
    Confirm Button { margin-left: 2; }
    '''

    def __init__(self, question):
        super().__init__()
        self.question = question

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label(self.question)
            with Horizontal():
                yield Button('Yes (y)', variant='warning', id='yes')
                yield Button('No (n)', id='no')

    def _answer(self, value):
        # A button event can arrive after the confirmation was already dismissed (a double
        # click, a queued key, or a refresh that removed the modal). dismiss() would then pop
        # the last remaining screen and crash the whole TUI with ScreenStackError.
        if self.is_current:
            self.dismiss(value)

    def on_button_pressed(self, event):
        self._answer(event.button.id == 'yes')

    def action_answer(self, value):
        self._answer(value)


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


class NewTask(ModalScreen[dict]):
    """A new task's title, short title, goal and section, and optionally its scope and acceptance."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    NewTask { align: center middle; }
    NewTask > VerticalScroll { width: 90; height: auto; max-height: 90%; border: thick $accent; background: $surface; padding: 1 2; }
    NewTask Input, NewTask Select { margin-bottom: 1; }
    NewTask Horizontal { height: auto; align-horizontal: right; }
    NewTask Button { margin-left: 2; }
    '''

    def __init__(self, goals):
        super().__init__()
        self.goals = goals

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


class PickModel(ModalScreen[str]):
    """Choose a model from Pi's own list; type to filter."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    PickModel { align: center middle; }
    PickModel > Vertical { width: 80; height: 80%; border: thick $accent; background: $surface; padding: 1 2; }
    PickModel OptionList { height: 1fr; }
    '''

    def __init__(self, title, models, current):
        super().__init__()
        self.title_text, self.models, self.current = title, models, current

    def compose(self) -> ComposeResult:
        from textual.widgets import Input
        with Vertical():
            yield Label(f'{self.title_text} (now {self.current})')
            yield Input(placeholder='filter, e.g. india or deepseek', id='filter')
            yield OptionList(*self.models, id='models')

    def on_mount(self):
        self.shown = list(self.models)

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


class LogScreen(Screen):
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
        lines = fleet_view.log_lines(self.logs(self.runner, 1000))
        if lines == getattr(self, '_lines', None):
            return
        self._lines = lines
        log = self.query_one('#full-log', RichLog)
        log.clear()
        for line, style in lines:
            log.write(Text(line, style=style))
        if not lines:
            log.write('(no output yet)')


def action_text(line, width=0, stamp=None):
    """One action as a colored line (fleet_view.action_style), cut to ``width`` (0: whole)."""
    text = Text()
    if stamp is not None:
        text.append(stamp + '  ', style='dim')
        width = max(0, width - len(stamp) - 2) if width else 0
    text.append(fleet_view.fit_line(line, width), style=fleet_view.action_style(line))
    return text


class WorkerScreen(Screen):
    """One worker's actions as a log: oldest first, stamped with the time, new ones appended at the
    bottom so the view keeps its place while you scroll back; refreshed. Each action is colored by
    its kind and kept to one line; w shows long ones whole."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'back'), Binding('w', 'toggle_wrap', 'wrap')]

    def __init__(self, runner, task):
        super().__init__()
        self.runner, self.task_id = runner, task  # Screen.task is Textual's own, read-only
        self.shown = []
        self.wrap = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield RichLog(id='worker-actions', wrap=True, highlight=False, markup=False)

    def action_toggle_wrap(self):
        self.wrap = not self.wrap
        self.shown = []  # rewrite every line at the new setting
        self.refresh_actions()

    def on_resize(self, event):
        if not self.wrap:
            self.shown = []  # cut again to the new width
            self.refresh_actions()

    def on_mount(self):
        self.title = f'{self.runner.name}: {self.task_id}'
        self.query_one('#menubar', MenuBar).show([('w', 'Wrap'), ('esc', 'Back')])
        self.refresh_actions()
        self.set_interval(LOG_REFRESH, self.refresh_actions)

    def refresh_actions(self):
        actions = [(at, line) for line, _, at in fleet_view.action_log(self.runner, self.task_id)]
        log = self.query_one('#worker-actions', RichLog)
        last = self.shown[-1] if self.shown else None
        if last in actions:  # append only what is new; a full redraw would lose the scroll position
            fresh = actions[len(actions) - actions[::-1].index(last):]
        else:
            log.clear()
            fresh = actions
            if not actions:
                log.write('No actions recorded yet.')
        width = 0 if self.wrap else max(20, self.size.width - 4)  # border and scrollbar
        for at, line in fresh:
            stamp = time.strftime('%H:%M:%S', time.localtime(at)) if at is not None else '--:--:--'
            log.write(action_text(line, width, stamp))
        if fresh:
            self.shown = actions


class TasksScreen(Screen):
    """One runner's open tasks in priority (section, then rank) order: filter them, re-sort them, clear or
    set aside a hold, answer the owner's questions. Refreshed like the main screen."""
    VIEW_NAMES = {'all': 'All', 'working': 'Active', 'held': 'Blocker', 'waiting': 'Waiting', 'questions': 'Questions'}
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'Back', show=False),
                Binding('tab', 'step_view(1)', 'next view', show=False),
                Binding('shift+tab', 'step_view(-1)', 'previous view', show=False),
                *[Binding(str(n + 1), f'show_view("{view}")', view, show=False)
                  for n, view in enumerate(fleet_view.TASK_VIEWS)],
                *[Binding(key, f'task("{key}")', key, show=False) for key in 'udcabs'],
                Binding('n', 'new_task', 'New', show=False)]
    DEFAULT_CSS = '''
    #task-views { height: 1; padding: 0 1; }
    #tasks { height: 1fr; }
    #task-detail { height: auto; max-height: 7; padding: 0 1; border-top: solid $panel; }
    '''
    # State and Why are cut to what the terminal has left; Why goes first on a narrow one.
    FIXED, TEXT = ('#', 'Task', 'Short'), ('State', 'Why')

    def __init__(self, runner_name):
        super().__init__()
        self.runner_name, self.view, self.rows, self.shown = runner_name, 'all', [], []

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        yield Static(id='task-views')
        yield DataTable(id='tasks', cursor_type='row', zebra_stripes=True)
        yield Static(id='task-detail')

    def on_mount(self):
        self.title = f'{self.runner_name}: tasks'
        self.query_one('#tasks', DataTable).add_columns(*self.FIXED, *self.TEXT)
        self.refresh_tasks()
        self.set_interval(REFRESH, self.refresh_tasks)

    def runner(self):
        return next((r for r in self.app.runners if r.name == self.runner_name), None)

    def refresh_tasks(self, follow=None):
        """``follow``: keep the cursor on this task wherever it moved (after a re-sort)."""
        runner = self.runner()
        self.rows = fleet_view.task_rows(runner, include_closed=True) if runner else []
        views = Text()
        for number, view in enumerate(fleet_view.TASK_VIEWS):
            count = len(fleet_view.task_view(self.rows, view))
            label = f'{number + 1} {self.VIEW_NAMES[view]} {count}'
            views.append(('  ' if number else '') + label, style='bold reverse' if view == self.view else 'dim')
        views.append('   tab next view', style='dim')
        self.query_one('#task-views', Static).update(views)
        table = self.query_one('#tasks', DataTable)
        current = follow or (self.current().task if self.current() else None)
        self.shown = fleet_view.task_view(self.rows, self.view)
        position = {row.task: number + 1 for number, row in enumerate(self.rows)}
        cells = [{'#': (str(position[row.task]), 'dim'), 'Task': (row.task, 'bold'),
                  'Short': (row.short, ''),
                  'State': (row.state, fleet_view.state_style(row)),
                  'Why': (row.why, 'yellow' if row.question else 'dim')} for row in self.shown]
        self.app.fill(table, cells, self.FIXED, self.TEXT, minimum=10)
        tasks = [row.task for row in self.shown]
        if current in tasks and table.cursor_row != tasks.index(current):
            table.move_cursor(row=tasks.index(current))
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
        self.query_one('#menubar', MenuBar).show(([('enter', 'Open')] if row else []) + keys + [('esc', 'Back')])
        self.query_one('#task-detail', Static).update(text)

    def on_data_table_row_selected(self, event):
        row = self.current()
        if row is not None:
            self.app.push_screen(TaskScreen(self.runner_name, row.task))

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
        self.app.push_screen(NewTask(fleet_view.open_goals(runner)), add)

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


class TaskScreen(Screen):
    """One task: its question and the runner's suggested answer, its whole task record and
    its worker's last actions. Answer it here; refreshed like the main screen."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'Back', show=False),
                Binding('s', 'section', 'Section', show=False),
                *[Binding(key, f'answer("{key}")', key, show=False) for key in 'ohrwd']]
    DEFAULT_CSS = '''
    #task-scroll { height: 1fr; padding: 0 1; }
    #task-answers { height: auto; padding: 0 1; border-top: solid $panel; }
    '''

    def __init__(self, runner_name, task):
        super().__init__()
        self.runner_name, self.task_id = runner_name, task

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
        if runner is None or question is None or self.app.view_only:
            return []
        return fleet_view.answers(runner, question, command=self.app.command)

    def refresh_tasks(self, follow=None):
        runner, question = self.runner(), self.question()
        row = next((r for r in fleet_view.task_rows(runner, include_closed=True) if r.task == self.task_id), None) if runner else None
        text = Text()
        text.append(self.task_id, style='bold')
        if row:
            text.append(f'  {row.short}\n')
            text.append(f'{row.section} · {row.state}\n', style=fleet_view.state_style(row) or 'dim')
        else:
            text.append('  (closed, or not in tasks/ now)\n', style='dim')
        if question:
            text.append(f'\nQuestion for you ({question.effort}, unblocks {question.unblocks})\n', style='bold yellow')
            text.append(question.needs + '\n', style='yellow')
            if question.answer:
                text.append('The runner suggests: ', style='bold')
                text.append(question.answer + '\n', style='dim')
        elif row and row.why:
            text.append(row.why + '\n')
        entry = fleet_view.task_entry(runner, self.task_id) if runner else ''
        if entry:
            text.append('\nTask record\n', style='bold')
            text.append(entry + '\n')
        actions = fleet_view.recent_actions(runner, self.task_id) if runner else []
        if actions:
            text.append('\nLast actions\n', style='bold')
            for line, age in actions:
                text.append(f'{fleet_view.ago(age):>9}  ', style='dim')
                text.append_text(action_text(line, max(20, self.size.width - 15)))
                text.append('\n')
        self.query_one('#task-body', Static).update(text)
        answers = self.answers()
        self.query_one('#menubar', MenuBar).show([(a.key, a.label) for a in answers]
                                                 + ([] if self.app.view_only else [('s', 'Section')]) + [('esc', 'Back')])
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

    def action_section(self):
        runner = self.runner()
        if runner is None or self.app.view_only:
            return
        self.app.push_screen(PickSection(self.task_id), lambda section: section and self.app.execute(
            fleet_view.Action('s', f'Section {self.task_id}',
                              [self.app.command, 'tasks', 'place', self.task_id, section, runner.name])))


class PrepareRepository(ModalScreen[str]):
    """Preparation may commit a legacy conversion; starting is a separate choice."""
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
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
                        'With no accepted intent, plan with /docs_sync; Prepare invents no goals or tasks.')
            with Horizontal():
                yield Button('Prepare', variant='primary', id='prepare')
                yield Button('Prepare and start', id='prepare-start')
                yield Button('Cancel', id='cancel')

    def on_button_pressed(self, event):
        self.dismiss(None if event.button.id == 'cancel' else event.button.id)

    def action_cancel(self):
        self.dismiss(None)


class RepoTree(DirectoryTree):
    """Directories only; a repository is marked ready (a committed tasks/ store) or not."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.readiness_cache = {}

    def filter_paths(self, paths):
        return [p for p in paths if p.is_dir() and not p.name.startswith('.')]

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
        if path is not None and (path / '.git').exists():
            if path not in self.readiness_cache:
                self.readiness_cache[path] = fleet_view.readiness(path)
            ready = self.readiness_cache[path]
            label.append('  ' + ready.mark, style='bold green' if ready.ready else 'yellow')
        return label


class BrowseScreen(Screen):
    """Pick a repository and start its service."""
    BINDINGS = [Binding('p', 'start', 'Play'), Binding('escape,q', 'app.pop_screen', 'back')]
    CSS = '''
    #tree { width: 1fr; }
    #info { width: 1fr; padding: 0 1; }
    '''

    def __init__(self, root, start):
        super().__init__()
        self.root, self.start = root, start
        self.chosen = None
        self.preparing = False
        self.prepare_result = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield MenuBar(id='menubar')
        with Horizontal():
            yield RepoTree(self.root, id='tree')
            yield Static('Move to a repository; ready ones have a committed tasks/ store.', id='info')

    def on_mount(self):
        self.title = f'start a runner: {self.root}'
        self.query_one('#menubar', MenuBar).show([('p', 'Play'), ('esc', 'Back')])

    def on_tree_node_highlighted(self, event):
        node = event.node
        if node.data is None:
            return
        self.show_repository(node.data.path)

    def show_repository(self, path):
        self.chosen = fleet_view.readiness(path)
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
            info.append('Press p for Prepare or Prepare and start.\n')
        if self.preparing:
            info.append('\nPreparing repository…\n', style='yellow')
        if self.prepare_result and self.prepare_result[0] == str(path):
            report = self.prepare_result[1]
            info.append('\n' + report['outcome'] + '\n', style='bold')
            for refusal in report.get('refusals', []):
                info.append(str(refusal) + '\n')
            info.append((report.get('next') or 'Resolve the reported problem, then run Prepare again.') + '\n')
            if report['outcome'] == 'NO_STORE':
                info.append('Plan accepted intent with /docs_sync; no goals or tasks were created.\n')
        self.query_one('#info', Static).update(info)

    def action_start(self):
        if self.app.view_only or self.preparing:
            return
        if self.chosen is None:
            self.notify('Choose a repository first.', severity='warning')
            return
        self.show_repository(self.chosen.path)  # never start from a stale readiness result
        if not self.chosen.repo or Path(self.chosen.path).resolve() != Path(self.chosen.repo).resolve():
            self.notify('Choose a Git repository root.', severity='warning')
        elif self.chosen.ready:
            self.start(self.chosen)
        else:
            ready = self.chosen
            self.app.push_screen(PrepareRepository(ready),
                                 lambda choice: choice and self.prepare(ready.path, choice == 'prepare-start'))

    def prepare(self, path, start):
        if self.app.view_only or self.preparing:
            return
        self.preparing = True
        self.prepare_result = None
        self.show_repository(path)
        self.run_worker(lambda: self.run_prepare(path, start), thread=True, group='prepare')

    def run_prepare(self, path, start):
        """Run the supported CLI, not a second implementation of conversion or bootstrap."""
        try:
            result = self.app.runner_cmd([self.app.command, 'tasks', 'prepare', path],
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
        ready = fleet_view.readiness(path)
        tree = self.query_one('#tree', RepoTree)
        tree.update_readiness(ready)
        if self.chosen and self.chosen.path == str(path):
            self.show_repository(path)
            if start and self.chosen.ready and self.app.screen is self:
                self.start(self.chosen)


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
        Binding('f', 'pick_model("fallback")', 'Fallback', show=False),
        Binding('t', 'run("t")', 'Tasks', show=False),
        Binding('u', 'run("u")', 'Uninstall', show=False),
        Binding('n', 'browse', 'New', show=False),
        Binding('o', 'setup_portal', 'Nous Portal', show=False),
        Binding('q', 'quit', 'Quit', show=False),
    ]
    CONTROL = {'run', 'browse', 'pick_model', 'setup_portal'}

    def __init__(self, *, command, script, state_root, env_dir, systemctl='systemctl',
                 journalctl='journalctl', agent=None, runner_cmd=subprocess.run, view_only=False, browse_root=None,
                 list_models=fleet_view.models):
        super().__init__()
        self.list_models = list_models
        self.model_cache = None
        self.command, self.script = command, script
        self.state_root, self.env_dir = state_root, env_dir
        self.systemctl, self.journalctl = systemctl, journalctl
        self.agent = agent
        self.runner_cmd = runner_cmd
        self.view_only = view_only
        self.browse_root = browse_root
        self.runners = []
        self.selected = None

    def check_action(self, action, parameters):
        """View-only (for example served to a browser on a shared network): no control keys."""
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
        table = self.query_one('#runners', DataTable)
        table.add_columns(*self.RUNNER_COLUMNS, *self.RUNNER_TEXT)
        self.query_one('#lanes', DataTable).add_columns(*self.LANE_COLUMNS, *self.LANE_TEXT)
        self.action_refresh()
        self.refresh_log()
        self.set_interval(REFRESH, self.action_refresh)
        self.set_interval(LOG_REFRESH, self.refresh_log)
        self.code = code_stamp()
        self.set_interval(CODE_CHECK, self.reload_if_updated)

    def on_resize(self, event):
        self._shown = {}  # the columns fit the new width
        if self.query_one('#runners', DataTable).columns:  # the first resize comes before on_mount
            self.action_refresh()

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
        if code_stamp() != self.code and len(self.screen_stack) == 1 and not any(w.is_running for w in self.workers):
            self.exit('reload')

    # -- data -------------------------------------------------------------------
    def action_refresh(self):
        self.runners = fleet_view.collect(self.state_root, self.env_dir, systemctl=self.systemctl)
        table = self.query_one('#runners', DataTable)
        keep = self.selected
        rows = []
        for runner in self.runners:
            now = ', '.join(f'{lane.task} {fleet_view.status(lane)[1].lower()}' for lane in runner.lanes[:2])
            if runner.job:
                now = ', '.join(x for x in (fleet_view.job_text(runner.job), now) if x)
            if len(runner.lanes) > 2:
                now += f' +{len(runner.lanes) - 2}'
            active, mergeable, waiting, blocker, decision, total = (str(n) for n in fleet_view.task_counts(runner))
            rows.append({'Runner': (runner.name, ''),
                         'State': (f'{runner.state} {fleet_view.duration(runner.minutes)}'.strip(), f'bold {runner.color}'),
                         'Active': (active, 'green'), 'Mergeable': (mergeable, 'cyan'), 'Waiting': (waiting, ''),
                         'Blocker': (blocker, 'yellow' if blocker != '0' else ''),
                         'Decision': (decision, 'yellow' if decision != '0' else ''), 'Total': (total, 'bold'),
                         'Needs': (' '.join((fleet_view.needs(runner) or '-').split()), 'yellow' if runner.questions else ''),
                         'Now': (now or '-', '')})
        self.fill(table, rows, self.RUNNER_COLUMNS, self.RUNNER_TEXT)
        names = [r.name for r in self.runners]
        if names:
            row = names.index(keep) if keep in names else 0
            if table.cursor_row != row:
                table.move_cursor(row=row)
            self.selected = names[row]
        else:
            self.selected = None
        counts = ', '.join(f'{n} {state}' for state, n in fleet_view.summary(self.runners))
        self.sub_title = f'{len(self.runners)} runners: {counts}' if self.runners else 'no runners'
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
            detail.update('No pi-autowork runners yet. Press n for a new one: choose a repository and play its service.')
            self.query_one('#lanes', DataTable).display = False
            menubar.show([] if self.view_only else [('n', 'New'), ('o', 'Nous Portal'), ('q', 'Quit')])
            return
        # The keys go in the menu bar at the top, like a GUI app's menu; the pane holds the facts.
        if self.view_only:
            menubar.show([('l', 'Log'), ('q', 'Quit')], prefix='view only')
        else:
            menubar.show([(a.key, a.label) for a in self.available(runner)] + [('n', 'New'), ('o', 'Nous Portal'), ('q', 'Quit')])
        text = Text()
        # First the answer to "is it stuck, and why": one sentence, wrapped, never cut.
        sentence, style = fleet_view.verdict(runner)
        text.append(f'{runner.name}  ', style='bold')
        text.append(sentence + '\n', style=style)
        active, mergeable, waiting, blocker, decision, total = fleet_view.task_counts(runner)
        detail_row(text, 'Tasks', f'{total} open · {active} active · {mergeable} mergeable · {waiting} waiting · {blocker} blocker'
                   + f' · {decision} for your decision')
        waiting = fleet_view.waiting_detail(runner)
        if waiting:
            detail_row(text, 'Waiting', waiting)
        blockers = fleet_view.blocker_parts(runner, {q.id for q in runner.questions})
        if blockers:
            detail_row(text, 'Blocker', blockers, 'bold red')
        if runner.questions:  # what the owner can answer, easiest first (BLOCKERS.md)
            count = len(runner.questions)
            detail_row(text, 'Questions', fleet_view.question_summary(runner)
                + ('  (b answers them)' if self.agent and not self.view_only else ''), 'bold yellow')
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
        # Short: the full model IDs are in the m and f pickers.
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
        rows = [{'Task': (lane.task, ''),
                 'Status': (' · '.join(fleet_view.status(lane)), self.STATUS_STYLE[fleet_view.status(lane)[0]]),
                 'Try': (str(lane.attempt), ''), 'For': (fleet_view.duration(lane.minutes), ''),
                 'Quiet': (fleet_view.quiet(lane).removeprefix('quiet '), 'bold yellow'),
                 'Doing': (doing(lane), fleet_view.action_style(doing(lane)))} for lane in runner.lanes]
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
        lines = fleet_view.log_lines(self.logs(runner, 400, since='-60min')) if runner is not None else []
        key = (runner.name if runner else None, lines)
        if key == getattr(self, '_log', None):
            return
        self._log = key
        log.clear()
        for line, style in lines:
            log.write(Text(line, style=style))
        if runner is not None and not lines:
            log.write('(nothing in the last hour; Enter shows the whole log)')

    # -- actions ----------------------------------------------------------------
    def available(self, runner):
        return fleet_view.actions(runner, command=self.command, script=self.script, agent=self.agent)

    def action_run(self, key):
        runner = self.current()
        if runner is None:
            if key == 'p':
                self.action_browse()
            return
        if key == 'l':
            self.push_screen(LogScreen(runner, self.logs))
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

    def action_setup_portal(self):
        def prepared(result):
            if result:
                self.model_cache = None
                self.notify(result['message'], timeout=10)
        self.push_screen(PortalSetup(), prepared)

    def action_pick_model(self, which):
        runner = self.current()
        if runner is None or not runner.has_service:
            self.notify('Models are set per service; play one first (p, or n for a new one).', severity='warning')
            return
        try:
            if self.list_models is fleet_view.models:
                settings = fleet_view.read_env(Path(self.env_dir) / f'{runner.name}.env')
                self.model_cache = self.list_models(pi=os.environ.get('AUTOWORK_PI', 'pi'),
                    agent_dir=portal.service_agent_dir(settings))
            elif self.model_cache is None:
                self.model_cache = self.list_models()
        except portal.SetupError as error:
            self.notify(str(error), severity='error', timeout=10)
            return
        if not self.model_cache:
            self.notify("Pi listed no models (pi --list-models).", severity='error')
            return
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
        self.push_screen(PickModel(title, self.model_cache, current), chosen)

    def action_browse(self):
        root = self.browse_root or (Path.home() / 'git' if (Path.home() / 'git').is_dir() else Path.home())
        self.push_screen(BrowseScreen(str(root), self.start_repository))

    def start_repository(self, ready):
        action = fleet_view.Action('a', f'start {Path(ready.repo).name}', [self.command, 'start', ready.repo],
                                   confirm=f'Start a pi-autowork service for {ready.repo}?')

        def go(yes):
            if yes:
                current = fleet_view.readiness(ready.path)
                if not current.ready:
                    self.notify('Repository is no longer ready: ' + ', '.join(current.problems), severity='warning')
                    if isinstance(self.screen, BrowseScreen):
                        self.screen.show_repository(ready.path)
                    return
                self.pop_screen()
                self.execute(action)
        self.push_screen(Confirm(action.confirm), go)

    def execute(self, action):
        env = {**os.environ, **action.env}
        if action.interactive:
            with self.suspend():
                self.runner_cmd(action.argv, env=env)
            self.action_refresh()
            return
        # A restart or stop waits for the runner to stop gracefully (up to the unit's 150 s):
        # run it off the event loop, or the whole TUI freezes and looks crashed.
        self.notify(f'{action.label}: running...', timeout=4)
        self.run_worker(lambda: self.finish_action(action, env), thread=True, group='actions')

    def finish_action(self, action, env):
        """In a worker thread: run the command, then report it on the event loop."""
        try:
            result = self.runner_cmd(action.argv, env=env, capture_output=True, text=True)
            output = ((result.stdout or '') + (result.stderr or '')).strip().splitlines()
            ok, message = result.returncode == 0, (output[-1] if output else action.label)
        except OSError as error:
            ok, message = False, str(error)
        self.call_from_thread(self.notify, message[:300], severity='information' if ok else 'error',
                              title=f'{action.label}: {"done" if ok else "failed"}')
        self.call_from_thread(self.action_refresh)
        if isinstance(self.screen, (TasksScreen, TaskScreen)):
            self.call_from_thread(self.screen.refresh_tasks, getattr(self.screen, 'follow', None))


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
        os.execv(sys.executable, [sys.executable, str(Path(__file__).resolve()),
                                  *(sys.argv[1:] if argv is None else argv)])
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
