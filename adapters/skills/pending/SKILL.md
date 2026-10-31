---
name: pending
description: "Report open, done and next tasks."
disable-model-invocation: true
---

# Pending

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md), then follow the
[pending skill](../../../skills/pending/SKILL.md) in this session: run its read-only
query helper for the repository in question and report what is open, next, or done,
in the user's language, keeping task IDs. It writes nothing and starts nothing.
