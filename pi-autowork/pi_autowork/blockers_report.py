"""Decision-first, read-only report with separately labelled source diagnostics.

No actions or probes. Committed selection and recorded execution remain distinct;
prose warnings never grant or revoke execution authority.
"""
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from pi_autowork import fleet_view
import failure_policy
import task_select
import task_queue

DIAGNOSTICS = '\n\n## Diagnostics\n'


class Report(str):
    """Plain text with an out-of-band summary: source text cannot forge its boundary."""
    def __new__(cls, overview, details):
        capture = super().__new__(cls, overview.rstrip('\n') + DIAGNOSTICS + details)
        capture.overview = overview.rstrip('\n') + '\n'
        return capture


def _plain(value):
    return ''.join(c if c in '\n\t' or (ord(c) >= 32 and ord(c) != 127)
                   else f'\\x{ord(c):02x}' for c in str(value))


def summary(report):
    """The default view and copy payload; diagnostics are an explicit opt-in."""
    if isinstance(report, Report):
        return report.overview
    return report.partition(DIAGNOSTICS)[0].rstrip() + '\n'


def _stamp(value, now):
    try:
        if isinstance(value, bool):
            raise ValueError('not a timestamp')
        observed = datetime.fromtimestamp(float(value), timezone.utc)
        age = (now - observed).total_seconds()
        relative = fleet_view.ago(int(age)) if age >= 0 else 'clock ahead of capture'
        return observed.strftime('%Y-%m-%d %H:%M:%S UTC') + f' ({relative})'
    except (TypeError, ValueError, OverflowError, OSError):
        return 'unknown observation time'


def _notes(task):
    return dict(re.findall(r'^- (Question|Owner decision|Held by|Blocker resolution): (.*)$',
                           task.body or '', re.M)) if task else {}


def _restricted(task):
    # Flag explicit wording for reconciliation, not a new NLP admission policy.
    return bool(re.search(r'\b(?:do not (?:run|execute)|must not (?:run|execute)|no ejecutar)\b',
                          _notes(task).get('Owner decision', ''), re.I))


def _runtime(status, errors):
    """Prefer full rows; compact legacy duplicates must not replace their evidence."""
    rows, alternatives = {}, []
    for field in ('task_observations', 'held', 'tasks'):
        entries = status.get(field, [])
        if not isinstance(entries, list):
            errors.append(f'Runtime details unavailable: invalid {field} list.')
            continue
        for raw in entries:
            if field == 'tasks' and isinstance(raw, list) and len(raw) == 4 and all(isinstance(v, str) for v in raw):
                raw = dict(zip(('task', 'state', 'cause', 'reason'), raw))
            if not isinstance(raw, dict) or not isinstance(raw.get('task'), str):
                errors.append(f'Runtime details unavailable: invalid {field} entry.')
                continue
            row = dict(raw, source=field)
            if field == 'held':
                row.setdefault('state', 'held')
            old = rows.get(row['task'])
            if old is None:
                rows[row['task']] = row
                continue
            reason, previous = str(row.get('reason') or ''), str(old.get('reason') or '')
            prefix = ' '.join(reason.split()).rstrip('…').removesuffix('...').rstrip()
            same = all(not row.get(k) or not old.get(k) or row[k] == old[k] for k in ('state', 'cause'))
            if same and (not reason or previous == reason
                         or (field == 'tasks' and ' '.join(previous.split()).startswith(prefix))):
                continue
            if same and not previous:
                old.update(row)
            else:
                alternatives.append(row)  # contradictory observations remain visible, never silently reconciled
    return list(rows.values()) + alternatives


def _deferred_wait(row, deferred):
    """Use typed dependency evidence, or the exact legacy producer wait format."""
    if row.get('cause') not in (None, '', 'task_wait') or row.get('root_kind') not in (None, '', 'outside'):
        return False
    if 'blocked_by' in row:
        dependencies = row['blocked_by']
        return (isinstance(dependencies, list) and bool(dependencies)
                and all(isinstance(dep, str) and dep in deferred for dep in dependencies))
    reason = ' '.join(str(row.get('reason') or '').split())
    for prefix in ('wait for deferred ', 'dependency: '):
        if reason.startswith(prefix):
            return all(dep.strip() in deferred for dep in reason[len(prefix):].split(','))
    return False


