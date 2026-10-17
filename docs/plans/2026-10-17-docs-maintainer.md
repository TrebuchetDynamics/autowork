# Docs maintainer worker

Status: Accepted

Accepted by the owner on 2026-10-17.

## Why

Many holds are not product questions. A worker stops on an ambiguous contract, a
wrong Touches list, a missing check or a stale priority, and the fix is to restate
the task and run it again. Today that lands in `BLOCKERS.md` for the owner, or
waits for someone to run `/blockers`. Planning repair is spread over
TOOLSET-141-c4 (stall-only contract repair), TOOLSET-146-bc (closeout Docs Sync)
and the repair half of `/blockers`. Owner direction: "each repo autowork needs
another worker specifically to work on tasks docs itself. blockers, resorting,
replanning ambiguity etc. many blockers are solved by reprompting. this worker can
run docs_sync too. its permanent task can be DOCS-MAINTAINER. we have a plan to use
docs/tasks heavily, we need that now."

## Decisions

1. **A runner role, not a queue task.** Every runner has one standing
   `DOCS-MAINTAINER` worker, shown in status, `autowork ls` and the TUI beside the
   task workers. It is never a `TODO.md` entry: a task that never closes would
   break done, archive and priority handling. It does not count toward the task
   worker cap (`PI_AUTOWORK_WORKERS`).
2. **Event-driven, never polling.** It starts only on a trigger: a task held for a
   planning cause (contract, scope, Touches, checks, dependencies), a worker
   blocker, an incomplete or ambiguous contract, priority drift, a closed task whose
   docs may need syncing, or stale questions in `BLOCKERS.md`. Unchanged input
   never restarts it. With no trigger it makes no model call, so an idle runner
   still costs no tokens.
3. **Sole writer of planning files.** It owns `TODO.md`, `goals.json`, `BLOCKERS.md`
   (the runner block and repairs outside it) and `docs/tasks/`. The coordinator
   stops editing them itself and hands each change to the maintainer, except the
   mechanical writes `goals.py` already performs (reorder records, closeout
   archive). Owner edits always win: the maintainer merges around uncommitted or
   newer owner changes and never reverts them.
4. **What it may change on its own,** from repository evidence (the task's Sources,
   accepted plans, the worker's report and the candidate): restate a held task's
   contract and requeue it so the same candidate is reverified or re-prompted;
   correct Touches, checks and dependencies; split an oversized task; re-sort to
   unblock dependency chains, with each move's reason in the commit message;
   supersede duplicates. It may not change product scope or acceptance, grant
   authority or credentials, or move a task above the owner's own top picks. Those
   stay `BLOCKERS.md` questions, written only after a repair attempt could not
   resolve them.
5. **One owner for planning repair.** The maintainer task supersedes TOOLSET-141-c4,
   runs the conditional Docs Sync pass that TOOLSET-146-bc planned for closeout
   (146-bc keeps the per-task doc-impact evidence in worker reports), and takes
   over the routine-repair half of `/blockers`, which keeps only genuine owner
   questions. TOOLSET-153-64 (hold for repository agents) is unchanged.
6. **`docs/tasks/` now.** TOOLSET-149-df moves up directly behind the maintainer
   task, and its exclusion against converting this repository is lifted: this
   repository converts first, through 149-df's own guarded writer. Other
   repositories convert later, each through its own runner. The maintainer is the
   writer of `docs/tasks/` records.

## Planner's calls

- The maintainer runs with the runner's primary model and the docs-sync and
  plan-for-me skills, in its own worktree, and integrates through the normal
  verified merge like any candidate, with `goals.py validate` and backlog-check as
  its checks.
- One maintainer run handles every pending trigger at once, so a burst of holds
  costs one run, not one per hold.
- Its run history and results appear in status as `DOCS-MAINTAINER` with the last
  trigger, outcome and the tasks it changed.
