# Campaign selection and state

## Evidence before selection

Read repo instructions and status, then `ROADMAP.md`, `TODO.md`, `TASKS.md`, issues, plans, PRDs/ADRs, acceptance criteria, and CI failures that are locally available. Prefer documented needs over invented improvements, but rank their actual consequences against live defects. If task sources are absent or exhausted, use `live discovery`; do not create project-management files merely to run the campaign. Maps, TODOs, smells, and static-analysis warnings are leads, not proof.

| Lane | Useful sources → feedback signal |
| --- | --- |
| Correctness | Callers, workflows, state transitions, edge cases → minimal repro/regression test |
| Security | Input/trust boundaries, authorization, secret handling, dependency exposure → safe local negative case; no secret disclosure or production probing |
| Performance | Hot paths, redundant I/O/computation, resource use → repeatable latency/memory/work measurement, not aesthetic guesses |
| System design | Coupling, data flow, boundaries, change history → concrete caller/change-locality/testability consequence |
| UI/UX | User flows, components, visual states → accessibility, responsive, loading/empty/error and interaction evidence; disclose unavailable browser/visual checks |
| Reliability | Concurrency, cleanup, retries, recovery, logs → failure injection or state/resource check |
| Tests | Risky uncovered behavior, failures/flakes → regression or repeatable flake evidence; green generic suites alone are insufficient |
| Delivery | CI, build/install/release configuration, manifests → local build/package/dry-run; no publishing |
| Docs | Setup, examples, interface drift → live source citations and executable example/link checks |

Record applicability, evidence, result, last explored step, and next unexplored seam for every lane. A repository without UI can mark UI not applicable with a reason. Collection mode also inventories every member and maps shared evidence to members; it never forces an edit per member.

## Ranking and fairness

Compare consequence/severity, affected users, owner priority, evidence confidence, reversibility, and validation cost **across** lanes. A broken user interaction can outrank a cheap packaging cleanup; a high-impact design defect can outrank an easy lint fix. Ease is a tie-breaker, not the objective. Require a feasible validation signal before mutation.

Keep up to three actionable candidates. Blocked and deferred findings live separately with the exact reason, required decision/new evidence, and revisit condition. Completed/rejected/no-progress leads do not return unchanged. One blocked branch does not freeze other work; user rejection of waiting means pivot to independent discovery, not bypass that branch's gate.

At each queue refresh check underexplored lanes, including when the queue is full. Within every two accepted slices or investigation-only steps, advance at least one underexplored applicable lane: inspect a concrete new seam or commission a distinct scout and consume its result. Rotate by coverage debt instead of repeatedly inspecting packaging. Mere relabeling or re-reading unchanged evidence is not progress. Urgent security/data-loss response can defer this obligation: record the consequence, deferred seam, and next revisit point on each refresh. This is discovery fairness, not a quota of edits or permission to implement a weaker finding.

## Concrete work sets and approval

For each proposed design prepare an approval-ready item:

```text
Work set/version and item ID:
- evidence, consequence, selection rationale:
- proposed behavior/design; alternatives and tradeoffs:
- paths/seams and non-goals; dependencies on other items:
- objective checks and baseline signal:
- risk, recovery, external/spend boundary:
- required decision; approval source and exact approved scope:
```

Use required brainstorming/design/planning workflows before implementation. Several concrete independent designs may be reviewed and approved as one named work set. Example: approve A's parser boundary correction and B's keyboard-focus behavior, each with specified files, expectations, and checks. The parent can then execute A followed by B without re-asking. “Improve any future architecture however you see fit” is not approval of unknown designs. An approved queue label without a concrete design is not a substitute for a required design gate.

When discovery adds C or B needs a materially different design, prepare its concrete decision and keep it gated; continue remaining authorized items. Reuse existing approval exactly; never reopen answered questions simply because a new worker starts. Parent-owned routine implementation judgments stay inside approved boundaries. Children escalate new product/architecture/scope/risk choices through their supervisor channel and wait.

## Compact conversation state

```text
Campaign: objective; mode/scope/non-goals; task sources; explicit limits
Lifecycle: active | paused | blocked | stopped | complete | handoff
Approvals: work set/version/items, source, decisions still gated
Coverage: lane/seam/member, applicability, evidence/result, last/next exploration
Queue: up to three ranked actionable candidates
Blocked/deferred/no-progress: reason, attempts, revisit condition
Slice: ID, phase, allowed paths, pre/post snapshots, writer/run status, reviewer IDs
Evidence: baseline and commands/outcomes, review dispositions, accepted slices
Next action: concrete step or precise terminal reason
```

Each candidate needs a consequence, live evidence, exact baseline command/artifact, smallest intended change, pass condition, and owner/risk blocker. Evidence connects **selection → trajectory → outcome**: why this candidate, what was actually inspected/changed/delegated, and whether its objective improved. Reuse current evidence; rescout only stale or new seams.

## Routing and terminal audit

Use available `systematic-debugging` for broken/flaky/slow behavior including CI/pipeline, `test-driven-development` for behavioral changes, and required design/review/verification skills at their gates. Available local specialists add domain evidence: `technical-auditor` for architecture, frontend specialists for UI, `wiki-docs` for source-backed docs, and `pi-extensions-helper` for Pi resources. Do not unconditionally route to retired shims or stack unrelated skills. Shipping is a separate user-authorized handoff.

Before terminal completion map each explicit task/member and acceptance criterion to fresh evidence, classify dirty state, account for every child, and reconcile the queue. Empty short queues trigger new discovery. Exhaustion needs an evidence-backed fresh pass over applicable scoped lanes, not merely a clean audit or repeated low-value work. All-gated work yields a precise blocked report; limits yield a handoff; explicit one-slice mode yields a checkpoint after one acceptance. No-progress branches get a revisit condition rather than blind retries.
