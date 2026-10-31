---
name: grill-with-docs
description: "Grill a plan and record decisions as ADRs and terms."
disable-model-invocation: true
---

# Grill With Docs

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md), then the
[host-neutral Grill With Docs workflow](../../../skills/grill-with-docs/SKILL.md) and its pinned
reference. Use this host's own file, terminal and delegation tools. No Hermes runtime,
Pi extension or external service is required.

Where the pinned upstream entry calls another skill by name, the host-neutral workflow
states the composition directly: this host exposes commands, not a Skill tool. Delegate
a bounded search only when the host provides a sub-agent tool. Preserve read-only
requests, review gates, task state and delivery limits, and stop before implementation
until the owner confirms the outcome the workflow requires.

Report what the workflow's receipt asks for, and separate what you read from what you
changed.
