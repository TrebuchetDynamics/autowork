# Engine graph review

Status: Accepted

Accepted by the planner on 2026-10-17 under owner delegation ("use graphify to
understand in another angle pi-autowork and detect obvious engineering issues so
we can improve"). Every decision below is the planner's call.

## Engine graph review findings

Status: Accepted

A code graph of `pi-autowork/` and `skills/autowork/scripts/` (graphify AST
extraction, no model: 136 files, 2967 nodes, 7728 edges), checked against the
running fleet, gave five findings. Production code is 17.5k lines in 59 modules.

1. **A status read can say nothing is running while work runs.** `--parallel-status`
   takes the engine's `writer.lock` without waiting (`task_execution.lock`, `wait=0`).
   When any engine command holds it, the read answers `ACTION_REQUIRED` with no
   tasks (reproduced on this repository's session: `[Errno 11] Resource temporarily
   unavailable`). The coordinator reads that as an empty pool, so `in_flight()` is
   false while workers run, and the decisions it guards (following main, merging,
   toolset updates) can act under running work. Task: TOOLSET-200-c1.
2. **Status reads were most of the coordinator's engine traffic.** Each `status()`,
   `tasks()` and `in_flight()` call started an engine process (1.5 to 3.6 s of CPU),
   about 10 times in 30 s per runner. A 5-second snapshot cut that to about 2 per
   runner (52e0d45, 91de6b9); no task remains.
3. **An idle runner churns its session.** With an empty queue, a runner creates a
   session worktree, finds nothing, and removes it, every interval (one fleet runner:
   a new `pi-autowork/<timestamp>` session each minute, still on the current release).
   Task: TOOLSET-201-5e.
4. **About 20 engine modules belong to the retired owner cycle.** Only their own
   tests, `tests/fixtures/legacy_owner_cycle.py` and historical references use
   them; the live skills run only `owner_cycle.py` (the parallel engine) and
   `worktree_closeout.py`. They are roughly 5k production and 8k test lines that
   every full check still runs. Task: TOOLSET-202-9a.
5. **Structure, recorded for TOOLSET-115-bf, no task now.** `coordinator.py` is a
   1805-line class with 85 graph edges and about 15 separate engine call sites.
   Seven engine modules (`task_execution`, `parallel_dispatch`, `parallel_claims`,
   `parallel_integrate`, `parallel_state`, `parallel_status`, `worktree_closeout`)
   import each other in one cycle. `git()` is defined in 9 modules. These cost
   readability, not runtime, and belong to the lifecycle redesign.

## Planner's calls

- A status read waits briefly for the lock instead of reading without it: slot files
  and journal appends are written under that lock, and a read between them can be
  inconsistent.
- A failed status read is "unknown", which the coordinator treats as busy: waiting
  one cycle costs little, acting under running work can lose it.
- Retired modules are deleted, not kept behind a flag (owner rule: no compatibility
  shims). Modules a live skill, adapter, script or the live engine still uses stay,
  whatever the graph says (`finish_task` for Autoresearch, `audit_profiles` and
  `cron_output` for the profile scripts, the discovery helpers).
- Structural findings (5) go to TOOLSET-115-bf, not into separate refactor tasks.
