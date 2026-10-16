"""The fleet as `tx autowork` and its TUI see it. Standard library only.

Every runner on this machine, whichever way it runs (a tmux session from
`tx autowork`, a `pi-autowork@` systemd service, or both), with its health from the
runner's own status.json (``health.fleet``), its blockers grouped by kind, recent
log lines, and the exact command behind every action. Nothing here calls a model,
and nothing here changes a runner: actions only build the argv that `tx`,
`pi-autowork.sh` or `systemctl` already accept.
"""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import time

from pi_autowork import health

PREFIX = 'pi-autowork-'
KINDS = {'runner': 'runner', 'cycle': 'dependency cycle', 'held': 'held', 'contract': 'entry changed',
         'claim': 'claimed elsewhere', 'outside': 'outside Now/Next'}
CAUSES = {'blocker': 'blocker', 'scope': 'outside Touches', 'scope_request': 'needs files', 'overlap': 'overlap',
          'report': 'bad report', 'conflict': 'conflict', 'validation': 'validation', 'crash': 'crashed',
          'launch': 'launch failed', 'contract_changed': 'entry changed', 'moved': 'main moved'}
ORDER = ['runner', 'cycle', 'held', 'contract', 'claim', 'outside']
COLORS = {'working': 'green', 'idle': 'green', 'blocked': 'yellow', 'paused': 'yellow', 'starting': 'yellow'}


@dataclass
class Runner:
    name: str
    repo: str = ''
    mode: str = ''            # tmux, service, tmux+service, or '' when only state is left
    service: str = ''         # systemd sub-state, '' when there is no unit
    view: bool = False        # a tmux session that follows the service journal
    state: str = 'unknown'
    minutes: int | None = None
    running: int = 0
    waiting: int = 0
    held: list = field(default_factory=list)
    roots: list = field(default_factory=list)
    state_dir: str = ''       # this runner's pi-autowork state directory
    lanes: list = field(default_factory=list)

    @property
    def session(self):
        return session_name(self.name)

    @property
    def color(self):
        return COLORS.get(self.state, 'red')

    @property
    def runs_in_tmux(self):
        return 'tmux' in self.mode

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


PHASE_WORDS = ('waiting to integrate', 'set aside', 'verifying', 'implemented', 'integrating', 'integrated',
               'running', 'pending', 'done', 'failed', 'held', 'closed')


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


