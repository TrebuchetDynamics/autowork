"""Read-only parallel progress and journal-derived metrics.

Durations are observed state durations, not provider billing or CPU time. Worker,
integration and waiting time sum task intervals (so overlapping time is counted
per task); wall time is elapsed coordinator-run time, excluding released gaps.
"""
import json
import math
from pathlib import Path
import time

import parallel_dispatch as dispatch
import parallel_state as state
import task_execution as execution

WORKING = {'running'}
INTEGRATING = {'integrating'}
WAITING = {'dispatched', 'reported', 'integrated', 'held', 'interrupted', 'released', 'waiting'}


def journal(common):
    path = execution.safe_path(common / 'journal.jsonl')
    if not path.exists():
        return []
    events = []
    for line in path.read_text().splitlines():
        value = json.loads(line, object_pairs_hook=execution.unique)
        if (not isinstance(value, dict) or type(value.get('timestamp')) not in (float, int)
                or not math.isfinite(value['timestamp']) or not isinstance(value.get('event'), str)):
            raise ValueError('malformed parallel journal event')
        if events and value['timestamp'] < events[-1]['timestamp']:
            raise ValueError('parallel journal timestamps moved backwards')
        events.append(value)
    return events


def metrics(events, now):
    """Replay intervals once; repeated same-state receipt writes do not double count."""
    totals = dict(wall_seconds=0.0, worker_seconds=0.0, integration_seconds=0.0,
                  waiting_seconds=0.0, peak_workers=0, conflicts=0, retries=0)
    phases, attempts = {}, {}
    last = events[0]['timestamp'] if events else now
    coordinator = False
    for event in [*events, {'timestamp': now, 'event': '_end'}]:
        stamp = max(last, event['timestamp'])
        delta = stamp - last
        if coordinator:
            totals['wall_seconds'] += delta
        for phase in phases.values():
            key = ('worker_seconds' if phase in WORKING else 'integration_seconds'
                   if phase in INTEGRATING else 'waiting_seconds' if phase in WAITING else None)
            if key:
                totals[key] += delta
        kind = event['event']
        if kind == 'coordinator_claimed':
            coordinator = True
        elif kind == 'coordinator_released':
            coordinator = False
        elif kind == 'slot_changed':
            slot = event['slot']
            task = slot['task_id']
            old = phases.get(task)
            attempt = slot.get('attempt', 1)
            if attempt > attempts.get(task, attempt):
                totals['retries'] += attempt - attempts[task]
            attempts[task] = attempt
            if slot['state'] == 'held' and old != 'held' and 'conflict' in slot.get('reason', '').lower():
                totals['conflicts'] += 1
            phases[task] = slot['state']
        elif kind == 'dispatch_observed':
            # Pending tasks have no worker slot yet. Replace the previous pending
            # snapshot, without erasing held/reported execution phases.
            phases = {k: v for k, v in phases.items() if v != 'waiting'}
            for item in event['waiting']:
                phases.setdefault(item['id'], 'waiting')
        totals['peak_workers'] = max(totals['peak_workers'], sum(p in WORKING for p in phases.values()))
        last = stamp
    return totals


