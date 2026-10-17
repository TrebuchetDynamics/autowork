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
        log = self.query_one('#full-log', RichLog)
        log.clear()
        log.write(self.logs(self.runner, 1000) or '(no output yet)')


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
    CSS = '''
    #runners { width: auto; max-width: 60%; }
    #side { width: 1fr; }
    #detail { height: auto; max-height: 40%; padding: 0 1; }
    #lanes { height: auto; max-height: 12; border-top: solid $panel; border-bottom: solid $panel; }
    #log { height: 1fr; }
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

    def __init__(self, *, command, script, state_root, env_dir, tmux='tmux', systemctl='systemctl',
                 journalctl='journalctl', agent=None, runner_cmd=subprocess.run, view_only=False, browse_root=None,
                 list_models=fleet_view.models):
        super().__init__()
        self.list_models = list_models
        self.model_cache = None
        self.command, self.script = command, script
        self.state_root, self.env_dir = state_root, env_dir
        self.tmux, self.systemctl, self.journalctl = tmux, systemctl, journalctl
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
        with Horizontal():
            yield DataTable(id='runners', cursor_type='row', zebra_stripes=True)
            with Vertical(id='side'):
                yield Static(id='detail')
                yield DataTable(id='lanes', cursor_type='none', zebra_stripes=True)
                yield RichLog(id='log', wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self):
        table = self.query_one('#runners', DataTable)
        table.add_columns('Runner', 'Mode', 'State', 'For', 'Run', 'Wait', 'Held', 'Now')
        self.query_one('#lanes', DataTable).add_columns('Task', 'Phase', 'Try', 'For', 'Last activity')
        self.action_refresh()
        self.set_interval(REFRESH, self.action_refresh)
        self.set_interval(LOG_REFRESH, self.refresh_log)

    # -- data -------------------------------------------------------------------
    def action_refresh(self):
        self.runners = fleet_view.collect(self.state_root, self.env_dir, tmux=self.tmux, systemctl=self.systemctl)
        table = self.query_one('#runners', DataTable)
        keep = self.selected
        table.clear()
        for runner in self.runners:
            now = ', '.join(f'{lane.task} {lane.phase}' for lane in runner.lanes[:2])
            if len(runner.lanes) > 2:
                now += f' +{len(runner.lanes) - 2}'
            table.add_row(runner.name, runner.mode or '-', Text(runner.state, style=f'bold {runner.color}'),
                          fleet_view.duration(runner.minutes), str(runner.running), str(runner.waiting),
                          str(len(runner.held)), fleet_view.short(now or '-', 40), key=runner.name)
        names = [r.name for r in self.runners]
        if names:
            row = names.index(keep) if keep in names else 0
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
        """Enter on a runner (the table takes the key itself): its full-screen log."""
        if event.data_table.id == 'runners':
            self.action_run('enter')

    def show_detail(self):
        detail = self.query_one('#detail', Static)
        runner = self.current()
        if runner is None:
            detail.update('No pi-autowork runners yet. Press d to choose a repository and start its service.')
            self.query_one('#lanes', DataTable).display = False
            return
        text = Text()
        text.append(runner.name, style='bold')
        text.append(f'  {runner.mode or "no runner"}  ')
        text.append(f'{runner.state} {fleet_view.duration(runner.minutes)}'.strip(), style=f'bold {runner.color}')
        text.append(f'\n{runner.repo or "(repository unknown)"}\n', style='dim')
        text.append(f'{runner.running} running, {runner.waiting} waiting, {len(runner.held)} held\n')
        if runner.model:
            text.append('model ', style='dim')
            text.append(runner.model)
            text.append('  fallback ', style='dim')
            text.append(runner.fallback + '\n')
        for kind, items in fleet_view.blockers(runner):
            text.append(f'{kind}: ', style='bold yellow')
            text.append(items + '\n')
        if runner.held and runner.state == 'working':
            text.append('held: ', style='bold yellow')
            text.append(', '.join(t + (f' {fleet_view.CAUSES.get(c, c)}' if c else '') for t, c in runner.held) + '\n')
        if self.view_only:
            text.append('view only', style='dim')
        else:
            text.append('  '.join(f'[{a.key}] {a.label}' for a in self.available(runner)) + '  [d] start a repository',
                        style='dim')
        detail.update(text)
        self.show_lanes(runner)

    def show_lanes(self, runner):
        """One row per task in flight: phase, attempt, how long, and the worker's last action."""
        table = self.query_one('#lanes', DataTable)
        table.clear()
        for lane in runner.lanes:
            stale = lane.activity_age is not None and lane.activity_age > 1800
            activity = Text(f'{lane.activity}  {fleet_view.ago(lane.activity_age)}'.strip() or '-',
                            style='dim' if stale else '')
            phase = Text(lane.phase, style='bold yellow' if lane.phase.startswith('waiting') else 'bold green')
            table.add_row(lane.task, phase, str(lane.attempt), fleet_view.duration(lane.minutes), activity)
        table.display = bool(runner.lanes)

    def logs(self, runner, lines=200):
        return fleet_view.logs(runner, lines=lines, tmux=self.tmux, journalctl=self.journalctl)

    def refresh_log(self):
        log = self.query_one('#log', RichLog)
        runner = self.current()
        log.clear()
        if runner is not None:
            log.write(self.logs(runner) or '(no output yet)')

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
        result = self.runner_cmd(action.argv, env=env, capture_output=True, text=True)
        output = ((result.stdout or '') + (result.stderr or '')).strip().splitlines()
        message = output[-1] if output else action.label
        self.notify(message[:300], severity='information' if result.returncode == 0 else 'error',
                    title=f'{action.label}: {"done" if result.returncode == 0 else "failed"}')
        self.action_refresh()


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
             tmux=os.environ.get('AUTOWORK_TMUX', 'tmux'),
             systemctl=os.environ.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl'),
             journalctl=os.environ.get('AUTOWORK_JOURNALCTL', 'journalctl'),
             agent=fleet_view.blockers_agent(), view_only=args.view_only, browse_root=args.browse_root).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
