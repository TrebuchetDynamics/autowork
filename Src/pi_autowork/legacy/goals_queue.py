"""Goal/task eligibility, human priority drift and order reconciliation."""
import json
import sys

from .goals_ledger import (
    PRIORITY_SCHEMA, SECTIONS, SECTION_RANK, STATUS_RANK,
)
from .goals_todo import (
    task_blocks, task_bodies,
)


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


def priority_status(data, text, *, bodies=None):
    """Compare TODO.md's unfinished-task sequence with the last reconciled record."""
    record = data.get('priority_order')
    if not record:
        return {'state': 'unmigrated', 'action': UNMIGRATED_ACTION}
    active = active_task_ids(data)
    if bodies is None:
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


def queue(data, text, *, allow_drift=False, bodies=None):
    """The shared selection guard; optional pre-parsed bodies belong to this exact text."""
    status = priority_status(data, text, bodies=bodies)
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
