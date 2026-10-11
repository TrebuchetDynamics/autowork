# Dependencies, reproducibility and licensing

The command bridge and the full setup are different layers. The bridge registers
bundled skills; individual workflows need execution tools and may use other skills.
The published manifest declares OMH, Ponytail and Hermes Speech as stack dependencies.
`--bundle-only` skips the external-source setup stage; it is not a separately
packaged minimal plugin and does not disable runtime policy writes.

Sources: [plugin manifest](../plugin.yaml), [installation inventory](../plugins/PLUGINS.md),
[defaults](../plugins/defaults.json), [installer](../install-plugins.sh).

## Current source policy

| Component | Selection | Reproducibility limit |
| --- | --- | --- |
| Bundled workflows | This repository revision | Pin the checkout revision to reproduce these files. |
| Autoresearch 2.2.2 | Vendored revision and file hashes in [UPSTREAM.json](../skills/autoresearch/UPSTREAM.json) | Reviewed updates require refreshing the pinned subtree and tests. |
| Grill Me 2.0.0 | Bundled [SKILL.md](../skills/grill-me/SKILL.md) | Its checked-in bytes are fixed by this repository revision. |
| OMH setup CLI | Git revision pinned in defaults.json | The Hermes plugin source is separately resolved through the source inventory/catalog. |
| OMH plugin, Ponytail, Hermes Speech | Native Hermes installs from declared sources | No unified bundle lockfile pins their installed revisions. |
| Addy agent-skills | Shallow clone and native skill imports | Current upstream content may change between installations. |
| Graphify | Dedicated setup helper | Not covered by a unified bundle lockfile. |

A repeat install skips existing resources rather than force-updating them. Two
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

- Vendored Autoresearch retains its [MIT license and attribution](../skills/autoresearch/upstream/LICENSE).
- Grill Me declares MIT in its [skill metadata](../skills/grill-me/SKILL.md).
- Other bundled files may carry individual notices. Retain those notices.
- External integrations remain subject to their upstream licenses. A complete
  version-bound third-party license inventory has not been established here.
