"""Accepted source resolution, consumer readiness and first-index lifecycle."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
import re
import sys
from pathlib import Path

from goals_ledger import (
    SECTION_RANK, checked_bytes, dump, errors, git_identity,
    load, normalize, parse_ledger, path_of, revision,
)
from goals_queue import (
    queue,
)
from goals_todo import (
    heading_rows, markdown_prose, render, render_text, task_bodies,
    task_fields, task_prose,
)


def reference_key(ref):
    """Normalize harmless local spelling differences, never traversal or URLs."""
    name, separator, anchor = ref.partition('#')
    path = Path(name or 'TODO.md')
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref) or path.is_absolute() or '..' in path.parts:
        return ref
    return path.as_posix() + separator + anchor


def plan_acceptance_error(section):
    """One explicit status is required; conflicting metadata is not acceptance."""
    statuses = re.findall(r'^[ \t]*(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)',
                          markdown_prose(section), re.M | re.I)
    if len(statuses) > 1:
        return 'plan section has conflicting or duplicate Status metadata'
    if len(statuses) != 1 or statuses[0].strip().lower() != 'accepted':
        return 'plan section lacks explicit Status: Accepted'
    return ''


def local_reference(repo, ref, blobs, reasons, *, include_children=False):
    """Resolve maintained links; optionally return the raw full heading subtree.

    Acceptance metadata belongs to the heading's introduction. Scope recovery
    must compare all descendants, including fenced examples, byte for byte.
    """
    if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref):
        return ''  # Remote sources are not locally qualified.
    name, _, anchor = ref.partition('#')
    path = Path(name or 'TODO.md')
    if path.is_absolute() or '..' in path.parts:
        reasons.append(f'nonlocal reference {ref}')
        return ''
    for parent in (path, *path.parents):
        if (repo / parent).is_symlink():
            reasons.append(f'symlink reference {ref}')
            return ''
    name = path.as_posix()
    if name not in blobs:
        blobs[name] = checked_bytes(repo / path)
    blob = blobs[name]
    if blob is None:
        reasons.append(f'missing reference {ref}')
        return ''
    if not anchor:
        return markdown_prose(blob.decode('utf-8')) if path.suffix.lower() in ('.md', '.markdown') else ''
    text = markdown_prose(blob.decode('utf-8'))
    headings = heading_rows(text)
    found = next((i for i, row in enumerate(headings) if row[0] == anchor), None)
    if found is None:
        reasons.append(f'missing anchor {ref}')
        return ''
    end = next((row[1] for row in headings[found + 1:]
                if not include_children or row[3] <= headings[found][3]), len(text))
    source = blob.decode('utf-8') if include_children else text
    return source[headings[found][2]:end]


def backlog_receipt(a, *, candidate=None):
    """Check consumer contracts; candidate bytes are only for init preflight."""
    repo = Path(a.repo)
    blobs = {name: checked_bytes(repo / name) for name in ('TODO.md', 'goals.json')}
    if candidate is not None:
        blobs.update(candidate)
    reasons = [f'missing {name}' for name, blob in blobs.items() if blob is None]
    identity = git_identity(repo)
    if identity is None and candidate is None:
        reasons.append('unbound non-Git fixture is not consumer authority')
    plan_path, _, anchor = a.plan.partition('#')
    plan = repo / plan_path
    if not plan_path or Path(plan_path).is_absolute() or '..' in Path(plan_path).parts:
        reasons.append('plan must be repo-relative')
    else:
        if plan_path not in blobs:
            blobs[plan_path] = checked_bytes(plan)
        if blobs[plan_path] is None:
            reasons.append('missing accepted plan')
    ids = a.tasks.split(',')
    if len(ids) != len(set(ids)) or any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', tid) for tid in ids):
        reasons.append('tasks must name unique existing IDs without normalization')
    if not anchor:
        reasons.append('accepted plan requires a heading anchor')
    if plan_path and not Path(plan_path).is_absolute() and '..' not in Path(plan_path).parts:
        decision = local_reference(repo, a.plan, blobs, reasons)
        acceptance_error = plan_acceptance_error(decision)
        if acceptance_error:
            reasons.append(acceptance_error)
        for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', decision):
            if not re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', ref):
                name, separator, heading = ref.partition('#')
                resolved = os.path.normpath(Path(plan_path).parent / name) if name else plan_path
                local_reference(repo, resolved + (separator + heading if separator else ''), blobs, reasons)
    picks = []
    data = None
    priority = {'state': 'unknown'}
    if blobs['goals.json'] is not None:
        try:
            ledger_blob = blobs['goals.json']
            assert ledger_blob is not None
            data = parse_ledger(ledger_blob)
            ledger_errors = errors(data)
            reasons.extend(ledger_errors)
            if ledger_errors:
                data = None
            else:
                data = normalize(data)
                if not reasons:
                    ranked, priority = queue(data, (blobs['TODO.md'] or b'').decode('utf-8'), allow_drift=True)
                    picks = [t['id'] for t, _ in ranked]
        except (ValueError, TypeError, KeyError, AttributeError) as exc:
            reasons.append(f'invalid backlog: {exc}')
            data = None
    # Plan metadata and task contracts are independent repairable inputs. Report
    # both in one pass, but never turn a partial diagnostic into readiness.
    if data is not None and blobs['TODO.md'] is not None:
        todo_blob = blobs['TODO.md']
        assert todo_blob is not None
        bodies = task_bodies(todo_blob.decode('utf-8'))
        known = {t['id'] for t in data['tasks']}
        goals_by_id = {g['id']: g for g in data['goals']}
        dependency_ids = known | goals_by_id.keys()
        # Goal IDs predate TASK_ID and may contain punctuation or spaces. Keep
        # their exact legacy matching, compiling only those exceptional IDs once.
        non_token_goals = {gid: re.compile(r'(?<![\w-])' + re.escape(gid) + r'(?![\w-])')
                           for gid in goals_by_id if re.fullmatch(r'[\w-]+', gid) is None}
        for tid, entries in bodies.items():
            if tid not in known and any(mark == ' ' and section in SECTION_RANK
                                       for _, mark, section in entries):
                reasons.append(f'{tid}: executable body has no ledger task')
        for t in data['tasks']:
            tid = t['id']
            entries = bodies.get(tid, [])
            if t['status'] == 'superseded':
                continue  # Explicitly retired bodies can retain unchecked history in the archive.
            if t['status'] == 'done':
                if any(mark == ' ' for _, mark, _ in entries):
                    reasons.append(f'{tid}: checkbox/section does not match done ledger task')
                continue
            if len(entries) != 1:
                reasons.append(f'{tid}: missing or duplicate task body')
                continue
            body, checked, section = entries[0]
            fields = task_fields(body)
            for label in ('Goal', 'Scope', 'Acceptance', 'Dependencies', 'Sources'):
                if label not in fields:
                    reasons.append(f'{tid}: missing {label}')
            if not re.match(r'`?' + re.escape(t['goal']) + r'`?(?:[.\s]|$)', fields.get('Goal', '')):
                reasons.append(f'{tid}: Goal does not match ledger')
            if checked != ' ' or section != t.get('section', 'Next'):
                reasons.append(f'{tid}: checkbox/section does not match ledger')
            goal = goals_by_id[t['goal']]
            expected = set(t.get('depends_on', []) + goal.get('depends_on', []))
            dependencies = fields.get('Dependencies', '')
            # An explicit None declaration can be followed by coordination or
            # history, not executable prerequisites. Do not let those notes
            # invent edges or satisfy a missing ledger dependency. Keep full
            # matching for actual prerequisite lists, including numbered lists.
            if re.match(r'none\b', dependencies, re.I):
                dependencies = re.split(r'\.(?:\s|$)', dependencies, maxsplit=1)[0]
            # Tokens preserve the old (?<![\w-])ID(?![\w-]) boundaries for task
            # and simple goal IDs; exceptional goal IDs use the compiled fallback.
            # Parse the field once; scanning every known ID per task is quadratic
            # and thrashes Python's regex cache on large backlogs.
            named = set(re.findall(r'[\w-]+', dependencies)) & dependency_ids
            named.update(gid for gid, pattern in non_token_goals.items() if pattern.search(dependencies))
            for dep in sorted(expected - named):
                reasons.append(f'{tid}: Dependencies do not name {dep}')
            for dep in sorted(named - expected):
                reasons.append(f'{tid}: Dependencies name {dep} absent from ledger')
            sources = re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', fields.get('Sources', ''))
            if tid in ids and reference_key(a.plan) not in {reference_key(ref) for ref in sources}:
                reasons.append(f'{tid}: Sources do not link accepted plan')
            for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', task_prose(body)):
                local_reference(repo, ref, blobs, reasons)
        for g in data['goals']:
            local_reference(repo, g['source'], blobs, reasons)
    ineligible = []
    if data is not None and not reasons:
        tasks = {t['id']: t for t in data['tasks']}
        goals = {g['id']: g for g in data['goals']}
        for tid in ids:
            t = tasks.get(tid)
            if t is None:
                reasons.append(f'unknown task {tid}')
                continue
            g = goals[t['goal']]
            if tid not in picks:
                ineligible.append(f'{tid}: not eligible (status={t["status"]}, section={t["section"]}, goal={g["status"]})')
            if t['status'] == 'in_progress':
                ineligible.append(f'{tid}: already in progress')
            for dep in t.get('depends_on', []):
                if tasks[dep]['status'] != 'done':
                    ineligible.append(f'{tid}: unmet task dependency {dep}')
            for dep in g.get('depends_on', []):
                if goals[dep]['status'] != 'met':
                    ineligible.append(f'{tid}: unmet goal dependency {dep}')
        # In-progress work is reconciled separately. A named plan checks its own
        # goals' ordered frontier, not unrelated goals in the global queue.
        # Explicit task scope, current source and actual writer checks still apply;
        # metadata readiness does not grant execution or publication authority.
        requested_goals = {tasks[tid]['goal'] for tid in ids if tid in tasks}
        open_picks = [tid for tid in picks if tasks[tid]['status'] == 'open'
                      and tasks[tid]['goal'] in requested_goals]
        if open_picks and open_picks[0] not in ids:
            ineligible.append(f'current frontier {open_picks[0]} precedes requested plan')
        if priority['state'] == 'drift':
            ineligible.append('priority drift: TODO.md order differs from the recorded order; run goals.py reorder')
    if git_identity(repo) != identity:
        reasons.append('Git repository identity changed during check')
    binding = {'git_common_dir': str(identity[0]) if identity else None,
               'registered_authority': None}
    if any(checked_bytes(repo / name) != blob for name, blob in blobs.items()
           if candidate is None or name not in candidate):
        reasons.append('inputs changed during check')
    state = ('draft_saved' if reasons else 'backlog_reconciled_not_eligible'
             if ineligible else 'ready_for_autowork')
    receipt = {'state': state, 'authority_binding': binding,
               'authoritative_repo': str(repo), 'plan': a.plan, 'task_ids': ids,
               'primary_milestone': data.get('primary_milestone') if data else None,
               'focus_fallback_required': bool(data and data.get('primary_milestone')
                    and any(t['id'] in ids and t['goal'] != data['primary_milestone']
                            for t in data['tasks'])),
               'eligible_task_ids': picks, 'live_ownership': 'unknown',
               'priority_state': priority['state'],
               'sha256': {name: hashlib.sha256(blob).hexdigest() if blob is not None else None
                          for name, blob in blobs.items()}, 'reasons': reasons + ineligible}
    if a.receipt:
        try:
            previous = json.loads(checked_bytes(Path(a.receipt)))
        except (ValueError, TypeError, OSError):
            previous = None
        if previous != receipt:
            reasons.append('stale receipt')
            receipt['state'] = 'draft_saved'
            receipt['reasons'] = reasons + ineligible
    return (1 if reasons else 2 if ineligible else 0), receipt


def backlog_check(a):
    """Check the consumer, not the author's fixture; never mutate the backlog."""
    code, receipt = backlog_receipt(a)
    print(json.dumps(receipt, indent=2, sort_keys=True))
    return code


