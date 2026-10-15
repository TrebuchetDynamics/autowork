# Browser validation for product UI refinements

## 1. Establish behavioral and visual baselines

Read the target page, shared layout, design tokens and existing browser tests before editing. Extract the protected behavior: selectable filter/sort domains, URL state, pagination, detail links, source/freshness labels, role gates, destructive confirmations and recovery states. Record row-height and overflow bounds from the tests as constraints on the composition.

Run existing targeted tests on unchanged source and capture narrow, intermediate and desktop widths. Include map/sidebar panel modes. Intermediate widths expose tables that fit a large desktop but exceed a small laptop's panel.

Choose the smallest coherent refinement from observed defects. For dense registries, try spacing, compound-value alignment, header wrapping and a clear navigation/destructive-action hierarchy before converting fields into taller stacked groups. Inspect computed `display`, `text-align` and margins when compound cells collide: a stronger generic selector can defeat a later field-specific rule. Repair that conflict rather than layering blanket overrides. Preserve the established collapsed/expanded domain rather than exposing every hidden field by default.

## 2. Isolate the complete fixture lifecycle

Use an authorized isolated candidate and a local seeded fixture, not production data. Inspect the fixture script's supported configuration. Namespace every owned resource: application port, database port, container, volume, lock, results, authentication-state files and temporary logs. Distinct ports do not isolate a script that writes fixed log names under a shared temporary directory.

Create a task-private temporary directory beneath approved scratch and pass it explicitly to the fixture process. Use absolute evidence paths in shell redirections: an inline `env TMPDIR=... command > "$TMPDIR/log"` assignment does not change the shell's earlier expansion of that redirection. Isolate writable build caches rather than directing writes through shared dependency symlinks.

Reuse the existing fixture harness, seed and cleanup behavior. For a harness exposing `FIXTURE_APP_PORT`, `FIXTURE_DB_PORT`, `FIXTURE_DB_CONTAINER`, `FIXTURE_DB_VOLUME`, `FIXTURE_LOCK` and `FIXTURE_E2E_RESULTS`, set the complete supported namespace, not just the application port. Fixture lifecycle mutations do not authorize real fleet/device operations.

## 3. Add discriminating coverage

Exercise panel fit, keyboard focus, long identities, empty/filter recovery, primary navigation and destructive-action separation. Preserve existing unique coverage and meaningful assertions. Verify new regressions fail against the missing protection; when one assertion prevents a later assertion from being reached, use a focused negative control to prove the later protection independently.

Label illustrative data and do not infer fresh reports, measured GPS or operational health from approval status. Scope page-local summaries explicitly so a bounded result page does not look like a fleet total.

## 4. Diagnose failures without relabeling them

Retain failed runs and their input identities. When a UI change coincides with an existing test failure, run the same test against pristine source using equivalent tools, dependencies and fixtures. A pristine pass leaves a candidate concern or unresolved interaction; it does not establish that the test is flaky. A pristine failure supports investigating a shared baseline problem, not weakening the test.

Do not guess that a lost click is a hydration race. Inspect the failure stage and use the project's existing hydration helper only when the diagnosis supports it. Preserve confirmation, audit, access-control and persistence assertions in justified test-only repairs. Do not mask failures with retries, skips, exclusions or larger acceptance bounds.

When the required gate already enables retries, keep that policy unchanged and parse its original inventory and every result batch by unique test/project identity. Verify selected and recorded identities match exactly, then report first-attempt passes, flaky cases, skips and unexpected failures separately. Name retry-dependent confirmation or lifecycle cases in the retained evidence. A successful configured gate is not a retry-clean result, and a separate clean focused run does not supersede its failed attempts. Do not rerun unchanged inputs merely to obtain a cleaner-looking receipt.

## 5. Close the visual and source loop

Batch related corrections, rerun affected tests and recapture relevant sizes/states. Compare hierarchy, density, readability, wrapping, touch targets and action priority—not merely absence of horizontal document overflow. Inspect the ledger's own scroll container as well as the outer page.

Wait for navigation's loading/dimming treatment to settle before capturing an empty or recovery state. Inspect map/sidebar controls separately from basemap loading: a mounted map and visible marker do not prove external tiles finished rendering. If assets remain unavailable, label that limitation rather than calling the capture a complete map-render pass.

Freeze final product/test inputs before final gates. Record source hashes with commands, tool/dependency identity, results and captures. Subsequent source corrections require refreshed affected checks and source-bound review. Retain intermediate compositions and reviews as history, not final approval.

Run required full gates without overlapping another run where serialization is required. Report targeted passes, full-gate status, source integration and deployment separately; a rendered isolated candidate establishes none of the latter by itself.

Retain the final source-bound evidence outside expiring scratch before handing off an isolated delivery. Use `git worktree move <tested-path> <retained-path>` for a linked worktree, record the old-to-new path mapping, and compare committed tree and owned-file hashes before and after relocation. Rerun the project's sync/typecheck command when generated configuration may contain absolute paths; relocation must not silently leave a broken preview workspace. Keep a primary completion receipt pointing to historical attempts rather than leaving a progress receipt as the apparent current state.

Exclude saved authentication state and credential-bearing browser traces from retained evidence unless safely sanitized. Tear down only the task-owned fixture: verify its exact container labels, loopback port and volume before removal, then read back those exact targets to confirm absence. Never clean up a similarly named shared fixture or another worker's resources.
