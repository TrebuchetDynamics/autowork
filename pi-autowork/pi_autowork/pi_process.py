"""Linux process-lifetime boundary for Pi or its unmodified SDK host.

Executable seam::

    python pi_process.py --identity PRIVATE_JSON --deadline SECONDS -- pi [args...]

The SDK may append --version or --mode rpc. Alternatively guard the SDK host:
``-- python pi_rpc.py [args...]``; pi_pid/pi_start_time then identify that host,
not its Pi subprocess. All three standard descriptors are inherited, not piped
or drained; this module never reads or writes RPC. The wrapper stays in its
caller's process group; the guarded command gets a separate session/group.
TERM/INT and parent death stop the tree. Exit status is Pi's status (signals use
128+signal), 124 on deadline, or 125 on supervisor/setup/cleanup failure.

Identity is an atomic 0600 JSON snapshot: pid/start_time identify this wrapper,
pi_pid/pi_start_time identify Pi, cleanup_complete is initially false, and
exit_code is initially null. Start times are /proc clock-tick strings. Only a
final cleanup_complete=true record, matched to the expected wrapper identity,
is proof that all its children were reaped. Missing/stale/false records are NOT
proof of cleanup. Use a private directory and a unique path per concurrent
invocation; sequential --version and RPC launches may reuse a path. No command
arguments, prompts or exception messages are recorded. Existing records are
never authority for signalling anything.

Requires Linux prctl, /proc and Python pidfd APIs (no PID-only signal fallback).
Subreaping catches double forks and setsid escapes; pidfds bind signals to the
observed process, with start ticks and live ancestry checked when acquiring
handles. Cleanup grants 0.35s for TERM then escalates, with a 1.5s total budget.
The deadline bounds execution, plus that bounded cleanup allowance.

This is scoped supervision, not a security boundary or cgroup replacement.
SIGKILL of this wrapper cannot run cleanup or publish proof; Pi has a parent-
death kill but its descendants can survive. Uninterruptible tasks, hostile
fork storms, proc restrictions, external reparenting/tracing and kernel or
filesystem stalls can defeat bounded complete cleanup. Such completion must
not be inferred from exit alone. A delegated cgroup is needed for stronger
containment, especially when the whole worker group is forcibly killed.
"""
import argparse
import ctypes
import json
import math
import os
from pathlib import Path
import signal
import subprocess
import tempfile
import time


_GRACE = .35
_CLEANUP_BUDGET = 1.5


def _stat(pid):
    """Return (parent PID, start ticks); comm can contain spaces and ')'."""
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return int(fields[1]), fields[19]
    except (FileNotFoundError, ProcessLookupError):
        return None


def _pin(pid, started):
    """Pin an identity, never signal by a possibly recycled numeric PID."""
    before = _stat(pid)
    if before is None or before[1] != started:
        return None
    try:
        fd = os.pidfd_open(pid)
    except ProcessLookupError:
        return None
    try:
        after = _stat(pid)
        if after is not None and after[1] == started:
            return fd
    except BaseException:
        os.close(fd)
        raise
    os.close(fd)
    return None


def _prctl(option, value):
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(option, value, 0, 0, 0) != 0:
        raise OSError(ctypes.get_errno(), 'process supervision unavailable')


