# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Autowork. Scope and current architecture: [project contract](docs/project.md).
[goals.json](goals.json) indexes the remaining work below; verified completed
tasks move to the archive automatically. Ledger eligibility is not worker
admission or live qualification.

## Now

### MAIN-001-38 — Restore the offline gate after the queue reset and integration diagnostic change

- [ ] MAIN-001-38 — Restore the offline gate after the queue reset and integration diagnostic change
- Planning: Keep one main-repair task as requested. Hot-file scope is limited to the status assertions/docs and the integration regression with its owning implementation/tests; there is no other open task to order behind. No unrelated updater, fleet/TUI or dispatch change is prescribed by these failures.
- Next action: Run the focused Checks; reconcile reset-ledger assumptions and the integration fixture with current accepted behavior, investigate cleanup behind the cgroup follow-on error, and fix any demonstrated local defect without undoing the queue reset or writer protections.
- Failing tests: `test_project_status.ProjectStatusTests.test_live_qualification_stays_open_and_separate`; `test_project_status.ProjectStatusTests.test_reviewed_delivery_is_current_not_pending`; `test_task_execution.RecoveryTests.test_runner_jobs_do_not_block_integration_but_outside_scratch_sessions_do`.
- Evidence: `<git-common-dir>/autowork-execution/main-evidence/868ae56442381e511bb83532883b2c9be466f9f5/` (`main_check.json`, `main-check.log`, `main-check.exit`, `main-check-reruns.log`, `flaky_history.json`), checked `868ae56442381e511bb83532883b2c9be466f9f5`, last green `616cb7f335056db1a7a31e281d22c80d3e418d62`. Full check exit 1; all three isolated reruns exit 1; no current flaky classification. Since-green commits: `868ae564`, `0cc75087`, `5729fd49`, `09d65eaa`, `6ab2c115`, `892d4311`, `e92b490f`; messages and source changes are recorded in the accepted repair.
- Ownership: Autowork worker; independent review and serialized integration by the coordinator.
- Touches: tests/test_project_status.py, docs/project.md, skills/autowork/scripts/test_task_execution.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py
- Payoff: Restore the safe offline gate while preserving the owner queue reset, historical delivery evidence and outside-writer protection.
- Sources: [Accepted repair](docs/tasks/main-868ae564-offline-repair.md#accepted-repair); owner queue-reset commit `0cc75087`; integration-diagnostic commit `5729fd49`.
- Short: Restore the red main offline gate
- Status: open
- Goal: RELIABILITY-2026-10
- Scope: Repair the three reproducible offline failures at 868ae564 without undoing the owner queue reset or the file-specific writer diagnostic; preserve live qualification boundaries.
- Acceptance: `test_project_status.ProjectStatusTests.test_live_qualification_stays_open_and_separate`, `test_project_status.ProjectStatusTests.test_reviewed_delivery_is_current_not_pending`, `test_task_execution.RecoveryTests.test_runner_jobs_do_not_block_integration_but_outside_scratch_sessions_do` and the full offline check pass with regressions covering an intentionally reset ledger and file-specific integration holds; no deleted task is restored or live acceptance fabricated.
- Checks: `python3 scripts/check.py tests/test_project_status.py skills/autowork/scripts/test_task_execution.py skills/autowork/scripts/test_parallel_integrate.py`; `python3 scripts/check.py`
- Dependencies: None.

## Next

## Needs decision

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | partial | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | MAIN-001-38 |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass; executed <code>TOOLSET-116-fc: python3 scripts/check.py passed 575/715/217/8 tests (one skip/eight excluded modules); all 12 focused README-audit tests and exact-source independent review approved; mixed-text single-line examples and adjacent-image preservation verified offline</code> → pass | — |
| PRIORITY: Make TODO.md order the enforced human priority | met | Executed check: pass ([TOOLSET-029](TODO.archive.md#toolset-029)) | — |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass; executed <code>python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| UI-TASTE: Ship Uizze's UI Taste as a vendored bundled skill | met | executed <code>python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| SKILL-REVIEW: Fix review findings in the newly vendored UI skills | met | executed <code>Integrated 9f84355: python3 scripts/check.py passed 558/698/212/8 tests, one skip and eight excluded modules; retained description regression and original zero-warning linter evidence; offline only</code> → pass | — |
| GENTLE-UPDATE: Roll out updates without forcing gateway restarts | met | executed <code>TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084)</code> → pass; executed <code>TOOLSET-084 live 2026-10-15: hermes toolset update at afe1482 requested the restart with no chat turn in flight; /toolset update status showed gateway_restart completed, new PID 553964, menus resent 9/9; concurrent --check returned busy (exit 3) without touching the first receipt; earlier deferred restart waited for a chat turn that ended on its own (no forced chat drain); 7 linked profiles pinned to clean clones that only updates advance</code> → pass | — |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |

<!-- goals:coverage:end -->
