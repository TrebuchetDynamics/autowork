# More parallel workers, and more than one worker per task

Status: Accepted (Plan For Me, 2026-10-19). Owner request: "more parallelism and even more
workers, even one task can launch more than one worker if useful."
Evidence: [multi-agent orchestration research](../research/multi-agent-orchestration.md).

## Goal

Keep the host's spare capacity busy with useful work. That means many workers across
runners, and several workers on one task when that shortens it, without more merge
conflicts or a saturated host.

- **Non-goals:**
  - Shared-tree concurrent editing, as in CRDT workspaces.
  - Agents negotiating with each other.
  - A new orchestration service or daemon.
  - Changing review or full-check rules.
- **Anti-goals.** It's a failure, even if it works, when:
  - more workers produce more merge conflicts or more held tasks;
  - one runner's fan-out starves another runner's first worker;
  - two attempts of one task both land;
  - a worker's helpers edit outside its worktree.

## Decisions (the planner's calls)

1. **One host-wide worker pool**, shared by every runner, instead of per-runner caps and
   a load-average gate.
   - **Why:** caps of 8 are idle while the CPU gate refuses everyone. This uses the same
     `flock` slots as ports (shipped) and check slots (TOOLSET-228-0c): no daemon, and a
     dead holder frees its slot.
   - **CPU work moves to check slots.** CPU-heavy work (full checks, and from now on
     the long suites workers run) takes check slots. Model-bound workers take pool
     slots. The load average then only stops new workers at 1.5× the CPU count, as a
     safety net.
2. **Fair share.** The next free pool slot goes to the runner with ready work and the
   fewest running workers. A runner's first worker is never refused by the pool
   (TOOLSET-222-e1 keeps that).
3. **Spare capacity goes inside tasks only when no task is waiting for a slot.**
   - **Order:** whole tasks first, then helpers, then parallel attempts.
   - **Why:** a ready task finishing is worth more than a second attempt at one that's
     already running.
4. **Helpers, not swarms.**
   - **What a worker gets:** `autowork-helper <role> <prompt>` runs a bounded Pi job in
     the worker's own worktree:
     - **look:** read-only research;
     - **test:** run a check and triage what fails;
     - **review:** a critique of the current diff.
   - **What a helper can't do:** edit files or commit.
   - **Limits:** at most 3 helpers per worker at a time, each one taking a pool slot.
     That bounds cost and keeps one writer per worktree. The research found that
     task-specific subagents gave the most stable gains; long, separable tasks gain
     most.
5. **Parallel attempts only where a second attempt is already justified:** a task on its
   second attempt, or a task marked `Attempts: 2`.
   - **How:** a second worker runs in its own `-p2` worktree on the fallback model.
   - **Which one lands:** the first commit to pass review lands; the other is stopped
     and its work set aside, never merged.
   - **Why:** different models give genuinely different attempts. Only one may land,
     because cross-agent conflicts are common.
6. **Split before you fan out.** TOOLSET-156-75 gains a trigger: when at least two pool
   slots are idle and a ready task's Touches fall into two or more disjoint groups, the
   split planning job runs before dispatch. Disjoint scopes planned up front lift clean
   integration from 1/9 to 9/9 scenarios.
7. **Plans are wide.** The planning craft asks for independent tasks with disjoint
   Touches. A dependency chain longer than three steps needs a stated reason.
8. **Integration keeps up.** None of this helps if one review at a time lands the work.
   TOOLSET-230-bf, then TOOLSET-231-49 (the speculative merge queue), stay first among
   the integration work and are dependencies of decision 5.
   - **Recommended, the owner's setting:** once 230-bf lands, remove this repository's
     one-worker setting, since 27 of its tasks wait for that slot.

## Alternatives rejected

- **Raising per-runner caps only.** That's idle while the CPU gate refuses, and adds
  load once the gate opens.
- **A central scheduler daemon.** Another process to keep alive. `flock` slots already
  share ports and check slots across runners.
- **Several agents editing one worktree** (shared claims, as in AgentRoom). Coordination
  inside a tree needs new protocol, and the evidence favours disjoint scopes planned up
  front.
- **Best-of-N on every task.** It costs N times as much for small fixes, where the
  model, not the orchestration, decides the result.

## Tasks

