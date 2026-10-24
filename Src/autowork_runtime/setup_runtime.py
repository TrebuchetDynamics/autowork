"""Native profile readback and gateway activation, invoked after explicit setup."""
from pathlib import Path


def finish_profile(bundle, home, root, inventory, *, bundle_only=False, no_reload=False, verify_settings=None):
    errors = []
    bundled = {p.parent.name for p in (bundle / 'skills').glob('*/SKILL.md')
               if p.parent.name not in {'repo-docs', 'repo-interview'}}
    commands = {r['command'] for r in inventory['commands']
                if r.get('kind') == 'plugin' and r.get('source') == 'autowork'}
    missing = sorted(bundled - commands)
    if missing: errors.append('Unavailable bundled commands: ' + ', '.join(missing))
    own = next((p for p in inventory['plugins'] if p['name'] == 'autowork'), {})
    if not own.get('enabled') or own.get('error'):
        errors.append('autowork is not loaded cleanly in this profile')
    if not bundle_only:
        for field in ('missing_plugins', 'missing_skills', 'unchecked_skill_sources'):
            if inventory[field]: errors.append(field + ': ' + ', '.join(inventory[field]))
    # Plugin load re-applies the bundle's profile settings; confirm they actually landed.
    drift = verify_settings() if verify_settings else []
    if drift:
        errors.append('Profile settings not healed: ' + ', '.join(drift))
    result = {'home': str(home), 'bundled_commands': sorted(bundled - set(missing)),
              'settings': 'drift' if drift else 'current',
              'gateway': 'not_checked', 'errors': errors,
              'note': 'Command registration is verified, not a Telegram message or model invocation. '
                      'Existing sessions may retain their previous tools, prompts and memory provider.'}
    if no_reload:
        result['gateway'] = 'deferred_by_request'
    else:
        from gateway.control_socket import query_gateway_control, reload_gateway_plugins
        from gateway.status import get_running_pid
        # Prefer a dedicated profile gateway; otherwise use the shared root gateway.
        hosts = list(dict.fromkeys((home, root)))
        host = next((h for h in hosts if query_gateway_control(h, 'status', timeout=3)), None)
        if host is None:
            if any(get_running_pid(h / 'gateway.pid', cleanup_stale=False) for h in hosts):
                result['gateway'] = 'unreachable'
                errors.append('A gateway is running but its control endpoint is unavailable; wiring unverified')
            else:
                result['gateway'] = 'not_running'
        else:
            receipt = reload_gateway_plugins(host, profile_home=home, timeout=30) or {}
            result['gateway_host'] = str(host)
            valid = (receipt.get('reloaded') is True and
                     Path(receipt.get('home') or '').resolve() == home.resolve())
            active = set()
            for activation in receipt.get('activations', []):
                active.update((activation.get('name'), command) for command in
                              activation.get('activated_now', {}).get('gateway_commands', []))
            expected = {(r['source'], r['command']) for r in inventory['commands'] if r.get('kind') == 'plugin'
                        and (not bundle_only or r['source'] == 'autowork')}
            absent = sorted(owner + ':' + command for owner, command in expected - active)
            if not valid or absent or receipt.get('adapters_rewired') is None:
                result['gateway'] = 'reload_incomplete'
                errors.append('Gateway command wiring unverified: ' +
                              (', '.join(absent) or receipt.get('error') or 'invalid activation receipt'))
            else:
                result['gateway'] = 'commands_reloaded'
                result['verified_gateway_commands'] = sorted(owner + ':' + command for owner, command in expected)
                result['adapters_rewired'] = receipt['adapters_rewired']
    result['status'] = 'incomplete' if errors else 'ready'
    return result, int(bool(errors))


def finalize(bundle, report, args):
    from hermes_cli.plugins import get_plugin_manager
    home = Path(get_plugin_manager().home_path).resolve()
    root = Path(args.hermes_home).expanduser().resolve()
    if home != root and home.parent != root / 'profiles':
        return {'status': 'incomplete', 'errors': ['Profile does not belong to requested Hermes root']}, 1
    try:
        verify_runtime_defaults = _AUTOWORK_COMPAT.peer(globals(), 'runtime_defaults').verify_runtime_defaults
        return finish_profile(bundle, home, root, report, bundle_only=args.bundle_only,
                              no_reload=args.no_reload, verify_settings=verify_runtime_defaults)
    except (OSError, ValueError, TypeError, ImportError) as exc:
        return {'status': 'incomplete', 'home': str(home), 'errors': [str(exc)]}, 1
