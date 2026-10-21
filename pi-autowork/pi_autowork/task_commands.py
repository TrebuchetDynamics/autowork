"""`autowork tasks ...`: read and edit a repository's tasks/ store. Standard library only.

Reads (list, show, why, validate) use a pinned commit, HEAD by default; --worktree reads
uncommitted edits. Writes (add, field, place, move, hold, release, done, supersede, goal)
change task files in the working tree and never commit; each takes the repository's task
lock, refuses a file that changed since it was read (or since the revision `--expect`
names), refuses a contract change to a task a worker or lease holds, and validates the
whole would-be store before the write is kept. A written file grants no authority beyond
its typed fields, and a declared check still needs the existing approval to run.
`prepare` brings a repository to a valid store (task_prepare.py).
"""
import argparse
from contextlib import contextmanager
import fcntl
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
# Worker slot states with unfinished work: nothing converts under them.
OCCUPYING = ('dispatched', 'running', 'reported', 'integrating', 'integrated', 'held', 'interrupted')
# ...and those whose attempt is still live: its contract may not change under it. A held or
# interrupted attempt is waiting for exactly that repair.
ACTIVE = ('dispatched', 'running', 'reported', 'integrating', 'integrated')
# The fields a task's contract hash covers, plus its goal: what an admitted attempt ran against.
CONTRACT = ('scope', 'acceptance', 'checks', 'depends_on', 'touches', 'resources', 'kind', 'ownership',
            'live', 'exclusions', 'goal')


class CommandError(Exception):
    """A refusal with its message; nothing was written."""


def _git(repo, *args, env=None):
    clean = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True,
                            env={**clean, **(env or {})}, timeout=60)
    if result.returncode:
        raise CommandError(f'git {args[0]} failed: {result.stderr.strip()}')
    return result.stdout.strip()


