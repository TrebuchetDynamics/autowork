# Memory and retained data

Source: [OMH setup](../install-omh.py) and [bundle defaults](../plugins/defaults.json).

## OMH memory per profile

OMH is the bundled external memory provider. Full setup selects
`memory.provider: omh` (when no other provider holds that slot) with `auto-safe` policy and binds the plugin to an
independent store for every selected profile: `<hermes-home>/omh` when the profile has no
OMH binding yet. Existing stores are preserved: an explicit profile binding, the
profile `.env` or exported `OMH_HOME`, or, for a profile already using OMH without
one, its standalone `~/.omh`. Resolved duplicate stores, including
symlink aliases and inherited global `OMH_HOME`, are refused before writes; a
duplicate anywhere among the Hermes root's profiles blocks setup, even for
profiles that were not selected.
Clear another selected provider explicitly before setup; OMH never silently
steals its slot. Full setup's preflight refuses such a profile. Running
`install-omh.py` directly still completes, but OMH memory stays off,
and the helper prints `OMH setup: NAME (memory off: memory.provider is <name>; run ...)`
with the `hermes [-p NAME] memory off` command to clear it. It prints
`memory off: memory.provider is not set` when OMH left the slot empty, and
`memory provider unverified: ...` when the profile config cannot be read back.

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

Hindsight support has been removed. Existing memory stores are not deleted or
migrated by this change. Removing its plugin does not erase its stored memories.

## OMH runtime troubleshooting

A passing standalone OMH doctor does not prove that the live Hermes plugin can
bind its runtime store. If chat reports `RuntimeBindingError`, ask the agent to
invoke `omh_status` without home overrides to obtain the specific refusal.
A missing binding reads `Tool execution failed: RuntimeBindingError: OMH home is
not configured for this profile`. For a missing profile binding, point Hermes at the existing OMH store; do not
create a replacement store or overwrite managed skills. With the default setup
layout, use:

```sh
hermes -p default config set plugins.entries.omh.settings.omh_home "$HOME/.hermes/omh"
omh --omh-home "$HOME/.hermes/omh" --hermes-home "$HOME/.hermes" doctor
```

Substitute the actual existing store and profile home if they differ. For a named
profile, use `hermes -p PROFILE config set` with that profile's store instead.
Retry the native `omh_status` tool in chat (start a new session if the retry still
fails); successful runtime reads verify the binding fix. Other binding failures require diagnosis, not this setting change.


## Capture, inspection and deletion

Memory can persist repository facts, decisions, lessons, procedures and episode
summaries supplied to OMH. Retained records can later be recalled into an agent's
context. Local storage does not mean recalled content stays off the configured
model provider: treat retained text as information the agent may use in prompts.
Do not place credentials or confidential material in memory on the assumption
that `auto-safe` guarantees privacy.

`auto-safe` enables OMH's automatic admission of candidates that pass its eligibility
and safety checks. It does not mean every captured candidate is automatically
approved. In the locally inspected implementation, automatic admission also needs
a `safe` safety verdict (and a principal context for user-scope captures), while
duplicate candidates, derived content requiring review and relative-time summaries
always stay on the review path. These rules belong to the installed OMH version, not this command bridge;
check its actual policy and candidate review output. No blanket retention period,
secret-detection guarantee or automatic purge is promised by Toolset.

Use the actual profile and store binding reported by setup. For a default-layout
named profile, these read-only inspection commands are examples:

```sh
omh --omh-home "$HOME/.hermes/profiles/work/omh" --hermes-home "$HOME/.hermes/profiles/work" memory status
omh --omh-home "$HOME/.hermes/profiles/work/omh" --hermes-home "$HOME/.hermes/profiles/work" memory review --limit 10
omh --omh-home "$HOME/.hermes/profiles/work/omh" --hermes-home "$HOME/.hermes/profiles/work" memory inspect --summary
```

Substitute its existing store if setup preserved a different binding. `review`
shows candidates; `inspect` shows available memory snapshots, not proof of every
stored byte. `memory inventory` and `memory recall` provide additional inspection;
read their installed `--help` before selecting scopes. `inventory --write-ledger`
writes a metadata ledger; without it, inventory only reads.

OMH distinguishes retirement from deletion. `memory retire` is report-only unless
`--apply` is supplied, and archiving is not erasure. `memory prune --help` describes
hard-delete-local operations with record/revision and confirmation requirements;
not every record qualifies. Inspect the exact target and follow the installed
provider's lifecycle procedure. Local deletion cannot erase prior model requests,
exports or backups. Toolset does not provide a universal memory eraser.

Removing Toolset or disabling OMH leaves existing stores intact. Select an intended
replacement provider explicitly; there is no automatic migration between OMH,
Hermes built-in files or old Hindsight stores. See [removal and recovery](uninstall.md).
