"""Run with Hermes Python/source path; no model, bot or network calls."""
import json
import os
from pathlib import Path
from queue import Queue
import tempfile
from types import SimpleNamespace


def main():
    root = Path(__file__).resolve().parents[1]
    with tempfile.TemporaryDirectory(prefix='autoresearch-native-') as temporary:
        home = Path(temporary)
        os.environ['HERMES_HOME'] = str(home)
        os.environ.pop('HERMES_SAFE_MODE', None)
        (home / 'plugins').mkdir()
        (home / 'plugins/hermes-toolset').symlink_to(root, target_is_directory=True)
        (home / 'config.yaml').write_text('plugins:\n  enabled: [hermes-toolset]\n')
        from hermes_cli.plugins import get_plugin_manager, get_plugin_commands
        from hermes_cli.commands_platforms import telegram_menu_commands, telegram_menu_max_commands
        from gateway.session_context import set_session_vars, clear_session_vars
        from tools.skills_tool import skill_view
        manager = get_plugin_manager()
        manager.discover_and_load()
        loaded = manager._plugins['hermes-toolset']
        assert loaded.enabled and not loaded.error, loaded.error
        commands = get_plugin_commands()
        assert 'hermes-toolset:engineering' in [i['name'] for i in manager.list_plugin_skill_metadata()]
        assert (home / 'skills/engineering/upstream/references/security-checklist.md').is_file()
        assert 'No update receipt yet' in commands['toolset']['handler']('update status')
        names = json.loads((root / 'skills/autoresearch/UPSTREAM.json').read_text())['commands']
        payload = json.loads(skill_view('hermes-toolset:plan-for-me'))
        assert 'error' not in payload, payload
        menu, _ = telegram_menu_commands(telegram_menu_max_commands())
        menu = dict(menu)
        # Fleet menus may exceed Telegram's cap. Sanitized colon names must never
        # appear as unresolvable menu entries, regardless of the selected cap.
        for name in names:
            assert f'autoresearch:{name}' in commands
            assert f'autoresearch-{name}' in commands
            assert f'autoresearch{name}' not in menu
        assert all('autoresearch_' + name in menu for name in names if name != 'plan'), menu
        assert 'plan_for_me' in menu and 'autoresearch' not in menu, menu
        assert 'autowork' in menu, menu
        assert 'autogoal' not in commands and 'autogoal' not in menu
        cli = SimpleNamespace(_pending_input=Queue(), _agent_running=False)
        manager._cli_ref = cli
        tokens = set_session_vars()
        try:
            for alias in ('autowork',):
                assert commands[alias]['handler']('Improve this repo; no push') is None
                assert 'hermes-toolset:autowork' in cli._pending_input.get_nowait()
            for name in names:
                raw = 'Goal: cache latency\n--chain evals; do not implement'
                assert commands[f'autoresearch:{name}']['handler'](raw) is None
                queued = cli._pending_input.get_nowait()
                assert 'hermes-toolset:plan-for-me' in queued
                assert f'Selected subcommand: {name}\n' in queued
                assert queued.endswith(raw)
                assert 'TODO.md is the central work queue' in queued
        finally:
            clear_session_vars(tokens)
            manager._cli_ref = None
        accepted = []
        manager.set_gateway_message_injector(accepted, lambda **kwargs: accepted.append(kwargs) or True)
        tokens = set_session_vars(platform='telegram', chat_id='42', thread_id='8', profile='research')
        try:
            for alias in ('autowork',):
                assert commands[alias]['handler']('Improve this repo; no push') is None
                assert accepted[-1]['origin']['thread_id'] == '8'
            for name in names:
                assert commands[f'autoresearch-{name}']['handler']('plan only') is None
                assert accepted[-1]['origin']['thread_id'] == '8'
                assert accepted[-1]['plugin_home'] == home
        finally:
            clear_session_vars(tokens)
        manager.unload('hermes-toolset')
        assert not any(n.startswith('autoresearch') for n in manager._plugin_commands)
        print('PASS: all 13 colon/Telegram aliases, menu, skill loading, CLI injection, gateway origin and unload')


if __name__ == '__main__':
    main()
