---
name: ui-taste
description: "Use to build, polish or review web and iOS UI screens."
version: 0.2.2
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
Adapter-local references linked below resolve relative to this SKILL.md.

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
- **Preserve the selectable domain during layout work.** Inspect the existing
  control list and its filtering/state-restoration code before rebuilding it.
  Do not replace an explicit list with an enum's `.values` without checking every
  member: persisted compatibility values can remain valid for decoding while being
  intentionally absent from the UI. Keep the supported subset explicit and test
  both visible choices and excluded legacy choices; otherwise a presentation-only
  refactor silently changes product behavior and can push intended controls offscreen.
- **Act on established screenshot feedback.** Reuse the user's supplied screens
  and latest explicit improvement request when they repeat the command; do not
  restart discovery or stop at another critique. Treat visible defects as
  acceptance cases and implement the smallest complete correction.
- **Compact means clearer, not smaller targets.** Prefer one heading, one obvious
  primary action, consistent gutters and fields grouped by purpose. Remove repeated
  branding and explanatory walls before shrinking type. Put optional key metadata
  and setup manuals behind clearly labeled disclosures; keep required credentials,
  failures, recovery actions and security consent reachable. Keep installation
  warnings before installation links/actions inside the same disclosure. Preserve
  readable large text, touch targets and keyboard/Back operation.
- **Read layout regressions before choosing the refinement.** Inspect existing
  responsive, density, accessibility and action tests alongside the screen. Treat
  meaningful bounds as design inputs: stacking every label above its value can
  make a dense registry unusable even when one card looks cleaner. Fix alignment,
  wrapping and action priority before spending more vertical space; do not relax
  established bounds to accommodate a preferred composition.
- **Size layout transitions to the available panel.** Compare the ledger's actual
  minimum width with its containing panel, including map/sidebar modes. Choose
  the table/card transition from that fit rather than a generic viewport breakpoint;
  otherwise a laptop or sidebar can inherit a clipped desktop table.
- **Verify what you ship.** Render the result with whatever browser or renderer is
  available at representative desktop and mobile sizes. When nothing can render it,
  say the checks were code-only rather than claiming a visual pass.
  For phone forms, include keyboard and system-navigation insets. Check the scroll
  viewport's bounds, not only a button's position: short content can leave the
  button above system chrome even when the viewport still extends underneath it.
  Use a negative control to prove the regression detects the removed protection.
  Run existing behavioral tests as well as new visual/layout assertions. When a
  failure appears, compare the same test against pristine source under equivalent
  fixture conditions before classifying it as pre-existing or changing the harness.
  A baseline pass does not establish the candidate's failure mechanism. Capture
  settled states, not navigation dimming or loading overlays; distinguish verified
  layout from external assets that have not finished loading. After any
  correction, bind fresh checks, captures and review to the revised source hashes;
  an earlier screenshot or approval does not qualify the new bytes.
- **Report gate outcomes, not just exit codes.** Separate focused no-retry
  passes from broader retry-enabled gates. Disclose flaky safety-action tests and
  skipped coverage even when the command exits successfully; a clean focused run
  does not erase broader failures or establish reproducibility.
- **Delivery stays separate.** Documentation changes follow
  [Docs Sync](../docs-sync/SKILL.md). Commit, push or publish only through the
  repository's normal delivery workflow (for example
  [Git Commit Push](../git-commit-push/SKILL.md)) and its existing authority.

## App-derived branding and visual iteration

1. **Honor the image's origin.** When the owner requires artwork from the app,
   capture the production renderer and retain its untouched image and reproducible
   app state. Do not substitute an illustration, traced mark, external formula
   renderer, thumbnail enlargement or cropped UI screenshot as the master.
2. **Choose the composition before packaging.** Show two or three clearly labeled
   app-rendered drafts before regenerating platform resources or building a preview
   package. If the owner rejects the appearance, change the relevant parameters,
   framing or orientation—not just the palette—and show the revised images.
3. **Treat a selection as a source switch.** Once the owner selects another draft,
   regenerate every derivative, proof, saved preset and preview package from that
   draft. Check delivery pixels against the selected comparison image; otherwise a
   new filename can conceal an old composition. Retire the rejected draft from the
   active handoff without deleting its provenance.
4. **Make transformations honest.** Verify that app rotation actually changes the
   rendered pixels. If rotation is applied after capture, say so and record its
   resampling/crop; never present a stored rotation field as an executed transform.
5. **Separate approvals.** Record composition selection without asking the owner
   to choose it again. Keep any already-required installed-device check, asset
   replacement authority and publication gate distinct; neither green tests nor a
   built preview supplies those missing observations or permissions.

For capture sizing, rotation/crop recipes, native-size proofs and package readback,
use [app-derived artwork](references/app-derived-artwork.md).

For Flutter widget captures, disclosure regressions and Android test-APK handoffs,
read [Flutter/Android validation](references/flutter-validation.md), a reference
owned by this adapter rather than the pinned upstream playbooks.

For dense web registries, isolated browser fixtures and baseline/candidate failure
comparison, read [browser validation](references/browser-validation.md).

Report the playbooks used, files changed, what was actually rendered and checked,
and any limitation that affected the result.
