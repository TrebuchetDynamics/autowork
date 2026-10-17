"""The fleet as the `autowork` command and its TUI see it. Standard library only.

Every runner on this machine (a `pi-autowork@` systemd service), with its health from the
runner's own status.json (``health.fleet``), its blockers grouped by kind, recent
log lines, and the exact command behind every action. Nothing here calls a model,
and nothing here changes a runner: actions only build the argv that `autowork` or
`pi-autowork.sh` already accept.
"""
from dataclasses import dataclass, field
import json
import os
from pathlib import Path
import re
import subprocess
import time

from pi_autowork import health, questions as owner_questions

KINDS = {'runner': 'runner', 'cycle': 'dependency cycle', 'held': 'held', 'contract': 'not runnable',
         'claim': 'claimed elsewhere', 'outside': 'outside Now/Next'}
CAUSES = {'blocker': 'blocker', 'scope': 'outside Touches', 'scope_request': 'needs files', 'overlap': 'overlap',
          'report': 'bad report', 'conflict': 'conflict', 'validation': 'validation', 'crash': 'crashed', 'empty': 'no result',
          'launch': 'launch failed', 'contract_changed': 'entry changed', 'moved': 'main moved'}
ORDER = ['runner', 'cycle', 'held', 'contract', 'claim', 'outside']
COLORS = {'working': 'green', 'idle': 'green', 'blocked': 'yellow', 'paused': 'yellow', 'starting': 'yellow'}
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
    return found


def needs(runner):
    """What would move this runner, in a few words: the owner's questions, else its first blocker."""
    if runner.state in ('paused', 'not running'):
        return 'start it' if runner.state == 'not running' else 'resume it'
    if runner.questions:
        first = runner.questions[0]
        count = len(runner.questions)
        return f"{count} question{'s' if count > 1 else ''}, easiest {first.id}"
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
               'verifying': 'cyan', 'implemented': 'cyan', 'resuming': 'cyan'}


def log_lines(text):
    """[(line, style)]: the journal as a person reads it. Per-task `pending` lines (the
    `No task can start now` line covers them), systemd's unit lines, the start banner and
    the results a restart printed again are dropped; a start or stop is one rule line."""
    out, last = [], {}
    for line in text.splitlines():
        if UNIT_LINE.match(line) or BANNER.match(line) or not line.strip():
            continue
        if ' Started (PID ' in line:
            out.append((f'{line[:7]} ── started ──', 'bold'))
            continue
        if '] Stopping: ' in line:
            out.append((f'{line[:7]} ── stopping: workers pause and resume on the next start ──', 'bold'))
            continue
        if '] Stopped. ' in line:
            out.append((f'{line[:7]} ── stopped ──', 'bold'))
            continue
        task = TASK_LINE.match(line)
        if task:
            _, name, word = task.groups()
            if word == 'pending' or last.get(name) == word:
                continue
            last[name] = word
            out.append((line, WORD_STYLES.get(word, '')))
            continue
        if 'Questions for the owner' in line or 'No task can start' in line or 'Merge pending' in line:
            out.append((line, 'yellow'))
        elif 'needs attention' in line or 'failed' in line.lower():
            out.append((line, 'red'))
        else:
            out.append((line, ''))
    return out


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


def _lines(argv, timeout=10):
    try:
        out = subprocess.run(argv, capture_output=True, text=True, timeout=timeout)
    except (OSError, subprocess.SubprocessError):
        return []
    return out.stdout.splitlines() if out.returncode == 0 else []


def paused_marker(env_dir, name):
    """Written by `autowork pause`, removed by `autowork resume` and `autowork start`: a stopped
    service is paused only when someone paused it; otherwise it is simply not running."""
    return Path(env_dir) / f'{name}.paused'


