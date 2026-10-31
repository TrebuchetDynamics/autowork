---
name: unused-code
description: "Remove proven dead or unreachable code."
license: MIT
---

# Unused Code

Apply the [shared Ponytail method](../shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.

Delete only code whose unreachability is evidenced inside a known ownership
boundary. Read the [host and authority adaptations](../shared/PI-TOOLSET.md), then
the pinned [unused-code protocol](upstream/PROTOCOL.md). This is not dependency
pruning, speculative simplification or a repository architecture rewrite.

## Prove liveness boundaries first

Inspect status, instructions, entrypoints, manifests, package exports and baseline
checks. Rank candidates with the Graphify workflow described by the Autowork
repository's `adapters/skills/graphify/SKILL.md` when a current local graph exists;
build a code-only graph only when graph generation is in scope. A graph or map is
orientation and must be verified against live source. Stale graphs, zero inbound
edges, `INFERRED` edges, low coverage and zero search matches never prove
unreachability. The pinned protocol's Understand Anything graph pass applies only
when a legacy `.understand-anything` graph is the sole index.

For every candidate check:
- callers, imports, re-exports, public package/CLI/API entrypoints;
- string/config/template references, runtime discovery, registries, reflection,
  dependency injection and serializers;
- generators, migrations, schemas, fixtures, tests, docs and examples;
- cross-package and external consumers, ownership and compatibility promises.

Unknown public or dynamic consumers mean **retain and explain**, not “unused.”
Prefer private leaves with corroborating compiler/linter and reference evidence.
Require at least one executable post-delete signal before accepting removal.
A retained uncertain candidate does not block an independent proven candidate
already inside the authorized scope.

Delete one coherent batch, remove only newly orphaned support, rerun candidate
checks and affected validation, and inspect stale references and the actual diff.
A regression stops further deletion. Repair or restore only this batch's
attributable delta after comparing against its saved baseline and current files;
never use blanket Git restore/clean or overwrite intervening edits.

**Receipt:** candidates and evidence; removed `path:symbol` with proof; retained
candidates with exact uncertainty; baseline/post-delete checks; review; net removal
when measured; stop reason and next action. No proven candidate means delete
nothing. Honor read-only, batch and delivery limits.

**Example:** keep an exported plugin hook with no static callers; remove an
independently proven private helper only if in scope and its checks pass.


## Boundaries

- Not a refactor; use `/skill-folder-refactor`.
- Not an architecture review; use `/improve-codebase-architecture`.

**Done when:** proven dead code is removed with post-delete checks, or every uncertain candidate is retained with its reason.
[Source and hashes](UPSTREAM.json) · [MIT license](upstream/LICENSE).