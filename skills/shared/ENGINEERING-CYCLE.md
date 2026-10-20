# Repository engineering cycle

Optional routing reference: consult when a method is needed and its selection is
unclear. Ready tasks use Autowork's execution contract directly. Autowork owns
workflow authority; engineering protocols contribute techniques within that contract.

Use the existing docs-sync backlog and autowork executor. This is workflow guidance,
not a scheduler, new database or `/cycle` command. Documentation work alone never
launches autowork. Caller scope and saved stop/batch limits control continuation.
Default interactive execution completes one slice, including authorized recovery
and closeout. An explicit one-task limit stops new selection after that task;
standing authority cannot override the caller's narrower stop. Explicit continuation or whole-spec scope
permits further eligible batches only within its accepted bounds.
Recurrence authorizes the saved occurrence, not wider scope or extra budgets.
Reconcile consumed history first; unknown usage is not zero, and
exhaustion requires explicit additional allocation, never a new occurrence or session.
Design approval alone does not authorize execution. Preserve no-commit, no-push,
no-deploy and other user boundaries throughout; skill defaults cannot expand them.

Apply [TODO work center](TODO-WORKCENTER.md): TODO.md holds user-facing plans and
orders; reconcile it with goals.json before selection or rendering. Autoresearch
persists findings there by default. Autowork invokes bounded planning when useful
work has unresolved research or decomposition questions, then retries execution.
An empty queue alone calls for bounded inspection, not mandatory Autoresearch.

## One coordinator, supporting skills on demand

Autowork is the default coordinator for authorized repository development. It owns
selection, execution handoff, reconciliation and closeout. An explicitly requested
specialist command stays within its own scope; it does not secretly start Autowork.
Installation makes skills available, not mandatory to load or invoke.

