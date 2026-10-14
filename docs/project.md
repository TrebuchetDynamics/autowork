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

## Current components

| Component | Source | Responsibility |
| --- | --- | --- |
| Hermes registration | [entry point](../__init__.py), [workflow aliases](../workflow_commands.py), [research aliases](../autoresearch_commands.py) | Discover skill folders, publish current skill IDs, register commands and route conversation arguments |
| Hermes diagnostics | [bundle](../bundle.py), [menu policy](../telegram_menu_policy.py) | Distinguish core registration from integration readiness and prioritize public commands |
| Fleet installation | [orchestrator](../setup_bundle.py), [preflight](../setup_preflight.py), [finalization](../setup_runtime.py) | Validate prerequisites, install resources/configuration, check profiles and refresh supported gateways |
| Autowork recovery | [planning decision](../skills/autowork/scripts/backlog_plan.py), [cycle](../skills/autowork/scripts/owner_cycle.py) | Return bounded recovery actions; the agent executes them and reports actual results |
| Task index and history | [goals helper](../skills/docs-sync/scripts/goals.py), [archive helper](../skills/docs-sync/scripts/todo_archive.py) | Validate and update goals.json, render TODO coverage and archive explicitly closed, ledger-done bodies under the canonical lock; open bodies and ledger history remain |
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
remain available; its plan selector routes to Plan For Me without a routing loop.
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
checks. A linked worktree needs explicit canonical targeting unless a registered
backlog authority is already bound. Stale revisions and unsafe paths are refused;
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
Ledger eligibility does not establish native admission, ownership or execution.

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
invoke the supported native handoff without a separate validation-only round trip.
The real handoff must still validate the contract internally. Do not start a fresh
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

[start_goal.py](../skills/autowork/scripts/start_goal.py) validates the contract,
ledger eligibility and source freshness during real dispatch. Reuse that boundary
and existing isolation/ownership admission instead of creating a second dispatcher,
removing validation or editing upstream Hermes. The
[owner cycle](../skills/autowork/scripts/owner_cycle.py) is the existing composition
point to evaluate before adding any new helper.

