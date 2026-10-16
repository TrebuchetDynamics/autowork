---
name: plan-with-me
description: "Research, refine or challenge a plan through focused questions (including Grill Me), and save accepted decisions and tasks."
disable-model-invocation: true
---

# Plan With Me

Read the [host contract](../COMMON.md), pinned
[Autoresearch plan protocol](../../../skills/autoresearch/upstream/plan.md) and
[interactive planning adaptations](../../../skills/shared/RESEARCH-PLAN.md#interactive-planning-plan-with-me).
Refine the initial prompt into a working brief and investigate relevant evidence.
For important assumptions or explicit challenge mode, use
[challenge protocol](../grill-me/PROTOCOL.md) with the adaptations above; no
whole-frontier questionnaire or repeated approval of settled answers.
`Selected mode: challenge`, a Grill Me compatibility request, or an explicit
request to challenge a plan selects this mode. Preserve the literal user request
and its restrictions; mode selection adds no implementation or write authority.
Follow the [planning craft](../../../skills/shared/PLANNING-CRAFT.md): size the
work, offer to skip the questions, get the user describing before offering options,
and ask in rounds (one open question, or a few ready decisions numbered with
recommendations worded so "yes" accepts them), using native user-input tools or
chat. Inspect existing docs/source first so questions resolve product intent rather
than facts already in the repo. Play each understood part back with guesses marked.
Decide routine engineering details yourself and say them as your calls. Honor
questions-only/read-only without writing files.

Save explicit answers in existing requirement/spec documents when permitted. At
finish, summarize scope, non-goals, acceptance and open questions. Ask for approval
only if your synthesis adds material unaccepted intent. Reconcile accepted decisions
through [Docs Sync](../docs-sync/SKILL.md): full TODO.md tasks, priorities,
dependencies, checks and `Touches:`. Run the planning craft's builder check on the saved tasks
before reporting them ready. Do not start implementation merely because a plan exists.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Unchanged findings need
no new docs pass. Follow this host adapter for execution authority; the shared
contract does not require Hermes-native tooling on this host.