def initialize(a, *, writes):
    """Create only after all input/consumer checks; repeats never rewrite bytes."""
    atomic_write, TRANSACTION = writes.write, writes.transaction
    repo = Path(a.repo)
    try:
        intent_path = Path(a.intent)
        intent_blob = checked_bytes(intent_path)
        if intent_blob is None:
            sys.exit('missing intent file; supply version-1 accepted goal/task intent')
        data = parse_ledger(intent_blob)
        problems = errors(data)
        if problems:
            sys.exit('\n'.join(problems) + '\ninit refused; no write')
        if not data['goals'] or not data['tasks']:
            sys.exit('init requires accepted goals and complete task intent; no write')
        # Normalize a copy; compare full objects including extension metadata.
        normalized = normalize(json.loads(json.dumps(data)))
        ledger = json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=False) + '\n'
        original_todo = checked_bytes(repo / 'TODO.md')
        supplied = checked_bytes(Path(a.todo_file)) if a.todo_file else None
        if a.todo_file and supplied is None:
            sys.exit('missing --todo-file input; no write')
        if original_todo is not None and supplied is not None and original_todo != supplied:
            sys.exit('existing TODO.md conflicts with --todo-file; reconcile intent; no write')
        todo = original_todo if original_todo is not None else supplied
        if todo is None:
            sys.exit('missing TODO.md; supply complete task bodies with --todo-file; no write')
        text = todo.decode('utf-8')
        # Rendering is separate, but reject unsafe coverage before any write.
        render_text(repo, normalized, text)
        bodies = task_bodies(text)
        for task in normalized['tasks']:
            if task['status'] in ('done', 'superseded'):
                continue  # Closed or superseded history may live in the established archive.
            entries = bodies.get(task['id'], [])
            if len(entries) == 1:
                fields = task_fields(entries[0][0])
                if not fields.get('Ownership'):
                    sys.exit(f'{task["id"]}: missing Ownership; no write')
                statuses = re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)',
                                      task_prose(entries[0][0]), re.M)
                if statuses and (len(statuses) != 1 or statuses[0].strip() != task['status']):
                    sys.exit(f'{task["id"]}: Status conflicts with intent; no write')
        candidate = {'goals.json': ledger.encode('utf-8'), 'TODO.md': todo}
        candidate.update(getattr(a, 'sources', None) or {})  # propose: sources as acceptance would leave them
        sources = {}
        for goal in normalized['goals']:
            source = goal['source']
            if not isinstance(source, str) or '#' not in source or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', source):
                sys.exit('init requires local accepted source path#heading for every goal; no write')
            if not goal['tasks']:
                blobs, reasons = dict(candidate), []
                section = local_reference(repo, source, blobs, reasons)
                acceptance = plan_acceptance_error(section)
                if acceptance:
                    reasons.append(acceptance)
                if reasons:
                    sys.exit('\n'.join(reasons) + '\ninit refused; no write')
                sources.update({name: hashlib.sha256(blob).hexdigest() if blob is not None else None
                                for name, blob in blobs.items()})
                continue
            check = argparse.Namespace(repo=str(repo), plan=source,
                                       tasks=','.join(goal['tasks']), receipt=None)
            code, receipt = backlog_receipt(check, candidate=candidate)
            if code == 1:
                sys.exit('\n'.join(receipt['reasons']) + '\ninit refused; no write')
            sources.update(receipt['sha256'])
        existing = checked_bytes(path_of(repo))
        if getattr(a, 'dry_run', False):
            if existing is not None:
                sys.exit('goals.json already exists; propose is only for a first index; no write')
            return normalized
        if existing is not None:
            if original_todo is None:
                sys.exit('existing goals.json has no TODO.md; reconcile bodies through maintenance; no write')
            current = load(repo)
            if errors(current) or normalize(current) != normalized:
                sys.exit('existing goals.json conflicts with intent; use maintenance commands to reconcile; no write')
            print('ok already initialized; no write'); return
        # Freeze referenced sources and inputs too, not just the ledger pair.
        if checked_bytes(intent_path) != intent_blob or (a.todo_file and checked_bytes(Path(a.todo_file)) != supplied):
            sys.exit('initialization inputs changed; no write')
        for name, digest in sources.items():
            if name not in candidate:
                blob = checked_bytes(repo / name)
                if (hashlib.sha256(blob).hexdigest() if blob is not None else None) != digest:
                    sys.exit('accepted sources changed; no write')
        # Roll back only our exact new TODO bytes if ledger replacement fails.
        # This is cooperative coordination, not a crash-atomic two-file commit.
        if original_todo is None:
            atomic_write(repo / 'TODO.md', text, expected_bytes=None)
            digest = hashlib.sha256()
            for name, blob in (('goals.json', None), ('TODO.md', todo)):
                digest.update(name.encode() + b'\0')
                digest.update(b'missing\0' if blob is None else str(len(blob)).encode() + b'\0' + blob)
            TRANSACTION.set((repo, digest.hexdigest()))
        try:
            atomic_write(path_of(repo), ledger, expected_bytes=None)
        except (OSError, SystemExit):
            if original_todo is None and checked_bytes(repo / 'TODO.md') == todo:
                (repo / 'TODO.md').unlink()
            raise
        print('ok initialized; run fmt, validate, render and backlog-check')
    except (OSError, ValueError, TypeError) as exc:
        sys.exit(f'init input/write error: {exc}; reconcile inputs before retrying')


