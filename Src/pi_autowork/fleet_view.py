"""The fleet as the `autowork` command and its TUI see it. Standard library only.

Every runner on this machine (a `pi-autowork@` systemd service), with its health from the
runner's own status.json (``health.fleet``), its blockers grouped by kind, recent
log lines, and the exact command behind every action. Nothing here calls a model,
and nothing here changes a runner: actions only build the argv that `autowork` or
`pi-autowork.sh` already accept.
"""
from dataclasses import dataclass, field, replace
import datetime
import json
import hashlib
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from pi_autowork import health, main_check, portal, questions as owner_questions, task_prepare, task_snapshot, task_status
from pi_autowork.common import safe_name

KINDS = {'runner': 'runner', 'cycle': 'dependency cycle', 'held': 'blocker', 'contract': 'not runnable',
         'claim': 'claimed elsewhere', 'outside': 'outside Now/Next'}
CAUSES = task_status.CAUSES
ORDER = ['runner', 'cycle', 'held', 'contract', 'claim', 'outside']
COLORS = {'working': 'green', 'idle': 'green', 'blocked': 'yellow', 'paused': 'yellow', 'starting': 'yellow',
          'restarting': 'cyan', health.HOST_WAIT: 'yellow'}
# systemd sub-states of a unit that is stopping or starting again, not stopped.
RESTARTING = ('stop', 'stop-sigterm', 'stop-sigkill', 'stop-post', 'final-sigterm', 'auto-restart', 'start-pre',
              'start-post', 'activating', 'deactivating')
RESTART_WINDOW = 180    # seconds a `restarting on it` line keeps a stopped service `restarting`
GATE_WINDOW = 300
DEFAULT_MODEL = 'openai-codex/gpt-6.1-sol'           # pi_runtime's defaults
DEFAULT_FALLBACK = 'openrouter/deepseek/deepseek-v4.1-flash'
MODEL_KEYS = {'model': 'PI_AUTOWORK_PRIMARY', 'fallback': 'PI_AUTOWORK_FALLBACK'}
SETUP_LABELS = {
    'none': 'Setup required — run /docs_sync',
    'uncommitted': 'Setup required — run /docs_sync',
    'no_repository': 'Setup required — run /docs_sync',
    'legacy': 'Migration required — Force converts legacy planning',
    'invalid': 'Task store needs repair',
    'conversion_pending': 'Task store needs repair',
}


def read_env(path, *, errors=None):
    """KEY=value lines of a service settings file."""
    try:
        lines = Path(path).read_text().splitlines()
    except (OSError, UnicodeError) as exc:
        if errors is not None:
            errors.append(f'environment {path}: {exc}')
        return {}
    return dict(line.split('=', 1) for line in lines if '=' in line and not line.lstrip().startswith('#'))


def write_env(path, updates):
    """Set (or, with None, remove) keys in a settings file, keeping every other line and 0600."""
    path = Path(path)
    lines = path.read_text().splitlines() if path.exists() else []
    done = set()
    out = []
    for line in lines:
        key = line.split('=', 1)[0] if '=' in line else None
        if key in updates:
            done.add(key)
            if updates[key] is not None:
                out.append(f'{key}={updates[key]}')
            continue
        out.append(line)
    out += [f'{k}={v}' for k, v in updates.items() if k not in done and v is not None]
    old = os.umask(0o077)
    try:
        tmp = path.with_suffix('.env.tmp')
        tmp.write_text('\n'.join(out) + '\n')
        os.replace(tmp, path)
    finally:
        os.umask(old)


def models(pi='pi', search=None, timeout=60, *, agent_dir=None):
    """provider/model IDs from `pi --list-models` (Pi's own catalog)."""
    argv = [pi, '--list-models'] + ([search] if search else [])
    found = []
    table = False
    env = dict(os.environ, PI_CODING_AGENT_DIR=agent_dir) if agent_dir else None
    for line in _lines(argv, timeout=timeout, env=env):
        parts = line.split()
        if [p.lower() for p in parts[:2]] == ['provider', 'model']:
            table = True
            continue
        if (table and len(parts) >= 3 and re.fullmatch(r'[A-Za-z0-9._-]+', parts[0])
                and re.fullmatch(r'[0-9][0-9.,]*[kKmM]?', parts[2])):
            found.append(f'{parts[0]}/{parts[1]}')
    if not found:
        raise portal.SetupError('Pi listed no usable models; check Pi installation/logins. For Nous Portal, '
                                'use autowork setup-portal --provider NAME --model ID (proposal only).')
    return found


@dataclass
class Runner:
    name: str
    repo: str = ''
    mode: str = ''            # 'service', or '' when only state is left
    service: str = ''         # systemd sub-state, '' when there is no unit
    state: str = 'unknown'
    minutes: int | None = None
    running: int | None = 0
    waiting: int | None = 0
    stopped: int | None = 0  # waiting tasks that cannot move until something is resolved: Blockers
    stopped_groups: list = field(default_factory=list)  # [{label, count, tasks}] by what stops them
    held: list = field(default_factory=list)
    roots: list = field(default_factory=list)
    state_dir: str = ''       # this runner's pi-autowork state directory
    lanes: list = field(default_factory=list)
    enabled: bool = False     # its service starts at login; paused also needs `autowork pause`'s marker
    model: str = ''
    fallback: str = ''
    push: bool = False       # saved service grant; only PI_AUTOWORK_PUSH=1 enables publication
    questions: list = field(default_factory=list)  # the owner's open questions in BLOCKERS.md
    decisions: int = 0  # open tasks in Needs decision: never dispatched, so not in the engine's status
    toolset: str = ''         # PI_AUTOWORK_TOOLSET: the service runs this checkout, not the Pi package
    waiting_groups: list = field(default_factory=list)  # why tasks wait, grouped (status.json)
    blocker: str = ''         # what keeps the runner itself from dispatching (status.json)
    stop_reason: str = ''     # saved startup refusal, even when generic setup checks also fail
    max_workers: int | None = None
    restarting: str = ''      # 'onto <commit>' or 'service' while it stops and starts again
    gate: str = ''            # the latest resource-gate reason, when the last cycle was gated
    maintainer: dict = field(default_factory=dict)  # the DOCS-MAINTAINER's last run (TOOLSET-164-f1)
    main_check: dict = field(default_factory=dict)  # main's full offline check (TOOLSET-176-98)
    job: dict | None = None   # the runner's own Pi job running now (TOOLSET-177-d0)

    prepare_state: str | None = None  # one read-only preparation probe per fleet refresh

    # Display-only fleet observation. Explicit fields, so dataclasses.replace() keeps the
    # provenance the TUI depends on; command.runner_json excludes them from the CLI contract.
    snapshot: task_snapshot.TaskSnapshot | None = field(default=None, repr=False, compare=False)
    preparation: 'Preparation | None' = field(default=None, repr=False, compare=False)
    question_provenance: dict = field(default_factory=dict, repr=False, compare=False)
    acquisition_errors: list = field(default_factory=list, repr=False, compare=False)

    display_deleted: tuple = field(default=(), repr=False, compare=False)
    display_recreated: tuple = field(default=(), repr=False, compare=False)

    @property
    def color(self):
        return COLORS.get(self.state, 'red')

    @property
    def has_service(self):
        return bool(self.service)

    @property
    def setup_label(self):
        """Use Docs Sync's read-only preparation states, not just the tasks/ directory."""
        if not self.repo or not Path(self.repo).is_dir():
            return ''
        state = self.prepare_state
        if state is None:
            state = task_prepare.prepare(self.repo, mode='check').get('state')
        return SETUP_LABELS.get(state, '')

    @property
    def setup_required(self):
        return bool(self.setup_label)


IN_FLIGHT, PHASES = task_status.IN_FLIGHT, task_status.PHASES


@dataclass
class Lane:
    """One task in flight: what its worker or the runner is doing with it now."""
    task: str
    phase: str
    detail: str = ''
    attempt: int = 1
    minutes: int | None = None     # since the attempt started
    activity: str = ''             # the worker's last action: a tool call or what it said
    activity_age: int | None = None  # seconds since that action


def _tail(path, size=65536):
    try:
        with open(path, 'rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - size))
            return stream.read().decode(errors='replace').splitlines()
    except OSError:
        return []


def _phases(state_dir):
    """{task: (phase, detail)} from the runner's own log, its latest line per task."""
    found = {}
    for line in _tail(Path(state_dir) / 'runner.log'):
        match = re.match(r'^\S+ ([A-Za-z0-9][A-Za-z0-9._-]*): (.*)$', line)
        if match:
            try:
                stamp = datetime.datetime.fromisoformat(line.split()[0].replace('Z', '+00:00')).timestamp()
            except ValueError:
                stamp = 0
            found[match.group(1)] = (*_split_phase(match.group(2)), stamp)
    return found


PHASE_WORDS = ('waiting for a check slot', 'waiting to integrate', 'set aside', 'verifying', 'landing', 'implemented', 'integrating', 'integrated',
               'running', 'pending', 'paused', 'done', 'failed', 'held', 'closed')


def _split_phase(text):
    """'waiting to integrate until ... (pid ...)' -> ('waiting to integrate', 'until ... (pid ...)')."""
    text = ' '.join(text.split())
    head, _, rest = text.partition(' — ')
    for word in PHASE_WORDS:
        if head == word or head.startswith(word + ' ') or head.startswith(word + ':') or head.startswith(word + ';'):
            detail = head[len(word):].lstrip(' :;')
            return word, '; '.join(x for x in (detail, rest) if x)
    words = head.split()
    return ' '.join(words[:3]), '; '.join(x for x in (' '.join(words[3:]), rest) if x)


def _actions(state_dir, task, now, size=262144):
    """The task's Pi session actions, newest first: (text, seconds ago, epoch time), from the last
    ``size`` bytes of its transcript."""
    sessions = Path(state_dir) / 'sessions'
    try:
        files = [f for f in sessions.iterdir()
                 if re.search(rf'_pi-autowork-(verify-)?{re.escape(task)}-', f.name)]
    except OSError:
        return
    if not files:
        return
    for line in reversed(_tail(max(files, key=lambda f: f.stat().st_mtime), size)):
        try:
            event = json.loads(line)
        except ValueError:
            continue
        message = event.get('message') or {}
        if message.get('role') != 'assistant':
            continue
        text = ''
        for part in message.get('content') or []:
            if part.get('type') == 'toolCall':
                args = part.get('arguments')
                if isinstance(args, str):
                    try:
                        args = json.loads(args)
                    except ValueError:
                        args = {'command': args}
                first = str((args or {}).get('command') or (args or {}).get('path') or '').strip().splitlines()
                text = f"{part.get('name', 'tool')}: {first[0] if first else ''}".strip()
            elif part.get('type') == 'text' and part.get('text', '').strip() and not text:
                text = 'said: ' + ' '.join(part['text'].split())
        if not text:
            continue
        age = at = None
        try:
            from datetime import datetime
            at = datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).timestamp()
            age = int(now - at)
        except (KeyError, ValueError, TypeError):
            pass
        yield text, age, at


