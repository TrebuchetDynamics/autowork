# Autonomous recovery cycle

## Default: no external owner required

Autowork is the local planner, implementer, reviewer and integrator. It does not
need an owner profile, parent-session reply, release acknowledgement or mailbox
route to perform already authorized repository work. This default takes precedence
over the owner-handoff requirements later in this compatibility reference.
Recorded `ACTIVE` claims and owner names are attribution and discovery evidence,
not indefinite approval gates. Selection retains them as `recorded_claims`.

Before adopting existing work, inspect current native workers and actual file
conflicts. A genuinely running overlapping worker must finish or be coordinated;
otherwise preserve its candidate, review the changes and tests, and continue or
integrate the bounded local work yourself. Dirty files, an old claim or an idle
parent session alone do not require someone's release. Do not overwrite unrelated
changes. Use a fresh isolated candidate and serialize canonical integration when
necessary. Keep actual dependencies, test failures and explicit external-action
limits; do not mark work complete until verified.

When canonical documents or ordinary execution inputs are missing, repair or
bootstrap them from accepted scope in the same occurrence. Supply your own
attribution and exact source/revision evidence for the existing repair APIs; their
`owner` field identifies the executor, not a person whose approval is required.
Prepare native worker contracts in default `worker` mode. Use `proposal` mode and
external handoffs only when the user explicitly requests that division of work.

`owner_cycle.py` defaults to `coordination_mode=autonomous`, never creates owner
requests, and returns local repair/preparation actions. Existing route files do not
turn owner gating back on. The agent must execute those actions, not report the
helper's readiness receipt as completed work. To explicitly request the legacy
external-owner workflow, pass `--require-owner` to the cycle or selector; the
owner-request, inbox and registry-release instructions below apply to that opt-in.
No new schedule, publication authority or live-operation permission is implied.

## Composed ready preflight

The normal ready command is `owner_cycle.py REPO --profile PROFILE --state-dir
PRIVATE_STATE --apply --source-path FILE ...`. It selects the accepted ready
body itself, or accepts `--plan path#heading --tasks TASK` for a named slice.
No separate contract-writing, capture or validate-only invocation is required.
Prior native work is reconciled first; pending review, interrupted/owned cards and
unintegrated candidates keep their original lane. Missing handoff continuity is
not proof of missing ownership: real admission still checks live cards under lock.

`ready_preflight.py` reuses docs-sync's task parser and bounded source capture.
The body must contain Scope, Acceptance, Checks, Sources and Ownership; the
canonical ledger must already be normalized. Explicit `--source-path` files bind
the task's code/docs/tests/dependency closure. Accepted local links, governing
TODO/ledger/plan, instructions and registry are also captured, within the existing
32-file/byte/path/credential boundaries. Source hashes must match the original
accepted selection. HEAD is captured as a full immutable base unless `--base` is
explicit. Contract fields retain source/base/ownership, checks, budget and stops;
no optional routing loader, planning/docs audit or suite runs before handoff.

Exactly one real `start_goal.py` call owns native profile/cwd, ownership,
dependency/focus/authority, freshness, immutable assembly and readback checks.
Only a verified new handoff updates the canonical task to `in_progress` through
the goals helper; it never closes the task, changes focus or claims qualification.
`--ledger-mode proposal --integration-owner OWNER`, `--fallback-file` and
`--pass-root` are explicit native options, not inferred authority. Attributed
prerequisite/candidate recovery retains the manual request interface below.

The owner-cycle lock and private `ready-preflights/TASK/preparation.json` preserve
base, artifact hashes, original options and unknown usage. A dispatch marker is
saved before the call: timeout/interruption/refusal never licenses another call,
new card, refreshed evidence or budget reset. If interrupted before dispatch,
unchanged hashed preparation is reused; changed sources/options/artifacts refuse.
Missing inputs return only the named preparation, not a planning detour. Repair
post-dispatch bookkeeping or notification on the original card, not by repeating
admission. Full evidence stays in history and `unblock-latest.json`; routine output
is compact, with `--verbose` for private diagnostics. These are offline-composed
paths, not provider/model/Telegram qualification or measured startup savings.

