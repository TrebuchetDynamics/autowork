# Complete outcomes with fewer handoffs

Before preparing a worker, choose a coherent delivery batch under the current
TODO task. The coordinator decides implementation order, reversible design choices,
test selection and batch boundaries without asking for approval already granted.
The default one-card limit is a concurrency limit, not a one-file work limit.

## Choose the batch once

Read the parent acceptance criteria and a bounded dependency map. Identify the
remaining consumers, callers, runners, tests and packaging inputs needed for one
observable outcome. Include connected authorized changes together when they share
prerequisites and can be checked/reviewed as a unit. For retirement work, prefer
“remove the obsolete dependency from retained Linux journeys and runners” over
separate cards for each scenario, runner and exclusive test file. Keep required
retained behavior and its coverage explicit.

A batch is neither a file-count quota nor an unlimited rewrite. Split for a real
boundary: unresolved prerequisite, live writer conflict, different authority/live
environment, independent failure domain, or demonstrated worker-budget limit.
Record the concrete reason in the existing contract's Scope/Stop conditions; no
new approval form or mandatory planning artifact. Use the supported 50-turn default
or 100 with a Goal budget rationale when one coherent outcome needs it. Do not
reset budgets, bypass exact-file admission, or widen an active worker's contract
silently. Reconcile an active original card before changing its supported scope.

Within the admitted batch, the worker completes all named consumers, associated
fixes, focused tests and docs before the one required review handoff. A first
successful file deletion is not acceptance. Unexpected outside-scope work returns
to the coordinator for an authorized scope update or successor; preserve the
original candidate and avoid an overlapping replacement worker.

## Spend verification on changed behavior

Keep one concise remaining-work checklist in the existing TODO body or receipt.
Reuse accepted plans and source-bound review results; no fresh docs audit merely
because a cron fired. Read only changed inputs and outstanding acceptance gaps.
Run discriminating checks while implementing. Before review run the union of the
batch's affected checks once, deduplicated. Required independent review remains.

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
Do not wait for the next cron tick merely to make a routine decision. The picker
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
A shipped slice counts as a delivered slice, not a completed parent TODO. Show
parent status and remaining outcomes separately; retain verified completion counts
without making “0 parent tasks” the headline for a real delivery. Never invent a
percentage, total slice count, finish time or parent completion. No implementation,
queued, running, reviewed, integrated and pushed remain different facts.

## Resume across calls

`reconcile.py` maintains the existing `autowork/reconcile-report.json` projection
and returns `continuation` plus `changed_fields`. Resume its task/run and next
action; use current metadata for evidence links. No second task database is needed.
The projection notices run/outcome, delivery, error and event/metadata changes; it
does not monitor arbitrary source files or authenticate live ownership. Check
those before execution. Unchanged blocked evidence calls for a different supported
repair or independent work, not an identical retry or repeated broad audit.

Use `check_receipt.py run-or-reuse` with the original declared inputs, candidate,
command and qualification scope. It executes if the receipt path is new and reuses
a matching passing receipt otherwise. A stale receipt refuses execution at that
path: preserve it, identify changed inputs and run at a new receipt path. Required
independent review and repository-mandated fresh checks still run separately.
Only TERM_SESSION_ID and WINDOWID are removed from both check execution and its
fingerprint. Unknown variables, task identity, credentials and toolchain remain
bound. Old receipts may require one fresh execution; never rewrite their hashes.

Use `reconcile.py --compact` for routine calls. It omits raw metadata/events and
bounds the summary to 1,200 characters with an explicit truncation flag; omit the
flag when a decision requires the full evidence. Consecutive unchanged blocked
observations are saved in the existing projection. At two, change the supported
repair approach or pursue independent authorized work; no blind retry, new worker
overlap, claim fabrication or upstream Hermes Agent edits. These counts describe
observations, not failed execution attempts, and never reset worker retry budgets.
