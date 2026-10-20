"""Run one Pi job for pi-autowork: model choice, fallback, bounded retries, records.

A straight port of the runner's Bash `pi_job`/`run_pi`/`choose_model`; the formal
worker-runtime boundary (launch/observe/stop/resume) is TOOLSET-117-cb. Behavior:

- the primary model when authenticated and not cooling down, else the fallback
  (`PI_AUTOWORK_NO_FALLBACK=1` disables it); a provider failure on the primary cools
  it for PI_AUTOWORK_COOLDOWN seconds, recorded in STATE/provider.json;
- Pi runs under `timeout --foreground -s INT -k 120 LIMIT` in the caller's process
  group, so a stop reaching the group reaches Pi and its tools; exit 124 is a timeout;
- a provider failure or an unsettled/aborted run is retried up to
  PI_AUTOWORK_MAX_RETRIES times, resuming the same session, with backoff;
- every run appends one redacted line to STATE/runs.jsonl; the raw stream, which
  holds prompts, code and tool output, is deleted;
- no run starts once PI_AUTOWORK_MAX_COST is reached within PI_AUTOWORK_COST_WINDOW.

    pi_runtime.py job STATE ROLE TASK DIR SESSION LIMIT MESSAGE [PI ARGS...]
        -> {"ok": bool, "text": str, "notes": [...]}
    pi_runtime.py choose STATE  -> {"chosen": model|null, "reason": str}; exit 1 if none
    pi_runtime.py ready STATE MODEL | spent STATE | over-budget STATE
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
        self.primary = env.get('PI_AUTOWORK_PRIMARY', 'openai-codex/gpt-6.1-sol')
        self.fallback = env.get('PI_AUTOWORK_FALLBACK', 'openrouter/deepseek/deepseek-v4.1-flash')
        self.fallback_enabled = env.get('PI_AUTOWORK_NO_FALLBACK', '0') != '1'
        self.cooldown = int(env.get('PI_AUTOWORK_COOLDOWN', '1800'))
        self.backoff = int(env.get('PI_AUTOWORK_BACKOFF', '30'))
        self.max_retries = int(env.get('PI_AUTOWORK_MAX_RETRIES', '3'))
        self.max_cost = env.get('PI_AUTOWORK_MAX_COST', '0')
        self.window_text = env.get('PI_AUTOWORK_COST_WINDOW', '24')
        self.window = float(self.window_text)
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
    if not s.fallback_enabled:
        if auth_ready(s, s.primary):
            return s.primary, ''
        return None, 'primary not authenticated and the fallback is disabled'
    if not primary_cooling(s):
        if auth_ready(s, s.primary):
            return s.primary, ''
        reason = 'primary not authenticated'
        cool_primary(s, reason)
    else:
        reason = _provider_file(s).get('reason') or 'primary cooling down'
    return (s.fallback if auth_ready(s, s.fallback) else None), reason


# --- Budget ---------------------------------------------------------------------
def spent(s):
    since = now_iso(s.window)
    total = 0.0
    try:
        lines = (s.state / 'runs.jsonl').read_text().splitlines()
    except OSError:
        return 0
    for line in lines:
        try:
            row = json.loads(line)
        except ValueError:
            continue
        if isinstance(row, dict) and str(row.get('time', '')) >= since:
            total += float(row.get('cost_usd') or 0)
    return int(total) if total == int(total) else total


def over_budget(s):
    try:
        limit = float(s.max_cost)
    except ValueError:
        return False
    return limit != 0 and spent(s) >= limit


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

    def number(value):
        return value if isinstance(value, (int, float)) else 0
    return dict(settled=settled is not None, aborted=bool((settled or {}).get('aborted')),
                stop=last.get('stopReason'), error=last.get('errorMessage') or gaveup.get('finalError'),
                retries=sum(e.get('type') == 'auto_retry_start' for e in events),
                tokens=sum(number((m.get('usage') or {}).get('totalTokens')) for m in messages),
                cost=sum(number(((m.get('usage') or {}).get('cost') or {}).get('total')) for m in messages),
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


def stop_stuck_commands(runner_pid, limit, stopping, now=None):
    """A tool command Pi started that has run longer than ``limit`` gets SIGTERM, then SIGKILL
    30 s later, with everything it started (TOOLSET-215-a8: one browser test hung for 89 of a
    worker's 90 minutes). Pi reports the failed call, so the worker continues the same attempt.
    ``stopping`` maps pids already signalled to when; returns the commands stopped now."""
    now = time.monotonic() if now is None else now
    stopped = []
    for pi in _children(runner_pid):  # `timeout` runs Pi as its child
        for command in _children(pi):
            line = _command(command)
            if command in stopping:
                if now - stopping[command] >= 30:
                    for pid in _tree(command):
                        try:
                            os.kill(pid, signal.SIGKILL)
                        except OSError:
                            pass
                continue
            age = _age(command)
            if age is None or age < limit or DAEMONS.search(line):
                continue
            for pid in reversed(_tree(command)):
                try:
                    os.kill(pid, signal.SIGTERM)
                except OSError:
                    pass
            stopping[command] = now
            stopped.append((int(age // 60), line[:120]))
    return stopped


def run_pi(s, directory, message, session, target, limit, extra, role=None):
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


def record(s, role, task, outcome, model, fallback, run, result=''):
    result = redact(result)[:300]
    row = {'time': now_iso(), 'role': role, 'task': task, 'outcome': outcome, 'provider': provider(model),
           'model': model_name(model), 'seconds': run.get('seconds', 0), 'session': s.session_label,
           'pi_retries': run.get('retries', 0), 'fallback_reason': fallback or None,
           'tokens': run.get('tokens', 0), 'cost_usd': run.get('cost', 0),
           'error': run.get('error') or None, 'result': result or None}
    with open(s.state / 'runs.jsonl', 'a') as stream:  # one short append per run
        stream.write(json.dumps(row) + '\n')


# --- One job --------------------------------------------------------------------
def job(s, role, task, directory, message, session, limit, extra):
    attempt, note, notes = 0, '', []
    while True:
        if over_budget(s):
            notes.append(f'{role} {task}: budget reached (${spent(s)} of ${s.max_cost} in '
                         f'{s.window_text} h); not starting Pi')
            return dict(ok=False, text='', notes=notes, why='budget')
        chosen, reason = choose(s)
        if chosen is None:
            record(s, role, task, 'no_model', s.primary, reason, {'error': reason or 'no model ready'})
            return dict(ok=False, text='', notes=notes, why='no_model')
        run = run_pi(s, directory, message + note, session, chosen, limit, extra, role=role)
        if STOP:
            record(s, role, task, 'interrupted', chosen, reason, run)
            return dict(ok=False, text='', notes=notes, why='interrupted')
        if run['rc'] == 124:
            record(s, role, task, 'timeout', chosen, reason, run)
            return dict(ok=False, text='', notes=notes, why='timeout')
        if provider_failure(run) or not run['settled'] or run['aborted']:
            kind = 'provider' if provider_failure(run) else 'crash'
            attempt += 1
            record(s, role, task, kind + '_failure', chosen, reason, run)
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
        record(s, role, task, 'finished', chosen, reason, run, result)
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
    if len(argv) == 2 and argv[0] == 'spent':
        print(spent(Settings(argv[1])))
        return 0
    if len(argv) == 2 and argv[0] == 'over-budget':
        return 0 if over_budget(Settings(argv[1])) else 1
    if len(argv) == 2 and argv[0] == 'choose':
        chosen, reason = choose(Settings(argv[1]))
        print(json.dumps({'chosen': chosen, 'reason': reason}))
        return 0 if chosen else 1
    print('usage: pi_runtime.py job STATE ROLE TASK DIR SESSION LIMIT MESSAGE [PI ARGS...] | choose STATE',
          file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
