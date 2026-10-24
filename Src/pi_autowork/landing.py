"""Moving the owner's main checkout onto a landed session without touching the owner's work.

The coordinator lands a session by fast-forwarding the main branch. When the owner's
checkout has uncommitted edits in files the landing changes, the ordinary `git merge
--ff-only` would refuse; this module lands around such edits: it prepares a new index
and rebased working files off to the side, then moves the ref with a compare-and-swap
and installs the prepared files. No stash, reset or checkout ever touches the owner's
work, and anything it cannot do safely is refused with the reason, leaving the ref, the
index and the edit as they were.

Quiet time for the owner's other edits (``recent_owner_paths``) is measured on content,
not mtimes, and persisted in the runner's state so a restart does not restart the clock.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time

from .common import git, git_ok, open_for_writing


class LandingBroken(Exception):
    """The main branch moved but the landing could not finish writing the checkout: the
    runner must stop and say so, since main and the working files now disagree."""


def checkout_operation(repo):
    """The reason never to land through an unfinished operation in the owner's checkout, or ''."""
    for marker in ('MERGE_HEAD', 'CHERRY_PICK_HEAD', 'REVERT_HEAD', 'rebase-merge', 'rebase-apply'):
        found = git(repo, 'rev-parse', '--path-format=absolute', '--git-path', marker)
        if found and Path(found).exists():
            return f'a {marker.split("_")[0].split("-")[0].lower()} is in progress in the main checkout'
    return ''


def recent_owner_paths(repo, state, paths, quiet):
    """The ``paths`` whose content changed less than ``quiet`` seconds ago.

    Quiet means unchanged bytes since our last observation, not an old mtime. Observations
    persist in ``state``/owner-content.json so a service restart does not restart the quiet
    interval. Clean paths disappear from the record; a later edit starts a fresh interval.
    """
    record = Path(state) / 'owner-content.json'
    try:
        previous = json.loads(record.read_text())
        if not isinstance(previous, dict):
            previous = {}
    except (OSError, ValueError):
        previous = {}
    now, observed, recent = time.time(), {}, []
    for path in paths:
        file = Path(repo) / path
        try:
            data = os.fsencode(os.readlink(file)) if file.is_symlink() else file.read_bytes()
            digest = hashlib.sha256(data).hexdigest()
        except FileNotFoundError:
            digest = 'deleted'
        except OSError:
            recent.append(path)
            continue
        old = previous.get(path)
        since = (old.get('since') if isinstance(old, dict) and old.get('hash') == digest else now)
        if not isinstance(since, (int, float)) or since > now:
            since = now
        observed[path] = {'hash': digest, 'since': since}
        if now - since < quiet:
            recent.append(path)
    if observed != previous:
        with tempfile.NamedTemporaryFile(mode='w', dir=state, prefix='owner-content.', delete=False) as out:
            json.dump(observed, out)
        os.replace(out.name, record)
    return recent


