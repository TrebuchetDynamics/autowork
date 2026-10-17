---
name: plan-with-me
description: "Use to plan together through research and questions."
license: MIT
metadata:
  version: 0.3.1
  hermes:
    tags: [interview, requirements, documentation, planning]
---

# Plan With Me

The interactive counterpart to Plan For Me: research the repository, find out what
the user actually wants and why through focused questions, and save the plan and
tasks. Read the [planning craft](../shared/PLANNING-CRAFT.md), the pinned
[plan protocol](../autoresearch/upstream/plan.md) and the
[interactive planning adaptations](../shared/RESEARCH-PLAN.md#interactive-planning-plan-with-me).
Use Docs Sync to reconcile findings and answers into existing documentation. Follow
the [shared contract](../shared/COMMON-CONTRACT.md) and
[plan handoff](../shared/PLAN-HANDOFF.md). For cancelled tasks, blockers, pending-task
lists, validation performance, onboarding pages, teaching, investor briefs,
jurisdiction changes, long interviews and live gates, load the matching section of [special cases](references/special-cases.md).

`/plan_with_me` (`/plan-with-me` also works in CLI) starts an interview about the
current repository; arguments narrow the topic. `/plan_with_me blockers [repo|name]`
is [`/blockers`](../blockers/SKILL.md): a picked question per blocked task, easiest
first, planning each task that needs it with this skill ([special cases](references/special-cases.md#blockers-and-recovery)). Its default scope includes saving
answered decisions and maintaining affected docs. `questions only`, `audit` or
`read-only` means no file changes. It does not authorize code changes or start
autowork. Honor any separate implementation authority already given.

The public skill ID is `plan-with-me`, and the source directory is
`skills/plan-with-me/`. The public command means ask the user and plan together.

## Challenge mode

For “grill me”, “challenge this plan” or the compatibility `/grill_me` command,
read [the questioning protocol](../grill-me/SKILL.md) on demand. This is a mode of
Plan With Me, not a second required planning workflow. Its decision tree drives the
order: ask only frontier decisions whose prerequisites are settled, and work it in
rounds as below. No exhaustive interrogation or repeat approval of settled answers.

## Learn enough to ask a useful question

Read repository instructions, the user's current request, relevant existing docs,
glossary, accepted decisions and scoped source/tests. Reuse the actual
README/PRD/spec/ADR and backlog owners; do not perform a full docs-sync bootstrap
before asking. Distinguish implemented behavior from intended behavior. Facts are
yours to find; never ask the user for something the repository can answer, or reopen
settled answers without new contradictory evidence.

Then size the work ([planning craft](../shared/PLANNING-CRAFT.md#know-what-you-know)).
A clear task needs no interview: say so, save the task and stop. Otherwise the first
response is two things, in this order:

1. One line saying they can skip the questions ("say *plan it for me* and I'll
   decide"). If they take it, continue as Plan For Me in this conversation with the
   evidence already gathered; say any significant how-it-gets-made choice in one line.
2. One question. When intent is thin, make it an open question that gets them
   describing a real moment ("What happened the last time you wished this existed?").
   When intent is clear, ask the highest-impact decision.

Do not return only an interview plan, a process explanation or a list of topics.

For a concrete method gap or explicit protocol request, select one technique through
[engineering](../engineering/SKILL.md); consult
[the engineering cycle](../shared/ENGINEERING-CYCLE.md) only if routing is unclear.
`interview-me`, planning and documentation protocols are optional techniques for
those gaps. Questions-only interviews need no planning, graph or documentation pass.
Do not load a sequence of methods merely because answers mention an API or UI.
If a supporting skill is missing, continue this workflow and report the fallback
briefly at handoff; do not install or modify imported skills during the interview.
This companion includes docs persistence, unlike a standalone intent interview: do
not adopt upstream defaults that repeatedly re-confirm a clear answer or stop before
the already requested documentation work. Actual user scope takes precedence.

## Ask, listen, adapt

Use `clarify` when available or ordinary chat when it is not, in plain language that
matches the user's vocabulary, never process jargon. Get them describing before
offering options: their own words carry intent that your options can't, and options
steer. Offer a short menu only when they're stuck, or when choosing among concrete
alternatives the evidence has already narrowed; then give two or three options with
a recommendation and its trade-off. When they say "just guess" or "what do you
think?", propose something concrete. Give a brief reason a question matters when it
is not obvious. Allow a free-form answer; never force an invented choice or present
a recommendation as a known fact.

Work in rounds. A round is either one open question, or the current frontier of
ready decisions: those whose prerequisites are settled and that each have a clear
recommendation. Number them, give your recommendation for each, and word each so
"yes" accepts it ("Keep the CSV export as is? ➡️ yes: nobody asked to change it").
A plain "yes" accepts every recommendation in the round. A question that depends on
another still open belongs to a later round. Keep rounds to the few decisions that
matter now; do not dump the whole territory. Wait for the reply before the next round.

Choose what to ask by its effect on the plan, not a fixed questionnaire. Cover the
ground in [planning craft](../shared/PLANNING-CRAFT.md#cover-the-ground-not-a-script)
only where it is unresolved and relevant: who needs it and why now, observable
success with one acceptance example, scope, non-goals and anti-goals, constraints,
and conflicting priorities. For vague words such as "fast" or "easy", ask for a
concrete user situation or acceptable outcome. When an answer contradicts accepted
intent or the code, explain the conflict and ask which direction governs; preserve
history rather than silently replacing it.

Play back as you go. As soon as one part is understood well enough to describe (what
it's for and who it serves, or how one piece behaves), describe it back in a short
paragraph, marking your guesses as guesses, and ask what is wrong or missing. Then
move to the next part. Do not repeat the whole interview after each reply.

`You decide` delegates that choice: recommend and record a compatible decision
inside the stated constraints as the planner's call. It does not grant unrelated
execution or publication authority. `Skip` leaves the question open; `stop` ends
questioning, including confirmation questions, and preserves answered progress with
unresolved matters left open. Silence is neither an answer nor acceptance. In
scheduled/noninteractive runs, report the single highest-value question and leave
it pending; do not fabricate replies or poll.

## Companion frontends and platform scope

1. Establish the product boundary before discussing implementation: distinguish an existing website, a native companion app, an embedded website and an additional browser build of the companion. A second frontend for the same backend is not automatically a WebView or a second web application.
2. Use concrete product names when asking about platforms. If a reply mentions keeping the existing website and adding the companion, clarify whether a separate Flutter browser build is also required; do not treat the word "web" as proof of that requirement or silently discard an earlier explicit platform choice.
3. Inspect existing page loaders, public APIs, role gates and shared UI patterns before proposing parity. A generic list endpoint may omit the page's filters, summaries, history, position provenance or privacy projection. Prefer shared server read models over duplicating queries or scraping framework-internal page data.
4. Settle frontend/platform scope before asking about hosting or designing cross-origin authentication. First-party cookie reuse, native session handling and cross-site browser access have different constraints; an unresolved deployment choice does not authorize a new token protocol, relaxed cookies or broad CORS access.
5. Once native versus embedded and feature depth are settled, save those answers in the existing planning owner before another consequential round when continuity would otherwise be lost. Mark only unresolved choices Open; do not restart discovery or make understood product scope look undecided. Keep cloud session/state independent of local-device connection state when the requested module must work without that connection.

## Scope reductions and simpler test cleanup

When the user chooses a simpler qualitative task, remove timing, benchmark,
repeated-run and speed-target requirements from its active contract; retain
correctness checks instead of the retired measurement campaign. Prefer one bounded
test-value cleanup over new measurement infrastructure in that scope. Inspect
unchanged test verdicts before edits. Require each deletion or consolidation to
identify duplicated behavior/assertions and the retained test protecting them;
low priority, similar names, coverage overlap or fewer tests alone never justify
losing unique regression, security, boundary or configuration protection. Keep
uncertain cases and report recommendations instead.

State whether low-priority items means test cases or repository tasks; do not
silently turn a test-cleanup request into unrelated backlog cancellation. If the
user requests a new simpler replacement, save the successor and supersede the old
task without marking its unproven outcome passed. Creating that replacement does
not implement it, renew an execution budget or dispatch a worker.

## Save answers and finish the plan

During an ongoing interview, save material explicit answers in the existing owner
when useful for continuity; resolved terms go to the glossary owner as they settle.
Keep unanswered issues and inferred requirements clearly Open/Proposed. Never mark
an entire plan Accepted from one local answer. For a resumed interview, read saved
answers and ask only what remains unresolved. Apply the
[single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff);
save meaningful answers during the interview, then batch final documentation and
ledger checks once. Respect read-only scope and preserve concurrent edits, task IDs
and active leases. Keep a question scoped to the tasks it affects; an unanswered
optional feature must not hold independent accepted tasks. Do not restart Docs Sync
after each response.

When the frontier is empty, or the user asks to finish, give a concise readback:
outcome, users, success, scope/non-goals/anti-goals, constraints, their decisions,
the planner's calls and remaining open questions. Ask for confirmation only if the
synthesis introduces a material inference or unresolved conflict. Clear contextual
approval counts; do not demand a magic word or re-approve answers already given.
If a draft needs acceptance, present the concrete draft and bind the reply to that
scope. Approval covers what they saw: accepting a pitch or sequence does not approve
an unseen mockup or added requirements.

In writable mode, run a narrow docs-sync Maintain pass for the affected owners,
applying its canonical ledger and concurrency rules. Default invocation already
requests this persistence, so do not ask again whether to save. Accepted intent
becomes bounded Now/Next tasks with dependencies, acceptance, verification and
`Touches:` (plus `Resources:` where needed) per the
[TODO work center](../shared/TODO-WORKCENTER.md).
Unanswered product choices remain outside executable work. Run the
[builder check](../shared/PLANNING-CRAFT.md#builder-check-before-handoff) on the
saved tasks and fold its answers in. Validate changed docs and ledger, then run the
actual consumer backlog-check when handing off accepted tasks. Put the accepted-plan
anchor in each affected task's Sources, not only its Next action; repair supported
missing bindings and rerun the same gate. Report the ready first task separately
from a dependent successor: `backlog_reconciled_not_eligible` for a combined slice
can be normal dependency ordering, not a blocker.

Finish with changed document paths, decisions captured, the planner's calls, open
questions and the actual readiness result when a consumer check was applicable and
executed; otherwise state that readiness was not assessed. Questions-only/read-only
mode finishes with a conversational summary, no Maintain pass and no writes.
Docs-only scope leaves ready tasks undispatched. Existing implementation authority
permits the established autowork handoff without another permission question;
preserve review and owned-commit requirements.

Example: for "interview me about onboarding", inspect the current setup docs, offer
the skip line, then ask them to walk you through the last time someone got stuck
setting up. Use the answer to establish an observable onboarding outcome before
discussing installer details. Save it in the existing product/setup owner, not a
competing interview spec.
