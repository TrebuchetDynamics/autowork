---
name: docs-sync
description: "Use when maintaining repo docs and goal-linked tasks."
version: 0.9.0
license: MIT
metadata:
  hermes:
    tags: [documentation, governance, technical-writing, ste-inspired, backlog, todo]
---

# Docs Sync

Keep docs accurate and distinguish intent from implementation. Reuse owners.
The public skill ID is `docs-sync`; invoke it with `/docs_sync` or `/docs-sync`.
Follow [the shared skill contract](../shared/COMMON-CONTRACT.md) for study, hygiene,
safety and evidence; use `wiki-docs` for raw-source-to-wiki compilation.

Every Bootstrap/Maintain delivers corrected applicable docs and bounded ledger
work with complete `TODO.md` bodies for every evidenced unmet goal/requirement.
Findings or rendered coverage alone are insufficient.

Follow [the shared plan contract](../shared/PLAN-HANDOFF.md) for idea-to-execution
handoffs. Accepted answers update existing owners; proposals stay outside the
executable backlog. Writing a task does not authorize its execution. Use [the engineering cycle](../shared/ENGINEERING-CYCLE.md)
for targeted supporting skills and reconciliation after authorized implementation;
a documentation-only request never launches autowork.

## 1. Choose mode and scope

| Mode | Work |
| --- | --- |
| Bootstrap | Build applicable missing docs. |
| Maintain | Update affected owners only. |
| Audit | Read/report; write only when explicitly authorized. |

Bare `/docs_sync` or `/docs-sync` means Bootstrap + Maintain: inspect, build every
applicable core owner, correct supported drift, and run goal-gap analysis. Arguments
narrow scope. Explicit Audit/read-only scope changes no files, including TODO.md,
goals.json and BLOCKERS.md. Task-addition/brainstorming persistence is narrow
Maintain, not bootstrap. Preserve IDs, focus, completed work, history, active owners
and unrelated edits. State mode/scope briefly, then make the authorized changes.

