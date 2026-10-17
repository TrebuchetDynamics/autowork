"""`autowork`: run, watch and control pi-autowork runners. Standard library only.

    autowork                      the live TUI (on a terminal; help otherwise)
    autowork ls [--long]          every runner: state, workers, what it waits on
    autowork status [target]      one runner's full status
    autowork logs [-f] [target]   the runner's service journal
    autowork start [dir]          install (if needed) and start the repository's service
    autowork stop|restart [target]
    autowork pause|resume [target]
                                  stop the service and keep it off (also after a reboot), or
                                  start it again; workers resume on the same attempt
    autowork model [target] [provider/model] [--fallback provider/model]
                                  show or set the service's Pi model, then restart it
    autowork models [search]      Pi's model list (pi --list-models)
    autowork remove [target]      stop and remove the service; state and worktrees stay
    autowork run [dir]            run the runner here, in the foreground (debugging)
    autowork web [--port N] [--host H] [--view-only]
    autowork blockers [dir]       answer what blocks the queue (/autowork blockers in an agent)

A systemd user service (`pi-autowork@<repository name>`) is the default way to run a
repository's runner. A target is a runner name (sierra), a repository path, or `.`.
Nothing here calls a model; the TUI and web view run Textual through `uv`.
"""
import argparse
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view  # noqa: E402

COMPONENT = Path(__file__).resolve().parents[1]
TOOLSET = COMPONENT.parent
TEXTUAL = os.environ.get('AUTOWORK_TEXTUAL', 'textual==8.2.8')
TEXTUAL_SERVE = os.environ.get('AUTOWORK_TEXTUAL_SERVE', 'textual-serve==1.1.3')
COLORS = {'green': '32', 'yellow': '33', 'red': '31'}


class Fail(Exception):
    """A message for the user and exit status 1."""


def env_paths(env=os.environ):
    config = env.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    state = env.get('XDG_STATE_HOME') or str(Path.home() / '.local' / 'state')
    return {
        'env_dir': env.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork',
        'unit': Path(env.get('PI_AUTOWORK_UNIT_DIR') or f'{config}/systemd/user') / 'pi-autowork@.service',
        'state_root': env.get('PI_AUTOWORK_STATE_DIR') or f'{state}/pi-autowork',
        'systemctl': env.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl'),
        'journalctl': env.get('AUTOWORK_JOURNALCTL', 'journalctl'),
    }


def script(paths):
    """pi-autowork.sh: the one the installed unit runs, else this release's."""
    override = os.environ.get('PI_AUTOWORK_SCRIPT')
    if override:
        return override
    runs = unit_script(paths)
    if runs and Path(runs).is_file():
        return runs
    return str(TOOLSET / 'scripts' / 'pi-autowork.sh')


def self_path():
    """The `autowork` launcher, for the TUI's actions."""
    return os.environ.get('AUTOWORK_COMMAND') or str(COMPONENT / 'bin' / 'autowork')


def runners(paths):
    return fleet_view.collect(paths['state_root'], paths['env_dir'], systemctl=paths['systemctl'])


def resolve(target, paths):
    """A runner name, a path or `.` -> (repository, instance name)."""
    target = target or '.'
    if '/' in target or target in ('.', '..') or Path(target).is_dir():
        ready = fleet_view.readiness(target)
        if not ready.repo:
            raise Fail(f'not inside a Git repository: {target}')
        return ready.repo, fleet_view.instance(ready.repo)
    name = target
    env_file = Path(paths['env_dir']) / f'{name}.env'
    if env_file.is_file():
        match = re.search(r'(?m)^PI_AUTOWORK_REPO=(.*)$', env_file.read_text())
        if match:
            return match.group(1).strip(), name
    for runner in runners(paths):
        if runner.name == name and runner.repo:
            return runner.repo, name
    raise Fail(f'no runner named {name}; pass a repository path, or see: autowork ls')


def systemctl(paths, *argv, quiet=True):
    return subprocess.run([paths['systemctl'], '--user', *argv], capture_output=quiet, text=True)


