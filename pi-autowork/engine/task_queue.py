"""The engine's one view of a repository's tasks: TaskStore records at a pinned commit.

Selection, dispatch, claims, retry, status and integration read tasks only through this
module. A contract handed to the planner and workers is built from one record: its
``fields`` carry the typed values under the labels the admission rules read (Touches,
Resources, Ownership, Live authorization, Kind, Dependencies, ...), followed by the
record's body notes (Held by, Owner decision, Next action, ...); typed values always win
over a note of the same label. A repository without tasks/ selects nothing: it says to
run `autowork migrate`.
"""
import datetime
from functools import lru_cache
import re
import subprocess
import tomllib

import task_select
from task_store import Ownership, LiveAuthorization, Kind, StoreError, TaskStore, _blobs

NOTE = re.compile(r'^- ([A-Za-z][A-Za-z \'-]*): (.*)$', re.M)
UNCONVERTED = 'no tasks/ store: run `autowork migrate {repo}` to convert this repository once'


class Unconverted(StoreError):
    """The repository has no task store; nothing is selected from it."""


def commit(repo, rev='HEAD'):
    """The commit a revision names, or None when it names none (an unborn branch)."""
    result = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--verify', '-q', f'{rev}^{{commit}}'],
                            capture_output=True, text=True, timeout=30)
    return result.stdout.strip() or None


@lru_cache(maxsize=32)
def _store(repo, sha):
    return TaskStore.at(repo, sha)


def store(repo, rev='HEAD'):
    """The TaskStore at ``rev`` (cached by commit); Unconverted when it has no tasks/."""
    sha = commit(repo, rev)
    if sha is None:
        raise Unconverted(UNCONVERTED.format(repo=repo))
    try:
        return _store(str(repo), sha)
    except StoreError as exc:
        if 'no task store' in str(exc):
            raise Unconverted(UNCONVERTED.format(repo=repo)) from None
        raise


def notes(record):
    """Body notes `- Label: value`, in order; a later line of the same label wins."""
    return {label: value.strip() for label, value in NOTE.findall(record.body)}


def fields(record):
    """The labels the admission and planning rules read, from the record's typed values."""
    view = dict(notes(record))
    view.update(Status=record.status or '', Goal=record.goal or '', Short=record.short)
    for label in ('Ownership', 'Resources', 'Live authorization', 'Kind', 'Touches', 'Held by'):
        view.pop(label, None)  # only the typed value grants or limits anything
    if (holder := task_select.held_by(record)) is not None:
        view['Held by'] = holder  # a current hold only; an expired one is history
    if record.status == 'open' or record.scope:
        view.update(Scope=record.scope, Acceptance='; '.join(record.acceptance),
                    Checks='; '.join(record.checks),
                    Dependencies=', '.join(record.depends_on) or 'None.')
        if record.verified_depends_on:
            view['Verified dependencies'] = ', '.join(record.verified_depends_on)
        if record.exclusions:
            view['Exclusions'] = '; '.join(record.exclusions)
    if record.touches and record.touches != ('**',):  # ** stands for an unknown set, as no Touches did
        view['Touches'] = ', '.join(record.touches)
    if record.resources:
        view['Resources'] = ', '.join(record.resources)
    if record.ownership == Ownership.OWNER:
        view['Ownership'] = 'Owner only'
    if record.live == LiveAuthorization.AUTHORIZED:
        view['Live authorization'] = 'authorized in the task record'
    if record.kind == Kind.PLAN:
        view['Kind'] = 'plan'
    return view


def contract_text(record):
    """What a worker reads: the task as its file states it at the pinned commit."""
    lines = [f'{record.id} — {record.title}', '']
    for label, value in fields(record).items():
        if value:
            lines.append(f'- {label}: {value}')
    return '\n'.join(lines)


def contract(record, snapshot):
    return {'id': record.id, 'title': record.title, 'section': record.section,
            'contract': contract_text(record), 'fields': fields(record),
            'record_revision': record.record_revision, 'contract_hash': record.contract_hash,
            'rev': snapshot.rev, 'priority': {'state': 'store', 'rev': snapshot.rev}}


def reason(snapshot, task_id, plan=None):
    """Why a task is not selectable, in words, or None when it is."""
    record = snapshot.tasks.get(task_id)
    if record is None:
        return 'missing from tasks/'
    blocked = task_select.blocking(snapshot, record)
    if blocked is not None:
        words = {'DONE': 'completed', 'SUPERSEDED': 'superseded', 'NEEDS_DECISION': 'decision-held',
                 'DRAFT': 'needs Scope, Acceptance, Checks and Touches (draft: {})',
                 'NO_GOAL': 'no goal {}', 'GOAL_MET': 'goal {} is met',
                 'GOAL_DEPENDENCY_UNMET': 'goal dependency {} is unmet',
                 'DEPENDENCY_UNFINISHED': 'unresolved dependency {}',
                 'DEPENDENCY_UNVERIFIED': 'dependency {} needs verified evidence or an owner waiver/qualification',
                 'HELD': 'held by {}'}
        return words[blocked.code].format(blocked.detail)
    if plan and plan not in re.findall(r'\]\(([^)]+)\)', notes(record).get('Sources', '')):
        return 'not linked to the named plan'
    return None


