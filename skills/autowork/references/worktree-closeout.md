# Worktree closeout

Autowork worktrees are temporary implementation spaces, not the final delivery
location. There is no hard limit on useful active worktrees: 20 or 50 may be valid
while workers need them. Minimize abandoned finished worktrees instead of limiting
concurrency or deleting active work.

## Integrate first

Record the canonical checkout, its actual default branch (`main` or `master`, not
both), the task worktree/branch and ownership when creating a worktree. Reuse a
suitable existing task worktree before creating another. Never rename a repository's
branch or switch another session's checkout to manufacture the desired target.
An explicitly different repository integration policy still applies.

Before ending a worktree-backed task, complete required checks/review, integrate
through the repository's supported path and verify the delivered commit on the
canonical default branch. Serialize canonical writes and preserve unrelated edits.
A local task-branch commit is not integration. No push or remote merge authority
is granted by cleanup. If integration is blocked, report **integration pending**,
retain the candidate and continue only independently authorized work.

## Remove finished worktrees with the helper

`scripts/worktree_closeout.py` removes finished worktrees deterministically. The
task helper (`owner_cycle.py CONSUMER --apply`) runs it on every task claim, so
worktrees left by earlier tasks, sessions or hosts are cleaned up without a model
having to remember. After integrating, run it for the task's own worktree from the
canonical checkout; naming a worktree skips the 30-minute grace period:

```sh
python3 <this-skill-directory>/scripts/worktree_closeout.py "$CANONICAL" --worktree "$TASK_WORKTREE" --apply
```

Without `--worktree` it considers every registered worktree of the repository;
without `--apply` it only reports. A worktree is removed only when every check
passes, so nothing it removes holds unique work:

1. The canonical checkout is on `main` or `master`; it is never a candidate.
2. The worktree is not locked, not a parallel slot that is not yet closed (the
   coordinator cleans those) and not under the pi-autowork state directory.
3. Its HEAD is an ancestor of the default branch; unmerged work is kept. A squash
   or cherry-pick is not an ancestor and is kept too: ancestry failure alone never
   authorizes deletion.
4. `git status --ignored` shows no tracked or untracked change and no ignored file
   other than regenerable caches (`__pycache__`, `*.pyc`, `.pytest_cache`,
   `.mypy_cache`, `.ruff_cache`, `.hypothesis`). Check receipts, logs and other
   ignored files keep it.
5. No process has its working directory, an open file or an argument inside it,
   and process activity can be read (`/proc`); unknown activity keeps everything.
6. Its HEAD, reflog and ORIG_HEAD have not changed for 30 minutes, unless named.

It then runs ordinary `git worktree remove` (never `--force`), reads the
registration back, and deletes the worktree's branch with `git branch -d` when the
branch still points at the removed HEAD. A registration whose directory is already
gone is forgotten the same way when its HEAD is integrated. It never runs blanket
`git worktree prune`, `rm -rf` or `git branch -D`. Every kept worktree is reported
with its reason; report those as **cleanup pending**. An idle agent session whose
working directory is a removed worktree must return to the canonical checkout.

The helper decides from Git and process evidence only. It is not a runtime guarantee
that a cron model reaches closeout, and fixture checks do not qualify live cleanup.

## Report and resume

Report integration and cleanup separately: canonical branch/commit, exact removed
paths, and any **cleanup pending** path with its concrete preservation reason.
Implementation acceptance may pass while workspace cleanup remains pending; never
claim the complete worktree closeout is finished until removal and default-branch
readback succeed. The next task claim retries pending cleanup automatically; a
worktree that fails any check above is kept however old it is.
