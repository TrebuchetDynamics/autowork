# Accepted plan handoff

Keep ideas and unanswered decisions in their existing documentation owner until
accepted. An accepted plan section names its status (`Status: Accepted`), scope,
acceptance and sources. Preserve existing task/goal IDs and completed history.
Repo-docs reconciles accepted work into `goals.json` and complete `TODO.md` task
bodies; rendered goal coverage alone is not an executable task.

## One planning pass, one handoff

Plan With Me owns missing user decisions. Plan For Me owns bounded investigation
and engineering choices. Docs Sync owns persistence. Autowork owns execution and
closeout. These are responsibilities within the same conversation, not mandatory
separate agents or repeated startup passes. Do not chain all four for a ready task.

Resume from the current TODO task, accepted section and saved findings. Read only
relevant changes since that evidence: scope/decisions, source and tests, dependencies,
repository instructions and task state. A new invocation alone invalidates nothing.
Do not ask settled questions, regenerate accepted plans or run a broad docs/graph
pass to rediscover the same facts. If freshness cannot be established, inspect the
specific uncertain inputs; do not assume unchanged HEAD covers dirty files.

Use the existing task body or planning receipt for a compact continuation:
- task IDs and canonical plan section;
- decided scope/exclusions, remaining material questions and their affected tasks;
- evidence paths and source revision/file fingerprints where available;
- changed documents, exact checks/results and their input bindings;
- next executable action and any genuine retry condition.
No new mandatory file, duplicate tracker or ceremonial approval form. Explicit
answers and delegated engineering choices carry forward. Proposals remain proposed;
never infer acceptance from silence or label an entire draft accepted from one answer.

Investigate only the uncertainty preventing the next action. Stop when evidence
supports a choice within authorized scope and observable acceptance/checks can be
written. Do not run experiments, interview the user or compare more alternatives
when conventions and current evidence already answer the question. Preserve a
material unknown only on its dependent tasks; independent accepted work stays ready.

Persist one coherent batch through narrow Docs Sync, not a pass per finding or
skill transition. During a long interview, save meaningful decisions for continuity,
without running the full ledger pipeline after each answer. If no findings, intent,
implementation or task inputs changed, reuse the saved handoff; do not render,
rewrite dates, duplicate tasks or create an empty planning commit.

After actual doc/task changes, run the applicable formatter, validator, renderer,
links and consumer check once on the final batch. Carry their exact results into
the next stage. Repeat only checks invalidated by changed inputs, failed evidence
or repository-required fresh checks. A cached readiness result is never native
admission: Autowork still checks current source, ownership and candidate before
dispatch. Report stale receipts honestly rather than repinning them.

Standalone planning remains planning-only. When Autowork invoked planning under
existing implementation authority, return the resolved decision and ready task to
that same coordinator in the same occurrence. Do not ask “implement now?”, start
a second planning cycle, or spawn a competing worker. Genuine product decisions
or external authority remain explicit; choose routine reversible details yourself.

Resolve `goals.py` from the sibling repo-docs skill as described in the
[shared contract](COMMON-CONTRACT.md). Use its supported mutations and validate
and render the canonical ledger; preserve concurrency/revision guards. Check the
actual consumer with `backlog-check <repo> --plan path#heading --tasks T1,T2`.
Report its JSON state and exit: `draft_saved` (1),
`backlog_reconciled_not_eligible` (2), or `ready_for_autowork` (0).
Readiness is not execution authorization or a live ownership check.

Diagnose all check reasons before closing the handoff. When existing owner acceptance
unambiguously covers the section, repo-docs repairs its exact status metadata and
other clerical contract defects in the authorized Maintain pass, then reruns the
same consumer check. Preserve approval evidence, scope exclusions and Proposed
decisions. Missing approval stays draft. See
[decisive planning](../repo-docs/references/decisive-planning.md); never stop at a
repairable `draft_saved` or substitute queue size for an ordered implementation plan.

For an explicit plan slice, select only its named IDs. Reconcile existing workers,
dependencies, current source and primary milestone before handoff. A usable
backlog does not require a fresh documentation prepass. The consumer checks the
ordered frontier within the named tasks' goals, never an unrelated global goal.
Its `focus_fallback_required` field is a warning, not execution authority: a named
slice outside the primary milestone still needs the unchanged source-bound native
fallback gate. If the named slice differs
from the primary milestone, retain the focus unless the owner reprioritizes it;
use start_goal's existing `--goal-task` and structured `--fallback-file` admission
with fresh source evidence and attributed reasons, as specified in
[autowork handoff](../autowork/references/handoff.md). There is no new override
flag and no permission to select an unrelated global task or bypass a refusal.

The worker contract carries the IDs, scope, sources, expected change, acceptance,
verification and stop conditions. Mark in_progress only after confirmed handoff.
Workers implement and check their authorized slice and submit review evidence;
a queued card or review request does not prove execution, approval or delivery.
Apply task/evidence transitions only through the authorized ledger owner and
supported helper. Proposal-mode workers return receipts to the integration owner.
Reconcile affected docs and task bodies against verified outcomes, preserving
remaining milestone gaps. Do not mark unverified work complete.
