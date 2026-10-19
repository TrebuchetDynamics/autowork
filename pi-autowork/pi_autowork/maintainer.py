"""DOCS-MAINTAINER: the runner role that repairs task docs instead of leaving it to the owner.

Accepted plan: docs/plans/2026-10-17-docs-maintainer.md (TOOLSET-164-f1). Many holds are
not product questions: a wrong Touches list, an ambiguous or incomplete contract, a task
the engine will not run as written. The fix is to restate the task from the repository's
own evidence and run it again. One maintainer run handles pending items in a batch;
handled items stay handled across batches until their entry or reason class changes.
An unchanged unsuccessful repair becomes an owner question, not another model call.

This module holds the pure parts (triggers, item receipts, the prompt, the run
record); the coordinator runs the job in a disposable checkout and merges what it
commits. Standard library only.
"""
import hashlib
import json
from pathlib import Path
import re
import time

ROLE = 'DOCS-MAINTAINER'
PLANNING_CAUSES = ('scope', 'scope_request', 'blocker', 'contract_changed', 'no_change')
PLANNING_FILES = ('TODO.md', 'goals.json', 'BLOCKERS.md', 'TODO.archive.md')
PLANNING_DIRS = ('docs/tasks/',)
LIMIT = 12


def triggers(rows, main=None, findings=None, reported_flakes=(), ledger_errors=(), limit=LIMIT):
    """[(task, kind, why)] planning holds, unrunnable tasks, MAIN failures or invalid LEDGER.
    Ledger errors take precedence: nothing can run until they validate. Sorted, so
    the same queue/errors give the same set."""
    errors = sorted({' '.join(str(e).split()) for e in ledger_errors if str(e).strip()})
    if errors:
        # Do not let changing task holds/main commits retrigger the same ledger repair.
        return [('LEDGER', 'invalid goals.json', '\n'.join(errors))]
    found = []
    if (main or {}).get('state') == 'red':
        commits = '; '.join((main.get('commits') or [])[:10]) or 'unknown'
        found.append(('MAIN', 'main red', f"failing: {', '.join(main.get('failures') or [])}; commits since the last "
                                         f"green main: {commits}"[:900]))
    if (main or {}).get('state') == 'broken':
        found.append(('MAIN', 'check broken', f"the full check crashed twice before any test result at "
                                              f"{(main.get('rev') or '')[:12]}: {main.get('crash') or 'unknown'}"[:900]))
    for test_id, revisions in ((main or {}).get('flaky_history') or {}).items():
        if len(set(revisions)) >= 3 and test_id not in reported_flakes:
            found.append(('MAIN', 'flaky test', f'{test_id}; flaky on revisions: {", ".join(revisions[:3])}'))
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
    return sorted(found)[:limit]


def key(found):
    """The set's identity. A red main is the same trigger while the same tests fail: tasks now
    land one by one, so its commits since the last green grow without anything new to repair."""
    same = [(task, kind, why.split('; commits since')[0] if task == 'MAIN' else why) for task, kind, why in found]
    return hashlib.sha256(json.dumps(same).encode()).hexdigest()[:16]


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
    'task; restate a contract that demands what no one provides (a coordinator receipt, handoff, registry or '
    'verification the repository has no mechanism for) to what an unattended worker can do, and let it repair a '
    'defect already in the code that stops its checks; '
    'supersede a duplicate with python3 {goals} supersede; re-sort to unblock a dependency chain '
    '(never above the owner\'s first tasks in Now). For LEDGER (goals.py validate errors): repair the ledger '
    'and its planning docs from repository evidence. An unverified goal with no open task needs a task for '
    'its remaining proof, or an evidence-backed status correction; never invent proof or mark it verified '
    'just to pass validation. For MAIN (flaky test): the test failed in the full run '
    'but passed alone on three different revisions. Unless an open task already covers it, add one test-hardening '
    'task with those revisions as Evidence; investigate isolation, resource load and fixture timing, not a '
    'product-code repair. Main is not red for a flaky test. For MAIN (check broken): the full check itself crashed before '
    'reporting any test result, so no test is known to fail. Never add a repair task for test names. Unless an open task '
    'covers it, add one task to make the full check run to its results (pin or provision the crashing tool from the '
    'repository\'s setup docs, or restate the repository\'s `Full check:` line), with the crash line as Evidence. '
    'For held: no_change (the worker ran the task and found nothing to change; its report says why): when '
    'the report\'s evidence shows the Acceptance is already met, close the task as done with that evidence '
    'through {goals}; otherwise restate the task so it names the change to make. '
    'For MAIN (main red, main fails its full offline check): unless an '
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


def entries(todo, goals):
    """Entry digests and named fields, using the same task parser as the engine."""
    result = {}
    for task, bodies in goals.task_bodies(todo).items():
        body, mark, section = bodies[0]
        fields = dict(goals.task_fields(body), Title=body.partition('\n')[0].strip(),
                      Checkbox=mark, Section=section)
        content = [(text.rstrip(), checkbox, heading) for text, checkbox, heading in bodies]
        digest = hashlib.sha256(json.dumps(content).encode()).hexdigest()
        result[task] = dict(digest=digest, fields=fields)
    return result


def reason_class(why, task_ids=()):
    """Waiting reason without known task IDs or ID-shaped tokens/counts; keep prose intact."""
    ids = set(task_ids)
    why = re.sub(r'\b[A-Za-z0-9][\w-]*\b', lambda m: '' if m[0] in ids else m[0], why)
    why = re.sub(r'\b(?:[A-Z][A-Z0-9]*(?:[-_][A-Za-z0-9]+)+|[A-Z]|[A-Za-z][\w-]*\d[\w-]*|\d+[A-Za-z][\w-]*)\b|\d+', '', why)
    return ' '.join(why.split())


