# Planning craft

Shared method for Plan With Me and Plan For Me. It decides how well a plan is
understood and written; first load the
[planning artifact/authority contract](RESEARCH-PLAN.md#planning-artifact-and-authority-contract).
[The handoff](PLAN-HANDOFF.md) decides where it is saved and who executes it. Adapted from obra/superpowers `brainstorming` and mattpocock/skills
`grilling` and `domain-modeling` (both MIT), fitted to the TODO.md work queue.

## Know what you know

Before planning, ask: what do I know about what they want, and why? Your belief
about the request is usually thinner than it feels. Size the work and say the size
in plain words; the user can override it.

| Size | Signal | Plan |
|------|--------|------|
| Clear task | everything that matters is in the request | no interview; save one complete TODO task (reuse its ID), then stop planning |
| Small change | one outcome, few decisions | brief, decisions and one or two tasks |
| Project | several outcomes, real trade-offs | written plan section, decisions and dependent tasks |

If it grows mid-plan, say so and step up a size. If it is really several independent
projects, identify their order and independent lanes, then finish the whole requested
batch. Do not finish the invocation after planning just the first project.

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

## Plan for an unattended worker

An Autowork worker runs a task alone and can only finish it or stop. Every stop
that a person must answer costs hours. So write each task so that it can be
finished without anyone:

- **Inputs it can reach.** Name each input and where it comes from, or how the
  worker makes it. Never write "the coordinator must provide", "obtain a handoff",
  "await a receipt" or "verify exclusivity". The runner provides no more than its
  worker prompt states: private ports and `$TMPDIR`, a fresh baseline, integration
  by merge, and the full check run on the merged tree.
- **Prerequisites are in scope.** If a defect already in the code would stop the
  task's checks, such as a broken test or a missing fixture, the task may repair
  it. Do not forbid "unrelated" fixes that the task's own checks depend on.
- **Offline acceptance.** Acceptance is what the worker can check here. Devices,
  production, live services and human review go under live checks, not Acceptance.
- **Independent tasks first.** Prefer tasks with disjoint `Touches` that can run
  at once. For a dependency chain longer than three tasks, state why each link
  depends on the last. Split a task that touches unrelated areas.
- **Resources mean resources.** Use `Resources: exclusive` or `live` only for a
  real shared thing, such as a device, a port the code cannot move, or a live
  account. Never use them for caution: a task marked so runs alone and holds back
  the queue.
- **No process gates the repository lacks.** Signatures, registries, ownership
  ledgers and evidence bundles belong in a task only if the repository already has
  the mechanism, and the task says how to use it.
- **Questions only for the owner's part.** These are credentials, devices,
  spending, a change to third-party software, and product, security or scope
  decisions. Anything else is the planner's call, recorded as such. Don't leave
  it for the worker to ask about.

## Size each task

One task, one reviewable outcome: about five files or fewer in `Touches:`, at most
three acceptance criteria, one test seam, and a body a reader takes in within a
minute. Split a larger task along file ownership, each piece owning its code, tests
and docs, not by layer (model, then API, then UI): a layer split chains every piece
to the one before it and leaves none testable alone.

## Disjoint write sets

`Touches:` is the task's expected write set. Parallel Autowork runs likely-independent
work first, and a task naming a file that unlanded work also names waits until it lands
(a directory or glob only ranks). The plan is what keeps write sets apart, so tasks can
run together:

- Tasks that can run together have disjoint writes. Re-cut shared ownership where
  useful; otherwise report the scheduling overlap. Add `Dependencies:` only for a
  real prerequisite, not merely a shared path or a preferred sequence.
- A hot file, one named by three or more open tasks or longer than about 1500 lines,
  gets a first task that extracts the part being changed into its own module; later
  tasks touch that module.
- Put each task's tests in a new focused test file or class, not appended to a
  shared large suite.
- Name exact files when you know them. Only when you do not, widen to the owning
  directories rather than omit the field.
- Never list the coordinator's files: `TODO.md`, `TODO.archive.md`, `goals.json`,
  `CHANGELOG.md`.
- A shared registry (command table, route list, export index) changes in one task,
  or in a closing glue task that depends on the others.

## Interfaces between dependent tasks

When one task uses what another makes, write the seam in both: `Produces:` in the
producer and `Consumes:` in the consumer, each naming the exact function, CLI
command or field and its shape, such as
`parse_feed(path) -> list[Entry(id: str, seen: datetime)]`. Both fields are
optional; the builder check compares them.

## Executable acceptance

Write each acceptance criterion as given/when/then and name the test that proves
it, new or existing (`tests/test_feed.py::test_skips_blank_rows`), which fails on
today's code. `Checks:` runs those tests directly. A criterion no test can check
here is a live check, not Acceptance. The task's next action starts with the failing
test named in its Acceptance.

## Pre-mortem before saving

Imagine the batch landed and broke something. Name up to three ways: an existing
behaviour that regressed, an input the plan is silent on (empty, duplicate, huge,
malformed), or a consumer of changed state that now misreads it. Give each a guard
test in the task that owns it, or an explicit exclusion in that task's scope. Write
one line of invariants every task in the batch keeps, in the plan section or each
task (for example "the on-disk format does not change").

## Builder check before handoff

Before reporting a written plan as ready, have it read as the builder who cannot ask
questions. Dispatch a fresh subagent (`delegate_task`, or the host's equivalent) with:

> You are the engineer who will implement TODO task(s) IDS in REPO. You cannot talk
> to the planner. Read the task bodies and the plan section they cite. Report only
> the questions you would still need answered before you could implement well:
> places where you would have to guess and a wrong guess would matter. For each,
> give the question and why the answer changes the work, ranked by importance. Skip
> anything the tasks leave to the implementer, anything you could reasonably decide,
> and wording nitpicks. Also list anything that would make you stop and wait for
> someone: an input you could not get, a check you could not run here, or a
> prerequisite the task forbids you to fix. Also identify which saved tasks could
> run in parallel and why the rest cannot. If nothing important is left, say
> "nothing important left".

Without a subagent tool, read the tasks as that builder yourself. Sort the questions:

- **Answered already** by the conversation or repository: write the answer into the task.
- **Minor**: a sensible builder could settle it without changing the outcome. Settle
  it and mark it as the planner's call.
- **Theirs**: only the user can answer it, and the answer changes what gets built.

Then check the batch yourself and fix it before handoff: each executable task
declares bounded `Touches:` (or `Resources: exclusive` with a real resource reason);
shared writes are re-cut or explicitly nonparallel, true prerequisites have
`Dependencies:` edges, and unrelated lanes remain independent. `Dependencies:`
lists task IDs only; each `Consumes:` matches its producer's `Produces:`. Map every
requested outcome to a complete saved task or a scoped unresolved choice; future
roadmap ideas do not replace the requested batch.

Bring the "theirs" pile in one message, most important first. That is the only
question round the check produces. Until answered, keep just the affected tasks
pending; independent tasks stay ready. Skip the check for a clear task, a
questions-only run or a dry run.

## Approval covers what you showed

"Sounds good" approves what the user saw, not a description you have not written
yet. Mark guesses as guesses; only what they said goes in as theirs. A throwaway
spike they agreed to stays throwaway; keeping its result is a new planning request.
