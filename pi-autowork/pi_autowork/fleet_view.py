"""The fleet as the `autowork` command and its TUI see it. Standard library only.

Every runner on this machine (a `pi-autowork@` systemd service), with its health from the
runner's own status.json (``health.fleet``), its blockers grouped by kind, recent
log lines, and the exact command behind every action. Nothing here calls a model,
and nothing here changes a runner: actions only build the argv that `autowork` or
`pi-autowork.sh` already accept.
"""
from dataclasses import dataclass, field
import datetime
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time

from pi_autowork import health, main_check, questions as owner_questions

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


def models(pi='pi', search=None, timeout=60):
    """provider/model IDs from `pi --list-models` (Pi's own catalog)."""
    argv = [pi, '--list-models'] + ([search] if search else [])
    found = []
    for line in _lines(argv, timeout=timeout):
        parts = line.split()
        if len(parts) >= 2 and parts[0] != 'provider' and re.fullmatch(r'[A-Za-z0-9._-]+', parts[0]):
            found.append(f'{parts[0]}/{parts[1]}')
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
    held: list = field(default_factory=list)
    roots: list = field(default_factory=list)
    state_dir: str = ''       # this runner's pi-autowork state directory
    lanes: list = field(default_factory=list)
    enabled: bool = False     # its service starts at login; paused also needs `autowork pause`'s marker
    model: str = ''
    fallback: str = ''
    questions: list = field(default_factory=list)  # the owner's open questions in BLOCKERS.md
    toolset: str = ''         # PI_AUTOWORK_TOOLSET: the service runs this checkout, not the Pi package
    waiting_groups: list = field(default_factory=list)  # why tasks wait, grouped (status.json)
    blocker: str = ''         # what keeps the runner itself from dispatching (status.json)
    max_workers: int | None = None
    restarting: str = ''      # 'onto <commit>' or 'service' while it stops and starts again
    gate: str = ''            # the latest resource-gate reason, when the last cycle was gated
    maintainer: dict = field(default_factory=dict)  # the DOCS-MAINTAINER's last run (TOOLSET-164-f1)
    main_check: dict = field(default_factory=dict)  # main's full offline check (TOOLSET-176-98)
    job: dict | None = None   # the runner's own Pi job running now (TOOLSET-177-d0)

    @property
    def color(self):
        return COLORS.get(self.state, 'red')

    @property
    def has_service(self):
        return bool(self.service)


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


def _actions(state_dir, task, now):
    """The task's Pi session actions, newest first: (text, seconds ago), from its transcript."""
    sessions = Path(state_dir) / 'sessions'
    try:
        files = [f for f in sessions.iterdir()
                 if re.search(rf'_pi-autowork-(verify-)?{re.escape(task)}-', f.name)]
    except OSError:
        return
    if not files:
        return
    for line in reversed(_tail(max(files, key=lambda f: f.stat().st_mtime), 262144)):
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
        age = None
        try:
            from datetime import datetime
            age = int(now - datetime.fromisoformat(event['timestamp'].replace('Z', '+00:00')).timestamp())
        except (KeyError, ValueError, TypeError):
            pass
        yield text, age


def _activity(state_dir, task, now):
    """The last thing the task's Pi session did: (text, seconds ago)."""
    for text, age in _actions(state_dir, task, now):
        return short(text, 90), age
    return '', None


def recent_actions(runner, task, n=10, now=None):
    """The task's last ``n`` actions, newest first, in plain words: [(text, seconds ago)]."""
    now = time.time() if now is None else now
    out = []
    for text, age in _actions(runner.state_dir, task, now) if runner.state_dir else ():
        out.append((doing_text(text), age))
        if len(out) >= n:
            break
    return out


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


QUIET_AFTER = 300


def doing(lane):
    """What a worker is doing now, in plain words."""
    if lane.phase == 'waiting for a check slot':
        return 'waiting for a check slot, ' + (lane.detail or '0 ahead')
    if lane.phase == 'waiting to integrate':
        return 'waiting to integrate: ' + (lane.detail or 'another integration first')
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
            or lane.phase in ('waiting to integrate', 'waiting for a check slot')):
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


