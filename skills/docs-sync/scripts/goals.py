#!/usr/bin/env python3
"""goals.json: the machine-readable goal list that docs-sync writes and autowork reads.

TODO.md stays the human view; its `Goal coverage` table is rendered from this file.
Agents change goals.json only through these commands, never by hand-editing JSON.

  goals.py init <repo> --intent JSON [--todo-file MARKDOWN]
                                                initialize from accepted intent and full task bodies; never overwrite
  goals.py propose <repo> --intent JSON [--todo-file MARKDOWN]
                                                first index without accepted sources: check as init would,
                                                save docs/tasks/proposed-goals.json, ask the owner in BLOCKERS.md
  goals.py accept <repo>                         on the owner's yes: mark the proposal's sources Accepted and init
  goals.py validate <repo>                       structural + evidence-rule check (exit 1 on errors)
  goals.py fmt <repo>                            canonical byte-stable rewrite (applies the "met" rule)
  goals.py next <repo> [--json]                  next eligible open task (dependencies satisfied);
                                                exit 3 with a PRIORITY_DRIFT report when TODO.md order changed
  goals.py reorder <repo>                        record TODO.md task order as the human priority (goals.json only)
  goals.py move <repo> <task> up|down            move an open task among its TODO.md group's open tasks
  goals.py place <repo> <task> <section>         move an open task to Now, Next or Needs decision (TODO.md and ledger)
  goals.py field <repo> <task> <label> <value>   set one single-line field of an open task's entry
                                                (TODO.md only; reorder records the new order)
  goals.py bootstrap-order <repo> [--dry-run]    one-time move of legacy priority into TODO.md order;
                                                apply requires --expected-revision from the dry run
  goals.py focus <repo> <GOAL>                   set the primary milestone without changing priorities
  goals.py focus <repo> --json                   read primary milestone without writing
  goals.py focus <repo> --clear                  remove focus and restore legacy selection order
  goals.py redact <repo> --replacements-file JSON --archive-dir PRIVATE
                                                redact historical refs/sources and render under one lock
  goals.py revision <repo>                       content token for goals.json and TODO.md
  goals.py merge-driver goals|todo|archive BASE OURS THEIRS
                                                Git low-level driver; writes OURS only, exits 1 on conflict
  goals.py merge-finalize <repo>                 rebuild order and coverage before committing a resolved merge
  goals.py render <repo>                         rewrite TODO.md's goal-coverage block from goals.json
  goals.py archive <repo> [--verified-tasks T1,T2]
                                                move closed task bodies to TODO.archive.md; keep ledger history
  goals.py backlog-check <repo> --plan path#heading --tasks T1,T2 [--receipt prior.json]
                                                read-only consumer-bound completion receipt (0 ready, 1 draft, 2 ineligible)
  Every command accepts --expected-revision TOKEN and --canonical-repo CHECKOUT.
  Explicit --canonical-repo targets another verified checkout of the same Git repository.
  Commands target the requested checkout; legacy native authority config is ignored.
  CLI operations lock the common Git directory (or a local no-Git fixture) before load.
  goals.py task <repo> <TASK> <open|in_progress|done>
  goals.py supersede <repo> <TASK> --by T1,T2 --reason TEXT
                                                retire without acceptance; render archives unchecked original history
  goals.py section <repo> <TASK> <Now|Next|Needs decision>
  goals.py new-id <repo> [--prefix P]           print an unused ID such as P-084-a7 (next number + 2-hex hash)
  goals.py add-task <repo> [TASK] --goal <GOAL> --title <text> [--section Now|Next|Needs decision] [--depends-on T1,T2]
                                                omit TASK to allocate one with new-id rules
  goals.py evidence <repo> <GOAL> --kind executed|inspection --ref <cmd/path> --result pass|fail [--ran-at ISO]

Rule (the met rule): a goal is `met` only with executed+pass evidence and all tasks done.
Fmt downgrades missing evidence to `unverified`, or reopens unfinished work as `partial`.
Superseded tasks never satisfy dependencies or the all-done met rule, even when
their successors finish. Explicit goal/dependency reconciliation remains required;
supersession is a disposition, not completion evidence.
Only version 1 ledgers are supported. Incompatible field shapes and duplicate JSON
keys are rejected before writing; formatting preserves additional metadata.
Next applies the same normalization in memory, then rejects invalid ledger state;
completed goals awaiting evidence remain dependency gates, not runnable work.
Optional `primary_milestone` names one existing goal. Its eligible tasks sort first,
even in Next; all eligible fallback tasks remain available after them in next --json.
"""
import argparse
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import date, datetime, timezone
import fcntl
from graphlib import CycleError, TopologicalSorter
import hashlib
import html
import importlib.util
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
BEGIN, END = '<!-- goals:coverage:begin -->', '<!-- goals:coverage:end -->'
TRANSACTION: ContextVar[tuple[Path, str] | None] = ContextVar('goals_transaction', default=None)
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
def coordination(repo, canonical_repo=None):
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
        token = TRANSACTION.set((repo, revision(repo)))
        try:
            yield repo
        finally:
            TRANSACTION.reset(token)
            fcntl.flock(lock, fcntl.LOCK_UN)


def atomic_write(path, text, *, expected_bytes=UNSPECIFIED):
    fd, name = tempfile.mkstemp(prefix='.' + path.name + '.', dir=path.parent)
    try:
        with os.fdopen(fd, 'w', encoding='utf-8', newline='') as stream:
            if path.exists():
                os.fchmod(stream.fileno(), path.stat().st_mode & 0o777)
            stream.write(text)
            stream.flush()
            os.fsync(stream.fileno())
        snapshot = TRANSACTION.get()
        if snapshot is not None and revision(snapshot[0]) != snapshot[1]:
            sys.exit(f'stale write: {path}; repository changed during command; no write')
        if expected_bytes is not UNSPECIFIED and checked_bytes(path) != expected_bytes:
            sys.exit(f'stale write: {path}; file changed during command; no write')
        os.replace(name, path)
    finally:
        if os.path.exists(name):
            os.unlink(name)


def dump(repo, data):
    atomic_write(path_of(repo), json.dumps(normalize(data), indent=2, sort_keys=True, ensure_ascii=False) + '\n')


def redact(repo, data, replacements_file, archive_dir):
    """Redact historical metadata, preserving original bytes outside the repo.

    This uses the existing cooperative lock/stale guard, not a crash-atomic
    two-file transaction or protection against writers ignoring the lock.
    """
    repo = Path(repo)
    replacements = json.loads(checked_bytes(Path(replacements_file)))
    if not isinstance(replacements, dict) or not replacements or any(
            not isinstance(k, str) or not Path(k).is_absolute()
            or not isinstance(v, str) or not v or Path(v).is_absolute()
            for k, v in replacements.items()):
        sys.exit('replacements must map absolute literal prefixes to nonempty portable placeholders')
    if any(prefix in value for prefix in replacements for value in replacements.values()):
        sys.exit('portable placeholders must not contain replacement prefixes')
    archive = Path(archive_dir).resolve()
    if archive == repo or repo in archive.parents:
        sys.exit('archive directory must be outside repository')
    # One pass, longest literal first: overlapping mappings never cascade.
    pattern = re.compile('|'.join(re.escape(k) for k in sorted(replacements, key=len, reverse=True)))
    changed = False
    for goal in data['goals']:
        source = goal.get('source')
        if isinstance(source, str):
            new = pattern.sub(lambda m: replacements[m.group()], source)
            changed |= new != source
            goal['source'] = new
        for entry in goal.get('evidence', []):
            ref = entry.get('ref')
            if isinstance(ref, str):
                new = pattern.sub(lambda m: replacements[m.group()], ref)
                if new != ref:
                    entry['ref'] = new
                    entry['redacted'] = True
                    changed = True
    if not changed:
        print('ok no redaction needed'); return
    # Validate the second write before changing the ledger. A malformed TODO
    # must not leave a partially redacted pair that becomes a no-op on retry.
    render_text(repo, data)
    originals = {n: checked_bytes(repo / n) for n in ('goals.json', 'TODO.md')}
    token = TRANSACTION.get()[1]
    destination = archive / token
    if destination.is_symlink():
        sys.exit('refusing symlink archive revision directory')
    destination.mkdir(parents=True, exist_ok=True, mode=0o700)
    hashes = {}
    for name, blob in originals.items():
        hashes[name] = hashlib.sha256(blob).hexdigest() if blob is not None else None
        path = destination / name
        existing = checked_bytes(path)
        if existing is not None and existing != blob:
            sys.exit(f'archive mismatch: {path}; no write')
        if blob is not None:
            if existing is None:
                atomic_write(path, blob.decode('utf-8'))
            if checked_bytes(path) != blob:
                sys.exit(f'archive verification failed: {path}; no write')
    manifest = json.dumps({'revision': token, 'sha256': hashes}, indent=2, sort_keys=True) + '\n'
    path = destination / 'manifest.json'
    existing = checked_bytes(path)
    if existing is not None and existing != manifest.encode():
        sys.exit(f'archive mismatch: {path}; no write')
    atomic_write(path, manifest)
    if checked_bytes(path) != manifest.encode():
        sys.exit('archive manifest verification failed; no write')
    # Do not normalize: redaction must not change status, ordering or other metadata.
    output = json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
    atomic_write(path_of(repo), output)
    # Advance only to our exact expected bytes, never bless an intervening edit.
    digest = hashlib.sha256()
    for name, blob in (('goals.json', output.encode()), ('TODO.md', originals['TODO.md'])):
        digest.update(name.encode() + b'\0')
        digest.update(b'missing\0' if blob is None else str(len(blob)).encode() + b'\0' + blob)
    TRANSACTION.set((repo, digest.hexdigest()))
    render(repo, data, archive=False)
    print(f'ok redacted historical metadata; originals archived at {destination}')


def todo_text(repo):
    blob = checked_bytes(Path(repo) / 'TODO.md')
    return blob.decode('utf-8') if blob is not None else ''


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


