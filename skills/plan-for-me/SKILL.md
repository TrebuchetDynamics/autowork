---
name: plan-for-me
description: "Use to research and save a plan without an interview."
license: MIT
metadata:
  version: 0.3.0
  hermes:
    tags: [research, requirements, documentation, planning]
---

# Plan For Me

`/plan_for_me` (also `/plan-for-me`) investigates the repository, decides an
approach within the user's scope, and saves the plan and tasks. The public skill
ID is `plan-for-me`; its source directory is `skills/plan-for-me/`.

Read the [planning craft](../shared/PLANNING-CRAFT.md), the
[shared contract](../shared/COMMON-CONTRACT.md), the pinned
[Autoresearch plan protocol](../autoresearch/upstream/plan.md), and the
[planning adaptations](../shared/RESEARCH-PLAN.md). Apply the protocol directly;
the adaptations govern host tools, accepted scope, persistence and handoff.
Other research protocols remain in the [Autoresearch skill](../autoresearch/SKILL.md).
For game animation, environment or level-expansion requests and for
validation-performance planning, load the matching section of
[special cases](references/special-cases.md).

## Investigate and decide

Size the work first and say the size in plain words
([planning craft](../shared/PLANNING-CRAFT.md#know-what-you-know)): a clear task
gets one TODO task and no planning pass; a project gets a written plan section and
dependent tasks. Split several independent projects and plan them in order.

Inspect project instructions, relevant implementation and tests, existing docs,
accepted decisions, TODO.md/goals.json and active task ownership. Reuse existing
answers and task IDs. Compare practical approaches and record the evidence for
the selected one. Own the complex part: resolve design, decomposition, interfaces
and acceptance within delegated scope, and choose reversible engineering details and
supported recovery routes yourself rather than leaving them as worker permission
questions. Hand off the smallest clear outcome, decided approach, exact checks and
stop conditions. Record a delegated planner decision as such, never as a user
selection. Ask only for genuinely missing product intent or external authority,
and continue independent work. Delegation does not erase approval controls or
explicit scope, spending, ownership and stop limits. Never invent acceptance or
reopen settled choices without new evidence.

Write down what the user asked for as theirs and everything else as yours: goals,
non-goals and anti-goals (what would make the result a failure even if it works),
constraints, and every default you chose, each marked as the planner's call so the
user can reject it. Generate several approaches before choosing; record the rejected
ones only when the reason is non-obvious. Surface any contradiction between the
request and the code instead of planning around it. Name new domain terms precisely
and record them, and give a decision its own ADR only when it is hard to reverse,
surprising without context and a real trade-off.

For aspirational requests such as "10/10" or "premium", preserve settled product
positioning and turn the aspiration into observable quality gates. Mark the rubric,
thresholds and lab conditions as planner calls; distinguish measured baselines from
proposed targets and lab results from field performance or conversion evidence.
Do not award a perfect score from green tests or an empty design-detector result.
Inspect the current desktop and narrow localized render before proposing another
rebuild; improve specific hierarchy, product-proof and layout defects while retaining
verified imagery, brand commitments and already-qualified interactions.

When a new requirement supersedes a completed slice's deliberate limitation,
record the prospective override in the current spec and queue a successor; keep
its completed ID, original acceptance and archived evidence intact. Separate the
new positive behavior from safety boundaries that still apply, so replacing one
stop/rejection rule does not silently remove unrelated guards.

Trace a planned state transition through producer, ownership/cancellation guards,
preview, command commitment and presentation before splitting tasks; a producer-only
change can be immediately canceled or misclassified by its consumers. Require a
composed regression for the intended handoff and a negative regression proving
unrelated ownership loss still cancels. Mark new fixtures and unexercised technical
choices as planned, not measured baselines or verified algorithms.

For blocker or unblock requests, read the current task body, latest runs and
receipts first and report the observed phase; an older summary may predate review
or recovery. Verify retained review and gate evidence against the exact owned
source before choosing the next action. Route an approved, qualified candidate to
its existing delivery owner rather than planning another implementation or repair;
otherwise a stale blocker creates duplicate work. Distinguish reviewed candidate,
main inclusion, deployment and live acceptance, and retain historical failed evidence
without treating it as the current frontier when a matching newer check passes.
Separate missing intent or excluded repair scope from transport, gate or accounting
failures, comparing the fix with the original worker contract. Reuse the original
task, candidate and cumulative accounting; never infer budget from displayed turn
counts. Save findings in the existing task body; a conditional recovery recommendation
is not an executable next task, and consumer eligibility does not prove a free lease
or authorize redispatch. Before proposing a "patch-only" security-remediation
exception, compare the resolved versions, advisory fixed ranges, available releases
and immediate parents' declared dependency ranges. Explicitly identify any required
minor/major or transitive-range change; a narrow-sounding permission request must
not promise a repair that its own scope excludes. Registry lookup is planning
evidence, not compatibility proof or authorization to install or change the lockfile.

For a concrete method gap or explicit protocol request, select one technique through
[engineering](../engineering/SKILL.md); consult
[the engineering cycle](../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
Routine planning needs no experiment loop.

For requests to finish faster or free the owner's time, plan backward from a usable
handoff rather than rewriting the whole backlog. Inspect the still-failing acceptance
criterion and recent partial deliveries first; separate necessary positive capability,
required safety/package proof, unavailable external evidence and convenience work.
Freeze speculative scope, reuse existing IDs/artifacts, and choose outcome-sized
batches. Do not present task splitting, shorter prose, more frequent scheduling or
larger test totals as measured throughput improvement. Keep the saved plan and user
summary short enough to reduce the attention cost they asked to escape.

State the handoff's observable done conditions, the remaining full-project roadmap
and the next actually executable action separately. A staged handoff does not cancel
later obligations, waive authentication/data-preservation gates, or qualify downstream
training, research or deployment. If a positive trust/capability mechanism is still
unidentified, label that contract unready and name the exact missing mechanism;
do not hand the worker another open-ended instruction to discover it between guard
fixes. Propose or apply only an authorized fix-or-skip disposition, preserving real
dependencies, and identify existing independent work instead of manufacturing new
investigation tasks. Do not claim that saved next-batch guidance has changed an active
worker's behavior or been integrated into a queue whose pinned inputs are preserved.

When called by Autowork, investigate its named uncertainty and return to the
current task. For a held or blocked task, return a **fix or skip** decision, never a
restated blocker: fix with the smallest reversible change inside the delegated scope
(for example a verified alternative state for a broken external link, or the
in-scope part of a remediation), recorded as the planner's call; or skip by splitting
the blocked acceptance into its own task that names the exact missing input, keeping
it open, so Autowork continues with the next ready task. Only credentials, money,
deployment, legal or explicit owner approval remain user inputs. For backlog recovery, follow the
[bounded planning fallback](../autowork/references/backlog-planning.md).

## Save the plan and hand off

Follow the [TODO work center](../shared/TODO-WORKCENTER.md) and
[single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Use [Docs Sync](../docs-sync/SKILL.md) to persist findings and decisions in the
existing document owners and actionable tasks in TODO.md, synchronized with
goals.json. Include acceptance criteria, dependencies, verification and Now/Next
ordering; distinguish proposed decisions from accepted scope. Save observable
criteria under `Acceptance:` and exact verification commands under a separate,
unique `Checks:` field. Give each executable task `Touches:` (and `Resources:` where
needed) from the paths your investigation found, per the TODO work center, so
parallel Autowork can run independent tasks together. Inspect the current execution consumer's required fields
before calling a handoff executable: ledger/backlog readiness alone may not check
its contract shape. Do not claim a task or launch execution just to validate a
planning handoff. Reconcile one affected batch and reuse input-bound checks when
the evidence is unchanged.

Before reporting the plan ready, run the
[builder check](../shared/PLANNING-CRAFT.md#builder-check-before-handoff): a fresh
reader in Autowork's place lists what it would have to guess. Write answers already
known into the tasks, settle minor ones as the planner's call, and ask the user only
the questions that change what gets built, in one message. Keep just the affected
tasks pending until they answer; independent tasks stay ready.

Planning includes saving this work by default. Explicit read-only, chat-only,
no-write or dry-run requests save nothing. Planning alone does not authorize
implementation, commits, worker dispatch or a recurring schedule. Preserve any
separate implementation authority already given and the normal Autowork gates.

Finish with the chosen approach, supporting evidence, the planner's calls, changed
document paths, task IDs, unresolved questions and the next executable task. Report consumer
readiness only when its check actually ran; a saved plan is not completed work.
