"""Goal ledger validation, identity and stateless guarded IO. Transaction state is supplied by each caller."""
from contextlib import contextmanager
import fcntl
from graphlib import CycleError, TopologicalSorter
import hashlib
import json
import math
import os
import tempfile
import re
import time
import subprocess
import sys
from pathlib import Path

GOAL_STATUS = ('unmet', 'partial', 'unverified', 'met')
TASK_STATUS = ('open', 'in_progress', 'done', 'superseded')
TASK_ID = r'[A-Za-z0-9][A-Za-z0-9_-]*'
SECTIONS = ('Now', 'Next', 'Needs decision', 'Done', 'Superseded')
KINDS = ('executed', 'inspection')
RESULTS = ('pass', 'fail')
# Order: primary milestone first, then section (Now before Next), goal priority, then status as a
# tie-break: unverified/partial (prove or finish what exists) before unmet (new work).
STATUS_RANK = {'unverified': 0, 'partial': 1, 'unmet': 2, 'met': 3}
SECTION_RANK = {'Now': 0, 'Next': 1}
PRIORITY_SCHEMA = 1
UNSPECIFIED = object()


def path_of(repo):
    return Path(repo) / 'goals.json'


def parse_ledger(blob):
    """Do not let JSON's last-key-wins behavior erase conflicting author input."""
    def unique_object(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('goals.json contains duplicate JSON key; resolve conflicting members before retrying')
            result[key] = value
        return result
    return json.loads(blob, object_pairs_hook=unique_object)


def load(repo):
    p = path_of(repo)
    if not p.exists():
        sys.exit(f'{p} not found')
    try:
        data = parse_ledger(p.read_text())
    except json.JSONDecodeError as exc:
        sys.exit(f'goals.json:{exc.lineno}:{exc.colno}: malformed JSON')
    except ValueError as exc:
        sys.exit(str(exc))
    problems = shape_errors(data)
    if problems:
        sys.exit('\n'.join(problems))
    return data


def shape_errors(data):
    """Reject shapes we cannot safely interpret, without blocking semantic repairs."""
    if not isinstance(data, dict):
        return ['goals.json must be an object']
    problems = []
    if type(data.get('version')) is not int or data['version'] != 1:
        problems.append('version must be 1')
    for collection in ('goals', 'tasks'):
        rows = data.get(collection)
        if not isinstance(rows, list):
            problems.append(f'{collection} must be a list')
            continue
        for index, row in enumerate(rows):
            location = f'{collection}[{index}]'
            if not isinstance(row, dict):
                problems.append(f'{location} must be an object')
                continue
            if not isinstance(row.get('id'), str) or not row['id']:
                problems.append(f'{location}.id must be a nonempty string')
            for field in ('title', 'status', 'goal', 'section', 'supersession_reason'):
                if field in row and not isinstance(row[field], str):
                    problems.append(f'{location}.{field} must be a string')
            fields = ('depends_on', 'tasks') if collection == 'goals' else ('depends_on', 'superseded_by')
            for field in fields:
                value = row.get(field, [])
                if not isinstance(value, list) or any(not isinstance(v, str) or not v for v in value):
                    problems.append(f'{location}.{field} must be a list of nonempty strings')
            if collection == 'goals':
                if 'source' in row and not isinstance(row['source'], str):
                    problems.append(f'{location}.source must be a string')
                priority = row.get('priority', 100)
                if type(priority) not in (int, float) or (isinstance(priority, float) and not math.isfinite(priority)):
                    problems.append(f'{location}.priority must be a finite number')
                evidence = row.get('evidence', [])
                if not isinstance(evidence, list):
                    problems.append(f'{location}.evidence must be a list')
                else:
                    for number, entry in enumerate(evidence):
                        if not isinstance(entry, dict):
                            problems.append(f'{location}.evidence[{number}] must be an object')
                        elif any(field in entry and not isinstance(entry[field], str)
                                 for field in ('kind', 'result', 'ref')):
                            problems.append(f'{location}.evidence[{number}] fields must be strings')
    if 'priority_order' in data:
        record = data['priority_order']
        tasks = record.get('tasks') if isinstance(record, dict) else None
        if (not isinstance(record, dict) or type(record.get('schema')) is not int
                or record['schema'] != PRIORITY_SCHEMA or not isinstance(tasks, list)
                or any(not isinstance(tid, str) or not tid for tid in tasks) or len(set(tasks)) != len(tasks)):
            problems.append(f'priority_order must be {{"schema": {PRIORITY_SCHEMA}, "tasks": [unique task IDs]}}')
    return problems


def proven(goal):
    return any(e.get('kind') == 'executed' and e.get('result') == 'pass' for e in goal.get('evidence', []))


def normalize(data):
    """Apply the met rule, fill defaults and sort into a stable order."""
    problems = shape_errors(data)
    if problems:
        raise ValueError('; '.join(problems))
    goals, tasks = data.get('goals', []), data.get('tasks', [])
    for g in goals:
        g.setdefault('depends_on', []); g.setdefault('evidence', []); g.setdefault('tasks', [])
        g.setdefault('priority', 100)
        if g.get('status') == 'met' and not proven(g):
            g['status'] = 'unverified'
        elif g.get('status') == 'met' and any(
                t.get('goal') == g['id'] and t.get('status') != 'done' for t in tasks):
            g['status'] = 'partial'
        g['evidence'] = sorted(g['evidence'], key=lambda e: (e.get('kind', ''), e.get('ref', '')))
        g['depends_on'] = sorted(set(g['depends_on'])); g['tasks'] = sorted(set(g['tasks']))
    for t in tasks:
        t.setdefault('depends_on', []); t.setdefault('section', 'Next'); t.setdefault('status', 'open')
        t['depends_on'] = sorted(set(t['depends_on']))
        if t['status'] in ('done', 'superseded'):
            t['section'] = 'Done' if t['status'] == 'done' else 'Superseded'
    # Goals keep authoring order (priority, then id); tasks follow section then id.
    goals.sort(key=lambda g: (g['priority'], g['id']))
    tasks.sort(key=lambda t: (SECTIONS.index(t['section']) if t['section'] in SECTIONS else 9, t['id']))
    normalized = dict(data)
    normalized.update(goals=goals, tasks=tasks)
    return normalized


def dependency_cycles(data):
    problems = []
    for kind, rows in (('goal', data['goals']), ('task', data['tasks'])):
        try:
            TopologicalSorter({row['id']: row.get('depends_on', []) for row in rows}).prepare()
        except CycleError as exc:
            problems.append(f'{kind} dependency cycle: ' + ' -> '.join(exc.args[1]))
    if problems:
        return problems
    # Goal completion waits for its tasks; each task also waits for its goal's
    # prerequisites. These edges can deadlock even when both ledgers are DAGs.
    goals = {g['id']: g for g in data['goals']}
    tasks = {t['id']: t for t in data['tasks']}
    active_tasks = {tid for tid, t in tasks.items() if t.get('status') not in ('done', 'superseded')}
    active_goals = {gid for gid, g in goals.items() if g.get('status') != 'met'
                    or not proven(g) or any(tasks[tid].get('goal') == gid for tid in active_tasks)}
    graph = {}
    for gid in active_goals:
        graph[('goal', gid)] = [('task', tid) for tid in active_tasks if tasks[tid].get('goal') == gid]
    for tid in active_tasks:
        task = tasks[tid]
        graph[('task', tid)] = ([('task', dep) for dep in task.get('depends_on', []) if dep in active_tasks] +
                               [('goal', dep) for dep in goals.get(task.get('goal'), {}).get('depends_on', [])
                                if dep in active_goals])
    try:
        TopologicalSorter(graph).prepare()
    except CycleError as exc:
        problems.append('cross-level dependency cycle: ' +
                        ' -> '.join(f'{kind} {identifier}' for kind, identifier in exc.args[1]))
    return problems


def errors(data, *, allow_pending_evidence=False):
    errs = shape_errors(data)
    if errs:
        return errs
    goals, tasks = data.get('goals'), data.get('tasks')
    gids = [g.get('id') for g in goals]; tids = [t.get('id') for t in tasks]
    if 'primary_milestone' in data:
        focus = data['primary_milestone']
        if not isinstance(focus, str) or not focus or focus not in gids:
            errs.append('primary_milestone must name an existing goal')
    for dup in {i for i in gids if gids.count(i) > 1} | {i for i in tids if tids.count(i) > 1}:
        errs.append(f'duplicate id {dup}')
    for g in goals:
        gid = g.get('id', '?')
        for k in ('id', 'title', 'source', 'status'):
            if not g.get(k):
                errs.append(f'{gid}: missing {k}')
        if g.get('status') not in GOAL_STATUS:
            errs.append(f'{gid}: status must be one of {GOAL_STATUS}')
        if g.get('status') == 'met' and not proven(g):
            errs.append(f'{gid}: met without executed+pass evidence (run fmt to downgrade to unverified)')
        for e in g.get('evidence', []):
            if e.get('kind') not in KINDS or e.get('result') not in RESULTS or not e.get('ref'):
                errs.append(f'{gid}: evidence needs kind {KINDS}, result {RESULTS} and ref')
        for d in g.get('depends_on', []):
            if d not in gids:
                errs.append(f'{gid}: depends_on unknown goal {d}')
        for t in g.get('tasks', []):
            if t not in tids:
                errs.append(f'{gid}: unknown task {t}')
        actual = {t.get('id') for t in tasks if t.get('goal') == gid}
        if actual != set(g.get('tasks', [])):
            errs.append(f'{gid}: task membership does not match ledger')
        open_tasks = [t for t in tasks if t.get('goal') == gid and t.get('status') != 'done']
        if g.get('status') == 'met' and open_tasks:
            errs.append(f'{gid}: met goal has unfinished tasks (run fmt to reopen)')
        if (g.get('status') != 'met' and not open_tasks
                and not (allow_pending_evidence and actual)):
            errs.append(f'{gid}: {g.get("status")} goal has no open task')
    for t in tasks:
        tid = t.get('id', '?')
        if not isinstance(tid, str) or re.fullmatch(TASK_ID, tid) is None:
            errs.append(f'invalid task ID {tid!r}: use letters, digits, underscores or hyphens; start with a letter or digit')
        for k in ('id', 'goal', 'title', 'status'):
            if not t.get(k):
                errs.append(f'{tid}: missing {k}')
        if t.get('goal') not in gids:
            errs.append(f'{tid}: unknown goal {t.get("goal")}')
        if t.get('status') not in TASK_STATUS:
            errs.append(f'{tid}: status must be one of {TASK_STATUS}')
        if t.get('section', 'Next') not in SECTIONS:
            errs.append(f'{tid}: section must be one of {SECTIONS}')
        for d in t.get('depends_on', []):
            if d not in tids:
                errs.append(f'{tid}: depends_on unknown task {d}')
    for tid in data.get('priority_order', {}).get('tasks', []):
        if tid not in tids:
            errs.append(f'priority_order names unknown task {tid}')
    for t in tasks:
        if t.get('status') == 'superseded':
            successors = t.get('superseded_by', [])
            if not successors or any(tid not in tids or tid == t['id'] for tid in successors):
                errs.append(f"{t['id']}: superseded_by must name other existing tasks")
            if not t.get('supersession_reason', '').strip():
                errs.append(f"{t['id']}: supersession_reason is required")
    if not errs and any(t['status'] == 'superseded' for t in tasks):
        try:
            TopologicalSorter({t['id']: t.get('depends_on', []) +
                               (t.get('superseded_by', []) if t['status'] == 'superseded' else [])
                               for t in tasks}).prepare()
        except CycleError:
            errs.append('task dependency/supersession cycle; reconcile successors and dependencies')
    if not errs:
        errs.extend(dependency_cycles(data))
    return errs


def checked_bytes(path):
    if path.is_symlink():
        sys.exit(f'refusing symlink: {path}')
    if path.exists() and not path.is_file():
        sys.exit(f'expected regular file: {path}')
    return path.read_bytes() if path.exists() else None


def revision(repo):
    digest = hashlib.sha256()
    for name in ('goals.json', 'TODO.md'):
        path = Path(repo) / name
        blob = checked_bytes(path)
        digest.update(name.encode() + b'\0')
        digest.update(b'missing\0' if blob is None else str(len(blob)).encode() + b'\0' + blob)
    return digest.hexdigest()


def git_identity(repo):
    """Return common Git directory and whether this is the primary checkout."""
    # Identity belongs to the explicit path, never an inherited Git session.
    # Drop all GIT_* settings (repository/index/object/discovery/config, including
    # numbered config keys) only in these child processes; keep PATH, HOME and
    # the rest of the caller environment, and do not mutate os.environ.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    def query(option):
        try:
            result = subprocess.run(['git', '-C', str(repo), 'rev-parse', option],
                                    capture_output=True, text=True, timeout=10, env=env)
        except FileNotFoundError:
            return None
        return result.stdout.strip() if result.returncode == 0 else None
    root = query('--show-toplevel')
    if root is None:
        if (repo / '.git').exists() or (repo / '.git').is_symlink():
            sys.exit('cannot resolve Git repository identity; refusing fixture fallback')
        return None
    if Path(root).resolve() != repo:
        sys.exit('repo must name the repository root')
    common, local = query('--git-common-dir'), query('--git-dir')
    if common is None or local is None:
        sys.exit('cannot resolve Git repository identity')
    common = (repo / common).resolve(strict=True)
    local = (repo / local).resolve(strict=True)
    return common, common == local


def backlog_authority(repo, identity):
    """Compatibility for older read-only callers; native bindings are retired."""
    return None


@contextmanager
def coordination(repo, canonical_repo=None, *, transaction):
    repo = Path(repo).resolve(strict=True)
    identity = git_identity(repo)
    if canonical_repo is not None:
        target = Path(canonical_repo).resolve(strict=True)
        target_identity = git_identity(target)
        if identity is None or target_identity is None or identity[0] != target_identity[0]:
            sys.exit('canonical target must be in the same repository')
        repo = target
    lock_dir = identity[0] if identity is not None else repo
    lock_path = lock_dir / '.docs-sync-goals.lock'
    if lock_path.is_symlink():
        sys.exit(f'refusing symlink lock: {lock_path}')
    fd = os.open(lock_path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        if git_identity(repo) != (target_identity if canonical_repo is not None else identity):
            sys.exit('Git repository identity changed while acquiring lock; retry current state')
        token = transaction.set((repo, revision(repo)))
        try:
            yield repo
        finally:
            transaction.reset(token)
            fcntl.flock(lock, fcntl.LOCK_UN)


def atomic_write(path, text, *, expected_bytes=UNSPECIFIED, transaction):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            if path.exists():
                os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        snapshot = transaction.get()
        if snapshot is not None and revision(snapshot[0]) != snapshot[1]:
            sys.exit(f'stale write: {path}; repository changed during command; no write')
        if expected_bytes is not UNSPECIFIED and checked_bytes(path) != expected_bytes:
            sys.exit(f'stale write: {path}; file changed during command; no write')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def dump(repo, data, *, write):
    write(path_of(repo), json.dumps(normalize(data), indent=2, sort_keys=True, ensure_ascii=False) + '\n')


NEW_ID_SOURCES = ('TODO.md', 'TODO.archive.md', 'todo.archive.md', 'docs/TODO-archive.md')


def known_ids(repo, data):
    """Every task-shaped token in the ledger, TODO and archives, so a new ID never reuses history."""
    ids = {t['id'] for t in (data or {}).get('tasks', []) if isinstance(t.get('id'), str)}
    for name in NEW_ID_SOURCES:
        blob = checked_bytes(Path(repo) / name)
        if blob is not None:
            ids.update(re.findall(r'(?<![\w-])[A-Za-z][A-Za-z0-9_]*-\d+(?:-[0-9a-f]{2})?(?![\w-])', blob.decode('utf-8', 'replace')))
    return ids


def new_task_id(repo, data, prefix=None):
    """Next number plus a two-hex-digit hash: collaborators who pick the same number still get distinct IDs."""
    ids = known_ids(repo, data)
    numbered = [m.groups() for m in (re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)-(\d+)(?:-[0-9a-f]{2})?', i) for i in ids) if m]
    if prefix is None:
        ledger = [m.group(1) for m in (re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)-\d+(?:-[0-9a-f]{2})?', t['id'])
                                       for t in (data or {}).get('tasks', [])) if m]
        pool = ledger or [p for p, _ in numbered]
        prefix = max(sorted(set(pool)), key=pool.count) if pool else 'T'
    if re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', prefix) is None:
        sys.exit('invalid prefix: use letters, digits or underscores; start with a letter; no write')
    numbers = [n for p, n in numbered if p == prefix]
    width = max([3] + [len(n) for n in numbers])
    number = str(max([0] + [int(n) for n in numbers]) + 1).zfill(width)
    for _ in range(64):
        digest = hashlib.sha256(f'{prefix}-{number}:{time.time_ns()}:{os.urandom(8).hex()}'.encode()).hexdigest()
        candidate = f'{prefix}-{number}-{digest[:2]}'
        if candidate not in ids:
            return candidate
    sys.exit(f'could not find an unused ID for {prefix}-{number}; no write')