def eligible(data):
    goals = {g['id']: g for g in data['goals']}
    tasks = {t['id']: t for t in data['tasks']}
    record = data.get('priority_order')
    order = {tid: index for index, tid in enumerate(record['tasks'])} if record else {}
    out = []
    for t in data['tasks']:
        g = goals.get(t['goal'])
        if t['status'] in ('done', 'superseded') or t.get('section') not in SECTION_RANK or not g or g['status'] == 'met':
            continue
        if any(tasks.get(d, {}).get('status') != 'done' for d in t['depends_on']):
            continue
        if any(goals.get(d, {}).get('status') != 'met' for d in g['depends_on']):
            continue
        focus_rank = 0 if g['id'] == data.get('primary_milestone') else 1
        # Recorded human order outranks goal priority; unrecorded tasks fall back to it.
        human_rank = order.get(t['id'], len(order))
        out.append((focus_rank, SECTION_RANK[t['section']], human_rank, g['priority'],
                    STATUS_RANK[g['status']], t['id'], t, g))
    return [(t, g) for *_, t, g in sorted(out, key=lambda r: r[:6])]


UNMIGRATED_ACTION = ('UNMIGRATED: TODO.md order is not recorded; legacy goal-priority selection applies. '
                     'Run `goals.py bootstrap-order <repo> --dry-run`, then apply with its revision.')
DRIFT_ACTION = ('Reconcile the human order with `goals.py reorder <repo> --expected-revision <revision>`, '
                'then select again. Do not execute the stale order.')


def active_task_ids(data):
    return {t['id'] for t in data['tasks'] if t.get('status') in ('open', 'in_progress')}


def priority_status(data, text):
    """Compare TODO.md's unfinished-task sequence with the last reconciled record."""
    record = data.get('priority_order')
    if not record:
        return {'state': 'unmigrated', 'action': UNMIGRATED_ACTION}
    active = active_task_ids(data)
    bodies = task_bodies(text)
    current = [tid for tid in bodies if tid in active]
    recorded = [tid for tid in record['tasks'] if tid in active]
    duplicates = sorted(tid for tid in current if len(bodies[tid]) > 1)
    if current == recorded and not duplicates:
        return {'state': 'synced'}
    shared = [tid for tid in current if tid in recorded]
    moved = sorted(tid for tid in shared if shared.index(tid) != [r for r in recorded if r in shared].index(tid))
    return {'state': 'drift', 'todo_order': current, 'recorded_order': recorded, 'moved': moved,
            'added': [tid for tid in current if tid not in recorded],
            'missing': [tid for tid in recorded if tid not in current],
            'duplicates': duplicates, 'action': DRIFT_ACTION}


class PriorityDrift(ValueError):
    def __init__(self, status):
        self.status = status
        super().__init__('PRIORITY_DRIFT: TODO.md order differs from the recorded priority order '
                         f"(todo {status['todo_order']}, recorded {status['recorded_order']}). " + status['action'])


def queue(data, text, *, allow_drift=False):
    """The shared selection guard: eligible work plus the priority state it was ranked under."""
    status = priority_status(data, text)
    if status['state'] == 'drift' and not allow_drift:
        raise PriorityDrift(status)
    return eligible(data), status


def selection_notes(data, order):
    """Explain why the human's first pick does not run first; never change the order."""
    picks = eligible(data)
    tasks = {t['id']: t for t in data['tasks']}
    top = next((tid for tid in order if tasks.get(tid, {}).get('status') == 'open'), None)
    if top is None or (picks and picks[0][0]['id'] == top):
        return []
    first = picks[0][0]['id'] if picks else None
    focus = data.get('primary_milestone')
    if top not in {t['id'] for t, _ in picks}:
        reason = f"{top} is first in TODO.md but not eligible (section {tasks[top]['section']} or an unmet dependency)"
    elif focus and tasks[first]['goal'] == focus and tasks[top]['goal'] != focus:
        reason = f'{top} is first in TODO.md but focus {focus} selects {first} first'
    else:
        reason = f'{top} is first in TODO.md but section order selects {first} first'
    return [reason + '; recorded order kept as written.']


def reconcile_order(data, text):
    """Return the record for TODO.md's current order, or raise on unsafe input."""
    if not data.get('priority_order'):
        sys.exit(json.dumps({'outcome': 'UNMIGRATED', 'action': UNMIGRATED_ACTION}))
    status = priority_status(data, text)
    if status['state'] == 'drift' and (status['missing'] or status['duplicates']):
        sys.exit(json.dumps({'outcome': 'PRIORITY_CONFLICT', 'missing': status['missing'],
                             'duplicates': status['duplicates'],
                             'action': 'Restore exactly one TODO.md body per unfinished task before reconciling.'}))
    active = active_task_ids(data)
    order = [tid for tid in task_bodies(text) if tid in active]
    return {'schema': PRIORITY_SCHEMA, 'tasks': order}, status


def task_blocks(text):
    """Movable task blocks: an ID heading or checkbox up to the next block in its group.

    A group is a `##` section, or a heading inside it that is not a task's own ID
    heading (for example `### P2 — Parity`). Blocks never move across a group heading.
    """
    prose = task_prose(text)
    marks = list(re.finditer(TASK_MARK, prose, re.M))
    own = {block_start(prose, mark) for mark in marks}
    sections, section, level = [], '', 2
    for m in re.finditer(r'^(#{2,6})[ \t]+(.+)$', prose, re.M):
        if len(m[1]) == 2:
            section, level = m[2].strip(), 2
            sections.append((m.start(), section))
        elif m.start() not in own and len(m[1]) <= max(3, level):
            # A sibling or parent group. A deeper heading (#### Evidence) is the
            # preceding task's own subsection and moves with it.
            level = len(m[1])
            sections.append((m.start(), f'{section} / {m[2].strip()}'))
    blocks = []
    for mark in marks:
        region = max((s for s in sections if s[0] < mark.start()), default=(0, ''))
        start = block_start(prose, mark, region[0])
        blocks.append({'id': mark[2], 'mark': mark[1], 'start': start, 'region': region})
    for index, block in enumerate(blocks):
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        ends = [s for s, _ in sections if s > block['start']]
        region_end = ends[0] if ends else len(text)
        block['end'] = following['start'] if following and following['region'] == block['region'] \
            and following['start'] < region_end else region_end
        chunk = text[block['start']:block['end']]
        core = chunk.rstrip()
        block['core'], block['sep'] = core, chunk[len(core):]
        inner = task_prose(chunk).split('\n')[1:]
        # Deeper subsections belong to the task; a group-level heading here is ambiguous.
        block['foreign_heading'] = any(re.match(r'#{1,3}[ \t]', line) for line in inner)
    return blocks


def legacy_rank(data):
    """Pre-migration ranking of every unfinished task, excluding focus and dependencies."""
    goals = {g['id']: g for g in data['goals']}
    def key(task):
        g = goals[task['goal']]
        return (SECTIONS.index(task['section']), g['priority'], STATUS_RANK[g['status']], task['id'])
    return sorted((t for t in data['tasks'] if t['status'] in ('open', 'in_progress')), key=key)


def bootstrap_plan(data, text):
    tasks = {t['id']: t for t in data['tasks']}
    active = active_task_ids(data)
    bodies = task_bodies(text)
    reasons = []
    for tid in sorted(active):
        found = bodies.get(tid, [])
        if len(found) != 1:
            reasons.append(f'{tid}: needs exactly one TODO.md body (found {len(found)})')
        elif found[0][2] != tasks[tid]['section']:
            reasons.append(f"{tid}: TODO.md section {found[0][2] or 'none'} differs from ledger section {tasks[tid]['section']}")
    blocks = task_blocks(text)
    rank = {t['id']: index for index, t in enumerate(legacy_rank(data))}
    regions, output, cursor = [], [], 0
    by_region = {}
    for block in blocks:
        by_region.setdefault(block['region'], []).append(block)
    for region, members in sorted(by_region.items()):
        slots = [b for b in members if b['id'] in active and b['mark'] == ' ']
        target = sorted(slots, key=lambda b: rank[b['id']])
        if [b['id'] for b in slots] != [b['id'] for b in target]:
            regions.append({'heading': region[1], 'before': [b['id'] for b in slots],
                            'after': [b['id'] for b in target]})
            reasons.extend(f"{b['id']}: block contains another heading; reorder this section manually"
                           for b in slots if b['foreign_heading'])
        replacement = dict(zip((id(b) for b in slots), target))
        for block in members:
            moved = replacement.get(id(block), block)
            output.append(text[cursor:block['start']] + moved['core'] + block['sep'])
            cursor = block['end']
    new_text = ''.join(output) + text[cursor:]
    if sorted(b['core'] for b in blocks) != sorted(b['core'] for b in task_blocks(new_text)):
        reasons.append('task block bytes would change; refusing reorder')
    order = [tid for tid in task_bodies(new_text) if tid in active]
    migrated = dict(data, priority_order={'schema': PRIORITY_SCHEMA, 'tasks': order})
    before_picks = [t['id'] for t, _ in eligible(data)]
    after_picks = [t['id'] for t, _ in eligible(migrated)]
    if not reasons and before_picks[:1] != after_picks[:1]:
        reasons.append(f'first eligible pick would change ({before_picks[:1]} -> {after_picks[:1]}); '
                       'legacy order is not representable within TODO.md groups')
    # Keeping owner-written groups can move deeper tasks; report each one for review.
    changes = [{'task': tid, 'position_before': before_picks.index(tid) + 1,
                'position_after': after_picks.index(tid) + 1}
               for tid in before_picks if tid in after_picks and before_picks.index(tid) != after_picks.index(tid)]
    return {'reasons': reasons, 'regions': regions, 'text': new_text, 'record': migrated['priority_order'],
            'next_before': before_picks[:1], 'next_after': after_picks[:1], 'eligible_order_changes': changes}

