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
    wanted = set(defaults()['imported_plugins']) | {'hermes-toolset'}
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
            'note': 'Menu capacity is limited; typed commands and /toolset list remain available.'}


def list_commands(raw_args=''):
    report = inventory()
    request = raw_args.strip().lower()
    query = request[5:].strip() if request.startswith('list ') else ('' if request == 'list' else request)
    rows = [r for r in report['commands'] if not query or query in r['command'] or query in r['source']]
    if request:
        lines = [f'Toolset commands: {len(rows)} matches']
        for row in rows:
            alias = f" (Telegram: /{row['telegram']})" if row['telegram'] != row['command'] else ''
            lines.append(f"/{row['command']}{alias} — {row['source']}")
    else:
        lines = ['Hermes toolset bundle']
        for plugin in report['plugins']:
            name = plugin['name']
            version = f" {plugin['version']}" if plugin.get('version') else ''
            status = 'error' if plugin.get('error') else ('loaded' if plugin.get('enabled') else 'disabled')
            skills = sum(n.startswith(name + ':') for n in report['plugin_skills'])
            lines.append(f"{name}{version}: {status} — {plugin.get('tools', 0)} tools, "
                         f"{plugin.get('commands', 0)} commands, {skills} skills, {plugin.get('hooks', 0)} hooks")
            if plugin.get('memory_provider'):
                lines.append('  Memory capabilities load through memory.provider; server connectivity is not checked here.')
        lines += [f"{len(report['commands'])} available commands across plugins and local/external skills.",
                  'Per-plugin skill counts cover registered plugin skills; OMH workflow skills are loaded separately.',
                  'Counts show registered capabilities, not tools enabled in your current chat.',
                  '/toolsets lists tool groups; plugins can provide skills, commands and hooks without a tool group.']
    if report['missing_plugins']:
        lines.append('Missing/disabled plugins: ' + ', '.join(report['missing_plugins']))
    lines.extend(f"{p['name']}: {p['error']}" for p in report['plugins'] if p.get('error'))
    if report['missing_skills']:
        lines.append('Unavailable skill commands (missing, blocked, or ambiguous): ' + ', '.join(report['missing_skills']))
    if report['unchecked_skill_sources']:
        lines.append('Skill repositories not yet set up: ' + ', '.join(report['unchecked_skill_sources']))
    if report['telegram_menu_hidden']:
        lines.append('Telegram menu capacity hides some entries; type their commands directly.')
    lines.append('Commands: /toolset list · Update all profiles: /toolset update · Filter: /toolset ponytail')
    lines.append('Diagnostics: hermes toolset doctor --json · Setup: hermes toolset setup')
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


