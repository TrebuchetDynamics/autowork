# Repository engineering cycle

Use the existing docs-sync backlog and autowork executor. This is workflow guidance,
not a scheduler, new database or `/cycle` command. Documentation work alone never
launches autowork. Only an explicit whole-spec implementation request authorizes
continuation through that accepted scope; default autowork still hands off one slice.
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

Resolve bundled skills through `hermes-toolset:docs-sync`, `hermes-toolset:autowork`
and [hermes-toolset:engineering](../engineering/SKILL.md), or their actual loaded
SKILL.md paths. The engineering adapter's pinned Addy snapshot is the default;
consult its phase router only when a method is needed; load selected support only. This works without
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
| Changed logic or a bug | `test-driven-development` | Run the repository's discriminating red/green checks. |
| Review an implemented slice | `code-review-and-quality` | Use its review criteria within the required native review lane. |
| Ambiguous new product direction | `idea-refine` | Refine the existing outcome and alternatives; do not reopen accepted scope. |
| Missing or overloaded task context | `context-engineering` | Give the worker only relevant constraints, source, decisions and checks. |
| Quality requirements or a weakened check | `constraint-driven-development` | Bind existing quality requirements to observable checks; no invented owner-approved thresholds. |
| APIs, schemas or module boundaries | `api-and-interface-design` | Specify callers, compatibility, error behavior and contract checks. |
| UI or interaction work | `frontend-ui-engineering` | Plan/build states, accessibility, responsive behavior and relevant interaction checks. |
| Replacing/removing behavior or data formats | `deprecation-and-migration` | Identify consumers, compatibility, transition steps, rollback and migration checks. |
| Build, test automation or packaging boundaries | `ci-cd-and-automation` | Bind the changed boundary to runnable pipeline/build checks. |
| Services, jobs, retries or integration operations | `observability-and-instrumentation` | Define operational questions, useful signals and a verification path; preserve sensitive data. |
| Proven unnecessary complexity | `code-simplification` | Simplify owned code while preserving observable behavior; avoid unrelated cleanup. |
| Owned changes ready to commit | `git-workflow-and-versioning` | Group validated changes; autowork's finish_task.py/agent_commit.sh remains the commit mechanism. |
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
2. For explicitly authorized whole-spec execution, the integration owner reads
   `goals.py next <repo> --json`, restricts selection to accepted IDs, checks live
   ownership and fresh sources, and hands off a dependency-ready slice through
   existing start_goal admission. Use default `worker` ledger mode with the existing
   base, source snapshot, task ID and complete contract. Use
   `--ledger-mode proposal --integration-owner <owner>` only for an explicitly
   requested split-role workflow; whole-spec scope alone does not select proposal mode.
   Mark in_progress only after actual handoff. No new scheduler or substitute run.
3. The worker loads the relevant verified skills, implements, runs checks and
   updates scoped documentation. It returns task/goal IDs, changed paths, source
   fingerprints, exact checks/results, documentation changes and remaining gaps.
   Proposal workers never mutate canonical goals.json, goal coverage or closure;
   they send receipts to the named integration owner and request required review.
4. The owner verifies implementation evidence and required review acceptance at
   the tested source before closure. Pending/rejected review keeps the task
   in_progress and dependent tasks ineligible; do not encode review as an executed
   test pass. Native review handoff can finish the worker card while canonical
   task closure remains pending. Reconcile that same card, do not redispatch it.
   Check exact integration evidence when the accepted task requires integration.
5. After those gates, the owner uses the bundled `goals.py task <repo> <TASK> done`
   and `goals.py evidence <repo> <GOAL> --kind executed --ref "<actual command>"
   --result pass|fail` for actual check receipts. The helper requires all goal tasks
   done and an executed pass to promote an unmet goal; it does not independently
   verify review, source freshness or truth of caller-supplied evidence.
   Run narrow docs-sync Maintain to reconcile affected docs and task bodies, then
   `goals.py validate <repo>` and `goals.py render <repo>`; use canonical authority
   and revision guards and preserve concurrent edits. Rendering updates goal
   coverage and automatically archives explicitly closed, ledger-done task bodies
   under the [archive contract](../docs-sync/references/todo-archive.md). It does
   not reconcile task-body status or implementation docs. Read back and review
   TODO.md and the selected archive before delivering their changes together.
6. Re-read `next` and ownership after reconciliation. Under an active Autowork
   invocation/job, finish authorized closeout and hand off the next eligible batch
   within its accepted scope and remaining occurrence budget. An explicit whole-spec
   mandate also continues within its named scope. A planning-only or one-task request
   without standing continuation authority reports the next slice and stops.
   Exhausted budget, unresolved review/capability or ownership is recorded honestly;
   it never grants broader scope. Report implementation, checks, review, integration
   and delivery separately. Offline fixtures are not native/model execution proof.
