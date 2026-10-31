---
name: test-optimizer
description: "Shrink test suites that add no protection."
license: MIT
---

# Test Optimizer

Actively reduce executed test cases, test code and maintenance/runtime cost.
Delete tests that add no meaningful protection. Do not settle for reorganizing a
bloated suite or moving the same executions into a table. Keep the smallest set
that detects distinct, supported regressions, not a target count or coverage score.

Apply the [shared Ponytail method](../shared/PONYTAIL.md) and
[common contract](../shared/COMMON-CONTRACT.md).
Use the [ASD-STE100 and project language rules](../shared/COMMUNICATION.md) for user-facing text.
Reuse the existing
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
3. **Remove before polishing:** prioritize evidence-backed deletion of redundant,
   vacuous and obsolete tests. Prune equivalent inputs to useful representatives,
   retaining distinct boundaries. Then shrink fixtures and share immutable setup.
   Labeled tables may reduce code, but do not count unchanged cases as pruning.
   Keep mutable state isolated and failure IDs useful.
4. **Classify:** keep, consolidate, remove, repair or investigate. For each removal,
   record one reason: a retained equivalent detector and oracle, a retired product
   obligation, or evidence that the test protects no owned behavior or invariant.
   Do not invent a replacement for a test that had no meaningful detector.
   Unproven removal candidates remain intact.
5. **Apply and verify:** change one coherent batch within scope. Preserve product
   behavior and every distinct required oracle; do not weaken assertions, skip cases
   or lower thresholds to get green. Run affected checks and required acceptance
   gates, inspect the diff and obtain required independent review. A gate delegated
   to the coordinator remains pending, not passed.

## High-value reduction targets

- Delete unconditional checks such as `assert 0 == 0` when their setup/execution
  also protects no product contract. Check for implicit startup/import or error
  detection before declaring a test vacuous.
- Delete tests of retired features or unreachable obsolete paths after tracing
  supported callers, dynamic/external entrypoints and compatibility obligations.
- Remove tests that only verify a mock's configured return value, language/framework
  behavior or copied implementation logic when no independent product oracle exists.
  If they expose a real coverage gap, repair the smallest relevant detector instead.
- Remove duplicate cases and layers that protect the same behavior under equivalent
  conditions. Keep an integration test when it catches a real handoff a unit mock cannot.
- Reduce oversized fixtures, snapshots and setup to what the retained oracle needs.
  Remove helpers, data and dependencies used only by deleted tests after checking
  their remaining consumers. Do not compress unrelated behaviors into one giant test.

For every retained candidate, name the distinct failure it can catch and why the
remaining suite cannot catch it reliably. If no distinct value can be established,
investigate the source rather than defending the test count. Prefer a smaller
suite when the evidence supports it. Add cases only for a demonstrated missing
required risk, not to replace each deleted test or test these instructions' wording.

“Never touched” needs clarification from evidence, not another approval ceremony.
Code absent from supported execution paths is a removal lead. Code that rarely
changes, tests that rarely fail, or tests unrelated to today's diff are not dead.
Use sound affected-test selection for local iteration, without deleting unrelated
valid tests or bypassing required deployment/acceptance gates.

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
- removed IDs mapped to retained oracles, retired obligations or evidence of no
  owned contract/invariant;
- before → after test-code lines, declared tests and **executed cases separately**;
- commands, outcomes, review, remaining risk and pending gates;
- comparable measured runtime, or **not measured**; stop reason and next action.

Parameterizing 80 tests into one function with 80 cases is code consolidation, not
79 fewer executions or an inferred speedup. Do not claim full-suite equivalence
from a focused green run.

[Evaluation scenarios and evidence limits](references/evaluation.md).
## Boundaries

- Not test-first authoring; use the `tdd` protocol through `/engineering`.
- Not dead-code removal; use `/unused-code`.

**Done when:** supported removals are applied with an oracle mapping and the affected checks pass, or a read-only report is delivered.
