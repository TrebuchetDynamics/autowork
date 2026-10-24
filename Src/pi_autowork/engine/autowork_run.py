#!/usr/bin/env python3
"""Run a worker's long suite/build in a host-wide worker check slot (stdlib only)."""
import fcntl
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import time


def process_identity(pid):
    """Linux process start ticks, so old queue records cannot match a reused PID."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return int(fields[1]), int(fields[19])
    except (OSError, ValueError, IndexError):
        return None


def slot_root():
    # Same host-wide directory as pi_autowork.main_check; never a task's TMPDIR or XDG override.
    uid = os.getuid()
    runtime = Path(f'/run/user/{uid}')
    root = Path(os.environ.get('PI_AUTOWORK_CHECK_ROOT') or
                (runtime if runtime.is_dir() else Path('/var/tmp')) / f'autowork-checks-{uid}')
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != uid or root.stat().st_mode & 0o077:
        raise ValueError(f'check slot directory must be private and owned by this user: {root}')
    return root


def records(directory):
    for path in Path(directory).glob('*.json') if directory else ():
        try:
            value = json.loads(path.read_text())
            if isinstance(value, dict):
                yield value
        except (OSError, ValueError):
            continue  # an interrupted write is not a wait record


def queue_intervals(directory, command):
    """Queue intervals attributable to this tool command, including completed wrappers."""
    identity = process_identity(command)
    if identity is None:
        return []
    intervals = []
    for row in records(directory):
        if [command, identity[1]] not in row.get('ancestors', []):
            continue
        end = row.get('admitted') or row.get('finished') or row['updated']
        live = process_identity(row['pid'])
        if row.get('admitted') is None and not row.get('finished') and live and live[1] == row['start_ticks']:
            end = time.monotonic()
        intervals.append((row['waiting_since'], end))
    return intervals


def report_wait(directory, report):
    """Enrich an existing worker report; do not manufacture one for a dead worker."""
    path = Path(report)
    if not path.is_file():
        return
    value = json.loads(path.read_text())
    if not isinstance(value, dict):
        return
    value['worker_check_slot_wait_seconds'] = sum(
        row.get('wait_seconds', max(0, (row.get('finished') or row['updated']) - row['waiting_since']))
        for row in records(directory))
    temporary = path.with_suffix('.wait.tmp')
    temporary.write_text(json.dumps(value, indent=2) + '\n')
    temporary.replace(path)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    if not argv:
        print('usage: autowork-run <command> [args ...]', file=sys.stderr)
        return 2
    count = int(os.environ.get('PI_AUTOWORK_WORKER_CHECK_SLOTS') or max(2, (os.cpu_count() or 1) // 4))
    if count < 1:
        raise ValueError('PI_AUTOWORK_WORKER_CHECK_SLOTS must be positive')
    root = slot_root()
    pid = os.getpid()
    parent, ticks = process_identity(pid)
    ancestors, current = [], pid
    while identity := process_identity(current):
        ancestors.append([current, identity[1]])
        current = identity[0]
    row = dict(pid=pid, ppid=parent, start_ticks=ticks, ancestors=ancestors,
               waiting_since=time.monotonic(), admitted=None)
    directory = os.environ.get('AUTOWORK_WORKER_CHECK_DIR')
    record = Path(directory) / f'{pid}-{ticks}.json' if directory else None

    def save():
        if record is not None:
            record.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
            row['updated'] = time.monotonic()
            temporary = record.with_suffix('.tmp')
            temporary.write_text(json.dumps(row) + '\n')
            temporary.replace(record)

    lease = None
    announced = False
    try:
        while lease is None:
            save()
            for index in range(count):
                fd = os.open(root / f'worker-slot-{index}', os.O_RDWR | os.O_CREAT, 0o600)
                try:
                    fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                except BlockingIOError:
                    os.close(fd)
                else:
                    lease = fd
                    break
            if lease is None:
                if not announced:
                    print('autowork-run: waiting for a worker check slot', file=sys.stderr, flush=True)
                    announced = True
                time.sleep(.1)
        row['admitted'] = time.monotonic()
        row['wait_seconds'] = row['admitted'] - row['waiting_since'] if announced else 0.0
        save()
        # Inherit the lease: killing this supervisor cannot admit another suite while its child runs.
        with subprocess.Popen(argv, pass_fds=(lease,), start_new_session=True) as child:
            interrupted, descendants = False, {}
            def forward(sig, frame):
                nonlocal interrupted
                interrupted = True
                # Test runners can start new sessions and close fds. Capture their identities
                # before terminating their parent, so reparenting cannot hide a running suite.
                processes = {int(p.name): process_identity(int(p.name)) for p in Path('/proc').glob('[0-9]*')}
                pending = [child.pid]
                while pending:
                    parent = pending.pop()
                    for pid, identity in processes.items():
                        if identity and identity[0] == parent and pid not in descendants:
                            descendants[pid] = identity[1]
                            pending.append(pid)
                for pid in descendants:
                    try:
                        os.kill(pid, sig)
                    except ProcessLookupError:
                        pass
                try:
                    os.killpg(child.pid, sig)
                except ProcessLookupError:
                    pass
            signal.signal(signal.SIGTERM, forward)
            signal.signal(signal.SIGINT, forward)
            rc = child.wait()
        if rc < 0 or interrupted:
            # Finish cancellation even for TERM-ignoring checks that left the command group.
            for pid, ticks in descendants.items():
                identity = process_identity(pid)
                if identity and identity[1] == ticks:
                    try:
                        os.kill(pid, signal.SIGKILL)
                    except ProcessLookupError:
                        pass
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
        else:
            fcntl.flock(lease, fcntl.LOCK_UN)  # normal completion releases leftover daemon descriptors
        return rc if rc >= 0 else 128 - rc
    except FileNotFoundError as error:
        print(f'autowork-run: {error}', file=sys.stderr)
        return 127
    except PermissionError as error:
        print(f'autowork-run: {error}', file=sys.stderr)
        return 126
    finally:
        row['finished'] = time.monotonic()
        save()
        if lease is not None:
            os.close(lease)


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        try:
            sys.exit(main())
        except ValueError as error:
            print(f'autowork-run: {error}', file=sys.stderr)
            sys.exit(2)
    finally:
        sys.argv = previous
