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

### TOOLSET-099-87 — Run as many independent tasks at once as possible

- [ ] TOOLSET-099-87 — Run as many independent tasks at once as possible
- Status: open; offline implementation complete, awaiting archive after live use on a fleet repository (TOOLSET-096-7e).
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [usage](docs/cross-host.md#run-autowork-continuously), [engine](skills/autowork/references/parallel-workers.md).
- Touches: scripts/pi-autowork.sh, scripts/pi_autowork_touches.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/references/parallel-workers.md, tests/test_pi_autowork.py, docs/cross-host.md
- Scope: Owner direction: run every task that is independent and achievable at once. `--workers` 1-8, default 8 (engine limit); 3 GB free memory per worker. A read-only Pi pass proposes `Touches:` for runnable tasks lacking it (`scripts/pi_autowork_touches.py` records them in the TODO's own field style); `NONE` keeps a task solo for 24 h. Idle sessions merge the main branch. Engine fix: a task without `Touches:` is no longer held at integration for changing its own files. A scope-held first commit whose retry made no commit is re-verified once (`READOPTED`), recovering work held by the old rule.
- Acceptance: Tasks without `Touches:` gain proposed paths and run in parallel; an unboundable task runs alone and is not re-asked; solo tasks integrate.
- Checks: `python3 -m unittest tests/test_pi_autowork.py` (34 pass); engine tests in `skills/autowork/scripts`; `shellcheck scripts/pi-autowork.sh`; `python3 scripts/check.py`.
- Dependencies: TOOLSET-098-4c.
- Ownership: Toolset coordinator under the owner's request.
- Exclusions: No push by the runner; no direct edits in fleet repositories.

## Next

### TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index

- [ ] TOOLSET-064 — Give bundled skills trigger-first descriptions within Hermes' 60-character index
- Status: open
- Goal: SKILL-REVIEW — Fix review findings in the newly vendored UI skills.
- Sources: [review findings](docs/project.md#new-skill-review-2026-10-15), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Rewrite toolset-owned `description` fields over 60 characters (autoresearch, autowork, beautify-github-readme, cron-autowork, engineering, lgtm, plan-for-me, plan-with-me) to one trigger-first sentence; vendored Impeccable stays unchanged.
- Acceptance: Hermes' skill linter reports no `description-length` warning for toolset-owned skills, and a test enforces the limit.
- Checks: A regression over `skills/*/SKILL.md`, then `python3 scripts/check.py`.
- Dependencies: None.
- Exclusions: No vendored-file edits.
- Candidate: `autowork/TOOLSET-064` at `2e3ef49` combines the retained reviewed descriptions with main `7882845` and the reviewed TOOLSET-097-41 repair. The conflict-free refresh preserves every owned skill body against that pinned main. The description regression and all 40 Pi tests pass; the fresh full offline gate passes 556/689/212/8 tests across four directories (one skipped test; eight excluded modules). Bash syntax, docs/index validation and whitespace checks pass. The earlier Hermes linter result remains zero description-length warnings for the unchanged descriptions; no new independent review is claimed. The first combined gate failure remains retained, not relabeled passed.
- Planner's call: Preserve the reviewed combined implementation and refresh it against pinned main in the idle isolated candidate rather than overlapping canonical writers. The refresh merged without conflicts; the original independent approvals remain historical evidence, and this occurrence adds fresh offline qualification, not a new review. Main still matched `7882845` at final admission, but two active canonical sessions prevent integration. Keep both tasks open.
- Next action: When canonical writers clear, reconcile this combined candidate with fresh main, rerun changed-input checks and review any new conflicts, integrate locally, then close and archive verified tasks. No push or deployment.

### TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22

- [ ] TOOLSET-082 — Restore the OMH memory plugin on Hermes 0.22
- Status: open
- Goal: OMH-TRIM — Keep the OMH skills profiles use and drop the rest from every prompt.
- Sources: [plan](docs/project.md#omh-catalog-trim-2026-10-15), [OMH installer](install-omh.py), [bundle defaults](plugins/defaults.json), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: On Hermes 0.22.0, loading OMH 3.0.0 logs "Plugin 'omh' skipped: requires hermes >=0.21.1,<0.22.0, running 0.22.0", and `hermes memory status` in a profile whose `memory.provider` is `omh` reports the plugin as not installed, so OMH memory is likely inactive fleet-wide. Confirm across profiles, find the OMH release or pin that supports Hermes 0.22, and update `plugins/defaults.json`'s pinned `omh.source` (or document the incompatibility and the safe interim provider) without changing memory stores.
- Acceptance: `plugins/defaults.json` pins an OMH release whose plugin manifest admits Hermes 0.22 and whose skill names cover the trim's keep list; a fresh-install preview uses that pin; docs/memory.md records the incompatibility and the interim handling for profiles still on the old release; OMH stores and existing memories are untouched. Refreshing already installed profiles is TOOLSET-098-5d.
- Checks: `python3 -m unittest discover -s tests -p test_install_omh.py`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No memory-store migration or deletion; no provider switch without the owner.
- Candidate: `autowork/TOOLSET-082` (c4644bb) pins official OMH v3.0.2 (manifest `>=0.21.1`), maps all 41 kept names, adds offline tests and interim guidance; the cron reported independent review approval on 2026-10-15.
- Planner's call (2026-10-15 replan): split the live refresh of installed profiles into TOOLSET-098-5d so the reviewed offline pin can close; the live checks moved there unchanged.
- Next action: Merge the candidate onto current main, rerun the checks above, close.

### TOOLSET-097-41 — Report the correct Hermes profile from nested installation paths

- [ ] TOOLSET-097-41 — Report the correct Hermes profile from nested installation paths
- Status: open
- Goal: PI-RUNNER
- Sources: [accepted repository scope](docs/project.md#accepted-requirements), [Pi runner](scripts/pi-autowork.sh), [offline regressions](tests/test_pi_autowork.py), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Repair the Hermes coexistence diagnostic when the installation root itself contains a profiles directory; derive the label relative to the selected root, not the first matching ancestor.
- Acceptance: Named and default-profile jobs display their actual profile below a nested installation root; active matching jobs still refuse execution and paused jobs stay excluded.
- Checks: `python3 -m unittest discover -s tests -p test_pi_autowork.py`; `python3 scripts/check.py`; `bash -n scripts/pi-autowork.sh`; `git diff --check`.
- Dependencies: None.
- Ownership: Next Autowork coordinator. Before starting, check the `pi-par` worktree under `.claude/worktrees/`, which held uncommitted edits to both touched files on 2026-10-15; adopt or wait for that writer instead of duplicating it.
- Touches: scripts/pi-autowork.sh, tests/test_pi_autowork.py
- Candidate: `autowork/pi-profile-reconcile` adopts only the implementation and regression from retained candidate `9625a6e` onto `73c6f7e`, preserving the newer parallel runner and service/worktree fixes. All 33 Pi tests, the full offline gate (four directories), Bash syntax, goals validation and whitespace checks passed; independent read-only review approved the two-file diff. Test subprocess/stream ResourceWarnings remain, and one offline test was skipped.
- Planner's call: Canonical writers prevent integration, not verification in an isolated candidate. Keep this task open until the reviewed candidate is integrated; do not import the old candidate's stale archive/index changes. Next action: integrate this branch only after the canonical writer gate clears, recheck changed inputs, then archive this task.
- Current evidence: Found by the toolset cron on 2026-10-15: the full offline gate fails one Pi test when the checkout path contains `/profiles/` (as in profile cron runs) and passes elsewhere.
- Exclusions: No job mutation, provider execution, push or deployment; no change to coexistence refusal policy.

### TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection

- [ ] TOOLSET-072 — Cache the check receipt runtime inventory without losing drift detection
- Status: open
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md), [check_receipt.py](skills/autowork/scripts/check_receipt.py), [receipt tests](skills/autowork/scripts/test_check_receipt.py), [delivery tests](skills/autowork/scripts/test_delivery_state.py), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: In `check_receipt.runtime()`, memoize the `packages` list and `executable_sha256` per process, keyed by a cheap stamp: for packages, the `(path, st_mtime_ns, st_ino)` of every existing `sys.path` directory (installing, removing or upgrading a distribution adds or removes a `*.dist-info`/`*.egg-info` entry and changes its directory's mtime); for the executable, `(st_dev, st_ino, st_size, st_mtime_ns)` of `sys.executable`. Return the same receipt fields and values as today. Measured before (`376f7ed`): `test_delivery_state.py` 23 tests, about 45 s of call time in a normal run; profile 42 s of 110 s in package metadata and 7 s in executable hashing.
- Acceptance: Receipt contents are unchanged for an unchanged environment; a distribution directory added to a `sys.path` entry between the before and after `runtime()` calls is still reported as in-check drift (new regression test); replacing the executable file changes its hash; `test_check_receipt.py` and `test_delivery_state.py` pass; time for those two modules and for the Autowork directory is measured before and after on the same machine (3 runs each) and recorded.
- Checks: `cd skills/autowork/scripts && python3 -m unittest test_check_receipt test_delivery_state`; the new drift regression; `python3 scripts/check.py`; `python3 scripts/check.py --jobs 1` with `/usr/bin/time` 3 times; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No change to receipt schema, reuse rules or drift semantics; no caching across processes or on disk; no push.
- Next action: Start from current main. The existing `autowork/TOOLSET-072` worktree holds no commits for this task (it points at an older main) and is not a candidate.

### TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups

- [ ] TOOLSET-073 — Measure subprocess coverage, then review identical and subset test groups
- Status: open
- Goal: TEST-SUITE — Optimize test suites without losing defect detection.
- Sources: [audit](docs/project.md#baseline-audit-toolset-068-2026-10-15), [protocol](skills/engineering/local/test-suite-optimization/PROTOCOL.md).
- Scope: In a scratch directory, rerun per-test coverage with subprocess measurement (coverage.py `COVERAGE_PROCESS_START` with a scratch `sitecustomize.py` or `.pth`, `parallel = True`, then `coverage combine`), so the 493 tests without records gain them. Recompute identical and strict-subset groups. Read every group of 3 or more and every subset case among the 30 slowest tests; classify each as distinct contract, parametrize candidate or removal candidate under the protocol's Keep rules. Add the subprocess-coverage recipe to the protocol's "Measure first" section. Record results in the audit section and up to three follow-up tasks with exact tests and measured before values.
- Acceptance: Per-test records exist for at least 1,150 of the 1,253 tests or the shortfall is explained; every group read has a recorded classification with its reason; removal candidates name the remaining test that covers their behavior; no test or source file outside the protocol changes.
- Checks: `python3 skills/docs-sync/scripts/goals.py validate .`; `python3 skills/docs-sync/scripts/docs.py check .`; `git diff --stat`; `git diff --check`.
- Dependencies: None.
- Prior work: TOOLSET-068 (done, archived).
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No test removal or consolidation in this task; no repository dependency on coverage plugins; no push.

### TOOLSET-066 — Qualify the Claude Code plugin with a live questions-only workflow

- [ ] TOOLSET-066 — Qualify the Claude Code plugin with a live questions-only workflow
- Status: open; live qualification not run.
- Goal: CLAUDE-CODE — Install the portable workflows in Claude Code.
- Sources: [Claude Code decision](docs/project.md#claude-code-package-2026-10-15), [install guide](docs/cross-host.md#claude-code), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Clone the published repository at `origin/main` into a scratch directory and load it for one session with `claude --plugin-dir <clone>` (no marketplace or settings change), run `/hermes-toolset:plan-with-me questions only: ask one question about this project` in a disposable repository, and confirm the model asks one question and edits nothing.
- Acceptance: The namespaced command loads the adapter, follows the host contract and leaves the repository unchanged; the result is recorded with the Claude Code version.
- Checks: Session transcript or output plus `git status` of the disposable repository.
- Dependencies: TOOLSET-065.
- Environment prerequisite: Owner approval for one short model run on their Claude Code account (Claude Code 2.1.300 is installed; the plugin is published).
- Planner's call (2026-10-15 replan): `--plugin-dir` on a clean clone of the published commit replaces a marketplace install into a disposable configuration, which would need an interactive login; it loads the same files for one session and changes no settings.
- Exclusions: No real user repositories, settings or credentials changed.

### TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow

- [ ] TOOLSET-003 — Qualify automatic planning recovery with a real bounded workflow
- Status: open; live qualification not run.
- Goal: RECOVERY — Prove recovery reaches execution, not just a planning receipt.
- Sources: [accepted scope](docs/project.md#accepted-requirements), [recovery contract](skills/autowork/references/backlog-planning.md), [existing regressions](skills/autowork/scripts/test_backlog_plan.py), [verification limits](docs/testing.md), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: In a disposable repository, reproduce missing prerequisites and candidate drift. Observe automatic planning, TODO update and retry of the eligible original slice; repeat unchanged inputs once to verify decision reuse.
- Acceptance: No extra user planner command; original exclusions and ownership survive; execution is reported separately from planning.
- Checks: Run focused recovery regressions and one bounded isolated model/native smoke journey covering both cases. Retain exact source, task, commands/results, commit or none, and remaining blocker. Offline tests alone cannot close this task.
- Exclusions: No production messages/deployment, real user repositories, forbidden prerequisite commits, writer takeover or fabricated completion.
- Dependencies: None.
- Environment prerequisite: An installed host CLI with model access, a run budget, and the owner observing the run.
- Ownership: Next authorized coordinator; no active claim recorded.
- Current evidence: The shipped containment backend admits only local fixture executables and explicitly excludes provider/network dispatch. Its synthetic spending controller is not a model spending limit. No qualifying model journey was run.
- Next action: Supply an isolated model endpoint with externally enforced spend and descendant limits, then execute the bounded recovery journey; existing offline fixtures cannot replace it.
- Owner decision (2026-10-15): run the journey like TOOLSET-091-00, as an owner-observed host session (`hermes chat --oneshot --run-budget S` or `claude -p`) on a disposable repository, with the host's run budget as the bound instead of an externally capped endpoint.

### TOOLSET-098-5d — Refresh the installed OMH plugin in each OMH profile to the Hermes 0.22 release

- [ ] TOOLSET-098-5d — Refresh the installed OMH plugin in each OMH profile to the Hermes 0.22 release
- Status: open
- Goal: OMH-TRIM
- Sources: [OMH plan](docs/project.md#omh-catalog-trim-2026-10-15), [OMH installer](install-omh.py), TOOLSET-082, [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: List the profiles whose installed OMH plugin requires Hermes <0.22. With the owner's approval, refresh each one's OMH plugin and executable to the release pinned by TOOLSET-082 through the existing installer, with a backup, then rerun `/toolset update` for the affected profiles.
- Acceptance: In each refreshed profile `hermes memory status` shows the OMH plugin installed and available and `omh doctor --json` passes against the same existing store; `hermes plugins enable hermes-toolset` no longer refuses (on 2026-10-15 a newly created profile refused it because its OMH plugin requires Hermes <0.22); stores and memories are untouched; any profile that fails keeps its backup and is reported.
- Checks: `hermes memory status`, `omh doctor --json` and the `/toolset update` per-profile result before and after in each profile.
- Dependencies: TOOLSET-082.
- Environment prerequisite: Owner approval to modify installed plugins in live profiles.
- Ownership: Toolset coordinator with that approval.
- Exclusions: No memory-store migration or deletion, no provider switch, no push.

### TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles

- [ ] TOOLSET-019 — Deploy reviewed local fixes to selected eligible profiles
- Status: in_progress; reviewed scoped local updater is implemented and integrated in eb72be6; selected-profile deployment remains pending.
- Goal: RECOVERY — Deliver reviewed repairs without remote fetches or fleet-wide side effects.
- Sources: [accepted recovery plan](docs/project.md#end-to-end-original-task-recovery), [updater](update_bundle.py), [updater tests](tests/test_update_bundle.py), [installation](docs/installation.md), [2026-10-15 replan](docs/project.md#backlog-replan-2026-10-15).
- Scope: Extend the existing updater with explicit selected profiles and immutable reviewed local source, native security admission, preflight/staging/backups, installed hash readback and resumable per-profile results. Preserve unselected consumers of shared sources and pinned runtimes.
- Acceptance: No implicit fetch, profile expansion, scan override, worker restart or configuration/schedule change. Active affected consumers defer; independent eligible targets proceed. Drift/source races refuse before unsafe writes. Retry reuses the same source and backups, unchanged deployment is a no-op, and installed bytes/registrations are verified without claiming product recovery.
- Checks: 52 real-Git/fake-native updater fixtures passed. Independent review found shared-board ownership and interrupted-clone defects; both reproduced and passed after repair. The combined 318/470/139/8 offline gate passed. Native scoped preflight ran; installation and live registration remain unverified.
- Dependencies: None.
- Ownership: Shared maintainer for implementation; authorized coordinator for selected-profile deployment.
- Exclusions: No implicit remote publication, dependency overrides, native scanner bypass, global configuration changes or active-runtime rebinding.
- Historical deployment evidence: Preflight against 51d99d6 deferred three selected profiles under the former native-ownership checks and one for a customized `skills/autoresearch/SKILL.md`; their bytes were preserved. That receipt proves no installation. The TODO-first implementation has since retired card-only vetoes; recheck actual consumers and current customizations rather than treating those old deferrals as present blockers.
- Current evidence (2026-10-15): fleet-wide `/toolset update` has since installed every reviewed fix in all profiles (all at 90f164f, finalize readback ready). Only the selected-profile mode (`--profile NAME`) is still unqualified live.
- Next action: Run the reviewed updater once in selected-profile mode for one profile, read back installed hashes and registrations, rerun it to confirm a no-op, and record the receipts. Reuse the reviewed updater; do not repeat its completed implementation or label preflight as deployment.

### TOOLSET-096-7e — Qualify the worktree runner live on a fleet repository

- [ ] TOOLSET-096-7e — Qualify the worktree runner live on a fleet repository
- Status: open
- Goal: PI-RUNNER — Run Autowork continuously through Pi with a model fallback.
- Sources: [usage](docs/cross-host.md#run-autowork-continuously).
- Scope: Run the released runner on a fleet repository alongside its Hermes jobs (owner's choice) until it ends a session, and record what it completed and how the end-of-session merge went.
- Acceptance: `runs.jsonl` and the repository's main branch show completed tasks merged at the end of a session, or a `Merge pending` with the exact reason and the branch kept; no push by the runner; the repository's uncommitted changes untouched.
- Checks: `runs.jsonl`, runner output, `git -C <fleet-repo> log` and `worktree list`.
- Dependencies: TOOLSET-095-48.
- Ownership: Toolset coordinator on the owner's request.
- Exclusions: No push; no change to the repository's Hermes jobs.

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

### TOOLSET-011 — Qualify the updated reporting workflow on the affected profile

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

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass; executed <code>python3 scripts/check.py (411/572/201/8 offline tests passed, includes test_every_codex_adapter_is_explicit_only) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | met | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass; executed <code>uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p test_goals.py / test_milestone_focus.py / test_goal_concurrency.py (all OK) plus malformed-source CLI probe on 5db9ccf; offline only</code> → pass | — |
| OMH-TRIM: Keep the OMH skills profiles use and drop the rest from every prompt | unmet | executed <code>TOOLSET-080/081: python3 scripts/check.py passed; one-profile qualification cut OMH skill-index entries from 12,349 to 3,522 characters with code-review and verification-gate loading and omh doctor unchanged; fleet rollout 101 managed entries in each of 9 OMH profiles</code> → pass | TOOLSET-082, TOOLSET-098-5d |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass | — |
| TEST-SUITE: Optimize test suites without losing defect detection | unmet | — | TOOLSET-072, TOOLSET-073 |
| PRIORITY: Make TODO.md order the enforced human priority | unmet | — | TOOLSET-029 |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | executed <code>Shared TOOLSET-017/018/019 implementation integrated eb72be6; independent review findings repaired with failing-then-passing regressions; final Python 3.12 scripts/check.py passed 318/470/139/8 tests, two skips/eight excluded. Native recovery, deployment and model qualification remain incomplete.</code> → pass; executed <code>TOOLSET-015 reviewed 16a750ce: seven disposable real-Git regressions, Bash syntax and whitespace passed; coordinator integration candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 263/448/139/8 offline tests, 2 skipped and 8 excluded; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-016: exact 9b894fd same-card review approved; integration b470c68 Python 3.12 scripts/check.py passed 283/448/139/8 offline tests (2 skipped, 8 excluded), bash -n and git diff --check passed; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-020: exact 5e05e6b native independent review approved; integration-candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 319/475/139/8 offline tests, two skips/eight excluded; local main integration preservation ZERO_CHANGED; native/model/live qualification unrun</code> → pass; executed <code>TOOLSET-021 exact ab12f821 native independent review run398 approved; integration 49739eff: env -u HERMES_KANBAN_DB uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 332/495/139/8 offline tests, 3 skips, 8 excluded; git diff --check HEAD^1 passed; native/model/live/startup unqualified</code> → pass; executed <code>TOOLSET-022 exact 816678e3 native independent review run406 approved; integration 5f49a2e0: Python 3.12 scripts/check.py on frozen integration candidate passed 332/510/139/8 offline tests, three skips/eight native-model-integration modules excluded; whitespace passed; native/model/live/startup unqualified</code> → pass | TOOLSET-003, TOOLSET-019 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass; executed <code>python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | executed <code>Reviewed fef4241; integration e2a0838: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (252/448/135/8 offline tests; 2 skipped; 8 live/integration modules excluded); native timing remains TOOLSET-013</code> → pass | — |
| DOCS-COMPLETENESS: Make core-document completeness and drift machine-checkable | met | executed <code>python3 scripts/check.py (403/571/197/8 offline tests passed, 1 skipped, 8 modules excluded; includes test_docs_manifest, test_docs_stale, test_docs_profiles; offline only)</code> → pass | — |
| UI-TASTE: Ship Uizze's UI Taste as a vendored bundled skill | met | executed <code>python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| SKILL-REVIEW: Fix review findings in the newly vendored UI skills | unmet | — | TOOLSET-064 |
| CLAUDE-CODE: Install the portable workflows in Claude Code | unmet | — | TOOLSET-066 |
| GENTLE-UPDATE: Roll out updates without forcing gateway restarts | met | executed <code>TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084)</code> → pass; executed <code>TOOLSET-084 live 2026-10-15: hermes toolset update at afe1482 requested the restart with no chat turn in flight; /toolset update status showed gateway_restart completed, new PID 553964, menus resent 9/9; concurrent --check returned busy (exit 3) without touching the first receipt; earlier deferred restart waited for a chat turn that ended on its own (no forced chat drain); 7 linked profiles pinned to clean clones that only updates advance</code> → pass | — |
| PARALLEL: Run independent Autowork tasks in parallel workers with one coordinator | met | executed <code>TOOLSET-091-00 live 2026-10-15: Pi 1.2.0 workers (gpt-6.1-sol) via pi-autowork.sh on a disposable repo: 2 overlapping workers, sequential integration, C after A, combined check pass, no push, 158 s vs 240 s sequential; SIGKILLed coordinator restart adopted live workers without duplicates. Codex 0.162.1 workers cannot commit in the workspace-write sandbox (sequential fallback). Hermes workers not run by owner decision.</code> → pass | — |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |
| PI-RUNNER: Run Autowork continuously through Pi with a model fallback | partial | executed <code>TOOLSET-093-01: python3 -m unittest tests/test_pi_autowork.py (20 fake-Pi tests) and shellcheck passed; live --once with openai-codex/gpt-6.1-sol completed one task in a disposable repository; fallback not qualified live</code> → pass; executed <code>TOOLSET-094-65 live 2026-10-15: disposable repository, 5 tasks each completed once; real primary credential failure fell back to openrouter/deepseek/deepseek-v4.1-flash, which resumed and completed the task in the same session; SIGINT mid-task resumed in the same session; no push; tests/test_pi_autowork.py 21 passed</code> → pass | TOOLSET-096-7e, TOOLSET-097-41 |

<!-- goals:coverage:end -->
