# Troubleshooting

Symptom-first fixes for installing and using Hermes Toolset. Each entry links to
the owning guide; procedures are not repeated here. Start with the diagnostics:

```sh
hermes toolset doctor --core     # bundled skills and commands only
hermes toolset doctor --json     # full stack, machine-readable
```

In chat, `/toolset` shows load status and `/toolset list` shows which plugin owns
each command. Diagnostics check registration only: they never prove that a model
ran, a worker is available or a Telegram message was delivered.

## Commands

### A workflow command is not recognized

- **Check:** `/toolset list` and `hermes toolset doctor --core`.
- **Plugin not loaded or not enabled in this profile:** plugins are enabled per
  profile. Run `hermes -p PROFILE plugins enable hermes-toolset`; see
  [first use](onboarding.md).
- **Name owned by another plugin:** an existing command keeps its name. The
  bundle logs `Skipping /NAME: command already exists` and the skill stays
  available as `hermes-toolset:NAME`; see [workflows](workflows.md#commands).
- **Running gateway predates the update:** updating source does not refresh a
  running gateway's registry. Reload the plugin or restart the gateway, then
  open a new conversation.

### A command is missing from Telegram's picker but works when typed

This is expected. Menu capacity is limited, and compatibility spellings such as
`/autoresearch_plan` are deliberately not advertised. `/commands` lists
everything; see [workflow commands in the picker](onboarding.md#workflow-commands-in-telegrams-picker).

### Telegram still shows retired or old commands

Handlers refresh on plugin reload, but the bot menu refreshes only when the
gateway reconnects. `/toolset update` requests one graceful gateway restart when
it changes anything, and clears leftover per-chat lists that still contain retired
commands (`chat_menus_healed`). Otherwise restart the gateway through your normal
service procedure. See [update all profiles](installation.md#update-all-profiles).

### The agent follows old skill instructions after an update

Existing conversations keep instructions they already loaded. Open a new
conversation.

## Setup and doctor

### `doctor --core` passes but plain `doctor` fails

Plain `doctor` also requires the external integrations (OMH, Ponytail, speech,
imported skills). The `integration_gaps` field names them. Run full setup to add
them, or keep using the core workflows; see [installation](installation.md#install).

### Setup or a profile reports `incomplete`

- Read the profile's `errors` and the update or setup log; later stages can fail
  after earlier ones wrote, and there is no automatic rollback.
- Missing dependency consent: rerun with `--yes-deps`.
- Native security scans and blocked dependencies are reported, never bypassed.
- Fix the reported cause and rerun the same command; see
  [preflight](installation.md#preflight-before-fleet-writes).

### The `gateway` field is not `commands_reloaded`

| Value | Meaning |
| --- | --- |
| `not_running` | No live gateway; commands load when it starts. |
| `deferred_by_request` | You passed `--no-reload`. |
| `unreachable` / `reload_incomplete` | Wiring was not verified; restart the gateway and rerun setup. |

### Approval prompts disappeared after installing

This is the bundle's documented runtime policy (`approvals.mode: off` and related
keys), applied on every plugin load. Set
`plugins.entries.hermes-toolset.settings.apply_runtime_defaults` to `false`
first, then restore your values; see [reference](reference.md#plugin-settings)
and [removal and recovery](uninstall.md#restore-configuration-deliberately).

### Settings return after you changed them

Same cause: while `apply_runtime_defaults` is not `false`, each load rewrites the
policy keys that differ. Opt out first, then change them.

### `--dry-run` still changed configuration

CLI startup can apply runtime defaults before setup's preflight runs. From a
source checkout, `bash install.sh --yes-deps --dry-run` previews without booting
Hermes; see the [README](../README.md#first-use-in-your-project).

## Updates

### `/toolset update` replied “requested” but nothing seems to change

The reply only starts the background updater. Use `/toolset update status` for
the durable result. If status says the process stopped without a receipt, inspect
`maintenance/toolset-update/run.log` at the Hermes root and rerun.

### The update refuses or reports `drift`

- **Uncommitted changes or local commits in a plugin checkout:** the updater
  only fast-forwards. Commit, move or reconcile your changes; it never stashes,
  resets or force-pulls.
- **`drift`:** an installed skill file has unknown local differences on a path
  upstream did not change. All writes are deferred until you reconcile the
  listed paths.
- **Conflicting skill edits:** preserved for you to reconcile.

See [update all profiles](installation.md#update-all-profiles) for the full rules.

### The bundle broke after moving or deleting its checkout

Source installs link each profile to the checkout. Restore it at the same path,
or reinstall from its new location; see [update or remove](onboarding.md#update-or-remove).

## Workflows

### `/docs_sync` changed documents but nothing was implemented

By design: documentation and planning never start implementation. Run
`/autowork` for the task you want built; see [workflows](workflows.md#commands).

### Autowork reports `PRIORITY_DRIFT` or `UNMIGRATED`

`TODO.md` task order changed since the last recorded priority, or the project has
not recorded one yet. Scheduled Autowork reconciles drift itself; manually, run
the commands the report prints (`goals.py reorder`, or a one-time
`goals.py bootstrap-order` for `UNMIGRATED`). See
[TODO-owned task priority](project.md#todo-owned-task-priority).

### `docs.py check` reports findings

Each line names the role, the document and the problem: a broken link or anchor,
a documented script that does not exist, or a baseline role that is neither
mapped nor recorded as not applicable. Fix the document or the manifest; see the
[role manifest](../skills/docs-sync/references/document-scaffold.md#optional-role-manifest).

## Still stuck

Collect `hermes toolset doctor --json`, the relevant receipt or log and the exact
command you ran. Run `python3 scripts/check.py` from a source checkout to rule out
a local bundle regression; see [testing](testing.md).
