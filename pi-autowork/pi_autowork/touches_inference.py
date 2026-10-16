"""Touches inference for pi-autowork: find runnable tasks without Touches, record a
proposed list in TODO.md in the task's own field style, and widen a list the runner
recorded itself. The engine enforces Touches: a worker's changed files must stay
inside it or its integration is held.

  touches_inference.py missing REPO TOOLSET LIMIT   -> JSON [{"id", "title"}], priority order
  touches_inference.py apply REPO TOOLSET TASK PATHS -> exit 0 when recorded and read back
  touches_inference.py widen REPO TOOLSET TASK RECORDED EXTRA
      -> add EXTRA paths, only while the task's Touches still equal RECORDED (what the
         runner inferred), so a list a person wrote or edited is never changed
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


if __name__ == '__main__':
    try:
        command, repo, toolset = sys.argv[1:4]
        if command == 'missing':
            missing(repo, toolset, int(sys.argv[4]))
        elif command == 'apply':
            apply(repo, toolset, sys.argv[4], sys.argv[5])
        elif command == 'widen':
            widen(repo, toolset, *sys.argv[4:7])
        else:
            raise ValueError('unknown command')
    except (ValueError, IndexError, OSError) as error:
        print(f'touches_inference: {error}', file=sys.stderr)
        sys.exit(1)