def unit_script(paths):
    """The script the installed unit runs, or None without a unit."""
    try:
        match = re.search(r'(?m)^ExecStart=\S*bash (\S*pi-autowork\.sh) ', paths['unit'].read_text())
    except OSError:
        return None
    return match.group(1) if match else None


def service_state(paths, name):
    """'active', 'installed' (unit enabled or settings present), 'stale' (its unit runs a
    script that is gone, as after removing the package it came from) or 'none'."""
    unit = f'pi-autowork@{name}.service'
    runs = unit_script(paths)
    if runs and not Path(runs).is_file():
        return 'stale'
    if systemctl(paths, 'is-active', '--quiet', unit).returncode == 0:
        return 'active'
    if (Path(paths['env_dir']) / f'{name}.env').is_file() or \
            systemctl(paths, 'is-enabled', '--quiet', unit).returncode == 0:
        return 'installed'
    return 'none'


# -- commands ---------------------------------------------------------------------
def cmd_start(args, paths):
    ready = fleet_view.readiness(args.target or '.')
    if not ready.ready:
        problems = [f'  - {hint}' for hint in fleet_view.how_to_fix(ready)] or [f'  - needs {ready.mark}']
        raise Fail(f'{ready.repo or ready.path} is not ready for Autowork ({ready.mark}):\n' + '\n'.join(problems))
    name = fleet_view.instance(ready.repo)
    unit = f'pi-autowork@{name}.service'
    state = service_state(paths, name)
    if state == 'active':
        print(f'{unit} is already running {ready.repo}.')
        return 0
    if state == 'installed':
        # enable as well, so it comes back after a reboot or a new login
        result = systemctl(paths, 'enable', '--now', unit, quiet=False)
        if result.returncode:
            raise Fail(f'could not start {unit}')
        print(f'Started {unit} for {ready.repo}.')
        return 0
    # 'none', or 'stale': reinstall from this release (the unit is shared, so every service follows)
    return subprocess.run(['bash', script(paths), '--install-service', '--repo', ready.repo]).returncode


def cmd_stop(args, paths, action='stop'):
    repo, name = resolve(args.target, paths)
    unit = f'pi-autowork@{name}.service'
    if service_state(paths, name) == 'none':
        raise Fail(f'{name} has no service; start one with: autowork start {repo}')
    if systemctl(paths, action, unit, quiet=False).returncode:
        raise Fail(f'could not {action} {unit}')
    print(f'{action.capitalize()}ped {unit}.' if action == 'stop' else f'Restarted {unit}.')
    return 0


def cmd_pause(args, paths, resume=False):
    repo, name = resolve(args.target, paths)
    unit = f'pi-autowork@{name}.service'
    if service_state(paths, name) == 'none':
        raise Fail(f'{name} has no service; start one with: autowork start {repo}')
    verb = 'enable' if resume else 'disable'
    if systemctl(paths, verb, '--now', unit, quiet=False).returncode:
        raise Fail(f'could not {"resume" if resume else "pause"} {unit}')
    print(f'Resumed {unit}.' if resume else
          f'Paused {unit}: stopped, and it stays off until: autowork resume {name}')
    return 0


def pi_models(search=None):
    found = fleet_view.models(os.environ.get('AUTOWORK_PI', 'pi'), search)
    if not found:
        raise Fail('Pi listed no models (pi --list-models); check Pi and its logins')
    return found


def cmd_models(args, paths):
    for model in pi_models(args.search):
        print(model)
    return 0


def cmd_model(args, paths):
    repo, name = resolve(args.target, paths)
    env_file = Path(paths['env_dir']) / f'{name}.env'
    if not env_file.is_file():
        raise Fail(f'{name} has no service yet; start it first: autowork start {repo}')
    settings = fleet_view.read_env(env_file)
    updates = {}
    if args.model:
        updates['PI_AUTOWORK_PRIMARY'] = args.model
    if args.fallback:
        updates['PI_AUTOWORK_FALLBACK'] = args.fallback
    if not updates:
        print(f'{name}: model {settings.get("PI_AUTOWORK_PRIMARY") or fleet_view.DEFAULT_MODEL}, '
              f'fallback {settings.get("PI_AUTOWORK_FALLBACK") or fleet_view.DEFAULT_FALLBACK}')
        return 0
    known = set(pi_models())
    unknown = [m for m in updates.values() if m not in known]
    if unknown:
        raise Fail(f"not in Pi's model list: {', '.join(unknown)} (see: autowork models)")
    fleet_view.write_env(env_file, updates)
    unit = f'pi-autowork@{name}.service'
    print(f'{name}: ' + ', '.join(f'{"model" if k.endswith("PRIMARY") else "fallback"} {v}' for k, v in updates.items()))
    if service_state(paths, name) == 'active':
        if systemctl(paths, 'restart', unit, quiet=False).returncode:
            raise Fail(f'could not restart {unit}')
        print(f'Restarted {unit}; workers resume on the same attempt with the new model for new runs.')
    return 0