| Task | Outcome | Depends on |
|---|---|---|
| Host worker pool | Every runner takes a host-wide pool slot per worker. The load gate only applies at 1.5× CPUs. Fair share across runners. | TOOLSET-228-0c, TOOLSET-222-e1 |
| Worker check slots | Workers' long test runs take a host check slot through `autowork-run`. | TOOLSET-228-0c |
| Worker helpers | `autowork-helper look/test/review`, read-only, at most 3 per worker, using spare pool slots only. | Host worker pool |
| Parallel attempts | A second attempt, or `Attempts: 2`, runs a second worker on the fallback model when spare slots exist. The first to pass review lands; the other is set aside. | Host worker pool, TOOLSET-230-bf |
| Split on spare capacity | A new trigger for TOOLSET-156-75: idle slots plus disjoint Touches groups. | Host worker pool |
| Wide plans | The planning craft and the docs maintainer prefer independent tasks. A chain longer than three needs a reason. | None |

The task bodies below go into TODO.md with `goals.py add-task`, one ID each, once the
owner's uncommitted planning edits there are committed (2026-10-19: another session was
editing TODO.md and goals.json). Until then they are accepted but not yet queued. The
builder check ran on them, and its five questions are answered in the bodies.

## Task bodies

### POOL — Every worker on the host takes a slot from one shared worker pool, shared fairly among runners
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decisions 1-2); [research](docs/research/multi-agent-orchestration.md); [resource gate](skills/autowork/scripts/parallel_dispatch.py) (`resource_gate`, `capacity`, `HARD_LIMIT`, `port_lease` for the flock pattern); TOOLSET-228-0c (check slots).
- Evidence (2026-10-19 05:30): nine runners allowed up to 65 workers and ran 9, with 119 tasks waiting; each runner's gate refuses another worker at load average >= CPUs (22), and the load stayed 22-50 all day, so caps of 8 sat idle while one runner's 27 ready tasks waited for its single slot.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/coordinator.py, pi-autowork/pi_autowork/cli.py, pi-autowork/pi_autowork/fleet_view.py, tests/test_pi_autowork.py, docs/reference.md, CHANGELOG.md
- Scope: (1) Before launching a worker, dispatch takes one of `PI_AUTOWORK_HOST_WORKERS` host-wide pool slots (default: 2 × CPU count), each a `flock`ed file under the user's runtime directory, passed to the worker like its port lease, so it frees itself when the worker exits. (2) Fair share: each runner writes `pool/<repository key>.json` in the same runtime directory on each dispatch pass (live workers, ready tasks, updated_at; stale after 5 minutes). A runner takes a freed slot only if no fresh record shows ready work with fewer live workers than its own; a runner's first worker is never refused by the pool. (3) `HARD_LIMIT` becomes 16 and remains a per-runner ceiling; `--workers` accepts 1-16 (default 8 unchanged) and the coordinator passes the engine's limit instead of a literal 8. (4) The load-average gate refuses a new worker only at 1.5 × the CPU count; memory and disk gates are unchanged. (5) Waiting for a pool slot shows as `waiting for a host worker slot (N of M in use)`, a wait, not stalled.
- Acceptance: In fixtures: with a pool of 2 and two repositories, the third worker waits until one exits, then starts; a killed worker frees its slot; a runner with three live workers yields the next slot to a runner with one; a runner's first worker starts with the pool full; load at 1.2 × CPUs no longer refuses a worker; the status line names the pool.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: TOOLSET-228-0c, TOOLSET-222-e1.
- Ownership: Toolset coordinator. Supersedes the load-average part of TOOLSET-118-68; its cgroup and process-tree parts stay there.
- Exclusions: No central daemon; no change to check slots, review or the full check; no per-task fan-out (separate tasks).
- Planner's call: a host-wide flock pool shares capacity the way ports and check slots already do, and CPU-heavy work is bounded by check slots, so the load average becomes a safety net, not the scheduler.

