"""Apply bundle policy and command visibility in Hermes' bound profile."""
import json
from pathlib import Path
import re

OMH_PACKAGE = 'oh-my-hermes'
PLUGIN = 'autowork'
BUNDLE_SKILLS = Path(__file__).resolve().parent / 'skills'


def _frontmatter_name(path):
    try:
        text = path.read_text(encoding='utf-8')
    except (OSError, UnicodeError):
        return None
    parts = text.split('---', 2)
    if len(parts) < 3 or parts[0].strip():
        return None
    match = re.search(r'^name:\s*["\']?([^"\'\n]+?)["\']?\s*$', parts[1], re.M)
    return match[1] if match else None


def omh_skills(raw):
    """Registered name -> OMH catalog name for skills in the profile's OMH skill folders.

    OMH registers its managed skills folder in `skills.external_dirs`; the folder's
    parent holds OMH's manifest. Registered names come from each SKILL.md, since
    they do not always equal the catalog name (`context` registers as `ulw-context`).
    """
    skills_config = raw.get('skills') if isinstance(raw, dict) else None
    folders = skills_config.get('external_dirs') if isinstance(skills_config, dict) else None
    found = {}
    for entry in folders if isinstance(folders, list) else []:
        folder = Path(str(entry)).expanduser()
        try:
            manifest = json.loads((folder.parent / 'manifest.json').read_text(encoding='utf-8'))
            root = folder.resolve()
        except (OSError, ValueError, RuntimeError):
            continue
        if not isinstance(manifest, dict) or manifest.get('package') != OMH_PACKAGE:
            continue
        for skill in manifest.get('skills') or []:
            if not isinstance(skill, dict) or not isinstance(skill.get('name'), str) or not isinstance(skill.get('path'), str):
                continue
            path = (folder / skill['path']).resolve()
            if root not in path.parents:
                continue
            name = _frontmatter_name(path)
            if name:
                found[name] = skill['name']
    return found


def skills_patch(raw, keep, previous):
    """`skills.disabled` keeping the user's entries, plus OMH skills outside the keep list.

    Only names this bundle added before (`previous`) are ever removed, and bundled
    toolset skills are never left disabled. Without a keep list nothing is trimmed.
    """
    skills_config = raw.get('skills') if isinstance(raw, dict) else None
    current = skills_config.get('disabled') if isinstance(skills_config, dict) else None
    current = [n for n in current if isinstance(n, str)] if isinstance(current, list) else []
    trim = sorted(name for name, catalog in omh_skills(raw).items()
                  if keep is not None and catalog not in keep and name not in keep)
    bundled = {p.parent.name for p in BUNDLE_SKILLS.glob('*/SKILL.md')}
    disabled = sorted((set(current) - set(previous) - bundled) | set(trim))
    return disabled, trim


def plugin_entry(raw):
    """This plugin's `plugins.entries` block."""
    entries = ((raw.get('plugins') or {}).get('entries') or {}) if isinstance(raw, dict) else {}
    entry = entries.get(PLUGIN) if isinstance(entries, dict) else None
    return entry if isinstance(entry, dict) else {}


def expected_settings(raw):
    """Bundle policy for one profile's raw config: approvals, turn budget, injection and menu."""
    defaults = _AUTOWORK_COMPAT.peer(globals(), 'bundle').defaults
    menu_patch = _AUTOWORK_COMPAT.peer(globals(), 'telegram_menu_policy').menu_patch

    settings = defaults()
    wanted = settings['hermes']
    patch = {
        'approvals': {
            'mode': wanted['approvals_mode'],
            'destructive_slash_confirm': wanted['destructive_slash_confirm'],
            'mcp_reload_confirm': wanted['mcp_reload_confirm'],
        },
        # Hermes quick setup writes a 90-iteration cap that cuts Autowork turns short.
        'agent': {'max_turns': wanted['max_turns']},
        'plugins': {'entries': {PLUGIN: {
            'allow_gateway_injection': wanted['allow_gateway_injection'],
        }}},
    }
    patch.update(menu_patch(raw))
    keep = settings.get('omh_keep_skills')
    entry = plugin_entry(raw)
    previous = entry.get('omh_trim') if isinstance(entry.get('omh_trim'), list) else []
    disabled, trim = skills_patch(raw, set(keep) if isinstance(keep, list) else None, previous)
    current = (raw.get('skills') or {}).get('disabled') if isinstance(raw, dict) and isinstance(raw.get('skills'), dict) else None
    # Write only what changes, so profiles without OMH gain no new keys.
    if disabled != (current or []):
        patch['skills'] = {'disabled': disabled}
    if trim or previous:
        patch['plugins']['entries'][PLUGIN]['omh_trim'] = trim
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
    entry = plugin_entry(raw)
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


def opted_out_settings(raw):
    """What an opted-out profile still receives: the bundle's own Telegram menu entries.

    The opt-out keeps a profile's approval, turn, injection and skill settings. Every
    profile had opted out, which also froze the menu, so commands added since (/blockers)
    never reached a Telegram menu."""
    return _AUTOWORK_COMPAT.peer(globals(), 'telegram_menu_policy').menu_patch(raw)


def apply_runtime_defaults(ctx):
    # This opt-out must be set before restoring prompts; otherwise the next load
    # deliberately reapplies the bundle policy.
    opted_out = ctx.get_config('apply_runtime_defaults', True) is False

    # Read raw YAML, refusing malformed settings rather than overwriting them
    # with fallback defaults. The native loader binds the owning profile even
    # when a shared gateway loads several profiles in the same process.
    try:
        from hermes_cli.config import require_readable_config_before_write, save_config
        raw = require_readable_config_before_write()
    except Exception:
        if opted_out:  # an opted-out profile never failed to load over its config
            return
        raise
    patch = opted_out_settings(raw) if opted_out else expected_settings(raw)
    if settings_drift(raw, patch):
        # Merge under Hermes' config lock, preserving unrelated settings and
        # deny rules. Keep false values explicit even if upstream defaults change.
        save_config(patch, merge_existing=True, preserve_keys=set(_leaf_paths(patch)))


def verify_runtime_defaults():
    """Re-read the bound profile after load; [] when its settings match. An opted-out profile
    is checked only for the bundle's menu entries."""
    from hermes_cli.config import read_raw_config
    raw = read_raw_config() or {}
    return settings_drift(raw, opted_out_settings(raw) if _opted_out(raw) else expected_settings(raw))


CRON_SCRIPTS = ('cron-autowork/scripts/autowork-start-notice.py',)
MANAGED = b'# autowork: '


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
