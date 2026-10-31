---
name: plan-with-me
description: "Research, refine or challenge a plan through focused questions (including Grill Me), and save accepted decisions and tasks."
disable-model-invocation: true
---

# Plan With Me

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md), then the
[Plan With Me protocol](../../../skills/plan-with-me/SKILL.md) and its
[planning artifact and authority contract](../../../skills/shared/RESEARCH-PLAN.md).
The protocol owns the interview, uncertainty loop and save flow; run them in this
session with native user-input tools or chat.

Challenge mode is the protocol's mode: a `Selected mode: challenge`, a Grill Me
compatibility request or an explicit challenge request selects it. Read the
[challenge protocol](../grill-me/PROTOCOL.md); preserve the literal request and add
no implementation or write authority. Honor questions-only and read-only requests
without writing files.

`/plan-with-me blockers [repo|name]` is [`/blockers`](../blockers/SKILL.md): routine
planning repairs first, then genuine owner questions, easiest first; replanning
happens here before the next question.

Use the [single-pass handoff](../../../skills/shared/PLAN-HANDOFF.md#one-planning-pass-one-handoff):
resume accepted decisions and existing task IDs, investigate only missing evidence,
persist one affected batch, and reuse input-bound checks. Save accepted decisions and
complete task records with `autowork tasks add`/`goal`: placement, dependencies,
checks and `touches`. Run the planning craft's builder check, `autowork tasks
validate --worktree .`, and commit the batch once before reporting selection.

After the commit, `autowork tasks why ID` reports committed-store selection eligibility
and position only, not resource/ownership admission, capacity or dispatch. Report the
actual selection result, or say selection was not assessed. Distinguish a branch-local
commit from delivery to the actual canonical consumer: disclose whether that consumer
includes the commit and whether selection was checked there. Report runtime and
ownership unassessed unless observed.

Standalone planning stops despite earlier unrelated implementation permission. An
Autowork-owned substep returns to that same coordinator without execution inside
planning or competing workers, without asking again for settled authorization.
When existing execution fails without new product uncertainty, return the exact task
ID, attempt evidence and failed operation to the same coordinator for supported
recovery; do not reopen the product interview or create duplicate tasks.
A later explicit implementation instruction enters the execution workflow. The shared
contract requires neither Hermes-native tooling nor a claimed hard sandbox on this host.