PROPOSED = 'docs/tasks/proposed-goals.json'


ASK_START = '<!-- docs-sync:accept-goals:start -->'


ASK_END = '<!-- docs-sync:accept-goals:end -->'


def accept_section(blob, anchor):
    """The file's bytes with the heading's own Status set to Accepted (inserted under the
    heading when it has none); None when the anchor is missing or its Status is ambiguous."""
    original = blob.decode('utf-8')
    text = markdown_prose(original)
    rows = heading_rows(text)
    found = next((i for i, row in enumerate(rows) if row[0] == anchor), None)
    if found is None:
        return None
    start = rows[found][2]
    end = rows[found + 1][1] if found + 1 < len(rows) else len(text)
    statuses = list(re.finditer(r'^[ \t]*(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)', text[start:end], re.M | re.I))
    if len(statuses) > 1:
        return None
    if statuses:
        first, last = start + statuses[0].start(1), start + statuses[0].end(1)
        return (original[:first] + 'Accepted' + original[last:]).encode('utf-8')
    return (original[:start] + '\n\nStatus: Accepted' + original[start:]).encode('utf-8')


def accepted_sources(repo, data):
    """{path: bytes} of every goal source file as the owner's acceptance would leave it."""
    patched = {}
    for goal in data.get('goals') or []:
        source = goal.get('source')
        if not isinstance(source, str) or '#' not in source or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', source):
            sys.exit(f'{goal.get("id")}: a proposed goal needs a local source path#heading; no write')
        name, _, anchor = source.partition('#')
        path = Path(name)
        if path.is_absolute() or '..' in path.parts:
            sys.exit(f'{goal.get("id")}: nonlocal source {source}; no write')
        blob = patched.get(path.as_posix()) or checked_bytes(Path(repo) / path)
        if blob is None:
            sys.exit(f'{goal.get("id")}: missing source {name}; write the goal\'s section first; no write')
        new = accept_section(blob, anchor)
        if new is None:
            sys.exit(f'{goal.get("id")}: source {source} is missing or has conflicting Status lines; no write')
        patched[path.as_posix()] = new
    return patched