### RUN — A worker's long test runs take a host check slot
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decision 1); TOOLSET-228-0c (runner check slots); [worker prompt](skills/autowork/scripts/parallel_dispatch.py) (`prompt`, `full_check_rule`).
- Evidence: with more workers, CPU load comes from the suites they run, not from the model calls; TOOLSET-228-0c bounds only the runner's own full checks.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/autowork_run.py, pi-autowork/pi_autowork/coordinator.py, docs/reference.md, CHANGELOG.md
- Scope: (1) Add `autowork-run <command…>` (on the worker's PATH, a small standard-library script): it takes one of `PI_AUTOWORK_WORKER_CHECK_SLOTS` host-wide worker check slots (default: CPU count / 4, at least 2; separate from the runner's own TOOLSET-228-0c slots, same flock mechanism and directory), then starts the command, releases the slot when it ends and returns its exit code; waiting prints one line. The command's time limit (`PI_AUTOWORK_COMMAND_TIMEOUT`, `stop_stuck_commands`) counts from when it starts, after the slot: the waiting wrapper is not a stuck command. (2) The worker prompt says to run any suite or build expected to take more than two minutes through `autowork-run`, and focused tests directly. (3) The worker report notes how long it waited for slots.
- Acceptance: In fixtures with 1 check slot: two workers' `autowork-run` commands run one after the other; a killed holder frees the slot; the exit code passes through; a wrapper waiting longer than the command limit is not stopped; the prompt contains the rule.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py; python3 scripts/check.py
- Dependencies: TOOLSET-228-0c.
- Ownership: Toolset coordinator.
- Exclusions: No enforcement on commands run without the wrapper; no change to focused tests.
- Planner's call: a voluntary wrapper on PATH needs no sandbox; workers already follow the prompt's TMPDIR and port rules, and the cost of ignoring it is only load, which the 1.5 × CPU safety gate still bounds.

### HELPER — A worker can run up to three read-only helpers for its task
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decisions 3-4); [research](docs/research/multi-agent-orchestration.md) (task-specific subagents gave the most stable harness gains; dynamic concurrency pays on long-horizon tasks and has 13 failure modes); [Pi job runner](pi-autowork/pi_autowork/pi_runtime.py) (`job`).
- Evidence: Pi has no built-in subagent tool (`pi --help`, 2026-10-19); the worker prompt already allows "your host's own subagents", which Pi workers cannot use.
- Touches: skills/autowork/scripts/autowork_helper.py, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, pi-autowork/pi_autowork/pi_runtime.py, pi-autowork/tests/test_pi_runtime.py, docs/reference.md, CHANGELOG.md
- Scope: (1) `autowork-helper look|test|review "<question>"` on the worker's PATH runs one Pi job in the worker's worktree with read-only tools (look: read, grep, find, ls; test: plus bash, told never to edit; review: read-only, given `git diff` of the worktree), its own session and a 900 s limit, and prints the helper's answer. (2) It takes a host pool slot (from the POOL task) and refuses with a clear line when none is free, when the worker already has three helpers running, or when a fresh POOL record of any runner shows a ready task without a worker: a helper never takes a waiting task's first slot. (3) After it ends, the worktree must be unchanged; a helper that changed it is reported and its changes are left for the worker to inspect. (4) The worker prompt says when to use helpers: independent questions about the code, triaging a long test failure, reviewing the diff before committing; never for the edit itself.
- Acceptance: In fixtures with a fake Pi: a helper answer is printed; a fourth concurrent helper is refused; a helper with no free pool slot is refused at once; a helper that edits a file is reported; the prompt contains the rule.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py pi-autowork/tests/test_pi_runtime.py; python3 scripts/check.py
- Dependencies: POOL.
- Ownership: Toolset coordinator.
- Exclusions: No helper that edits or commits; no helper of a helper; no shared tree between workers.
- Planner's call: one writer per worktree keeps integration as it is; read-only helpers give the measured gains of task-specific subagents without the shared-tree coordination problems.

