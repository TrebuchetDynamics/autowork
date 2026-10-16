"""The fleet as `tx autowork` and its TUI see it. Standard library only.

Every runner on this machine, whichever way it runs (a tmux session from
`tx autowork`, a `pi-autowork@` systemd service, or both), with its health from the
runner's own status.json (``health.fleet``), its blockers grouped by kind, recent
log lines, and the exact command behind every action. Nothing here calls a model,
and nothing here changes a runner: actions only build the argv that `tx`,
`pi-autowork.sh` or `systemctl` already accept.
"""
from dataclasses import dataclass, field
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
    for row in health.fleet(state_root, now=now, service=lambda name: services.get(name, '-')):
        runner = found.get(row['name'])
        if runner is None:
            continue  # state left behind by a runner that no longer has a session or service
        if runner.repo and Path(runner.repo) != Path(row['repo']):
            continue
        runner.repo = runner.repo or row['repo']
        runner.state = row['state']
        runner.minutes = int((now - row['since']) // 60) if row.get('since') and row['state'] != 'not running' else None
        runner.running, runner.waiting = row.get('workers', 0), row.get('waiting', 0)
        runner.held = [(h.get('task', '?'), h.get('cause')) for h in row.get('held', [])]
        runner.roots = [r for r in row.get('roots', []) if r.get('kind') in health.NEEDS_PERSON]
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
            out.append(Action('a', 'start in tmux', [tx, 'autowork', repo], env={'TX_NO_ATTACH': '1'}))
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
