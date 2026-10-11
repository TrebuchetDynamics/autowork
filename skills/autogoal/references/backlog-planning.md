# Autoresearch Plan fallback

Use this only after owner recovery, when no accepted ready work remains. The
owner_cycle receipt contains `planning.action`; it does not execute a model.

- `execute_ready_work`: continue the accepted task. Do not plan just to fill a quota.
- `reconcile_owner`: retain the live writer and its work; do not launch a competing planner.
- `integrate_existing_inputs`: resolve the existing documentation proposal with
  its integration owner, or use authorized repo-docs Bootstrap if no backlog exists.
  Do not create a second proposal while canonical adoption is the missing step.
- `repair_execution_inputs` / `recover_first`: repair the named prerequisite using
  existing authority; research cannot grant permission or repair routing.
- `reuse`: read the bound prior receipt and act on its integration/execution outcome.
  Do not repeat the plan against identical inputs.
- `plan`: execute the bounded pass below in this occurrence.

## One bounded pass

1. Save the triggering owner-cycle JSON as a private immutable per-pass input
   (use its history receipt), then load `hermes-toolset:autoresearch` with
   `Selected subcommand: plan` and read its `upstream/plan.md`. This is skill
   execution in the current agent, not a shell command or a new scheduled job.
2. Bind Goal to the already accepted milestone; Scope to its unfinished code,
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
   actual integration owner. Respect Graphify requirements, current leases and
   source-bound revision guards. If another owner must integrate, route one
   attributed request with the planning receipt; record `integration_pending`.
   Never call a detached draft an executable backlog.
5. Validate and retry the canonical consumer in this same occurrence. If ready,
   continue ordinary native handoff under the original implementation authority.
   Otherwise name the exact missing input and its owner. Report planning as
   planning, not a completed TODO task or product implementation.
6. Record the completed pass against its original cycle snapshot:

```sh
python3 <autogoal>/scripts/backlog_plan.py record \
  --cycle /private/original-cycle.json --state-dir /private/profile/autogoal \
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
