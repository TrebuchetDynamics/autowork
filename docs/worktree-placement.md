# Worktree placement

New task checkouts live in `<canonical-repo>/.worktrees/<task>/`. The canonical
checkout is the first non-bare entry from `git worktree list --porcelain`, not
necessarily the current directory. `.worktrees/` is ignored; the shared helper also
adds a local Git exclusion for repositories without a tracked ignore rule.

Autowork worker, retry, integration and isolation paths use
`skills/autowork/scripts/worktree_paths.py`. Pi sessions and scratch checkouts use
the same helper. Existing session paths remain resumable until explicitly moved.

## Claude Code

Copy `skills/autowork/scripts/worktree_paths.py` to
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

## Existing checkouts

Use `git worktree move OLD NEW` after checking for live processes, open files and
runner ownership. Verify HEAD, branch, status and file contents before and after.
Preserve active sessions in place until they stop; do not force-remove them or
rewrite historical logs. Update live state references separately if needed.
