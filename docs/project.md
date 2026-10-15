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
including historical-card gates. Legacy orchestration is retained only as a test
fixture and historical reference, outside the distributed execution path.

## Current components

| Component | Source | Responsibility |
| --- | --- | --- |
| Hermes registration | [entry point](../__init__.py), [workflow aliases](../workflow_commands.py), [research aliases](../autoresearch_commands.py) | Discover skill folders, publish current skill IDs, register commands and route conversation arguments |
| Hermes diagnostics | [bundle](../bundle.py), [menu policy](../telegram_menu_policy.py) | Distinguish core registration from integration readiness and prioritize public commands |
| Fleet installation | [orchestrator](../setup_bundle.py), [preflight](../setup_preflight.py), [finalization](../setup_runtime.py) | Validate prerequisites, install resources/configuration, check profiles and refresh supported gateways |
| Autowork execution | [cycle](../skills/autowork/scripts/owner_cycle.py), [task execution](../skills/autowork/scripts/task_execution.py) | Select repository tasks and coordinate direct execution with live-writer protection; the agent implements and reports actual results |
| Task index and history | [goals helper](../skills/docs-sync/scripts/goals.py), [archive helper](../skills/docs-sync/scripts/todo_archive.py) | Validate and update goals.json, render TODO coverage and archive explicitly closed, ledger-done bodies and separately labelled superseded history under the shared Git lock; supersession does not claim completion |
| Codex package | [manifest](../.codex-plugin/plugin.json), [marketplace](../.agents/plugins/marketplace.json) | Install portable skills into Codex; no Hermes gateway or configuration dependency |
| Pi package | [manifest](../package.json), [extension](../adapters/pi.mjs) | Register native commands and pass literal arguments to portable workflows |
| Portable behavior | [host contract](../adapters/skills/COMMON.md) | Use the current host's tools; preserve permissions, memory and credentials |

Hermes commands inject a skill-loading request into the current conversation. The
model performs the workflow; command registration alone does not run it. Codex
loads portable skills directly. Pi commands read adapter instructions and send a
user message, queued as a follow-up when the session is busy.

Hermes publishes `plan-with-me`, `plan-for-me`, `docs-sync` and `autoresearch`
from their matching source directories. The retired repo-interview and repo-docs
commands are not registered. Portable discovery exposes the same primary names;
Grill Me is a Plan With Me challenge reference rather than a separate public skill.
Pi retains `/grill_me` compatibility. Independent Autoresearch and all 13 selectors
remain available; its plan selector runs Autoresearch's pinned plan protocol with
Plan For Me's planning adaptations, and `/plan_for_me` is the dedicated planner.
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
  section or a heading inside it that is not a task's own ID heading; blocks never
  cross one. It refuses a changed first eligible pick and lists every deeper
  eligible-order change in the dry run for review. On 2026-10-14 the user accepted
  group-aware bootstrap, including bravo's TASK-002 moving
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

Open question: manifest location (default: `docs/roles.json`, reusing an existing
docs index when present).