def cmd_remove(args, paths):
    repo, _ = resolve(args.target, paths)
    return subprocess.run(['bash', script(paths), '--remove-service', '--repo', repo]).returncode


def cmd_run(args, paths):
    ready = fleet_view.readiness(args.target or '.')
    if not ready.repo:
        raise Fail(f'not inside a Git repository: {args.target or "."}')
    os.execvp('bash', ['bash', script(paths), '--repo', ready.repo])


def cmd_status(args, paths):
    repo, _ = resolve(args.target, paths)
    os.execvp('bash', ['bash', script(paths), '--repo', repo, '--status'])


def cmd_logs(args, paths):
    _, name = resolve(args.target, paths)
    argv = [paths['journalctl'], '--user', '-u', f'pi-autowork@{name}.service', '-n', str(args.lines), '-o', 'cat']
    os.execvp(argv[0], argv + (['-f'] if args.follow else ['--no-pager']))


def paint(text, color, enabled):
    return f'\033[{COLORS.get(color, "31")}m{text}\033[0m' if enabled else text


def cmd_ls(args, paths):
    found = runners(paths)
    color = os.environ.get('NO_COLOR') is None and (os.environ.get('AUTOWORK_COLOR') == 'always'
                                                    or (os.environ.get('AUTOWORK_COLOR') != 'never' and sys.stdout.isatty()))
    width = shutil.get_terminal_size((100, 24)).columns
    fit = lambda line: line if len(line) <= width else line[:width - 3] + '...'
    if not found:
        print('autowork runners: none\n  start one from a repository with: autowork start')
        return 0
    summary = ', '.join(paint(f'{n} {state}', fleet_view.COLORS.get(state, 'red'), color)
                        for state, n in fleet_view.summary(found))
    print(f'autowork runners: {len(found)} ({summary})')
    name_w = max(len(r.name) for r in found)
    for r in found:
        label = f'{r.state} {fleet_view.duration(r.minutes)}'.strip()
        counts = f'{r.running} running, {r.waiting} waiting' + (f', {len(r.held)} held' if r.held else '')
        if not args.long:
            row = fit(f'  {r.name:<{name_w}}  {r.mode or "-":<8}  {label:<14}  {counts}')
            print(row.replace(f'{label:<14}', paint(f'{label:<14}', r.color, color), 1))
            continue
        print(f'\n{r.name}  {r.mode or "-"}  {paint(label, r.color, color)}')
        print(fit(f'  {counts}  {r.repo}'))
        if r.model:
            print(fit(f'  model {r.model}, fallback {r.fallback}'))
        for lane in r.lanes:
            print(fit(f'  {lane.task}: {lane.phase} {fleet_view.duration(lane.minutes)}'
                      + (f'  {lane.activity} ({fleet_view.ago(lane.activity_age)})' if lane.activity else '')))
        for kind, items in fleet_view.blockers(r):
            print(fit(f'  {kind}: {items}'))
    print(fit('\nMore: autowork ls --long   autowork status <name>   autowork (the TUI)'))
    return 0


def uv_python(*packages):
    if not shutil.which('uv'):
        raise Fail('the TUI needs uv (https://docs.astral.sh/uv/)')
    argv = ['uv', 'run', '--quiet', '--no-project']
    for package in packages:
        argv += ['--with', package]
    return argv + ['python3']


