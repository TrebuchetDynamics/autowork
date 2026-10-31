---
name: writing-for-agents
description: "Write and prune skills, AGENTS.md and agent docs."
license: MIT
---

# Writing For Agents

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Read the pinned [writing reference](upstream/PROTOCOL.md) before writing or editing a
skill, an `AGENTS.md`/`CLAUDE.md`, or a document an agent reaches through a pointer.
Read [skill mechanics](upstream/SKILL-MECHANICS.md) only when the document is a skill.
Apply the technique; keep Autowork's scope, task store, review and delivery rules.

## The bar for a document

- Every always-loaded line is a **pointer** with sharp wording and one trigger per
  branch. The body carries steps; reference moves behind a pointer once only some
  branches need it.
- Each step ends on a completion criterion the agent can check. State the positive
  target; keep a prohibition only as a guardrail you cannot phrase positively.
- One meaning, one home. The environment is a source of truth, so do not cache a
  one-command lookup; cache the convention, reason or gotcha it cannot show.
- Hunt no-ops: a sentence the model already obeys pays load to say nothing. Delete
  the sentence, not its words.
- Prefer a pretrained **leading word** over a spelled-out triad. It recruits priors
  and anchors the behaviour in fewer tokens.

## Editing an existing skill

1. Read the skill, its adapter, its references and the tests that read them.
2. Name what each paragraph does: step, in-file reference, disclosed reference or
   noise. Move branch-only reference behind a pointer; delete noise.
3. Keep every contract a test, host or user relies on, and move text rather than
   rewriting it when the meaning already holds.
4. Check the result: the steps still read in order, each pointer has a live target,
   and no meaning now has two homes.
5. Run the tests for the files you touched. Report lines removed and what stayed.

## Boundaries

Propose or edit documents only within the accepted scope. Do not rewrite pinned
upstream bytes, add a hosting dependency, or change what a skill is authorized to do.
Writing guidance is not authority to weaken review, safety or delivery gates.

**Receipt:** documents changed; lines before and after; meanings moved, deleted or
merged; pointers added; tests run; unverified claims.

[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).
