# Dependencies, reproducibility and licensing

The command bridge and the full setup are different layers. The bridge registers
bundled skills; individual workflows need execution tools and may use other skills.
The Hermes manifest declares OMH and Hermes Speech as stack dependencies.
[Portable packages](cross-host.md) do not install those integrations. Ponytail is
now pinned and bundled for every host, not an external plugin prerequisite.
`--bundle-only` skips the external-source setup stage; it is not a separately
packaged minimal plugin and does not disable runtime policy writes.

Sources: [plugin manifest](../plugin.yaml), [installation inventory](../plugins/PLUGINS.md),
[defaults](../plugins/defaults.json), [installer](../install-plugins.sh).

## Current source policy

| Component | Selection | Reproducibility limit |
| --- | --- | --- |
| Bundled workflows | This repository revision | Pin the checkout revision to reproduce these files. |
| Ponytail 5.3.2 | Six protocols, benchmark attribution and optional map script at [pinned revision and hashes](../skills/ponytail/UPSTREAM.json) | Offline on all hosts; local adapters scope upstream behavior. No upstream hooks, installers, persistent modes or telemetry are activated. |
| Autoresearch 2.2.2 | Vendored revision and file hashes in [UPSTREAM.json](../skills/autoresearch/UPSTREAM.json) | Reviewed updates require refreshing the pinned subtree and tests. |
| UI Taste 0.2.0 (Uizze) | Vendored from a pinned Uizze commit, [pin and hashes](../skills/ui-taste/UPSTREAM.json) | Plain Markdown playbooks copied unchanged under `upstream/`; the toolset adapter sets host rules; works offline. Its optional paid Uizze MCP is never configured by Toolset. |
| Impeccable 4.5.2 | Vendored official Hermes package, [pin and hashes](../skills/impeccable/UPSTREAM.json) | All references and scripts ship with the plugin; Apache-2.0 license and notices retained. |
| Beautify GitHub README | Vendored revision and file hashes in [UPSTREAM.json](../skills/beautify-github-readme/UPSTREAM.json) | Upstream skill byte-exact under `upstream/`; the toolset adapter sets host rules and adds a README audit that reuses the upstream SVG checks; MIT license retained. |
| Grill Me 2.1.0 | Bundled [SKILL.md](../skills/grill-me/SKILL.md) | Its checked-in bytes are fixed by this repository revision. |
| OMH setup CLI | Git revision pinned in defaults.json | The Hermes plugin source is separately resolved through the source inventory/catalog. |
| OMH plugin, Hermes Speech | Native Hermes installs from declared sources | No unified bundle lockfile pins their installed revisions. |
| Toolset engineering protocols (`skills/engineering/local/`) | Written and versioned in this repository; no upstream pin | `test-suite-optimization` adapts two criteria from Matt Pocock's MIT `tdd` skill in its own words; no text is copied. |
| Addy agent-skills (25 protocols) | Vendored commit and hashes in [UPSTREAM.json](../skills/engineering/UPSTREAM.json) | Updated only through a reviewed Toolset change; shared references included. Two defensive examples are paraphrased, with original and adapted hashes recorded; a refresh restores upstream bytes, so re-apply them by hand. |
| Graphify | Dedicated setup helper | Not covered by a unified bundle lockfile. |
| textual-serve 1.1.3 (MIT), `autowork web` only | Pinned in [`command.py`](../pi-autowork/pi_autowork/command.py) (`AUTOWORK_TEXTUAL_SERVE`), fetched by `uv run --with` like Textual | Not a runner dependency; only the browser view uses it. |
| Textual 8.2.8 (MIT), the `autowork` TUI only | Pinned in [`command.py`](../pi-autowork/pi_autowork/command.py) (`AUTOWORK_TEXTUAL`); fetched by `uv run --with` into uv's cache on first use | Not a runner dependency: pi-autowork itself stays standard-library Python, and every other `autowork` command works without it. |