## Document admission is actionable work

Before invoking recovery with `--apply`, read the saved continuation and any retained
operation receipt. Bind the actual plan path/anchor and consumer's current reasons;
a prior wrong source is not a reason to repeat or abandon the same operation blindly.
Resume its supported next action when inputs permit, preserving uncertain dispatch.

A `draft_saved` result means document validation failed, not that no useful work
exists. Repair the exact reported metadata/body/link errors through narrow Docs Sync
before searching for unrelated product defects: legacy task bodies can block the
entire backlog, including any new candidate. Use Plan For Me only for genuinely
missing decomposition or evidence. An absent Sources field may be reconstructed
from the task's existing accepted goal source; never invent scope or acceptance.
Preserve conflicting intent and ask for that precise decision only when necessary.
Retry the real consumer after the repair in the same occurrence. `ACTION_REQUIRED`
is an instruction to act, not a completed recovery or sufficient stopping condition.
When unresolved, report the exact reason strings, affected task/document, attempted
repair and missing evidence; “document admission pending” alone is not actionable.

## Native runtime limits stay operation-scoped

Saved handoff IDs restore registration consistency, not authenticated worker
identity or authority for claim-protected operations. Keep shell ownership
scrubbing intact; never export identity, infer a lease from a workspace path, or
use caller-supplied IDs to impersonate a worker. Use protected native lifecycle
tools only through their actual authenticated context.

If that context is unavailable, preserve the original card/history and record the
exact affected operation. Continue supported coordinator-side preparation,
reviewed-candidate integration and independent authorized offline work in isolated
registered workspaces. Check an accepted named fallback against its own goal's
frontier and retain the normal source-bound milestone fallback and live-ownership
gates. A held native operation is not a profile-wide BLOCKED verdict. Coordinator
CLI controls use coordinator authority; they do not authenticate a worker.

Respect a source restriction: inability to extend one runtime route does not
license Hermes Agent edits, tunneling commands through unrelated tools, or another
core-edit-or-stop ultimatum. Report the unavailable route separately from actual
implementation and remaining acceptance.

## Reviewed local delivery evidence

Protected-PR provenance remains the delivery evaluator's default. For a repository
that explicitly permits reviewed local integration, the coordinator may pass a
separate trusted JSON file via `reconcile.py --repo REPO --local-policy FILE`, or
`owner_cycle.py --local-policy FILE` on its composed ready path. Never load this
authority from worker metadata or infer it from a green check, ancestry or a card
marked done. This selects an explicit policy; invalid policy cannot fall back to
protected-PR claims. The evaluator reads Git only and grants no mutation authority.

The policy object requires `version: 1`, `mode: reviewed_local`, the complete
exact `candidate` identity (including base, tree and prerequisites),
`target: refs/heads/main`, a nonempty `authority` evidence reference,
`implementer` and a nonempty unique `reviewers` list excluding the implementer.
Reconciliation additionally requires the original `task_id` and integer `run_id`
of the latest owning-profile run; `implementer` must match that profile.

The existing integration object binds the same candidate/target, `action: merge`,
`before` equal to the candidate base and an observed `after`. Its provenance has
exactly `source: reviewed_local`, the same `authority`, `observed: true` and
`review`. That review binds the complete candidate, matching `implementer`, an
allowed independent `reviewer`, a nonempty review `id`, `observed: true` and
`outcome: approved`. Retain independently observed exact-candidate review before
integration. These are caller attestations, not issuer authentication: the trusted
coordinator must verify authority and review through their original evidence.
Fabricating matching strings is not verification, and fixtures remain fixtures.

Local Git must show the candidate introduced by fast-forward or a two-parent merge
whose parents are exactly before/candidate and whose tree is exactly the reviewed
candidate tree. The default evaluator (`historical=False`) requires current local
main to equal after: this strict current-target check remains separate from
historical readback. Read-only reconciliation explicitly uses `historical=True`;
its `integration_evaluation: historical` and `historically locally integrated`
result verify the original event while allowing main to advance with either an
unchanged or changed tree, provided after remains in main ancestry. Reset/divergent
main, moved candidate/prerequisite refs, malformed original topology and forged
provenance still refuse. No original candidate, policy, review or check is repinned.

