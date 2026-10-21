"""Read-only schema-1 task snapshots; no working-tree task content is trusted.

TaskStore.at(repo, rev) resolves rev once, then reads only that commit. ``tasks``
and ``goals`` are immutable ID maps; pending(repo) returns changed paths, not
records. StoreError invalidates the entire snapshot and reports path:line errors.

Files are UTF-8 Markdown with TOML between opening/closing +++ lines. See the
component's task-store.md for the schema and the precise runnable/hash boundary.
"""
from dataclasses import dataclass
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tomllib
from types import MappingProxyType
from typing import Mapping


class StoreError(ValueError):
    """No records may be consumed from an invalid store."""


class Kind(str, Enum):
    UNKNOWN = 'unknown'
    IMPLEMENTATION = 'implementation'
    PLAN = 'plan'
    INSPECTION = 'inspection'


class Ownership(str, Enum):
    UNKNOWN = 'unknown'
    WORKER = 'worker'
    COORDINATOR = 'coordinator'
    OWNER = 'owner'


class LiveAuthorization(str, Enum):
    DENIED = 'denied'
    AUTHORIZED = 'authorized'


@dataclass(frozen=True)
class Record:
    schema: int
    id: str
    title: str
    path: str
    body: str
    record_revision: str
    contract_hash: str


@dataclass(frozen=True)
class GoalRecord(Record):
    priority: int
    source: str
    status: str
    focus: bool


@dataclass(frozen=True)
class TaskRecord(Record):
    short: str
    status: str | None
    goal: str | None
    section: str | None
    rank: int | None
    depends_on: tuple[str, ...]
    touches: tuple[str, ...]
    resources: tuple[str, ...]
    kind: Kind
    ownership: Ownership
    live: LiveAuthorization
    scope: str
    acceptance: tuple[str, ...]
    checks: tuple[str, ...]
    exclusions: tuple[str, ...]
    missing_fields: tuple[str, ...]

    @property
    def draft(self) -> bool:
        return bool(self.missing_fields)

    @property
    def runnable(self) -> bool:
        """Contract/authority eligible, NOT a lease or permission to run checks.

        Dependency completion, resource availability, and caller rights are gates
        for consumers, not assertions this immutable record can make.
        """
        return (not self.draft and self.status == 'open'
                and self.section in ('Now', 'Next')
                and self.kind in (Kind.IMPLEMENTATION, Kind.PLAN, Kind.INSPECTION)
                and self.ownership == Ownership.WORKER
                and ('live' not in self.resources or self.live == LiveAuthorization.AUTHORIZED))


_TASK_LISTS = ('depends_on', 'touches', 'resources', 'acceptance', 'checks', 'exclusions')
_TASK_STRINGS = ('id', 'title', 'short', 'status', 'goal', 'section', 'scope')
_TASK_REQUIRED = (*_TASK_STRINGS, 'rank', *_TASK_LISTS, 'kind', 'ownership')
_GOAL_REQUIRED = ('id', 'title', 'priority', 'source', 'status', 'focus')
_CONTRACT_FIELDS = ('scope', 'acceptance', 'checks', 'depends_on', 'touches',
                    'status', 'resources', 'kind', 'ownership', 'live', 'exclusions')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
_RESOURCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_./-]*\Z')


