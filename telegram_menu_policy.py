"""Reserve Autoresearch picker entries using Hermes' supported menu configuration."""
import json
from pathlib import Path


def menu_patch(raw):
    menu = raw
    for key in ('platforms', 'telegram', 'extra', 'command_menu'):
        menu = menu.get(key, {}) if isinstance(menu, dict) else {}
    priority = menu.get('priority', []) if isinstance(menu, dict) else []
    if isinstance(priority, str): priority = [priority]
    if not isinstance(priority, list): priority = []
    names = json.loads((Path(__file__).parent / 'skills/autoresearch/UPSTREAM.json').read_text())['commands']
    wanted = ['autowork', 'autoresearch'] + ['autoresearch_' + name for name in names]
    merged = list(dict.fromkeys([str(p) for p in priority if str(p).strip()] + wanted))
    # Preserve the user's cap and prepend/append/replace preference. Their explicit
    # higher-priority entries may still fill an intentionally small menu.
    return {'platforms': {'telegram': {'extra': {'command_menu': {'priority': merged}}}}}