def cmd_tui(args, paths):
    argv = uv_python(TEXTUAL) + [str(COMPONENT / 'pi_autowork' / 'tui.py'), '--command', self_path(),
                                 '--script', script(paths)] + (['--view-only'] if args.view_only else [])
    os.execvp(argv[0], argv)


def cmd_web(args, paths):
    argv = uv_python(TEXTUAL, TEXTUAL_SERVE) + [str(COMPONENT / 'pi_autowork' / 'tui_web.py'), '--command',
                                                self_path(), '--script', script(paths), '--host', args.host,
                                                '--port', str(args.port)] + (['--view-only'] if args.view_only else [])
    print(f'autowork: serving the TUI at http://{args.host}:{args.port} (Ctrl+C stops it)', file=sys.stderr)
    os.execvp(argv[0], argv)


def cmd_blockers(args, paths):
    repo, _ = resolve(args.target, paths)
    agent = fleet_view.blockers_agent()
    if not agent:
        raise Fail('no agent for /autowork blockers: install claude or pi, or set AUTOWORK_AGENT')
    os.execvp(agent[0], [*agent, f'/autowork blockers {repo}'])


def parser():
    top = argparse.ArgumentParser(prog='autowork', description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = top.add_subparsers(dest='command')
    ls = sub.add_parser('ls', help='every runner, one line each')
    ls.add_argument('--long', '-v', action='store_true', help='add workers in flight and blockers')
    ls.add_argument('--brief', '-b', action='store_true', help=argparse.SUPPRESS)
    for name, help_text in (('status', "one runner's full status"), ('stop', 'stop the runner'),
                            ('restart', "restart the runner's service"), ('remove', 'stop and remove the service'),
                            ('start', "install (if needed) and start the repository's service"),
                            ('run', 'run the runner here in the foreground'),
                            ('blockers', 'answer what blocks the queue')):
        item = sub.add_parser(name, help=help_text)
        item.add_argument('target', nargs='?', help='runner name, repository path or . (default: .)')
    logs = sub.add_parser('logs', help="the runner's recent output")
    logs.add_argument('-f', '--follow', action='store_true')
    logs.add_argument('-n', '--lines', type=int, default=200)
    logs.add_argument('target', nargs='?')
    web = sub.add_parser('web', help='the TUI in a web browser')
    web.add_argument('--host', default='127.0.0.1')
    web.add_argument('--port', type=int, default=8765)
    web.add_argument('--view-only', action='store_true')
    tui = sub.add_parser('tui', help='the live TUI (also: autowork with no command)')
    tui.add_argument('--view-only', action='store_true')
    for name, help_text in (('pause', 'stop the service and keep it off'), ('resume', 'start a paused service again')):
        item = sub.add_parser(name, help=help_text)
        item.add_argument('target', nargs='?')
    model = sub.add_parser('model', help="show or set a service's Pi model")
    model.add_argument('target', nargs='?')
    model.add_argument('model', nargs='?', help='provider/model, from: autowork models')
    model.add_argument('--fallback', help='the fallback provider/model')
    models = sub.add_parser('models', help="Pi's model list")
    models.add_argument('search', nargs='?')
    sub.add_parser('help', help='this help')
    return top


COMMANDS = {'ls': cmd_ls, 'status': cmd_status, 'logs': cmd_logs, 'start': cmd_start,
            'stop': cmd_stop, 'restart': lambda a, p: cmd_stop(a, p, 'restart'), 'remove': cmd_remove,
            'run': cmd_run, 'web': cmd_web, 'tui': cmd_tui, 'blockers': cmd_blockers,
            'pause': cmd_pause, 'resume': lambda a, p: cmd_pause(a, p, resume=True),
            'model': cmd_model, 'models': cmd_models}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    top = parser()
    if not argv:
        if sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('AUTOWORK_TUI', '1') != '0':
            argv = ['tui']
        else:
            top.print_help()
            return 0
    args = top.parse_args(argv)
    if args.command in (None, 'help'):
        top.print_help()
        return 0
    try:
        return COMMANDS[args.command](args, env_paths()) or 0
    except Fail as exc:
        print(f'autowork: {exc}', file=sys.stderr)
        return 1


if __name__ == '__main__':
    raise SystemExit(main())
