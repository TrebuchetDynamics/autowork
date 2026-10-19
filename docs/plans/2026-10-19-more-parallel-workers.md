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
| TOOLSET-260-ae: host worker pool | Every runner takes a host-wide pool slot per worker. The load gate only applies at 1.5× CPUs. Fair share across runners. | TOOLSET-228-0c, TOOLSET-222-e1 |
| TOOLSET-261-15: worker check slots | Workers' long test runs take a host check slot through `autowork-run`. | TOOLSET-228-0c |
| TOOLSET-262-13: worker helpers | `autowork-helper look/test/review`, read-only, at most 3 per worker, using spare pool slots only. | TOOLSET-260-ae |
| TOOLSET-263-94: parallel attempts | A second attempt, or `Attempts: 2`, runs a second worker on the fallback model when spare slots exist. The first to pass review lands; the other is set aside. | TOOLSET-260-ae, TOOLSET-230-bf |
| TOOLSET-264-39: split on spare capacity | A new trigger for TOOLSET-156-75: idle slots plus disjoint Touches groups. | TOOLSET-260-ae |
| TOOLSET-259-ca: wide plans | The planning craft and the docs maintainer prefer independent tasks. A chain longer than three needs a reason. | None |

The tasks are queued in TODO.md (Next) and goals.json; their bodies there are canonical.
