---
name: autonomous-codebase-improver
description: "Improve a repository across work lanes."
license: MIT
---

# Autonomous Codebase Improver

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Use for open-ended improvement across correctness, security, performance, design,
UI/accessibility, reliability, tests, delivery and docs. Not a second runner,
scheduler or replacement for Autowork. A known defect, fixed plan or audit-only
request keeps its narrower workflow.

Read the [host and authority adaptations](../shared/PI-TOOLSET.md), then the pinned
[campaign protocol](upstream/PROTOCOL.md) and relevant selection/recovery references.
This adapter overrides their Pi-only worker requirement, repeated approval
ceremonies and separate conversation-only task-state convention. Autowork owns
the task store, execution, review and acceptance.

## Local authority rules

User instructions and repository policy still govern. These rules take precedence
over conflicting upstream instructions:

| Area | Rule for this adapter |
| --- | --- |
| Execution | Use discovered host-native capabilities. In-session implementation without a delegated worker is allowed only when repository policy permits it and independent review is available. |
| Review | Require fresh independent review of the actual slice delta. Missing review capability keeps discovery read-only. Never self-approve or install tools to bypass this gate. |
| Decisions | Reuse accepted scope and routine local implementation authority. Ask only for genuinely missing product, risk or external-action authority. |
| Task state | The coordinator updates task body notes through `autowork tasks`. Workers report results but never edit `tasks/`. Missing CLI capability means read-only discovery and an exact blocker report. |
| Limits | Continue within this session by default. Explicit one-improvement, read-only, time, budget and pause/stop limits win. |
| Delivery | Follow existing local commit and integration authority. Push, deployment and live qualification remain separate and need their corresponding authority. |

## Current-session campaign

1. Orient on repository tasks, actual source, ownership and checks. Establish scope,
   non-goals, explicit limits and prior authorization. Default to continuous work
   **within this session**; an explicit one-improvement request stops after one.
2. Rank at most three evidenced candidates by consequence, confidence, reversibility
   and validation cost across applicable lanes. Record coverage and deferred leads
   in task body notes as described below. Refresh an underexplored lane after at
   most two accepted slices or investigation-only steps. Urgent security/data-loss
   work may defer this exploration: record the consequence, deferred seam and next
   revisit point at each refresh. This exception does not override scope or limits.
   Do not manufacture edits for coverage.
3. Choose one bounded task with acceptance and checks. Reuse accepted decisions and
   routine local implementation authority. Park genuinely gated work with an exact
   missing decision; continue independent authorized work rather than retrying a hold.
4. Check [pre-slice capacity](#pre-slice-capacity) before mutation. Establish a
   recoverable baseline and sole-writer ownership. Use the host's supported execution
   path and discovered capabilities, not assumed Pi agent names. If independent
   review cannot be obtained, keep discovery read-only and report the blocker.
5. Validate the actual slice delta, obtain fresh independent review and apply the
   [acceptance checklist](#acceptance-and-recovery). Worker success is not acceptance.
   Unknown active writer status retains ownership. Stop rather than launch a
   replacement or reset files.
6. Emit a progress receipt, refresh candidates/coverage and continue within limits.
   An empty shortlist triggers bounded discovery with a named seam and question.
   Claim exhaustion only after a fresh evidence-backed pass across applicable
   scoped lanes and coverage of each explicit task or collection member. Record
   evidence and reasons for non-applicable lanes. One clean seam is not exhaustion.
   If no actionable candidates remain, report "no further actionable candidates
   found." All useful work gated produces a blocked report. Pause/stop, an explicit
   one-improvement limit or insufficient resources produces a checkpoint with
   remaining coverage and next action, not completion of the whole objective.

Ordinary child workers never inherit this controller or delegate. Tools that write
caches or test outputs also need exclusive ownership. Missing delegation alone is
not a requirement to install pi-subagents: follow the shared host translation.

## Pre-slice capacity

Inspect available time, context, token/spend and delegation limits before starting
or resuming a slice. Estimate the bounded implementation, required checks, fresh
review and room for fixes or safe recovery. Reviewer availability alone is not
sufficient when the remaining allocation cannot support that path.

Use exposed limits and observed costs. Label unavailable measurements rather than
inventing precise capacity. If a feasible path cannot be established, narrow the
slice within accepted scope or checkpoint before mutation. Do not increase budgets,
switch models or start another session to evade limits. Recheck before a fix round.
If capacity is lost mid-slice, retain ownership and hand off the unaccepted delta
and recovery state. Never bypass review or presume rollback is safe.

## Acceptance and recovery

Before accepting a slice:

- Compare focused checks with the recorded baseline. Classify pre-existing
  failures separately. Introduced regressions block further implementation until
  repaired or safely removed.
- Resolve each review finding. Revalidate substantive fixes and obtain focused
  independent follow-up review. A passing generic suite does not dismiss a finding.
- Confirm current slice-owned contents and path state match the reviewed state.
  Reconcile unexpected changes. If validation or fixes change reviewed content,
  refresh the actual delta, rerun affected checks and obtain review before acceptance.
- Apply the default cap of three review rounds per slice, including follow-ups.
  Earlier explicit limits still win. Unresolved blockers at the cap mean rejection,
  not acceptance or a reset of the round count. Safely remove only the rejected
  slice's attributable delta before continuing independent work. If safe recovery
  cannot be proved, stop with a blocked handoff and preserve existing work.

Use the pinned [compare-before-rollback procedure](upstream/references/delegation-and-recovery.md#lightweight-baseline-and-compare-before-rollback).
A timed-out validation command can leave mutating subprocesses alive, even after
its worker has ended. Retain exclusive ownership until those processes are
quiescent and their effects are reconciled. Do not start replacement checks,
rollback or another writer meanwhile. Use supported controls only on attributable
processes. If status remains unknown, hand off blocked with process/run identities
and the missing evidence. A timed-out check is not a pass.

## Progress notes and evidence

A campaign progress receipt is a report, not an engine verification receipt.
The coordinator saves progress, coverage and deferred leads in the relevant task's
body notes through [`autowork tasks`](../shared/TODO-WORKCENTER.md#edit-records).
Preserve existing notes and use `--expect REV` after an earlier record read.
Do not create a second backlog. In read-only/no-write mode, report in conversation
only: do not change task records or write report files.

Never create or edit `tasks/evidence/<ID>.toml`. Only the engine's verified close
writes that receipt. A reviewer acceptance, passing checks or manual task close
does not establish `coordinator_verified` closure. If the task CLI is unavailable,
report the missing capability without hand-editing records or inventing closure.

**Receipt contents:** task/title and selection reason; baseline → actual result; paths,
checks and review disposition; accepted/rejected slices; ownership/run status;
coverage and blocked leads with revisit conditions; next action or stop reason;
commit/integration/push/live evidence separately.

**Example:** after accepted A, continue authorized independent B. If the user said
“one improvement,” checkpoint after A with B pending. A pause prevents new launches.
Upstream evaluation results are not evidence that this adapted campaign ran.
Use the [adapter evaluation scenarios](references/adapter-evaluation.md) when
checking these local rules. Offline checks validate packaging, not model behavior.


## Boundaries

- Not one known fix; use `/autowork` for a ready task.
- Not an architecture report; use `/improve-codebase-architecture`.
- Not test-suite reduction; use `/test-optimizer`.

**Done when:** the chosen improvement is implemented within scope, verified with affected checks, and committed or reported with its remaining risk.
[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).