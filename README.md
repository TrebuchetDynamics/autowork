# hermes-toolset

A Hermes plugin that turns the skills in this repository into commands in
Hermes CLI chat and Telegram. Add a `skills/<name>/SKILL.md`, update the installed
plugin, and restart Hermes; there is no command list to maintain.

## Install

For a published version that includes `hermes toolset setup`:

Setup is broader than installing this plugin: the current source inventory targets
all profiles for OMH, Ponytail, external skills, Graphify, speech support,
and OMH memory. Setup selects OMH with bounded `auto-safe` capture; no external
memory server or connection JSON is required. If the published version
does not yet include setup, use the local checkout instructions below.

```sh
hermes plugins install TrebuchetDynamics/hermes-toolset
hermes plugins enable hermes-toolset
hermes toolset setup --yes-deps
hermes toolset doctor
```

From a local checkout, one command performs the complete installation for every
existing live profile:

```sh
bash install.sh --yes-deps
```

`install.sh`, `install-plugins.sh`, and `hermes toolset setup` share the same
complete setup path: bundled skills, plugin installation/enablement, profile
configuration, OMH setup, per-profile readiness checks, and running-gateway command
refresh. No manual symlinks or per-profile enable commands are needed. Use
`--dry-run` to preview, `--bundle-only` to install only this bundle and its native
skills, or `--no-reload` to explicitly defer gateway wiring. Dependency consent
and native security scans still apply; a blocked dependency or failed readiness
check returns nonzero and reports setup as incomplete.

Plugins are enabled per profile. For a named profile, use that profile's home for
the link and `hermes -p PROFILE plugins enable hermes-toolset` to enable it.
`hermes toolset setup` installs and enables the sources in
[plugins/PLUGINS.md](plugins/PLUGINS.md), including external skill repositories,
Graphify's Hermes integration, and OMH's full memory setup. It also links and enables
hermes-toolset itself in every existing live profile, preserving existing plugin
installations. After creating another profile, rerun setup or, from this checkout,
run `bash install-plugins.sh --bundle-only` to add just this bundle and its defaults
across profiles. The links depend on keeping this checkout installed. It applies
[our defaults](plugins/defaults.json): select OMH with `auto-safe` memory in independent stores, keep the
current TUI, disable the optional menubar, allow toolset gateway injection, and
set `approvals.mode` to `off` for profiles with hermes-toolset installed. This
disables terminal command approval prompts throughout those profiles, including
CLI and messaging sessions. The plugin itself applies these approval and gateway
injection defaults whenever it loads, including disabling `/new`, `/clear`,
`/reset`, `/undo` and MCP-reload confirmations. No setup command is needed for
this policy after the plugin is enabled. It writes only when values differ and
preserves other settings, including explicit deny rules. Hermes hard blocks still
apply. Setup also clears global and per-channel skill disable lists.
To opt out of automatic policy application, first run
`hermes -p PROFILE config set plugins.entries.hermes-toolset.settings.apply_runtime_defaults false`,
then restore the desired settings, for example
`hermes -p PROFILE config set approvals.mode manual` and
`hermes -p PROFILE config set approvals.destructive_slash_confirm true`.
It runs OMH doctor after setup, checks every profile, and refreshes live commands. Native Hermes installation has no post-install
hook, so the setup command is required after installing this repository.
Use `hermes toolset setup --dry-run` to preview target profiles.

## Bundled Grill Me

`skills/grill-me/SKILL.md` bundles the MIT-licensed official
`official/software-development/grill-me` skill (version 2.0.0), preserving its
upstream attribution. It is available through `/grill-me` in CLI chat and
`/grill_me` in Telegram. Enabling/loading hermes-toolset installs missing bundled
skills and shared support files into that profile's native skill directory, using
the same offline provisioner as full setup. Existing flat and categorized skills
are preserved; incomplete existing slots fail visibly instead of being replaced.
Ordinary plugin loading never installs network dependencies, changes sibling
profiles, or reloads a gateway. Full setup provisions native skills across all
profiles before external plugin setup.
Setup refreshes running gateway command handlers and checks their activation
receipts automatically. It does not send test messages or restart ongoing turns.
Existing sessions can retain prior tools, prompts and memory providers; those
changes apply to new sessions. A stopped gateway is reported as not running,
not as a tested messaging connection.

