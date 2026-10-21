# Work queue

[Completed tasks](TODO.archive.md)


Central queue for Autowork. Scope and current architecture: [project contract](docs/project.md).
[goals.json](goals.json) indexes the remaining work below; verified completed
tasks move to the archive automatically. Ledger eligibility is not worker
admission or live qualification.

## Now

### TOOLSET-294-f6 — TaskStore reads tasks/ files into immutable records from a pinned commit

- [ ] TOOLSET-294-f6 — TaskStore reads tasks/ files into immutable records from a pinned commit
- Held by: an interactive session implementing TASK-STORE on the owner's instruction (relayed 2026-10-20); do not dispatch or adopt; until 2026-10-27
- Short: Read-only TaskStore over tasks/
- Status: open
- Goal: TASK-STORE
- Payoff: Give every engine consumer one typed, immutable view of a repository's tasks and goals.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [current queue reader](pi-autowork/engine/task_execution.py) (`selection_inputs`, `_queue_inputs`, `task_ledger`); [ledger rules](skills/docs-sync/scripts/goals_ledger.py).
- Evidence: the engine parses TODO.md bodies and goals.json in `task_execution._queue_inputs` and again in parallel_*, fleet_view and worker; no single typed record exists, and the working tree is read directly.
- Touches: pi-autowork/engine/task_store.py, pi-autowork/engine/test_task_store.py, pi-autowork/engine/fixtures/task_store/
- Scope: (1) Define the schema, versioned from the start (`schema = 1` in every file; an unknown or missing version is refused, never guessed or upgraded): `tasks/items/<ID>.md` and `tasks/goals/<ID>.md`, TOML frontmatter between `+++` lines and a Markdown body; task fields id, title, short, status (`open|done|superseded`), goal, section (`Now|Next|Needs decision`), rank, depends_on, touches, resources, kind, ownership, live authorization, scope, acceptance, checks, exclusions; goal fields id, title, priority, source, status, focus. (2) `TaskStore.at(repo, rev)` reads every file with `git show`/`git ls-tree` at a pinned commit and returns frozen records; `TaskStore.pending(repo)` lists uncommitted task-file edits without reading them as tasks. (3) Each record carries a record revision (hash of its bytes) and a contract hash over scope, acceptance, checks, dependencies, touches, section group (runnable vs Needs decision), status and the authority fields; rank, title, short, Now-vs-Next and free notes are excluded. (4) Typed authority fields: unknown or absent values never grant permission. (5) Fail closed: a malformed file, duplicate ID or unknown goal makes the whole store invalid with path:line errors; a task missing required contract fields is a visible draft, not runnable.
- Acceptance: `test_task_store` covers: records read at a pinned commit ignore a later working-tree edit (`test_reads_the_pinned_commit_not_the_worktree`); an uncommitted edit shows only as pending (`test_uncommitted_edit_is_pending`); changing rank or title keeps the contract hash, changing acceptance, checks, Touches or moving to Needs decision changes it (`test_contract_hash_ignores_rank_and_title`); absent `resources`/`live` grant nothing (`test_absent_authority_grants_nothing`); malformed TOML, a duplicate ID, an unknown goal and an unknown schema version fail closed (`test_corrupt_store_fails_closed`); a draft is listed but not runnable (`test_draft_is_visible_not_runnable`).
- Checks: python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py; python3 scripts/check.py
- Dependencies: None.
- Ownership: Toolset coordinator.
- Exclusions: No writer, CLI, migration or consumer change in this task; no SQLite; no third-party TOML library (read with `tomllib`).
- Planner's call: frontmatter is TOML because the reader is stdlib `tomllib` and the writer can stay small; the contract-hash field list above is the starting set and later tasks may add a field only with a test.

### TOOLSET-295-57 — Task selection from the store matches the current selector

