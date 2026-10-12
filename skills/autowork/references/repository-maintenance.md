# Repository maintenance when the queue cannot run

A broad request to develop or maintain this repository includes discovering and
executing ordinary documentation, UI/UX, tests, refactoring and reliability work.
Scheduled Autowork must use this path when recovery leaves no runnable task. A
blocked milestone is not the boundary of the whole repository's maintenance work.
Explicit task-only scope, pauses, excluded directories and live-operation limits
still win. Do not interpret a task-specific recovery failure as a repository-wide
prohibition; equally, do not silently override a genuine repository-wide hold.

## Select, discover, execute

1. Reconcile running workers and completed results; prefer an existing ready task.
   Repair attributable paperwork once and retry selection. Preserve the blocked
   task and its exact dependencies. Do not spend the whole occurrence repeating
   the same repair or waiting for a reply that has not arrived.
2. If no task can run, read the last `work_search` receipt and inspect one or two
   unexamined, authorized components. Use current source, callers, tests, user
   flows and documentation as evidence. Choose a useful area outside the held
   milestone when the job has broad repository scope. An owner of one slice does
   not own every disjoint component; check actual file and integration ownership.
3. Consider these sources of useful work, without requiring a task in each:
   - Documentation: broken setup steps, stale API examples, missing explanations
     of implemented behavior. Validate against source or a safe command/link check.
   - UI/UX/accessibility: an existing user flow with confusing states, broken
     navigation, missing keyboard access or poor error feedback. Inspect the real
     interface and applicable design requirements; verify the changed flow when
     tools permit. Screenshot-free source inspection is not visual acceptance.
   - Tests/reliability: a reproducible defect or an important uncovered contract;
     use a focused failing reproduction and a bounded fix.
   - Refactoring: demonstrated duplication, coupling or repeated change friction
     with concrete call sites. Preserve behavior with suitable characterization
     checks. Large files alone are not a reason to rewrite them.
   - Performance/developer tooling: a measured bottleneck or a broken local/CI
     workflow. Identify the observable before/after result.
4. For nontrivial decomposition, run one bounded Autoresearch Plan pass over the
   chosen component, then repo-docs Maintain (Bootstrap only if truly absent).
   A `planning.action` of `reuse`, `integrate_existing_inputs` or
   `repair_execution_inputs` describes the original task, not coverage of all
   maintenance areas. Reuse that task's evidence while exploring a distinct seam;
   never run the same planner again on identical scope/evidence. Do not bypass a
   global canonical-ledger or integration-owner conflict by creating a second one.
5. Reuse existing tasks before adding at most three evidence-backed tasks to
   canonical TODO.md and its goals.json ledger. Each needs source evidence, user
   benefit, bounded files, dependencies, ownership, acceptance and checks. Record
   new decisions as agent decisions under the current repository-development
   request, not as historical user approvals. Missing supporting tools get bounded
   setup under existing authority; disclose a genuine unavailable prerequisite.
6. Retry selection and execute one eligible slice in this same occurrence through
   the normal native handoff. Preserve the primary milestone and record why its
   runnable slices cannot proceed before choosing independent maintenance. Supply
   the engine's source-bound fallback evidence when required; discovery does not
   waive admission. Finish checks, owned commit and already-authorized delivery.
   Up to three ready tasks is a replenishment target, never a quota for busywork.

## Keep discovery moving

Use the existing profile-local journal's `work_search` receipt, not a second task
ledger. Record repository, authorization source, category/component, checked
paths and scoped fingerprints, actual findings, candidate IDs, rejection reasons,
chosen task and next unexamined component. Do not call a generated task complete.
On the next idle occurrence choose an unexamined relevant seam; revisit an exhausted
one only when its evidence changed. Unchanged HEAD is insufficient for a dirty tree.
Do not rotate categories mechanically when a stronger concrete problem is known.

After a bounded search finds no useful eligible delta, state which scope was
checked and the precise remaining hold. Follow existing quiet/no-change scheduling
policy; never promise perpetual changes or fabricate work to avoid a zero count.
When every disjoint candidate shares a real missing input, escalate that one input
with its owner instead of producing another broad audit. Planning, repaired metadata
and queued workers remain separate from completed TODO tasks in the final report.
