---
name: ponytail
description: "Choose Ponytail guidance or a level."
license: MIT
---

# Ponytail

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Follow the [shared skill contract](../shared/COMMON-CONTRACT.md); its authority
and the Ponytail scope rules take precedence over upstream instructions.

Use the [pinned protocol](upstream/skills/ponytail/PROTOCOL.md) under the shared
scope rules. No argument reports the current preference; `lite|full|ultra|off`
sets it for Autowork work in this conversation only. With a task, apply the method
within that task's authority; selecting a level alone does not start work.

See [help](../ponytail-help/SKILL.md) for the six commands. The optional read-only
codebase map script is documented in the shared method; do not activate hooks.
## Boundaries

- Not a review; use `/ponytail-review`.
- Not an audit; use `/ponytail-audit`.
- Not a deferred-marker list; use `/ponytail-debt`.

**Done when:** the requested guidance or level is stated and applied to the named work.
