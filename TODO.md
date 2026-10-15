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

### TOOLSET-085-1a — Select several eligible tasks and decide which can run together

- [ ] TOOLSET-085-1a — Select several eligible tasks and decide which can run together
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [task selection](skills/autowork/scripts/task_execution.py), [ledger eligibility](skills/docs-sync/scripts/goals.py).
- Scope: Add `skills/autowork/scripts/parallel_plan.py` with a pure function that takes the ordered runnable tasks (reuse `task_execution.select()`'s per-task contract checks, refactored so one function returns every passing task in order instead of the first) plus the running set, and returns the tasks to dispatch now and a reason for each waiting task. Parse two new optional TODO fields: `Touches:` (comma list of repo paths, directory prefixes ending in `/`, or globs) and `Resources:` (tokens; `live` and `exclusive` mean run alone). Conflict rules from the plan: direct or transitive dependency, overlapping paths (prefix or glob match in either direction), a shared resource token, a serial path (built-in list: package manifests, lockfiles, migration and schema folders, CI workflow files), or a missing `Touches:` means not together. Never dispatch `in_progress` tasks or tasks held by a live slot; an `in_progress` task without a slot counts as running work with its `Touches:`, and without `Touches:` it blocks all dispatch beside it (reported). Fill rule: the highest-priority runnable task is always considered first; if it must run alone or conflicts with running work, nothing lower is dispatched. Also export `overlap(actual_paths, declared, other_sets)` for TOOLSET-088's check of reported files. No dispatch, lease or CLI changes.
- Touches: skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, skills/autowork/scripts/task_execution.py
- Acceptance: Unit tests show: two independent tasks with disjoint `Touches:` are both selected; a dependent pair (including transitive) is not; overlapping paths, globs, a shared resource token, `live`/`exclusive`, a serial path and a missing `Touches:` each serialize; the top task that must run alone blocks lower dispatch; an `in_progress` task without a slot blocks overlapping dispatch, and blocks everything without `Touches:`; existing `select()` behavior and every existing `test_task_execution.py`/`test_priority_selection.py` case are unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_plan.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No inference of file sets from prose or by an LLM; no changes to goals.py ordering.

### TOOLSET-086-9f — Add a repository coordinator lease, worker slots and an execution journal

- [ ] TOOLSET-086-9f — Add a repository coordinator lease, worker slots and an execution journal
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [current lease](skills/autowork/scripts/task_execution.py).
- Scope: Add `skills/autowork/scripts/parallel_state.py` storing `coordinator.json`, `slots/<TASK>.json` and append-only `journal.jsonl` under `<git-common-dir>/autowork-execution/`, written atomically under the existing `writer.lock` and reusing `task_execution`'s process identity (PID, start ticks, boot ID). Functions: claim/release the coordinator lease bound to the `--owner-pid` identity of the persistent coordinator session (refuse a second live coordinator; supersede a dead one; reject a missing or non-ancestor owner), create/update slots through the state machine in the plan, including the retry transitions from its builder-check answers (`interrupted` → `dispatched` attempt 2 in the same worktree; `held` → a fresh attempt on `autowork/<TASK>-r2`; a second failure stays `held`); illegal transitions raise, append journal events, and `reconcile(repo)` that classifies each slot as live worker (adopt), dead with commit (queue integration), dead with uncommitted changes (`interrupted`, worktree kept), or clean without commit (`released`). Make `task_execution.execute()` return `BUSY` while a live parallel coordinator exists, and make the coordinator claim refuse while a live sequential `active.json` owner exists. A live lease never expires by age.
- Touches: skills/autowork/scripts/parallel_state.py, skills/autowork/scripts/test_parallel_state.py, skills/autowork/scripts/task_execution.py
- Acceptance: Tests show two coordinators cannot both claim one repository (also across two linked worktrees); a sequential claim and a parallel coordinator exclude each other; a dead coordinator is superseded; reconcile is idempotent (running it twice gives the same states and journal adds nothing new the second time) and classifies the four worker cases above with real Git fixtures; an illegal slot transition is refused; existing lease tests pass unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_state.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: None.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No worker launch, worktree creation or integration (TOOLSET-087/088); no heartbeat-based expiry.

### TOOLSET-087-32 — Dispatch workers in their own worktrees with a refilled worker pool

- [ ] TOOLSET-087-32 — Dispatch workers in their own worktrees with a refilled worker pool
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [bounded runner and isolate suggestion](skills/autowork/scripts/task_execution.py); builds on TOOLSET-085-1a and TOOLSET-086-9f.
- Scope: Add `skills/autowork/scripts/parallel_dispatch.py` and new `task_execution` flags: `--parallel [N]` (default 2, cap 4 unless `--max-workers`, hard limit 8), `--max-workers`, `--worker-host hermes|codex|pi`, `--worker-command JSON` (argv with `{worktree}`, `{prompt_file}`, `{timeout}`), `--worker-timeout` (default 3600), `--min-free-mem-mb` (default 1500), and `--wait --timeout S`. With `--apply --parallel`, claim the coordinator lease, reconcile slots, compute the dispatch set (TOOLSET-085-1a), and for each task create worktree `<parent>/<repo>-autowork-<TASK>` on branch `autowork/<TASK>` at the recorded canonical HEAD (refuse an existing branch or folder that the journal does not show Autowork created), write the self-contained worker prompt from the plan (task body, worktree, branch, baseline, rules, `report.json` schema), and start the worker CLI in its own process group with cwd = worktree, its own `TMPDIR`, `AUTOWORK_SLOT` and `AUTOWORK_PORT_BASE`, without `HERMES_TOOLSET_EXECUTION_COMMON`. Record worker identity and log path in the slot. Resource gate: hold dispatch while MemAvailable < `--min-free-mem-mb` × (running workers + 1) or the 1-minute load average ≥ CPU count. Restart an `interrupted` slot once in its own worktree with a resume note. Templates never add approval- or sandbox-bypass flags (Codex adds only the worktree and Git common directory as write roots); `--parallel` output shows each worker command. Hermes workers use the coordinator's profile unless `--worker-profile` is given. `--apply --parallel` and every later parallel call require the coordinator's `--owner-pid`. `--wait` blocks until a worker exits or the timeout passes and returns the changed slots; a worker past `--worker-timeout` gets its process group stopped and becomes `interrupted`. Calling `--apply --parallel` again refills free slots. Verify the shipped templates against the installed CLIs (`hermes chat --query-file F --oneshot --in DIR --run-budget S`; `codex exec -C DIR` with the sandbox setting that still allows commits from a linked worktree; Pi's prompt argument) and ship only verified ones; with no usable template, non-Linux or a Claude Code coordinator without `--worker-command`, return `SEQUENTIAL_FALLBACK` plus the ordinary single-task contract. Tests use a deterministic fake worker script (edits files, sleeps, commits, writes `report.json`).
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/task_execution.py, skills/autowork/scripts/fixtures/
- Acceptance: With the fake worker: two independent tasks start in separate worktrees and run at the same time (overlapping process lifetimes recorded in the journal); a dependent or conflicting task is not started; a third task fills the slot freed by the first finisher; a timed-out worker is stopped and its worktree kept; a crashed worker's slot reconciles per TOOLSET-086-9f without a duplicate start, and an interrupted slot restarts once in the same worktree; low memory holds dispatch; user branches/folders with the target names are refused untouched; the unsupported-host path returns `SEQUENTIAL_FALLBACK`; plain `owner_cycle.py --apply` output is unchanged.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_dispatch.py` (new); `python3 scripts/check.py`; `git diff --check`; the template verification commands recorded in task evidence.
- Dependencies: TOOLSET-085-1a, TOOLSET-086-9f.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No integration or task closing (TOOLSET-088-a7); no real LLM worker run in tests; no Claude Code approval-mode template.

### TOOLSET-088-a7 — Integrate finished workers one at a time and close tasks only after validation

- [ ] TOOLSET-088-a7 — Integrate finished workers one at a time and close tasks only after validation
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [delivery verifier](skills/autowork/scripts/delivery_state.py), [bounded runner](skills/autowork/scripts/task_execution.py).
- Scope: Add `skills/autowork/scripts/parallel_integrate.py` and flags `--integrate TASK --run ARGV... --timeout S` and `--parallel-close TASK`. Integrate in priority order among `reported` slots, under the writer lock: verify the commit descends from the slot baseline and matches `report.json`; compare `git diff --name-only baseline..commit` with the task's `Touches:`, coordinator-owned files and other slots' files (`parallel_plan.overlap`), holding the task on any mismatch; in the coordinator-owned integration worktree (`<parent>/<repo>-autowork-integration`, detached), check out canonical HEAD and run `git merge --no-ff autowork/<TASK>`, aborting and holding on conflict; run the validation argv in that worktree through the bounded process core factored out of `command()` (cwd parameter, no `active.json`, `writer.lock` only around state writes; sequential `command()` output byte-identical); then fast-forward the canonical checkout with `git merge --ff-only` only if its HEAD is unchanged (redo the merge once on a moved HEAD; hold after that). Record `integrated` with the merge commit and check receipt. `--parallel-close` refuses unless the slot is `integrated` with a passing validation receipt, then runs `goals.py task TASK done` (and `goals.py archive`), journals it, and removes the clean worker worktree and branch it created. Held and failed slots keep their worktrees. Once no worker is running, a held slot gets one fresh attempt on `autowork/<TASK>-r2` from the current canonical HEAD; a second failure stays held for Plan For Me's fix-or-skip.
- Touches: skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/task_execution.py
- Acceptance: Tests show: a clean worker branch merges and validates, then closes; `--parallel-close` before integration or after a failed validation is refused and the ledger is unchanged; a merge conflict leaves the canonical checkout, its dirty user files and the worker branch untouched and holds the task; a file outside `Touches:` or a coordinator-owned file holds integration; a moved canonical HEAD is re-merged once; a held task gets exactly one fresh `-r2` attempt after the pool drains, keeping the first attempt's branch; sequential `--run` output is unchanged; a failed worker never removes another slot's commit or worktree; the canonical checkout is only ever fast-forwarded.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_integrate.py` (new); `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-087-32.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No rebase, automatic conflict resolution, reset of the canonical checkout, push or remote integration.

### TOOLSET-089-72 — Report parallel progress and metrics, with an end-to-end fixture and benchmark

- [ ] TOOLSET-089-72 — Report parallel progress and metrics, with an end-to-end fixture and benchmark
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15); reads the journal from TOOLSET-086-9f.
- Scope: Add `--parallel-status [--json]` printing the plan's table (header `AUTOWORK — PARALLEL`, `Workers: a/m active`, one row per task with state, worker slot, elapsed, blocked reason; then completed, failed and integration-queue counts) and, with `--json`, worktree, checks, commit and integration fields. Compute metrics from the journal: total wall time, worker time, integration time, waiting/blocked time, peak workers, conflict and retry counts. Add an end-to-end test with a disposable repository whose TODO has task A and B (independent, disjoint `Touches:`) and C (depends on A), driven through the real CLI with the fake worker: A and B overlap in time, C starts only after A is closed, and the final canonical checkout passes the fixture's own test. Add `scripts/bench_parallel.py` running the same controlled workload sequentially and with `--parallel 2`, printing elapsed times and coordinator overhead.
- Touches: skills/autowork/scripts/parallel_status.py, skills/autowork/scripts/test_parallel_e2e.py, scripts/bench_parallel.py, skills/autowork/scripts/task_execution.py
- Acceptance: Status output matches a golden snapshot for a fixed journal and stays under 25 lines for 4 workers; the A/B/C end-to-end test passes deterministically 5 times in a row; the benchmark's measured sequential and parallel times and overhead are recorded in this task's evidence with the machine and workload, without claiming LLM-worker speedups.
- Checks: `python3 -m unittest skills/autowork/scripts/test_parallel_e2e.py`; `python3 scripts/bench_parallel.py`; `python3 scripts/check.py`; `git diff --check`.
- Dependencies: TOOLSET-088-a7.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No live host workers (TOOLSET-091-00); no change to sequential output.

### TOOLSET-090-2d — Document parallel Autowork and wire it into each host

- [ ] TOOLSET-090-2d — Document parallel Autowork and wire it into each host
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15), [Autowork skill](skills/autowork/SKILL.md), [adapter skill](adapters/skills/autowork/SKILL.md), [cross-host guide](docs/cross-host.md).
- Scope: Add a short parallel-mode section to `skills/autowork/SKILL.md` and a reference `skills/autowork/references/parallel-workers.md` with the coordinator loop (claim, dispatch, `--wait`, review report, `--integrate`, `--parallel-close`, metadata commit, refill), `Touches:`/`Resources:` authoring, conflict handling, worktrees, recovery and authority. Mirror the invocation in `adapters/skills/autowork/SKILL.md` (Claude Code: sequential unless `--worker-command` is given; Codex and Pi: their templates). Document the `Touches:`/`Resources:` fields in the shared TODO rules and Docs Sync so planners write them. Fix the stale "Delegation does not create Git worktrees" line in `references/accepted-plan-execution.md`. Update README (one short paragraph and a link, no internals), docs/workflows.md, docs/cross-host.md (host capability table), docs/testing.md and the CHANGELOG. Add tests: sequential `owner_cycle.py --apply` results are byte-identical to before for an existing fixture, and an unsupported host returns `SEQUENTIAL_FALLBACK`.
- Touches: skills/autowork/SKILL.md, skills/autowork/references/, adapters/skills/autowork/SKILL.md, skills/shared/TODO-WORKCENTER.md, skills/docs-sync/SKILL.md, README.md, docs/workflows.md, docs/cross-host.md, docs/testing.md, CHANGELOG.md, skills/autowork/scripts/test_parallel_compat.py
- Acceptance: Docs describe only implemented behavior and flags (checked against `--help`); the host table states which hosts run parallel workers and which fall back; compatibility and fallback tests pass; `docs.py check` passes; skill bundle and adapter tests pass.
- Checks: `python3 scripts/check.py`; `python3 skills/docs-sync/scripts/docs.py check .`; `node --test tests/portable_pi.test.mjs`; `git diff --check`.
- Dependencies: TOOLSET-089-72.
- Ownership: Toolset coordinator under Autowork local repository authority.
- Exclusions: No new Telegram command (the flag passes through `/autowork` arguments); no Hermes Agent changes.

