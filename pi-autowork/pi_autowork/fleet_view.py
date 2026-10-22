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
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from pi_autowork import health, main_check, portal, questions as owner_questions, task_prepare
from pi_autowork.common import safe_name

KINDS = {'runner': 'runner', 'cycle': 'dependency cycle', 'held': 'blocker', 'contract': 'not runnable',
         'claim': 'claimed elsewhere', 'outside': 'outside Now/Next'}
CAUSES = {'blocker': 'blocker', 'scope': 'outside Touches', 'scope_request': 'needs files', 'overlap': 'overlap',
          'report': 'bad report', 'conflict': 'conflict', 'validation': 'validation', 'crash': 'crashed', 'empty': 'no result',
          'launch': 'launch failed', 'contract_changed': 'entry changed', 'moved': 'main moved'}
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
    'legacy': 'Migration required — run /docs_sync',
    'invalid': 'Task store needs repair',
    'conversion_pending': 'Task store needs repair',
}


def read_env(path):
    """KEY=value lines of a service settings file."""
    try:
        lines = Path(path).read_text().splitlines()
    except OSError:
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
    running: int = 0
    waiting: int = 0
    stopped: int = 0  # waiting tasks that cannot move until something is resolved: Blockers
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


IN_FLIGHT = ('dispatched', 'running', 'reported', 'integrating', 'integrated')
PHASES = {'dispatched': 'starting', 'running': 'implementing', 'reported': 'implemented',
          'integrating': 'integrating', 'integrated': 'integrated'}


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
            found[match.group(1)] = _split_phase(match.group(2))
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
    return None


def _question_count(runner: Runner) -> str:
    count = len(runner.questions)
    return f"{count} question{'s' if count > 1 else ''}" if count else ''


def _working_verdict(runner: Runner) -> Verdict:
    """Live jobs and worker lanes, rather than every commit still in flight."""
    if runner.job and not runner.lanes:
        return f"Working — {job_text(runner.job)} ({duration(runner.minutes) or '0m'})", 'bold green'
    # Fifteen finished commits waiting to merge must not read as "16 of 1 workers busy".
    heads = [status(lane)[0] for lane in runner.lanes]
    busy = runner.running or heads.count(ACTIVE)
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
    parts = [f"{g['count']} {g['label']}" for g in runner.waiting_groups[:limit]]
    more = len(runner.waiting_groups) - limit
    return ' · '.join(parts) + (f' · +{more} more reasons' if more > 0 else '')


# Each task shows one headline and a detail (docs/project.md, "Task status vocabulary"):
# the headline says whether it moves, the detail how far it got. Engine states stay internal.
ACTIVE, MERGEABLE, WAITING, BLOCKER = 'Active', 'Mergeable', 'Waiting', 'Blocker'
# An implemented commit has not been checked: it waits, it is not Mergeable.
WAIT_PHASES = {'implemented': 'Implemented', 'waiting to integrate': 'Merge turn', 'batch check': 'Batch check',
               'waiting for a check slot': 'Check slot', 'paused': 'Paused', 'pending': 'Pending'}
ACTIVE_PHASES = {'starting': 'Starting', 'running': 'Implementing', 'implementing': 'Implementing',
                 'verifying': 'Verifying', 'integrating': 'Merging', 'landing': 'Merging'}


def status(lane):
    """(headline, detail) of a task in flight. Only an integrated commit, whose checks and review
    passed and which is on the session branch, is Mergeable: main is all that remains."""
    if lane.phase == 'integrated':
        return MERGEABLE, 'Verified'
    if lane.phase in WAIT_PHASES:
        return WAITING, WAIT_PHASES[lane.phase]
    return ACTIVE, ACTIVE_PHASES.get(lane.phase, lane.phase.capitalize())


def resolver(asked):
    """Who clears a Blocker: the owner only when the task has an open question in BLOCKERS.md;
    a conflict, a failed check or a missing report is the runner's own repair."""
    return 'Needs you' if asked else 'Agent repair'


# A hold the engine lifts by itself once another task's files are free: a wait, not an obstacle.
WAIT_CAUSES = ('overlap',)