def _digest(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _hash(value: dict) -> str:
    return _digest(json.dumps(value, sort_keys=True, ensure_ascii=False,
                              separators=(',', ':')).encode('utf-8'))


def _git(repo, *args, stdin=None) -> bytes:
    # Do not let inherited GIT_DIR/GIT_INDEX_FILE redirect the requested repo.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    try:
        result = subprocess.run(['git', '--no-optional-locks', '--no-replace-objects',
                                 '-C', str(repo), *args], env=env, input=stdin,
                                capture_output=True, timeout=30)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise StoreError(f'tasks/:1: Git read failed: {exc}') from exc
    if result.returncode:
        raise StoreError('tasks/:1: Git read failed: ' + result.stderr.decode('utf-8', 'replace').strip())
    return result.stdout


def _blobs(repo, oids) -> list[bytes]:
    """Every blob in one `git cat-file --batch` call: one process per snapshot, not per file."""
    if not oids:
        return []
    out = _git(repo, 'cat-file', '--batch', stdin=''.join(oid + '\n' for oid in oids).encode())
    blobs, cursor = [], 0
    for oid in oids:
        end = out.index(b'\n', cursor)
        header = out[cursor:end].split()
        if len(header) != 3 or header[0].decode() != oid or header[1] != b'blob':
            raise StoreError(f'tasks/:1: Git read failed: unexpected object header for {oid}')
        size = int(header[2])
        blobs.append(out[end + 1:end + 1 + size])
        cursor = end + 1 + size + 1
    return blobs


class _Document:
    """Validation context retains source locations, never exposes mutable TOML."""
    def __init__(self, path: str, blob: bytes):
        self.path = path
        try:
            text = blob.decode('utf-8')
        except UnicodeDecodeError as exc:
            self.fail('invalid UTF-8', line=blob[:exc.start].count(b'\n') + 1)
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].strip() != '+++':
            self.fail('expected opening +++ frontmatter delimiter')
        end = next((i for i in range(1, len(lines)) if lines[i].strip() == '+++'), None)
        if end is None:
            self.fail('missing closing +++ frontmatter delimiter')
        self.frontmatter = ''.join(lines[1:end])
        self.body = ''.join(lines[end + 1:])
        try:
            self.data = tomllib.loads(self.frontmatter)
        except tomllib.TOMLDecodeError as exc:
            # Python 3.11/3.12 expose line numbers only in the message.
            match = re.search(r'at line (\d+)', str(exc))
            line = int(match[1]) + 1 if match else end + 1
            self.fail(f'malformed TOML: {exc}', line=line)
        except ValueError as exc:
            # Numeric conversion limits can escape tomllib as plain ValueError.
            self.fail(f'unsupported TOML value: {exc}')
        if type(self.data.get('schema')) is not int or self.data['schema'] != 1:
            self.fail('schema must be 1; missing/unknown versions are refused', 'schema')

    def fail(self, message, field=None, *, line=None):
        if line is None:
            match = re.search(r'^[ \t]*' + re.escape(field or '') + r'[ \t]*=',
                              getattr(self, 'frontmatter', ''), re.M) if field else None
            line = self.frontmatter[:match.start()].count('\n') + 2 if match else 1
        raise StoreError(f'{self.path}:{line}: {message}')

    def validate(self, goal=False):
        required = _GOAL_REQUIRED if goal else _TASK_REQUIRED
        allowed = {'schema', *required} | (set() if goal else {'live'})
        for key in self.data.keys() - allowed:
            self.fail(f'unknown field {key}', key)
        for key in (_GOAL_REQUIRED if goal else _TASK_STRINGS):
            if key in self.data and key not in ('priority', 'focus'):
                if not isinstance(self.data[key], str) or not self.data[key].strip():
                    self.fail(f'{key} must be a nonempty string', key)
        if 'id' not in self.data or not _ID.fullmatch(self.data['id']):
            self.fail('id must use letters, digits, underscores or hyphens', 'id')
        integer = 'priority' if goal else 'rank'
        if integer in self.data and type(self.data[integer]) is not int:
            self.fail(f'{integer} must be an integer', integer)
        statuses = ('unmet', 'partial', 'unverified', 'met') if goal else ('open', 'done', 'superseded')
        if 'status' in self.data and self.data['status'] not in statuses:
            self.fail(f'status must be one of {statuses}', 'status')
        if goal:
            for key in required:
                if key not in self.data:
                    self.fail(f'missing goal field {key}', key)
            if type(self.data['focus']) is not bool:
                self.fail('focus must be a boolean', 'focus')
            return
        if 'section' in self.data and self.data['section'] not in ('Now', 'Next', 'Needs decision'):
            self.fail('section must be Now, Next or Needs decision', 'section')
        for key in _TASK_LISTS:
            if key not in self.data:
                continue
            value = self.data[key]
            if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                self.fail(f'{key} must be an array of nonempty strings', key)
            if key == 'resources' and any(not _RESOURCE.fullmatch(v) for v in value):
                self.fail('resources must contain resource tokens, not prose', key)
        for key, enum in (('kind', Kind), ('ownership', Ownership), ('live', LiveAuthorization)):
            if key in self.data:
                try:
                    enum(self.data[key])
                except (ValueError, TypeError):
                    self.fail(f'unknown {key} value', key)

    def record(self, blob, goal=False):
        self.validate(goal)
        data = self.data
        common = dict(schema=1, id=data['id'], title=data.get('title', ''), path=self.path,
                      body=self.body, record_revision=_digest(blob))
        if goal:
            fields = {key: data[key] for key in ('priority', 'source', 'status', 'focus')}
            return GoalRecord(**common, **fields, contract_hash=_hash(fields))
        contract = {key: data.get(key) for key in _CONTRACT_FIELDS}
        # Writing an authority field's default must not look like a contract change.
        contract.update(kind=data.get('kind', 'unknown'), ownership=data.get('ownership', 'unknown'),
                        live=data.get('live', 'denied'))
        contract['section_group'] = ('runnable' if data.get('section') in ('Now', 'Next')
                                     else data.get('section'))
        fields = {key: tuple(data.get(key, ())) for key in _TASK_LISTS}
        fields.update({key: data.get(key) for key in ('status', 'goal', 'section', 'rank')})
        fields.update(short=data.get('short', ''), scope=data.get('scope', ''),
                      kind=Kind(data.get('kind', 'unknown')),
                      ownership=Ownership(data.get('ownership', 'unknown')),
                      live=LiveAuthorization(data.get('live', 'denied')))
        missing = [key for key in _TASK_REQUIRED if key not in data]
        missing.extend(key for key in ('acceptance', 'checks', 'touches') if key in data and not data[key])
        return TaskRecord(**common, **fields, contract_hash=_hash(contract),
                          missing_fields=tuple(missing))