def render_text(repo, data, text=None):
    def cell(value):
        return (html.escape(value, quote=False).replace('|', '&#124;').replace('`', '&#96;')
                .replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>'))

    tasks = {t['id']: t for t in data['tasks']}
    rows = ['| Goal | Status | Evidence | Task |', '| --- | --- | --- | --- |']
    def evidence_cell(entry):
        if 'summary' in entry:
            summary = cell(entry['summary'])
            if entry.get('task') and entry.get('archive'):
                # Archive links are authored by evidence(), not arbitrary scratch refs.
                from urllib.parse import quote
                anchor = entry.get('anchor', entry['task'].lower())
                target = quote(entry['archive'], safe='/.-_') + ('#' + quote(anchor, safe='-_.') if anchor else '')
                return summary + f" ([{cell(entry['task'])}]({target}))"
            return summary
        return (cell(entry['kind']) + (' (redacted historical evidence)' if entry.get('redacted') else '')
                + f" <code>{cell(entry['ref'])}</code> → {cell(entry['result'])}")

    for g in data['goals']:
        compact = [e for e in g['evidence'] if 'summary' in e and e.get('coverage_current') is True]
        # Keep an explicit identity: canonical evidence sorting is not recency.
        # Untouched legacy goals retain their existing rows and full refs.
        visible = compact if compact else g['evidence']
        ev = '; '.join(evidence_cell(e) for e in visible) or '—'
        open_t = [t for t in g['tasks'] if tasks.get(t, {}).get('status') not in ('done', 'superseded')]
        rows.append(f"| {cell(g['id'])}: {cell(g['title'])} | {cell(g['status'])} | {ev} | {cell(', '.join(open_t)) or '—'} |")
    block = '\n'.join([BEGIN, '', 'Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.', '', *rows, '', END])
    todo = Path(repo) / 'TODO.md'
    if text is None:
        text = todo.read_bytes().decode('utf-8') if todo.exists() else '# TODO\n\n## Goal coverage\n\n'
    prose = markdown_prose(text)
    begins = list(re.finditer(re.escape(BEGIN), prose))
    ends = list(re.finditer(re.escape(END), prose))
    headings = list(re.finditer(r'^##[ \t]+Goal coverage[ \t]*\r?$', prose, re.M))
    if begins or ends:
        if len(begins) != 1 or len(ends) != 1 or begins[0].start() >= ends[0].start():
            sys.exit('ambiguous coverage markers in TODO.md; reconcile their boundaries; no write')
        text = text[:begins[0].start()] + block + text[ends[0].end():]
    elif headings:
        if len(headings) != 1:
            sys.exit('multiple Goal coverage sections in TODO.md; choose the maintained section; no write')
        heading = headings[0]
        # Replace only up to the next heading of any level: a following `### Decisions log`
        # is owner content, not part of the legacy table, and must stay byte-identical.
        nxt = re.search(r'\n#{1,6}[ \t]+', prose[heading.end():])
        rest = text[heading.end() + nxt.start():] if nxt else '\n'
        text = text[:heading.end()] + '\n\n' + block + '\n' + rest
    else:
        text = text + '\n\n## Goal coverage\n\n' + block + '\n'
    return text


def archive_tasks(repo, data, *, render_coverage=False, verified_tasks=()):
    """Save and verify history before removing live bodies, under coordination()."""
    spec = importlib.util.spec_from_file_location('docs_sync_todo_archive', Path(__file__).with_name('todo_archive.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if data is not None:
        problems = errors(normalize(data), allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
    todo = Path(repo) / 'TODO.md'
    before = checked_bytes(todo)
    text = before.decode('utf-8') if before is not None else '# TODO\n\n'
    if data is not None:
        # Archival must not hide an invalid generated region inside a moved body.
        render_text(repo, data, text)
    plan = module.prepare(repo, data, text, mask=task_prose, checked_bytes=checked_bytes,
                          verified_tasks=verified_tasks,
                          boundaries=[m.start() for m in re.finditer(re.escape(BEGIN), markdown_prose(text))])
    output = render_text(repo, data, plan['text']) if render_coverage else plan['text']
    if plan['archive']:
        path = plan['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        expected = plan['after'].encode('utf-8')
        if plan['before'] != expected:
            atomic_write(path, plan['after'], expected_bytes=plan['before'])
        if checked_bytes(path) != expected:
            sys.exit('archive verification failed; TODO.md retained; retry after reconciliation')
    if output.encode('utf-8') != before and (before is not None or render_coverage):
        atomic_write(todo, output, expected_bytes=before)
    return {key: plan[key] for key in ('moved', 'retained', 'archive')}


def render(repo, data, *, archive=True):
    if archive:
        return archive_tasks(repo, data, render_coverage=True)
    atomic_write(Path(repo) / 'TODO.md', render_text(repo, data))


def markdown_prose(text):
    """Mask fenced examples without changing offsets used for clerical repairs."""
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        if fence is not None:
            lines.append(re.sub(r'[^\r\n]', ' ', line))
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) +
                            '{' + str(len(fence)) + r',}[ \t]*(?:\r?\n)?', line):
                fence = None
            continue
        opening = re.match(r' {0,3}(`{3,}|~{3,})([^\r\n]*)', line)
        if opening and not (opening[1][0] == '`' and '`' in opening[2]):
            fence = opening[1]
            lines.append(re.sub(r'[^\r\n]', ' ', line))
        else:
            lines.append(line)
    return ''.join(lines)


def reference_key(ref):
    """Normalize harmless local spelling differences, never traversal or URLs."""
    name, separator, anchor = ref.partition('#')
    path = Path(name or 'TODO.md')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref) or path.is_absolute() or '..' in path.parts:
        return ref
    return path.as_posix() + separator + anchor


def plan_acceptance_error(section):
    """One explicit status is required; conflicting metadata is not acceptance."""
    statuses = re.findall(r'^[ \t]*(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)',
                          markdown_prose(section), re.M | re.I)
    if len(statuses) > 1:
        return 'plan section has conflicting or duplicate Status metadata'
    if len(statuses) != 1 or statuses[0].strip().lower() != 'accepted':
        return 'plan section lacks explicit Status: Accepted'
    return ''


def heading_rows(text):
    """(anchor, start, end, level) of each Markdown heading in fence-masked text."""
    headings = []
    counts = {}
    for match in re.finditer(r'^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*\r?$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', match[2].lower()).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        headings.append((slug + (f'-{count}' if count else ''), match.start(), match.end(), len(match[1])))
    return headings


def local_reference(repo, ref, blobs, reasons, *, include_children=False):
    """Resolve maintained links; optionally return the raw full heading subtree.

    Acceptance metadata belongs to the heading's introduction. Scope recovery
    must compare all descendants, including fenced examples, byte for byte.
    """
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref):
        return ''  # Remote sources are not locally qualified.
    name, _, anchor = ref.partition('#')
    path = Path(name or 'TODO.md')
    if path.is_absolute() or '..' in path.parts:
        reasons.append(f'nonlocal reference {ref}')
        return ''
    for parent in (path, *path.parents):
        if (repo / parent).is_symlink():
            reasons.append(f'symlink reference {ref}')
            return ''
    name = path.as_posix()
    if name not in blobs:
        blobs[name] = checked_bytes(repo / path)
    blob = blobs[name]
    if blob is None:
        reasons.append(f'missing reference {ref}')
        return ''
    if not anchor:
        return markdown_prose(blob.decode('utf-8')) if path.suffix.lower() in ('.md', '.markdown') else ''
    text = markdown_prose(blob.decode('utf-8'))
    headings = heading_rows(text)
    found = next((i for i, row in enumerate(headings) if row[0] == anchor), None)
    if found is None:
        reasons.append(f'missing anchor {ref}')
        return ''
    end = next((row[1] for row in headings[found + 1:]
                if not include_children or row[3] <= headings[found][3]), len(text))
    source = blob.decode('utf-8') if include_children else text
    return source[headings[found][2]:end]


def task_prose(text):
    """Ignore examples and generated coverage while retaining source offsets."""
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END),
                  lambda m: re.sub(r'[^\r\n]', ' ', m[0]), markdown_prose(text), flags=re.S)


CHECK_LABELS = ('Checks', 'Verification')


def task_checks(fields):
    """A task's verification commands; `Verification:` is an accepted spelling of `Checks:`."""
    present = [label for label in CHECK_LABELS if fields.get(label)]
    return fields[present[0]] if len(present) == 1 else None


