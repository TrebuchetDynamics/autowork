"""Upstream slash commands with gateway-compatible spellings."""
from functools import partial
import logging

COMMANDS = ('plan', 'debug', 'fix', 'security', 'ship', 'probe', 'scenario',
            'predict', 'reason', 'learn', 'improve', 'evals', 'regression')


def _dispatch(invoke, ctx, path, command, raw_args):
    return invoke(ctx, 'autoresearch', path,
                  f'Selected subcommand: {command}\n\n{raw_args}')


def register(ctx, skills, invoke):
    from hermes_cli.commands import resolve_command
    from hermes_cli.plugins import get_plugin_commands

    path = next((path for name, _, path in skills if name == 'autoresearch'), None)
    if path is None:
        return
    existing = get_plugin_commands()
    bundled = {command for _, command, _ in skills}
    for command in COMMANDS:
        for separator in (':', '-'):
            alias = f'autoresearch{separator}{command}'
            if alias in existing or alias in bundled or resolve_command(alias) is not None:
                logging.getLogger(__name__).warning('Skipping /%s: command already exists.', alias)
                continue
            # Compatibility spellings stay typeable but are not advertised: Hermes
            # omits commands that require text from Telegram menus. Empty text still
            # dispatches and runs upstream setup.
            ctx.register_command(alias, partial(_dispatch, invoke, ctx, path, command),
                                 description=f'Autoresearch: {command}', args_hint='<instructions>')
