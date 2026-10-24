"""Run one Pi job for pi-autowork: model choice, fallback, bounded retries, records.

A straight port of the runner's Bash `pi_job`/`run_pi`/`choose_model`; the formal
worker-runtime boundary (launch/observe/stop/resume) is TOOLSET-117-cb. Behavior:

- the primary model when authenticated and not cooling down, else the fallback
  (`PI_AUTOWORK_NO_FALLBACK=1` disables it); a provider failure on the primary cools
  it for PI_AUTOWORK_COOLDOWN seconds, recorded in STATE/provider.json;
- RPC is the default: a scoped Linux guard owns an AsyncPiClient host and its Pi/tool
  descendants. JSON under GNU timeout is explicit rollout rollback only; no automatic
  transport fallback. Exit 124 is a timeout, not permission to replay uncertain input;
- a provider failure or an unsettled/aborted run is retried up to
  PI_AUTOWORK_MAX_RETRIES times, resuming the same session, with backoff;
- every run appends one redacted line to STATE/runs.jsonl; the raw stream, which
  holds prompts, code and tool output, is deleted. Cost and tokens are recorded there
  to be measured, never enforced: there is no spending limit.

    pi_runtime.py job STATE ROLE TASK DIR SESSION LIMIT MESSAGE [PI ARGS...]
        -> {"ok": bool, "text": str, "notes": [...]}
    pi_runtime.py choose STATE  -> {"chosen": model|null, "reason": str}; exit 1 if none
    pi_runtime.py ready STATE MODEL
"""
from datetime import datetime, timedelta
import json
import os
from pathlib import Path
import re
import signal
import subprocess
import sys
import tempfile
import time
import uuid

if __package__:
    from . import accounting, portal, telemetry
else:
    import accounting
    import portal
    import telemetry  # pi_runtime.py is also a standalone subprocess entry point.

PROVIDER_FAILURE = re.compile(
    r'429|rate.?limit|quota|usage limit|overloaded|5[0-9]{2}|unavailable|timed? ?out|ECONN|ENOTFOUND|EAI_AGAIN'
    r'|network|fetch failed|401|403|unauthori[sz]ed|forbidden|credential|api key|not logged in|/login|oauth'
    r'|expired|no such model|model .*not (found|available)', re.I)
SECRET = re.compile(r'(sk-[A-Za-z0-9_-]{8,}|Bearer [A-Za-z0-9._~+/=-]+'
                    r'|[A-Za-z0-9_]*(KEY|TOKEN|SECRET|PASSWORD)[A-Za-z0-9_]*=[^\s]+)')
STOP = False


def redact(text):
    return SECRET.sub('[redacted]', text or '')


class Settings:
    def __init__(self, state, env=os.environ):
        self.state = Path(state)
        self.pi = env.get('PI_BIN', 'pi')
        self.transport = env.get('PI_AUTOWORK_TRANSPORT', 'rpc')
        self.rpc_python = env.get('PI_AUTOWORK_RPC_PYTHON', '')
        self.primary = env.get('PI_AUTOWORK_PRIMARY', 'openai-codex/gpt-6.1-sol')
        self.fallback = env.get('PI_AUTOWORK_FALLBACK', 'openrouter/deepseek/deepseek-v4.1-flash')
        self.fallback_enabled = env.get('PI_AUTOWORK_NO_FALLBACK', '0') != '1'
        self.cooldown = int(env.get('PI_AUTOWORK_COOLDOWN', '1800'))
        self.backoff = int(env.get('PI_AUTOWORK_BACKOFF', '30'))
        self.max_retries = int(env.get('PI_AUTOWORK_MAX_RETRIES', '3'))
        self.skill_args = env.get('PI_AUTOWORK_SKILL_ARGS', '').split()
        self.dry_run = env.get('PI_AUTOWORK_DRY_RUN', '0') == '1'
        self.session_label = env.get('PI_AUTOWORK_SESSION', '')


def provider(model):
    return model.split('/', 1)[0]


def model_name(model):
    return model.split('/', 1)[1] if '/' in model else model


