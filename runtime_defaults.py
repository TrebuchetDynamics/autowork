"""Apply bundle policy and command visibility in Hermes' bound profile."""


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
    entry = (((raw.get('plugins') or {}).get('entries') or {}).get('hermes-toolset') or {}) if isinstance(raw, dict) else {}
    return isinstance(entry, dict) and entry.get('apply_runtime_defaults', True) is False


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