def _activity(state_dir, task, now):
    """The last thing the task's Pi session did: (text, seconds ago)."""
    # This is a display projection, never an attempt/closure authority. Read two
    # bounded per-task files, not an unbounded scan of retained session histories.
    from pi_autowork.pi_rpc import runtime_path
    from pi_autowork.processes import running
    for role in ('worker', 'verify'):
        try:
            with runtime_path(state_dir, role + ':' + task, 'active.json').open() as stream:
                progress = json.loads(stream.read(8192))
            if (progress.get('task') != task or progress.get('role') != role
                    or progress.get('transport') != 'rpc' or not progress.get('active')
                    or not -2 <= now - float(progress['updated_at']) <= 10 or not running(progress)):
                continue
            phase = re.sub(r'[^a-z_ -]', '', str(progress.get('phase') or 'starting'))[:40]
            tool = re.sub(r'[^A-Za-z0-9_.:-]', '?', str(progress.get('current_tool') or ''))[:40]
            at = progress.get('last_event_at')
            age = max(0, int(time.monotonic() - float(at))) if at is not None else None
            return f'RPC · {phase}' + (f' · {tool}' if tool else ''), age
        except (OSError, ValueError, TypeError, KeyError):
            pass
    for text, age, _ in _actions(state_dir, task, now):
        return short(text, 90), age
    return '', None


def recent_actions(runner, task, n=10, now=None):
    """The task's last ``n`` actions, oldest first as in a log, in plain words: [(text, seconds ago)]."""
    return [(text, age) for text, age, _ in action_log(runner, task, n, now)]


def action_log(runner, task, n=500, now=None, size=2097152):
    """The task's last ``n`` actions, oldest first: [(text, seconds ago, epoch time)], read from the
    last ``size`` bytes of its transcript (a long attempt's transcript runs to megabytes)."""
    now = time.time() if now is None else now
    out = []
    for text, age, at in _actions(runner.state_dir, task, now, size) if runner.state_dir else ():
        out.append((doing_text(text), age, at))
        if len(out) >= n:
            break
    # The runner's own stages in between, which no transcript records: its full check on the
    # merged tree, the reruns and the base comparison ran for 15 minutes behind a quiet view.
    merged = out[::-1] + gate_stages(runner, task, now)
    merged.sort(key=lambda item: item[2] if item[2] is not None else float('-inf'))
    return merged[-n:]


def gate_stages(runner, task, now=None):
    """The review gate's recorded stages for ``task`` (worker.gate_events): [(text, seconds ago, at)]."""
    now = time.time() if now is None else now
    if not runner.state_dir:
        return []
    path = Path(runner.state_dir) / 'full-check' / f'{safe_name(task)}.gate.jsonl'
    stages = []
    for line in _tail(path, 65536):
        try:
            event = json.loads(line)
            at = float(event['at'])
            stages.append((f'runner: {event["text"]}', int(now - at), at))
        except (ValueError, KeyError, TypeError):
            continue
    return stages


TESTS = re.compile(r'\b(unittest|pytest|check\.py|go test|cargo test|npm (run )?test|flutter test|dart test|'
                   r'vitest|jest|tox|make test|test_\w+\.py)\b')


def doing_text(activity):
    """A tool call as a person says it: 'bash: python3 -m unittest x' -> 'running tests: unittest x'."""
    tool, _, arg = str(activity).partition(': ')
    arg = ' '.join(arg.split())
    if tool == 'said':
        return 'said: ' + arg
    if tool in ('edit', 'write'):
        return 'editing ' + arg
    if tool == 'read':
        return 'reading ' + arg
    if tool in ('grep', 'find', 'ls', 'glob'):
        return 'searching ' + arg if arg else 'searching'
    if tool.startswith('subagent'):
        return 'waiting on a sub-agent' if 'wait' in tool else 'starting a sub-agent'
    if tool == 'bash':
        words = re.sub(r'^(cd \S+ && |env (\w+=\S+ )+|timeout \d+ |TMPDIR=\S+ )+', '', arg)
        if TESTS.search(words):
            return 'running tests: ' + words
        if re.match(r'(git|gh) ', words):
            return words
        if re.search(r'\b(staticcheck|go vet|ruff|flake8|mypy|eslint|pyright|shellcheck|dart analyze|flutter analyze|'
                     r'cargo clippy|git diff --check)\b', words):
            return 'checking: ' + words
        if re.match(r'(rg|grep|find|ls|sed -n|cat|head|tail) ', words):
            return 'reading: ' + words
        if re.search(r'\b(build|compile|tsc|gradle|flutter build|cargo build|go build|npm (ci|install))\b', words):
            return 'building: ' + words
        return 'running: ' + words
    return f'{tool}: {arg}'.strip(': ')


FAILED_WORDS = re.compile(r'\b(fail(ed|s|ure)?|blocked|error|refused|held)\b', re.I)
PASSED_WORDS = re.compile(r'\b(pass(ed|es)?|completed|green|ok)\b', re.I)
ACTION_KINDS = (('editing ', 'cyan'), ('running tests', 'yellow'), ('building', 'blue'), ('running:', 'blue'),
                ('reading', 'dim'), ('searching', 'dim'), ('checking', 'dim'), ('git ', 'blue'), ('gh ', 'blue'),
                ('starting a sub-agent', 'magenta'), ('waiting on a sub-agent', 'magenta'),
                ('landing', 'green'), ('integrat', 'green'), ('batch check', 'yellow'),
                ('waiting for a check slot', 'dim'), ('waiting to integrate', 'dim'))


def action_style(text):
    """The Rich style a TUI gives an action line (doing_text, doing), by its kind: verdicts bold,
    green when they pass and red when they fail; edits cyan; tests yellow; reads dim; commands
    blue; sub-agents magenta (TOOLSET-343-9356fe48)."""
    text = ' '.join(str(text).split())
    inner = text.removeprefix('reviewer: ')
    kind = next((style for prefix, style in ACTION_KINDS if inner.startswith(prefix)), None)
    # What a worker said, or a reviewer's words that are no tool call: a verdict.
    if inner.startswith('said: ') or (text.startswith('reviewer: ') and kind is None):
        if FAILED_WORDS.search(inner):
            return 'bold red'
        return 'bold green' if PASSED_WORDS.search(inner) else 'bold'
    return kind or ''


def state_style(row):
    """A task row's state color: working green, waiting yellow, held or failed red, an owner
    decision (Needs decision) magenta, done dim."""
    words = f'{getattr(row, "state", "")} {getattr(row, "why", "")}'.lower()
    if getattr(row, 'kind', '') == 'held' or 'failed' in words:
        return 'bold red'
    if getattr(row, 'section', '') == 'Needs decision':
        return 'bold magenta'
    if getattr(row, 'kind', '') == 'working':
        return 'bold green'
    if getattr(row, 'kind', '') == 'waiting':
        return 'bold yellow'
    return 'dim' if str(getattr(row, 'state', '')).startswith('done') else ''


def fit_line(text, width):
    """``text`` on one line of ``width`` columns, cut with an ellipsis when longer."""
    text = ' '.join(str(text).split())
    return text if width <= 0 or len(text) <= width else text[:max(1, width - 1)].rstrip() + '…'


QUIET_AFTER = 300


def doing(lane):
    """What a worker is doing now, in plain words."""
    if lane.phase == 'waiting for a check slot':
        return 'waiting for a check slot, ' + (lane.detail or '0 ahead')
    if lane.phase == 'waiting to integrate':
        return 'waiting to integrate: ' + (lane.detail or 'another integration first')
    if lane.phase == 'batch check':
        return 'batch check: ' + (lane.detail or 'one full check for the batch')
    if lane.phase in ('integrating', 'integrated'):
        return lane.phase
    text = doing_text(lane.activity) if lane.activity else ''
    if lane.phase == 'verifying':
        return 'reviewer: ' + (text or 'starting')
    if lane.phase == 'landing':
        return 'landing: ' + (lane.detail or 'passed in its batch')
    return text or ('starting' if lane.phase in ('starting', 'running', 'implementing') else lane.phase)


def lane_status(runner, lane):
    """An execution annotation must never masquerade as verified inventory status."""
    if runner.snapshot is not None:
        row = next((r for r in inventory_rows(runner) if r.task == lane.task), None)
        if row is not None and (lane.task, lane.attempt, lane.phase) in runner.snapshot.joined_lanes:
            return row.state, state_style(row)
        return 'Annotation · ' + lane.phase + ' (unmatched execution)', 'dim'
    return ' · '.join(status(lane)), ''