## OMH memory per profile

OMH is the bundled external memory provider. Full setup selects
`memory.provider: omh` with `auto-safe` policy and binds the plugin to an
independent store for every profile: `<hermes-home>/omh` for new bindings.
Existing explicit stores are preserved. Resolved duplicate stores, including
symlink aliases and inherited global `OMH_HOME`, are refused before writes.
Clear another selected provider explicitly before setup; OMH never silently
steals its slot.

`auto-safe` admits only bounded eligible records; other candidates still need
review. Reviewed OMH records and Hermes built-in `MEMORY.md`/`USER.md` remain
separate. Setup does not erase or import built-in memory or legacy Hindsight
stores, change the chat model, or start a memory server. Shared plugin code does
not imply a shared store. Project-local `.omh` records are separate project
context and can intentionally be shared by sessions in the same repository.

To configure only OMH using the checked-in defaults, select every existing
profile when including default (upstream root setup synchronizes children):

```sh
python3 install-omh.py --hermes-home "$HOME/.hermes" \
  --profile default --profile work
hermes -p work memory status
```

The helper runs children before default, binds each runtime store explicitly,
and checks OMH doctor after root synchronization. Repeat after creating a
profile; `--bundle-only` does not configure external memory. Restart or reload
existing sessions after switching providers; no shared gateway is restarted.
Provider status is not replay evidence: verify a harmless reviewed record in
its own profile and its absence from other profile stores before relying on it.

Hermes may flag the bundled workflow scripts during installation. Review its
findings; the plain install command can require an explicit scanner override.
Setup never bypasses scans for imported plugins or skills. Some upstream skills
currently trigger hard blocks that even Hermes's `--force` cannot override.

`--yes-deps` consents to declared plugin dependencies. Security scans remain
enabled; blocked imports make setup fail and need review. Existing installations
are preserved. No gateways are restarted automatically.

Hindsight support has been removed. Existing memory stores are not deleted or
migrated by this change. Removing its plugin does not erase its stored memories.

## Telegram setup

Enabling/loading hermes-toolset applies its gateway-injection setting in the
owning profile. There is no YAML wiring step. This lets a skill command queue an
agent turn in the chat where it was invoked. Full setup refreshes running gateway
commands and verifies activation receipts; `--no-reload` explicitly defers that.
Existing CLI chats must be reopened to receive a new plugin/tool inventory.

Requires a current Hermes build with `register_skill`, `register_command`,
and `inject_message(..., origin=...)` support. Hermes needs its normal model and Telegram
configuration; individual skills may require their own tools.

## OMH runtime troubleshooting

A passing standalone OMH doctor does not prove that the live Hermes plugin can
bind its runtime store. If chat reports `RuntimeBindingError`, ask the agent to
invoke `omh_status` without home overrides to obtain the specific refusal.
For a missing profile binding, point Hermes at the existing OMH store; do not
create a replacement store or overwrite managed skills. With the default setup
layout, use:

```sh
hermes config set plugins.entries.omh.settings.omh_home "$HOME/.hermes/omh"
omh --omh-home "$HOME/.hermes/omh" --hermes-home "$HOME/.hermes" doctor
```

Substitute the actual existing store and profile home if they differ. For a named
profile, also use `hermes -p PROFILE config set` for that profile's setting.
Retry the native `omh_status` tool in chat; successful runtime reads verify the
binding fix. Other binding failures require diagnosis, not this setting change.

## Commands

Use `/toolset` for plugin versions, load status, registered tool/command/skill/hook
counts, and unavailable imports. These are registered capabilities, not a claim
that every tool is enabled in the current chat. Hermes's `/toolsets` lists tool
groups; plugins that provide skills, commands, or hooks need not appear there.
Use `/toolset list` in CLI chat or Telegram for the installed command inventory,
or `/toolset omh` to filter it. `hermes toolset doctor --json` reports plugin load
errors and missing imports. Imported native commands keep their own handlers;
imported plugin skills without commands receive aliases. Telegram's menu has a
capacity limit, so some commands must be typed rather than selected in the menu.

