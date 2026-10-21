---
name: engineering
description: "Use for a specific engineering method or Addy protocol."
version: 0.1.0
license: MIT
---

# Engineering protocols for Hermes

Apply the pinned Addy Osmani protocols to the current repository task. This adapter
controls host integration; upstream files retain their MIT license, with two
documented defensive-example adaptations. Read [provenance](UPSTREAM.json) for the exact revision and file hashes.
No external import, separate agent harness or upstream hook installation is needed.

## Select one technique when needed

Use for a concrete method gap or explicit protocol request. Zero protocols is valid for a clear
task with sufficient repository instructions and checks. Autowork owns scope,
authorization, task state, review and completion. These protocols supply techniques
within that contract. Upstream lifecycle instructions do not add planning artifacts,
human approval checkpoints, review lanes or publication authority. Preserve explicit
user methods, repository requirements and all required acceptance checks.

Select exactly one protocol and verify its pinned hash and shared reference hashes:

```sh
python3 "<engineering-skill-dir>/scripts/route.py" --protocol performance-optimization
```

Read the returned protocol and relevant supporting references.

The adapter also carries toolset-written protocols under `local/`, versioned with this
repository rather than pinned, selected only with `--protocol` and never in a phase
bundle: [test-suite-optimization](local/test-suite-optimization/PROTOCOL.md) defines
minimum sufficient regression protection for slow, redundant or low-signal tests.
Default to audit of the named/current repository; read-only saves nothing. Explicit
apply or existing implementation authority permits a bounded verified batch without
another approval ceremony. Preserve risk-to-oracle mappings, named bug traceability
and required gates; use proportional evidence and disclose unknowns, not count targets.
Apply the [test budget](../shared/ENGINEERING-CYCLE.md#test-budget), including justified
unique-risk exceptions. If the method is unclear, consult the menu in
[engineering cycle](../shared/ENGINEERING-CYCLE.md).
Stop when the gap is resolved; do not load every protocol or invent a skill quota.

### Optional phase bundles

Request a phase bundle only when several methods are needed. Existing phase
commands remain supported; `--domain` adds to that bundle. `--protocol` cannot be
combined with a phase or `--domain`.

| Phase | Protocols |
| --- | --- |
| plan | planning-and-task-breakdown, documentation-and-adrs |
| implement | incremental-implementation, test-driven-development for behavior changes |
| debug | debugging-and-error-recovery, test-driven-development |
| review | code-review-and-quality |
| document | documentation-and-adrs |
| deliver | git-workflow-and-versioning |

```sh
python3 "<engineering-skill-dir>/scripts/route.py" plan
python3 "<engineering-skill-dir>/scripts/route.py" implement --domain frontend-ui-engineering
```

Omit an inapplicable technique (for example TDD for a prose-only correction). Test-first
work uses the [test budget](../shared/ENGINEERING-CYCLE.md#test-budget): start with
one discriminating regression where sufficient; review extra cases for distinct risks.
Upstream advice to add tests does not justify duplicates or waive safety obligations.

This vendored pack is the default source for Addy methods, including when a profile
has no external imports. Existing native imports are preserved but do not take
precedence merely because their bare names match. An explicit user-selected source
wins; identify its revision and disclose missing support. If a host scanner blocks
a protocol, honor that decision and use a disclosed safe fallback; vendoring is not
permission to bypass a scanner or execution restriction.

## Resolve supporting files in the snapshot

The upstream tree preserves `skills/<name>/` and root `references/` relationships.
Only filenames `SKILL.md` are renamed `PROTOCOL.md` to prevent duplicate host
registration; content adaptations and original hashes are recorded in UPSTREAM.json. For upstream links ending in SKILL.md,
use the corresponding PROTOCOL.md in this snapshot. `../../references/...` is
relative to the selected protocol's folder. Upstream support-document references
under `references/`, `skills/`, `docs/`, `agents/` and `commands/` resolve within
this adapter's `upstream/` root. Artifact/output paths (such as `docs/decisions/`)
always belong to the target repository and reuse its existing document owners.
Preserve normal document-relative links otherwise. Read referenced
checklists when relevant; never claim missing material was consulted.

Use this adapter through `autowork:engineering` or its verified installed
path. Other upstream skills are protocol files, not separately registered Hermes
commands. Analytical personas are not actual subagents unless separate agents ran.
Do not execute upstream host integration commands or install hooks from examples.

## Adapt artifacts and authority

Apply the [work center](../shared/TODO-WORKCENTER.md). The repository's `tasks/`
store is the one work queue, edited through `autowork tasks`. Map upstream
`tasks/todo.md` and `tasks/plan.md` onto existing task records in `tasks/items/` and
linked plans;
never create a competing backlog or duplicate task IDs. Reuse accepted specs,
quality requirements and decisions. Docs Sync reconciles documentation; planning
saves tasks;
Autoresearch performs bounded research/planning; Autowork remains the executor.

Carry existing user authorization through phases. Routine engineering choices and
an agent-written plan do not require another approval. Ask only for a material
missing product decision or authority beyond the existing request; continue
independent authorized work. Read-only/no-write requests change no files.
Planning-only writes accepted planning artifacts, not product implementation.
Upstream automatic commits/ship steps use Autowork's owned-file completion/review
path and actual publication authority; no implicit push, deployment or live action.
Keep repository-specific tests, active-writer protection and genuine review gates.

## Record application, not just selection

For a technique that materially changes a decision or artifact, record in the
existing task record (as a note), supporting receipt or worker handoff:

`Skill application: <trigger>; <protocol path>@<pinned revision>; <decision or changed artifact>; <executed check/result or NOT_CHECKED>.`

Planning receipts accompany the task into execution; workers add implementation,
debugging and review evidence as needed. A router response, loaded file or list of
skill names is not application or task completion. Finish with task IDs, artifacts,
checks and next action; follow Autowork's task status/reporting contract.
