# Product scope and architecture

Hermes Toolset coordinates repository planning, documentation and development.
This document records accepted scope and the current implementation. Operator
procedures belong in [installation](installation.md), [cross-host setup](cross-host.md)
and [removal/recovery](uninstall.md); outstanding work belongs in [TODO.md](../TODO.md).

## Accepted requirements

Status: Accepted

This metadata records the existing accepted workflow scope below; it does not
accept unresolved policy choices in TODO.md or authorize implementation.

- Plan With Me asks the user for missing requirements and saves accepted decisions.
- Plan For Me investigates, chooses supported approaches and records plans/tasks.
- Docs Sync maintains source-backed documents and a central TODO.md work queue.
- Autowork executes authorized work, verifies it and makes scoped local commits
  unless prohibited. Stalled preparation invokes bounded planning and retries
  execution without requiring a separate planner command from the user.
- Load supporting methods only when useful. Installation does not require every
  skill on every task. Preserve explicit exclusions, concurrent work and live gates.
- Support Hermes CLI/Telegram and native Codex/Pi packages. Runtime-specific
  workers, profiles, policy settings and external integrations stay host-specific.

These requirements derive from the repository's implemented workflow contracts,
linked in [workflows](workflows.md). Planning does not itself grant implementation,
publication or deployment authority. Prompt instructions are not a guarantee of
unattended completion; verification must distinguish dispatch, execution and delivery.