- [ ] TOOLSET-295-57 — Task selection from the store matches the current selector
- Held by: an interactive session implementing TASK-STORE on the owner's instruction (relayed 2026-10-20); do not dispatch or adopt; until 2026-10-27
- Short: Store selection parity
- Status: open
- Goal: TASK-STORE
- Payoff: Prove the cut cannot change which task a runner picks.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [selector](pi-autowork/engine/task_execution.py) (`_contracts`, `_queue_inputs`, `dependency_done`); [queue order](skills/docs-sync/scripts/goals_queue.py) (`queue`, `eligible`, `priority_status`); [priority tests](pi-autowork/engine/test_priority_selection.py).
- Evidence: the decision requires selection order to stay focused goal, section, rank, goal priority, derived goal status, then ID, and to be proven by a differential test before the cut.
- Touches: pi-autowork/engine/task_select.py, pi-autowork/engine/test_task_select.py
- Scope: (1) `task_select.order(store)` and `task_select.next(store, done)` over TaskStore records, with dependency satisfaction including archived and `done` records. (2) `task_select.why(store, id)` returns structured reasons (blocked by dependency, Needs decision, draft, superseded, goal met, position and the rule that placed it). (3) A differential test builds each fixture both ways (TODO.md + goals.json, and the equivalent tasks/ tree) and asserts the same order and next task as the current `task_execution` selector, including focus, sections, dependencies, met goals and drafts. (4) Record the time and memory to read and order a generated 1,000-task store at a pinned commit, as the baseline for a budget (a measurement, not a pass/fail gate).
- Acceptance: `test_task_select.SelectionParityTests` passes on at least eight fixtures covering focus, Now/Next/Needs decision, cross-goal priority, an unmet dependency, an archived dependency, a met goal, a superseded task and a draft; `test_why_names_the_blocking_rule` asserts the reason for each non-selected task.
- Checks: python3 -m unittest discover -s pi-autowork/engine -p test_task_select.py; python3 -m unittest discover -s pi-autowork/engine -p test_priority_selection.py; python3 scripts/check.py
- Dependencies: TOOLSET-294-f6.
- Ownership: Toolset coordinator.
- Exclusions: The current selector stays untouched here; no consumer switches to the new selector in this task.

### TOOLSET-296-9f — A schema-bound writer and the autowork tasks commands edit the store

- [ ] TOOLSET-296-9f — A schema-bound writer and the autowork tasks commands edit the store
- Held by: an interactive session implementing TASK-STORE on the owner's instruction (relayed 2026-10-20); do not dispatch or adopt; until 2026-10-27
- Short: Store writer and tasks CLI
- Status: open
- Goal: TASK-STORE
- Payoff: Let planners and skills change tasks without parsing or hand-editing files.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [current planning commands](skills/docs-sync/scripts/goals.py) (`add-task`, `field`, `place`, `move`, `new-id`, `supersede`); [CLI](pi-autowork/pi_autowork/cli.py).
- Evidence: planning skills edit TODO.md and goals.json through goals.py; the decision moves these edits to the `autowork` CLI over `tasks/`.
- Touches: pi-autowork/engine/task_store.py, pi-autowork/engine/test_task_store_write.py, pi-autowork/pi_autowork/cli.py, pi-autowork/pi_autowork/task_commands.py, tests/test_task_commands.py
- Scope: (1) A writer that emits canonical TOML for the known schema only, round-trips every valid record byte-for-byte and refuses values it cannot represent (multi-line strings it would reflow, unknown keys, control characters). (2) `autowork tasks list|show|why|validate <repo>` read at HEAD; `autowork tasks add|field|place|move|supersede|new-id <repo> ...` write `tasks/` files in the working tree; new tasks take the next multiple of 1000 in their section and `move` takes the midpoint between its neighbours' ranks, equal ranks allowed with the ID breaking the tie; when no integer remains it rebalances only the contiguous run of gapless neighbours, to multiples of 1000 within that run's bounds, prints the files it will change and never renumbers the queue with the same ID allocation and goal-priority rules as goals.py, and never write TODO.md or goals.json; a task file written this way grants no authority beyond its typed fields, and a declared check still needs the existing approval to run. (3) `validate` exits 1 with path:line errors on a corrupt store.
- Acceptance: `test_task_store_write.test_round_trips_every_fixture` and `test_refuses_input_it_cannot_preserve`; `tests/test_task_commands.py` covers add then show, field, place into Needs decision (contract hash changes), move (only rank changes), a move with no gap left (only the gapless run is rewritten, `test_move_without_a_gap_rebalances_locally`), supersede, `why` output and `validate` failing on a broken file.
- Checks: python3 -m unittest discover -s pi-autowork/engine -p test_task_store_write.py; python3 -m unittest discover -s tests -p test_task_commands.py; python3 scripts/check.py
- Dependencies: TOOLSET-294-f6, TOOLSET-295-57.
- Ownership: Toolset coordinator.
- Exclusions: goals.py keeps working on unconverted repositories until TOOLSET-301-32; no commit or push from these commands.