### ATTEMPT — A second attempt runs two workers when spare slots exist, and the first to pass review lands
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decisions 3, 5); [research](docs/research/multi-agent-orchestration.md) (cross-agent PRs conflict far more; per-step model choice); [retry](skills/autowork/scripts/parallel_integrate.py) (fresh `-r2` attempt); [set-aside](skills/autowork/scripts/parallel_integrate.py) (`set_aside`); [fallback model](pi-autowork/pi_autowork/pi_runtime.py).
- Evidence: a task that needs a second attempt already failed once; today the second attempt runs alone on the primary model.
- Touches: skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py, skills/autowork/scripts/parallel_integrate.py, skills/autowork/scripts/test_parallel_integrate.py, skills/autowork/scripts/parallel_state.py, pi-autowork/pi_autowork/coordinator.py, tests/test_pi_autowork.py, docs/reference.md, CHANGELOG.md
- Scope: (1) When a task starts its second attempt, or its entry says `Attempts: 2`, and at least one pool slot would still be free after every waiting task's first worker (POOL records), a sibling worker starts in its own `autowork-<task>-p2` worktree from the same baseline on the fallback model. It is its own slot, `<task>--p2`, with `sibling_of: <task>` (a new slot kind, no migration); status, exhaustion and set-aside treat the pair as one task. (2) Each reports as usual; the first commit to pass review integrates (when both are in one integration batch, the earlier report); the sibling is stopped, and its worktree and branch are set aside, never merged. (3) If both fail, the task is held once, with both reasons. (4) Status shows both workers under the task.
- Acceptance: In fixtures: a second attempt with a free slot starts two workers on different models; the first passing commit lands and the other is set aside; with no spare slot only one starts; both failing gives one hold with both reasons; a first attempt without `Attempts: 2` starts one worker.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_dispatch.py skills/autowork/scripts/test_parallel_integrate.py; python3 scripts/check.py tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: POOL, TOOLSET-230-bf.
- Ownership: Toolset coordinator.
- Exclusions: No more than two attempts at once; never on a first attempt unless the entry asks; never merging both.
- Planner's call: a second attempt is where a different try is worth paying for, and a different model makes the two tries genuinely different; landing only one avoids the conflicts parallel agents produce.

### SPLIT — Spare capacity triggers the task split before dispatch
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decision 6); [research](docs/research/multi-agent-orchestration.md) (disjoint scopes planned up front: clean integration 1/9 → 9/9); TOOLSET-156-75 (the split planning job and its invariants).
- Evidence: most waiting tasks across the fleet wait on dependencies while slots are free (2026-10-19 05:30).
- Touches: pi-autowork/pi_autowork/coordinator.py, skills/autowork/scripts/parallel_plan.py, skills/autowork/scripts/test_parallel_plan.py, tests/test_pi_autowork.py, CHANGELOG.md
- Scope: (1) Add trigger (d) to TOOLSET-156-75's split job: at least two pool slots are idle for one stall threshold, and a ready task's declared Touches fall into two or more groups with no common directory and no shared serial path. (2) At most one split job per runner at a time and once per task, with 156-75's invariants (Acceptance preserved, 2-5 subtasks, validated).
- Acceptance: In fixtures: idle slots plus a task touching `a/` and `b/` trigger one split job; a task touching one directory does not; with no idle slots nothing is split; a task is split at most once.
- Checks: python3 scripts/check.py skills/autowork/scripts/test_parallel_plan.py tests/test_pi_autowork.py; python3 scripts/check.py
- Dependencies: TOOLSET-156-75, POOL.
- Ownership: Toolset coordinator.
- Exclusions: No split of a task with Resources: exclusive or live; no change to 156-75's other triggers.
- Planner's call: splitting into disjoint scopes is the form of parallelism the evidence supports best, and idle slots are the moment it pays.

### WIDE — Plans prefer independent tasks; a long dependency chain needs a reason
- Status: open
- Goal: PI-RUNNER
- Payoff: Run Autowork continuously through Pi with a model fallback.
- Sources: [plan](docs/plans/2026-10-19-more-parallel-workers.md) (decision 7); [planning craft](skills/shared/PLANNING-CRAFT.md) (`Plan for an unattended worker`); [docs maintainer](pi-autowork/pi_autowork/maintainer.py) (`PROMPT`).
- Evidence: across the fleet, dependency waits were the most common reason on every runner but one (2026-10-19 05:30).
- Touches: skills/shared/PLANNING-CRAFT.md, pi-autowork/pi_autowork/maintainer.py, pi-autowork/tests/test_maintainer.py, CHANGELOG.md
- Scope: (1) The planning craft adds: prefer tasks with disjoint Touches that can run at once; a chain longer than three tasks names why each link depends on the last; split a task that touches unrelated areas. (2) The builder check asks which saved tasks could run in parallel and why the rest cannot. (3) The docs maintainer's re-sort, when it unblocks a chain, prefers splitting off independent parts.
- Acceptance: The craft and the maintainer prompt contain the rules; the maintainer test asserts the prompt line.
- Checks: python3 scripts/check.py pi-autowork/tests/test_maintainer.py
- Dependencies: None.
- Ownership: Toolset skills.
- Exclusions: No automatic rewriting of existing plans.
- Planner's call: the cheapest parallelism is a plan whose tasks do not wait on each other.
