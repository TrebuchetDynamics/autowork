---
name: ponytail-audit
description: "Audit a repository with Ponytail rules."
license: MIT
---

# Ponytail Audit

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Follow the [shared skill contract](../shared/COMMON-CONTRACT.md); its authority
and the Ponytail scope rules take precedence over upstream instructions.

Read the [pinned audit protocol](../ponytail/upstream/skills/ponytail-audit/PROTOCOL.md).
Map the requested scope and rank concrete findings. Report only: no fixes,
new backlog, scheduler or repository-wide scan beyond the requested boundary.
State the expected load, unread areas and checks not performed.
## Boundaries

- Not a change review; use `/ponytail-review`.
- Not a marker list; use `/ponytail-debt`.

**Done when:** the audit report gives severity, evidence and one next action.
