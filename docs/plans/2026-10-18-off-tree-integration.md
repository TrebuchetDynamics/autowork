# Off-tree integration and a speculative merge queue

Status: Accepted

Accepted by the planner on 2026-10-18 under owner direction ("is this the best method
for multi agents work on a single codebase? research online the best method for us",
then "yes, plan both"). Every decision below is the planner's call.

## Off-tree integration design

Status: Accepted

**What the field does.** Agents work in isolated worktrees, clones or containers, one
branch each, with overlapping work serialized: Autowork already does this. Merge
services keep `main` always passing (the "not rocket science" rule from bors: merge
into a temporary branch, test it, move `main` only on a pass) and merge without a
working copy: `git merge-tree --write-tree` builds the merge without touching any
index or working tree, `commit-tree` and `update-ref <ref> <new> <old>` move the
branch only if it still points where it was read. No merge service asks whether a
person is "in the checkout", because it never writes one.

**Where Autowork differs.** Integration builds each merge in the `autowork-integration`
worktree and validates it there, but then fast-forwards the runner's session worktree,
a checked-out working copy; closeout and planning commits also write through working
copies. So before each of them `require_no_writers` scans live processes and decides
whether each is the runner's own (leader, process group, parent chain, cgroup,
marker). Every new kind of process the runner starts is a new false "outside session":
on 2026-10-18 the runner's own worker test processes held nine verified commits.

**Design.** The runner's session branch becomes a ref no worktree checks out. Every
write to it (integration, closeout, planning commits) is made in a detached scratch
worktree or with plumbing, and lands with a compare-and-swap `update-ref`; a ref that
moved since it was read is re-integrated, as the existing "canonical HEAD moved" path
does. Nothing then writes a working copy anyone else could be using, so integration and
closeout need no writer check and the process attribution is deleted. The only working
copy the runner still updates is the main checkout, when it lands the session on
`main`; that step keeps a file-level rule (TOOLSET-216-08: a clean 3-way merge of
uncommitted edits, a wait only on a real conflict or a file open for writing), and the
branch and the checkout move together, never the ref alone (a checked-out branch whose
ref moves shows the reverse of the merge as uncommitted changes).

## Speculative merge queue design

Status: Accepted

Integration takes one verified commit at a time in TODO.md priority order, and each
takes a review and a full check, 30 to 40 minutes at today's load: nine waiting
commits are hours. A speculative queue builds the next K (default 3) commits stacked
in priority order (base+A, base+A+B, base+A+B+C), validates them at the same time
(within the host's check slots), and lands each in order whose own stack passed. When
one fails, it is held as today, and the stacks after it are rebuilt without it and
validated again. Priority order and every gate stay as they are; only the waiting
between them goes.

## Planner's calls

- Off-tree integration replaces the attribution rules instead of adding more: the
  finished TOOLSET-165-f7 and TOOLSET-195-ee land first (they fix today's holds), and
  this task then deletes their attribution code from integration and closeout (no
  compatibility path).
- The main checkout keeps a working-copy rule, at file level, because people work there.
- K is 3 by default; 1 turns the queue back into today's one-at-a-time integration.