def _activity(state_dir, task, now):
    """The last thing the task's Pi session did: (text, seconds ago), from its transcript."""
    sessions = Path(state_dir) / 'sessions'
    try:
        files = [f for f in sessions.iterdir()
                 if re.search(rf'_pi-autowork-(verify-)?{re.escape(task)}-', f.name)]
    except OSError:
        return '', None
    if not files:
        return '', None
    for line in reversed(_tail(max(files, key=lambda f: f.stat().st_mtime), 131072)):
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
        return short(text, 90), age
    return '', None


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
        started = slot.get('started_at')
        activity, age = _activity(runner.state_dir, task, now) if runner.state_dir else ('', None)
        out.append(Lane(task=task, phase=phase, detail=detail, attempt=slot.get('attempt', 1),
                        minutes=int((now - started) // 60) if started else None, activity=activity, activity_age=age))
    return out


def ago(seconds):
    if seconds is None:
        return ''
    if seconds < 90:
        return f'{seconds}s ago'
    return duration(seconds // 60) + ' ago'


def session_name(name):
    return PREFIX + name.replace('.', '_').replace(':', '_')


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


def _lines(argv, timeout=10):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return []
    return out.stdout.splitlines() if out.returncode == 0 else []


def collect(state_root, env_dir, *, tmux='tmux', systemctl='systemctl', now=None):
    """Every runner: tmux sessions, pi-autowork@ services and runner state, merged by name."""
    now = time.time() if now is None else now
    found = {}

    def get(name):
        return found.setdefault(name, Runner(name=name))

    for line in _lines([tmux, 'list-sessions', '-F', '#{session_name}\t#{@pi_autowork_repo}\t#{@pi_autowork_mode}']):
        name, _, rest = line.partition('\t')
        repo, _, kind = rest.partition('\t')
        if not name.startswith(PREFIX):
            continue
        runner = get(name[len(PREFIX):])
        runner.repo = runner.repo or repo
        if kind == 'journal':
            runner.view = True
        else:
            runner.mode = 'tmux'
    services = {}
    for line in _lines([systemctl, '--user', 'list-units', 'pi-autowork@*', '--all', '--plain', '--no-legend']):
        parts = line.split()
        if len(parts) >= 4 and parts[0].startswith('pi-autowork@') and parts[0].endswith('.service'):
            services[parts[0][len('pi-autowork@'):-len('.service')]] = parts[3]
    for name, sub in services.items():
        runner = get(name)
        runner.service = sub
        runner.mode = 'tmux+service' if runner.mode == 'tmux' else 'service'
        env = Path(env_dir) / f'{name}.env'
        if not runner.repo and env.is_file():
            match = re.search(r'(?m)^PI_AUTOWORK_REPO=(.*)$', env.read_text())
            runner.repo = match.group(1).strip() if match else ''
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
            continue  # state left behind by a runner that no longer has a session or service
        if runner.repo and Path(runner.repo) != Path(row['repo']):
            continue
        runner.repo = runner.repo or row['repo']
        runner.state_dir = folders.get(row['repo'], '')
        runner.state = row['state']
        runner.minutes = int((now - row['since']) // 60) if row.get('since') and row['state'] != 'not running' else None
        runner.running, runner.waiting = row.get('workers', 0), row.get('waiting', 0)
        runner.held = [(h.get('task', '?'), h.get('cause')) for h in row.get('held', [])]
        runner.roots = [r for r in row.get('roots', []) if r.get('kind') in health.NEEDS_PERSON]
    for runner in found.values():
        runner.lanes = lanes(runner, now)
    return sorted(found.values(), key=lambda r: r.name)


def summary(runners):
    counts = {}
    for runner in runners:
        counts[runner.state] = counts.get(runner.state, 0) + 1
    order = ['working', 'idle', 'paused', 'blocked', 'stalled', 'not running', 'not cycling', 'starting', 'unknown']
    return [(state, counts[state]) for state in order + sorted(set(counts) - set(order)) if state in counts]


def logs(runner, *, lines=200, tmux='tmux', journalctl='journalctl'):
    """Recent output: the tmux pane of a tmux runner, else the service journal."""
    if runner.runs_in_tmux:
        return '\n'.join(_lines([tmux, 'capture-pane', '-p', '-J', '-S', f'-{lines}', '-t', f'={runner.session}:']))
    if runner.has_service:
        return '\n'.join(_lines([journalctl, '--user', '-u', f'pi-autowork@{runner.name}.service', '-n', str(lines),
                                 '--no-pager', '-o', 'cat'], timeout=20))
    return ''


@dataclass
class Action:
    key: str
    label: str
    argv: list
    interactive: bool = False   # takes over the terminal (attach, an agent session)
    confirm: str = ''           # a question to ask first, '' for none
    env: dict = field(default_factory=dict)


def actions(runner, *, tx, script, systemctl='systemctl', agent=None, task=None):
    """What the owner can do to this runner now, as the commands that already do it."""
    repo = runner.repo
    out = [Action('enter', 'open session', [tx, runner.session], interactive=True)]
    if runner.runs_in_tmux:
        out.append(Action('s', 'stop', [tx, 'autowork', 'stop', runner.name],
                          confirm=f'Stop the tmux runner for {runner.name}? Workers pause and resume on the next start.'))
    elif runner.has_service and runner.service in ('running', 'start', 'reload'):
        out.append(Action('s', 'stop service', [systemctl, '--user', 'stop', f'pi-autowork@{runner.name}.service'],
                          confirm=f'Stop pi-autowork@{runner.name}? Workers pause and resume on the next start.'))
    elif repo:
        if runner.has_service:
            out.append(Action('a', 'start service', [systemctl, '--user', 'start', f'pi-autowork@{runner.name}.service']))
        else:
            out.append(Action('a', 'start in tmux', [tx, 'autowork', 'start', repo], env={'TX_NO_ATTACH': '1'}))
    if repo and not runner.has_service:
        out.append(Action('i', 'install service', [script, '--install-service', '--repo', repo],
                          confirm=f'Install and start pi-autowork@{runner.name} for {repo}?'))
    if repo and runner.has_service:
        out.append(Action('u', 'remove service', [script, '--remove-service', '--repo', repo],
                          confirm=f'Stop and remove pi-autowork@{runner.name}? State and worktrees stay.'))
    if repo and task:
        out.append(Action('x', f'set aside {task}', [script, '--repo', repo, '--set-aside', task],
                          confirm=f'Set aside {task}? Its work stays on -set-aside-N branches and it runs fresh.'))
    if repo and agent:
        out.append(Action('b', 'answer blockers', [*agent, f'/autowork blockers {repo}'], interactive=True))
    return out


def blockers_agent(env=os.environ):
    """The agent command for `/autowork blockers`: TX_AUTOWORK_AGENT, else claude, else pi."""
    configured = env.get('TX_AUTOWORK_AGENT', '').split()
    if configured:
        return configured
    for name in ('claude', 'pi'):
        for folder in env.get('PATH', '').split(os.pathsep):
            if folder and os.access(os.path.join(folder, name), os.X_OK):
                return [name]
    return None