def quiet(lane):
    """'quiet 12m' when the worker's last action is QUIET_AFTER seconds or older, else ''."""
    if (lane.activity_age is None or lane.activity_age < QUIET_AFTER
            or lane.phase in ('waiting to integrate', 'waiting for a check slot', 'batch check')):
        return ''
    return 'quiet ' + duration(lane.activity_age // 60)


LOG_STAMP = re.compile(r'^(\d{4}-\d\d-\d\dT\d\d:\d\d:\d\d[+-]\d\d:\d\d) (.*)$')


def recent_events(runner, now=None):
    """(restarting, gate) from the runner's own log: 'onto <commit>' when it said it restarts
    onto an update within RESTART_WINDOW and has not started since; the last resource-gate
    reason when the latest dispatch line, within GATE_WINDOW, was gated."""
    now = time.time() if now is None else now
    if not runner.state_dir:
        return '', ''
    from datetime import datetime
    restarting, gate = '', ''
    for line in _tail(Path(runner.state_dir) / 'runner.log', 32768):
        match = LOG_STAMP.match(line)
        if not match:
            continue
        try:
            age = now - datetime.fromisoformat(match.group(1)).timestamp()
        except ValueError:
            continue
        text = match.group(2)
        update = re.match(r'Toolset updated to (\S+?);? restarting on it', text)
        if update:
            restarting = ('onto ' + update.group(1)) if age < RESTART_WINDOW else ''
        elif text.startswith('Started (PID '):
            restarting = ''
        if text.startswith(('No task can start now', 'Waiting: ')):
            found = re.search(r'resource gate: ([^;]+)', text)
            gate = found.group(1).strip() if found and age < GATE_WINDOW else ''
    return restarting, gate


JOB_WORDS = {'maintainer': 'DOCS-MAINTAINER repairing task docs', 'provision': 'installing what the review of {task} needs',
             'merge': 'resolving a merge', 'touches': 'planning the file scope of {task}'}


def job_text(job):
    """'DOCS-MAINTAINER repairing task docs', 'installing what the review of A needs', …"""
    words = JOB_WORDS.get(job.get('role'), '{role} {task}')
    return words.format(role=job.get('role', 'job'), task=job.get('task') or '').strip()


Verdict = tuple[str, str]


def _service_verdict(runner: Runner) -> Verdict | None:
    """Startup refusals, task-store setup and service lifecycle take precedence."""
    if runner.stop_reason:
        return f'Needs attention — {runner.stop_reason}', 'bold red'
    setup = runner.setup_label
    if setup:
        return setup, 'bold yellow'
    if runner.state == 'restarting':
        return (f"Restarting {runner.restarting}" if runner.restarting.startswith('onto') else 'Restarting', 'bold cyan')
    if runner.state == 'paused':
        return 'Paused — p resumes it', 'bold yellow'
    if runner.state == 'not running':
        return 'Not running — a starts its service', 'bold red'
    if runner.state == 'unavailable':
        return 'Runtime unavailable — ' + (runner.blocker or 'see acquisition errors'), 'bold red'
    return None


def _question_count(runner: Runner) -> str:
    count = len(runner.questions)
    return f"{count} question{'s' if count > 1 else ''}" if count else ''


def _working_verdict(runner: Runner) -> Verdict:
    """Live jobs and worker lanes, rather than every commit still in flight."""
    if runner.job and not runner.lanes:
        return f"Working — {job_text(runner.job)} ({duration(runner.minutes) or '0m'})", 'bold green'
    # Fifteen finished commits waiting to merge must not read as "16 of 1 workers busy".
    heads = ([row.bucket for row in inventory_rows(runner)] if runner.snapshot is not None else
             [status(lane)[0] for lane in runner.lanes])
    busy = heads.count(ACTIVE) if runner.snapshot is not None else runner.running or heads.count(ACTIVE)
    of = f' of {runner.max_workers}' if runner.max_workers else ''
    text = f"Working — {busy}{of} worker{'s' if busy != 1 else ''} busy"
    if heads.count(MERGEABLE):
        text += f'; {heads.count(MERGEABLE)} mergeable'
    if heads.count(WAITING):
        queued = heads.count(WAITING)
        text += f"; {queued} commit{'s' if queued != 1 else ''} waiting"
    if runner.gate:
        text += f'; no more start: {runner.gate}'
    asks = _question_count(runner)
    if asks:
        text += f'; {asks} for you'
    return text, 'bold green'


def _question_verdict(runner: Runner) -> Verdict:
    first = runner.questions[0]
    return (f'Waiting on you — {_question_count(runner)}, easiest {first.id} (unblocks {first.unblocks}): {first.needs}',
            'bold yellow')


def _held_verdict(runner: Runner, head: str) -> Verdict:
    if not runner.held:
        return head, 'bold yellow'
    task, cause = (blocking(runner.held) or runner.held)[0]
    if cause in WAIT_CAUSES:
        return f"Waiting — {task}: {health.CAUSES.get(cause, cause)}", 'bold yellow'
    asked = any(q.id == task for q in runner.questions)
    return f'Blocker — {task}: {blocker_detail(cause, asked)}', 'bold yellow'


def _blocked_verdict(runner: Runner) -> Verdict:
    """Health's runner blocker, waiting groups, dependency roots and legacy holds."""
    age = duration(runner.minutes)
    head = ('Stuck ' + age).strip() if runner.state in ('stalled', 'blocked', 'not cycling') else runner.state
    if runner.blocker:
        return f'{head} — {runner.blocker}', 'bold red'
    if runner.state != 'not cycling' and runner.waiting_groups:
        return f'Waiting — {waiting_line(runner)}', 'bold yellow'
    if runner.roots:
        root = max(runner.roots, key=lambda r: r.get('blocks', 0))
        if runner.state == 'not cycling':
            return f"{head} — {health.describe(root)}", 'bold red'
        return f"Waiting — {health.describe(root)}", 'bold yellow'
    if runner.state == 'not cycling':
        return f'{head} — its status has not been refreshed; the runner may be busy or hung', 'bold red'
    return _held_verdict(runner, head)


def verdict(runner: Runner) -> Verdict:
    """(sentence, style): whether this runner is stuck, and why, in one line."""
    service = _service_verdict(runner)
    if service is not None:
        return service
    if runner.snapshot is not None:
        counts = task_counts(runner)
        if counts is None:
            return ('Task inventory unavailable — ' + (runner.blocker or 'see acquisition errors')), 'bold yellow'
        if counts[0] or counts[1] or runner.job:
            return _working_verdict(runner)
        if runner.questions:
            return _question_verdict(runner)
        if counts[3]:
            return 'Blocker — ' + blocker_parts(runner), 'bold yellow'
        if counts[2]:
            return 'Waiting — ' + waiting_line(runner), 'bold yellow'
        if counts[4]:
            count = counts[4]
            return f'{count} task{"s" if count != 1 else ""} in Needs decision', 'bold yellow'
        return 'Idle — nothing left to run in Now/Next', 'bold green'
    if runner.state == 'working':
        return _working_verdict(runner)
    if runner.questions:
        return _question_verdict(runner)
    if runner.state == 'idle':
        return 'Idle — nothing left to run in Now/Next', 'bold green'
    if runner.state == health.HOST_WAIT:
        text = runner.waiting_groups[0]['label'] if runner.waiting_groups else health.HOST_WAIT
        return text, 'bold yellow'
    if runner.gate and not runner.lanes:
        return f'Host busy — {runner.gate}', 'bold yellow'
    return _blocked_verdict(runner)


def maintainer_line(runner, now=None):
    """'DOCS-MAINTAINER: merged 12m ago; changed A, B (triggered by A, B, C)', or ''."""
    run = runner.maintainer
    if not run.get('at'):
        return ''
    now = time.time() if now is None else now
    text = f"DOCS-MAINTAINER: {run.get('outcome', '?')} {ago(int(now - run['at']))}"
    if run.get('changed'):
        text += '; changed ' + ', '.join(run['changed'])
    if run.get('triggers'):
        text += ' (for ' + ', '.join(run['triggers'][:6]) + (' …' if len(run['triggers']) > 6 else '') + ')'
    return text


def waiting_line(runner, limit=4):
    """'23 wait for X (overlapping files) · 12 on dependencies · …', or ''."""
    groups = waiting_parts(runner) if runner.snapshot is not None else [(g['count'], g['label']) for g in runner.waiting_groups]
    parts = [f'{n} {label}' for n, label in groups[:limit]]
    more = len(groups) - limit
    return ' · '.join(parts) + (f' · +{more} more reasons' if more > 0 else '')


# Each task shows one headline and a detail (docs/project.md, "Task status vocabulary"):
# the headline says whether it moves, the detail how far it got. Engine states stay internal.
ACTIVE, MERGEABLE, WAITING, BLOCKER = task_status.ACTIVE, task_status.MERGEABLE, task_status.WAITING, task_status.BLOCKER
WAIT_PHASES, ACTIVE_PHASES = task_status.WAIT_PHASES, task_status.ACTIVE_PHASES
status, resolver = task_status.status, task_status.resolver


# A hold the engine lifts by itself once another task's files are free: a wait, not an obstacle.
WAIT_CAUSES = task_status.WAIT_CAUSES


def blocking(held):
    """The holds that are Blockers: every hold but those the engine lifts by itself."""
    return [(task, cause) for task, cause in held if cause not in WAIT_CAUSES]


blocker_detail = task_status.blocker_detail


def question_summary(runner):
    """'2 questions for you in BLOCKERS.md: 1 for the blocker above, 1 that blocks no task'. The
    Blocker count is held tasks; questions also cover waiting tasks and the runner itself, and a
    bare '2 questions' beside 'Blocker 1' read as a contradiction."""
    count = len(runner.questions)
    if not count:
        return ''
    held = {task for task, _ in runner.held}
    kinds = [('for the blocker above', 'for the blockers above',
              sum(q.id in held for q in runner.questions)),
             ('on a waiting task', 'on waiting tasks',
              sum(q.id not in held and q.unblocks > 0 for q in runner.questions)),
             ('that blocks no task', 'that block no task',
              sum(q.id not in held and q.unblocks <= 0 for q in runner.questions))]
    parts = [f'{n} {one if n == 1 else many}' for one, many, n in kinds if n]
    head = f"{count} question{'s' if count > 1 else ''} for you in BLOCKERS.md"
    return head + (': ' + ', '.join(parts) if len(parts) > 1 or kinds[0][2] != count else '')


def task_counts(runner):
    """(active, mergeable, waiting, blocker, decision, total) for a runner: every open task in exactly
    one column, so the columns add up to Total. Decision is the Needs-decision tasks, which wait
    for the owner, not the engine. Blocker is the held tasks and the waiting tasks stopped behind
    something that needs a person or a repair: a blocked runner showed Blocker 0 and its stuck
    task as Waiting, as if nothing were wrong."""
    snap = snapshot_for(runner)
    if snap.counts is None or not runner.display_deleted:
        return snap.counts
    buckets = (ACTIVE, MERGEABLE, WAITING, BLOCKER, 'Decision')
    rows = inventory_rows(runner)
    return (*(sum(row.bucket == bucket for row in rows) for bucket in buckets), len(rows))


def inventory_rows(runner):
    """Effective display only; the attached committed snapshot is never rewritten."""
    return tuple(row for row in snapshot_for(runner).rows if row.task not in runner.display_deleted)


# Why a task in flight waits, as a label of the Waiting row ("7 implemented, waiting for review").
WAIT_LABELS = task_status.WAIT_LABELS


def waiting_parts(runner):
    """[(count, label)] of every Waiting task, so the parts add up to the Waiting count: commits in
    flight by phase, then the queue's reasons, then overlap holds. The row showed only the queue's
    reasons, '8: 6 on dependencies · 2 …' beside '15 waiting'."""
    groups = {}
    for row in inventory_rows(runner):
        if row.bucket == WAITING:
            groups[row.why] = groups.get(row.why, 0) + 1
    return [(n, label) for label, n in groups.items()]


def blocker_parts(runner, asked=()):
    """'3: B Conflict · Agent repair · 2 behind X (outside condition or task not in Now/Next)', or '':
    the Blocker count, then each held task and what stops the waiting ones, adding up to it."""
    rows = [row for row in inventory_rows(runner) if row.bucket == BLOCKER]
    details = [f'{row.task} {row.why}' for row in rows]
    if runner.stop_reason:
        details.append(f'Runner: {runner.stop_reason}')
    return (f'{len(rows)}: ' + ' · '.join(details)) if details else ''


def waiting_detail(runner):
    """'15: 7 implemented, waiting for review · 6 on dependencies · 2 wait for …', or ''."""
    parts = waiting_parts(runner)
    if not parts:
        return ''
    return f"{sum(n for n, _ in parts)}: " + ' · '.join(f'{n} {label}' for n, label in parts)


def reviews(state_dir, proc='/proc'):
    """({task: its own review runs}, {task: a batch checking it runs}) for the runner whose state is
    ``state_dir``, from live `worker.py --verify STATE TASK` and `--verify-batch STATE SESSION
    SCRIPT TASK...` processes. The runner log's last "verifying" outlives a review that died."""
    state = os.path.realpath(state_dir)
    single, batch = set(), set()
    for entry in Path(proc).glob('[0-9]*'):
        try:
            argv = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except OSError:
            continue
        for i, arg in enumerate(argv[:-2]):
            if arg in ('--verify', '--verify-batch') and os.path.realpath(argv[i + 1]) == state:
                if arg == '--verify':
                    single.add(argv[i + 2])
                else:
                    batch.update(a for a in argv[i + 4:] if a)
                break
    return single, batch


def lanes(runner, now=None):
    """Tasks in flight for this runner, from the engine's slots, the runner log and Pi transcripts."""
    now = time.time() if now is None else now
    if not runner.repo:
        return []
    try:
        common = task_snapshot._git(runner.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir').decode().strip()
    except (OSError, ValueError, subprocess.SubprocessError):
        return []
    phases = _phases(runner.state_dir) if runner.state_dir else {}
    single, batch = reviews(runner.state_dir) if runner.state_dir else (set(), set())
    out = []
    for path in sorted(Path(common or '/nonexistent', 'autowork-execution', 'slots').glob('*.json')):
        try:
            slot = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if slot.get('state') not in IN_FLIGHT:
            continue
        task = slot.get('task_id', path.stem)
        phase, detail, phase_at = phases.get(task, (PHASES[slot['state']], '', 0))
        if slot['state'] == 'integrating' and runner.state_dir:
            # Both the merged and base suites publish here; a dead invocation is never a live wait.
            progress = main_check.slot_status(Path(runner.state_dir) / 'full-check' / f'{task}.status.json')
            if progress.get('state') == 'waiting' and main_check.alive(progress.get('pid')):
                phase, detail = 'waiting for a check slot', f"{progress.get('ahead', 0)} ahead"
        if phase == 'implemented' and task in batch:
            # A finished commit a running batch (or merge-train car) is checking: it read as idle
            # "Implemented" for the whole check, so six tasks under check looked forgotten.
            phase, detail = 'batch check', 'one full check for the batch'
        if phase == 'verifying' and runner.state_dir and task not in single:
            # Its review is gone: hours of "verifying" for three tasks whose reviews had died.
            phase, detail = (('batch check', 'one full check for the batch') if task in batch else
                             ('waiting to integrate', 'its review is not running'))
        started = slot.get('started_at')
        activity, age = _activity(runner.state_dir, task, now) if runner.state_dir else ('', None)
        lane = Lane(task=task, phase=phase, detail=detail, attempt=slot.get('attempt', 1),
                    minutes=int((now - started) // 60) if started else None, activity=activity, activity_age=age)
        lane.slot_state = slot['state']
        lane.started_at, lane.phase_at = started, phase_at
        try:
            contract = Path(common, 'autowork-execution', 'slot-data', str(task),
                            f'attempt-{lane.attempt}', 'contract.json')
            lane.contract_hash = json.loads(contract.read_text()).get('contract_hash')
        except (OSError, ValueError, AttributeError):
            lane.contract_hash = None
        out.append(lane)
    # Twenty finished commits listed first hid the eight tasks actually running.
    return sorted(out, key=lambda lane: status(lane)[0] != ACTIVE)


def ago(seconds):
    if seconds is None:
        return ''
    if seconds < 90:
        return f'{seconds}s ago'
    return duration(seconds // 60) + ' ago'


def instance(repo):
    """The name pi-autowork.sh --install-service gives the repository."""
    name = Path(repo).name
    if re.fullmatch(r'[A-Za-z0-9._-]+', name):
        return name
    try:
        return subprocess.run(['systemd-escape', '--', name], capture_output=True, text=True,
                              timeout=10).stdout.strip() or name
    except (OSError, subprocess.SubprocessError):
        return name


def duration(minutes):
    if minutes is None:
        return ''
    return f'{minutes // 60}h{minutes % 60:02d}m' if minutes >= 60 else f'{minutes}m'


def short(text, limit=32):
    text = ' '.join(str(text).split())
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(' ', 1)[0] if ' ' in text[:limit] else text[:limit]
    return cut + '...'


@dataclass(frozen=True)
class Question:
    id: str
    effort: str
    unblocks: int
    needs: str
    answer: str = ''    # how the runner says to answer it
    kind: str = ''      # held, quick_hold, claim, cycle, contract, outside, ...: which quick answers apply


def _planning_questions(text):
    """Read unanswered maintainer stops, not resolved history or the engine block."""
    block = owner_questions.block_of(text)
    if block is not None:
        text = text.replace(owner_questions.START + block + owner_questions.END, '', 1)
    text = re.sub(r'^##[ \t]+Resolved[ \t]*\n.*?(?=^#{1,2}[ \t]|\Z)', '', text,
                  flags=re.M | re.S | re.I)
    found = []
    for section in re.finditer(r'^### Q-(\S+) — Planning stopped[ \t]*\n(.*?)(?=^#{1,6}[ \t]|\Z)',
                               text, re.M | re.S):
        body = section[2]
        statuses = re.findall(r'^- Status:[ \t]*(.*)$', body, re.M | re.I)
        if statuses and re.match(r'RESOLVED\b', statuses[-1].strip(), re.I):
            continue
        fields, current = [], None
        for line in body.splitlines():
            field = re.match(r'^- ((?:Task|Question|Owner decision):[ \t]*.*)$', line)
            if field:
                current = [field[1].strip()]
                fields.append(current)
            elif (current is not None and line[:1].isspace() and line.strip()
                  and not re.match(r'(?:[-*+]|\d+[.)]|#+)(?:\s|$)', line.lstrip())):
                current.append(line.strip())
            else:
                current = None  # another field, bullet or unindented prose ends the logical field
        need = ' '.join(' '.join(field) for field in fields) if fields else ' '.join(body.split())
        found.append(Question(section[1], 'decision', 1, need, kind='decision'))
    return found


def read_questions(repo, state_dir='', *, provenance=None, errors=None):
    """Engine questions followed by maintainer planning stops, without changing BLOCKERS.md.
    They reach the repository when the session merges, so prefer the session worktree's copy,
    including when it has only planning-stop questions and no engine block."""
    block, planning = None, []
    try:
        session = json.loads((Path(state_dir) / 'session.json').read_text())['path'] if state_dir else ''
    except FileNotFoundError:
        session = ''
    except (OSError, ValueError, KeyError, TypeError) as exc:
        session = ''
        if errors is not None:
            errors.append(f'question session source: {exc}')
    for folder in (session, repo):
        try:
            text = (Path(folder) / 'BLOCKERS.md').read_text() if folder else ''
        except FileNotFoundError:
            continue
        except (OSError, UnicodeError) as exc:
            if errors is not None:
                errors.append(f'questions {folder}: {exc}')
            continue
        if provenance is not None:
            provenance.update(questions_workspace=str(folder), questions_at=time.time())
        block, planning = owner_questions.block_of(text), _planning_questions(text)
        if block is not None or planning:
            break
    found = []
    for line in (block or '').splitlines():
        head = re.match(r'^### Q-(.+?) — \S+ — effort (\S+) — unblocks (\d+)', line)
        if head:
            found.append(Question(head[1], head[2], int(head[3]), ''))
        elif found and line.startswith('- Needs: '):
            found[-1] = replace(found[-1], needs=line[len('- Needs: '):].strip())
        elif found and line.startswith('- Answer: '):
            found[-1] = replace(found[-1], answer=line[len('- Answer: '):].strip())
        elif found and line.startswith('- Kind: '):
            found[-1] = replace(found[-1], kind=line[len('- Kind: '):].strip())
    return found + planning


def needs(runner):
    """What would move this runner, in a few words: setup, owner questions, else its first blocker."""
    if runner.stop_reason:
        return runner.stop_reason
    setup = runner.setup_label
    if setup:
        return setup
    if runner.state == 'restarting':
        return ('restarting ' + runner.restarting).strip() if runner.restarting != 'service' else 'restarting'
    if runner.state in ('paused', 'not running'):
        return 'start it' if runner.state == 'not running' else 'resume it'
    if runner.questions:
        first = runner.questions[0]
        count = len(runner.questions)
        return f"{count} question{'s' if count > 1 else ''}, easiest {first.id}"
    if runner.waiting_groups:
        return waiting_line(runner)
    groups = blockers(runner)
    if groups:
        kind, items = groups[0]
        return f'{kind}: {items}'
    if runner.decisions:
        return f"{runner.decisions} task{'s' if runner.decisions > 1 else ''} in Needs decision"
    return ''


TASK_LINE = re.compile(r'^\[(\d\d:\d\d)\] (\S+): (\w+)\b')
# systemd's own lines about the unit, and the runner's start banner (its settings are in the detail).
UNIT_LINE = re.compile(r'^(Starting|Started|Stopping|Stopped) pi-autowork@|^pi-autowork@\S+: ')
BANNER = re.compile(r'^(PI AUTOWORK$|Repository: |Toolset: |Engine: |Primary: |Fallback: |Mode: )')
WORD_STYLES = {'done': 'green', 'integrated': 'green', 'failed': 'bold red', 'running': 'cyan',
               'verifying': 'cyan', 'landing': 'cyan', 'implemented': 'cyan', 'resuming': 'cyan', 'paused': 'yellow'}


def log_lines(text):
    """[(line, style)]: the journal as a person reads it. Per-task `pending` lines (the
    `No task can start now` line covers them), systemd's unit lines, the start banner, session
    lines and the results a restart printed again are dropped; a stop and the start that
    follows are one `restarted` line (`onto <commit>` for an update), and a line that only
    repeats the one before gets a `×N` count instead of a copy."""
    out, last = [], {}
    stop = None        # (time, onto) of a stop or update not yet followed by its start
    onto = ''

    def add(line, style):
        message = line[8:] if line.startswith('[') and line[6:8] == '] ' else line
        if out and out[-1][3] == message:
            out[-1][2] += 1
            return
        out.append([line, style, 1, message])

    for line in text.splitlines():
        if UNIT_LINE.match(line) or BANNER.match(line) or not line.strip():
            continue
        stamp = line[:7]
        update = re.search(r'\] Toolset updated to (\S+?);? restarting on it', line)
        if update:
            onto, stop = update.group(1), stop or (stamp, update.group(1))
            continue
        if '] Stopping: ' in line or '] Stopped. ' in line:
            stop = stop or (stamp, onto)
            continue
        if ' Started (PID ' in line:
            if stop:
                add(f"{stop[0]} ── restarted{' onto ' + stop[1] if stop[1] else ''} ──", 'bold')
            else:
                add(f'{stamp} ── started ──', 'bold')
            stop, onto = None, ''
            continue
        if re.match(r'^\[\d\d:\d\d\] Session \S+ started from ', line):
            continue
        task = TASK_LINE.match(line)
        if task:
            _, name, word = task.groups()
            if word == 'pending' or last.get(name) == word:
                continue
            last[name] = word
            add(line, WORD_STYLES.get(word, ''))
            continue
        if 'Questions for the owner' in line or 'No task can start' in line or 'Merge pending' in line:
            add(line, 'yellow')
        elif 'needs attention' in line or 'failed' in line.lower():
            add(line, 'red')
        else:
            add(line, '')
    if stop:
        out.append([f"{stop[0]} ── {'restarting onto ' + stop[1] if stop[1] else 'stopped'} ──", 'bold', 1, ''])
    return [(line + (f'  ×{count}' if count > 1 else ''), style) for line, style, count, _ in out]


def quiet_log(text):
    """log_lines without styles."""
    return '\n'.join(line for line, _ in log_lines(text))


def blockers(runner, limit=6):
    """[(kind label, 'ID cause (n), ...')] in a fixed order: what a person can unblock."""
    groups = {}
    for root in runner.roots:
        if root.get('kind') not in KINDS:
            continue
        item = short(root.get('id', '?'))
        if root.get('kind') == 'held' and root.get('cause'):
            item += ' ' + CAUSES.get(root['cause'], root['cause'])
        groups.setdefault(root['kind'], []).append(f"{item} ({root.get('blocks', 0)})")
    def joined(items):
        more = f', +{len(items) - limit} more' if len(items) > limit else ''
        return ', '.join(items[:limit]) + more
    return [(KINDS[k], joined(groups[k])) for k in ORDER if k in groups]


class DiscoveryUnavailable(RuntimeError):
    """Service discovery failed; an empty list would be misleading."""


def _lines(argv, timeout=10, *, strict=False, env=None):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout, env=env)
    except (OSError, subprocess.SubprocessError) as error:
        if strict:
            raise DiscoveryUnavailable(f'runner discovery unavailable: {type(error).__name__}') from error
        return []
    if out.returncode and strict:
        raise DiscoveryUnavailable(f'runner discovery unavailable: service query exited {out.returncode}')
    return out.stdout.splitlines() if out.returncode == 0 else []


def paused_marker(env_dir, name):
    """Written by `autowork pause`, removed by `autowork resume` and `autowork start`: a stopped
    service is paused only when someone paused it; otherwise it is simply not running."""
    return Path(env_dir) / f'{name}.paused'


def _service_states(env_dir, systemctl: str, strict: bool, errors=None) -> dict[str, str]:
    services = {}
    for line in _lines([systemctl, '--user', 'list-units', 'pi-autowork@*', '--all', '--plain', '--no-legend'], strict=strict):
        parts = line.split()
        if len(parts) >= 4 and parts[0].startswith('pi-autowork@') and parts[0].endswith('.service'):
            services[parts[0][len('pi-autowork@'):-len('.service')]] = parts[3]
    # A stopped, disabled (paused) service may not be loaded, so systemd does not list it;
    # every installed service has a settings file.
    for env_file in sorted(Path(env_dir).glob('*.env')):
        if read_env(env_file, errors=errors).get('PI_AUTOWORK_REPO'):
            services.setdefault(env_file.stem, 'dead')
    return services


def _service_runner(name: str, sub: str, env_dir, systemctl: str, errors=None) -> Runner:
    settings = read_env(Path(env_dir) / f'{name}.env', errors=errors)
    try:
        result = subprocess.run([systemctl, '--user', 'is-enabled', '--quiet', f'pi-autowork@{name}.service'],
                                capture_output=True, timeout=10)
        enabled = result.returncode == 0
        if result.returncode not in (0, 1) and errors is not None:
            errors.append(f'{name}: service enabled query exited {result.returncode}')
    except (OSError, subprocess.SubprocessError) as exc:
        enabled = False
        if errors is not None:
            errors.append(f'{name}: service enabled query: {exc}')
    return Runner(name=name, service=sub, mode='service',
                  repo=settings.get('PI_AUTOWORK_REPO', '').strip(),
                  model=settings.get('PI_AUTOWORK_PRIMARY') or DEFAULT_MODEL,
                  fallback=settings.get('PI_AUTOWORK_FALLBACK') or DEFAULT_FALLBACK,
                  push=settings.get('PI_AUTOWORK_PUSH', '0') == '1',
                  toolset=settings.get('PI_AUTOWORK_TOOLSET', '').strip(), enabled=enabled)


def _health_runner(found: dict[str, Runner], row: dict, now: float) -> Runner | None:
    """Merge a health row into its installed service; orphaned state is only history."""
    if not row.get('repo'):
        return None  # a state-folder basename is not repository/service identity
    # systemd escapes instance names; health records the repository basename.
    runner = next((r for r in found.values() if r.repo and Path(r.repo) == Path(row['repo'])),
                  found.get(row['name']))
    if runner is None or (runner.repo and Path(runner.repo) != Path(row['repo'])):
        return None
    repo = runner.repo or row['repo']
    state_dir = row['state_dir']
    try:
        minutes = int((now - row['since']) // 60) if row.get('since') and row['state'] != 'not running' else None
        job = row.get('job')
        if job and job.get('started'):
            minutes = int((now - job['started']) // 60)
        # status.json deliberately omits the PID and may outlive a stopped runner.
        check = main_check.read(state_dir, repo, fallback=row.get('main_check'))
        return replace(runner, repo=repo, state_dir=state_dir, state=row['state'], minutes=minutes,
                       running=row.get('workers', 0), waiting=row.get('waiting', 0),
                       stopped=row.get('stopped', 0), stopped_groups=row.get('stopped_groups') or [],
                       held=[(h.get('task', '?'), h.get('cause')) for h in row.get('held', [])],
                       roots=[r for r in row.get('roots', []) if health.needs_person(r)],
                       waiting_groups=row.get('waiting_groups') or [], blocker=row.get('blocker') or '',
                       stop_reason=row.get('stop_reason') or '', max_workers=row.get('max_workers'),
                       maintainer=row.get('maintainer') or {}, main_check=check, job=job,
                       acquisition_errors=list(row.get('errors') or []))
    except (OSError, ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
        error = f'{state_dir}: runtime projection unavailable: {exc}'
        return replace(runner, repo=repo, state_dir=state_dir, state='unavailable',
                       running=None, waiting=None, stopped=None, blocker=error,
                       acquisition_errors=[*row.get('errors', []), error])


def _prepared_runner(runner: Runner) -> Runner:
    if not runner.repo or not Path(runner.repo).is_dir():
        return runner
    report = task_prepare.prepare(runner.repo, mode='check')
    return replace(runner, prepare_state=report.get('state'),
                   decisions=(report.get('counts') or {}).get('open:Needs decision', 0))


def _active_runner(runner: Runner, now: float) -> Runner:
    """Worker transcripts and recent log events can supersede an old health snapshot."""
    runner = replace(runner, lanes=lanes(runner, now))
    restarting, gate = recent_events(runner, now)
    # Status refreshes between cycles, not during a long verification: recent work wins.
    if runner.state in ('blocked', 'stalled', 'not cycling') and any(
            lane.activity_age is not None and lane.activity_age < health.STALE_AFTER for lane in runner.lanes):
        runner = replace(runner, state='working', minutes=None)
    provenance, errors = {}, []
    questions = read_questions(runner.repo, runner.state_dir, provenance=provenance, errors=errors) if runner.repo else []
    return replace(runner, restarting=restarting, gate=gate, questions=questions,
                   question_provenance=provenance, acquisition_errors=[*runner.acquisition_errors, *errors])


def _service_lifecycle(runner: Runner, env_dir) -> Runner:
    if runner.has_service and runner.service in RESTARTING:
        runner = replace(runner, restarting=runner.restarting or 'service')
    if runner.has_service and runner.service not in ('running', 'start', 'reload'):
        if not runner.enabled and paused_marker(env_dir, runner.name).exists():
            state = 'paused'  # paused on purpose: `autowork resume`
        elif runner.restarting:
            state = 'restarting'  # its own update, not a stop
        else:
            state = 'not running'  # its records may say otherwise
        return replace(runner, state=state, minutes=None)
    return runner


def collect(state_root, env_dir, *, systemctl='systemctl', now=None, strict=False,
            _generation=0, _cached=None, _last_good=None, _errors=None) -> list[Runner]:
    """Every runner: pi-autowork@ services and their runner state, merged by name."""
    now = time.time() if now is None else now
    services = _service_states(env_dir, systemctl, strict, _errors)
    found = {name: _service_runner(name, sub, env_dir, systemctl, _errors) for name, sub in services.items()}
    rows = health.fleet(state_root, now=now, service=lambda name: services.get(name, '-'))
    # Historical duplicate folders must not overwrite independently verified live data.
    rows.sort(key=lambda row: (row['runner_alive'], not row.get('errors'),
                               row.get('updated_at') or 0), reverse=True)
    associated = set()
    for row in rows:
        if _errors is not None:
            _errors.extend(row.get('errors') or [])
        runner = _health_runner(found, row, now)
        if runner is not None:
            if runner.name in associated:
                retained = found[runner.name]
                error = f'{row["state_dir"]}: duplicate runtime identity; retained {retained.state_dir}'
                retained.acquisition_errors.extend([*row.get('errors', []), error])
                if _errors is not None:
                    _errors.append(error)
            else:
                found[runner.name] = runner
                associated.add(runner.name)
        elif _errors is None:
            for error in row.get('errors') or []:
                print(f'pi-autowork: {error}', file=sys.stderr)
    retained = _last_good or _cached
    previous = {s.workspace: s for s in retained.snapshots} if retained else {}
    audits = {p.workspace: p for p in _cached.preparation} if _cached else {}
    for name, runner in found.items():
        if _errors is None:  # Full CLI diagnostics remain uncached.
            runner = _prepared_runner(runner)
        active = _active_runner(runner, now)
        runner = _service_lifecycle(active, env_dir)
        snap = snapshot_for(runner, generation=_generation, last_good=previous.get(str(Path(runner.repo).resolve())))
        if _errors is not None:
            _errors.extend(f'{name}: {error}' for error in snap.errors)
            preparation = _preparation(runner, env_dir, now, audits, _errors)
            runner = replace(runner, preparation=preparation, prepare_state=preparation.state)
        # Both public consumers use current committed Decision membership.
        runner.decisions = snap.counts[4] if snap.counts is not None else 0
        found[name] = runner
    # Put the owner's decisions and setup work first; keep each group alphabetical.
    return sorted(found.values(), key=lambda r: (not (r.questions or r.setup_required), r.name))


@dataclass(frozen=True)
class Preparation:
    workspace: str
    key: str | None
    observed_at: float
    state: str
    errors: tuple = ()


@dataclass(frozen=True)
class FleetSnapshot:
    runners: tuple
    snapshots: tuple
    generation: int
    captured_at: float
    errors: tuple = ()
    preparation: tuple = ()


def _preparation_key(runner, env_dir):
    """Invalidate diagnostics for dirty content, revision, settings and environment.

    No pending/readiness result is cached by HEAD. Status plus dirty-file stat
    signatures distinguish repeated edits to an already-dirty source file.
    """
    snap = runner.snapshot
    status = task_snapshot._git(runner.repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all')
    dirty = []
    for item in status.decode(errors='replace').split('\0'):
        if not item:
            continue
        path = Path(runner.repo, item[3:])
        try:
            stat = path.stat()
            dirty.append((str(path), stat.st_mtime_ns, stat.st_ctime_ns, stat.st_size))
        except FileNotFoundError:
            dirty.append((str(path), 'absent'))
    settings = Path(env_dir, f'{runner.name}.env').read_bytes()
    return hashlib.sha256(repr((snap.workspace, snap.repository_identity, snap.revision,
                                status, dirty, settings, sorted(os.environ.items()))).encode()).hexdigest()


def _preparation(runner, env_dir, now, cached, errors):
    key = None
    try:
        key = _preparation_key(runner, env_dir)
    except (OSError, ValueError) as exc:
        errors.append(f'{runner.name}: preparation invalidation read: {exc}')
    previous = cached.get(runner.snapshot.workspace)
    if key is not None and previous and previous.key == key and 0 <= now - previous.observed_at < 30:
        errors.extend(previous.errors)
        return previous
    problems = []
    try:
        report = task_prepare.prepare(runner.repo, mode='check')
        state = report.get('state') or 'unknown'
        if state == 'unknown' or report.get('outcome') in ('INVALID_STORE', 'TOOLCHAIN_MISMATCH'):
            problems.append(f'{runner.name}: preparation: {report}')
    except (OSError, ValueError, subprocess.SubprocessError) as exc:
        state = 'unknown'
        problems.append(f'{runner.name}: preparation: {exc}')
    errors.extend(problems)
    return Preparation(runner.snapshot.workspace, key, now, state, tuple(problems))


def collect_for_tui(state_root, env_dir, *, generation, cached_preparation=None, last_good=None,
                    systemctl='systemctl', now=None):
    """Current inventory plus explicitly aged, <=30s display-only preparation audit.

    Pass the previous envelope to reuse audits/retain last-good inventories. Omit
    it after an action, preparation, interactive return or explicit refresh. The
    separate last_good argument can retain inventory without reusing any audit.
    Confirmed Start continues to use the uncached readiness() path.
    """
    now = time.time() if now is None else now
    errors = []
    try:
        # Directory acquisition errors must not turn into a successful empty glob.
        for label, path in (('service settings', env_dir), ('runner state', state_root)):
            try:
                list(Path(path).iterdir())
            except FileNotFoundError:
                pass  # no settings/state yet is a valid empty installation
            except OSError as exc:
                errors.append(f'{label}: {exc}')
        runners = tuple(collect(state_root, env_dir, systemctl=systemctl, now=now, strict=True,
                                _generation=generation, _cached=cached_preparation, _last_good=last_good, _errors=errors))
    except (DiscoveryUnavailable, OSError, ValueError, subprocess.SubprocessError) as exc:
        errors.append(str(exc))
        runners = ()
        previous = last_good or cached_preparation
        if previous:
            retained = []
            for old in previous.runners:
                runner = replace(old)
                runner.snapshot = replace(old.snapshot, generation=generation, freshness='stale',
                                          errors=old.snapshot.errors + tuple(errors),
                                          engine_freshness='stale' if old.snapshot.engine_source.observed_at is not None else 'unknown')
                runner.preparation = old.preparation
                retained.append(runner)
            runners = tuple(retained)
    return FleetSnapshot(runners, tuple(r.snapshot for r in runners), generation, now, tuple(errors),
                         tuple(r.preparation for r in runners if r.preparation is not None))


def runner_rows(runners):
    """Pure fleet-table projection: one row per runner, ready for a Textual DataTable."""
    rows = []
    for runner in runners:
        now = ', '.join(f'{lane.task} {lane_status(runner, lane)[0]}' for lane in runner.lanes[:2])
        if runner.job:
            now = ', '.join(x for x in (job_text(runner.job), now) if x)
        if len(runner.lanes) > 2:
            now += f' +{len(runner.lanes) - 2}'
        vector = task_counts(runner)
        active, mergeable, waiting, blocker, decision, total = (
            (str(n) for n in vector) if vector is not None else ('?',) * 6)
        rows.append({'Runner': (runner.name, ''),
                     'State': (f'{runner.state} {duration(runner.minutes)}'.strip(), f'bold {runner.color}'),
                     'Active': (active, 'green'), 'Mergeable': (mergeable, 'cyan'), 'Waiting': (waiting, ''),
                     'Blocker': (blocker, 'yellow' if blocker != '0' else ''),
                     'Decision': (decision, 'yellow' if decision != '0' else ''), 'Total': (total, 'bold'),
                     'Needs': (' '.join((needs(runner) or '-').split()), 'yellow' if runner.questions else ''),
                     'Now': (now or '-', '')})
    return tuple(rows)


def summary(runners):
    counts = {}
    for runner in runners:
        counts[runner.state] = counts.get(runner.state, 0) + 1
    order = ['working', 'idle', 'restarting', 'paused', health.HOST_WAIT, 'blocked', 'stalled', 'not running', 'not cycling',
             'starting', 'unknown']
    return [(state, counts[state]) for state in order + sorted(set(counts) - set(order)) if state in counts]


def logs(runner, *, lines=200, journalctl='journalctl', since=None):
    """Recent output: the service journal (``since``: a journalctl time such as '-60min')."""
    if not runner.has_service:
        return ''
    return '\n'.join(_lines([journalctl, '--user', '-u', f'pi-autowork@{runner.name}.service', '-n', str(lines),
                             *(['--since', since] if since else []), '--no-pager', '-o', 'cat'], timeout=20))


@dataclass
class Action:
    key: str
    label: str
    argv: list
    interactive: bool = False   # takes over the terminal (attach, an agent session)
    confirm: str = ''           # a question to ask first, '' for none
    env: dict = field(default_factory=dict)
    deletion: 'DeleteIdentity | None' = None


@dataclass(frozen=True)
class DeleteIdentity:
    runner: str
    workspace: str
    repository_identity: str | None
    task: str


def observe_deletions(identities):
    """Off-loop working-tree presence, not membership or task-store authority."""
    out = []
    for identity in identities:
        try:
            Path(identity.workspace, 'tasks/items', identity.task + '.md').stat()
            present, error = True, ''
        except FileNotFoundError:
            present, error = False, ''
        except OSError as exc:
            present, error = None, str(exc)
        out.append((identity, present, error))
    return tuple(out)


def actions(runner, *, command, script, agent=None):
    """What the owner can do to this runner now, as `autowork` commands (or the runner script).
    One key per action, the first letter of its one-word label, which the TUI highlights in
    the word: P plays a stopped or paused runner and pauses a running one."""
    repo, name = runner.repo, runner.name
    out = [Action('l', 'Log', [], interactive=True)]  # the TUI's own full-screen log view (also Enter)
    running = runner.service in ('running', 'start', 'reload')
    if runner.has_service and running:
        out.append(Action('p', 'Pause', [command, 'pause', name],
                          confirm=f'Pause {name}? Its service stops and stays off until resumed; '
                                  'workers resume on the same attempt.'))
    elif runner.has_service and runner.state == 'paused':
        out.append(Action('p', 'Play', [command, 'resume', name]))
    elif repo:
        out.append(Action('p', 'Play', [command, 'start', repo]))
    if running:
        out.append(Action('s', 'Stop', [command, 'stop', name],
                          confirm=f'Stop {name}? Workers pause and resume on the same attempt at the next start.'))
        if runner.has_service:
            out.append(Action('r', 'Restart', [command, 'restart', name],
                              confirm=f'Restart {name}? It reloads in place; running workers keep running.'))
    if runner.has_service:
        out.append(Action('m', 'Model', [command, 'model', name]))       # the TUI picks the model
        out.append(Action('f', 'Fallback', [command, 'model', name, '--fallback']))
    if repo:
        out.append(Action('t', 'Tasks', [], interactive=True))  # the TUI's Tasks window
    if repo and agent and runner.setup_required:  # no tasks yet: plan them in an agent (autowork plan)
        out.append(Action('b', 'Backlog', [command, 'plan', repo], interactive=True))
    if repo and runner.has_service and not running:
        out.append(Action('u', 'Uninstall', [command, 'remove', name],
                          confirm=f'Remove pi-autowork@{name}? Its state and worktrees stay.'))
    return out


# The Tasks window's views, in key order: what each shows (a TaskRow's kind).
TASK_VIEWS = ('all', 'working', 'held', 'waiting', 'questions', 'closed')


TaskRow = task_snapshot.TaskRow


def _invalidate_runtime(runner, error):
    """Quarantine display data without changing service lifecycle or admission."""
    if runner.state not in ('paused', 'not running', 'restarting'):
        runner.state = 'unavailable'
    runner.blocker, runner.minutes, runner.job = error, None, None
    runner.running = runner.waiting = runner.stopped = runner.max_workers = None
    runner.held, runner.roots, runner.waiting_groups, runner.stopped_groups = [], [], [], []
    runner.maintainer = {}


def snapshot_for(runner, *, generation=0, last_good=None):
    """The attached capture is shared by every renderer; direct API callers capture once."""
    if runner.snapshot is None:
        observation = {}
        if runner.state_dir:
            observation, errors = health.read_observation(Path(runner.state_dir, 'status.json'))
            identity, problems = health.read_observation(Path(runner.state_dir, 'runner.json'))
            errors.extend(problems)
            for source, record in (('status.json', observation), ('runner.json', identity)):
                if record.get('repo') and Path(record['repo']) != Path(runner.repo):
                    errors.append(f'{Path(runner.state_dir, source)}: repo does not match registered service')
            if errors:
                _invalidate_runtime(runner, '; '.join(errors))
            if errors or runner.state == 'unavailable':
                observation = {'errors': errors}
        observation.update(lanes=runner.lanes, questions=runner.questions, **runner.question_provenance)
        observation['errors'] = [*(observation.get('errors') or []), *runner.acquisition_errors]
        try:
            runner.snapshot = task_snapshot.capture(runner.repo, engine_observation=observation,
                                                   generation=generation, last_good=last_good)
        except (ValueError, TypeError, KeyError, AttributeError, OverflowError) as exc:
            # Quarantine this runner's projection, never the fleet or canonical inventory.
            error = f'{runner.state_dir}/status.json: runtime projection unavailable: {exc}'
            _invalidate_runtime(runner, error)
            runner.snapshot = task_snapshot.capture(runner.repo, engine_observation={
                'errors': [*observation.get('errors', []), error]}, generation=generation, last_good=last_good)
    return runner.snapshot


def freshness(runner, now=None, *, detailed=False):
    """Provenance preview, or full detail, with separate inventory/runtime/pending ages."""
    snap = snapshot_for(runner)
    now = time.time() if now is None else now
    text = (f'{snap.freshness} · revision {snap.revision or "unknown"} · generation {snap.generation}'
            f' · captured {ago(max(0, int(now - snap.captured_at)))}'
            f' · execution {snap.engine_freshness}')
    if snap.engine_source.observed_at is not None:
        text += ' ' + ago(max(0, int(now - snap.engine_source.observed_at)))
    if snap.pending_paths is None:
        text += ' · pending paths unknown'
    else:
        text += f' · {len(snap.pending_paths)} pending paths (working tree, independently observed)'
    if snap.questions_workspace:
        text += f' · questions: {snap.questions_workspace}/BLOCKERS.md (working tree, independently observed)'
    if runner.display_deleted:
        text += ' · deletion pending commit: ' + ', '.join(runner.display_deleted)
    if runner.display_recreated:
        text += ' · restored/recreated pending record (not committed inventory): ' + ', '.join(runner.display_recreated)
    # Keep unmatched observations as evidence, not an unbounded wall above the tasks.
    # Closed rows absent from the current inventory are especially common after migrations.
    if detailed:
        return ' · '.join((text, *snap.errors, *snap.annotations))
    closed, warnings = 0, list(snap.errors)
    for annotation in snap.annotations:
        if annotation.endswith(': unmatched execution observation (closed)'):
            closed += 1
        else:
            warnings.append(annotation)
    notes = [' '.join(str(warning).split())[:240] for warning in warnings[:3]]
    if len(warnings) > 3:
        notes.append(f'+{len(warnings) - 3} source warnings')
    if closed:
        notes.append(f'{closed} unmatched closed execution observations (not inventory)')
    if warnings or closed:
        notes.append('full diagnostics: Blockers → Details')
    return ' · '.join((text, *notes))


def task_store(repo):
    """The task store at ``repo``'s HEAD, or None: what the runner reads (uncommitted owner
    edits reach it once the runner commits them)."""
    from pi_autowork.engine import task_queue
    try:
        return task_queue.store(Path(repo))
    except (task_queue.StoreError, OSError, TypeError, subprocess.SubprocessError):
        return None


def task_rows(runner: Runner, include_closed=False) -> list[TaskRow]:
    """Task rows in priority order, optionally including closures and their provenance."""
    snap = snapshot_for(runner)
    rows = list(inventory_rows(runner)) + list(snap.question_rows)
    # Independent questions remain annotations, never resurrected inventory.
    rows.extend(replace(row, kind='annotation', bucket='', why='Independent question; deletion pending commit')
                for row in snap.rows if row.task in runner.display_deleted and row.question)
    if include_closed:
        annotated = {row.task for row in snap.question_rows}
        rows.extend(row for row in closed_task_rows(runner) if row.task not in annotated)
    return rows


def closed_task_rows(runner):
    """All committed closures, including those with independent question annotations."""
    return [row for row in snapshot_for(runner).closed_rows if row.task not in runner.display_deleted]


def task_entry(runner, task):
    """``task``'s whole record file (tasks/items/<task>.md), as written in the checkout."""
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', task or ''):
        return ''
    try:
        return Path(runner.repo, 'tasks', 'items', f'{task}.md').read_text()
    except (OSError, TypeError, ValueError):
        return ''


def open_goals(runner):
    """(id, title) of the goals in ``runner``'s task store not yet met: a new task's choices."""
    return list(snapshot_for(runner).goals)


def task_view(rows, view):
    """The rows a TASK_VIEWS filter shows."""
    if view == 'all':
        return [r for r in rows if r.kind not in ('closed', 'annotation')]
    if view == 'questions':
        return [r for r in rows if r.question]
    return [r for r in rows if r.kind == view]


def task_actions(runner, row, *, command, script, agent=None):
    """What the Tasks window can do with one task: re-sort it (its rank is the priority),
    clear or set aside its hold, answer the owner's questions in an agent, or delete it."""
    repo, name, task = runner.repo, runner.name, row.task
    if task in runner.display_deleted:
        return []
    confirm = (f'Delete {task}? Its record is removed from tasks/ permanently. '
               'Worktrees, commits and evidence stay; tasks that depend on it stay blocked. '
               'A worker or lease using it produces a warning, not a refusal.')
    snap = snapshot_for(runner)
    identity = DeleteIdentity(name, snap.workspace, snap.repository_identity, task)
    delete = Action('x', 'Delete', [command, 'tasks', 'delete', task, identity.workspace],
                    confirm=confirm, deletion=identity)
    if row.kind == 'closed':
        return [delete]
    out = [Action('u', 'Up', [command, 'tasks', 'move', task, 'up', name]),
           Action('d', 'Down', [command, 'tasks', 'move', task, 'down', name]),
           Action('s', 'Section', [], interactive=True)]  # the TUI asks which: Now, Next or Needs decision
    if row.kind == 'held':
        out.append(Action('c', 'Clear', [command, 'clear-held', name, task],
                          confirm=f'Clear the hold on {task}? Its commit goes back to integration; '
                                  'its worktrees stay.'))
        out.append(Action('a', 'Aside', [script, '--repo', repo, '--set-aside', task],
                          confirm=f'Set aside {task}? Its work stays on -set-aside-N branches and it runs fresh.'))
    if agent and runner.questions:
        out.append(Action('b', 'Blockers', [command, 'blockers', repo], interactive=True))
    out.append(delete)
    return out


@dataclass
class Answer:
    """One way to answer an owner question from the TUI, as an `autowork` command."""
    key: str
    label: str              # one word; its key is the first letter
    explain: str            # what it writes, in a few words
    argv: list              # `{text}` stands for the owner's words, when ``needs_text``
    needs_text: bool = False


def answers(runner, question, *, command, today=None):
    """The answers a question's kind supports, written where the runner reads them: the task's
    record. Questions about no task (FULL-CHECK, LEDGER) have none: an agent answers them."""
    task, name = question.id, runner.name
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', task) or task in ('FULL-CHECK', 'LEDGER'):
        return []
    day = today or datetime.date.today()
    out = []
    fingerprint = re.search(r'Blocker resolution: (\S+?);', question.answer or '')
    if question.kind == 'quick_hold' and fingerprint:
        out.append(Answer('r', 'Resolve', 'name the producer task or the decision that unblocks it',
                          [command, 'tasks', 'field', task, 'Blocker resolution', f'{fingerprint[1]}; {{text}}', name], True))
    out.append(Answer('w', 'Write', 'your decision, as a dated Owner decision note in its record',
                      [command, 'tasks', 'field', task, 'Owner decision', f'{day}: {{text}}', name], True))
    out.append(Answer('d', 'Defer', 'move it to Needs decision, with your reason as its Owner decision',
                      [command, 'tasks', 'place', task, 'Needs decision', name, '--decision', f'{day}: deferred: {{text}}'], True))
    return out


@dataclass
class Readiness:
    """Whether a directory can run an Autowork service, and why not."""
    path: str
    repo: str = ''            # the Git toplevel, '' when not in a repository
    ready: bool = False
    problems: list = field(default_factory=list)
    branch: str = ''

    @property
    def mark(self):
        if self.ready:
            return 'ready'
        if not self.repo:
            return 'not a repository'
        return ('' if 'legacy planning' in self.problems else 'needs ') + ', '.join(self.problems)


REQUIRED = ('tasks',)


def uncommitted_planning(repo, base, required=REQUIRED):
    """Planning inputs absent from the base tree, even if they exist in the checkout."""
    return [name for name in required if subprocess.run(
        ['git', '-C', str(repo), 'cat-file', '-e', f'{base}:{name}'],
        capture_output=True, timeout=10).returncode]


def readiness(path):
    """A repository root with its tasks/ store committed on its main branch is ready."""
    path = str(Path(path).expanduser())
    out = Readiness(path=path)
    if not Path(path).is_dir():
        out.problems = ['a directory']
        return out
    try:
        top = subprocess.run(['git', '-C', path, 'rev-parse', '--show-toplevel'], capture_output=True, text=True,
                             timeout=10)
    except (OSError, subprocess.SubprocessError):
        return out
    if top.returncode:
        return out
    out.repo = top.stdout.strip()
    if Path(out.repo).resolve() != Path(path).resolve():
        out.problems.append(f'its repository root ({out.repo})')
    if task_prepare.detect(out.repo) in ('legacy', 'conversion_pending'):
        out.problems.append('legacy planning')
    else:
        out.problems += [name for name in REQUIRED if not (Path(out.repo) / name).is_dir()]
    branch = subprocess.run(['git', '-C', out.repo, 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                            capture_output=True, text=True, timeout=10).stdout.strip()
    out.branch = branch
    if branch not in ('main', 'master'):
        out.problems.append('main checked out' if branch else 'a branch (HEAD is detached)')
    elif not any(name in out.problems for name in (*REQUIRED, 'legacy planning')) and uncommitted_planning(out.repo, branch):
        out.problems.append(f'commit tasks/ on {branch} first')
    if not out.problems:
        report = task_prepare.prepare(out.repo, mode='check')
        # A valid store on an old runner still needs Start's service-copy upgrade path.
        if not report.get('ok') or report.get('state') != 'converted' or report.get('outcome') not in (
                'READY', 'ACTIVATION_PENDING'):
            out.problems.append('task store preparation: ' + report.get('outcome', 'INVALID_STORE'))
    out.ready = not out.problems
    return out


def how_to_fix(ready):
    """One line per missing piece, for the TUI and `autowork start`."""
    hints = []
    for problem in ready.problems:
        if problem == 'legacy planning':
            hints.append(f'Run `autowork tasks prepare --force {ready.repo}` to convert now '
                         '(Force here asks for confirmation); plain Prepare may defer or refuse.')
        elif problem == 'tasks':
            hints.append(f'Run `autowork tasks prepare {ready.repo}` to convert legacy planning; '
                         'with no accepted intent, plan the work with /docs_sync (`autowork plan`, '
                         'or Plan here). No tasks are invented.')
        elif problem.startswith('task store preparation:'):
            hints.append(f'Run `autowork tasks prepare {ready.repo}` and resolve its outcome through '
                         '/docs_sync (`autowork plan`, or Plan here).')
        elif problem.startswith('commit tasks/ on '):
            hints.append(problem)
        elif problem.startswith('main checked out') or problem.startswith('a branch'):
            hints.append(f'Check out main in {ready.repo}: the runner works only from the main branch checkout.')
        elif problem.startswith('its repository root'):
            hints.append(f'Choose the repository root {ready.repo} instead of a subdirectory.')
    return hints


def skill_command(agent, skill):
    """A workflow skill as the agent's own slash command: Claude Code namespaces plugin
    skills (`/autowork:plan-for-me`); Pi and Codex register them with underscores
    (`/plan_for_me`, adapters/pi.mjs)."""
    name = os.path.basename(agent[0]) if agent else ''
    return f'/autowork:{skill}' if name == 'claude' else '/' + skill.replace('-', '_')


def blockers_prompt(agent, repo):
    """The `/blockers` command in the agent's own spelling."""
    return f'{skill_command(agent, "blockers")} {repo}'


def plan_prompt(agent, repo):
    """`/plan_for_me` for a repository without tasks: Docs Sync prepares the store and the
    planner saves tasks from the accepted intent; no runner or schedule starts it."""
    return (f'{skill_command(agent, "plan-for-me")} Plan the work of {repo}: prepare the task store '
            f'and the missing core docs with {skill_command(agent, "docs-sync")}, then investigate the '
            'repository, decide the next work from its accepted intent and save ready tasks. '
            'Do not invent intent; record genuinely missing intent as open questions.')


def blockers_agent(env=os.environ):
    """The agent command for `/blockers` and `autowork plan`: AUTOWORK_AGENT, else claude, else pi."""
    configured = env.get('AUTOWORK_AGENT', '').split()
    if configured:
        return configured
    for name in ('claude', 'pi'):
        for folder in env.get('PATH', '').split(os.pathsep):
            if folder and os.access(os.path.join(folder, name), os.X_OK):
                return [name]
    return None
