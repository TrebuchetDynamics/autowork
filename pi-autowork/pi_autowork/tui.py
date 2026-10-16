"""`tx autowork` on a terminal: a live view of every pi-autowork runner, with controls.

Run by `tx autowork` through `uv run --with textual==8.2.8`, so the runner itself stays
standard-library only. It reads runner state (status.json, tmux, systemd, logs) every
few seconds and calls no model. Every action runs a command that already exists
(`tx autowork ...`, `pi-autowork.sh ...`, `systemctl --user ...`); there is no second
way to change a runner.

    python3 tui.py --tx PATH --script PATH [--state-root DIR] [--env-dir DIR]
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
from textual.screen import ModalScreen  # noqa: E402
from textual.widgets import Button, DataTable, Footer, Header, Label, OptionList, RichLog, Static  # noqa: E402

REFRESH = 3.0
LOG_REFRESH = 5.0


class Confirm(ModalScreen[bool]):
    BINDINGS = [Binding('y', 'answer(True)', 'yes'), Binding('n,escape', 'answer(False)', 'no')]
    DEFAULT_CSS = '''
    Confirm { align: center middle; }
    Confirm > Vertical { width: 70; height: auto; border: thick $warning; background: $surface; padding: 1 2; }
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


class FleetApp(App):
    TITLE = 'pi-autowork'
    CSS = '''
    #runners { width: auto; max-width: 60%; }
    #side { width: 1fr; }
    #detail { height: auto; max-height: 50%; padding: 0 1; border-bottom: solid $panel; }
    #log { height: 1fr; }
    '''
    BINDINGS = [
        Binding('enter', 'run("enter")', 'open session'),
        Binding('a', 'run("a")', 'start'),
        Binding('s', 'run("s")', 'stop'),
        Binding('i', 'run("i")', 'install service'),
        Binding('u', 'run("u")', 'remove service'),
        Binding('x', 'set_aside', 'set aside'),
        Binding('b', 'run("b")', 'blockers'),
        Binding('r', 'refresh', 'refresh'),
        Binding('q', 'quit', 'quit'),
    ]

    def __init__(self, *, tx, script, state_root, env_dir, tmux='tmux', systemctl='systemctl',
                 journalctl='journalctl', agent=None, runner_cmd=subprocess.run):
        super().__init__()
        self.tx, self.script = tx, script
        self.state_root, self.env_dir = state_root, env_dir
        self.tmux, self.systemctl, self.journalctl = tmux, systemctl, journalctl
        self.agent = agent
        self.runner_cmd = runner_cmd
        self.runners = []
        self.selected = None

    # -- layout -----------------------------------------------------------------
    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            yield DataTable(id='runners', cursor_type='row', zebra_stripes=True)
            with Vertical(id='side'):
                yield Static(id='detail')
                yield RichLog(id='log', wrap=False, highlight=False, markup=False)
        yield Footer()

    def on_mount(self):
        table = self.query_one('#runners', DataTable)
        table.add_columns('Runner', 'Mode', 'State', 'For', 'Run', 'Wait', 'Held')
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
            table.add_row(runner.name, runner.mode or '-', Text(runner.state, style=f'bold {runner.color}'),
                          fleet_view.duration(runner.minutes), str(runner.running), str(runner.waiting),
                          str(len(runner.held)), key=runner.name)
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
        if event.row_key is not None and event.row_key.value != self.selected:
            self.selected = event.row_key.value
            self.show_detail()
            self.refresh_log()

    def show_detail(self):
        detail = self.query_one('#detail', Static)
        runner = self.current()
        if runner is None:
            detail.update('No pi-autowork runners. Start one with: tx autowork <repo>, or install a service (i).')
            return
        text = Text()
        text.append(runner.name, style='bold')
        text.append(f'  {runner.mode or "no runner"}  ')
        text.append(f'{runner.state} {fleet_view.duration(runner.minutes)}'.strip(), style=f'bold {runner.color}')
        text.append(f'\n{runner.repo or "(repository unknown)"}\n', style='dim')
        text.append(f'tx {runner.session}', style='cyan')
        if runner.view:
            text.append('  (journal view open)', style='dim')
        text.append(f'\n{runner.running} running, {runner.waiting} waiting, {len(runner.held)} held\n')
        for kind, items in fleet_view.blockers(runner):
            text.append(f'{kind}: ', style='bold yellow')
            text.append(items + '\n')
        if runner.held and runner.state == 'working':
            text.append('held: ', style='bold yellow')
            text.append(', '.join(t + (f' {fleet_view.CAUSES.get(c, c)}' if c else '') for t, c in runner.held) + '\n')
        keys = '  '.join(f'[{a.key}] {a.label}' for a in self.available(runner))
        text.append(keys, style='dim')
        detail.update(text)

    def refresh_log(self):
        log = self.query_one('#log', RichLog)
        runner = self.current()
        log.clear()
        if runner is not None:
            log.write(fleet_view.logs(runner, lines=200, tmux=self.tmux, journalctl=self.journalctl)
                      or '(no output yet)')

    # -- actions ----------------------------------------------------------------
    def available(self, runner, task=None):
        return fleet_view.actions(runner, tx=self.tx, script=self.script, systemctl=self.systemctl,
                                  agent=self.agent, task=task)

    def action_run(self, key, task=None):
        runner = self.current()
        if runner is None:
            return
        action = next((a for a in self.available(runner, task) if a.key == key), None)
        if action is None:
            self.notify(f'Nothing to do with "{key}" for {runner.name} right now.', severity='warning')
            return
        if action.confirm:
            self.push_screen(Confirm(action.confirm), lambda yes: yes and self.execute(action))
        else:
            self.execute(action)

    def action_set_aside(self):
        runner = self.current()
        if runner is None or not runner.held:
            self.notify('No held task to set aside here.', severity='warning')
            return
        self.push_screen(PickTask(runner.held), lambda task: task and self.action_run('x', task))

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
    parser.add_argument('--tx', required=True, help='The tx launcher, for session and stop actions.')
    parser.add_argument('--script', required=True, help='pi-autowork.sh, for service and set-aside actions.')
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    state = os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local' / 'state')
    parser.add_argument('--state-root', default=os.environ.get('PI_AUTOWORK_STATE_DIR') or f'{state}/pi-autowork')
    parser.add_argument('--env-dir', default=os.environ.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork')
    args = parser.parse_args(argv)
    FleetApp(tx=args.tx, script=args.script, state_root=args.state_root, env_dir=args.env_dir,
             tmux=os.environ.get('TX_TMUX', 'tmux'), systemctl=os.environ.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl'),
             journalctl=os.environ.get('TX_JOURNALCTL', 'journalctl'),
             agent=fleet_view.blockers_agent()).run()
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