### TOOLSET-297-41 — autowork migrate converts a repository to tasks/ once

- [ ] TOOLSET-297-41 — autowork migrate converts a repository to tasks/ once
- Held by: an interactive session implementing TASK-STORE on the owner's instruction (relayed 2026-10-20); do not dispatch or adopt; until 2026-10-27
- Short: autowork migrate
- Status: open
- Goal: TASK-STORE
- Payoff: Convert each repository in one checked step, with nothing lost and the same next task.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [TODO rules](skills/shared/TODO-WORKCENTER.md); [archive contract](skills/docs-sync/references/todo-archive.md).
- Evidence: the owner chose a one-time conversion per repository with no dual reader.
- Touches: pi-autowork/pi_autowork/cli.py, pi-autowork/pi_autowork/task_migrate.py, tests/test_task_migrate.py
- Scope: (1) `autowork migrate <repo> [--dry-run]` reads TODO.md and goals.json, writes `tasks/items/` and `tasks/goals/` (rank from TODO.md order, every body field kept), removes TODO.md and goals.json (no pointer or stub is left; `autowork tasks overview` prints the board on demand); TODO.archive.md is untouched. (2) Before writing, it checks parity: same task set, same contract fields, and `task_select` order equal to the current selector's; any mismatch refuses with the difference. (3) It refuses a dirty planning file, a live runner slot, a held lease or claim, an unfinished integration or closure transaction in that repository, or an already converted repository, and makes one local commit on success.
- Acceptance: `tests/test_task_migrate.py`: a fixture with focus, three goals, Needs decision, dependencies and archived tasks converts with identical order and field content (`test_migration_keeps_order_and_fields`); a dirty TODO.md, a live slot, a held claim, an unfinished closure and a converted repo each refuse (`test_migration_refuses_unsafe_states`); a body field the schema cannot hold refuses rather than drops it, and `--dry-run` writes nothing (`test_migration_refuses_unlossless_input`).
- Checks: python3 -m unittest discover -s tests -p test_task_migrate.py; python3 scripts/check.py
- Dependencies: TOOLSET-295-57, TOOLSET-296-9f.
- Ownership: Toolset coordinator.
- Exclusions: Does not convert any repository itself and never pushes; no reverse migration.

## Next

### TOOLSET-303-24 — Harden managed-recovery interruption test isolation

