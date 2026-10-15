# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Hermes Toolset. Scope and current architecture: [project contract](docs/project.md).
[goals.json](goals.json) indexes the remaining work below; verified completed
tasks move to the archive automatically. Ledger eligibility is not worker
admission or live qualification.

TOOLSET-002's reviewed first-index initialization is integrated locally;
TOOLSET-003 remains the isolated live-recovery qualification. TOOLSET-001 and
TOOLSET-002 completion evidence is in [the archive](TODO.archive.md).
Fast-startup plan: TOOLSET-012 is reviewed and integrated locally; TOOLSET-013
retains measured native startup qualification. TOOLSET-003/011 still need their
named environments; TOOLSET-008's reviewed continuation correction is integrated
and archived. Priority plan: TOOLSET-028 (archived) enforces TODO.md order offline; TOOLSET-029 is the
separately authorized fleet migration. Preserve caller limits, queue priorities and ownership.

Execution notes: Each task states the remaining action, acceptance, checks and stop
conditions. Read linked detail only for a concrete gap; do not re-plan settled work
or redo verified partial delivery. Reuse check evidence only while source, tests,
dependencies and environment match. Required tests, review, ownership protections,
integrity checks and live qualification remain mandatory. Editing this queue does
not change a running worker's assigned contract or authorize dispatch/scheduling.

## Now

## Next

### TOOLSET-029 — Migrate fleet repositories to recorded TODO.md priority order

