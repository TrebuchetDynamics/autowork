# Repository-stage preparation

Plan, select and execute useful work at the repository’s current stage.

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
| Code exists, no useful task list | Inspect actual gaps and record a bounded task directly; use Autoresearch only for unresolved planning questions. Reconcile canonical TODO.md/goals.json through scoped repo-docs. |
| Ready tasks exist | Read their complete bodies and select accepted, dependency-ready work; skip replanning. |
| Tests/build fail | Reproduce the failure, diagnose and fix with regression coverage; ordinary engineering failures are work. |
| Task combines offline work and live qualification | Separate their acceptance; finish useful offline implementation/tests while preserving the live gate. |
| Documentation proposal exists outside canonical checkout | Reconcile and integrate it through the actual owner; do not generate another competing backlog. |
| Repeated blocker | Repair attributable inputs, follow through owner handoff, or execute independent accepted work. Escalate only the exact external input still missing. |
| Mature repo with no open task | Check one bounded source/test/user-flow seam against documented intent; implement a demonstrated gap, or report evidence that no useful authorized delta was found. |

Use `hermes-toolset:plan-for-me` subcommand `plan` for unresolved discovery questions and
`hermes-toolset:docs-sync` for canonical tasks. Planning follows
[bounded backlog planning](backlog-planning.md): at most
three useful slices, measurable checks, no invented scope or repetitive replanning.
For a new backlog, derive tasks from the user's development request and existing
project intent; record decisions as agent decisions under that scope, never a
fabricated historical user approval. Existing accepted plans and competing owners
remain authoritative. Satisfy repo-docs prerequisites rather than quietly omitting them.

For broad repository development, follow [repository maintenance](repository-maintenance.md)
whenever no runnable task remains. Discover useful docs, UI/UX, tests, refactoring
and reliability work beyond the blocked milestone; retain explicit task-only limits.
Record bounded canonical tasks and execute one in the same scheduled occurrence.

## Execute and finish a useful slice

Use the [execution engine](../SKILL.md) for native worker admission,
source-bound recovery, review, checks and commits. Read it as the execution stage
of Autowork, not a second command or an excuse to skip this preparation. Resolve
its relative helper/reference paths under `../`. Preserve native ownership,
budgets, leases and repository exceptions. Apply
[unattended continuation](owner-cycle.md) and process owner
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
