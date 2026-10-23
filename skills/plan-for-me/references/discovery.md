# Autonomous project discovery

Load this reference when a standalone Plan For Me invocation has no concrete
objective: bare `/plan_for_me`, "plan this project", "make it better", or a broad
direction such as "improve reliability". [SKILL.md](../SKILL.md) and the
[planning authority contract](../../shared/RESEARCH-PLAN.md) still apply. This
reference changes what is investigated first; it grants no implementation,
publication, spending or live-operation authority.

A bare invocation is a discovery request, not a request for an interview. Read the
repository before asking anything. If accepted intent is genuinely absent, report
that finding instead of inventing a roadmap.

## Route from meaning

| Request | Route |
| --- | --- |
| No concrete objective, or a broad quality/risk/performance direction | Discover the project, derive evidence-backed goals, then save one executable frontier. |
| A named outcome, feature, defect or accepted slice | Focused planning for that outcome and its authorized prerequisites; do not audit unrelated projects. |
| Read-only, chat-only, no-write or dry-run | Use the same discovery or focused method; save nothing. |
| Autowork-owned planning substep | Stay inside the named task and authorized prerequisites; return to that same coordinator. |

Classify semantically. A supplied objective wins even when it is short; a vague
adjective ("better", "premium", "faster") is a direction for discovery, not an
accepted outcome. When a request mixes a concrete outcome with a broad aspiration,
plan the concrete outcome and record the aspiration as a separate proposal.

## Goal classes

Build an explicit goal model from the evidence:

| Class | Meaning | Planner authority |
| --- | --- | --- |
| Accepted | Named in accepted product specifications, owner decisions, plans or goal records. | Refine, decompose and sequence it. |
| Derived engineering | A necessary engineering outcome inside the accepted direction: repair a reproduced crash, close a proved data-loss or security defect, restore a required check, remove a demonstrated bottleneck, or qualify an accepted feature. | Establish it as a delegated planner decision, with evidence. |
| Proposed strategic | A new product direction, major feature, monetization model, architecture pivot or substantial scope expansion. | Research, evaluate and recommend it; keep it out of runnable scope until the owner accepts it. |

Broad autonomy covers **how** to achieve accepted objectives, not **what** the
product should become. Sparse documentation still supports useful engineering
planning. A completely undefined project does not support invented business
requirements; report the one missing decision that would create real intent.

## Investigate progressively

Start with a repository map, not a recursive read of every file:

1. Read repository instructions, README/vision, accepted plans and specifications,
   goals and task records, active ownership, and recent Git history.
2. Identify entry points, modules, public contracts, data/state ownership, tests,
   fixtures, CI, build and deployment configuration.
3. Choose the few seams where the most consequential uncertainty lives, using
   dependency edges, change frequency, failing checks, known defects and
   architectural boundaries. Widen only when a decision depends on it.
4. For a monorepo or multi-project repository, establish project boundaries first;
   do not combine unrelated products into one goal or batch.

Record consequential findings with the path, source revision when available, and
confidence. Label them:

- `OBSERVED` — read in current source, tests, configuration or executed output.
- `DOCUMENTED` — stated by an accepted owner/specification document.
- `INFERRED` — a reasoned conclusion not yet proved by current source.
- `UNKNOWN` — insufficient evidence; name what would settle it.

Never promote `INFERRED` to verified fact. Absence from one inspected file is not
absence from the repository.

## Build the project model

State, briefly:

- what the product is for and who uses it;
- its most important user journeys;
- its architecture and authoritative state/interface owners;
- current maturity and recently completed work;
- which requirements are unimplemented, partially implemented, unverified,
  regressed or blocked;
- which problems impede further delivery;
- which next improvements offer the greatest return.

Trace each important requirement:

`Goal -> Specification -> Implementation -> Verification -> Task`

Classify each row as implemented and verified, implemented but unverified,
partially implemented, not implemented, regressed, blocked by an external
prerequisite, uncertain for lack of evidence, or superseded. The task follows from
the actual gap: qualification for an unverified feature, implementation for a
missing requirement, a defect or decision for a code/spec conflict, never a
duplicate implementation task.

## Specify before decomposing

For each substantial discovery result, work in this order: **Discover -> Specify
-> Design -> Decompose -> Validate -> Hand off**.

- **Specify** the intended behavior in the existing document owner: users or
  affected systems, preconditions and triggers, inputs/outputs, success and failure
  behavior, edge cases, exclusions and invariants. Use Given/When/Then scenarios
  where they make acceptance unambiguous.
