---
name: pending
description: "Use to see what is pending or done in a repository's task ledger, without changing it."
disable-model-invocation: true
---

# Pending

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Read the [host contract](../COMMON.md), then follow the
[pending skill](../../../skills/pending/SKILL.md) in this session: run its read-only
query helper for the repository in question and report what is open, next, or done,
in the user's language, keeping task IDs. It writes nothing and starts nothing.
