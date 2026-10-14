# Evidence-driven planning and reconciliation

Use during Bootstrap/Maintain when accepted work needs decomposition, a large queue
has no clear next outcome, or the consumer reports `draft_saved`. Audit applies the
reasoning read-only. Task counts are inventory, not a plan.

## Produce a decision and usable plan

Read accepted milestones, relevant source/tests, full task bodies and consumer
authority. Record a compact frontier in the existing plan owner:

| Candidate IDs | Evidence and unmet outcome | Dependency / uncertainty | Decision and reason |
| --- | --- | --- | --- |
| Existing task ID | Source path/symbol or actual check | Prerequisite ID or missing fact | Now, Next, or deferred |

Compare relevant candidates without duplicating the ledger. Respect accepted focus
and selector ordering. Prefer a ready slice that proves a user outcome or removes
a demonstrated critical prerequisite. Within authorized priorities, weigh consequence,
unblock value, evidence confidence and bounded effort; do not invent numeric scores
or silently reprioritize goals. For routine ordering within the accepted focus,
use supported task-section controls under canonical ownership and revision guards,
update the matching TODO body, then rerun `next`; a narrative ranking alone does
not change selector state. Preserve live leases and dependencies. Changes to owner
priorities, focus or product scope need authority not supplied by routine ordering.

Produce the outputs below using existing repository instructions. The named
protocols are optional techniques for an unresolved method gap or explicit request;
select through [engineering](../../engineering/SKILL.md) and consult
[the engineering cycle](../../shared/ENGINEERING-CYCLE.md) only if routing is unclear:

- `planning-and-task-breakdown`: Now/Next IDs, dependency order, likely files,
  observable acceptance, exact verification and a review checkpoint in existing
  bodies. Split oversized work by usable outcome; preserve IDs/history and leases.
- `spec-driven-development`: close actual scope/acceptance gaps in the existing
  PRD/spec, with evidence, exclusions and uncertainty. Do not restart accepted design.
- `documentation-and-adrs`: record consequential choices, reasons and tradeoffs in
  their owners. Routine task ordering does not need an ADR.
- `doubt-driven-development`: when a non-trivial assumption controls readiness,
  isolate the artifact/contract, seek counterexamples and record corrections/checks.
  Apply its bounded review procedure when available; label degraded self-checks
  honestly, never as fresh-context review. Mechanical metadata repair needs no cycle.

Preserve relevant domain acceptance: API work needs caller/error and
compatibility criteria; migrations need transition/rollback; services need operational
signals; CI changes need actual pipeline checks; UI needs interaction/accessibility
criteria. Preserve the existing quality bar and make the worker contract
self-contained. `constraint-driven-development` and `context-engineering` are
available for gaps in those techniques; domain criteria do not mandate loading
another skill. Keep outputs in
existing task bodies.

Decide routine choices with evidence now; do not create `Needs decision` tasks for
internal naming, test selection, document organization or equivalent implementation
options. Distinguish a missing product requirement from an engineering choice
inside an accepted requirement. Carry the chosen option, tradeoff and check forward.

Record materially applied skill → changed owner/decision/check. A catalog listing is not
application evidence. Missing capabilities never authorize installation, scanner
bypass, fabricated review or expanded scope.
Read imported skills as supporting instructions; do not rewrite their SKILL.md
files or self-improvement metadata during a docs-sync pass. Such instruction edits
require a separate authorized task.

## Compact an existing queue

1. Derive the pending-ID set from the canonical ledger; read every full body,
   accepted plan, section and live owner. Classify active, unclaimed, held and
   withdrawn entries. Pin exact dirty baselines and keep original bodies privately
   for comparison; never regenerate bodies from ledger summaries.
2. Keep one bounded remaining outcome per existing body: action, acceptance, exact
   checks, stop/next step, with Goal, Sources, Dependencies and Ownership intact.
   For active work the action is observing the original continuation; for held work,
   the precise missing input. Link accepted depth instead of duplicating it; similar
   titles do not prove redundant acceptance. Prefer reconciling a reviewed candidate
   over a new coding task, and keep convenience wrappers from becoming prerequisites.
   Do not split work to raise counts or infer cancellation from a speed request.