@dataclass(frozen=True)
class TaskStore:
    rev: str
    tasks: Mapping[str, TaskRecord]
    goals: Mapping[str, GoalRecord]

    @classmethod
    def at(cls, repo: str | Path, rev: str) -> 'TaskStore':
        """Read all task/goal records at a commit; any invalid file aborts."""
        pinned = _git(repo, 'rev-parse', '--verify', '--end-of-options', f'{rev}^{{commit}}').decode().strip()
        # Include trees themselves: a trailing-slash pathspec silently omits a
        # symlink/gitlink replacing a store directory, disguising it as empty.
        tree = _git(repo, 'ls-tree', '-rtz', '--full-tree', pinned, '--', 'tasks')
        tasks, goals, documents = {}, {}, {}
        seen, files = {}, []
        if not any(entry.split(b'\t', 1)[-1] == b'tasks' for entry in tree.split(b'\0') if entry):
            # An unconverted repository has no store; it is never an empty queue.
            raise StoreError(f'tasks/:1: no task store at {pinned[:12]}')
        for entry in tree.split(b'\0'):
            if not entry:
                continue
            metadata, raw_path = entry.split(b'\t', 1)
            path = os.fsdecode(raw_path)
            mode, kind, _oid = metadata.split()
            if path in ('tasks', 'tasks/items', 'tasks/goals'):
                if mode != b'040000' or kind != b'tree':
                    raise StoreError(f'{path}:1: expected a store directory')
                continue
            if not path.startswith(('tasks/items/', 'tasks/goals/')):
                continue  # Evidence and other tasks/ owners are not records.
            if mode not in (b'100644', b'100755') or kind != b'blob':
                raise StoreError(f'{path}:1: expected a regular Markdown file')
            if Path(path).suffix != '.md' or len(Path(path).parts) != 3:
                raise StoreError(f'{path}:1: expected tasks/items/<ID>.md or tasks/goals/<ID>.md')
            files.append((path, _oid.decode()))
        for path, blob in zip((path for path, _ in files), _blobs(repo, [oid for _, oid in files])):
            document = _Document(path, blob)
            is_goal = path.startswith('tasks/goals/')
            record = document.record(blob, is_goal)
            if record.id in seen:
                document.fail(f'duplicate ID {record.id} (also in {seen[record.id]})', 'id')
            seen[record.id] = path
            documents[path] = document
            (goals if is_goal else tasks)[record.id] = record
        focused = [goal for goal in goals.values() if goal.focus]
        if len(focused) > 1:
            documents[focused[1].path].fail(f'only one goal may have focus (also {focused[0].id})', 'focus')
        for task in tasks.values():
            if task.goal is not None and task.goal not in goals:
                documents[task.path].fail(f'unknown goal {task.goal}', 'goal')
        for record in (*goals.values(), *tasks.values()):
            if Path(record.path).stem != record.id:
                documents[record.path].fail('filename must match id', 'id')
        return cls(pinned, MappingProxyType(tasks), MappingProxyType(goals))

    @staticmethod
    def pending(repo: str | Path) -> tuple[str, ...]:
        """Changed task paths, including both sides of renames; never parse edits."""
        # Filtering before rename detection loses endpoints outside the store.
        status = _git(repo, 'status', '--porcelain=v1', '-z', '--untracked-files=all',
                      '--renames').split(b'\0')
        paths = set()
        index = 0
        while index < len(status):
            entry = status[index]
            index += 1
            if not entry:
                continue
            changed = [os.fsdecode(entry[3:])]
            if b'R' in entry[:2] or b'C' in entry[:2]:
                changed.append(os.fsdecode(status[index]))
                index += 1
            if any(path in ('tasks', 'tasks/items', 'tasks/goals')
                   or path.startswith(('tasks/items/', 'tasks/goals/')) for path in changed):
                paths.update(changed)
        return tuple(sorted(paths))
