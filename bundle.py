"""Bundle setup, imported skill aliases, and read-only command diagnostics."""

from functools import partial
import hashlib
import json
from pathlib import Path
import re
import subprocess
import os
import sys
import time

ROOT = Path(__file__).resolve().parent


def defaults():
    return json.loads((ROOT / 'plugins/defaults.json').read_text(encoding='utf-8'))


def record_skill_repository(home, source, names):
    """Record expected imports before installation so partial setup stays visible."""
    path = Path(home) / '.toolset-imports.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    state[source] = sorted(names)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state, indent=2) + '\n')
    temporary.replace(path)


def missing_skill_imports(home, command_names):
    path = Path(home) / '.toolset-imports.json'
    state = json.loads(path.read_text()) if path.exists() else {}
    expected = set(defaults()['required_skills'])
    missing_sources = []
    for line in (ROOT / 'plugins/PLUGINS.md').read_text().splitlines():
        fields = line.split()
        if fields and fields[0] == 'skills':
            if fields[1] not in state:
                missing_sources.append(fields[1])
            expected.update(state.get(fields[1], []))
    return sorted(expected - command_names), missing_sources


def _alias(name):
    name = re.sub(r'[^a-z0-9-]', '-', name.lower().replace('_', '-')).strip('-')
    if len(name) > 32:
        name = name[:23] + '-' + hashlib.sha256(name.encode()).hexdigest()[:8]
    return name


def register_imported_skills(ctx, invoke):
    from hermes_cli.commands import resolve_command
    from hermes_cli.plugins import get_plugin_commands, get_plugin_manager

    manager = get_plugin_manager()
    commands = get_plugin_commands()
    allowed = defaults()['imported_plugins']
    aliases = {}
    for info in manager.list_plugin_skill_metadata():
        namespace, sep, name = info['name'].partition(':')
        if not sep or namespace not in allowed:
            continue
        if info.get('frontmatter', {}).get('user-invocable') is False:
            continue
        command = _alias(name)
        # Keep an upstream native command when it already implements this skill.
        if command in commands and commands[command].get('plugin') == namespace:
            continue
        if not command or resolve_command(command) is not None or command in commands:
            command = _alias(f'{namespace}-{name}')
        if not command or resolve_command(command) is not None or command in commands:
            continue
        path = manager.find_plugin_skill(info['name'])
        if path is None or not path.is_file():
            continue
        ctx.register_command(command, partial(invoke, ctx, name, path, namespace=namespace),
                             description=f"Run {info['name']}", args_hint='[instructions]')
        aliases[command] = info['name']
    return aliases


def inventory():
    from hermes_cli.plugins import get_plugin_commands, get_plugin_manager
    from hermes_cli.commands_platforms import telegram_menu_commands, telegram_menu_max_commands
    from agent.skill_commands import get_skill_commands

    manager = get_plugin_manager()
    manager.discover_and_load()
    plugins = manager.list_plugins()
    wanted = set(defaults()['imported_plugins']) | {'autowork'}
    rows = []
    for name, item in sorted(get_plugin_commands().items()):
        if item.get('plugin') in wanted:
            rows.append({'command': name, 'telegram': name.replace('-', '_'),
                         'source': item['plugin'], 'kind': 'plugin'})
    for name, item in sorted(get_skill_commands().items()):
        name = name.lstrip('/')
        rows.append({'command': name, 'telegram': name.replace('-', '_'),
                     'source': item.get('name', name), 'kind': 'skill'})
    menu_limit = telegram_menu_max_commands()
    menu, hidden = telegram_menu_commands(max_commands=menu_limit)
    menu_names = dict(menu)
    for row in rows:
        row['in_telegram_menu'] = row['telegram'] in menu_names
    selected = [dict(p) for p in plugins if p['name'] in wanted]
    loaded = {p['name'] for p in selected if p.get('enabled') and not p.get('error')}
    required = wanted
    missing_skills, unchecked_sources = missing_skill_imports(
        manager.home_path, {row['command'] for row in rows})
    return {'plugins': selected, 'missing_plugins': sorted(required - loaded),
            'plugin_skills': sorted(info['name'] for info in manager.list_plugin_skill_metadata()
                                    if info['name'].partition(':')[0] in wanted),
            'missing_skills': missing_skills, 'unchecked_skill_sources': unchecked_sources,
            'commands': rows, 'telegram_menu_hidden': hidden, 'telegram_menu_limit': menu_limit,
            'note': 'Menu capacity is limited; typed commands and /autowork list remain available.'}


