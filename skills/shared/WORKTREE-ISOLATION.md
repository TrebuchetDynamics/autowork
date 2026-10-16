# Worktree isolation

Before creating a writing checkout, inspect repository instructions, Git status,
existing worktrees and active ownership. Pin the intended base to an immutable
commit and identify required prerequisites. A clean base does not include dirty
backlog edits or uncommitted dependencies; resolve attribution before assembling
an isolated candidate. Never copy foreign edits to manufacture a clean gate.

Use a private worktree when the workflow requires isolation, unless the user's
scope explicitly requires the current checkout. Keep the checkout and owned file
boundaries in the handoff. Verify its repository identity, base and required files
before editing. Autowork's manifest and initial worker gate remain required.

Worktree creation is not commit, push, merge, cleanup or delivery authorization.
Preserve existing worktrees, branches, indexes and live writers. Remove only
scratch you created when it is no longer needed, without deleting receipts or
launch inputs required for recovery.

For authorized Autowork tasks, apply [worktree closeout](../autowork/references/worktree-closeout.md):
integrate verified results into the canonical default branch (`main` or `master`),
then remove finished owned task/integration worktrees. Keep active, dirty, locked,
unmerged and recovery-bearing worktrees; report pending integration or cleanup.
There is no cap on necessary active worktrees. `worktree_closeout.py` removes only
worktrees that are integrated, clean, unlocked and unused; nothing else is deleted.
