"""Main's full offline check after a landing, so a red main opens its own repair (TOOLSET-176-98).

A task's review runs only that task's Checks; a landing that breaks an unrelated test went
unnoticed until a person ran the full check. A repository that declares its full offline
check (PI_AUTOWORK_MAIN_CHECK) has it run in the background, once per main revision, in a
disposable checkout of main; a failure names the failing tests and the commits since the
last green revision, and the DOCS-MAINTAINER adds one repair task for it. Standard library only.
"""
import concurrent.futures
from contextlib import contextmanager
import fcntl
import json
import os
from pathlib import Path
import re
import runpy
import shlex
import shutil
import signal
import subprocess
import sys
import tempfile
import time

FAILURE = re.compile(r'^(FAIL|ERROR|UNEXPECTED SUCCESS): (\S+) \(([^)]+)\)', re.M)
TIMEOUT = re.compile(r'^TIMEOUT: (\S+) after', re.M)


FULL_CHECK = re.compile(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Full check:(?:\*\*)?[ \t]*`?([^`\n]+?)`?[ \t]*$', re.M)


def full_check(repo, env=os.environ):
    """The repository's whole offline suite (TOOLSET-180-72): PI_AUTOWORK_VALIDATE, else the
    `Full check: <command>` line of its AGENTS.md; '' when it declares none."""
    declared = env.get('PI_AUTOWORK_VALIDATE', '').strip()
    if declared or not repo:
        return declared
    try:
        found = FULL_CHECK.search((Path(repo) / 'AGENTS.md').read_text(errors='replace'))
    except OSError:
        return ''
    return found[1].strip() if found else ''


def command(env=os.environ, repo=None):
    """Main's check: PI_AUTOWORK_MAIN_CHECK, else the repository's full check."""
    return env.get('PI_AUTOWORK_MAIN_CHECK', '').strip() or full_check(repo, env)


def slot_home():
    """The per-user pool the check slots live in: one host-wide location, from the user alone.

    Not XDG_RUNTIME_DIR: a cron job or a systemd unit without it derived a second pool, with its
    own PI_AUTOWORK_CHECK_SLOTS, so the swap-safe limit was never host-wide.
    """
    uid = os.getuid()
    for candidate in (Path(f'/run/user/{uid}'), Path('/var/tmp')):
        if candidate.is_dir():
            return candidate / f'autowork-checks-{uid}'
    raise ValueError('no per-user runtime directory for the check slots')


def slot_root():
    """One per-user pool across repositories, never under a task's TMPDIR.

    PI_AUTOWORK_CHECK_ROOT names it for a fixture or an isolated host; nothing else in the
    environment may move it.
    """
    override = os.environ.get('PI_AUTOWORK_CHECK_ROOT')
    root = Path(override) if override else slot_home()
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    if root.is_symlink() or root.stat().st_uid != os.getuid() or root.stat().st_mode & 0o077:
        raise ValueError(f'check slot directory must be private and owned by this user: {root}')
    return root


# A background main check waiting this long is admitted in turn with reviews, so a busy fleet
# never leaves main unchecked.
BACKGROUND_WAIT = 1800


def ticket_rank(name, now=None):
    """(class, enqueued) of a `wait-<class>-<monotonic ns>-<pid>` ticket; lower is admitted first.

    Class 0 is a review's suite, class 1 a background main check: main checks of every runner
    held the host's slots while a review that lands work waited behind them."""
    try:
        _, kind, stamp, _ = name.split('-')
        kind, stamp = int(kind), int(stamp)
    except ValueError:
        return (0, 0)
    now = time.monotonic_ns() if now is None else now
    return (0 if now - stamp >= BACKGROUND_WAIT * 10**9 else kind, stamp)


@contextmanager
def check_slot(waiting, background=False):
    """Admission to host-wide flock slots: reviews before background main checks, each in
    arrival order; dead tickets are cleaned on the next poll.

    Only tickets are unlinked. Slot/mutex inodes must stay put, including across restarts.
    The command inherits the lease: killing its supervisor does not release a still-live check.
    Normal completion unlocks it even if a background descendant kept an inherited fd.
    """
    count = int(os.environ.get('PI_AUTOWORK_CHECK_SLOTS') or max(1, (os.cpu_count() or 1) // 8))
    if count < 0:
        raise ValueError('PI_AUTOWORK_CHECK_SLOTS must be nonnegative')
    if count == 0:
        yield None
        return
    root = slot_root()
    lease, ticket = None, None
    with (root / 'queue.lock').open('a') as mutex:
        try:
            while lease is None:
                fcntl.flock(mutex, fcntl.LOCK_EX)
                try:
                    if ticket is None:
                        ticket = (root / f'wait-{int(background)}-{time.monotonic_ns():020d}-{os.getpid()}').open('x')
                        fcntl.flock(ticket, fcntl.LOCK_EX)
                    ahead, now = 0, time.monotonic_ns()
                    mine = ticket_rank(Path(ticket.name).name, now)
                    for path in sorted(root.glob('wait-*')):
                        if path == Path(ticket.name):
                            continue
                        with path.open('a') as other:
                            try:
                                fcntl.flock(other, fcntl.LOCK_EX | fcntl.LOCK_NB)
                            except BlockingIOError:
                                ahead += ticket_rank(path.name, now) < mine
                            else:
                                path.unlink()  # dead waiter, including SIGKILL
                    busy = 0
                    for index in range(count):
                        fd = os.open(root / f'slot-{index}', os.O_RDWR | os.O_CREAT, 0o600)
                        try:
                            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            busy += 1
                        else:
                            if ahead == 0 and lease is None:
                                lease = fd
                        if fd != lease:
                            os.close(fd)
                    if lease is not None:
                        Path(ticket.name).unlink()
                finally:
                    fcntl.flock(mutex, fcntl.LOCK_UN)
                if lease is None:
                    waiting(ahead + busy)
                    time.sleep(.1)
            yield lease
            fcntl.flock(lease, fcntl.LOCK_UN)  # the check ended; leftover daemons must not occupy its slot
        finally:
            if ticket is not None:
                # Creation/admission scans use the same mutex, so no live ticket is mistaken for stale.
                fcntl.flock(mutex, fcntl.LOCK_EX)
                Path(ticket.name).unlink(missing_ok=True)
                ticket.close()
                fcntl.flock(mutex, fcntl.LOCK_UN)
            if lease is not None:
                os.close(lease)  # on abnormal exit, a surviving command still owns its inherited fd


class Stopped(Exception):
    """The caller was told to stop while its suite waited or ran; the suite is killed."""


def run_command(cmd, checkout, limit, progress, output=None, stop=None, background=False):
    """Run a full suite with its complete timeout after admission; report queue progress.
    A background main check is admitted after the reviews waiting with it.

    The suite runs in its own session, which a stop sent to the caller's group never reaches:
    with ``stop`` (a callable), a true answer kills it and raises Stopped instead.
    """
    queued = timed_out = False

    def notify(state, **fields):
        value = dict(state=state, pid=os.getpid(), updated=time.time(), **fields)
        path = Path(progress)
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(value) + '\n')
        tmp.replace(path)

    def transition(waiting):
        fd = os.environ.get('AUTOWORK_CHECK_WAIT_FD')
        if fd:
            try:
                os.write(int(fd), f'{time.monotonic()} {int(waiting)}\n'.encode())
            except (OSError, ValueError):
                pass  # direct checks and old engines have no wait-accounting channel

    def wait(ahead):
        nonlocal queued
        if stop and stop():
            raise Stopped(f'stopped while queued: {cmd}')
        if not queued:
            transition(True)
        queued = True
        notify('waiting', ahead=ahead)

    try:
        with check_slot(wait, background) as lease:
            if queued:
                transition(False)
            notify('running', started=time.time())
            env = {k: v for k, v in os.environ.items() if k != 'AUTOWORK_CHECK_WAIT_FD'}
            with subprocess.Popen(['bash', '-c', cmd], cwd=checkout, env=env, stdin=subprocess.DEVNULL,
                                  stdout=output, stderr=subprocess.STDOUT, start_new_session=True,
                                  pass_fds=(() if lease is None else (lease,))) as process:
                deadline = time.monotonic() + limit
                while True:
                    left = deadline - time.monotonic()
                    try:
                        return process.wait(timeout=min(left, 1) if stop else left), False
                    except subprocess.TimeoutExpired:
                        stopped = bool(stop and stop())
                        if not stopped and time.monotonic() < deadline:
                            continue
                        os.killpg(process.pid, signal.SIGKILL)
                        if stopped:
                            process.wait()
                            raise Stopped(f'stopped: {cmd}')
                        timed_out = True
                        return process.wait(), True
    finally:
        if queued:
            transition(False)
        notify('finished', timed_out=timed_out)


def slot_status(path):
    try:
        value = json.loads(Path(path).read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def record_path(state):
    return Path(state) / 'main_check.json'


def read(state):
    try:
        value = json.loads(record_path(state).read_text())
    except (OSError, ValueError):
        return {}
    if not isinstance(value, dict):
        return {}
    if value.get('state') == 'running' and value.get('slot_status'):
        value['check_slot'] = slot_status(value['slot_status'])
    return value


def write(state, value):
    path = record_path(state)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value) + '\n')
    tmp.replace(path)
    return value


def publish_evidence(state, common, revision, value):
    """Publish a complete, read-only snapshot outside worktrees; retain five revisions."""
    root = Path(common) / 'autowork-execution/main-evidence'
    root.mkdir(parents=True, exist_ok=True)
    bundle = root / revision
    value['evidence'] = str(bundle)
    value['checked_rev'] = revision  # recheck records clear rev so the scheduler will run again

    def remove(path):
        path.chmod(0o700)
        shutil.rmtree(path)

    with tempfile.TemporaryDirectory(prefix='.publishing-', dir=root) as staging:
        staging = Path(staging)
        (staging / 'main_check.json').write_text(json.dumps(value) + '\n')
        (staging / 'flaky_history.json').write_text(json.dumps(value.get('flaky_history') or {}) + '\n')
        for name in ('main-check.log', 'main-check.exit', 'main-check-reruns.log'):
            source = Path(state) / name
            # A green run has no reruns; never publish diagnostics left by an older run.
            if name == 'main-check-reruns.log' and exit_code(state) == 0:
                content = b''
            else:
                try:
                    content = source.read_bytes()
                except FileNotFoundError:
                    content = b''
            (staging / name).write_bytes(content)
        for path in staging.iterdir():
            path.chmod(0o400)
        if bundle.exists():
            remove(bundle)
        staging.rename(bundle)
        bundle.chmod(0o500)
    revisions = sorted((path for path in root.iterdir() if path.is_dir() and not path.name.startswith('.')),
                       key=lambda path: path.stat().st_mtime_ns, reverse=True)
    for old in revisions[5:]:
        remove(old)


def exit_code(state):
    """Only a complete receipt counts: shell redirection can expose an empty file first."""
    try:
        return int((Path(state) / 'main-check.exit').read_text().strip())
    except (OSError, ValueError):
        return None


# Diagnostic selection only: a crashed check names no test (TOOLSET-237-35).
CRASH = re.compile(r'exited unexpectedly|Segmentation fault|core dumped|panic:|Fatal error|Killed', re.I)
WEAK_CRASH = re.compile(r'Bad state|Aborted|out of memory', re.I)
LOG_LEVEL = re.compile(r'^(?:\[(?:trace|debug|info|warn(?:ing)?|error|fatal|critical)\]|'
                       r'(?:trace|debug|info|warn(?:ing)?|error|fatal|critical):)', re.I)
PYTHON_EXCEPTION = re.compile(r'^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)*(?::|$)')


def crash_line(log_text):
    """Last highest-ranked crash message, excluding log-level lines; else last non-blank line.

    Keep indentation until traceback exceptions are identified, so source and frame lines
    cannot be mistaken for the final exception (TOOLSET-244-5d).
    """
    hit, last, highest = '', 'no output', 0
    traceback = False
    for raw in log_text.splitlines():
        if not raw.strip():
            continue
        last = ' '.join(raw.split())
        if LOG_LEVEL.match(raw.lstrip()):
            continue
        if raw.startswith('Traceback (most recent call last):'):
            traceback = True
        exception = traceback and bool(PYTHON_EXCEPTION.match(raw))
        if exception:
            traceback = False
        rank = 2 if exception or CRASH.search(last) else 1 if WEAK_CRASH.search(last) else 0
        if rank and rank >= highest:
            hit, highest = last, rank
    return (hit or last)[:300]


def failures(log_text, limit=20):
    """Failing tests as 'module.Class.test' (or a timed-out directory), first ones first."""
    found = [where for _, _, where in FAILURE.findall(log_text)]
    found += re.findall(r'^FAILED (\S+::\S+)', log_text, re.M)  # pytest
    found += re.findall(r'^\s*--- FAIL: (\S+)', log_text, re.M)  # go test
    found += [f'{directory} (timed out)' for directory in TIMEOUT.findall(log_text)]
    return list(dict.fromkeys(found))[:limit]


def complete_results(text, root, cmd=None):
    """Do not excuse a flaky test alongside a process that died without a summary.

    The offline inventory may shard modules, so count its units, not just modules.
    Unknown shell commands without CHECK boundaries cannot prove completeness.
    ``cmd`` is the command that produced ``text``: the gate's check may be declared in
    AGENTS.md and never enter this process's environment, so only main's own check passes it
    explicitly; every other caller means the repository's full check.
    """
    summary = re.compile(r'^Ran \d+ tests? in [\d.]+s\n\n(?:OK\b|FAILED\b)', re.M)
    sections = list(re.finditer(r'^CHECK (.+) \((\d+) modules\)$', text, re.M))
    expected = {}
    if 'Offline inventory:' in text:
        try:
            checker = runpy.run_path(str(root / 'scripts/check.py'))
            for directory, _ in checker['units'](root, checker['discover_tests'](root)):
                name = directory.relative_to(root).as_posix()
                expected[name] = expected.get(name, 0) + 1
        except (OSError, ValueError, KeyError, TypeError):
            return False
        if set(expected) != {section[1] for section in sections}:
            return False
    if not sections:
        cmd = full_check(str(root)) if cmd is None else cmd
        try:
            args = shlex.split(cmd)
        except ValueError:
            return False
        return (len(args) >= 3 and args[1:3] == ['-m', 'unittest']
                and not re.search(r'[;&|<>()\n]', cmd) and len(summary.findall(text)) == 1)
    for index, section in enumerate(sections):
        end = sections[index + 1].start() if index + 1 < len(sections) else len(text)
        if len(summary.findall(text[section.end():end])) != expected.get(section[1], int(section[2])):
            return False
    return True


def rerun_failures(log, root, receipt, rev, timeout=600, cmd=None, only=None, workers=4):
    """Rerun up to ten IDs in their original CHECK directory, before scratch cleanup.

    A separate revision-bound receipt lists only completed, ungated passes. Missing
    modules, ambiguous directories, skips, timeouts and excess failures stay red.
    ``cmd`` is the command whose log this is; without it, the repository's declared full
    check explains a gate log, and main's own check passes its command explicitly. ``only``
    limits the reruns to those IDs, and ``workers`` is how many run side by side.
    """
    root, receipt = Path(root).resolve(), Path(receipt)
    text = Path(log).read_text(errors='replace')
    directory, locations = root, {}
    for line in text.splitlines():
        section = re.match(r'^CHECK (.+) \(\d+ modules\)$', line)
        if section:
            directory = (root / section[1]).resolve()
        match = FAILURE.match(line)
        if match:
            locations.setdefault(match[3], set()).add(directory)
    # Match scripts/check.py's fixture environment: no inherited runner/live flags,
    # and fixture-local pushes must not inherit the runner's remote push guard.
    env = {k: v for k, v in os.environ.items()
           if not k.startswith(('PI_AUTOWORK_', 'AUTOWORK_')) and k not in (
               'CONTAINMENT_LINUX_TESTS', 'RUN_CONTROLLER_BRIDGE_LINUX',
               'HERMES_NATIVE_HANDOFF_TEST', 'HERMES_NATIVE_REGISTRATION_TEST')}
    try:
        entries = [(env.get(f'GIT_CONFIG_KEY_{i}', ''), env.get(f'GIT_CONFIG_VALUE_{i}', ''))
                   for i in range(int(env.get('GIT_CONFIG_COUNT') or 0))]
        kept = [(key, value) for key, value in entries if 'pi-autowork-push-disabled' not in key]
        if kept != entries:
            env = {k: v for k, v in env.items() if k != 'GIT_CONFIG_COUNT'
                   and not k.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_'))}
            env['GIT_CONFIG_COUNT'] = str(len(kept))
            for i, (key, value) in enumerate(kept):
                env[f'GIT_CONFIG_KEY_{i}'], env[f'GIT_CONFIG_VALUE_{i}'] = key, value
    except ValueError:
        pass
    runs = []
    for test_id, places in [item for item in locations.items() if only is None or item[0] in only][:10]:
        if not re.fullmatch(r'(?:\w+\.)+\w+', test_id) or len(places) != 1:
            continue
        directory = next(iter(places))
        if directory.is_relative_to(root) and directory.is_dir():
            runs.append((test_id, directory))

    def rerun(test_id, directory):
        """(passed, diagnostics) of one test run alone."""
        argv = [sys.executable, '-m', 'unittest', test_id]
        notes = f'RERUN {test_id} in {directory}\ncommand: {shlex.join(argv)}\n'
        try:
            # A file, not a pipe: a detached daemon inheriting stdout must not
            # make communicate() wait forever for EOF after the test times out.
            with tempfile.TemporaryFile() as capture, subprocess.Popen(
                    argv, cwd=directory, env=env,
                    stdout=capture, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                    start_new_session=True) as process:
                timed_out = False
                try:
                    process.wait(timeout=timeout)
                except subprocess.TimeoutExpired:
                    timed_out = True
                    os.killpg(process.pid, signal.SIGKILL)
                    process.wait()
                size = os.fstat(capture.fileno()).st_size
                capture.seek(0)
                output = capture.read(size).decode('utf-8', errors='replace')
        except OSError as error:
            return False, notes + f'Could not rerun {test_id}: {error}\n'
        notes += f'exit code: {process.returncode}\n'
        if timed_out:
            return False, notes + output + f'TIMEOUT: {test_id} after {timeout:g}s\n'
        return (process.returncode == 0 and bool(re.search(r'^Ran [1-9]\d* tests? in ', output, re.M))
                and bool(re.search(r'^OK$', output, re.M)) and not gate_skips(output)), notes + output

    # Side by side: one at a time, ten reruns that each hit their timeout took 20 minutes.
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(lambda run: rerun(*run), runs))
    with receipt.with_suffix('.log').open('w') as diagnostics:
        for notes in (notes for _, notes in outcomes):
            diagnostics.write(notes)
    flaky = [test_id for (test_id, _), (passed, _) in zip(runs, outcomes) if passed]
    result = dict(rev=rev, flaky=flaky, incomplete=not complete_results(text, root, cmd))
    tmp = receipt.with_suffix('.tmp')
    tmp.write_text(json.dumps(result) + '\n')
    tmp.replace(receipt)


def gate_skips(log_text):
    """Tests the host's resource gate skipped (TOOLSET-193-54): not failures, but not checked."""
    return log_text.count('RESOURCE_GATE_SKIP:')


def process_stat(pid):
    """Linux process state and start ticks; comm may itself contain spaces and ')'."""
    try:
        pid = int(pid)
        if pid <= 0:
            return None
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return fields[0], fields[19]
    except (OSError, ValueError, TypeError, IndexError):
        return None


def start_time(pid):
    stat = process_stat(pid)
    return stat[1] if stat else None


def alive(pid, started=None):
    stat = process_stat(pid)
    return bool(stat and stat[0] not in ('Z', 'X') and (started is None or stat[1] == str(started)))


def line(record, now=None):
    """'main red since 1a2b3c4: 5 failing', 'main green at 1a2b3c4', 'main check running …', or ''."""
    now = time.time() if now is None else now
    state = record.get('state')
    if state == 'red':
        return f"main red since {record.get('rev', '')[:7]}: {len(record.get('failures') or [])} failing"
    if state == 'broken':
        return f"main check broken at {record.get('rev', '')[:7]}: {record.get('crash') or 'it crashed'}"
    if state == 'recheck' and record.get('crashed'):
        return f"main check again at {record.get('crashed', '')[:7]}: it crashed before any test result"
    if state == 'recheck':
        return f"main check again at {record.get('gated', '')[:7]} when the host is quieter"
    if state == 'green':
        flaky = len(record.get('flaky') or [])
        return f"main green at {record.get('rev', '')[:7]}" + (f' ({flaky} flaky)' if flaky else '')
    if state == 'running':
        progress = record.get('check_slot') or {}
        if progress.get('state') == 'waiting':
            return f"main check waiting for a check slot, {progress.get('ahead', 0)} ahead"
        started = progress.get('started', record.get('started', now))
        return f"main check running on {record.get('rev', '')[:7]} ({int((now - started) // 60)}m)"
    return ''


if __name__ == '__main__':
    if sys.argv[1] == '--run':
        code, _ = run_command(sys.argv[2], os.getcwd(), float(sys.argv[3]), sys.argv[4], background=True)
        sys.exit(code if code >= 0 else 128 - code)
    # Main's check may differ from the repository's gate check: name it here, not by env order.
    rerun_failures(*sys.argv[1:], cmd=command(repo=sys.argv[2]))