def now_iso(offset_hours=0):
    return (datetime.now().astimezone() - timedelta(hours=offset_hours)).isoformat(timespec='seconds')


# --- Models ---------------------------------------------------------------------
def auth_ready(s, model):
    argv = [s.pi, 'auth', 'check', '--provider', provider(model), '--model', model_name(model)]
    if s.dry_run:
        argv.append('--no-refresh')
    try:
        return subprocess.run(argv, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120).returncode == 0
    except (OSError, subprocess.SubprocessError):
        return False


def _provider_file(s):
    try:
        return json.loads((s.state / 'provider.json').read_text())
    except (OSError, ValueError):
        return {}


def primary_cooling(s):
    return time.time() < float(_provider_file(s).get('primary_unavailable_until') or 0)


def cool_primary(s, reason):
    path = s.state / 'provider.json'
    tmp = path.with_name(f'provider.json.{os.getpid()}')
    tmp.write_text(json.dumps({'primary_unavailable_until': int(time.time()) + s.cooldown, 'reason': reason}))
    os.replace(tmp, path)


def choose(s):
    """(model or None, fallback reason)."""
    def ready(model):
        try:
            portal.check_model(model)
        except portal.SetupError as error:
            return False, str(error)
        return auth_ready(s, model), ''

    if not s.fallback_enabled:
        usable, reason = ready(s.primary)
        if usable:
            return s.primary, ''
        return None, reason or 'primary not authenticated and the fallback is disabled'
    if not primary_cooling(s):
        usable, reason = ready(s.primary)
        if usable:
            return s.primary, ''
        reason = reason or 'primary not authenticated'
        cool_primary(s, reason)
    else:
        reason = _provider_file(s).get('reason') or 'primary cooling down'
    usable, fallback_reason = ready(s.fallback)
    return (s.fallback if usable else None), fallback_reason or reason


# --- One run --------------------------------------------------------------------
def analyse(raw):
    events = []
    for line in raw.split('\n'):
        try:
            value = json.loads(line)
        except ValueError:
            continue
        if isinstance(value, dict):
            events.append(value)
    settled = [e for e in events if e.get('type') == 'agent_settled']
    settled = settled[-1] if settled else None
    messages = [e.get('message') or {} for e in events
                if e.get('type') == 'message_end' and (e.get('message') or {}).get('role') == 'assistant']
    last = messages[-1] if messages else {}
    gaveup = [e for e in events if e.get('type') == 'auto_retry_end' and e.get('success') is False]
    gaveup = gaveup[-1] if gaveup else {}

    usage = [m.get('usage') or {} for m in messages]

    def token_sum(field):
        values = [accounting.number(u.get(field)) for u in usage]
        return sum(values) if values and all(v is not None for v in values) else None

    # Pi's ordinary usage.cost is calculated from catalog rates. It is not a bill.
    # Only an explicitly provenance-labelled provider amount is measurable; an
    # adapter that does not supply that provenance leaves spend unknown.
    costs = [accounting.number((u.get('cost') or {}).get('total'))
             if u.get('cost_source') == 'provider_reported' and u.get('billing') != 'subscription'
             else None for u in usage]
    measured = sum(c for c in costs if c is not None)
    complete = bool(costs) and all(c is not None for c in costs)
    return dict(settled=settled is not None, aborted=bool((settled or {}).get('aborted')),
                stop=last.get('stopReason'), error=last.get('errorMessage') or gaveup.get('finalError'),
                retries=sum(e.get('type') == 'auto_retry_start' for e in events),
                tokens=token_sum('totalTokens'), input_tokens=token_sum('input'), output_tokens=token_sum('output'),
                cost=measured if complete else None, measured_cost_usd=measured,
                cost_source='provider_reported' if any(c is not None for c in costs) else 'missing',
                billing=('subscription' if usage and all(u.get('billing') == 'subscription' for u in usage)
                         else 'mixed' if any(u.get('billing') == 'subscription' for u in usage) else None),
                text='\n'.join(c.get('text', '') for c in (last.get('content') or [])
                               if isinstance(c, dict) and c.get('type') == 'text'))


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


