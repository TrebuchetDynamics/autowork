---
name: plan-for-me
description: "Use to research and save a plan without an interview."
license: MIT
metadata:
  version: 0.4.0
  hermes:
    tags: [research, requirements, documentation, planning]
---

# Plan For Me

`/plan_for_me` (also `/plan-for-me`) investigates the repository, decides an
approach within the user's scope, and saves the plan and tasks. With a concrete
objective it determines how to achieve it; with little or none it discovers which
evidence-backed objectives matter most, then determines how to achieve them. The
public skill ID is `plan-for-me`; its source directory is `skills/plan-for-me/`.

First read the [planning artifact and authority contract](../shared/RESEARCH-PLAN.md).
It governs allowed writes and the full requested batch on every route. Then read
the [planning craft](../shared/PLANNING-CRAFT.md), the
[shared contract](../shared/COMMON-CONTRACT.md), the pinned
[Autoresearch plan protocol](../autoresearch/upstream/plan.md), and the
[planning adaptations](../shared/RESEARCH-PLAN.md). Apply the protocol directly;
the adaptations govern host tools, accepted scope, persistence and handoff.
For a bare invocation or a vague direction, also read
[autonomous project discovery](references/discovery.md) before choosing work.
Other research protocols remain in the [Autoresearch skill](../autoresearch/SKILL.md).
For aspirational quality goals, superseded limitations, state-transition changes,
blocker or unblock requests, security-remediation exceptions, requests to finish
faster, game animation or level expansion, and validation-performance planning, load
the matching section of [special cases](references/special-cases.md).

## Route the request

Decide from the request's meaning, not from a short phrase list:

| Request | Route |
| --- | --- |
| No concrete objective; "plan this project"; "make it better"; a broad direction such as "improve reliability" or "improve performance" | Autonomous discovery: read [autonomous project discovery](references/discovery.md), investigate the repository, derive accepted and engineering goals, then save one executable frontier. Do not ask for a goal before investigating. |
| A named outcome, feature, defect, spec slice or accepted plan | Focused planning for that outcome and its authorized prerequisites; do not expand into unrelated project work. |
| Read-only, chat-only, no-write or dry-run | Use the matching route above but save nothing, including queue metadata. |
| An Autowork-owned planning substep | Stay inside the named task and its authorized prerequisites; return findings and records to that same coordinator. |

A bare `/plan_for_me` is a discovery request, not an interview. A vague adjective
("better", "premium", "faster") is a direction for discovery, not an accepted
outcome. A supplied objective wins even when short. If the repository has no
accepted objective or meaningful source, report the missing product intent and the
one decision that would create it; do not manufacture a roadmap to fill the queue.
New product directions stay proposals and never become runnable tasks by being
well written.

## Investigate and decide

