---
name: test-optimizer
description: "Use when reducing redundant tests or low-value scenarios."
license: MIT
---

# Test Optimizer

Reduce test code, duplicate executions and redundant scenarios while retaining the
smallest sufficient protection against real regressions. Optimize detection per
unit of maintenance/runtime cost—not a target number of tests.

Apply the [shared Ponytail method](../shared/PONYTAIL.md) and

Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
[common contract](../shared/COMMON-CONTRACT.md). Reuse the existing
[test-suite optimization protocol](../engineering/local/test-suite-optimization/PROTOCOL.md)
for evidence, validation, quarantine and review; do not create a competing method
or backlog. Load its relevant sections once.

## Scope and mode

- Bare invocation audits the named/current repository; it changes no tests.
- Explicit `apply`, a request to reduce/optimize the suite, or existing implementation
  authority permits one supported batch without another approval ceremony.
- Read-only/questions-only/no-write wins over apply: change nothing, including
  reports or task records. Otherwise reuse the existing task/plan owner through
  `autowork tasks`; unavailable task tooling is not permission to hand-edit records.
- Preserve ownership, required gates and user limits. Explicit stop, time, token,
  spend and batch limits override conflicting continuation advice in references.
  No automatic commits, push, live suites, dependencies or CI-policy changes.

## Optimization pass

1. **Baseline:** inspect status, scope, runner configuration, fixtures and available
   reports. Record exact commands, selected/collected cases, outcomes and available
   timings. A failing baseline is not permission to delete its failing detectors.
2. **Map protection:** for each candidate name the public behavior, preconditions,
   layer, oracle, unique boundary/incident and cost. Trace helpers and real callers;
   equal coverage, similar names and never failing are not equivalence.
3. **Simplify first:** shrink fixtures; share immutable setup; eliminate duplicate
   executions. Use labeled tables for equivalent setup while preserving distinct
   cases and useful failure IDs. Keep mutable state isolated.
4. **Classify:** keep, consolidate, remove, repair or investigate. For every removal
   record `removed ID → retained ID + equivalent oracle`, or evidence the product
   obligation was retired. Unsupported candidates remain intact.
5. **Apply and verify:** change one coherent batch within scope. Preserve product
   behavior and every distinct required oracle; do not weaken assertions, skip cases
   or lower thresholds to get green. Run affected checks and required acceptance
   gates, inspect the diff and obtain required independent review. A gate delegated
   to the coordinator remains pending, not passed.

## “Very unlikely” is a lead, not deletion evidence

Prioritize likelihood **and consequence**, supported input paths, incident history,
contract obligations and detection uniqueness. Keep rare security, authorization,
data-loss, compatibility, concurrency and named regression protection when it guards
a distinct supported risk.

Remove a contrived scenario only when source/contract evidence rules out its
premise across applicable public, internal, dynamic and external entrypoints and
it protects no separate invariant; retain the actual boundary/rejection oracle.
For reachable cases, select representatives only from proven equivalent behavior
classes. Distinct boundaries remain distinct. Unknown reachability means investigate.

Example: two identical parser checks can become one retained detector. A claimed
“impossible” input stays until validated. A once-in-years corruption regression
stays, with its bug ID.

## Receipt

Report:
- scope/mode and keep/consolidate/remove/investigate decisions;
- removed IDs mapped to retained oracles or retired obligations;
- before → after test-code lines, declared tests and **executed cases separately**;
- commands, outcomes, review, remaining risk and pending gates;
- comparable measured runtime, or **not measured**; stop reason and next action.

Parameterizing 80 tests into one function with 80 cases is code consolidation, not
79 fewer executions or an inferred speedup. Do not claim full-suite equivalence
from a focused green run.

[Evaluation scenarios and evidence limits](references/evaluation.md).