def land_around_edits(repo, base, old, new, *, require_clean=False):
    """Move ``base`` from ``old`` to ``new`` in ``repo`` around uncommitted edits; return the
    reason it could not, or ''.

    Prepare an index without checking out, rebase dirty regular files, then CAS the ref.
    No stash/reset/checkout touches the owner's work. Unsupported file kinds, staged
    overlapping edits and any conflict wait rather than guessing at their meaning. The
    real index is locked throughout; all files are prepared and checked before moving
    the ref, then checked again before installing any output. Snapshot and /proc checks
    detect races, but are not a lock shared by arbitrary external editors.

    ``require_clean`` refuses overlapping working edits instead of rebasing them,
    including edits appearing after a caller's preflight (planning-console apply).
    Raises LandingBroken when the ref moved and the checkout could not be finished.
    """
    repo = str(repo)
    index = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-path', 'index'))
    lock = Path(str(index) + '.lock')
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except OSError:
        return 'the main index is locked; another Git writer may be active'
    prepared, snapshots, outputs = {}, {}, []
    moved = finished = installed = False
    ref = f'refs/heads/{base}'
    path = 'main index'
    try:
        with tempfile.TemporaryDirectory(prefix='autowork-land-') as scratch:
            scratch = Path(scratch)
            env = dict(os.environ, GIT_INDEX_FILE=str(scratch / 'index'))
            shutil.copyfile(index, env['GIT_INDEX_FILE'])

            def run(*args, **kwargs):
                return subprocess.run(['git', '-C', repo, *args], capture_output=True, env=env, **kwargs)

            def tree(rev):
                entries = run('ls-tree', '-rz', rev, check=True).stdout.split(b'\0')
                return {os.fsdecode(e.split(b'\t', 1)[1]): e.split(b'\t', 1)[0].split()
                        for e in entries if e}

            before, after = tree(old), tree(new)
            changed = sorted(p for p in before.keys() | after.keys() if before.get(p) != after.get(p))
            # Raw blobs are correct only without checkout conversions. Do not silently
            # drop CRLF, smudge filters, encodings or ident expansion in this fallback.
            if (git(repo, 'config', '--get', 'core.autocrlf') not in (None, 'false')
                    or git(repo, 'config', '--get', 'core.eol') == 'crlf'):
                return f'{changed[0]}: checkout conversion requires a normal Git landing'
            if git(repo, 'config', '--get', 'core.sparseCheckout') == 'true':
                return f'{changed[0]}: sparse checkout requires a normal Git landing'
            staged = run('diff', '--cached', '--name-only', '-z', old, check=True).stdout.split(b'\0')
            result = run('read-tree', '-i', '-m', old, new)
            if result.returncode:
                return 'the main index cannot take the landing: ' + result.stderr.decode(errors='replace').strip()
            # Check both the current working attributes and the destination's index:
            # the session may itself introduce a conversion in .gitattributes.
            for source in ((), ('--cached',)):
                attrs = run('check-attr', *source, '-z', 'filter', 'working-tree-encoding', 'eol', 'text',
                            'ident', '--', *changed, check=True).stdout.split(b'\0')
                for name, attr, value in zip(attrs[0::3], attrs[1::3], attrs[2::3]):
                    if value not in (b'unspecified', b'unset'):
                        return f'{os.fsdecode(name)}: checkout conversion ({os.fsdecode(attr)}) is unsupported'
            for path in changed:
                file = Path(repo) / path
                # Refuse symlinks, gitlinks and paths through symlink directories.
                if any(p.is_symlink() for p in (file, *file.parents)):
                    return f'{path}: symlink path cannot be landed around safely'
                a, b = before.get(path), after.get(path)
                if any(e and e[0] not in (b'100644', b'100755') for e in (a, b)):
                    return f'{path}: unsupported file kind'
                if os.fsencode(path) in staged:
                    return f'{path}: staged edit overlaps the landing'
                if file.exists() and not file.is_file():
                    return f'{path}: not a regular file'
                info = file.stat() if file.exists() else None
                content = file.read_bytes() if info else None
                snapshots[path] = (info, content)
                base_blob = run('cat-file', 'blob', a[2].decode(), check=True).stdout if a else None
                target = run('cat-file', 'blob', b[2].decode(), check=True).stdout if b else None
                mode = (info.st_mode & 0o777) if info else None
                dirty_file = content != base_blob or (a and bool(mode & 0o111) != (a[0] == b'100755'))
                output = target
                if dirty_file:
                    if require_clean:
                        return f'{path}: dirty working file overlaps the landing'
                    if (content is None or base_blob is None or target is None or a[0] != b[0]
                            or bool(mode & 0o111) != (a[0] == b'100755')):
                        return f'{path}: uncommitted add/delete or mode change overlaps the landing'
                    for name, data in (('ours', target), ('base', base_blob), ('theirs', content)):
                        (scratch / name).write_bytes(data)
                    merged = run('merge-file', '-p', str(scratch / 'ours'), str(scratch / 'base'),
                                 str(scratch / 'theirs'))
                    if merged.returncode:
                        return f'{path}: uncommitted edit conflicts with the landing'
                    output = merged.stdout
                # Prepare destination-filesystem outputs before moving main: permission,
                # disk-space or cross-device errors must not leave a half-written file.
                file.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=file.parent, prefix='.autowork-land-', delete=False) as out:
                    staged_file = Path(out.name)
                    outputs.append(staged_file)
                    if output is not None:
                        out.write(output)
                        if mode is not None:
                            permissions = (mode if a and a[0] == b[0]
                                           else (mode & ~0o111) | (int(b[0], 8) & 0o111))
                        else:
                            # Linux is the runner's platform. Read rather than change
                            # the process-wide umask while preparing new files.
                            mask = next((line.split()[1] for line in Path('/proc/self/status').read_text().splitlines()
                                         if line.startswith('Umask:')), '077')
                            permissions = (0o777 if b[0] == b'100755' else 0o666) & ~int(mask, 8)
                        os.fchmod(out.fileno(), permissions)
                    out.flush()
                    os.fsync(out.fileno())
                prepared[path] = staged_file if output is not None else None
            # Fill the real lockfile too before CAS: ENOSPC/flush failures must not
            # advance HEAD or leave an old index describing staged reversions.
            path = 'main index'
            with os.fdopen(lock_fd, 'wb') as stream:
                lock_fd = None
                stream.write(Path(env['GIT_INDEX_FILE']).read_bytes())
                stream.flush()
                os.fsync(stream.fileno())

            # Validate after the expensive merge work, not just when we first read.
            def unchanged():
                reason = checkout_operation(repo)
                if reason:
                    return reason
                if git(repo, 'symbolic-ref', '--short', '-q', 'HEAD') != base:
                    return 'the main checkout changed branches during landing'
                held = open_for_writing([Path(repo) / p for p in snapshots])
                if held:
                    return f'{os.path.relpath(sorted(held)[0], repo)} is open for writing'

                def identity(st):
                    return ((st.st_dev, st.st_ino, st.st_mode, st.st_size, st.st_mtime_ns, st.st_ctime_ns)
                            if st else None)
                for name, (info, content) in snapshots.items():
                    file = Path(repo) / name
                    if any(p.is_symlink() for p in (file, *file.parents)):
                        return f'{name}: path changed to a symlink during landing'
                    now = file.lstat() if file.exists() else None
                    if identity(now) != identity(info) or (now and file.read_bytes() != content):
                        return f'{name}: working file changed during landing'
                return ''

            reason = unchanged()
            if reason:
                return reason
            if not git_ok(repo, 'update-ref', ref, new, old):
                return f'{base} changed during landing; compare-and-swap refused'
            moved = True
            reason = unchanged()
            if reason:
                if not git_ok(repo, 'update-ref', ref, old, new):
                    raise LandingBroken(f'Cannot restore {base} after refused landing: {reason}')
                moved = False
                return reason
            for path, output in prepared.items():
                file = Path(repo) / path
                if output is None:
                    file.unlink(missing_ok=True)
                else:
                    os.replace(output, file)
                installed = True
            # Only the committed session tree goes into the index. The rebased owner
            # edit stays a working-tree diff, never part of a commit.
            os.replace(lock, index)
            finished = True
            return ''
    except (OSError, subprocess.CalledProcessError) as exc:
        # A file may disappear between lstat/read in the post-CAS validation.
        # Nothing has been installed yet: restore the ref just as for a changed
        # snapshot, rather than retaining an advanced HEAD with the old index.
        if moved and not installed:
            if not git_ok(repo, 'update-ref', ref, old, new):
                raise LandingBroken(f'Cannot restore {base} after refused landing: {exc}') from exc
            moved = False
        if moved:
            raise LandingBroken(f'Landing moved {base} but could not finish writing {path}: {exc}; '
                                f'prepared index kept at {lock}; remaining .autowork-land-* outputs kept') from exc
        if isinstance(exc, OSError) and exc.filename:
            path = os.path.relpath(exc.filename, repo)
        return f'{path}: cannot prepare landing: {exc}'
    finally:
        if lock_fd is not None:
            os.close(lock_fd)
        if not moved or finished:
            lock.unlink(missing_ok=True)
            for output in outputs:
                output.unlink(missing_ok=True)
