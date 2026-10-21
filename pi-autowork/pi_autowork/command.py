"""`autowork`: run, watch and control pi-autowork runners. Standard library only.

    autowork                      the live TUI (on a terminal; help otherwise)
    autowork ls [--long] [--json] every runner: state, workers, what it waits on
    autowork status [target]      one runner's full status
    autowork logs [-f] [target]   the runner's service journal
    autowork start [dir]          install (if needed) and start the repository's service
    autowork stop [target]
    autowork restart [target] [--stop-workers]
                                  reload the runner in place: new release and settings, running
                                  workers keep running; --stop-workers pauses them instead
    autowork pause|resume [target]
                                  stop the service and keep it off (also after a reboot), or
                                  start it again; workers resume on the same attempt
    autowork model [target] [provider/model] [--fallback provider/model]
                                  show or set the service's Pi model, then restart it
    autowork models [search]      Pi's model list (pi --list-models)
    autowork remove [target]      stop and remove the service; state and worktrees stay
    autowork run [dir]            run the runner here, in the foreground (debugging)
    autowork web [--port N] [--host H] [--view-only]
    autowork blockers [dir]       answer what blocks the queue (/blockers in an agent)
    autowork update [flags]       update the installed suite in place (install.sh update)
    autowork clear-held [target] [TASK...]
                                  return held commits to integration as technical recovery
                                  (keeps the worktrees); no owner decision is asked
    autowork tasks list|validate|new-id [target]   autowork tasks show|why TASK [target]
                                  read a tasks/ store at HEAD (validate --worktree: uncommitted)
    autowork tasks add|field|place|move|hold|release|done|supersede ... [target]
                                  edit task files in the working tree (never commits): an
                                  owner answer ("Owner decision", "Held by", "Blocker
                                  resolution" notes), a new section or rank (the priority)
    autowork tasks prepare [target] [--check|--no-commit]
                                  detect, convert, recover and diagnose the store (Docs Sync's
                                  first step; --check writes nothing)
    autowork migrate [target] [--dry-run] [--no-commit]
                                  convert a repository to the tasks/ store once (one local commit)
    autowork scorecard [--days N] [--json] [target...]
                                  per runner: tasks closed, held share, start to merge, owner
                                  questions over the last N days (default 7)

A systemd user service (`pi-autowork@<repository name>`) is the default way to run a
repository's runner. A target is a runner name (sierra), a repository path, or `.`.
Nothing here calls a model; the TUI and web view run Textual through `uv`.
"""
import argparse
import dataclasses
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, scorecard, service, task_commands, task_migrate  # noqa: E402

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


PI_SOURCE = 'git:github.com/TrebuchetDynamics/autowork'


def package_script():
    """pi-autowork.sh in the Pi package installed from PI_SOURCE (`pi list`), or None."""
    try:
        lines = subprocess.run([os.environ.get('AUTOWORK_PI', 'pi'), 'list'], capture_output=True, text=True,
                               timeout=60).stdout.splitlines()
    except (OSError, subprocess.SubprocessError):
        return None
    for i, line in enumerate(lines[:-1]):
        if line.split()[:1] == [PI_SOURCE]:
            found = Path(lines[i + 1].strip()) / 'scripts' / 'pi-autowork.sh'
            return str(found) if found.is_file() else None
    return None


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


def runners(paths, *, strict=False):
    return fleet_view.collect(paths['state_root'], paths['env_dir'], systemctl=paths['systemctl'], strict=strict)


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
    fleet_view.paused_marker(paths['env_dir'], name).unlink(missing_ok=True)  # starting ends a pause
    state = service_state(paths, name)
    # Services run from the Pi package installed from PI_SOURCE. A unit that runs another
    # copy (a package installed under an older name) is moved onto it:
    # reinstalling rewrites the shared unit and restarts this service, whose workers pause
    # and resume; the other services follow when they next restart.
    target = os.environ.get('PI_AUTOWORK_SCRIPT') or package_script()
    runs = unit_script(paths)
    if state != 'none' and target and runs and Path(runs).resolve() != Path(target).resolve():
        print(f'Moving pi-autowork services from {runs} to {target}.', flush=True)
        code = subprocess.run(['bash', target, '--install-service', '--repo', ready.repo]).returncode
        others = [r.name for r in runners(paths) if r.name != name and r.service in ('running', 'start', 'reload')]
        if not code and others:
            print(f'Still on the old copy until restarted: {", ".join(others)} (autowork restart NAME).')
        return code
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
    return subprocess.run(['bash', target or script(paths), '--install-service', '--repo', ready.repo]).returncode


def restart(paths, name, repo, stop_workers=False):
    """(code, message): reload a running runner in place, else restart its service."""
    unit = f'pi-autowork@{name}.service'
    if not stop_workers and service_state(paths, name) == 'active':
        done, text = service.reload_in_place(paths['systemctl'], unit, paths['state_root'], repo)
        if done is not None:
            return (0 if done else 1), text
    if systemctl(paths, 'restart', unit, quiet=False).returncode:
        raise Fail(f'could not restart {unit}')
    return 0, f'Restarted {unit}; workers paused and resume on the same attempt.'


