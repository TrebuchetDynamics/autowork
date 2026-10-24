"""Read-only task, receipt and live-followup preparation; no transaction authority."""
from dataclasses import dataclass
import os
from pathlib import Path
import re
from typing import Callable

from pi_autowork.engine import task_store


@dataclass(frozen=True)
class ClosurePorts:
    """Current owner dependencies, bound by the compatibility facade for each call."""
    git: Callable
    passed: Callable
    task_path: Callable
    live_items: Callable


def receipt_path(task):
    return f'tasks/evidence/{task}.toml'


def receipt_text(repo, task, slot, info, checks, record, *, ports):
    """The closure's evidence, deterministic for one verified operation: no time, no logs, no
    transcript; secrets redacted and absolute paths dropped, as for public commits."""
    from pi_autowork.engine import check_receipt
    command = (checks.get('command_receipt') or {}).get('argv') or (checks.get('command_receipt') or {}).get('command') or []
    if isinstance(command, str):
        command = [command]

    def public(text):
        text = check_receipt.redact(str(text))
        return re.sub(r'(?<![\w.-])/(?:[^\s/]+/)+[^\s/]*', '<path>', text)

    tree = ports.git(repo, 'rev-parse', f"{info['commit']}^{{tree}}")
    review = (slot.get('review') or {}).get('decision') or ('passed' if ports.passed(checks) else 'failed')
    fields = [('schema', 1), ('task', task), ('candidate', slot['commit']), ('integration', info['commit']),
              ('tree', tree), ('contract_hash', record.contract_hash),
              ('checks', [public(part) for part in command]),
              ('result', 'pass' if ports.passed(checks) else 'fail'), ('review', public(review))]
    lines = [f'{key} = {task_store.toml_value(key, value)}' for key, value in fields]
    return '\n'.join(lines) + '\n'


def live_backlog_id(record):
    """One live-qualification backlog per goal, never one Needs-decision task per close."""
    goal = record.goal or 'UNASSIGNED'
    return 'LIVE-' + re.sub(r'[^A-Za-z0-9._-]+', '-', goal)


def followup_text(task, record, items, *, existing=None, followup=None):
    """A per-goal Needs decision backlog for live checks offline closes left pending.

    The old one-task-per-close follow-up turned a fleet's ordinary offline delivery into
    dozens of owner questions. One backlog per goal keeps every live obligation visible
    without multiplying Decision rows. ``existing`` is (path, text) when the backlog is
    already present in the worktree or at HEAD.
    """
    followup = followup or live_backlog_id(record)
    proof = [' '.join(f'{task}: {item}'.split()) for item in items]
    if existing is not None:
        path, text = existing
        parsed = task_store._Document(path, text.encode()).record(text.encode(), False)
        fields = dict(
            depends_on=sorted(set(parsed.depends_on) | {task}),
            touches=list(dict.fromkeys([*parsed.touches, *(record.touches or ['**'])])),
            resources=list(dict.fromkeys([*parsed.resources, *record.resources])),
            acceptance=list(dict.fromkeys([*parsed.acceptance, *proof])))
        return followup, task_store.edit(text, fields)
    fields = dict(schema=1, id=followup, title='Live qualifications for ' + (record.goal or 'unassigned work'),
                  short='Live qualifications', status='open', goal=record.goal,
                  section='Needs decision', rank=task_store_rank(record), depends_on=[task],
                  touches=list(record.touches) or ['**'], resources=list(record.resources),
                  kind='implementation', ownership='owner', exclusions=['Offline evidence does not count'],
                  scope='Owner-authorized live checks accumulated from offline task closures in this goal.',
                  acceptance=proof, checks=['Live qualification by an authorized person'])
    return followup, task_store.render(fields, '\n')


def existing_backlog(repo, followup, *, ports):
    """(path, text) of a backlog in the worktree or at HEAD, or None."""
    path = ports.task_path(followup)
    target = Path(repo) / path
    try:
        return path, target.read_text()
    except OSError:
        try:
            return path, ports.git(repo, 'show', f'HEAD:{path}', raw=True).decode()
        except ValueError:
            return None


def backlog_target(repo, record, *, ports):
    """The open backlog to append to, or the first free backlog ID if earlier ones closed."""
    base = live_backlog_id(record)
    for number in range(1, 100):
        followup = base if number == 1 else f'{base}-{number}'
        found = existing_backlog(repo, followup, ports=ports)
        if found is None:
            return followup, None
        parsed = task_store._Document(found[0], found[1].encode()).record(found[1].encode(), False)
        if parsed.status == 'open':
            return followup, found
    raise ValueError(f'too many closed live backlogs for {record.goal or "unassigned work"}')


def task_store_rank(record):
    return (record.rank or 0) + 1


def close_writes(repo, task, slot, info, checks, record, *, ports):
    """Prepare {path: text} for the task's done record, receipt and pending live checks.
    By default live checks are notes on the done record, not another owner decision;
    PI_AUTOWORK_LIVE_FOLLOWUP=backlog keeps the per-goal backlog behavior, and =none drops the
    notes. Nothing else; TODO.archive.md is not written."""
    # From the record as committed: a close records the verified contract, never a local edit.
    committed = ports.git(repo, 'show', f'HEAD:{ports.task_path(task)}', raw=True).decode()
    text = task_store.edit(committed, {'status': 'done', 'closure': 'coordinator_verified',
                                       'closure_evidence': receipt_path(task),
                                       **{key: None for key in ('closure_actor', 'closure_timestamp',
                                                               'closure_reason', 'owner_waiver', 'owner_qualification')}})
    writes = {ports.task_path(task): text, receipt_path(task): receipt_text(repo, task, slot, info, checks, record, ports=ports)}
    live = ports.live_items((slot.get('report') or {}).get('pending_live'))
    if live:
        mode = os.environ.get('PI_AUTOWORK_LIVE_FOLLOWUP', 'notes').strip().lower()
        if mode == 'backlog':
            followup, existing = backlog_target(repo, record, ports=ports)
            followup, body = followup_text(task, record, live, existing=existing, followup=followup)
            writes[ports.task_path(followup)] = body
        elif mode != 'none':
            fresh = [item for item in live
                     if f'- Pending live: {" ".join(item.split())}' not in text]
            if fresh:
                text = text.rstrip('\n') + '\n' + ''.join(
                    f'- Pending live: {" ".join(item.split())}\n' for item in fresh)
                writes[ports.task_path(task)] = text
    return writes
