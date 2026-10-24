"""`autowork scorecard`: what each runner delivered and what it cost, over a window of days.

Read from each repository's engine journal and Git history, without a model call:

- closed: tasks whose record became done in the window, however they were closed (the
  engine, the maintainer or a person);
- held: the share of integrations (a slot leaving `integrating`) that ended `held`
  rather than `integrated`, the rework a failed review or check costs;
- start to merge: the median time from a task's first dispatch to its integration;
- questions: distinct owner questions (`### Q-…`) added to BLOCKERS.md in the window.
"""
import csv
import io
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import tomllib

from . import accounting

JOURNAL = Path('autowork-execution') / 'journal.jsonl'


def common_dir(repo):
    try:
        out = subprocess.run(['git', '-C', str(repo), 'rev-parse', '--path-format=absolute', '--git-common-dir'],
                             capture_output=True, text=True, timeout=30).stdout.strip()
    except (OSError, subprocess.TimeoutExpired):
        return None
    return Path(out) if out else None


def journal_events(common, since):
    """slot_changed events at or after `since` (epoch seconds), oldest first."""
    from pi_autowork.engine import execution_journal
    try:
        events = execution_journal.read(common / 'autowork-execution', ordered=False)['events']
    except (OSError, ValueError):
        return []
    return sorted((e for e in events if e['event'] == 'slot_changed' and e['timestamp'] >= since),
                  key=lambda e: e['timestamp'])