| Hermes CLI chat | Telegram | Purpose |
| --- | --- | --- |
| `/autogoal` | `/autogoal` | Run the autonomous goal workflow |
| `/git-commit-push` | `/git_commit_push` | Commit and push scoped changes |
| `/git-pull-merge` | `/git_pull_merge` | Pull and merge changes |
| `/lgtm` | `/lgtm` | Continue from an approved checkpoint |
| `/repo-docs` | `/repo_docs` | Maintain repository documentation |
| `/repo-interview` | `/repo_interview` | Answer focused questions, then update docs and plans |

Use `/repo-interview` when you want questions before planning. It asks one at a
time, reuses existing answers, and saves decisions through repo-docs. Add
`questions only` for an interview without file changes.

For example, type `/repo-docs update the architecture documentation` in Hermes
CLI chat, or `/git_commit_push only src/; no push` in Telegram. Arguments are
passed as text to the skill, never executed as a shell command by the plugin.
These are conversational slash commands, not new `hermes <skill>` shell
subcommands. The agent loads the skill through `skill_view` and performs its
instructions using the current conversation and tools.

Bundled skills also remain available by their qualified names, such as
`hermes-toolset:repo-docs`. Supporting files stay next to their `SKILL.md`. Shared contracts live in
[`skills/shared`](skills/shared/COMMON-CONTRACT.md), alongside the skill folders;
the legacy skill copier preserves that support directory too. Resolve helper
commands from the loaded bundle rather than assuming `~/.hermes/shared-skills`.
Generated autogoal ledger commands use quoted paths to the bundled helper.
An existing built-in or previously registered plugin command wins a name
collision; the skipped alias produces a warning and the qualified skill remains
available. Choose distinctive names to avoid collisions with other plugins,
local skills, and configured quick commands.