def task_fields(body):
    """Read maintained fields, including continued Sources and header-inline Goal."""
    body = task_prose(body)
    matches = list(re.finditer(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):(?:\*\*)?[ \t]*', body, re.M))
    fields = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        value = body[match.end():end].strip()
        if value:
            fields.setdefault(match[1], []).append(value)
    inline = re.match(r'^\s*[—–-]\s+Goal:[ \t]*(\S[^\n]*)', body)
    if inline:
        fields.setdefault('Goal', []).append(inline[1])
    return {label: values[0] for label, values in fields.items() if len(values) == 1}


TASK_MARK = r'^[-*] \[([ xX])\]\s+(?:\*\*)?`?([A-Za-z0-9][A-Za-z0-9_-]*)`?(?:\*\*)?(?=\s|:)'


def block_start(prose, mark, floor=0):
    """A task block begins at its own ID heading when one directly precedes the checkbox."""
    before = prose[floor:mark.start()].rstrip()
    last_line = before.rsplit('\n', 1)[-1]
    if re.match(r'#{3,6}[ \t]', last_line) and re.search(
            r'(?<![\w-])' + re.escape(mark[2]) + r'(?![\w-])', last_line):
        return floor + len(before) - len(last_line)
    return mark.start()


def task_bodies(text):
    """Only checkbox entries outside generated coverage are task contracts."""
    prose = task_prose(text)
    matches = list(re.finditer(TASK_MARK, prose, re.M))
    bodies = {}
    for i, match in enumerate(matches):
        # The next task's own ID heading belongs to that task, not this body's last field.
        end = block_start(prose, matches[i + 1], match.end()) if i + 1 < len(matches) else len(text)
        section_end = re.search(r'^##\s', prose[match.end():end], re.M)
        if section_end:
            end = match.end() + section_end.start()
        block = text[match.end():end]
        # Trim CRLF `\r` and trailing blanks so `## Now \r` names the ledger section `Now`.
        sections = re.findall(r'^##[ \t]+([^\r\n]*)', prose[:match.start()], re.M)
        section = sections[-1].strip() if sections else ''
        if section == 'Now / Next':
            explicit = re.findall(r'(?:^|\.\s+)Section:[ \t]*(Now|Next|Needs decision)(?=\.|\s*$)', prose[match.end():end], re.M)
            if len(explicit) == 1:
                section = explicit[0]
        bodies.setdefault(match[2], []).append((block, match[1], section))
    return bodies


def deferred_tasks(bodies):
    """Owner-answered deferrals from parsed TODO bodies, not unanswered decisions."""
    deferred = set()
    for task, entries in bodies.items():
        if len(entries) != 1:
            continue
        body, mark, section = entries[0]
        if section != 'Needs decision' or mark.lower() == 'x':
            continue
        decision = task_fields(body).get('Owner decision', '')
        stamp = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', decision)
        if stamp:
            try:
                date.fromisoformat(stamp[1])
            except ValueError:
                continue
            deferred.add(task)
    return deferred


def backlog_receipt(a, *, candidate=None):
    """Check consumer contracts; candidate bytes are only for init preflight."""
    repo = Path(a.repo)
    blobs = {name: checked_bytes(repo / name) for name in ('TODO.md', 'goals.json')}
    if candidate is not None:
        blobs.update(candidate)
    reasons = [f'missing {name}' for name, blob in blobs.items() if blob is None]
    identity = git_identity(repo)
    if identity is None and candidate is None:
        reasons.append('unbound non-Git fixture is not consumer authority')
    plan_path, _, anchor = a.plan.partition('#')
    plan = repo / plan_path
    if not plan_path or Path(plan_path).is_absolute() or '..' in Path(plan_path).parts:
        reasons.append('plan must be repo-relative')
    else:
        if plan_path not in blobs:
            blobs[plan_path] = checked_bytes(plan)
        if blobs[plan_path] is None:
            reasons.append('missing accepted plan')
    ids = a.tasks.split(',')
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', tid) for tid in ids):
        reasons.append('tasks must name unique existing IDs without normalization')
    if not anchor:
        reasons.append('accepted plan requires a heading anchor')
    if plan_path and not Path(plan_path).is_absolute() and '..' not in Path(plan_path).parts:
        decision = local_reference(repo, a.plan, blobs, reasons)
        acceptance_error = plan_acceptance_error(decision)
        if acceptance_error:
            reasons.append(acceptance_error)
        for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', decision):
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref):
                name, separator, heading = ref.partition('#')
                resolved = os.path.normpath(Path(plan_path).parent / name) if name else plan_path
                local_reference(repo, resolved + (separator + heading if separator else ''), blobs, reasons)
    picks = []
    data = None
    priority = {'state': 'unknown'}
    if blobs['goals.json'] is not None:
        try:
            ledger_blob = blobs['goals.json']
            assert ledger_blob is not None
            data = parse_ledger(ledger_blob)
            ledger_errors = errors(data)
            reasons.extend(ledger_errors)
            if ledger_errors:
                data = None
            else:
                data = normalize(data)
                if not reasons:
                    ranked, priority = queue(data, (blobs['TODO.md'] or b'').decode('utf-8'), allow_drift=True)
                    picks = [t['id'] for t, _ in ranked]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            reasons.append(f'invalid backlog: {exc}')
            data = None
    # Plan metadata and task contracts are independent repairable inputs. Report
    # both in one pass, but never turn a partial diagnostic into readiness.
    if data is not None and blobs['TODO.md'] is not None:
        todo_blob = blobs['TODO.md']
        assert todo_blob is not None
        bodies = task_bodies(todo_blob.decode('utf-8'))
        known = {t['id'] for t in data['tasks']}
        goals_by_id = {g['id']: g for g in data['goals']}
        dependency_ids = known | goals_by_id.keys()
        # Goal IDs predate TASK_ID and may contain punctuation or spaces. Keep
        # their exact legacy matching, compiling only those exceptional IDs once.
        non_token_goals = {gid: re.compile(r'(?<![\w-])' + re.escape(gid) + r'(?![\w-])')
                           for gid in goals_by_id if re.fullmatch(r'[\w-]+', gid) is None}
        for tid, entries in bodies.items():
            if tid not in known and any(mark == ' ' and section in SECTION_RANK
                                       for _, mark, section in entries):
                reasons.append(f'{tid}: executable body has no ledger task')
        for t in data['tasks']:
            tid = t['id']
            entries = bodies.get(tid, [])
            if t['status'] == 'superseded':
                continue  # Explicitly retired bodies can retain unchecked history in the archive.
            if t['status'] == 'done':
                if any(mark == ' ' for _, mark, _ in entries):
                    reasons.append(f'{tid}: checkbox/section does not match done ledger task')
                continue
            if len(entries) != 1:
                reasons.append(f'{tid}: missing or duplicate task body')
                continue
            body, checked, section = entries[0]
            fields = task_fields(body)
            for label in ('Goal', 'Scope', 'Acceptance', 'Dependencies', 'Sources'):
                if label not in fields:
                    reasons.append(f'{tid}: missing {label}')
            if not re.match(r'`?' + re.escape(t['goal']) + r'`?(?:[.\s]|$)', fields.get('Goal', '')):
                reasons.append(f'{tid}: Goal does not match ledger')
            if checked != ' ' or section != t.get('section', 'Next'):
                reasons.append(f'{tid}: checkbox/section does not match ledger')
            goal = goals_by_id[t['goal']]
            expected = set(t.get('depends_on', []) + goal.get('depends_on', []))
            dependencies = fields.get('Dependencies', '')
            # An explicit None declaration can be followed by coordination or
            # history, not executable prerequisites. Do not let those notes
            # invent edges or satisfy a missing ledger dependency. Keep full
            # matching for actual prerequisite lists, including numbered lists.
            if re.match(r'none\b', dependencies, re.I):
                dependencies = re.split(r'\.(?:\s|$)', dependencies, maxsplit=1)[0]
            # Tokens preserve the old (?<![\w-])ID(?![\w-]) boundaries for task
            # and simple goal IDs; exceptional goal IDs use the compiled fallback.
            # Parse the field once; scanning every known ID per task is quadratic
            # and thrashes Python's regex cache on large backlogs.
            named = set(re.findall(r'[\w-]+', dependencies)) & dependency_ids
            named.update(gid for gid, pattern in non_token_goals.items() if pattern.search(dependencies))
            for dep in sorted(expected - named):
                reasons.append(f'{tid}: Dependencies do not name {dep}')
            for dep in sorted(named - expected):
                reasons.append(f'{tid}: Dependencies name {dep} absent from ledger')
            sources = re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', fields.get('Sources', ''))
            if tid in ids and reference_key(a.plan) not in {reference_key(ref) for ref in sources}:
                reasons.append(f'{tid}: Sources do not link accepted plan')
            for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', task_prose(body)):
                local_reference(repo, ref, blobs, reasons)
        for g in data['goals']:
            local_reference(repo, g['source'], blobs, reasons)
    ineligible = []
    if data is not None and not reasons:
        tasks = {t['id']: t for t in data['tasks']}
        goals = {g['id']: g for g in data['goals']}
        for tid in ids:
            t = tasks.get(tid)
            if t is None:
                reasons.append(f'unknown task {tid}')
                continue
            g = goals[t['goal']]
            if tid not in picks:
                ineligible.append(f'{tid}: not eligible (status={t["status"]}, section={t["section"]}, goal={g["status"]})')
            if t['status'] == 'in_progress':
                ineligible.append(f'{tid}: already in progress')
            for dep in t.get('depends_on', []):
                if tasks[dep]['status'] != 'done':
                    ineligible.append(f'{tid}: unmet task dependency {dep}')
            for dep in g.get('depends_on', []):
                if goals[dep]['status'] != 'met':
                    ineligible.append(f'{tid}: unmet goal dependency {dep}')
        # In-progress work is reconciled separately. A named plan checks its own
        # goals' ordered frontier, not unrelated goals in the global queue.
        # Explicit task scope, current source and actual writer checks still apply;
        # metadata readiness does not grant execution or publication authority.
        requested_goals = {tasks[tid]['goal'] for tid in ids if tid in tasks}
        open_picks = [tid for tid in picks if tasks[tid]['status'] == 'open'
                      and tasks[tid]['goal'] in requested_goals]
        if open_picks and open_picks[0] not in ids:
            ineligible.append(f'current frontier {open_picks[0]} precedes requested plan')
        if priority['state'] == 'drift':
            ineligible.append('priority drift: TODO.md order differs from the recorded order; run goals.py reorder')
    if git_identity(repo) != identity:
        reasons.append('Git repository identity changed during check')
    binding = {'git_common_dir': str(identity[0]) if identity else None,
               'registered_authority': None}
    if any(checked_bytes(repo / name) != blob for name, blob in blobs.items()
           if candidate is None or name not in candidate):
        reasons.append('inputs changed during check')
    state = ('draft_saved' if reasons else 'backlog_reconciled_not_eligible'
             if ineligible else 'ready_for_autowork')
    receipt = {'state': state, 'authority_binding': binding,
               'authoritative_repo': str(repo), 'plan': a.plan, 'task_ids': ids,
               'primary_milestone': data.get('primary_milestone') if data else None,
               'focus_fallback_required': bool(data and data.get('primary_milestone')
                    and any(t['id'] in ids and t['goal'] != data['primary_milestone']
                            for t in data['tasks'])),
               'eligible_task_ids': picks, 'live_ownership': 'unknown',
               'priority_state': priority['state'],
               'sha256': {name: hashlib.sha256(blob).hexdigest() if blob is not None else None
                          for name, blob in blobs.items()}, 'reasons': reasons + ineligible}
    if a.receipt:
        try:
            previous = json.loads(checked_bytes(Path(a.receipt)))
        except (ValueError, TypeError, OSError):
            previous = None
        if previous != receipt:
            reasons.append('stale receipt')
            receipt['state'] = 'draft_saved'
            receipt['reasons'] = reasons + ineligible
    return (1 if reasons else 2 if ineligible else 0), receipt