def ask_owner(repo, data, todo_name, *, write):
    """The one owner question, kept between docs-sync's markers under BLOCKERS.md's Active."""
    tasks = [t for t in data['tasks'] if t.get('status') not in ('done', 'superseded')]
    goals = '\n'.join(f'  - {g["id"]} — {g.get("title", "")} ({g["source"]}; '
                      f'{sum(1 for t in tasks if t.get("goal") == g["id"])} task(s))' for g in data['goals'])
    block = (f'{ASK_START}\n\n### Q-ACCEPT-GOALS — USER_DECISION — effort decision — unblocks {len(tasks)}\n\n'
             f'- Task: accept the drafted goals so {todo_name} becomes an executable backlog\n'
             f'- Needs: these goals are drafted, not accepted; no runner can start their tasks until you accept them:\n'
             f'{goals}\n'
             f'- Since: {datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")}\n'
             f'- Answer: "yes" accepts them all: run `goals.py accept <repo>`, which marks each source section '
             f'`Status: Accepted` and initializes goals.json from {PROPOSED}. To change a goal first, edit '
             f'{PROPOSED} or its section and run `goals.py propose` again.\n\n{ASK_END}\n')
    path = Path(repo) / 'BLOCKERS.md'
    text = path.read_text(encoding='utf-8') if path.exists() else (
        '# External input blockers\n\nOnly confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here.\n\n'
        '## Active\n\n## Resolved\n\nNone.\n')
    if ASK_START in text and ASK_END in text:
        head, rest = text.split(ASK_START, 1)
        text = head + block + rest.split(ASK_END, 1)[1].lstrip('\n')
    elif re.search(r'^## Active[ \t]*$', text, re.M):
        text = re.sub(r'^## Active[ \t]*\n', lambda m: m[0] + '\n' + block, text, count=1, flags=re.M)
    else:
        text = text.rstrip('\n') + '\n\n## Active\n\n' + block
    write(path, text)


