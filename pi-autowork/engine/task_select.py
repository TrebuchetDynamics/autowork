"""Task selection over a TaskStore snapshot: one order, one next task, one explanation.

The sort key keeps the engine's selection rule: the focused goal first, then section
(Now before Next), then each task's rank, goal priority, goal status and task ID.
A task is selectable when it is open, not a draft, in Now or Next, its dependencies
are done, its goal is not met and its goal's dependencies are met. Authority
(ownership, live resources) is not a selection rule: admission applies it afterwards,
as it does for the TODO.md queue.
"""
from dataclasses import dataclass
import datetime
import re

SECTION_RANK = {'Now': 0, 'Next': 1}
# Lower runs first: unverified goals before partial ones, partial before unmet.
GOAL_STATUS_RANK = {'unverified': 0, 'partial': 1, 'unmet': 2, 'met': 3}
KEY_RULES = ('FOCUS', 'SECTION', 'RANK', 'GOAL_PRIORITY', 'GOAL_STATUS', 'TASK_ID')
# `- Held by: <who>; until <YYYY-MM-DD>` in a task's body is its claim: an open task held by
# someone is not selected. Without a date it holds until the line is removed.
HELD_BY = re.compile(r'^- Held by: (.*)$', re.M)
UNTIL = re.compile(r'\buntil (\d{4}-\d{2}-\d{2})\b')


@dataclass(frozen=True)
class Reason:
    """Why a task is or is not selected: a stable ``code`` and the ID or value it names."""
    code: str
    detail: str = ''


def _finished(store, done):
    return {tid for tid, task in store.tasks.items() if task.status == 'done'} | set(done)


def blocking(store, task, done=()):
    """The first rule that keeps ``task`` out of the order, or None when it is selectable."""
    if task.status == 'done':
        return Reason('DONE')
    if task.status == 'superseded':
        return Reason('SUPERSEDED')
    if task.section not in SECTION_RANK:
        return Reason('NEEDS_DECISION', task.section or '')
    if task.draft:
        return Reason('DRAFT', ', '.join(task.missing_fields))
    if (holder := held_by(task)) is not None:
        return Reason('HELD', holder)
    goal = store.goals.get(task.goal)
    if goal is None:
        return Reason('NO_GOAL', task.goal or '')
    if goal.status == 'met':
        return Reason('GOAL_MET', goal.id)
    for dep in goal.depends_on:
        if store.goals[dep].status != 'met':
            return Reason('GOAL_DEPENDENCY_UNMET', dep)
    finished = _finished(store, done)
    for dep in task.depends_on:
        if dep not in finished:
            return Reason('DEPENDENCY_UNFINISHED', dep)
    return None


def held_by(task, today=None):
    """Who holds an open task, from its last `Held by:` note, or None (no note, or past its date)."""
    lines = HELD_BY.findall(task.body or '')
    if not lines:
        return None
    holder = lines[-1].strip()
    until = UNTIL.search(holder)
    if until and datetime.date.fromisoformat(until[1]) < (today or datetime.date.today()):
        return None
    return holder


def _key(store, task):
    goal = store.goals[task.goal]
    return (0 if goal.focus else 1, SECTION_RANK[task.section], task.rank, goal.priority,
            GOAL_STATUS_RANK[goal.status], task.id)


def order(store, done=()):
    """Every selectable task, highest priority first, planning tasks included. ``done``
    adds IDs known closed outside this snapshot."""
    ready = [task for task in store.tasks.values() if blocking(store, task, done) is None]
    return sorted(ready, key=lambda task: _key(store, task))


def next(store, done=()):
    """The first selectable task that is not a planning task, or None."""
    return min((task for task in order(store, done) if task.kind.value != 'plan'),
               key=lambda task: _key(store, task), default=None)


def why(store, task_id, done=()):
    """(first, [Reason]) for one task: the rule that blocks it, or its 1-based position and
    the part of the sort key that put the task ahead of it first."""
    task = store.tasks.get(task_id)
    if task is None:
        return False, [Reason('UNKNOWN_TASK', task_id)]
    if (reason := blocking(store, task, done)) is not None:
        return False, [reason]
    ranked = order(store, done)
    position = [t.id for t in ranked].index(task_id)
    reasons = [Reason('POSITION', str(position + 1))]
    if position:
        ahead = ranked[position - 1]
        rule = next_rule(_key(store, ahead), _key(store, task))
        reasons.append(Reason('AFTER_' + rule, ahead.id))
    return position == 0, reasons


def next_rule(ahead, behind):
    """The first sort-key rule on which two keys differ."""
    return KEY_RULES[[a != b for a, b in zip(ahead, behind)].index(True)]
