+++
schema = 1
id = "TOOLSET-298-c2"
title = "The engine reads only tasks/"
short = "Engine cutover to tasks/"
status = "done"
goal = "TASK-STORE"
section = "Needs decision"
rank = 2000
depends_on = ["TOOLSET-297-41"]
touches = ["pi-autowork/engine/task_execution.py", "pi-autowork/engine/parallel_dispatch.py", "pi-autowork/engine/parallel_claims.py", "pi-autowork/engine/retry_selection.py", "pi-autowork/engine/test_task_execution.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "(1) Selection, dispatch, claims and retry take records from TaskStore at the base commit and use `task_select`; parallel_state and parallel_status follow only where they read the queue. (2) Dispatch reads every authority field (resources, live authorization, kind, ownership, checks) only from the base revision, never from a worker branch or working-tree edit, and admits work against a record's contract hash; a rank or title edit keeps an admitted slot, a contract change sets it aside. (3) Retired, closed and removed tasks are judged by TaskStore at the base revision (`parallel_dispatch`'s closed-on lookup), so a task closed on the base branch is never redispatched from an older session. (4) A repository without `tasks/` stops with \"run autowork migrate <repo>\" and selects nothing. Engine tests move their fixtures to `tasks/`."
acceptance = ["a rank or title edit to an admitted task keeps its slot (`test_rank_edit_keeps_admitted_work`); an acceptance edit sets it aside (`test_contract_edit_invalidates_admitted_work`); a task closed at the base revision is not redispatched and an unconverted repo returns the migrate instruction (`test_closed_at_base_is_not_redispatched`, `test_unconverted_repo_names_migrate`)."]
checks = ["python3 -m unittest discover -s pi-autowork/engine; python3 scripts/check.py"]
exclusions = ["Integration's change classification is TOOLSET-302-33; the runner service, fleet view and TUI are TOOLSET-299-d9; no fallback reader for TODO.md."]
+++

- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Payoff: Remove the second parse of TODO.md and goals.json from selection, dispatch and integration.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [selector](pi-autowork/engine/task_execution.py); [dispatch](pi-autowork/engine/parallel_dispatch.py); [integration](pi-autowork/engine/parallel_integrate.py) (`PLANNING_FILES`, `planning_only`); [claims](pi-autowork/engine/parallel_claims.py); [state](pi-autowork/engine/parallel_state.py); [status](pi-autowork/engine/parallel_status.py); [retry](pi-autowork/engine/retry_selection.py).
- Evidence: Offline only: on task-store-v2 (merged 38999d67) the engine selects, dispatches and integrates from tasks/ at a pinned commit; admitted_contract_changed holds contract edits (test_contract_edit_invalidates_admitted_work, test_rank_edit_keeps_admitted_work, test_worker_cannot_grant_authority_via_task_edit pass); closure is one commit (test_closure_is_one_commit, test_replayed_closure_is_a_noop, test_crash_mid_closure_resumes_once); mutants killed; no live qualification.
- Ownership: Toolset coordinator.