def retire_question(repo, *, write):
    path = Path(repo) / 'BLOCKERS.md'
    text = path.read_text(encoding='utf-8') if path.exists() else ''
    if ASK_START in text and ASK_END in text:
        head, rest = text.split(ASK_START, 1)
        write(path, head + rest.split(ASK_END, 1)[1].lstrip('\n'))


def propose(a, *, writes):
    """First index without accepted sources: check the draft exactly as init will once the
    owner accepts it, save it and ask the owner once in BLOCKERS.md. Approves nothing."""
    atomic_write, TRANSACTION = writes.write, writes.transaction
    repo = Path(a.repo)
    blob = checked_bytes(Path(a.intent))
    if blob is None:
        sys.exit('missing intent file; no write')
    data = parse_ledger(blob)
    if (repo / 'TODO.md').exists() is False and not a.todo_file:
        sys.exit('missing TODO.md; supply complete task bodies with --todo-file; no write')
    initialize(argparse.Namespace(repo=a.repo, intent=a.intent, todo_file=a.todo_file,
                                  sources=accepted_sources(repo, data), dry_run=True), writes=writes)
    if not (repo / 'TODO.md').exists():
        atomic_write(repo / 'TODO.md', checked_bytes(Path(a.todo_file)).decode('utf-8'), expected_bytes=None)
        TRANSACTION.set((repo, revision(repo)))  # this command's own write
    (repo / PROPOSED).parent.mkdir(parents=True, exist_ok=True)
    atomic_write(repo / PROPOSED, blob.decode('utf-8'))
    ask_owner(repo, data, 'TODO.md', write=atomic_write)
    tasks = [t['id'] for t in data['tasks'] if t.get('status') not in ('done', 'superseded')]
    print(json.dumps({'state': 'awaiting_acceptance', 'goals': [g['id'] for g in data['goals']], 'tasks': tasks,
                      'draft': PROPOSED, 'question': 'BLOCKERS.md#Q-ACCEPT-GOALS'}))