- [ ] TOOLSET-029 — Migrate fleet repositories to recorded TODO.md priority order
- Status: open.
- Historical migration receipt: partial (2026-10-14): 6 of 9 migrated and committed locally with unchanged eligible order: this repository and five fleet repositories (four of them after a separate checkpoint commit of their pending queue edits). Not migrated: one repository with a staged 9-file docs batch that includes the queue files, one with a live in-progress claim and active session, and one with no commits. All matching jobs were already paused and stay paused.
- Goal: PRIORITY — Make TODO.md order the enforced human priority.
- Sources: [accepted priority plan](docs/project.md#todo-owned-task-priority), [accepted rollout](docs/project.md#rollout), [bootstrap contract](docs/project.md#reconciliation-and-bootstrap).
- Scope: For each fleet repository with goals.json: dry-run bootstrap and report the full before/after order (including one repository's deeper difference), preserve stopped/paused jobs, lock and verify unchanged inputs, migrate, validate, compare the next pick before and after, and commit locally per repository within the existing migration authority. The later stop-all instruction supersedes automatic resumption.
- Acceptance: Every repository has a synchronized `priority_order`; first eligible picks are unchanged; matching repositories get no TODO.md rewrite; a failed repository stays paused; a later manual reorder changes selection after reconciliation.
- Checks: Per-repository dry-run receipts, `goals.py validate` and `goals.py next --json` before and after, and job readback confirming stopped/paused state is unchanged.
- Dependencies: TOOLSET-028.
- Ownership: Toolset coordinator under separate live authorization.
- Exclusions: No push, no unrelated job changes and no job resumption while the owner's stop-all instruction remains in force.
- Next action: Recheck the remaining repositories' current staged/unstaged changes, actual writers, initial commit and recorded priority state. Re-run the dry-run with a fresh revision for any now-eligible repository; preserve current pauses and genuinely overlapping work. Prior receipt conditions are not permanent holds.

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- [ ] TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow
- Status: open; live qualification not run.
- Goal: RECOVERY — Prove recovery reaches execution, not just a planning receipt.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [recovery contract](skills/autowork/references/backlog-planning.md), [existing regressions](skills/autowork/scripts/test_backlog_plan.py), [verification limits](docs/testing.md).
- Scope: In a disposable repository, reproduce missing prerequisites and candidate drift. Observe automatic planning, TODO update and retry of the eligible original slice; repeat unchanged inputs once to verify decision reuse.
- Acceptance: No extra user planner command; original exclusions and ownership survive; execution is reported separately from planning.
- Checks: Run focused recovery regressions and one bounded isolated model/native smoke journey covering both cases. Retain exact source, task, commands/results, commit or none, and remaining blocker. Offline tests alone cannot close this task.
- Exclusions: No production messages/deployment, real user repositories, forbidden prerequisite commits, writer takeover or fabricated completion.
- Dependencies: None.
- Environment prerequisite: Configured isolated model/native environment.
- Ownership: Next authorized coordinator; no active claim recorded.
- Current evidence: The shipped containment backend admits only local fixture executables and explicitly excludes provider/network dispatch. Its synthetic spending controller is not a model spending limit. No qualifying model journey was run.
- Next action: Supply an isolated model endpoint with externally enforced spend and descendant limits, then execute the bounded recovery journey; existing offline fixtures cannot replace it.

### TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles

- [ ] TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles
- Status: in_progress; reviewed scoped local updater is implemented and integrated in eb72be6; selected-profile deployment remains pending.
- Goal: RECOVERY — Deliver reviewed repairs without remote fetches or fleet-wide side effects.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [updater](update_bundle.py), [updater tests](tests/test_update_bundle.py), [installation](docs/installation.md).
- Scope: Extend the existing updater with explicit selected profiles and immutable reviewed local source, native security admission, preflight/staging/backups, installed hash readback and resumable per-profile results. Preserve unselected consumers of shared sources and pinned runtimes.
- Acceptance: No implicit fetch, profile expansion, scan override, worker restart or configuration/schedule change. Active affected consumers defer; independent eligible targets proceed. Drift/source races refuse before unsafe writes. Retry reuses the same source and backups, unchanged deployment is a no-op, and installed bytes/registrations are verified without claiming product recovery.
- Checks: 52 real-Git/fake-native updater fixtures passed. Independent review found shared-board ownership and interrupted-clone defects; both reproduced and passed after repair. The combined 318/470/139/8 offline gate passed. Native scoped preflight ran; installation and live registration remain unverified.
- Dependencies: None.
- Ownership: Shared maintainer for implementation; authorized coordinator for selected-profile deployment.
- Exclusions: No implicit remote publication, dependency overrides, native scanner bypass, global configuration changes or active-runtime rebinding.
- Historical deployment evidence: Preflight against 51d99d6 deferred three selected profiles under the former native-ownership checks and one for a customized `skills/autoresearch/SKILL.md`; their bytes were preserved. That receipt proves no installation. The TODO-first implementation has since retired card-only vetoes; recheck actual consumers and current customizations rather than treating those old deferrals as present blockers.
- Next action: Check actual process identity, workspace writers and live helper consumers, then reconcile customized skill drift before scoped installation. Historical cards require no release or reconciliation. Reuse the reviewed updater; do not repeat its completed implementation or label preflight as deployment.

- [ ] TOOLSET-011 — Qualify the updated reporting workflow on the affected profile
- Status: open; original target environment unavailable.
- Goal: CRON-REPORTING — Verify setup confirmation and scheduled Telegram delivery separately.
- Sources: [accepted reporting qualification](docs/workflows.md#telegram-reporting-qualification), [reporting contract](skills/cron-autowork/SKILL.md), [verification boundaries](docs/workflows.md), archived TOOLSET-010 source delivery.
- Scope: On the original host/profile, install the updated bundle through its supported path. Identify the existing job, preserve its state/scope, verify its requested Telegram route, then inspect the next scheduled result.
- Acceptance: A setup request from another surface confirms once in the intended chat/topic; a scheduled occurrence has attributable execution and Telegram message receipts. Report failed, queued or unverified delivery honestly.
- Checks: Read back installed source and saved route/state; verify the actual setup message and scheduled result/delivery. These live checks are not run.
- Exclusions: No duplicate job, implicit resume, immediate development run, budget reset, push/deployment, USB formatting or real-PC changes. Never substitute another profile.
- Dependencies: TOOLSET-010.
- Environment prerequisite: Original host, affected profile/job and authorized Telegram transport.
- Ownership: Coordinator with that access; no active claim.
- Current evidence: Exact original profile directory and original job ID are absent from this host's root and existing-profile job stores. No replacement job, profile or message was created.
- Next action: Restore access to the original host/profile/job and its authorized Telegram route, then inspect the setup and scheduled delivery receipts.


### TOOLSET-013 — Measure time to useful worker action and qualify the faster startup

- [ ] TOOLSET-013 — Measure time to useful worker action and qualify the faster startup
- Status: open; TOOLSET-012 is integrated; isolated bounded environment still required.
- Goal: STARTUP — Verify lower preparation overhead without weaker startup safety.
- Sources: [accepted measurement contract](docs/project.md#faster-ready-task-startup), TOOLSET-012, [admission](skills/autowork/scripts/start_goal.py), [reporting boundaries](skills/autowork/references/dispatch-and-reporting.md).
- Scope: Compare manual and composed startup on the same disposable accepted task, source, model/environment and cold/warm conditions. Separate request-to-handoff, queue wait, admission and first useful test/reproduction/edit after the guard. Count coordinator tool/model round trips and routine messages.
- Acceptance: Fewer preparation round trips/messages with no observed comparable startup regression; preserve stale/ownership/dependency refusals. A heartbeat/queued card is not useful action; offline fixtures cannot close native qualification. Investigate contradictory timing.
- Checks: Run both routes with source-bound implementation commands; retain exact argv, dependency/interpreter/model identity, enforced limits, timestamps, native admission/run evidence and failures. Harness/baseline runs are not yet executed.
- Exclusions: No production repositories/messages, fabricated measurements, absolute latency/minimum-version promises, budget reset, protection bypass, push/deployment or live schedule/profile edits.
- Dependencies: TOOLSET-012.
- Environment prerequisite: Isolated configured native/model environment with external spending/descendant limits; unknown usage is not zero.
- Ownership: Authorized coordinator with that environment; no active claim.
- Current evidence: No externally capped isolated model environment is established; the existing local containment/controller fixtures exclude provider execution. No useful-action timing or speed claim was inferred from them.
- Next action: With the same isolated model environment required by TOOLSET-003, execute the paired cold/warm comparison and report actual results.

### TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index

- [ ] TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index
- Status: open; recorded, not scheduled.
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [review findings](docs/project.md#new-skill-review-2026-10-15).
- Scope: Rewrite toolset-owned `description` fields over 60 characters (autoresearch, autowork, beautify-github-readme, cron-autowork, engineering, lgtm, plan-for-me, plan-with-me) to one trigger-first sentence; vendored Impeccable stays unchanged.
- Acceptance: Hermes' skill linter reports no `description-length` warning for toolset-owned skills, and a test enforces the limit.
- Checks: A regression over `skills/*/SKILL.md`, then `python3 scripts/check.py`.
- Dependencies: None.
- Exclusions: No vendored-file edits.

### TOOLSET-066 — Qualify the Claude Code plugin with a live questions-only workflow

- [ ] TOOLSET-066 — Qualify the Claude Code plugin with a live questions-only workflow
- Status: open; live qualification not run.
- Goal: CLAUDE-CODE — Install the portable workflows in Claude Code.
- Sources: [Claude Code decision](docs/project.md#claude-code-package-2026-10-15), [install guide](docs/cross-host.md#claude-code).
- Scope: Install the published marketplace into a disposable Claude Code configuration with a configured account, run `/hermes-toolset:plan-with-me questions only: ask one question about this project` in a disposable repository, and confirm the model asks one question and edits nothing.
- Acceptance: The namespaced command loads the adapter, follows the host contract and leaves the repository unchanged; the result is recorded with the Claude Code version.
- Checks: Session transcript or output plus `git status` of the disposable repository.
- Dependencies: TOOLSET-065.
- Environment prerequisite: A Claude Code account authorized for a short model run; the plugin pushed to the published repository.
- Exclusions: No real user repositories, settings or credentials changed.


### TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection

- [ ] TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection
- Status: open
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md), [check_receipt.py](skills/autowork/scripts/check_receipt.py), [receipt tests](skills/autowork/scripts/test_check_receipt.py), [delivery tests](skills/autowork/scripts/test_delivery_state.py).
- Scope: In `check_receipt.runtime()`, memoize the `packages` list and `executable_sha256` per process, keyed by a cheap stamp: for packages, the `(path, st_mtime_ns, st_ino)` of every existing `sys.path` directory (installing, removing or upgrading a distribution adds or removes a `*.dist-info`/`*.egg-info` entry and changes its directory's mtime); for the executable, `(st_dev, st_ino, st_size, st_mtime_ns)` of `sys.executable`. Return the same receipt fields and values as today. Measured before (`376f7ed`): `test_delivery_state.py` 23 tests, about 45 s of call time in a normal run; profile 42 s of 110 s in package metadata and 7 s in executable hashing.
- Acceptance: Receipt contents are unchanged for an unchanged environment; a distribution directory added to a `sys.path` entry between the before and after `runtime()` calls is still reported as in-check drift (new regression test); replacing the executable file changes its hash; `test_check_receipt.py` and `test_delivery_state.py` pass; time for those two modules and for the Autowork directory is measured before and after on the same machine (3 runs each) and recorded.
- Checks: `cd skills/autowork/scripts && python3 -m unittest test_check_receipt test_delivery_state`; the new drift regression; `python3 scripts/check.py`; `python3 scripts/check.py --jobs 1` with `/usr/bin/time` 3 times; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to receipt schema, reuse rules or drift semantics; no caching across processes or on disk; no push.

### TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups

- [ ] TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups
- Status: open
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Scope: In a scratch directory, rerun per-test coverage with subprocess measurement (coverage.py `COVERAGE_PROCESS_START` with a scratch `sitecustomize.py` or `.pth`, `parallel = True`, then `coverage combine`), so the 493 tests without records gain them. Recompute identical and strict-subset groups. Read every group of 3 or more and every subset case among the 30 slowest tests; classify each as distinct contract, parametrize candidate or removal candidate under the protocol's Keep rules. Add the subprocess-coverage recipe to the protocol's "Measure first" section. Record results in the audit section and up to three follow-up tasks with exact tests and measured before values.
- Acceptance: Per-test records exist for at least 1,150 of the 1,253 tests or the shortfall is explained; every group read has a recorded classification with its reason; removal candidates name the remaining test that covers their behavior; no test or source file outside the protocol changes.
- Checks: `python3 skills/docs-sync/scripts/goals.py validate .`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --stat`; `git diff --check`.
- Dependencies: TOOLSET-068.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No test removal or consolidation in this task; no repository dependency on coverage plugins; no push.

### TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22

- [ ] TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22
- Status: open
- Goal: OMH-TRIM — Keep the OMH skills profiles use and drop the rest from every prompt.
- Sources: [plan](docs/project.md#omh-catalog-trim-2026-10-15), [OMH installer](install-omh.py), [bundle defaults](plugins/defaults.json).
- Scope: On Hermes 0.22.0, loading OMH 3.0.0 logs "Plugin 'omh' skipped: requires hermes >=0.21.1,<0.22.0, running 0.22.0", and `hermes memory status` in a profile whose `memory.provider` is `omh` reports the plugin as not installed, so OMH memory is likely inactive fleet-wide. Confirm across profiles, find the OMH release or pin that supports Hermes 0.22, and update `plugins/defaults.json`'s pinned `omh.source` (or document the incompatibility and the safe interim provider) without changing memory stores.
- Acceptance: `hermes memory status` shows the OMH plugin installed and available in an OMH profile, or the incompatibility and its interim handling are recorded; OMH stores and existing memories are untouched; the trim's keep list still matches the new release's skill names.
- Checks: `hermes memory status` and `omh doctor --json` in one profile before and after; `python3 scripts/check.py`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No memory-store migration or deletion; no provider switch without the owner.

### TOOLSET-084 — Qualify the gentler update rollout live

- [ ] TOOLSET-084 — Qualify the gentler update rollout live
- Status: open
- Goal: GENTLE-UPDATE — Roll out updates without forcing gateway restarts.
- Sources: [rollout findings](docs/project.md#gentler-update-rollout-2026-10-15), [update guide](docs/installation.md#update-all-profiles), [linked profiles](docs/installation.md#linked-profiles-and-pinned-clones).
- Scope: After the user publishes TOOLSET-075..079 and asks for an update, run `hermes toolset update` and confirm from the receipt and gateway log that the restart was requested only with no chat turn in flight (or deferred and later completed), that `/toolset update status` shows the new gateway PID and menu resends, and that a second update during the first reports `busy`. With the user's OK, pin one linked profile and confirm it loads the clone after the next restart.
- Acceptance: A live receipt records `gateway_restart: completed` with `gateway_restart_result`, or a deferred restart that later completed; no forced drain appears in the gateway log for that restart; any pinned profile runs the same revision as before.
- Checks: `/toolset update status full`; the gateway log around the restart; `git -C PROFILE/plugins/hermes-toolset rev-parse HEAD` for a pinned profile.
- Dependencies: TOOLSET-079.
- Ownership: Toolset coordinator; live steps need the user's request.
- Exclusions: No push, update, restart or pinning without the user's request.

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass; executed <code>python3 scripts/check.py (411/572/201/8 offline tests passed, includes test_every_codex_adapter_is_explicit_only) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | met | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass; executed <code>uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p test_goals.py / test_milestone_focus.py / test_goal_concurrency.py (all OK) plus malformed-source CLI probe on 5db9ccf; offline only</code> → pass | — |
| OMH-TRIM: Keep the OMH skills profiles use and drop the rest from every prompt | unmet | executed <code>TOOLSET-080/081: python3 scripts/check.py passed; one-profile qualification cut OMH skill-index entries from 12,349 to 3,522 characters with code-review and verification-gate loading and omh doctor unchanged; fleet rollout 101 managed entries in each of 9 OMH profiles</code> → pass | TOOLSET-082 |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass | — |
| TEST-SUITE: Optimize test suites without losing defect detection | unmet | — | TOOLSET-072, TOOLSET-073 |
| PRIORITY: Make TODO.md order the enforced human priority | unmet | — | TOOLSET-029 |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | executed <code>Shared TOOLSET-017/018/019 implementation integrated eb72be6; independent review findings repaired with failing-then-passing regressions; final Python 3.12 scripts/check.py passed 318/470/139/8 tests, two skips/eight excluded. Native recovery, deployment and model qualification remain incomplete.</code> → pass; executed <code>TOOLSET-015 reviewed 16a750ce: seven disposable real-Git regressions, Bash syntax and whitespace passed; coordinator integration candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 263/448/139/8 offline tests, 2 skipped and 8 excluded; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-016: exact 9b894fd same-card review approved; integration b470c68 Python 3.12 scripts/check.py passed 283/448/139/8 offline tests (2 skipped, 8 excluded), bash -n and git diff --check passed; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-020: exact 5e05e6b native independent review approved; integration-candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 319/475/139/8 offline tests, two skips/eight excluded; local main integration preservation ZERO_CHANGED; native/model/live qualification unrun</code> → pass; executed <code>TOOLSET-021 exact ab12f821 native independent review run398 approved; integration 49739eff: env -u HERMES_KANBAN_DB uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 332/495/139/8 offline tests, 3 skips, 8 excluded; git diff --check HEAD^1 passed; native/model/live/startup unqualified</code> → pass; executed <code>TOOLSET-022 exact 816678e3 native independent review run406 approved; integration 5f49a2e0: Python 3.12 scripts/check.py on frozen integration candidate passed 332/510/139/8 offline tests, three skips/eight native-model-integration modules excluded; whitespace passed; native/model/live/startup unqualified</code> → pass | TOOLSET-003, TOOLSET-019 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass; executed <code>python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | executed <code>Reviewed fef4241; integration e2a0838: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (252/448/135/8 offline tests; 2 skipped; 8 live/integration modules excluded); native timing remains TOOLSET-013</code> → pass | TOOLSET-013 |
| DOCS-COMPLETENESS: Make core-document completeness and drift machine-checkable | met | executed <code>python3 scripts/check.py (403/571/197/8 offline tests passed, 1 skipped, 8 modules excluded; includes test_docs_manifest, test_docs_stale, test_docs_profiles; offline only)</code> → pass | — |
| UI-TASTE: Ship Uizze's UI Taste as a vendored bundled skill | met | executed <code>python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| SKILL-REVIEW: Fix review findings in the newly vendored UI skills | unmet | — | TOOLSET-064 |
| CLAUDE-CODE: Install the portable workflows in Claude Code | unmet | — | TOOLSET-066 |
| GENTLE-UPDATE: Roll out updates without forcing gateway restarts | unmet | executed <code>TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084)</code> → pass | TOOLSET-084 |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |

<!-- goals:coverage:end -->