Owner-cycle retains that source-bound reconciliation result and may continue fresh
eligible selection after verified historical closeout, without repeating the old
merge. The result grants no new integration, admission or publication authority;
the next handoff still checks current source, ownership and target independently.
Missing, foreign, stale, contradictory or PR-shaped local provenance remains
unknown. Required exact-candidate
check receipts still gate delivery. This closes only the scoped local delivery lane;
`publication` remains unknown, milestone completion remains false, and native,
model, live acceptance, sessions, retry limits and unknown usage remain separate.
The coordinator, not this read-only evaluator or worker, owns integration and
canonical task closure.

## Continuation and accounting failures

An existing card with partial work and a session/budget failure needs execution
recovery, not another product plan. Read its saved continuation, current card,
latest run status/end time and accounting evidence before choosing an action.
A card still marked running, todo or ready with a terminated latest run is inconsistent state,
not proof of a live worker. `reconcile_run_state` requires checking the original
run/process and supported lifecycle controls before resuming; it never authorizes
a duplicate worker. Preserve consumed turns/cost, retry counts and uncertain charges.
A saved receipt does not grant native claim identity or reset exhausted capacity.
If verified usage exhausts the allocation, the missing input is additional budget,
not implementation permission. Report allocation, consumed usage, any unknown usage
and the specific additional allocation needed on the original card. Do not treat
history restoration or a new per-turn max as cumulative enforcement.

For a cached `no_supported_delta`, the helper returns `resolve_recorded_blocker`,
including its evidence and exact outcome. Read that evidence and resolve the failed
operation, or identify the precise unavailable control/input. Do not pretend there
is a saved repair, repeat unchanged planning, or stop at “I will refine the plan”.
Invalid/mismatched planning receipts return `inspect_planning_receipt`; preserve them
and reconstruct from actual state rather than treating them as successful or absent.
Use independent authorized work when this operation cannot proceed, while retaining
its card and budget. A different product idea does not repair native accounting.

## Scheduled execution and explicit planning requests

Treat an already authorized Autowork cron as execution. A separate explicit `plan`
conversation remains planning-only; it neither grants new implementation authority
nor revokes the job's standing scope. Honor explicit pauses and no-write limits.
Re-read native review state instead of repeating a prior occurrence's pending-review
report. Gate and integrate the exact approved offline candidate, then continue eligible
selection. Report partial reviewed/integrated slices separately from full TODO or live
acceptance; an open combined task does not mean no implementation occurred.

## Run the executable cycle

Use the shared runner rather than assembling status JSON by hand:

```sh
python3 <autowork>/scripts/owner_cycle.py /absolute/consumer \
  --plan SPEC.md#slice --tasks T1 \
  --state-dir "$HERMES_HOME/autowork"
```

Resolve the actual owning profile home first; never guess default from a named
session. Add `--apply --authority /private/owner.json` only with the existing
source-bound authority described in handoff.md. Prerequisite/candidate request
flags are forwarded to the existing recovery pipeline. The runner writes private
history, `unblock-latest.json` and a compact `report-latest.txt` automatically,
then performs fresh canonical selection. It never invents a ledger or acceptance.

Only in optional `--require-owner` mode, an unchanged blocker reuses one
`requests/<id>.json`; the second occurrence changes
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
base and explicitly supplied prerequisite/worker-role options). Omit `goal-max-turns`
to inherit the helper's 100-turn default and default rationale; explicit 50 remains
supported, while explicit 100 requires a nonempty contract rationale. Existing
cards retain their limits, cumulative usage and sessions; no automatic retry/reset.
The runner calls
that helper only after fresh readiness. Native ownership, snapshot, contract and
admission checks still run there. A card handoff is QUEUED, never task completion;
failed/uncertain dispatch requires native reconciliation. Without a handoff request,
readiness does not dispatch. Without repair authority, diagnosis does not repair.

The runner's bounded work search uses the canonical selector. When no candidate
is found, inspect one accepted source/test seam as below; an empty selector does
not prove all independent work exhausted. Keep offline and live acceptance separate.

