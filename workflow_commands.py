"""Human-facing workflow names backed by stable skill IDs and legacy commands."""
from functools import partial
import logging

WORKFLOWS = (
    ('plan_with_me', 'repo-interview', None, 'Ask me questions and save our plan'),
    ('plan_for_me', 'autoresearch', 'plan', 'Investigate, choose an approach and save the plan'),
    ('docs_sync', 'repo-docs', None, 'Keep repository documentation and tasks accurate'),
)


def dispatch(invoke, ctx, skill, path, subcommand, raw_args):
    if subcommand:
        raw_args = f'Selected subcommand: {subcommand}\n\n{raw_args}'
    return invoke(ctx, skill, path, raw_args)


def register(ctx, skills, invoke):
    from hermes_cli.commands import resolve_command
    from hermes_cli.plugins import get_plugin_commands

    paths = {name: path for name, _, path in skills}
    occupied = set(get_plugin_commands()) | {command for _, command, _ in skills}
    for public, skill, subcommand, description in WORKFLOWS:
        if skill not in paths:
            continue
        # Telegram resolves underscores as hyphens. Reserve both spellings
        # together so an existing owner cannot be shadowed on either surface.
        names = (public.replace('_', '-'), public)
        if any(name in occupied or resolve_command(name) is not None for name in names):
            logging.getLogger(__name__).warning('Skipping /%s: command already exists.', public)
            continue
        handler = partial(dispatch, invoke, ctx, skill, paths[skill], subcommand)
        for name in names:
            ctx.register_command(name, handler, description=description, args_hint='[instructions]')
            occupied.add(name)
