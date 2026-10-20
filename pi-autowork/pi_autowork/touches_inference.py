"""Touches inference for pi-autowork: find runnable tasks without Touches, record a
proposed list in TODO.md in the task's own field style, and widen a list the runner
recorded itself. Touches is a scheduling hint only: parallel dispatch runs tasks
whose Touches overlap after independent ones and never holds a task for it; overlap
is settled by merging in priority order, and a real conflict goes to the merge
resolver.

  touches_inference.py missing REPO TOOLSET LIMIT   -> JSON [{"id", "title"}], priority order
  touches_inference.py apply REPO TOOLSET TASK PATHS -> exit 0 when recorded and read back
  touches_inference.py widen REPO TOOLSET TASK RECORDED EXTRA
      -> add EXTRA paths, only while the task's Touches still equal RECORDED (what the
         runner inferred), so a list a person wrote or edited is never changed this way
  touches_inference.py grant REPO TOOLSET TASK EXTRA
      -> add at most three exact files a worker named to Touches a person wrote, once,
         and note it in the entry; prints the added paths
"""
import json
from pathlib import Path
import re
import sys

COORDINATOR = {'TODO.md', 'TODO.archive.md', 'goals.json', 'CHANGELOG.md'}


def modules(toolset):
    sys.path.insert(0, str(Path(toolset) / 'skills/autowork/scripts'))
    sys.path.insert(0, str(Path(toolset) / 'skills/docs-sync/scripts'))
    import goals
    import parallel_dispatch
    return goals, parallel_dispatch


def missing(repo, toolset, limit):
    _, dispatch = modules(toolset)
    try:
        contracts = dispatch.contracts(Path(repo))
    except dispatch.execution.PriorityDriftError:
        print('[]')  # the runner's dispatch records the new order first; no proposals until then
        return
    rows = [{'id': t['id'], 'title': t.get('title', '')} for t in contracts
            if not t['fields'].get('Touches', '').strip()]
    print(json.dumps(rows[:limit]))


def clean(paths):
    items = [p.strip().strip('`') for p in paths.split(',')]
    items = [p for p in items if p]
    for p in items:
        if p.startswith('/') or '..' in Path(p).parts or p.startswith('~'):
            raise ValueError(f'not a repository-relative path: {p}')
        if p.rstrip('/') in COORDINATOR:
            raise ValueError(f'coordinator-owned file: {p}')
    if not items:
        raise ValueError('no paths')
    return ', '.join(dict.fromkeys(items))


def entry(goals, text, task):
    entries = goals.task_bodies(text).get(task) or []
    if len(entries) != 1:
        raise ValueError(f'{task}: expected one TODO entry, found {len(entries)}')
    body = entries[0][0]
    start = text.find(body)
    if start < 0 or text.find(body, start + 1) >= 0:
        raise ValueError(f'{task}: entry text is not unique in TODO.md')
    return body, start


def apply(repo, toolset, task, paths):
    goals, _ = modules(toolset)
    paths = clean(paths)
    todo = Path(repo) / 'TODO.md'
    text = todo.read_bytes().decode('utf-8')
    body, start = entry(goals, text, task)
    scope = re.search(r'^([ \t]*(?:[-*][ \t]+)?)(?:\*\*)?Scope:', body, re.M)
    if not scope:
        raise ValueError(f'{task}: no Scope field to sit beside')
    prefix = scope.group(1)
    before = body[:scope.start()]
    # Match this field's newline, not the first line in a mixed-style document.
    end = body.find('\n', scope.end())
    newline = '\r\n' if end > 0 and body[end - 1] == '\r' else '\n'
    spaced = prefix.strip() == '' and before.endswith(newline * 2)
    line = f'{prefix}Touches: {paths}{newline}' + (newline if spaced else '')
    new_body = before + line + body[scope.start():]
    new_text = text[:start] + new_body + text[start + len(body):]
    read = goals.task_bodies(new_text).get(task) or []
    if len(read) != 1 or goals.task_fields(read[0][0]).get('Touches', '').strip() != paths:
        raise ValueError(f'{task}: Touches did not read back')
    todo.write_bytes(new_text.encode('utf-8'))
    print(paths)


