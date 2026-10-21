---
name: plan-for-me
description: "Use to research and save a plan without an interview."
license: MIT
metadata:
  version: 0.3.2
  hermes:
    tags: [research, requirements, documentation, planning]
---

# Plan For Me

`/plan_for_me` (also `/plan-for-me`) investigates the repository, decides an
approach within the user's scope, and saves the plan and tasks. The public skill
ID is `plan-for-me`; its source directory is `skills/plan-for-me/`.

First read the [planning artifact and authority contract](../shared/RESEARCH-PLAN.md).
It governs allowed writes and the full requested batch on every route. Then read
the [planning craft](../shared/PLANNING-CRAFT.md), the
[shared contract](../shared/COMMON-CONTRACT.md), the pinned
[Autoresearch plan protocol](../autoresearch/upstream/plan.md), and the
[planning adaptations](../shared/RESEARCH-PLAN.md). Apply the protocol directly;
the adaptations govern host tools, accepted scope, persistence and handoff.
Other research protocols remain in the [Autoresearch skill](../autoresearch/SKILL.md).
For aspirational quality goals, superseded limitations, state-transition changes,
blocker or unblock requests, security-remediation exceptions, requests to finish
faster, game animation or level expansion, and validation-performance planning, load
the matching section of [special cases](references/special-cases.md).

## Investigate and decide

Size the work first and say the size in plain words
([planning craft](../shared/PLANNING-CRAFT.md#know-what-you-know)): a clear task
gets one complete saved TODO task without an interview, not immediate execution;
a project gets a written plan section and tasks with real dependencies. Plan all
requested projects in one coherent batch, retaining independent ready lanes.

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

For a concrete method gap or explicit protocol request, select one technique through
[engineering](../engineering/SKILL.md); consult
[the engineering cycle](../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
Routine planning needs no experiment loop.

When called by Autowork, investigate its named uncertainty and return to the
current task. For a held or blocked task, return a **fix or skip** decision, never a
restated blocker: describe the smallest reversible fix inside the delegated scope
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
needed) from the paths your investigation found, per the TODO work center. Cut and
write the tasks by the [planning craft](../shared/PLANNING-CRAFT.md#size-each-task):
small tasks with disjoint write sets, acceptance that names a failing test, and a
pre-mortem whose guards land in the owning tasks. Inspect the current execution consumer's required fields
before calling a handoff executable: ledger/backlog readiness alone may not check
its contract shape. Do not claim a task or launch execution just to validate a
planning handoff. Reconcile one affected batch and reuse input-bound checks when
the evidence is unchanged.

For future work whose content depends on implementation evidence, follow
[rolling planning](../shared/TODO-WORKCENTER.md#rolling-planning): save only the
first batch whose content is known now, at most 8 new tasks total including one
closing `Kind: plan` task under the same Goal. Give it `Plan round: 1 of 10` by
default and dependencies on every building task in the batch. Its Scope names the
goal and what the next round must find out from the finished batch's evidence.
When continuing an existing chain, advance N in `Plan round: N of M` without
resetting its limit; apply the shared stopping rules. A small or single-batch plan
adds no planning task and keeps the existing saving flow.

For a rolling plan, the final report says the chain will continue on its own under
an already running, authorized Autowork runner, gives its round limit (10 by default),
and explains how to stop it: move the planning task to `Needs decision`. Saving the
chain does not start a runner or grant execution authority.

Before reporting the plan ready, run the
[builder check](../shared/PLANNING-CRAFT.md#builder-check-before-handoff): a fresh
reader in Autowork's place lists what it would have to guess. Write answers already
known into the tasks, settle minor ones as the planner's call, and ask the user only
the questions that change what gets built, in one message. Keep just the affected
tasks pending until they answer; independent tasks stay ready. Then lint the batch
with `goals.py plan-lint <repo> --tasks ID,ID,...`: fix every error and report each
warning with your call on it ([plan handoff](../shared/PLAN-HANDOFF.md)).

Planning includes saving this work by default. Explicit read-only, chat-only,
no-write or dry-run requests save nothing. Planning alone does not authorize
implementation, commits, worker dispatch or a recurring schedule. An explicit
standalone planning request narrows this occurrence despite earlier unrelated
implementation permission. Return an Autowork-owned planning substep to its same
coordinator; execution resumes there, not inside this planning substep.

An audit or an "is it ready?" request is planning too: give the verdict in one line,
then save each gap as a task (or name the existing task it updates), owner-only gaps
in `Needs decision` with their one question. Findings without task IDs are not a
finished plan.

Finish with the chosen approach, supporting evidence, the planner's calls, changed
document paths, task IDs, unresolved questions and the next executable task. Report consumer
readiness only when its check actually ran; a saved plan is not completed work.