Ordinary installation preserves existing resources, adding only missing Markdown
files in the bundled `shared/` support directory (without overwriting local edits).
`/autowork update` synchronizes
bundled content, including the pinned engineering pack, to the release bytes.
Edited native copies are reset or removed when their release file is removed;
their original bytes remain in the update backup and the action is reported.
External imports are not upgraded by that command. A checkout revision alone does
not prove that native profile copies match it. Exact historical copies can avoid a
repeated drift notice, but they are still synchronized. The separate guarded
managed-checkout recovery path uses three-way reconciliation and refuses unresolved
conflicts rather than discarding local changes. Historical byte equality does not
prove an older copy was unintentional or compatible with an active worker. Review
intentional pins and quiesce/reconcile active runs before updating; see the
[update boundary and recovery](installation.md#update-all-profiles). Two
machines with the same Toolset checkout can therefore have different external
versions. Native scans remain enabled; blocked imports mean incomplete setup.
`--yes-deps` permits declared dependency installation, not a scanner bypass.

## Updating

Review changes to the source inventory, defaults, manifest and vendored hashes.
Record the actual external versions/revisions installed in each target profile,
preview setup, and validate in a separate isolated Hermes root without live sibling
profiles before applying to the fleet. A named test profile is insufficient: setup
resolves its home to the containing fleet root.
Review scan failures rather than silently substituting another source or disabling
scanning. Updating this repository alone does not update every existing import.

A unified dependency lockfile, license inventory and automated update procedure
remain unimplemented. This page makes the limitation explicit; it is not a lockfile.

## Licensing

Autowork is licensed under the [MIT License](../LICENSE), copyright
2026 TrebuchetDynamics. Third-party components retain their respective licenses
and copyright notices.

- Vendored Ponytail retains its [MIT license and attribution](../skills/ponytail/upstream/LICENSE); pinned protocol bytes are unchanged behind local adapters, and its optional map helper is renamed `.cjs` for Autowork's ESM package with a documented bounded-read safety fix.
- Vendored Impeccable retains its [Apache-2.0 license](../skills/impeccable/LICENSE) and [notices](../skills/impeccable/NOTICE.md). Its official Hermes files are copied unchanged, with upstream SKILL.md stored as PROTOCOL.md behind the local Ponytail-aware adapter, and supplemental [modern-screenshot](../skills/impeccable/licenses/modern-screenshot-MIT.txt) and [platform-design-skills](../skills/impeccable/licenses/platform-design-skills-MIT.txt) MIT notices.
- Vendored UI Taste retains its [Apache-2.0 license](../skills/ui-taste/upstream/LICENSE), [notice](../skills/ui-taste/upstream/NOTICE) (Impeccable 4.4.0 by Paul Bakaus and ehmo's MIT platform-design-skills) and Uizze's [modifications notice](../skills/ui-taste/upstream/MODIFICATIONS.md). Its SKILL.md is stored as PROTOCOL.md so only the toolset adapter registers; it is otherwise an unmodified copy, not an endorsement by Uizze or the Impeccable author.
- Vendored Addy agent-skills retains its [MIT license and attribution](../skills/engineering/upstream/LICENSE). Two defensive examples have documented paraphrases with original/adapted hashes; other pinned protocol bytes are preserved. SKILL.md filenames become PROTOCOL.md to avoid duplicate host discovery.
- Vendored Autoresearch retains its [MIT license and attribution](../skills/autoresearch/upstream/LICENSE).
- Vendored Beautify GitHub README (oil-oil) retains its [MIT license](../skills/beautify-github-readme/upstream/LICENSE); its SKILL.md becomes PROTOCOL.md to avoid duplicate host discovery, other bytes unchanged.
- Grill Me declares MIT in its [skill metadata](../skills/grill-me/SKILL.md).
- Other bundled files may carry individual notices. Retain those notices.
- External integrations remain subject to their upstream licenses. A complete
  version-bound third-party license inventory has not been established here.

## Bundled Ponytail

[UPSTREAM.json](../skills/ponytail/UPSTREAM.json) pins commit
`09c434ab73ca43761c5d8b0c5d341926c2fba710` (declared version 5.3.2), the MIT license
and SHA-256 of every imported file. Six upstream SKILL.md files are stored as
PROTOCOL.md to avoid recursive skill discovery. Local native and portable entry
skills apply [Autowork's scope rules](../skills/shared/PONYTAIL.md); the upstream
help card is provenance only because it advertises unsupported global/plugin UI.

The only executable imported is `hooks/ponytail-map.js`, stored as
`upstream/scripts/ponytail-map.cjs` with one local fix: actual source reads are capped
at 64 KiB rather than reading the entire file and slicing afterwards. The manifest
retains both upstream and adapted hashes. It is invoked manually, never registered
as a hook. It uses Node built-ins and Git to print a bounded regex-based reuse index;
without tracked files (or if Git fails), it falls back to a directory walk that does
not fully honor ignore rules. Use normal search for correctness and sensitive trees.
The six skills need no Node dependency themselves. Debt uses native search/Git;
gain labels its bundled benchmark report as upstream-reported, not Autowork savings.
Upstream installers, publishers, uninstallers, lifecycle hooks, UI/band code and
benchmark execution are excluded.

To refresh, inspect an exact upstream commit in a scratch clone. For each original
path in the manifest's `files` mapping, copy `git show FULL_SHA:ORIGINAL_PATH` bytes
to the mapped local path, recompute its SHA-256, and update revision/version after
reviewing the diff. Keep the allowlist: do not copy root manifests or activate the
upstream plugin. Reapply or re-evaluate the bounded-read fix and retain the original
upstream hash as well as the adapted hash; a blind refresh must not restore the
unbounded read. Review new script dependencies and adapters together. Impeccable's
upstream SKILL.md similarly stays byte-exact under PROTOCOL.md; refreshing must not
overwrite its local entry adapter. Run:

```sh
python3 scripts/affected_tests.py --run
node --test tests/portable_pi.test.mjs
```

The tests check hashes, all entry links, isolated native provisioning, literal Pi
command dispatch and an unpacked npm archive including execution of the `.cjs` map.
They do not prove live model adherence or installation into real host profiles.
Normal installation/update uses these committed resources without fetching Ponytail.
Existing separately installed Ponytail plugins are left unchanged; their commands
may retain ownership, so resolve the bundled skill explicitly when needed.

## Refresh the pinned engineering pack

Review the upstream diff and choose an exact commit. From a local upstream checkout:

```sh
python3 scripts/vendor-agent-skills.py --source /path/to/agent-skills --revision FULL_REVIEWED_COMMIT_SHA
python3 -m unittest discover -s tests -p test_engineering_vendor.py
```

The pack includes all 25 skills, their local support files, root references, docs,
commands and analytical personas, plus licensing/source documentation. Host hooks,
harness manifests, evals and root upstream scripts are excluded and never activated.
The refresh tool copies Git objects from that revision, not dirty working files, and
writes upstream bytes unchanged: it reverts the two paraphrased defensive examples
(`browser-testing-with-devtools`, `source-driven-development`) and drops their
`upstream_sha256` records. Re-apply both paraphrases and their hashes, then review
the diff before committing; `test_engineering_vendor.py` does not catch their loss. Review newly introduced links and dependencies,
run the full offline checks, then ship with the bundle. The former native-card
registration-admission suite was retired with its unreachable engine. Native plugin
registration remains a separate optional `tests/integration_plugin.py` check; see
[its environment and limits](testing.md#verify).
`/autowork update` consumes that reviewed snapshot; it never fetches Addy latest.
Existing profile-level Addy imports remain untouched as optional alternatives.

## Refresh the vendored UI Taste skill

UI Taste is distributed from `https://uizze.sh` (`npx skills add https://uizze.sh
--skill ui-taste`) and is not on Uizze's `main` branch; the vendored copy comes from
the GitHub mirror commit recorded in [UPSTREAM.json](../skills/ui-taste/UPSTREAM.json).
To move to a newer reviewed commit, clone `https://github.com/uizze/uizze` in a
scratch directory and, for each path from
`git ls-tree -r --name-only REVISION skills/ui-taste`, write
`git show REVISION:PATH` byte-for-byte under `skills/ui-taste/upstream/`, storing
`SKILL.md` as `PROTOCOL.md`. Compare it with the current `uizze.sh` copy, review the
diff and the toolset adapter's rules against it, then update the revision,
`domain_check` and every hash under `files` in UPSTREAM.json and run
`python3 -m unittest discover -s tests -p test_ui_taste_bundle.py` and the full
offline checks. Never fetch it during install, setup or update.