def _deferred_summary(runner, store, deferred, status, now):
    """A small overview only when every open task is deferred or waits on those deferrals."""
    entries = []
    for task in sorted((t for t in store.tasks.values() if t.status == 'open'),
                       key=lambda t: (t.id not in deferred, t.id)):
        if task.id in deferred:
            note = _notes(task).get('Owner decision', '')
            note = re.sub(r'^\d{4}-\d{2}-\d{2}\s*(?:[:—–-]\s*)?', '', note).strip()
            # Quote the recorded condition, not an inferred permission or a generic label.
            excerpt = fleet_view.short(note, 320) if note else 'unblock condition not stated in the owner note'
            entries.append(f'- {task.id}: deferred — {excerpt} (full note: Details).')
            continue
        waiting = {dep for dep in task.depends_on if dep not in store.tasks
                   or store.tasks[dep].status != 'done'
                   or (dep in task.verified_depends_on and not store.tasks[dep].qualified)}
        if not waiting or not waiting <= deferred:
            return None  # unrelated runnable work or another prerequisite needs the general report
        line = f'- {task.id}: waits for ' + ', '.join(sorted(waiting))
        blocked = task_select.blocking(store, task)
        if blocked and blocked.code != 'DEPENDENCY_UNFINISHED':
            line += f'; {blocked.code}: {blocked.detail}'
        entries.append(line + '.')
    backlog = status.get('merge_backlog')
    backlog = (str(backlog.get('count', 'unknown')) + (' (paused)' if backlog.get('paused') else '')
               if isinstance(backlog, dict) else 'unknown')
    lines = [f'{runner.name} — {runner.state}; recorded deferrals; no new questions recorded — READ ONLY', *entries[:5]]
    if len(entries) > 5:
        lines.append(f'- {len(entries) - 5} more deferred/dependent tasks in Details.')
    lines.extend(['Last recorded check: ' + (fleet_view.main_check.line(runner.main_check) or 'unknown')
                  + '; integration backlog: ' + backlog + '.',
                  'Runtime observed: ' + _stamp(status.get('updated_at'), now) + '; fleet source age in Details.',
                  'Service: ' + (runner.service or 'not observed')
                  + '; no worker lane details supplied (not proof of inactivity).',
                  'Details: full reasons/sources. Preserve deferrals; selection is not live admission.'])
    return _plain('\n'.join(lines))


