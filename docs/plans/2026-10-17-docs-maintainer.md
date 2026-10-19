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

## Remaining implementation slices (2026-10-19)

Status: Accepted

The owner chose to finish the remaining scope in smaller verified slices on
2026-10-19 and reiterated that the timed-out parent needs splitting. The previous
Work batches prose did not create independently selectable tasks. This split now
books real child outcomes; original 164-f1 acceptance and partial-delivery history
remain the aggregate closeout, not a claim that splitting implements the feature.

- TOOLSET-265-16: Route planning-file writes through the docs maintainer without losing owner edits.
- TOOLSET-266-7a: Batch remaining docs-maintainer triggers and ask only unresolved owner questions.
- TOOLSET-267-a0: Bound docs-maintainer repair loops and report actual changed task bodies.

The children form one ordered chain; only the first is Now, successors are Next.
Place the first at the original parent frontier and preserve the relative order
of unrelated work. The parent depends on every child and performs only aggregate
verification/closeout after they finish. Children do not depend on the parent.
The scope excludes duplicate implementation of already delivered trigger/repair
behavior. 149/150/151 retain format compatibility and conversion ownership; no
child or this pass converts the ledger.

Planner decisions: deterministic projection uses the same guarded maintainer-owned
planning path without requiring a new model call; substantive jobs remain batched
and event-driven. Daily repair accounting uses UTC calendar days and existing
source-bound receipts; it never resets task execution budgets or treats the
maintainer's own edits as external permission for another repair. Original owner
edit, no-acceptance-change, no-profile/service/cron and required check/review
boundaries remain. These implementation regressions are planned, unrun.

Source inspection found update_questions still writes the generated block directly,
maintainer.triggers lacks explicit refused-reorder/closeout/stale-question events,
and maintain still initially detects some changes by ID mention. Existing item
receipts and post-merge body comparison are reused rather than replaced. The old
164-f1 worktree and branch are absent; no current slot exists for that task. Do not
promise recovery of unlocated dirty files: reconcile current delivered source and
retained history before implementing the missing deltas.

215-91 is unrelated to these children and remains owner-deferred until its native
safety probe passes on supported Hermes. That decision authorizes no upgrade,
weaker rule or upstream patch; no dependency on it is introduced.
