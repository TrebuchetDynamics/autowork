---
name: autonomous-codebase-improver
description: Use when requests call for broad, open-ended or continuous roadmap-driven repository improvement across bugs, security, design, UI, performance, reliability, tests, delivery, or docs; not a single known defect or fixed plan.
---

# Autonomous Codebase Improver

A **parent-only**, evidence-backed campaign: discover → approve concrete work → one worker → validate → fresh review → parent acceptance → continue. Ordinary children execute only their assigned slice; they never inherit this controller or delegate. This skill remains opt-in, outside the default skill profile. It is not a service or permission to ship.

## Mode and authority

| Request | Boundary |
| --- | --- |
| Bare invocation, “improve this repo”, “keep improving” | **Continuous campaign by default** |
| “One improvement” or explicit one-slice checkpoint | Stop after one accepted slice |
| Named subsystem | Continuous within that subsystem |
| Named collection | Inventory every member; cover each with evidence, not forced edits |
| Known defect, fixed plan, audit-only, review-only | Honor the narrower task; no scope or mutation expansion |

Explicit limits and user pause/stop win. Re-invocation resumes state, not discovery from scratch, and never grants pending approval. Continuous intent permits continued selection, **not approval of unknown future designs**. Follow required Superpowers design/planning gates; present concrete approval-ready work sets and reuse their approval exactly. New product, architecture, risk, scope, or spend decisions stay gated while independent authorized work continues.

Before selecting work read [campaign selection and state](references/campaign.md). Before any child launch or recovery read [delegation and recovery](references/delegation-and-recovery.md), and use the available `pi-subagents` skill's relevant execution/safety guidance. Discover actual executable roles and controls; missing worker or fresh-review capability blocks implementation, never triggers solo fallback.

## Operating loop

1. **Orient.** Inspect repo instructions, dirty state, manifests, README, tests/CI, and the codebase map when present. Read repository-owned tasks first; verify leads against live code. Establish objective, mode, non-goals, explicit limits, approvals, and coverage.
2. **Discover and rank.** Consider correctness, security, performance, system design, UI/UX, reliability, tests, delivery, and docs. Use distinct read-only scouts only when new evidence is needed. Keep at most three actionable candidates plus separate coverage and blocked/deferred records. Rank by consequence across lanes, not a packaging-first ladder. At every refresh inspect coverage debt; after at most two accepted slices or investigation-only steps, advance an underexplored applicable lane even if the queue is nonempty. Urgent security/data-loss may preempt with a recorded reason and next revisit point.
3. **Authorize and baseline.** Select one bounded candidate with concrete consequence and objective checks. Resolve its required design approval using the approved work set. Capture recoverable pre-slice contents and path state (including previous uncommitted work); run baseline checks and preserve results. Assign exclusive writer ownership before launch.
4. **Implement.** One pi-subagents worker is the sole writer for the cwd. Give it the approved design, allowed paths, non-goals, checks, baseline location, and escalation rule—not “improve everything.” No parent edits or concurrent mutating validation. Ownership survives timeout, detach, error, pause, cancellation, and handoff until run/tools are quiescent and the delta reconciled.
5. **Validate and review.** Capture the quiescent post-worker state; inspect the actual slice delta, not just `git diff HEAD`. Run focused checks and required repo gates. Require a fresh-context read-only reviewer of that delta, acceptance criteria, regression protection, and evidence. A worker's success claim is not acceptance.
6. **Synthesize and accept.** Parent dispositions every finding. Send required fixes to one worker, then revalidate and obtain focused follow-up review for non-trivial fixes. Default cap: three review rounds; unresolved blockers are not accepted. Before advancing, fix regressions or safely remove a rejected slice using compare-before-rollback. If recovery is unsafe, stop with a blocked handoff. Parent accepts only when intended outcome, checks, review, ownership, and delta agree.
7. **Continue.** In continuous mode, emit a progress receipt with the next concrete action, refresh coverage/queue, and select the next authorized candidate in the same campaign. Do not send a terminal report merely because of one success, a clean audit, an empty short queue, or one blocked candidate. Explicit limits and stops still apply. Empty queues trigger fresh discovery; no-progress leads need new evidence before retry.

## Stops, recovery, and reporting

- A design/credential/spend gate is branch-local: park it with a revisit condition and continue independent authorized work. Two attempts on the same blocker without new evidence stop that branch, not the campaign.
- If baseline checks already fail, classify pre-existing failures separately. Introduced regressions block new implementation until repaired or safely removed. Never rollback against HEAD or overwrite external edits; use the recovery reference.
- Pause/stop prevents new launches immediately. Use only supported child controls, account for in-flight mutations, and retain ownership if status is unknown. Resume refreshes ownership and stale evidence. Context/time/spend/spawn limits produce a handoff, not exhaustion or cap bypass.
- Exhaustion requires scoped tasks/collection coverage plus a fresh evidence-backed pass over applicable lanes. Say “no further actionable candidates found,” not “no bugs exist.” If all useful work is gated, ask once for the exact decision. Never promise work after the session stops.

**Progress receipt:** slice/lead, selection rationale, baseline → result, changed paths, review disposition, ownership, coverage/queue update, blocked/deferred revisit conditions, next action. Investigation-only receipts name what was ruled out and the next seam.

**Terminal report:** reason/lifecycle, original scope and each task's acceptance evidence, accepted vs rejected/unreplicated slices, commands/outcomes, remaining coverage/queue, dirty-state classification, active run IDs/ownership, exact next action. Keep compact state in the conversation; do not create a task database.

## Example and evidence boundary

“Improve this repo”: A and B have concrete approved designs. After A's worker, checks, fresh review, and parent acceptance, issue a progress receipt and start B—not a final answer or a repeated approval request. If B needs a new architecture decision, park B and discover independent authorized work.

Required design/TDD/debugging/review/verification workflows remain under Superpowers; use available domain specialists only at real seams. No commits, pushes, production access, external mutation, broad upgrades, destructive Git, model/budget changes, or global activation without corresponding authorization.

[Pressure scenarios](references/pressure-scenarios.md) define decision probes and actual parent-capable two-slice/safety acceptance. [Evaluation receipt](references/evaluation-receipt.md) records the supplied old-skill decision failure. Repository edits and offline checks are **provisional**: only passing end-to-end behavioral evidence supports verified campaign behavior; missing evidence is unreplicated, failed behavior blocks verified acceptance. Pin the loaded skill path/revision, not just the repository file you intended to load. No live model calls in npm tests.

## Shared contract

Follow [the shared skill contract](../../shared/COMMON-CONTRACT.md) for repo study, dirty-worktree hygiene, verification evidence, safe handoffs, and safety defaults.