- **Design** consequential choices inside delegated scope: architecture, data and
  interface contracts, ownership, compatibility, failure/recovery, security
  boundaries, verification strategy and real trade-offs. Compare practical
  alternatives only when the choice is real; follow existing conventions when they
  already answer it. Create an ADR only when the decision is hard to reverse,
  surprising without context and a real trade-off.
- **Decompose** into bounded tasks. **Validate** feasibility, authorization,
  ordering and duplication. **Hand off** through the existing Docs Sync and
  `autowork tasks` contracts; do not implement, dispatch, restart or schedule.

Keep new product strategy as a proposal in the appropriate document or a
`Needs decision` task with its `Question:` note. A proposal never becomes a worker
task by being well written.

## Prioritize the real frontier

Rank candidate work by expected value, not task count:

- severity of a proved defect and safety/correctness obligations;
- expected product or engineering value and critical-path impact;
- how many downstream tasks a result unblocks;
- strength of the evidence and confidence;
- implementation effort, technical/operational risk and review burden;
- ability to verify the outcome offline;
- actual independent execution lanes.

Safety and correctness outrank speculative convenience. Use qualitative estimates
when no measured data exists; do not fabricate ROI percentages, benchmarks or
baselines. A regression blocking six tasks may outrank six unrelated small
improvements without being expanded into a rewrite.

Inspect existing goals, tasks, dependencies, active work, completion records and
proposals before creating anything. Prefer repairing, refining or reprioritizing an
existing task over duplicating it. If the accepted backlog already covers the
highest-value gaps, report that and change nothing.

## Bound the batch

Distinguish the **strategic roadmap** (accepted outcomes and their real
dependencies) from the **execution frontier** (the smallest high-value group that
can be specified accurately and acted on now).

Apply the existing [rolling-planning rules](../../shared/TODO-WORKCENTER.md#rolling-planning):
at most eight new tasks per round, including any closing planning task, all under
the same goal. Do not fill the allowance artificially. Add a successor planning
task only when later content genuinely depends on implementation evidence. Stop
when the goal is complete, further work needs new owner intent, or the round adds
no building task. Never create an unbounded self-replenishing chain or a second
planning daemon.

Each executable task needs a canonical ID, an existing or justified goal, a
concrete outcome, bounded scope, observable acceptance, exact known checks, real
dependencies, bounded `touches`, resources, exclusions, kind, ownership, Now/Next
rank and source references. Do not invent worker ownership, live authorization or
permission the repository does not grant. A check that does not exist yet is a
proposed, unrun check, not a passing test.

## Reconcile repeated invocations

Before saving, compare:

- the last accepted plan and task IDs;
- current revision and relevant changed source;
- new or changed specifications and owner decisions;
- completed tasks and verification receipts;
- failed or regressed checks;
- active workers, holds and dirty files.

Replan only where evidence materially changed or a new worthwhile gap is proved.
Unchanged evidence means no duplicates and no empty planning commit. Preserve owner
priorities, settled decisions and historical task identity. Do not grow an
unbounded planning transcript; keep the durable detail in existing documents and
task records.

## Respect authority and persistence

Discovery authorizes project-wide planning, not product decisions or unrestricted
implementation. Preserve read-only modes, live leases and active workers, admitted
contracts, dirty checkouts, credential and production restrictions, publication
limits, document ownership and completed task history.

Save through the supported `autowork tasks` workflow and task-store preparation. Do
not edit legacy TODO.md/goals.json, bypass a hold, or clear another writer's claim
to make planning pass. If preparation is blocked, preserve the blocker, continue
independent read-only discovery, and report what remains unsaved. An explicit
standalone request stops after its planning batch; an Autowork substep returns its
findings and records to the same coordinator.

## Report

Keep the final report concise and evidence-bound:

- **Project understanding** — product, architecture, maturity.
- **Accepted goals** — existing goals plus any derived engineering goals, marked as
  planner decisions.
- **Most important gaps** — ranked, with evidence and confidence.
- **Planning decisions** — meaningful approaches chosen autonomously.
- **Executable plan** — task IDs, priority, dependencies and verification.
- **Proposed strategic opportunities** — separate from runnable work.
- **Outstanding decisions** — only what genuinely needs the owner.
- **Next executable task** — the most valuable action already authorized.

Distinguish saved planning from implemented work and from verified results. A saved
task is not completed code, and a proposed check is not a passing test. Keep this
report concise; detailed evidence belongs in the plan and task records.