def backlog_check(a):
    """Check the consumer, not the author's fixture; never mutate the backlog."""
    code, receipt = backlog_receipt(a)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return code


def initialize(a):
    """Create only after all input/consumer checks; repeats never rewrite bytes."""
    repo = Path(a.repo)
    try:
        intent_path = Path(a.intent)
        intent_blob = checked_bytes(intent_path)
        if intent_blob is None:
            sys.exit('missing intent file; supply version-1 accepted goal/task intent')
        data = parse_ledger(intent_blob)
        problems = errors(data)
        if problems:
            sys.exit('\n'.join(problems) + '\ninit refused; no write')
        if not data['goals'] or not data['tasks']:
            sys.exit('init requires accepted goals and complete task intent; no write')
        # Normalize a copy; compare full objects including extension metadata.
        normalized = normalize(json.loads(json.dumps(data)))
        ledger = json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
        original_todo = checked_bytes(repo / 'TODO.md')
        supplied = checked_bytes(Path(a.todo_file)) if a.todo_file else None
        if a.todo_file and supplied is None:
            sys.exit('missing --todo-file input; no write')
        if original_todo is not None and supplied is not None and original_todo != supplied:
            sys.exit('existing TODO.md conflicts with --todo-file; reconcile intent; no write')
        todo = original_todo if original_todo is not None else supplied
        if todo is None:
            sys.exit('missing TODO.md; supply complete task bodies with --todo-file; no write')
        text = todo.decode('utf-8')
        # Rendering is separate, but reject unsafe coverage before any write.
        render_text(repo, normalized, text)
        bodies = task_bodies(text)
        for task in normalized['tasks']:
            if task['status'] in ('done', 'superseded'):
                continue  # Closed or superseded history may live in the established archive.
            entries = bodies.get(task['id'], [])
            if len(entries) == 1:
                fields = task_fields(entries[0][0])
                if not fields.get('Ownership'):
                    sys.exit(f'{task["id"]}: missing Ownership; no write')
                statuses = re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)',
                                      task_prose(entries[0][0]), re.M)
                if statuses and (len(statuses) != 1 or statuses[0].strip() != task['status']):
                    sys.exit(f'{task["id"]}: Status conflicts with intent; no write')
        candidate = {'goals.json': ledger.encode('utf-8'), 'TODO.md': todo}
        candidate.update(getattr(a, 'sources', None) or {})  # propose: sources as acceptance would leave them
        sources = {}
        for goal in normalized['goals']:
            source = goal['source']
            if not isinstance(source, str) or '#' not in source or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', source):
                sys.exit('init requires local accepted source path#heading for every goal; no write')
            if not goal['tasks']:
                blobs, reasons = dict(candidate), []
                section = local_reference(repo, source, blobs, reasons)
                acceptance = plan_acceptance_error(section)
                if acceptance:
                    reasons.append(acceptance)
                if reasons:
                    sys.exit('\n'.join(reasons) + '\ninit refused; no write')
                sources.update({name: hashlib.sha256(blob).hexdigest() if blob is not None else None
                                for name, blob in blobs.items()})
                continue
            check = argparse.Namespace(repo=str(repo), plan=source,
                                       tasks=','.join(goal['tasks']), receipt=None)
            code, receipt = backlog_receipt(check, candidate=candidate)
            if code == 1:
                sys.exit('\n'.join(receipt['reasons']) + '\ninit refused; no write')
            sources.update(receipt['sha256'])
        existing = checked_bytes(path_of(repo))
        if getattr(a, 'dry_run', False):
            if existing is not None:
                sys.exit('goals.json already exists; propose is only for a first index; no write')
            return normalized
        if existing is not None:
            if original_todo is None:
                sys.exit('existing goals.json has no TODO.md; reconcile bodies through maintenance; no write')
            current = load(repo)
            if errors(current) or normalize(current) != normalized:
                sys.exit('existing goals.json conflicts with intent; use maintenance commands to reconcile; no write')
            print('ok already initialized; no write'); return
        # Freeze referenced sources and inputs too, not just the ledger pair.
        if checked_bytes(intent_path) != intent_blob or (a.todo_file and checked_bytes(Path(a.todo_file)) != supplied):
            sys.exit('initialization inputs changed; no write')
        for name, digest in sources.items():
            if name not in candidate:
                blob = checked_bytes(repo / name)
                if (hashlib.sha256(blob).hexdigest() if blob is not None else None) != digest:
                    sys.exit('accepted sources changed; no write')
        # Roll back only our exact new TODO bytes if ledger replacement fails.
        # This is cooperative coordination, not a crash-atomic two-file commit.
        if original_todo is None:
            atomic_write(repo / 'TODO.md', text, expected_bytes=None)
            digest = hashlib.sha256()
            for name, blob in (('goals.json', None), ('TODO.md', todo)):
                digest.update(name.encode() + b'\0')
                digest.update(b'missing\0' if blob is None else str(len(blob)).encode() + b'\0' + blob)
            TRANSACTION.set((repo, digest.hexdigest()))
        try:
            atomic_write(path_of(repo), ledger, expected_bytes=None)
        except (OSError, SystemExit):
            if original_todo is None and checked_bytes(repo / 'TODO.md') == todo:
                (repo / 'TODO.md').unlink()
            raise
        print('ok initialized; run fmt, validate, render and backlog-check')
    except (OSError, ValueError, TypeError) as exc:
        sys.exit(f'init input/write error: {exc}; reconcile inputs before retrying')


PROPOSED = 'docs/tasks/proposed-goals.json'
ASK_START = '<!-- docs-sync:accept-goals:start -->'
ASK_END = '<!-- docs-sync:accept-goals:end -->'


def accept_section(blob, anchor):
    """The file's bytes with the heading's own Status set to Accepted (inserted under the
    heading when it has none); None when the anchor is missing or its Status is ambiguous."""
    original = blob.decode('utf-8')
    text = markdown_prose(original)
    rows = heading_rows(text)
    found = next((i for i, row in enumerate(rows) if row[0] == anchor), None)
    if found is None:
        return None
    start = rows[found][2]
    end = rows[found + 1][1] if found + 1 < len(rows) else len(text)
    statuses = list(re.finditer(r'^[ \t]*(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)', text[start:end], re.M | re.I))
    if len(statuses) > 1:
        return None
    if statuses:
        first, last = start + statuses[0].start(1), start + statuses[0].end(1)
        return (original[:first] + 'Accepted' + original[last:]).encode('utf-8')
    return (original[:start] + '\n\nStatus: Accepted' + original[start:]).encode('utf-8')


def accepted_sources(repo, data):
    """{path: bytes} of every goal source file as the owner's acceptance would leave it."""
    patched = {}
    for goal in data.get('goals') or []:
        source = goal.get('source')
        if not isinstance(source, str) or '#' not in source or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', source):
            sys.exit(f'{goal.get("id")}: a proposed goal needs a local source path#heading; no write')
        name, _, anchor = source.partition('#')
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            sys.exit(f'{goal.get("id")}: nonlocal source {source}; no write')
        blob = patched.get(path.as_posix()) or checked_bytes(Path(repo) / path)
        if blob is None:
            sys.exit(f'{goal.get("id")}: missing source {name}; write the goal\'s section first; no write')
        new = accept_section(blob, anchor)
        if new is None:
            sys.exit(f'{goal.get("id")}: source {source} is missing or has conflicting Status lines; no write')
        patched[path.as_posix()] = new
    return patched


def ask_owner(repo, data, todo_name):
    """The one owner question, kept between docs-sync's markers under BLOCKERS.md's Active."""
    tasks = [t for t in data['tasks'] if t.get('status') not in ('done', 'superseded')]
    goals = '\n'.join(f'  - {g["id"]} — {g.get("title", "")} ({g["source"]}; '
                      f'{sum(1 for t in tasks if t.get("goal") == g["id"])} task(s))' for g in data['goals'])
    block = (f'{ASK_START}\n\n### Q-ACCEPT-GOALS — USER_DECISION — effort decision — unblocks {len(tasks)}\n\n'
             f'- Task: accept the drafted goals so {todo_name} becomes an executable backlog\n'
             f'- Needs: these goals are drafted, not accepted; no runner can start their tasks until you accept them:\n'
             f'{goals}\n'
             f'- Since: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}\n'
             f'- Answer: "yes" accepts them all: run `goals.py accept <repo>`, which marks each source section '
             f'`Status: Accepted` and initializes goals.json from {PROPOSED}. To change a goal first, edit '
             f'{PROPOSED} or its section and run `goals.py propose` again.\n\n{ASK_END}\n')
    path = Path(repo) / 'BLOCKERS.md'
    text = path.read_text(encoding='utf-8') if path.exists() else (
        '# External input blockers\n\nOnly confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here.\n\n'
        '## Active\n\n## Resolved\n\nNone.\n')
    if ASK_START in text and ASK_END in text:
        head, rest = text.split(ASK_START, 1)
        text = head + block + rest.split(ASK_END, 1)[1].lstrip('\n')
    elif re.search(r'^## Active[ \t]*$', text, re.M):
        text = re.sub(r'^## Active[ \t]*\n', lambda m: m[0] + '\n' + block, text, count=1, flags=re.M)
    else:
        text = text.rstrip('\n') + '\n\n## Active\n\n' + block
    atomic_write(path, text)


def retire_question(repo):
    path = Path(repo) / 'BLOCKERS.md'
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    if ASK_START in text and ASK_END in text:
        head, rest = text.split(ASK_START, 1)
        atomic_write(path, head + rest.split(ASK_END, 1)[1].lstrip('\n'))


