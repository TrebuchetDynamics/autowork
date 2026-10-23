"""Plain, read-only diagnostic text for one selected runner. No actions or probes.

Fleet observations, committed selection rules and recorded runtime states remain
separate: a runtime observation is not proof of current admission or ownership.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from pi_autowork import fleet_view


def _plain(value):
    # Literal markup is useful in a copied question; terminal control sequences aren't.
    return ''.join(c if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127)
                   else f'\\x{ord(c):02x}' for c in str(value))


def build(runner):
    """Collect a stable report on demand; callers must run this off the UI thread.

    Only the selected repo's committed TaskStore and its status file are read.
    Do not call setup_label/needs/verdict: those may run a preparation audit.
    """
    lines = ['BLOCKERS — READ ONLY',
             'Captured: ' + datetime.now(timezone.utc).isoformat(timespec='seconds'),
             'Runner: ' + runner.name, 'Repository: ' + (runner.repo or '(unknown)'),
             '', 'Fleet observation (last refresh; may be stale)',
             'State: ' + runner.state, 'Service: ' + (runner.service or '(not observed)'),
             'State duration: ' + (fleet_view.duration(runner.minutes) or '(unknown)')]
    for label, value in [('Startup refusal', runner.stop_reason), ('Dispatch blocker', runner.blocker),
                         ('Resource gate', runner.gate), ('Preparation state', runner.prepare_state),
                         ('Restart', runner.restarting), ('Main check', fleet_view.main_check.line(runner.main_check))]:
        if value:
            lines.append(f'{label}: {value}')
    # The fleet's short line deliberately abbreviates IDs; the copied report must not.
    for field in ('state', 'rev', 'main_head', 'checked_rev', 'green', 'gated', 'crashed',
                  'red_since', 'crash', 'failures', 'flaky', 'commits'):
        if field in runner.main_check:
            lines.append(f'Main check {field}: ' + json.dumps(runner.main_check[field], ensure_ascii=False))
    snapshot = getattr(runner, 'snapshot', None)
    if snapshot is not None:
        lines.append(f'Inventory at fleet refresh: {snapshot.freshness}; revision {snapshot.revision}; '
                     f'captured {snapshot.captured_at}; execution {snapshot.engine_freshness}')
    errors = [*getattr(runner, 'acquisition_errors', ()), *(snapshot.errors if snapshot else ())]
    for error in dict.fromkeys(errors):
        lines.append('Fleet acquisition error (last refresh): ' + str(error))
    lines.extend(['', 'Recorded holds, waits and dependency roots (fleet observation)'])
    for task, cause in runner.held:
        lines.append(f'- {task}: held; {cause or "cause not recorded"}')
    for group in [*runner.stopped_groups, *runner.waiting_groups]:
        tasks = group.get('tasks') or []
        lines.append(f'- {group.get("label", "reason not recorded")}: ' + ', '.join(map(str, tasks)))
        if group.get('count', len(tasks)) > len(tasks):
            lines.append(f'  {group["count"]} reported; only {len(tasks)} IDs recorded by this producer.')
    for root in runner.roots:
        lines.append(f'- Root {root.get("id", "unknown")}: {root.get("kind", "unknown")}; '
                     f'blocks {root.get("blocks", "unknown")}')
        if root.get('reason'):
            lines.append('  ' + str(root['reason']))
    lines.extend(['', 'Questions (fleet observation; all recorded questions)'])
    if not runner.questions:
        lines.append('No questions recorded in this fleet observation; not proof that none exist.')
    for question in runner.questions:
        lines.extend([f'- {question.id}: {question.effort}; unblocks {question.unblocks}',
                      '  Needs: ' + question.needs])
        if question.answer:
            lines.append('  Answer instructions (not executed): ' + question.answer)
    lines.extend(['', 'Worker observations (quiet is not proof of a dead worker)'])
    for lane in runner.lanes:
        lines.append(f'- {lane.task}: {lane.phase}; {lane.detail}')
        if lane.activity_age is not None:
            lines.append(f'  Last activity: {lane.activity_age}s ago')
        if lane.minutes is not None:
            lines.append('  Attempt duration: ' + fleet_view.duration(lane.minutes))
    lines.extend(['', 'Committed task information (selection rules, not live admission)'])
    store = fleet_view.task_store(runner.repo) if runner.repo else None
    if store is None:
        lines.append('Committed task information unavailable: missing, unreadable or invalid store.')
    else:
        import task_select  # loaded by fleet_view.task_store, same engine as the existing Tasks view
        lines.append('Revision: ' + store.rev)
        opened = sorted((t for t in store.tasks.values() if t.status == 'open'),
                        key=lambda t: (t.section or '', t.rank or 0, t.id))
        if not opened:
            lines.append('No open records at this committed revision.')
        for task in opened:
            blocked = task_select.blocking(store, task)
            reason = (f'{blocked.code}: {blocked.detail}' if blocked else
                      'Eligible for selection; admission is not confirmed.')
            lines.append(f'- {task.id}: {task.title} [{task.section}]')
            lines.append('  ' + reason)
            if not task.runnable:
                lines.append(f'  Not worker-runnable: ownership={task.ownership.value}; kind={task.kind.value}; '
                             f'live={task.live.value}; missing={", ".join(task.missing_fields) or "none"}')
            for label, value in re.findall(r'^- (Question|Owner decision|Held by|Blocker resolution): (.*)$',
                                           task.body or '', re.M):
                lines.append(f'  {label}: {value}')
    lines.extend(['', 'Runtime status (separate observation; may be stale or from older contracts)'])
    try:
        if not runner.state_dir:
            raise ValueError('no state directory recorded')
        status = json.loads(Path(runner.state_dir, 'status.json').read_text())
        if not isinstance(status, dict):
            raise ValueError('expected a status object')
        lines.append('Producer timestamp: ' + str(status.get('updated_at', '(unknown)')))
        if 'merge_backlog' in status:
            backlog = status['merge_backlog']
            if isinstance(backlog, dict):
                lines.append('Recorded integration backlog: ' + '; '.join(
                    f'{key}={backlog.get(key, "(not recorded)")}'
                    for key in ('paused', 'count', 'oldest_seconds')))
                if backlog.get('reason'):
                    lines.append('  ' + str(backlog['reason']))
            else:
                lines.append('Recorded integration backlog unavailable: invalid merge_backlog object.')
        # Legacy producers shorten tasks[*][3], but retain full reasons here.
        # Keep these source observations separate, including roots not in the queue.
        for field, label, identity in [('held', 'Recorded full hold', 'task'),
                                       ('roots', 'Recorded full root', 'id'),
                                       ('task_observations', 'Recorded full task', 'task')]:
            entries = status.get(field, [])
            if not isinstance(entries, list):
                lines.append(f'{label} details unavailable: invalid {field} list.')
                continue
            for entry in entries:
                if not isinstance(entry, dict):
                    lines.append(f'{label} details unavailable: invalid entry.')
                    continue
                detail = '; '.join(str(entry[key]) for key in ('state', 'cause', 'kind') if entry.get(key))
                lines.append(f'- {label} {entry.get(identity, "unknown")}: '
                             + (detail or 'cause not recorded'))
                if entry.get('reason'):
                    lines.append('  ' + str(entry['reason']))
                if 'tasks' in entry:
                    tasks = entry['tasks']
                    lines.append('  Recorded affected IDs: ' + (', '.join(map(str, tasks))
                                 if isinstance(tasks, list) else '(invalid tasks list)'))
        rows = status.get('tasks')
        if not isinstance(rows, list):
            lines.append('Per-task runtime details unavailable from this producer.')
        else:
            for row in rows:
                if isinstance(row, list) and len(row) == 4 and all(isinstance(x, str) for x in row):
                    task, state, cause, why = row
                    lines.append(f'- {task}: {state}; {cause}\n  {why}')
                else:
                    lines.append('A runtime task entry is invalid; its details are unavailable.')
    except (OSError, ValueError, TypeError) as error:
        lines.append('Runtime status unavailable: ' + str(error))
    lines.extend(['', 'This report runs no agent, answers no question and changes no runner or repository.',
                  'Missing data is not evidence of no blockers. No transport or live-health diagnosis is implied.'])
    return _plain('\n'.join(lines)) + '\n'