- [ ] TOOLSET-303-24 — Harden managed-recovery interruption test isolation
- Coordination: Keep the owner's TASK-STORE Now order and all current contracts unchanged. This test-only Next slice has no product prerequisite on that migration or the archived recovery task. Its Touches are disjoint from the current TaskStore reader. TOOLSET-299-d9 broadly names tests/ for its later runner/fleet cutover: retain that future scope, and serialize if both tasks become ready; do not add a false migration prerequisite or edit its contract just to silence lint. Historical recovery acceptance and live exclusions remain intact.
- Next action: Start with the named test and inspect its disposable Git identity/timestamps, inherited fixture patches, process/environment isolation and each injected interruption seam. Compare isolated/module/full-check context and resource load, capturing an unexpected early-return result before changing the fixture; choose a test-only correction supported by observations, not an assumed timing cause.
- Exclusions: No update_bundle.py or other product-code repair; no changed recovery policy, global process-visibility suppression, weakened check classification, real Hermes profiles, native/model/live qualification, publication or worker edits to coordinator-owned planning files.
- Ownership: Toolset coordinator; one writer per affected workspace.
- Touches: tests/test_update_bundle.py
- Evidence: Full-check failure followed by isolated pass on cc24267381e079ccee1914fb919ccecdc788313e, f9c49c20cb822442f9f85d767eff67e03081d67b and 04997ef075924de339871d03eca38b07c85ac665. Read the bundle in place at <git-common-dir>/autowork-execution/main-evidence/04997ef075924de339871d03eca38b07c85ac665 (or $AUTOWORK_MAIN_EVIDENCE/04997ef075924de339871d03eca38b07c85ac665): main_check.json, main-check.log, main-check.exit, main-check-reruns.log, flaky_history.json. Full check exit 1, four directories passed and one failed; the rename subtest reports AssertionError: Killed not raised at tests/test_update_bundle.py:1269. The saved isolated command (runner-resolved Python executable) `python3 -m unittest test_update_bundle.ManagedRecoveryTests.test_interrupted_publication_resumes_original_backup` in the scratch checkout tests directory exits 0 (one test, 7.138s). main_check.json records green with this flaky ID; main is not red for this test. The history lists the other two revisions, not their individual rerun logs. All three revision commits change planning documents only (TODO.md, TODO.archive.md and/or goals.json; 04997ef also docs/project.md), not updater code. The completed recovery worker report at <git-common-dir>/autowork-execution/slot-data/TOOLSET-172-92/attempt-1/report.json reports earlier module passes at 5ed86c9, not current stability or a cause. Do not copy runtime bundles into Git or require an owner to provide them.
- Sources: [accepted managed checkout recovery](docs/project.md#managed-hermes-checkout-recovery); [interruption fixture](tests/test_update_bundle.py) (`ManagedRecoveryTests.setUp`, `test_interrupted_publication_resumes_original_backup`, inherited `UpdateTests.setUp`); [offline checker](scripts/check.py); [completed recovery task](TODO.archive.md#toolset-172-92--recover-verified-managed-hermes-checkouts-when-updates-cannot-fast-forward); DOCS-MAINTAINER MAIN (flaky test) instruction, 2026-10-20.
- Payoff: Restore confidence in the offline updater regression without treating a suite-only flake as a product failure; grouped with existing reliability maintenance, not new recovery behavior.
- Short: Stable recovery interruption fixture
- Status: open
- Goal: RELIABILITY-2026-10
- Scope: Investigate isolation, resource load and fixture timing in test_update_bundle.ManagedRecoveryTests.test_interrupted_publication_resumes_original_backup; harden only test-owned setup, fault injection and cleanup in tests/test_update_bundle.py. Preserve the updater recovery contract; no product-code repair.
- Acceptance: `test_update_bundle.ManagedRecoveryTests.test_interrupted_publication_resumes_original_backup` deterministically reaches every existing interruption point, raises its injected Killed exception and still proves same-original-backup resume, preservation of original source/profile bytes, and publication of the originally selected target after upstream moves. Record evidence distinguishing isolation, resource-load and fixture-timing hypotheses; retain all existing assertions and subtests. Repeated isolated runs, the module and the full offline gate show the fixture improvement without skipping cases, weakening assertions, inflating sleeps/timeouts or adding production test hooks; report commands, repetitions and any remaining flake. Cleanup restores patches and disposable Git/home fixtures even after failure.
- Checks: Planned: `for run in 1 2 3; do python3 scripts/check.py tests/test_update_bundle.py -k test_interrupted_publication_resumes_original_backup || exit; done`; `python3 scripts/check.py tests/test_update_bundle.py`; `python3 scripts/check.py`; `git diff --check`. Use a fresh short TMPDIR; these are required checks, not passing evidence.
- Dependencies: None.

## Needs decision

### TOOLSET-298-c2 — The engine reads only tasks/

- [ ] TOOLSET-298-c2 — The engine reads only tasks/
- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Short: Engine cutover to tasks/
- Status: open
- Goal: TASK-STORE
- Payoff: Remove the second parse of TODO.md and goals.json from selection, dispatch and integration.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [selector](pi-autowork/engine/task_execution.py); [dispatch](pi-autowork/engine/parallel_dispatch.py); [integration](pi-autowork/engine/parallel_integrate.py) (`PLANNING_FILES`, `planning_only`); [claims](pi-autowork/engine/parallel_claims.py); [state](pi-autowork/engine/parallel_state.py); [status](pi-autowork/engine/parallel_status.py); [retry](pi-autowork/engine/retry_selection.py).
- Evidence: these modules read TODO.md or goals.json directly and detect task changes by file bytes, so a rank edit can invalidate admitted work.
- Touches: pi-autowork/engine/task_execution.py, pi-autowork/engine/parallel_dispatch.py, pi-autowork/engine/parallel_claims.py, pi-autowork/engine/retry_selection.py, pi-autowork/engine/test_task_execution.py
- Scope: (1) Selection, dispatch, claims and retry take records from TaskStore at the base commit and use `task_select`; parallel_state and parallel_status follow only where they read the queue. (2) Dispatch reads every authority field (resources, live authorization, kind, ownership, checks) only from the base revision, never from a worker branch or working-tree edit, and admits work against a record's contract hash; a rank or title edit keeps an admitted slot, a contract change sets it aside. (3) Retired, closed and removed tasks are judged by TaskStore at the base revision (`parallel_dispatch`'s closed-on lookup), so a task closed on the base branch is never redispatched from an older session. (4) A repository without `tasks/` stops with "run autowork migrate <repo>" and selects nothing. Engine tests move their fixtures to `tasks/`.
- Acceptance: a rank or title edit to an admitted task keeps its slot (`test_rank_edit_keeps_admitted_work`); an acceptance edit sets it aside (`test_contract_edit_invalidates_admitted_work`); a task closed at the base revision is not redispatched and an unconverted repo returns the migrate instruction (`test_closed_at_base_is_not_redispatched`, `test_unconverted_repo_names_migrate`).
- Checks: python3 -m unittest discover -s pi-autowork/engine; python3 scripts/check.py
- Dependencies: TOOLSET-297-41.
- Ownership: Toolset coordinator.
- Exclusions: Integration's change classification is TOOLSET-302-33; the runner service, fleet view and TUI are TOOLSET-299-d9; no fallback reader for TODO.md.