def verdict(runner):
    """(sentence, style): whether this runner is stuck, and why, in one line."""
    count = len(runner.questions)
    asks = f"{count} question{'s' if count > 1 else ''}" if count else ''
    if runner.state == 'restarting':
        return (f"Restarting {runner.restarting}" if runner.restarting.startswith('onto') else 'Restarting', 'bold cyan')
    if runner.state == 'paused':
        return 'Paused — p resumes it', 'bold yellow'
    if runner.state == 'not running':
        return 'Not running — a starts its service', 'bold red'
    if runner.state == 'working' and runner.job and not runner.lanes:
        return f"Working — {job_text(runner.job)} ({duration(runner.minutes) or '0m'})", 'bold green'
    if runner.state == 'working':
        # Live workers, not every task in flight: 15 finished commits waiting to merge read as
        # "16 of 1 workers busy".
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
        if asks:
            text += f'; {asks} for you'
        return text, 'bold green'
    if runner.state == 'idle':
        return 'Idle — nothing left to run in Now/Next', 'bold green'
    if runner.state == health.HOST_WAIT:
        text = runner.waiting_groups[0]['label'] if runner.waiting_groups else health.HOST_WAIT
        return text, 'bold yellow'
    if runner.gate and not runner.lanes:
        return f'Host busy — {runner.gate}', 'bold yellow'
    if runner.questions:
        first = runner.questions[0]
        return (f'Waiting on you — {asks}, easiest {first.id} (unblocks {first.unblocks}): {first.needs}',
                'bold yellow')
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
    if runner.held:
        task, cause = (blocking(runner.held) or runner.held)[0]
        if cause in WAIT_CAUSES:
            return f"Waiting — {task}: {health.CAUSES.get(cause, cause)}", 'bold yellow'
        asked = any(q.id == task for q in runner.questions)
        return f'Blocker — {task}: {blocker_detail(cause, asked)}', 'bold yellow'
    return head, 'bold yellow'


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
WAIT_PHASES = {'implemented': 'Implemented', 'waiting to integrate': 'Merge turn',
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


def task_counts(runner):
    """(active, mergeable, waiting, blocker, total) for a runner."""
    heads = [status(lane)[0] for lane in runner.lanes]
    active = heads.count(ACTIVE) if runner.lanes else runner.running
    mergeable = heads.count(MERGEABLE)
    blocker = len(blocking(runner.held))
    waiting = heads.count(WAITING) + runner.waiting + len(runner.held) - blocker
    return active, mergeable, waiting, blocker, active + mergeable + waiting + blocker


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
    """What would move this runner, in a few words: the owner's questions, else its first blocker."""
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
    return ''


TASK_LINE = re.compile(r'^\[(\d\d:\d\d)\] (\S+): (\w+)\b')
# systemd's own lines about the unit, and the runner's start banner (its settings are in the detail).
UNIT_LINE = re.compile(r'^(Starting|Started|Stopping|Stopped) pi-autowork@|^pi-autowork@\S+: ')
BANNER = re.compile(r'^(PI AUTOWORK$|Repository: |Toolset: |Engine: |Primary: |Fallback: |Budget: |Mode: )')
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


def _lines(argv, timeout=10, *, strict=False):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
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


def collect(state_root, env_dir, *, systemctl='systemctl', now=None, strict=False):
    """Every runner: pi-autowork@ services and their runner state, merged by name."""
    now = time.time() if now is None else now
    found = {}

    def get(name):
        return found.setdefault(name, Runner(name=name))

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
    for name, sub in services.items():
        runner = get(name)
        runner.service = sub
        runner.mode = 'service'
        settings = read_env(Path(env_dir) / f'{name}.env')
        runner.repo = runner.repo or settings.get('PI_AUTOWORK_REPO', '').strip()
        runner.model = settings.get('PI_AUTOWORK_PRIMARY') or DEFAULT_MODEL
        runner.fallback = settings.get('PI_AUTOWORK_FALLBACK') or DEFAULT_FALLBACK
        runner.toolset = settings.get('PI_AUTOWORK_TOOLSET', '').strip()
        runner.enabled = subprocess.run([systemctl, '--user', 'is-enabled', '--quiet', f'pi-autowork@{name}.service'],
                                        capture_output=True).returncode == 0
    folders = {}
    for folder in Path(state_root).glob('*/'):
        for record in ('runner.json', 'status.json'):
            try:
                repo = json.loads((folder / record).read_text()).get('repo')
            except (OSError, ValueError, AttributeError):
                continue
            if repo:
                folders.setdefault(repo, str(folder))
    for row in health.fleet(state_root, now=now, service=lambda name: services.get(name, '-')):
        runner = found.get(row['name'])
        if runner is None:
            continue  # state left behind by a runner whose service was removed
        if runner.repo and Path(runner.repo) != Path(row['repo']):
            continue
        runner.repo = runner.repo or row['repo']
        runner.state_dir = folders.get(row['repo'], '')
        runner.state = row['state']
        runner.minutes = int((now - row['since']) // 60) if row.get('since') and row['state'] != 'not running' else None
        runner.running, runner.waiting = row.get('workers', 0), row.get('waiting', 0)
        runner.held = [(h.get('task', '?'), h.get('cause')) for h in row.get('held', [])]
        runner.roots = [r for r in row.get('roots', []) if r.get('kind') in health.NEEDS_PERSON]
        runner.waiting_groups = row.get('waiting_groups') or []
        runner.blocker = row.get('blocker') or ''
        runner.max_workers = row.get('max_workers')
        runner.maintainer = row.get('maintainer') or {}
        runner.main_check = row.get('main_check') or {}
        runner.job = row.get('job')
        if runner.job and runner.job.get('started'):
            runner.minutes = int((now - runner.job['started']) // 60)
    for runner in found.values():
        runner.lanes = lanes(runner, now)
        runner.restarting, runner.gate = recent_events(runner, now)
        # The runner refreshes its status between cycles, not during a long verification it
        # runs itself: a worker or reviewer acting now means it works, whatever the status says.
        if runner.state in ('blocked', 'stalled', 'not cycling') and any(
                lane.activity_age is not None and lane.activity_age < health.STALE_AFTER for lane in runner.lanes):
            runner.state, runner.minutes = 'working', None
        runner.questions = read_questions(runner.repo, runner.state_dir) if runner.repo else []
        if runner.has_service and runner.service in RESTARTING:
            runner.restarting = runner.restarting or 'service'
        if runner.has_service and runner.service not in ('running', 'start', 'reload'):
            if not runner.enabled and paused_marker(env_dir, runner.name).exists():
                runner.state, runner.minutes = 'paused', None  # paused on purpose: `autowork resume`
            elif runner.restarting:
                runner.state, runner.minutes = 'restarting', None  # its own update, not a stop
            else:
                runner.state, runner.minutes = 'not running', None  # its records may say otherwise
    return sorted(found.values(), key=lambda r: r.name)


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
    """One open task of a runner's TODO.md, in its priority order."""
    task: str
    short: str          # `Short:` (at most 40 characters), else the title cut to 40
    section: str        # Now, Next or Needs decision
    state: str          # in plain words: implementing, implemented, held, waiting, ready, ...
    kind: str           # working, held, waiting, ready: what a TASK_VIEWS filter matches
    why: str = ''       # the hold or wait reason, or the owner's question
    question: bool = False


def goals_module():
    """docs-sync's goals.py from this toolset: TODO.md is parsed the way the runner parses it."""
    scripts = str(Path(__file__).resolve().parents[2] / 'skills' / 'docs-sync' / 'scripts')
    if scripts not in sys.path:
        sys.path.insert(0, scripts)
    import goals
    return goals


def task_rows(runner):
    """Every open task in ``runner``'s TODO.md, in its order, with what the runner says about it."""
    try:
        text = Path(runner.repo, 'TODO.md').read_text()
    except (OSError, TypeError, ValueError):
        return []
    try:
        states = json.loads(Path(runner.state_dir, 'status.json').read_text()).get('tasks') or []
    except (OSError, TypeError, ValueError, AttributeError):
        states = []
    engine = {row[0]: row for row in states if isinstance(row, list) and len(row) == 4}
    if not engine:  # a runner from before the per-task list: its groups name up to 20 tasks each
        engine.update((t, (t, 'waiting', '', g['label'])) for g in runner.waiting_groups for t in g.get('tasks') or [])
        engine.update((t, (t, 'held', cause or '', '')) for t, cause in runner.held)
    lanes = {lane.task: lane for lane in runner.lanes}
    asked = {q.id: q for q in runner.questions}
    goals = goals_module()
    rows = []
    for task, entries in goals.task_bodies(text).items():
        block, mark, section = entries[0]
        if mark != ' ' or section not in ('Now', 'Next', 'Needs decision'):
            continue
        title = ' '.join(block.split('\n', 1)[0].strip().lstrip('—–-:').split())
        short = ' '.join((goals.task_fields(block).get('Short') or '').split()) or title
        _, state, cause, why = engine.get(task, (task, '', '', ''))
        question = asked.get(task)
        if task in lanes or state in IN_FLIGHT:
            words, kind = ' · '.join(status(lanes.get(task) or Lane(task, PHASES[state]))), 'working'
        elif state == 'held' and cause in WAIT_CAUSES:
            words, kind = f'{WAITING} · ' + blocker_detail(cause).split(' · ')[0], 'held'
        elif state == 'held':
            words, kind = f'{BLOCKER} · ' + blocker_detail(cause, bool(question)), 'held'
        elif state in ('waiting', 'pending'):
            words, kind = WAITING, 'waiting'
        elif section == 'Needs decision':
            words, kind = f'{WAITING} · Needs decision', 'waiting'
        else:
            words, kind = f'{WAITING} · Ready' if state in ('', 'ready') else state, 'ready'
        short = short if len(short) <= 40 else short[:39].rstrip() + '…'
        rows.append(TaskRow(task=task, short=short, section=section, state=words, kind=kind,
                            why='you: ' + question.needs if question else why, question=bool(question)))
    return rows


def task_entry(runner, task):
    """``task``'s whole TODO.md entry, as written."""
    try:
        text = Path(runner.repo, 'TODO.md').read_text()
    except (OSError, TypeError, ValueError):
        return ''
    block = next((b for b in goals_module().task_blocks(text) if b['id'] == task), None)
    return block['core'] if block else ''


def open_goals(runner):
    """(id, title) of the goals in ``runner``'s goals.json not yet met: a new task's choices."""
    try:
        data = json.loads(Path(runner.repo, 'goals.json').read_text())
        return [(g['id'], g.get('title') or '') for g in data.get('goals') or [] if g.get('status') != 'met']
    except (OSError, TypeError, ValueError, KeyError, AttributeError):
        return []


def task_view(rows, view):
    """The rows a TASK_VIEWS filter shows."""
    if view == 'all':
        return rows
    if view == 'questions':
        return [r for r in rows if r.question]
    return [r for r in rows if r.kind == view]


def task_actions(runner, row, *, command, script, agent=None):
    """What the Tasks window can do with one task: re-sort it (TODO.md order is the priority),
    clear or set aside its hold, or answer the owner's questions in an agent."""
    repo, name, task = runner.repo, runner.name, row.task
    out = [Action('u', 'Up', [command, 'move', task, 'up', name]),
           Action('d', 'Down', [command, 'move', task, 'down', name]),
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
    TODO.md entry. Questions about no task (FULL-CHECK, LEDGER) have none: an agent answers them."""
    task, name = question.id, runner.name
    if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', task) or task in ('FULL-CHECK', 'LEDGER'):
        return []
    day = today or datetime.date.today()
    out = []
    if question.kind == 'claim':
        until = day + datetime.timedelta(days=7)
        out.append(Answer('o', 'Open', 'no one is working on it: Status: open, so the runner runs it',
                          [command, 'field', task, 'Status', 'open', name]))
        out.append(Answer('h', 'Held', f'someone is: Held by: the owner; until {until}',
                          [command, 'field', task, 'Held by', f'the owner; until {until}', name]))
    fingerprint = re.search(r'Blocker resolution: (\S+?);', question.answer or '')
    if question.kind == 'quick_hold' and fingerprint:
        out.append(Answer('r', 'Resolve', 'name the producer task or the decision that unblocks it',
                          [command, 'field', task, 'Blocker resolution', f'{fingerprint[1]}; {{text}}', name], True))
    out.append(Answer('w', 'Write', 'your decision, as a dated Owner decision line in its entry',
                      [command, 'field', task, 'Owner decision', f'{day}: {{text}}', name], True))
    out.append(Answer('d', 'Defer', 'move it to Needs decision, with your reason as its Owner decision',
                      [command, 'place', task, 'Needs decision', name, '--decision', f'{day}: deferred: {{text}}'], True))
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


REQUIRED = ('TODO.md', 'goals.json')


def uncommitted_planning(repo, base, required=REQUIRED):
    """Planning inputs absent from the base tree, even if they exist in the checkout."""
    return [name for name in required if subprocess.run(
        ['git', '-C', str(repo), 'cat-file', '-e', f'{base}:{name}'],
        capture_output=True, timeout=10).returncode]


def readiness(path):
    """A repository root with TODO.md and goals.json committed on its main branch is ready."""
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
    out.problems += [name for name in REQUIRED if not (Path(out.repo) / name).is_file()]
    branch = subprocess.run(['git', '-C', out.repo, 'symbolic-ref', '--quiet', '--short', 'HEAD'],
                            capture_output=True, text=True, timeout=10).stdout.strip()
    out.branch = branch
    if branch not in ('main', 'master'):
        out.problems.append('main checked out' if branch else 'a branch (HEAD is detached)')
    elif not any(name in out.problems for name in REQUIRED) and uncommitted_planning(out.repo, branch):
        out.problems.append(f'commit TODO.md and goals.json on {branch} first')
    out.ready = not out.problems
    return out


def how_to_fix(ready):
    """One line per missing piece, for the TUI and `autowork start`."""
    hints = []
    for problem in ready.problems:
        if problem == 'TODO.md':
            hints.append('Create TODO.md: plan the work with /plan-with-me or Docs Sync in any host.')
        elif problem == 'goals.json':
            hints.append('Create goals.json from TODO.md: /docs-sync, or '
                         'python3 <toolset>/skills/docs-sync/scripts/goals.py init <repo> --intent JSON.')
        elif problem.startswith('commit TODO.md and goals.json on '):
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
