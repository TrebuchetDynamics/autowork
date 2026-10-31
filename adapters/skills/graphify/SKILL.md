---
name: graphify
description: "Query a local Graphify code graph before wide reading."
disable-model-invocation: true
---

# Graphify

Apply the [shared Ponytail method](../../../skills/shared/PONYTAIL.md) within this workflow's scope.

Use the [ASD-STE100 and project language rules](../../../skills/shared/COMMUNICATION.md) for user-facing text.

Read the [host contract](../COMMON.md), then use this host's native terminal and file
tools. Graphify maps a project into a local graph; you query that graph instead of
reading many files. This adapter is Autowork content that calls the official Graphify
CLI. It does not bundle, install or configure Graphify. Where the official `/graphify`
skill is installed (Hermes), that skill builds the graph; this workflow owns the
Autowork scope, evidence, limit and reporting rules that follow.

## Preconditions

- Require the `graphify` command. The PyPI distribution is `graphifyy` and needs
  Python 3.10+. Detect it with a shell lookup and record `graphify --version`.
- Do not install the tool, change host settings, add hooks or call a model from this
  workflow. When the command is absent, report the missing tool and continue with
  text search. A user can install it with `uv tool install graphifyy`.
- Never run `graphify hook install` or `graphify <agent> install` here; they write
  repository or agent configuration outside this workflow's authority.

## Build or reuse a graph

1. Inspect repository instructions, `git status --short --branch` and existing output.
2. Reuse `graphify-out/graph.json` only when `graph.schema_version`,
   `graph.graphify_version` and `built_at_commit` are readable and that commit matches
   the current `git rev-parse HEAD`. Treat a different commit, uncommitted candidate
   files or a missing version as stale orientation. Read the keys this file actually
   has; other releases can rename them.
3. Build code-only output. Parsing is local, deterministic and needs no key:

   ```sh
   graphify extract . --code-only --out <ignored-directory>
   ```

   Use one repository or folder, add `--exclude` for large unrelated trees, and keep
   the run bounded. Do not request a semantic pass or network call unless the user
   asks for it.
4. Verify the result before use: a nonempty `graph.json`, `nodes` and `links` counts
   read from that file, its schema and tool version, and `graphify --version`. Each
   link carries `relation` and `confidence`. Empty output is not a map.

## Query instead of wide reading

| Purpose | Command |
| --- | --- |
| One node with its neighbors | `graphify explain "<node>"` |
| Shortest connection between two nodes | `graphify path "<A>" "<B>"` |
| What depends on a node | `graphify affected "<node>" --depth 3 --relation calls` |
| Scoped answer to a question | `graphify query "<words>" --budget 2000` |
| Most connected nodes | `graphify god-nodes --top 10 --json` |

`query`, `path` and `explain` exit `0` with an answer, `3` when a name matches
several nodes and `4` when no node matches. On `3`, choose one printed candidate; do
not guess. `path` can also exit `0` and report that no directed path exists; add
`--undirected` only when direction is not part of the question. Pass
`--graph PATH` to read a graph outside the default location.

## Evidence rules

- `EXTRACTED` edges are explicit in the source. `INFERRED` edges are resolved by
  Graphify and are not runtime proof. Source line numbers can be stale.
- A graph is orientation, never proof of behavior, usage or deadness. Verify each lead
  in live source: callers, imports, re-exports, public entrypoints, runtime discovery,
  strings, configuration and tests.
- Absent inbound edges do not prove unreachable code. Deletions follow the
  [Unused Code workflow](../../../skills/unused-code/SKILL.md), including its
  ownership boundaries and post-delete checks.
- Do not commit `graphify-out/`, caches or absolute local paths. Never rewrite tracked
  files, ignore rules or settings to make a scan pass.
- A read-only request builds nothing and writes nothing. Graph counts, query output
  and a rendered `graph.html` are not test, security or runtime evidence.

## Report

State the scope, the command and tool version, the graph path and source revision,
node and link counts, the queries with their exit codes, verified findings, coverage
gaps such as unsupported languages or zero-symbol files, and any stale or mixed-state
input. Separate what the graph returned from what the source confirmed. Do not claim
dead code, runtime behavior or effort savings from the graph alone.