The accepted [TODO-first execution plan](#todo-first-execution-without-kanban)
is implemented: Autowork executes from repository tasks without Kanban prerequisites,
including historical-card gates. The direct execution path loads only the task
index helpers; legacy orchestration modules still ship in `skills/autowork/scripts`
as test fixtures and historical reference, and a few native admission and recovery
helpers outside the direct path (`ready_preflight.py`, `publication.py`) still import
`start_goal` from them.

## Current components

| Component | Source | Responsibility |
| --- | --- | --- |
| Hermes registration | [entry point](../__init__.py), [workflow aliases](../workflow_commands.py), [research aliases](../autoresearch_commands.py) | Discover skill folders, provision them and `skills/shared` into the profile, apply runtime defaults and cron scripts, publish current skill IDs, register commands (with `/toolset` and imported-skill aliases from [bundle](../bundle.py)) and route conversation arguments |
| Hermes diagnostics | [bundle](../bundle.py), [menu policy](../telegram_menu_policy.py) | Distinguish core registration from integration readiness and prioritize public commands |
| Fleet installation | [orchestrator](../setup_bundle.py), [preflight](../setup_preflight.py), [finalization](../setup_runtime.py) | Validate prerequisites, install resources/configuration, check profiles and refresh supported gateways |
| Autowork execution | [cycle](../skills/autowork/scripts/owner_cycle.py), [task execution](../skills/autowork/scripts/task_execution.py) | Select repository tasks and coordinate direct execution with live-writer protection; the agent implements and reports actual results |
| Task index and history | [goals helper](../skills/docs-sync/scripts/goals.py), [archive helper](../skills/docs-sync/scripts/todo_archive.py) | Validate and update goals.json, render TODO coverage and archive explicitly closed, ledger-done bodies and separately labelled superseded history under the shared Git lock; supersession does not claim completion |
| Codex package | [manifest](../.codex-plugin/plugin.json), [marketplace](../.agents/plugins/marketplace.json) | Install portable skills into Codex; no Hermes gateway or configuration dependency |
| Pi package | [manifest](../package.json), [extension](../adapters/pi.mjs) | Register native commands, expose `adapters/skills` as Pi skills and pass literal arguments to portable workflows |
| Portable behavior | [host contract](../adapters/skills/COMMON.md) | Use the current host's tools; preserve permissions, memory and credentials |

Hermes workflow commands inject a skill-loading request into the current conversation
(`/toolset` answers directly). The model performs the workflow; command registration alone does not run it. Codex
loads portable skills directly. Pi commands read adapter instructions and send a
user message, queued as a follow-up when the session is busy.

Hermes publishes every bundled skill folder except `grill-me` under its matching
source directory; the primary workflow skills are `plan-with-me`, `plan-for-me`,
`docs-sync` and `autoresearch`. The retired repo-interview and repo-docs commands
are not registered. Portable discovery exposes the same primary names; Grill Me is
a Plan With Me challenge reference rather than a separate public skill. Hermes
(`/grill-me`, `/grill_me` in Telegram) and Pi (`/grill_me`) keep a compatibility
command that opens Plan With Me in challenge mode, and Hermes still provisions the
native grill-me skill into the profile. Independent Autoresearch and all 13 selectors
remain available. In Hermes its plan selector runs Autoresearch's pinned plan protocol
with Plan For Me's planning adaptations; the Codex and Pi adapters hand it to Plan
For Me. `/plan_for_me` is the dedicated planner everywhere.
Shared protocols retain their existing helper/reference paths. Local package
discovery is distinct from model execution and cross-host live qualification.

## Interface and state contract

The [workflow registrar](../workflow_commands.py) and
[research registrar](../autoresearch_commands.py) own Hermes aliases and literal
argument routing. [Pi registration](../adapters/pi.mjs) owns portable commands.
These are conversation interfaces, not an owned HTTP service; there is no Toolset
OpenAPI contract. Collisions preserve the existing command owner, as described in
[workflows](workflows.md#commands).

The task index uses version 1 JSON with goals, tasks, IDs, statuses, dependencies
and optional milestone focus. [The helper](../skills/docs-sync/scripts/goals.py)
rejects unsupported versions, duplicate keys and inconsistent membership. Goal
completion requires executed passing evidence and all linked tasks done. Full
scope, acceptance, dependencies and ownership stay in TODO task bodies; rendering
coverage does not reconstruct those bodies or prove their acceptance.

`goals.py init <repo> --intent FILE [--todo-file FILE]` provides the first-index
interface for empty and TODO-only repositories. It reuses the version-1 schema
and consumer body checks, requires user-supplied local accepted source headings,
and preserves existing TODO/history/ownership/focus rather than inferring intent.
Equivalent existing state is a byte-preserving no-op; conflicts require explicit
maintenance, not overwrite. Run formatting, validation, rendering and consumer
readiness separately. See the
[executable initialization path](../skills/docs-sync/references/document-scaffold.md#first-task-index-initialization).

Ledger operations share a Git-common-directory advisory lock and support revision
checks. Commands target the requested checkout, including linked worktrees;
explicit canonical targeting selects another checkout of the same repository.
Historical native backlog bindings are ignored. Stale revisions and unsafe paths are refused;
cooperating locks do not prevent an uncoordinated direct writer. See
[concurrent maintenance](../skills/docs-sync/references/concurrent-maintenance.md).

Rendering also selects the established archive and moves only explicitly closed,
ledger-done bodies. Review both TODO and that archive after rendering, preserve
historical bytes and verify unchanged second-pass output. Ambiguous or conflicting
completion metadata stays live. See the
[archive contract](../skills/docs-sync/references/todo-archive.md) and
[offline checks](testing.md#archive-and-ownership-regression-checks).

Setup, upgrade, migration and removal procedures remain with the
[installation runbook](installation.md) and [recovery guide](uninstall.md).
Preview success is not rollback protection. The task-index initialization helper
does not initialize installer/runtime stores or add live qualification.

## Data and trust boundaries

Repository documents and task state belong to the target project. Hermes runtime
receipts and profile stores belong to the configured Hermes home; do not commit
private runtime state. The portable packages do not configure those stores.
See [memory](memory.md) for Hermes capture/storage behavior and
[dependencies](dependencies.md) for source pins and licenses.

Hermes runtime defaults intentionally change approval settings; portable adapters
do not. Preflight prevents installer-stage writes on prerequisite failure, but
CLI plugin loading can occur before preflight and later setup failures are not
transactionally rolled back. [Installation](installation.md#preflight-before-fleet-writes)
is the authoritative boundary description.

## Planned work and verification

[TODO.md](../TODO.md) owns implementation priorities. Its open entries describe planned
changes; completed entries record bounded local results and qualification limits.
The [goals.json](../goals.json) index mirrors the current queue and retains completed
task history. TOOLSET-002's first-time initialization interface is independently
reviewed and integrated locally; its bounded completion evidence is in
[the archive](../TODO.archive.md). TOOLSET-003 retains live recovery qualification.
Historical completion notes are not new executed proof.
Ledger eligibility does not establish live ownership, execution, review or product qualification.

[Testing](testing.md) owns executable checks and their limits. Clean installation,
model execution, Telegram delivery and task completion are distinct acceptance
claims. Offline helper tests do not establish any of those live outcomes.

## Faster ready-task startup

Status: Accepted

The user selected earlier useful implementation with less preparation/tool chatter,
then explicitly selected the faster ready-task path as the default. This acceptance
covers that startup outcome, not parallel execution, weaker verification, or a
changed continuation policy. TOOLSET-012 is independently reviewed and integrated
locally; its completion evidence is in [the archive](../TODO.archive.md).
Measured native qualification remains pending in [TOOLSET-013](../TODO.md).

### Outcome and scope

For a task with accepted intent, complete body and usable sources, perform one
batched coordinator preflight, derive the handoff from the existing body, and
use the current-session execution boundary without a separate validation-only
round trip. The actual boundary must still validate the task contract internally;
no Kanban handoff or card-state transition is required. Do not start a fresh
planning/documentation pass or load optional methods on the normal ready path.
Deeper preparation is a fallback only for an observed missing/conflicting input,
source drift, ownership conflict, failed admission, or a genuinely ambiguous task.
Retain pending review/integration/recovery reconciliation before selecting new work.

Use a compact status when dispatch is established; keep routine source/check/contract
details in private receipts. A queued card is not useful implementation or proof
of its startup guard. Reports must distinguish queued, admitted, first useful
worker action, failed/held startup, and completed tasks. Errors and required user
actions remain visible; less chatter must not hide a failure.

### Evidence and decision

[Autowork](../skills/autowork/SKILL.md) already says to reconcile once, use runnable
backlog without a fresh docs pass and delegate deep investigation to the worker.
[Delivery batching](../skills/autowork/references/delivery-batches.md) already
prescribes compact readback and source-bound check reuse. The observed manual
coordinator path still required separate source capture, hand-written contract,
validation-only invocation, real dispatch and status bookkeeping. This is evidence
of orchestration overhead, not a measured universal runtime bottleneck.

TOOLSET-012's reviewed historical baseline composed native preparation and a frozen
startup guard; its recorded fixtures mocked native calls and did not measure
useful model action, savings or live delivery. Retain that evidence in
[the archive](../TODO.archive.md), not as a current requirement to call the retired
native handoff.

The [current owner cycle](../skills/autowork/scripts/owner_cycle.py) selects and
coordinates direct repository execution. Use its
[current-session contract](../skills/autowork/references/owner-cycle.md#current-session)
for actual owner identity and source-bound checks. An `EXECUTE` result is a contract
for this session, not an implicit worker launch or useful implementation. Preserve
real writer protection and explicit limits; measured qualification remains open.

Decision: Make the ready path default, compose reusable existing controls, and
move detailed routine readback into receipts. Reason: fewer model/tool round trips
before implementation while retaining the current refusal and review boundaries.
No opt-in fast mode, new schedule, extra parallel worker, relaxed budget, skipped
review, speculative caching or model/provider change is included.

### Worker contracts and engineering protocols

These additional user requirements belong to TOOLSET-012's accepted implementation:

- Give workers a short task-specific execution contract. Include objective,
  scope/exclusions, current evidence, acceptance/checks, ownership, immutable source
  and budget/stop conditions; reference supporting detail rather than injecting the
  whole routing/lifecycle reference. Load routing guidance only for a concrete
  technique-selection need. Shortness must not remove an executable admission guard
  or require the worker to guess a missing constraint.
- Support exact selection of one engineering protocol without a mandatory phase
  bundle or automatically appended protocols. Phase bundles remain optional and
  supported for existing explicit callers. No protocol is required for a task whose
  instructions/checks are already sufficient. Selected protocols and applicable
  support files remain bound to the vendored hashes; omission of unrelated guidance
  is not permission to skip an integrity check.
- Keep selection, dispatch, recovery, ownership, budgets, review, completion and
  publication authority in Autowork. Engineering protocols provide guidance for
  specific techniques; upstream automatic planning/commit/ship language cannot
  create a competing coordinator, approval ceremony or broader authority.
- Preserve all required tests, independent review, active-writer protections,
  canonical authority, source freshness, vendored integrity and task/commit identity
  checks. A smaller prompt or router response is not evidence those gates passed.

At requirement capture (`f617808`),
[the engineering adapter](../skills/engineering/SKILL.md) already called itself
guidance rather than a coordinator, but
[its router](../skills/engineering/scripts/route.py) required a phase and prepended
that phase's protocol list. Exact single-protocol selection and conditional routing
guidance are now implemented and independently reviewed.
[Vendor/routing tests](../tests/test_engineering_vendor.py),
[workflow-cycle tests](../tests/test_workflow_cycle.py) and the offline suite passed;
provenance and upstream protocol bytes are preserved. TOOLSET-012's composed
candidate is independently reviewed and integrated locally; see
[its archived completion evidence](../TODO.archive.md). These offline checks do not
establish live worker or scheduled execution.

### Task context simplification

At task-context simplification, the user requested simpler tasks for faster
Autowork execution. The five then-pending IDs stayed unchanged: TOOLSET-003,
TOOLSET-011, TOOLSET-012, TOOLSET-013 and TOOLSET-008.
The compact [TODO.md](../TODO.md) bodies stated the remaining action, acceptance,
checks, exclusions, dependencies, ownership and next step directly. This was an
editorial simplification, not reduced scope or weaker completion criteria; the
completed TOOLSET-008/012 bodies now reside in [the archive](../TODO.archive.md).

Research baseline: those five task bodies contained 1,524 words; the compact bodies
contain 1,082 words (29.0% fewer), measured by whitespace-separated words excluding
headings, navigation and generated coverage. This measures task-context reduction,
not a proven runtime speedup. No model/native timing experiment was run here.

Decision at simplification: remove repeated rationale/lifecycle prose, point to
accepted contracts for detail, and avoid redoing TOOLSET-012's reviewed
engineering-guidance slice. Keep user ordering, ledger state/dependencies and
completed history intact. At that point, TOOLSET-012's original worker/contract
remained assigned and TOOLSET-013 waited for it. TOOLSET-012 is now reviewed and
integrated; TOOLSET-013 waits for its isolated native/model environment, not another
implementation. TOOLSET-008's policy correction is reviewed, integrated and
archived. The remaining live gates are not simplification targets. Planning alone
changes no code, dispatch, schedule or budget.

### Acceptance and measurement

TOOLSET-012's completed offline implementation required one public coordinator entry point
performs normal ready-task preparation/dispatch, derives all required handoff
fields from authoritative task context, and does not invoke a separate
validation-only command, planner, docs audit, full suite or optional skill loader
before dispatch. Missing required scope/acceptance is a bounded diagnostic/fallback,
not a fabricated contract. Real admission still checks current source, dependencies,
canonical authority, ownership, immutable base and original worker-start guard.
Tests exercise ready, stale, held, missing-context and interrupted-handoff cases.

TOOLSET-013 owns runtime qualification after implementation. Measure separately
coordinator request-to-handoff, queue wait, admission, and first useful worker
action (first scoped test/reproduction or implementation operation after admission,
not heartbeat or card creation). Compare the current manual route and composed
route against the same disposable task, source, model, environment and cold/warm
condition. Record elapsed time, coordinator tool/model round trips, user-visible
routine messages, exact receipts and failures. An offline fixture can verify the
composition, not actual model startup or universal latency.

The required improvement is fewer coordinator preparation round trips and routine
messages on the ready path, with source-bound comparable runtime evidence showing
no startup-latency regression. No absolute time target or percentage improvement
was requested or measured. Investigate contradictory timing instead of claiming
success from a lower command count alone. Runtime runs need an isolated configured
environment with externally enforced spending/descendant limits; absence of that
environment does not block independent offline implementation.

### Ordered work and exclusions

Within this accepted goal: first TOOLSET-012 implements and offline-verifies the
composed default path; next TOOLSET-013 measures and qualifies it. Existing queue
priorities and leases are preserved; continuation policy is now specified in
[Autonomous execution authority](#autonomous-execution-authority), not left as a
routine permission question. Planning saves documents and backlog only: it does
not dispatch, commit, push, modify live profiles/jobs or claim faster operation.

## Autonomous execution authority

Status: Accepted

The user directed planning to handle complexity and Autowork to execute quickly,
with more freedom and no repeated permission requests to do already-authorized
work. The planner chooses the following operating policy under that delegation;
this does not claim the user separately selected a new batch count or live authority.

- Planning resolves consequential design, decomposition, interfaces, migration and
  acceptance before handoff. Supply a short executable contract with the remaining
  outcome, sources, checks, exclusions and actual stop conditions. Do not hand the
  worker an unresolved design interview or a mandatory skill/planning phase chain.
- Autowork executes the accepted outcome. It decides reversible implementation
  details, fixes tests/fixtures and user-space tooling, reconstructs attributable
  local inputs, and changes a failing approach on the same task without asking to
  proceed or restarting planning. Preserve accepted behavior and record material
  deviations. Complexity, a first test failure or a missing fixture is work, not
  a permission blocker. Do not add agent-invented inspect-only or one-rerun limits.
- The coordinator handles recovery and completion: reconcile the original TODO
  task and retained source/workspace evidence, preserve consumed budgets and pins,
  use supported repair/alternate routes, finish
  reviewed local closeout, and continue eligible non-overlapping work when one
  operation is held. No repeated unchanged audit or profile-wide blocked verdict.
- Keep required tests, independent review, ownership, source/integrity checks and
  actual approval controls. Run discriminating checks while editing; reuse only
  matching receipts and run required changed-input/final gates once. A transport
  interruption means observe the existing check, not start it again or call it passed.
- Escalate only an actual missing external input/authority or consequential product
  conflict that the accepted outcome cannot resolve. Name the exact held operation
  and input once; retain its resume step and continue independent accepted work.
  Do not bypass real pending approval, fake credentials/evidence, seize a live
  writer, reset exhausted budgets, or infer money/deployment/destructive authority.

Continuation decision: Existing caller scope and saved stop/batch limits control
execution. Recurrence authorizes the saved occurrence, not extra budgets or wider
scope. The current job's at-most-one-new-batch limit stays unchanged; authorized
closeout and work inside that batch need no extra approval. An already explicit
multi-batch/whole-spec mandate continues within its existing limits. This resolves
TOOLSET-008's operating-policy question without another user permission round.

Evidence: [iteration rules](../skills/autowork/references/iteration-and-decisions.md)
already instruct workers to fix failures and choose routine details;
[owner recovery](../skills/autowork/references/owner-cycle.md) makes external-owner
mode optional. The current queue had one policy-gated task and separately scoped
live-environment qualification tasks. Actual runtime blocking frequency was not
measured. Concurrent instruction edits are evidence inputs, not proof of delivery.

Execution slice: [TOOLSET-008](../TODO.archive.md#toolset-008--make-autowork-continuation-authority-consistent)
now aligns these semantics across native/portable instructions and generated worker
contracts, with regression cases for autonomous fixes, known recovery, explicit
stop limits, pending review/approval and exhausted allocation. Reuse existing
controls; add no permission framework or extra review lane. Keep native/model
qualification distinct from offline policy tests. This planning pass saves the
accepted policy and task only; it launches no implementation or new timer.

## End-to-end original-task recovery

Status: Accepted

Recover the existing product work through its TODO.md contract, accepted scope,
checks and attributable candidate evidence. Shared helper delivery, installation,
actual execution and product acceptance are separate outcomes. The later accepted
[TODO-first decision](#todo-first-execution-without-kanban) supersedes native-card
registration, release and continuation as prerequisites; it does not waive tests,
independent review, real live-writer protection or explicit task/caller limits.

### Current frontier

- TOOLSET-008's continuation correction is reviewed, integrated and archived. Do
  not repeat its earlier failed size/picker gate or restart its old worker.
- TOOLSET-017/018 delivered bounded offline changes in `eb72be6`, but their remaining
  native-card-only requirements are explicitly superseded by TOOLSET-026, not
  completed. Their exact unchecked acceptance and historical evidence remain in
  [the archive](../TODO.archive.md). No missing Kanban operation blocks current
  repository work, and no native acceptance pass is inferred from supersession.
- TOOLSET-025/026/027 implement current-session execution, recovery from attributable
  filesystem/Git evidence and card-independent deployment guards. Use the
  [current execution interface](../skills/autowork/references/owner-cycle.md), not
  the retired handoff or a board-state transition. Adopt retained work only after
  checking actual process identity and overlapping workspace/source changes.
- TOOLSET-019's reviewed scoped local updater is integrated; selected-profile
  installation is still pending. Reuse the implementation and its source-bound
  checks. Preflight the intended immutable local source, actual consumers and
  customized skills; back up, apply through the supported path, and read back
  installed hashes and registration only under existing deployment authority.
  A historical card or old preflight deferral is not a current ownership veto.
- TOOLSET-020/021/022's delivery-readback corrections are integrated. Refresh the
  exact review/candidate and current local/remote evidence before acting. Do not
  repeat a merge or reopen a completed task merely because an older report said
  integration was pending. Direct-main evidence needs its actual permitted policy;
  protected-PR requirements remain mandatory where they apply.

### Remaining verification and operating limits

TOOLSET-003 retains the bounded disposable model-driven recovery journey;
TOOLSET-013 retains paired useful-action startup measurement. Both require their
configured isolated environment and real external limits. The local no-agent
journey in [TODO-first qualification](#todo-first-delivery-qualification) does not
satisfy model acceptance or prove a speedup. TOOLSET-011 retains the original
reporting environment and actual Telegram-delivery checks; do not substitute a
new profile, schedule or message for that target.

Preserve existing product task IDs, dirty candidates, input-matched check receipts,
required independent review and publication restrictions. Unknown usage is not
zero; a recurring occurrence does not replenish an exhausted explicit allocation.
A supported runtime upgrade may be considered only for an actually required,
demonstrably supplied capability, without custom upstream patches. It is not a
mandatory repair for retired Kanban prerequisites and is not authorized by this
documentation pass.

The owner's stop-all scheduling instruction remains in force. Preserve stopped
and paused schedules; installation, migration and documentation do not authorize
resumption. Intentionally paused product work stays paused. Missing attributable
preview/source/ownership evidence holds its operation, not unrelated local work.

The superseded native-card design is preserved verbatim in the
[historical snapshot](../TODO.archive.md#superseded-native-card-recovery-design).
It records prior intent and failed/unchecked evidence, not current dispatch steps.

## TODO-first execution without Kanban

Status: Accepted

Decision: The user wants TODO.md and its repository documents to be the work board
so any developer can join through ordinary Git/project tools. On 2026-10-14 the
user explicitly authorized disregarding Kanban, including old cards. This selects
card-free Autowork for new work and recovery, not an optional Kanban backend.
Implemented in the TODO-first delivery: direct execution, live process coordination,
card-independent recovery, scoped installation guards and contributor/cron guidance.
Offline checks and isolated native script execution are qualified; model-driven
production runs and external message delivery are separate outcomes.

### Authority and scope

- TODO.md owns task identity, intent, scope, acceptance, dependencies and visible
  progress; goals.json remains its synchronized machine index, not another board.
  Verified completed bodies move to TODO.archive.md with evidence retained.
- Cron determines when the existing authorized agent runs. The current session
  executes a bounded useful slice directly, using host-native delegation only
  when useful and authorized. Audits, maintenance and substantial implementation
  do not require a Kanban card, board, assignee or native task-state transition.
- Old cards may be ignored for task selection, recovery, review and integration.
  No mandatory board lookup, card import, card release, native continuation API or
  same-card registration is a prerequisite. Unavailable Kanban is not a blocker.
- Preserve actual work, checks and explicit user constraints. Inspect real process
  and workspace activity rather than treating a historical card as a lease. Do not
  kill workers, delete worktrees, archive native cards or reset budgets to migrate.
- These requirements supersede the native-card-specific remaining direction in
  the earlier end-to-end original-task recovery plan and TOOLSET-017/018. Preserve
  their shipped results and failed/unchecked evidence; do not claim their old
  native acceptance passed. Reconcile obsolete queue entries during implementation
  with an explicit supersession disposition, never fake completion or keep an
  obsolete native prerequisite as the next action. TOOLSET-019's safe deployment
  intent remains, but card status alone must cease being a deployment veto.

### Evidence and diagnosis

At planning time, `skills/autowork/scripts/owner_cycle.py::run_locked` reconciled a retained
native handoff before selection and could return `BLOCKED` without selecting a TODO
task. `skills/autowork/scripts/reconcile.py` calls
`continuation_capability.assess(None)`, while
`skills/autowork/references/historical-owner-cycle.md#original-card-continuation-capability`
explicitly documents the missing binding. These are concrete native-integration
holds; they do not establish that every historical failure came from Kanban.

The portable `adapters/skills/autowork/SKILL.md` already coordinates execution in
the current host session without requiring cards. Use that simpler model across
hosts. [Hermes cron documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/cron)
separately supports agent sessions and script-only jobs; cards are not required by
the scheduler. Documentation inspected on 2026-10-14 is external reference, not
qualification of this installation or the planned execution path.

### Minimal execution contract

Use the existing TODO task ID everywhere. The implementation should retain only
necessary private execution data: canonical repository/workspace identity, actual
worker/session identity and liveness where available, source/candidate revision,
explicit runtime limits and known usage, last verified check/review receipts, and
next action. Reuse existing suitable receipts; no mandatory second task registry,
card-shaped state machine, mirrored product statuses or board synchronization.
Private state is coordination/evidence, never the product requirement authority.

Coordinate automated writers across profiles and Git worktrees for the same
canonical repository. Use actual process identity plus workspace/source inspection
before adopting idle work; elapsed time or a stale PID alone cannot prove release.
Use supported local locks and isolated worktrees where needed. Document that manual
writers ignoring an advisory lock and different hosts require separate coordination;
do not pretend local filesystem locks provide distributed exclusion.

Preserve explicit task/caller budgets and the host's real execution limits. Repeated
cron ticks do not replenish a user's exhausted task allocation. Unknown usage is
not zero, and a receipt or prompt cannot enforce spending. Use the current host's
bounded invocation/delegation controls; do not create a new universal lifetime-task
budget requirement just to emulate cards. An unavailable enforcement capability
holds only the operation requiring that explicit cap. Read-only inspection and
already-authorized local verification/integration are separate from worker launch.

Required acceptance tests, independent review where required, source-bound receipt
reuse, serialized integration and publication authority remain. Neither a completed
session nor a checkbox alone proves acceptance. Future execution cannot depend on
native Kanban review reassignment or a card becoming `done`.

### Delivery sequence and acceptance

1. TOOLSET-025 implements the direct execution path and its bounded ownership/check
   contract. Fail the test if any default-path Kanban API/CLI/board access occurs.
   A TODO-only repository must work without Hermes/Kanban setup; an existing index
   stays supported. No extra required public file or tracking tool for contributors.
2. TOOLSET-026 removes legacy-card recovery and deployment vetoes. Test absent,
   malformed, blocked, done and mismatched historical cards without querying or
   changing them. Preserve dirty candidates and detect actual overlapping writers.
   Adopt an idle candidate only from attributable filesystem/Git/check evidence;
   reuse matching checks and rerun invalidated/required ones. Explicit allocation
   exhaustion remains a real limit, unrelated to card status.
3. TOOLSET-027 aligns skills, docs, task-index supersession, cron prompts and scoped
   rollout with that same path. Preserve paused jobs, exact task filters, delivery,
   existing publication limits and the newly activated cron self-repair bindings.
   Do not force every invocation into planning, audits or delegation. A contributor
   follows README/AGENTS/TODO, makes a scoped change, tests and submits normal review.

Required regression journeys: ready TODO to first useful action with zero Kanban
calls; concurrent manual/cron writers; interrupted check reuse and stale-check
invalidation; crash before versus after a write; repeat tick without duplicate
work; review-requested changes and integration without native card transitions;
old-card-unavailable recovery; explicit cap/exhaustion; paused-job preservation;
TODO/archive/index agreement and unchanged second pass. Retain failure evidence.

Run focused offline checks, the safe `python scripts/check.py` inventory and
independent review for the exact candidate. The delivery passed these offline
checks and independent review, including repairs found during review.
Qualify a bounded disposable cron journey separately with an available configured
host and real runtime limits; no product/production test target or duplicate schedule
is implied. Report source delivery, configured rollout, actual execution and
Telegram delivery separately. Rollback preserves candidate/receipt bytes and pauses;
never silently reactivate Kanban prerequisites or recreate old cards.

### Non-goals and remaining uncertainty

Do not edit upstream Hermes Agent, repair consumer product code, discard cards or
candidates, weaken tests/review, expand publication/live authority, reset allocations,
or build another Kanban implementation. No optional Kanban backend is planned.
No further product-choice question remains. Exact host limit/liveness interfaces
and migration race behavior require implementation research and qualification;
they are not reasons to repeat the product interview or wait for a Kanban API.

### TODO-first delivery qualification

The direct entrypoint selects repository contracts without loading native dispatch
or reconciliation. Tests cover missing/malformed old handoffs, TODO-only and indexed
repositories, worktree/profile contention, actual process identity, preserved dirty
candidates, command failure/timeout, explicit allowance exhaustion, detached child
cleanup, named-plan/dependency binding and source/executable freshness. Generic
command receipts record execution, not reusable acceptance or task completion.
The Linux runner uses process birth identity and advisory Git-common-dir locks;
manual writers and other hosts still require explicit coordination.

The scoped installer observes all current direct repository leases for a profile
and actual helper consumers; it never queries historical boards. Docs Sync permits
normal branch-local worktree edits under the shared lock and ignores old native
backlog bindings. Superseded TOOLSET-017/018 requirements retain their exact unchecked
bodies and failed/unchecked history in the archive, with explicit successor links.
No superseded requirement is counted as done or used to satisfy dependencies.

An isolated native no-agent cron journey implemented a fixture, ran its acceptance
check, reused matching check evidence, rejected changed-input evidence and archived
the completed TODO body. A repeat run did not implement it again. Native scheduler
qualification uses the real job store, due-job selection, claim, script execution
and local result recording; unrelated upstream worktree garbage collection is
disabled in that isolated harness. No production job, product repository, provider
call or Telegram delivery is part of this qualification. Profile installation and
future model-driven scheduled behavior must be reported separately.

## TODO-owned task priority

Status: Accepted

Decision: On 2026-10-14 the user accepted that TODO.md order is the human priority
authority and goals.json is the execution index. Synchronization is explicit and a
disagreement is never silently resolved in favor of stale ledger order. Before this
change, `eligible()` ranked by focus, section, goal priority, goal status and task
ID, so a human reorder in TODO.md did not change selection when goals.json existed.

### Ordering contract

- The ledger records `priority_order`: a schema version and the last-reconciled
  TODO.md sequence of unfinished task IDs. It captures human intent, not the
  scheduler's resulting order; focus and dependencies affect which task runs but
  never rewrite it.
- Selection precedence is focus, section, recorded human order, then goal priority
  as a fallback for tasks absent from the record. Dependencies remain mandatory.
- One shared guard serves every selection entry point. When the current TODO.md
  sequence of unfinished IDs differs from the record (moved, added, missing or
  duplicated IDs; prose and coverage edits are ignored), default selection returns
  `PRIORITY_DRIFT` with the IDs involved, never a ready result for the old order.
  Explicitly named tasks and an owner's active claim are not interrupted.
- A ledger without `priority_order` keeps legacy selection and reports a visible
  `UNMIGRATED` flag with the bootstrap command. Selection never rewrites files.

### Reconciliation and bootstrap

- `goals.py reorder` records the current TODO.md order under the shared lock and
  revision guard. It writes only goals.json, refuses missing or duplicated bodies,
  and reports focus or dependency constraints that keep the human's first pick from
  running first. Scheduled Autowork invokes it on drift before selecting new work.
- `goals.py bootstrap-order` is a one-time, versioned migration. It ranks every
  unfinished task by the legacy order (section, goal priority, goal status, ID,
  excluding focus and dependencies), moves whole task blocks within their groups
  without changing their contents and records the snapshot. A group is a `##`
  section or a `###` heading inside it that is not a task's own ID heading; deeper
  headings move with their task, and blocks never cross a group. It refuses a changed first eligible pick and lists every deeper
  eligible-order change in the dry run for review. On 2026-10-14 the user accepted
  group-aware bootstrap, including one repository's design-review task moving
  from 31st to 34th of 37 eligible tasks. A matching repository gets the snapshot without a TODO.md
  rewrite. `--dry-run` reports every proposed move and the revision token that the
  apply step requires. An existing record makes bootstrap a no-op; disagreement
  never reruns it.
- New task bodies are inserted where they are intended to rank.

### Rollout

Offline implementation and regressions come first and modify no consumer
repository. The separately authorized fleet migration dry-runs each repository,
locks and verifies unchanged inputs, migrates, validates, compares the next pick
before and after, and commits locally per repository without push. Preserve all
stopped/paused jobs under the owner's later stop-all instruction; a successful
migration does not authorize resumption. Failed repositories remain deferred.

## Checkable core-document completeness

Status: Accepted

Decision: On 2026-10-14 the user approved recording two Docs Sync improvements as
bounded tasks: a machine-checkable document role manifest and repository-type
role profiles. Today Docs Sync's core-document completeness, link and command
checks, and drift detection are prose instructions that only an agent applies;
`goals.py` has no equivalent for documents. This acceptance covers offline helper,
skill-reference and regression work; it does not accept a particular manifest
path or authorize rewriting consumer repositories.

- A tracked manifest records each document role's path (or combined section),
  outcome status, covered source paths and last-verified commit. Helper checks
  report broken local links/anchors, documented repository commands that do not
  exist, and roles that are neither mapped nor recorded as not applicable.
- A staleness check lists roles whose covered source paths changed after their
  last-verified commit. It reads Git history only and never rewrites documents.
- Repository-type profiles (service, library, CLI/plugin, application,
  infrastructure) declare baseline roles, so applicability is not re-decided on
  every run. Reference (commands/configuration), glossary, troubleshooting and
  installation/upgrade become explicit roles where a profile needs them.
- Absent a manifest, Docs Sync keeps its current prose behavior; adoption is
  opt-in per repository and never creates empty documents.

Implemented: TOOLSET-030 to TOOLSET-032 added `docs.py validate|check|stale|profiles`
(goal DOCS-COMPLETENESS met on offline evidence). The manifest defaults to
`docs/roles.json` (`--manifest` overrides it); this repository uses that path.

## Reliability bug harvest (2026-10-15)

Status: Accepted

Decision: On 2026-10-15 the user asked for a high-ROI bug harvest using this
repository's own Plan For Me, Docs Sync and Autowork workflows. Five read-only
investigations covered the task index and archiver, the all-profile updater, setup
and installers, the Autowork helpers and the plugin runtime. Every finding below
was reproduced against a fixture; the top tier was re-reproduced by the planner.
Ranking (impact × likelihood ÷ fix cost), task grouping and the fix approaches are
the planner's calls; offline regressions are the acceptance bar and no live
qualification is implied.

| Rank | Task | Bug | Impact |
| --- | --- | --- | --- |
| 1 | TOOLSET-043 | One loose checklist line anywhere in TODO.md, or `Dependencies: None.` followed by prose, makes Autowork refuse runnable tasks | Blocks real fleet repositories now |
| 2 | TOOLSET-044 | Writer detection misses the installed `hermes` launcher (`python3 -I -c … hermes_cli …`) | A live writer can be overlapped |
| 3 | TOOLSET-045 | Setup ignores `apply_runtime_defaults: false` and turns approval prompts back off | Silently reverses a security opt-out |
| 4 | TOOLSET-046 | A profile folder sharing a bundled skill's name without `SKILL.md` makes plugin load raise | Every bundled command disappears |
| 5 | TOOLSET-047 | CRLF or trailing-space `##` headings fail section checks; `render` deletes `###` content under a legacy Goal coverage heading | Refused init/backlog; silent data loss |
| 6 | TOOLSET-048 | Chat update status reports a reaped-never zombie or killed updater as running forever; a symlinked Hermes home refuses chat updates | Wrong update status |
| 7 | TOOLSET-049 | Setup's bounded YAML readers reject Hermes-written configs (indentless lists, `{}`, BOM, empty sections) and a stray profile symlink aborts setup/update | Blocks full setup |
| 8 | TOOLSET-050 | Telegram menu healing misreads `.env` inline comments and odd chat IDs and stops at the first failing chat | Menus silently not healed |
| 9 | TOOLSET-051 | `docs.py check` false positives on footnotes, commented-out links and `~/` script paths | False documentation findings |

Lower-ranked reproduced findings stay recorded here for later tasks: merged local
skill edits reported as drift on the next update (larger fix), `Label:` sub-bullets
replacing the `Acceptance:` field, archiving unindented section prose with the
preceding checkbox task, `check_receipt` timeout tracebacks and wrapper bypass of
the shell-status guard, nested worktrees blocking the parent checkout, `/toolset`
argument case sensitivity, executable-bit removal not propagated, malformed
`facts.json` tracebacks and untracked leftover skill folders aborting installs.

## Vendored UI Taste skill

Status: Accepted

Request (user, 2026-10-15): add the `ui-taste` skill that `npx skills add
https://uizze.sh/` installs, vendored into this repository from the Uizze GitHub
repository as one single skill named `ui-taste`.

Findings:
- `uizze.sh/.well-known/skills/index.json` publishes `ui-taste` (v0.2.0, 16 files)
  and `ios-design`. Uizze's `skills/` folder on `main` no longer contains either: per
  its DISTRIBUTION.md they are domain-only. A complete GitHub mirror existed at commit
  `afd703a14a5db5f2fe6c2860badbe811058aa9e5` (`skills/ui-taste/`, removed in
  `8a97121` the same day).
- At that commit `SKILL.md`, `agents/openai.yaml`, LICENSE, NOTICE and all eight
  playbooks plus `references/uizze-reference-policy.md` are byte-identical to the
  domain copy fetched on 2026-10-15; only packaging metadata differs (`MANIFEST.json`,
  which the commit records with per-file origins, `MODIFICATIONS.md` and
  `CHECKSUMS.sha256`). All 16 files are plain, non-executable Markdown/JSON/YAML.
- License: Apache-2.0 with NOTICE attribution to Impeccable (Paul Bakaus, 4.4.0) and
  ehmo's MIT platform-design-skills; Uizze's repository root is MIT. The playbooks
  are adaptations of Impeccable 4.4.0, which this bundle already ships as 4.5.2.
- The skill works offline; it mentions an optional paid Uizze MCP
  (`find_ui_references`, `find_ui_materials`) and links a remote banner image.

Planner's calls (reversible; reject any of them):
- Source of record is the immutable commit `afd703a`, not the mutable domain; its
  16 files are copied byte-for-byte with an `UPSTREAM.json` (repository, revision,
  path, license, sha256 per file) and a recorded domain cross-check.
- Vendor only `ui-taste`. `ios-design`, `anti-ui-slop`, `ui-design`, `ui-radar`,
  `image-to-ui` and `uizze-ui` are not added.
- Keep the bundled Impeccable alongside it; no routing change between them.
- Vendor unmodified, like Impeccable. Toolset configures no Uizze MCP connection and
  never runs `npx` during install, setup or update; the paid MCP stays optional as
  the skill itself states.
- Refresh through a documented `git show <revision>:skills/ui-taste/<file>` procedure
  verified by a hash test, not a new vendoring script.
- Expose it on Codex and Pi like the other workflows (explicit-only Codex policy, Pi
  command `/ui_taste`); it is not added to the Telegram menu priority. Superseded
  2026-10-15: the user chose to advertise `/ui_taste` and `/beautify_github_readme`,
  then `/impeccable` and `/lgtm`, then `/engineering`, `/git_commit_push` and
  `/git_pull_merge`, in the bundle's menu priority, displacing the last seven
  built-ins at the default 60-entry cap. `/git_pull_merge` was retired the same day
  when Git Pull Merge merged into Git Commit Push, so six are advertised.

Anti-goals: rewriting upstream text, fetching anything at runtime, adding an MCP or
account dependency, or presenting the vendored copy as an endorsement by Uizze or
the Impeccable author.

## README design skill (2026-10-15)

Status: Accepted

Decision: On 2026-10-15 the user asked to add
[oil-oil/beautify-github-readme](https://github.com/oil-oil/beautify-github-readme)
(MIT, pinned at `d6562a5f5c484d069f8560b39c215c9cda4b5a55`) to the bundle, vendor
it, adapt it to this toolset, and then use it on this README. The layout follows the
engineering pack: a toolset-owned `SKILL.md` adapter, the upstream skill byte-exact
under `upstream/` (its `SKILL.md` renamed `PROTOCOL.md` so it is not registered as a
second skill), and `UPSTREAM.json` with file hashes checked by a test. The repository's
showcase images, translated READMEs and Codex agent manifest are excluded.

Adapter rules (planner's calls): commands are `/beautify-github-readme` and
`/beautify_github_readme`; README text is documentation whose claims stay verified
through Docs Sync, so `docs.py check` runs after README edits; pure SVG is the default
because Hermes has no bundled image-generation skill; the upstream attribution and
showcase offer is never made unsolicited; scheduled or Autowork-driven runs only
audit unless their task scope authorizes edits; delivery uses the repository's
normal commit workflow. A Codex/Pi adapter ships with the explicit-only policy.

| Task | Outcome |
| --- | --- |
| TOOLSET-060 | Vendor and adapt the skill with provenance, tests and docs |
| TOOLSET-061 | Visual refresh of this README with a project-native hero and workflow diagram |

## New skill review (2026-10-15)

Status: Accepted

Decision: On 2026-10-15 a read-only review of the two newly vendored skills (UI
Taste and Beautify GitHub README) against Hermes' skill loader, linter and the
portable packages found the issues below. The user asked to record them and fix the
first two. Every finding was reproduced; the fix approaches are the planner's calls.

| Task | Finding | Fix |
| --- | --- | --- |
| TOOLSET-062 | Beautify's vendored `audit_readme.py` misses a missing dark-mode `<picture><source srcset>` image and reference-style images (`![x][ref]`), and wrongly reports root-relative `/assets/…` and `<path with spaces>` images as missing | A toolset audit script beside the adapter that reuses the upstream SVG checks; the adapter runs it instead of the upstream one |
| TOOLSET-063 | UI Taste ships its upstream `SKILL.md` directly, so Hermes gets no toolset rules (scheduled runs, paid Uizze tools, Impeccable precedence) and indexes it by a 276-character description truncated to *"Give your coding agent better UI taste. Build and polish ..."* | Move the pinned files byte-exact under `upstream/` (`SKILL.md` becomes `PROTOCOL.md`) behind a toolset adapter, the Beautify layout |
| TOOLSET-064 | Hermes' skill index keeps 57 characters of each description; nine other bundled skills lose their trigger phrase | Recorded, not scheduled: trigger-first descriptions of at most 60 characters |

UI Taste adapter rules (planner's calls, replacing the earlier "no routing change
between them" call): load one design skill per task, the one the user names; an
unnamed UI request uses UI Taste, and Impeccable stays the choice for its own
commands (`/impeccable …`, design-context setup and its detector). Scheduled, cron
or Autowork-driven runs use only the read-only audit playbook unless their task
scope authorizes UI edits. The paid Uizze tools are used only when the host already
exposes them; Toolset never configures the MCP, asks for an account or token, or
sends private code in a query.

Also observed and left unrecorded: the repository has no `.gitattributes`, so a
Windows checkout that converts line endings would fail every vendored-file hash test.
Windows is not a documented target.

## Claude Code package (2026-10-15)

Status: Accepted

Decision: On 2026-10-15 the user asked for support for installing hermes-toolset
skills in Claude Code. It ships as a Claude Code plugin marketplace at the repository
root, exposing the same 13 portable adapters as Codex and Pi.

Findings (Claude Code 2.1.300 and its plugin documentation):
- A `skills` path in `.claude-plugin/plugin.json` adds to the default scan of the
  plugin's root `skills/` folder, which here holds the Hermes-only skills. A
  marketplace entry with `"source": "./"` and a `skills` list replaces that scan;
  an isolated install confirmed only the 13 adapters load.
- Marketplace installs copy the whole repository into Claude Code's plugin cache, so
  adapter links into `skills/` keep resolving.
- Claude Code and Pi both honor `disable-model-invocation: true` in skill frontmatter.

Planner's calls (reversible): one marketplace and plugin both named
`hermes-toolset`; no hooks, agents, MCP servers or settings; every adapter carries
`disable-model-invocation: true`, so Claude Code matches the Codex explicit-only
policy and Pi skills also stop being selected automatically (Pi's registered
commands read `SKILL.md` directly and are unaffected); the host contract names all
three portable hosts; manifest versions stay equal across Claude Code, Codex and Pi.
A live Claude Code workflow run stays a separate task.

| Task | Outcome |
| --- | --- |
| TOOLSET-065 | Claude Code marketplace and plugin manifests, explicit-only adapters, tests and docs |
| TOOLSET-066 | Run one questions-only workflow in a real Claude Code session from the installed plugin |

## Test-suite optimization method (2026-10-15)

Status: Accepted

Request (user, 2026-10-15): add a way to optimize and minimize test suites that fits
the Hermes Toolset pipeline, considering Matt Pocock's
[TDD skill](https://github.com/mattpocock/skills/blob/main/skills/engineering/tdd/SKILL.md).

Findings:
- The engineering pack already pins Addy Osmani's `test-driven-development` protocol.
  Pocock's TDD skill (MIT) overlaps it, requires confirming test seams with the user
  before any test is written, and calls `codebase-design` and `code-review` skills that
  are not bundled. Nothing bundled covers redundancy, mutation scores or test cost.
- `scripts/route.py` resolves only protocols listed in the pinned `UPSTREAM.json`, so a
  toolset-written protocol needs its own entry point.
- Measured baseline on `75fb76f`: `python3 scripts/check.py` runs 1,247 offline tests
  (455/575/209/8) in 242 s wall time, directories one after another.
  `skills/autowork/scripts` takes 146 s; `test_delivery_state.py` holds 10 of its 15
  slowest tests (about 40 s). coverage.py 7.13.5 and pytest 8.3.3 are installed;
  no mutation tool is. The suite runs once per checkout, not once per profile.

Planner's calls (reversible; reject any of them):
- Do not vendor Pocock's TDD skill. Credit and adapt two of its ideas in toolset words:
  reject tautological assertions, and test at public seams. Seams are chosen by the
  worker within Autowork's scope, never by a user confirmation step.
- Add one toolset-owned protocol, `test-suite-optimization`, under
  `skills/engineering/local/`, selected with `route.py --protocol` like pinned ones. No
  new slash command, coordinator or task file.
- The protocol audits first and changes nothing; each consolidation, removal or speed-up
  becomes its own TODO.md task executed by Autowork. Fewer tests is never the goal:
  coverage (lines and branches) and, when available, mutation score of the touched
  modules must not drop, and named regression tests are kept.
- Redundancy evidence comes from coverage.py per-test contexts, which are installed.
  Mutation testing is optional: run a tool such as mutmut only from a disposable
  environment outside the repository, never as a repository dependency.
- Apply it to this repository first; run `check.py` directories concurrently as the first
  measured speed-up because it changes no test.

Anti-goals: deleting tests to make a run pass or to hit a count, weakening an assertion
to keep a merged test green, a second TDD method that competes with the pinned one, or
a required network or paid tool.

| Task | Outcome |
| --- | --- |
| TOOLSET-067 | The `test-suite-optimization` protocol and its engineering routing |
| TOOLSET-068 | Measured audit of this repository that records bounded follow-up tasks |
| TOOLSET-069 | `check.py` runs its test directories concurrently with ordered output |
| TOOLSET-072 | Cache `check_receipt.runtime()`'s package inventory and executable hash safely |
| TOOLSET-073 | Subprocess coverage, then evidence-based review of identical and subset groups |

### Baseline audit (TOOLSET-068, 2026-10-15)

Method: the `test-suite-optimization` protocol, audit only, on commit `376f7ed`, this
machine, offline inventory of `scripts/check.py` (97 modules; excluded native modules
stay out). Raw output stayed in a scratch directory.

| Measure | Result |
| --- | --- |
| Tests | 1,253 (461 `tests`, 575 Autowork scripts, 209 Docs Sync scripts, 8 Git Commit Push); 1 skipped |
| Sequential run, `--jobs 1`, 3 passing runs | 225 s, 225 s, 237 s |
| Per directory (unittest's own time, 3 runs) | `tests` 26–27 s; Autowork 132–139 s; Docs Sync 37–43 s; Git Commit Push under 0.1 s |
| Default parallel run (TOOLSET-069) | 164–175 s; bounded by the Autowork directory |
| Coverage of toolset Python sources (coverage.py 7.13.5, branch, tests and vendored `upstream/` omitted) | 67% of 9,370 statements and 4,040 branches combined |
| Tests with per-test coverage records | 760 of 1,253; the rest reach code only through subprocesses or check text |
| Identical covered-line sets | 58 groups, 187 tests |
| Strict subset of a sibling in the same class | 248 tests |
| Mutation score | Not measured; no tool installed and none added |

Findings:
- **Cost, not redundancy, dominates.** `test_delivery_state.py` (23 tests) holds 9 of
  the 15 slowest tests. Profiling it (110 s under cProfile) attributes about 42 s to
  `check_receipt.runtime()` building `packages` from `importlib.metadata.distributions()`
  (449,000 email-header parses) and 7 s to re-hashing `sys.executable`, on every call
  before and after each check. Subprocesses take about 9 s. The same code runs in
  real Autowork check receipts, so its cost also scales with the host's installed
  packages in production.
- **Identical coverage is mostly not duplication.** The largest groups read so far
  (`test_owner_cron` prompt tests, `test_update_bundle` historical-board veto tests)
  each assert different required text or a different board state through one shared
  helper. They are cheap and distinct contracts; none is recommended for removal.
  The other groups and the 248 subset cases are unverified leads.
- **Subprocess blind spot.** 493 tests have no coverage record because the code they
  exercise runs in child processes, so redundancy evidence is missing exactly where
  many slow tests live. Any removal here first needs subprocess coverage.

Follow-up tasks: TOOLSET-072 (cache the receipt runtime inventory without losing
in-check drift detection) and TOOLSET-073 (measure subprocess coverage, then review
the identical and subset groups). No consolidation task is recorded until that
evidence exists.

## Gentler update rollout (2026-10-15)

Status: Accepted

Request (user, 2026-10-15): improve the update pipeline, preferring less force.

Findings from the 2026-10-15 rollouts (Telegram menu changes TOOLSET-070/071/074):
- Every applied update requested `hermes gateway restart` at once. Hermes then waits
  up to `agent.restart_after_turn_timeout` (1800 s) for chat turns before forcing,
  and gives running cron jobs only `agent.cron_drain_timeout` (30 s). At 11:50 the
  drain timed out with 3 cron jobs in flight: they survived as external workers,
  but Hermes skipped its SessionDB checkpoint and clean-shutdown marker and
  recovered on startup.
- Small updates produced four gateway restarts in about an hour (10:49, 10:55,
  11:46, 11:50); one restart reloads every profile.
- Seven profiles link `plugins/hermes-toolset` to the canonical checkout and three
  use pinned clones. Any restart deploys the checkout's current state to the linked
  seven, including another writer's unreleased commits (`/git_pull_merge`
  disappeared there before any update rolled it out), while the clones change only
  through an update.
- `hermes toolset update --check` during another update returns that run's
  `running` record with no owner or wait; the result stays `gateway_restart:
  requested` after the restart finished, without the new PID or whether each bot
  re-sent its menu.
- Hermes publishes `active_agents` in `gateway_state.json` (busy contract:
  `derive_gateway_busy`), and each profile's `cron/external-workers/` lists running
  cron runs.

Planner's calls (reversible; reject any of them): an updater-requested restart waits
for a quiet gateway (no active agents and no running cron workers) instead of
relying on Hermes' forced drain, and reports `deferred` rather than forcing when no
quiet window comes; restarts coalesce so a burst of updates causes one restart;
linked profiles are reported and can opt into pinned clones so a restart never
deploys unreleased checkout state; status records the restart outcome. No Hermes
code or global timeout changes.

Revised while implementing TOOLSET-075: "quiet" means no chat or API turn in flight,
not "no cron run". A 45-minute sample on 2026-10-15 (10:25–11:10) found 14 cron runs
overlapping with no gap of even 30 seconds, so a cron-free wait would never restart.
Cron runs execute in Hermes' restart-safe external workers and keep Hermes'
documented restart behavior; chat turns are what Hermes interrupts after its wait.
The updater subtracts claimed cron runs from `active_agents`; unknown activity
counts as busy.

| Task | Outcome |
| --- | --- |
| TOOLSET-075 | Restart the gateway only in a quiet window; never trigger a forced drain |
| TOOLSET-076 | Coalesce restarts across a burst of updates |
| TOOLSET-077 | Record the restart outcome and menu resends in the update status |
| TOOLSET-078 | Report a concurrent update clearly instead of returning its record |
| TOOLSET-079 | Report linked profiles and offer pinned clones so restarts deploy only released code |

## OMH catalog trim (2026-10-15)

Status: Accepted

Request (user, 2026-10-15): after a fleet audit found OMH's review and verification
guidance in real use but no demonstrated value from the rest of its catalog, keep OMH
selectively and plan trimming its footprint.

Findings:
- Hermes Toolset installs OMH 3.0.0 with `omh setup --full` (`plugins/defaults.json`
  `omh.full: true`), so 9 profiles register all 142 OMH skills. Hermes lists every
  registered skill in each request's skill index; the audit sampled 11,832 characters of
  OMH/ULW index entries per prompt.
- Recorded `skill_view` loads across all profiles' session databases: 295 loads of 29
  distinct OMH skills; 113 were never loaded. Top: `code-review` 126, `verification-gate`
  58, `automation-blueprint` 22, `visual-qa` 12, `mobile-release` 12, `web-research` 7,
  `release-cut` 6, `agent-instructions` 5, then 21 skills with 1–4 loads each.
  Corrected during TOOLSET-080: OMH skills register under their SKILL.md names, which
  differ from catalog names for some (`context` is `ulw-context`, `browser-operator` is
  `omh-browser`). Counted by registered name, 364 loads hit 35 distinct skills, adding
  `browser-operator`, `command-operator`, `product-docs`, `research`, `ultrawork` and
  `voice-operator`.
- `omh setup --core` keeps only five core skills (`agent-ops-review`, `cancel`, `doctor`,
  `oh-my-hermes`, `skill`) and drops `code-review` and `verification-gate`.
  `omh capability-policy disable <family>` only stops OMH recommending a family; it
  writes `files_removed=False`, so the skills stay in Hermes' index and the context
  cost is unchanged. Both used skills sit in `delegate_coding_and_ship` (37 skills).
- Hermes' prompt builder omits skills named in `skills.disabled`
  (`agent/prompt_builder.py`, `get_disabled_skill_names`). Hermes Toolset's setup
  currently resets `skills.disabled` and `skills.platform_disabled` to empty in every
  profile, so a trim made there would be undone by the next setup; plugin load and
  `/toolset update` do not touch them.
- Nine profiles use OMH as their memory provider; the provider is the OMH plugin, not
  these skills.

Planner's calls (reversible; reject any of them):
- Trim through Hermes' `skills.disabled`, not by deleting OMH files or switching to
  `--core`: it is per profile, reversible, leaves OMH's install, memory provider and
  doctor checks intact, and keeps `--full` so OMH updates stay simple.
- Keep list: every OMH skill loaded at least once (35 by registered name), the five core
  skills and the `retain_knowledge` family (`memory-new`, `memory-sync`, `decision-recall`,
  `wiki`), 41 in all. Record it in `plugins/defaults.json` as top-level `omh_keep_skills`
  (the `omh` block must keep exactly the keys `install-omh.py` validates); every other
  OMH-managed skill (101 of 142) is disabled. Re-measure usage before widening or shrinking it.
- Hermes Toolset owns only the OMH entries it adds: setup and runtime defaults merge them
  with the user's own `skills.disabled` entries instead of resetting the list, and drop
  only managed entries that are no longer OMH skills or are now kept. The existing
  runtime-defaults opt-out disables the trim.
- Qualify on one profile with a paused cron first, then roll out with `/toolset update`.

Anti-goals: uninstalling OMH, touching the memory provider or its stores, deleting OMH
files, removing a user's own disabled-skill entries, or judging the trim by catalog
size instead of the measured index and unchanged review/verification use.

| Task | Outcome |
| --- | --- |
| TOOLSET-080 | Managed OMH trim through `skills.disabled`, applied by setup, plugin load and update |
| TOOLSET-081 | Live qualification on one profile, then fleet rollout with before/after index size |

## Parallel Autowork (2026-10-15)

Status: Accepted

Request (user, 2026-10-15, delegated with `/plan_for_me`): evolve Autowork into one
coordinator with several workers. The coordinator picks independent eligible tasks
from TODO.md/goals.json, runs each in its own Git worktree and branch, integrates the
results one at a time, and marks a task done only after the integrated result passes
validation. Sequential Autowork must keep working as it does today. Core principle:
parallelize independent implementation, not repository authority.

Owner addition: task worktrees are temporary. Verified results must reach the
canonical default branch (`main` or `master` as actually configured), followed by
removal of finished owned task and integration worktrees. Many active worktrees
are acceptable; abandoned finished worktrees are not the desired steady state.
Preserve active, dirty, locked, unmerged and recovery-bearing worktrees, and report
integration or cleanup pending rather than falsely claiming full closeout. Apply
the [worktree closeout contract](../skills/autowork/references/worktree-closeout.md)
to sequential and parallel work. This adds no push authority or bulk deletion of
historical worktrees. TOOLSET-088-a7 owns remaining automated parallel integration/
cleanup; TOOLSET-090-2d owns its host documentation. Their existing statuses and
runtime qualification remain unchanged by this instruction update.

Findings (source as of `89549d2`):
- `goals.py eligible()` already returns every eligible task in priority order
  (focus, section, recorded TODO order, goal priority), but it keeps `in_progress`
  tasks. `task_execution.select()` walks that list and returns only the first task
  that passes its contract checks (unique Scope/Acceptance/Checks, dependencies done
  in TODO, archive or ledger, TODO/ledger agreement).
- `task_execution.execute()` holds one repository lease,
  `<git-common-dir>/autowork-execution/active.json`, under `writer.lock`; a live lease
  returns `BUSY`. Owner liveness is `/proc` identity (PID, start ticks, boot ID), with
  no heartbeat; a dead owner's lease is superseded. Processes carrying
  `HERMES_TOOLSET_EXECUTION_COMMON` count as Autowork and block every worktree.
- `BUSY` already suggests an isolated worktree (`<parent>/<repo>-autowork-<TASK>`,
  branch `autowork/<TASK>`), and `--writers` gates merging back. There is no merge
  helper: integration is manual Git. `delivery_state.integration_state()` verifies
  ff or two-parent merges and recomputes conflict-free merges with `merge-tree`.
- TODO bodies have no file or resource field; `Scope:` is prose.
  `disjoint_fallback.verify()` compares declared path prefixes but is tied to old
  native cards.
- `goals.py` mutations run under a repository-wide `flock` shared by all worktrees,
  with `--expected-revision` guards.
- Hosts: all four supported hosts have a headless CLI that can run one worker in a
  given folder. Hermes: `hermes chat --query-file F --oneshot --in DIR
  --run-budget S`. Codex: `codex exec -C DIR`. Pi: `pi -p`, run with the worktree as
  its working directory. Claude Code: `claude -p`, but unattended runs need a
  permission mode, which would change the user's approval policy. Hermes'
  in-process `delegate_task` copies the parent's cwd and has no per-child folder; its
  `delegation.worktree_isolation` creates its own worktrees from HEAD, outside
  Autowork's records. `references/accepted-plan-execution.md` still says delegation
  never creates worktrees.

Decisions (all planner's calls; reversible; reject any of them):
- **Entry point.** `owner_cycle.py REPO --parallel N` (and `/autowork --parallel N`,
  or "parallel N" in free-text hosts) turns on parallel mode. Without it nothing
  changes. N defaults to 2 when the flag has no number and is capped at 4 unless
  `--max-workers` raises it (hard limit 8). It never starts more workers than there
  are runnable independent tasks.
- **Workers are separate host CLI processes**, not in-process subagents. The helper
  starts each one in its worktree from a host template, in its own process group,
  and records its PID identity. A live PID is how ownership is proven: a lease held
  by a live worker never expires. Shipped templates: `hermes`, `codex`, `pi`.
  Claude Code coordinators fall back to sequential mode unless the user passes their
  own `--worker-command`, because a template would have to pick an approval mode for
  them. Any coordinator can pass `--worker-command` (JSON argv with `{worktree}`,
  `{prompt_file}`, `{timeout}` placeholders). Without a usable template or Linux
  `/proc`, parallel mode reports `SEQUENTIAL_FALLBACK` with the reason and returns
  the ordinary single-task contract.
- **Workers never select tasks.** A worker gets a generated, self-contained prompt
  with its one task body, worktree, branch, baseline commit and rules. The prompt
  does not load the Autowork skill, to avoid recursive selection. Rules: edit only
  inside the worktree; never edit coordinator-owned files; commit locally once;
  never push, merge or touch another worktree; write `report.json` (commit, changed
  files, checks run with results, blockers, one proposed CHANGELOG line). Workers may
  use their host's own subagents, but may not start other workers.
- **Coordinator-owned files:** TODO.md, TODO.archive.md, goals.json and CHANGELOG.md.
  Only the coordinator writes them, after integration. A worker change to any of them
  holds that task's integration.
- **Independence is declared, then checked.** New optional task fields:
  - `Touches:` a comma list of repository paths, directory prefixes ending in `/`,
    or globs.
  - `Resources:` tokens such as `port:8080`, `db:test`, `network`, `live`, `exclusive`.

  Two tasks may run together only when all of these hold:
  - neither depends on the other, directly or transitively;
  - both declare `Touches:`, and their path sets do not overlap;
  - they share no resource token;
  - neither has `live` or `exclusive`;
  - neither touches a serial path. Serial paths are package manifests, lockfiles,
    migration and schema folders, and CI workflow files.

  A task without `Touches:` runs alone. When a worker reports, its actual
  `git diff --name-only baseline..commit` must stay inside its `Touches:` and must
  not overlap work that is running or already integrated in this run. Otherwise
  integration is held and the task is retried alone after the others.
- **Priority is preserved.** Each free slot first considers the highest-priority
  runnable task. If that task can run alone only, or conflicts with running work,
  no lower-priority task is dispatched. The pool drains, and the top task then runs
  by itself. Lower-priority work fills slots only beside compatible higher-priority
  work.
- **Repository lease and journal.** These live under
  `<git-common-dir>/autowork-execution/`:
  - `coordinator.json`: one live coordinator per repository. It holds the owner
    identity, workspace, profile, maximum workers and start time.
  - `slots/<TASK>.json`: task, worktree, branch, baseline, worker identity, state
    and report.
  - `journal.jsonl`: append-only events with timestamps.

  All writes happen under the existing `writer.lock`. A sequential claim returns
  `BUSY` while a live parallel coordinator exists, and the reverse is also true.
  Worker processes do not carry `HERMES_TOOLSET_EXECUTION_COMMON`, so they don't
  block the coordinator. Slot states: `dispatched`, `running`, `reported`,
  `integrating`, `integrated`, `closed`, `held` (reason), `interrupted`, `released`.
- **Recovery is idempotent.** A new coordinator, run in either mode, first
  reconciles every slot:
  - Live worker: adopt it and keep waiting. Never start a duplicate.
  - Dead worker with a commit: queue the task for integration.
  - Dead worker with uncommitted changes: mark `interrupted` and preserve the
    worktree. Restart once in the same worktree with a resume note; a second
    failure becomes `held`.
  - Clean worktree with no commit: release the task back to the queue.

  A worker that exceeds `--worker-timeout` (default 3600 s) has its process group
  stopped and becomes `interrupted`. A failed worker never removes another worker's
  result.
- **Worktrees** use the existing convention, `<parent>/<repo>-autowork-<TASK>` on
  branch `autowork/<TASK>`, created from the canonical HEAD recorded as the slot
  baseline. Existing user branches or worktrees with those names are refused rather
  than reused unless the slot journal shows Autowork created them. Clean integrated
  worktrees are removed. Held, interrupted and failed ones are kept for diagnosis.
  Each worker gets its own `TMPDIR` under the slot and `AUTOWORK_SLOT` /
  `AUTOWORK_PORT_BASE` (20000 + 100 × slot) for tests that open ports.
- **Integration** happens in a coordinator-owned integration worktree, one task at
  a time, in priority order among reported tasks:
  1. Verify the commit descends from the baseline, the changed files and the report.
  2. In the integration worktree, detach at canonical HEAD and run
     `git merge --no-ff autowork/<TASK>`. A conflict aborts the merge and holds the
     task.
  3. Run the coordinator's validation argv (task checks plus a combined regression)
     through the existing bounded `--run` runner.
  4. Fast-forward the canonical checkout with `git merge --ff-only` only if its HEAD
     has not moved. If it moved, redo the merge once on the new HEAD. Git's own
     refusal protects dirty files.

  `--parallel-close TASK` then runs `goals.py task TASK done` and the archive step
  only for an `integrated` and validated slot. The coordinator edits the TODO body
  and CHANGELOG and commits that metadata. A refill follows, so dependents (task C
  after A) become eligible only after A closes.
- **Resource gate.** No new worker starts while `MemAvailable` is below
  `--min-free-mem-mb` (default 1500 per running worker plus one), or while the
  1-minute load average is at or above the CPU count. Such a slot waits rather than
  failing. Token or provider spend is not metered: unknown usage is not zero, so the
  only caps are wall time (`--worker-timeout`, Hermes `--run-budget`) and the
  number of workers.
- **Observability.** `--parallel-status [--json]` prints the coordinator table:
  workers active/maximum, and per task the state, worker slot, worktree, elapsed
  time, blocked reason, checks, commit and integration state. It also prints run
  metrics computed from the journal: total wall time, worker time, integration time,
  waiting or blocked time, peak workers, conflicts and retries. `--wait --timeout S`
  blocks in the helper until a worker exits, so the coordinator spends no tokens
  polling.
- **Authority is unchanged.** Workers and the coordinator make local commits only.
  There is no push, deployment, history rewrite or remote integration without the
  existing explicit authorization. A worker's successful exit is never completion.

Builder-check answers (planner's calls, 2026-10-15):
- **Worker permissions.** Templates never add flags that bypass approvals or
  sandboxes. Hermes workers use the profile's own approval settings (Toolset-managed
  profiles already run unattended). The Codex template keeps the host's approval
  policy and adds only scoped write roots: the worktree and the Git common directory.
  A host whose worker cannot commit under those limits gets no template and falls
  back to sequential mode. `--parallel` output lists each worker's command, so the
  permissions in use are visible.
- **The slot is the claim.** Dispatch does not write TODO.md or goals.json; tasks stay
  `open` until `--parallel-close`. Sequential runs see parallel work through the
  coordinator lease (`BUSY`). A task already `in_progress` without a slot (left by a
  sequential run) is never dispatched. Its `Touches:` count as running work. If it
  has no `Touches:`, no task is dispatched beside it, and the status reports why.
- **Retries.** An `interrupted` slot (dead worker with uncommitted changes, or a
  timeout) restarts once in the same worktree and branch with a resume note (attempt
  2). A `held` slot (conflict, files outside `Touches:`, coordinator-owned file,
  failed validation) waits until no worker is running, then gets one fresh attempt:
  new branch `autowork/<TASK>-r2` and worktree from the current canonical HEAD.
  The first attempt's branch and worktree are kept. After a second failure the slot
  stays `held` and the task goes to Plan For Me's fix-or-skip, as for any blocked task.
- **Validation runner.** Factor the bounded process core (subreaper, timeout,
  descendant cleanup, receipt) out of `command()` into a function that takes a
  working directory. The sequential `command()` keeps calling it, and its output is
  tested byte-identical. Integration validation runs in the integration worktree
  under the coordinator lease only: no `active.json` is written, and `writer.lock`
  is held only for state writes, not for the whole run.
- **Worker profile and model.** Hermes workers run in the coordinator's profile with
  its default model; `--worker-profile` may override that. TOOLSET-091-00 checks
  that concurrent sessions in one profile behave.
- **Owner proof.** `--apply --parallel` requires `--owner-pid` of the persistent
  coordinator session, like sequential `--apply`. Every refill, wait, integrate and
  close call passes the same PID, and `coordinator.json` records that identity.
  A run with no persistent ancestor gets `ACTION_REQUIRED`.
- **Memory gate.** Dispatch needs `MemAvailable` ≥ `--min-free-mem-mb` ×
  (running workers + 1).

Anti-goals: a second task board, remote queue or database; in-process subagent
fleets without per-worker folders; dispatching lower-priority work ahead of a
runnable higher-priority task; treating per-worktree test passes as combined
correctness; automatic conflict resolution or rebasing worker branches; parallel
mode changing the default single-task behavior; claiming LLM-worker speedups from
the controlled benchmark.

Remaining uncertainty (resolved during implementation, recorded in task evidence):
the exact Codex sandbox flags that allow commits from a linked worktree (its Git
directory is outside the worktree), and Pi's prompt-file argument. Both are verified
against the installed CLIs before their templates ship. Templates that cannot be
verified stay out of the default list.

| Task | Outcome |
| --- | --- |
| TOOLSET-085-1a | Select several runnable tasks and decide which can run together (`Touches:`/`Resources:`, serial paths, priority-preserving fill) |
| TOOLSET-086-9f | Repository coordinator lease, worker slots, journal and idempotent slot recovery |
| TOOLSET-087-32 | Worktree creation, worker prompts, host CLI templates, resource gate, timeout, wait and refill |
| TOOLSET-088-a7 | Sequential integration through an integration worktree, validation, guarded close |
| TOOLSET-089-72 | Status table and metrics, end-to-end A/B/C fixture, sequential-versus-parallel benchmark |
| TOOLSET-090-2d | Skill, adapter, README and workflow/cross-host/testing docs; compatibility and fallback tests |
| TOOLSET-091-00 | Live qualification with real host workers on a disposable repository |

## Continuous Pi runner (2026-10-15)

Status: Accepted

Request (user, 2026-10-15): a copyable script that runs Autowork continuously
through the Pi coding agent, one bounded Pi run per task, with GPT-6.1 Sol
(`openai-codex`) as the primary model and DeepSeek V4.1 Flash (`openrouter`) as the
fallback, idling without model calls when no task is runnable.

Review findings that shaped it: Autowork's portable instructions look for new work
when nothing is ready, so the runner selects the task itself with `goals.py next`
and names it; Pi's JSON mode exits 0 on a failed model response, so the runner reads
the events; extension commands queue their prompt, so the runner uses the documented
`/skill:autowork`; local locks do not coordinate with Hermes Autowork cron jobs.

Owner's decisions: ship the script in this package and target the caller's
repository (a copy still targets its own repository); TODO-only repositories get
`--once` only; refuse when a Hermes Autowork cron job targets the same repository;
the fallback has the same authority as the primary, and each run records its model.

| Task | Outcome |
| --- | --- |
| TOOLSET-093-01 | `scripts/pi-autowork.sh`, fake-Pi tests and the usage guide |
| TOOLSET-094-65 | Qualify fallback switching and a multi-task continuous run live |

## Backlog replan (2026-10-15)

Status: Accepted

Every change below is the planner's call; the owner may reject any of them.

The owner asked to list the pending tasks and replan them where needed. Findings
from the repository, candidate branches and the installed hosts:

- Two tasks already have reviewed candidates that only need integration:
  TOOLSET-064 (`autowork/TOOLSET-064`, eight trigger-first descriptions) and
  TOOLSET-082 (`autowork/TOOLSET-082`, the Hermes 0.22-compatible OMH pin). Both
  moved to the top of Next.
- TOOLSET-082 mixed an offline pin with a live refresh of installed profiles. The
  refresh is split into TOOLSET-098-5d, which needs owner approval to change
  installed plugins. A newly created profile shows the cost of waiting: its
  old OMH plugin makes Hermes refuse to enable the Toolset there.
- TOOLSET-097-41 records a Pi runner defect the toolset cron found: one Pi test
  fails when the checkout path contains `/profiles/`. Another session's `pi-par`
  worktree has uncommitted edits to the same files, so the task tells the next
  coordinator to check that writer first.
- TOOLSET-013 measured the native `start_goal` admission path, which Autowork no
  longer uses; it is superseded by TOOLSET-091-00, which times real host runs.
- TOOLSET-019's deployment outcome was met by fleet-wide `/toolset update` runs;
  only the selected-profile updater mode remains to qualify once.
- TOOLSET-066 can run now: `claude --plugin-dir` on a clean clone of the published
  commit loads the plugin for one session without a marketplace install or settings
  change. It still needs owner approval for the short model run.
- TOOLSET-003 no longer needs an externally capped model endpoint: the owner
  accepted an owner-observed host session bounded by the host's run budget.
- Unchanged and waiting on the owner or an external environment: TOOLSET-091-00
  (owner-observed real workers), TOOLSET-096-7e (owner picks a fleet repository),
  TOOLSET-029 (stop-all instruction), TOOLSET-011 (original host and profile gone).
- Not planned: the profile-local skill edits kept by `/toolset update` are
  agent-learned lessons; the one in the toolset profile is already being ported by
  another session.

New priority order: 064, 082, 097-41, 072, 073, 066, 091-00, 003, 098-5d, 019,
096-7e, 029, 011. The first five are offline work Autowork can do without new
authority.