def widen(repo, toolset, task, recorded, extra):
    goals, _ = modules(toolset)
    todo = Path(repo) / 'TODO.md'
    text = todo.read_bytes().decode('utf-8')
    body, start = entry(goals, text, task)
    current = goals.task_fields(body).get('Touches', '').strip()
    if current != clean(recorded):
        raise ValueError(f'{task}: Touches changed since the runner recorded them; not widening')
    paths = clean(current + ', ' + extra)
    field = re.search(r'^([ \t]*(?:[-*][ \t]+)?(?:\*\*)?Touches:(?:\*\*)?[ \t]*)([^\r\n]*)', body, re.M)
    if not field or field.group(2).strip() != current:
        raise ValueError(f'{task}: Touches field not found in its entry')
    new_body = body[:field.start(2)] + paths + body[field.end(2):]
    new_text = text[:start] + new_body + text[start + len(body):]
    read = goals.task_bodies(new_text).get(task) or []
    if len(read) != 1 or goals.task_fields(read[0][0]).get('Touches', '').strip() != paths:
        raise ValueError(f'{task}: widened Touches did not read back')
    todo.write_bytes(new_text.encode('utf-8'))
    print(paths)


GRANTED = 'Touches widened by the runner from worker evidence'
GRANT_LIMIT = 3


def grant(repo, toolset, task, extra):
    """Widen Touches a person wrote, once, by at most three exact files a worker named
    (TOOLSET-152-d4). A glob, a directory, a coordinator file, a file another slot's
    task declares, or a second request is refused: it stays a question for the owner."""
    goals, dispatch = modules(toolset)
    plan = dispatch.parallel_plan
    todo = Path(repo) / 'TODO.md'
    text = todo.read_bytes().decode('utf-8')
    body, start = entry(goals, text, task)
    fields = goals.task_fields(body)
    if fields.get(GRANTED):
        raise ValueError(f'{task}: Touches were already widened once from worker evidence')
    current = fields.get('Touches', '').strip()
    if not current:
        raise ValueError(f'{task}: no Touches to widen')
    declared = plan.paths(current)
    wanted = [p for p in dict.fromkeys(plan.paths(clean(extra))) if p not in declared]
    if not wanted:
        raise ValueError(f'{task}: the requested files are already in Touches')
    if len(wanted) > GRANT_LIMIT:
        raise ValueError(f'{task}: {len(wanted)} files requested; at most {GRANT_LIMIT} are widened without a person')
    for path in wanted:
        if path.endswith('/') or any(c in path for c in '*?['):
            raise ValueError(f'{task}: {path} is not one exact file')
        if path in COORDINATOR or Path(path).name == 'BLOCKERS.md':
            raise ValueError(f'coordinator-owned file: {path}')
    common = Path(dispatch.state.common_dir(Path(repo)))
    bodies = goals.task_bodies(text)
    for slot in dispatch.state.slots(common):
        other = slot['task_id']
        if other == task or slot['state'] in ('closed', 'released'):
            continue
        found = bodies.get(other) or []
        theirs = goals.task_fields(found[0][0]).get('Touches', '').strip() if len(found) == 1 else ''
        # A slot whose task declares no Touches may write anywhere: nothing is free beside it.
        if not theirs or plan._shared(wanted, plan.paths(theirs)):
            raise ValueError(f'{task}: {", ".join(wanted)} may belong to {other}, which has a live or held slot')
    paths = ', '.join(declared + wanted)
    field = re.search(r'^([ \t]*(?:[-*][ \t]+)?(?:\*\*)?)Touches:(?:\*\*)?[ \t]*([^\r\n]*)(\r?\n|$)', body, re.M)
    if not field or field.group(2).strip() != current:
        raise ValueError(f'{task}: Touches field not found in its entry')
    note = f'{field.group(1).removesuffix("**")}{GRANTED}: {", ".join(wanted)}{field.group(3) or chr(10)}'
    new_body = body[:field.start(2)] + paths + field.group(3) + note + body[field.end():]
    new_text = text[:start] + new_body + text[start + len(body):]
    read = goals.task_bodies(new_text).get(task) or []
    if len(read) != 1 or goals.task_fields(read[0][0]).get('Touches', '').strip() != paths:
        raise ValueError(f'{task}: widened Touches did not read back')
    todo.write_bytes(new_text.encode('utf-8'))
    print(', '.join(wanted))


if __name__ == '__main__':
    try:
        command, repo, toolset = sys.argv[1:4]
        if command == 'missing':
            missing(repo, toolset, int(sys.argv[4]))
        elif command == 'apply':
            apply(repo, toolset, sys.argv[4], sys.argv[5])
        elif command == 'widen':
            widen(repo, toolset, *sys.argv[4:7])
        elif command == 'grant':
            grant(repo, toolset, *sys.argv[4:6])
        else:
            raise ValueError('unknown command')
    except (ValueError, IndexError, OSError) as error:
        print(f'touches_inference: {error}', file=sys.stderr)
        sys.exit(1)
