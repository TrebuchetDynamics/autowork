"""Advertise current workflow commands using Hermes' supported menu configuration."""

WORKFLOWS = ['plan_with_me', 'plan_for_me', 'docs_sync', 'autowork', 'cron_autowork']
# Names this bundle once promoted or registered; compatibility spellings stay
# typeable but are no longer advertised, so earlier priority entries are removed.
RETIRED = {'autoresearch', 'autogoal', 'grill_me', 'repo_interview', 'repo_docs'}


def _bundle_owned(name):
    key = name.strip().lower().lstrip('/').replace('-', '_').replace(':', '_')
    return key in RETIRED or key.startswith('autoresearch_')


def menu_patch(raw):
    menu = raw
    for key in ('platforms', 'telegram', 'extra', 'command_menu'):
        menu = menu.get(key, {}) if isinstance(menu, dict) else {}
    priority = menu.get('priority', []) if isinstance(menu, dict) else []
    if isinstance(priority, str): priority = [priority]
    if not isinstance(priority, list): priority = []
    kept = [str(p) for p in priority if str(p).strip() and not _bundle_owned(str(p))]
    merged = list(dict.fromkeys(kept + WORKFLOWS))
    # Preserve the user's cap, prepend/append/replace preference and their own entries.
    return {'platforms': {'telegram': {'extra': {'command_menu': {'priority': merged}}}}}
