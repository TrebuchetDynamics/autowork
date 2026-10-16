"""Provision task worktrees with gitignored dependencies from the canonical checkout.

A fresh worktree has no ignored files: vendored sources, generated SDKs or local
toolchains that the main checkout has (sierra TASK-022 stopped on a missing ignored
source tree). The service environment names such paths in
``PI_AUTOWORK_LINK_PATHS`` (comma-separated, repository-relative). Each is
symlinked into the worktree only when it exists in the canonical checkout, is
absent in the worktree, and Git ignores it there, so a link never shadows
tracked content. Read-only is cooperative: a symlink does not stop writes.

    workspaces.py link CANONICAL WORKTREE PATHS   # prints one line per path
"""
from pathlib import Path, PurePosixPath
import os
import subprocess
import sys


def _ignored(worktree, path):
    result = subprocess.run(['git', '-C', str(worktree), 'check-ignore', '-q', '--no-index', '--', path],
                            capture_output=True, text=True, timeout=30)
    return result.returncode == 0


def link_ignored(canonical, worktree, paths):
    """[(path, outcome)] where outcome is 'linked', 'present' or a refusal reason."""
    canonical, worktree = Path(canonical).resolve(), Path(worktree).resolve()
    results = []
    for raw in [p.strip() for p in paths.split(',') if p.strip()]:
        rel = PurePosixPath(raw.rstrip('/'))
        if rel.is_absolute() or '..' in rel.parts or not rel.parts or rel.parts[0] == '.git':
            results.append((raw, 'refused: not a plain repository-relative path'))
            continue
        source, target = canonical / rel, worktree / rel
        if target.exists() or target.is_symlink():
            results.append((raw, 'present'))
        elif not source.exists():
            results.append((raw, 'refused: missing in the canonical checkout'))
        elif not source.resolve().is_relative_to(canonical):
            results.append((raw, 'refused: resolves outside the canonical checkout'))
        # A directory pattern (`vendor/`) matches only when Git is told it is a directory.
        elif not _ignored(worktree, str(rel) + ('/' if source.is_dir() else '')):
            results.append((raw, 'refused: not ignored by Git here, so it would shadow tracked content'))
        else:
            created = _link(source, target)
            if _shows_up(worktree, str(rel)):
                for path in reversed(created):  # only what this call made
                    path.unlink() if path.is_symlink() else path.rmdir()
                results.append((raw, 'refused: the link would show up as a change in Git'))
            else:
                results.append((raw, 'linked'))
    return results


def _link(source, target):
    """Link source at target; return created paths (parents first).

    Git does not treat a symlink as a directory, so a `vendor/` rule would not
    ignore a linked `vendor`: a directory becomes a real directory of links.
    """
    created = []
    missing = [p for p in [target.parent, *target.parent.parents] if not p.exists()]
    for parent in reversed(missing):
        parent.mkdir()
        created.append(parent)
    if source.is_dir():
        target.mkdir()
        created.append(target)
        for child in sorted(source.iterdir()):
            os.symlink(child, target / child.name, target_is_directory=child.is_dir())
            created.append(target / child.name)
    else:
        os.symlink(source, target)
        created.append(target)
    return created


def _shows_up(worktree, path):
    result = subprocess.run(['git', '-C', str(worktree), 'status', '--porcelain', '--untracked-files=all', '--', path],
                            capture_output=True, text=True, timeout=60)
    return bool(result.stdout.strip()) or result.returncode != 0


def main(argv):
    if len(argv) == 4 and argv[0] == 'link':
        for path, outcome in link_ignored(argv[1], argv[2], argv[3]):
            print(f'{path}: {outcome}')
        return 0
    print('usage: workspaces.py link CANONICAL WORKTREE PATHS', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
