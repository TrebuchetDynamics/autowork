---
name: lgtm
description: "Resolve a short approval against the immediately preceding concrete recommendation."
disable-model-invocation: true
---

# Lgtm

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md).

Resolve the latest assistant-owned checkpoint only. If work remains, state the accepted scope and perform it once with normal verification. If the checkpoint reports completed work, acknowledge without repeating it. Preserve exclusions; do not infer commit/push/deployment from a generic approval that did not offer them. Ask only when no safe target exists.