| Current need | Smallest workflow |
| --- | --- |
| Ready task with clear checks | Autowork executes; no research or documentation prepass. |
| Known small repair, empty queue | Record one bounded task and execute; no research ceremony. |
| Unresolved hypothesis, tradeoff or measured optimization | Bounded Autoresearch, then return findings to the same Autowork task. |
| Affected docs, accepted decisions or task metadata | Narrow docs-sync Maintain; no repository bootstrap. |
| User requirements that evidence cannot answer | plan-with-me; Grill Me only for requested/advisable adversarial questioning. |
| Specific engineering method gap | Engineering reference adapter and the relevant protocol only. |
| Slow, redundant or low-signal tests, or a suite past the [test budget](#test-budget) | Engineering `--protocol test-suite-optimization`: audit by default; authorized apply verifies one bounded batch. |
| Material implementation or simplification choice | [Ponytail](../autowork/references/ponytail.md): smallest complete change, with concrete reuse and verification evidence. |
| Review of that implementation | Ponytail review criteria in the existing required review lane; resolve separate versus integrated guidance from the installed version. |
| UI/design work | Impeccable when relevant; no design pass for unrelated changes. |

Zero supporting skills is valid when the task and repository checks suffice. Load
one relevant method at a time and stop when the gap is resolved; the table below
is a menu, not a checklist. Do not reread unchanged supporting instructions within
the same task or add a second review/planning loop merely because a skill exists.
Explicit user-required methods and actual acceptance/review gates still apply.
A helper called by Autowork returns findings, changed paths, checks and task IDs to
that coordinator; it never starts another picker, backlog or scheduler. Reuse the
same TODO entry and receipt. Record a skill's application only when it materially
changes a decision or artifact; never manufacture receipts for unused skills.

## Test budget

Tests are evidence, not a count target. Aim for **minimum sufficient regression
protection**: the smallest set of reliable oracles covering the change's distinct
behavior and risks. Use the canonical
[test-suite optimization method](../engineering/local/test-suite-optimization/PROTOCOL.md)
for its matrix, evidence, retained-risk mapping and review rules.

- Start a bug fix with one discriminating regression that fails without the fix at
  the right public seam; extend an existing case/table when sufficient. This is a
  default, not a blanket one-test cap. Extra cases/layers need a distinct risk and
  review rationale (for example a real boundary a unit mock cannot establish).
  Do not generate a test per function/line or repeat an implementation-mirroring
  TDD loop. Each case should identify its behavior/risk by useful name or matrix.
- Prose-only documentation and pure renames usually need no new runtime test;
  validate their relevant references/contracts. Config, parser or migration
  **behavior** can need regression coverage. Equal coverage or a never-failed CI
  history does not make a case redundant. An assertless no-exception smoke or a
  contractual interaction can be a valid oracle; internal mock calls with no owned
  contract, tautologies and duplicated cases are not protection by themselves.
- Use the smallest fixture and one coherent behavior per case. Share immutable
  setup; preserve mutable-state isolation. Prefer events or bounded polls to sleeps.
  Consolidation must preserve named bug traceability, unique risks and identifiable
  failures, not merely reduce methods or test lines.
- Record repository-specific per-suite CI wall-time limits and a justified new-case
  budget per change/PR, environment/baseline and the review rule for unique-risk
  exceptions. Unknown costs/history stay unknown. Budget exceptions never waive
  safety, security, authorization, data-loss or required qualification obligations.
- Run focused tests and the task's `Checks:` while working, not a full suite after
  each edit. Run the required normal gate once for final acceptance under the
  repository's execution contract; if the coordinator owns that gate, retain its
  pending result rather than claim it passed. Optional impact selection needs sound
  dependency mapping, unknown-impact fallback and the existing full gate or an
  explicitly agreed periodic full run; it must not weaken CI.
- Repository thresholds govern audit triggers; absent those, over 10 minutes for
  the normal offline check, roughly 1,000 lines in a test module, or a near-duplicate
  addition are signals to reuse/record one `test-suite-optimization` audit task
  (at most one open per repository), not reasons to delete tests. Review the slowest/
  noisiest suites quarterly in existing maintenance, without creating a scheduled job.
  Default to audit; explicit apply or existing implementation authority permits
  bounded verified edits. Quarantine requires owner, reason, expiry, issue and lost
  protection/risk, visible reporting and repair/justified retirement/escalation at
  expiry; never silently hide a critical regression.

## Autoresearch evidence enters the same cycle

Use [autoresearch](../autoresearch/SKILL.md) for bounded measured experiments,
diagnosis, adversarial analysis and research-driven planning. Its original command
protocols are vendored with a pinned revision. `plan`/`learn`/`improve` and all
research checkpoints route findings through docs-sync narrow Maintain: update
existing document owners, deduplicate accepted tasks, schedule Now/Next in TODO.md
and canonical goals.json, and run the consumer handoff gate. TSV/handoff files are
evidence, never a competing task queue. Autowork retains task ownership, execution,
review and commit gates. Planning does not dispatch workers or create timers;
already-authorized implementation can continue from a verified eligible handoff.

## Autonomous decisions are the default

Within the user's authorized outcome, decide routine reversible choices yourself:
implementation approach, internal naming, test seams, document structure, supported
metadata repair and dependency-ready ordering within the accepted focus. Inspect
existing conventions and constraints first, choose the smallest sufficient option,
record the reason and verifying check, then act. Do not ask the user to choose
between equivalent engineering options or approve each phase again. An agent's
own plan is not a new approval gate. Missing certainty calls for a bounded source
inspection or discriminating test, not an automatic owner question.

Use this decision order: explicit user/repository constraints → accepted contracts
and existing conventions → evidence from a cheap reversible probe → simplest
compatible implementation. For a consequential choice, compare viable alternatives
and record why the selected one wins. For trivial choices, proceed without creating
an ADR or decision task. Stop investigating once evidence distinguishes the options;
revisit only when a check fails or new evidence changes the choice.

Ask only for a missing fact or decision that materially changes the user's outcome,
conflicts with accepted requirements, crosses ownership/scope, or needs authority
not already granted. Explain the exact missing input, recommend an option and keep
independent work moving. Silence is never permission, review acceptance or evidence.
Routine decisions are made under existing authority, not "approved by default".
Existing explicit authority carries forward; do not request it again. Docs-only
scope stays docs-only, and required independent review and commit gates remain.

Record `Decision: <choice>; Evidence: <source>; Reason: <tradeoff>; Check: <proof>`
in the existing task/plan owner when material. Carry that decision into the worker
contract so it is not re-interviewed. Label inferred product intent as proposed;
never relabel it Accepted merely because the engineering choice is reversible.

## Load the skill needed at the current step

Resolve bundled skills through `autowork:docs-sync`, `autowork:autowork`
and [autowork:engineering](../engineering/SKILL.md), or their actual loaded
SKILL.md paths. The engineering adapter's pinned Addy snapshot is the default;
select one technique with `scripts/route.py --protocol NAME` when a method is needed.
Phase bundles are optional; load selected support only. This works without
external imports and avoids ambiguous bare names. Preserve recorded vendored
adaptations and apply the adapter's TODO, authorization and host-tool translations.

An explicit user request to use a separate installed Addy version wins: verify its
source/revision through the profile catalog and `skills/.hub/lock.json`, disclose
missing references, and record that alternative. Do not invent an `addyosmani:`
namespace or assume another profile's home. Existing imports are left intact.

| Need | Targeted addyosmani skill | Apply to the existing owner |
| --- | --- | --- |
| Missing owner intent that evidence cannot resolve | `interview-me` | Ask only the material owner question; routine engineering decisions use the autonomy rule above. |
| Missing specification | `spec-driven-development` | Reuse the accepted spec/PRD; do not restart accepted design. |
| Changed behavior or architectural decision | `documentation-and-adrs` | Amend affected docs/ADR with observed facts; docs-sync owns backlog reconciliation. |
| Accepted work needs bounded tasks | `planning-and-task-breakdown` | Add dependencies, scope and checks to canonical `goals.json` and root `TODO.md`. |
| A consequential planning assumption needs scrutiny | `doubt-driven-development` | Test the artifact/contract; record corrections and unresolved risks. |
| Implement an eligible slice | `incremental-implementation` | Keep one observable result, owned files and task ID. |
| Changed logic or a bug | `test-driven-development` | Minimum sufficient red/green protection at the right seams within the [test budget](#test-budget). |
| Review an implemented slice | `code-review-and-quality` | Use its review criteria within the required project review workflow. |
| Ambiguous new product direction | `idea-refine` | Refine the existing outcome and alternatives; do not reopen accepted scope. |
| Missing or overloaded task context | `context-engineering` | Give the worker only relevant constraints, source, decisions and checks. |
| Quality requirements or a weakened check | `constraint-driven-development` | Bind existing quality requirements to observable checks; no invented owner-approved thresholds. |
| APIs, schemas or module boundaries | `api-and-interface-design` | Specify callers, compatibility, error behavior and contract checks. |
| UI or interaction work | `frontend-ui-engineering` | Plan/build states, accessibility, responsive behavior and relevant interaction checks. |
| Replacing/removing behavior or data formats | `deprecation-and-migration` | Identify consumers, compatibility, transition steps, rollback and migration checks. |
| Build, test automation or packaging boundaries | `ci-cd-and-automation` | Bind the changed boundary to runnable pipeline/build checks. |
| Services, jobs, retries or integration operations | `observability-and-instrumentation` | Define operational questions, useful signals and a verification path; preserve sensitive data. |
| Proven unnecessary complexity | `code-simplification` | Simplify owned code while preserving observable behavior; avoid unrelated cleanup. |
| Owned changes ready to commit | `git-workflow-and-versioning` | Group validated changes; use ordinary Git and the repository's scoped commit conventions. |
| Release or rollout planning in accepted scope | `shipping-and-launch` | Capture readiness and rollback criteria; planning does not itself authorize deployment. |
| Reproduction or failing checks | `debugging-and-error-recovery` | Diagnose before changing code; use the verified fallback below when unavailable. |
| Measured performance requirement | `performance-optimization` | Establish a baseline, target the measured cause and compare the same workload. |
| Trust boundaries or sensitive input | `security-and-hardening` | Trace threats to mitigations and abuse-case checks within the task. |
| Browser behavior needs qualification | `browser-testing-with-devtools` | Exercise the actual journey on the required environment; static checks are not browser proof. |
| External implementation/API behavior is uncertain | `source-driven-development` | Verify authoritative source/contracts before relying on remembered behavior. |

Consult this menu only for an unresolved method gap or explicit protocol request.
A phase change alone is not a trigger. Reuse accepted specs, plans, quality bars
and repository procedures; do not replay planning, review or delivery workflows.
For a protocol actually applied, record material decision/artifact/check evidence
in the existing task receipt. Do not create an application record for every skill
that could conceivably be relevant. Missing optional guidance is not a gate;
missing required acceptance or execution capability must still be reported.

Load only relevant skills, not this whole table. Adapt upstream examples such as
`tasks/todo.md`, new spec files and automatic commits to existing owners and
permissions; never create a competing backlog or duplicate accepted tasks.

For docs-sync, apply these skills through
[decisive planning](../docs-sync/references/decisive-planning.md): evidence-backed
Now/Next ordering, bounded bodies and repaired consumer contracts are the outputs.
Record selected skill → changed owner/decision/check; a list of loaded skills does
not establish application. A usable accepted backlog does not need repeated planning.

TDD identity collision: use the engineering adapter's pinned
`upstream/skills/test-driven-development/PROTOCOL.md` by default. Neither a bare
`test-driven-development` name nor Hermes's bundled
`software-development/test-driven-development` establishes Addy provenance.
If the vendored protocol is unavailable, identify the actual fallback and gap.

If a domain skill is scanner-blocked or unavailable, use verified repository
procedures/checklists for its same obligations and report any missing capability;
do not bypass the scanner or silently omit the risk.
If `debugging-and-error-recovery` is scanner-blocked or unavailable, report that
fact and use an available, verified `systematic-debugging` skill for diagnosis.
If that fallback is also absent, use the repository's documented reproduction and
debugging procedure and report the limitation. Do not install, bypass the scanner,
or waive the same acceptance checks to obtain a supporting skill. Missing required
execution/review capability remains an explicit unresolved gate.

Check referenced support files before claiming to have read them. Per-skill installs
may omit upstream root `references/definition-of-done.md`,
`references/security-checklist.md` or `references/performance-checklist.md` even
when SKILL.md loads. Disclose missing support; use the accepted task's repository
criteria and available project checklists, retaining required security/performance
coverage. Mark unavailable required checks NOT_CHECKED, never pretend they passed.

## One canonical backlog, one executor, one closure owner

1. Docs Sync reconciles accepted requirements into existing goal/task IDs and full
   TODO bodies. Use [plan handoff](PLAN-HANDOFF.md) and its consumer backlog-check;
   drafts, missing acceptance and unresolved dependencies do not become ready work.
   A usable backlog skips another bootstrap or broad audit.
2. For explicitly authorized whole-spec execution, restrict selection to accepted
   IDs and dependency-ready tasks. Read TODO and any existing goals index, inspect
   actual process/workspace ownership and source freshness, then execute in the
   current session using Autowork's direct contract. No native card admission,
   board lookup or mandatory worker is required. Optional delegation uses the
   current host's tools only when useful and authorized.
3. Implement, run discriminating checks and update scoped documentation. Retain
   task IDs, source/candidate identity, changed paths, actual commands/results and
   remaining gaps. Honor explicit task/caller limits and real host controls; a
   receipt cannot enforce spending and a new occurrence cannot reset allocations.
   Delegated workers stay within their assigned scope and return evidence to the
   integration owner rather than modifying unrelated canonical task state.
4. Verify implementation evidence and required independent review acceptance at
   the tested source before closure. Pending/rejected review holds completion and
   dependent work; it is not a test pass. Address review changes in the current
   authorized session, with affected checks and fresh review. No native card
   reassignment, continuation API or done transition is required. Inspect exact
   integration evidence whenever the accepted task requires integration.
5. **Assess documentation impact** from the verified diff, task Acceptance/checks
   and actual affected docs (commands/configuration, interfaces, architecture,
   operations and verification requirements). Record `doc_impact` as `not_needed`
   with a source-backed reason, `updated` with paths and passing readback/checks,
   or `pending` with the concrete gap and resume action. Workers update in-scope
   component docs and route shared docs to the coordinator/DOCS-MAINTAINER. See the
   [parallel report contract](../autowork/references/parallel-workers.md#documentation-impact-evidence).
   In sequential native/portable execution, resolve bundled Docs Sync in the actual
   host and run scoped Maintain only for a concrete delta, before final closure.
   No full bootstrap or global manifest is required; archive rendering alone is not
   Maintain. Do not change unrelated policy or Acceptance. Read back affected docs
   and run their checks. Preserve foreign dirty docs and reconcile moved source,
   rather than overwrite or repin old evidence. Required doc failure/interruption
   retains implementation and pending resume evidence, not a false documentation
   pass or implementation replay. Needed closeout stays within once/until-empty
   scope; stops, pauses and exhausted budgets launch no new work.
   The Pi runtime's closeout Maintain pass belongs to DOCS-MAINTAINER (TOOLSET-266-7a),
   not a second close authority inside its atomic transaction. Report evidence alone
   neither launches that pass nor proves documentation acceptance.
   After the required gates, when goals.json exists, the owner uses the bundled `goals.py task <repo> <TASK> done`
   and `goals.py evidence <repo> <GOAL> --kind executed --ref "<actual command>"
   --result pass|fail` for actual check receipts. The helper requires all goal tasks
   done and an executed pass to promote an unmet goal; it does not independently
   verify review, source freshness or truth of caller-supplied evidence.
   Reconcile task bodies, then run `goals.py validate <repo>` and
   `goals.py render <repo>`; use canonical authority
   and revision guards and preserve concurrent edits. Rendering updates goal
   coverage and automatically archives explicitly closed, ledger-done task bodies
   under the [archive contract](../docs-sync/references/todo-archive.md). It does
   not reconcile task-body status or implementation docs. Read back and review
   TODO.md and the actual selected archive, including a custom history path.
   Verify complete open bodies remain live, complete closed bodies and prior history
   survive in the archive, local links resolve, and an unchanged second render leaves
   both files byte-identical. Include attributable TODO/archive changes in the handoff
   and any authorized commit together. These checks do not prove model adherence or
   live task completion.
   With TODO-only tasks, reconcile their verified acceptance and evidence directly;
   no index or extra public task registry is required.
6. Re-read the eligible TODO/index queue and actual ownership after reconciliation. Under an active Autowork
   invocation/job, finish authorized closeout. Select another batch only when caller
   scope permits it and saved stop/batch limits and remaining allocation allow it.
   Default interactive, planning-only and explicit one-task requests report the next
   slice and stop; explicit continuation/whole-spec mandates use their named scope.
   Exhausted budget, unresolved review/capability or ownership is recorded honestly;
   it never grants broader scope. Report implementation, checks, review, integration
   and delivery separately. Offline fixtures are not native/model execution proof.