@contextmanager
def locked(repo):
    """The repository's task lock: one task-store writer per checkout at a time."""
    git_dir = Path(_git(repo, 'rev-parse', '--absolute-git-dir'))
    with open(git_dir / 'autowork-tasks.lock', 'a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(handle, fcntl.LOCK_UN)


def in_flight(repo, states=OCCUPYING):
    """(task IDs a worker slot in ``states`` or a live lease holds, problems reading that
    state). Engine modules are imported here only: other commands need none of them."""
    import parallel_state
    import task_execution
    held, problems = set(), []
    common = parallel_state.common_dir(Path(repo))
    try:
        slots = parallel_state.slots(common) if (common / 'slots').is_dir() else []
    except ValueError as exc:
        problems.append(f'worker slots cannot be read ({exc})')
        slots = []
    held |= {s['task_id'] for s in slots if s['state'] in states}
    try:
        if parallel_state.live_coordinator(common):
            problems.append('a live parallel coordinator lease')
    except ValueError as exc:
        problems.append(f'the coordinator lease cannot be read ({exc})')
    try:
        lease = task_execution.read(common / 'active.json') if (common / 'active.json').exists() else None
        if lease and task_execution.active_owner(lease):
            problems.append('a live sequential execution lease')
            if isinstance(lease.get('task_id'), str):
                held.add(lease['task_id'])
    except ValueError as exc:
        problems.append(f'the sequential execution lease cannot be read ({exc})')
    return held, problems


def _unheld(repo, tid):
    """Refuse a contract change to a task an attempt holds: integration would set it aside."""
    held, _ = in_flight(repo, ACTIVE)
    if tid in held:
        raise CommandError(f'{tid} is held by a worker slot or a live lease; its contract cannot change now')


def revision(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else None


def expect(repo, tid, rev, goal=False):
    """Refuse when the record is no longer the revision the caller decided from."""
    if rev and revision(_path(repo, tid, goal)) != rev:
        raise CommandError(f'{tid} changed since revision {rev[:12]} was read; reread it; nothing written')


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
    """Next number plus a two-hex hash; IDs in the frozen TODO.archive.md history are taken too."""
    ids = set(store.tasks) | set(store.goals)
    archive = Path(repo) / 'TODO.archive.md'
    if archive.is_file():
        ids |= set(re.findall(r'\b[A-Za-z][A-Za-z0-9_]*-\d+(?:-[0-9a-f]{2})?\b', archive.read_text()))
    numbered = [m.groups() for m in (re.fullmatch(r'([A-Za-z][A-Za-z0-9_]*)-(\d+)(?:-[0-9a-f]{2})?', i)
                                     for i in ids) if m]
    if prefix is None:  # the tasks' most common prefix; never a goal's
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

def _read(repo, rev='HEAD', worktree=False):
    return worktree_store(repo) if worktree else TaskStore.at(repo, rev)


def cmd_list(repo, rev='HEAD', worktree=False):
    store = _read(repo, rev, worktree)
    ready = {t.id: n + 1 for n, t in enumerate(task_select.order(store))}
    rows = []
    for t in sorted(store.tasks.values(), key=lambda t: (t.status != 'open', t.section or '', t.rank or 0, t.id)):
        blocked = task_select.blocking(store, t)
        rows.append(dict(id=t.id, title=t.title, section=t.section, rank=t.rank, status=t.status, goal=t.goal,
                         position=ready.get(t.id), blocked_by=blocked.code if blocked else None))
    return rows


def cmd_show(repo, tid, rev='HEAD', worktree=False):
    store = _read(repo, rev, worktree)
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


def _same_title(title):
    return ' '.join(title.lower().split())


def cmd_add(repo, goal, title, short, section='Now', scope=None, acceptance=(), checks=(), touches=(),
            depends_on=(), task_id=None, prefix=None, resources=(), exclusions=(), kind='implementation',
            ownership='worker', sources=None):
    """One complete record in one write. A task of the same goal with the same title, open or
    done, is the same outcome: it is refused, naming that task, so a repeated pass adds nothing."""
    store = worktree_store(repo)
    if goal not in store.goals:
        raise CommandError(f'unknown goal {goal}')
    same = sorted(t.id for t in store.tasks.values()
                  if t.goal == goal and t.status != 'superseded' and _same_title(t.title) == _same_title(title))
    if same:
        raise CommandError(f'{same[0]} already records "{title}" under {goal}; change that task instead')
    tid = task_id or new_id(repo, store, prefix)
    if tid in store.tasks:
        raise CommandError(f'{tid} already exists')
    fields = dict(schema=1, id=tid, title=title, short=short, status='open', goal=goal, section=section,
                  rank=bottom_rank(store, section), depends_on=list(depends_on), touches=list(touches),
                  resources=list(resources), kind=kind, ownership=ownership, exclusions=list(exclusions))
    if scope:
        fields['scope'] = scope
    if acceptance:
        fields['acceptance'] = list(acceptance)
    if checks:
        fields['checks'] = list(checks)
    text = task_store.render(fields, '\n')
    if sources:
        text = task_store.set_note(text, 'Sources', ' '.join(sources.split()))
    _write(repo, _path(repo, tid), None, text)
    return tid


def cmd_goal(repo, gid, title=None, source=None, priority=None, status=None, focus=None, depends_on=None,
             evidence=None):
    """Add a goal, or change the given fields of an existing one. A met goal names its evidence
    (an executed, passing check), kept as the goal's `Evidence:` note; focus moves to this goal
    from any other. The first goal of a repository starts its store. Returns 'added' or 'changed'."""
    if any(p.is_file() for p in (Path(repo) / 'tasks').glob('*/*.md')):
        store = worktree_store(repo)
    else:  # no record yet: this goal starts tasks/ (Git keeps no empty folder)
        if any((Path(repo) / name).exists() for name in ('TODO.md', 'goals.json')):
            raise CommandError(f'{repo} keeps its tasks in TODO.md and goals.json: run `autowork tasks prepare` to convert it first')
        store = TaskStore(rev='', tasks={}, goals={})
        (Path(repo) / 'tasks' / 'goals').mkdir(parents=True, exist_ok=True)
        (Path(repo) / 'tasks' / 'items').mkdir(exist_ok=True)
    if gid in store.tasks:
        raise CommandError(f'{gid} is a task, not a goal')
    changes = {k: v for k, v in dict(title=title, source=source, priority=priority, status=status, focus=focus,
                                      depends_on=list(depends_on) if depends_on is not None else None).items()
               if v is not None}
    if status == 'met' and not (evidence or '').strip():
        raise CommandError('a met goal needs --evidence naming the executed, passing check')
    for other in depends_on or ():
        if other not in store.goals:
            raise CommandError(f'unknown goal {other}')
    note = ('Evidence', ' '.join(evidence.split())) if evidence else None
    path = _path(repo, gid, goal=True)
    if focus:
        for other in store.goals.values():
            if other.focus and other.id != gid:
                other_path = _path(repo, other.id, goal=True)
                before = other_path.read_bytes()
                _write(repo, other_path, before, task_store.edit(before.decode(), {'focus': False}, goal=True))
    if gid not in store.goals:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', gid):
            raise CommandError('a goal ID uses letters, digits, underscores or hyphens')
        missing = [f'--{k}' for k in ('title', 'source', 'priority') if k not in changes]
        if missing:
            raise CommandError('a new goal needs ' + ', '.join(missing))
        fields = dict(dict(schema=1, id=gid, status='unmet', focus=False, depends_on=[]), **changes)
        text = task_store.render(fields, '\n', goal=True)
        _write(repo, path, None, task_store.set_note(text, *note) if note else text)
        return 'added'
    if not changes and not note:
        raise CommandError('nothing to change')
    before = path.read_bytes()
    text = task_store.edit(before.decode(), changes, goal=True) if changes else before.decode()
    _write(repo, path, before, task_store.set_note(text, *note) if note else text)
    return 'changed'


TYPED = {'rank': int, 'depends_on': list, 'touches': list, 'resources': list, 'acceptance': list,
         'checks': list, 'exclusions': list, 'title': str, 'short': str, 'scope': str, 'goal': str,
         'kind': str, 'ownership': str, 'live': str}


def cmd_field(repo, tid, key, value):
    """A typed header field (rank, touches, ...) or, for any other label, a note line such as
    `Held by` or `Owner decision` in the task's body."""
    _task(worktree_store(repo), tid)
    if key in ('status', 'section', 'id', 'schema'):
        raise CommandError(f'use place or supersede to change {key}')
    if key in CONTRACT:
        _unheld(repo, tid)
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


def cmd_place(repo, tid, section, decision=None):
    """Move an open task to the bottom of a section; ``decision`` also records why, as its
    `Owner decision:` note."""
    store = worktree_store(repo)
    t = _task(store, tid)
    if t.status != 'open':
        raise CommandError(f'{tid} is {t.status}')
    if section not in ('Now', 'Next', 'Needs decision'):
        raise CommandError('section is Now, Next or Needs decision')
    if section != t.section:
        _unheld(repo, tid)
    note = ('Owner decision', ' '.join(decision.split())) if decision else None
    _set(repo, tid, {'section': section, 'rank': bottom_rank(store, section, without=tid)}, note)


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


def cmd_hold(repo, tid, by, until=None):
    """Keep the runner off an open task: its record's `Held by:` note, never its status. A
    held task is never selected or dispatched, and still blocks its dependents and tasks that
    share its resources or serial work, until the note is removed or its date passes."""
    t = _task(worktree_store(repo), tid)
    if t.status != 'open':
        raise CommandError(f'{tid} is {t.status}; only an open task can be held')
    if until and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', until):
        raise CommandError('--until is a date: YYYY-MM-DD')
    value = ' '.join(by.split()) + (f'; until {until}' if until else '')
    _set(repo, tid, {}, ('Held by', value))


def cmd_release(repo, tid):
    """Remove the task's `Held by:` note so the runner may select it again."""
    _task(worktree_store(repo), tid)
    path = _path(repo, tid)
    before = path.read_bytes()
    text = before.decode()
    after = re.sub(r'(?m)^- Held by: .*\n?', '', text)
    if after == text:
        raise CommandError(f'{tid} is not held')
    _write(repo, path, before, after)


def cmd_done(repo, tid, evidence):
    """Close a task without the engine's verified closure: a planning task, or one whose
    acceptance the evidence shows already met. The evidence is kept as the task's note."""
    t = _task(worktree_store(repo), tid)
    if t.status != 'open':
        raise CommandError(f'{tid} is {t.status}')
    if not evidence.strip():
        raise CommandError('done needs --evidence naming why the acceptance is met')
    _unheld(repo, tid)
    _set(repo, tid, {'status': 'done'}, ('Evidence', ' '.join(evidence.split())))


def reopen(repo, tid, reason):
    """Open a done task again, at the bottom of its section, with why as its `Reopened:` note:
    the runner's answer to a close whose receipt no longer matches the task's contract."""
    store = worktree_store(repo)
    t = _task(store, tid)
    if t.status != 'done':
        raise CommandError(f'{tid} is {t.status}')
    section = t.section or 'Now'
    _set(repo, tid, {'status': 'open', 'section': section, 'rank': bottom_rank(store, section, without=tid)},
         ('Reopened', ' '.join(reason.split())))


def cmd_supersede(repo, tid, by, reason):
    store = worktree_store(repo)
    _task(store, tid)
    for other in by:
        _task(store, other)
    _unheld(repo, tid)
    note = ('Superseded by', f'{", ".join(by)}; {" ".join(reason.split())}')
    _set(repo, tid, {'status': 'superseded'}, note)


# --- CLI -------------------------------------------------------------------------------

def add_parser(sub):
    tasks = sub.add_parser('tasks', help='read and edit the tasks/ store')
    verbs = tasks.add_subparsers(dest='verb', required=True)
    for name in ('list', 'validate', 'new-id'):
        p = verbs.add_parser(name)
        p.add_argument('repo', nargs='?', default='.')
        if name in ('validate', 'list'):
            p.add_argument('--worktree', action='store_true', help='read uncommitted edits too')
        if name == 'new-id':
            p.add_argument('--prefix')
        if name != 'new-id':
            p.add_argument('--rev', default='HEAD')
    for name in ('show', 'why'):
        p = verbs.add_parser(name)
        p.add_argument('task')
        p.add_argument('repo', nargs='?', default='.')
        p.add_argument('--rev', default='HEAD')
        if name == 'show':
            p.add_argument('--worktree', action='store_true', help='read uncommitted edits too')
    p = verbs.add_parser('prepare', help='detect, convert, recover and diagnose the store (Docs Sync runs it first)')
    p.add_argument('repo', nargs='?', default='.')
    mode = p.add_mutually_exclusive_group()
    mode.add_argument('--check', action='store_true', help='read only: report the state and what would be done')
    mode.add_argument('--no-commit', action='store_true',
                      help='stage a conversion in the working tree and index; never move HEAD')
    p = verbs.add_parser('add')
    p.add_argument('repo', nargs='?', default='.')
    for flag in ('--goal', '--title', '--short'):
        p.add_argument(flag, required=True)
    p.add_argument('--section', default='Now', choices=('Now', 'Next', 'Needs decision'))
    p.add_argument('--id', dest='task_id')
    p.add_argument('--scope')
    p.add_argument('--kind', default='implementation', choices=('implementation', 'plan', 'inspection'))
    p.add_argument('--ownership', default='worker', choices=('worker', 'coordinator', 'owner'))
    p.add_argument('--sources', help='the accepted path#anchor it comes from, kept as its Sources note')
    for flag in ('--acceptance', '--checks', '--touches', '--depends-on', '--resources', '--exclusions'):
        p.add_argument(flag, action='append', default=[])
    p = verbs.add_parser('field')
    p.add_argument('task'); p.add_argument('label'); p.add_argument('value')
    p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('place')
    p.add_argument('task'); p.add_argument('section', choices=('Now', 'Next', 'Needs decision'))
    p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--decision', help='also record this as its Owner decision (dated, one line)')
    p = verbs.add_parser('move')
    p.add_argument('task'); p.add_argument('direction', choices=('up', 'down'))
    p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('hold', help="keep the runner off an open task (its `Held by:` note)")
    p.add_argument('task'); p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--by', required=True, help='who holds it, for example "an interactive session"')
    p.add_argument('--until', help='YYYY-MM-DD; the hold ends after this day')
    p = verbs.add_parser('release', help='remove the hold so the runner may select the task')
    p.add_argument('task'); p.add_argument('repo', nargs='?', default='.')
    p = verbs.add_parser('done', help='close an open task with the evidence that its acceptance is met')
    p.add_argument('task'); p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--evidence', required=True)
    p = verbs.add_parser('supersede')
    p.add_argument('task'); p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--by', action='append', required=True)
    p.add_argument('--reason', required=True)
    p = verbs.add_parser('goal', help='add a goal, or change its title, source, priority, status, focus or dependencies')
    p.add_argument('goal'); p.add_argument('repo', nargs='?', default='.')
    p.add_argument('--title'); p.add_argument('--source', help='the accepted plan or spec it comes from, path#anchor')
    p.add_argument('--priority', type=int, help='1 is first among goals')
    p.add_argument('--status', choices=('unmet', 'partial', 'unverified', 'met'))
    p.add_argument('--focus', action=argparse.BooleanOptionalAction, default=None,
                   help='the one goal whose tasks go first')
    p.add_argument('--depends-on', action='append', help='a goal that must be met first')
    p.add_argument('--evidence', help='for --status met: the executed, passing check')
    for name in WRITES:
        if name != 'add':
            verbs.choices[name].add_argument('--expect', metavar='REVISION',
                                             help='refuse unless the record is still this revision (show --worktree)')
    return tasks


WRITES = ('add', 'field', 'place', 'move', 'hold', 'release', 'done', 'supersede', 'goal')


def run(args, repo):
    """Print the result as JSON (reads) or one line (writes); return the exit code. Writes
    hold the repository's task lock, so two writers never interleave."""
    try:
        if args.verb == 'prepare':
            from pi_autowork import task_prepare
            out = task_prepare.prepare(repo, 'check' if args.check else 'stage' if args.no_commit else 'commit')
            print(json.dumps(out, indent=2))
            return 0 if out['ok'] else 1
        if args.verb in WRITES:
            with locked(repo):
                if getattr(args, 'expect', None):
                    goal = args.verb == 'goal'
                    expect(repo, args.goal if goal else args.task, args.expect, goal)
                out = _run(args, repo)
        else:
            out = _run(args, repo)
    except (CommandError, StoreError, WriteError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(out if isinstance(out, str) else json.dumps(out, indent=2))
    return 0


def _run(args, repo):
    verb = args.verb
    if verb == 'list':
        out = cmd_list(repo, args.rev, args.worktree)
    elif verb == 'show':
        out = cmd_show(repo, args.task, args.rev, args.worktree)
    elif verb == 'why':
        out = cmd_why(repo, args.task, args.rev)
    elif verb == 'validate':
        out = cmd_validate(repo, args.rev, args.worktree)
    elif verb == 'new-id':
        out = cmd_new_id(repo, args.prefix)
    elif verb == 'add':
        out = 'added ' + cmd_add(repo, args.goal, args.title, args.short, args.section, args.scope,
                                 args.acceptance, args.checks, args.touches, args.depends_on, args.task_id,
                                 resources=args.resources, exclusions=args.exclusions, kind=args.kind,
                                 ownership=args.ownership, sources=args.sources)
    elif verb == 'field':
        cmd_field(repo, args.task, args.label, args.value)
        out = f'ok {args.task} {args.label}'
    elif verb == 'place':
        cmd_place(repo, args.task, args.section, args.decision)
        out = f'ok {args.task} -> {args.section}'
    elif verb == 'move':
        changes = cmd_move(repo, args.task, args.direction)
        out = 'ok ' + ', '.join(f'{tid} rank {rank}' for tid, rank in changes.items())
    elif verb == 'hold':
        cmd_hold(repo, args.task, args.by, args.until)
        out = f'ok {args.task} held'
    elif verb == 'release':
        cmd_release(repo, args.task)
        out = f'ok {args.task} released'
    elif verb == 'done':
        cmd_done(repo, args.task, args.evidence)
        out = f'ok {args.task} done'
    elif verb == 'supersede':
        cmd_supersede(repo, args.task, args.by, args.reason)
        out = f'ok {args.task} superseded'
    elif verb == 'goal':
        out = f'{cmd_goal(repo, args.goal, args.title, args.source, args.priority, args.status, args.focus, args.depends_on, args.evidence)} goal {args.goal}'
    return out