def blocking(held):
    """The holds that are Blockers: every hold but those the engine lifts by itself."""
    return [(task, cause) for task, cause in held if cause not in WAIT_CAUSES]


def blocker_detail(cause, asked=False):
    """'Conflict · Agent repair'."""
    text = CAUSES.get(cause, cause or 'held')
    return f'{text[:1].upper()}{text[1:]} · {resolver(asked)}'


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
    heads = [status(lane)[0] for lane in runner.lanes]
    active = heads.count(ACTIVE) if runner.lanes else runner.running
    mergeable = heads.count(MERGEABLE)
    held = len(blocking(runner.held))
    blocker = held + runner.stopped
    waiting = heads.count(WAITING) + runner.waiting + len(runner.held) - held
    return active, mergeable, waiting, blocker, runner.decisions, active + mergeable + waiting + blocker + runner.decisions


# Why a task in flight waits, as a label of the Waiting row ("7 implemented, waiting for review").
WAIT_LABELS = {'Implemented': 'implemented, waiting for review', 'Merge turn': 'reviewed, waiting for their merge turn',
               'Batch check': 'in a batch check', 'Check slot': 'waiting for a check slot',
               'Paused': 'paused by a restart', 'Pending': 'pending'}


def waiting_parts(runner):
    """[(count, label)] of every Waiting task, so the parts add up to the Waiting count: commits in
    flight by phase, then the queue's reasons, then overlap holds. The row showed only the queue's
    reasons, '8: 6 on dependencies · 2 …' beside '15 waiting'."""
    phases = {}
    for lane in runner.lanes:
        head, detail = status(lane)
        if head == WAITING:
            phases[detail] = phases.get(detail, 0) + 1
    parts = [(n, WAIT_LABELS.get(detail, detail.lower())) for detail, n in phases.items()]
    parts += [(g['count'], g['label']) for g in runner.waiting_groups]
    grouped = sum(g['count'] for g in runner.waiting_groups)
    if runner.waiting > grouped:
        parts.append((runner.waiting - grouped, 'waiting for another reason'))
    overlap = len(runner.held) - len(blocking(runner.held))
    if overlap:
        parts.append((overlap, "waiting for another task's files"))
    return parts