def gateway_drain(folder):
    """Restart progress from the updater module, loaded by path like its subprocess."""
    import importlib.util
    spec = importlib.util.spec_from_file_location('hermes_toolset_update_bundle', ROOT / 'update_bundle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.gateway_drain(folder)


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
    for key in ('error', 'action', 'request_note'):
        if result.get(key):
            lines.append(f'{key.replace("_", " ").capitalize()}: {result[key]}')
    if 'skill_files' in result:
        edits = {}
        for edit in result.get('local_edits') or []:
            edits[edit.get('action', 'edited')] = edits.get(edit.get('action', 'edited'), 0) + 1
        lines.append(f"Skill files written: {result['skill_files']}; local edits: "
                     + (', '.join(f'{n} {a}' for a, n in sorted(edits.items())) or 'none'))
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
        if isinstance(drain, dict):
            waiting = drain.get('waiting_on') or []
            line += f", draining ({drain.get('seconds_left', '?')}s left, {len(waiting)} turn(s))"
            lines += [line] + [f'  waiting on {w}' for w in waiting[:3]]
            line = None
        elif drain:
            line += ', done'
        if line:
            lines.append(line)
    lines.append('Full receipt: /toolset update status full')
    return lines


def update_status(full=False):
    path = update_home() / 'maintenance/toolset-update/latest.json'
    if not path.is_file():
        return 'No update receipt yet. Run /toolset update; if just started, check status again shortly.'
    try:
        result = json.loads(path.read_text())
        request = path.with_name('request.json')
        if request.is_file():
            requested = json.loads(request.read_text())
            requested_pid = requested.get('pid')
            if requested_pid != result.get('pid') and requested.get('started_ns', 0) > result.get('started_ns', 0):
                if updater_alive(requested_pid):
                    return 'Requested update is starting; use /toolset update status shortly.'
                result['request_note'] = 'The later chat request did not produce a receipt (another updater may have held the lock). Showing the actual latest updater result.'
        if result.get('status') == 'running':
            if not updater_alive(result.get('pid')):
                return 'Update process stopped without a final receipt. Inspect maintenance/toolset-update/run.log and rerun /toolset update.'
        if result.get('gateway_restart') in ('requested', 'pending'):
            drain = gateway_drain(path.parent)
            result['gateway_restart_progress'] = drain or 'completed or not tracked; the gateway has reloaded unless restart output in run.log shows an error'
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
    return ('Upstream check' if check else 'All-profile update') + ' requested. Use /toolset update status for the result. Local conflicts are preserved; workers and schedules are not restarted.'


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
        return 'Usage: /toolset update [--check|status [full]] — updates all existing profiles; no force option.'
    return list_commands(raw_args)


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
    doctor = actions.add_parser('doctor', help='Report enabled plugins and available commands')
    doctor.add_argument('--json', action='store_true')
    doctor.add_argument('--core', '--bundle-only', dest='core_only', action='store_true',
                        help='Check bundled skills/commands; report external gaps without failing on them')


def diagnose(report, *, core_only=False):
    """Evaluate one inventory snapshot without invoking setup or reloading gateways."""
    errors = []
    own = next((p for p in report['plugins'] if p['name'] == 'hermes-toolset'), {})
    if not own.get('enabled') or own.get('error'):
        errors.append('hermes-toolset is not loaded cleanly')
    names = {p.parent.name for p in (ROOT / 'skills').glob('*/SKILL.md')
             if p.parent.name not in {'repo-docs', 'repo-interview'}}
    commands = {r['command'] for r in report['commands']
                if r.get('kind') == 'plugin' and r.get('source') == 'hermes-toolset'}
    missing_commands = sorted(n.replace('_', '-') for n in names
                              if n.replace('_', '-') not in commands)
    public_names = set()
    for name in names:
        if name == 'grill-me' and 'plan-with-me' in names:
            continue  # Challenge mode is exposed through Plan With Me.
        text = (ROOT / 'skills' / name / 'SKILL.md').read_text(encoding='utf-8')
        match = re.search(r'^name: ([a-z0-9_-]+)$', text, re.MULTILINE)
        public_names.add(match.group(1) if match else name)
    missing_skills = sorted('hermes-toolset:' + n for n in public_names
                            if 'hermes-toolset:' + n not in report['plugin_skills'])
    if not names:
        errors.append('No bundled skills found')
    if missing_commands:
        errors.append('Unavailable bundled commands: ' + ', '.join(missing_commands))
    if missing_skills:
        errors.append('Unavailable bundled skills: ' + ', '.join(missing_skills))
    gaps = {field: [name for name in report[field] if name != 'hermes-toolset']
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
    lines = [f"Hermes Toolset — {report['scope']} check: {report['status']}",
             f"Core: {report['core_status']} (bundled skill and command registration)",
             f"Integrations: {report['integrations_status']}"]
    lines.extend('  ' + error for error in report['core_errors'])
    for field, names in report['integration_gaps'].items():
        if names:
            lines.append('  ' + field.replace('_', ' ') + ': ' + ', '.join(names))
    if report['scope'] == 'core' and report['integrations_status'] != 'ready':
        lines.append('External gaps do not fail this core check; workflows using them may be unavailable.')
    lines.append(report['readiness_note'])
    return '\n'.join(lines)


def handle_cli(args):
    if args.action == 'update':
        argv = [sys.executable, str(ROOT / 'update_bundle.py'), '--hermes-home',
                str(args.hermes_home or update_home())]
        if args.check:
            argv.append('--check')
        return subprocess.run(argv, cwd=ROOT, check=False).returncode
    if args.action == 'doctor':
        report = diagnose(inventory(), core_only=getattr(args, 'core_only', False))
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
    ctx.register_command('toolset', handle_chat, description='Bundle status, commands, and all-profile upstream update',
                         args_hint='[list|update|filter]')
    ctx.register_cli_command('toolset', help='Install and diagnose the Hermes toolset bundle',
                             setup_fn=setup_parser, handler_fn=handle_cli)
