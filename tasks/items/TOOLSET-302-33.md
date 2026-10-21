+++
schema = 1
id = "TOOLSET-302-33"
title = "Integration judges task edits by contract hash, not by path"
short = "Contract-hash change classification"
status = "open"
goal = "TASK-STORE"
section = "Needs decision"
rank = 3000
depends_on = ["TOOLSET-298-c2"]
touches = ["pi-autowork/engine/parallel_integrate.py", "pi-autowork/engine/task_store.py", "pi-autowork/engine/test_parallel_integrate.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "(1) Classify a `tasks/` change by comparing records at base, incoming and current: rank, title, short, notes and Now/Next are bookkeeping; a worker-authored change that adds a task or edits any task's authority fields (resources, live authorization, kind, ownership, checks) is never bookkeeping: integration refuses it or holds it for the coordinator, and authority is read only from the base revision; a contract-hash change to the task being integrated (acceptance, checks, dependencies, Touches, authority fields, Needs decision, superseded) requires revalidation or a hold. (2) `done` survives a merge only if the contract hash equals the one that was verified (status is outside the hash, so a plain closure keeps it); otherwise the task returns to open with the reason; done and superseded are checked as explicit status transitions. (3) BLOCKERS.md and TODO.archive.md stay path-classified planning files."
acceptance = ["`test_rank_edit_on_base_keeps_the_remerge_shortcut`, `test_acceptance_edit_on_base_requires_revalidation` and `test_done_with_a_changed_contract_is_reopened` and `test_worker_cannot_grant_authority_via_task_edit` (a worker branch that adds a task with `live_authorization = true` or extra resources or checks, or grants them to another task, is refused or held, never merged as bookkeeping) pass."]
checks = ["python3 -m unittest discover -s pi-autowork/engine -p test_parallel_integrate.py; python3 scripts/check.py"]
exclusions = ["No distributed leases; one integration coordinator per repository."]
+++

- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Payoff: Stop a clean Git merge from closing a task under acceptance nobody verified.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [integration](pi-autowork/engine/parallel_integrate.py) (`PLANNING_FILES`, `planning_only`, the remerge shortcut, the post-verification contract recheck).
- Evidence: `planning_only` treats `docs/` and the planning files as safe to remerge without rerunning checks; simply adding `tasks/` there would let an acceptance or check edit ride through as "planning only". File-per-task also allows clean textual merges of one task's acceptance edit and another branch's `status = "done"`.
- Ownership: Toolset coordinator.
