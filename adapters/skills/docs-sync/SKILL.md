---
name: docs-sync
description: "Create or maintain source-backed project documentation and the central TODO.md work queue."
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
roles only when useful. Fix supported doc issues now. Turn remaining accepted gaps
into bounded TODO.md tasks with ID, outcome, sources, scope/exclusions, acceptance,
dependencies and ownership. Keep Now/Next/Needs decision distinct. Preserve existing
IDs, completed work, active writers and priorities; never manufacture work.

Automatically move verified completed bodies out of TODO.md into `TODO.archive.md`
during writing passes, preserving an existing archive owner. Use the bundled goals
helper's `archive <repo>` command; `render` also archives closed ledger-done tasks.
Reconcile checkbox/Status and ledger completion first. Without goals.json, verify
completion checks and call `archive <repo> --verified-tasks ID1,ID2` with the closed
IDs. Preserve whole entries and ledger evidence; report retained conflicts. Apply
the [archive contract](../../../skills/docs-sync/references/todo-archive.md).

If goals.json exists, synchronize it using the bundled
[goals helper](../../../skills/docs-sync/scripts/goals.py): inspect `--help`, then
fmt/validate/render with the absolute repository path. Its rendering does not create
full task bodies. Do not create a second tracker when the repository already has an
authoritative equivalent. Use source inspection for routine edits; graph tools only
when available and useful or explicitly required. Check links, commands and statuses.
With a [role manifest](../../../skills/docs-sync/references/document-scaffold.md#optional-role-manifest),
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