def selectable(repo, requested=None, plan=None, *, sequential=False, rev='HEAD'):
    """(contracts in priority order, reasons for the rest) at ``rev``."""
    snapshot = store(repo, rev)
    wanted = requested.split(',') if requested else None
    ordered = [t.id for t in task_select.order(snapshot)]
    # Every other open task in Now/Next is listed with its reason, never silently skipped.
    others = sorted((t for t in snapshot.tasks.values() if t.status == 'open' and t.id not in ordered
                     and t.section in task_select.SECTION_RANK),
                    key=lambda t: (task_select.SECTION_RANK[t.section], t.rank or 0, t.id))
    pool = wanted or ordered + [t.id for t in others]
    chosen, why = [], []
    for tid in pool:
        if (text := reason(snapshot, tid, plan)) is not None:
            why.append(f'{tid}: {text}')
            continue
        record = snapshot.tasks[tid]
        if sequential and record.kind == Kind.PLAN:
            why.append(f'{tid}: ready for planning (maintainer only)')
            continue
        chosen.append(contract(record, snapshot))
    return chosen, why


def unfinished(repo, rev='HEAD'):
    """Every open task as a contract, runnable or not: planning context for hot files."""
    snapshot = store(repo, rev)
    return [contract(t, snapshot) for t in snapshot.tasks.values() if t.status == 'open']


def closed(repo, rev='HEAD'):
    """IDs done or superseded at ``rev``; an unreadable or unconverted revision closes nothing."""
    try:
        snapshot = store(repo, rev)
    except StoreError:
        return set()
    return {t.id for t in snapshot.tasks.values() if t.status in ('done', 'superseded')}


def qualified(repo, rev='HEAD'):
    """Done prerequisites with a verified receipt or an explicit owner waiver/qualification."""
    return {t.id for t in store(repo, rev).tasks.values() if t.status == 'done' and t.qualified}


def present(repo, rev='HEAD'):
    """Every task ID the store records at ``rev``, closed ones included; None when unreadable."""
    try:
        return set(store(repo, rev).tasks)
    except StoreError:
        return None


def _dated(text):
    stamp = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', text)
    try:
        return bool(stamp) and bool(datetime.date.fromisoformat(stamp[1]))
    except ValueError:
        return False  # 2026-02-30 is no date


def deferred(snapshot):
    """Owner-answered deferrals: open tasks in Needs decision with a dated `Owner decision:` note.
    Their dependents wait for them without another question."""
    return {t.id for t in snapshot.tasks.values() if t.status == 'open' and t.section == 'Needs decision'
            and _dated(notes(t).get('Owner decision', ''))}


CONTRACT_LINE = re.compile(r"^[ \t]*(?:[-*][ \t]+)?([A-Za-z][A-Za-z '/-]*):[ \t]*(.*)$", re.M)


def parse_contract(text):
    """{label: value} of a contract as contract_text() wrote it (`- Label: value`; the first line
    is its title), or as an attempt dispatched before the store recorded it (`Label: value`)."""
    return {label: value.strip() for label, value in CONTRACT_LINE.findall(text or '')}


def record(repo, task_id, rev='HEAD'):
    """The task's record at ``rev``, or None when the store lacks it or cannot be read."""
    try:
        return store(repo, rev).tasks.get(task_id)
    except StoreError:
        return None


def order_ranks(repo):
    """{task: position} of the open Now/Next tasks in the store's priority order at HEAD."""
    snapshot = store(repo)
    open_tasks = sorted((t for t in snapshot.tasks.values() if t.status == 'open' and t.section in task_select.SECTION_RANK),
                        key=lambda t: (task_select.SECTION_RANK[t.section], t.rank or 0, t.id))
    return {t.id: index for index, t in enumerate(open_tasks)}, {t.id: set(t.depends_on) for t in open_tasks}


def stale_closures(repo, rev='HEAD'):
    """[(task, receipt hash, record hash)] for each done task whose verified close no longer
    covers its contract: its receipt tasks/evidence/<ID>.toml pins another contract_hash than
    its record has at ``rev``. A merge can produce one (one side closed the task, the other
    changed its acceptance); the runner reopens it, since no one verified the merged contract.
    A task closed without a receipt (by a person, with its evidence note) is not checked."""
    snapshot = store(repo, rev)
    done = {t.id: t for t in snapshot.tasks.values()
            if t.status == 'done' and t.closure == 'coordinator_verified'}
    listing = subprocess.run(['git', '-C', str(repo), 'ls-tree', '-z', snapshot.rev, '--', 'tasks/evidence/'],
                             capture_output=True, timeout=60).stdout.split(b'\0')
    receipts = {}
    for entry in listing:
        if not entry:
            continue
        metadata, path = entry.split(b'\t', 1)
        task = path.decode().removeprefix('tasks/evidence/').removesuffix('.toml')
        if task in done and metadata.split()[1] == b'blob':
            receipts[task] = metadata.split()[2].decode()
    found = []
    for task, blob in zip(receipts, _blobs(repo, list(receipts.values()))):
        try:
            pinned = tomllib.loads(blob.decode()).get('contract_hash')
        except (UnicodeDecodeError, tomllib.TOMLDecodeError):
            pinned = None  # an unreadable receipt proves nothing about this contract
        if pinned != done[task].contract_hash:
            found.append((task, pinned, done[task].contract_hash))
    return sorted(found)
