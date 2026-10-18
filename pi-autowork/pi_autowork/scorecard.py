"""`autowork scorecard`: what each runner delivered and what it cost, over a window of days.

Read from each repository's engine journal and Git history, without a model call:

- closed: tasks whose checked entry was added to the TODO archive in the window, however
  they were closed (the engine, the maintainer or a person);
- held: the share of integrations (a slot leaving `integrating`) that ended `held`
  rather than `integrated`, the rework a failed review or check costs;
- start to merge: the median time from a task's first dispatch to its integration;
- questions: distinct owner questions (`### Q-…`) added to BLOCKERS.md in the window.
"""
import json
from pathlib import Path
import re
import statistics
import subprocess
import time

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
    path = common / JOURNAL
    events = []
    try:
        with open(path, errors='replace') as stream:
            for line in stream:
                if '"slot_changed"' not in line:
                    continue
                try:
                    event = json.loads(line)
                except ValueError:
                    continue
                if event.get('timestamp', 0) >= since:
                    events.append(event)
    except OSError:
        return []
    return sorted(events, key=lambda e: e['timestamp'])


ARCHIVES = ('docs/TODO-archive.md', 'TODO.archive.md', 'todo.archive.md')
CHECKED = re.compile(r'(?m)^\s*[-*] \[[xX]\]\s+[*`]*([A-Za-z][\w.-]*\d[\w.-]*)')


def git_text(repo, *argv):
    try:
        return subprocess.run(['git', '-C', str(repo), *argv], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return ''


def archived(repo, days):
    """Task IDs checked in the TODO archive now but not at the last commit before the window:
    every close, however it was made, and none twice when a commit rewrites the archive."""
    tracked = set(git_text(repo, 'ls-files', '--', *ARCHIVES).split())
    start = git_text(repo, 'rev-list', '-1', f'--before={days} days ago', 'HEAD').strip()
    now, before = set(), set()
    for path in ARCHIVES:
        if path not in tracked:
            continue
        now |= set(CHECKED.findall(git_text(repo, 'show', f'HEAD:{path}')))
        if start:
            before |= set(CHECKED.findall(git_text(repo, 'show', f'{start}:{path}')))
    return now - before


def owner_questions(repo, days):
    """Distinct question headings added to BLOCKERS.md in the last `days` days."""
    try:
        log = subprocess.run(['git', '-C', str(repo), 'log', f'--since={days} days ago', '-p', '--format=',
                              '--', 'BLOCKERS.md'], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.TimeoutExpired):
        return 0
    return len(set(re.findall(r'(?m)^\+### (Q-\S+)', log)))


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
    return {'repo': str(repo), 'closed': len(archived(repo, days)), 'integrations': attempts,
            'held_share': round(held / attempts, 2) if attempts else None,
            'start_to_merge_minutes': round(statistics.median(merge_minutes)) if merge_minutes else None,
            'questions': owner_questions(repo, days)}


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
