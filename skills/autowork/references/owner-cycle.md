# Direct repository execution

`owner_cycle.py` is the public entry point for card-free TODO selection and local
coordination. It does not query Kanban, invoke native handoff/review, or implicitly
change TODO/goals status. TODO.md owns product requirements; goals.json is optional.
Private receipts preserve coordination and evidence, never a second task board.

## Current session

```sh
python3 <autowork>/scripts/owner_cycle.py /absolute/repo \
  --apply --owner-pid ACTUAL_SESSION_PID
```

Without `--apply`, inspect the proposed selection. With `--apply`, bind the actual
persistent, dedicated coordinator ancestor PID and process birth identity to this repository
and workspace. Resolve it from current host process evidence; a transient shell PID
or guessed identity is not a session owner. Do not use a shared gateway/server PID that hosts concurrent sessions. The `EXECUTE` result is a contract to
execute now in the current session, not a task completion or implicit worker launch.
Release with the same live owner and `--release` after retaining candidate/check
receipts. An interrupted owner is reconciled from actual process plus workspace/Git
evidence before adoption; a stale PID or elapsed time alone proves no release.

`--profile` and `--state-dir` are optional attribution/private-storage settings;
neither requires Hermes setup for ordinary contributors. Managed profile/cron
invocations must supply both `--profile CURRENT_PROFILE` and
`--state-dir VERIFIED_PROFILE_HOME/autowork`, resolved from verified occurrence
context. This binds the active coordinator to its installation so scoped helper
updates preserve it. The runtime does not query native profile discovery or guess
profile identity. `--tasks ID1,ID2` keeps an exact named task filter;
`--plan path#heading` binds accepted context and may be used independently.
`--source-path PATH` binds existing regular check-input files; directories and missing
paths are rejected. Generic command receipts are not reusable acceptance proofs. Use
`check_receipt.py` for the separately supported source-bound acceptance reuse contract. `--scope repository` expresses
broad repository work; `--scope tasks` retains task-only scope. Check selected
scope, dependencies, acceptance and sources before implementation.

## Bounded command

```sh
python3 <autowork>/scripts/owner_cycle.py /absolute/repo \
  --apply --timeout 120 --run python3 -m unittest tests.test_example
```

`--run` accepts argv, not a shell string, and requires an explicit finite timeout.
It runs that foreground command under the shared repository lock and retains its exact
argv, executable and selected file hashes. Detached descendants are stopped at command
exit; leftover children make the result unsuccessful. This is cooperative local
process cleanup, not a hostile-code sandbox. The optional `--budget-seconds` caps
cumulative command walltime for this TODO ID; an interrupted pending receipt requires
usage reconciliation and a later tick cannot refill it.
It retains execution evidence;
it never closes the TODO task. A command-only invocation needs no persistent PID
unless recovering that owner's existing claim. This bundled runner currently requires Linux process inspection for durable ownership
and bounded descendant cleanup. Other hosts execute directly through their own
supported workspace coordination and command controls; do not invent process proof. Preserve command/session/log/final-exit evidence;
a transport interruption is not a pass and requires inspecting the original run.

## Limits and recovery

Honor explicit task/caller limits and known consumed usage; unknown usage is not
zero. The helper's timeout enforces wall time only, not provider spend, tokens or
lifetime task turns. Require the host's real enforcement for a requested cap; its
absence holds only the operation needing that cap. Read-only inspection and
already-authorized local verification/integration are separate from launching work.
A fresh occurrence never resets an exhausted allocation. No default native 100-turn
allocation or universal lifetime-task budget is created by this helper.

No old card lookup, import, release, native continuation API or same-card registration
is required. Preserve existing dirty candidates, accepted constraints and historical
failed/unchecked evidence. Inspect actual workers and file conflicts across worktrees
and profiles; coordinate different hosts and manual writers separately from advisory
local locks. Required tests, source-bound check reuse, required independent review,
serialized local integration and publication authority remain in force. Review rework
uses the current session and ordinary project review, not native card transitions.

After two unchanged holds, repair the local cause or execute independent authorized
work. An unavailable live environment does not block independent implementation or fixture qualification:
leave the original live task in Needs decision when its actual external input is missing,
and record the actual source/test seam inspected for independent work. Never claim
live acceptance from local fixtures or a selected contract.

Track a hold by its exact failed operation and bound inputs. A newly reached gate
is not another occurrence of the previous one, and an unrelated shared repair does
not clear an unchanged hold. Before retrying an old failure, compare its slice with
current integrated source: it may already be delivered by another verified path.
Keep the old failure unproved; never relabel it passed. Treat a nonzero or
interrupted mutation as possibly partially applied: read back each target before a
retry. Never probe with a knowingly invalid live mutation to learn whether it fails.

An enabled recurring job for the same repository can be mid-closeout without any
claim visible here. Before canonical integration, inspect its latest run through
the scheduler's supported run/status interface and reconcile it as a possible
writer. Do not pause or resume a schedule merely to obtain a slot.

## Cross-profile recovery and deployment

When a fix spans shared Toolset source and consumer profiles:

1. Read each original consumer's current workspace, saved continuation, remaining
   allocation and latest run. Maintenance reports are leads, not readback. Classify
   active work, pending review, approved integration, failure, pause and dependency
   hold separately.
2. Before deployment, inspect the supported updater's source selection, target
   selection and treatment of existing copies. Creating missing skills does not
   prove refresh of existing ones; remote/fleet defaults do not satisfy a
   pinned-source, named-profile scope. Without a supported route, record the exact
   capability gap; no manual overwrite presented as recovery.
3. Verify source integration, installed bytes and the consumer's next transition
   separately. Callers of shared-source absolute paths can see a source change even
   when installed copies are unchanged. Offline regressions do not prove consumer execution.
4. Under execution authority, resume the original task with its pins, evidence and
   consumed budget. A planning-only pass records steps and acceptance through Docs
   Sync instead of deploying or resuming jobs. Keep private runtime IDs and profile
   paths out of Git.
5. Report shared fix, deployment, consumer transition and product acceptance as
   separate outcomes; a reviewed shared fix is not recovery of the original task.
   Preserve paused consumers and held dependents.

## Composed ready preflight

Historical native composition and its original evidence are retained in
[historical owner cycle](historical-owner-cycle.md#composed-ready-preflight).
Those requirements are superseded by the direct execution contract above.

## Reviewed local delivery evidence

The [historical evidence contract](historical-owner-cycle.md#reviewed-local-delivery-evidence)
retains earlier receipts and qualification limits; it creates no card prerequisite
for present-day checks, review or authorized integration.