### TOOLSET-302-33 — Integration judges task edits by contract hash, not by path

- [ ] TOOLSET-302-33 — Integration judges task edits by contract hash, not by path
- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Short: Contract-hash change classification
- Status: open
- Goal: TASK-STORE
- Payoff: Stop a clean Git merge from closing a task under acceptance nobody verified.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [integration](pi-autowork/engine/parallel_integrate.py) (`PLANNING_FILES`, `planning_only`, the remerge shortcut, the post-verification contract recheck).
- Evidence: `planning_only` treats `docs/` and the planning files as safe to remerge without rerunning checks; simply adding `tasks/` there would let an acceptance or check edit ride through as "planning only". File-per-task also allows clean textual merges of one task's acceptance edit and another branch's `status = "done"`.
- Touches: pi-autowork/engine/parallel_integrate.py, pi-autowork/engine/task_store.py, pi-autowork/engine/test_parallel_integrate.py
- Scope: (1) Classify a `tasks/` change by comparing records at base, incoming and current: rank, title, short, notes and Now/Next are bookkeeping; a worker-authored change that adds a task or edits any task's authority fields (resources, live authorization, kind, ownership, checks) is never bookkeeping: integration refuses it or holds it for the coordinator, and authority is read only from the base revision; a contract-hash change to the task being integrated (acceptance, checks, dependencies, Touches, authority fields, Needs decision, superseded) requires revalidation or a hold. (2) `done` survives a merge only if the contract hash equals the one that was verified; otherwise the task returns to open with the reason. (3) BLOCKERS.md and TODO.archive.md stay path-classified planning files.
- Acceptance: `test_rank_edit_on_base_keeps_the_remerge_shortcut`, `test_acceptance_edit_on_base_requires_revalidation` and `test_done_with_a_changed_contract_is_reopened` and `test_worker_cannot_grant_authority_via_task_edit` (a worker branch that adds a task with `live_authorization = true` or extra resources or checks, or grants them to another task, is refused or held, never merged as bookkeeping) pass.
- Checks: python3 -m unittest discover -s pi-autowork/engine -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: TOOLSET-298-c2.
- Ownership: Toolset coordinator.
- Exclusions: No distributed leases; one integration coordinator per repository.

