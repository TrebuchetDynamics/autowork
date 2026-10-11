---
name: autowork
description: "Develop a repository at any stage: understand intent, plan useful work, maintain tasks, implement, verify and commit. Use for autonomous repository progress, including empty or missing backlogs."
version: 0.1.0
license: MIT
---

# Autowork

Take the specified repository forward. Plan when needed, read or create actionable
tasks, execute useful work, verify it and report the next step. `/autogoal` is the
compatibility command for this workflow. Existing helper paths, private `autogoal/`
state, job IDs and native goal workers remain compatible; do not migrate or reset them.

## Bind the job

Use the supplied repository, otherwise the session's verified project directory.
Read its instructions, current source, docs, tasks, dirty files and worker ownership.
Preserve the user's latest scope, pauses, no-push/no-deploy restrictions and existing
work. A broad request to develop this repository authorizes ordinary reversible
engineering choices; missing task paperwork is not a request for renewed permission.
Resolve conventions, implementation details and local tooling autonomously.

If purpose is genuinely absent, ask one concrete question about the intended product
while continuing independent inspection and setup. Do not invent a product, credentials,
live acceptance or ownership. Lack of a detailed spec is not itself a blocker when
purpose and a useful bounded outcome are already clear.

## Choose the repository's next useful stage

| Observed state | Work to do now |
| --- | --- |
| Empty/scaffold repo with known purpose | Inspect tooling, define the smallest working vertical slice and its acceptance, scaffold and implement it. |
| Code exists, no useful task list | Inspect actual gaps, run one bounded Autoresearch Plan pass, then repo-docs Bootstrap/Maintain into canonical TODO.md/goals.json. |
| Ready tasks exist | Read their complete bodies and select accepted, dependency-ready work; skip replanning. |
| Tests/build fail | Reproduce the failure, diagnose and fix with regression coverage; ordinary engineering failures are work. |
| Task combines offline work and live qualification | Separate their acceptance; finish useful offline implementation/tests while preserving the live gate. |
| Documentation proposal exists outside canonical checkout | Reconcile and integrate it through the actual owner; do not generate another competing backlog. |
| Repeated blocker | Repair attributable inputs, follow through owner handoff, or execute independent accepted work. Escalate only the exact external input still missing. |
| Mature repo with no open task | Check one bounded source/test/user-flow seam against documented intent; implement a demonstrated gap, or report evidence that no useful authorized delta was found. |

Use `hermes-toolset:autoresearch` subcommand `plan` for bounded discovery and
`hermes-toolset:repo-docs` for canonical tasks. Planning follows
[bounded backlog planning](../autogoal/references/backlog-planning.md): at most
three useful slices, measurable checks, no invented scope or repetitive replanning.
For a new backlog, derive tasks from the user's development request and existing
project intent; record decisions as agent decisions under that scope, never a
fabricated historical user approval. Existing accepted plans and competing owners
remain authoritative. Satisfy repo-docs prerequisites rather than quietly omitting them.

## Execute and finish a useful slice

Use the [execution engine](../autogoal/SKILL.md) for native worker admission,
source-bound recovery, review, checks and commits. Read it as the execution stage
of Autowork, not a second command or an excuse to skip this preparation. Resolve
its relative helper/reference paths under `../autogoal/`. Preserve native ownership,
budgets, leases and repository exceptions. Apply
[unattended continuation](../autogoal/references/owner-cycle.md) and process owner
inbox replies before repeating an unchanged blockage.

Default: prepare and execute one bounded useful slice (or hand it to the existing
native worker), then identify the next task. An explicitly authorized whole-spec
request uses the engine's whole-spec execution mode. Existing scheduled occurrences
continue this loop; invoking Autowork never creates a recurring job by itself.
Planning, queue creation or a readiness receipt alone is not a completed development
slice. Continue from planning through canonical admission to supported execution
in the same occurrence when the required inputs are available.

Commit completed owned work after relevant checks and required review. Push only
under existing explicit publication authority. Do not steal an active task, overwrite
foreign changes, bypass protected integration, deploy or perform live operations
merely to avoid a zero count. A real external hold applies to that action; it does
not stop disjoint authorized work. Never create busywork or empty commits.

## Report actual results

State: COMPLETED, IN_PROGRESS, BLOCKED or NO_CHANGE, supported by evidence.
Task: actual TODO ID/title (or the newly established task). Changed: concrete result.
Checks: executed results and material omissions. Delivery: owned commit SHA and
push state, or none. Next: task ID/title and eligibility, or exact blocker/owner.
A queued worker is IN_PROGRESS with execution unverified, not a completed task.
Keep planning/recovery progress separate from completed-task counts. Do not claim
that every repository can progress when purpose, authority or external inputs are absent.
