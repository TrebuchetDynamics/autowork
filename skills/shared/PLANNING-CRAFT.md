# Planning craft

Shared method for Plan With Me and Plan For Me. It decides how well a plan is
understood and written; [the handoff](PLAN-HANDOFF.md) decides where it is saved and
who executes it. Adapted from obra/superpowers `brainstorming` and mattpocock/skills
`grilling` and `domain-modeling` (both MIT), fitted to the TODO.md work queue.

## Know what you know

Before planning, ask: what do I know about what they want, and why? Your belief
about the request is usually thinner than it feels. Size the work and say the size
in plain words; the user can override it.

| Size | Signal | Plan |
|------|--------|------|
| Clear task | everything that matters is in the request | no interview; one TODO task, or say it is ready for Autowork |
| Small change | one outcome, few decisions | brief, decisions and one or two tasks |
| Project | several outcomes, real trade-offs | written plan section, decisions and dependent tasks |

If it grows mid-plan, say so and step up a size. If it is really several independent
projects, say so, agree on an order and plan them one at a time.

## Facts are yours, decisions are theirs

Look up anything the repository, tools or primary sources can answer: never ask the
user for a fact. When a fact is slow to find, keep planning the branches that do not
depend on it. Put only preferences, intent and consequential trade-offs to the user.

Cross-check what the user says against the code. When they disagree, surface it:
"The importer drops whole batches, but you said partial imports are kept. Which is
right?" Decide internal naming, test seams and equivalent engineering options
yourself.

## Cover the ground, not a script

Territory to cover, never read out as a questionnaire: what it is and what makes it
matter; why now and what success looks like; goals, non-goals and **anti-goals**
(what would make it a failure even if it technically works); prior art and what was
already tried; constraints; the details they care about; and which how-it-gets-made
choices (platform, language, libraries, data) they want to make versus hand to you.
When there is existing work, build on what it already uses.

Anchor questions in specifics: "Walk me through the last time this broke", "If it
could only do one of these well, which?", "What would make you wince if I got it
wrong?" A guess they can correct ("I'm guessing this is because X keeps biting you?")
often beats a question.

## Think wide, then say your calls

Before proposing an approach, generate several, drop the weak ones (including any
that fight the stated why) and show the comparison only when it helps a decision.
Say every default out loud: a default they never heard is one they could not reject.
Record each choice you made as the planner's call, never as something the user
agreed to.

## Name things precisely

Use the repository's existing glossary or terminology owner when there is one. When
a term is vague or overloaded ("account": customer or user?), propose one canonical
term and record it; challenge a term that conflicts with the glossary. Stress-test
boundaries with concrete edge-case scenarios. A glossary holds domain terms only, not
implementation notes or general programming concepts. Create `GLOSSARY.md` only when
the repository has none and a resolved project term would otherwise be lost.

Record a decision as its own ADR (in the existing decisions owner, or `docs/adr/`
when none exists) only when all three hold: hard to reverse, surprising without
context, and the result of a real trade-off. Otherwise one line in the task's
decisions is enough. An ADR can be a single paragraph: context, decision, why.

## Builder check before handoff

Before reporting a written plan as ready, have it read as the builder who cannot ask
questions. Dispatch a fresh subagent (`delegate_task`, or the host's equivalent) with:

> You are the engineer who will implement TODO task(s) IDS in REPO. You cannot talk
> to the planner. Read the task bodies and the plan section they cite. Report only
> the questions you would still need answered before you could implement well:
> places where you would have to guess and a wrong guess would matter. For each,
> give the question and why the answer changes the work, ranked by importance. Skip
> anything the tasks leave to the implementer, anything you could reasonably decide,
> and wording nitpicks. If nothing important is left, say "nothing important left".

Without a subagent tool, read the tasks as that builder yourself. Sort the questions:

- **Answered already** by the conversation or repository: write the answer into the task.
- **Minor**: a sensible builder could settle it without changing the outcome. Settle
  it and mark it as the planner's call.
- **Theirs**: only the user can answer it, and the answer changes what gets built.

Bring the "theirs" pile in one message, most important first. That is the only
question round the check produces. Until answered, keep just the affected tasks
pending; independent tasks stay ready. Skip the check for a clear task, a
questions-only run or a dry run.

## Approval covers what you showed

"Sounds good" approves what the user saw, not a description you have not written
yet. Mark guesses as guesses; only what they said goes in as theirs. A throwaway
spike they agreed to stays throwaway; keeping its result is a new planning request.
