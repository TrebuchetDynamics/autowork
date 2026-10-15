# Command and configuration reference

Exact entry points, flags, settings and environment variables this bundle reads.
Each entry names its source of truth; when they disagree, the source wins and this
page has drifted. Conversational workflow commands (`/autowork`, `/docs_sync`,
`/plan_with_me` and the rest) are listed in [workflows](workflows.md#commands);
procedures and their side effects are in [installation](installation.md).

## Terminal: `hermes toolset`

Source: [`bundle.py`](../bundle.py) `setup_parser` and `handle_cli`. Add `-p PROFILE`
after `hermes` to run from a named profile; `setup` and `update` still target every
live profile under the same Hermes root.

| Command | Flags | Effect |
| --- | --- | --- |
| `hermes toolset doctor` | `--json`; `--core` (alias `--bundle-only`) | Reports plugin load and command/skill registration. Exit 1 unless `status` is `ready`. `--core` ignores external integration gaps. |
| `hermes toolset setup` | `--dry-run`, `--yes-deps`, `--bundle-only`, `--no-reload`, `--hermes-home ROOT` | Runs [`setup_bundle.py`](../setup_bundle.py): installs sources in [`plugins/PLUGINS.md`](../plugins/PLUGINS.md), applies [defaults](../plugins/defaults.json), finalizes every live profile. |
| `hermes toolset update` | `--check`, `--hermes-home ROOT` | Runs [`update_bundle.py`](../update_bundle.py) and waits: fast-forward-only update of every live profile. `--check` fetches and previews only. |
| `hermes toolset finalize` | `--hermes-home ROOT` (required), `--bundle-only`, `--no-reload` | Verifies one profile's registrations and runtime settings and refreshes gateway commands; setup calls it per profile. |

`setup` flags:

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Preview target profiles and actions without writing. CLI startup can still apply runtime defaults; see [installation](installation.md#preflight-before-fleet-writes). |
| `--yes-deps` | Consent to declared Python dependencies during native installs. |
| `--bundle-only` | Link, enable and configure only this bundle; skip external sources. |
| `--no-reload` | Defer live gateway wiring explicitly. |
| `--hermes-home ROOT` | Hermes root containing `profiles/` (default: `HERMES_HOME`, else `~/.hermes`). |

## Chat: `/toolset`

Source: [`bundle.py`](../bundle.py) `handle_chat`, `list_commands`, `start_update`,
`update_status`. Works in CLI chat and Telegram.

| Form | Effect |
| --- | --- |
| `/toolset` | Bundle version, revision and profile; ready workflow commands; the last update; other plugins' load status and counts; missing imports with the setup command. |
| `/toolset list` | Every available command with its owner and Telegram spelling. |
| `/toolset list TEXT` or `/toolset TEXT` | Commands whose name or owner contains `TEXT`, for example `/toolset omh`. |
| `/toolset update` | Starts the all-profile updater in the background and returns immediately. |
| `/toolset update --check` | Starts an upstream check only. |
| `/toolset update status` | Summarizes the durable result from `maintenance/toolset-update/latest.json` at the Hermes root in a few lines. |
| `/toolset update status full` | Shows that whole receipt as JSON. |

## Source-checkout scripts

Run from a clone of this repository. The shell installers are thin wrappers.

| Script | Flags | Effect |
| --- | --- | --- |
| `bash install.sh` | Same as `hermes toolset setup` | Executes [`setup_bundle.py`](../setup_bundle.py). |
| `bash install-plugins.sh` | Same as `install.sh`; `--help` | Public calls, including `--help`, execute `setup_bundle.py`. The source-installer usage appears only with the internal `--sources-only --help`. |
| `bash install-skills.sh` | `--dry-run`, `--hermes-home ROOT`, `--profile-home HOME` | Runs [`install_skills.py`](../install_skills.py): copies `skills/` (except retired `repo-docs` and `repo-interview`) into the default and every existing profile, or only `--profile-home`; `--hermes-home` and `--profile-home` are mutually exclusive. Never overwrites existing skill paths or changes configuration. |
| `python3 update_bundle.py` | `--hermes-home ROOT` (required), `--check`, `--profile NAME` (repeatable with `--source`), `--source CHECKOUT`, `--revision SHA`, `--native-python PATH` | All-profile update, or with `--profile`, `--source`, `--revision` and `--native-python` (all four required) a scoped deployment of a reviewed local commit; see [installation](installation.md#deploy-an-exact-local-revision-to-selected-profiles). |
| `python3 install-graphify.py` | `--hermes-home ROOT`, `--profile NAME` (both required), `--dry-run` | Installs Graphify's Hermes skill into selected existing profiles; installs the `graphifyy` tool with `uv tool install` when missing. |
| `python3 install-omh.py` | `--hermes-home ROOT`, `--profile NAME` (both required), `--dry-run` | Applies the checked-in OMH defaults to selected homes, installing `omh` with `uv tool install` when missing, and writes `plugins.entries.omh.settings.omh_home`; see [memory](memory.md). |
| `python3 scripts/check.py` | `--list`, `--timeout SECONDS` (default 600 per directory) | Runs the offline test inventory; see [testing](testing.md). |

## Repository helpers used by workflows

These ship inside the bundle and are run by skills against your project. Paths are
relative to this repository.

| Helper | Commands | Reference |
| --- | --- | --- |
| [`skills/docs-sync/scripts/goals.py`](../skills/docs-sync/scripts/goals.py) | `init`, `validate`, `fmt`, `render`, `revision`, `archive`, `next`, `reorder`, `bootstrap-order`, `focus`, `task`, `supersede`, `section`, `add-task`, `redact`, `evidence`, `backlog-check` | `goals.py --help`; [document scaffold](../skills/docs-sync/references/document-scaffold.md#first-task-index-initialization) |
| [`skills/docs-sync/scripts/docs.py`](../skills/docs-sync/scripts/docs.py) | `validate`, `check`, `stale`, `profiles` | `docs.py --help`; [role manifest](../skills/docs-sync/references/document-scaffold.md#optional-role-manifest) |

## Plugin settings

Source: [`runtime_defaults.py`](../runtime_defaults.py),
[`plugins/defaults.json`](../plugins/defaults.json). Set them per profile with
`hermes -p PROFILE config set KEY VALUE`.

| Key | Default | Meaning |
| --- | --- | --- |
| `plugins.entries.hermes-toolset.settings.apply_runtime_defaults` | `true` | Boolean `false` stops the plugin from applying the runtime policy below on load (`config set` stores the word `false` as a boolean). The legacy `…hermes-toolset.config.apply_runtime_defaults` is honored when `settings` lacks the key. Setup honors it too and skips the policy and skill-list settings for that profile. Set it before restoring your own values. |

While `apply_runtime_defaults` is not `false`, each plugin load writes these
values whenever they differ, preserving other settings:

| Key | Value written |
| --- | --- |
| `approvals.mode` | `off` |
| `approvals.destructive_slash_confirm` | `false` |
| `approvals.mcp_reload_confirm` | `false` |
| `agent.max_turns` | `unlimited` (no per-turn iteration cap; Hermes quick setup writes `90`) |
| `plugins.entries.hermes-toolset.allow_gateway_injection` | `true` |
| `platforms.telegram.extra.command_menu.priority` | Your entries first, then the workflow commands and the `ui_taste`, `beautify_github_readme`, `impeccable`, `lgtm`, `engineering` and `git_commit_push` skill commands appended; retired bundle names and `autoresearch_*` entries removed. Other menu settings such as the mode and cap are not changed ([`telegram_menu_policy.py`](../telegram_menu_policy.py)). |

Every setup, including `--bundle-only`, also clears the global and per-platform skill
disable lists, except in opted-out profiles. Full setup additionally applies the `omh` block of `defaults.json`
(memory mode `auto-safe`, TUI and menubar off). See [installation](installation.md#install) for the policy and
[removal](uninstall.md) to restore values.

## Environment variables

| Variable | Read by | Meaning |
| --- | --- | --- |
| `HERMES_HOME` | Setup, skill installer, `install-plugins.sh` | Default Hermes root when `--hermes-home` is absent. A named-profile home (`ROOT/profiles/NAME`) resolves to `ROOT`. Defaults to `~/.hermes`. `/toolset update` uses the running profile's Hermes root the same way. |
| `OMH_HOME` | [`install-omh.py`](../install-omh.py) | An exported or `.env` binding is preserved as the OMH store location; see [memory](memory.md). |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL` | Update menu healing, from each profile's `.env` (not the process environment) | For each distinct bot token, the chats whose leftover command lists the updater checks; see [installation](installation.md#update-all-profiles). |

## Files and state

| Path | Owner | Contents |
| --- | --- | --- |
| `ROOT/maintenance/toolset-update/latest.json` | Updater | Latest update receipt: status, revisions, profiles, local edits, backup location. |
| `ROOT/maintenance/toolset-update/restart.json` | Updater | The last gateway restart the updater requested (process ID), or its deferred-restart waiter (process ID, latest chat-turn count), plus `covers`, the updates that restart will load; used to report progress, avoid overlapping restarts and record the outcome on each covered update. |
| `ROOT/maintenance/toolset-update/run.log` | Updater | Output of updates started with `/toolset update` and of gateway restarts the updater requests; terminal `hermes toolset update` prints to the terminal. |
| `TODO.md`, `goals.json`, `TODO.archive.md` (project) | Docs Sync, Autowork | Work queue, its machine index and completed-task history. |
| `docs/roles.json` (project, optional) | Docs Sync | Document role manifest. |
