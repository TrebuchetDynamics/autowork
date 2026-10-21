# Worktree placement

New task checkouts live in `<canonical-repo>/.worktrees/<task>/`. The canonical
checkout is the first non-bare entry from `git worktree list --porcelain`, not
necessarily the current directory. `.worktrees/` is ignored; the shared helper also
adds a local Git exclusion for repositories without a tracked ignore rule.

Autowork worker, retry, integration and isolation paths use
`pi-autowork/engine/worktree_paths.py`. Pi sessions and scratch checkouts use
the same helper. Existing session paths remain resumable until explicitly moved.

## Claude Code

Copy `pi-autowork/engine/worktree_paths.py` to
`~/.claude/hooks/worktree-policy.py`. Merge these entries into the user
`~/.claude/settings.json` hooks, preserving other settings:

```json
{
  "hooks": {
    "WorktreeCreate": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/worktree-policy.py"}]}],
    "WorktreeRemove": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/worktree-policy.py"}]}],
    "PreToolUse": [{"matcher": "Bash", "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/worktree-policy.py"}]}]
  }
}
```

The native creation hook prints the created absolute path. The Bash guard redirects
ordinary manual `git worktree add` calls to `EnterWorktree`; it is a workflow guard,
not a shell sandbox. The removal hook keeps dirty, ignored-file-bearing and
unmerged checkouts, and never deletes branches. Restart existing Claude sessions
to ensure they load the new hooks and user instructions.

The hook payloads and lifecycle are documented in the
[Claude Code hooks reference](https://code.claude.com/docs/en/hooks).

## One interactive writer per checkout

One interactive session writes a checkout at a time. Copy
`pi-autowork/engine/checkout_lock.py` to `~/.claude/hooks/checkout-lock.py` and
add these hooks beside the worktree policy's:

```json
{
  "hooks": {
    "PreToolUse": [{"matcher": "Edit|Write|MultiEdit|NotebookEdit", "hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/checkout-lock.py"}]}],
    "SessionEnd": [{"hooks": [{"type": "command", "command": "python3 ~/.claude/hooks/checkout-lock.py"}]}]
  }
}
```

The first session to edit a file in a repository's canonical checkout holds it; the
lock lives in the Git common directory (`interactive-writer.json`), so every linked
checkout sees it. Another session's edit there is denied with a reason that names
the holder and its uncommitted files; that session continues in a worktree through
`EnterWorktree`, or waits. The lock passes on once every file the holder edited is
committed or reverted (after a one-minute grace, since the hook runs before an edit
lands), or when the holder's session ends. A holder with uncommitted files is never
released automatically: `python3 ~/.claude/hooks/checkout-lock.py status|release
[REPO]` shows the holder and frees it by hand. Edits under `.worktrees/`, linked
worktrees and paths outside Git are never locked; reads are never blocked. Like the
Bash worktree guard, this guards the edit tools, not shell commands that write files.

## Existing checkouts

Use `git worktree move OLD NEW` after checking for live processes, open files and
runner ownership. Verify HEAD, branch, status and file contents before and after.
Preserve active sessions in place until they stop; do not force-remove them or
rewrite historical logs. Update live state references separately if needed.
