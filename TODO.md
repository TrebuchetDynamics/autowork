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
- Historical migration receipt: partial (2026-10-14): 6 of 9 migrated and committed locally with unchanged eligible order: hermes-toolset, sierra, landing-golf, india, juliet and golf (the last four after a separate checkpoint commit of their pending queue edits). Not migrated: charlie (a staged 9-file docs batch includes the queue files), bravo (live in-progress claim and active session) and kilo (no commits). All matching jobs were already paused and stay paused.
- Goal: PRIORITY — Make TODO.md order the enforced human priority.
- Sources: [accepted priority plan](docs/project.md#todo-owned-task-priority), [accepted rollout](docs/project.md#rollout), [bootstrap contract](docs/project.md#reconciliation-and-bootstrap).
- Scope: For each fleet repository with goals.json: dry-run bootstrap and report the full before/after order (including bravo's deeper difference), preserve stopped/paused jobs, lock and verify unchanged inputs, migrate, validate, compare the next pick before and after, and commit locally per repository within the existing migration authority. The later stop-all instruction supersedes automatic resumption.
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


### TOOLSET-068 — Audit this repository's test suite and record bounded follow-ups

- [ ] TOOLSET-068 — Audit this repository's test suite and record bounded follow-ups
- Status: open
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [plan](docs/project.md#test-suite-optimization-method-2026-10-15), [check runner](scripts/check.py), [the protocol from TOOLSET-067](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Scope: Apply the protocol in audit mode to the offline inventory of `python3 scripts/check.py` (excluded native modules stay out). Measure in a scratch directory: per-directory wall time (3 runs), the 30 slowest tests, line and branch coverage of the toolset's Python sources with per-test contexts, and groups of tests whose covered-line sets are identical or strict subsets. Mutation testing is optional: if used, install the tool only in a disposable virtual environment outside the repository and sample the modules with the most redundancy candidates. Inspect the top candidates by reading the tests. Record the baseline and findings in the plan section of docs/project.md, and add up to five follow-up tasks in TODO.md under the TEST-SUITE goal, each with its measured before values, the exact tests involved, the protocol's acceptance template and its checks. Start with `test_delivery_state.py` setup cost (about 40 s of the slowest 15 tests).
- Acceptance: The plan section records the measured baseline (counts, times, coverage percentages, method and commit); each follow-up task names concrete tests and measurable before values; no test or source file changes in this task; candidates without evidence are listed as unverified, not as tasks.
- Checks: `python3 skills/docs-sync/scripts/goals.py validate .`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --stat` shows only docs/project.md, TODO.md and goals.json; `git diff --check`.
- Dependencies: TOOLSET-067.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No test deletion, consolidation or source edit; no repository dependency changes; no push.

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass; executed <code>python3 scripts/check.py (411/572/201/8 offline tests passed, includes test_every_codex_adapter_is_explicit_only) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | met | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass; executed <code>uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p test_goals.py / test_milestone_focus.py / test_goal_concurrency.py (all OK) plus malformed-source CLI probe on 5db9ccf; offline only</code> → pass | — |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass | — |
| TEST-SUITE: Optimize test suites without losing defect detection | unmet | — | TOOLSET-068 |
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
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |

<!-- goals:coverage:end -->