Apply the [autonomous decision rules](../shared/ENGINEERING-CYCLE.md#autonomous-decisions-are-the-default)
and consult its phase/domain skill menu only for a concrete method gap. Decide routine engineering
choices now, record material reasoning, and carry decisions and skill-application
receipts into task bodies; ask only for genuinely missing owner intent or authority.

Do not force filenames, invent requirements, create empty scaffolds or present
plans as implemented. Label missing intent in place as
`Open question: <question> (default: <recommended answer>)`. Use `grill-me` for
necessary owner questions (ask directly if unavailable). Continue independent
supported work; silence/defaults are not approval.

This skill authorizes no code/install/production/instruction/commit/push/release
work independently. Inherit coding-task scope; examples are not execution orders.

## Incremental caller handoff

Apply the [single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
A planner or Autowork caller supplies its task, findings and affected owners; reuse
that verified context and inspect the changed inputs instead of rediscovering the
repository. Batch supported edits, then validate the final batch once. Unchanged
findings require no write or render. Return paths, task IDs, input-bound checks and
the next action to the caller; do not invoke another planner to restate its plan.
Explicit bare Bootstrap scope still covers all applicable document roles.

## 2. Discover and coordinate

Identify boundaries/instructions/intent/snapshot and actual owners/generated inputs.
Inspect relevant source/manifests/tests/CI and scoped Git status/diffs, including
untracked files. Use the supplied base, not assumed `main`. Preserve pre-existing
work/layouts; inspect landed changes after interruption. Report missing authority;
never create competing docs/trackers or guess content.

Use a private pinned Git worktree for writing unless explicit scope restricts edits
to the current checkout. Before ledger/TODO changes load
[concurrent maintenance](references/concurrent-maintenance.md): one integration
owner accepts proposals; cooperative `goals.py` mutations serialize and refuse stale
revisions. Derive repository/lock identity with Git environment overrides removed.
Never reset, clean, stage or overwrite unrelated work, or commit stale whole-file
TODO over newer entries. Revision checks are cooperative stale-write guards, not
atomic CAS against direct writers. Gate-budget/normative-contract/hypothesis checks
in that reference do not prove production API or RF acceptance.

Native Git common config `repoDocs.backlogAuthority` binds an authoritative registered
same-repo worktree. Existing `goals.py next` and coordination honor the binding;
explicit `--canonical-repo` must match it. Without a binding, linked worktrees need
explicit canonical targeting; copied ledgers are not writable canonical state.
Inspect authority; do not set this key in actual repositories for this workflow.
Resolve the actual consumer, not just a docs-only scratch checkout. Scratch
`validate` passing does not give the consumer a backlog: no consumer backlog means
`draft_saved`.

## 2a. Targeted relationship analysis

Routine link, wording and task-metadata repairs use direct source evidence;
no Graphify or other supporting skill is required merely to edit documentation.
For architecture, cross-component impact or uncertain task dependencies, use
`graphify` and [Graphify analysis](references/graphify-analysis.md) when its map
adds needed evidence. Corroborate graph findings in source and accepted intent.
An explicit Graphify requirement remains binding. If graph tooling is unavailable,
use bounded source inspection where sufficient and report material coverage gaps;
never claim that source-only work completed a requested graph analysis. Audit
reads existing artifacts only. Graph inference is not approval or executed validation.

## 3. Intent and evidence

Requirements/accepted decisions own intent; code/tests show implementation; release
records show delivery. Investigate mismatches rather than changing intent to match
code. Distinguish Proposed, Planned and Implemented. Ground claims in paths/symbols/
checks; never invent approval, owners, metrics, history or validation.

Trace owner corrections through dependent contracts/backlog; distinguish policy
changes from implementation. Preserve security/user state, historical receipts,
exact commands, IDs and leases. Read/pin source reports; retain reusable scratch
findings in existing owners. Withdraw unsupported reference claims, not invent
replacement evidence. Notice-only edits must reproduce original bytes after notice
removal. Label authorized redaction; no rewritten history or reactivated proposals.
Keep public skills profile-independent, operational receipts private and fixtures
neutral. Relocation does not purge Git history. Never copy secrets/production data.

## 4. Core document owners

Bootstrap accounts for all applicable roles, reusing equivalent existing paths.
Use [document scaffolding](references/document-scaffold.md) for role ownership,
section templates and conditional documents. Roles need not be separate files.
README, PRD, architecture, spec, test-plan, runbook and CHANGELOG are product/service baselines;
other roles are conditional. Narrow Maintain updates only affected roles. Absence
of a default filename alone does not establish inapplicability.

| Role | Owns |
| --- | --- |
| README | Purpose, prerequisites, shortest supported setup/run/test and navigation. |
| PRD | Why/what: users, approved goals/scope, constraints, measurable acceptance. |
| architecture | Current system map, boundaries, data flow and source-backed relationships. |
| ADR | One durable architectural choice, alternatives and consequences. |
| spec | How: components/data/interfaces, failures, security, migration, rollout. |
| OpenAPI | Exact owned HTTP contract, following authoritative input/generator. |
| test-plan | Risk-based checks, observable outcomes, environments, coverage gaps. |
| runbook | Operations, health, diagnosis, recovery/rollback/backup limits. |
| CHANGELOG | Notable implemented/released changes under actual release conventions. |

Record path and maintained, created, unchanged_verified, created_with_open_questions,
conditional_not_applicable, or not_applicable with boundary reason. "Blocked" is not
an applicable-role outcome. Build substantive supported content despite unknowns;
label questions/defaults and book real question tasks, not fabricated intent/history.
README links detailed owners; reuse requirement IDs without duplicated schemas.

ADRs cover significant hard-to-reverse choices, not routine edits/interview answers.
Check current numbering; otherwise use unique zero-padded IDs and Proposed/Accepted/
Rejected/Superseded statuses. Accepted requires approval. Preserve history; accepted
replacement gets a new ADR and reciprocal supersession links. Do not backdate.
OpenAPI applies to owned HTTP APIs, not CLI/library/third-party placeholders. Identify
schema/code/generated authority; change input only within scope. Preserve supported
versions/layouts/authentication/compatibility; report source changes outside scope.

For client API delivery load [client contract handoff](references/client-contract-handoff.md).
Bind service/revision/freshness and source versus deployed qualification. WebSocket
contracts need post-upgrade messages, not only OpenAPI routes. Preserve actual wire
semantics; label examples/gaps and omit secrets. Storage plans must reuse existing
gates, bind metrics/units, preserve decoding dependencies, and separate plans/offline
checks from authorized remote recovery/activation/relief. Whole-service checks need
per-supported-cell evidence bound to target/interval, not receipt-only fixtures,
sparse silence or readiness probes. Tests name observable outcomes and distinguish
run/existing/planned automation. Runbooks give prerequisites/action/signal/recovery
limits and destructive boundaries. Do not invent production or supported recovery.
CHANGELOG records implemented/released changes, not proposals or routine doc churn.

## 5. Goal-gap analysis and task bodies

Load [decisive planning](references/decisive-planning.md) when decomposing accepted
work, ordering a large queue or repairing a failed handoff. Produce an evidence-backed
Now/Next decision in the existing owner; task counts alone are not planning. Apply
verified relevant Addy skills to those concrete artifacts, not merely a skill list.

Fix in-scope supported docs now, not merely queue repairs. Route behavior to
PRD/spec/contracts/tests, decisions to ADR/spec, setup to README/runbook, operations
to runbook, verification to test-plan, releases to CHANGELOG. Audit reports ranked
incorrect/stale/missing/contradictory/duplicated findings with evidence/consequence/
correction; it writes nothing.

Apply [TODO work center](../shared/TODO-WORKCENTER.md): TODO.md is the central
user-facing work queue. Before rendering or selection, reconcile attributable user
orders and priority changes into goals.json; never silently discard them because
the old index disagrees. Read intent, ledger, full bodies and live execution state.
`goals.json` is the tracked machine execution index synchronized with that queue. Commit ledger with docs only when authorized;
never gitignore it. For a first index, use `scripts/goals.py init <repo> --intent FILE`
with user-supplied version-1 goal/task intent and existing full TODO bodies. If TODO
is absent, supply those bodies with `--todo-file FILE`. Follow the executable
[initialization example](references/document-scaffold.md#first-task-index-initialization).
Initialization requires local source headings with explicit `Status: Accepted`;
it does not infer approval, requirements or task metadata from prose. Preserve IDs,
history, ownership and focus in the input. It refuses conflicting existing state;
an unchanged repeat leaves both content files byte-identical. Then run `fmt`,
`validate`, `render` and the actual consumer's `backlog-check`. Initialization is
not dispatch or model qualification. For maintenance, use supported operations
or reconcile goal objects with intent `source` under the canonical owner, then
`fmt`. There is no `add-goal` command; `init` is not a merge/migration interface.
`add-task` rejects unknown goals. Goal-less TODO bodies cannot replace ledger state.

1. Collect stated requirements/acceptance, planned design/ADR work, test/operations
   gaps, README promises and real owner questions. Reuse IDs. Goals record id/title/
   source/status/evidence/tasks/depends_on/priority (lower sooner) from accepted intent.
2. Status is met/partial/unmet/unverified. `met` needs executed passing evidence:
   `{"kind":"executed","ref":"<exact command or CI job>","result":"pass"}`.
   Unrun tests mean unverified. Harness checks prove code paths, not live acceptance.
   `fmt` downgrades unsupported met, never upgrades. Last-task closure needs actual
   goal evidence or a successor; do not leave unmet goals without open tasks.
3. Each non-met goal gets bounded implementation work plus proof, named by outcome.
   At most one investigation/contract task per goal, only for a blocking unknown;
   no stacked preflights. Unverified work needs its check. Keep two ordered open
   slices for remaining work (Now then Next) with dependencies; preserve done work.
   For unattended engineering, target up to three independently ready, accepted
   slices when useful work exists. Separate implementation/offline checks from
   live-device qualification: retain the live gate on its task, not on independent
   offline work. Give each slice its own sources, acceptance, dependencies and owner.
   Never fabricate scope, remove real dependencies, duplicate done work or claim
   device acceptance to fill the queue. Report a justified shortfall when fewer
   useful slices remain.
4. Preserve accepted `primary_milestone`; `goals.py focus <repo> <GOAL>` requires
   authorized priority change. Focused eligible work precedes unrelated work,
   still respecting dependencies. Use vertical implementation/recovery/platform QA.
   Receipts/docs are subtasks unless they remove a demonstrated prerequisite.
   A slice states remaining gaps; qualified/reviewed/delivered/met remain distinct.
5. Deduplicate ledger/tracker entries. Reread maximum ID immediately before allocation.
   Unchanged evidence must leave goals.json and TODO.md byte-identical on repeat.
6. Use absolute repo paths. Run `goals.py fmt <repo>`, `goals.py validate <repo>`
   (must print `ok`), then `goals.py render <repo>`. Render updates Goal coverage
   and archives explicitly closed, ledger-done task bodies under the
   [archive contract](references/todo-archive.md); it does not reconstruct task bodies.
   Verify open-body preservation, complete archived bodies, links and byte stability
   on an unchanged second render using the actual selected archive path. Include
   attributable TODO/archive changes together in handoffs and authorized commits.
   Match every open/in_progress ID to a full body outside the coverage block.
   Restore missing bodies from authority under the same ID, retaining
   owners/dependencies. Reread concurrent completion evidence, rerender before
   stability checks, and never reopen done work for queue counts.

When graph analysis was used or explicitly required, include `Graph evidence:` in
affected Sources: verified nodes/paths, confidence and coverage, or the graph gap.
Otherwise cite direct source evidence without inventing graph metadata. Derive bounded outcome slices, blast radius and real
prerequisites from corroborated relationships, not graph centrality alone.

Each body has ID/checkbox, Goal/payoff, Sources, bounded Scope/exclusions, observable
Acceptance/checks, explicit `Dependencies:` and `Ownership:` fields. Keep the dependency
key separate because the consumer checker matches field labels exactly. List actual
prerequisite IDs there, matching the ledger, or explicitly declare `None`.
Coordination/history sentences following a `None` declaration do not create or
satisfy task dependencies. Keep those notes in separate fields when possible.
Before handoff,
compare each touched body's checkbox and enclosing TODO section with the `goals.json`
task status/section; `fmt` and `validate` do not prove that consumer binding. Correct
body placement without promoting a `Needs decision` task or changing focus absent
authority. Now is ready work; Next is accepted successors; Needs decision is owner
questions/defaults. Proposals stay outside executable Now/Next. Accepted tasks belong
there even when this docs pass does not execute them; execution needs its own authority.
Saving never launches autowork, claims cards, resumes cron or changes schedules.

Priority reorders preserve bodies/leases and need supported selector controls;
P labels alone do not affect `goals.py next <repo> --json`. Report actual eligible
picks, not claimed work. Needs decision/focus is not eligibility or live availability.
"No eligible follow-ups" requires all goals met with executed evidence and `next`
printing `none`; otherwise report the actual gap.

Every writing Bootstrap/Maintain pass automatically archives completed task bodies:
`goals.py render <repo>` performs the move with coverage rendering, or run
`goals.py archive <repo>` for archive-only maintenance. Reconcile completion
evidence, checkbox/Status and ledger first; inspect the archive result's retained
IDs instead of claiming they moved. In TODO-only repositories, inspect executed
completion checks and use `goals.py archive <repo> --verified-tasks ID1,ID2` for
the verified closed IDs. Audit/read-only passes write nothing.

Load [the TODO archive contract](references/todo-archive.md) before moving completed
bodies, creating history or dated pass-notes. Default `TODO.archive.md`; reuse
`docs/TODO-archive.md` or actual linked owner. Live TODO keeps open bodies/context/
coverage. Move completed bodies/pass-notes verbatim to append-only history; retain
ledger history. Verify multiplicity, continuations, links and second-pass bytes,
not just counts. Archive never queues work. Audit changes neither file.

Fix real monitor drift; intentional planned/external/generated references use exact
tracked `.docs-sync-drift-ignore` lines. Unstated speculative goals get a question
(default: not in scope), not tasks; explicit booking instruction supplies intent.

### Consumer-bound brainstorming handoff check

After saving accepted intent and reconciling full bodies, run the read-only gate:

```sh
python3 "<this-skill-directory>/scripts/goals.py" backlog-check /absolute/consumer --plan docs/spec.md#accepted-heading --tasks TASK1,TASK2
```

Put `Status: Accepted` on its own line inside the referenced plan heading only
when an actual owner decision supports it. Explain the accepted scope and any
remaining Proposed architecture on subsequent lines; appending qualifications to
this machine-read status line prevents exact recognition of an otherwise accepted
section. Do not change approval meaning merely to obtain a passing check.

If actual acceptance already proves this section's scope, repair missing or malformed
status metadata in this pass and rerun the same check. `draft_saved` is a diagnostic,
not a stopping point for an authorized clerical repair. Without acceptance evidence,
retain draft status and identify the unresolved decision; never manufacture approval.

Optional: `--canonical-repo /absolute/primary`, `--expected-revision TOKEN`,
`--receipt prior.json`. JSON stdout is the receipt; retain it only at an existing
authorized location. It binds exact full plan/TODO/goals bytes and authoritative
path, not just a heading/coverage row. A prior receipt is checked against current
bytes/authority; stale/mismatched input cannot certify readiness. Revision tokens
are freshness guards, not dispatch permission. Never fabricate receipts or copy
scratch state into consumers to force success. For safe same-task body reconstruction,
accepted-source link repair and byte-identical duplicate removal, use the
[executable recovery procedure](../autowork/references/blocker-recovery.md#accepted-task-contracts)
and `scripts/recover_backlog.py` with the current revision. It never accepts a plan,
changes ledger status or resolves conflicting intent; rerun the same consumer gate.

| JSON state | Exit | Meaning |
| --- | --- | --- |
| `draft_saved` | 1 | Consumer backlog absent or accepted plan/task binding unreconciled. |
| `backlog_reconciled_not_eligible` | 2 | Reconciled bodies, but current dependencies/focus/status block requested tasks. |
| `ready_for_autowork` | 0 | At least one requested task is currently ledger-eligible. |

An actual consumer with no backlog is draft even if docs scratch `validate` passes.
Report state/exit, saved paths, IDs, authority and eligible slice or exact blocker.
Capture this command's own exit status before a later successful command can mask
it. Inspect the JSON state as well as wrapper success; ledger validation and
manual body checks do not substitute for consumer readiness. Do not claim an edit
landed from surrounding script output when the editing tool returned failure.
Eligibility checks current dependencies/focus/status. Live lease availability remains
unknown. The command does not dispatch; readiness is not implementation authorization.
Do not substitute an unrelated global pick.

### Autoresearch intake and task scheduling

For `/autoresearch` findings, plans, experiments or chained handoffs, load
[the autoresearch adapter](../autoresearch/SKILL.md). Treat run logs, TSV and
`handoff.json` as evidence inputs; this skill still owns canonical documentation
and backlog reconciliation. Narrow Maintain records accepted findings in existing
owners and schedules bounded work in TODO.md with matching goals.json priority,
dependencies, full acceptance/checks and preserved ownership. Reuse matching task
IDs, including leased/in-progress work; repeated evidence creates no duplicates.
Research recommendations do not manufacture accepted product requirements.

Include baseline/target/units, exact Verify/Guard results, run/source references,
remaining gaps and chosen implementation/verification slices. Run the normal
consumer-bound handoff gate and report actual Now/Next eligibility. Scheduling
here means ordered backlog work, not a new timer or dispatch. Continue through
autowork only within existing implementation authority; explicit audit/read-only
and no-implementation limits carry across all chained research commands.

## 6. Language, verification and report

Consult [the STE-inspired writing profile](references/ste-inspired-profile.md)
for substantive English-writing guidance when useful, not for a link or ID repair. Review literals, meaning and repository facts separately; no
translation by default or dictionary-compliance claim from sentence counts.
Use [bootstrap/idempotency regression](references/bootstrap-idempotency-regression.md)
for authorized behavioral checks; static text tests do not prove model adherence.
Run nearest contracts and requested broader gates without new tooling. Bind results
to tested bytes; inspect full logs/manifests, wait for suites and separate scoped
passes from unrelated failures. Partial hashes do not qualify the whole tree.
Check links/anchors/commands/keys/status/acceptance in the dirty checkout and a clean
worktree or exact candidate closure; artifacts must not hide missing targets. Inspect
the checker's scan scope and checkout completeness: a file-link checker may omit TODO
or fragment anchors, and an unpopulated submodule can look like broken documentation.
Run dedicated checks for uncovered targets and verify against a closure with referenced
paths present; report pre-existing or checkout-only failures separately instead of
rewriting unrelated docs.
Label optional scratch/candidate evidence. Never execute production/destructive
procedures just to verify prose. Review scoped diffs for unsupported/unrelated edits.

Report scope, changed owners, actual checks, gaps and eligible next task. Bootstrap
includes role/path/outcome coverage; Maintain only affected roles. Include TODO/goals
paths, IDs/status counts, validate and archive checks, and consumer state/exit.
Backlog is not dispatch/delivery proof. Name language/behavior checks not performed.
When graph analysis was used or required, include Graphify coverage/limitations,
freshness, actual queries, source corroboration
and the evidence chain behind changed docs and tasks; graph output alone is not delivery.

## Hard-blocker coordination contract

Inspect root BLOCKERS.md during authorized Bootstrap/Maintain. Load `hard-blockers`
before entry changes; reading/respecting needs no load. Create absent canonical
Active/Resolved sections with None during bootstrap, not invented blockers: this
required empty coordination file is the no-empty-scaffold exception. Only USER_INPUT,
SUDO or USER_DECISION belong there after autonomous paths/decisions are checked;
internal engineering/review/tool issues stay in tasks/cards. Preserve entries and
Default if no answer; reference IDs in questionnaires/tasks and continue independent
work. Change Last checked only after reevaluation. Verify resolution before moving
to Resolved; never silently delete. Explicit Audit/read-only changes nothing.