### TOOLSET-299-d9 — The runner and the fleet view read only tasks/

- [ ] TOOLSET-299-d9 — The runner and the fleet view read only tasks/
- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Short: Runner and fleet view cutover
- Status: open
- Goal: TASK-STORE
- Payoff: Keep the runner, readiness checks and the TUI consistent with the engine's single store.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [coordinator](pi-autowork/pi_autowork/coordinator.py) (plan-file change detection); [worker](pi-autowork/pi_autowork/worker.py) (`PLANNING_FILES`); [maintainer](pi-autowork/pi_autowork/maintainer.py); [fleet view](pi-autowork/pi_autowork/fleet_view.py) (`REQUIRED`); [questions](pi-autowork/pi_autowork/questions.py); [TUI](pi-autowork/pi_autowork/tui.py); [Touches inference](pi-autowork/pi_autowork/touches_inference.py); [service](pi-autowork/pi_autowork/service.py).
- Evidence: these modules name TODO.md and goals.json for readiness, planning-only detection, plan-change wakeups and task counts.
- Touches: pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/worker.py, pi-autowork/pi_autowork/maintainer.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/pi_autowork/questions.py, pi-autowork/pi_autowork/tui.py, pi-autowork/pi_autowork/touches_inference.py, pi-autowork/pi_autowork/service.py, pi-autowork/pi_autowork/command.py, tests/
- Scope: (1) Readiness requires `tasks/`; an unconverted repository shows "run autowork migrate" in `autowork status` and the TUI and its runner idles at zero tokens. (2) Plan-change wakeups use a task-tree signature (the `tasks/` tree hash at HEAD plus `git status` of `tasks/`), not file or directory mtimes, since editing a nested file need not change its directory's timestamp. Worker and maintainer planning-only checks follow TOOLSET-302-33's classification. (3) Task counts, statuses and questions come from TaskStore; the TUI shows pending uncommitted task edits as pending. (4) The docs maintainer writes through the TaskStore writer.
- Acceptance: tests cover: an unconverted repo reports the migrate instruction and starts no worker (`test_unconverted_repo_idles_with_migrate_hint`); an in-place edit of an existing task file wakes the coordinator (`test_nested_task_edit_wakes_coordinator`); fleet view counts match TaskStore on a fixture (`test_fleet_counts_match_store`).
- Checks: python3 -m unittest discover -s tests; python3 scripts/check.py
- Dependencies: TOOLSET-298-c2, TOOLSET-302-33.
- Ownership: Toolset coordinator.
- Exclusions: No change to which fleet repositories run; converting them is the owner's step.

### TOOLSET-300-68 — Closing a task publishes one receipt and status commit exactly once

