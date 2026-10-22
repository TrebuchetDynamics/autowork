---
name: docs-sync
description: "Create or maintain source-backed project documentation and the tasks/ work queue."
disable-model-invocation: true
---

# Docs Sync

Read the [host contract](../COMMON.md) and use the shared
[document scaffold](../../../skills/docs-sync/references/document-scaffold.md).
Bare invocation bootstraps missing applicable roles and updates supported drift;
scoped requests change only affected owners. Audit/read-only changes no files.
Reuse paths and combine roles for small repos; never generate empty documentation.

Inspect source/tests for current behavior and accepted requirements for intent.
Separate current architecture from planned changes. Maintain README, requirements,
architecture/spec, test plan, runbook and changelog as applicable; add conditional
roles only when useful. Fix supported doc issues now.

Before task work, run `autowork capabilities`: it must succeed, list `tasks` with
`prepare`, and report `prepare_api` 2 or higher. If not, the installed CLI is older
than this skill: report `TOOLCHAIN_MISMATCH` (executable, what is missing, fix:
`autowork update` when the owner allows installing, then reload the host), keep to
document work, and never fall back to editing TODO.md or goals.json.

Then run `autowork tasks prepare .` in the consumer repository (Audit: `--check`,
which writes nothing; without commit authority: `--no-commit`) and act on its
`outcome`: `READY`, `MIGRATED` (converted a TODO.md + goals.json repository now),
`NO_STORE`, `MIGRATION_DEFERRED` (work in flight: the request is recorded and the
repository's runner drains and converts it; report pending, not done),
`MIGRATION_BLOCKED` (report the named refusal), `INVALID_STORE` or
`ACTIVATION_PENDING` (the running runner's release cannot read `tasks/`; the owner
restarts it). When the owner's request says `force` (`/docs_sync force`), run
`autowork tasks prepare --force .` instead (needs `prepare_api` 3): it converts now,
stopping the service, live workers and other lease holders, setting every attempt aside
with its work kept, and committing the owner's planning edits; report what it stopped
and set aside. Force never discards work or data; report a `MIGRATION_BLOCKED` it still
returns rather than deleting anything. Its `state` is `none` for a new repository (bootstrap goals
from its `accepted` headings only, else report the missing intent and create no
queue), and its `diagnostics` name defects with the `autowork tasks` command that
repairs each: repair only from accepted evidence, never grant ownership, `live` or
resources, never close work to silence one, and leave `IN_FLIGHT` contracts alone.

Turn remaining accepted gaps into goals and tasks in `tasks/`, the repository's only
task store, through `autowork tasks`: `goal ID --title --source path#anchor
--priority N` for goals, `add --goal G --title T --short S` with `--scope`,
`--acceptance`, `--checks`, `--touches` and `--depends-on` for tasks, `field ID
LABEL VALUE` for other typed fields or notes (such as `Sources`), `place` and `move`
for section and rank, `supersede --by OTHER --reason` to retire a task and `done ID
--by WHO --reason TEXT [--evidence REF]` to close any task kind manually. Manual
closure records actor, timestamp and reason, never a receipt or verification claim.
Meeting a goal or satisfying a `verified_depends_on` prerequisite needs coordinator
verification or an explicit owner `owner_waiver`/`owner_qualification` record (set
through `field`, naming authority, criterion and evidence); never invent one.
Ordinary dependencies are unaffected. CLI/fleet views and scorecard counts keep
Manual distinct from Verified. Give each executable task its
`touches` (widen when unsure, or set `resources` to `exclusive` with a
reason) so parallel Autowork can run tasks together. Keep Now/Next/Needs decision
distinct; priority is section, then rank. Only typed fields (`ownership`,
`resources`, `live`) grant authority; live authorization is the owner's to grant.
Preserve existing IDs, completed work, holds and priorities; never manufacture work.

For any prose containing quotes, backticks, `$` (including `$(...)` and `$VAR`)
or newlines, write one UTF-8 JSON object with a file-writing tool and use
`autowork tasks add --json task.json`, `autowork tasks field ID --json field.json`,
or `autowork tasks goal ID --json goal.json` from the consumer repository.
Use `--json - < task.json` for stdin, never interpolated shell arguments, `echo`
or an unquoted heredoc. Keys mirror options with underscores; lists take arrays.
Field input is `{"label": "scope", "value": "text"}` (an array for `acceptance`).
Add's `notes`, or field label `notes`, is the complete literal Markdown body:
read and retain Sources, holds and other notes before replacing it. Do not mix
JSON with value flags or label/value arguments. See the
[literal input reference](../../../pi-autowork/task-store.md#literal-prose-input---json)
for keys and types; all validation and `--expect REV` guards still apply.

Each `autowork tasks` write changes only the working tree, never commits, takes the
task lock, refuses a file changed since it was read (or since `--expect REV`, the
`record_revision` of `show ID --worktree`) and validates the whole store; `add`
refuses a duplicate title under the same goal. Finish with `autowork tasks validate
--worktree .` and `autowork tasks prepare .` again (an unchanged repository reports
the same result); `list`, `show` and `why` read the committed store. Never write
TODO.md or goals.json. An existing `TODO.archive.md` is frozen, read-only
history ([frozen archive](../../../skills/docs-sync/references/todo-archive.md)).
Do not create a second tracker. Use source inspection for routine edits; graph tools
only when available and useful or explicitly required. Check links, commands and
statuses. With a [role manifest](../../../skills/docs-sync/references/document-scaffold.md#optional-role-manifest),
also run the bundled `docs.py stale <repo>` and `docs.py check <repo>` and keep it synchronized.
Its optional repository-type `profile` sets which roles are baseline.

The scaffold's parent-skill references describe document roles, not permission to
start Hermes coordination. Use this adapter for execution rules. Keep actual external
inputs in BLOCKERS.md; internal engineering work belongs in tasks. Saving docs does
not authorize implementation, commit, push, scheduling or host configuration changes.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Unchanged findings need
no new docs pass. Follow this host adapter for execution authority; the shared
contract does not require Hermes-native tooling on this host.
