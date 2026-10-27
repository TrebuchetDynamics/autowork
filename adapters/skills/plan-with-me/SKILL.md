---
name: plan-with-me
description: "Research, refine or challenge a plan through focused questions (including Grill Me), and save accepted decisions and tasks."
disable-model-invocation: true
---

# Plan With Me

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

First read the [planning artifact and authority contract](../../../skills/shared/RESEARCH-PLAN.md),
then the [host contract](../COMMON.md), pinned
[Autoresearch plan protocol](../../../skills/autoresearch/upstream/plan.md) and
[interactive planning adaptations](../../../skills/shared/RESEARCH-PLAN.md#interactive-planning-plan-with-me).
Refine the initial prompt into a working brief and investigate relevant evidence.
For important assumptions or explicit challenge mode, use
[challenge protocol](../grill-me/PROTOCOL.md) with the adaptations above; no
whole-frontier questionnaire or repeated approval of settled answers.
`Selected mode: challenge`, a Grill Me compatibility request, or an explicit
request to challenge a plan selects this mode. Preserve the literal user request
and its restrictions; mode selection adds no implementation or write authority.
Follow the [consequential uncertainty loop](../../../skills/shared/PLANNING-CRAFT.md#consequential-uncertainty):
track open intent, concrete acceptance, scope and constraints by the decisions/tasks
they change; ask the highest-impact ready question with context and trade-offs,
using native user-input tools or chat. Thin intent needs a concrete example, not an
arbitrary option menu. Inspect repository facts yourself and decide routine details
within authority as planner calls. After every answer, update only what it resolves,
play back new understanding with guesses marked, then ask the next consequential
question. Continue until material intent and acceptance are actionable; a fully
specified request needs no filler. Ask shared batch constraints once.

A bare "yes" accepts one unambiguous proposal, never several separate
recommendations; clarify ambiguous answer scope and keep affected choices open.
Preserve corrections and accepted decisions on resume. "You decide" delegates that
choice; "skip" leaves it open; "stop/finish" ends all questioning and preserves
resolved progress without fabricated answers. Do not habitually offer to skip at
the opening; an explicit switch to Plan For Me reuses existing evidence/decisions.
Honor questions-only/read-only without writing files.

`/plan_with_me blockers [repo|name]` is [`/blockers`](../blockers/SKILL.md): routine
planning repairs first, then genuine owner questions, easiest first; replanning happens here
before the next question.

Save explicit answers in existing requirement/spec documents when permitted. At
finish, summarize scope, non-goals, acceptance and open questions. Ask for approval
only if your synthesis adds material unaccepted intent and the user has not said
stop/finish; otherwise leave that intent open without another question. Reconcile
accepted decisions into their document owners and complete task records with `autowork tasks
add`/`goal` ([work center](../../../skills/shared/TODO-WORKCENTER.md)): placement, dependencies,
checks and `touches`. Run the planning craft's builder check on the saved tasks, then run
`autowork tasks validate --worktree .` and commit the batch once before reporting selection.
Bring only unanswered consequential builder questions back to the user; settle
repository facts and routine details yourself, without reopening accepted answers.
Do not start implementation merely because a plan exists.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Unchanged findings need
no new docs pass. Finish every requested outcome in the batch, not just the first
clear task; preserve independent ready lanes and keep open choices scoped.
After the commit, `autowork tasks why ID` reports committed-store selection eligibility
and position only, not resource/ownership admission, capacity or dispatch. Report the
actual selection result, or say selection was not assessed. Distinguish a branch-local
commit from delivery to the actual canonical consumer: disclose whether that consumer
includes the commit and whether selection was checked there. Report runtime and
ownership unassessed unless observed.

Standalone planning stops despite earlier unrelated implementation permission.
An Autowork-owned substep returns to that same coordinator without execution inside
planning or competing workers, without asking again for settled authorization.
When existing execution fails without new product uncertainty, return the exact task
ID, attempt evidence and failed operation to the same coordinator for supported
recovery; do not reopen the product interview or create duplicate tasks.
A later explicit implementation instruction enters
the execution workflow. The shared contract requires neither Hermes-native tooling
nor a claimed hard sandbox on this host.
