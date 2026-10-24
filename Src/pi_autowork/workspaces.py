"""Provision task worktrees with gitignored dependencies from the canonical checkout.

A fresh worktree has no ignored files: vendored sources, generated SDKs or local
toolchains that the main checkout has (sierra TASK-022 stopped on a missing ignored
source tree). The repository's settings name such paths in
``PI_AUTOWORK_LINK_PATHS`` (comma-separated, repository-relative). Each is
mirrored into the worktree (real directories, hard-linked files) only when it
exists in the canonical checkout, is absent in the worktree, and Git ignores it
there, so it never shadows tracked content. Read-only is cooperative: hard links
share contents, so a tool editing a file in place edits the original.

    workspaces.py link CANONICAL WORKTREE PATHS   # prints one line per path
"""
from pi_autowork.layout import load
from pathlib import Path, PurePosixPath
import os
import shutil
import subprocess
import sys


def task_path(toolset, repo, name):
    """Use the same canonical location policy as the engine and Claude hooks."""
    module = load(toolset, 'pi_autowork.engine.worktree_paths')
    return module.worktree_path(repo, name)


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
                    path.rmdir() if path.is_dir() and not path.is_symlink() else path.unlink()
                results.append((raw, 'refused: the link would show up as a change in Git'))
            else:
                results.append((raw, 'linked'))
    return results


LOCKFILE_DEPENDENCIES = {'package-lock.json': 'node_modules', 'npm-shrinkwrap.json': 'node_modules',
                         'pnpm-lock.yaml': 'node_modules', 'yarn.lock': 'node_modules',
                         'uv.lock': '.venv', 'poetry.lock': '.venv'}


def lockfile_dependencies(canonical, worktree):
    """([paths], [(path, reason)]): installed dependency directories of tracked lockfiles to link
    without a setting (TOOLSET-283-15), and those left out. A review tree without the main checkout's
    node_modules held a task 45 hours for a package its lockfile declares. Only a lockfile identical
    in both trees qualifies: a task that changes its dependencies installs its own."""
    canonical, worktree = Path(canonical).resolve(), Path(worktree).resolve()
    listed = subprocess.run(['git', '-C', str(worktree), 'ls-files', '-z'], capture_output=True, text=True, timeout=60)
    paths, skipped = [], []
    for name in sorted(listed.stdout.split('\0') if listed.returncode == 0 else []):
        rel = PurePosixPath(name)
        directory = LOCKFILE_DEPENDENCIES.get(rel.name)
        if not directory:
            continue
        dependency = str(rel.parent / directory) if str(rel.parent) != '.' else directory
        if not (canonical / dependency).is_dir() or (worktree / dependency).exists():
            continue
        try:
            same = (canonical / rel).read_bytes() == (worktree / rel).read_bytes()
        except OSError:
            same = False
        if same:
            paths.append(dependency)
        else:
            skipped.append((dependency, f'not linked: {name} differs from the main checkout'))
    return paths, skipped


def _link(source, target):
    """Mirror source at target; return created paths, parents first.

    Directories are real and files are hard links (a copy across filesystems), so the
    tree behaves like the original for every tool: `find` does not descend into a
    symlinked directory (sierra TASK-026), and Git does not treat a symlink as a
    directory, so a `vendor/` rule would not ignore a linked `vendor`. Hard links
    share file contents: a tool that edits a file in place edits the original too.
    """
    created = []
    missing = [p for p in [target.parent, *target.parent.parents] if not p.exists()]
    for parent in reversed(missing):
        parent.mkdir()
        created.append(parent)

    def place(src, dst):
        if src.is_symlink():
            os.symlink(os.readlink(src), dst)
        else:
            try:
                os.link(src, dst)
            except OSError:  # another filesystem, or links not allowed: copy
                shutil.copy2(src, dst)
        created.append(dst)

    if not source.is_dir() or source.is_symlink():
        place(source, target)
        return created
    target.mkdir()
    created.append(target)
    for root, dirs, files in os.walk(source):  # does not follow symlinked directories
        here = target / Path(root).relative_to(source)
        for name in sorted(dirs):
            if (Path(root) / name).is_symlink():
                place(Path(root) / name, here / name)
            else:
                (here / name).mkdir()
                created.append(here / name)
        for name in sorted(files):
            place(Path(root) / name, here / name)
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


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        sys.exit(main(sys.argv[1:]))
    finally:
        sys.argv = previous