3. Do not edit a live worker's pinned launch context while admission may depend on
   it; return the proposal to its coordinator. Check the launcher's admission contract
   before promising fewer runs: shared artifacts do not remove dependencies.
4. Keep general workflow links in an Execution field or navigation, not `Sources:`:
   another accepted source there can make automatic plan resolution ambiguous even
   when an explicitly named `backlog-check` passes. Verify both after link changes.
5. Move full previous bodies verbatim to the archive before replacing live prose.
   Verify one body per pending ID, unchanged headings/anchors, section/order, ledger
   objects, acceptance and command literals. Missing environment or owner inputs
   remain gates.
6. Integrate under the shared lock after baseline comparison; run fmt, validate,
   render, links and the consumer check per governing plan once on the final batch,
   then check the next unclaimed slice. Count words from final live bodies only,
   excluding headings, coverage and fences, as context reduction, not speedup.

## Repair clerical handoff failures before stopping

Inspect every consumer `backlog-check` reason and its own exit code. Distinguish
missing authority/approval from defects already within Maintain scope:

1. Locate actual owner acceptance in the conversation or maintained decision and
   bind it to this section and scope. An Accepted heading, queued tasks, defaults
   or a request to document are not approval evidence. Check for later reversal
   and Proposed subdecisions.
2. When acceptance is unambiguous, correct the current section to contain
   `Status: Accepted` alone. Put scope, evidence reference and exclusions on separate
   lines. Preserve Proposed decisions and historical records. Make this clerical
   repair now; do not ask for approval already given or queue another metadata task.
3. Repair supported body/section/dependency/link defects under existing IDs and
   coordination guards. Never normalize a substantive disagreement into approval.
   Without acceptance evidence, retain draft status and name the missing decision.
4. Run fmt/validate/render when ledger edits require them, then rerun the identical
   consumer check with the same plan/task IDs. Re-read concurrent changes. Retry
   after a supported change; unchanged failures need diagnosis, not a loop.

Example: `Status: Accepted (setup behavior only)` becomes the exact status line
plus `Scope: setup behavior only` when actual approval proves that scope. It cannot
authorize a still-Proposed authentication redesign in another section. The checker
stays read-only: it diagnoses metadata, never decides human intent.

Keep executable task fields and acceptance metadata outside fenced code examples.
The consumer ignores fenced examples and generated coverage when reading task
contracts; clerical recovery preserves their original text. A task may link a
more specific accepted plan than its goal's source: automatic selection uses the
goal plan when the task links it, otherwise the task's unique accepted source.
Multiple accepted task sources without that goal binding require an explicit
plan/task selection, not a guessed choice or a rewritten approval.

Use one current Status field per plan section; conflicting status lines are a
metadata defect, not approval. Equivalent local links such as `./SPEC.md#slice`
and `SPEC.md#slice` identify the same plan. Dependency cycles are reported with
their task/goal IDs: correct the unsupported edge from documented intent before
retrying, rather than treating the queue as empty or removing dependencies blindly.
Reopening a Done task moves its ledger section to Next; reopening or adding work
to a met goal makes it partial and preserves prior evidence. Reconcile the TODO
body and section in the same Docs Sync pass before consumer handoff.

## Finish with an actionable handoff

Report actual state/exit, approval source, Now/Next IDs, why Now comes first,
observable outcome, checks and remaining gaps. Re-run `next --json`; distinguish
eligibility, live ownership and execution authorization. `draft_saved` with an
authorized repairable defect means Maintain is unfinished. Missing approval,
authority or a real dependency remains an explicit bounded blocker.

For docs-only scope, report the ready task as undispatched. With existing execution
authority, pass the accepted slice to the existing autowork workflow without asking
again or inventing another dispatcher; preserve review, verification and commit
gates. Queuing, readiness and doc commits do not prove implementation or delivery.

Source guidance: [planning](https://github.com/addyosmani/agent-skills/blob/main/skills/planning-and-task-breakdown/SKILL.md),
[documentation](https://github.com/addyosmani/agent-skills/blob/main/skills/documentation-and-adrs/SKILL.md),
and [doubt-driven development](https://github.com/addyosmani/agent-skills/blob/main/skills/doubt-driven-development/SKILL.md).
Project owners and user boundaries override upstream example paths and defaults.
