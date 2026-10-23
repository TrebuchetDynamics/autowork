# Blocker recovery implementation plan

> Execution: native, with one independent final review. The owner explicitly requested implementation; no additional approval checkpoint is needed.

**Goal:** Technical holds remain visible and receive bounded engineering action without being relabelled as owner decisions.

**Spec:** Owner's October 23 implementation request in this session: centralize question admission, count technical blockers, connect exhausted review findings to existing repair machinery, preserve evidence and budgets, and independently harden selective-review candidate scope.

**Architecture:** Extend the shared `failure_policy` rather than add a scheduler. Questions, status roots and health consume its disposition. Existing DOCS-MAINTAINER jobs and private item receipts own bounded repair planning; original worker candidates and review-rework evidence stay retained. Selective-review hardening is isolated on its existing feature branch.

## Constraints

- No second scheduler, blanket retry increase or relaxed acceptance/checks.
- Preserve genuine owner/live authorization and external-input questions.
- No service changes or fleet-wide review opt-out. No publication in this implementation pass.
- Active TOOLSET-380/381/382 own TUI work; this branch does not edit their files or tasks.
- Scope inspected at `2c07bbaa`; no open task duplicates the question/health/repair changes. TOOLSET-381 is a retained read-only blocker-report candidate, not this fix.

## Slices and verification

### 1. Shared question admission

Files: `pi-autowork/engine/failure_policy.py`, `parallel_status.py`, `pi-autowork/pi_autowork/questions.py`, their focused tests.

- [x] Add regressions for a real quick-hold history whose cause is `contract_changed`, failed technical maintainer repair, malformed ledger, dependency cycle and incomplete contract.
- [x] Observe failures: technical cases currently produce USER_INPUT/USER_DECISION.
- [x] Add a shared disposition reader for rows/roots; map contract/cycle/store defects to engineering repair and preserve typed owner causes, outside prerequisites and exhausted-report compatibility.
- [x] Gate every `build()` question at its common `add()` function; retain owner questions and existing deferral behavior.
- [x] Run `python3 -m unittest discover -s pi-autowork/tests -p test_questions.py` and `python3 -m unittest discover -s pi-autowork/engine -p test_failure_policy.py`.

### 2. Technical blocker accounting

Files: `pi-autowork/pi_autowork/health.py`, `pi-autowork/tests/test_health.py`.

- [x] Change the exhausted-review regression to require its dependents in stopped/blocked counts, not ordinary waiting; preserve zero owner questions.
- [x] Introduce separate action-required and owner-required predicates. Ordinary overlap/dependency waits stay waiting; unresolved technical repair roots block their dependents.
- [x] Run `python3 -m unittest discover -s pi-autowork/tests -p test_health.py`.

### 3. Bounded exhausted-review repair

Files: `pi-autowork/pi_autowork/maintainer.py`, `coordinator.py`, relevant engine recovery code/tests only if needed, `tests/test_pi_autowork.py`.

- [x] Reproduce `reviewed_twice` with preserved findings producing no maintainer action.
- [x] Route it into the existing maintainer job, carrying the retained candidate, incident and findings. Use existing item receipts to suppress repeated unchanged work across restart and cosmetic task edits.
- [x] Preserve acceptance/checks/authority and review-rework budget; do not delete retained artifacts or create owner questions after unsuccessful technical repair.
- [x] Add a fake-Pi coordinator regression proving scheduling, durable deduplication and continued independent work, without real model/service calls.
- [x] Run focused maintainer and coordinator tests, then `python3 scripts/affected_tests.py --base 2c07bbaa --run` once for the combined branch.

### 4. Independent selective-review hardening

Sole delegated writer uses `.worktrees/selective-review`. Add an earlier-code/final-prose multi-commit regression, inspect the engine's actual accepted merge shape, and retain review whenever the complete candidate range is unproven. No merge or activation in this pass.

## Review focus

- Stale owner booleans must not promote known technical causes.
- Retained-report exhaustion still needs its current explicit owner gate until a separate investigator exists.
- A recovery receipt must not be invalidated by mere polling, timing or cosmetic edits.
- Repair planning must not weaken acceptance/checks or reset an exhausted review-rework budget.
- A successful check of a final commit must not hide earlier code changes.

## Progress

- Context and root causes verified; canonical checkout left to its live runner.
- Implemented and independently reviewed all four slices; no remaining blocking review findings.
- Review caught and regressions now reject lossy display-field contract comparisons (including unchanged display text), cosmetic requeue admission, and deletion of a spent review budget after a later validation failure.
- `python3 scripts/affected_tests.py --base 2c07bbaa --run`: 56 affected modules, zero failed directories; log `/tmp/autowork-blocker-validation.log`.
- Selective-review checkout: `python3 scripts/affected_tests.py --base HEAD --run`: 46 affected modules, zero failed directories; log `/tmp/autowork-selective-range-validation.log`.
- Both inventories excluded the three optional native integration modules. No live-model, service, delivery or throughput qualification was attempted.
- Implementation finished in two isolated task checkouts without changing fleet settings, task records, the retained TOOLSET-381 candidate or canonical files. The owner's subsequent Git Commit Push invocation authorizes scoped topic-branch commits and publication; main integration and live qualification remain separate, pending steps.
