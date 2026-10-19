"""Discover bundled skills and expose them through Hermes' command API."""

from functools import partial
import logging
from pathlib import Path
import re


SKILLS_DIR = Path(__file__).resolve().parent / "skills"
logger = logging.getLogger(__name__)


_NAME = re.compile(r"[a-z0-9][a-z0-9_-]{0,31}\Z")


def _discover_skills():
    """Validate the complete command set before registering anything."""
    root = SKILLS_DIR.resolve()
    skills = []
    commands = set()
    for folder in sorted(root.iterdir()):
        path = folder / "SKILL.md"
        if folder.name in {"repo-docs", "repo-interview"}:
            continue  # Retired local worker snapshots are never discoverable skills.
        if not folder.is_dir() or not path.is_file():
            continue
        name = folder.name
        if not _NAME.fullmatch(name):
            raise ValueError(f"Invalid skill folder {name!r}: use 1–32 lowercase letters, digits, '-' or '_'.")
        if not path.resolve().is_relative_to(root):
            raise ValueError(f"Skill {name!r} points outside the bundled skills directory.")
        # Hermes maps Telegram underscores back to hyphens at dispatch time.
        command = name.replace("_", "-")
        if command in commands:
            raise ValueError(f"Skills collide on command /{command} after Telegram normalization.")
        commands.add(command)
        skills.append((name, command, path))
    return skills


def _invoke(ctx, name, path, raw_args, namespace="autowork"):
    from gateway.session_context import get_session_env

    if not path.is_file():
        return f"Skill {name!r} no longer exists. Update the plugin and restart Hermes."
    public = name
    if namespace == "autowork" and name == "grill-me" and (SKILLS_DIR / "plan-with-me/SKILL.md").is_file():
        public = "plan-with-me"
        raw_args = "Challenge mode: read ../grill-me/SKILL.md and stress-test the plan.\n\n" + raw_args
    prompt = (
        f"The user invoked the /{name} skill command. "
        f'Load skill_view(name="{namespace}:{public}") and follow its instructions '
        "to perform the requested work in this conversation. "
        "Resolve supporting files relative to that skill's directory.\n\n"
        f"User arguments:\n{raw_args}"
    )
    if namespace == "autowork" and name in {"autoresearch", "plan-for-me"}:
        prompt = (
            "TODO.md is the central work queue. By default, persist actionable "
            "research/planning findings there through docs_sync and synchronize "
            "goals.json; reuse task IDs and preserve user ordering. Explicit "
            "read-only, chat-only, no-write and --dry-run requests write nothing. "
            "Planning alone does not authorize implementation or timed scheduling.\n\n"
        ) + prompt
    platform = get_session_env("HERMES_SESSION_PLATFORM")
    chat_id = get_session_env("HERMES_SESSION_CHAT_ID")
    target = {}
    if platform and chat_id:
        # Origin routing also works when this is the first message in a chat.
        # Hermes retains profile ownership and applies gateway admission rules.
        origin = {"platform": platform, "chat_id": chat_id}
        for field in ("chat_type", "chat_name", "thread_id", "user_id", "user_id_alt",
                      "user_name", "scope_id", "parent_chat_id", "message_id", "profile"):
            value = get_session_env(f"HERMES_SESSION_{field.upper()}")
            if value:
                origin[field] = value
        target["origin"] = origin
    elif session_key := get_session_env("HERMES_SESSION_KEY"):
        target["session_key"] = session_key
    if ctx.inject_message(prompt, **target):
        return None
    return (
        f"Skill {name!r} was not started. For Telegram/gateway use, set "
        "plugins.entries.autowork.allow_gateway_injection: true in this profile's "
        "config.yaml and restart its gateway. If already enabled, check Hermes gateway logs."
    )


def blockers_args(raw_args):
    """The rest of `blockers [repo|name]`, or None: `/autowork blockers` and
    `/plan_with_me blockers` are `/blockers`, routed here rather than by the model."""
    first, _, rest = (raw_args or '').strip().partition(' ')
    return rest.strip() if first.lower() == 'blockers' else None


def _autowork(run_skill, run_blockers, raw_args):
    """`status` reads runners; `plugin status`, `update` and `list` inspect/maintain the bundle;
    `blockers` is `/blockers`;
    any other arguments run the skill."""
    from .bundle import maintenance_reply

    rest = blockers_args(raw_args)
    if rest is not None and run_blockers is not None:
        return run_blockers(rest)
    reply = maintenance_reply(raw_args)
    return run_skill(raw_args) if reply is None else reply


def register(ctx):
    """Hermes plugin entry point; called again on plugin load after a restart."""
    from hermes_cli.commands import resolve_command
    from hermes_cli.plugins import get_plugin_commands

    skills = _discover_skills()
    from hermes_constants import get_hermes_home
    from .install_skills import install
    native_skills = [path.parent for _, _, path in skills]
    shared = SKILLS_DIR / 'shared'
    if shared.is_dir():
        native_skills.append(shared)
    messages = []
    if install(SKILLS_DIR, [('current', get_hermes_home())], skills=native_skills, report=messages.append):
        # Commands load skills by qualified name, so a preserved native folder must not block them.
        logger.warning('Bundled native skill provisioning incomplete:\n%s', '\n'.join(messages))
    from .runtime_defaults import apply_runtime_defaults, provision_cron_scripts
    apply_runtime_defaults(ctx)
    for name in provision_cron_scripts(SKILLS_DIR, get_hermes_home()):
        logger.warning("Not replacing user-owned cron script scripts/%s.", name)
    existing = get_plugin_commands()
    for name, command, path in skills:
        # Canonical folders own the current skill identities.
        if name != "grill-me" or not any(n == "plan-with-me" for n, _, _ in skills):
            ctx.register_skill(name, path)
        if name in {"docs-sync", "plan-with-me", "plan-for-me"}:
            continue  # workflow_commands reserves both public spellings atomically.
        if resolve_command(command) is not None or command in existing:
            logger.warning("Skipping /%s: command already exists; use skill_view('autowork:%s').",
                           command, name)
            continue
        handler = partial(_invoke, ctx, name, path)
        if name == "autowork":
            blockers = next((partial(_invoke, ctx, n, p) for n, _, p in skills if n == "blockers"), None)
            handler = partial(_autowork, handler, blockers)
        ctx.register_command(
            command, handler,
            description=f"Run the {name} skill",
            args_hint="<instructions>" if name in {"autoresearch", "grill-me"} else "[instructions]",
        )
    from .autoresearch_commands import register as register_autoresearch
    register_autoresearch(ctx, skills, _invoke)
    from .workflow_commands import register as register_workflows
    register_workflows(ctx, skills, _invoke)
    from .bundle import register_bundle
    register_bundle(ctx, _invoke)
