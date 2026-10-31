---
name: ponytail-review
description: "Review a change with Ponytail rules."
license: MIT
---

# Ponytail Review

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Follow the [shared skill contract](../shared/COMMON-CONTRACT.md); its authority
and the Ponytail scope rules take precedence over upstream instructions.

Read the [pinned review protocol](../ponytail/upstream/skills/ponytail-review/PROTOCOL.md).
Review the named candidate and connected callers; otherwise inspect uncommitted
changes, falling back to the last commit. Report findings without editing code.
When supporting Autowork, contribute these criteria to its existing review lane.
A `Ship` verdict does not authorize delivery or replace required independent review.
## Boundaries

- Not a repository audit; use `/ponytail-audit`.
- Not implementation; use `/autowork`.

**Done when:** findings carry severity, evidence and a verdict, with unverified areas named.