def cmd_restart(args, paths):
    repo, name = resolve(args.target, paths)
    if service_state(paths, name) == 'none':
        raise Fail(f'{name} has no service; start one with: autowork start {repo}')
    code, text = restart(paths, name, repo, args.stop_workers)
    print(text)
    return code


def cmd_stop(args, paths, action='stop'):
    repo, name = resolve(args.target, paths)
    unit = f'pi-autowork@{name}.service'
    if service_state(paths, name) == 'none':
        raise Fail(f'{name} has no service; start one with: autowork start {repo}')
    if systemctl(paths, action, unit, quiet=False).returncode:
        raise Fail(f'could not {action} {unit}')
    print(f'Stopped {unit}.')
    return 0


def cmd_pause(args, paths, resume=False):
    repo, name = resolve(args.target, paths)
    unit = f'pi-autowork@{name}.service'
    if service_state(paths, name) == 'none':
        raise Fail(f'{name} has no service; start one with: autowork start {repo}')
    verb = 'enable' if resume else 'disable'
    if systemctl(paths, verb, '--now', unit, quiet=False).returncode:
        raise Fail(f'could not {"resume" if resume else "pause"} {unit}')
    marker = fleet_view.paused_marker(paths['env_dir'], name)
    if resume:
        marker.unlink(missing_ok=True)
    else:  # so a paused service is told apart from one that is simply not running
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text('paused with autowork pause\n')
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
        code, text = restart(paths, name, repo)
        print(f'{text} New runs use the new model.' if not code else text)
        return code
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
    try:
        found = runners(paths, strict=True)
    except fleet_view.DiscoveryUnavailable as error:
        raise Fail(str(error)) from error
    if args.json:
        # Everything the TUI shows, for a script or an agent watching the fleet.
        print(json.dumps({'runners': [dataclasses.asdict(r) for r in found]}, indent=2, default=str))
        return 0
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


def cmd_scorecard(args, paths):
    if args.target:
        found = [resolve(target, paths) for target in args.target]
    else:
        found = [(r.repo, r.name) for r in runners(paths) if r.repo]
    rows = {name: scorecard.measure(repo, args.days) for repo, name in found}
    if args.json:
        print(json.dumps({'days': args.days, 'runners': rows}, indent=2))
    else:
        print('\n'.join(scorecard.table(rows, args.days)))
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
    if args.mouse:
        argv.append('--mouse')
    os.execvp(argv[0], argv)


def cmd_web(args, paths):
    argv = uv_python(TEXTUAL, TEXTUAL_SERVE) + [str(COMPONENT / 'pi_autowork' / 'tui_web.py'), '--command',
                                                self_path(), '--script', script(paths), '--host', args.host,
                                                '--port', str(args.port)] + (['--view-only'] if args.view_only else [])
    print(f'autowork: serving the TUI at http://{args.host}:{args.port} (Ctrl+C stops it)', file=sys.stderr)
    os.execvp(argv[0], argv)


def cmd_update(args, paths):
    """Update the installed suite in place: the same items as a full install."""
    installer = Path(os.environ.get('AUTOWORK_INSTALLER') or (TOOLSET / 'install.sh'))
    if not installer.is_file():
        raise Fail(f'no installer at {installer}; update the package first: pi update {PI_SOURCE}')
    return subprocess.run(['bash', str(installer), 'update', *args.extra], check=False).returncode


def cmd_blockers(args, paths):
    repo, _ = resolve(args.target, paths)
    agent = fleet_view.blockers_agent()
    if not agent:
        raise Fail('no agent for /blockers: install claude or pi, or set AUTOWORK_AGENT')
    # In the repository: started from the TUI or the home directory, Claude Code asked whether
    # to trust the whole home directory, and the session was not the repository's.
    os.chdir(repo)
    os.execvp(agent[0], [*agent, fleet_view.blockers_prompt(agent, repo)])


def cmd_clear_held(args, paths):
    """Return held commits to integration as technical recovery; no owner decision is asked."""
    repo, name = resolve(args.target, paths)
    runner = next((r for r in runners(paths) if r.name == name), None)
    if runner is None:
        raise Fail(f'no runner named {name}')
    held = [task for task, _ in runner.held]
    if args.tasks:
        wanted = {t for t in re.split(r'[,\s]+', ' '.join(args.tasks)) if t}
        unknown = sorted(wanted - set(held))
        if unknown:
            raise Fail('not held: ' + ', '.join(unknown))
        held = [t for t in held if t in wanted]
    if not held:
        print(f'{name}: no held tasks to clear.')
        return 0
    if args.dry_run:
        print(f'{name}: would clear {len(held)} held task(s): ' + ', '.join(held))
        return 0
    if not runner.state_dir:
        raise Fail(f'{name}: no state directory yet; start the runner once: autowork start {repo}')
    requests = Path(runner.state_dir) / 'requests'
    requests.mkdir(parents=True, exist_ok=True)
    for task in held:
        (requests / f'clear-held-{task}').touch()
    print(f'{name}: requested technical recovery for {len(held)} held task(s): ' + ', '.join(held))
    print('Each held commit goes back to integration with its worktrees kept; the runner acts within a cycle.')
    if runner.service not in ('running', 'start', 'reload'):
        print(f'Start the runner to apply it: autowork start {repo}')
    return 0


