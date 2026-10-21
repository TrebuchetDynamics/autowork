# Autoresearch plan adaptations

Read this contract **before** the pinned `skills/autoresearch/upstream/plan.md`
and supporting methods. It governs Plan For Me, Plan With Me, challenge/Grill Me
compatibility and every Autoresearch plan route on every host. Its planning
boundaries take precedence over generic method prompts, task-sizing shortcuts and
execution defaults; host tool mappings still apply. These are instructions, not a
hard tool sandbox. Use host restrictions when available; do not claim enforcement
that the host does not supply.

## Planning artifact and authority contract

Bind the current request before acting:

| Invocation | Allowed finish |
| --- | --- |
| Explicit standalone planning | Save the requested plan/batch, then stop. Earlier unrelated implementation permission does not widen this request. |
| Autowork-owned planning substep | Return findings and saved tasks to that **same coordinator**; its existing execution authority continues outside this substep. No competing worker, dispatch or workflow restart. |
| Questions-only, read-only, chat-only, no-write, no changes or dry-run | Read and discuss only; save nothing, including queue metadata or research scratch. |
| Later explicit instruction to implement the accepted plan | End planning and enter the authorized execution workflow under repository checks, ownership and delivery limits. |

“Yes”, “looks good”, an easy fix, an accepted/saved plan and a supporting skill
urging coding are not transitions to implementation. Acceptance of a plan is not
execution authority. Do not ask an already-authorized coordinator to approve again.

Classify each proposed write by **artifact role**, not filename or extension:

| Role | During writable planning |
| --- | --- |
| Existing plan/spec/requirements owners; complete TODO bodies and existing goals index | Save in-scope evidence, decisions, questions and ordered tasks through narrow Docs Sync. Preserve IDs, history, active contracts and unrelated batches. |
| Temporary research notes/results | Only bounded, allowed scratch; never implementation disguised as a spike. No scratch in no-write mode. |
| Production code, tests, fixtures, executable instructions (including Markdown `SKILL.md`), CI, manifests and lockfiles | Implementation: describe future changes in tasks; do not write them during planning. |

Investigate with reads and safe checks. Inspect commands for generated files,
cache writes and live effects before running them; a command called “dry-run” may
mutate. Do not repair implementation, generate tests, install dependencies, alter
services, commit or push to make a planning check pass. Name future tests/checks as
proposed/unrun. Preserve someone else's dirty work. If this occurrence crosses its
own boundary, stop the offending action and report attributable changes; do not
hide them with reset/clean or overwrite unrelated work.

## Full requested batch

1. Inventory **every requested outcome**, existing task ID and unresolved choice.
   Group shared decisions/evidence once. A clear one-line task still gets a complete
   saved body; “no interview” means no unnecessary questions, not “implement now”.