def snapshot(repo, *, now=None):
    repo = Path(execution.git(Path(repo).expanduser().resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common = state.common_dir(repo)
    # Atomic slot writes and complete journal appends are read under the same lock
    # as writers. An untouched repository needs no new runtime directory.
    if common.exists():
        with execution.lock(common / 'writer.lock'):
            return _snapshot(repo, common, time.time() if now is None else now)
    return _snapshot(repo, common, time.time() if now is None else now)


def pending_tasks(repo, known=()):
    """Visible TODO-only and indexed tasks that do not yet have execution slots."""
    todo = repo / 'TODO.md'
    if not todo.exists():
        return []
    goals = execution.goals_module()
    bodies = goals.task_bodies(todo.read_text())
    done = {task for task, items in bodies.items() if len(items) == 1 and items[0][1].lower() == 'x'}
    done.update(execution.archived_done(repo))
    indexed = {}
    if (repo / 'goals.json').exists():
        indexed = {t['id']: t for t in goals.normalize(goals.load(repo))['tasks']}
        done.update(task for task, value in indexed.items() if value['status'] == 'done')
    result = []
    import re
    for task, items in bodies.items():
        if task in known or not any(item[2] in ('Now', 'Next') for item in items):
            continue
        if len(items) != 1:
            raise ValueError('duplicate TODO task IDs in parallel status')
        body, mark, section = items[0]
        if task in done or section not in ('Now', 'Next'):
            continue
        fields = goals.task_fields(body)
        deps = fields.get('Dependencies', 'None.').strip().strip('.')
        unresolved = [] if re.split(r';|\.\s', deps)[0].lower() in ('none', 'none required', '—', '-', '') else [
            dep for dep in re.findall(r'[A-Za-z0-9][A-Za-z0-9_-]*', deps) if dep not in done]
        running = fields.get('Status', indexed.get(task, {}).get('status', '')).startswith('in_progress')
        reason = ('sequential task in progress' if running else 'dependency: ' + ', '.join(unresolved)
                  if unresolved else 'awaiting dispatch')
        result.append(dict(id=task, reason=reason))
    return result


def _snapshot(repo, common, now):
    events = journal(common)
    coordinator = state.lease(common)
    last_coordinator = next((e['coordinator'] for e in reversed(events) if e['event'] == 'coordinator_claimed'), {})
    capacity = (coordinator or last_coordinator).get('max_workers', 0)
    observed = next((e for e in reversed(events) if e['event'] == 'dispatch_observed'), {})
    capacity = observed.get('max_workers', capacity)
    pending = {v['id']: v['reason'] for v in observed.get('waiting', [])}
    rows = []
    active = 0
    for slot in state.slots(common):
        task = slot['task_id']
        live = slot['state'] in ('running', 'dispatched') and state.worker_live(slot)
        active += live
        changes = [e for e in events if e['event'] == 'slot_changed' and e['task_id'] == task]
        end = changes[-1]['timestamp'] if changes and slot['state'] == 'closed' else now
        rows.append(dict(task=task, state=slot['state'], slot=dispatch.meta(common, slot).get('slot_index'),
                         elapsed_seconds=max(0, end - (changes[0]['timestamp'] if changes else slot['started_at'])),
                         reason=slot.get('reason'), worktree=slot['worktree'], checks=slot.get('checks'),
                         commit=slot.get('commit'), integration=slot.get('integration'), attempt=slot['attempt'],
                         worker_live=live))
        pending.pop(task, None)
    # Include dependencies and pre-existing sequential claims that have no slot.
    for item in pending_tasks(repo, {r['task'] for r in rows}):
        task = item['id']
        observations = [e['timestamp'] for e in events if e['event'] == 'dispatch_observed'
                        and any(v['id'] == task for v in e['waiting'])]
        rows.append(dict(task=task, state='waiting', slot=None,
                         elapsed_seconds=max(0, now - observations[0]) if observations else 0,
                         reason=(item['reason'] if pending.get(task, '').startswith('dependency:')
                                 else pending.get(task, item['reason'])), worktree=None, checks=None,
                         commit=None, integration=None, attempt=0, worker_live=False))
    return dict(outcome='PARALLEL_STATUS', workspace=str(repo), active_workers=active, max_workers=capacity,
                tasks=rows, completed=sum(r['state'] == 'closed' for r in rows),
                failed=sum(r['state'] in ('held', 'interrupted', 'released') for r in rows),
                integration_queue=sum(r['state'] in ('reported', 'integrating') for r in rows),
                metrics=metrics(events, now))


def render(value):
    def text(value, width):
        # Keep untrusted task reasons on one terminal line and bound table width.
        return ' '.join(str(value).split())[:width]
    lines = ['AUTOWORK — PARALLEL', f"Workers: {value['active_workers']}/{value['max_workers']} active",
             f"{'Task':<20} {'State':<12} {'Slot':>4} {'Elapsed':>9}  Blocked reason"]
    for row in value['tasks']:
        lines.append(f"{text(row['task'], 20):<20} {row['state']:<12} {str(row['slot'] or '-'):>4} "
                     f"{row['elapsed_seconds']:>8.1f}s  {text(row['reason'] or '-', 70)}")
    lines.append(f"Completed: {value['completed']}  Failed: {value['failed']}  Integration queue: {value['integration_queue']}")
    m = value['metrics']
    lines += [f"Wall: {m['wall_seconds']:.1f}s  Worker: {m['worker_seconds']:.1f}s  Integration: {m['integration_seconds']:.1f}s  Waiting/blocked: {m['waiting_seconds']:.1f}s",
              f"Peak workers: {m['peak_workers']}  Conflicts: {m['conflicts']}  Retries: {m['retries']}"]
    return '\n'.join(lines)
