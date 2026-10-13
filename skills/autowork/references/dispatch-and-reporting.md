## Explicit parallel backlog requests

When the owner explicitly asks for subagents to accelerate backlog implementation,
use parallel bounded implementation contracts rather than serial audit-only passes.
This overrides the scheduled picker's single-dispatch default for that request only;
do not change recurring cadence or replace existing live workers.

1. Reconcile live ownership, dependency readiness and the accepted milestone. Select
   independently editable implementation slices; claim exact files and exclusions.
2. Assign shared contracts, generated files and dependency edits to one producer.
   Agree on interface symbols and public-control test IDs before dispatching consumers.
3. If a downstream qualification task depends on unfinished production work, delegate
   only independent executable fixture/harness preparation. Keep its dependency and
   open status intact; harness readiness is not platform qualification.
4. Give the parent integration and ledger ownership. Children return attributed changes
   and exact executed checks; the parent verifies a coherent candidate before completion.
   Compare returned file hashes to the integrated files, then run the union of affected
   test targets once with duplicates removed. Do not add child pass counts when suites
   overlap: only the combined run establishes a combined total. Use each harness's
   recorded interpreter and environment for rechecks; a bare interpreter can exercise
   different dependencies than the worker's tested environment.
   Report running work as running, not delivered, and preserve named native gaps.
   Use the integration recipe in references/handoff.md for completion reconciliation.

## Output contract

Report the primary milestone, merged user outcomes, qualification boundaries and
remaining milestone gaps, recurring failure causes and actual verification cost;
unknown usage is unknown. Card counts do not prove product progress.

### Make blockers actionable

Before reporting BLOCKED, distinguish work Autowork can repair under existing
permission from an action only the user can supply. Perform authorized internal
repairs and retry the same task; do not turn ordinary engineering decisions into
user chores. Preserve active writers, evidence and explicit live-operation limits.

For a genuine user-dependent blocker, place `Action needed from you:` immediately
after the status line. State one recommended action, its verified target, why it
is necessary, and what Autowork will resume after it. If authorization is missing,
ask for the exact bounded change, not generic permission to “proceed”. Supply a
copyable command only after verifying its path, arguments and effects; otherwise
request the missing decision or value plainly. Never include credentials.

For example, after verifying a hook rejects an otherwise authorized task branch:
`Action needed from you: authorize updating this repository's reference-transaction
hook to allow scoped commits on isolated task branches. It currently rejects the
task commit. After the change, I will retry this task's commit and request review.`
Name the verified repository/hook path in the actual report. Prefer the narrow
required repair; do not recommend disabling all safeguards or bypassing hooks.
If the user already authorized the hook change, carry out that exact authorized
change instead of asking again. If they report removing it, verify current state
and resume the original task; do not repeat an obsolete request.

When no user action is needed, omit the user-action line. Say
`Autowork next action: <specific repair/resume/check for task ID>` and perform that
step within the occurrence when possible. If a tool/runtime limitation prevents it,
name the failed operation and available recovery rather than promising execution.
A verified active worker is RUNNING, even if this occurrence repaired its admission;
report that repair under This run. Process observation alone does not prove its
initial guard, tests or commit passed. A stopped worker awaiting a concrete
intervention is BLOCKED; report the failed operation as its cause. A blocked live
qualification does not block independently authorized offline tasks.

“Resolve policy conflict”, “contact owner” and “continue verification” are not
complete unblock instructions. Each needs a specific next action and responsible
actor. Reuse one pending request while unchanged, report any new evidence, and
continue independent authorized work; do not flood the user with repeated asks.

### Required task-centered status

Every non-silent report, including cron, blocked and failed runs, uses these fields
in this order. TODO task IDs and titles are user-facing identifiers, not hidden
implementation details. Keep internal Kanban/card/run IDs and routine boilerplate
in durable receipts unless needed for diagnosis.

```text
<PROJECT / profile> — <OUTCOME>; <delivered behavior or current execution state>
Action needed from you: <only for a genuine user-dependent blocker; exact action, target, reason and what resumes>.
Task: TODO.md <ID> — <exact title> [<canonical task state or unverified>].
This run: <concrete change or none>; checks: <actual result and material failures>.
Next: TODO.md <ID> — <exact title> [eligible / blocked by <IDs or reason>]; or next eligible: none; or not evaluated.
Delivery: <commit SHA and push result, or no commit/push>. Blocker/action: <when applicable>.
```

