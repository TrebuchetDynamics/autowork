# Test-suite optimization

Toolset-owned engineering protocol. Use it when a test suite is slow, repetitive or
low-signal and the task is to make it cheaper or clearer **without losing the ability
to catch defects**. The goal is never a smaller test count: two tests that cover the
same lines can still catch different defects.

The technique is test-suite minimization and optimization: redundancy analysis,
consolidation, execution and fixture cost, and assertion quality. It audits first and
changes nothing; every change becomes its own task. For writing new tests test-first,
use the pinned `test-driven-development` protocol instead.

## When to run it

Run it when a suite passes the [test budget](../../../shared/ENGINEERING-CYCLE.md#test-budget):
the normal offline check takes over 10 minutes, test modules pass about 1,000 lines,
or new work keeps adding near-identical tests. One audit task per repository is open
at a time; its findings become ordinary tasks.

## Quick pass first

On a large suite, start cheap and stop when it already yields clear tasks:

1. Time the normal check and list the slowest 30 tests and the largest test modules.
2. Read those modules for the candidates below: duplicates, parametrizable
   families, rebuilt fixtures, sleeps and repeated process or repository setup.
3. Record the speed-ups that change no assertions as tasks right away.

Measure per-test coverage (below) only for the consolidation and removal candidates
the quick pass finds, not for the whole suite.

## Measure first

Record a baseline on one named commit and machine before judging anything:

- **Inventory and time:** the repository's normal check command, its test count and
  wall time over 3 runs; time per test directory or module; the 30 slowest tests
  (for example `pytest --durations=30` or the runner's equivalent).
- **Coverage:** line and branch coverage of the project's own sources with per-test
  contexts, so each covered line records which tests reach it (coverage.py:
  `coverage run --branch --context=test` with `dynamic_context = test_function`, then
  `coverage json --show-contexts`). Use the repository's existing coverage tool when
  it has one. For subprocess-heavy suites, also measure children: put
  `import coverage; coverage.process_startup()` in a scratch `sitecustomize.py`,
  prepend that directory to `PYTHONPATH`, and set `COVERAGE_PROCESS_START` to an
  absolute scratch config with `[run] branch = True`, `parallel = True` and an
  absolute `data_file`. Restrict measurement to owned sources and omit tests and
  vendored code. In the runner's `startTest`, call `Coverage.current().switch_context(test.id())`
  and export that same ID in a dedicated environment variable; the startup hook
  must switch the child's context to that inherited ID. Dynamic test-function
  contexts alone do not identify a child process's calling test. Reset the context
  between tests, retain per-test timings and outcomes, and run `coverage combine`
  with the same config after all children exit, then `coverage json --show-contexts`.
  Verify a child-only smoke test has its caller's context before the full run,
  including a nested source file. Prefer `source = /absolute/repository` with
  explicit omissions: a root-only include glob can silently omit nested modules.
  Record blind spots explicitly: sanitized environments, isolated Python (`-I`),
  other interpreters, hard-killed children and non-Python commands may not produce
  records. Equal line sets do not imply equal branches, assertions or contracts.
  Keep the data/output directory off `sys.path` (separate it from the startup-hook
  directory); coverage shard creation can otherwise invalidate metadata caches
  during the very tests being measured. Retain instrumentation-induced failures
  and rerun the exact affected test after repairing the harness, separately from
  an ordinary uninstrumented run.
  Keep instrumentation and raw data outside the repository; do not alter tests or
  add a coverage dependency merely to audit them.
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
