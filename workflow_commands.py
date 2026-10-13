"""Canonical workflow commands and explicit legacy aliases."""
from functools import partial
import logging

WORKFLOWS = (
    ('plan_with_me', 'plan-with-me', None, 'Ask me questions and save our plan'),
    ('plan_for_me', 'autoresearch', 'plan', 'Investigate, choose an approach and save the plan'),
    ('docs_sync', 'docs-sync', None, 'Keep repository documentation and tasks accurate'),
)


def dispatch(invoke, ctx, skill, path, subcommand, raw_args):
    if subcommand:
        raw_args = f'Selected subcommand: {subcommand}\n\n{raw_args}'
    return invoke(ctx, skill, path, raw_args)


def register(ctx, skills, invoke):
    from hermes_cli.commands import resolve_command
    from hermes_cli.plugins import get_plugin_commands

    paths = {name: path for name, _, path in skills}
    occupied = set(get_plugin_commands()) | {command for name, command, _ in skills
                                             if name not in {"docs-sync", "plan-with-me"}}
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

    # Legacy commands route to canonical sources, but are hidden from menus.
    for old, canonical in (("repo-docs", "docs-sync"), ("repo-interview", "plan-with-me")):
        if canonical not in paths:
            continue
        aliases = (old, old.replace('-', '_'))
        if any(alias in occupied or resolve_command(alias) is not None for alias in aliases):
            continue
        for alias in aliases:
            ctx.register_command(alias, partial(dispatch, invoke, ctx, canonical, paths[canonical], None),
                                 description=f"Compatibility alias for {canonical}", args_hint='<instructions>')
            occupied.add(alias)
