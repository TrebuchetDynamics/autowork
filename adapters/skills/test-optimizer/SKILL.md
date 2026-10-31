---
name: test-optimizer
description: "Shrink test suites by removing redundant, low-value tests."
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
authority permits one supported batch. Read-only writes nothing. Prioritize proven
redundant, vacuous and obsolete test removal, then simplify what remains. Meaningless
tests need no replacement. Preserve distinct supported risks and oracles: rarity,
unchanged code and irrelevance to today's diff alone do not justify deletion.
Report actual code/case reductions separately from measured runtime. Keep review,
user limits, task-state and delivery restrictions throughout.
