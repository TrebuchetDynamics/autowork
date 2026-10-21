"""`autowork scorecard`: what each runner delivered and what it cost, over a window of days.

Read from each repository's engine journal and Git history, without a model call:

- closed: tasks whose record became done in the window, however they were closed (the
  engine, the maintainer or a person);
- held: the share of integrations (a slot leaving `integrating`) that ended `held`
  rather than `integrated`, the rework a failed review or check costs;
- start to merge: the median time from a task's first dispatch to its integration;
- questions: distinct owner questions (`### Q-…`) added to BLOCKERS.md in the window.
"""
from pathlib import Path
import re
import statistics
import subprocess
import sys
import time
import tomllib

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
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
    import execution_journal
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
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
    from task_store import StoreError, TaskStore
    try:
        return {t.id for t in TaskStore.at(repo, rev).tasks.values() if t.status == 'done'}
    except StoreError:
        return None


def closed(repo, days):
    """Task IDs done now but not at the last commit before the window: every close, however it
    was made. A window that starts before the repository's conversion counts from the
    conversion commit, which closes nothing."""
    now = done(repo, 'HEAD') or set()
    start = git_text(repo, 'rev-list', '-1', f'--before={days} days ago', 'HEAD').strip()
    before = done(repo, start) if start else None
    if before is None:
        since = [f'{start}..HEAD'] if start else ['HEAD']
        first = git_text(repo, 'rev-list', '--reverse', *since, '--', 'tasks').split()
        before = (done(repo, first[0]) or set()) if first else set()
    return now - before


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
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
    from task_store import StoreError, TaskStore
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
    now = time.time() if now is None else now
    since = now - days * 86400
    common = common_dir(repo)
    events = journal_events(common, since) if common else []
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
    return {'repo': str(repo), 'closed': len(closed(repo, days)), 'integrations': attempts,
            'held_share': round(held / attempts, 2) if attempts else None,
            'start_to_merge_minutes': round(statistics.median(merge_minutes)) if merge_minutes else None,
            'questions': owner_questions(repo, days),
            'regressions': attributed, 'regressions_incomplete': incomplete}


def table(rows, days):
    """Plain-text lines for `rows` ({name: measure(...)})."""
    if not rows:
        return ['autowork scorecard: no runners']
    name_w = max(len('runner'), *(len(n) for n in rows))
    head = f"{'runner':<{name_w}}  {'closed':>6}  {'held':>9}  {'start→merge':>11}  {'questions':>9}"
    lines = [f'autowork scorecard, last {days} day(s)', head]
    for name, row in rows.items():
        held = (f"{row['held_share']:.0%} of {row['integrations']}" if row['held_share'] is not None else '-')
        merge = (f"{row['start_to_merge_minutes']} min" if row['start_to_merge_minutes'] is not None else '-')
        lines.append(f"{name:<{name_w}}  {row['closed']:>6}  {held:>9}  {merge:>11}  {row['questions']:>9}")
    total = sum(r['closed'] for r in rows.values())
    asked = sum(r['questions'] for r in rows.values())
    lines.append(f'{len(rows)} runner(s): {total} task(s) closed, {asked} question(s) for the owner')
    return lines
