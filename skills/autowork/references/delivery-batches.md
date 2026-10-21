# Complete outcomes with fewer handoffs

Before implementation, choose a coherent delivery batch under the current
task. The coordinator decides implementation order, reversible design choices,
test selection and batch boundaries without asking for approval already granted.
The default one-slice limit is an outcome limit, not a one-file work limit.

## Choose the batch once

Read the parent acceptance criteria and a bounded dependency map. Identify the
remaining consumers, callers, runners, tests and packaging inputs needed for one
observable outcome. Include connected authorized changes together when they share
prerequisites and can be checked/reviewed as a unit. For retirement work, prefer
“remove the obsolete dependency from retained Linux journeys and runners” over
separate tasks for each scenario, runner and exclusive test file. Keep required
retained behavior and its coverage explicit.

A batch is neither a file-count quota nor an unlimited rewrite. Split for a real
boundary: unresolved prerequisite, live writer conflict, different authority/live
environment, independent failure domain, or demonstrated worker-budget limit.
Record the concrete reason in the existing contract's Scope/Stop conditions; no
new approval form or mandatory planning artifact. Honor explicit task/caller allocations and real host limits. Do not
reset budgets, bypass actual writer exclusion, or widen an active worker's contract
silently. Inspect actual process/workspace activity before changing delegated scope.

Within the admitted batch, the worker completes all named consumers, associated
fixes, focused tests and docs before the one required review handoff. A first
successful file deletion is not acceptance. Unexpected outside-scope work returns
to the coordinator for an authorized scope update or successor; preserve the
original candidate and avoid an overlapping replacement worker.

## Spend verification on changed behavior

Keep one concise remaining-work checklist in the existing task record's notes or receipt:
`Required outcome | remaining code/tests | acceptance evidence | batch or split reason`.
Separate optional hardening from required acceptance. A guard-only batch must name
the acceptance failure it repairs and the product change it unlocks. After it passes,
resume that change; do not grow a chain of precautionary guard tasks. New evidence
of a real regression still requires repair. Optional improvements go to Next without
becoming new blockers for already accepted scope.
Reuse accepted plans and source-bound review results; no fresh docs audit merely
because a cron fired. Read only changed inputs and outstanding acceptance gaps.
Run discriminating checks while implementing. Before review run the union of the
batch's affected checks once, deduplicated. Required independent review remains.
Read the whole mandatory gate (self-tests, fixture stages) before the first full
run and group evidenced fixture repairs into one batch, not one defect per run.
Compare executed commands with every required check before claiming offline
acceptance; a green nearest suite does not cover omitted targets. Match evidence
to the named public control: a direct internal call does not prove the UI path,
including cancel/dismissal callbacks. A conflict-free merge assessment is
preparation, not integrated or tested behavior.

After approval, verify commit identity, owned blobs, ancestry and the integration
diff. Reuse approved exact-source checks only when source, tests, dependency and
environment inputs match and repository policy allows it. Run integration-specific
checks, changed-input checks and any mandatory canonical gate. Changed inputs
invalidate affected evidence; uncertainty calls for a check, not assumed reuse.
Do not add overlapping test counts or equate receipt validation with product tests.

## Continue delivery

Reconcile newly approved work and finish authorized local integration before
starting another audit. Recompute remaining parent acceptance and prepare the next
coherent batch in the same occurrence when the slot is free and budget permits.
Do not wait for the next cron tick merely to make a routine decision.
When reporting active work or pending review, inspect actual process/workspace and review evidence
immediately before returning the waiting report. Reuse it if already taken at this
final boundary; elapsed drafting time alone can make the initial readback stale. A newly terminal result returns to closeout now:
verify exact review approval, reuse still-valid check receipts, integrate and publish
under existing authority, then select the next batch. This is one final readback,
not a polling loop, fresh history scan or test rerun. If still active, report it and
return. If the occurrence budget expires, save the exact closeout step and reason;
do not silently treat it as completed or replenish worker budgets.
The picker
may return after verified asynchronous handoff; do not busy-poll or invent a
background continuation. Reuse existing terminal notifications/continuations;
never create another schedule, resume a paused job, or replace a live worker.

If two successive deliveries leave the same parent open, assess the remaining work
once: combine connected eligible leftovers, or state the concrete split boundary.
Do not repeatedly dispatch file-sized fragments by habit. This is an agent policy,
not a scheduler guarantee or measured throughput improvement.

## Describe real progress

Lead with delivered behavior and its verified commit/integration/publication stage.
Example: “Delivered: Linux journeys no longer require the retired transport.
Parent TASK-ID remains open: service and packaging removal still pending.”
A shipped slice counts as a delivered slice, not a completed parent task. Show
parent status and remaining outcomes separately; retain verified completion counts
without making “0 parent tasks” the headline for a real delivery. Never invent a
percentage, total slice count, finish time or parent completion. No implementation,
queued, running, reviewed, integrated and pushed remain different facts.

## Resume across calls

Keep the actual task/session, source/candidate and next action in existing private
receipts. Resume from current process/workspace and review evidence. These receipts
are not a task database or proof of liveness. Unchanged blocked evidence calls for
a different supported repair or independent work, not an identical retry or broad audit.

Use `check_receipt.py run-or-reuse` with the original declared inputs, candidate,
command and qualification scope. It executes if the receipt path is new and reuses
a matching passing receipt otherwise. A stale receipt refuses execution at that
path: preserve it, identify changed inputs and run at a new receipt path. Required
independent review and repository-mandated fresh checks still run separately.
Only TERM_SESSION_ID and WINDOWID are removed from both check execution and its
fingerprint. Unknown variables, task identity, credentials and toolchain remain
bound. Old receipts may require one fresh execution; never rewrite their hashes.

At two unchanged observations, change the supported repair approach or pursue
independent authorized work; no blind retry, overlapping writer, claim fabrication
or upstream Hermes Agent edits. Never reset explicit allocations to continue.

A pending integration remains actionable even when report evidence is unchanged.
Perform the missing verification/integration step, or record the exact failed
command or missing input and retry condition. No new guard/planning task just to
postpone closeout. A pending independent review cannot be treated as approval.
