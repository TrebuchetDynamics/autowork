+++
schema = 1
id = "TOOLSET-299-d9"
title = "The runner and the fleet view read only tasks/"
short = "Runner and fleet view cutover"
status = "done"
goal = "TASK-STORE"
section = "Needs decision"
rank = 4000
depends_on = ["TOOLSET-302-33", "TOOLSET-298-c2"]
touches = ["pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/worker.py", "pi-autowork/pi_autowork/maintainer.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/questions.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/touches_inference.py", "pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/command.py", "tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "(1) Readiness requires `tasks/`; an unconverted repository shows \"run autowork migrate\" in `autowork status` and the TUI and its runner idles at zero tokens. (2) Plan-change wakeups use a task-tree signature (the `tasks/` tree hash at HEAD plus `git status` of `tasks/`), not file or directory mtimes, since editing a nested file need not change its directory's timestamp. Worker and maintainer planning-only checks follow TOOLSET-302-33's classification. (3) Task counts, statuses and questions come from TaskStore; the TUI shows pending uncommitted task edits as pending. (4) The docs maintainer writes through the TaskStore writer."
acceptance = ["tests cover: an unconverted repo reports the migrate instruction and starts no worker (`test_unconverted_repo_idles_with_migrate_hint`); an in-place edit of an existing task file wakes the coordinator (`test_nested_task_edit_wakes_coordinator`); fleet view counts match TaskStore on a fixture (`test_fleet_counts_match_store`)."]
checks = ["python3 -m unittest discover -s tests; python3 scripts/check.py"]
exclusions = ["No change to which fleet repositories run; converting them is the owner's step."]
+++

- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Payoff: Keep the runner, readiness checks and the TUI consistent with the engine's single store.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [coordinator](pi-autowork/pi_autowork/coordinator.py) (plan-file change detection); [worker](pi-autowork/pi_autowork/worker.py) (`PLANNING_FILES`); [maintainer](pi-autowork/pi_autowork/maintainer.py); [fleet view](pi-autowork/pi_autowork/fleet_view.py) (`REQUIRED`); [questions](pi-autowork/pi_autowork/questions.py); [TUI](pi-autowork/pi_autowork/tui.py); [Touches inference](pi-autowork/pi_autowork/touches_inference.py); [service](pi-autowork/pi_autowork/service.py).
- Evidence: Offline only: on task-store-v2 (merged 38999d67) test_unconverted_repo_idles_with_migrate_hint, test_nested_task_edit_wakes_coordinator and test_fleet_counts_match_store pass with all tests/test_pi_autowork.py and pi-autowork/tests; plan_signature includes git status of tasks/ (mutant killed); no live qualification.
- Ownership: Toolset coordinator.
- Dependencies: TOOLSET-298-c2, TOOLSET-302-33.
