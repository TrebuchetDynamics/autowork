"""Read-only schema-1 task snapshots; no working-tree task content is trusted.

TaskStore.at(repo, rev) resolves rev once, then reads only that commit. ``tasks``
and ``goals`` are immutable ID maps; pending(repo) returns changed paths, not
records. StoreError invalidates the entire snapshot and reports path:line errors.

Files are UTF-8 Markdown with TOML between opening/closing +++ lines. See the
component's task-store.md for the schema and the precise runnable/hash boundary.
"""
from dataclasses import dataclass, replace
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
    depends_on: tuple[str, ...] = ()


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
    verified_depends_on: tuple[str, ...] = ()
    closure: str | None = None
    closure_actor: str | None = None
    closure_timestamp: str | None = None
    closure_reason: str | None = None
    closure_evidence: str | None = None
    owner_waiver: str | None = None
    owner_qualification: str | None = None
    receipt_valid: bool = False

    @property
    def verified(self):
        return self.status == 'done' and self.closure == 'coordinator_verified' and self.receipt_valid

    @property
    def qualified(self):
        return self.verified or bool(self.owner_waiver or self.owner_qualification)

    @property
    def closure_info(self):
        if self.status != 'done':
            return None
        return dict(provenance=self.closure, actor=self.closure_actor, timestamp=self.closure_timestamp,
                    reason=self.closure_reason, evidence=self.closure_evidence,
                    label=('Verified' if self.verified else 'Verified (evidence missing or invalid)')
                          if self.closure == 'coordinator_verified' else 'Manual',
                    evidence_valid=self.receipt_valid if self.closure == 'coordinator_verified' else None,
                    owner_waiver=self.owner_waiver, owner_qualification=self.owner_qualification)

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
_CLOSURE_FIELDS = ('closure', 'closure_actor', 'closure_timestamp', 'closure_reason', 'closure_evidence',
                   'owner_waiver', 'owner_qualification')
_TASK_STRINGS = ('id', 'title', 'short', 'status', 'goal', 'section', 'scope')
_TASK_REQUIRED = (*_TASK_STRINGS, 'rank', *_TASK_LISTS, 'kind', 'ownership')
_GOAL_REQUIRED = ('id', 'title', 'priority', 'source', 'status', 'focus')
# Status is a transition, not contract: closing a task must keep the hash its verification
# pinned. Consumers check done and superseded explicitly; Needs decision is section_group.
_CONTRACT_FIELDS = ('scope', 'acceptance', 'checks', 'depends_on', 'touches',
                    'resources', 'kind', 'ownership', 'live', 'exclusions')
_ID = re.compile(r'[A-Za-z0-9][A-Za-z0-9_-]*\Z')
_RESOURCE = re.compile(r'[A-Za-z0-9][A-Za-z0-9_./:-]*\Z')  # port:8080, db:test


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


def _objects(repo, oids):
    """Batch immutable objects, retaining missing references as absent rather than proof."""
    if not oids:
        return {}
    out = _git(repo, 'cat-file', '--batch', stdin=''.join(oid + '\n' for oid in oids).encode())
    objects, cursor = {}, 0
    for oid in oids:
        end = out.index(b'\n', cursor)
        header = out[cursor:end].split()
        if header == [oid.encode(), b'missing']:
            cursor = end + 1
            continue
        if len(header) != 3 or header[0].decode() != oid:
            raise StoreError(f'tasks/:1: Git read failed: unexpected object header for {oid}')
        size = int(header[2])
        objects[oid] = (header[1], out[end + 1:end + 1 + size])
        cursor = end + 1 + size + 1
    return objects


