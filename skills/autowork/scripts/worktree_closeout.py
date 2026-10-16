#!/usr/bin/env python3
"""Remove finished worktrees of a repository; keep anything that could still matter.

A worktree is removable only when every check passes: it is not the canonical
checkout, not locked, not managed by a running parallel slot or pi-autowork, its
HEAD is already on the canonical `main`/`master`, it has no tracked or untracked
changes and no ignored files other than regenerable caches, no process has its
working directory, an open file or an argument inside it, and its Git metadata has
been quiet for the grace period (explicitly named worktrees skip the grace period).
Nothing it removes holds unique work: the commit is on the default branch and the
directory had nothing else in it.

Without --apply this only reports. --apply runs ordinary `git worktree remove`
(never --force), reads the registration back and deletes the worktree's branch
with `git branch -d` once that branch is merged.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys
import time

GRACE_SECONDS = 30 * 60
CACHE_PARTS = {'__pycache__', '.pytest_cache', '.mypy_cache', '.ruff_cache', '.hypothesis'}
CACHE_SUFFIXES = ('.pyc', '.pyo')


def git(root, *args, check=True):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(root), *args], env=env, capture_output=True, text=True, timeout=60)
    if check and result.returncode:
        raise ValueError(f'git {" ".join(args)} failed: {result.stderr.strip()}')
    return result.stdout.strip() if check else result


def registrations(canonical):
    entries = []
    for block in git(canonical, 'worktree', 'list', '--porcelain').split('\n\n'):
        entry = {'branch': None, 'locked': False, 'prunable': False, 'bare': False}
        for line in block.splitlines():
            key, _, value = line.partition(' ')
            if key == 'worktree':
                entry['path'] = Path(value)
            elif key == 'HEAD':
                entry['head'] = value
            elif key == 'branch':
                entry['branch'] = value.removeprefix('refs/heads/')
            elif key in ('locked', 'prunable', 'bare'):
                entry[key] = True
        if 'path' in entry:
            entries.append(entry)
    return entries


def users(paths):
    """{path: [evidence]} for processes inside each path; None when processes cannot be listed."""
    proc = Path('/proc')
    if not (proc / 'self' / 'cwd').exists():
        return None
    roots = [Path(p) for p in paths]
    inside = lambda path: next((r for r in roots if path == r or r in path.parents), None)
    callers = ancestors()
    found = {}
    for entry in proc.glob('[0-9]*'):
        pid = entry.name
        try:
            seen = [('working directory', Path(os.readlink(entry / 'cwd')))]
            # This helper and whoever launched it name the worktree as an argument;
            # their working directory and open files still count.
            if int(pid) not in callers:
                seen += [('argument', Path(arg)) for arg in
                         (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0') if arg.startswith('/')]
            for link in (entry / 'fd').iterdir():
                try:
                    seen.append(('open file', Path(os.readlink(link))))
                except OSError:
                    continue
        except OSError:
            continue  # Exited, or another user's process that cannot write here.
        for kind, path in seen:
            root = inside(path)
            if root is not None:
                found.setdefault(str(root), []).append(f'pid {pid} {kind} {path}')
                break
    return found


def ancestors():
    pids, pid = set(), os.getpid()
    while pid > 1 and pid not in pids:
        pids.add(pid)
        try:
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return pids


def runner_owner(canonical, path):
    """The runner that manages this worktree, if any; a runner cleans up its own."""
    state = Path(os.environ.get('PI_AUTOWORK_STATE_DIR')
                 or Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local' / 'state') / 'pi-autowork')
    if path == state or state.resolve() in path.parents:
        return 'pi-autowork'
    common = Path(git(canonical, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    for slot in sorted((common / 'autowork-execution' / 'slots').glob('*.json')):
        try:
            value = json.loads(slot.read_text())
        except (OSError, ValueError):
            return 'parallel Autowork (unreadable slot ' + slot.name + ')'
        if value.get('state') != 'closed' and Path(str(value.get('worktree', ''))).resolve() == path:
            return 'parallel Autowork slot ' + str(value.get('task_id'))
    return None


def leftovers(root):
    """Status lines that are not regenerable caches."""
    lines = git(root, 'status', '--porcelain=v1', '--untracked-files=all', '--ignored').splitlines()
    cache = lambda name: (bool(CACHE_PARTS & set(Path(name).parts)) or name.endswith(CACHE_SUFFIXES))
    changes = [line for line in lines if not line.startswith('!! ')]
    ignored = [line[3:] for line in lines if line.startswith('!! ') and not cache(line[3:].rstrip('/'))]
    return changes, ignored


def quiet_seconds(root, now):
    gitdir = Path(git(root, 'rev-parse', '--absolute-git-dir'))
    # HEAD and its reflog move with checkouts and commits; the index and the gitdir
    # itself also change when any reader's `git status` refreshes the index.
    times = [p.stat().st_mtime for p in (gitdir / 'HEAD', gitdir / 'logs' / 'HEAD', gitdir / 'ORIG_HEAD')
             if p.exists()]
    return now - max(times)


def judge(canonical, default, entry, found, grace, now):
    """None when removable, else the reason to keep it."""
    path = entry['path']
    if entry['locked']:
        return 'locked'
    owner = runner_owner(canonical, path)
    if owner:
        return f'managed by {owner}'
    if 'head' not in entry:
        return 'no HEAD recorded'
    if git(canonical, 'merge-base', '--is-ancestor', entry['head'], 'refs/heads/' + default, check=False).returncode:
        return f'HEAD {entry["head"][:12]} is not integrated into {default}'
    if entry['prunable']:
        return None  # Directory already gone; only the registration remains.
    quiet = quiet_seconds(path, now)  # Before `git status`, which may touch metadata.
    changes, ignored = leftovers(path)
    if changes:
        return f'{len(changes)} uncommitted change(s), e.g. {changes[0]}'
    if ignored:
        return f'ignored files may be evidence, e.g. {ignored[0]}'
    if found is None:
        return 'process activity unknown on this system'
    if found.get(str(path)):
        return 'in use: ' + found[str(path)][0]
    if quiet < grace:
        return f'used {int(quiet // 60)} min ago (grace {grace // 60} min)'
    return None


def remove(canonical, default, entry):
    path, branch = entry['path'], entry['branch']
    if not entry['prunable'] and git(path, 'rev-parse', 'HEAD') != entry['head']:
        raise ValueError(f'{path} moved during closeout')
    git(canonical, 'worktree', 'remove', '--', str(path))
    if path.exists() or any(e['path'] == path for e in registrations(canonical)):
        raise ValueError(f'{path} is still registered after removal')
    deleted = False
    if branch and branch != default and git(canonical, 'rev-parse', 'refs/heads/' + branch, check=False).stdout.strip() == entry['head']:
        deleted = not git(canonical, 'branch', '-d', branch, check=False).returncode
    return {'path': str(path), 'branch': branch, 'head': entry['head'], 'branch_deleted': deleted}


def closeout(canonical, worktrees=None, apply=False, grace=GRACE_SECONDS, now=None, users=users):
    canonical = Path(git(Path(canonical).expanduser().resolve(), 'rev-parse', '--show-toplevel')).resolve()
    default = git(canonical, 'symbolic-ref', '--quiet', '--short', 'HEAD', check=False).stdout.strip()
    if default not in ('main', 'master'):
        raise ValueError('run from the canonical checkout of main or master, not ' + (default or 'a detached HEAD'))
    entries = [e for e in registrations(canonical) if not e['bare']]
    for e in entries:
        e['path'] = e['path'].resolve() if e['path'].exists() else e['path']
    candidates = [e for e in entries if e['path'] != canonical]
    if worktrees is not None:
        wanted = []
        for raw in worktrees:
            path = Path(raw).expanduser().resolve()
            if path == canonical:
                raise ValueError(f'{path} is the canonical checkout')
            match = next((e for e in candidates if e['path'] == path), None)
            if match is None:
                raise ValueError(f'{path} is not a worktree of {canonical}')
            wanted.append(match)
        candidates, grace = wanted, 0
    found = users([e['path'] for e in candidates if not e['prunable']])
    now = time.time() if now is None else now
    result = {'canonical': str(canonical), 'default_branch': default, 'removable': [], 'removed': [], 'kept': []}
    for entry in candidates:
        try:
            reason = judge(canonical, default, entry, found, grace, now)
        except ValueError as exc:
            reason = 'could not inspect: ' + str(exc)
        if reason:
            result['kept'].append({'path': str(entry['path']), 'branch': entry['branch'], 'reason': reason})
            continue
        result['removable'].append({'path': str(entry['path']), 'branch': entry['branch']})
        if apply:
            try:
                result['removed'].append(remove(canonical, default, entry))
            except ValueError as exc:
                result['kept'].append({'path': str(entry['path']), 'branch': entry['branch'],
                                       'reason': 'removal failed: ' + str(exc)})
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('canonical', help='The canonical checkout, on main or master.')
    parser.add_argument('--worktree', action='append', help='Only this worktree (repeatable); skips the grace period.')
    parser.add_argument('--apply', action='store_true', help='Remove what qualifies; without it, only report.')
    parser.add_argument('--grace-minutes', type=float, default=GRACE_SECONDS / 60,
                        help='Keep worktrees whose Git metadata changed this recently (default 30).')
    args = parser.parse_args(argv)
    try:
        if args.grace_minutes < 0:
            raise ValueError('--grace-minutes must not be negative')
        sys.path.insert(0, str(Path(__file__).parent))
        import task_execution
        canonical = Path(args.canonical).expanduser().resolve()
        common = Path(git(canonical, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
        with task_execution.lock(common / 'autowork-execution' / 'writer.lock'):
            result = closeout(canonical, args.worktree, args.apply, int(args.grace_minutes * 60))
    except BlockingIOError:
        result = {'outcome': 'BUSY', 'reason': 'An Autowork operation holds the repository writer lock; retry later.'}
    except (ValueError, OSError, subprocess.SubprocessError) as exc:
        result = {'outcome': 'ACTION_REQUIRED', 'reason': str(exc)}
    print(json.dumps(result, indent=2))
    return 1 if 'outcome' in result else 0


if __name__ == '__main__':
    raise SystemExit(main())