# Workflow commands shown first in the overview, in Telegram spelling.
LEAD_WORKFLOWS = ('plan_with_me', 'plan_for_me', 'docs_sync', 'autowork', 'cron_autowork', 'git_commit_push')


def _ago(started_ns):
    try:
        minutes = max(0, int((time.time_ns() - int(started_ns)) / 60e9))
    except (TypeError, ValueError):
        return ''
    if minutes < 60:
        return f'{minutes} min ago'
    return f'{minutes // 60} h ago' if minutes < 48 * 60 else f'{minutes // 1440} days ago'


def _identity():
    """Bundle revision and the profile serving this chat, best effort."""
    try:
        revision = subprocess.run(['git', '-C', str(ROOT), 'rev-parse', '--short', 'HEAD'],
                                  capture_output=True, text=True, timeout=5).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        revision = ''
    try:
        from hermes_constants import get_hermes_home
        home = Path(get_hermes_home()).expanduser()
        profile = home.name if home.parent.name == 'profiles' else 'default'
    except Exception:
        profile = ''
    return revision, profile


def _last_update():
    try:
        result = json.loads((update_home() / 'maintenance/toolset-update/latest.json').read_text())
    except Exception:
        return None
    after = sorted({s.get('after', '')[:7] for s in (result.get('sources') or {}).values()} - {''})
    when = _ago(result.get('started_ns'))
    return (f"Last update: {result.get('status', 'unknown')}"
            + (f', {when}' if when else '') + (f", at {', '.join(after)}" if after else '')
            + ' · /autowork update status')


def overview(report):
    """A short, actionable /autowork status reply: what is installed, ready, missing and next."""
    revision, profile = _identity()
    own = next((p for p in report['plugins'] if p['name'] == 'autowork'), None)
    version = f" {own['version']}" if own and own.get('version') else ''
    head = f'Autowork{version}' + (f' ({revision})' if revision else '')
    if profile:
        head += f' · profile {profile}'
    if own and own.get('error'):
        head += f": error — {own['error']}"
    elif own and not own.get('enabled'):
        head += ': disabled'
    lines = [head]
    available = {row['telegram'] for row in report['commands']}
    ready = [name for name in LEAD_WORKFLOWS if name in available]
    toolset_skills = [n for n in report['plugin_skills'] if n.startswith('autowork:')]
    if ready:
        lines.append('Ready: ' + ' '.join('/' + name for name in ready)
                     + (f' · {len(toolset_skills)} skills, {len(report["commands"])} commands in all'
                        if toolset_skills else ''))
    last = _last_update()
    if last:
        lines.append(last)
    for plugin in report['plugins']:
        if plugin['name'] == 'autowork':
            continue
        name = plugin['name'] + (f" {plugin['version']}" if plugin.get('version') else '')
        if plugin.get('error'):
            lines.append(f"{name}: error — {plugin['error']}")
            continue
        if not plugin.get('enabled'):
            lines.append(f'{name}: disabled')
            continue
        skills = sum(n.startswith(plugin['name'] + ':') for n in report['plugin_skills'])
        counts = [f'{n} {label}' for n, label in ((plugin.get('tools', 0), 'tools'),
                  (plugin.get('commands', 0), 'commands'), (skills, 'skills'), (plugin.get('hooks', 0), 'hooks')) if n]
        lines.append(f'{name}: loaded' + (f" — {', '.join(counts)}" if counts else ''))
        if plugin.get('memory_provider'):
            lines.append('  memory provider; server connectivity not checked')
    gaps = []
    if report['missing_plugins']:
        gaps.append('plugins ' + ', '.join(report['missing_plugins']))
    if report['missing_skills']:
        gaps.append('skills ' + ', '.join(report['missing_skills']))
    if report['unchecked_skill_sources']:
        gaps.append('skill sources ' + ', '.join(report['unchecked_skill_sources']))
    if gaps:
        lines.append('Needs setup: ' + '; '.join(gaps) + ' → hermes autowork setup')
    if report['telegram_menu_hidden']:
        lines.append(f"Telegram menu hides {report['telegram_menu_hidden']} commands; type them directly.")
    lines.append('More: /autowork list · /autowork update · hermes autowork doctor')
    return lines