The candidate's default `owner_cycle.py --profile PROFILE --apply` path now
composes prior-work reconciliation, accepted selection/body parsing, bounded
explicit source capture, a complete contract, one real native admission call and
durable bookkeeping. See [the command contract](../skills/autowork/references/owner-cycle.md#composed-ready-preflight).
It retains the manual recovery interface, original immutable pins and unknown
usage; attempted dispatches cannot automatically restart preparation. Offline
fixtures exercise actual Git assembly and the frozen startup guard with native
calls mocked. They do not measure useful model action, savings or live delivery.

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

TOOLSET-012 owns the offline implementation: one public coordinator entry point
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
- The coordinator handles recovery and completion: reconcile original card/run,
  preserve consumed budgets and pins, use supported repair/alternate routes, finish
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

The user selected planning end-to-end recovery of the affected original tasks,
including shared fixes and supported scoped deployment, while preserving pauses
and budgets. Success means attributable implementation, required checks and review,
permitted integration and truthful task closure on those original tasks. A shared
helper commit, installed file, refreshed cron prompt or passing unrelated fixture
is an intermediate result. This planning selection does not itself run workers,
resume paused jobs, authorize publication or authorize upstream Agent edits.

Keep profile names, original card/run IDs, paths and private evidence in the existing
profile recovery receipts. The following shared work extends the existing tasks;
it creates no replacement product card or parallel product backlog. Refresh actual
card/run/process and candidate state before any execution or deployment.

### 1. Finish the held continuation candidate

TOOLSET-008 already has an independently reviewed candidate, but its integration
gate failed. The retained candidate has a 16,654-byte core skill against a strict
16,000-byte limit and an obsolete unconditional-continuation assertion. Focused
review approval remains historical evidence, not approval of an eventual correction.

- Preserve the original candidate and card. Inspect current writers and prepare
  attributable coordinator corrections in an isolated checkout of that candidate.
  Keep native worker restart, local correction, review and integration distinct.
  Do not require a done-to-running transition merely to prepare local corrections;
  this does not authorize restarting a worker or resetting its allocation.
- Move detailed mode guidance into existing references and retain a compact core
  rule. Keep the size limit and each reference reachable. Update the stale picker
  assertion to exercise caller-limited continuation; retain default-one-slice,
  explicit-stop, explicit-continuation and scheduled-limit coverage.
- Touch `skills/autowork/SKILL.md`, its existing mode/iteration references,
  `skills/autowork/scripts/test_picker_policy.py` and affected existing workflow
  tests only as needed. Reconcile the seven original candidate paths against main;
  preserve later shared repairs and dirty canonical bookkeeping.
- Run `python3 -m unittest discover -s tests -p 'test_workflow_*.py'` and, from
  `skills/autowork/scripts`, `python3 -m unittest test_picker_policy
  test_worker_role_contract test_owner_cycle test_retry_selection` on the corrected
  candidate. Then run the repository's offline integration gate once. Obtain fresh
  independent review for the corrected bytes before permitted local integration.
  If the required review/lifecycle route is unavailable, retain the verified
  correction and name that operation; never reuse approval for changed bytes.

### 2. Repair registration preparation, not the verifier's refusal

TOOLSET-017 owns the Toolset change. Current `start_goal.py` creates the native card
after freezing candidate/source inputs; the required registration needs that card's
identity, while the registry itself may already be in the immutable snapshot.
Appending the required row then invalidates the original guard. A clearer error or
more permissive prompt cannot supply the missing transition.

Plan the lifecycle as reserve without dispatch, register exact identity/scope,
freeze final startup prerequisites, verify, then release. Treat an explicitly
declared coordination registry separately from executable product inputs; never
automatically exempt arbitrary source files from fingerprinting. Use supported
native lifecycle controls and the repository's registration operation. No direct
board database writes, fabricated worker identity or unrestricted shell callback.

For an existing original card, preserve old manifests, requirement bytes, refusals
and consumed usage. A supported recovery must record the before/after prerequisite
identities and allow only the attributed registration change; it must reject
unrelated source, scope, base, ownership or runtime drift. Existing frozen runtimes
require an explicit supported migration, not replacement of helper files in place.
If the host cannot record/release that transition, report the capability unavailable
and keep native execution held. Implement and test the Toolset-side preparation
separately; do not label it end-to-end recovery.

### 3. Establish real continuation and review-rework capability

TOOLSET-018 owns the accounting/capability contract. The inspected native CLI exposes
an initial goal limit, but its `unblock` operation supplies no remaining-turn cap or
original-session selector. Its edit operation does not provide that cap either.
No verified cumulative-accounting operation is currently established for the held
tasks. Assistant-message counts and outer goal-loop counts are different units.

Before resumption, read authoritative attempt/session accounting, explicit original
allocation, retry history and unknown charges. Compute a remainder only when the
units and complete history agree. Require the runtime to enforce that remainder
on the original card and retain it across retries and review rework. A prompt,
new max-turns value, replacement session or helper-only counter is not enforcement.

Use a Toolset compatibility adapter only when the installed native runtime exposes
the needed operations. The adapter must explicitly report missing capabilities;
do not invent CLI flags or patch upstream. If unavailable, the concrete external
prerequisite is a supported runtime operation for original-card continuation with
atomic accounting/cap enforcement and, where needed, completed-card rework.
Offline adapter refusals can be tested now; native recovery remains held until
that operation and the original accounting are established. No extra allocation
is inferred from this plan or a later cron tick.

### 4. Deploy only the reviewed change to eligible selected profiles

TOOLSET-019 owns supported scoped deployment. Extend `update_bundle.py` and its
existing tests with explicit profile selection and a reviewed immutable local
source, without an implicit fetch or all-profile expansion. Retain native security
admission for installation/update; prior scanner approvals apply only to their
recorded scope. Planning source changes is not approval of a new scan override.

Preflight the complete selected change before writes: source identity and closure,
installed bytes/customizations, active helper references, affected frozen runtimes
and ownership. Stage and back up attributable changes, install through the supported
path, verify installed hashes and command registration, and record actual results
per profile. Preserve paused jobs, settings, models, delivery and budgets. Defer
active pinned consumers; a newer installation never silently migrates their cards.
Continue independent eligible profiles without touching unselected/shared active
consumers. Repeated unchanged deployment is a no-op; interruption resumes from the
original source/backup record rather than fetching a different revision.

### 5. Close the affected original work in independent lanes

The existing private recovery receipts map these lanes to the original product
tasks. Add outcomes there and in their existing task ledgers, not new product IDs.

- Registration-held work: after the original-card prerequisite transition and
  accounting are verified, resume its accepted implementation and exact acceptance,
  review and integration. Record successful initial admission and useful execution;
  a verified registration alone does not close the product task.
- Continuation-held work: use the enforced original-card remainder and corrected
  existing scope. Complete its implementation, visual/affected backend checks,
  review and integration; retain separate live qualification.
- Approved integration: refresh exact candidate/review and current target state,
  then perform authorized closeout without waiting for unrelated registration or
  continuation repairs. Source changes require affected checks and new review.
- Paused ownership: preserve the pause and original claim; recover attributable
  preview prerequisites and disposition as preparation only. No worker/schedule
  resume is implied. Report this lane as intentionally paused, not recovered.

TOOLSET-003 remains the separate disposable native recovery qualification;
TOOLSET-011 and TOOLSET-013 retain their delivery and startup-measurement scopes.
Do not make their unavailable environments prerequisites for an independent local
source correction or already-authorized integration.

Verification must cover registry changes before/after freeze, duplicate/mismatched
identity, changed product inputs, incomplete accounting, exhausted remainder,
interrupted continuation, already-running claims, completed-card review rework,
paused/unselected profiles and source changes during deployment. Use offline real
Git and native doubles for deterministic contracts, then the bounded actual native
journey when its capabilities are available. Offline success never substitutes
for original-task recovery. Report implemented, reviewed, integrated, installed,
running, qualified and intentionally paused separately.

### Execution evidence

TOOLSET-008 is complete: correction `9d1c7dc` passed the full offline inventory
(288/451/139/8 tests, two skips and eight excluded native/model modules), received
fresh independent review, and was integrated locally. Its native core is 15,960
bytes, under the unchanged 16,000-byte limit. The original native worker/card was
not restarted. Verified completed bodies are retained in TODO.archive.md.

The original reporting target is absent from this host; TOOLSET-011 remains open.
TOOLSET-003 and TOOLSET-013 still need an isolated model environment with externally
enforced spend and descendant limits. The existing containment/controller fixtures
explicitly exclude provider execution and cannot qualify those tasks.

TOOLSET-017/018/019 shared implementation is integrated in `eb72be6`: blocked
registration reservation and attributable preparation, an explicit native
continuation/accounting contract, and selected-profile local updates with native
security admission. Independent review found three defects (partial evidence
writes, shared-board ownership discovery and interrupted staging); failing
regressions reproduced each, repairs passed, and the final offline inventory
passed 318/470/139/8 tests (two skips, eight native/model modules excluded).
Concurrent consultation repairs already on main were preserved.

These source changes do not complete original-card recovery. The installed runtime
still lacks the required prerequisite migration and cumulative-cap continuation
operations/accounting. Selected-profile installation remains subject to fresh
ownership and native security admission; pauses and original budgets remain intact.

Final selected-profile preflight against clean `51d99d6` deferred three targets for
nonterminal/pinned native ownership and one for a customized Autoresearch skill.
The customization adds candidate-selection guidance and was preserved. No profile
installation, scanner override, schedule change or original-worker restart occurred.
Installation and product recovery therefore remain open in TOOLSET-017/018/019.
