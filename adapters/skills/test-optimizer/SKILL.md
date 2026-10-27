---
name: test-optimizer
description: "Use when reducing redundant tests or low-value scenarios."
disable-model-invocation: true
---

# Test Optimizer

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md), then the
[host-neutral Test Optimizer workflow](../../../skills/test-optimizer/SKILL.md).
It reuses the bundled test-suite optimization protocol; no Hermes runtime, Pi
extension or external test tool is required.

Bare invocation audits; explicit reduction/apply or existing implementation
authority permits one supported batch. Read-only writes nothing. Preserve
distinct risks and oracles; rarity alone never justifies deleting a test.
Report actual code/case reductions separately from measured runtime. Keep review,
user limits, task-state and delivery restrictions throughout.
