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
The [goals.json](../goals.json) index now mirrors the open queue, including the
Needs decision policy gate. TOOLSET-002 owns independent review and integration of
the first-time initialization interface described above; offline helper execution
does not close its canonical task before review. Historical completion
notes remain in TODO and its established archive; they are not new executed proof.
Ledger eligibility does not establish native admission, ownership or execution.

[Testing](testing.md) owns executable checks and their limits. Clean installation,
model execution, Telegram delivery and task completion are distinct acceptance
claims. Offline helper tests do not establish any of those live outcomes.

## Faster ready-task startup

Status: Accepted

The user selected earlier useful implementation with less preparation/tool chatter,
then explicitly selected the faster ready-task path as the default. This acceptance
covers that startup outcome, not parallel execution, weaker verification, or a
changed continuation policy. Implementation and measured runtime qualification
remain pending in [TOOLSET-012 and TOOLSET-013](../TODO.md).

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
preflight and overall acceptance remain pending. These checks do not establish
live worker or scheduled execution.

### Task context simplification

The user requested simpler tasks for faster Autowork execution. The five pending
IDs stay unchanged: TOOLSET-003, TOOLSET-011, TOOLSET-012, TOOLSET-013 and TOOLSET-008.
[TODO.md](../TODO.md) now states the remaining action, acceptance, checks, exclusions,
dependencies, ownership and next step directly; this is an editorial simplification,
not reduced product scope or weaker completion criteria.

Research baseline: those five task bodies contained 1,524 words; the compact bodies
contain 1,082 words (29.0% fewer), measured by whitespace-separated words excluding
headings, navigation and generated coverage. This measures task-context reduction,
not a proven runtime speedup. No model/native timing experiment was run here.

Decision: remove repeated rationale/lifecycle prose, point to existing accepted
contracts for detail, and avoid redoing TOOLSET-012's reviewed engineering-guidance
slice. Keep user ordering, ledger state/dependencies and completed history intact.
TOOLSET-012's original worker/contract remains assigned; TOOLSET-013 still waits for
it. Live environments and the TOOLSET-008 policy question remain real gates, not
simplification targets. Planning changes no code, dispatch, schedule or budget.

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
priorities, leases and unresolved TOOLSET-008 continuation policy are preserved;
this plan does not promote the new goal ahead of them. Planning saves documents
and backlog only: it does not dispatch, commit, push, resume the interrupted
publication, modify live profiles/jobs, deploy, or claim faster operation today.