def list_commands(raw_args=''):
    report = inventory()
    request = raw_args.strip().lower()
    if not request:
        return '\n'.join(overview(report))
    query = request[5:].strip() if request.startswith('list ') else ('' if request == 'list' else request)
    rows = [r for r in report['commands'] if not query or query in r['command'] or query in r['source']]
    lines = [f'Autowork commands: {len(rows)} matches']
    for row in rows:
        alias = f" (Telegram: /{row['telegram']})" if row['telegram'] != row['command'] else ''
        lines.append(f"/{row['command']}{alias} — {row['source']}")
    if report['missing_plugins']:
        lines.append('Missing/disabled plugins: ' + ', '.join(report['missing_plugins']))
    lines.extend(f"{p['name']}: {p['error']}" for p in report['plugins'] if p.get('error'))
    if report['missing_skills']:
        lines.append('Unavailable skill commands (missing, blocked, or ambiguous): ' + ', '.join(report['missing_skills']))
    if report['unchecked_skill_sources']:
        lines.append('Skill repositories not yet set up: ' + ', '.join(report['unchecked_skill_sources']))
    return '\n'.join(lines)


def update_home():
    from hermes_constants import get_hermes_home
    home = Path(get_hermes_home()).expanduser()
    return home.parent.parent if home.parent.name == 'profiles' else home


def updater_alive(pid):
    """Return whether an updater pid still runs, reaping our own exited child first."""
    try:
        pid = int(pid)
    except (ValueError, TypeError):
        return False
    if pid <= 0:
        return False
    try:
        # The gateway discards the Popen, so an exited chat child stays a zombie.
        if os.waitpid(pid, os.WNOHANG)[0] == pid:
            return False
    except ChildProcessError:
        pass
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    try:
        state = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except (OSError, IndexError):
        return True
    return state not in ('Z', 'X')


