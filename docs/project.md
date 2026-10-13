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