def run_pi(s, directory, message, session, target, limit, extra, role=None, task=''):
    if s.transport == 'json':
        result = run_json(s, directory, message, session, target, limit, extra, role)
        result['transport'] = 'json'
        return result
    if s.transport != 'rpc':
        return dict(analyse(''), rc=1, seconds=0, error='invalid PI_AUTOWORK_TRANSPORT',
                    failure_kind='toolchain', retry_safe=False, transport=s.transport)
    if __package__:
        from . import pi_rpc
    else:
        sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
        from pi_autowork import pi_rpc
    return pi_rpc.run(s, directory, message, session, target, limit, extra, role, task)


def run_json(s, directory, message, session, target, limit, extra, role=None):
    runs = s.state / 'runs'
    runs.mkdir(parents=True, exist_ok=True)
    fd, raw = tempfile.mkstemp(prefix='run.', dir=runs)
    os.close(fd)
    err = raw + '.err'
    start = time.monotonic()
    argv = ['timeout', '--foreground', '-s', 'INT', '-k', '120', str(limit),
            s.pi, '--mode', 'json', '--provider', provider(target), '--model', model_name(target),
            '--session-dir', str(s.state / 'sessions'), '--session-id', session, '--no-approve',
            *s.skill_args, *extra, '--', message]
    try:
        with open(raw, 'wb') as out, open(err, 'wb') as errors:
            # Same process group as the caller: a stop sent to the group reaches Pi too.
            child = subprocess.Popen(argv, cwd=directory, stdin=subprocess.DEVNULL, stdout=out, stderr=errors)
            watch, stopping = command_limit(role, limit), {}
            while True:
                try:
                    rc = child.wait(timeout=5 if watch else None)
                    break
                except subprocess.TimeoutExpired:
                    for minutes, line in stop_stuck_commands(child.pid, watch, stopping):
                        print(f'pi-autowork: stopped a command that ran {minutes} min (limit '
                              f'{int(watch // 60)} min): {line}', file=sys.stderr, flush=True)
        run = analyse(Path(raw).read_text(errors='replace'))
        run.update(rc=rc, seconds=int(time.monotonic() - start))
        run['error'] = redact(str(run['error'] or ''))[:300]
        if not run['error'] and rc != 0:
            tail = Path(err).read_text(errors='replace').splitlines()[-5:]
            run['error'] = redact(' '.join(tail) + (' ' if tail else ''))[:300]
        return run
    finally:
        # Keep only the compact record; the raw stream holds prompts, code and tool output.
        for path in (raw, err):
            try:
                os.unlink(path)
            except OSError:
                pass


def provider_failure(run):
    return run['stop'] == 'error' or (not run['settled'] and bool(PROVIDER_FAILURE.search(run['error'] or '')))


def record(s, role, task, outcome, model, fallback, run, result='', *, directory=None):
    result = redact(result)[:300]
    attempt_id = None
    if directory is not None:
        try:
            engine = telemetry.engine()
            slot = engine.execution.read(engine.slot_path(engine.common_dir(directory), task)) or {}
            attempt_id = slot.get('attempt_id')
        except (OSError, ValueError, subprocess.SubprocessError):
            pass
    row = {'run_id': uuid.uuid4().hex, 'time': now_iso(), 'role': role,
           'task': accounting.attributed_task(role, task),
           'host': os.environ.get('AUTOWORK_TELEMETRY_HOST') or 'pi', 'attempt_id': attempt_id,
           'outcome': outcome, 'provider': provider(model),
           'model': model_name(model), 'seconds': run.get('seconds', 0), 'session': s.session_label,
           'pi_retries': run.get('retries', 0), 'fallback_reason': fallback or None,
           'tokens': run.get('tokens'), 'input_tokens': run.get('input_tokens'),
           'output_tokens': run.get('output_tokens'), 'cost_usd': run.get('cost'),
           'measured_cost_usd': run.get('measured_cost_usd', 0),
           'cost_source': run.get('cost_source', 'missing'), 'billing': run.get('billing'),
           'error': run.get('error') or None, 'result': result or None,
           **{key: run.get(key) for key in ('transport', 'sdk_version', 'pi_version', 'session_id',
                                          'generation', 'prompt_digest', 'failure_kind', 'cleanup_complete',
                                          'startup_seconds', 'first_tool_seconds', 'tool_seconds',
                                          'compactions', 'command_interruptions', 'usage_coverage', 'known_usage')}}
    try:
        accounting.append(s.state / 'runs.jsonl', row)
    except OSError as exc:
        print(f'pi-autowork: could not record usage: {exc}', file=sys.stderr)
    if directory is not None:
        telemetry.model_run(directory, role, task, model, outcome, run)