## Optional external-owner continuation (`--require-owner`)

At the beginning of every authorized owner occurrence, read this profile's
`autowork/inbox/` with `progress_runtime.py inbox --state-dir OWN_HOME/autowork`.
Reconcile each request against the actual consumer and current ownership. An inbox
item is a request, never permission to take another worker's task. Acknowledge it
with `progress_runtime.py reply --state-dir OWN_HOME/autowork --request-id ID
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
  "state_dir": "/actual/owner/home/autowork" }`. Resolve the actual owner from
  existing ownership/session evidence first. With `--apply`, the runner delivers
  one request into that inbox and polls its matching outbox. Delivery, acknowledgement,
  reported resolution and verified resolution are separate states. An unknown owner
  becomes one precise escalation; never guess a sibling profile or send to all.
- `handoff-requests/TASK_ID.json`: the already authorized, task-bound native handoff
  payload above. With `--apply`, a ready task uses this automatically. Native
  admission still checks the current source, contract and ownership.

Use `--allow-ready-fallback` for normal milestone-wide autowork scope, including
scheduled runs. Omit it when the user restricts work to literal task IDs. It can
select an already accepted, ready task in the same milestone while retaining the
original held task and blocker. It never changes focus, releases live qualification,
steals ownership or dispatches without an exact handoff payload.