def _write_identity(path, record):
    # mkstemp is 0600 even with a permissive caller umask; replace never follows
    # an old identity symlink. No persisted record is read as kill authority.
    fd, temporary = tempfile.mkstemp(prefix='.pi-process-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(record, stream, sort_keys=True)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        try:
            os.unlink(temporary)
        except FileNotFoundError:
            pass


def _discover(root, started, handles, until):
    """Walk live parent links, including children forked by nonleader threads.

    A child may exit/reparent during the walk; the next pass finds adoptees at
    the subreaper. Validate BOTH ends after pinning, not a stale /proc snapshot.
    """
    pending = [(root, started)]
    seen = set()
    while pending and time.monotonic() < until:
        pid, born = pending.pop()
        if (pid, born) in seen:
            continue
        seen.add((pid, born))
        parent = _stat(pid)
        if parent is None or parent[1] != born:
            continue
        try:
            tasks = list(Path(f'/proc/{pid}/task').iterdir())
        except (FileNotFoundError, ProcessLookupError):
            continue
        for task in tasks:
            try:
                children = (task / 'children').read_text().split()
            except (FileNotFoundError, ProcessLookupError):
                continue
            for value in children:
                if time.monotonic() >= until:
                    return
                child = int(value)
                info = _stat(child)
                if info is None or info[0] != pid:
                    continue
                key = (child, info[1])
                fd = _pin(*key)
                if fd is None:
                    continue
                current_parent, current_child = _stat(pid), _stat(child)
                if (current_parent is None or current_parent[1] != born
                        or current_child != info):
                    os.close(fd)
                    continue
                if key in handles:
                    os.close(fd)
                else:
                    handles[key] = fd
                pending.append(key)


def _reap(pi):
    """Return true only when the kernel confirms there are no children left."""
    while True:
        try:
            pid, status = os.waitpid(-1, os.WNOHANG)
        except ChildProcessError:
            return True
        if pid == 0:
            return False
        if pi is not None and pid == pi.pid:
            pi.returncode = os.waitstatus_to_exitcode(status)


def _cleanup(pi, started):
    began = time.monotonic()
    until = began + _CLEANUP_BUDGET
    handles, terminated = {}, set()
    try:
        while time.monotonic() < until:
            _discover(os.getpid(), started, handles, until)
            force = time.monotonic() - began >= _GRACE
            for key, fd in handles.items():
                if not force and key in terminated:
                    continue
                try:
                    signal.pidfd_send_signal(fd, signal.SIGKILL if force else signal.SIGTERM)
                except ProcessLookupError:
                    pass
                terminated.add(key)
            if _reap(pi):
                return True
            time.sleep(.01)
        return _reap(pi)
    finally:
        for fd in handles.values():
            os.close(fd)


class _QuietParser(argparse.ArgumentParser):
    def error(self, message):
        # argparse's default error includes raw arguments on stderr.
        raise ValueError('invalid supervisor invocation')


def main(argv=None):
    began = time.monotonic()
    parent = os.getppid()
    stopped = 0

    def stop(signum, frame):
        nonlocal stopped
        if not stopped:
            stopped = signum

    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, stop)
    # SIG_IGN survives exec and would auto-reap children, losing their status.
    signal.signal(signal.SIGCHLD, signal.SIG_DFL)
    parser = _QuietParser(add_help=False)
    parser.add_argument('--identity', required=True, type=Path)
    parser.add_argument('--deadline', required=True, type=float)
    parser.add_argument('command', nargs=argparse.REMAINDER)
    try:
        args = parser.parse_args(argv)
        command = args.command
        if command and command[0] == '--':
            command = command[1:]
        if not command or not math.isfinite(args.deadline) or args.deadline <= 0:
            return 125
    except (ValueError, TypeError):
        return 125

    started = _stat(os.getpid())[1]
    record = dict(pid=os.getpid(), start_time=started, pi_pid=None,
                  pi_start_time=None, cleanup_complete=False, exit_code=None)
    pi = None
    code = 125
    try:
        _write_identity(args.identity, record)
        _prctl(36, 1)  # PR_SET_CHILD_SUBREAPER
        _prctl(1, signal.SIGTERM)  # PR_SET_PDEATHSIG
        if os.getppid() != parent or parent == 1:
            stop(signal.SIGTERM, None)  # close the parent-death registration race
        # Fail closed before launching Pi if safe signalling isn't available.
        fd = os.pidfd_open(os.getpid())
        try:
            signal.pidfd_send_signal(fd, 0)
        finally:
            os.close(fd)
        wrapper_pid = os.getpid()

        def child_setup():
            # This standalone executable is single-threaded: preexec is safe.
            _prctl(1, signal.SIGKILL)
            if os.getppid() != wrapper_pid:
                os._exit(125)

        if stopped:
            code = 128 + stopped
            record['reason'] = 'signal'
        elif time.monotonic() - began >= args.deadline:
            code = 124
            record['reason'] = 'deadline'
        else:
            # No new stdio pipes, and no communicate()/drain of inherited FDs.
            pi = subprocess.Popen(command, start_new_session=True, preexec_fn=child_setup)
            record.update(pi_pid=pi.pid, pi_start_time=_stat(pi.pid)[1])
            _write_identity(args.identity, record)
            while True:
                if stopped:
                    code = 128 + stopped
                    record['reason'] = 'signal'
                    break
                result = pi.poll()
                if result is not None:
                    code = result if result >= 0 else 128 - result
                    record['reason'] = 'exit'
                    break
                if time.monotonic() - began >= args.deadline:
                    code = 124
                    record['reason'] = 'deadline'
                    break
                time.sleep(.01)
    except (OSError, ValueError, AttributeError, subprocess.SubprocessError):
        record['reason'] = 'supervisor_error'
        code = 125
    finally:
        try:
            record['cleanup_complete'] = _cleanup(pi, started)
        except (OSError, ValueError, AttributeError):
            record['cleanup_complete'] = False
        if not record['cleanup_complete']:
            code = 125
            record['reason'] = 'cleanup_incomplete'
        record['exit_code'] = code
        try:
            _write_identity(args.identity, record)
        except OSError:
            code = 125  # old false snapshot cannot be mistaken for proof
    return code


if __name__ == '__main__':
    raise SystemExit(main())