Repo-docs and autogoal decide routine engineering choices autonomously within the
accepted scope. They carry decisions into worker contracts and apply relevant
[Addy agent-skills](https://github.com/addyosmani/agent-skills) throughout planning,
implementation and verification, including API, UI, migration, CI and operational
work. Handoffs identify the skill used, the artifact or decision it informed, and
its check result. Missing owner intent or authority remains an explicit question;
loading a skill alone is not proof of applying it.

The [engineering cycle](skills/shared/ENGINEERING-CYCLE.md) connects accepted
specs and existing `goals.json`/`TODO.md` tasks to targeted installed engineering
skills, implementation, checks, native review and owner-ledger reconciliation.
A documentation-only `/repo-docs` request does not launch workers. To continue
through a spec, explicitly ask `/autogoal` to implement that accepted spec within
its stated scope. Default `/autogoal` hands off one slice. Review acceptance and
executed evidence precede canonical closure; no push or deployment is implied.
Skill availability and support files are checked at use time; a missing skill is
reported with its safe fallback, not silently treated as loaded.

## Autoresearch

The bundle vendors [uditgoenka/autoresearch](https://github.com/uditgoenka/autoresearch)
v2.2.2 at the revision in [UPSTREAM.json](skills/autoresearch/UPSTREAM.json), with
its MIT license and runtime scripts. Installing the bundle makes it available in
every configured profile; no separate Claude/Codex installation is required.

Use `/autoresearch` for goal routing or a metric-driven loop. All 13 upstream
subcommands are available:

`plan`, `debug`, `fix`, `security`, `ship`, `probe`, `scenario`, `predict`,
`reason`, `learn`, `improve`, `evals`, `regression`.

CLI keeps `/autoresearch:plan`; Telegram uses `/autoresearch_plan` (likewise for
every subcommand). `/autoresearch plan ...` also works. Colon commands are omitted
from Telegram's menu; use the underscore spelling there. Menu capacity can hide
entries without disabling typed commands. Existing command owners keep precedence.

```text
/autoresearch_plan reduce cache latency; document findings and schedule TODO tasks; do not implement yet
/autoresearch Goal: reduce parser time Scope: src/parser Metric: milliseconds Verify: python bench.py Iterations: 10
```

The [Hermes adapter](skills/autoresearch/SKILL.md) connects research to repo-docs:
findings update existing documents, matching tasks are reused, and accepted gaps
become full TODO.md bodies with goals.json priorities, dependencies and checks.
This schedules the backlog; it does not create a timer. Autogoal can execute
eligible tasks when implementation is authorized, preserving its ownership,
verification and commit gates. Read-only and planning-only requests remain scoped.
Upstream flags and analytical methods are retained; host-specific tools, generic
confirmation prompts, experimental Git handling and documentation handoffs follow
the adapter. Claude-only hooks are not installed.

## Add or update a skill

```text
skills/
  my-skill/
    SKILL.md
    references/   # optional
    scripts/      # optional
```

Use a folder name of 1–32 lowercase letters, digits, hyphens, or underscores,
starting with a letter or digit. The folder determines the command name; keep
the skill's frontmatter `name` consistent with it. Underscores become hyphens
in CLI commands and Telegram uses underscores: `my_skill` becomes `/my-skill`
in CLI chat and `/my_skill` in Telegram. `my-skill` and `my_skill` cannot coexist.

Every immediate child containing `SKILL.md` is discovered at plugin startup.
Folders without that file are ignored. Invalid names, ambiguous aliases, or
skill paths pointing outside the bundle cause an explicit plugin-load error.

For a GitHub installation, publish your skill changes and run:

```sh
hermes plugins update hermes-toolset
hermes gateway restart
```

Follow any Hermes request to stop a running gateway before updating. For a local
symlink installation, edit this checkout and restart instead. New commands are
discovered on startup, not watched live. Telegram's menu has limited capacity;
Hermes controls which commands appear there.

## Verify

```sh
python scripts/check.py
python scripts/check.py --list
python -m py_compile __init__.py bundle.py install-omh.py install-graphify.py
```

The checker runs top-level and maintained bundled workflow tests in separate
Python processes, with a 180-second timeout per directory. `--list` prints the
inventory without importing tests. Model, installed native backend and optional
integration suites are explicitly excluded with reasons; live opt-in flags are
removed from test subprocesses. Passing this gate does not qualify model/native
execution. Tests use temporary Git fixtures and may write offline scratch receipts.

`tests/integration_plugin.py` additionally checks the actual Hermes manifest
reader, loader, bundled skill reader, Telegram menu, CLI queue, gateway routing,
and unload behavior. Run it using Hermes' Python environment with the Hermes
source root on `PYTHONPATH`. It uses a temporary profile and a capture callback
instead of sending Telegram messages or calling a model.

`tests/integration_bundle.py` checks an existing isolated `HERMES_HOME`: all
loaded skill content, CLI queues and captured gateway routing for every generated
alias, plus the expected-import inventory. Run it with the same Hermes Python
environment and source `PYTHONPATH`. It exits nonzero for missing or blocked
imports. Native command registration is inspected; upstream actions, external
services, and live Telegram delivery are not invoked.

From this repository's root, use the installed Hermes interpreter and source
checkout (adjust `HERMES_SOURCE` if Hermes is installed elsewhere):

```sh
HERMES_PYTHON="$(hermes --print-runtime-command --module runpy | python -c 'import json, sys; print(json.load(sys.stdin)[0])')"
HERMES_SOURCE="$HOME/.hermes/hermes-agent"
PYTHONPATH="$HERMES_SOURCE" "$HERMES_PYTHON" -c 'import hermes_bootstrap, runpy, sys; runpy.run_path(sys.argv[1], run_name="__main__")' tests/integration_plugin.py
```

For the full bundle check, first provide an existing isolated profile where the
bundle and its declared imports have already been installed. Do not point this
check at your live profile; plugin loading may write runtime records.

```sh
HERMES_HOME="/path/to/isolated-installed-profile" PYTHONPATH="$HERMES_SOURCE" "$HERMES_PYTHON" -c 'import hermes_bootstrap, runpy, sys; runpy.run_path(sys.argv[1], run_name="__main__")' tests/integration_bundle.py
```

The offline suite runs in GitHub Actions. Live Telegram delivery and model
execution require your configured Hermes installation.
