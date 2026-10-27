---
name: bug-harvest
description: "Use when hunting unknown bugs in a continuing campaign."
license: MIT
---

# Bug Harvest

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Run an evidence-backed hunt for unknown defects, one active candidate at a time.
For a supplied known repro, use the debugging method directly instead of starting
a campaign. Apply the [host and authority adaptations](../shared/PI-TOOLSET.md)
before reading the pinned [bug-harvest protocol](upstream/PROTOCOL.md).

## Campaign boundary

Inspect current source, instructions, task state and ownership; quarantine unrelated
dirty files. Establish the user's scope and explicit stop limits before discovery.
Use a bounded executable check to find evidence, not code smells or endless TODO
searching. Keep at most three leads; select the clearest reproducible consequence
with the smallest blast radius.

For the selected bug, record symptom, evidence, reproducer, expected post-fix
signal and likely files. Confirm the failure, identify its root cause, make the
smallest safe fix, add discriminating regression protection, rerun the repro and
affected checks, and satisfy required review. Separate pre-existing failures from
introduced regressions. Record severity with its concrete impact and trigger.

Continue to the next evidence-backed candidate only while within the authorized
campaign and remaining limits. A named next candidate is not permission to exceed
a one-bug/slice limit. A bounded rescan finding no candidate, user stop, exhausted
budget, unsafe ownership or missing required capability ends or pauses the hunt.

**Receipt:** task/bug, severity and why, repro before → after, changed paths,
regression checks, review state, search after the last fix (or NOT_RUN because a
limit was reached), stop reason and resumable next action. Never claim no bugs
exist; report what was searched. No automatic commit or push.

**Example:** “Hunt one bug in the parser; no push” permits one verified fix and a
checkpoint, not a second repair or a claim that the parser has no remaining bugs.

[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).
