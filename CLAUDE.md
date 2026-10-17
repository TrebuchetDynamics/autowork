# Repository instructions for Claude

Read and follow `AGENTS.md` in this directory.

All new worktrees belong in `<canonical-repo>/.worktrees/<task>/` (plural),
including delegated Claude work. Never create sibling repository directories or
use `.claude/worktrees/`. Use `EnterWorktree`; the user WorktreeCreate hook enforces
the destination. Reuse existing task checkouts. Preserve other workers and
uncommitted work. The explicit user location overrides bundled skill examples.
