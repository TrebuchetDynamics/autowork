# Autoresearch Plan fallback

Use this when an existing task needs substantive research or decomposition. An
empty queue first needs bounded inspection; an obvious repair can be recorded and
executed without a research protocol. First reconcile live workers
and existing results; do not wait for repeated blocked runs. Apply
[TODO work center](../../shared/TODO-WORKCENTER.md). An owner_cycle receipt may
contain `planning.action`; that receipt is optional for entering the skill and
does not execute a model. Routine acceptance clarification needs no research pass.

- `discover_repository_work`: choose independent work under repository-wide
  authority using [repository maintenance](repository-maintenance.md); the original
  task remains held. Run discovery and execution, not another blocked summary.
- `execute_ready_work`: continue the accepted task. Do not plan just to fill a quota.
- `reconcile_owner`: retain the live writer and its work; do not launch a competing planner.
- `integrate_existing_inputs`: resolve the existing documentation proposal with
  the current authorized coordinator, or use repo-docs Bootstrap if no backlog exists.
  Do not create a second proposal while canonical adoption is the missing step.
- `repair_execution_inputs` / `recover_first`: repair the named prerequisite using
  existing authority; research cannot grant permission or repair routing.
- `reuse`: read the bound prior receipt and act on its integration/execution outcome.
  Do not repeat the plan against identical inputs.
- `plan`: prepare the bounded task in this occurrence. Use the research pass below
  only for unresolved questions; direct evidence and a clear repair need no protocol.

These decisions cover the bound task, not the entire repository. For a broad
development request with no runnable task, use [repository maintenance](repository-maintenance.md)
to inspect a different authorized component even when this task remains held.
Do not duplicate its unchanged plan or evade a shared integration conflict.

## One bounded pass

1. If there is a triggering owner-cycle JSON, save its immutable history receipt.
   Otherwise record the current repository revision, TODO/goals state and planning
   reason in a new or reused research receipt at the authorized research location;
   do not fabricate a cycle or task ID.
   Then load `hermes-toolset:autoresearch` with
   `Selected subcommand: plan` and read its `upstream/plan.md`. This is skill
   execution in the current agent, not a shell command or a new scheduled job.
2. Bind Goal to the accepted milestone or an evidence-backed maintenance outcome
   under broad repository authorization; Scope to its unfinished code,
   callers and tests; Verify to concrete acceptance checks. Inspect existing
   tasks, worktrees and receipts before proposing work. Use available planning,
   diagnosis and documentation skills through the shared engineering-cycle matrix.
   Resolve ordinary implementation choices autonomously. Missing product intent
   remains one precise question, not invented acceptance.
3. Produce at most three useful slices. Each has an existing or proposed task ID,
   accepted source, concrete unfinished behavior, bounded changes, dependencies,
   owner, exact verification command and observable pass condition. A suspected
   defect gets a reproduction task before a fix; no claim that inspection reproduced it.
   Separate offline implementation/regression acceptance from live qualification.
   Keep live gates on their own task. Do not remove real dependencies or duplicate
   already implemented work to increase task counts.
4. Load repo-docs narrow Maintain with these findings. Reuse tasks before adding
   them; write full bodies in canonical TODO.md and reconcile goals.json under the
   current authorized coordinator. Reconcile user TODO orders before rendering.
   Respect Graphify requirements, actual live writers and source-bound revision
   guards. Do not require external owner acknowledgement for ordinary local work.
   If a real concurrent writer prevents integration, preserve its work and record
   `integration_pending`; continue independent authorized work.
   Never call a detached draft an executable backlog.
5. Validate and retry the canonical consumer in this same occurrence. If ready,
   continue ordinary native handoff under the original implementation authority.
   Otherwise name the exact missing input and its owner. Report planning as
   planning, not a completed TODO task or product implementation.
6. When an actual cycle snapshot exists, record the completed pass against it:
   For a receipt-free entry, retain the research receipt and saved task IDs instead
   of invoking the cycle recorder with invented inputs.

```sh
python3 <autowork>/scripts/backlog_plan.py record \
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
