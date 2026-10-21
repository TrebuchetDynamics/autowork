"""Stale agent scratch in a RAM-backed /tmp is removed, so it cannot cap the workers.

Workers and reviewers copied whole repositories into /tmp and left them: on one host 39 GB in
7,839 entries, which made the memory gate start no new worker (TOOLSET-162-d2). A top-level
/tmp entry is removed only when every rule holds: the runner's user owns it, it is not a
socket or a system name, nothing inside it changed for PI_AUTOWORK_TMP_STALE seconds (default
7200; 0 turns the janitor off), no unfinished slot reserves it, and no process uses it as
its working directory or holds a file in it open. One sweep runs per host at most every
SWEEP_EVERY seconds, under a lock; incomplete slot discovery defers cleanup.
Standard library only.

    janitor.py sweep [TMP]   # sweep now and print what was freed
"""
import fcntl
import json
import os
from pathlib import Path
import shutil
import stat
import subprocess
import sys
import time

SWEEP_EVERY = 1800
DEFAULT_STALE = 7200
KEEP = ('.X11-unix', '.ICE-unix', '.font-unix', '.XIM-unix', '.Test-unix')
KEEP_PREFIXES = ('tmux-', 'ssh-', 'systemd-', 'snap-', 'pulse-', 'krb5', 'dbus-', 'claude-')


def stale_after(env=os.environ):
    try:
        return int(env.get('PI_AUTOWORK_TMP_STALE', DEFAULT_STALE))
    except ValueError:
        return DEFAULT_STALE


def in_use(tmp):
    """Top-level names under ``tmp`` that a process works in or holds a file open in."""
    prefix = str(tmp).rstrip('/') + '/'
    used = set()
    for proc in Path('/proc').iterdir():
        if not proc.name.isdigit():
            continue
        links = [proc / 'cwd']
        try:
            links += list((proc / 'fd').iterdir())
        except OSError:
            pass
        for link in links:
            try:
                target = os.readlink(link)
            except OSError:
                continue
            if target.startswith(prefix):
                used.add(target[len(prefix):].split('/', 1)[0])
    return used


def changed_since(path, cutoff):
    """Whether anything at or under ``path`` was modified at or after ``cutoff``."""
    try:
        if os.lstat(path).st_mtime >= cutoff:
            return True
    except OSError:
        return False
    if not os.path.isdir(path) or os.path.islink(path):
        return False
    for root, dirs, files in os.walk(path, onerror=lambda error: None):
        for name in dirs + files:
            try:
                if os.lstat(os.path.join(root, name)).st_mtime >= cutoff:
                    return True
            except OSError:
                continue
    return False


def size(path):
    total = 0
    for root, _, files in os.walk(path, onerror=lambda error: None):
        for name in files:
            try:
                total += os.lstat(os.path.join(root, name)).st_size
            except OSError:
                continue
    return total if os.path.isdir(path) else (os.lstat(path).st_size if os.path.lexists(path) else 0)


CACHE_DIRS = ('target', 'build', '.dart_tool')
# The review's integration checkout, main-check and maintainer scratch, and session worktrees.
NEVER_PRUNED = ('autowork-integration', 'pi-scratch-', 'pi-autowork-')


def build_caches(worktrees, busy=(), *, stale=None, now=None, urgent=False):
    """Regenerable build output in this runner's own worktrees that may go (TOOLSET-210-53):
    `target/`, `build/` and `.dart_tool/` directly in a worktree under ``worktrees`` that is
    not in ``busy`` (running or verifying slots, the session), ignored by Git there, and, unless
    ``urgent`` (the disk is low), untouched for ``stale`` seconds. Sources are never candidates."""
    stale = DEFAULT_STALE if stale is None else stale
    now = time.time() if now is None else now
    busy = {os.path.realpath(p) for p in busy if p}
    found = []
    try:
        trees = sorted(Path(worktrees).iterdir())
    except OSError:
        return found
    for tree in trees:
        if (not tree.is_dir() or tree.is_symlink() or os.path.realpath(tree) in busy or not (tree / '.git').exists()
                or tree.name.startswith(NEVER_PRUNED)):
            continue
        for name in CACHE_DIRS:
            cache = tree / name
            if not cache.is_dir() or cache.is_symlink():
                continue
            ignored = subprocess.run(['git', '-C', str(tree), 'check-ignore', '-q', name],
                                     capture_output=True).returncode == 0
            if not ignored or (not urgent and changed_since(cache, now - stale)):
                continue
            found.append(cache)
    # Oldest first, so a low disk frees the least recently used output first.
    return sorted(found, key=lambda p: os.lstat(p).st_mtime)


def prune_build_caches(worktrees, busy=(), **options):
    """(count, bytes) removed of build_caches()."""
    count = freed = 0
    for cache in build_caches(worktrees, busy, **options):
        amount = size(cache)
        shutil.rmtree(cache, ignore_errors=True)
        if not cache.exists():
            count, freed = count + 1, freed + amount
    return count, freed


