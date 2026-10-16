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
- Planner's call (2026-10-16): Skip the excluded live/model operation in this occurrence; its remaining fleet qualification is already separated under TOOLSET-096-7e. Preserve both open acceptances. The offline TOOLSET-072/073 work and TOOLSET-102-ea's measured fixture follow-up are archived. No new live authority is inferred.

## Next

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

## Needs decision

### TOOLSET-101-f6 — Deploy reviewed fleet-audit helpers through the native scanned updater

- [ ] TOOLSET-101-f6 — Deploy reviewed fleet-audit helpers through the native scanned updater
- Status: open
- Goal: RECOVERY
- Sources: [maintenance contract](skills/autowork/references/profile-feedback.md), [scoped updater](update_bundle_native.py), [deployment boundary](skills/autowork/references/owner-cycle.md#cross-profile-recovery-and-deployment), [verification](docs/testing.md).
- Scope: Adopt the reviewed confidentiality, output-identity and per-job execution-evidence repairs into the dynamically discovered managed installations through the supported profile-scoped scanned updater. Read actual helper paths and owner/session activity before publication; retain source bindings, existing owner state and all pauses.
- Acceptance: Every authorized installed target resolves the reviewed helper bytes; same read-only response/execution consumer passes; existing schedules, workers, profile settings and history are preserved. Installed adoption is not product recovery or live qualification.
- Checks: Native scoped updater readback; installed helper hashes; synthetic credential-tail and per-job execution replays; exact existing-job settings before/after. Do not trigger schedules or duplicate collector/consultation runs.
- Dependencies: AUDIT-QUOTED-SECRET, TOOLSET-092-18, TOOLSET-100-78.
- Ownership: Shared-source maintenance coordinator after the native scan gate is resolved through its supported approval path.
- Touches: update_bundle_native.py, skills/autowork/scripts/audit_profiles.py, scripts/profile-consult.py
- Resources: exclusive managed installation publication; preserve active coordinators.
- External gate: Retained native install was BLOCKED by its community-source caution verdict. No scan override approval is present. Repeated unchanged scans, force flags, manual copies, symlink replacement and source repins are not authorized recovery paths.
- Planner's call: Split only installed adoption from the completed source fixes and retain this acceptance open. Preserve the prior scan refusal. Continue independent authorized source work rather than replaying the refusal; no deployment or product acceptance follows from local integration.
- Current evidence: Source merge 4b79912 is independently approved and passes the complete Python 3.12 offline gate (562/709/212/8 tests, one skip, eight excluded modules). Canonical consumer restores twelve paused-development execution records while retaining twelve sync records. Installed helper copies remain at the previously observed revision and still disclose synthetic header tails.
- Exclusions: No push, Agent edits, scan bypass, owner config/memory changes, product/live/device operations, worker replacement or schedule activation.

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| PORTABLE: Align portable workflow discovery | met | executed <code>Integration af8e567: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests -p test_portable_package.py; node --test tests/portable_pi.test.mjs; uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py; exact 5e5d043 independent review and isolated Codex 0.162.1/Pi 1.2.0 discovery verified</code> → pass; executed <code>python3 scripts/check.py (411/572/201/8 offline tests passed, includes test_every_codex_adapter_is_explicit_only) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | met | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| BACKLOG: Provide repeatable first-time backlog initialization | met | executed <code>Reviewed 7f07b182; integrated 73a8efc: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (247/437/135/8 offline tests; 2 skipped; native/model excluded)</code> → pass; executed <code>uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s skills/docs-sync/scripts -p test_goals.py / test_milestone_focus.py / test_goal_concurrency.py (all OK) plus malformed-source CLI probe on 5db9ccf; offline only</code> → pass | — |
| OMH-TRIM: Keep the OMH skills profiles use and drop the rest from every prompt | unmet | executed <code>Integrated 9f84355: python3 scripts/check.py passed, including OMH pin/keep-list fixtures; live installed-profile refresh TOOLSET-098-5d remains open</code> → pass; executed <code>TOOLSET-080/081: python3 scripts/check.py passed; one-profile qualification cut OMH skill-index entries from 12,349 to 3,522 characters with code-review and verification-gate loading and omh doctor unchanged; fleet rollout 101 managed entries in each of 9 OMH profiles</code> → pass | TOOLSET-098-5d |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass | — |
| TEST-SUITE: Optimize test suites without losing defect detection | met | executed <code>TOOLSET-072: 20cbcc5 vs 9f84355, /usr/bin/time python3 scripts/check.py --jobs 1, three interleaved runs each; all six passed 558/689-or-698/212/8 tests, one skip/eight excluded; serial wall medians 468.81 to 420.92 s, Autowork unittest medians 189.849 to 140.612 s; recorded inputs match commits; offline only</code> → pass; executed <code>TOOLSET-073 at de0f3ac: scratch subprocess coverage 1278/1491 contexts; 31 large groups and five slow subsets assertion-reviewed; normal python3 scripts/check.py passed 562/709/212/8, one skip/eight excluded; instrumented cache failure retained and focused harness-repair rerun passed; docs/test-suite-audit.md; offline only</code> → pass; executed <code>TOOLSET-102-ea: python3 scripts/check.py passed 562/712/212/8, one skip/eight exclusions; Pi module 40 passed; focused median 5.390 to 0.709 s; paired changed+composed-sibling subprocess coverage 1536 lines/403 arcs unchanged; independent review approved; docs/test-suite-audit.md</code> → pass; executed <code>TOOLSET-104-cc: checker regressions 11 passed; independent exact-source review approved; scripts/check.py original failed Pi timestamped-line assertion; unchanged full top-level retry 563 passed, retained 712/212/8 passes, one skip/eight exclusions; combined offline evidence, not one clean full invocation</code> → pass; executed <code>TOOLSET-105-79: deterministic old assertion failed; repaired Pi module 40 passed; changed-PID/missing-start negative probes rejected; independent exact-source review approved; python3 scripts/check.py passed 563/712/212/8, one skip/eight excluded; offline only</code> → pass; executed <code>TOOLSET-110-61: python3 scripts/check.py passed 564/715/216/8 tests, one skip/eight excluded modules; 12 focused checker tests passed; independent exact-source review approved; offline only</code> → pass | — |
| PRIORITY: Make TODO.md order the enforced human priority | unmet | — | TOOLSET-029 |
| RECOVERY: Qualify bounded automatic planning recovery | unverified | executed <code>4b79912: Python 3.12 scripts/check.py passed 562/709/212/8 tests, one skip/eight excluded; exact-tree independent review approved; same canonical read-only response/execution replay passed; installed adoption remains TOOLSET-101-f6</code> → pass; executed <code>Shared TOOLSET-017/018/019 implementation integrated eb72be6; independent review findings repaired with failing-then-passing regressions; final Python 3.12 scripts/check.py passed 318/470/139/8 tests, two skips/eight excluded. Native recovery, deployment and model qualification remain incomplete.</code> → pass; executed <code>TOOLSET-015 reviewed 16a750ce: seven disposable real-Git regressions, Bash syntax and whitespace passed; coordinator integration candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 263/448/139/8 offline tests, 2 skipped and 8 excluded; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-016: exact 9b894fd same-card review approved; integration b470c68 Python 3.12 scripts/check.py passed 283/448/139/8 offline tests (2 skipped, 8 excluded), bash -n and git diff --check passed; native recovery NOT_CHECKED</code> → pass; executed <code>TOOLSET-020: exact 5e05e6b native independent review approved; integration-candidate uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 319/475/139/8 offline tests, two skips/eight excluded; local main integration preservation ZERO_CHANGED; native/model/live qualification unrun</code> → pass; executed <code>TOOLSET-021 exact ab12f821 native independent review run398 approved; integration 49739eff: env -u HERMES_KANBAN_DB uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py passed 332/495/139/8 offline tests, 3 skips, 8 excluded; git diff --check HEAD^1 passed; native/model/live/startup unqualified</code> → pass; executed <code>TOOLSET-022 exact 816678e3 native independent review run406 approved; integration 5f49a2e0: Python 3.12 scripts/check.py on frozen integration candidate passed 332/510/139/8 offline tests, three skips/eight native-model-integration modules excluded; whitespace passed; native/model/live/startup unqualified</code> → pass; executed <code>TOOLSET-103-fe exact reviewed tree 23b46fb: Python 3.12 scripts/check.py retry passed 562/712/212/8 tests, one skip/eight exclusions; 20 exact-framed read-only response replays; installed adoption TOOLSET-101-f6 remains open</code> → pass; executed <code>TOOLSET-106-5d: python3 scripts/check.py passed 563/713/212/8 offline tests (one skip, eight excluded modules); 48 focused collector tests and identical synthetic header consumer passed; independent exact-source review approved; installed adoption remains TOOLSET-101-f6</code> → pass; executed <code>TOOLSET-108-21: response regression RED then 22 focused passes; independent exact-source review approved; Python 3.12 scripts/check.py 563/715/215/8 passed, one skip/eight exclusions; identical read-only consumer restores two prior frames with actual ranks, installed adoption remains TOOLSET-101-f6</code> → pass | TOOLSET-003, TOOLSET-019, TOOLSET-101-f6 |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass; executed <code>python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| CRON-REPORTING: Make Telegram scheduling reports reliable across invocation surfaces | partial | executed <code>Offline source guidance: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python -m unittest discover -s tests (246 run, 2 skipped; no live delivery qualification)</code> → pass | TOOLSET-011 |
| STARTUP: Start useful implementation sooner with less preparation | unmet | executed <code>Reviewed fef4241; integration e2a0838: uv run --python 3.12 --no-project --with-requirements requirements-test.txt python scripts/check.py (252/448/135/8 offline tests; 2 skipped; 8 live/integration modules excluded); native timing remains TOOLSET-013</code> → pass | — |
| DOCS-COMPLETENESS: Make core-document completeness and drift machine-checkable | met | executed <code>TOOLSET-107-93: 22 focused CLI tests; independent re-review approved after literal-marker rework; Python 3.12 scripts/check.py passed 563/713/215/8 tests, one skip/eight exclusions; docs.py check passed; offline only</code> → pass; executed <code>TOOLSET-109-f1: 23 focused CLI tests; exact-source independent review approved; Python 3.12 scripts/check.py passed 563/715/216/8 tests, one skip/eight excluded; docs.py check and git diff --check passed; offline only</code> → pass; executed <code>python3 scripts/check.py (403/571/197/8 offline tests passed, 1 skipped, 8 modules excluded; includes test_docs_manifest, test_docs_stale, test_docs_profiles; offline only)</code> → pass | — |
| UI-TASTE: Ship Uizze's UI Taste as a vendored bundled skill | met | executed <code>python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| SKILL-REVIEW: Fix review findings in the newly vendored UI skills | met | executed <code>Integrated 9f84355: python3 scripts/check.py passed 558/698/212/8 tests, one skip and eight excluded modules; retained description regression and original zero-warning linter evidence; offline only</code> → pass | — |
| CLAUDE-CODE: Install the portable workflows in Claude Code | unmet | — | TOOLSET-066 |
| GENTLE-UPDATE: Roll out updates without forcing gateway restarts | met | executed <code>TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084)</code> → pass; executed <code>TOOLSET-084 live 2026-10-15: hermes toolset update at afe1482 requested the restart with no chat turn in flight; /toolset update status showed gateway_restart completed, new PID 553964, menus resent 9/9; concurrent --check returned busy (exit 3) without touching the first receipt; earlier deferred restart waited for a chat turn that ended on its own (no forced chat drain); 7 linked profiles pinned to clean clones that only updates advance</code> → pass | — |
| PARALLEL: Run independent Autowork tasks in parallel workers with one coordinator | met | executed <code>TOOLSET-091-00 live 2026-10-15: Pi 1.2.0 workers (gpt-6.1-sol) via pi-autowork.sh on a disposable repo: 2 overlapping workers, sequential integration, C after A, combined check pass, no push, 158 s vs 240 s sequential; SIGKILLed coordinator restart adopted live workers without duplicates. Codex 0.162.1 workers cannot commit in the workspace-write sandbox (sequential fallback). Hermes workers not run by owner decision.</code> → pass | — |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |
| PI-RUNNER: Run Autowork continuously through Pi with a model fallback | partial | executed <code>TOOLSET-093-01: python3 -m unittest tests/test_pi_autowork.py (20 fake-Pi tests) and shellcheck passed; live --once with openai-codex/gpt-6.1-sol completed one task in a disposable repository; fallback not qualified live</code> → pass; executed <code>TOOLSET-094-65 live 2026-10-15: disposable repository, 5 tasks each completed once; real primary credential failure fell back to openrouter/deepseek/deepseek-v4.1-flash, which resumed and completed the task in the same session; SIGINT mid-task resumed in the same session; no push; tests/test_pi_autowork.py 21 passed</code> → pass | TOOLSET-096-7e, TOOLSET-099-87 |

<!-- goals:coverage:end -->
