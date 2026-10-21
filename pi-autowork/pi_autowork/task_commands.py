"""`autowork tasks ...`: read and edit a repository's tasks/ store. Standard library only.

Reads (list, show, why, validate) use a pinned commit, HEAD by default; validate
--worktree checks uncommitted edits. Writes (add, field, place, move, supersede)
change task files in the working tree and never commit; each refuses a file that
changed since it was read, and the whole would-be store is validated before the
write is kept. A written file grants no authority beyond its typed fields, and a
declared check still needs the existing approval to run.
"""
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import task_select  # noqa: E402
import task_store  # noqa: E402
from task_store import StoreError, TaskStore, WriteError  # noqa: E402

STEP = 1000


class CommandError(Exception):
    """A refusal with its message; nothing was written."""


def _git(repo, *args, env=None):
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            env={**clean, **(env or {})}, timeout=60)
    if result.returncode:
        raise CommandError(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


def worktree_store(repo):
    """The store as the working tree has it, read through a throwaway commit; the real
    index, HEAD and refs are untouched."""
    if not (Path(repo) / 'tasks').is_dir():
        raise StoreError('tasks/:1: no task store in the working tree')
    with tempfile.TemporaryDirectory() as tmp:
        env = {'GIT_INDEX_FILE': str(Path(tmp) / 'index')}
        head = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '-q', 'HEAD'],
                              capture_output=True, text=True).stdout.strip()
        if head:
            _git(repo, 'read-tree', head, env=env)
        _git(repo, 'add', '-A', '--', 'tasks', env=env)
        tree = _git(repo, 'write-tree', env=env)
        ident = {'GIT_AUTHOR_NAME': 'autowork', 'GIT_AUTHOR_EMAIL': 'autowork@localhost',
                 'GIT_COMMITTER_NAME': 'autowork', 'GIT_COMMITTER_EMAIL': 'autowork@localhost'}
        commit = _git(repo, 'commit-tree', tree, *(['-p', head] if head else []), '-m', 'worktree tasks', env=ident)
    return TaskStore.at(repo, commit)


def _path(repo, tid, goal=False):
    return Path(repo) / 'tasks' / ('goals' if goal else 'items') / f'{tid}.md'


def _write(repo, path, before, after):
    """Replace ``path`` only if it still holds ``before``; keep the change only if the
    whole store still validates, else put the old bytes back."""
    current = path.read_bytes() if path.exists() else None
    if current != before:
        raise CommandError(f'{path.relative_to(repo)} changed since it was read; nothing written')
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(f'.{path.name}.{os.getpid()}.tmp')
    tmp.write_bytes(after.encode())
    os.replace(tmp, path)
    try:
        worktree_store(repo)
    except StoreError as exc:
        if before is None:
            path.unlink()
        else:
            path.write_bytes(before)
        raise CommandError(f'{exc}; nothing written') from None


def _section_ranks(store, section, without=None):
    """Open tasks of a section in priority order: (rank, id) pairs."""
    return sorted((t.rank, t.id) for t in store.tasks.values()
                  if t.section == section and t.status == 'open' and t.id != without and t.rank is not None)