def reserved_tmp(tmp, state_root=None):
    """Top-level scratch reserved by unfinished slots, or None if discovery failed.

    A sweep is host-wide: consult every registered runner, including stopped ones,
    but read current engine slots, not potentially stale health snapshots or history.
    Incomplete discovery must never turn a held allocation into disposable scratch.
    """
    root = Path(state_root or os.environ.get('PI_AUTOWORK_STATE_DIR') or
                Path(os.environ.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'pi-autowork')
    repos, reserved = set(), set()
    for record in [*root.glob('*/runner.json'), *root.glob('*/status.json')]:
        try:
            repo = json.loads(record.read_text()).get('repo')
            if repo:
                repos.add(repo)
        except (OSError, ValueError, AttributeError, TypeError):
            return None
    for repo in repos:
        try:
            result = subprocess.run(['git', '-C', repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                    env={k: v for k, v in os.environ.items() if not k.startswith('GIT_')},
                                    capture_output=True, text=True, timeout=10)
            if result.returncode:
                return None
            common = Path(result.stdout.strip()) / 'autowork-execution'
            for slot in (common / 'slots').glob('*.json'):
                try:
                    phase = json.loads(slot.read_text()).get('state')
                    if phase not in ('held', 'interrupted', 'dispatched', 'running', 'reported', 'integrating', 'integrated'):
                        continue
                    data = common / 'slot-data' / slot.stem
                    try:
                        paths = [Path(json.loads((data / 'tmp.json').read_text())['path'])]
                    except FileNotFoundError:  # old slots allocated scratch beside each attempt's report
                        paths = list(data.glob('attempt-*/tmp'))
                    for path in paths:
                        try:
                            relative = path.resolve().relative_to(Path(tmp).resolve())
                        except ValueError:  # an allocation on disk, outside the swept root
                            continue
                        if relative.parts:
                            reserved.add(relative.parts[0])
                except FileNotFoundError:
                    continue  # a slot retired while being read
                except (OSError, ValueError, KeyError, TypeError, AttributeError):
                    return None
        except (OSError, subprocess.TimeoutExpired):
            return None
    return reserved


def candidates(tmp='/tmp', *, stale=None, now=None, uid=None, used=None, state_root=None):
    """Top-level entries of ``tmp`` that every rule allows removing."""
    stale = stale_after() if stale is None else stale
    if stale <= 0:
        return []
    now = time.time() if now is None else now
    uid = os.getuid() if uid is None else uid
    reserved = reserved_tmp(tmp, state_root)
    if reserved is None:
        return []  # no destructive cleanup without a complete reservation inventory
    used = (in_use(tmp) if used is None else used) | reserved
    cutoff = now - stale
    out = []
    try:
        entries = list(os.scandir(tmp))
    except OSError:
        return []
    for entry in entries:
        name = entry.name
        if name in KEEP or name.startswith(KEEP_PREFIXES) or name in used:
            continue
        try:
            info = entry.stat(follow_symlinks=False)
        except OSError:
            continue
        if info.st_uid != uid or stat.S_ISSOCK(info.st_mode) or info.st_mtime >= cutoff:
            continue  # the cheap check first; a deep one only for what looks old
        if changed_since(entry.path, cutoff):
            continue
        out.append(entry.path)
    return out


def sweep(tmp='/tmp', **options):
    """Remove every candidate: (count, bytes freed)."""
    count, freed = 0, 0
    for path in candidates(tmp, **options):
        amount = size(path)
        if os.path.isdir(path) and not os.path.islink(path):
            shutil.rmtree(path, ignore_errors=True)
        else:
            try:
                os.unlink(path)
            except OSError:
                continue
        if not os.path.lexists(path):
            count, freed = count + 1, freed + amount
    return count, freed


def sweep_if_due(state_root, tmp='/tmp', now=None):
    """One sweep per host every SWEEP_EVERY seconds: (count, bytes), or None when not due."""
    if stale_after() <= 0:
        return None
    now = time.time() if now is None else now
    root = Path(state_root)
    root.mkdir(parents=True, exist_ok=True)
    record = root / 'janitor.json'
    with open(root / 'janitor.lock', 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return None  # another runner is sweeping
        try:
            last = json.loads(record.read_text()).get('at', 0)
        except (OSError, ValueError, AttributeError):
            last = 0
        if now - last < SWEEP_EVERY:
            return None
        count, freed = sweep(tmp, now=now, state_root=root)
        record.write_text(json.dumps({'at': now, 'removed': count, 'freed_bytes': freed}))
        return count, freed


def main(argv):
    if argv[:1] != ['sweep']:
        print(__doc__.strip().splitlines()[-1].strip(), file=sys.stderr)
        return 2
    count, freed = sweep(argv[1] if len(argv) > 1 else '/tmp')
    print(f'removed {count} stale /tmp entries, {freed / 2 ** 30:.1f} GB')
    return 0


if __name__ == '__main__':
    raise SystemExit(main(sys.argv[1:]))
