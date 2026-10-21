---
name: docs-sync
description: "Use when maintaining repo docs and goal-linked tasks."
version: 0.13.0
license: MIT
metadata:
  hermes:
    tags: [documentation, governance, technical-writing, ste-inspired, backlog, tasks]
---

# Docs Sync

Keep docs accurate and distinguish intent from implementation. Reuse owners.
The public skill ID is `docs-sync`; invoke it with `/docs_sync` or `/docs-sync`.
Follow [the shared skill contract](../shared/COMMON-CONTRACT.md) for study, hygiene,
safety and evidence; use `wiki-docs` for raw-source-to-wiki compilation.

Every Bootstrap/Maintain delivers corrected applicable docs and, for every
evidenced unmet goal or requirement, complete task records in `tasks/`. Findings
alone are insufficient.

After a workflow update, verify the installed copies first, then maintain each
project's tasks with freshly loaded instructions; installation does not rewrite
project documents. Deliver integrated, verified corrections, not only private
proposals, unless an actual overlapping writer or missing intent prevents them.
Keep document-only scope separate from implementation, dispatch and schedule changes.

Follow [the shared plan contract](../shared/PLAN-HANDOFF.md) for idea-to-execution
handoffs. Accepted answers update existing owners; proposals stay outside the
executable queue. Writing a task does not authorize its execution; a
documentation-only request never launches autowork. Reconcile verified outcomes
under the ownership and review rules below.

## 1. Choose mode and scope

| Mode | Work |
| --- | --- |
| Bootstrap | Build applicable missing docs. |
| Maintain | Update affected owners only. |
| Audit | Read/report; write only when explicitly authorized. |

Bare `/docs_sync` or `/docs-sync` means Bootstrap + Maintain: inspect, build every
applicable core owner, correct supported drift, and run goal-gap analysis. Arguments
narrow scope. Explicit Audit/read-only scope changes no files, including `tasks/`
and BLOCKERS.md. Task-addition/brainstorming persistence is narrow Maintain, not
bootstrap. Preserve IDs, focus, completed work, history, active holds and unrelated
edits. State mode/scope briefly, then make the authorized changes.