def bottom_rank(store, section, without=None):
    ranks = [rank for rank, _ in _section_ranks(store, section, without)]
    return (max(ranks) // STEP + 1) * STEP if ranks else STEP


def place_between(ranked, position):
    """New ranks to insert one item at ``position`` of ``ranked`` [(rank, id)], as
    {id or None: rank}; None is the inserted item. Midpoint when a gap exists; else only
    the contiguous run without room is spread, never the whole section."""
    items = [None if i == position else ranked[i - (i > position)][1] for i in range(len(ranked) + 1)]
    rank = {tid: r for r, tid in ranked}
    a = b = position
    while True:
        lower = rank[items[a - 1]] if a > 0 else None
        upper = rank[items[b + 1]] if b + 1 < len(items) else None
        count = b - a + 1
        if lower is None or upper is None or upper - lower > count:
            break
        b += 1  # take in the next gapless neighbour; past the last one there is always room
    window = items[a:b + 1]
    if lower is None and upper is None:
        values = [STEP * (k + 1) for k in range(count)]
    elif upper is None:
        values = [lower + STEP * (k + 1) for k in range(count)]
    elif lower is None:
        values = [upper - STEP * (count - k) for k in range(count)]
    else:
        gap = (upper - lower) / (count + 1)
        values = [lower + round(gap * (k + 1)) for k in range(count)]
    return {tid: value for tid, value in zip(window, values) if tid is None or rank.get(tid) != value}


def new_id(repo, store, prefix=None):
    """Next number plus a two-hex hash, as goals.py allocates; the archive's IDs are taken too."""
    ids = set(store.tasks) | set(store.goals)
    archive = Path(repo) / 'TODO.archive.md'
    if archive.is_file():
        ids |= set(re.findall(r'\b[A-Za-z][A-Za-z0-9_]*-\d+(?:-[0-9a-f]{2})?\b', archive.read_text()))
    numbered = [m.groups() for m in (re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)-(\d+)(?:-[0-9a-f]{2})?', i)
                                     for i in ids) if m]
    if prefix is None:  # the tasks' most common prefix, as goals.py chooses it; never a goal's
        own = [m.group(1) for m in (re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)-\d+(?:-[0-9a-f]{2})?', t)
                                    for t in store.tasks) if m]
        pool = own or [p for p, n in numbered if f'{p}-{n}' not in store.goals]
        prefix = max(sorted(set(pool)), key=pool.count) if pool else 'T'
    if not re.fullmatch(r'[A-Za-z][A-Za-z0-9_]*', prefix):
        raise CommandError('invalid prefix: letters, digits or underscores, starting with a letter')
    numbers = [n for p, n in numbered if p == prefix]
    number = str(max([0] + [int(n) for n in numbers]) + 1).zfill(max([3] + [len(n) for n in numbers]))
    for _ in range(64):
        digest = hashlib.sha256(f'{prefix}-{number}:{time.time_ns()}:{os.urandom(8).hex()}'.encode()).hexdigest()
        if (candidate := f'{prefix}-{number}-{digest[:2]}') not in ids:
            return candidate
    raise CommandError(f'no unused ID for {prefix}-{number}')


def _task(store, tid):
    if tid not in store.tasks:
        raise CommandError(f'unknown task {tid}')
    return store.tasks[tid]


def _set(repo, tid, changes, note=None):
    path = _path(repo, tid)
    before = path.read_bytes()
    text = task_store.edit(before.decode(), changes) if changes else before.decode()
    if note:
        text = task_store.set_note(text, *note)
    _write(repo, path, before, text)


# --- commands --------------------------------------------------------------------------

def cmd_list(repo, rev='HEAD'):
    store = TaskStore.at(repo, rev)
    ready = {t.id: n + 1 for n, t in enumerate(task_select.order(store))}
    rows = []
    for t in sorted(store.tasks.values(), key=lambda t: (t.status != 'open', t.section or '', t.rank or 0, t.id)):
        blocked = task_select.blocking(store, t)
        rows.append(dict(id=t.id, title=t.title, section=t.section, rank=t.rank, status=t.status, goal=t.goal,
                         position=ready.get(t.id), blocked_by=blocked.code if blocked else None))
    return rows


def cmd_show(repo, tid, rev='HEAD'):
    store = TaskStore.at(repo, rev)
    t = _task(store, tid)
    return dict(id=t.id, title=t.title, short=t.short, status=t.status, goal=t.goal, section=t.section,
                rank=t.rank, depends_on=list(t.depends_on), touches=list(t.touches), resources=list(t.resources),
                kind=t.kind.value, ownership=t.ownership.value, live=t.live.value, scope=t.scope,
                acceptance=list(t.acceptance), checks=list(t.checks), exclusions=list(t.exclusions),
                draft=t.draft, missing_fields=list(t.missing_fields), contract_hash=t.contract_hash,
                record_revision=t.record_revision, path=t.path, rev=store.rev, notes=t.body)


