"""Advertise current workflow commands using Hermes' supported menu configuration."""
import re

# Hermes' 60-entry default menu is already full of built-ins, so only these are advertised;
# each one displaces the lowest-ranked built-in, which stays typeable.
WORKFLOWS = ['plan_with_me', 'blockers', 'plan_for_me', 'docs_sync', 'autowork',
             'ui_taste', 'beautify_github_readme', 'impeccable', 'lgtm',
             'engineering', 'git_commit_push']
# Names this bundle once promoted or registered; compatibility spellings stay
# typeable but are no longer advertised, so earlier priority entries are removed.
RETIRED = {'autoresearch', 'autogoal', 'grill_me', 'repo_interview', 'repo_docs', 'git_pull_merge',
           'cron_autowork'}


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


def chat_ids(env):
    """Owner chats whose chat-scoped menu would outrank the lists Hermes refreshes."""
    ids = []
    for key in ('TELEGRAM_ALLOWED_USERS', 'TELEGRAM_HOME_CHANNEL'):
        for value in str(env.get(key, '')).split(','):
            value = value.strip()
            if re.fullmatch(r'-?[0-9]+', value) and int(value) not in ids:
                ids.append(int(value))
    return ids


def stale_chat_menus(env, call, failed=None):
    """Clear chat-scoped menus that still advertise retired bundle commands.

    Telegram prefers a chat's own command list over the default/private/group
    lists Hermes re-pushes on reconnect, so a leftover list never refreshes.
    Lists without retired names may be deliberate and are left alone. Each chat
    is handled independently: a chat whose Bot API call fails is recorded in
    `failed` as `(chat, error type name)` and the remaining chats are still checked.
    """
    cleared = []
    for chat in chat_ids(env):
        scope = {'type': 'chat', 'chat_id': chat}
        try:
            names = [c.get('command', '') for c in call('getMyCommands', scope=scope)]
            if any(_bundle_owned(n) for n in names) and call('deleteMyCommands', scope=scope):
                cleared.append(chat)
        except (OSError, ValueError) as error:
            if failed is not None:
                failed.append((chat, type(error).__name__))
    return cleared
