# Planning craft

Shared method for Plan With Me and Plan For Me. It decides how well a plan is
understood and written; first load the
[planning artifact/authority contract](RESEARCH-PLAN.md#planning-artifact-and-authority-contract).
[The handoff](PLAN-HANDOFF.md) decides where it is saved and who executes it. Adapted from obra/superpowers `brainstorming` and mattpocock/skills
`grilling` and `domain-modeling` (both MIT), fitted to the `tasks/` work queue.

## Know what you know

Before planning, ask: what do I know about what they want, and why? Your belief
about the request is usually thinner than it feels. Size the work and say the size
in plain words; the user can override it.

| Size | Signal | Plan |
|------|--------|------|
| Clear task | everything that matters is in the request | no interview; save one complete task record (reuse its ID), then stop planning |
| Small change | one outcome, few decisions | brief, decisions and one or two tasks |
| Project | several outcomes, real trade-offs | written plan section, decisions and dependent tasks |
| Project discovery | a standalone Plan For Me request has no concrete objective, or only a vague direction | evidence-based project model and goal classes first, then one executable frontier; never an interview for a goal or invented product scope |

A discovery request starts from repository evidence, not a question: follow the
[discovery protocol](../plan-for-me/references/discovery.md). It may derive
engineering goals inside the accepted direction; new product directions stay
proposals.

If it grows mid-plan, say so and step up a size. If it is really several independent
projects, identify their order and independent lanes, then finish the whole requested
batch. Do not finish the invocation after planning just the first project.

## Facts and decision authority

Look up anything the repository, tools or primary sources can answer: never ask the
user for a fact. Inspect the relevant owner before asserting current behavior or
absence; absence from one inspected file is not absence from the repository.
When a fact is slow to find, keep planning the branches that do not
depend on it. Plan For Me resolves evidence-supported engineering trade-offs
within delegated scope; missing facts get bounded research, not a worker design
interview. Plan With Me retains consequential intent interviews and user
participation in consequential choices; use the uncertainty loop below. In either
mode, genuine owner-only intent and authority stay with the user.
Never infer authorization from an engineering preference, silence or an Accepted
heading.

Cross-check what the user says against the code. When they disagree, surface it:
"The importer drops whole batches, but you said partial imports are kept. Which is
right?" Decide internal naming, test seams and equivalent engineering options
yourself.

## Source-backed task scope

Every task includes a compact **Repo obligations triggered:** note in its existing
body: the normative doc owner and section for each changed observable contract,
required updates, generated outputs, guards and fixtures. State `none` with evidence
for categories that do not apply. Include every planned write in `touches` and its
validation in `checks`; docs are part of the deliverable, not a later worker's scope
violation. This is a prose content requirement, not a new task-store schema field.

Before saving, search specs/tests for assertions encoding the behavior being
replaced, including integration/browser consumers. Record file:line, keep or
re-baseline, and replacement intent; changed assertion files belong in `touches`
and `checks`. Quote the source expression or exact text for existing numeric and
contract invariants: minimum versus maximum, units, defaults, caps and clamping
precedence. Label new thresholds as planner decisions, not existing facts.
Preserve required caveat copy verbatim and independent invariants explicitly.

For interaction work, inventory current event owners before designing capture:
handlers, nested interactive elements, delegation, propagation and passive/default
behavior. Name the existing click, tap and keyboard activation paths to preserve.
For noninteraction work, omit this inventory rather than invent event requirements.

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

## Consequential uncertainty

Keep a compact working map in the existing brief or conversation, not a new
mandatory artifact. Consider users/outcome, a concrete success/failure example,
scope/non-goals, constraints, hard-to-reverse trade-offs and relevant edge cases.
For each open point, identify the decision, acceptance or task a different answer
would change. If it changes none, it is not an interview question. Distinguish
repository facts, explicit user choices, delegated planner calls and assumptions.
Reuse accepted answers on resume; only contradictory new evidence reopens them.

Use this loop, not a question quota:

1. Investigate facts and settle routine engineering details within authority.
   Across a bulk batch, group a shared uncertainty once and note affected tasks.
2. Ask the highest-impact unresolved user decision whose prerequisites are settled.
   State its concrete context and consequence. Thin intent calls for a real example
   ("What happened last time this got in your way?"), not an arbitrary menu. When
   evidence narrows a real trade-off, offer two or three realistic alternatives,
   your recommendation and what it gives up; allow a free-form answer.
3. Bind the reply only to what it resolves. A bare "yes" accepts a single
   unambiguous proposal, not several recommendations. For multiple choices, use
   explicit choice-scoped answers; if scope is ambiguous, leave affected choices
   open and clarify. Preserve all other settled decisions and user corrections.
4. Play back new material understanding, update the map and affected acceptance,
   then ask the next consequential question. For example, deciding capitalization
   does not settle whether blank input is rejected: ask that next if it still
   changes the requested behavior. Do not finish merely because one answer arrived
   or the current round ran out; check the relevant map, including acceptance.

| Observed state | Next action |
| --- | --- |
| Intent and acceptance actionable; no material open issue | Save the whole requested plan, no filler or routine-authority questions. |
| User says "you decide" | Resolve that choice within constraints as a planner call; continue the loop. |
| User says "skip" | Leave that choice open, continue independent decisions/work. |
| User says "stop/finish" | End all questioning; save resolved progress and scoped open issues, no invented answers. |
| User explicitly switches to Plan For Me | Reuse evidence and accepted decisions; choose within delegated scope, no interview restart. |

Silence is not acceptance. No habitual opening skip pitch or closing blanket
approval substitutes for consequential inquiry. In read-only mode, every saving
step above becomes a chat summary, with no writes. In writable mode preserve
resolved decisions for continuity and apply the single-pass handoff, without code
edits or a full Docs Sync pass per reply. Open issues hold only affected tasks.

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
  by merge, and merged-tree checks under the repository's execution contract.
- **Prerequisites are in scope.** If a defect already in the code would stop the
  task's checks, such as a broken test or a missing fixture, the task may repair
  it. Do not forbid "unrelated" fixes that the task's own checks depend on.
- **Offline acceptance.** Acceptance is what the worker can check here. Devices,
  production, live services and human review go under live checks, not Acceptance.
- **Independent tasks first.** Prefer tasks with disjoint `touches` that can run
  at once. For a dependency chain longer than three tasks, state why each link
  depends on the last. Split a task that touches unrelated areas.
- **Resources mean resources.** Use the `exclusive` or `live` resource only for a
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

One task, one reviewable outcome: about five files or fewer in `touches`, at most
three acceptance criteria, one test seam, and a record a reader takes in within a
minute. Split a larger task along file ownership, each piece owning its code, tests
and docs, not by layer (model, then API, then UI): a layer split chains every piece
to the one before it and leaves none testable alone.

When several feature tiers repeatedly rewrite one component and its tests/docs,
prefer one cohesive task with internal milestones. If separate reviewable outcomes
justify multiple tasks, declare shared paths in every record and describe the
actual scheduling constraints below. Rank alone is not mutual exclusion; do not
promise independent execution or add fictitious dependency/resource gates.

## Disjoint write sets

`touches` is the task's expected write set. Prefer disjoint writes, but report
actual overlap rather than invent prerequisites. Under
[`parallel_plan.py::plan`](../../pi-autowork/engine/parallel_plan.py):

- Tasks naming the same hot literal production file wait until the unlanded work lands.
  Hot means named by three or more unfinished tasks, including noncandidate
  contracts and live slots awaiting integration; file length does not make it hot.
  Cold files, directories, globs and test modules only rank likely-independent work
  first; their overlap alone does not hold dispatch. Test modules are excluded from
  the hot-file gate even when three or more tasks name them. Merge resolves actual
  conflicts and checks qualify the merged result; overlap is not a promise of no conflict.
- Add `depends_on` only for a real prerequisite, not merely a shared path or a
  preferred sequence. For example, overlapping tests or cold files do not require
  extraction or dependency edges.
- Choose extraction for cohesion, observed conflict cost and testability, not a
  line-count or task-count threshold.
  A bounded fix may stay in a large or hot file when it is cohesive and testable at
  an existing seam. Re-cut ownership or extract only when evidence makes that useful;
  do not invent a preliminary extraction task or another permission gate.
- Shared named resources serialize their users; `exclusive`/`live` run alone only
  for real resource needs. Keep protected-path coordination: protected-path tasks
  serialize with each other, not ordinary tasks in isolated worktrees. New manifests,
  lockfiles, schema/migration and CI files need explicit protected paths in `touches`
  before editing; a broad directory does not reserve them. These gates apply even
  when file overlap would otherwise only rank.
- Name exact files when you know them. Only when you do not, widen to the owning
  directories rather than omit the field.
- Never list the coordinator's files: `tasks/`, `BLOCKERS.md`, `TODO.archive.md`,
  `CHANGELOG.md`.
- A shared registry (command table, route list, export index) changes in one task,
  or in a closing glue task that depends on the others.

## Interfaces between dependent tasks

When one task uses what another makes, write the seam in both: a `Produces:` note in the
producer and a `Consumes:` note in the consumer, each naming the exact function, CLI
command or field and its shape, such as
`parse_feed(path) -> list[Entry(id: str, seen: datetime)]`. Both notes are
optional; the builder check compares them.

## Executable acceptance

Write each acceptance criterion as given/when/then and name the test that proves
it, new or existing (`tests/test_feed.py::test_skips_blank_rows`), which fails on
today's code. `checks` runs those tests directly. A criterion no test can check
here is a live check, not acceptance. The task's next action starts with the failing
test named in its acceptance.

Name the measurement seam for each criterion: observable output/value/element,
setup and owning test. Numeric measurements specify the defining rect/value, units
and tolerance; temporal behavior specifies the observation window; write budgets
identify the instrumented API, exact filter and reset point. Static string or
configuration checks need no invented timers or counters. A threshold without its
measurement seam leaves the worker to choose what counts as a pass.

Prefer extending an existing public test seam: add or extend at most one focused
test per behavior changed, without duplicating existing cases. A new focused file
or class is optional when it improves ownership or discovery, not a prerequisite.
No tests merely for docs, config or renames; an explicitly scoped
instruction-contract guard tests the instruction behavior itself, not every prose
edit. Reuse existing negative guards and required checks rather than add a separate
test for every risk.

Run focused tests and the task's `checks` while working, not the whole suite after
every edit. Preserve every task-required check and independent review. Follow the
repository's execution contract: when the runner owns the merged-tree gate, do not
repeat it in the worker; otherwise run a required worker full gate once at the end.
For the supported checker, the runner uses an affected landing check on the merged
candidate (with conservative full fallback). Main retains its separate full check
after landing. An affected-only pass is not a full-main pass; neither source-contract
checks nor this guidance prove model adherence or faster workers. See
[affected landing checks](../../pi-autowork/README.md#affected-landing-checks).

## Pre-mortem before saving

Imagine the batch landed and broke something. Name up to three ways: an existing
behaviour that regressed, an input the plan is silent on (empty, duplicate, huge,
malformed), or a consumer of changed state that now misreads it. Map each to an
existing guard, a focused test within the behavior budget, or an explicit exclusion
in the owning task's scope. Write
one line of invariants every task in the batch keeps, in the plan section or each
task (for example "the on-disk format does not change").

## Decision closure

Before calling a task ready, walk from starting inputs through implementation and
verification to handoff. Select interfaces, data, error, compatibility and migration
behavior where relevant; check reachable inputs and setup, bounded prerequisite
repairs, and exact checks and success evidence. Use repository conventions and
bounded research to settle material engineering choices now, not another design
interview for the worker.

When material choices exist, keep one compact decision map in the existing
plan/task body: choice, selected approach and evidence/reason, rejected alternative
when meaningful, affected task IDs and acceptance/check. This is prose, not a new
required field or template for every small task. For a clear task, fill only actual
gaps; no extra interview or builder ceremony.

Give every material builder finding one disposition:

| Finding | Saved disposition |
| --- | --- |
| Already answered | Reuse settled evidence; copy the answer and source into the affected task. |
| Planner-resolvable | Research missing facts and resolve consequential engineering choices within delegated scope; record the planner's call and its check. In Plan With Me, use the uncertainty loop for consequential choices not delegated by the user. |
| Worker-reversible | Explicitly leave reversible coding details to the worker within the selected contract; no permission question. |
| Owner/external-blocked | Keep only affected tasks pending with the exact missing intent, authority or input and resume condition; independent accepted tasks stay ready. |

New tests and fixtures the task can create are deliverables, not external blockers.
Name the bounded local setup/repair in scope and its verification; do not quietly
expand exclusions. If an input really cannot be reached or created under the
contract, record that input and its resume condition instead of declaring readiness.
Keep real live qualification separate and unmet; no offline substitute or waiver.

Persist each resolution in the affected contract, not merely as builder advice.
No material finding remains unclassified in a ready task. Recheck changed findings,
not the whole unchanged planning pass. This closes known choices, not a guarantee
against unknown failures, and grants no implementation or external authority.

## Builder check before handoff

For plans requiring the builder check below, run it before committing the batch or
making it runnable, not after an authorized runner can select it. Have it read as
the builder who cannot ask questions. Dispatch a fresh read-only subagent
(`delegate_task`, or the host's equivalent) with:

> You are the engineer who will implement task(s) IDS in REPO. You cannot talk
> to the planner. Read the task records (`tasks/items/<ID>.md`), their cited plan,
> repository instructions, implementation, existing tests and normative docs.
> Check required docs missing from `touches`, stale contradictory assertions,
> numeric bounds, event ownership and measurement seams against those sources;
> cite file:line and the proving expression/assertion for each material finding.
> Mark unavailable evidence unverified. Report only material contract gaps and
> the questions you would still need answered before you could implement well:
> places where you would have to guess and a wrong guess would matter. For each,
> give the question and why the answer changes the work, ranked by importance. Skip
> anything the tasks leave to the implementer, anything you could reasonably decide,
> and wording nitpicks. Also list anything that would make you stop and wait for
> someone: an input you could not get, a check you could not run here, or a
> prerequisite the task forbids you to fix. Also identify which saved tasks could
> run in parallel and why the rest cannot. If nothing important is left, say
> "nothing important left".

Without a subagent tool, read the tasks as that builder yourself. Apply
[decision closure](#decision-closure) to every material finding, including inputs,
setup and checks, and persist its disposition before reporting readiness.

Then check the batch yourself and fix it before handoff: each executable task
declares bounded `touches` (and the `exclusive` resource only with a real resource
reason); shared writes have the actual admission/ranking constraints above recorded
(re-cut only when useful), true prerequisites have `depends_on` edges, and unrelated
lanes remain independent. `depends_on` lists task
IDs only; each `Consumes:` matches its producer's `Produces:`. Map every
requested outcome to a complete saved task or a scoped unresolved choice; future
roadmap ideas do not replace the requested batch.

Bring only genuine owner-only questions to the user, most important first, with
each question's effect on the work. Plan With Me also keeps its interactive
consequential choices. Reuse the uncertainty loop and choice-scoped answers;
do not turn builder findings into a blanket approval or repeat settled questions.
If an answer exposes a new material issue, resolve it before declaring the affected
task ready. Keep just affected tasks pending;
independent tasks stay ready. Skip the check for a clear task, a questions-only
run or a dry run.

## Approval covers what you showed

"Sounds good" approves what the user saw, not a description you have not written
yet. Mark guesses as guesses; only what they said goes in as theirs. A throwaway
spike they agreed to stays throwaway; keeping its result is a new planning request.
