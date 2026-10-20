# Test-suite optimization

Toolset-owned engineering protocol for slow, repetitive or low-signal tests. Aim for
**minimum sufficient protection against real regressions**, not a minimum count.
Equal covered lines do not mean equal behavior, branches, assertions or contracts.
For writing new tests test-first, use the pinned `test-driven-development` protocol;
this method optimizes existing protection within the caller's authority.

Default to audit of the named/current repository. Explicit read-only writes nothing,
including plans and queues; return findings only. An explicit apply request or an
existing authorized implementation task permits one bounded, supported batch with
verification, without another planning or permission ceremony. Preserve repository
instructions, active writers, required checks and no-commit/no-push/live limits.
Never interpret “all my repos” as authority for an automatic filesystem-wide scan.

## When to run it

Use for a concrete test-cost or detection-quality problem, or when the suite exceeds
its repository-specific [test budget](../../../shared/ENGINEERING-CYCLE.md#test-budget).
Absent local thresholds, over 10 minutes for the normal offline gate, roughly 1,000
lines in a test module, or another near-duplicate case are audit signals, not quality
verdicts or deletion targets. Reuse the existing audit and implementation task IDs;
keep at most one open suite audit per repository, not a competing backlog.

## Quick pass first

Build a compact behavior/risk matrix **before choosing removal candidates**:

| Public contract / representative edge | Layer and existing test/case | Oracle / defect detected | Unique boundary or incident risk | Cost / evidence / unknowns |
| --- | --- | --- | --- | --- |
| Identify the owned obligation, not an internal method | Unit, integration or smoke/E2E; exact detector ID | Observable result, invariant, error or contractual interaction | Why another detector cannot replace it; bug/task ID if any | Available timing, history, coverage and missing evidence |

Keep pure logic, parsing and calculation at unit level; real DB/HTTP/queue/
serialization contracts at integration level; a small set of critical journeys at
smoke/E2E level. Choose the lowest reliable layer only if it preserves the same risk.
A unit mock cannot prove a real handoff. Duplicate layers need a stated integration
risk, not “more coverage.”

Inspect the slowest/largest modules using existing reports first. Look for repeated
setup, sleeps, duplicate executions and case families. Stop once evidence supports a
bounded useful batch; do not require whole-suite experiments for every audit. Prefer
fixture/execution improvements that preserve every oracle before riskier removals.

## Measure first

Bind evidence to source/test revision, environment, command, selected and collected
case counts, outcomes and sample window. Separate observed facts from hypotheses.
Use proportional evidence; missing tools or history do not prevent a qualitative
audit or unrelated safe improvements. They hold only changes that depend on them.

- **Timing:** use available per-test/file/directory timings and slowest-test reports
  (for example the runner's equivalent of `pytest --durations=30`). Measure candidate
  scope before/after on the same environment, command and workload for quantitative
  claims. Use bounded repeats when variance matters; report runs and spread. No
  unconditional three-run whole-suite baseline. An exact-duplicate/clarity audit
  may proceed without timing; report cost or speedup as unmeasured, never inferred
  from fewer methods, cases or lines. Full-suite speedup needs comparable passing
  full-suite measurements, not focused timings or a failed instrumented attempt.
- **History and flakes:** inspect available CI failure history and bounded repeated
  runs of suspect cases; record failures/runs and window. Missing history is unknown,
  not zero failures; one passing run is not a zero-flake rate. Stable, never-failed
  regressions can be valuable guards. Separate product races from test instability.
- **Coverage:** inspect diff line/branch coverage at touched behavior and per-test
  contexts where they distinguish candidates. Total coverage is context, not the
  target. Preserve required line/branch obligations of touched modules; inspect
  assertions and the behavior matrix even when percentages or covered sets match.
  Record unavailable tools and subprocess/native blind spots explicitly; never
  install a coverage dependency merely to audit or treat missing records as dead tests.
- **Mutation (optional):** when tooling is available, inspect critical modules and
  candidate scope in a disposable environment outside the repository. Do not require
  a new dependency, network or paid service; record “not measured” when unavailable.
  Use the distinctions below instead of ranking tests by an aggregate score.

### Contextual coverage when needed

Use the repository's existing tool. For coverage.py, enable branch measurement and
per-test contexts, then export `coverage json --show-contexts`. Instrument only the
candidate scope needed to resolve uncertainty, not the whole suite by default.
For subprocess-heavy suites, a scratch `sitecustomize.py` may call
`coverage.process_startup()` with an absolute `COVERAGE_PROCESS_START` config,
`parallel = True` and an absolute data path. Restrict measurement to owned sources
and omit tests/vendored code. In the runner's `startTest`, switch the current context
to `test.id()` and export that ID in a dedicated environment variable; the startup
hook switches the child's context to the inherited ID. Reset between tests and
retain timings/outcomes. Dynamic test-function contexts alone do not identify the
child's caller. Combine only after all children exit, using the same config.

Verify a child-only smoke case, including a nested source file, retains its caller
context before widening measurement. Prefer an absolute repository source path
with explicit omissions: root-only include globs can omit nested modules. Sanitized
environments, isolated Python (`-I`), other interpreters, killed children and
non-Python commands may remain blind. Keep data/output off `sys.path`, separate
from the startup hook: shard creation can invalidate metadata caches during tests.
Retain instrumentation failures and rerun exact affected cases after harness repair,
separately from ordinary uninstrumented checks. Keep instrumentation/raw data in
scratch outside Git; do not alter tests just to obtain an audit measurement.

### Mutation evidence and uncertainty

Mutants survive, not tests. Compare the same source and mutation operators before/
after; record mutant-to-test detection maps where available, not just scores.
Preserve uniquely detected non-equivalent faults and critical-module detection.
Identical killed-mutant sets are only redundancy leads alongside the behavior matrix.

Distinguish killed, surviving, uncovered/no-coverage, equivalent, invalid, ignored,
pending and timed-out mutants. A survivor may expose an assertion gap or equivalent
behavior; neither a survivor nor a low score makes a test disposable. Explain any
equivalence judgment. A timeout counted as detected by a tool is not proof of a
meaningful oracle. Invalid/ignored/pending outcomes and unknown detection mappings
are uncertainty, not evidence of redundant protection. Tool-specific totals must
not conceal these distinctions or justify weakened thresholds.

## Find candidates

Read each candidate's body, helpers, setup and oracle against the matrix:

- **Exact duplicates/subsumption:** same seam, preconditions, behavior and oracle;
  subset coverage alone is not proof. Check branches and unique interactions.
- **Case families:** consolidate equivalent setup/action into labeled table cases;
  retain every distinct behavior and an identifiable failure per case. Fewer declared
  methods or moving tests between files is not itself pruning or a speedup.
- **Expensive setup/execution:** share immutable fixtures and small data builders,
  not mutable databases/processes whose isolation matters. Replace fixed sleeps
  with events or bounded polling. Remove duplicate execution or parallelize only
  when independence and resource limits are established.
- **Weak oracles:** tautologies recomputing the implementation's answer, internal
  mock-call assertions, side channels and framework-only checks are candidates only
  when they protect no owned contract. The tautology/public-seam ideas adapt Matt
  Pocock's MIT-licensed `tdd` skill. A no-exception startup smoke, contractual log,
  externally visible interaction or protocol call ordering may be a valid oracle
  without an explicit assertion. “Assertless” or “mocked” alone is not a verdict.
- **Fidelity:** replace mock-heavy internals with fakes or real contract checks when
  they improve detection. Combine assertions only for one coherent behavior. Use
  property tests when existing generators/invariants and reproducible counterexamples
  improve on a handwritten matrix; preserve critical named examples. Golden/snapshot
  tests need intentional stable output contracts and reviewable diffs, not bulk approval.

## Keep

Never lose or weaken a still-required obligation:

- named bug/incident/task regressions, including those that have never failed;
- unique branches or non-equivalent mutant detection;
- composed handoffs or real boundary risks not established by unit mocks;
- safety, security, authorization and data-loss protection;
- repository-required live, qualification and compatibility evidence.

These are protected risks, not immutable test-file layouts. A named regression may
move into an equivalent labeled case, but its bug ID and traceable oracle must
survive. Every deletion maps to a retained test/case **and its oracle**, or documents
why the product obligation was retired. Delete obsolete tests with deleted behavior,
not surviving compatibility guarantees. If equivalence cannot be established, keep
or investigate; green checks, equal coverage and no recorded failures do not prove it.

## Record tasks, do not edit (audit default)

An audit changes no tests or product sources. Unless read-only, record a compact
keep/consolidate/remove/repair/quarantine/investigate map in the existing plan owner,
with exact test/fixture IDs, risk-to-oracle mapping, evidence, unknowns, budgets and
bounded next tasks. Reuse existing audit/suite-thinning IDs and ownership. Unsupported
candidates remain investigate findings, not executable removal tasks. Order supported
work by payoff and risk, preferring oracle-preserving fixture improvements.

In authorized apply mode, reuse the implementation task and execute one supported
batch; do not insist on another audit task or approval. Save the same mapping and
actual before/after checks in its existing receipt. No implicit commit, publication,
schedule, new framework or execution of live suites is authorized by this method.
Keep raw/private CI history, credentials and scratch output out of Git.

## Budgets, flakes and selection

Apply the shared [test budget](../../../shared/ENGINEERING-CYCLE.md#test-budget).
Record repository-specific per-suite CI wall-time limits and a justified new-case
budget per change/PR, with environment/baseline and a review rule for exceptions.
Missing measurements stay unknown; propose limits explicitly rather than pretending
an existing threshold or measurement. Each case names its behavior/risk in a useful
name or matrix, without mandatory boilerplate. Start a bug fix with one discriminating
regression at the right public seam, extending an existing case where sufficient.
Additional cases/layers must protect distinct risks. Behavioral config/parser/
migration coverage is not banned as “configuration.” No tests per function/line or
implementation-mirroring TDD loops. Review slowest/noisiest suites quarterly through
existing maintenance; this is not permission to create a timed job.

Diagnose flakes first. Quarantine needs an owner, reason, expiry, tracking issue and
explicit lost protection/risk, plus visible reporting and any required replacement
protection. Never silently skip a critical regression or manufacture a passing gate.
At expiry repair it, retire only with documented risk review supporting deletion,
or escalate visibly; do not silently extend or leave it permanently disabled.

Impact-based selection is optional only with sound dependency mapping, including
fixtures, config, generated inputs and cross-module boundaries. Unknown impact falls
back to the normal gate. Retain the existing full gate or an explicitly agreed
periodic full run; do not weaken CI, blanket-skip tests or lower thresholds to save time.
Focused selection during work is not a replacement for required repository acceptance.

## Acceptance for each change

Before claiming an applied batch complete:

- focused changed behaviors and the normal repository gate pass under its execution
  contract; a delegated final gate stays pending until its actual result, not waived;
- required diff/line/branch obligations remain, and measured critical mutant detection
  does not drop on comparable source/operators; document blind spots and uncertainty;
- every removed test maps to a retained detector/oracle or a documented retired risk;
  all merged cases still run, identify failures, and preserve named bug traceability;
- source-bound before/after evidence covers the actual scope, outcomes and costs;
  quantitative saved-time claims have comparable passing measurements. Unmeasured
  clarity improvements say so. Never claim full-suite equivalence from focused checks.

Independent review checks the matrix, actual test/helper diff, retained oracles,
missing evidence, budget exceptions and quarantine/selection safety. For method
qualification use a compact disposable fixture: equivalent table cases; equal-coverage
but distinct authorization behaviors; a valuable never-failed regression; an assertless
smoke oracle; a real handoff absent from mocks; a flaky critical check; equivalent/
surviving mutants; missing CI/mutation evidence; read-only versus authorized apply;
and an extra case for a unique boundary risk. Review decisions and artifacts, not
heading/phrase compliance. Failures call for narrow corrections to decisions or
oracles, not another layer of prose-assertion tests. Offline fixture review is not
live qualification, actual repository pruning or a measured performance result.

## Never

- delete, skip or weaken a detector to make a run green or reach a count;
- discard a safety obligation, bug trace or unique risk during consolidation;
- replace a public/real-boundary oracle with internal-detail assertions;
- add a required network, paid, coverage or mutation dependency just for an audit;
- manufacture history, timings, equivalence, tool results or approval;
- treat a green run, coverage percentage, mutation score or test count alone as quality.
