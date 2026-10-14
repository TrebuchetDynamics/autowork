---
name: plan-with-me
description: "Use when the user wants collaborative planning: research the repository, clarify their initial request and important decisions through questions, then save docs and tasks."
license: MIT
metadata:
  version: 0.1.0
  hermes:
    tags: [interview, requirements, documentation, planning]
---

# Plan With Me

The interactive counterpart to Plan For Me: investigate with Autoresearch, refine
the initial request through focused questions, and save the plan and tasks. Read
the pinned [plan protocol](../autoresearch/upstream/plan.md) and apply the
[interactive planning adaptations](../shared/RESEARCH-PLAN.md#interactive-planning-plan-with-me).
Use Docs Sync to reconcile findings and answers into existing documentation. Follow the [shared contract](../shared/COMMON-CONTRACT.md)
and [plan handoff](../shared/PLAN-HANDOFF.md).

`/plan_with_me` (`/plan-with-me` also works in CLI) starts an interview about the
current repository; arguments narrow the topic. Its default scope includes saving
answered decisions and maintaining affected docs. `questions only`, `audit` or
`read-only` means no file changes. It does not authorize code changes or start
autowork. Honor any separate implementation authority already given.

The public skill ID is `plan-with-me`, and the source directory is
`skills/plan-with-me/`. The public command means ask the user and plan together.

## Challenge mode

For “grill me”, “challenge this plan” or the compatibility `/grill_me` command,
read [the questioning protocol](../grill-me/SKILL.md) on demand. This is a mode of
Plan With Me, not a second required planning workflow. The interactive adaptations
override its whole-frontier rounds and generic approval prompt: one question at a
time, no exhaustive interrogation or repeat approval of settled answers.

## Resume without repeating the interview

Apply the [single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Resume saved answers; ask only material unresolved choices. Keep a question scoped
to the tasks it affects. An unanswered optional feature must not hold independent
accepted tasks. Save meaningful answers during the interview, then batch final
documentation/ledger checks once; do not restart Docs Sync after each response.

## Learn enough to ask a useful question

Read repository instructions, the user's current request, relevant existing docs,
accepted decisions and scoped source/tests. Reuse the actual README/PRD/spec/ADR
and backlog owners; do not perform a full docs-sync bootstrap before asking.
Distinguish implemented behavior from intended behavior. Do not ask the user for
facts you can establish from the repository, or reopen settled answers without
new contradictory evidence.

State a brief understanding of the outcome and the most consequential missing
information. Ask the first useful question in the first response after this
bounded inspection; do not return only an interview plan.

For a concrete method gap or explicit protocol request, select one technique through
[engineering](../engineering/SKILL.md); consult
[the engineering cycle](../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
`interview-me`, planning and documentation protocols are optional techniques for
those gaps. Questions-only interviews need no planning, graph or documentation pass.
Do not load a sequence of methods merely because answers mention an API or UI. If a supporting skill is missing, continue this workflow and
report the fallback briefly at handoff, without delaying the first question; do not install or modify imported skills during the interview.

This companion includes docs persistence, unlike a standalone intent interview.
Do not adopt upstream defaults that repeatedly re-confirm a clear answer or stop
before the already requested documentation work. Actual user scope takes precedence.

## Ask, listen, adapt

Ask **one focused question at a time**, using `clarify` when available or ordinary
chat when it is not. Wait for the reply before asking the next question. Use plain
language, give a brief reason it matters, and offer two or three meaningful options
with a recommendation and tradeoffs when useful. Allow a free-form answer; do not
force an invented choice or disguise a recommendation as a known fact.

Choose the next question by its effect on the plan, not a fixed questionnaire:

- Who needs the outcome, what problem they face and why it matters now.
- Which result counts as success, including one observable acceptance example.
- Scope and non-goals, constraints, compatibility and meaningful tradeoffs.
- Priority between conflicting outcomes, migration or operational expectations.

Only explore dimensions that remain unresolved and relevant. Decide internal
naming, test seams and equivalent engineering options autonomously. For vague
answers such as "fast" or "easy", ask for a concrete user situation or acceptable
outcome. When an answer contradicts accepted intent, explain the conflict and ask
which direction now governs; preserve history rather than silently replacing it.

After an answer, briefly reflect any material new understanding and ask the next
highest-value question. Do not repeat the whole interview after each reply.
`You decide` delegates that choice: recommend and record a compatible decision
inside the stated constraints instead of forcing the user to pick. It does not
grant unrelated execution or publication authority. `Skip` leaves the question
open; `stop` ends questioning, including confirmation questions, and preserves
answered progress with unresolved matters left open. Silence is neither
an answer nor acceptance. In scheduled/noninteractive runs, report the single
highest-value question and leave it pending; do not fabricate replies or poll.

## Save answers and finish the plan

During an ongoing interview, save material explicit answers in the existing owner
when useful for continuity. Keep unanswered issues and inferred requirements
clearly Open/Proposed. Never mark an entire plan Accepted from one local answer.
For a resumed interview, read saved answers and ask only what remains unresolved.
Respect read-only scope and preserve concurrent edits, task IDs and active leases.

When the useful gaps are resolved, or the user asks to finish, give a concise
readback: outcome, users, success, scope/non-goals, constraints, decisions and any
remaining open questions. Ask for confirmation only if the synthesis introduces
a material inference or unresolved conflict. Clear contextual approval counts;
do not demand a magic word or re-approve answers already given. If a draft needs
acceptance, present the concrete draft and bind the reply to that scope.

In writable mode, run a narrow docs-sync Maintain pass for the affected owners, applying its
canonical ledger and concurrency rules. Default invocation already requests
this persistence, so do not ask again whether to save. Accepted intent becomes
bounded Now/Next tasks with dependencies, acceptance and verification. Unanswered
product choices remain outside executable work. Validate changed docs and ledger,
then run the actual consumer backlog-check when handing off accepted tasks.

Finish with changed document paths, decisions captured, open questions and the
actual readiness result when a consumer check was applicable and executed; otherwise
state that readiness was not assessed. Questions-only/read-only mode finishes with
a conversational summary, no Maintain pass and no writes. Docs-only scope leaves
ready tasks undispatched. Existing
implementation authority permits the established autowork handoff without another
permission question; preserve review and owned-commit requirements. No new
scheduler, parallel backlog, automatic deployment or invented acceptance.

Example: for "interview me about onboarding", inspect the current setup docs and
ask who must complete setup if unresolved, or what they should accomplish unaided. Use the
answer to establish an observable onboarding outcome before discussing installer
details. Save it in the existing product/setup owner, not a competing interview spec.