Choose one applicable template alternative, not all alternatives verbatim.
Reporting does not change canonical task status. If evidence access fails, label
the report BLOCKED by evidence access while leaving the task state unverified.
Choose the outcome from evidence, not the cron job title or scheduler exit status:

| Outcome | Meaning |
| --- | --- |
| COMPLETED | Named TODO task acceptance and required closure gates passed, with canonical completion verified. This is task success, not whole-project completion. |
| PROGRESS | Verified partial implementation or a resolved prerequisite advanced the named task; acceptance remains incomplete. State the actual advance. |
| RUNNING | The same named task has an observed active worker; this occurrence did not complete it. |
| QUEUED | Handoff is recorded, but worker execution has not yet been observed. |
| BLOCKED | The named task cannot advance because of an unresolved dependency, failed acceptance, ownership or other concrete gate. |
| FAILED | This occurrence's attempted operation failed and its intended result was not achieved. |
| NO_CHANGE | Reconciliation found no new task progress or completion. |

If checks fail and ownership prevents further work, report BLOCKED with the failures,
not success or “verified progress.” Passing ledger validation, an isolated build,
creating a card, or observing another session's old result does not complete a TODO
task. Attribute externally observed results to their owning session; distinguish
new work this occurrence from earlier evidence. For mixed outcomes name completed
task IDs separately and retain the failed/blocked task; do not imply every task passed.

Read current canonical TODO bodies, goals.json, ownership and completion receipts
before composing the report. Count a newly reconciled worker completion when the
previous occurrence recorded that task as unfinished and current canonical state,
acceptance and required review prove it done. Attribute it to the original worker;
report COMPLETED even with no new implementation by the picker. List its TODO ID
and title as completed since the previous occurrence. Do not count the same completion again;
an old done task or delivery-only update is not another completion. Without a
trustworthy prior baseline, label the new-completion count unverified, not zero.
If the baseline proves no new completions, record **0 TODO tasks completed** in
the task-status detail. For verified partial delivery, lead with what was delivered
and report the parent as open with its remaining acceptance. Do not headline a
real delivery as zero progress or count a slice as a completed parent. See
[delivery batching](delivery-batches.md).
If completion evidence could not be read, say **completion count
unverified** rather than guessing zero. If the task is known only by ID, show that ID
and `title unverified`; if there is no verified task binding, say `Task: not identified`
and name the missing source. Never invent a title from a job label or card summary.

Select “Next” from the current canonical selector (`goals.py next <repo> --json`),
then verify its full TODO title, dependencies and live ownership. An eligible
selection is not a claim or promise of dispatch. If selection returns none, use
`Next eligible: none — <reason>` and, when evidenced, name the intended successor
as a **blocked candidate**, with its dependency IDs. If ownership prevents a fresh
selection or evidence is unavailable, report `Next: not evaluated — <reason>`;
do not present an old planned successor as ready. “All tasks complete” requires
canonical completion evidence, not merely a selector returning none.

The next action names the actual task it advances and the missing evidence or
prerequisite; “continue verification” without a task is insufficient.
“Scheduled in TODO.md” means ordered backlog work, not an active timer or worker.
Omit empty Questions sections and exhaustive skipped-check lists; preserve material
unverified acceptance and real owner questions. A queued handoff is normal asynchronous
dispatch, not failure unless dispatcher/run evidence establishes a blocker.
Questions: use the action-first request above for the one decision needed now. Offer alternatives only when they materially change the outcome; state the recommendation and the exact step waiting for the answer. Silence is not approval. Continue independent authorized work; missing preferred filenames alone do not prove that no tasks are eligible.
Nothing eligible: `Checked scope exhausted` plus inspected sources/components and evidence that considered candidates are complete, claimed, blocked, or unsupported; do not claim repository-wide completeness from a scoped search.

No skill invocation or queued card alone proves a running goal loop, Telegram delivery, scheduler activation, or completed downstream task. Record the native task ID, selected 50/100-turn budget, and observed queued/running/completed/blocked state in the durable receipt. Human-facing summaries always include verified TODO IDs and titles; native execution IDs are optional diagnostic detail. This goal worker has its own durable session; it does not set a /goal in the originating Telegram or CLI conversation.