Decide routine engineering choices within accepted scope, record material reasoning
in existing task records and reuse accepted decisions; ask only for genuinely missing
owner intent or authority. For a concrete method gap or explicit protocol request,
select one technique through [engineering](../engineering/SKILL.md); consult
[the engineering cycle](../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
Carry evidence of materially applied methods into the same task records.

Do not force filenames, invent requirements, create empty scaffolds or present
plans as implemented. Label missing intent in place as
`Open question: <question> (default: <recommended answer>)`. Use `grill-me` for
necessary owner questions (ask directly if unavailable). Continue independent
supported work; silence/defaults are not approval.

This skill authorizes no code/install/production/instruction/commit/push/release
work independently. Inherit coding-task scope; examples are not execution orders.
For research/design-only work, save actionable findings as tasks and goals in
`tasks/` in the same batch; a research document alone is not the handoff. A
no-code restriction covers presentation sites too: a suggested docs framework is a
candidate, not permission to scaffold, install or build it.

## Incremental caller handoff

Apply the [single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
A planner or Autowork caller supplies its task, findings and affected owners; reuse
that verified context and inspect the changed inputs instead of rediscovering the
repository. Compare the latest run, reviewed candidate, integrated source and current
record before retaining a recovery instruction; edit the record in place instead of
appending successive status notes. Completed work must not remain an open task that
instructs a worker to reimplement it. Batch supported edits, then validate the final
batch once. Unchanged findings require no write. Return paths, task IDs, input-bound
checks and the next action to the caller; do not invoke another planner to restate
its plan. Explicit bare Bootstrap scope still covers all applicable document roles.

## 2. Discover and coordinate

Identify boundaries/instructions/intent/snapshot and actual owners/generated inputs.
Inspect relevant source/manifests/tests/CI and scoped Git status/diffs, including
untracked files. Use the supplied base, not assumed `main`. Preserve pre-existing
work/layouts; inspect landed changes after interruption. Include staged, unstaged
and untracked inputs; an unstaged-only inventory misses indexed dependencies. Before
integration and reporting, reread affected source, task records and recent commits:
reconcile landed work under existing IDs and withdraw obsolete proposals.
Report missing authority; never create competing docs/trackers or guess content.

A refused write or baseline mismatch is a reconciliation step, not a request for
new approval: reread the target record and apply only the authorized delta to the
latest state, or reconstruct it when the target itself changed. Never replay a
whole-file snapshot or repin evidence to hide drift. Follow
[stale-target reconciliation](references/concurrent-maintenance.md#reconcile-a-stale-or-occupied-target).

Only the owner, or the coordinator's own bookkeeping, edits files under `tasks/`.
A worker's commit that edits any task file is held and never merged. Distinguish an
owner-requested priority change for the next selection (a `rank` or section edit)
from rewriting a running worker's contract: integration treats rank, title, short
and notes as bookkeeping, but an acceptance, checks, dependency, authority or
section change to an admitted task sets its attempt aside or requires revalidation.
Never interrupt a worker, repin its candidate or change its admitted contract to
force progress. If an overlapping writer or another designated integration owner
prevents landing, retain the scoped candidate and intended `autowork tasks`
commands in durable private storage, not expiring scratch, and label new tasks
pending integration rather than queued or ready.

Use a private Git worktree for writing unless explicit scope restricts edits to the
current checkout. Edit task records only through `autowork tasks` (see
[concurrent maintenance](references/concurrent-maintenance.md)): it writes only the
working tree, never commits, refuses a file changed since it was read and validates
the whole store before keeping a write. Never reset, clean, stage or overwrite
unrelated work. Commit task edits with the docs only when authorized; keep
branch-local changes reviewable. Resolve the actual consumer repository, not a
docs-only scratch checkout: a scratch store passing validation does not give the
consumer any tasks. Keep new IDs provisional until the consumer's store allocates
them (`autowork tasks new-id`).

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
checks; never invent approval, owners, metrics, history or validation. Bind
historical receipts to their tested revision: old untested wording does not prove
current absence. Before retaining a “local-only” or “not on main” claim, check
`git merge-base --is-ancestor <reviewed-commit> <target>` and the relevant current
source blobs; integration can advance independently of an old receipt. Correct
CHANGELOG and test-plan together while keeping packaging, deployment and live
qualification separate.

Reconcile retained checks by reading the receipt, result inventory and actual
runner liveness together. If the runner is gone but its receipt lacks a terminal
exit or full aggregate, record the attempt as incomplete/unqualified, not running
or passed; failed batches do not establish an invented whole-suite total. Before
promoting a retained full-gate receipt, verify its declared log and owned-source
hashes, then reconcile the selected inventory with unique recorded test/project
identities across every batch in code. Preserve retry, flaky and skip classifications;
summed batch counters can double-count attempts or conceal missing identities.
Record a completed focused check with its source/tools, selected-versus-recorded inventory,
setup-versus-product cases, skip reasons and cleanup evidence. Keep its duration
out of full-gate speedup claims. Put the detailed result in one existing evidence
owner and link it from the live task's `Evidence:` note and the plan; update the next
action without resetting ownership, budgets or acceptance. For paired visual evidence, retain baseline and
candidate observations separately: a defect present in both is an outstanding
acceptance gap, not proof that the candidate introduced it. State fixture limits
such as substituted fonts or a blank renderer alongside the claim, because painted
widget chrome does not establish production typography or device/GPU rendering.
Record an owner-permitted acceptance waiver with its exact
criterion, authority, residual risk and remaining checks; it is never an executed
pass and does not extend to other criteria or tasks. When scope changes, reconcile
the authority owner, active task records and operational guidance together.

Trace owner corrections through dependent contracts and tasks; distinguish policy
changes from implementation. Preserve security/user state, historical receipts,
exact commands, IDs and holds. Read/pin source reports; retain reusable scratch
findings in existing owners. Withdraw unsupported reference claims, not invent
replacement evidence. Notice-only edits must reproduce original bytes after removing
only this pass's notices; preserve pre-existing annotations. Label authorized redaction; no rewritten history or reactivated proposals.
Keep public skills profile-independent, operational receipts private and fixtures
neutral. Relocation does not purge Git history. Never copy secrets/production data.
When asked to save supplied operational notes, preserve the source under a short
provenance notice and link it from existing documentation navigation. Keep its
host/version qualifications and distinguish reported measurements from checks you
actually repeated. Saving a runbook does not authorize its install/configuration
commands or convert its checklist into executable tasks.

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
When the repository has a [role manifest](references/document-scaffold.md#optional-role-manifest),
keep it synchronized with these outcomes, run `scripts/docs.py stale <repo>` to scope
Maintain and `scripts/docs.py check <repo>` before reporting; fix or report every
finding. A pass does not prove content accuracy.
Its optional [profile](references/document-scaffold.md#repository-type-profiles) sets
the baseline roles for the repository type; choose it from what the repository ships.

ADRs cover significant hard-to-reverse choices, not routine edits/interview answers.
Check current numbering; otherwise use unique zero-padded IDs and Proposed/Accepted/
Rejected/Superseded statuses. Accepted requires approval. Preserve history; accepted
replacement gets a new ADR and reciprocal supersession links. Do not backdate.
OpenAPI applies to owned HTTP APIs, not CLI/library/third-party placeholders. Identify
schema/code/generated authority; change input only within scope. When handlers or a
service are retired, keep the task's original criteria, cite immutable history and
defer it absent an accepted surviving contract; deletion is not met. Preserve supported
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
On repeat passes, check newly landed scoped commits and update CHANGELOG and the
affected test-plan together without rewriting earlier entries. Reconcile partial
delivery explicitly: record implemented behavior under the actual Unreleased/version
section, replace blanket “all checks planned” wording with existing versus remaining
coverage, and give the same live task one concrete next action. Keep its original
acceptance and open status when qualification remains; documentation reconciliation
is not a rerun of historical tests. Anchor changelog edits to the enclosing release
section and a unique neighboring entry, because headings such as `### Fixed` recur
across versions. Stop the edit/check chain on a failed replacement so a later
successful validator cannot mask an unapplied correction.
Treat a failed preservation assertion the same way: chain shell checks with `&&`
or use checked subprocess calls, not `;`, so a later successful validator cannot
mask a failed conservation check. After a failure, inspect the affected bytes
before resuming only the unapplied work.

## 5. Goal-gap analysis and tasks

Load [decisive planning](references/decisive-planning.md) when decomposing accepted
work, ordering a large queue or repairing a failed handoff. Produce an evidence-backed
Now/Next decision in the existing owner; task counts alone are not planning.
Existing instructions suffice unless a concrete method gap or explicit protocol
request calls for supporting guidance.

Fix in-scope supported docs now, not merely queue repairs. Route behavior to
PRD/spec/contracts/tests, decisions to ADR/spec, setup to README/runbook, operations
to runbook, verification to test-plan, releases to CHANGELOG. Audit reports ranked
incorrect/stale/missing/contradictory/duplicated findings with evidence/consequence/
correction; it writes nothing.

### The task store

A repository's tasks live in `tasks/`, its only task store (format:
[the task store reference](../../pi-autowork/task-store.md)). Apply the
[shared task rules](../shared/TODO-WORKCENTER.md) for `touches` and `resources`.

- `tasks/goals/<ID>.md`: one goal per file, with `title`, `priority` (1 first),
  `source` (the accepted plan or spec heading, `path#anchor`), `status`
  (`unmet`, `partial`, `unverified`, `met`), `focus` (at most one goal) and
  `depends_on` (goal IDs that must be met first).
- `tasks/items/<ID>.md`: one task per file. TOML frontmatter between `+++` lines
  holds the typed contract: `title`, `short` (40 characters at most), `status`
  (`open`, `done`, `superseded`), `goal`, `section` (`Now`, `Next`,
  `Needs decision`), `rank` (lower first within its section), `depends_on`,
  `touches`, `resources`, `kind` (`implementation`, `plan`, `inspection`),
  `ownership` (`worker`, `coordinator`, `owner`), `live` (`denied`, `authorized`),
  `scope`, `acceptance`, `checks` and `exclusions`. After the frontmatter, free
  body notes use `- Label: value` lines (`Sources:`, `Owner decision:`,
  `Held by:`, `Evidence:`, `Question:`, `Superseded by:`).
- `tasks/evidence/<ID>.toml`: the receipt the engine's verified close writes. Do
  not write receipts by hand.

A record missing contract fields is a visible draft and is never selected. A
`TODO.archive.md` that exists is frozen, read-only history: read it, never write it
(see [frozen archive](references/todo-archive.md)). BLOCKERS.md keeps owner
questions; CHANGELOG.md keeps releases. A repository that still has TODO.md and
goals.json selects nothing until the owner runs `autowork migrate [repo]` once;
do not convert it yourself or recreate those files. In a repository with no task
store at all, `autowork tasks` refuses (`no task store`): keep the planned goals and
tasks in the plan and ask the owner to start the store, rather than hand-writing
records.

### Edit tasks and goals with `autowork tasks`

Every task or goal edit goes through one CLI, run from (or naming) the consumer
repository. Read first, then write:

| Need | Command |
| --- | --- |
| Inspect | `autowork tasks list`, `autowork tasks show ID`, `autowork tasks why ID` |
| Add or change a goal | `autowork tasks goal ID --title T --source path#anchor --priority N [--status S] [--focus/--no-focus] [--depends-on G] [--evidence TEXT]` |
| Add a task | `autowork tasks add --goal G --title T --short S [--section Next] [--scope TEXT] [--acceptance A ...] [--checks C ...] [--touches P ...] [--depends-on ID ...]` |
| Set a typed field or note | `autowork tasks field ID LABEL VALUE` (for example `rank`, `touches`, `checks`, `kind`, `ownership`, `resources`, `exclusions`, `depends_on`, or a note label such as `Sources`) |
| Change section | `autowork tasks place ID Now\|Next\|"Needs decision" [--decision TEXT]` |
| Reorder | `autowork tasks move ID up\|down`, or `field ID rank N` |
| Close without the engine | `autowork tasks done ID --evidence TEXT` |
| Retire for a successor | `autowork tasks supersede ID --by OTHER --reason TEXT` |
| Check the result | `autowork tasks validate --worktree .` |

A new goal needs `--title`, `--source` and `--priority`. `add` rejects an unknown
goal and allocates the next ID (`autowork tasks new-id` shows it); it defaults to
`kind = "implementation"`, `ownership = "worker"` and the bottom of its section.
Each write changes only the working tree, never commits, refuses a file changed
since it was read and is undone when the resulting store does not validate. After
the batch, run `autowork tasks validate --worktree .`, then commit the task files
with the docs when authorized. `list`, `show` and `why` read the committed store
(HEAD), so confirm selection with them only after that commit. Unchanged evidence
leaves `tasks/` byte-identical on repeat.

### From gaps to tasks

1. Collect stated requirements/acceptance, planned design/ADR work, test/operations
   gaps, README promises and real owner questions. Reuse IDs. Each goal binds to
   its accepted `source` heading, priority and goal dependencies.
2. Goal status is met/partial/unmet/unverified. `met` needs every owned task done
   and an executed, passing check: `autowork tasks goal ID --status met --evidence
   "<exact command or CI job>: pass"`. Unrun tests mean unverified. Harness checks
   prove code paths, not live acceptance. Do not leave an unmet goal without an
   open task.
3. Each non-met goal gets bounded implementation work plus proof, named by outcome.
   At most one investigation/contract task per goal (`kind = "inspection"` or
   `"plan"`), only for a blocking unknown; no stacked preflights. Unverified work
   needs its check. Keep ordered open slices for remaining work (Now then Next) with
   dependencies; preserve done work. For unattended engineering, target up to three
   independently ready, accepted slices when useful work exists. Separate
   implementation/offline checks from live-device qualification: retain the live
   gate on its task, not on independent offline work. Model pre-release inputs as
   task dependencies; do not require a goal holding deployment-bound proof to be met
   before the deployment enabling it. Give each slice its own sources, acceptance,
   dependencies and ownership. Never fabricate scope, remove real dependencies,
   duplicate done work or claim device acceptance to fill the queue. Report a
   justified shortfall when fewer useful slices remain.
4. Preserve accepted focus; `--focus` on a goal requires an authorized priority
   change. Focused eligible work precedes unrelated work, still respecting
   dependencies. Use vertical implementation/recovery/platform QA. Receipts/docs
   are subtasks unless they remove a demonstrated prerequisite. A slice states
   remaining gaps; qualified/reviewed/delivered/met remain distinct.
5. Deduplicate against existing records before adding: `autowork tasks list` and
   `show` the candidates sharing a goal or outcome.

When graph analysis was used or explicitly required, include `Graph evidence:` in
the affected task's `Sources:` note: verified nodes/paths, confidence and coverage,
or the graph gap. Otherwise cite direct source evidence without inventing graph
metadata. Derive bounded outcome slices, blast radius and real prerequisites from
corroborated relationships, not graph centrality alone.

### Task contract

Each executable task has its goal, a `Sources:` note linking the exact accepted
`path#heading`, a bounded `scope` with `exclusions`, observable `acceptance`, and
separate `checks` holding the exact verification commands. Do not bury commands in
acceptance: the runner needs checks. Mark proposed fixtures and unexecuted commands
as planned; a check records the required procedure, not a passing result. List
actual prerequisite task IDs in `depends_on` (an empty list is explicit) and keep
coordination, history and prior evidence in notes. Give every executable task you
create or rewrite `touches` (its `Touches:` paths) and `resources` where needed:
widen to owning directories when unsure, or set `resources` to `exclusive` with a
`Reason:` note when no path can be bounded. Parallel Autowork admits a task beside
others only from these fields. Never list files under `tasks/` in `touches`: the
coordinator owns them.

Now is ready work; Next is accepted successors; Needs decision is owner questions
and defaults. Proposals stay outside executable Now/Next. Only typed fields grant
authority: `ownership`, `resources` and `live`. A note never grants anything. Set
`ownership = "owner"` for owner-only work, and put a task claiming the `live`
resource under Needs decision unless the owner granted `live = "authorized"`;
record who authorized which live scope and when in an `Owner decision:` note. Never
infer live authorization from accepted scope or coordinator ownership; it is the
owner's to grant. Other accepted tasks belong in Now/Next even when this docs pass
does not execute them; execution needs its own authority. Saving never launches
autowork, claims work, resumes cron or changes schedules.

### Priority

Selection takes the focus goal first, then section (Now before Next), then rank,
with goal priority and goal dependencies gating. There is no separate recorded
order: moving a task is editing its rank (`move`, `field ID rank N`) or section
(`place`). Confirm with `autowork tasks list` and `autowork tasks why ID` that the
intended tasks lead. Derive pick summaries from the selector, not hand-kept lists.
Needs decision or focus is not eligibility or live availability. "No eligible
follow-ups" requires every goal met with executed evidence; otherwise report the
actual gap.

Someone working on a task outside the runner holds it with `autowork tasks hold ID
--by WHO [--until YYYY-MM-DD]` (its `Held by:` note) and lifts the hold with
`autowork tasks release ID`. There is no in-progress status. Report held tasks
separately from new open selections, because a held task is not new work to claim.

### Put deferred qualification last

When the owner asks to leave real-world checks until the end, identify the exact
checks from the conversation and give their tasks the highest ranks in Next (or
place them in Needs decision when they need an owner); do not merely add a deferred
note. Preserve their relative order, acceptance, dependencies and access gates, and
the relative order of unrelated work. Check selection with `autowork tasks list`:
rank alone does not exclude a task from execution. Keep that deferred tail intact
during later priority changes unless the owner changes it. Do not add dependency
edges from independent implementation or fixture QA to these externally gated
checks, because that would turn an access gap into a development stop. Deferral is
neither a pass nor cancellation, and it grants no device, credential or
live-operation authority.

### Closing and retiring tasks

The engine's verified close writes `status = "done"` and its receipt in one commit;
do not repeat it. A person or planning step that closes a task without the engine
uses `autowork tasks done ID --evidence TEXT`, naming the executed check that meets
acceptance. A done task whose receipt pins another contract than its merged record
is reopened by the runner; reconcile the record, never edit the receipt.

When an accepted decision retires a task, use `autowork tasks supersede ID --by
OTHER --reason TEXT`; the successor must exist. Superseded is not done: it does not
satisfy dependencies or count toward a met goal. Owner-cancelled work without an
accepted successor is never marked done; place it in Needs decision with an
`Owner decision:` note recording the stop, and confirm with `autowork tasks why ID`
that it is not selected.

### Read-only pending-task reports

Read the store with `autowork tasks list` and `show`, enumerate open IDs in
selection order, and calculate section totals from those same IDs. Report
superseded tasks separately as history, not executable work. Within Needs decision,
distinguish unresolved owner choices or live-operation authority from accepted
scope awaiting recovery, qualification or delivery. Describe a `Held by:` note as
recorded, not as checked liveness, and state whether target identity and deployed
readiness were assessed. A listing performs no repair, transition or schedule
change. If an owner stop is not yet reflected in the store, distinguish recorded
totals from pending work after that stop, and expose the stale entry as a risk;
never silently count stopped work as authorized or claim its closeout was applied.

### Owner-stopped closeout

Read the current task and latest retained result before interpreting a close request.
If acceptance is unmet and the intended disposition is unclear, ask once whether to
stop without completion or retain the task for qualification; reuse an explicit stop
answer without asking again. Do not run additional experiments to justify
cancellation. Keep the original contract, withdraw active continuation notes and
place the task in Needs decision with the stop recorded (`place ID "Needs
decision" --decision TEXT`), or supersede it when an accepted successor exists;
never mark it done or fabricate a successor. Keep unmet goal status unmet. Run
`autowork tasks why ID` and assert it is not selectable before reporting removal
from execution. Queue exclusion does not prove an already-running worker stopped:
assess it separately when in scope and report any unverified liveness.

### Simplify execution, not acceptance

To simplify tasks or speed Autowork, give each live record one concrete next action
and remove repeated discovery or rationale; keep IDs, rank, scope, acceptance,
mandatory checks, dependencies, ownership, live gates and verified partial delivery.
Git history keeps the earlier text. Keep each `Sources:` note bound to its exact
accepted product-plan heading; a queue-simplification plan does not replace it.
Never rewrite a running worker's admitted contract. Report prose reduction, not
measured speedup. Follow
[queue compaction](references/decisive-planning.md#compact-an-existing-queue).

When asked whether tasks are necessary or may be removed, classify held work as an
owner choice, operation/target approval, technical reconciliation or dependency-only
hold; do not present all held work as a new product interview. Retire justified
obsolete or explicitly stopped work with a non-completion disposition. Retain
required behavior, distinct package/composed proof and parent acceptance records;
similar titles or a shared test window do not establish redundancy. Compare
preconditions, evidence, platform scope and dependencies before merging; prefer one
compatible observation with separate verdicts when those contracts differ. Record
the removal or retention reason in the task's notes without inventing replacement
tasks. When the owner chooses tracked children, keep the parent's ID, acceptance
and evidence as the aggregate closeout, make the parent depend on the children
(never the reverse) and give children bounded remaining outcomes. Children done is
not the parent's acceptance; `validate` refuses dependency cycles.

### Accepted-plan handoff check

After saving accepted intent and the matching tasks, check the handoff against the
actual consumer:

```sh
autowork tasks validate --worktree /absolute/consumer
autowork tasks why TASK1 /absolute/consumer
```

`validate` must pass and every requested task must be complete (no draft reasons).
After the authorized commit, `why` names the blocking rule (a dependency, focus, section, hold, draft or met
goal) or the tasks ahead of it. Put `Status: Accepted` on its own line inside the
referenced plan heading only when an actual owner decision supports it, and
explain remaining Proposed architecture on later lines. Before restoring status,
compare the whole heading subtree with the owner decision: parent acceptance or an
unchanged introduction does not approve changed or added children. Without
acceptance evidence, keep the plan Proposed and its tasks out of Now/Next, and name
the unresolved decision; never manufacture approval.

Report validation, saved paths, IDs and the eligible slice or exact blocker.
Capture each command's own exit status before a later successful command can mask
it. Do not claim an edit landed from surrounding script output when the editing
tool returned failure. Eligibility checks current dependencies, focus, section and
holds; it does not dispatch, and readiness is not implementation authorization.
Never move tasks, change focus or drop dependencies only to make a task eligible.

### Autoresearch intake and task scheduling

For `/autoresearch` findings, plans, experiments or chained handoffs, load
[the autoresearch adapter](../autoresearch/SKILL.md). Treat run logs, TSV and
`handoff.json` as evidence inputs; this skill still owns canonical documentation
and task reconciliation. Narrow Maintain records accepted findings in existing
owners and schedules bounded work with `autowork tasks add` under the matching
goal, with rank, dependencies, full acceptance/checks and preserved ownership.
Reuse matching task IDs, including held work; repeated evidence creates no
duplicates. Research recommendations do not manufacture accepted product
requirements.

Include baseline/target/units, exact Verify/Guard results, run/source references,
remaining gaps and chosen implementation/verification slices. Run the handoff check
above and report actual Now/Next eligibility. Scheduling here means ordered tasks,
not a new timer or dispatch. Continue through autowork only within existing
implementation authority; explicit audit/read-only and no-implementation limits
carry across all chained research commands.

## 6. Language, verification and report

Consult [the STE-inspired writing profile](references/ste-inspired-profile.md)
for substantive English-writing guidance when useful, not for a link or ID repair. Review literals, meaning and repository facts separately; no
translation by default or dictionary-compliance claim from sentence counts.
Use [bootstrap/idempotency regression](references/bootstrap-idempotency-regression.md)
for authorized behavioral checks; static text tests do not prove model adherence.
Run nearest contracts and requested broader gates without new tooling. Run the final
`autowork tasks validate --worktree .`, the `docs.py` checks and a repeat-pass
byte-stability check after the last document or task mutation; earlier passes do
not certify a later edit. Bind results
to tested bytes; inspect full logs/manifests, wait for suites and separate scoped
passes from unrelated failures. Partial hashes do not qualify the whole tree.
Check links/anchors/commands/keys/status/acceptance in the dirty checkout and a clean
worktree or exact candidate closure; artifacts must not hide missing targets. Inspect
the checker's scan scope and checkout completeness: a file-link checker may omit task
records or fragment anchors, and an unpopulated submodule can look like broken documentation.
Run dedicated checks for uncovered targets and verify against a closure with referenced
paths present; report pre-existing or checkout-only failures separately instead of
rewriting unrelated docs.
Label optional scratch/candidate evidence. Never execute production/destructive
procedures just to verify prose. Review scoped diffs for unsupported/unrelated edits.

Lead with changed / verified / remaining, built from the final diff and retained
receipts, not a process replay. Distinguish unchanged since this pass's baseline from
clean against HEAD. Report scope, changed owners, actual checks, gaps and eligible next task. Bootstrap
includes role/path/outcome coverage; Maintain only affected roles. Include the
changed `tasks/` paths, task and goal IDs, status counts and the validation result.
Tasks are not dispatch/delivery proof. Name language/behavior checks not performed.
For ELI5 or owner-decision summaries, lead with the everyday outcome and the exact
input needed (a safe test phone, a disposable server, or permission), not a wall of
task IDs. Separate product choices from access/authorization and missing runtime
contracts; permission cannot create an absent capability. Keep IDs in the saved
tasks or a secondary detail, and do not reopen already answered defaults.
When graph analysis was used or required, include Graphify coverage/limitations,
freshness, actual queries, source corroboration
and the evidence chain behind changed docs and tasks; graph output alone is not delivery.

## Hard-blocker coordination contract

Inspect root BLOCKERS.md during authorized Bootstrap/Maintain. Load `hard-blockers`
before entry changes; reading/respecting needs no load. Create absent canonical
Active/Resolved sections with None during bootstrap, not invented blockers: this
required empty coordination file is the no-empty-scaffold exception. Only USER_INPUT,
SUDO or USER_DECISION belong there after autonomous paths/decisions are checked;
internal engineering/review/tool issues stay in tasks. Preserve entries and
Default if no answer; reference IDs in questionnaires/tasks and continue independent
work. Change Last checked only after reevaluation. Verify resolution before moving
to Resolved; never silently delete. Explicit Audit/read-only changes nothing.
