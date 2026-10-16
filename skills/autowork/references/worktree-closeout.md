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

## Remove only finished, owned worktrees

After verified integration, automatically clean up the task worktree and temporary
integration worktree created for this work, without another permission round:

1. Confirm the exact path and recorded ownership; never select every worktree or
   match by age/name alone. Never remove the canonical checkout.
2. Inspect actual processes, open writable files, execution leases and Git worktree
   locks. Keep active, locked and unknown-ownership worktrees. An old PID or a clean
   Git status alone does not prove that a worker has stopped.
3. Verify its exact HEAD is integrated into the canonical default branch. Keep
   unmerged work. A squash/cherry-pick needs source-bound equivalence evidence;
   ancestry failure alone never authorizes deletion or discarding the branch.
4. Inspect tracked edits, untracked files and ignored files. Retain anything with
   unfinished work, receipts, launch inputs or recovery evidence. Move required
   evidence to its established private receipt owner and verify preservation before
   cleanup; never erase it just to make the worktree appear clean.
5. Run ordinary `git worktree remove`, without force. Keep branches unless separate
   branch-cleanup authority applies. Never use blanket pruning, `rm -rf`, force
   removal or automatic branch deletion as a substitute for these checks.
6. Read back `git worktree list --porcelain`, confirm the exact worktree path is gone
   and verify the canonical checkout is still on the recorded default branch with
   the integrated result. Run subsequent coordinator commands there, not in the
   deleted directory. Apply the same checks to an owned integration worktree.

After the ownership/liveness/evidence checks above, this guarded Git sequence can
remove one clean ancestry-integrated task worktree. Set the four variables from
verified task evidence, run from the canonical checkout, and inspect every result:

```sh
case "$DEFAULT_BRANCH" in main|master) ;; *) exit 1 ;; esac &&
test "$(git -C "$CANONICAL" symbolic-ref --short HEAD)" = "$DEFAULT_BRANCH" &&
CANONICAL_COMMON=$(git -C "$CANONICAL" rev-parse --path-format=absolute --git-common-dir) &&
TASK_COMMON=$(git -C "$TASK_WORKTREE" rev-parse --path-format=absolute --git-common-dir) &&
test "$CANONICAL_COMMON" = "$TASK_COMMON" &&
test "$(git -C "$TASK_WORKTREE" rev-parse HEAD)" = "$TASK_COMMIT" &&
git -C "$CANONICAL" merge-base --is-ancestor "$TASK_COMMIT" HEAD &&
TASK_STATUS=$(git -C "$TASK_WORKTREE" status --porcelain=v1 --untracked-files=all --ignored) &&
test -z "$TASK_STATUS" &&
git -C "$CANONICAL" worktree remove -- "$TASK_WORKTREE"
```

This shell sequence does not detect live owners or authorize integration itself;
those preceding checks remain mandatory. This instruction contract is not a runtime guarantee
that a model will execute it, and fixture checks do not qualify live cron cleanup.

## Report and resume

Report integration and cleanup separately: canonical branch/commit, exact removed
paths, and any **cleanup pending** path with its concrete preservation reason.
Implementation acceptance may pass while workspace cleanup remains pending; never
claim the complete worktree closeout is finished until removal and default-branch
readback succeed. Resume eligible cleanup at the next safe reconciliation before
creating replacement worktrees. Old unrelated worktrees are not bulk-cleanup targets.