def collect(state_root, env_dir, *, systemctl='systemctl', now=None):
    """Every runner: pi-autowork@ services and their runner state, merged by name."""
    now = time.time() if now is None else now
    found = {}

    def get(name):
        return found.setdefault(name, Runner(name=name))

    services = {}
    for line in _lines([systemctl, '--user', 'list-units', 'pi-autowork@*', '--all', '--plain', '--no-legend']):
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
    for runner in found.values():
        runner.lanes = lanes(runner, now)
        # The runner refreshes its status between cycles, not during a long verification it
        # runs itself: a worker or reviewer acting now means it works, whatever the status says.
        if runner.state in ('blocked', 'stalled', 'not cycling') and any(
                lane.activity_age is not None and lane.activity_age < health.STALE_AFTER for lane in runner.lanes):
            runner.state, runner.minutes = 'working', None
        runner.questions = read_questions(runner.repo, runner.state_dir) if runner.repo else []
        if runner.has_service and runner.service not in ('running', 'start', 'reload'):
            if not runner.enabled and paused_marker(env_dir, runner.name).exists():
                runner.state, runner.minutes = 'paused', None  # paused on purpose: `autowork resume`
            else:
                runner.state, runner.minutes = 'not running', None  # its records may say otherwise
    return sorted(found.values(), key=lambda r: r.name)


def summary(runners):
    counts = {}
    for runner in runners:
        counts[runner.state] = counts.get(runner.state, 0) + 1
    order = ['working', 'idle', 'paused', 'blocked', 'stalled', 'not running', 'not cycling', 'starting', 'unknown']
    return [(state, counts[state]) for state in order + sorted(set(counts) - set(order)) if state in counts]


def logs(runner, *, lines=200, journalctl='journalctl'):
    """Recent output: the service journal."""
    if not runner.has_service:
        return ''
    return '\n'.join(_lines([journalctl, '--user', '-u', f'pi-autowork@{runner.name}.service', '-n', str(lines),
                             '--no-pager', '-o', 'cat'], timeout=20))


@dataclass
class Action:
    key: str
    label: str
    argv: list
    interactive: bool = False   # takes over the terminal (attach, an agent session)
    confirm: str = ''           # a question to ask first, '' for none
    env: dict = field(default_factory=dict)


def actions(runner, *, command, script, agent=None, task=None):
    """What the owner can do to this runner now, as `autowork` commands (or the runner script)."""
    repo, name = runner.repo, runner.name
    out = [Action('enter', 'log', [], interactive=True)]  # the TUI's own full-screen log view
    running = runner.service in ('running', 'start', 'reload')
    if runner.has_service and running:
        out.append(Action('p', 'pause', [command, 'pause', name],
                          confirm=f'Pause {name}? Its service stops and stays off until resumed; '
                                  'workers resume on the same attempt.'))
    elif runner.has_service and runner.state == 'paused':
        out.append(Action('p', 'resume', [command, 'resume', name]))
    if runner.has_service:
        out.append(Action('m', 'model', [command, 'model', name]))       # the TUI picks the model
        out.append(Action('M', 'fallback model', [command, 'model', name, '--fallback']))
    if running:
        out.append(Action('s', 'stop', [command, 'stop', name],
                          confirm=f'Stop {name}? Workers pause and resume on the same attempt at the next start.'))
        if runner.has_service:
            out.append(Action('R', 'restart', [command, 'restart', name],
                              confirm=f'Restart {name}? Workers pause and resume on the same attempt.'))
    elif repo:
        out.append(Action('a', 'start service', [command, 'start', repo]))
    if repo and runner.has_service and not running:
        out.append(Action('u', 'remove service', [command, 'remove', name],
                          confirm=f'Remove pi-autowork@{name}? Its state and worktrees stay.'))
    if repo and task:
        out.append(Action('x', f'set aside {task}', [script, '--repo', repo, '--set-aside', task],
                          confirm=f'Set aside {task}? Its work stays on -set-aside-N branches and it runs fresh.'))
    if repo and agent:
        out.append(Action('b', 'answer blockers', [command, 'blockers', repo], interactive=True))
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


def readiness(path):
    """A repository root with TODO.md and goals.json on its main branch is ready."""
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