def propose(a):
    """First index without accepted sources: check the draft exactly as init will once the
    owner accepts it, save it and ask the owner once in BLOCKERS.md. Approves nothing."""
    repo = Path(a.repo)
    blob = checked_bytes(Path(a.intent))
    if blob is None:
        sys.exit('missing intent file; no write')
    data = parse_ledger(blob)
    if (repo / 'TODO.md').exists() is False and not a.todo_file:
        sys.exit('missing TODO.md; supply complete task bodies with --todo-file; no write')
    initialize(argparse.Namespace(repo=a.repo, intent=a.intent, todo_file=a.todo_file,
                                  sources=accepted_sources(repo, data), dry_run=True))
    if not (repo / 'TODO.md').exists():
        atomic_write(repo / 'TODO.md', checked_bytes(Path(a.todo_file)).decode('utf-8'), expected_bytes=None)
        TRANSACTION.set((repo, revision(repo)))  # this command's own write
    (repo / PROPOSED).parent.mkdir(parents=True, exist_ok=True)
    atomic_write(repo / PROPOSED, blob.decode('utf-8'))
    ask_owner(repo, data, 'TODO.md')
    tasks = [t['id'] for t in data['tasks'] if t.get('status') not in ('done', 'superseded')]
    print(json.dumps({'state': 'awaiting_acceptance', 'goals': [g['id'] for g in data['goals']], 'tasks': tasks,
                      'draft': PROPOSED, 'question': 'BLOCKERS.md#Q-ACCEPT-GOALS'}))


def accept(a):
    """The owner accepted the proposal: mark its source sections Accepted, initialize from it,
    then format, render, and retire the draft and its question. Run only on the owner's answer."""
    repo = Path(a.repo)
    draft = repo / PROPOSED
    blob = checked_bytes(draft)
    if blob is None:
        sys.exit(f'no proposal at {PROPOSED}; run propose first; no write')
    patched = accepted_sources(repo, parse_ledger(blob))
    originals = {name: checked_bytes(repo / name) for name in patched}
    for name, new in patched.items():
        atomic_write(repo / name, new.decode('utf-8'), expected_bytes=originals[name])
    TRANSACTION.set((repo, revision(repo)))  # each step below guards against writers other than this one
    try:
        initialize(argparse.Namespace(repo=a.repo, intent=str(draft), todo_file=None))
    except SystemExit:
        for name, old in originals.items():
            if checked_bytes(repo / name) == patched[name]:
                atomic_write(repo / name, old.decode('utf-8'))
        raise
    TRANSACTION.set((repo, revision(repo)))
    data = load(repo)
    dump(repo, data)
    TRANSACTION.set((repo, revision(repo)))
    render(repo, normalize(load(repo)))
    TRANSACTION.set((repo, revision(repo)))
    draft.unlink()
    retire_question(repo)
    print(f'ok accepted {len(data["goals"])} goal(s); goals.json initialized; run validate and backlog-check')


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest='cmd', required=True)
    init = sub.add_parser('init', help='create a version-1 index from accepted intent without overwriting existing state')
    init.add_argument('repo')
    init.add_argument('--intent', required=True, help='JSON file using the existing version-1 goals/tasks schema')
    init.add_argument('--todo-file', help='complete Markdown bodies when TODO.md is absent; must byte-match if it exists')
    pr = sub.add_parser('propose', help='first index without accepted sources: save the draft and ask the owner once')
    pr.add_argument('repo')
    pr.add_argument('--intent', required=True, help='version-1 goals/tasks JSON, as init takes it')
    pr.add_argument('--todo-file', help='complete Markdown bodies when TODO.md is absent')
    sub.add_parser('accept', help="the owner accepted the proposal: mark its sources Accepted and initialize").add_argument('repo')
    md = sub.add_parser('merge-driver', help='Git low-level driver; writes OURS only')
    md.add_argument('kind', choices=('goals', 'todo', 'archive'))
    md.add_argument('ancestor'); md.add_argument('ours'); md.add_argument('theirs')
    for name in ('validate', 'fmt', 'render', 'revision', 'merge-finalize', 'merge-attributes'):
        sub.add_parser(name).add_argument('repo')
    ar = sub.add_parser('archive'); ar.add_argument('repo')
    ar.add_argument('--verified-tasks', default='', help='explicitly verified closed IDs in a TODO-only repository')
    n = sub.add_parser('next'); n.add_argument('repo'); n.add_argument('--json', action='store_true')
    sub.add_parser('reorder', help='record TODO.md task order as the human priority (writes goals.json only)').add_argument('repo')
    bo = sub.add_parser('bootstrap-order', help='one-time migration of legacy priority into TODO.md order')
    bo.add_argument('repo'); bo.add_argument('--dry-run', action='store_true', help='report every proposed move; write nothing')
    f = sub.add_parser('focus'); f.add_argument('repo'); f.add_argument('goal', nargs='?')
    f.add_argument('--clear', action='store_true', help='remove primary milestone focus')
    f.add_argument('--json', action='store_true', help='read primary milestone without writing')
    t = sub.add_parser('task'); t.add_argument('repo'); t.add_argument('task'); t.add_argument('status', choices=[s for s in TASK_STATUS if s != 'superseded'])
    sup = sub.add_parser('supersede'); sup.add_argument('repo'); sup.add_argument('task')
    sup.add_argument('--by', required=True, help='comma-separated existing successor task IDs')
    sup.add_argument('--reason', required=True, help='accepted disposition, never passing evidence')
    mv = sub.add_parser('move', help='move an open task up or down among the open tasks of its TODO.md group')
    mv.add_argument('repo'); mv.add_argument('task'); mv.add_argument('direction', choices=('up', 'down'))
    s2 = sub.add_parser('section'); s2.add_argument('repo'); s2.add_argument('task')
    s2.add_argument('section', choices=[s for s in SECTIONS if s not in ('Done', 'Superseded')])
    ni = sub.add_parser('new-id'); ni.add_argument('repo')
    ni.add_argument('--prefix', help='ID prefix (default: the ledger\'s most common one)')
    n2 = sub.add_parser('add-task'); n2.add_argument('repo'); n2.add_argument('task', nargs='?', help='omit to allocate a new hashed ID')
    n2.add_argument('--prefix', help='prefix for an allocated ID (default: the ledger\'s most common one)')
    n2.add_argument('--goal', required=True); n2.add_argument('--title', required=True)
    n2.add_argument('--section', default='Next', choices=[s for s in SECTIONS if s not in ('Done', 'Superseded')])
    n2.add_argument('--depends-on', default='')
    n2.add_argument('--todo', action='store_true', help='also write its TODO.md entry at the top of its section')
    for flag in ('--short', '--scope', '--acceptance', '--checks'):
        n2.add_argument(flag, help='with --todo: that field of the entry (--short is required, at most 40 characters)')
    fd = sub.add_parser('field', help="set one single-line field of an open task's TODO.md entry (an owner answer)")
    fd.add_argument('repo'); fd.add_argument('task'); fd.add_argument('label'); fd.add_argument('value')
    pl = sub.add_parser('place', help="move an open task's TODO.md entry and ledger section to Now, Next or Needs decision")
    pl.add_argument('repo'); pl.add_argument('task'); pl.add_argument('section', choices=('Now', 'Next', 'Needs decision'))
    r = sub.add_parser('redact'); r.add_argument('repo')
    r.add_argument('--replacements-file', required=True, help='JSON absolute literal prefix to portable placeholder map')
    r.add_argument('--archive-dir', required=True, help='private original-byte archive outside repository')
    e = sub.add_parser('evidence'); e.add_argument('repo'); e.add_argument('goal')
    e.add_argument('--kind', choices=KINDS, required=True); e.add_argument('--ref', required=True)
    e.add_argument('--result', choices=RESULTS, required=True); e.add_argument('--ran-at', default='')
    e.add_argument('--task', help='completed task whose archive owns this closeout evidence')
    e.add_argument('--summary', help='short coverage summary (at most 80 characters); exact ref stays in ledger')
    b = sub.add_parser('backlog-check'); b.add_argument('repo')
    b.add_argument('--plan', required=True, help='accepted repo-relative path#heading')
    b.add_argument('--tasks', required=True, help='existing comma-separated task IDs')
    b.add_argument('--receipt', help='prior JSON stdout receipt to recheck for staleness')
    pl = sub.add_parser('plan-lint', help='read-only lint of TODO.md task contracts before dispatch'); pl.add_argument('repo')
    pl.add_argument('--tasks', default='', help='comma-separated task IDs (default: open Now/Next tasks)')
    pl.add_argument('--json', action='store_true'); pl.add_argument('--strict', action='store_true', help='exit 1 on warnings too')
    for parser in sub.choices.values():
        parser.add_argument('--expected-revision', help='refuse if goals.json or TODO.md changed since revision')
        parser.add_argument('--canonical-repo', help='explicit target checkout of the same Git repository (default: requested repo)')
    a = ap.parse_args()
    if a.cmd == 'merge-driver':
        from planning_merge import driver
        sys.exit(driver(a.kind, a.ancestor, a.ours, a.theirs))
    if a.cmd == 'plan-lint':  # read-only: no lock or revision guard needed
        import plan_lint
        sys.exit(plan_lint.report(a.repo, plan_lint.task_list(a.tasks), as_json=a.json, strict=a.strict))
    if a.cmd == 'focus' and sum((a.clear, a.goal is not None, a.json)) != 1:
        f.error('provide exactly one of GOAL, --clear or --json')
    with coordination(a.repo, a.canonical_repo) as repo:
        a.repo = str(repo)
        current = revision(repo)
        if a.expected_revision is not None and a.expected_revision != current:
            sys.exit(f'stale revision: expected {a.expected_revision}, current {current}; no write')
        if a.cmd == 'revision':
            print(current); return
        if a.cmd == 'backlog-check':
            sys.exit(backlog_check(a))
        execute(a)


SHORT_LIMIT = 40  # `Short:` fits a task list's column (the autowork TUI's Tasks window)