### TOOLSET-091-00 — Qualify parallel Autowork with real host workers

- [ ] TOOLSET-091-00 — Qualify parallel Autowork with real host workers
- Status: open.
- Goal: PARALLEL — Run independent Autowork tasks in parallel workers with one coordinator.
- Sources: [plan](docs/project.md#parallel-autowork-2026-10-15).
- Scope: On a disposable local repository (not a fleet project) with three small real tasks (A, B independent; C depends on A), run `/autowork --parallel 2` from a Hermes coordinator with Hermes workers, then repeat with Codex and Pi workers where installed. Record per run: worker overlap, integration order, C waiting for A, combined test result, wall time against a sequential run of the same tasks, worker and integration time, and any held or interrupted slot. Interrupt one run's coordinator mid-way and confirm a restart adopts live workers without duplicates.
- Acceptance: Each qualified host shows two real workers overlapping in separate worktrees, sequential integration, C after A, a passing combined check and no push; the interruption test starts no duplicate worker; measured times recorded with host versions; any host that fails stays documented as sequential-only.
- Checks: `--parallel-status --json` at each step, the journal, `git log --graph` of the disposable repository, and the recorded elapsed times.
- Dependencies: TOOLSET-090-2d.
- Environment prerequisite: Installed host CLIs with working model access; owner availability to observe the run.
- Exclusions: No fleet repositories or profiles, no push, no cron schedule.

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
- Dependencies: None.
- Prior work: TOOLSET-068 (done, archived).
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
- Dependencies: None.
- Prior work: TOOLSET-079 (done, archived).
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
| PARALLEL: Run independent Autowork tasks in parallel workers with one coordinator | unmet | — | TOOLSET-085-1a, TOOLSET-086-9f, TOOLSET-087-32, TOOLSET-088-a7, TOOLSET-089-72, TOOLSET-090-2d, TOOLSET-091-00 |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |

<!-- goals:coverage:end -->
