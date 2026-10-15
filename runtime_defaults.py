"""Apply bundle policy and command visibility in Hermes' bound profile."""
from pathlib import Path


def expected_settings(raw):
    """Bundle policy for one profile's raw config: approvals, injection and menu."""
    from .bundle import defaults
    from .telegram_menu_policy import menu_patch

    wanted = defaults()['hermes']
    patch = {
        'approvals': {
            'mode': wanted['approvals_mode'],
            'destructive_slash_confirm': wanted['destructive_slash_confirm'],
            'mcp_reload_confirm': wanted['mcp_reload_confirm'],
        },
        'plugins': {'entries': {'hermes-toolset': {
            'allow_gateway_injection': wanted['allow_gateway_injection'],
        }}},
    }
    patch.update(menu_patch(raw))
    return patch


def settings_drift(raw, expected, prefix=()):
    """Dotted paths whose current value differs from the expected leaf value."""
    drift = []
    for key, value in expected.items():
        path = prefix + (key,)
        actual = raw.get(key) if isinstance(raw, dict) else None
        if isinstance(value, dict):
            drift += settings_drift(actual, value, path)
        elif type(actual) is not type(value) or actual != value:
            drift.append('.'.join(path))
    return drift


def _leaf_paths(expected, prefix=()):
    for key, value in expected.items():
        if isinstance(value, dict):
            yield from _leaf_paths(value, prefix + (key,))
        else:
            yield prefix + (key,)


def _opted_out(raw):
    """Mirror Hermes' ctx.get_config: `settings.<key>`, then the legacy `config.<key>`."""
    entry = (((raw.get('plugins') or {}).get('entries') or {}).get('hermes-toolset') or {}) if isinstance(raw, dict) else {}
    if not isinstance(entry, dict):
        return False
    for subtree in ('settings', 'config'):
        values = entry.get(subtree)
        if isinstance(values, dict) and 'apply_runtime_defaults' in values:
            return values['apply_runtime_defaults'] is False
    return False


def setup_opted_out(config_path):
    """Setup-time `_opted_out` for one profile config: True, False or None (unknown).

    Parses with PyYAML, the loader Hermes reads config with. A missing,
    unreadable or malformed config is not an opt-out: setup proceeds and
    Hermes refuses the write as before. Without PyYAML, a config that never
    names the setting cannot opt out; one that does is unknown, never applied.
    """
    try:
        text = Path(config_path).read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return False
    try:
        import yaml
    except ImportError:
        return None if 'apply_runtime_defaults' in text else False
    try:
        raw = yaml.safe_load(text)
    except yaml.YAMLError:
        return False
    return _opted_out(raw)


def apply_runtime_defaults(ctx):
    # This opt-out must be set before restoring prompts; otherwise the next load
    # deliberately reapplies the bundle policy.
    if ctx.get_config('apply_runtime_defaults', True) is False:
        return

    from hermes_cli.config import require_readable_config_before_write, save_config

    # Read raw YAML, refusing malformed settings rather than overwriting them
    # with fallback defaults. The native loader binds the owning profile even
    # when a shared gateway loads several profiles in the same process.
    raw = require_readable_config_before_write()
    patch = expected_settings(raw)
    if settings_drift(raw, patch):
        # Merge under Hermes' config lock, preserving unrelated settings and
        # deny rules. Keep false values explicit even if upstream defaults change.
        save_config(patch, merge_existing=True, preserve_keys=set(_leaf_paths(patch)))


def verify_runtime_defaults():
    """Re-read the bound profile after load; [] when settings match or the user opted out."""
    from hermes_cli.config import read_raw_config
    raw = read_raw_config() or {}
    return [] if _opted_out(raw) else settings_drift(raw, expected_settings(raw))


CRON_SCRIPTS = ('cron-autowork/scripts/autowork-start-notice.py',)
MANAGED = b'# hermes-toolset: '


def provision_cron_scripts(skills_dir, home):
    """Copy bundle cron scripts into HERMES_HOME/scripts, where Hermes requires them.

    Hermes refuses cron scripts that resolve outside the profile's scripts folder,
    so a symlink to the bundle cannot work. A same-named file without the bundle
    marker belongs to the user and is left alone. Returns the names it could not
    provision.
    """
    target_dir = Path(home) / 'scripts'
    if target_dir.is_symlink():
        return [Path(rel).name for rel in CRON_SCRIPTS]
    skipped = []
    for rel in CRON_SCRIPTS:
        source = Path(skills_dir) / rel
        target = target_dir / source.name
        if not source.is_file():
            continue
        data = source.read_bytes()
        if target.is_symlink() or (target.exists() and MANAGED not in target.read_bytes()[:200]):
            skipped.append(source.name)
            continue
        if target.exists() and target.read_bytes() == data:
            continue
        target_dir.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name(f'.{target.name}.tmp')
        temporary.write_bytes(data)
        temporary.chmod(0o755)
        temporary.replace(target)
    return skipped