def git_text(repo, *argv):
    try:
        return subprocess.run(['git', '-C', str(repo), *argv], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def done(repo, rev):
    """IDs of the done tasks in the store at ``rev``, or None when it has no readable store."""
    from pi_autowork.engine.task_store import StoreError, TaskStore
    try:
        return {t.id for t in TaskStore.at(repo, rev).tasks.values() if t.status == 'done'}
    except StoreError:
        return None


def closure_history(repo, days, now):
    """Latest close transition per currently done task, on the reachable first-parent history.

    Reopen/reclose counts once, in its latest period. The first readable store is
    the conversion baseline, not a batch of new completions.
    """
    since = now - days * 86400
    # Git commit times are whole seconds; --before itself is inclusive.
    before = math.ceil(since) - 1
    start = git_text(repo, 'rev-list', '--first-parent', '-1', f'--before=@{before}', 'HEAD').strip()
    previous = done(repo, start) if start else None
    history = git_text(repo, 'log', '--reverse', '--first-parent', '--format=%H %ct',
                       f'{start}..HEAD' if start else 'HEAD', '--', 'tasks')
    result = {}
    for line in history.splitlines():
        revision, stamp = line.split()
        current = done(repo, revision)
        if current is None:
            continue
        if previous is not None and since <= int(stamp) <= now:
            result.update({task: int(stamp) for task in current - previous})
        previous = current
    current = done(repo, 'HEAD') or set()
    return {task: stamp for task, stamp in result.items() if task in current}


def closed(repo, days):
    return set(closure_history(repo, days, time.time()))


def owner_questions(repo, days):
    """Distinct question headings added to BLOCKERS.md in the last `days` days."""
    try:
        log = subprocess.run(['git', '-C', str(repo), 'log', f'--since={days} days ago', '-p', '--format=',
                              '--', 'BLOCKERS.md'], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return len(set(re.findall(r'(?m)^\+### (Q-\S+)', log)))


def regression_history(repo, *, patches=False):
    """Reachable commits, parents before children; NULs separate messages from diffs."""
    args = ['log', '--no-color', '--reverse', '--topo-order', '--full-history', '--format=%x00%H%x00%ct%x00%B%x00']
    if patches:
        args += ['-p', '--unified=0', '--no-renames', '--no-ext-diff', '--no-textconv',
                 '--src-prefix=a/', '--dst-prefix=b/', '--diff-merges=first-parent', '--', 'tasks/items/']
    fields = git_text(repo, *args).split('\0')
    return [(fields[i].strip(), int(fields[i + 1]), fields[i + 2], fields[i + 3])
            for i in range(1, len(fields) - 3, 4)]


def regressions(repo, since, now):
    """Explicit receipt-linked discoveries in the window, plus malformed note diagnostics.

    Delivery is the receipt's integration commit, not its candidate or closure commit.
    Reverts carry unknown severity/finder (None), never inferred from Git authorship.
    Note discovery is its first committed occurrence, even if later edited or removed.
    """
    from pi_autowork.engine.task_store import StoreError, TaskStore
    try:
        current = TaskStore.at(repo, 'HEAD')
    except StoreError:
        return [], []
    history = regression_history(repo)
    times = {sha: timestamp for sha, timestamp, _, _ in history}
    deliveries = {}
    for task in current.tasks:
        text = git_text(repo, 'show', f'{current.rev}:tasks/evidence/{task}.toml')
        try:
            receipt = tomllib.loads(text)
        except ValueError:
            continue
        commit = receipt.get('integration')
        if (receipt.get('schema') == 1 and receipt.get('task') == task
                and isinstance(commit, str) and commit in times):
            deliveries[task] = commit
    records, incomplete, seen, noted = [], [], set(), set()
    ancestors = {}

    def add(task, delivered, discovery, timestamp, source, severity=None, finder=None, source_task=None):
        if not since <= timestamp <= now or timestamp < times[delivered] or delivered == discovery:
            return
        pair = (delivered, discovery)
        if pair not in ancestors:
            try:
                ancestors[pair] = subprocess.run(
                    ['git', '-C', str(repo), 'merge-base', '--is-ancestor', delivered, discovery],
                    capture_output=True, timeout=30).returncode == 0
            except (OSError, subprocess.TimeoutExpired):
                ancestors[pair] = False
        if not ancestors[pair]:
            return
        records.append({'task': task, 'delivered_commit': delivered, 'discovery_commit': discovery,
                        'delivered_at': times[delivered], 'discovered_at': timestamp,
                        'time_to_discovery_seconds': timestamp - times[delivered],
                        'severity': severity, 'found_by': finder,
                        'found_by_owner': finder == 'owner' if finder else None,
                        'source': source, 'source_task': source_task})

    for sha, timestamp, message, _ in history:
        for delivered in set(re.findall(r'(?m)^This reverts commit ([0-9a-f]{40}(?:[0-9a-f]{24})?)(?:[.,]|$)', message)):
            for task, integration in deliveries.items():
                if integration == delivered:
                    add(task, delivered, sha, timestamp, 'revert')

    note_pattern = re.compile(r'- Regression of: ([A-Za-z0-9][A-Za-z0-9_-]*); commit ([0-9a-f]{40}(?:[0-9a-f]{24})?); '
                              r'severity (low|medium|high); found by (owner|check)')
    for sha, timestamp, _, patch in regression_history(repo, patches=True):
        path, snapshot = None, None
        for line in patch.splitlines():
            if line.startswith('+++ '):
                match = re.fullmatch(r'\+\+\+ b/tasks/items/([A-Za-z0-9][A-Za-z0-9_-]*)\.md', line)
                path = match[1] if match else None
            if not path or not line.startswith('+- Regression of:'):
                continue
            note = line[1:]
            key = (path, note)
            if key in seen:
                continue
            seen.add(key)
            # Confirm this is a body note in a real task, not frontmatter or another file.
            if snapshot is None:
                try:
                    snapshot = TaskStore.at(repo, sha)
                except StoreError:
                    break
            source_task = snapshot.tasks.get(path)
            if source_task is None or note not in source_task.body.splitlines():
                continue
            match = note_pattern.fullmatch(note)
            if match is None:
                if since <= timestamp <= now:
                    incomplete.append({'task': path, 'discovery_commit': sha, 'note': note,
                                       'reason': 'malformed Regression of note'})
                continue
            task, delivered, severity, finder = match.groups()
            if task == path or task not in snapshot.tasks or deliveries.get(task) != delivered:
                continue
            link = (path, task, delivered)
            if link in noted:
                continue
            noted.add(link)
            add(task, delivered, sha, timestamp, 'note', severity, finder, path)
    # A note can describe the same discovery as its commit's revert message; prefer
    # that explicit severity/finder over a second, metadata-free revert record.
    note_discoveries = {(r['task'], r['delivered_commit'], r['discovery_commit'])
                        for r in records if r['source'] == 'note'}
    records = [r for r in records if r['source'] != 'revert'
               or (r['task'], r['delivered_commit'], r['discovery_commit']) not in note_discoveries]
    return sorted(records, key=lambda r: (r['discovered_at'], r['discovery_commit'], r['task'],
                                          r['source'], r['source_task'] or '')), incomplete


def measure(repo, days, now=None):
    """Legacy runner counters and accounting; evaluation exports use :func:`report`."""
    return _collect(repo, days, time.time() if now is None else now)[0]


def _collect(repo, days, now):
    since = now - days * 86400
    common = common_dir(repo)
    retained_events = journal_events(common, -math.inf) if common else []
    events = [e for e in retained_events if e['timestamp'] >= since]
    integrated, held, first_start, merge_minutes = 0, 0, {}, []
    for event in events:
        task, state, previous = event.get('task_id'), event.get('state'), event.get('previous_state')
        if not task:
            continue
        if state == 'dispatched':
            first_start.setdefault(task, event['timestamp'])
        if previous == 'integrating' and state == 'integrated':
            integrated += 1
            if task in first_start:
                merge_minutes.append((event['timestamp'] - first_start.pop(task)) / 60)
        elif previous == 'integrating' and state == 'held':
            held += 1
    attempts = integrated + held
    attributed, incomplete = regressions(repo, since, now)
    closings = closure_history(repo, days, now)
    completed = set(closings)
    from pi_autowork.engine.task_store import StoreError, TaskStore
    try:
        snapshot = TaskStore.at(repo, 'HEAD')
        verified_ids = {tid for tid in completed if snapshot.tasks[tid].verified}
        verified = len(verified_ids)
        unverified = sum(snapshot.tasks[tid].closure == 'coordinator_verified' and not snapshot.tasks[tid].verified
                         for tid in completed)
    except StoreError:
        snapshot = None
        verified_ids = set()
        verified, unverified = 0, 0
    from pi_autowork.engine import execution_journal
    try:
        lifecycle = execution_journal.lifecycle_events(common / 'autowork-execution')['events'] if common else []
    except (OSError, ValueError):
        lifecycle = []
    usage = accounting.measure(repo, since, now, tasks=snapshot.tasks if snapshot else (),
                               verified=verified_ids, lifecycle=lifecycle)
    row = {'repo': str(repo), 'closed': len(completed), 'verified_closed': verified,
            'manual_closed': len(completed) - verified - unverified,
            'unverified_closed': unverified, 'integrations': attempts,
            'held_share': round(held / attempts, 2) if attempts else None,
            'start_to_merge_minutes': round(statistics.median(merge_minutes)) if merge_minutes else None,
            'questions': owner_questions(repo, days),
            'regressions': attributed, 'regressions_incomplete': incomplete, 'usage': usage}
    return row, dict(repo=repo, tasks=snapshot.tasks if snapshot else {}, closings=closings,
                     lifecycle=lifecycle, slot_events=retained_events, regressions=attributed)


BASELINE_METRICS = ('cost_per_verified_task_usd', 'owner_minutes_per_verified_task')
DAY = 86400


def metric(value, unit, status='measured'):
    return dict(value=value, status=status if value is not None else 'missing', unit=unit)


def load_baseline(path):
    """An owner's explicit estimates, never pricing inferred from token counts."""
    try:
        values = json.loads(Path(path).read_text())
        if not isinstance(values, dict) or any(accounting.number(values.get(k)) is None for k in BASELINE_METRICS):
            raise ValueError('expected nonnegative finite numbers: ' + ', '.join(BASELINE_METRICS))
        return {k: values[k] for k in BASELINE_METRICS}
    except (OSError, ValueError) as exc:
        raise ValueError(f'baseline {path}: {exc}') from exc


def completion_times(data, now):
    """Prefer a close observation only when it belongs to the latest Git close."""
    stamps = dict(data['closings'])
    observed = set()
    for fact in sorted(data['lifecycle'], key=lambda f: f['timestamp']):
        task, stamp = fact['task_id'], fact['timestamp']
        if (fact['event'] == 'closed' and task in stamps and task not in observed
                and stamps[task] <= stamp <= now):
            stamps[task] = stamp
            observed.add(task)
    return {task: (stamp, 'verified' if data['tasks'][task].verified else
                   'unverified' if data['tasks'][task].closure == 'coordinator_verified' else 'manual')
            for task, stamp in stamps.items() if task in data['tasks']}


def observations(data, now):
    """Retain samples/denominators until pooling; never average runner medians or rates."""
    facts = sorted((f for f in data['lifecycle'] if f['timestamp'] <= now), key=lambda f: f['timestamp'])
    by_task, recoveries, pending = {}, [], {}
    for fact in facts:
        task, kind = fact['task_id'], fact['event']
        by_task.setdefault(task, []).append(fact)
        key = task, fact.get('attempt_id')
        if kind in ('restart', 'interrupted'):
            pending[key] = len(recoveries)
            recoveries.append(dict(timestamp=fact['timestamp'], success=False))
        elif kind in ('worker_adopted', 'resumed') and key in pending:
            recoveries[pending.pop(key)]['success'] = True
    diagnostics = dict(invalid_records=0, invalid_attention_records=0, duplicate_attention=0)
    attention = list(accounting.records(accounting.state_dir(data['repo']) / 'attention.jsonl',
                                        0, now, diagnostics, 'event_id'))
    attention_valid = not diagnostics['invalid_attention_records'] and all(
        accounting.number(r.get('minutes')) is not None for r in attention)
    return dict(data, completions=completion_times(data, now), by_task=by_task, recoveries=recoveries,
                attention=attention, attention_valid=attention_valid,
                phase_endpoints=phase_endpoints(data, now))


def phase_endpoints(data, now):
    """First retained endpoints only; never manufacture an attempt for a legacy slot."""
    tasks, attempts, closed = {}, {}, {}
    facts = [(f['task_id'], f.get('attempt_id'), f['event'], f['timestamp'], f.get('scope'))
             for f in data['lifecycle']]
    facts.extend((e.get('task_id'), (e.get('slot') or {}).get('attempt_id'), e.get('state'),
                  e['timestamp'], 'attempt') for e in data['slot_events'])
    for task, attempt, kind, stamp, scope in facts:
        if not task or stamp > now:
            continue
        endpoints = tasks.setdefault(task, {})
        endpoints[kind] = min(endpoints.get(kind, stamp), stamp)
        if kind == 'closed':
            closed[task] = max(closed.get(task, -math.inf), stamp)
        if (not attempt or attempt in ('unknown', 'unassigned')
                or (scope == 'task' and kind != 'closed')):
            continue
        endpoints = attempts.setdefault((task, attempt), {})
        endpoints[kind] = min(endpoints.get(kind, stamp), stamp)
    # Attempt IDs are opaque. A later attempt means a later first observation,
    # not lexicographic ID order, a hold or a guessed terminal outcome.
    earliest, latest = {}, {}
    for (task, _), endpoints in attempts.items():
        stamp = min(endpoints.values())
        earliest[task] = min(earliest.get(task, math.inf), stamp)
        latest[task] = max(latest.get(task, -math.inf), stamp)
    # Terminal evidence dates classification only, never a latency endpoint.
    terminal = {key: max(closed.get(key[0], -math.inf),
                         latest[key[0]] if min(endpoints.values()) < latest[key[0]] else -math.inf)
                for key, endpoints in attempts.items()}
    task_terminal = {task: max(closed.get(task, -math.inf),
                              latest[task] if earliest.get(task, math.inf) < latest.get(task, -math.inf) else -math.inf)
                     for task in tasks}
    return dict(tasks=tasks, attempts=attempts, terminal=terminal, task_terminal=task_terminal)


PHASES = (
    ('task_accepted_to_dispatched', 'task_id', 'accepted', 'dispatched'),
    ('task_dispatched_to_integrated', 'task_id', 'dispatched', 'integrated'),
    ('attempt_running_to_reported', 'task_id+attempt_id', 'running', 'reported'),
    ('attempt_reported_to_integrating', 'task_id+attempt_id', 'reported', 'integrating'),
    ('attempt_integrating_to_integrated', 'task_id+attempt_id', 'integrating', 'integrated'),
    ('attempt_integrated_to_closed', 'task_id+attempt_id', 'integrated', 'closed'),
    ('all_attempt_exposure', 'task_id+attempt_id', 'running', 'reported'),
)
PHASE_RULES = (
    'All retained lifecycle and slot-state endpoints through cutoff; first timestamp of each kind per identity. '
    'Classify missing start first; ordered pairs are observed, reversed first pairs excluded even if a later end exists. '
    'Start without end is missing_end_terminal only with a later attempt (by first observation) or observed closed state '
    'at/after the phase start; '
    'otherwise right_censored, including held/interrupted states. '
    'No inferred endpoints or attempt IDs; unknown/unassigned IDs excluded from attempt rows. '
    'Median and nearest-rank p95 use observed pairs only; empty distributions are missing.'
)


def phase_diagnostics(sources, since, now):
    """Pool observed subsets and coverage independently of strict whole-cohort metrics."""
    result = {}
    for name, identity, first, last in PHASES:
        exposure = name == 'all_attempt_exposure'
        task_phase = identity == 'task_id'
        counts = dict(eligible=0, observed_pairs=0, missing_start=0, missing_end_terminal=0,
                      right_censored=0, reversed=0)
        left_excluded, samples = 0, []
        for data in sources:
            verified = {t for t, (stamp, kind) in data['completions'].items()
                        if kind == 'verified' and since <= stamp <= now}
            endpoints = data['phase_endpoints']
            rows = ({t: endpoints['tasks'].get(t, {}) for t in verified} if task_phase else
                    {key: stamps for key, stamps in endpoints['attempts'].items()
                     if exposure or key[0] in verified})
            for key, stamps in rows.items():
                a, b = stamps.get(first), stamps.get(last)
                if exposure and a is not None and a < since:
                    left_excluded += 1
                    continue
                # Exposure selects known in-window starts. Missing starts are
                # disclosed separately, outside that cohort's eligible count.
                counts['eligible'] += not exposure or a is not None
                if a is None:
                    counts['missing_start'] += 1
                elif b is None:
                    terminal = endpoints['task_terminal' if task_phase else 'terminal'].get(key, -math.inf) >= a
                    counts['missing_end_terminal' if terminal else 'right_censored'] += 1
                elif b < a:
                    counts['reversed'] += 1
                else:
                    counts['observed_pairs'] += 1
                    samples.append((b - a) / 60)
        unit = 'tasks' if task_phase else 'attempts'
        metrics = {key: metric(value, unit) for key, value in counts.items()}
        metrics.update(median_minutes=metric(statistics.median(samples) if samples else None, 'minutes'),
                       p95_minutes=metric(sorted(samples)[math.ceil(.95 * len(samples)) - 1]
                                          if samples else None, 'minutes'))
        cohort = ('Tasks with latest receipt-valid verified close in [window_start, cutoff]; starts may predate window. '
                  + ('Retries collapsed.' if task_phase else 'Distinct attempts retained, including failed/retry attempts.'))
        rules = PHASE_RULES
        if exposure:
            cohort = 'Attempts with first running in [window_start, cutoff], across all outcomes.'
            rules += (' First reported must also be in that window; no clipping or extrapolation. '
                      'missing_start and left_excluded are outside eligible; starts before window are left_excluded. '
                      'Observed completed attempt-span hours may overlap or include suspension: never runner uptime or delivery throughput.')
            metrics.update(left_excluded=metric(left_excluded, 'attempts'),
                           observed_completed_attempt_span_hours=metric(sum(samples) / 60 if samples else None, 'hours'))
        else:
            rules += ' eligible = observed_pairs + missing_start + missing_end_terminal + right_censored + reversed.'
        result[name] = dict(cohort=cohort, identity=identity, rules=rules, metrics=metrics)
    return result


def period_metrics(sources, start, end, *, final=False):
    def inside(stamp):
        return start <= stamp and (stamp <= end if final else stamp < end)

    count, manual, interventions, unattended = 0, 0, 0, 0
    attended_known = True
    durations = {'accepted_to_delivered': [], 'dispatch_to_integrated': []}
    costs, minutes, recoveries, regressed = [], [], [], 0
    for data in sources:
        completions = {t: kind for t, (stamp, kind) in data['completions'].items() if inside(stamp)}
        verified = {t for t, kind in completions.items() if kind == 'verified'}
        manual_ids = {t for t, kind in completions.items() if kind == 'manual'}
        count += len(verified)
        manual += len(manual_ids)
        # A hand close is one intervention even if old Git history has no telemetry.
        interventions += len(manual_ids)
        interventions += sum(inside(f['timestamp']) and f['event'] in accounting.INTERVENTIONS
                             and not (f['event'] == 'hand_closed' and f['task_id'] in manual_ids)
                             for f in data['lifecycle'])
        # accounting uses inclusive bounds; exclude the right edge from nonfinal weeks.
        until = end if final else math.nextafter(end, -math.inf)
        usage = accounting.measure(data['repo'], start, until, tasks=data['tasks'], verified=verified,
                                   lifecycle=data['lifecycle'])
        costs.append(usage['cost_usd'])
        attention_complete = (usage['owner_minutes'] is not None
                              and not usage['diagnostics']['invalid_attention_records']
                              and all(usage['tasks'][t]['owner_minutes'] is not None for t in verified))
        minutes.append(usage['owner_minutes'] if attention_complete else None)
        for task in verified:
            facts = data['by_task'].get(task, [])
            stamps = {}
            for f in facts:
                stamps.setdefault(f['event'], f['timestamp'])
            closed_at = data['completions'][task][0]
            # No lifecycle coverage is unknown, not evidence of unattended execution.
            covered = all(k in stamps for k in ('accepted', 'dispatched', 'closed'))
            attention = [r for r in data['attention']
                         if stamps.get('accepted', 0) <= accounting.timestamp(r['time']) <= closed_at
                         and (accounting.number(r.get('minutes')) or 0) > 0]
            attended_known &= covered and data['attention_valid'] and not any(not r.get('task') for r in attention)
            unattended += (covered and not any(r.get('task') == task for r in attention)
                           and not any(f['event'] in accounting.INTERVENTIONS
                                       and f['timestamp'] <= closed_at for f in facts))
            for prefix, first, last in [('accepted_to_delivered', 'accepted', 'delivered'),
                                        ('dispatch_to_integrated', 'dispatched', 'integrated')]:
                a, b = stamps.get(first), stamps.get(last)
                durations[prefix].append((b - a) / 60 if a is not None and b is not None and b >= a else None)
        recoveries.extend(r for r in data['recoveries'] if inside(r['timestamp']))
        regressed += len({r['task'] for r in data['regressions'] if r['task'] in verified})
    result = dict(verified_tasks=metric(count, 'tasks'), manual_closed=metric(manual, 'tasks'),
                  owner_interventions=metric(interventions, 'interventions'),
                  verified_tasks_per_day=metric(count / ((end - start) / DAY) if count else None, 'tasks/day'),
                  unattended_completion_percentage=metric(100 * unattended / count
                                                          if count and attended_known else None, 'percent'))
    for name, samples in durations.items():
        complete = samples and all(s is not None for s in samples)
        result[name + '_median_minutes'] = metric(statistics.median(samples) if complete else None, 'minutes')
        # Nearest rank: well defined for tiny cohorts without extrapolating beyond observations.
        result[name + '_p95_minutes'] = metric(sorted(samples)[math.ceil(.95 * len(samples)) - 1]
                                               if complete else None, 'minutes')
    result.update(cost_per_verified_task_usd=metric(sum(costs) / count
                  if count and all(c is not None for c in costs) else None, 'USD/task'),
                  owner_minutes_per_verified_task=metric(sum(minutes) / count
                  if count and all(m is not None for m in minutes) else None, 'minutes/task'),
                  recovery_success_rate=metric(sum(r['success'] for r in recoveries) / len(recoveries)
                                               if count and recoveries else None, 'fraction'),
                  regression_rate=metric(regressed / count if count else None, 'fraction'))
    return result


def differences(first, last, status='measured'):
    return {name: metric(b['value'] - a['value'] if a['value'] is not None and b['value'] is not None else None,
                         'percentage points' if b['unit'] == 'percent' else b['unit'], status)
            for name, a in first.items() for b in [last[name]]}


def evaluation(sources, since, now, baseline):
    summary = period_metrics(sources, since, now, final=True)
    weeks, start = [], since
    while start < now:
        end = min(start + 7 * DAY, now)
        weeks.append(dict(week=len(weeks) + 1, since=start, until=end, days=(end - start) / DAY,
                          metrics=period_metrics(sources, start, end, final=end == now)))
        start = end
    estimates = {k: metric(baseline[k] if baseline else None, summary[k]['unit'], 'estimate') for k in BASELINE_METRICS}
    return dict(summary=summary, phase_diagnostics=phase_diagnostics(sources, since, now),
                weeks=weeks, change=differences(weeks[0]['metrics'], weeks[-1]['metrics']),
                baseline=dict(description='owner-supplied baseline' if baseline else 'no baseline', metrics=estimates),
                baseline_change=differences(estimates, {k: summary[k] for k in BASELINE_METRICS}, 'estimate'))


def report(repositories, days=7, *, now=None, baseline=None):
    """One canonical report for text, JSON and CSV. Repositories are (path, name) pairs."""
    if type(days) is not int or not 1 <= days <= 30:
        raise ValueError('days must be between 1 and 30')
    now = time.time() if now is None else now
    rows, sources, seen = {}, [], set()
    for repo, name in repositories:
        identity = common_dir(repo) or Path(repo).resolve()
        if identity in seen:
            continue
        seen.add(identity)
        row, data = _collect(repo, days, now)
        source = observations(data, now)
        row['evaluation'] = evaluation([source], now - days * DAY, now, baseline)
        name = name if name not in rows else f'{name} ({repo})'
        rows[name] = row
        sources.append(source)
    return dict(days=days, since=now - days * DAY, until=now, runners=rows,
                overall=evaluation(sources, now - days * DAY, now, baseline))


def metric_rows(card):
    yield 'summary', card['summary']
    for week in card['weeks']:
        yield f'week-{week["week"]}', week['metrics']
    yield 'change', card['change']
    yield 'baseline', card['baseline']['metrics']
    yield 'baseline_change', card['baseline_change']
    for name, row in card['phase_diagnostics'].items():
        yield f'phase_diagnostics.{name}', row['metrics']


def phase_labels(card, period):
    return card['phase_diagnostics'].get(period.removeprefix('phase_diagnostics.'), {})


def csv_report(result):
    """Lossless long-form metrics; empty values mean missing, never numeric zero."""
    output = io.StringIO(newline='')
    writer = csv.writer(output)
    writer.writerow(['scope', 'runner', 'period', 'since', 'until', 'days', 'metric', 'value', 'status', 'unit', 'baseline',
                     'cohort', 'identity', 'rules'])
    cards = [('runner', n, r['evaluation']) for n, r in result['runners'].items()]
    cards.append(('overall', '', result['overall']))
    for scope, name, card in cards:
        weeks = {f'week-{w["week"]}': w for w in card['weeks']}
        for period, metrics in metric_rows(card):
            window = weeks.get(period, result)
            for key, value in metrics.items():
                writer.writerow([scope, name, period, window['since'], window['until'], window['days'],
                                 key, value['value'], value['status'], value['unit'], card['baseline']['description'],
                                 *(phase_labels(card, period).get(label, '') for label in ('cohort', 'identity', 'rules'))])
    return output.getvalue()


def report_table(result):
    lines = table(result['runners'], result['days'])
    cards = [(name, row['evaluation']) for name, row in result['runners'].items()]
    cards.append(('overall', result['overall']))
    for name, card in cards:
        lines.append(f'\n{name}: evaluation ({card["baseline"]["description"]})')
        for period, metrics in metric_rows(card):
            labels = phase_labels(card, period)
            if labels:
                lines.append(f'  {period}: ' + '; '.join(f'{key}={labels[key]}' for key in ('cohort', 'identity', 'rules')))
            lines.append(f'  {period}: ' + '; '.join(
                f'{key}={value["value"]:g} {value["unit"]} [{value["status"]}]'
                if value['value'] is not None else f'{key}=missing [missing]' for key, value in metrics.items()))
    return lines


def table(rows, days):
    """Plain-text lines for `rows` ({name: measure(...)})."""
    if not rows:
        return ['autowork scorecard: no runners']
    name_w = max(len('runner'), *(len(n) for n in rows))
    head = f"{'runner':<{name_w}}  {'closed':>6}  {'verified':>8}  {'manual':>6}  {'unverified':>10}  {'held':>9}  {'start→merge':>11}  {'questions':>9}"
    lines = [f'autowork scorecard, last {days} day(s)', head]
    for name, row in rows.items():
        held = (f"{row['held_share']:.0%} of {row['integrations']}" if row['held_share'] is not None else '-')
        merge = (f"{row['start_to_merge_minutes']} min" if row['start_to_merge_minutes'] is not None else '-')
        lines.append(f"{name:<{name_w}}  {row['closed']:>6}  {row.get('verified_closed', 0):>8}  {row.get('manual_closed', 0):>6}  {row.get('unverified_closed', 0):>10}  {held:>9}  {merge:>11}  {row['questions']:>9}")
        if 'usage' in row:
            usage = row['usage']
            cost = f"${usage['measured_cost_usd']:.2f} measured"
            if usage['cost_usd'] is None:
                cost += f", total unknown ({usage['unknown_cost_runs']} run(s) without billing)"
            minutes = usage['owner_minutes']
            attention = f'{minutes:g} recorded min' if minutes is not None else 'unknown'
            lines.append(f"  usage: {cost}; owner attention: {attention}; "
                         f"{usage['unattributed']['runs']} unattributed run(s)")
    total = sum(r['closed'] for r in rows.values())
    asked = sum(r['questions'] for r in rows.values())
    lines.append(f'{len(rows)} runner(s): {total} task(s) closed, {asked} question(s) for the owner')
    return lines
