# Evidence-driven planning and reconciliation

Use during Bootstrap/Maintain when accepted work needs decomposition, a large queue
has no clear next outcome, or a handoff left tasks as drafts or blocked. Audit
applies the reasoning read-only. Task counts are inventory, not a plan.

## Produce a decision and usable plan

Read accepted goals, relevant source/tests, the task records in `tasks/` and
consumer authority. Record a compact frontier in the existing plan owner:

| Candidate IDs | Evidence and unmet outcome | Dependency / uncertainty | Decision and reason |
| --- | --- | --- | --- |
| Existing task ID | Source path/symbol or actual check | Prerequisite ID or missing fact | Now, Next, or deferred |

Compare relevant candidates without duplicating task records. Respect accepted focus
and selection order. Prefer a ready slice that proves a user outcome or removes
a demonstrated critical prerequisite. Within authorized priorities, weigh consequence,
unblock value, evidence confidence and bounded effort; do not invent numeric scores
or silently reprioritize goals. For routine ordering within the accepted focus,
edit section and rank with `autowork tasks place`, `move` or `field ID rank N`, then
confirm with `autowork tasks list`; a narrative ranking alone does not change
selection. Preserve holds and dependencies. Changes to owner
priorities, focus or product scope need authority not supplied by routine ordering.

Produce the outputs below using existing repository instructions. The named
protocols are optional techniques for an unresolved method gap or explicit request;
select through [engineering](../../engineering/SKILL.md) and consult
[the engineering cycle](../../shared/ENGINEERING-CYCLE.md) only if routing is unclear:

- `planning-and-task-breakdown`: Now/Next IDs, dependency order, likely files,
  observable acceptance, exact verification and a review checkpoint in existing
  records. Split oversized work by usable outcome; preserve IDs/history and holds.
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
another skill. Keep outputs in existing task records.

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

1. List the open tasks (`autowork tasks list`); read every record, accepted plan,
   section and hold. Classify active, unclaimed, held and withdrawn entries. Keep
   the original records privately for comparison; never regenerate them from
   summaries.
2. Keep one bounded remaining outcome per existing record: action, acceptance, exact
   checks, stop/next step, with goal, `Sources:`, `depends_on` and `ownership`
   intact. For active work the action is observing the original continuation; for
   held work, the precise missing input. Link accepted depth instead of duplicating
   it; similar titles do not prove redundant acceptance. Prefer reconciling a
   reviewed candidate over a new coding task, and keep convenience wrappers from
   becoming prerequisites. Do not split work to raise counts or infer cancellation
   from a speed request.
3. Do not edit an admitted task's contract while its worker may depend on it;
   return the proposal to its coordinator. Check the launcher's admission contract
   before promising fewer runs: shared artifacts do not remove dependencies.
4. Keep general workflow links in a separate note or navigation, not `Sources:`:
   another accepted source there makes the governing plan ambiguous.
5. Edit records in place with `autowork tasks field`; Git history keeps the
   previous text. Verify one record per open ID, unchanged sections and ranks,
   acceptance and command literals. Missing environment or owner inputs remain
   gates.
6. Run `autowork tasks validate --worktree .` and the link checks once on the final
   batch, then check the next unclaimed slice. Count words from the final records
   only, as context reduction, not speedup.

## Repair clerical handoff failures before stopping

Inspect `autowork tasks validate --worktree` output and `autowork tasks why ID` for
each requested task. Distinguish missing authority/approval from defects already
within Maintain scope:

1. Locate actual owner acceptance in the conversation or maintained decision and
   bind it to this section and scope. An Accepted heading, queued tasks, defaults
   or a request to document are not approval evidence. Check for later reversal
   and Proposed subdecisions.
2. When acceptance is unambiguous, correct the current section to contain
   `Status: Accepted` alone. Put scope, evidence reference and exclusions on separate
   lines. Preserve Proposed decisions and historical records. Make this clerical
   repair now; do not ask for approval already given or queue another metadata task.
3. Repair supported draft fields, section, dependency and link defects under
   existing IDs with `autowork tasks`. Never normalize a substantive disagreement
   into approval. Without acceptance evidence, keep the plan Proposed and name the
   missing decision.
4. Rerun the same validation and `why` checks. Re-read concurrent changes. Retry
   after a supported change; unchanged failures need diagnosis, not a loop.

Example: `Status: Accepted (setup behavior only)` becomes the exact status line
plus `Scope: setup behavior only` when actual approval proves that scope. It cannot
authorize a still-Proposed authentication redesign in another section.

A task may link a more specific accepted plan than its goal's `source`; keep both
accurate. Use one current Status field per plan section; conflicting status lines
are a metadata defect, not approval. Dependency cycles are refused with their IDs:
correct the unsupported edge from documented intent before retrying, rather than
removing dependencies blindly. Reopening work for a met goal makes the goal partial
(`autowork tasks goal ID --status partial`) and preserves its evidence note.

## Finish with an actionable handoff

Report validation result, approval source, Now/Next IDs, why Now comes first,
observable outcome, checks and remaining gaps. Re-run `autowork tasks list`;
distinguish eligibility, holds and execution authorization. A draft or blocked task
with an authorized repairable defect means Maintain is unfinished. Missing approval,
authority or a real dependency remains an explicit bounded blocker.

For docs-only scope, report the ready task as undispatched. With existing execution
authority, pass the accepted slice to the existing autowork workflow without asking
again or inventing another dispatcher; preserve review, verification and commit
gates. Queuing, readiness and doc commits do not prove implementation or delivery.

Source guidance: [planning](https://github.com/addyosmani/agent-skills/blob/main/skills/planning-and-task-breakdown/SKILL.md),
[documentation](https://github.com/addyosmani/agent-skills/blob/main/skills/documentation-and-adrs/SKILL.md),
and [doubt-driven development](https://github.com/addyosmani/agent-skills/blob/main/skills/doubt-driven-development/SKILL.md).
Project owners and user boundaries override upstream example paths and defaults.