def blocker_parts(runner, asked=()):
    """'3: B Conflict · Agent repair · 2 behind X (outside condition or task not in Now/Next)', or '':
    the Blocker count, then each held task and what stops the waiting ones, adding up to it."""
    if runner.stop_reason:
        return f'Runner: {runner.stop_reason}'
    held = [f'{task} {blocker_detail(cause, task in asked)}' for task, cause in blocking(runner.held)]
    behind = [f"{g['count']} behind {g['label']}" for g in runner.stopped_groups]
    if not held and not behind:
        return ''
    return f'{len(held) + runner.stopped}: ' + ' · '.join(held + behind)


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
        common = subprocess.run(['git', '-C', runner.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                                capture_output=True, text=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
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
        phase, detail = phases.get(task, (PHASES[slot['state']], ''))
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
        out.append(Lane(task=task, phase=phase, detail=detail, attempt=slot.get('attempt', 1),
                        minutes=int((now - started) // 60) if started else None, activity=activity, activity_age=age))
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


@dataclass
class Question:
    id: str
    effort: str
    unblocks: int
    needs: str
    answer: str = ''    # how the runner says to answer it
    kind: str = ''      # held, quick_hold, claim, cycle, contract, outside, ...: which quick answers apply


def read_questions(repo, state_dir=''):
    """The open questions the runner wrote in BLOCKERS.md, easiest first. They are committed on
    its session branch first and reach the repository when the session merges, so the session
    worktree's copy is the current one."""
    block = None
    try:
        session = json.loads((Path(state_dir) / 'session.json').read_text())['path'] if state_dir else ''
    except (OSError, ValueError, KeyError, TypeError):
        session = ''
    for folder in (session, repo):
        try:
            block = owner_questions.block_of((Path(folder) / 'BLOCKERS.md').read_text()) if folder else None
        except OSError:
            continue
        if block is not None:
            break
    found = []
    for line in (block or '').splitlines():
        head = re.match(r'^### Q-(.+?) — \S+ — effort (\S+) — unblocks (\d+)', line)
        if head:
            found.append(Question(head[1], head[2], int(head[3]), ''))
        elif found and line.startswith('- Needs: '):
            found[-1].needs = line[len('- Needs: '):].strip()
        elif found and line.startswith('- Answer: '):
            found[-1].answer = line[len('- Answer: '):].strip()
        elif found and line.startswith('- Kind: '):
            found[-1].kind = line[len('- Kind: '):].strip()
    return found


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
        return f"{runner.decisions} task{'s' if runner.decisions > 1 else ''} need your decision"
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


def _service_states(env_dir, systemctl: str, strict: bool) -> dict[str, str]:
    services = {}
    for line in _lines([systemctl, '--user', 'list-units', 'pi-autowork@*', '--all', '--plain', '--no-legend'], strict=strict):
        parts = line.split()
        if len(parts) >= 4 and parts[0].startswith('pi-autowork@') and parts[0].endswith('.service'):
            services[parts[0][len('pi-autowork@'):-len('.service')]] = parts[3]
    # A stopped, disabled (paused) service may not be loaded, so systemd does not list it;
    # every installed service has a settings file.
    for env_file in sorted(Path(env_dir).glob('*.env')):
        if read_env(env_file).get('PI_AUTOWORK_REPO'):
            services.setdefault(env_file.stem, 'dead')
    return services


def _service_runner(name: str, sub: str, env_dir, systemctl: str) -> Runner:
    settings = read_env(Path(env_dir) / f'{name}.env')
    enabled = subprocess.run([systemctl, '--user', 'is-enabled', '--quiet', f'pi-autowork@{name}.service'],
                             capture_output=True).returncode == 0
    return Runner(name=name, service=sub, mode='service',
                  repo=settings.get('PI_AUTOWORK_REPO', '').strip(),
                  model=settings.get('PI_AUTOWORK_PRIMARY') or DEFAULT_MODEL,
                  fallback=settings.get('PI_AUTOWORK_FALLBACK') or DEFAULT_FALLBACK,
                  push=settings.get('PI_AUTOWORK_PUSH', '0') == '1',
                  toolset=settings.get('PI_AUTOWORK_TOOLSET', '').strip(), enabled=enabled)


def _state_folders(state_root) -> dict[str, str]:
    folders = {}
    for folder in Path(state_root).glob('*/'):
        for record in ('runner.json', 'status.json'):
            try:
                repo = json.loads((folder / record).read_text()).get('repo')
            except (OSError, ValueError, AttributeError):
                continue
            if repo:
                folders.setdefault(repo, str(folder))
    return folders


def _health_runner(found: dict[str, Runner], row: dict, folders: dict[str, str], now: float) -> Runner | None:
    """Merge a health row into its installed service; orphaned state is only history."""
    # systemd escapes instance names; health records the repository basename.
    runner = next((r for r in found.values() if r.repo and Path(r.repo) == Path(row['repo'])),
                  found.get(row['name']))
    if runner is None or (runner.repo and Path(runner.repo) != Path(row['repo'])):
        return None
    repo = runner.repo or row['repo']
    state_dir = folders.get(row['repo'], '')
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
                   maintainer=row.get('maintainer') or {}, main_check=check, job=job)


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
    return replace(runner, restarting=restarting, gate=gate,
                   questions=read_questions(runner.repo, runner.state_dir) if runner.repo else [])


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


def collect(state_root, env_dir, *, systemctl='systemctl', now=None, strict=False) -> list[Runner]:
    """Every runner: pi-autowork@ services and their runner state, merged by name."""
    now = time.time() if now is None else now
    services = _service_states(env_dir, systemctl, strict)
    found = {name: _service_runner(name, sub, env_dir, systemctl) for name, sub in services.items()}
    folders = _state_folders(state_root)
    for row in health.fleet(state_root, now=now, service=lambda name: services.get(name, '-')):
        runner = _health_runner(found, row, folders, now)
        if runner is not None:
            found[runner.name] = runner
    for name, runner in found.items():
        runner = _active_runner(_prepared_runner(runner), now)
        found[name] = _service_lifecycle(runner, env_dir)
    # Put the owner's decisions and setup work first; keep each group alphabetical.
    return sorted(found.values(), key=lambda r: (not (r.questions or r.setup_required), r.name))


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
    if repo and runner.has_service and not running:
        out.append(Action('u', 'Uninstall', [command, 'remove', name],
                          confirm=f'Remove pi-autowork@{name}? Its state and worktrees stay.'))
    return out


# The Tasks window's views, in key order: what each shows (a TaskRow's kind).
TASK_VIEWS = ('all', 'working', 'held', 'waiting', 'questions')


@dataclass
class TaskRow:
    """One open task of a runner's task store, in its priority order."""
    task: str
    short: str          # its `short` (at most 40 characters), cut to 40
    section: str        # Now, Next or Needs decision
    state: str          # in plain words: implementing, implemented, held, waiting, ready, ...
    kind: str           # working, held, waiting, ready: what a TASK_VIEWS filter matches
    why: str = ''       # the hold or wait reason, or the owner's question
    question: bool = False
    pending: bool = False  # its file has an uncommitted edit: the runner reads it once committed


def task_store(repo):
    """The task store at ``repo``'s HEAD, or None: what the runner reads (uncommitted owner
    edits reach it once the runner commits them)."""
    engine = str(Path(__file__).resolve().parents[1] / 'engine')
    if engine not in sys.path:
        sys.path.insert(0, engine)
    import task_queue
    try:
        return task_queue.store(Path(repo))
    except (task_queue.StoreError, OSError, TypeError, subprocess.SubprocessError):
        return None


def pending_edits(repo):
    """IDs of tasks whose file has an uncommitted edit (staged, unstaged or untracked)."""
    from task_store import TaskStore, StoreError
    try:
        paths = TaskStore.pending(Path(repo))
    except (StoreError, OSError, subprocess.SubprocessError):
        return set()
    return {Path(p).stem for p in paths if p.startswith('tasks/items/') and p.endswith('.md')}


@dataclass(frozen=True)
class _TaskState:
    """The engine's per-task state, cause and explanation (or its legacy group fallback)."""
    state: str = ''
    cause: str = ''
    why: str = ''


def _engine_task_states(runner: Runner) -> dict[str, _TaskState]:
    try:
        states = json.loads(Path(runner.state_dir, 'status.json').read_text()).get('tasks') or []
    except (OSError, TypeError, ValueError, AttributeError):
        states = []
    engine = {row[0]: _TaskState(*row[1:]) for row in states if isinstance(row, list) and len(row) == 4}
    if not engine:  # a runner from before the per-task list: its groups name up to 20 tasks each
        engine.update((t, _TaskState('waiting', '', g['label'])) for g in runner.waiting_groups for t in g.get('tasks') or [])
        engine.update((t, _TaskState('held', cause or '', '')) for t, cause in runner.held)
    return engine


def _task_state_words(task: str, section: str, engine: _TaskState, lane: Lane | None, asked: bool) -> tuple[str, str]:
    state, cause = engine.state, engine.cause
    if lane is not None or state in IN_FLIGHT:
        return ' · '.join(status(lane or Lane(task, PHASES[state]))), 'working'
    if state == 'held' and cause in WAIT_CAUSES:
        return f'{WAITING} · ' + blocker_detail(cause).split(' · ')[0], 'held'
    if state == 'held':
        return f'{BLOCKER} · ' + blocker_detail(cause, asked), 'held'
    if state in ('waiting', 'pending'):
        return WAITING, 'waiting'
    if section == 'Needs decision':
        return f'{WAITING} · Needs decision', 'waiting'
    return f'{WAITING} · Ready' if state in ('', 'ready') else state, 'ready'


def _open_task_row(record, engine: _TaskState, lane: Lane | None, question: Question | None, edited: bool) -> TaskRow:
    short = ' '.join(record.short.split()) or ' '.join(record.title.split())
    words, kind = _task_state_words(record.id, record.section, engine, lane, bool(question))
    if edited:
        words += ' · Edit not committed'
    short = short if len(short) <= 40 else short[:39].rstrip() + '…'
    return TaskRow(task=record.id, short=short, section=record.section, state=words, kind=kind,
                   why='you: ' + question.needs if question else engine.why, question=bool(question), pending=edited)


def _closed_task_rows(store) -> list[TaskRow]:
    rows = []
    for record in sorted(store.tasks.values(), key=lambda t: t.id):
        if record.status == 'done':
            info = record.closure_info
            why = (info['evidence'] if record.closure == 'coordinator_verified' else info['reason']) or 'Closure provenance not recorded'
            rows.append(TaskRow(record.id, record.short or record.title, 'Closed', info['label'], 'closed', why))
    return rows


def task_rows(runner: Runner, include_closed=False) -> list[TaskRow]:
    """Task rows in priority order, optionally including closures and their provenance."""
    store = task_store(runner.repo) if runner.repo else None
    if store is None:
        return []
    engine = _engine_task_states(runner)
    lanes = {lane.task: lane for lane in runner.lanes}
    asked = {q.id: q for q in runner.questions}
    edited = pending_edits(runner.repo)
    sections = {'Now': 0, 'Next': 1, 'Needs decision': 2}
    records = sorted((t for t in store.tasks.values() if t.status == 'open' and t.section in sections),
                     key=lambda t: (sections[t.section], t.rank or 0, t.id))
    rows = [_open_task_row(record, engine.get(record.id, _TaskState()), lanes.get(record.id),
                           asked.get(record.id), record.id in edited) for record in records]
    if include_closed:
        rows.extend(_closed_task_rows(store))
    return rows


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
    store = task_store(runner.repo) if runner.repo else None
    return [(g.id, g.title) for g in store.goals.values() if g.status != 'met'] if store else []


def task_view(rows, view):
    """The rows a TASK_VIEWS filter shows."""
    if view == 'all':
        return rows
    if view == 'questions':
        return [r for r in rows if r.question]
    return [r for r in rows if r.kind == view]


def task_actions(runner, row, *, command, script, agent=None):
    """What the Tasks window can do with one task: re-sort it (its rank is the priority),
    clear or set aside its hold, or answer the owner's questions in an agent."""
    repo, name, task = runner.repo, runner.name, row.task
    if row.kind == 'closed':
        return []
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
        return 'not a repository' if not self.repo else 'needs ' + ', '.join(self.problems)


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
    out.problems += [name for name in REQUIRED if not (Path(out.repo) / name).is_dir()]
    branch = subprocess.run(['git', '-C', out.repo, 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                            capture_output=True, text=True, timeout=10).stdout.strip()
    out.branch = branch
    if branch not in ('main', 'master'):
        out.problems.append('main checked out' if branch else 'a branch (HEAD is detached)')
    elif not any(name in out.problems for name in REQUIRED) and uncommitted_planning(out.repo, branch):
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
        if problem == 'tasks':
            hints.append(f'Run `autowork tasks prepare {ready.repo}` to convert legacy planning; '
                         'with no accepted intent, plan the work with /docs_sync. No tasks are invented.')
        elif problem.startswith('task store preparation:'):
            hints.append(f'Run `autowork tasks prepare {ready.repo}` and resolve its outcome through /docs_sync.')
        elif problem.startswith('commit tasks/ on '):
            hints.append(problem)
        elif problem.startswith('main checked out') or problem.startswith('a branch'):
            hints.append(f'Check out main in {ready.repo}: the runner works only from the main branch checkout.')
        elif problem.startswith('its repository root'):
            hints.append(f'Choose the repository root {ready.repo} instead of a subdirectory.')
    return hints


def blockers_prompt(agent, repo):
    """The `/blockers` command in the agent's own spelling: Claude Code namespaces plugin
    skills (`/autowork:blockers`); Pi and Codex take `/blockers`."""
    name = os.path.basename(agent[0]) if agent else ''
    return f'/autowork:blockers {repo}' if name == 'claude' else f'/blockers {repo}'


def blockers_agent(env=os.environ):
    """The agent command for `/blockers`: AUTOWORK_AGENT, else claude, else pi."""
    configured = env.get('AUTOWORK_AGENT', '').split()
    if configured:
        return configured
    for name in ('claude', 'pi'):
        for folder in env.get('PATH', '').split(os.pathsep):
            if folder and os.access(os.path.join(folder, name), os.X_OK):
                return [name]
    return None
