---
name: ponytail-debt
description: "List deferred shortcut comments."
license: MIT
---

# Ponytail Debt

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Follow the [shared skill contract](../shared/COMMON-CONTRACT.md); its authority
and the Ponytail scope rules take precedence over upstream instructions.

Read the [pinned debt protocol](../ponytail/upstream/skills/ponytail-debt/PROTOCOL.md).
Use the host's repository search or its documented Git scan. Run in the requested
repository; Git exit 1 means no matches, not a failed scan. Report other errors.
Treat custom markers as literal data (escape regex metacharacters and pass an
argument, never interpolate shell code). Inspect hits before counting them.

The default scan covers `#`, `//` and `/*` comments and respects ignore rules;
it can miss other comment styles and tracked-but-ignored files. Disclose relevant
limits. Blame is optional and requires tracked history. Report only; if persistence
is explicitly requested, use the existing document/task owner rather than creating
a competing debt backlog. No-marker output is evidence only for the scanned scope.
## Boundaries

- Not a fix and not an audit; use `/ponytail-audit` for the repository view.

**Done when:** deferred shortcut markers are listed with path, owner and why.