2. Save one coherent batch with complete task bodies: scope/exclusions, decisions,
   sources/evidence, observable acceptance, exact checks, bounded `Touches:` and
   actual shared `Resources:` where needed. Use the
   [handoff](PLAN-HANDOFF.md#one-planning-pass-one-handoff). Do not stop when the
   first task becomes clear or substitute a roadmap/count for requested bodies.
3. Order by real prerequisites. Keep independent ready lanes; overlapping writes
   constrain scheduling but do not by themselves create product dependencies.
   Re-cut ownership where useful, or report overlap honestly rather than promise
   parallel execution. Keep unresolved intent pending only on affected tasks.
4. Distinguish the complete requested batch from future evidence-dependent roadmap
   expansion. Rolling planning may defer that unknown expansion, not silently drop
   specified outcomes. At handoff, map each requested outcome to saved IDs or its
   explicitly scoped open choice, then report paths, checks and the next action
   without starting it. For optional scoped `Skills:` recommendations, follow the
   [existing convention](PLAN-HANDOFF.md#scoped-skills-convention); no new required field.

## Research and persistence method

1. Resume the requested goal, relevant repository source/tests and existing plans.
   If no goal was supplied, use the current authorized task or repository-development
   objective when unambiguous; otherwise ask for the missing goal. Do not invent it.
2. Investigate the actual uncertainty. Record source paths and concrete observations;
   fetch primary external sources when the decision depends on external behavior or
   current facts. Reading this protocol alone is not research. Reuse still-valid
   evidence and choose ordinary engineering details within delegated scope.
   Resolve consequential design/dependency choices here so Autowork receives an
   executable task, not an instruction to repeat the investigation. Record the
   chosen approach and checks in the existing task; leave reversible coding
   details to the worker. Follow the [handoff](PLAN-HANDOFF.md#one-planning-pass-one-handoff).
3. Apply upstream scope, metric, Verify, Guard and bounded-iteration analysis where
   meaningful. A qualitative plan needs observable acceptance, not a fabricated
   numeric metric. If feature tests do not exist yet, record proposed commands as
   unrun and add their implementation to the task. Do not retry nonexistent tests
   until they print a number or call missing tests a measured zero baseline.
   Inspect commands before running them; a Verify 'dry-run' can still mutate files.
   Explicit no-write/dry-run requests allow only nonmutating checks.
4. Replace upstream Phase 7's config-only finish and generic 'Run now?' question
   with persistence through Docs Sync: save the supported decision, alternatives
   rejected and why, evidence, remaining uncertainty, and actionable TODO task
   bodies/dependencies. Synchronize goals.json where this repository uses it.
   Reuse existing document owners and task IDs; do not create an experiment config
   or handoff.json as a substitute for the repository plan and work queue.
5. Read back affected documents and task bodies and run applicable consistency
   checks. Report actual saved paths/IDs, checks and next action. If persistence
   fails, report what remains unsaved; a chat answer is not a saved plan. Unchanged
   conclusions may reuse existing durable evidence, citing its location. New
   material reasoning must be saved even if implementation scope stays unchanged.
6. Finish according to the artifact/authority contract above. Return an
   Autowork-owned handoff to its same coordinator, not into execution inside this
   planning substep. In no-write mode show proposed updates inline and state that
   nothing was saved.

Apply the existing [single-pass handoff](PLAN-HANDOFF.md#one-planning-pass-one-handoff)
for acceptance, batching and reuse. Preserve genuine missing product intent as a
scoped question, not a reason to stop unrelated authorized planning.

## Existing execution is not a new planning problem

When Autowork already has a card and partial work, distinguish product uncertainty
from a session-continuation, accounting or runtime failure. If no product decision
is missing, return the exact failed operation and evidence to the same coordinator
for supported recovery. Do not create a replacement implementation task, rerun this
plan protocol, reset its budget or present another product plan as progress. Save
new technical findings to its existing task journal only when they add evidence.

## Interactive planning: Plan With Me

Use the same research and persistence method, with the user participating in
consequential decisions. Do not invoke Plan For Me as another coordinator or repeat
its discovery pass. Read the pinned plan protocol, then adapt its phases here.

- Turn the initial prompt into a concise working brief: intended users, problem,
  desired outcome, scope/non-goals, constraints and observable success. Separate
  explicit requirements from assumptions and unresolved choices; improve clarity
  without expanding the user's goal. Reuse this brief in the existing plan owner.
- Inspect enough evidence to ask a useful first question, then use the
  [consequential uncertainty loop](PLANNING-CRAFT.md#consequential-uncertainty).
  Map only open points that change intent, acceptance or tasks; group shared
  decisions once across the batch. Get the user describing before offering options.
  Ask the highest-impact ready question, with context and consequences; use concrete
  alternatives with trade-offs only when evidence narrows the choice. A bare “yes”
  accepts one unambiguous proposal, never several separate recommendations. Clarify
  ambiguous answers without accepting affected choices. After each reply, update
  what it actually resolves, investigate changed evidence and ask the next material
  question. Do not finish after one answer or complete a speculative plan before
  learning intent. For vague words such as “easy”, ask for a concrete user situation
  or success example. No habitual opening offer to skip; honor an explicit switch
  to Plan For Me using existing answers and evidence.
- Think wide privately to expose alternatives, and use Grill Me's decision tree to
  challenge important assumptions, failure cases and costly choices. Load the grill
  protocol only when that depth is useful or requested. This interview's round size,
  scope and stop rules override grill's exhaustive questioning and generic final
  implementation-approval prompt. Do not ask every possible question. Play each
  understood part back with guesses marked, and run the builder check before
  handing off saved tasks.
- Research repository facts yourself; ask the user about preferences, ambiguities
  and consequential tradeoffs the evidence cannot settle. “You decide” delegates
  that choice within the stated constraints; record your reasoned decision and
  continue. Explicit answers stay settled unless new evidence conflicts with them.
- Stop questioning once relevant intent and concrete acceptance are actionable,
  with no fixed question count or filler for fully specified requests, or when the
  user says finish/stop (including confirmation questions). A skipped choice stays
  open; a delegated choice becomes a planner call. Preserve corrections and reuse
  accepted decisions on resume. Keep remaining questions only on affected work.
  Save answers, evidence, decisions and TODO tasks in one coherent affected batch; meaningful
  interim answers may be saved for continuity. Do not require another interview or
  a complete documentation pass per answer. Questions-only/read-only/no-write and
  dry-run stay nonmutating; return the refined brief in chat instead.

The output is the same durable plan and work queue as Plan For Me, with the user's
answers informing it. Clearly distinguish their choices from delegated engineering
choices, proposals and unverified assumptions. A refined prompt alone is not the
writable-mode deliverable. Read back the saved plan/tasks before claiming persistence.