- [ ] TOOLSET-300-68 — Closing a task publishes one receipt and status commit exactly once
- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Short: Idempotent closure receipts
- Status: open
- Goal: TASK-STORE
- Payoff: Make closure replay-safe, so a crash or retry never double-closes or loses a receipt.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [closure](pi-autowork/engine/finish_task.py); [integration journal](pi-autowork/engine/parallel_integrate.py); [check receipts](pi-autowork/engine/check_receipt.py).
- Evidence: closure currently edits TODO.md, goals.json and the archive in separate writes; the decision requires one bookkeeping-only commit holding status and a sanitized receipt.
- Touches: pi-autowork/engine/finish_task.py, pi-autowork/engine/parallel_integrate.py, pi-autowork/engine/task_store.py, pi-autowork/engine/test_finish_task.py, pi-autowork/engine/test_parallel_integrate.py
- Scope: (1) Closure writes `status = "done"` plus `tasks/evidence/<ID>.toml` (check commands, results, commit, review, no private paths or names) in one commit through the existing journal. (2) Replaying a closure whose commit already exists is a no-op; a crash between journal steps resumes to exactly one commit. (3) Receipts are sanitized by the same rules as the public changelog. (4) The receipt names the exact candidate commit and tree that passed verification; the closure commit may change only that task's file and its receipt, and delivery to the default branch is recorded separately from closure.
- Acceptance: `test_closure_is_one_commit`, `test_replayed_closure_is_a_noop`, `test_crash_mid_closure_resumes_once` and `test_receipt_has_no_private_paths` pass.
- Checks: python3 -m unittest discover -s pi-autowork/engine -p test_finish_task.py; python3 -m unittest discover -s pi-autowork/engine -p test_parallel_integrate.py; python3 scripts/check.py
- Dependencies: TOOLSET-302-33.
- Ownership: Toolset coordinator.
- Exclusions: TODO.archive.md is not written by closure on a converted repository.

### TOOLSET-301-32 — Planning skills use the autowork CLI and this repository converts to tasks/

- [ ] TOOLSET-301-32 — Planning skills use the autowork CLI and this repository converts to tasks/
- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Short: Skills, docs and this repo's conversion
- Status: open
- Goal: TASK-STORE
- Payoff: Finish the cut: skills and docs describe one store, and this repository runs on it.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [Autowork skill](skills/autowork/SKILL.md); [Docs Sync](skills/docs-sync/SKILL.md); [Plan For Me](skills/plan-for-me/SKILL.md); [Blockers](skills/blockers/SKILL.md); [TODO rules](skills/shared/TODO-WORKCENTER.md).
- Evidence: the skills tell agents to edit TODO.md and run goals.py; after the cutover those files are no longer read on converted repositories.
- Touches: skills/autowork/, skills/docs-sync/, skills/plan-for-me/, skills/blockers/, skills/shared/TODO-WORKCENTER.md, docs/, README.md, tasks/
- Scope: (1) Skills and docs name `autowork tasks ...` for every task edit and drop goals.py instructions; goals.py's task-editing commands are removed (clean cut). (2) Run `autowork migrate` on this repository and commit the result. (3) Qualify on a disposable fixture repository: a runner converts nothing on its own, refuses before migration, and after migration selects, runs and closes one task with one receipt commit.
- Acceptance: skill tests pass with the new wording; this repository's `autowork tasks validate .` passes and `autowork tasks list .` shows the remaining TASK-STORE work; the fixture qualification (`tests/test_task_store_qualification.py`) records its commands and results (offline, not a live fleet claim).
- Checks: python3 scripts/check.py; autowork tasks validate .
- Dependencies: TOOLSET-297-41, TOOLSET-299-d9, TOOLSET-300-68, TOOLSET-302-33.
- Ownership: Toolset coordinator.
- Exclusions: No conversion of fleet repositories; their owner runs `autowork migrate` one at a time.

## Goal coverage

<!-- goals:coverage:begin -->

Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.

