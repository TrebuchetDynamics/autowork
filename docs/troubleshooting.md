# Troubleshooting

Symptom-first fixes for installing and using Autowork. Each entry links to
the owning guide; procedures are not repeated here. Start with the diagnostics:

```sh
hermes autowork doctor --core     # bundled skills and commands only
hermes autowork doctor --json     # full stack, machine-readable
```

In chat, `/autowork status` shows runner fleet status and `/autowork status NAME`
shows one repository. `/autowork plugin status` shows plugin load/setup status,
and `/autowork list` shows which of this
bundle's plugins (or a skill) owns each command; Hermes' `/commands` lists only
built-in and skill commands, not plugin commands. Diagnostics check registration only: they never prove that a model
ran, a worker is available or a Telegram message was delivered.

## Commands

### A workflow command is not recognized

- **Check:** `/autowork list` and `hermes autowork doctor --core`.
- **Plugin not loaded or not enabled in this profile:** plugins are enabled per
  profile. Run `hermes -p PROFILE plugins enable autowork`; see
  [first use](onboarding.md).
- **Name owned by another plugin:** an existing command keeps its name. The
  bundle logs `Skipping /NAME: command already exists` (with a `skill_view` hint
  for most skills) and the skill stays available as `autowork:NAME`; see [workflows](workflows.md#commands).
- **Running gateway predates the update:** updating source does not refresh a
  running gateway's registry. Reload the plugin or restart the gateway, then
  open a new conversation.

### A command is missing from Telegram's picker but works when typed

This is expected. Menu capacity is limited, and compatibility spellings such as
`/autoresearch_plan` are deliberately not advertised. `/autowork list` shows them
(Hermes' `/commands` omits plugin commands); see [workflow commands in the picker](onboarding.md#workflow-commands-in-telegrams-picker).

### Telegram still shows retired or old commands

Handlers refresh on plugin reload, but the bot menu refreshes only when the
gateway reconnects. `/autowork update` restarts the running root gateway once when it
changed anything and every profile activated cleanly, but only while no chat turn is
in flight (`gateway_restart: requested`); otherwise it reports `deferred` and a
waiter restarts at the first quiet moment within 6 hours, never forcing
(`deferred_expired` if none came; `pending` while an earlier restart is
outstanding). Profile-dedicated gateways are not detected. `/autowork update status`
shows `gateway_restart_progress` with what it is waiting on. It also
clears leftover per-chat lists that still contain retired commands for the owner and
home chats configured in each profile's `.env` (`chat_menus_healed`). Otherwise
restart the gateway through your normal service procedure. See [update all profiles](installation.md#update-all-profiles).

### The agent follows old skill instructions after an update

Existing conversations keep instructions they already loaded. Open a new
conversation.

## Setup and doctor

### `doctor --core` passes but plain `doctor` fails

Plain `doctor` also requires the external integrations (OMH, Ponytail, speech,
imported skills). The `integration_gaps` field names them. Run full setup to add
them, or keep using the core workflows; see [installation](installation.md#install).

### Setup or a profile reports `incomplete`

- Read the setup output or the profile's `errors` (update receipts record
  `enable_exit` and `finalize_exit` per profile; details are in `run.log`); later
  stages can fail after earlier ones wrote, and there is no automatic rollback.
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
`plugins.entries.autowork.settings.apply_runtime_defaults` to `false`
first, then restore your values; see [reference](reference.md#plugin-settings)
and [removal and recovery](uninstall.md#restore-configuration-deliberately).

### Settings return after you changed them

Same cause: while `apply_runtime_defaults` is not `false`, each load rewrites the
policy keys that differ. Opt out first, then change them.

### `--dry-run` still changed configuration

CLI startup can apply runtime defaults before setup's preflight runs. From a
source checkout, `bash install-plugins.sh --yes-deps --dry-run` previews without booting
Hermes; see the [README](../README.md#first-use-in-your-project).

### Setup is BLOCKED by a memory provider, or printed `memory off`

OMH never replaces another selected memory provider. Full setup's preflight
reports `BLOCKED: ... existing memory provider conflicts with OMH setup`; running
`install-omh.py` directly instead prints `memory off` with the provider's name and
the command that clears it (`hermes memory off`, with `-p PROFILE` for a named
profile). Run it, then rerun setup to use OMH memory. `memory.provider is not set` means OMH did not
take the empty slot; check `hermes -p PROFILE memory status`. See
[memory](memory.md#omh-memory-per-profile).

## Updates

### `/autowork update` replied “requested” but nothing seems to change

The reply only starts the background updater. Use `/autowork update status` for
the durable result. If status says the process stopped without a receipt, inspect
`maintenance/toolset-update/run.log` at the Hermes root and rerun.

### The update refuses, or reports `local_edits`

- **Uncommitted changes or local commits in a plugin checkout:** ordinary source
  updates require a clean equal or fast-forward checkout. Qualifying managed
  checkouts have a separate [guarded recovery path](installation.md#managed-checkout-recovery)
  with preserved local work and explicit refusal conditions; this is not permission
  to discard unproven commits. Otherwise commit, move or reconcile your changes;
  the ordinary update does not stash, reset or force-pull the source checkout.
- **`local_edits`:** a profile edited its installed skill copy. `reset` means the copy
  was replaced by the release and the edited bytes are in the update's backup (the
  receipt's `backup`); port lessons that should reach every profile into the bundle.
  `removed` is an edited copy of a skill file the bundle no longer ships, deleted the
  same way. A rerun lists a file again only if something edited it since.

See [update all profiles](installation.md#update-all-profiles) for the full rules.

### A restart rolled out changes no update released

Profiles linked to a working checkout load its current files at every gateway
restart. `/autowork update status` lists them; pin the ones that should change only
through updates with `hermes autowork pin NAME` (preview with `--dry-run`).
See [linked profiles](installation.md#linked-profiles-and-pinned-clones).

### The bundle broke after moving or deleting its checkout

Source installs link each profile to the checkout. Restore it at the same path,
or delete the now-dangling `plugins/autowork` link in each profile and rerun
setup from the new location (setup and update refuse a dangling link); see [update or remove](onboarding.md#update-or-remove).

## Workflows

### `/docs_sync` changed documents but nothing was implemented

By design: documentation and planning never start implementation. Run
`/autowork` for the task you want built; see [workflows](workflows.md#commands).

### Autowork says `no tasks/ store: run autowork migrate`

The repository still keeps its tasks in `TODO.md` and `goals.json`, which nothing reads.
Commit or set aside planning edits, let running work finish, then run `/docs_sync` in the
repository (or `autowork tasks prepare <repo>`, or `autowork migrate <repo>`): it converts
the queue to `tasks/` in one local commit and refuses, writing nothing, while work is in
flight. A conversion that was interrupted resumes on the next run. See
[Task Store v2](project.md#task-store-v2-2026-10-20).

### `autowork tasks validate` reports an error

Each error names a task or goal file and line (`tasks/items/T-1.md:7: unknown goal G`);
the whole store is refused until it is fixed, so the runner selects nothing meanwhile.
Fix that file (`autowork tasks field` or an editor) and run
`autowork tasks validate --worktree` again before committing.

### `docs.py check` reports findings

Each line names the role and the problem, and the document where one applies: a
manifest validation error, a missing mapped document or anchor, a broken link or
anchor, a documented script that does not exist, a missing covered path, or a
baseline role that is neither mapped nor recorded as not applicable. Fix the document or the manifest; see the
[role manifest](../skills/docs-sync/references/document-scaffold.md#optional-role-manifest).

### `docs.py stale` reports an unverifiable historical pin

`stale` exits 1 when a covered role has no `verified_at`, an unknown commit, or a
commit that is not an ancestor of the checkout's HEAD. An existing commit on a
different history is not current-source proof. Preserve its identifier and record
the role's source-evidence gap; do not replace a pin with HEAD merely to remove a
warning. Reverify the document against its full current source closure before
recording new verification, retaining the old identifier as historical evidence.
This repository's [role provenance inventory](project.md#role-source-evidence-gaps)
distinguishes the retained pins from current gaps. A passing `check` verifies
structure and local references, not content accuracy or runtime qualification.

## Still stuck

Collect `hermes autowork doctor --json`, the relevant receipt or log and the exact
command you ran. Run `python3 scripts/check.py` from a source checkout to rule out
a local bundle regression; see [testing](testing.md).