Size the work first and say the size in plain words
([planning craft](../shared/PLANNING-CRAFT.md#know-what-you-know)): a clear task
gets one complete saved task record without an interview, not immediate execution;
a project gets a written plan section and tasks with real dependencies. A bare or
vague request is project discovery: say so, then establish the project model and
the evidence-backed goal classes before choosing the frontier. Plan all requested
projects in one coherent batch, retaining independent ready lanes.

Inspect project instructions, relevant implementation and tests, existing docs,
accepted decisions, `autowork tasks list` and the records it names, and active task ownership. Reuse existing
answers and task IDs. Compare practical approaches and record the evidence for
the selected one. Own the complex part: resolve design, decomposition, interfaces
and acceptance within delegated scope, and choose reversible engineering details and
supported recovery routes yourself rather than leaving them as worker permission
questions. Hand off the smallest clear outcome, decided approach, exact checks and
stop conditions. Record a delegated planner decision as such, never as a user
selection. Ask only after investigating for genuinely missing product intent or
external authority, and continue independent work. Delegation does not erase
approval controls or explicit scope, spending, ownership and stop limits. Never
invent acceptance or reopen settled choices without new evidence.

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

Follow the [work center](../shared/TODO-WORKCENTER.md) and
[single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Use [Docs Sync](../docs-sync/SKILL.md) to persist findings and decisions in the
existing document owners. Reuse Docs Sync's capability/prepare flow against the
actual consumer: require `prepare_api` 4 or higher, inspect the reported outcome,
and never call a deferred conversion or activation-pending consumer ready. Reuse
that result while its inputs are unchanged; do not duplicate its conversion matrix,
force conversion, install updates or interrupt workers to complete planning.
Save the batch as task records with `autowork tasks add
--goal G --title T --short S --scope ... --acceptance ... --checks ... --touches ...
--depends-on ...`, adding or updating its goal first with `autowork tasks goal`.
Include acceptance criteria, dependencies, verification and Now/Next placement;
distinguish proposed decisions from accepted scope. Save observable criteria in
`acceptance` and exact verification commands in `checks`. Give each executable task
`touches` from the paths your investigation found, and `resources` where
needed, per the work center; set further fields and notes such as `Sources:` with
`autowork tasks field`. For literal prose, write JSON with a file-writing tool and
use `--json`; after an earlier material read, carry `show ID --worktree`'s
`record_revision` to the update's `--expect REV`. On refusal reread, reconcile and
reapply only the authorized delta, never a stale snapshot or blind retry (see the
work center). Cut and write the tasks by the [planning craft](../shared/PLANNING-CRAFT.md#size-each-task):
small tasks with disjoint write sets, acceptance that names a failing test, and a
pre-mortem whose guards land in the owning tasks. A record missing contract fields
is a draft the runner never selects: `autowork tasks validate --worktree .` lists
drafts, and after the commit `autowork tasks why ID` shows committed-store selection
eligibility and position. Check both before calling a handoff selection-ready;
capacity, resource/ownership admission and actual dispatch require separate evidence. Do not claim a task or launch execution just to validate a
planning handoff. Reconcile one affected batch and reuse input-bound checks when
the evidence is unchanged. For a discovery batch, save only the evidenced frontier:
reuse an existing backlog that already covers the gaps, and add no duplicate or
speculative task merely because the queue looks short.

For future work whose content depends on implementation evidence, follow
[rolling planning](../shared/TODO-WORKCENTER.md#rolling-planning): save only the
first batch whose content is known now, at most 8 new tasks total including one
closing planning task (`kind = "plan"`, set with `autowork tasks field ID kind plan`)
under the same goal. Note `Plan round: 1 of 10` by default (`autowork tasks field
ID "Plan round" "1 of 10"`) and give it dependencies on every building task in the
batch. Its scope names the goal and what the next round must find out from the
finished batch's evidence. When the runner hands you a planning task, close it with
`autowork tasks done ID --by WHO --reason TEXT [--evidence REF]` in the same commit
as the batch it produced. This is manual closure of planning, with no verification
receipt; it does not qualify implementation acceptance or a met goal. Preserve the
work center's verified-dependency/owner-qualification boundaries. A successor
advances N in `Plan round: N of M` without resetting its limit. Apply the shared stopping rules. A small or single-batch plan adds no
planning task and keeps the existing saving flow.

For a rolling plan, the final report says the chain will continue on its own under
an already running, authorized Autowork runner, gives its round limit (10 by default),
and explains how to stop it: move the planning task to `Needs decision`
(`autowork tasks place ID "Needs decision"`). Saving the
chain does not start a runner or grant execution authority.

For focused tasks and discovered frontiers, apply shared
[decision closure](../shared/PLANNING-CRAFT.md#decision-closure): record planner calls
and keep only genuinely owner/external-blocked affected tasks pending. Before
reporting ready, use the [builder check](../shared/PLANNING-CRAFT.md#builder-check-before-handoff)
and persist each material finding's disposition in the saved contract, not as
advice to a later worker. Then run `autowork tasks validate --worktree .`, fix every
error and draft you did not mean, and commit the batch once
([plan handoff](../shared/PLAN-HANDOFF.md)).

Planning includes saving this work by default. Explicit read-only, chat-only,
no-write or dry-run requests save nothing. Planning alone does not authorize
implementation, worker dispatch or a recurring schedule; its one commit holds only
the saved plan and records. An explicit
standalone planning request narrows this occurrence despite earlier unrelated
implementation permission. Return an Autowork-owned planning substep to its same
coordinator; execution resumes there, not inside this planning substep.

An audit or an "is it ready?" request is planning too: give the verdict in one line,
then save each gap as a task (or name the existing task it updates), owner-only gaps
in `Needs decision` with their one `Question:` note. Findings without task IDs are not a
finished plan.

Finish with the chosen approach, supporting evidence, the planner's calls, changed
document paths, task IDs, unresolved questions and the next executable task. Report
branch-local saving/checks separately from inclusion in the actual consumer and its
selection result; report consumer readiness only when that check actually ran.
A saved plan is not dispatch, delivery or completed work.
