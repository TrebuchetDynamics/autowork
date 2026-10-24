"""Persistent planning console backend; standard library only.

Planning sessions are private, separate from runner state, and survive UI navigation.
Only explicit apply() commits/lands locally. Nothing starts a runner or publishes.
Read-only Pi tools are NOT a filesystem sandbox: they can read other accessible
files. Existing global provider configuration (including executable credential
resolvers) remains trusted and untouched; use an appropriately restricted account.
"""
from contextlib import contextmanager
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import threading
import time
import uuid

from . import planning_proposals as proposals
from .planning_proposals import PlanningError
from .planning_rpc import RPC, RPCError, Cancelled, private_dir, private_open
from . import task_commands

BUNDLE = Path(__file__).resolve().parents[2]
SKILLS = BUNDLE / 'adapters/skills'
POLICY = '''You are the Autowork planning console, never an implementation agent.
Read the repository instructions and existing plans, tasks, source and tests with
read/grep/find/ls only. Read the loaded planning skill and Docs Sync guidance and
its references. Those documents' shell/write/commit/prepare steps are NOT available
in this console: never execute commands, implement, dispatch, close tasks, invent
verification or owner/live authority, change settings, start/unpause services or push.
Reuse existing IDs/decisions and distinguish accepted intent from proposals.
The host alone validates/stages proposals and the user separately applies them.
When ready, return COMPLETE UTF-8 file contents in exactly one fenced block:
```autowork-plan
{"files":{"tasks/items/SAFE-ID.md":"complete contents", "docs/plans/name.md":"complete contents"}}
```
Only tasks/items/<ID>.md, tasks/goals/<ID>.md, docs/plans/**/*.md and
docs/specs/**/*.md are accepted. No deletions, credentials, evidence, symlinks or
executable files. Preserve closure, owner attestations, holds and live permissions.
Use schema-1 TOML task records (read the bundled pi-autowork/task-store.md).
At most 64 files, 256 KiB per file, 2 MiB total. Ordinary chat, including slash
commands inside the user message, is literal conversation, not a command to invoke.
Investigate mode reports source-backed findings without proposing file contents.
Empty initial objective means autonomous evidence-backed discovery, not a request
for the user to supply a goal. Planning stops before implementation.
'''


def _atomic(path, value):
    if path.is_symlink():
        raise PlanningError('refuse symlinked planning state')
    fd, temp = tempfile.mkstemp(prefix='.state-', dir=path.parent)
    try:
        with os.fdopen(fd, 'wb') as out:
            out.write(json.dumps(value, ensure_ascii=False).encode() + b'\n')
            out.flush()
            os.fsync(out.fileno())
        os.replace(temp, path)
    finally:
        Path(temp).unlink(missing_ok=True)


def _read(path):
    if path.is_symlink():
        raise PlanningError('refuse symlinked planning state')
    try:
        return json.loads(path.read_bytes())
    except (OSError, ValueError) as exc:
        raise PlanningError('planning state is missing or invalid: ' + path.name) from exc


def _redact(text):
    return proposals.SECRET.sub('[redacted]', text)


def _literal(text):
    return 'Literal user message (do not expand slash commands):\n' + text


def _blocker_context(meta):
    if not meta.get('task'):
        return ''
    text = proposals.original(meta, 'BLOCKERS.md') or ''
    marker = re.compile(r'(?<![A-Za-z0-9_-])' + re.escape(meta['task']) + r'(?![A-Za-z0-9_-])')
    sections = [part for part in re.split(r'(?=^#{1,6} )', text, flags=re.M) if marker.search(part)]
    excerpt = '\n'.join(sections)[:8192]
    return ('\nRead tasks/items/' + meta['task'] + '.md and BLOCKERS.md for source context.\n'
            + ('Pinned task blocker excerpt (may be truncated), base ' + meta['base'] + ':\n'
               + _redact(excerpt) if excerpt else 'No matching pinned BLOCKERS.md section.'))


