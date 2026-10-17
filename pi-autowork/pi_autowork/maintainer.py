"""DOCS-MAINTAINER: the runner role that repairs task docs instead of leaving it to the owner.

Accepted plan: docs/plans/2026-10-17-docs-maintainer.md (TOOLSET-164-f1). Many holds are
not product questions: a wrong Touches list, an ambiguous or incomplete contract, a task
the engine will not run as written. The fix is to restate the task from the repository's
own evidence and run it again. One maintainer run handles every pending trigger at once;
an unchanged trigger set never reruns, and no trigger means no model call.

This module holds the pure parts (triggers, the trigger-set key, the prompt, the run
record); the coordinator runs the job in a disposable checkout and merges what it
commits. Standard library only.
"""
import hashlib
import json
from pathlib import Path
import time

ROLE = 'DOCS-MAINTAINER'
PLANNING_CAUSES = ('scope', 'scope_request', 'blocker', 'contract_changed')
PLANNING_FILES = ('TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md')
PLANNING_DIRS = ('docs/tasks/',)
LIMIT = 12


def triggers(rows, main=None, findings=None):
    """[(task, kind, why)] the maintainer can act on: a hold with a planning cause, a task the
    engine will not run as written, or a red main (TOOLSET-176-98) as the item `MAIN`. Sorted,
    so the same queue gives the same set."""
    found = []
    if (main or {}).get('state') == 'red':
        commits = '; '.join((main.get('commits') or [])[:10]) or 'unknown'
        found.append(('MAIN', 'main red', f"failing: {', '.join(main.get('failures') or [])}; commits since the last "
                                         f"green main: {commits}"[:900]))
    for row in rows:
        task, state, reason = row.get('task'), row.get('state'), ' '.join(str(row.get('reason') or '').split())
        if not task:
            continue
        if state == 'held' and not row.get('worker_live') and row.get('cause') in PLANNING_CAUSES:
            found.append((task, 'held: ' + row['cause'], reason[:400]))
        elif (state == 'held' and not row.get('worker_live') and row.get('cause') == 'validation'
              and int(row.get('attempt') or 0) >= 2 and (findings or {}).get(task)):
            # Its last attempt was reviewed and found wanting: split or restate it by the findings.
            found.append((task, 'review findings', ' '.join(findings[task].split())[:600]))
        elif state == 'waiting' and reason.startswith('not runnable'):
            found.append((task, 'not runnable', reason[:400]))
    return sorted(found)[:LIMIT]


def key(found):
    return hashlib.sha256(json.dumps(found).encode()).hexdigest()[:16]


def planning_only(paths):
    """Whether every changed path is a planning file the maintainer may write."""
    return bool(paths) and all(p in PLANNING_FILES or p.startswith(PLANNING_DIRS) for p in paths)


PROMPT = (
    'You are the DOCS-MAINTAINER of {repo}: you repair task docs so that held and unrunnable tasks can '
    'run again, without the owner. The runner cannot run these tasks as they are written:\n{items}\n'
    'For each one, read its TODO.md entry, its Sources and accepted plans, and the worker\'s report under '
    '.git/autowork-execution/slot-data/<task>/ when there is one. Then, only from that evidence: restate '
    'an ambiguous contract; correct Touches, Checks or Dependencies (a worker that names the exact files '
    'it needs is evidence); fill a missing required field from the task\'s own sources; split an oversized '
    'task; supersede a duplicate with python3 {goals} supersede; re-sort to unblock a dependency chain '
    '(never above the owner\'s first tasks in Now). For MAIN (main fails its full offline check): unless an '
    'open task already covers those failures, add one repair task first in Now with python3 {goals} add-task '
    'and write its entry with the failing tests and the commits as Evidence, Touches from the failing tests '
    'and the files those commits changed, and the full check as its Checks. For review findings (the last '
    'attempt was reviewed and found wanting): split the task into what its commit already does and a follow-up '
    'whose Acceptance lists the reviewer\'s findings, or restate it so the findings are explicit; keep every '
    'Acceptance item, and leave it as it is if a finding needs a product decision. Never change product scope or Acceptance, grant '
    'authority, credentials or spending, or decide a product question: leave such a task as it is. Use '
    '/skill:docs-sync and its goals.py commands for TODO.md and goals.json, run python3 {goals} validate . '
    'and fix what it reports, edit only TODO.md, goals.json, BLOCKERS.md, TODO.archive.md and docs/tasks/, '
    'and commit once on this checkout with a message that gives each change\'s reason. Do not push or '
    'switch branches. End with one line: PI_AUTOWORK_RESULT: completed or PI_AUTOWORK_RESULT: blocked, '
    'then the tasks you changed.')


def prompt(found, repo, goals):
    items = '\n'.join(f'- {task} ({kind}): {why}' for task, kind, why in found)
    return PROMPT.format(repo=repo, items=items, goals=goals)


def record_path(state):
    return Path(state) / 'maintainer.json'


def last(state):
    try:
        value = json.loads(record_path(state).read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


RETRYABLE = 'refused: it conflicts with the session'
TRIES = 2


def due(state, trigger_key):
    """Whether this trigger set still needs a run: a new set, or one whose last run was refused
    only because the session moved under it, tried fewer than TRIES times (one runner stalled
    for hours: the same set never reran after such a refusal)."""
    run = last(state)
    if run.get('key') != trigger_key:
        return True
    return run.get('outcome') == RETRYABLE and int(run.get('tries') or 1) < TRIES


def remember(state, *, trigger_key, found, outcome, changed=(), now=None):
    previous = last(state)
    tries = int(previous.get('tries') or 1) + 1 if previous.get('key') == trigger_key else 1
    value = dict(role=ROLE, key=trigger_key, at=time.time() if now is None else now, outcome=outcome,
                 triggers=[task for task, _, _ in found], changed=list(changed), tries=tries)
    path = record_path(state)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value) + '\n')
    tmp.replace(path)
    return value
