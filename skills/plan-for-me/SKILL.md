---
name: plan-for-me
description: "Use when the user wants you to investigate a repository, choose a supported approach, and save a plan and actionable tasks without an interview."
license: MIT
metadata:
  version: 0.1.0
  hermes:
    tags: [research, requirements, documentation, planning]
---

# Plan For Me

`/plan_for_me` (also `/plan-for-me`) investigates the repository, decides an
approach within the user's scope, and saves the plan and tasks. The public skill
ID is `plan-for-me`; its source directory is `skills/plan-for-me/`.

Read the [shared contract](../shared/COMMON-CONTRACT.md), the pinned
[Autoresearch plan protocol](../autoresearch/upstream/plan.md), and the
[planning adaptations](../shared/RESEARCH-PLAN.md). Apply the protocol directly;
the adaptations govern host tools, accepted scope, persistence and handoff.
Other research protocols remain in the [Autoresearch skill](../autoresearch/SKILL.md).

## Investigate and decide

Inspect project instructions, relevant implementation and tests, existing docs,
accepted decisions, TODO.md/goals.json and active task ownership. Reuse existing
answers and task IDs. Compare practical approaches and record the evidence for
the selected one. Resolve routine engineering choices autonomously; ask only for
consequential missing product intent or authority, and continue independent work.
Never invent acceptance or reopen settled choices without new evidence.

Use the [engineering cycle](../shared/ENGINEERING-CYCLE.md) to select additional
methods only for a concrete gap. Routine planning needs no experiment loop.
When called by Autowork, investigate its named uncertainty and return to the
current task. For backlog recovery, follow the
[bounded planning fallback](../autowork/references/backlog-planning.md).

## Save the plan and hand off

Follow the [TODO work center](../shared/TODO-WORKCENTER.md) and
[single-pass handoff](../shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff).
Use [Docs Sync](../docs-sync/SKILL.md) to persist findings and decisions in the
existing document owners and actionable tasks in TODO.md, synchronized with
goals.json. Include acceptance criteria, dependencies, verification and Now/Next
ordering; distinguish proposed decisions from accepted scope. Reconcile one
affected batch and reuse input-bound checks when the evidence is unchanged.

Planning includes saving this work by default. Explicit read-only, chat-only,
no-write or dry-run requests save nothing. Planning alone does not authorize
implementation, commits, worker dispatch or a recurring schedule. Preserve any
separate implementation authority already given and the normal Autowork gates.

Finish with the chosen approach, supporting evidence, changed document paths,
task IDs, unresolved questions and the next executable task. Report consumer
readiness only when its check actually ran; a saved plan is not completed work.
