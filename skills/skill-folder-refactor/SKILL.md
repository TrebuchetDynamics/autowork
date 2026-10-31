---
name: skill-folder-refactor
description: "Split one folder without behavior change."
license: MIT
---

# Skill Folder Refactor

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Refactor one named directory into responsibility-based subfolders without changing
behavior. Read the [host and authority adaptations](../shared/PI-TOOLSET.md), then
the pinned [folder-refactor protocol](upstream/PROTOCOL.md). If no folder is named,
ask for the boundary or perform read-only discovery when requested. Treat a
repository-root split as high risk; obtain explicit scope before editing.

## Preserve behavior, then simplify

Map exact files, public entrypoints, package boundaries, imports/exports, external
callers and behavior checks. Propose the smallest coherent topology under existing
authorization. Keep out-of-folder caller edits limited to required import fixes
and within the accepted scope; escalate public API or behavior changes.

1. **Move-only:** move files and fix paths/imports; do not simultaneously rename
   symbols, rewrite logic, extract helpers or delete compatibility facades.
2. **Validate:** run behavior checks and relevant build/import checks. Missing
   behavior coverage needs a focused public-seam check before deeper extraction.
   If no correct seam is available, stop deeper cleanup and report the gap.
3. **Extract only proven duplication:** at least two callers need identical
   semantics, a clear responsibility and adequate checks. Similar-looking code
   is not evidence for a shared abstraction.
4. **Cleanup:** remove shims or dead code only after caller and compatibility
   evidence supports it, then validate again.

The upstream minimum-three-slices and mandatory-continuation language does not
override the user's one-slice limit, budget or pause. Stop at that checkpoint and
distinguish a verified slice from incomplete target topology. No special
`folder_refactor_*` tool is required: inspect the actual tree with native tools;
record state in the existing task receipt rather than a new extension database.

**Completion audit:** reread the tree from disk. Classify every remaining root file
by exact basename as public facade/compatibility, intentionally out-of-scope, or
next move/extraction candidate. Unclassified files or remaining candidates mean
the whole target is not complete. Do not hide them in broad categories.

**Receipt:** target, planned → actual topology, moves, shared-code decision,
compatibility, checks/review, exact root-file classifications, overall completion
state, and next slice/stop reason. For example, one authorized move-only slice
with two remaining candidates is a checkpoint, not “folder refactor complete.”


## Boundaries

- Not behavior changes or deletions; use `/unused-code` for removal.
- Not an architecture review; use `/improve-codebase-architecture`.

**Done when:** a move-only diff passes the same checks before and after, and no behavior change is claimed without them.
[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).