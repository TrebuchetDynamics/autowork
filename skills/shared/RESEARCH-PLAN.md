# Autoresearch plan adaptations

Read the pinned `skills/autoresearch/upstream/plan.md` as the planning method.
These host adaptations take precedence over its generic prompts and output format.
They apply to Plan For Me, Plan With Me and every Autoresearch plan alias on every host.

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
6. Planning alone does not start implementation, commit, push or a timer. When
   Autowork called this protocol under existing implementation authority, return
   the saved handoff to that same coordinator and continue its task without asking
   again. Explicit read-only/chat-only/no-write/dry-run requests override persistence;
   show proposed updates inline and state that nothing was saved.

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
- Inspect enough evidence to ask a useful first question. Ask one highest-impact
  question at a time, wait for the answer, then investigate only the uncertainty
  that answer changes. Do not complete a speculative plan before learning intent.
  Offer practical options, tradeoffs and a recommendation when useful. For vague
  words such as “easy”, ask for a concrete user situation or success example.
- Use brainstorming to expose alternatives and Grill Me's decision tree to challenge
  important assumptions, failure cases and costly choices. Load the grill protocol
  only when that depth is useful or requested. This interview's one-question pacing,
  scope and stop rules override grill's whole-frontier rounds, exhaustive questioning
  and generic final implementation-approval prompt. Do not ask every possible question.
- Research repository facts yourself; ask the user about preferences, ambiguities
  and consequential tradeoffs the evidence cannot settle. “You decide” delegates
  that choice within the stated constraints; record your reasoned decision and
  continue. Explicit answers stay settled unless new evidence conflicts with them.
- Stop questioning once the brief and acceptance are actionable, or the user says
  finish/stop. Preserve remaining questions only on affected work. Save answers,
  evidence, decisions and TODO tasks in one coherent affected batch; meaningful
  interim answers may be saved for continuity. Do not require another interview or
  a complete documentation pass per answer. Questions-only/read-only/no-write and
  dry-run stay nonmutating; return the refined brief in chat instead.

The output is the same durable plan and work queue as Plan For Me, with the user's
answers informing it. Clearly distinguish their choices from delegated engineering
choices, proposals and unverified assumptions. A refined prompt alone is not the
writable-mode deliverable. Read back the saved plan/tasks before claiming persistence.