def short_errors(repo, data):
    """Open tasks whose `Short:` title is longer than SHORT_LIMIT characters or spans lines."""
    text = checked_bytes(Path(repo) / 'TODO.md')
    if text is None:
        return []
    bodies = task_bodies(text.decode('utf-8'))
    found = []
    for task in data.get('tasks') or []:
        if task.get('status') in ('done', 'superseded') or not bodies.get(task['id']):
            continue
        value = task_fields(bodies[task['id']][0][0]).get('Short')
        if value is not None and (len(value) > SHORT_LIMIT or '\n' in value):
            found.append(f'{task["id"]}: Short is one line of at most {SHORT_LIMIT} characters, not {len(value)}: '
                         f'{" ".join(value.split())[:60]}')
    return found


def move_block(text, task, step):
    """(new TODO.md text, '') with open task ``task`` swapped with the open task ``step`` places
    away in its own group (-1 up, 1 down), or (None, why it cannot move). Blocks never cross a
    group heading, and every block keeps its exact bytes."""
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    peers = [b for b in blocks if b['region'] == block['region'] and b['mark'] == ' ']
    index = peers.index(block) + step
    if not 0 <= index < len(peers):
        where = block['region'][1] or 'its section'
        return None, f'{task} is already {"first" if step < 0 else "last"} in {where}'
    other = peers[index]
    if block['foreign_heading'] or other['foreign_heading']:
        return None, f'{task} or {other["id"]} contains another heading; move it by hand'
    swap = {id(block): other, id(other): block}
    output, cursor = [], 0
    for b in blocks:
        output.append(text[cursor:b['start']] + swap.get(id(b), b)['core'] + b['sep'])
        cursor = b['end']
    new_text = ''.join(output) + text[cursor:]
    if sorted(b['core'] for b in blocks) != sorted(b['core'] for b in task_blocks(new_text)):
        return None, 'task block bytes would change'
    return new_text, ''


def set_field(text, task, label, value):
    """(new TODO.md text, '') with ``label: value`` the one such line of open task ``task``'s entry,
    replacing an earlier one, or (None, why). Two lines of one label would hide both from
    task_fields, so an answer replaces; Git keeps the earlier one."""
    value = ' '.join(str(value).split())
    if not value or not re.fullmatch(r'[A-Za-z][A-Za-z /-]*', label):
        return None, 'a field is a label and a one-line value'
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    lines = block['core'].split('\n')
    pattern = re.compile(r'^([ \t]*(?:[-*][ \t]+)?(?:\*\*)?)' + re.escape(label) + r':(?:\*\*)?(?:[ \t]|$)')
    hits = [i for i, line in enumerate(lines) if pattern.match(line)]
    if len(hits) > 1:
        return None, f'{task} has {len(hits)} {label}: lines; keep one by hand'
    if hits:
        lines[hits[0]] = f'{pattern.match(lines[hits[0]])[1]}{label}: {value}'
    else:  # right under the checkbox: never inside another field's continued value
        mark = next(i for i, line in enumerate(lines) if re.match(TASK_MARK, line))
        lines.insert(mark + 1, f'- {label}: {value}')
    new_text = text[:block['start']] + '\n'.join(lines) + text[block['start'] + len(block['core']):]
    entry = task_bodies(new_text).get(task) or []
    if len(entry) != 1 or ' '.join(task_fields(entry[0][0]).get(label, '').split()) != value:
        return None, f'{label}: would not read back from {task}\'s entry'
    return new_text, ''


def place_block(text, task, section):
    """(new TODO.md text, '') with open task ``task``'s entry moved, bytes intact, to the top of
    `## <section>`, or (None, why)."""
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    if block['region'][1].split(' / ')[0] == section:
        return None, f'{task} is already in {section}'
    if block['foreign_heading']:
        return None, f'{task} contains another heading; move it by hand'
    rest = text[:block['start']] + text[block['end']:]
    heading = re.search(r'^##[ \t]+' + re.escape(section) + r'[ \t]*\r?$', rest, re.M)
    if heading is None:
        return None, f'TODO.md has no "## {section}" section'
    at = heading.end() + len(re.match(r'(?:\r?\n)*', rest[heading.end():])[0])
    new_text = rest[:at] + block['core'] + '\n\n' + rest[at:]
    moved = next((b for b in task_blocks(new_text) if b['id'] == task), None)
    if (sorted(b['core'] for b in blocks) != sorted(b['core'] for b in task_blocks(new_text))
            or moved is None or moved['region'][1].split(' / ')[0] != section):
        return None, 'task block bytes would change'
    return new_text, ''


def touches_errors(repo, data):
    """Open tasks whose `Touches:` is not a list of paths (TOOLSET-213-45): prose or a note ran
    into it, and the engine would hold the worker's own files as outside Touches."""
    text = checked_bytes(Path(repo) / 'TODO.md')
    if text is None:
        return []
    bodies = task_bodies(text.decode('utf-8'))
    found = []
    for task in data.get('tasks') or []:
        if task.get('status') in ('done', 'superseded') or not bodies.get(task['id']):
            continue
        value = task_fields(bodies[task['id']][0][0]).get('Touches') or ''
        value = re.split(r'\n(?:[ \t]*[-*][ \t]|[ \t]*#|[ \t]*\n)', value, maxsplit=1)[0]
        bad = next((p.strip() for p in value.split(',') if '\n' in p.strip() or p.strip().count(' ') >= 3), None)
        if bad:
            found.append(f'{task["id"]}: Touches is not a list of paths: {" ".join(bad.split())[:80]}')
    return found