def cmd_tasks(args, paths):
    """`autowork tasks ...` on the tasks/ store of a runner name, path or `.`."""
    return task_commands.run(args, resolve(args.repo, paths)[0])


def parser():
    top = argparse.ArgumentParser(prog='autowork', description=__doc__,
                                  formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = top.add_subparsers(dest='command')
    ls = sub.add_parser('ls', help='every runner, one line each')
    ls.add_argument('--long', '-v', action='store_true', help='add workers in flight and blockers')
    ls.add_argument('--json', action='store_true', help="every field the TUI shows, as JSON")
    ls.add_argument('--brief', '-b', action='store_true', help=argparse.SUPPRESS)
    for name, help_text in (('status', "one runner's full status"), ('stop', 'stop the runner'),
                            ('remove', 'stop and remove the service'),
                            ('start', "install (if needed) and start the repository's service"),
                            ('run', 'run the runner here in the foreground'),
                            ('blockers', 'answer what blocks the queue')):
        item = sub.add_parser(name, help=help_text)
        item.add_argument('target', nargs='?', help='runner name, repository path or . (default: .)')
    clear = sub.add_parser('clear-held', help='return held commits to integration (technical recovery, no decision)')
    clear.add_argument('target', nargs='?', help='runner name, repository path or . (default: .)')
    clear.add_argument('tasks', nargs='*', help='task IDs to clear (default: every held task)')
    clear.add_argument('--dry-run', action='store_true', help='list what would be cleared')
    again = sub.add_parser('restart', help='reload the runner in place; running workers keep running')
    again.add_argument('target', nargs='?', help='runner name, repository path or . (default: .)')
    again.add_argument('--stop-workers', action='store_true',
                       help='restart the service instead: workers pause and resume on the same attempt')
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
    tui.add_argument('--mouse', action='store_true', help='Capture clicks; default allows terminal text selection')
    for name, help_text in (('pause', 'stop the service and keep it off'), ('resume', 'start a paused service again')):
        item = sub.add_parser(name, help=help_text)
        item.add_argument('target', nargs='?')
    model = sub.add_parser('model', help="show or set a service's Pi model")
    model.add_argument('target', nargs='?')
    model.add_argument('model', nargs='?', help='provider/model, from: autowork models')
    model.add_argument('--fallback', help='the fallback provider/model')
    models = sub.add_parser('models', help="Pi's model list")
    models.add_argument('search', nargs='?')
    update = sub.add_parser('update', help='update the installed suite in place (install.sh update)')
    update.add_argument('extra', nargs='*', help='extra install.sh flags (for example -q or --dry-run)')
    card = sub.add_parser('scorecard', help='per runner: tasks closed, held share, start to merge, owner questions')
    card.add_argument('--days', type=int, default=7)
    card.add_argument('--json', action='store_true')
    card.add_argument('target', nargs='*', help='runner names or repository paths (default: every runner)')
    task_commands.add_parser(sub)
    task_migrate.add_parser(sub)
    sub.add_parser('help', help='this help')
    return top


COMMANDS = {'ls': cmd_ls, 'status': cmd_status, 'logs': cmd_logs, 'start': cmd_start,
            'stop': cmd_stop, 'restart': cmd_restart, 'remove': cmd_remove,
            'run': cmd_run, 'web': cmd_web, 'tui': cmd_tui, 'blockers': cmd_blockers,
            'pause': cmd_pause, 'resume': lambda a, p: cmd_pause(a, p, resume=True),
            'model': cmd_model, 'models': cmd_models, 'scorecard': cmd_scorecard,
            'clear-held': cmd_clear_held, 'update': cmd_update, 'tasks': cmd_tasks,
            'migrate': lambda a, p: task_migrate.run(a, resolve(a.repo, p)[0])}


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    top = parser()
    if not argv:
        if sys.stdin.isatty() and sys.stdout.isatty() and os.environ.get('AUTOWORK_TUI', '1') != '0':
            argv = ['tui']
        else:
            top.print_help()
            return 0
    # `update` forwards arbitrary install.sh flags, so take its unknowns as those flags and
    # keep the strict parse for every other command.
    args, extra = top.parse_known_args(argv)
    if args.command == 'update':
        args.extra = [*args.extra, *extra]
    elif extra:
        top.error('unrecognized arguments: ' + ' '.join(extra))
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
