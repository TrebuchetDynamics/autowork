"""`autowork`: the live view of every pi-autowork runner, with controls.

Bare `autowork` on a terminal runs this through `uv run --with textual==8.2.8`, so the
runner itself stays standard-library only. It reads runner state (status.json, engine
slots, systemd, logs, Pi transcripts) every few seconds and calls no model. Every
action runs an `autowork` command (or the runner script); there is no second way to
change a runner. `d` browses directories and starts a service for a repository that
has TODO.md and goals.json on its main branch.

    python3 tui.py --command PATH --script PATH [--view-only]
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view  # noqa: E402

from rich.text import Text  # noqa: E402  (installed with textual)
from textual.app import App, ComposeResult  # noqa: E402
from textual.binding import Binding  # noqa: E402
from textual.containers import Horizontal, Vertical  # noqa: E402
from textual.screen import ModalScreen, Screen  # noqa: E402
from textual.widgets import (Button, DataTable, DirectoryTree, Footer, Header, Label, OptionList,  # noqa: E402
                             RichLog, Static)

REFRESH = 3.0
LOG_REFRESH = 5.0
QUESTIONS_SHOWN = 3


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

    def on_button_pressed(self, event):
        self.dismiss(event.button.id == 'yes')

    def action_answer(self, value):
        self.dismiss(value)


class PickTask(ModalScreen[str]):
    BINDINGS = [Binding('escape', 'cancel', 'cancel')]
    DEFAULT_CSS = '''
    PickTask { align: center middle; }
    PickTask > Vertical { width: 70; height: auto; max-height: 80%; border: thick $accent; background: $surface; padding: 1 2; }
    '''

    def __init__(self, tasks):
        super().__init__()
        self.tasks = tasks

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Label('Set aside which held task?')
            yield OptionList(*[f'{task}  {fleet_view.CAUSES.get(cause, cause or "")}' for task, cause in self.tasks])

    def on_option_list_option_selected(self, event):
        self.dismiss(self.tasks[event.option_index][0])

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
        yield RichLog(id='full-log', wrap=True, highlight=False, markup=False)
        yield Footer()

    def on_mount(self):
        self.title = f'{self.runner.name}: log'
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


class WorkerScreen(Screen):
    """One worker's last actions, newest first, in plain words; refreshed."""
    BINDINGS = [Binding('escape,q', 'app.pop_screen', 'back')]

    def __init__(self, runner, task):
        super().__init__()
        self.runner, self.task = runner, task

    def compose(self) -> ComposeResult:
        yield Header()
        yield Static(id='worker-actions')
        yield Footer()

    def on_mount(self):
        self.title = f'{self.runner.name}: {self.task}'
        self.refresh_actions()
        self.set_interval(LOG_REFRESH, self.refresh_actions)

    def refresh_actions(self):
        text = Text()
        actions = fleet_view.recent_actions(self.runner, self.task)
        for line, age in actions:
            text.append(f'{fleet_view.ago(age):>9}  ', style='dim')
            text.append(line + '\n')
        self.query_one('#worker-actions', Static).update(text if actions else 'No actions recorded yet.')


class RepoTree(DirectoryTree):
    """Directories only; a repository is marked ready (TODO.md and goals.json) or not."""

    def filter_paths(self, paths):
        return [p for p in paths if p.is_dir() and not p.name.startswith('.')]

    def render_label(self, node, base_style, style):
        label = super().render_label(node, base_style, style)
        path = node.data.path if node.data else None
        if path is not None and (path / '.git').exists():
            have = [name for name in fleet_view.REQUIRED if (path / name).is_file()]
            if len(have) == len(fleet_view.REQUIRED):
                label.append('  ready', style='bold green')
            else:
                label.append('  needs ' + ', '.join(n for n in fleet_view.REQUIRED if n not in have), style='yellow')
        return label


