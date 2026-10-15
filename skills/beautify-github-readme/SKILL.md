---
name: beautify-github-readme
description: "Redesign or audit a GitHub README, or create project-native SVG assets for it (hero, section headers, workflow diagrams, badges). Use when asked to beautify, redesign, visually refresh or audit a README; not for routine documentation edits."
version: 0.1.0
license: MIT
---

# Beautify GitHub README

`/beautify-github-readme` (Telegram `/beautify_github_readme`) applies the pinned
[Beautify GitHub README protocol](upstream/PROTOCOL.md) by oil-oil, MIT licensed
([licence](upstream/LICENSE), [provenance](UPSTREAM.json)). This adapter controls
host integration. Read the protocol, then apply the rules below, which take
precedence over it where they differ. Its `references/` and `scripts/` paths resolve
inside `upstream/`, except its README audit: run this skill's
`scripts/audit_readme.py` instead.

## Toolset rules

- **Scope first.** Keep the protocol's choice between README mode and asset-only
  mode, and its audit-only path. Only a request that names the scope ("redesign the
  whole README", "only a hero", "audit it") answers it; a bare "beautify it" does not.
  Otherwise ask the one compact scope question, through `clarify` when available.
  Scheduled, cron or Autowork-driven runs audit only unless their TODO task scope
  authorizes README or asset edits.
- **The README is documentation.** Its claims, commands and safety statements are
  Docs Sync facts. A redesign may reorder and shorten copy but must not drop a
  safety or policy statement, invent adoption, benchmarks or compatibility, or
  contradict [docs](../docs-sync/SKILL.md). After editing, run
  `python3 <docs-sync-skill-dir>/scripts/docs.py check <repo>` when the repository
  has `docs/roles.json`, plus the README audit below.
- **Pure SVG by default.** Hermes has no bundled image-generation skill. Offer hybrid
  composition only when an image-generation tool is actually available in this
  session and the subject needs raster material; otherwise build deterministic SVG.
  GIF output stays opt-in, as in the protocol, and needs Pillow and `rsvg-convert`.
- **No unsolicited promotion.** Do not make the protocol's step 9 attribution or
  showcase offer. Handle a "README MADE WITH" signature or showcase pull request only
  when the user asks for it, with each external action separately authorized.
- **Preview what you ship.** Render every SVG at 900 px and 360 px wide before
  embedding it, with whatever renderer is installed (`rsvg-convert`, Inkscape or a
  headless browser), and check light and dark backgrounds. Embed with relative paths
  and meaningful `alt` text so the README still reads with images off.
- **Delivery stays separate.** Assets go under `assets/readme/` unless the
  repository uses another location. Commit, push or open a pull request only through
  the repository's normal delivery workflow (for example
  [Git Commit Push](../git-commit-push/SKILL.md)) and its existing authority.

Run the README audit:

```sh
python3 "<beautify-github-readme-skill-dir>/scripts/audit_readme.py" /path/to/README.md
```

It applies the protocol's SVG checks and also follows GitHub's resolution: dark-mode
`<picture><source srcset>` variants, reference-style images, root-relative paths
from the repository root and `<…>` destinations; images in fenced code are skipped.

Report the mode used, files changed, what was deliberately left plain, the checks
run and any claim you could not verify.