def build(runner):
    """Read one frozen report off the UI thread. Summary first; diagnostics on demand."""
    now = datetime.now(timezone.utc)
    snapshot = getattr(runner, 'snapshot', None)
    errors = [*getattr(runner, 'acquisition_errors', ()), *(snapshot.errors if snapshot else ())]
    store = fleet_view.task_store(runner.repo) if runner.repo else None
    if store is None:
        errors.append('Committed task information unavailable: missing, unreadable or invalid store.')
    try:
        if not runner.state_dir:
            raise ValueError('no state directory recorded')
        status = json.loads(Path(runner.state_dir, 'status.json').read_text())
        if not isinstance(status, dict):
            raise ValueError('expected a status object')
    except (OSError, ValueError, TypeError) as error:
        status = {}
        errors.append('Runtime status unavailable: ' + str(error))
    rows = _runtime(status, errors)
    if not any(field in status for field in ('task_observations', 'held', 'tasks')):
        errors.append('Per-task runtime details unavailable from this producer.')
    roots = status.get('roots', [])
    if not isinstance(roots, list) or any(not isinstance(root, dict) for root in roots):
        errors.append('Recorded root details unavailable: invalid roots list or entry.')
        roots = [r for r in roots if isinstance(r, dict)] if isinstance(roots, list) else []
    opened = {t.id: t for t in store.tasks.values() if t.status == 'open'} if store else {}
    deferred = task_queue.deferred(store) if store else set()
    groups = {}
    for question in runner.questions:
        target = re.search(r'\bTask: \[[^\]]+\]\(tasks/items/([A-Za-z0-9._-]+)\.md\)', question.needs)
        task_id = target[1] if target and target[1] in opened else question.id
        groups.setdefault(task_id, []).append(question)
    for task in opened.values():
        if task.id not in deferred and (task.section == 'Needs decision' or _restricted(task)):
            groups.setdefault(task.id, [])
    technical = any(failure_policy.disposition(dict(cause=cause))['resolution_owner'] != failure_policy.OWNER
                    for _, cause in runner.held)
    technical |= any(r.get('state') == 'held' and failure_policy.disposition(r)['resolution_owner'] != failure_policy.OWNER
                     for r in rows)
    technical |= any(failure_policy.disposition(root)['resolution_owner'] != failure_policy.OWNER
                     for root in [*roots, *runner.roots])
    interrupted = bool(runner.stop_reason or runner.blocker or runner.gate
                       or runner.main_check.get('state') in ('red', 'broken'))
    headline = ('Awaiting owner decisions' if set(groups) - deferred and runner.state in ('blocked', 'stalled')
                and not technical and not interrupted and not errors else 'Recorded state: ' + runner.state)
    lines = [f'{runner.name} — {headline} — READ ONLY',
             'Captured: ' + now.strftime('%Y-%m-%d %H:%M:%S UTC'),
             'Runner: ' + runner.name, 'Repository: ' + (runner.repo or '(unknown)'),
             'Service: ' + (runner.service or 'not observed')]
    if runner.minutes is not None:
        lines.append(f'Recorded {runner.state}-state duration: ' + fleet_view.duration(runner.minutes))
    if snapshot is not None:
        lines.append(f'Fleet observation: {snapshot.freshness}; ' + _stamp(snapshot.captured_at, now))
    else:
        lines.append('Fleet observation: age unknown; may be stale.')
    check = fleet_view.main_check.line(runner.main_check)
    if check:
        lines.append('Last recorded main check: ' + check)
    backlog = status.get('merge_backlog')
    if isinstance(backlog, dict):
        lines.append(f'Integration backlog: {backlog.get("count", "unknown")} recorded; '
                     + ('paused; ' if backlog.get('paused') else '') + _stamp(status.get('updated_at'), now))
    else:
        lines.append('Integration backlog: not recorded.')
    for label, value in [('Startup refusal', runner.stop_reason), ('Dispatch blocker', runner.blocker),
                         ('Resource gate', runner.gate)]:
        if value:
            lines.append(f'{label}: {value}')
    for error in dict.fromkeys(errors):
        lines.append('Source warning: ' + str(error))
    recorded_activity = bool(runner.running or status.get('active_workers') or status.get('in_flight')
                             or runner.job or runner.restarting)
    if runner.running:
        lines.append(f'Recorded worker count (fleet): {runner.running}; not a health/admission check.')
    if 'active_workers' in status:
        lines.append(f'Recorded worker count (runtime): {status["active_workers"]}; not a health/admission check.')
    if status.get('in_flight'):
        lines.append(f'Recorded in-flight count (runtime): {status["in_flight"]}')
    if runner.job:
        lines.append('Recorded coordinator job: ' + str(runner.job.get('role', 'unknown')))
    if not runner.lanes:
        lines.append('No worker lane details supplied; counts do not prove worker health.'
                     if recorded_activity or 'active_workers' in status
                     else 'No worker observations supplied; this does not prove no active workers.')
    else:
        for lane in runner.lanes:
            lines.append(f'Worker {lane.task}: {lane.phase}; {lane.detail}')
            if lane.activity_age is not None:
                lines.append('  Last activity: ' + fleet_view.ago(lane.activity_age) + '; quiet is not proof of death.')
    shown, linked = {}, []

    def reason(text, prefix='  Needs: '):
        text = str(text or '').strip()
        if not text:
            return
        if text in shown:
            lines.append(prefix + f'Same text as [{shown[text]}] above.')
        else:
            key = shown[text] = f'E{len(shown) + 1}'
            lines.append(prefix + f'[{key}] ' + text)

    if deferred:
        lines.extend(['', 'Recorded owner deferrals (already answered; not new questions)'])
        for task_id in sorted(deferred):
            lines.append('- ' + task_id + ': preserve the existing deferral and its dependency/qualification gate.')
            reason(_notes(opened[task_id]).get('Owner decision'), '  Committed owner decision: ')
    lines.extend(['', 'Decisions and required inputs (recorded, not new authorization)'])
    if not groups:
        lines.append('No owner questions recorded; missing data is not evidence of no blockers.')
    for number, (task_id, questions) in enumerate(groups.items(), 1):
        task = opened.get(task_id)
        notes = _notes(task)
        lines.append(f'{number}. {task_id}' + (f' — {task.title}' if task else ''))
        origins = [q.id for q in questions if q.id != task_id]
        if origins:
            lines.append('  Raised by: ' + ', '.join(dict.fromkeys(origins)))
        observations = [('fleet', {'cause': cause}) for tid, cause in runner.held if tid == task_id]
        observations += [('runtime', row) for row in rows if row['task'] == task_id and row.get('state') == 'held']
        if observations:
            lines.append('  Recorded holds: ' + '; '.join(dict.fromkeys(
                f'{source}: {row.get("cause") or "unknown"}' for source, row in observations)))
        if notes.get('Question'):
            reason(notes['Question'], '  Committed question: ')
        for question in questions:
            if origins and notes.get('Question') and question.id in origins:
                linked.append((task_id, question))
                lines.append(f'  Source planning question: Details ({question.id}); reconcile with the committed question.')
                continue  # primary decision here; distinct planning requirements remain in diagnostics
            need = question.needs
            full = next((r for r in rows if r['task'] == task_id and r.get('reason')
                         and str(r['reason']).startswith(need.rstrip('…').removesuffix('...').rstrip())), None)
            if full:
                reason(full['reason'], '  Recorded need (runtime; ' + _stamp(status.get('updated_at'), now) + '): ')
            else:
                reason(need, '  Recorded question: ')
                if need.endswith(('…', '...')):
                    lines.append('  Source question is truncated; no matching full runtime reason was found.')
        for source, row in observations:
            if source == 'runtime':
                reason(row.get('reason'), '  Recorded runtime reason: ')
        if notes.get('Owner decision'):
            reason(notes['Owner decision'], '  Committed owner decision: ')
        if task and task.runnable and not task_select.blocking(store, task) and _restricted(task):
            lines.append('  WARNING: selectable metadata conflicts with an execution restriction in the owner note.')
            lines.append('  Next: reconcile section/ownership with the current owner decision using autowork tasks; '
                         'do not grant authority or restart merely to clear this warning.')
        elif task_id in deferred:
            lines.append('  Next: preserve the committed deferral; reconcile this recorded question '
                         'without inventing new approval or waiving its gate.')
        elif any(failure_policy.disposition(row)['resolution_owner'] != failure_policy.OWNER
                 for _, row in observations):
            lines.append('  Next: reconcile the technical hold and recorded question; '
                         'the question does not establish owner-only blocking. Preserve authorization and checks.')
        else:
            lines.append('  Next: record the answer/input evidence in '
                         + (task.path if task else 'the source task record')
                         + '; preserve the hold, authorization, acceptance and checks until resolved.')
        if questions:
            lines.append('  Reported unblock count: ' + ', '.join(str(q.unblocks) for q in questions)
                         + ' (producer estimate, not verified downstream readiness).')
    held = list(dict.fromkeys([*runner.held, *((r['task'], r.get('cause', '')) for r in rows
                                               if r.get('state') == 'held')]))
    other_holds = [(task, cause) for task, cause in held if task not in groups]
    if other_holds:
        lines.extend(['', 'Other recorded holds'])
        for task, cause in other_holds:
            lines.append(f'- {task}: {cause or "cause not recorded"}')
            for row in rows:
                if row['task'] == task:
                    reason(row.get('reason'), '  Recorded runtime reason: ')
    for row in rows:
        if row.get('state') == 'waiting' and not _deferred_wait(row, deferred):
            lines.append(f'- {row["task"]}: recorded runtime wait; {row.get("cause") or "cause not recorded"}')
            reason(row.get('reason'), '  Runtime wait: ')
    lines.extend(['', 'Diagnostics are available separately. Observations may be stale; selection is not live admission.',
                  'This report runs no agent, answers no question and changes no runner or repository.'])
    overview = _plain('\n'.join(lines))
    lines = ['Fleet observation (last refresh; may be stale)']
    if runner.prepare_state:
        lines.append('Preparation state: ' + runner.prepare_state)
    if runner.restarting:
        lines.append('Restart: ' + str(runner.restarting))
    if snapshot is not None:
        lines.append(f'Inventory revision: {snapshot.revision}; execution {snapshot.engine_freshness}')
    for error in dict.fromkeys(errors):
        lines.append('Fleet acquisition error / source warning: ' + str(error))
    if runner.main_check:
        lines.append('Main-check evidence: ' + json.dumps(runner.main_check, ensure_ascii=False))
    for task_id, question in linked:
        reason(question.needs, f'Planning evidence (fleet) {question.id} → {task_id}: ')
    for group in [*runner.stopped_groups, *runner.waiting_groups]:
        tasks = group.get('tasks') or []
        lines.append(f'- {group.get("label", "reason not recorded")}: ' + ', '.join(map(str, tasks)))
        if group.get('count', len(tasks)) > len(tasks):
            lines.append(f'  {group["count"]} reported; only {len(tasks)} IDs recorded by this producer.')
    for root in runner.roots:
        lines.append(f'- Fleet root {root.get("id", "unknown")}: {root.get("kind", "unknown")}; '
                     f'blocks {root.get("blocks", "unknown")}')
        reason(root.get('reason'), '  Fleet reason: ')
    lines.extend(['', 'Committed task information (selection rules, not live admission)'])
    if store is not None:
        lines.append('Revision: ' + store.rev)
        if not opened:
            lines.append('No open records at this committed revision.')
        for task in sorted(opened.values(), key=lambda t: (t.section or '', t.rank or 0, t.id)):
            blocked = task_select.blocking(store, task)
            selection = f'{blocked.code}: {blocked.detail}' if blocked else 'Eligible for selection; admission is not confirmed.'
            lines.extend([f'- {task.id}: {task.title} [{task.section}]', '  ' + selection])
            if not task.runnable:
                lines.append(f'  Not worker-runnable: ownership={task.ownership.value}; kind={task.kind.value}; '
                             f'live={task.live.value}; missing={", ".join(task.missing_fields) or "none"}')
            for label, value in _notes(task).items():
                reason(value, f'  {label}: ')
    lines.extend(['', 'Runtime status (separate observation; may be stale or from older contracts)',
                  'Observed: ' + _stamp(status.get('updated_at'), now)])
    if isinstance(backlog, dict):
        lines.append('Recorded integration backlog: ' + '; '.join(
            f'{key}={backlog.get(key, "(not recorded)")}' for key in ('paused', 'count', 'oldest_seconds')))
        reason(backlog.get('reason'), '  ')
    elif 'merge_backlog' in status:
        lines.append('Recorded integration backlog unavailable: invalid merge_backlog object.')
    closed = {r['task'] for r in rows if r.get('state') in ('closed', 'done', 'superseded')}
    if closed:
        lines.append(f'Closed history omitted: {len(closed)} task(s); see Tasks → Closed.')
    for row in [*rows, *roots]:
        if not isinstance(row, dict):
            lines.append('Invalid runtime root entry; details unavailable.')
            continue
        if row.get('state') in ('closed', 'done', 'superseded'):
            continue
        task = row.get('task') or row.get('id', 'unknown')
        lines.append(f'- {task}: ' + '; '.join(str(row[k]) for k in ('state', 'cause', 'kind') if row.get(k))
                     + f' [source: {row.get("source", "roots")}]')
        reason(row.get('reason'), '  Runtime reason: ')
        if 'tasks' in row:
            tasks = row['tasks']
            lines.append('  Recorded affected IDs: ' + (', '.join(map(str, tasks))
                         if isinstance(tasks, list) else '(invalid tasks list)'))
    lines.append('Missing data is not evidence of no blockers. No transport or live-health diagnosis is implied.')
    details = _plain('\n'.join(lines)) + '\n'
    only_waits = all(row.get('state') in ('closed', 'done', 'superseded')
                     or (row.get('state') == 'waiting' and row['task'] in opened
                         and _deferred_wait(row, deferred)) for row in rows)
    only_deferred_roots = all(root.get('id') in deferred for root in [*roots, *runner.roots])
    backlog_busy = isinstance(backlog, dict) and (backlog.get('count') or backlog.get('paused'))
    if (deferred and not groups and not technical and not interrupted and not errors
            and not recorded_activity and not runner.lanes and not runner.held
            and not backlog_busy and only_waits and only_deferred_roots):
        brief = _deferred_summary(runner, store, deferred, status, now)
        if brief:
            return Report(brief, overview + '\n\n' + details)
    return Report(overview, details)