def item_key(item):
    return key([item]) if item[0] in ('MAIN', 'LEDGER') else 'task:' + item[0]


def matches(receipt, item, entry, reasons, task_ids):
    if not receipt:
        return False
    if item[0] in ('MAIN', 'LEDGER'):
        return True  # the key already identifies the exact test/error
    why = (reasons or {}).get(item[0], item[2])
    return (receipt.get('digest') == entry.get('digest', '')
            and reason_class(receipt['reason'], task_ids) == reason_class(why, task_ids))


def pending(state, found, *, entries=None, reasons=None):
    """Only unhandled items, bounded after filtering so old holds cannot starve overflow."""
    run = last(state)
    records = run.get('items', {})
    # Keep ID context after tasks are archived. Compare both raw reasons with that
    # same context, so learning a new ID cannot change only one side's identity.
    ids = set(run.get('task_ids', [])) | set(entries or {})
    updated = ids != set(run.get('task_ids', []))
    run['task_ids'] = sorted(ids)
    if 'items' not in run and run.get('key') == key(found[:LIMIT]):
        # Upgrade only the exact batch the old record proves was handled. It had no
        # entry/field evidence: anchor to today's entries without inventing changed fields.
        records = {item_key(item): dict(outcome=run.get('outcome'), tries=int(run.get('tries') or 1), fields=[],
                                       reason=(reasons or {}).get(item[0], item[2]),
                                       digest=(entries or {}).get(item[0], {}).get('digest', ''))
                   for item in found[:LIMIT]}
        run['items'] = records
        updated = True
    if updated:
        save(state, run)
    selected = []
    for item in found:
        if item[0] == 'LEDGER' and key([item]) in run.get('ledger_attempts', {}):
            continue
        receipt = records.get(item_key(item))
        if matches(receipt, item, (entries or {}).get(item[0], {}), reasons, ids):
            if receipt['outcome'] != RETRYABLE or receipt['tries'] >= TRIES:
                continue
        elif (item[0] == 'MAIN' and key([item]) in run.get('handled_triggers', [])
              and run.get('outcome') != RETRYABLE):
            continue  # pre-item-receipt MAIN records
        selected.append(item)
    return selected[:LIMIT]


def stalled(state, found, *, entries, reasons=None):
    """Merged task repairs that left the same entry waiting for the same reason class."""
    run = last(state)
    records = run.get('items', {})
    ids = set(run.get('task_ids', [])) | set(entries)
    result = []
    for item in found:
        task, _, why = item
        receipt = records.get(item_key(item), {})
        if (task not in ('MAIN', 'LEDGER') and matches(receipt, item, entries.get(task, {}), reasons, ids)
                and receipt.get('outcome') == 'merged' and receipt.get('fields')):
            result.append(dict(task=task, reason=(reasons or {}).get(task, why), fields=receipt['fields']))
    return result


def due(state, trigger_key, found=None, *, entries=None, reasons=None):
    """Per-item due-ness; retain set-key compatibility for callers without item details."""
    if found is not None:
        return bool(pending(state, found, entries=entries, reasons=reasons))
    run = last(state)
    if trigger_key in run.get('ledger_attempts', {}):
        return False  # each ledger error set runs once, even across unrelated maintainer runs
    if run.get('key') != trigger_key:
        return True
    return run.get('outcome') == RETRYABLE and int(run.get('tries') or 1) < TRIES


def remember(state, *, trigger_key, found, outcome, changed=(), entries=None, before=None, reasons=None, now=None):
    previous = last(state)
    tries = int(previous.get('tries') or 1) + 1 if previous.get('key') == trigger_key else 1
    value = dict(role=ROLE, key=trigger_key, at=time.time() if now is None else now, outcome=outcome,
                 triggers=[task for task, _, _ in found], changed=list(changed), tries=tries)
    records = previous.get('items', {}).copy()
    ids = set(previous.get('task_ids', [])) | set(entries or {}) | set(before or {})
    if ids:
        value['task_ids'] = sorted(ids)
    for item in found:
        task = item[0]
        entry = (entries or {}).get(task, {})
        identity = item_key(item)
        prior = records.get(identity, {})
        attempts = prior.get('tries', 0) if matches(prior, item, entry, reasons, ids) else 0
        old = (before or {}).get(task, {}).get('fields', {})
        new = entry.get('fields', {})
        fields = sorted(field for field in old.keys() | new.keys() if old.get(field) != new.get(field))
        why = (reasons or {}).get(task, item[2])
        records[identity] = dict(task=task, reason=why, reason_class=reason_class(why, ids),
                                 digest=entry.get('digest', ''), outcome=outcome, tries=attempts + 1,
                                 fields=(fields or ['entry text']) if outcome == 'merged' and task in changed else [])
    value['items'] = records
    if previous.get('handled_triggers'):
        value['handled_triggers'] = previous['handled_triggers']
    flaky_tests = set(previous.get('flaky_tests') or [])
    if outcome != RETRYABLE:
        flaky_tests.update(why.split('; flaky on revisions:')[0] for _, kind, why in found if kind == 'flaky test')
    if flaky_tests:
        value['flaky_tests'] = sorted(flaky_tests)
    ledger_attempts = previous.get('ledger_attempts', {}).copy()
    if any(task == 'LEDGER' for task, _, _ in found):
        ledger_attempts[trigger_key] = outcome
    if ledger_attempts:
        value['ledger_attempts'] = ledger_attempts
    save(state, value)
    return value


def save(state, value):
    path = record_path(state)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value) + '\n')
    tmp.replace(path)