| Goal | Status | Evidence | Task |
| --- | --- | --- | --- |
| RELIABILITY-2026-10: Fix the reproduced high-ROI reliability bugs from the 2026-10-15 harvest | partial | executed <code>python3 scripts/check.py on integrated main (437/575/209/8 offline tests passed, includes the TOOLSET-043..051 regressions) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | TOOLSET-303-24 |
| README-DESIGN: Vendor the README design skill and use it on this README | met | executed <code>TOOLSET-060/061 (b15bbc7, 5a9c044, ff7196f): python3 scripts/check.py 4/4 directories passed, node --test tests/portable_pi.test.mjs passed, docs.py check ok, vendored audit_readme.py passed with 2 local images; independent review of the vendoring; offline only</code> → pass; executed <code>TOOLSET-116-fc: python3 scripts/check.py passed 575/715/217/8 tests (one skip/eight excluded modules); all 12 focused README-audit tests and exact-source independent review approved; mixed-text single-line examples and adjacent-image preservation verified offline</code> → pass | — |
| PRIORITY: Make TODO.md order the enforced human priority | met | Executed check: pass ([TOOLSET-029](TODO.archive.md#toolset-029)) | — |
| ARCHIVAL: Integrate archival and reconcile the rendering contract | met | executed <code>Reviewed 218865c; coordinator exact-commit Python 3.12 scripts/check.py: 253/448/139/8 offline tests passed, 2 skipped, 8 excluded; native same-card review approved; local integration only</code> → pass; executed <code>cd skills/docs-sync/scripts &amp;&amp; python3 -m unittest test_todo_archive test_archive_policy test_render_safety (31 tests; offline only)</code> → pass; executed <code>python3 scripts/check.py (411/572/204/8 offline tests passed; includes TOOLSET-042 archive newline, git diff --check and legacy-retry regressions); offline only</code> → pass | — |
| CONTINUATION: Resolve and align continuation authority | met | executed <code>TOOLSET-007 historical check-reuse implementation verified in 9d1c7dc offline gate: check_receipt/retry_selection/reconcile regression modules passed; full 288/451/139/8, two skips and eight excluded native/model modules. Historical task archived; TOOLSET-008 independently reviewed and integrated.</code> → pass; executed <code>TOOLSET-008: independently reviewed and integrated 9d1c7dc; Python 3.12 scripts/check.py passed 288/451/139/8 tests, 2 skipped and 8 native/model modules excluded; exact correction review reran 26 checks. Native behavior not qualified.</code> → pass | — |
| UI-TASTE: Ship Uizze's UI Taste as a vendored bundled skill | met | executed <code>python3 scripts/check.py (440/575/209/8 offline tests, includes test_ui_taste_bundle and portable package tests) and node --test tests/portable_pi.test.mjs (3 passed); offline only</code> → pass | — |
| SKILL-REVIEW: Fix review findings in the newly vendored UI skills | met | executed <code>Integrated 9f84355: python3 scripts/check.py passed 558/698/212/8 tests, one skip and eight excluded modules; retained description regression and original zero-warning linter evidence; offline only</code> → pass | — |
| GENTLE-UPDATE: Roll out updates without forcing gateway restarts | met | executed <code>TOOLSET-075..079 offline: python3 scripts/check.py (506/576/209/8 passed, 1 skipped) and node --test tests/portable_pi.test.mjs (3 passed); read-only pin dry run against the live home refused an unreleased revision as designed; live rollout not qualified (TOOLSET-084)</code> → pass; executed <code>TOOLSET-084 live 2026-10-15: hermes toolset update at afe1482 requested the restart with no chat turn in flight; /toolset update status showed gateway_restart completed, new PID 553964, menus resent 9/9; concurrent --check returned busy (exit 3) without touching the first receipt; earlier deferred restart waited for a chat turn that ended on its own (no forced chat drain); 7 linked profiles pinned to clean clones that only updates advance</code> → pass | — |
| POLICY-OPTOUT: Honor the documented runtime-policy opt-out everywhere it is checked | met | executed <code>python3 scripts/check.py --timeout 300 (406/571/197/8 offline tests passed; includes RuntimePolicyOptOutTests; offline only)</code> → pass | — |
| OMH-SETUP-REPORT: Report OMH memory left off when another provider holds the slot | met | executed <code>python3 scripts/check.py --timeout 300 (410/572/197/8 offline tests passed; includes test_install_omh memory-off regressions; offline only)</code> → pass | — |
| TASK-STORE: Keep project tasks in a Git-native tasks/ store the engine reads directly | unmet | — | TOOLSET-294-f6, TOOLSET-295-57, TOOLSET-296-9f, TOOLSET-297-41, TOOLSET-298-c2, TOOLSET-299-d9, TOOLSET-300-68, TOOLSET-301-32, TOOLSET-302-33 |

<!-- goals:coverage:end -->