Maintain a **target of three** small ready tasks from accepted scope. The runner
reports the validated queue and shortfall. When short, perform one bounded docs-sync
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
   --state-dir OWN_PROFILE_HOME/autowork --integration-owner ACTUAL_OWNER`
   from the loaded autowork directory. Save its actual JSON and exit status under
   this owner's `autowork/` state; update `unblock-latest.json` only from a completed
   invocation. Do not invent command inputs or cite another profile's receipt.
3. For a recoverable body/link defect, use existing owner/decision evidence, current
   revision and immutable same-task source to supply the documented authority JSON.
   Verify no overlapping writer before `--apply --authority FILE`. Repair only the
   attributable clerical inputs; retry selection in that SAME invocation. Task status,
   scope, acceptance, ownership and product authority stay unchanged. A malformed
   acceptance marker is not a new product decision when acceptance of the exact
   scope is already evidenced; use the supported immutable-provenance repair when
   available or the bounded docs-sync metadata procedure. Never manufacture acceptance.
   Explicit named-task diagnosis runs even when the task is in Needs decision or
   has unmet dependencies. Repairing its documented contract does not release that
   execution gate. If diagnosis exposes an attributable repair, use the existing
   recovery authority and retry; do not replace an available repair with another
   pending follow-up request. Report repairs separately from task completions.
4. A missing consumer ledger requires integration of existing accepted owner inputs,
   not repeated `validate` calls against an absent file. Perform scoped docs-sync
   Bootstrap/Maintain under its canonical integration owner (or send an attributed
   proposal to that actual owner if it is live), then retry the consumer in this tick.
   Do not leave completed maintenance in an abandoned scratch checkout. Readiness
   failures, missing bodies, user-space tooling and ordinary engineering choices are
   internal repairs, not requests to repeat already settled user decisions.
5. With supplied snapshot/attribution, use the CLI's explicit prerequisite/candidate
   continuation. Then run normal supported admission and hand off the eligible slice,
   carrying existing commit/push authority and original-card identity. The CLI itself
   does not dispatch. Candidate validation is not native admission or implementation.

## Registered claims and independent candidates

In optional `--require-owner` mode, an `open` ledger checkbox does not establish that a task is unclaimed. Selection
reads `docs/coordination/worktree-registry.jsonl` when present, using the latest
entry for each task/workspace. Unreleased claims remain held, including reviewed
candidates; only explicit `RELEASED` or `INTEGRATED` entries end that registry hold.
Other registry formats still require the repository's own ownership checks.
Never release a claim merely because its writer is old, idle or dirty.

For repository-wide work, a held slice automatically triggers a read-only search
across dependency-ready tasks. Read `work_search.candidates` in the owner-cycle
receipt, or run `retry_selection.py /canonical/repo --repository-frontier`.
For each candidate, check actual file-scope overlap and current ownership; then
prepare its contract and source snapshot in this occurrence. If
`requires_fallback_attestation` is true, supply the existing native structured
fallback evidence for why focused tasks cannot run, using `fallback-file` in the
handoff request. Rerun the cycle with the candidate's exact plan and task ID.
Do not change milestone focus, reset claims, or treat this search as completion.
A rejected candidate lists concrete contract gaps to repair under existing authority.
An empty focused queue does not mean there are no repository-wide candidates.

## If the preferred slice remains held

For broad repository development pass `--scope repository`; for explicit named-task
work retain `--scope tasks`. A `discover_repository_work` action requires the current
agent to choose and execute independent maintenance through
[repository maintenance](repository-maintenance.md), not return the helper receipt.
Follow the receipt's `planning.action` through [Autoresearch Plan fallback](backlog-planning.md).
A recorded plan is reused until bound inputs change. Missing canonical adoption
routes to the integration owner before any new planning proposal.


A live-owner conflict prevents edits to its inputs, not all independent work. Search
a bounded set of relevant source/caller/test or documentation/UX seams under
repository scope (a single milestone seam for task-only scope), record the concrete candidate and
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
The default is read-only inventory. It makes `hermes-toolset:autowork` the primary
attached skill, replacing legacy Autogoal bindings while retaining extra skills.
A prompt mention alone is not migration; verify both `skills` and legacy `skill`
readback, then repeat inventory to prove idempotency. Retain established continuity
state; changing the entry skill does not reset workers or receipts. Default audit
keeps its read-only product scope even with Autowork attached.
It updates existing owner jobs with one pointer
to this cycle, preserves their original authorization/exclusions and all unrelated
configuration, and reads each target back. It creates no jobs, changes no enabled
state and launches no worker. Missing-job profiles remain visible coverage gaps.
The default auditor checks owning-profile recovery receipts read-only; it never
performs their product recovery itself.

## Eligible task with no execution handoff

`backlog_ready: true` establishes selection only. `PREPARATION_REQUIRED` means
no same-task handoff is available; the cycle retains missing execution inputs
and returns `prepare_execution_handoff` in autonomous mode. Only explicit owner
mode routes a deduplicated request through the bound owner inbox. It exits nonzero
and does not resolve existing requests merely because
the task became eligible. Autoresearch must not replan this ready task.

Continue preparation in this occurrence: assemble the explicit contract, pinned
base and source snapshot. In proposal ledger mode, the handoff automatically freezes admitted planning
files as read-only context; do not wait for those files to be committed. If executable
source prerequisites are dirty but already attributable
under existing authority, use `prepare_prerequisites.py` and its real checks;
no renewed permission is needed for that authorized preparation. Preserve foreign
bytes and ownership. If attribution is genuinely absent, follow the actual owner
request and report the exact missing input; a profile name is not attribution.
Save the supported request under `handoff-requests/<task-id>.json` and rerun the
cycle with `--apply`; saved requests are consumed by the existing native helper.
Report execution only after observing its worker, and completion only after its
acceptance and commit receipts. A routed request alone does not unblock a task.

A persisted native goal card with `notification_blocked` still has a recorded
handoff. The cycle returns `QUEUED` with `notification_warning`; reconcile that
original card and repair its transport separately. Do not rerun admission to fix
a Telegram notification. Missing card identity or an uncertain/failed native call
still requires reconciliation and is never reported as successful dispatch.


## A profile mailbox is not its parent session

An owner route may bind `target_session` when repository integration belongs to a
specific parent conversation. Carry that ID into the request and inbox; replies
must include the observed replying `session_id` matching it. A sibling cron in the
same profile must not answer for that parent. Session fields are caller-supplied
binding evidence, not authentication or a transfer of integration authority.

`delivery.state=delivered` means a local mailbox file was published. Check
`session_wakeup`: `not_attempted` does not establish that the parent ran or saw the
request. Do not describe a self-written blocked reply as an owner decision. Use a
supported, authorized wake of the existing parent session when available; retain
its actual routing/session identity and confirm acknowledgement separately. If the
host provides no such transport, report that exact missing transition once rather
than another unchanged validation loop. Never resume a different session or adopt
parent-only integration authority just because both sessions use one profile.

A missing canonical backlog with an existing owned proposal needs integration,
not another discovery pass or replacement goals.json. Surface the exact proposed
files, current owner and parent-only repository rule. An explicit owner grant may
permit reviewed integration; absence of an active session lease alone does not.

## Original-card continuation capability

`continuation_capability.py` is a compatibility boundary, with no installed native
binding. Reconciliation reports `unavailable`; owner recovery retains that exact
blocker for continuation-held cards and does not replace their dispatch. This
report does not prevent already-authorized verification or integration of completed
work. It is not a probe that launches a worker.

The installed Hermes source inspected at revision `6a2662a4aa` exposes an initial
`--goal-max-turns` in `hermes_cli/kanban_parser.py`. Its `unblock` parser and
`hermes_cli/kanban.py::_cmd_unblock` take no remaining cap or original-session
selector. `hermes_cli/kanban_db.py::unblock_task` handles blocked/scheduled cards;
`edit_task` changes descriptive/recovery fields, not a cumulative allocation or a
done-to-implementation transition. These read-only observations do not establish
complete original accounting or a safe continuation operation. No upstream source
was changed. New runtime support needs explicit integration and qualification.

### Explicit native adapter contract

A trusted host integration may call `assess(identity, runtime,
original_allocation=allocation, rework=False)` for a fresh report, or `resume` with
the same arguments for **one** atomic native call. Neither accepts executable
commands, imports, callback paths or capability declarations from worker metadata.
There is no CLI flag that enables a fictional native implementation.

The caller supplies the preserved original allocation `{amount: integer, unit:
actual_runtime_unit}` and exact board, card, profile, original session, allocation
and expected claim identity. A later invocation cannot supply a larger allocation;
the runtime must retain its immutable original record as well. Counts of assistant
messages cannot be converted into goal iterations. This version supports exact
nonnegative integer accounting; other accounting types require a separately
validated native binding.

The runtime object provides these three operations:

- `capabilities()` returns version `1` with true `accounting`, `atomic_continue`,
  `cumulative_cap`, `compare_and_swap`, `idempotent`, `same_session` and
  `retry_rework_cap`. Explicit rework also requires `completed_rework`. These are
  guarantees of trusted integration code, not authentication by a Boolean field.
- `read_accounting(identity)` returns authoritative `identity`, nonempty `revision`,
  `status`, `claim_active`, immutable original `allocation`, `complete`,
  `unknown_charges`, ordered complete `attempt_ids`, and matching `attempts`.
  Each attempt has an ID, original session ID, exact allocation unit and consumed
  count. Completeness must include interrupted/retried/review work and outstanding
  charges. The adapter refuses incomplete, mixed-unit, changed-identity, active or
  exhausted observations. It cannot authenticate a fabricated accounting provider.
- `continue_atomic(request)` atomically compares the **entire** `expected` snapshot
  (identity, claim activity, status, revision, original allocation and history),
  enforces `remaining_cap` in `unit`, and continues the original card/session.
  `operation` is `continue` or explicit `rework`; `request_id` is deterministic for
  the expected state and operation. Native enforcement must persist across every
  retry, interruption and review-rework attempt, preserve original history and
  deduplicate repeated requests. It must reject changed claims/accounting. The
  helper's subtraction is validation, never the enforcement mechanism.

An accepted native receipt must echo the request ID, exact identity, unit and cap.
A native refusal stays refused. A timeout or malformed receipt is `unverified`,
requires fresh native readback and never retries automatically. `accepted` reports
native admission only, not completed implementation, review, integration or live
qualification. The adapter stores no replenishable local budget.

The stateful native double in `test_continuation_capability.py` exercises the
supported contract and missing-control refusals, including interruption after a
native commit and changed claims at the atomic boundary. These are offline
contract tests. The external prerequisite remains a supported installed runtime
operation plus authoritative original task accounting; neither passing fixtures
nor an experimental budget-controller receipt supplies it.
