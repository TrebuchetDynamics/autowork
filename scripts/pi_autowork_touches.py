"""Touches: helpers for pi-autowork.sh: find runnable tasks without Touches and record a
proposed list in TODO.md in the task's own field style. The engine then enforces it:
a worker's changed files must stay inside Touches or its integration is held.

  pi_autowork_touches.py missing REPO TOOLSET LIMIT   -> JSON [{"id", "title"}], priority order
  pi_autowork_touches.py apply REPO TOOLSET TASK PATHS -> exit 0 when recorded and read back
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
    rows = [{'id': t['id'], 'title': t.get('title', '')} for t in dispatch.contracts(Path(repo))
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


def apply(repo, toolset, task, paths):
    goals, _ = modules(toolset)
    paths = clean(paths)
    todo = Path(repo) / 'TODO.md'
    text = todo.read_text()
    entries = goals.task_bodies(text).get(task) or []
    if len(entries) != 1:
        raise ValueError(f'{task}: expected one TODO entry, found {len(entries)}')
    body = entries[0][0]
    start = text.find(body)
    if start < 0 or text.find(body, start + 1) >= 0:
        raise ValueError(f'{task}: entry text is not unique in TODO.md')
    scope = re.search(r'^([ \t]*(?:[-*][ \t]+)?)(?:\*\*)?Scope:', body, re.M)
    if not scope:
        raise ValueError(f'{task}: no Scope field to sit beside')
    prefix = scope.group(1)
    before = body[:scope.start()]
    spaced = prefix.strip() == '' and before.endswith('\n\n')  # fields separated by blank lines
    line = f'{prefix}Touches: {paths}\n' + ('\n' if spaced else '')
    new_body = before + line + body[scope.start():]
    new_text = text[:start] + new_body + text[start + len(body):]
    read = goals.task_bodies(new_text).get(task) or []
    if len(read) != 1 or goals.task_fields(read[0][0]).get('Touches', '').strip() != paths:
        raise ValueError(f'{task}: Touches did not read back')
    todo.write_text(new_text)
    print(paths)


if __name__ == '__main__':
    try:
        command, repo, toolset = sys.argv[1:4]
        if command == 'missing':
            missing(repo, toolset, int(sys.argv[4]))
        elif command == 'apply':
            apply(repo, toolset, sys.argv[4], sys.argv[5])
        else:
            raise ValueError('unknown command')
    except (ValueError, IndexError, OSError) as error:
        print(f'pi_autowork_touches: {error}', file=sys.stderr)
        sys.exit(1)
