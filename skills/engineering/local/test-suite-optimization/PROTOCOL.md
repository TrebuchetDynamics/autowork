# Test-suite optimization

Toolset-owned engineering protocol. Use it when a test suite is slow, repetitive or
low-signal and the task is to make it cheaper or clearer **without losing the ability
to catch defects**. The goal is never a smaller test count: two tests that cover the
same lines can still catch different defects.

The technique is test-suite minimization and optimization: redundancy analysis,
consolidation, execution and fixture cost, and assertion quality. It audits first and
changes nothing; every change becomes its own task. For writing new tests test-first,
use the pinned `test-driven-development` protocol instead.

## Measure first

Record a baseline on one named commit and machine before judging anything:

- **Inventory and time:** the repository's normal check command, its test count and
  wall time over 3 runs; time per test directory or module; the 30 slowest tests
  (for example `pytest --durations=30` or the runner's equivalent).
- **Coverage:** line and branch coverage of the project's own sources with per-test
  contexts, so each covered line records which tests reach it (coverage.py:
  `coverage run --branch --context=test` with `dynamic_context = test_function`, then
  `coverage json --show-contexts`). Use the repository's existing coverage tool when
  it has one.
- **Mutation score (optional):** only when a mutation tool is available, run from a
  disposable environment outside the repository, and only on the modules with
  candidates. Record "not measured" otherwise; never add the tool as a dependency.

Keep raw output in a scratch directory; record the numbers, method and commit in the
repository's plan or task, not the raw files.

## Find candidates

Group tests by evidence, then read them before calling anything redundant:

- **Exact duplicates:** the same setup, action and assertions under different names.
- **Subsumed tests:** the same public seam, with covered lines and assertions that are
  a subset of another test's. Identical coverage alone is a lead, not proof.
- **Parametrizable families:** near-identical tests that differ only in inputs and
  expected values; merge into one table-driven test that keeps every case and names
  each case in its failure message.
- **Expensive setup:** slow fixtures, repeated repository or process creation,
  sleeps and polling, setup rebuilt per test when it could be shared read-only.
- **Execution overhead:** suites run serially when they are independent, or the same
  tests run more than once per check.
- **Low-value tests:** no assertion; tautological expected values, where the test
  recomputes the answer the way the code does, so it can never disagree with it;
  implementation-coupled tests that mock internal collaborators or assert through a
  side channel instead of the public seam. The tautology and seam criteria are
  adapted from Matt Pocock's MIT-licensed `tdd` skill.

## Keep

Never remove or weaken, even when coverage looks redundant:

- a regression test named for a bug, incident or task;
- a test that alone covers a branch or alone kills a mutant;
- composed, cross-seam or end-to-end tests that prove a handoff the unit tests do not;
- tests for safety, security, data loss or authorization boundaries;
- tests the repository marks as required, live or qualification evidence.

## Record tasks, do not edit

The audit edits no tests or sources. Record findings in the repository's existing plan
owner, then one task per change in its work queue (TODO.md with goals.json here):
the exact tests or fixtures involved, the measured before values, the change, and the
acceptance below. Keep candidates without evidence as unverified findings, not tasks.
Order tasks by measured payoff and risk; prefer execution and fixture speed-ups that
change no assertions before consolidations.

## Acceptance for each change

A consolidation, removal or speed-up task is done only when:

- the changed tests and the full normal check pass;
- line and branch coverage of the touched modules do not drop, and the mutation score
  does not drop when it was measured;
- each removed test is listed with the remaining test that covers its behavior;
- every merged case still runs and still names itself on failure;
- wall time is measured before and after on the same machine, and reported even when
  the change is for clarity rather than speed.

## Never

- delete or skip a test to make a run pass or to reach a count;
- weaken an assertion to keep a merged test green;
- replace a public-seam test with one that reaches into internals;
- add a network, paid or required mutation tool;
- treat a green run, coverage percentage or test count alone as proof of quality.
