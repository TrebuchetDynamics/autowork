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

Turn remaining accepted gaps into goals and tasks in `tasks/`, the repository's only
task store, through `autowork tasks`: `goal ID --title --source path#anchor
--priority N` for goals, `add --goal G --title T --short S` with `--scope`,
`--acceptance`, `--checks`, `--touches` and `--depends-on` for tasks, `field ID
LABEL VALUE` for other typed fields or notes (such as `Sources`), `place` and `move`
for section and rank, `supersede --by OTHER --reason` to retire a task and `done
--evidence` to close one without the engine. Give each executable task its
`Touches:` paths (widen when unsure, or set `resources` to `exclusive` with a
reason) so parallel Autowork can run tasks together. Keep Now/Next/Needs decision
distinct; priority is section, then rank. Only typed fields (`ownership`,
`resources`, `live`) grant authority; live authorization is the owner's to grant.
Preserve existing IDs, completed work, holds and priorities; never manufacture work.

Each `autowork tasks` write changes only the working tree, never commits, refuses a
file changed since it was read and validates the whole store. Finish with
`autowork tasks validate --worktree .`; `list`, `show` and `why` read the committed
store. Never write TODO.md or goals.json; a repository that still has them waits for
the owner's `autowork migrate`. An existing `TODO.archive.md` is frozen, read-only
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
