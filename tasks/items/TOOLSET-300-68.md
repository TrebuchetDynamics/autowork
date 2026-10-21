+++
schema = 1
id = "TOOLSET-300-68"
title = "Closing a task publishes one receipt and status commit exactly once"
short = "Idempotent closure receipts"
status = "done"
goal = "TASK-STORE"
section = "Needs decision"
rank = 5000
depends_on = ["TOOLSET-302-33"]
touches = ["pi-autowork/engine/finish_task.py", "pi-autowork/engine/parallel_integrate.py", "pi-autowork/engine/task_store.py", "pi-autowork/engine/test_finish_task.py", "pi-autowork/engine/test_parallel_integrate.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "(1) Closure writes `status = \"done\"` plus `tasks/evidence/<ID>.toml` (check commands, results, commit, review, no private paths or names) in one commit through the existing journal. (2) Replaying a closure whose commit already exists is a no-op; a crash between journal steps resumes to exactly one commit. (3) Receipts are sanitized by the same rules as the public changelog. (4) The receipt names the exact candidate commit and tree that passed verification; the closure commit may change only that task's file and its receipt, and delivery to the default branch is recorded separately from closure."
acceptance = ["`test_closure_is_one_commit`, `test_replayed_closure_is_a_noop`, `test_crash_mid_closure_resumes_once` and `test_receipt_has_no_private_paths` pass."]
checks = ["python3 -m unittest discover -s pi-autowork/engine -p test_finish_task.py; python3 -m unittest discover -s pi-autowork/engine -p test_parallel_integrate.py; python3 scripts/check.py"]
exclusions = ["TODO.archive.md is not written by closure on a converted repository."]
+++

- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Payoff: Make closure replay-safe, so a crash or retry never double-closes or loses a receipt.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [closure](pi-autowork/engine/finish_task.py); [integration journal](pi-autowork/engine/parallel_integrate.py); [check receipts](pi-autowork/engine/check_receipt.py).
- Evidence: Offline only: on task-store-v2 (merged 38999d67) Docs Sync's goals/plan-lint/planning-merge/todo-archive modules, the pending TODO parser and Touches-inference CLI are removed; skills and adapters use autowork tasks verbs (each verb and flag checked against the CLI); README, docs and CHANGELOG describe the store; no live qualification.
- Ownership: Toolset coordinator.