def _blobs(repo, oids) -> list[bytes]:
    """Every blob in one `git cat-file --batch` call, not one process per file."""
    objects = _objects(repo, oids)
    if any(objects.get(oid, (None,))[0] != b'blob' for oid in oids):
        raise StoreError('tasks/:1: Git read failed: expected blob objects')
    return [objects[oid][1] for oid in oids]


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
        allowed = {'schema', *required} | ({'depends_on'} if goal else {'live', 'verified_depends_on', *_CLOSURE_FIELDS})
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
            depends = self.data.get('depends_on', [])
            if not isinstance(depends, list) or any(not isinstance(v, str) or not _ID.fullmatch(v) for v in depends):
                self.fail('depends_on must be an array of goal IDs', 'depends_on')
            return
        if 'section' in self.data and self.data['section'] not in ('Now', 'Next', 'Needs decision'):
            self.fail('section must be Now, Next or Needs decision', 'section')
        for key in (*_TASK_LISTS, 'verified_depends_on'):
            if key not in self.data:
                continue
            value = self.data[key]
            if not isinstance(value, list) or any(not isinstance(v, str) or not v.strip() for v in value):
                self.fail(f'{key} must be an array of nonempty strings', key)
            if key == 'resources' and any(not _RESOURCE.fullmatch(v) for v in value):
                self.fail('resources must contain resource tokens, not prose', key)
        for key in _CLOSURE_FIELDS:
            if key in self.data and (not isinstance(self.data[key], str) or not self.data[key].strip()):
                self.fail(f'{key} must be a nonempty string', key)
        if self.data.get('closure') not in (None, 'manual', 'coordinator_verified'):
            self.fail('closure must be manual or coordinator_verified', 'closure')
        if self.data.get('closure') == 'manual':
            for key in ('closure_actor', 'closure_timestamp', 'closure_reason'):
                if key not in self.data:
                    self.fail(f'manual closure needs {key}', 'closure')
        if not set(self.data.get('verified_depends_on', ())) <= set(self.data.get('depends_on', ())):
            self.fail('verified_depends_on must be a subset of depends_on', 'verified_depends_on')
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
            fields['depends_on'] = tuple(data.get('depends_on', ()))
            return GoalRecord(**common, **fields, contract_hash=_hash(fields))
        contract = {key: data.get(key) for key in _CONTRACT_FIELDS}
        # Writing an authority field's default must not look like a contract change.
        contract.update(kind=data.get('kind', 'unknown'), ownership=data.get('ownership', 'unknown'),
                        live=data.get('live', 'denied'))
        if data.get('verified_depends_on'):
            contract['verified_depends_on'] = data['verified_depends_on']
        contract['section_group'] = ('runnable' if data.get('section') in ('Now', 'Next')
                                     else data.get('section'))
        fields = {key: tuple(data.get(key, ())) for key in _TASK_LISTS}
        fields.update({key: data.get(key) for key in ('status', 'goal', 'section', 'rank')})
        fields.update(short=data.get('short', ''), scope=data.get('scope', ''),
                      kind=Kind(data.get('kind', 'unknown')),
                      ownership=Ownership(data.get('ownership', 'unknown')),
                      live=LiveAuthorization(data.get('live', 'denied')))
        fields.update({key: data.get(key) for key in _CLOSURE_FIELDS})
        fields['verified_depends_on'] = tuple(data.get('verified_depends_on', ()))
        missing = [key for key in _TASK_REQUIRED if key not in data]
        missing.extend(key for key in ('acceptance', 'checks', 'touches') if key in data and not data[key])
        if data.get('status') in ('done', 'superseded'):
            # A closed record is history: it never runs, so it needs no section, rank or contract.
            missing = [key for key in missing if key in ('id', 'title', 'status')]
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
        seen, files, evidence = {}, [], {}
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
            if path.startswith('tasks/evidence/') and mode in (b'100644', b'100755') and kind == b'blob':
                evidence[path] = _oid.decode()
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
        requested = [(tid, task.closure_evidence) for tid, task in tasks.items()
                     if task.closure == 'coordinator_verified'
                     and task.closure_evidence == f'tasks/evidence/{tid}.toml'
                     and task.closure_evidence in evidence]
        receipts = {}
        for (tid, _), blob in zip(requested, _blobs(repo, [evidence[path] for _, path in requested])):
            task = tasks[tid]
            try:
                receipt = tomllib.loads(blob.decode('utf-8'))
                valid = (type(receipt.get('schema')) is int and receipt.get('schema') == 1 and receipt.get('task') == tid
                         and receipt.get('contract_hash') == task.contract_hash
                         and receipt.get('result') == 'pass' and receipt.get('review') == 'passed'
                         and all(re.fullmatch(r'[0-9a-f]{40}(?:[0-9a-f]{24})?', receipt.get(key, ''))
                                 for key in ('candidate', 'integration', 'tree')))
            except (ValueError, TypeError, UnicodeError):
                valid = False
            if valid:
                receipts[tid] = receipt
        objects = _objects(repo, sorted({r[key] for r in receipts.values()
                                         for key in ('candidate', 'integration', 'tree')}))
        ancestors = set(_git(repo, 'rev-list', pinned).decode().split()) if receipts else set()
        for tid, receipt in receipts.items():
            integration = objects.get(receipt['integration'], (None, b''))
            headers = integration[1].split(b'\n\n', 1)[0].splitlines()
            parents = [line.removeprefix(b'parent ').decode('ascii', 'replace') for line in headers if line.startswith(b'parent ')]
            tree = next((line.removeprefix(b'tree ').decode('ascii', 'replace') for line in headers if line.startswith(b'tree ')), None)
            valid = (integration[0] == b'commit' and receipt['integration'] in ancestors
                     and objects.get(receipt['candidate'], (None,))[0] == b'commit'
                     and objects.get(receipt['tree'], (None,))[0] == b'tree'
                     and len(parents) == 2 and parents[1] == receipt['candidate'] and tree == receipt['tree'])
            tasks[tid] = replace(tasks[tid], receipt_valid=valid)
        focused = [goal for goal in goals.values() if goal.focus]
        if len(focused) > 1:
            documents[focused[1].path].fail(f'only one goal may have focus (also {focused[0].id})', 'focus')
        for goal in goals.values():
            for dep in goal.depends_on:
                if dep not in goals:
                    documents[goal.path].fail(f'unknown goal dependency {dep}', 'depends_on')
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


# --- Writing ---------------------------------------------------------------------------
# tomllib only reads. This writer emits exactly the schema's types and edits only the
# header lines it is asked to change; anything it cannot reproduce is refused, not dropped.