def cmd_why(repo, tid, rev='HEAD'):
    store = TaskStore.at(repo, rev)
    first, reasons = task_select.why(store, tid)
    return dict(task=tid, eligible=bool(reasons) and reasons[0].code == 'POSITION', first=first,
                reasons=[dict(code=r.code, detail=r.detail) for r in reasons])


def cmd_validate(repo, rev='HEAD', worktree=False):
    store = worktree_store(repo) if worktree else TaskStore.at(repo, rev)
    drafts = sorted(t.id for t in store.tasks.values() if t.draft)
    return dict(ok=True, tasks=len(store.tasks), goals=len(store.goals), drafts=drafts,
                pending=list(TaskStore.pending(repo)))


def cmd_new_id(repo, prefix=None):
    return new_id(repo, worktree_store(repo), prefix)


def cmd_add(repo, goal, title, short, section='Now', scope=None, acceptance=(), checks=(), touches=(),
            depends_on=(), task_id=None, prefix=None):
    store = worktree_store(repo)
    if goal not in store.goals:
        raise CommandError(f'unknown goal {goal}')
    tid = task_id or new_id(repo, store, prefix)
    if tid in store.tasks:
        raise CommandError(f'{tid} already exists')
    fields = dict(schema=1, id=tid, title=title, short=short, status='open', goal=goal, section=section,
                  rank=bottom_rank(store, section), depends_on=list(depends_on), touches=list(touches),
                  resources=[], kind='implementation', ownership='worker', exclusions=[])
    if scope:
        fields['scope'] = scope
    if acceptance:
        fields['acceptance'] = list(acceptance)
    if checks:
        fields['checks'] = list(checks)
    _write(repo, _path(repo, tid), None, task_store.render(fields, '\n'))
    return tid


TYPED = {'rank': int, 'depends_on': list, 'touches': list, 'resources': list, 'acceptance': list,
         'checks': list, 'exclusions': list, 'title': str, 'short': str, 'scope': str, 'goal': str,
         'kind': str, 'ownership': str, 'live': str}


def cmd_field(repo, tid, key, value):
    """A typed header field (rank, touches, ...) or, for any other label, a note line such as
    `Held by` or `Owner decision` in the task's body."""
    _task(worktree_store(repo), tid)
    if key in ('status', 'section', 'id', 'schema'):
        raise CommandError(f'use place or supersede to change {key}')
    if key in TYPED:
        kind = TYPED[key]
        if kind is int:
            try:
                parsed = int(value)
            except ValueError:
                raise CommandError(f'{key} must be an integer') from None
        elif kind is list:
            parsed = json.loads(value) if value.strip().startswith('[') else [v.strip() for v in value.split(',') if v.strip()]
        else:
            parsed = value
        _set(repo, tid, {key: parsed})
    else:
        _set(repo, tid, {}, (key, ' '.join(value.split())))


def cmd_place(repo, tid, section):
    store = worktree_store(repo)
    t = _task(store, tid)
    if t.status != 'open':
        raise CommandError(f'{tid} is {t.status}')
    if section not in ('Now', 'Next', 'Needs decision'):
        raise CommandError('section is Now, Next or Needs decision')
    _set(repo, tid, {'section': section, 'rank': bottom_rank(store, section, without=tid)})


def cmd_move(repo, tid, direction):
    """One place up or down within the task's section; returns {id: new rank} changed."""
    store = worktree_store(repo)
    t = _task(store, tid)
    ranked = _section_ranks(store, t.section)
    index = [i for _, i in ranked].index(tid)
    target = index - 1 if direction == 'up' else index + 1
    if not 0 <= target < len(ranked):
        raise CommandError(f'{tid} is already at the {"top" if direction == "up" else "bottom"} of {t.section}')
    rest = [pair for pair in ranked if pair[1] != tid]
    changes = place_between(rest, target)
    changes[tid] = changes.pop(None)
    for other, rank in sorted(changes.items(), key=lambda item: item[0] != tid):
        _set(repo, other, {'rank': rank})
    return changes


