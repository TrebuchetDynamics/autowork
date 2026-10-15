# Dependencies, reproducibility and licensing

The command bridge and the full setup are different layers. The bridge registers
bundled skills; individual workflows need execution tools and may use other skills.
The Hermes manifest declares OMH, Ponytail and Hermes Speech as stack dependencies.
[Codex/Pi packages](cross-host.md) use portable adapters and do not install these integrations.
`--bundle-only` skips the external-source setup stage; it is not a separately
packaged minimal plugin and does not disable runtime policy writes.

Sources: [plugin manifest](../plugin.yaml), [installation inventory](../plugins/PLUGINS.md),
[defaults](../plugins/defaults.json), [installer](../install-plugins.sh).

## Current source policy

| Component | Selection | Reproducibility limit |
| --- | --- | --- |
| Bundled workflows | This repository revision | Pin the checkout revision to reproduce these files. |
| Autoresearch 2.2.2 | Vendored revision and file hashes in [UPSTREAM.json](../skills/autoresearch/UPSTREAM.json) | Reviewed updates require refreshing the pinned subtree and tests. |
| UI Taste 0.2.0 (Uizze) | Vendored from a pinned Uizze commit, [pin and hashes](../skills/ui-taste/UPSTREAM.json) | Plain Markdown playbooks copied unchanged; works offline. Its optional paid Uizze MCP is never configured by Toolset. |
| Impeccable 4.5.2 | Vendored official Hermes package, [pin and hashes](../skills/impeccable/UPSTREAM.json) | All references and scripts ship with the plugin; Apache-2.0 license and notices retained. |
| Beautify GitHub README | Vendored revision and file hashes in [UPSTREAM.json](../skills/beautify-github-readme/UPSTREAM.json) | Upstream skill byte-exact under `upstream/`; the toolset adapter sets host rules; MIT license retained. |
| Grill Me 2.1.0 | Bundled [SKILL.md](../skills/grill-me/SKILL.md) | Its checked-in bytes are fixed by this repository revision. |
| OMH setup CLI | Git revision pinned in defaults.json | The Hermes plugin source is separately resolved through the source inventory/catalog. |
| OMH plugin, Ponytail, Hermes Speech | Native Hermes installs from declared sources | No unified bundle lockfile pins their installed revisions. |
| Addy agent-skills (25 protocols) | Vendored commit and hashes in [UPSTREAM.json](../skills/engineering/UPSTREAM.json) | Updated only through a reviewed Toolset change; shared references included. Two defensive examples are paraphrased, with original and adapted hashes recorded; a refresh restores upstream bytes, so re-apply them by hand. |
| Graphify | Dedicated setup helper | Not covered by a unified bundle lockfile. |

Ordinary installation skips existing resources. `/toolset update` updates bundled
content, including the pinned engineering pack, while preserving conflicts. External
imports are not upgraded by that command. A checkout revision alone does not prove
that native profile copies match it. The updater recognizes exact same-path
historical copies in bounded trusted Git history; unknown drift is preserved and
reported as incomplete for reconciliation. Historical byte equality does not
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

Hermes Toolset is licensed under the [MIT License](../LICENSE), copyright
2026 TrebuchetDynamics. Third-party components retain their respective licenses
and copyright notices.

- Vendored Impeccable retains its [Apache-2.0 license](../skills/impeccable/LICENSE) and [notices](../skills/impeccable/NOTICE.md). Its official Hermes package is copied unchanged, with supplemental [modern-screenshot](../skills/impeccable/licenses/modern-screenshot-MIT.txt) and [platform-design-skills](../skills/impeccable/licenses/platform-design-skills-MIT.txt) MIT notices.
- Vendored UI Taste retains its [Apache-2.0 license](../skills/ui-taste/LICENSE), [notice](../skills/ui-taste/NOTICE) (Impeccable 4.4.0 by Paul Bakaus and ehmo's MIT platform-design-skills) and Uizze's [modifications notice](../skills/ui-taste/MODIFICATIONS.md). It is an unmodified copy, not an endorsement by Uizze or the Impeccable author.
- Vendored Addy agent-skills retains its [MIT license and attribution](../skills/engineering/upstream/LICENSE). Two defensive examples have documented paraphrases with original/adapted hashes; other pinned protocol bytes are preserved. SKILL.md filenames become PROTOCOL.md to avoid duplicate host discovery.
- Vendored Autoresearch retains its [MIT license and attribution](../skills/autoresearch/upstream/LICENSE).
- Vendored Beautify GitHub README (oil-oil) retains its [MIT license](../skills/beautify-github-readme/upstream/LICENSE); its SKILL.md becomes PROTOCOL.md to avoid duplicate host discovery, other bytes unchanged.
- Grill Me declares MIT in its [skill metadata](../skills/grill-me/SKILL.md).
- Other bundled files may carry individual notices. Retain those notices.
- External integrations remain subject to their upstream licenses. A complete
  version-bound third-party license inventory has not been established here.

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
run the full offline checks and the native registration test
(`skills/autowork/scripts/test_registration_admission.py` with
`HERMES_NATIVE_REGISTRATION_TEST=1`), then ship with the bundle.
`/toolset update` consumes that reviewed snapshot; it never fetches Addy latest.
Existing profile-level Addy imports remain untouched as optional alternatives.

## Refresh the vendored UI Taste skill

UI Taste is distributed from `https://uizze.sh` (`npx skills add https://uizze.sh
--skill ui-taste`) and is not on Uizze's `main` branch; the vendored copy comes from
the GitHub mirror commit recorded in [UPSTREAM.json](../skills/ui-taste/UPSTREAM.json).
To move to a newer reviewed commit, clone `https://github.com/uizze/uizze` in a
scratch directory and, for each path from
`git ls-tree -r --name-only REVISION skills/ui-taste`, write
`git show REVISION:PATH` byte-for-byte under `skills/ui-taste/`. Compare it with the
current `uizze.sh` copy, review the diff, then update the revision, `domain_check` and
every `sha256` in UPSTREAM.json and run
`python3 -m unittest discover -s tests -p test_ui_taste_bundle.py` and the full
offline checks. Never fetch it during install, setup or update.