def execute(a):
    if a.cmd == 'merge-attributes':
        import todo_archive
        text = todo_text(a.repo)
        known = set(task_bodies(text))
        owner = todo_archive.archive_owner(Path(a.repo), todo_archive.navigation(text, task_prose(text), known))
        print('goals.json merge=docs-sync-goals\nTODO.md merge=docs-sync-todo')
        for name in dict.fromkeys((todo_archive.DEFAULT, *todo_archive.LEGACY, owner.as_posix())):
            print(json.dumps(name) + ' merge=docs-sync-archive' if any(c.isspace() for c in name)
                  else name + ' merge=docs-sync-archive')
        return
    if a.cmd == 'merge-finalize':
        from planning_merge import finalize
        try:
            finalize(a.repo)
        except ValueError as exc:
            sys.exit(str(exc))
        print('ok'); return
    if a.cmd == 'init':
        initialize(a); return
    if a.cmd == 'propose':
        propose(a); return
    if a.cmd == 'accept':
        accept(a); return
    if a.cmd == 'archive':
        data = load(a.repo) if path_of(a.repo).exists() else None
        result = archive_tasks(a.repo, data, verified_tasks=tuple(filter(None, a.verified_tasks.split(','))))
        print(json.dumps(result)); return
    if a.cmd == 'new-id':
        print(new_task_id(a.repo, load(a.repo) if path_of(a.repo).exists() else None, a.prefix)); return
    if a.cmd == 'field':  # TODO.md only: an answer the runner reads from the task's entry
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = set_field(before.decode('utf-8'), a.task, a.label, a.value)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        print(f'ok {a.task} {a.label}: {" ".join(a.value.split())}'); return
    if a.cmd == 'move':  # TODO.md only: goals.json is neither read nor written
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = move_block(before.decode('utf-8'), a.task, -1 if a.direction == 'up' else 1)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        # goals.json is untouched: `reorder` (the runner runs it) records the new order as priority.
        print(f'ok {a.task} moved {a.direction}'); return
    data = load(a.repo)

    if a.cmd == 'redact':
        redact(a.repo, data, a.replacements_file, a.archive_dir); return

    if a.cmd == 'focus':
        if a.json:
            print(json.dumps({'primary_milestone': data.get('primary_milestone')})); return
        if a.clear:
            data.pop('primary_milestone', None)
            dump(a.repo, data); print('ok focus cleared'); return
        if not any(g['id'] == a.goal for g in data['goals']):
            sys.exit(f'unknown goal {a.goal}')
        data['primary_milestone'] = a.goal
        dump(a.repo, data); print(f'ok focus -> {a.goal}'); return

    if a.cmd == 'validate':
        errs = errors(data) + touches_errors(a.repo, data) + short_errors(a.repo, data)
        print('\n'.join(errs) if errs else 'ok')
        sys.exit(1 if errs else 0)
    if a.cmd == 'fmt':
        dump(a.repo, data); print('ok'); return
    if a.cmd == 'render':
        render(a.repo, normalize(data)); print('ok'); return
    if a.cmd == 'next':
        data = normalize(data)
        # Closing the last task precedes recording its evidence. Keep that
        # goal as a dependency gate while allowing independent work to proceed.
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        try:
            picks, status = queue(data, todo_text(a.repo))
        except PriorityDrift as drift:
            print(json.dumps(dict(drift.status, outcome='PRIORITY_DRIFT', revision=revision(a.repo)), indent=2))
            sys.exit(3)
        if status['state'] == 'unmigrated':
            print(status['action'], file=sys.stderr)
        if a.json:
            print(json.dumps([{'task': t, 'goal': g['id'], 'goal_status': g['status'],
                               'priority_state': status['state']} for t, g in picks], indent=2))
        elif picks:
            t, g = picks[0]
            print(f"{t['id']} ({t['section']}) → {g['id']} [{g['status']}]: {t['title']}")
        else:
            print('none')
        return
    if a.cmd == 'reorder':
        data = normalize(data)
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        record, status = reconcile_order(data, todo_text(a.repo))
        previous = data['priority_order']['tasks']
        report = {'priority_order': record['tasks'], 'previous': previous,
                  'notes': selection_notes(dict(data, priority_order=record), record['tasks'])}
        if status['state'] == 'synced':
            print(json.dumps(dict(report, outcome='UNCHANGED'), indent=2)); return
        data['priority_order'] = record
        dump(a.repo, data)
        print(json.dumps(dict(report, outcome='RECONCILED'), indent=2)); return
    if a.cmd == 'bootstrap-order':
        data = normalize(data)
        if data.get('priority_order'):
            print(json.dumps({'outcome': 'ALREADY_BOOTSTRAPPED', 'schema': data['priority_order']['schema'],
                              'action': 'Bootstrap never reruns; use `goals.py reorder` for later TODO.md edits.'}, indent=2))
            return
        problems = errors(data, allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        plan = bootstrap_plan(data, before.decode('utf-8'))
        rewrite = plan['text'].encode('utf-8') != before
        report = {'regions': plan['regions'], 'rewrite_todo': rewrite, 'priority_order': plan['record']['tasks'],
                  'next_before': plan['next_before'], 'next_after': plan['next_after'],
                  'eligible_order_changes': plan['eligible_order_changes'], 'revision': revision(a.repo)}
        if plan['reasons']:
            print(json.dumps(dict(report, outcome='BOOTSTRAP_CONFLICT', reasons=plan['reasons']), indent=2))
            sys.exit(1)
        if a.dry_run:
            print(json.dumps(dict(report, outcome='BOOTSTRAP_PLAN'), indent=2)); return
        if a.expected_revision is None:
            sys.exit('bootstrap-order apply requires --expected-revision from a --dry-run report; no write')
        ledger_before = checked_bytes(path_of(a.repo))
        if rewrite:
            atomic_write(todo, plan['text'], expected_bytes=before)
            if checked_bytes(todo) != plan['text'].encode('utf-8') or checked_bytes(path_of(a.repo)) != ledger_before:
                sys.exit('bootstrap verification failed after TODO.md write; ledger unchanged; rerun --dry-run')
            # The TODO.md write is this transaction's own; guard the ledger against anything else.
            TRANSACTION.set((Path(a.repo), revision(a.repo)))
        data['priority_order'] = plan['record']
        dump(a.repo, data)
        print(json.dumps(dict(report, outcome='BOOTSTRAPPED', revision=revision(a.repo)), indent=2)); return
    if a.cmd == 'supersede':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task['status'] == 'done':
            sys.exit('completed task history cannot be relabelled superseded; no write')
        successors = sorted(set(tid.strip() for tid in a.by.split(',') if tid.strip()))
        reason = a.reason.strip()
        if task['status'] == 'superseded' and (task.get('superseded_by') != successors
                or task.get('supersession_reason') != reason):
            sys.exit('supersession already recorded with a different disposition; no write')
        task.update(status='superseded', section='Superseded', superseded_by=successors,
                    supersession_reason=reason)
        problems = errors(normalize(data), allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems) + '; no write')
        dump(a.repo, data)
        print('ok superseded; acceptance remains unpassed; run render to retain original history in archive')
        return
    if a.cmd == 'task':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task['status'] == 'superseded':
            sys.exit('superseded history cannot be reopened or completed; use its successor tasks; no write')
        task['status'] = a.status
        goal = next((g for g in data['goals'] if g['id'] == task['goal']), None)
        if a.status != 'done':
            if task.get('section') == 'Done':
                task['section'] = 'Next'
            if goal and goal.get('status') == 'met':
                goal['status'] = 'partial'
        dump(a.repo, data)
        still_open = [t for t in data['tasks'] if t.get('goal') == task['goal'] and t.get('status') != 'done']
        if a.status == 'done' and goal and goal.get('status') != 'met' and not still_open:
            print(f"WARNING: {goal['id']} is still {goal['status']} with no open task. Record the check you ran: "
                  f"goals.py evidence {a.repo} {goal['id']} --kind executed --ref \"<command>\" --result pass")
        print('ok'); return
    if a.cmd == 'place':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task.get('status') in ('done', 'superseded'):
            sys.exit(f'task {a.task} is {task["status"]}; no write')
        todo = Path(a.repo) / 'TODO.md'
        before = checked_bytes(todo)
        if before is None:
            sys.exit('TODO.md not found; no write')
        new_text, why = place_block(before.decode('utf-8'), a.task, a.section)
        if why:
            sys.exit(why + '; no write')
        atomic_write(todo, new_text, expected_bytes=before)
        TRANSACTION.set((Path(a.repo), revision(a.repo)))  # the TODO.md write is this command's own
        task['section'] = a.section
        dump(a.repo, data); print(f'ok {a.task} -> {a.section}'); return
    if a.cmd == 'section':
        task = next((x for x in data['tasks'] if x['id'] == a.task), None) or sys.exit(f'unknown task {a.task}')
        if task.get('status') in ('done', 'superseded'):
            sys.exit(f'task {a.task} is {task["status"]}')
        task['section'] = a.section
        dump(a.repo, data); print(f'ok {a.task} -> {a.section}'); return
    if a.cmd == 'add-task':
        if a.task is None:
            a.task = new_task_id(a.repo, data, a.prefix)
        elif a.prefix:
            sys.exit('--prefix applies only when TASK is omitted; no write')
        if re.fullmatch(TASK_ID, a.task) is None:
            sys.exit('invalid task ID: use letters, digits, underscores or hyphens; start with a letter or digit; no write')
        if any(x['id'] == a.task for x in data['tasks']):
            sys.exit(f'task {a.task} already exists')
        goal = next((x for x in data['goals'] if x['id'] == a.goal), None) or sys.exit(f'unknown goal {a.goal}')
        deps = [d for d in a.depends_on.split(',') if d]
        known = {x['id'] for x in data['tasks']}
        missing = [d for d in deps if d not in known]
        if missing:
            sys.exit(f'unknown depends_on task(s): {missing}')
        if a.todo:
            short = ' '.join((a.short or '').split())
            if not short or len(short) > SHORT_LIMIT:
                sys.exit(f'--todo needs --short of 1 to {SHORT_LIMIT} characters; no write')
            todo = Path(a.repo) / 'TODO.md'
            before = checked_bytes(todo)
            if before is None:
                sys.exit('TODO.md not found; no write')
            title = ' '.join(a.title.split())
            entry = [f'### {a.task} — {title}', '', f'- [ ] {a.task} — {title}', f'- Short: {short}',
                     '- Status: open', f'- Goal: {a.goal}']
            entry += [f'- {label}: {" ".join(value.split())}' for label, value in
                      (('Scope', a.scope), ('Acceptance', a.acceptance), ('Checks', a.checks)) if value]
            entry.append(f'- Dependencies: {", ".join(deps) if deps else "None."}')
            text = before.decode('utf-8')
            heading = re.search(r'^##[ \t]+' + re.escape(a.section) + r'[ \t]*\r?$', text, re.M)
            if heading is None:
                sys.exit(f'TODO.md has no "## {a.section}" section; no write')
            at = heading.end() + len(re.match(r'(?:\r?\n)*', text[heading.end():])[0])
            atomic_write(todo, text[:at] + '\n'.join(entry) + '\n\n' + text[at:], expected_bytes=before)
            TRANSACTION.set((Path(a.repo), revision(a.repo)))  # the TODO.md write is this command's own
        data['tasks'].append({'id': a.task, 'goal': a.goal, 'title': a.title, 'status': 'open',
                              'section': a.section, 'depends_on': deps})
        goal['tasks'] = sorted(set(goal.get('tasks', []) + [a.task]))
        if goal.get('status') == 'met':
            goal['status'] = 'partial'
        dump(a.repo, data); print(f'ok {a.task} -> {a.goal} ({a.section})'); return
    if a.cmd == 'evidence':
        goal = next((x for x in data['goals'] if x['id'] == a.goal), None) or sys.exit(f'unknown goal {a.goal}')
        entry = {'kind': a.kind, 'ref': a.ref, 'result': a.result}
        completed = [t['id'] for t in data['tasks'] if t.get('goal') == a.goal and t.get('status') == 'done']
        task = a.task or (completed[-1] if completed else None)
        if a.task and a.task not in completed:
            sys.exit('--task must name a completed task of this goal; no write')
        summary = a.summary or f'{a.kind.capitalize()} check: {a.result}'
        if not summary.strip() or len(summary) > 80 or '\n' in summary or '\r' in summary:
            sys.exit('--summary must be one short line (1–80 characters); no write')
        entry['summary'] = summary
        if task:
            import todo_archive
            text = todo_text(a.repo)
            prose = todo_archive.navigation(text, task_prose(text), {t['id'] for t in data['tasks']})
            owner = todo_archive.archive_owner(Path(a.repo), prose)
            anchor = task.lower()
            history = (checked_bytes(Path(a.repo) / owner) or b'').decode('utf-8')
            if history and task not in task_bodies(text) and f'<a id="{anchor}"></a>' not in history:
                # Legacy history may have a task heading rather than an ID-only anchor.
                # Reuse real headings without rewriting append-only historical bytes.
                spans, _ = todo_archive.entries(history, markdown_prose(history), {task})
                source = next((start for start, _, tid, _ in spans if tid == task), None)
                headings = [h for h in heading_rows(markdown_prose(history))
                            if source is not None and h[1] <= source]
                own = [h for h in headings if re.search(r'(?<![\w-])' + re.escape(task) +
                                                       r'(?![\w-])', history[h[1]:h[2]])]
                anchor = (own or headings)[-1][0] if (own or headings) else ''
            entry.update(task=task, archive=owner.as_posix(), anchor=anchor)
        if a.ran_at:
            entry['ran_at'] = a.ran_at
        goal['evidence'] = [x for x in goal.get('evidence', []) if (x.get('kind'), x.get('ref')) != (a.kind, a.ref)] + [entry]
        for previous in goal['evidence']:
            previous.pop('coverage_current', None)
        entry['coverage_current'] = True
        if a.kind == 'executed' and a.result == 'pass' and goal.get('status') in ('unmet', 'unverified', 'partial') \
                and all(t.get('status') == 'done' for t in data['tasks'] if t.get('goal') == a.goal):
            goal['status'] = 'met'
        if a.kind == 'executed' and a.result == 'fail' and goal.get('status') == 'met':
            goal['status'] = 'partial'
        dump(a.repo, data); print(f"ok {goal['id']} → {goal['status']}"); return


if __name__ == '__main__':
    # Merge helpers must share this invocation's lock/stale-write context.
    sys.modules['goals'] = sys.modules[__name__]
    main()