def accept(a, *, writes):
    """The owner accepted the proposal: mark its source sections Accepted, initialize from it,
    then format, render, and retire the draft and its question. Run only on the owner's answer."""
    atomic_write, TRANSACTION = writes.write, writes.transaction
    repo = Path(a.repo)
    draft = repo / PROPOSED
    blob = checked_bytes(draft)
    if blob is None:
        sys.exit(f'no proposal at {PROPOSED}; run propose first; no write')
    patched = accepted_sources(repo, parse_ledger(blob))
    originals = {name: checked_bytes(repo / name) for name in patched}
    for name, new in patched.items():
        atomic_write(repo / name, new.decode('utf-8'), expected_bytes=originals[name])
    TRANSACTION.set((repo, revision(repo)))  # each step below guards against writers other than this one
    try:
        initialize(argparse.Namespace(repo=a.repo, intent=str(draft), todo_file=None), writes=writes)
    except SystemExit:
        for name, old in originals.items():
            if checked_bytes(repo / name) == patched[name]:
                atomic_write(repo / name, old.decode('utf-8'))
        raise
    TRANSACTION.set((repo, revision(repo)))
    data = load(repo)
    dump(repo, data, write=atomic_write)
    TRANSACTION.set((repo, revision(repo)))
    render(repo, normalize(load(repo)), write=atomic_write)
    TRANSACTION.set((repo, revision(repo)))
    draft.unlink()
    retire_question(repo, write=atomic_write)
    print(f'ok accepted {len(data["goals"])} goal(s); goals.json initialized; run validate and backlog-check')