def _updater():
    """The updater module, loaded by path like its subprocess."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('autowork_update_bundle', ROOT / 'update_bundle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def gateway_drain(folder):
    """Restart progress from the updater module."""
    return _updater().gateway_drain(folder)


def finish_restart(home, folder):
    """Record and return the outcome of a requested restart that has finished, else None."""
    return _updater().finish_restart(home, folder)


def linked_profiles():
    """Profiles whose plugin links to a working checkout, or None when that cannot be read."""
    try:
        return _updater().fleet_linked_profiles(update_home())
    except (Exception, SystemExit):
        return None


def linked_lines(rows):
    if not rows:
        return []
    names = ', '.join(r['profile'] for r in rows)
    targets = ', '.join(sorted({r['target'] for r in rows}))
    return [f'Linked to a working checkout ({targets}); any gateway restart loads its current files: {names}',
            'Preview pinning one to its current revision: hermes autowork pin NAME --dry-run']


def last_restart(folder, started_ns):
    """The recorded outcome of the last updater restart this receipt does not cover, or None."""
    try:
        updater = _updater()
        marker = updater._read_marker(folder)
        if 'pid' in marker and not marker.get('finished') and not gateway_drain(folder):
            updater.finish_restart(folder.parent.parent, folder)
            marker = updater._read_marker(folder)
    except (Exception, SystemExit):
        return None
    outcome = marker.get('outcome')
    if not isinstance(outcome, dict) or started_ns in (marker.get('covers') or []):
        return None
    requested = marker.get('requested_ns')
    return {**outcome, 'requested': time.strftime('%Y-%m-%d %H:%M', time.localtime(requested / 1e9)) if requested else None}


def summarize_update(result):
    """A few chat lines for an update receipt; the full JSON stays one argument away."""
    status = result.get('status', 'unknown')
    profiles = result.get('profiles') or []
    sources = (result.get('sources') or {}).values()
    after = sorted({s.get('after', '')[:7] for s in sources})
    before = sorted({s.get('before', '')[:7] for s in sources} - set(after))
    lines = [f'Toolset update: {status}, {len(profiles)} profile(s)'
             + (f"; at {', '.join(after)}" if after else '')
             + (f" (from {', '.join(before)})" if before else '')]
    for key in ('error', 'action', 'gateway_restart_action', 'request_note'):
        if result.get(key):
            lines.append(f'{key.replace("_", " ").capitalize()}: {result[key]}')
    if 'skill_files' in result:
        edits = {}
        for edit in result.get('local_edits') or []:
            edits[edit.get('action', 'edited')] = edits.get(edit.get('action', 'edited'), 0) + 1
        lines.append(f"Skill files written: {result['skill_files']}; local edits: "
                     + (', '.join(f'{n} {a}' for a, n in sorted(edits.items())) or 'none'))
        reset = [e['path'] for e in result.get('local_edits') or [] if e.get('action') in ('reset', 'removed')]
        if reset:
            lines.append('Reset to the release or removed with it, the profile had edited them (old copies in '
                         + (result.get('backup') or 'the update backup') + '): '
                         + ', '.join(reset[:6]) + (f' (+{len(reset) - 6} more)' if len(reset) > 6 else ''))
    if result.get('hosts'):
        lines.append('Hosts: ' + '; '.join(
            f"{row['item']} {row['status']}"
            + (f" (exit {row['exit']})" if row.get('exit') else '')
            for row in result['hosts']))
    if result.get('settings_healed'):
        lines.append('Settings healed: ' + ', '.join(result['settings_healed']))
    menus = result.get('chat_menus_healed') or []
    if menus:
        by = {}
        for row in menus:
            by.setdefault(row.get('status', '?'), []).append(row.get('profile', '?'))
        lines.append('Chat menus: ' + '; '.join(f'{s} {", ".join(p)}' for s, p in sorted(by.items())))
    if result.get('gateway_restart'):
        line = f"Gateway restart: {result['gateway_restart']}"
        drain = result.get('gateway_restart_progress')
        covers = (drain.get('covers') if isinstance(drain, dict) else None) or result.get('gateway_restart_covers') or 0
        if covers > 1:
            line += f' (covers {covers} updates)'
        done = result.get('gateway_restart_result')
        if isinstance(done, dict):
            line += f", new gateway PID {done.get('gateway_pid')}"
            lines.append(line)
            line = None
            menus = 'Menus resent: ' + (', '.join(done.get('menus_resent') or []) or 'none')
            if done.get('menus_not_seen'):
                menus += '; not seen: ' + ', '.join(done['menus_not_seen'])
            lines.append(menus)
            lines += [f'Interrupted: {item}' for item in (done.get('interrupted') or [])[:3]]
        elif isinstance(drain, dict) and drain.get('state') == 'deferred':
            turns = drain.get('chat_turns')
            line += (', waiting for no chat turn in flight ('
                     + (f'{turns} at last check' if turns is not None else 'activity not yet read') + ')')
        elif result['gateway_restart'] == 'deferred' and drain:
            line += f': {drain}'
        elif isinstance(drain, dict):
            waiting = drain.get('waiting_on') or []
            line += f", draining ({drain.get('seconds_left', '?')}s left, {len(waiting)} turn(s))"
            lines += [line] + [f'  waiting on {w}' for w in waiting[:3]]
            line = None
        elif drain:
            line += ', done'
        if line:
            lines.append(line)
    last = result.get('last_gateway_restart')
    if isinstance(last, dict):
        done = last.get('gateway_restart_result') or {}
        menus = done.get('menus_resent') or []
        lines.append(f"Last gateway restart (requested {last.get('requested') or '?'}): {last.get('gateway_restart')}"
                     + (f", PID {done['gateway_pid']}, menus resent {len(menus)} of "
                        f"{len(menus) + len(done.get('menus_not_seen') or [])}" if done.get('gateway_pid') else ''))
    lines += linked_lines(result.get('linked_profiles'))
    lines.append('Full receipt: /autowork update status full')
    return lines


def update_status(full=False):
    path = update_home() / 'maintenance/toolset-update/latest.json'
    if not path.is_file():
        return 'No update receipt yet. Run /autowork update; if just started, check status again shortly.'
    try:
        result = json.loads(path.read_text())
        request = path.with_name('request.json')
        if request.is_file():
            requested = json.loads(request.read_text())
            requested_pid = requested.get('pid')
            if requested_pid != result.get('pid') and requested.get('started_ns', 0) > result.get('started_ns', 0):
                if updater_alive(requested_pid):
                    return 'Requested update is starting; use /autowork update status shortly.'
                result['request_note'] = 'The later chat request did not produce a receipt (another updater may have held the lock). Showing the actual latest updater result.'
        if result.get('status') == 'running':
            if not updater_alive(result.get('pid')):
                return 'Update process stopped without a final receipt. Inspect maintenance/toolset-update/run.log and rerun /autowork update.'
        if result.get('gateway_restart') == 'deferred':
            # The waiter rewrites the receipt when it restarts, sees another restart or gives up.
            result['gateway_restart_progress'] = gateway_drain(path.parent) or (
                'the deferred-restart waiter is not running and recorded no outcome; check `hermes gateway status` '
                'and maintenance/toolset-update/run.log, then run `hermes gateway restart` if the gateway still runs '
                'the old release')
        elif result.get('gateway_restart') in ('requested', 'pending'):
            drain = gateway_drain(path.parent)
            finished = None if drain else finish_restart(path.parent.parent.parent, path.parent)
            if finished:
                result.update(finished)
            else:
                result['gateway_restart_progress'] = drain or 'completed or not tracked; the gateway has reloaded unless restart output in run.log shows an error'
        elif (last := last_restart(path.parent, result.get('started_ns'))) is not None:
            result['last_gateway_restart'] = last
        current = linked_profiles()
        if current is not None:
            result['linked_profiles'] = [{k: r[k] for k in ('profile', 'target')} for r in current]
        # Gateway attachment extraction removes bare existing file paths from prose.
        # Keep the receipt literal; escape embedded fences without changing JSON values.
        if full:
            payload = json.dumps(result, indent=2).replace('`', r'\u0060')
            return f'```json\n{payload}\n```'
        summary = '\n'.join(summarize_update(result)).replace('`', "'")
        return f'```text\n{summary}\n```'
    except (OSError, ValueError) as error:
        return f'Cannot read update receipt: {type(error).__name__}; inspect maintenance/toolset-update/run.log.'


def start_update(*, check=False):
    # A symlinked Hermes home is accepted, as by the terminal updater; state below it is not.
    home = update_home().resolve()
    folder = home / 'maintenance/toolset-update'
    if any(p.is_symlink() for p in (folder, folder.parent)):
        return 'Update refused: symlinked update state directory.'
    folder.mkdir(parents=True, exist_ok=True)
    log = folder / 'run.log'
    if log.is_symlink():
        return 'Update refused: symlinked update log.'
    try:
        owner = _updater().running_update(folder)
    except (Exception, SystemExit):  # an unreadable lock or updater never blocks starting; the updater checks again
        owner = None
    if owner:
        return (f"Another Autowork {owner.get('mode') or 'update'} is running (PID {owner.get('pid') or '?'}"
                + (f", started {owner['started']}" if owner.get('started') else '')
                + '). Nothing was started; use /autowork update status, then rerun once it finishes.')
    argv = [sys.executable, str(ROOT / 'update_bundle.py'), '--hermes-home', str(home)]
    if check:
        argv.append('--check')
    try:
        started_ns = time.time_ns()
        with log.open('ab') as stream:
            process = subprocess.Popen(argv, stdin=subprocess.DEVNULL, stdout=stream, stderr=stream,
                             start_new_session=True, cwd=ROOT)
        request = folder / 'request.json'
        if request.is_symlink():
            return 'Update started; request marker is unsafe. Inspect the updater receipt directly.'
        request.write_text(json.dumps({'pid': process.pid, 'started_ns': started_ns}) + '\n')
    except OSError as error:
        return f'Update could not start: {type(error).__name__}.'
    return ('Upstream check' if check else 'All-profile update') + ' requested. Use /autowork update status for the result. Edited bundle skills are reset to the release (old copies in the backup); workers and schedules are not restarted.'


def handle_chat(raw_args=''):
    words = raw_args.strip().split()
    if words and words[0].lower() == 'update':
        if len(words) == 1:
            return start_update(check=False)
        if words[1:] == ['--check']:
            return start_update(check=True)
        if words[1:] == ['status']:
            return update_status()
        if words[1:] == ['status', 'full']:
            return update_status(full=True)
        return 'Usage: /autowork update [--check|status [full]] — updates all existing profiles; no force option.'
    return list_commands(raw_args)


def maintenance_reply(raw_args=''):
    """Reply to `/autowork update|status|list`, or None: other arguments run the Autowork skill.

    Only these exact forms are maintenance, so instructions such as
    `/autowork update the README` still reach the skill.
    """
    words = raw_args.strip().lower().split()
    if words[:1] == ['update'] and words[1:] in ([], ['--check'], ['status'], ['status', 'full']):
        return handle_chat(raw_args)
    if words == ['status']:
        return list_commands('')
    if words[:1] == ['list'] and len(words) <= 2:
        return list_commands(' '.join(words))
    return None


def setup_parser(parser):
    actions = parser.add_subparsers(dest='action', required=True)
    update = actions.add_parser('update', help='Update this bundle and native skills across all existing profiles')
    update.add_argument('--check', action='store_true', help='Fetch/check only; no checkout/profile updates')
    update.add_argument('--hermes-home', help='Hermes root containing profiles/')
    setup = actions.add_parser('setup', help='Install, enable, and configure sources in plugins/PLUGINS.md')
    setup.add_argument('--dry-run', action='store_true')
    setup.add_argument('--hermes-home', help='Hermes root containing profiles/')
    setup.add_argument('--yes-deps', action='store_true', help='Consent to declared Python dependencies')
    setup.add_argument('--bundle-only', action='store_true')
    setup.add_argument('--no-reload', action='store_true')
    finalize = actions.add_parser('finalize', help='Verify this profile and refresh gateway command wiring')
    finalize.add_argument('--hermes-home', required=True)
    finalize.add_argument('--bundle-only', action='store_true')
    finalize.add_argument('--no-reload', action='store_true')
    pin = actions.add_parser('pin', help="Replace a profile's plugin link with a clone of the same revision")
    # Positional: Hermes consumes a global --profile/-p before the subcommand sees it.
    pin.add_argument('profile', metavar='PROFILE')
    pin.add_argument('--dry-run', action='store_true', help='Report what would change; write nothing')
    pin.add_argument('--unpin', action='store_true', help='Restore the link saved by the last pin')
    pin.add_argument('--hermes-home', help='Hermes root containing profiles/')
    doctor = actions.add_parser('doctor', help='Report enabled plugins and available commands')
    doctor.add_argument('--json', action='store_true')
    doctor.add_argument('--core', '--bundle-only', dest='core_only', action='store_true',
                        help='Check bundled skills/commands; report external gaps without failing on them')


def diagnose(report, *, core_only=False):
    """Evaluate one inventory snapshot without invoking setup or reloading gateways."""
    errors = []
    own = next((p for p in report['plugins'] if p['name'] == 'autowork'), {})
    if not own.get('enabled') or own.get('error'):
        errors.append('autowork is not loaded cleanly')
    names = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')
             if p.parent.name not in {'repo-docs', 'repo-interview'}}
    commands = {r['command'] for r in report['commands']
                if r.get('kind') == 'plugin' and r.get('source') == 'autowork'}
    missing_commands = sorted(n.replace('_', '-') for n in names
                              if n.replace('_', '-') not in commands)
    public_names = set()
    for name in names:
        if name == 'grill-me' and 'plan-with-me' in names:
            continue  # Challenge mode is exposed through Plan With Me.
        text = (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
        match = re.search(r'^name: ([a-z0-9_-]+)$', text, re.MULTILINE)
        public_names.add(match.group(1) if match else name)
    missing_skills = sorted('autowork:' + n for n in public_names
                            if 'autowork:' + n not in report['plugin_skills'])
    if not names:
        errors.append('No bundled skills found')
    if missing_commands:
        errors.append('Unavailable bundled commands: ' + ', '.join(missing_commands))
    if missing_skills:
        errors.append('Unavailable bundled skills: ' + ', '.join(missing_skills))
    gaps = {field: [name for name in report[field] if name != 'autowork']
            for field in ('missing_plugins', 'missing_skills', 'unchecked_skill_sources')}
    integrations_ready = not any(gaps.values())
    ready = not errors and (core_only or integrations_ready)
    return {**report, 'scope': 'core' if core_only else 'full',
            'status': 'ready' if ready else 'incomplete',
            'core_status': 'incomplete' if errors else 'ready', 'core_errors': errors,
            'integrations_status': 'ready' if integrations_ready else 'unavailable',
            'integration_gaps': gaps,
            'readiness_note': 'Skill and command registration only. Model execution, workflow-specific '
                              'tools and live Telegram delivery are not tested.'}


def format_diagnosis(report):
    lines = [f"Autowork — {report['scope']} check: {report['status']}",
             f"Core: {report['core_status']} (bundled skill and command registration)",
             f"Integrations: {report['integrations_status']}"]
    lines.extend('  ' + error for error in report['core_errors'])
    for field, names in report['integration_gaps'].items():
        if names:
            lines.append('  ' + field.replace('_', ' ') + ': ' + ', '.join(names))
    if report['scope'] == 'core' and report['integrations_status'] != 'ready':
        lines.append('External gaps do not fail this core check; workflows using them may be unavailable.')
    lines += linked_lines(report.get('linked_profiles'))
    lines.append(report['readiness_note'])
    return '\n'.join(lines)


def handle_cli(args):
    if args.action == 'update':
        argv = [sys.executable, str(ROOT / 'update_bundle.py'), '--hermes-home',
                str(args.hermes_home or update_home())]
        if args.check:
            argv.append('--check')
        return subprocess.run(argv, cwd=ROOT, check=False).returncode
    if args.action == 'pin':
        argv = [sys.executable, str(ROOT / 'update_bundle.py'), '--hermes-home',
                str(args.hermes_home or update_home()), '--unpin-profile' if args.unpin else '--pin-profile', args.profile]
        if args.dry_run:
            argv.append('--dry-run')
        return subprocess.run(argv, cwd=ROOT, check=False).returncode
    if args.action == 'doctor':
        report = inventory()
        linked = linked_profiles()
        if linked is not None:
            report = {**report, 'linked_profiles': linked}
        report = diagnose(report, core_only=getattr(args, 'core_only', False))
        print(json.dumps(report, indent=2) if args.json else format_diagnosis(report))
        return int(report['status'] != 'ready')
    if args.action == 'finalize':
        from .setup_runtime import finalize
        report = inventory()
        result, code = finalize(ROOT, report, args)
        print(json.dumps(result, indent=2))
        return code
    argv = ['python3', str(ROOT / 'setup_bundle.py')]
    for flag in ('dry_run', 'yes_deps', 'bundle_only', 'no_reload'):
        if getattr(args, flag, False): argv.append('--' + flag.replace('_', '-'))
    if args.hermes_home: argv += ['--hermes-home', args.hermes_home]
    return subprocess.run(argv, cwd=ROOT, check=False).returncode


def register_bundle(ctx, invoke):
    register_imported_skills(ctx, invoke)
    # Chat maintenance is `/autowork update|status|list`, dispatched by maintenance_reply.
    ctx.register_cli_command('autowork', help='Install, update and diagnose the Autowork bundle',
                             setup_fn=setup_parser, handler_fn=handle_cli)
