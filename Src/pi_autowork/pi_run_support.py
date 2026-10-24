"""Shared event parsing, redaction and command watchdog; no transport or job policy."""
import json
import os
from pathlib import Path
import re
import signal
import time

if __package__:
    from . import pi_events
else:
    import pi_events

SECRET = re.compile(r'(sk-[A-Za-z0-9_-]{8,}|Bearer [A-Za-z0-9._~+/=-]+'
                    r'|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Za-z0-9_]*=[^\s]+)')

def redact(text):
    return SECRET.sub('[redacted]', text or '')


def analyse(raw):
    """Account one invocation's event stream, never cumulative session history.

    Share authoritative surfaces and conservative coverage with the RPC path.
    Pi resumes context internally; session headers and RPC history/stat snapshots
    are not fresh usage. See pi_events for the installed-Pi surface inventory.
    """
    projection = pi_events.EventProjection(clock=None)
    result = projection.outcome()
    for line in raw.split('\n'):
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except ValueError:
            value = None
        # Corrupt/malformed records may hide usage: keep the known subtotal but
        # do not certify complete coverage merely because settlement survived.
        try:
            projection.consume(value if isinstance(value, dict) else {})
        except pi_events.ProjectionOverflow as error:
            # The last valid snapshot is a lower bound, not a complete bill.
            # Retain its measured subtotal and attribution even when the event
            # that overflowed cannot be safely projected.
            result.update(settled=False, aborted=False, stop=None, text='', error=str(error),
                          tokens=None, input_tokens=None, output_tokens=None, cost=None,
                          failure_kind='projection_overflow', retry_safe=False)
            result['usage_coverage'].update(overflow=True, complete=False, tokens_complete=False,
                                           input_tokens_complete=False, output_tokens_complete=False,
                                           cost_complete=False)
            return result
        result = projection.outcome()
    return result


# Build servers a worker starts on purpose and leaves idle are not stuck commands.
DAEMONS = re.compile(r'GradleDaemon|KotlinCompileDaemon|flutter_tools\.snapshot.*daemon|--daemon\b|language-server')


def command_limit(role, limit, env=os.environ):
    """Seconds one tool command of a worker may run (TOOLSET-215-a8), or None (reviews and jobs)."""
    if role != 'worker':
        return None
    try:
        value = float(env.get('PI_AUTOWORK_COMMAND_TIMEOUT') or 1800)
        cap = float(limit) - 120  # always below the worker's own limit, so the worker can react
    except ValueError:
        return None
    return min(value, cap) if value > 0 and cap > 0 else None


def _children(pid):
    found = []
    for entry in Path('/proc').glob('[0-9]*'):
        try:
            fields = (entry / 'stat').read_text().rsplit(')', 1)[1].split()
        except (OSError, IndexError):
            continue
        if int(fields[1]) == pid:
            found.append(int(entry.name))
    return found


def _age(pid):
    """Seconds since ``pid`` started, or None."""
    try:
        start = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[19])
        uptime = float(Path('/proc/uptime').read_text().split()[0])
    except (OSError, IndexError, ValueError):
        return None
    return uptime - start / os.sysconf('SC_CLK_TCK')


def _command(pid):
    try:
        return ' '.join(Path(f'/proc/{pid}/cmdline').read_bytes().decode(errors='replace').split('\0')).strip()
    except OSError:
        return ''


def _tree(pid):
    pids, pending = [], [pid]
    while pending:
        current = pending.pop()
        pids.append(current)
        pending.extend(_children(current))
    return pids


def stop_stuck_commands(runner_pid, limit, stopping, now=None, *, pi_pid=None, pi_started=None):
    """A tool command Pi started that has run longer than ``limit`` gets SIGTERM, then SIGKILL
    30 s later, with everything it started (TOOLSET-215-a8: one browser test hung for 89 of a
    worker's 90 minutes). Pi reports the failed call, so the worker continues the same attempt.
    ``stopping`` maps process birth identities already signalled to when; returns the commands stopped now."""
    if __package__:
        from .processes import process_stat, start_time
        from .pi_process import signal_owned_tree
    else:
        from processes import process_stat, start_time
        from pi_process import signal_owned_tree
    now = time.monotonic() if now is None else now
    stopped = []
    for pi in _children(runner_pid):  # timeout or SDK host owns Pi directly
        if pi_pid is not None and pi != pi_pid:
            continue
        parent = process_stat(pi)
        if (parent is None or parent.parent != runner_pid
                or (pi_started is not None and parent.started != pi_started)):
            continue
        for command in _children(pi):
            line = _command(command)
            born = start_time(command)
            if not born:
                continue
            key = (command, born)
            if key in stopping:
                if now - stopping[key] >= 30:
                    signal_owned_tree(command, born, signal.SIGKILL, parent=pi, parent_started=parent.started)
                continue
            age = _age(command)
            directory = os.environ.get('AUTOWORK_WORKER_CHECK_DIR')
            if age is not None and directory:
                from pi_autowork.engine import autowork_run
                # Merge overlapping waits: two wrappers in one tool call must not double its allowance.
                end = 0
                for start, finish in sorted(autowork_run.queue_intervals(directory, command)):
                    age -= max(0, finish - max(start, end))
                    end = max(end, finish)
            if age is None or age < limit or DAEMONS.search(line):
                continue
            if not signal_owned_tree(command, born, signal.SIGTERM, parent=pi, parent_started=parent.started):
                continue
            stopping[key] = now
            stopped.append((int(age // 60), line[:120]))
    return stopped
