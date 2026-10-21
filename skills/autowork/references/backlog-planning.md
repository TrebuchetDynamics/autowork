# Automatic Plan For Me recovery

Autowork invokes `autowork:plan-for-me` only for a consequential unresolved
choice or missing decomposition that prevents execution. Routine debugging,
candidate drift with a known recovery, missing fixtures and reversible approach
changes stay in execution; difficulty alone does not require another plan.
The user need not send `/plan_for_me` or approve in-scope planning again. Reconcile
actual live writers, then execute the saved next action. If new evidence requires
a material decision, run one bounded planning pass in this occurrence and resume.
A ready task needs no planning ceremony.
Apply [TODO work center](../../shared/TODO-WORKCENTER.md). A `planning.action`
receipt directs the agent; it does not execute the skill or prove progress.

## Preparation stalls

For an isolated base missing local dependencies, inspect the exact diff and its
callers. Classify each prerequisite as committed and usable, attributable and
authorized, explicitly excluded (including no-commit), actively changing, or
unverified. Choose a supported route: use a verified committed base, finish an
authorized prerequisite, reduce the slice to independent useful behavior, or
select another eligible task within the requested scope. Recheck changed files
before handoff; do not freeze a stale candidate or silently drop acceptance.
Never import forbidden/foreign edits or remove a genuine dependency to force admission.

For a named task family, keep planning and execution within that family and its
necessary authorized prerequisites. Broader maintenance needs broader authority.
Save decisions, task bodies, dependency order and exact blockers in canonical
TODO.md/goals.json through Docs Sync, then retry selection and handoff immediately.
Continue under the original execution request; do not end with “plan ready—run
Autowork?” or ask the user to invoke the planner. If no route exists, identify the
single precise missing input or restriction to change and what it would enable.
Repeated unchanged inputs resume the saved plan's next action, not another plan.

- `discover_repository_work`: choose independent work under repository-wide
  authority using [repository maintenance](repository-maintenance.md); the original
  task remains held. Run discovery and execution, not another blocked summary.
- `execute_ready_work`: continue the accepted task. Do not plan just to fill a quota.
- `prepare_execution_handoff`: the accepted task or verified ready fallback only
  needs its contract, base and snapshot. Prepare them directly; no research pass
  is required. Reconcile a saved failure receipt before retrying the same inputs.
- `reconcile_owner`: retain the live writer and its work; do not launch a competing planner.
- `integrate_existing_inputs`: resolve the existing documentation proposal with
  the current authorized coordinator, or use docs-sync Bootstrap if no backlog exists.
  Do not create a second proposal while canonical adoption is the missing step.
- `repair_execution_inputs` / `recover_first`: repair the named prerequisite using
  existing authority; research cannot grant permission or repair routing.
- `reuse`: read the bound prior receipt and act on its integration/execution outcome.
  Do not repeat the plan against identical inputs.
- `plan`: execute Plan For Me using the bounded pass below, reconcile tasks and
  retry execution in this occurrence. The helper returning `plan` is not execution.

These decisions cover the bound task, not the entire repository. For a broad
development request with no runnable task, use [repository maintenance](repository-maintenance.md)
to inspect a different authorized component even when this task remains held.
Do not duplicate its unchanged plan or evade a shared integration conflict.

## One bounded pass

1. If there is a triggering owner-cycle JSON, save its immutable history receipt.
   Otherwise record the current repository revision, TODO/goals state and planning
   reason in a new or reused research receipt at the authorized research location;
   do not fabricate a cycle or task ID.
   Then load `autowork:plan-for-me` with
   `Selected subcommand: plan` and follow its link to the pinned
   [plan protocol](../../autoresearch/upstream/plan.md). This is skill
   execution in the current agent, not a shell command or a new scheduled job.
2. Bind Goal to the accepted milestone or an evidence-backed maintenance outcome
   under broad repository authorization; Scope to its unfinished code,
   callers and tests; Verify to concrete acceptance checks. Inspect existing
   tasks, worktrees and receipts before proposing work. Existing planning instructions
   normally suffice. For a concrete method gap or explicit protocol request, select
   one technique through [engineering](../../engineering/SKILL.md); consult
   [the engineering cycle](../../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
   Resolve ordinary implementation choices autonomously. Missing product intent
   remains one precise question, not invented acceptance.
3. Produce at most three useful slices. Each has an existing or proposed task ID,
   accepted source, concrete unfinished behavior, bounded changes, dependencies,
   owner, exact verification command and observable pass condition. A suspected
   defect gets a reproduction task before a fix; no claim that inspection reproduced it.
   Separate offline implementation/regression acceptance from live qualification.
   Keep live gates on their own task. Do not remove real dependencies or duplicate
   already implemented work to increase task counts.
4. Load docs-sync narrow Maintain with these findings. Reuse tasks before adding
   them; write full bodies in canonical TODO.md and reconcile goals.json under the
   current authorized coordinator. Reconcile user TODO orders before rendering.
   Respect Graphify requirements, actual live writers and source-bound revision
   guards. Do not require external owner acknowledgement for ordinary local work.
   If a real concurrent writer prevents integration, preserve its work and record
   `integration_pending`; continue independent authorized work.
   Never call a detached draft an executable backlog.
5. Validate and retry the canonical consumer in this same occurrence. If ready,
   continue current-session implementation under the original implementation authority.
   Otherwise name the exact missing input and its owner. Report planning as
   planning, not a completed TODO task or product implementation.
6. When an actual cycle snapshot exists, record the completed pass against it:
   For a receipt-free entry, retain the research receipt and saved task IDs instead
   of invoking the cycle recorder with invented inputs.

```sh
python3 <toolset>/pi-autowork/engine/backlog_plan.py record \
  --cycle /private/original-cycle.json --state-dir /private/profile/autowork \
  --evidence /private/planning-findings.json --outcome canonical_reconciled
```

Other outcomes are `integration_pending` or `no_supported_delta`. The evidence
must describe what actually ran and which checks did not. Failed/interrupted work
is not a completed pass: preserve partial evidence and resume it rather than
inventing a completion receipt. The input key excludes tick count and timestamps;
changed bound consumer inputs permit a new pass, unchanged inputs reuse this one.

## Final occurrence report

Task completed: actual TODO ID/title or none. Checks: executed command/results.
Commit: attributable SHA or none; publication separately. Next: selected task
ID/title or exact blocker/owner. Include a short planning outcome only when a pass
changed the backlog or found a new blocker. Never substitute the planner or
readiness helper's status for the worker's actual result.
