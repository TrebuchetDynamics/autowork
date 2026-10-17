#!/usr/bin/env python3
"""Canonical .worktrees placement; also a standalone Claude Code hook.

Install this file in ~/.claude/hooks and register WorktreeCreate, WorktreeRemove
and PreToolUse (Bash). No force removal, branch deletion or implicit adoption.
"""
import json
from pathlib import Path
import re
import subprocess
import sys


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True)
    if result.returncode:
        raise ValueError(result.stderr.strip() or 'git command failed')
    return result.stdout.strip()


def canonical_root(repo):
    first = git(repo, 'worktree', 'list', '--porcelain', '-z').split('\0\0')[0]
    fields = first.split('\0')
    if 'bare' in fields or not fields[0].startswith('worktree '):
        raise ValueError('A canonical non-bare checkout is required')
    return Path(fields[0][9:]).resolve()


def worktree_path(repo, name):
    """Resolve against the main checkout, never against a linked session's parent."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name):
        raise ValueError('Worktree name must be a plain slug without path separators')
    root = canonical_root(repo)
    path = root / '.worktrees' / name
    if path.parent.is_symlink() or path.is_symlink():
        raise ValueError('Refuse symlinked worktree destination')
    # Local exclusion also protects repositories without a committed ignore rule.
    common = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    exclude = common / 'info' / 'exclude'
    exclude.parent.mkdir(parents=True, exist_ok=True)
    if exclude.is_symlink():
        raise ValueError('Refuse symlinked Git exclude file')
    text = exclude.read_text() if exclude.exists() else ''
    if '/.worktrees/' not in text.splitlines():
        with exclude.open('a') as stream:
            stream.write('\n/.worktrees/\n')
    return path


def hook(payload):
    event = payload['hook_event_name']
    if event == 'PreToolUse':
        command = payload.get('tool_input', {}).get('command', '')
        # Manual creation bypasses Claude's lifecycle hooks. Route ordinary Git
        # invocations through EnterWorktree; this is a workflow guard, not a shell sandbox.
        if re.search(r'(?:^|[;&|\n])\s*(?:command\s+)?git\s+(?:(?:-C|-c)\s+(?:"[^"]*"|\x27[^\x27]*\x27|\S+)\s+)*worktree\s+add\b', command):
            print(json.dumps({'hookSpecificOutput': {
                'hookEventName': 'PreToolUse', 'permissionDecision': 'deny',
                'permissionDecisionReason': 'Use EnterWorktree for isolation. The configured WorktreeCreate hook '
                'places it in the canonical repository .worktrees/ directory. Reuse an existing task worktree.'}}))
        return
    if event == 'WorktreeCreate':
        name = payload['name']
        # Validate the input before prefixing so empty or dot-only names are rejected.
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', name):
            raise ValueError('Invalid Claude worktree name')
        path = worktree_path(payload['cwd'], 'claude-' + name)
        root = canonical_root(payload['cwd'])
        baseline = git(payload['cwd'], 'rev-parse', 'HEAD')
        git(root, 'worktree', 'add', '-b', 'claude/' + name, str(path), baseline)
        print(path)
    elif event == 'WorktreeRemove':
        path = Path(payload['worktree_path']).absolute()
        if not path.exists():
            return
        root = canonical_root(path)
        if (path.parent != root / '.worktrees' or not path.name.startswith('claude-')
                or path.is_symlink() or path.parent.is_symlink()):
            raise ValueError('Preserve worktree outside the managed Claude directory')
        if git(path, 'status', '--porcelain', '--untracked-files=all', '--ignored'):
            raise ValueError('Preserve worktree with uncommitted or ignored files')
        head = git(path, 'rev-parse', 'HEAD')
        git(root, 'merge-base', '--is-ancestor', head, 'HEAD')
        git(root, 'worktree', 'remove', str(path))


if __name__ == '__main__':
    try:
        hook(json.load(sys.stdin))
    except (KeyError, OSError, ValueError) as exc:
        print(f'Worktree policy: {exc}', file=sys.stderr)
        sys.exit(1)
