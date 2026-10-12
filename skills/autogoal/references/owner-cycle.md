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
history, `unblock-latest.json` and a compact `report-latest.txt` automatically,
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

## Unattended continuation contract

At the beginning of every authorized owner occurrence, read this profile's
`autogoal/inbox/` with `progress_runtime.py inbox --state-dir OWN_HOME/autogoal`.
Reconcile each request against the actual consumer and current ownership. An inbox
item is a request, never permission to take another worker's task. Acknowledge it
with `progress_runtime.py reply --state-dir OWN_HOME/autogoal --request-id ID
--owner EXACT_OWNER --status acknowledged --evidence ACTUAL_RECEIPT`. Perform
already authorized integration/repair, then reply `resolved` with the actual
commit/check receipt, or `blocked` with the one missing input. The requesting
profile retries readiness next occurrence; a resolution claim alone cannot close it.
No new schedule, worker or external message is created by the mailbox helper.

The agent establishes these private continuation files from **existing** evidence;
the user should not have to wire them manually:

- `recovery-authority.json`: the existing exact authority schema from handoff.md.
  With `--apply`, owner_cycle automatically uses it if no explicit authority is
  supplied. Current revision, accepted scope and no-overlapping-writer checks still
  apply. Never refresh stale authority blindly or infer acceptance from a cron tick.
- `owner-route.json`: `{ "consumer": "/canonical/repo", "owner": "actual-owner",
  "state_dir": "/actual/owner/home/autogoal" }`. Resolve the actual owner from
  existing ownership/session evidence first. With `--apply`, the runner delivers
  one request into that inbox and polls its matching outbox. Delivery, acknowledgement,
  reported resolution and verified resolution are separate states. An unknown owner
  becomes one precise escalation; never guess a sibling profile or send to all.
- `handoff-requests/TASK_ID.json`: the already authorized, task-bound native handoff
  payload above. With `--apply`, a ready task uses this automatically. Native
  admission still checks the current source, contract and ownership.

Use `--allow-ready-fallback` for normal milestone-wide autogoal scope, including
scheduled runs. Omit it when the user restricts work to literal task IDs. It can
select an already accepted, ready task in the same milestone while retaining the
original held task and blocker. It never changes focus, releases live qualification,
steals ownership or dispatches without an exact handoff payload.

Maintain a **target of three** small ready tasks from accepted scope. The runner
reports the validated queue and shortfall. When short, perform one bounded repo-docs
Maintain pass under the existing integration owner: split remaining implementation,
offline regression tests and live qualification into distinct acceptance criteria.
Preserve the live task and its gate; create an offline task only for demonstrably
unfinished accepted work with explicit sources, dependencies and checks. Reuse an
existing task if it already covers that work. Do not create duplicate tasks, empty
commits, arbitrary features or fabricate scope merely to reach three. If the accepted
scope has fewer useful tasks, report the actual shortfall and reason.

After repeated blockage, choose an action in this order: attributable repair;
resume/reconcile the actual owner; hand off an independent ready task; route the
missing input to its actual owner; escalate one unresolved input when routing or
resolution is impossible. A pending request is not an excuse to skip available work.
Do not repeat unchanged broad audits. Inspect new owner replies before repeating
checks; preserve pause and no-live-operation instructions.

The runner report is a **readiness receipt**, not the final cron result. After
worker reconciliation, produce the occurrence report from actual native and Git
receipts: completed TODO IDs and titles; checks and results; owned commit SHA and
publication state; next task ID/title; exact remaining blocker and owner. Count a
task only when its acceptance and required review passed. Count clerical repairs,
queue creation and handoff as separate progress, never implementation completion.
A commit alone does not prove completion, and the runner's zero completed tasks
must not overwrite a worker's verified completion in the same occurrence.

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
   Explicit named-task diagnosis runs even when the task is in Needs decision or
   has unmet dependencies. Repairing its documented contract does not release that
   execution gate. If diagnosis exposes an attributable repair, use the existing
   recovery authority and retry; do not replace an available repair with another
   pending follow-up request. Report repairs separately from task completions.
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

Follow the receipt's `planning.action` through [Autoresearch Plan fallback](backlog-planning.md).
A recorded plan is reused until bound inputs change. Missing canonical adoption
routes to the integration owner before any new planning proposal.


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

## Eligible task with no execution handoff

`backlog_ready: true` establishes selection only. `PREPARATION_REQUIRED` means
no same-task handoff is available; the cycle retains missing execution inputs
and routes a deduplicated `handoff_preparation` request through the bound owner
inbox. It exits nonzero and does not resolve existing requests merely because
the task became eligible. Autoresearch must not replan this ready task.

Continue preparation in this occurrence: assemble the explicit contract, pinned
base and source snapshot. If accepted inputs are dirty but already attributable
under existing authority, use `prepare_prerequisites.py` and its real checks;
no renewed permission is needed for that authorized preparation. Preserve foreign
bytes and ownership. If attribution is genuinely absent, follow the actual owner
request and report the exact missing input; a profile name is not attribution.
Save the supported request under `handoff-requests/<task-id>.json` and rerun the
cycle with `--apply`; saved requests are consumed by the existing native helper.
Report execution only after observing its worker, and completion only after its
acceptance and commit receipts. A routed request alone does not unblock a task.
