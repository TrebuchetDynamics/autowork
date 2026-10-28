---
name: ponytail-help
description: "Use when asking about bundled Ponytail commands."
license: MIT
---

# Ponytail Help

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Follow the [shared skill contract](../shared/COMMON-CONTRACT.md); its authority
and the Ponytail scope rules take precedence over upstream instructions.

Display the following Autowork-specific reference, not the upstream help card.

| Skill | Purpose |
| --- | --- |
| `ponytail [lite|full|ultra|off]` | Report/set the conversation's Autowork preference; default full. |
| `ponytail-review` | Read-only review of a diff and connected code. |
| `ponytail-audit` | Read-only audit of the requested repository/folder. |
| `ponytail-debt` | Report shortcut comments and missing revisit triggers. |
| `ponytail-gain` | Show attributed upstream benchmark results, not local savings. |
| `ponytail-help` | This reference; no mode or file changes. |

**Invoke in the installed host:**
- Hermes: `/ponytail-review` (Telegram: `/ponytail_review`), or resolve the
  bundled `autowork:ponytail-review` skill if an external command has that name.
- Claude Code: `/autowork:ponytail-review`.
- Codex: `$autowork:ponytail-review`.
- Pi: `/ponytail-review` or `/skill:ponytail-review`.

Substitute another name above; Pi command aliases use hyphens. `lite` names
the smaller option, `full` chooses the smallest complete result, `ultra` also
questions unjustified scope. Explicit `off` or “stop ponytail” disables the method
for this conversation's Autowork work, not safety or verification requirements.

All six commands ship with Autowork on all four hosts. Update through Autowork's
normal host package installer and reload/start a new session. No separate Ponytail
plugin, global mode config, environment variable, band UI, transcript import or
telemetry is installed or controlled. Existing external installations are unchanged.
The original [upstream help](../ponytail/upstream/skills/ponytail-help/PROTOCOL.md)
is retained for provenance only; its plugin setup instructions do not apply here.