# --- One job --------------------------------------------------------------------
def job(s, role, task, directory, message, session, limit, extra):
    attempt, note, notes = 0, '', []
    while True:
        chosen, reason = choose(s)
        if chosen is None:
            record(s, role, task, 'no_model', s.primary, reason, {'error': reason or 'no model ready'},
                   directory=directory)
            return dict(ok=False, text='', notes=notes, why='no_model')
        telemetry.model_run(directory, role, task, chosen, 'selected')
        run = run_pi(s, directory, message + note, session, chosen, limit, extra, role=role, task=task)
        kind = run.get('failure_kind')
        # Cleanup uncertainty must survive STOP/timeout classification: callers
        # must not dispose of scratch while owned descendants may remain.
        if kind == 'cleanup_unproven' or (kind and not run.get('retry_safe', False)):
            record(s, role, task, kind, chosen, reason, run, directory=directory)
            return dict(ok=False, text='', notes=notes, why=kind)
        if STOP:
            record(s, role, task, 'interrupted', chosen, reason, run, directory=directory)
            return dict(ok=False, text='', notes=notes, why='interrupted')
        if run['rc'] == 124:
            record(s, role, task, 'timeout', chosen, reason, run, directory=directory)
            return dict(ok=False, text='', notes=notes, why='timeout')
        if run['rc'] != 0 or provider_failure(run) or not run['settled'] or run['aborted']:
            kind = 'provider' if provider_failure(run) else 'crash'
            attempt += 1
            record(s, role, task, kind + '_failure', chosen, reason, run, directory=directory)
            if attempt > s.max_retries:
                return dict(ok=False, text='', notes=notes, why=kind + '_failure')
            if kind == 'provider' and chosen == s.primary and s.fallback_enabled:
                cool_primary(s, run['error'] or 'provider failure')
            else:
                time.sleep(min(s.backoff * (1 << (attempt - 1)), 600))
            note = (' A previous attempt in this session was interrupted by a model or provider failure: '
                    'first reconcile its partial work, then continue.')
            continue
        result = next((line for line in run['text'].splitlines()
                       if re.match(r'^PI_AUTOWORK_(RESULT|VERIFY):', line)), '')
        record(s, role, task, 'finished', chosen, reason, run, result, directory=directory)
        return dict(ok=True, text=run['text'], notes=notes)


def _stop(*_):
    global STOP
    STOP = True  # the group signal also reaches Pi; wait for it to exit, then record


def main(argv):
    if len(argv) >= 8 and argv[0] == 'job':
        signal.signal(signal.SIGINT, _stop)
        signal.signal(signal.SIGTERM, _stop)
        state, role, task, directory, session, limit, message, *extra = argv[1:]
        print(json.dumps(job(Settings(state), role, task, directory, message, session, limit, extra)))
        return 0
    if len(argv) == 3 and argv[0] == 'ready':
        return 0 if auth_ready(Settings(argv[1]), argv[2]) else 1
    if len(argv) == 2 and argv[0] == 'choose':
        chosen, reason = choose(Settings(argv[1]))
        print(json.dumps({'chosen': chosen, 'reason': reason}))
        return 0 if chosen else 1
    print('usage: pi_runtime.py job STATE ROLE TASK DIR SESSION LIMIT MESSAGE [PI ARGS...] | choose STATE',
          file=sys.stderr)
    return 2


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        sys.exit(main(sys.argv[1:]))
    finally:
        sys.argv = previous
