# Repository instructions for Claude

Read and follow `AGENTS.md` in this directory.

Interactive sessions work directly in the main checkout, one at a time. The first
session to edit a file there holds the checkout until its edits are committed or
reverted; a second session works in its own worktree (`EnterWorktree`) meanwhile.
The checkout-lock hook enforces this (docs/worktree-placement.md). Otherwise,
worktrees are for Autowork runners and parallel delegated agents only.

Those worktrees belong in `<canonical-repo>/.worktrees/<task>/` (plural),
including delegated Claude work. Never create sibling repository directories or
use `.claude/worktrees/`. Use `EnterWorktree`; the user WorktreeCreate hook enforces
the destination. Reuse existing task checkouts. Preserve other workers and
uncommitted work. The explicit user location overrides bundled skill examples.