class BrowseScreen(Screen):
    """Pick a repository and start its service."""
    BINDINGS = [Binding('s', 'start', 'start service'), Binding('escape,q', 'app.pop_screen', 'back')]
    CSS = '''
    #tree { width: 1fr; }
    #info { width: 1fr; padding: 0 1; }
    '''

    def __init__(self, root, start):
        super().__init__()
        self.root, self.start = root, start
        self.chosen = None

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield RepoTree(self.root, id='tree')
            yield Static('Move to a repository; ready ones have TODO.md and goals.json.', id='info')
        yield Footer()

    def on_mount(self):
        self.title = f'start a runner: {self.root}'

    def on_tree_node_highlighted(self, event):
        node = event.node
        if node.data is None:
            return
        self.chosen = fleet_view.readiness(node.data.path)
        info = Text()
        info.append(str(node.data.path) + '\n', style='bold')
        if self.chosen.ready:
            info.append('ready', style='bold green')
            info.append(f' on {self.chosen.branch}. Press s to start its service.\n')
        elif not self.chosen.repo:
            info.append('not a Git repository\n', style='dim')
        else:
            info.append(f'not ready: needs {", ".join(self.chosen.problems)}\n', style='bold yellow')
            for hint in fleet_view.how_to_fix(self.chosen):
                info.append(f'  {hint}\n')
        self.query_one('#info', Static).update(info)

    def action_start(self):
        if self.chosen is None or not self.chosen.ready:
            self.notify('Choose a ready repository (TODO.md and goals.json on its main branch).', severity='warning')
            return
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
        Binding('enter', 'run("enter")', 'log'),
        Binding('d', 'browse', 'start a repository'),
        Binding('a', 'run("a")', 'start'),
        Binding('s', 'run("s")', 'stop'),
        Binding('R', 'run("R")', 'restart'),
        Binding('p', 'run("p")', 'pause/resume'),
        Binding('m', 'pick_model("model")', 'model'),
        Binding('M', 'pick_model("fallback")', 'fallback'),
        Binding('u', 'run("u")', 'remove service'),
        Binding('x', 'set_aside', 'set aside'),
        Binding('b', 'run("b")', 'blockers'),
        Binding('r', 'refresh', 'refresh'),
        Binding('q', 'quit', 'quit'),
    ]
    CONTROL = {'run', 'set_aside', 'browse', 'pick_model'}

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
        if self.view_only and action in self.CONTROL:
            return False
        if action == 'run' and parameters and parameters[0] == 'enter':
            return True
        return True

    # -- layout -----------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        yield DataTable(id='runners', cursor_type='row', zebra_stripes=True)
        yield Static(id='detail')
        yield DataTable(id='lanes', cursor_type='row', zebra_stripes=True)
        yield RichLog(id='log', wrap=True, highlight=False, markup=False)
        yield Footer()

    def on_mount(self):
        table = self.query_one('#runners', DataTable)
        table.add_columns('Runner', 'State', 'Needs', 'Tasks', 'Now')
        self.query_one('#lanes', DataTable).add_columns('Task', 'Phase', 'Try', 'For', 'Doing')
        self.action_refresh()
        self.refresh_log()
        self.set_interval(REFRESH, self.action_refresh)
        self.set_interval(LOG_REFRESH, self.refresh_log)

    # -- data -------------------------------------------------------------------
    def action_refresh(self):
        self.runners = fleet_view.collect(self.state_root, self.env_dir, systemctl=self.systemctl)
        table = self.query_one('#runners', DataTable)
        keep = self.selected
        rows = []
        for runner in self.runners:
            now = ', '.join(f'{lane.task} {lane.phase}' for lane in runner.lanes[:2])
            if runner.job:
                now = ', '.join(x for x in (fleet_view.job_text(runner.job), now) if x)
            if len(runner.lanes) > 2:
                now += f' +{len(runner.lanes) - 2}'
            state = f'{runner.state} {fleet_view.duration(runner.minutes)}'.strip()
            tasks = f'{runner.running} run  {runner.waiting} wait  {len(runner.held)} held'
            rows.append((runner.name, state, runner.color, fleet_view.short(fleet_view.needs(runner) or '-', 44),
                         bool(runner.questions), tasks, fleet_view.short(now or '-', 40)))
        # Redraw only what changed: a clear-and-rewrite every refresh made panes flicker
        # and repaint over each other.
        if rows != getattr(self, '_rows', None):
            self._rows = rows
            table.clear()
            for name, state, color, need, asked, tasks, now in rows:
                table.add_row(name, Text(state, style=f'bold {color}'), Text(need, style='yellow' if asked else ''),
                              tasks, now, key=name)
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
            self.action_run('enter')
        elif event.data_table.id == 'lanes' and event.row_key is not None and self.current() is not None:
            self.push_screen(WorkerScreen(self.current(), event.row_key.value))

    def show_detail(self):
        detail = self.query_one('#detail', Static)
        runner = self.current()
        if runner is None:
            detail.update('No pi-autowork runners yet. Press d to choose a repository and start its service.')
            self.query_one('#lanes', DataTable).display = False
            return
        text = Text()
        # First the answer to "is it stuck, and why": one sentence, wrapped, never cut.
        sentence, style = fleet_view.verdict(runner)
        text.append(f'{runner.name}  ', style='bold')
        text.append(sentence + '\n', style=style)
        waiting = fleet_view.waiting_line(runner)
        if waiting:
            text.append(f'{runner.waiting} waiting: ', style='dim')
            text.append(waiting + '\n')
        if runner.questions:  # what the owner can answer, easiest first (BLOCKERS.md)
            count = len(runner.questions)
            text.append(f"{count} question{'s' if count > 1 else ''} for you in BLOCKERS.md", style='bold yellow')
            text.append('  (b answers them)\n' if self.agent and not self.view_only else '\n', style='dim')
            for q in runner.questions[:QUESTIONS_SHOWN]:
                text.append(f'  {q.id}', style='bold')
                text.append(f'  {q.effort}, unblocks {q.unblocks}: ', style='dim')
                text.append(q.needs + '\n')
            if count > QUESTIONS_SHOWN:
                text.append(f'  +{count - QUESTIONS_SHOWN} more\n', style='dim')
        checked = fleet_view.main_check.line(runner.main_check)
        if checked:
            text.append(checked + '\n', style='bold red' if checked.startswith('main red') else 'dim')
        repair = fleet_view.maintainer_line(runner)
        if repair:
            text.append(repair + '\n', style='cyan')
        if runner.held:
            text.append('held: ', style='bold yellow')
            text.append(', '.join(t + (f' {fleet_view.CAUSES.get(c, c)}' if c else '') for t, c in runner.held) + '\n')
        details = [runner.repo or '(repository unknown)']
        if runner.model:
            details.append(f'model {runner.model}, fallback {runner.fallback}')
        text.append('  '.join(details) + '\n', style='dim')
        if runner.toolset:  # a development checkout instead of the Pi package: say so
            text.append(f'toolset {runner.toolset} (PI_AUTOWORK_TOOLSET, not the Pi package)\n', style='yellow')
        if self.view_only:
            text.append('view only', style='dim')
        else:
            text.append('  '.join(f'[{a.key}] {a.label}' for a in self.available(runner)) + '  [d] start a repository',
                        style='dim')
        if text.plain != getattr(self, '_detail', None):
            self._detail = text.plain
            detail.update(text)
        self.show_lanes(runner)

    def show_lanes(self, runner):
        """One row per worker: phase, attempt, how long, and what it is doing in plain words."""
        table = self.query_one('#lanes', DataTable)
        rows = []
        for lane in runner.lanes:
            quiet = fleet_view.quiet(lane)
            rows.append((lane.task, lane.phase, str(lane.attempt), fleet_view.duration(lane.minutes),
                         fleet_view.doing(lane), quiet))
        if rows != getattr(self, '_lane_rows', None):
            self._lane_rows = rows
            keep = table.cursor_row
            table.clear()
            for task, phase, attempt, minutes, doing, quiet in rows:
                activity = Text(doing)
                if quiet:
                    activity.append(f'  {quiet}', style='bold yellow')
                style = 'bold yellow' if phase.startswith('waiting') else 'bold green'
                table.add_row(task, Text(phase, style=style), attempt, minutes, activity, key=task)
            if rows:
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
    def available(self, runner, task=None):
        return fleet_view.actions(runner, command=self.command, script=self.script, agent=self.agent, task=task)

    def action_run(self, key, task=None):
        runner = self.current()
        if runner is None:
            if key == 'a':
                self.action_browse()
            return
        if key == 'enter':
            self.push_screen(LogScreen(runner, self.logs))
            return
        if self.view_only:
            return
        action = next((a for a in self.available(runner, task) if a.key == key), None)
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
            self.notify('Models are set per service; start one first (a, or d to browse).', severity='warning')
            return
        if self.model_cache is None:
            self.model_cache = self.list_models()
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

    def action_set_aside(self):
        runner = self.current()
        if runner is None or not runner.held:
            self.notify('No held task to set aside here.', severity='warning')
            return
        self.push_screen(PickTask(runner.held), lambda task: task and self.action_run('x', task))

    def action_browse(self):
        root = self.browse_root or (Path.home() / 'git' if (Path.home() / 'git').is_dir() else Path.home())
        self.push_screen(BrowseScreen(str(root), self.start_repository))

    def start_repository(self, ready):
        action = fleet_view.Action('a', f'start {Path(ready.repo).name}', [self.command, 'start', ready.repo],
                                   confirm=f'Start a pi-autowork service for {ready.repo}?')

        def go(yes):
            if yes:
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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--command', required=True, help='The autowork launcher, for every action.')
    parser.add_argument('--script', required=True, help='pi-autowork.sh, for set-aside.')
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    state = os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local' / 'state')
    parser.add_argument('--state-root', default=os.environ.get('PI_AUTOWORK_STATE_DIR') or f'{state}/pi-autowork')
    parser.add_argument('--env-dir', default=os.environ.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork')
    parser.add_argument('--browse-root', default=os.environ.get('AUTOWORK_BROWSE_ROOT'))
    parser.add_argument('--view-only', action='store_true', help='Show runners; disable every control key.')
    args = parser.parse_args(argv)
    FleetApp(command=args.command, script=args.script, state_root=args.state_root, env_dir=args.env_dir,
             systemctl=os.environ.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl'),
             journalctl=os.environ.get('AUTOWORK_JOURNALCTL', 'journalctl'),
             agent=fleet_view.blockers_agent(), view_only=args.view_only, browse_root=args.browse_root).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
