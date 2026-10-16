---
name: beautify-github-readme
description: "Use to redesign or audit README visuals and SVG assets."
version: 0.1.1
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
  Before asking, reuse scope already answered for the current task: corrections and
  repeat invocations continue it unless the user changes it. Ask only when that
  context leaves scope genuinely unknown; do not restart the interview.
  Scheduled, cron or Autowork-driven runs audit only unless their TODO task scope
  authorizes README or asset edits.
- **The README is documentation.** Its claims, commands and safety statements are
  Docs Sync facts. A redesign may reorder and shorten copy but must not drop a
  safety or policy statement, invent adoption, benchmarks or compatibility, or
  contradict [docs](../docs-sync/SKILL.md). After editing, run
  `python3 <docs-sync-skill-dir>/scripts/docs.py check <repo>` when the repository
  has `docs/roles.json`, plus the README audit below.
  Before restructuring, record existing heading targets, command/flag semantics and
  policy disclosures; verify them after editing so moved sections do not break
  incoming links or conceal scope expansion. Put host selection, the shortest
  supported install path and a first-use smoke check before task-ledger mechanics,
  migration, recovery or contributor instructions. Use collapsible details for fleet
  setup and long task references, but keep consequential warnings visible directly
  before installation.
- **Branding restraint.** Prefer a plain project heading and real
  product proof over invented logos, oversized title banners or duplicated wordmarks.
  Beautification does not require a new asset or authorize an app-brand redesign.
  If a newly invented mark is rejected, remove it and its embed rather than making
  another unsolicited logo; remove only attributable assets and reconcile task notes
  that still describe the discarded asset as delivered.
- **Pure SVG by default.** Hermes has no bundled image-generation skill. Offer hybrid
  composition only when an image-generation tool is actually available in this
  session and the subject needs raster material; otherwise build deterministic SVG.
  GIF output stays opt-in, as in the protocol, and needs Pillow and `rsvg-convert`.
- **No unsolicited promotion.** Do not make the protocol's step 9 attribution or
  showcase offer. Handle a "README MADE WITH" signature or showcase pull request only
  when the user asks for it, with each external action separately authorized.
- **Inspect asset consumers before replacing them.** Trace README images through
  the site, capture generator and nearest contract tests. When a new title asset
  is warranted, isolate it from shared heroes rather than changing unrelated
  surfaces or forcing recapture. Keep existing capture guards intact;
  label retained older screenshots as older simulated UI, not current parity proof.
- **Preview what you ship.** Render every SVG at 900 px and 360 px wide before
  embedding it, with whatever renderer is installed (`rsvg-convert`, Inkscape or a
  headless browser), and check light and dark backgrounds. Embed with relative paths
  and meaningful `alt` text so the README still reads with images off.
  Also render the composed Markdown with an installed CommonMark renderer and headless
  browser: assert images load and the page has no horizontal overflow at both widths.
  Inspect the opening, section transitions and final links; use full-resolution crops
  when a full-page screenshot downscales text beyond readability. Call this a local
  approximation unless GitHub's actual renderer was exercised.
- **Use the local rendering stack efficiently.** Inventory Markdown CLIs as well as
  Python modules before adding dependencies; an installed `marked` can produce
  local preview HTML even when a Python Markdown package is absent. Preview with
  GitHub-like CSS, then inspect desktop and mobile page overflow, image loading
  and both folded and expanded details/code blocks. Keep wide commands and tables
  scrollable inside their blocks rather than widening the page. Label this a local
  approximation, not hosted GitHub verification. Save each browser capture to a
  distinct descriptive path before the next capture, because screenshot helpers may
  reuse one filename.
- **Delivery stays separate.** Assets go under `assets/readme/` unless the
  repository uses another location. Commit, push or open a pull request only through
  the repository's normal delivery workflow (for example
  [Git Commit Push](../git-commit-push/SKILL.md)) and its existing authority.

## Review-to-revision procedure

1. **Check the review against current source.** Read the actual README and its
   authoritative guides before applying review findings; line numbers and defects
   can describe an older revision. Fix remaining problems, retain useful visuals,
   and prefer reordering or replacing material over adding major sections.
2. **Make every advertised host actionable.** Near the first short example, provide
   a compact host/install/invocation comparison and copyable install commands.
   Label examples by interface, use one preferred spelling per interface and move
   aliases into a small reference. Distinguish portable workflows from host-only
   fleet, messaging and scheduler integration; installed adapters do not establish
   persistent background execution. Do not force readers through a separate long
   guide merely to discover the correct command prefix.
3. **Expose policy choices without changing defaults.** Put the opt-out command
   beside installation and state when it must run, such as before enabling the
   plugin. Keep it outside the default copy-paste block so following the normal
   install does not silently opt the reader out. State which side effects the
   opt-out does not cover.
4. **Validate examples against the authoring contract.** Include required fields
   such as goal/payoff, accepted source and ownership, or label the example shortened
   and link the complete format. Align scope, acceptance, check paths and reported
   changed files. Label task/report examples illustrative, never execution receipts.
   Explain reprioritization through the user-facing workflow, such as moving whole
   TODO blocks and running Docs Sync; keep internal helper paths, revision guards
   and migration commands in references rather than implying scripts are on PATH.
5. **Describe authority and activation precisely.** Explain whether an empty queue
   permits discovery, task recording and implementation in the same invocation
   under broad development authority; retain task-limited scope boundaries.
   Separate files updated from runtime activation and link status checks for
   pending/deferred restarts rather than implying a successful write loaded code.
6. **Match verification to the advertised hosts.** Separate current package checks,
   older isolated-install evidence and live model/messaging qualification. Run
   applicable package/command tests and native manifest validation in addition to
   documentation checks; do not perform fresh installations or live workflows just
   to beautify documentation. Preview the checked candidate before integration.
   Treat GitHub About metadata as a separate external edit requiring scoped
   authority, not an automatic consequence of README permission.

Run the README audit:

```sh
python3 "<beautify-github-readme-skill-dir>/scripts/audit_readme.py" /path/to/README.md
```

It applies the protocol's SVG checks and also follows GitHub's resolution: dark-mode
`<picture><source srcset>` variants, reference-style images, root-relative paths
from the repository root and `<…>` destinations; images in fenced code and confirmed
single-line backtick spans are skipped, including image examples embedded in text.
Multiline spans and ambiguous markup remain conservatively audited because this
lightweight checker does not implement a complete Markdown parser. Literal backticks
in HTML, autolinks and link/image destinations or titles do not open code spans.
Delimiter lookup is indexed; destination scanning tracks quotes, angle delimiters
and balanced parentheses, including continuation lines.
When changing the audit parser, retain visible-image negative checks across block
boundaries and unmatched delimiters; a literal-example fix must not hide real images.

Report the mode used, files changed, what was deliberately left plain, the checks
run and any claim you could not verify.