TASK_ORDER = ('schema', 'id', 'title', 'short', 'status', 'goal', 'section', 'rank', 'depends_on',
              'touches', 'resources', 'kind', 'ownership', 'live', 'scope', 'acceptance', 'checks',
              'exclusions', 'verified_depends_on', *_CLOSURE_FIELDS)
GOAL_ORDER = ('schema', 'id', 'title', 'priority', 'source', 'status', 'focus', 'depends_on')
_CONTROL = re.compile(r'[\x00-\x1f\x7f]')
_STRINGS = re.compile(r'"(?:[^"\\\n]|\\.)*"|\'[^\'\n]*\'')  # TOML one-line strings


class WriteError(ValueError):
    """The requested write cannot be represented without losing or reflowing content."""


def toml_value(key, value) -> str:
    """One-line TOML for a schema value: a string, an integer, a boolean or a string array."""
    if isinstance(value, bool):
        return 'true' if value else 'false'
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        if _CONTROL.search(value.replace('\n', '').replace('\r', '').replace('\t', '')):
            raise WriteError(f'{key}: control characters cannot be written')
        # JSON escapes line breaks/tabs in the same form as TOML basic strings.
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, (list, tuple)) and all(isinstance(v, str) for v in value):
        return '[' + ', '.join(toml_value(key, v) for v in value) + ']'
    raise WriteError(f'{key}: unsupported value {value!r}')


def render(fields: dict, body: str = '', goal: bool = False) -> str:
    """A new record in canonical key order; unknown keys are refused."""
    order = GOAL_ORDER if goal else TASK_ORDER
    unknown = set(fields) - set(order)
    if unknown:
        raise WriteError('unknown field ' + ', '.join(sorted(unknown)))
    header = [f'{key} = {toml_value(key, fields[key])}' for key in order if key in fields]
    text = ('+++\n' + '\n'.join(header) + '\n+++\n' + body).rstrip('\n') + '\n'
    _check(text, fields)
    return text


def _header_span(lines):
    if not lines or lines[0].strip() != '+++':
        raise WriteError('expected opening +++ frontmatter delimiter')
    end = next((i for i in range(1, len(lines)) if lines[i].strip() == '+++'), None)
    if end is None:
        raise WriteError('missing closing +++ frontmatter delimiter')
    return end


def edit(text: str, changes: dict, goal: bool = False) -> str:
    """Set (or, with None, remove) header keys, leaving every other byte as it was."""
    order = GOAL_ORDER if goal else TASK_ORDER
    lines = text.splitlines(keepends=True)
    end = _header_span(lines)
    before = tomllib.loads(''.join(lines[1:end]))
    for key, value in changes.items():
        if key not in order or key in ('schema', 'id'):
            raise WriteError(f'{key} cannot be set here')
        matches = [i for i in range(1, end) if re.match(rf'[ \t]*{re.escape(key)}[ \t]*=', lines[i])]
        if len(matches) > 1:
            raise WriteError(f'{key} appears more than once')
        if matches:
            i = matches[0]
            try:
                alone = tomllib.loads(lines[i])
            except tomllib.TOMLDecodeError:
                raise WriteError(f'{key} spans several lines; edit it by hand') from None
            if alone.get(key) != before.get(key) or '#' in _STRINGS.sub('', lines[i]):
                raise WriteError(f'{key} carries a comment this writer would drop; edit it by hand')
            newline = '\n' if lines[i].endswith('\n') else ''
            if value is None:
                del lines[i]
                end -= 1
            else:
                lines[i] = f'{key} = {toml_value(key, value)}' + (newline or '\n')
        elif value is not None:
            lines.insert(end, f'{key} = {toml_value(key, value)}\n')
            end += 1
    result = ''.join(lines)
    expected = {**before, **{k: v for k, v in changes.items() if v is not None}}
    for key in [k for k, v in changes.items() if v is None]:
        expected.pop(key, None)
    _check(result, expected)
    return result


def set_note(text: str, label: str, value: str) -> str:
    """Set the body line `- <label>: <value>`, replacing an earlier one or appending it."""
    if not re.fullmatch(r"[A-Za-z][A-Za-z '-]*", label):
        raise WriteError('a note label is letters, spaces, hyphens or apostrophes')
    if _CONTROL.search(value):
        raise WriteError(f'{label}: line breaks cannot be written; use one line')
    lines = text.splitlines(keepends=True)
    end = _header_span(lines)
    line = f'- {label}: {value}\n'
    for i in range(end + 1, len(lines)):
        if lines[i].startswith(f'- {label}:'):
            lines[i] = line
            break
    else:
        if len(lines) > end + 1 and not lines[-1].endswith('\n'):
            lines[-1] += '\n'
        lines.append(line)
    return ''.join(lines)


def _check(text: str, expected: dict):
    """The written header parses back to exactly the intended values."""
    lines = text.splitlines(keepends=True)
    end = _header_span(lines)
    parsed = tomllib.loads(''.join(lines[1:end]))
    want = {k: list(v) if isinstance(v, tuple) else v for k, v in expected.items()}
    if parsed != want:
        raise WriteError('the written header would not read back as written; nothing written')
