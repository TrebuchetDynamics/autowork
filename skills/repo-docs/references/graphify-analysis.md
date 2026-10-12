# Graphify-backed documentation and task planning

Use for relationship analysis when a graph adds needed evidence, or when
explicitly required. Routine wording, link and metadata repairs do not need it.
Load the installed `graphify` skill and only its needed references;
follow its supported pipeline rather than inventing a slash-command shell CLI.
Graphify supplies a map, not accepted intent, approval, executed tests or delivery.

## 1. Bind the graph to the inspected repository

Resolve the actual repository, worktree, HEAD, scope and dirty/untracked inputs.
Check `graphify-out/graph.json`, `GRAPH_REPORT.md` and available manifests in that
repository, not another terminal cwd. Read the graph's source paths and coverage.
An existing graph is reusable only for inputs it still represents: compare changed
files, excluded/generated files and semantic-update notices with actual contents.
HEAD alone is not freshness for dirty files. Inspect source even when graph is fresh.

Bootstrap/Maintain may generate derived graph artifacts within the authorized
workspace. Keep outputs separate from canonical docs/ledger and never overwrite a
larger existing graph with a scoped scan. Do not auto-stage outputs, install hooks,
modify ignore policy or enable watchers/global stores. Audit creates no graph,
cache, memory or other files and never installs dependencies; query an existing
graph read-only, or report the coverage gap and inspect source directly.

Check `graphify --help` through `terminal` for the installed CLI. No API key is required
for structural code extraction. Where supported, a bounded local baseline is:

```sh
graphify extract /absolute/repo --code-only --out /absolute/authorized-output
```

If extraction writes graph.json but no GRAPH_REPORT.md, use the supported
`graphify cluster-only /absolute/authorized-output --no-label --no-viz` through
`terminal` to generate the report locally without external community labeling.
Placeholder community labels are not semantic documentation analysis.

This is explicitly a code-only baseline, not analysis of requirements/docs. For
full analysis use the loaded skill's AST plus host-agent semantic extraction of
relevant README, accepted requirements/specs, tests, runbooks and existing TODO.
No external provider, credentials or upload is authorized just by this workflow.
Use existing supported dependencies; if installation needs authority, do not silently
install. Large-corpus scope warnings and extraction/health guards still apply.
Incremental AST refresh does not imply semantic docs were refreshed. Check notices
and complete the semantic update before treating those files as current.

Record `graphify_unavailable` for missing tooling/skill or failed extraction;
`graphify_partial` for missing/stale/excluded inputs or integrity warnings. Include
exact failure, attempted bounded recovery and affected conclusions; continue
independent source-backed work but do not report Graphify analysis complete.
An empty corpus may be not_applicable only with an explicit boundary reason.

## 2. Ask questions that change the documentation

With the target graph path explicit, run applicable commands through `terminal`:

```sh
graphify query "entry points setup configuration runtime data flow tests" --graph /absolute/output/graphify-out/graph.json --budget 2000
graphify query "accepted requirements implementation tests operations gaps" --graph /absolute/output/graphify-out/graph.json --budget 2000
graphify path "<actual entry node>" "<actual persistence or external boundary node>" --graph /absolute/output/graphify-out/graph.json
graphify explain "<actual architectural hub>" --graph /absolute/output/graphify-out/graph.json
```

Expand vocabulary using actual graph labels; never invent endpoint nodes just to
run `path`. Query relevant communities, hubs and cross-component connections.
Trace critical startup/configuration, public interfaces, data/lifecycle flow,
failure/security boundaries and corresponding tests. Use focused DFS/path followups
where broad retrieval misses a dependency. A query that returns no relevant nodes
is not proof of missing behavior: verify source/tests and graph coverage.

For each material finding bind node/edge IDs or labels, `source_file` and
`source_location` (when present), actual source symbol/section and freshness/scope.
Retain EXTRACTED, INFERRED and AMBIGUOUS confidence. Cross-check EXTRACTED facts
against source; INFERRED/AMBIGUOUS relationships are hypotheses until corroborated.
Graph hub size alone is not defect severity, ownership or task priority.

Use findings to correct existing owners, not generate a competing graph wiki:
- README: actual entry points, setup/test paths and navigation.
- Spec/ADR: component boundaries, verified dependencies and decision consequences;
  graph topology does not turn a design proposal into an accepted decision.
- Test-plan: requirement-to-behavior-to-test links and demonstrated coverage gaps.
- Runbook: real failure paths, recovery prerequisites and observable signals.
- PRD: preserve accepted intent; name implementation drift instead of rewriting goals.

## 3. Turn verified gaps into better TODO.md slices

Before creating a task, join accepted intent to a demonstrated gap in source/tests
and check existing goals/tasks/owners for the same outcome. Graph findings without
accepted intent remain proposals or owner questions, not executable work. Reuse
IDs and preserve completed work, leases, focus and canonical ledger authority;
do not invent task IDs from graph node IDs.

For graph-backed work, every added or materially revised task carries the required body fields
plus `Graph evidence:` inside its Sources section (node/path, source locations,
confidence and scope). If graph coverage is unavailable, say so and cite the
verified source instead. Do not require graph metadata for untouched historical tasks.
Name the user/system outcome rather than "review hub" or "improve documentation".

Decompose along the verified change/impact path into a bounded vertical slice:
- Goal/payoff: accepted requirement and the consequence of the current gap.
- Scope/exclusions: exact components/interfaces affected, compatibility/security
  constraints and what the slice deliberately leaves unchanged.
- Acceptance/checks: observable result, exact feasible test command or planned test,
  expected signal, plus relevant negative/failure and regression cases. Unrun checks
  stay planned; source relationships do not prove passing behavior.
- `Dependencies:`: actual prerequisite tasks, with reason grounded in the verified
  path; graph adjacency alone does not establish a scheduling dependency.
- `Ownership:`: actual integration/component owner or unresolved owner question.

Order Now/Next by accepted milestone, dependency readiness, user impact and risk;
use graph impact to explain blast radius, not to override focus/priority authority.
Fix supported documentation now. Implementation tasks include docs/tests as part
of delivery instead of multiplying graph exploration/preflight tasks. Keep at most
one investigation task per blocking unknown under the existing goal-gap contract.

## 4. Verify the handoff

For each changed doc claim or new task, show the evidence chain:
accepted requirement -> graph path/finding -> verified source/test gap -> owned
correction or bounded task -> observable acceptance. Record material unsupported
claims/coverage warnings and the queries actually run in existing authorized owners
or private run receipts; do not add timestamp-only churn to TODO.

Run existing goals fmt/validate/render and consumer backlog-check gates unchanged.
Check dependency/ownership fields, duplicate outcomes and Now/Next eligibility.
Unchanged evidence must keep goals.json and TODO.md byte-identical on repeat.
Report graph freshness/coverage, actual commands/results, source corroboration,
changed owners/tasks and outstanding uncertainty. Static policy tests and a real
Graphify CLI smoke test do not prove model adherence or better live task quality.