def cmd_supersede(repo, tid, by, reason):
    store = worktree_store(repo)
    _task(store, tid)
    for other in by:
        _task(store, other)
    note = ('Superseded by', f'{", ".join(by)}; {" ".join(reason.split())}')
    _set(repo, tid, {'status': 'superseded'}, note)


# --- CLI -------------------------------------------------------------------------------

def add_parser(sub):
    tasks = sub.add_parser('tasks', help='read and edit the tasks/ store')
    verbs = tasks.add_subparsers(dest='verb', required=True)
    for name in ('list', 'validate', 'new-id'):
        p = verbs.add_parser(name)
        p.add_argument('repo', nargs='?', default='.')
        if name == 'validate':
            p.add_argument('--worktree', action='store_true', help='check uncommitted edits too')
        if name == 'new-id':
            p.add_argument('--prefix')
        if name != 'new-id':
            p.add_argument('--rev', default='HEAD')
    for name in ('show', 'why'):
        p = verbs.add_parser(name)
        p.add_argument('task')
        p.add_argument('repo', nargs='?', default='.')
        p.add_argument('--rev', default='HEAD')
    p = verbs.add_parser('add')
    p.add_argument('repo', nargs='?', default='.')
    for flag in ('--goal', '--title', '--short'):
        p.add_argument(flag, required=True)
    p.add_argument('--section', default='Now', choices=('Now', 'Next', 'Needs decision'))
    p.add_argument('--id', dest='task_id')
    p.add_argument('--scope')
    for flag in ('--acceptance', '--checks', '--touches', '--depends-on'):
        p.add_argument(flag, action='append', default=[])
    p = verbs.add_parser('field')
    p.add_argument('task'); p.add_argument('label'); p.add_argument('value')
    p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('place')
    p.add_argument('task'); p.add_argument('section', choices=('Now', 'Next', 'Needs decision'))
    p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('move')
    p.add_argument('task'); p.add_argument('direction', choices=('up', 'down'))
    p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('supersede')
    p.add_argument('task'); p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--by', action='append', required=True)
    p.add_argument('--reason', required=True)
    return tasks


def run(args, repo):
    """Print the result as JSON (reads) or one line (writes); return the exit code."""
    try:
        verb = args.verb
        if verb == 'list':
            out = cmd_list(repo, args.rev)
        elif verb == 'show':
            out = cmd_show(repo, args.task, args.rev)
        elif verb == 'why':
            out = cmd_why(repo, args.task, args.rev)
        elif verb == 'validate':
            out = cmd_validate(repo, args.rev, args.worktree)
        elif verb == 'new-id':
            out = cmd_new_id(repo, args.prefix)
        elif verb == 'add':
            out = 'added ' + cmd_add(repo, args.goal, args.title, args.short, args.section, args.scope,
                                     args.acceptance, args.checks, args.touches, args.depends_on, args.task_id)
        elif verb == 'field':
            cmd_field(repo, args.task, args.label, args.value)
            out = f'ok {args.task} {args.label}'
        elif verb == 'place':
            cmd_place(repo, args.task, args.section)
            out = f'ok {args.task} -> {args.section}'
        elif verb == 'move':
            changes = cmd_move(repo, args.task, args.direction)
            out = 'ok ' + ', '.join(f'{tid} rank {rank}' for tid, rank in changes.items())
        elif verb == 'supersede':
            cmd_supersede(repo, args.task, args.by, args.reason)
            out = f'ok {args.task} superseded'
    except (CommandError, StoreError, WriteError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(out if isinstance(out, str) else json.dumps(out, indent=2))
    return 0