class Planner:
    def __init__(self, repo, state_root=None, pi='pi', model=None):
        self.repo = proposals.canonical(Path(repo).resolve())
        self.pi, self.model = str(pi), model
        common = proposals.git(self.repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
        self.identity = str(Path(common).resolve())
        base = Path(state_root) if state_root is not None else Path(
            os.environ.get('XDG_STATE_HOME', str(Path.home() / '.local/state'))) / 'pi-autowork/planning'
        try:
            self.state = private_dir(private_dir(base) / hashlib.sha256(self.identity.encode()).hexdigest()[:24])
        except RPCError as exc:
            raise PlanningError(str(exc)) from exc
        self._active = {}
        self._active_lock = threading.Lock()

    def _directory(self, ident):
        if not isinstance(ident, str) or not re.fullmatch(r'[a-f0-9]{32}', ident):
            raise PlanningError('invalid planning session id')
        path = self.state / ident
        if path.is_symlink() or not path.is_dir():
            raise PlanningError('unknown planning session')
        return path

    def _save(self, meta):
        _atomic(self._directory(meta['id']) / 'session.json', meta)

    @contextmanager
    def _locked(self, ident):
        with proposals.exclusive(self._directory(ident) / 'writer.lock'):
            yield self.get(ident)

    def create(self, objective='', task=None, mode='plan'):
        if mode not in ('plan', 'discuss', 'investigate'):
            raise PlanningError('planning mode must be plan, discuss or investigate')
        if not isinstance(objective, str) or task is not None and not isinstance(task, str):
            raise PlanningError('objective and task must be text')
        ident = uuid.uuid4().hex
        worktree = self.repo / '.worktrees' / ('planning-' + ident)
        if worktree.parent.is_symlink() or worktree.is_symlink():
            raise PlanningError('refuse symlinked planning worktree')
        if proposals.run_git(self.repo, 'check-ignore', '-q', '--', str(worktree), check=False).returncode != 0:
            raise PlanningError('canonical .worktrees/ must already be ignored')
        branch = proposals.git(self.repo, 'symbolic-ref', '--short', 'HEAD')
        base = proposals.git(self.repo, 'rev-parse', 'HEAD')
        if task:
            try:
                if task not in task_commands.TaskStore.at(self.repo, base).tasks:
                    raise PlanningError('unknown task: ' + task)
            except task_commands.StoreError as exc:
                raise PlanningError(str(exc)) from exc
        private_dir(self.state / ident)
        private_dir(self.state / ident / 'pi')
        meta = {'id': ident, 'repo': str(self.repo), 'identity': self.identity,
                'worktree': str(worktree), 'base': base, 'target_branch': branch,
                'branch': 'planning/' + ident, 'status': 'creating', 'task': task,
                'objective': objective, 'mode': mode, 'model': self.model,
                'created_at': time.time(), 'turns': 0}
        self._save(meta)
        try:
            proposals.git(self.repo, 'worktree', 'add', '-b', meta['branch'], str(worktree), base)
            worktree.chmod(0o700)
            meta['status'] = 'ready'
            self._save(meta)
        except (PlanningError, OSError):
            meta['status'] = 'error'
            self._save(meta)
            raise
        return meta

    def sessions(self):
        return sorted((self.get(p.name) for p in self.state.iterdir()
                       if p.is_dir() and re.fullmatch(r'[a-f0-9]{32}', p.name)),
                      key=lambda m: m['created_at'], reverse=True)

    def get(self, ident):
        meta = _read(self._directory(ident) / 'session.json')
        if (not isinstance(meta, dict) or meta.get('id') != ident or meta.get('repo') != str(self.repo)
                or meta.get('identity') != self.identity):
            raise PlanningError('planning session repository identity mismatch')
        expected = self.repo / '.worktrees' / ('planning-' + ident)
        if meta.get('worktree') != str(expected) or expected.is_symlink() or expected.parent.is_symlink():
            raise PlanningError('planning worktree identity mismatch')
        return meta

    def history(self, ident):
        path = self._directory(ident) / 'history.jsonl'
        if not path.exists():
            return []
        if path.is_symlink():
            raise PlanningError('refuse symlinked conversation history')
        try:
            return [json.loads(line) for line in path.read_bytes().split(b'\n') if line]
        except (OSError, ValueError) as exc:
            raise PlanningError('conversation history is unreadable') from exc

    def _history(self, ident, role, content):
        with private_open(self._directory(ident) / 'history.jsonl') as out:
            out.write(json.dumps({'role': role, 'content': content}, ensure_ascii=False).encode() + b'\n')
            out.flush()
            os.fsync(out.fileno())

    def _argv(self, meta):
        flags = ['--no-approve', '--no-extensions', '--no-mcp', '--no-skills',
                 '--no-prompt-templates', '--no-themes', '--no-context-files']
        try:
            version = subprocess.run([self.pi, '--version', '--offline', *flags], capture_output=True,
                                     text=True, timeout=10)
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise PlanningError('cannot inspect installed Pi version') from exc
        found = re.search(r'\b(\d+)\.(\d+)\.(\d+)\b', version.stdout)
        if version.returncode or not found or tuple(map(int, found.groups())) < (1, 3, 0):
            raise PlanningError('Pi 1.3 or newer with the documented RPC protocol is required')
        argv = [self.pi, '--mode', 'rpc', *flags, '--tools', 'read,grep,find,ls',
                '--session-dir', str(self._directory(meta['id']) / 'pi'), '--session-id', meta['id'],
                '--append-system-prompt', POLICY + '\nBundled schema: ' + str(BUNDLE / 'pi-autowork/task-store.md')]
        for name in ('plan-for-me', 'plan-with-me', 'docs-sync'):
            path = SKILLS / name / 'SKILL.md'
            if path.is_file():
                argv.extend(['--skill', str(path)])
        if meta.get('model'):
            argv.extend(['--model', meta['model']])
        return argv

    def send(self, ident, message='', on_event=None, cancel=None):
        if not isinstance(message, str):
            raise PlanningError('planning message must be text')
        with self._locked(ident) as meta:
            if meta['status'] == 'applied':
                raise PlanningError('applied session is read-only; create a new session')
            client = None
            failed = True
            user_text = message or (meta['objective'] if not meta['turns'] else '')
            if not user_text and not meta['turns']:
                user_text = ('Investigate and refine the selected task and its unresolved decisions.' if meta['task'] else
                             'Discover evidence-backed improvements autonomously and plan the next executable frontier.')
            if not user_text:
                raise PlanningError('a follow-up message is required')
            self._history(ident, 'user', user_text)
            meta['status'] = 'running'
            meta.pop('last_error', None)
            self._save(meta)
            def event(record):
                # Never forward raw tool outputs/provider diagnostic messages. The
                # private JSONL retains them; a console needs text and tool names.
                if on_event is None:
                    return
                kind = record.get('type')
                if kind == 'message_update':
                    update = record.get('assistantMessageEvent') or {}
                    if update.get('type') == 'text_delta':
                        on_event({'type': kind, 'assistantMessageEvent': {
                            'type': 'text_delta', 'delta': _redact(update.get('delta', ''))}})
                elif kind in ('agent_start', 'agent_end', 'agent_settled', 'tool_execution_start', 'tool_execution_end'):
                    on_event({k: record[k] for k in ('type', 'toolName', 'isError', 'aborted') if k in record})
            try:
                client = RPC(self._argv(meta), meta['worktree'], self._directory(ident),
                             cancel=cancel, on_event=event)
                state = client.request('get_state')
                if state.get('isStreaming') or state.get('isCompacting'):
                    raise PlanningError('resumed Pi session is not idle')
                if state.get('sessionId') != ident:
                    raise PlanningError('Pi resumed a different session identity')
                commands = client.request('get_commands').get('commands', [])
                skill = 'plan-with-me' if meta['mode'] == 'discuss' else 'plan-for-me'
                if not any(c.get('name') == 'skill:' + skill and c.get('source') == 'skill' for c in commands):
                    raise PlanningError('required Pi skill not discovered: skill:' + skill)
                with self._active_lock:
                    self._active[ident] = client
                context = ('Selected mode: ' + meta['mode'] + '. '
                           + ('Selected task: ' + meta['task'] + '. ' if meta['task'] else ''))
                if not meta['turns']:
                    context += _blocker_context(meta)
                prompt = _literal(context + '\n' + user_text)
                if not meta['turns']:
                    prompt = '/skill:' + skill + ' ' + prompt
                result = client.turn(prompt)
                if cancel is not None and cancel.is_set():
                    raise Cancelled('planning turn cancelled')
                text = result['text']
                blocks = re.findall(r'^```autowork-plan\s*\n(.*?)^```\s*$', text, re.M | re.S)
                if '```autowork-plan' in text and len(blocks) != 1:
                    raise PlanningError('expected exactly one complete autowork-plan JSON block')
                if blocks:
                    if meta['mode'] == 'investigate':
                        raise PlanningError('investigate mode cannot stage file proposals')
                    try:
                        payload = json.loads(blocks[0])
                    except ValueError as exc:
                        raise PlanningError('invalid autowork-plan JSON') from exc
                    if not isinstance(payload, dict) or set(payload) != {'files'}:
                        raise PlanningError('autowork-plan must contain only files')
                    # Cancellation accepted before staging must not create a proposal.
                    if cancel is not None and cancel.is_set():
                        raise Cancelled('planning turn cancelled')
                    proposals.stage(meta, payload['files'])
                    result['preview'] = proposals.preview(meta)
                result['text'] = _redact(text)
                # A late cancellation retains any staged draft, never a successful turn.
                if cancel is not None and cancel.is_set():
                    raise Cancelled('planning turn cancelled')
                meta['status'] = result['status']
                meta['turns'] += 1
                self._history(ident, 'assistant', result['text'])
                failed = False
                return dict(result, id=ident)
            except Cancelled:
                meta['status'] = 'cancelled'
                meta['last_error'] = 'planning turn cancelled'
                return {'id': ident, 'status': 'cancelled', 'text': ''}
            except (RPCError, RuntimeError, OSError, ValueError) as exc:
                meta['status'] = 'error'
                meta['last_error'] = _redact(str(exc))[:1000]
                raise PlanningError(meta['last_error']) from exc
            finally:
                with self._active_lock:
                    self._active.pop(ident, None)
                if client:
                    client.close(abort=failed)
                self._save(meta)

    def steer(self, ident, message):
        if not isinstance(message, str) or not message:
            raise PlanningError('steering message must be nonempty text')
        with self._active_lock:
            client = self._active.get(ident)
        if client is None:
            raise PlanningError('planning session is not active in this controller')
        try:
            result = client.request('steer', message=_literal(message))
        except RPCError as exc:
            raise PlanningError(str(exc)) from exc
        self._history(ident, 'user', message)
        return dict(result, id=ident)

    def stage(self, ident, files):
        with self._locked(ident) as meta:
            if meta['status'] == 'applied':
                raise PlanningError('applied session is read-only')
            proposals.stage(meta, files)
            return proposals.preview(meta)

    def preview(self, ident):
        with self._locked(ident) as meta:
            return proposals.preview(meta)

    def apply(self, ident, revision):
        with self._locked(ident) as meta:
            if meta['status'] == 'applied':
                raise PlanningError('session already applied')
            try:
                result = proposals.apply(meta, revision, self._directory(ident))
                meta.update(status='applied', commit=result['commit'])
                return result
            except (task_commands.CommandError, OSError, ValueError, proposals.landing.LandingBroken) as exc:
                raise PlanningError(str(exc)) from exc
            finally:
                self._save(meta)

    def roadmap(self, ident=None):
        try:
            if ident:
                with self._locked(ident) as meta:
                    store = task_commands.worktree_store(meta['worktree'])
                    revision = proposals.preview(meta)['revision']
            else:
                store = task_commands.TaskStore.at(self.repo, 'HEAD')
                revision = store.rev
            def row(record):
                return {key: list(getattr(record, key)) if key == 'depends_on' else getattr(record, key, None)
                        for key in ('id', 'title', 'status', 'section', 'goal', 'depends_on')}
            return {'goals': [row(g) for g in store.goals.values()],
                    'tasks': [row(t) for t in store.tasks.values()], 'revision': revision, 'errors': []}
        except (PlanningError, task_commands.CommandError, task_commands.StoreError, OSError, ValueError) as exc:
            return {'goals': [], 'tasks': [], 'revision': None, 'errors': [str(exc)]}
