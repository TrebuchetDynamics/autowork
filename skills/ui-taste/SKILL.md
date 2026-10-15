---
name: ui-taste
description: "Use to build, polish or review web and iOS UI screens."
version: 0.2.0
license: Apache-2.0
---

# UI Taste

`/ui-taste` (Telegram `/ui_taste`) applies Uizze's pinned
[UI Taste protocol](upstream/PROTOCOL.md), Apache-2.0 licensed
([licence](upstream/LICENSE), [notice](upstream/NOTICE),
[provenance](UPSTREAM.json)). This adapter controls host integration. Read the
protocol, then apply the rules below, which take precedence over it where they
differ. Its `reference/` playbooks and `references/` policy resolve inside
`upstream/`; load only the ones the request needs.

## Toolset rules

- **One design skill per task.** Use the design skill the user names. A UI request
  that names neither uses UI Taste. [Impeccable](../impeccable/SKILL.md) stays the
  choice for its own commands (`/impeccable <command>`, its `init`, hooks, doctor
  and pin tooling); do not load both for the same task.
- **Scheduled work is read-only by default.** Scheduled, cron or Autowork-driven
  runs audit only unless their TODO task scope authorizes UI edits; use the
  protocol's audit playbook and report findings.
- **Paid Uizze tools stay optional.** Call `find_ui_references` or
  `find_ui_materials` only when the host already exposes them in this session.
  Toolset and this skill never configure an MCP server, sign up for an account, ask
  for a token or payment, or send private source code, customer data or credentials
  in a query. Missing access never blocks local design work.
- **Verify what you ship.** Render the result with whatever browser or renderer is
  available at representative desktop and mobile sizes. When nothing can render it,
  say the checks were code-only rather than claiming a visual pass.
- **Delivery stays separate.** Documentation changes follow
  [Docs Sync](../docs-sync/SKILL.md). Commit, push or publish only through the
  repository's normal delivery workflow (for example
  [Git Commit Push](../git-commit-push/SKILL.md)) and its existing authority.

Report the playbooks used, files changed, what was actually rendered and checked,
and any limitation that affected the result.
