# Required owner recovery cycle

This is execution inside the existing owner's scope, not permission to replace a
worker, alter product intent, take over an integration owner or bypass admission.
A cron tick is not successful progress merely because it produced a status.

## Run the executable cycle

Use the shared runner rather than assembling status JSON by hand:

```sh
python3 <autogoal>/scripts/owner_cycle.py /absolute/consumer \
  --plan SPEC.md#slice --tasks T1 \
  --state-dir "$HERMES_HOME/autogoal" --integration-owner ACTUAL_OWNER
```

Resolve the actual owning profile home first; never guess default from a named
session. Add `--apply --authority /private/owner.json` only with the existing
source-bound authority described in handoff.md. Prerequisite/candidate request
flags are forwarded to the existing recovery pipeline. The runner writes private
history, `unblock-latest.json` and a five-line `report-latest.txt` automatically,
then performs fresh canonical selection. It never invents a ledger or acceptance.

An unchanged blocker reuses one `requests/<id>.json`; the second occurrence changes
the action to owner follow-up. Supply `--proposal /private/attributed-proposal
--owner-evidence EVIDENCE_REF` when known. Requests remain local and pending:
creation is not delivery or acknowledgement. Record an actual owner's reply with
`--apply --acknowledge --integration-owner OWNER --owner-evidence REPLY_REF`.
This is explicit caller evidence, not authentication or integration permission.
New evidence is retained without duplicating the request. The auditor surfaces
pending requests; integration remains the repository owner's job.

For an already authorized handoff, pass `--apply --handoff-request /private/handoff.json`.
Its object contains canonical `consumer`, exact selected `task_id`, and `options`
using start_goal.py option names (profile, title, contract-file, source-snapshot,
base and explicitly supplied prerequisite/worker-role options). The runner calls
that helper only after fresh readiness. Native ownership, snapshot, contract and
admission checks still run there. A card handoff is QUEUED, never task completion;
failed/uncertain dispatch requires native reconciliation. Without a handoff request,
readiness does not dispatch. Without repair authority, diagnosis does not repair.

The runner's bounded work search uses the canonical selector. When no candidate
is found, inspect one accepted source/test seam as below; an empty selector does
not prove all independent work exhausted. Keep offline and live acceptance separate.

## Execute before a blocked or idle report

1. Reconcile the exact original card/run and current owner decisions. A live or
   interrupted owner keeps its task and budget. Read the canonical authority and
   source path; never restore redirected Git routing or copy foreign dirty inputs.
2. Read ledger focus and current task bodies. Bind the literal task IDs and the
   actual accepted-plan path/anchor. If consumer readiness holds, **execute**
   `scripts/owner_cycle.py /absolute/consumer --plan EXACT_PLAN --tasks EXACT_IDS
   --state-dir OWN_PROFILE_HOME/autogoal --integration-owner ACTUAL_OWNER`
   from the loaded autogoal directory. Save its actual JSON and exit status under
   this owner's `autogoal/` state; update `unblock-latest.json` only from a completed
   invocation. Do not invent command inputs or cite another profile's receipt.
3. For a recoverable body/link defect, use existing owner/decision evidence, current
   revision and immutable same-task source to supply the documented authority JSON.
   Verify no overlapping writer before `--apply --authority FILE`. Repair only the
   attributable clerical inputs; retry selection in that SAME invocation. Task status,
   scope, acceptance, ownership and product authority stay unchanged. A malformed
   acceptance marker is not a new product decision when acceptance of the exact
   scope is already evidenced; use the supported immutable-provenance repair when
   available or the bounded repo-docs metadata procedure. Never manufacture acceptance.
4. A missing consumer ledger requires integration of existing accepted owner inputs,
   not repeated `validate` calls against an absent file. Perform scoped repo-docs
   Bootstrap/Maintain under its canonical integration owner (or send an attributed
   proposal to that actual owner if it is live), then retry the consumer in this tick.
   Do not leave completed maintenance in an abandoned scratch checkout. Readiness
   failures, missing bodies, user-space tooling and ordinary engineering choices are
   internal repairs, not requests to repeat already settled user decisions.
5. With supplied snapshot/attribution, use the CLI's explicit prerequisite/candidate
   continuation. Then run normal supported admission and hand off the eligible slice,
   carrying existing commit/push authority and original-card identity. The CLI itself
   does not dispatch. Candidate validation is not native admission or implementation.

## If the preferred slice remains held

A live-owner conflict prevents edits to its inputs, not all independent work. Search
ONE accepted milestone/source/caller/test seam, record the concrete candidate and
why it is eligible or excluded, and continue a safe disjoint slice under standing
scope. Respect focused selection and repository exclusions; choose an internal
implementation approach autonomously, but do not choose an unresolved product metric,
RF window, spending, device acceptance or ownership transfer. Do not create receipt-only
or duplicate tasks, change focus without authority, or run unchanged expensive gates.

An external execution window holds that live action, not independent implementation or fixture qualification
already covered by accepted intent. If one end-to-end task mixes source work with
live-device acceptance, leave the original live task in Needs decision and book a
bounded, source-backed offline slice through the canonical integration owner when
that implementation scope is already authorized. Do not invent approval or duplicate
completed work. Keep its actual source/test acceptance separate from live qualification.
Do not make a whole milestone idle just because its final hardware check is gated.
For each blocked/idle occurrence, record the actual source/test seam inspected in
`work_search` alongside the pipeline receipt, with the candidate and precise rejection
reason or owned handoff. A statement that maintenance was evaluated is insufficient.
If every focused slice needs external authority, retain that evidence before considering
an independent already-accepted slice under the normal scoped selection rules.

`NO_CHANGE` is valid only with the actual attempted recovery result and exhausted
bounded work search, or exact live ownership preventing work. A pending interview,
empty `next`, green ledger validation or stale `draft_saved` is not that evidence.
For a genuinely held slice, name the exact failed transition, executed argv/result,
remaining input/owner, disjoint candidate searched and next executable action. Report
zero completions honestly; never change task status to avoid a zero count.

Paused jobs stay paused. Paused/chat-only scope decisions prohibit using this cycle
as a substitute scheduled writer. Unsupported main-only admission remains a real
native limit; no branch/worktree, observer-lock or inline-picker workaround.

## Cron wiring

Explicit maintainer authorization to repair schedules permits
`python scripts/wire-owner-cron.py --root DEFAULT_HOME --apply` from shared source.
The default is read-only inventory. It updates existing owner jobs with one pointer
to this cycle, preserves their original authorization/exclusions and all unrelated
configuration, and reads each target back. It creates no jobs, changes no enabled
state and launches no worker. Missing-job profiles remain visible coverage gaps.
The default auditor checks owning-profile recovery receipts read-only; it never
performs their product recovery itself.
