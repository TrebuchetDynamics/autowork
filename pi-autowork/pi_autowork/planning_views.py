"""Plain-text projections shared by planning CLI and Textual. No model or writes."""
from collections import deque


def event_text(event):
    kind = event.get('type')
    if kind == 'message_update':
        update = event.get('assistantMessageEvent', {})
        return update.get('delta', '') if update.get('type') == 'text_delta' else ''
    if kind == 'tool_execution_start':
        return '\n[Reading: ' + str(event.get('toolName', 'tool')) + ']\n'
    if kind in ('auto_retry_start', 'auto_compaction_start'):
        return '\n[' + kind.replace('_', ' ') + ']\n'
    if kind == 'extension_ui_request' and event.get('method') == 'notify':
        return '\n' + str(event.get('message', '')) + '\n'
    return ''


def history_text(messages):
    return '\n\n'.join(str(m.get('role', 'message')).capitalize() + '\n' + str(m.get('content', ''))
                       for m in messages)


def preview_text(preview):
    errors = preview.get('errors', [])
    return ('UNACCEPTED PROPOSAL — review every change before Apply\n'
            'Review revision: ' + str(preview.get('revision', 'unavailable')) + '\n'
            'Validation: ' + ('valid' if preview.get('valid') else 'not valid') + '\n'
            + ''.join('Error: ' + str(error) + '\n' for error in errors)
            + 'Files: ' + ', '.join(preview.get('files', [])) + '\n\n'
            + preview.get('diff', '(no changes)'))


def roadmap_text(roadmap):
    """An adjacency diagram plus topological waves; never calls selection admission.

    Kahn's algorithm avoids recursive walks on deep/cyclic imported task graphs.
    Closed tasks remain visible as history, not proof of verified dependencies.
    """
    tasks = {t['id']: t for t in roadmap.get('tasks', [])}
    goals = roadmap.get('goals', [])
    lines = ['ROADMAP — ' + str(roadmap.get('revision', 'unknown')),
             'Dependency order is not execution eligibility or verification.']
    lines.extend('Unavailable: ' + str(e) for e in roadmap.get('errors', []))
    groups = [(g['id'], g.get('title', ''), g.get('status', '')) for g in goals]
    known = {g[0] for g in groups}
    groups.extend((g, 'Unassigned / unknown goal', '')
                  for g in sorted({str(t.get('goal') or '(none)') for t in tasks.values()} - known))
    for gid, title, status in groups:
        lines.append(f'\n{gid} · {title} [{status}]')
        for tid, task in tasks.items():
            if str(task.get('goal') or '(none)') != gid:
                continue
            lines.append(f'  ├─ {tid} · {task.get("title", "")} '
                         f'[{task.get("status", "unknown")} / {task.get("section", "")}]')
            for dep in task.get('depends_on', []):
                marker = '' if dep in tasks else ' (missing)'
                lines.append(f'  │    ← {dep}{marker}')
    degree = {tid: len(set(t.get('depends_on', [])) & tasks.keys()) for tid, t in tasks.items()}
    consumers = {tid: [] for tid in tasks}
    for tid, task in tasks.items():
        for dep in set(task.get('depends_on', [])) & tasks.keys():
            consumers[dep].append(tid)
    queue = deque(sorted(tid for tid in tasks if degree[tid] == 0))
    waves = []
    while queue:
        wave = [queue.popleft() for _ in range(len(queue))]
        waves.append(wave)
        for tid in wave:
            for other in consumers[tid]:
                degree[other] -= 1
                if not degree[other]:
                    queue.append(other)
    lines.append('\nDependency waves (including closed history):')
    lines.extend(f'  {i + 1}. ' + ', '.join(wave) for i, wave in enumerate(waves))
    cyclic = sorted(tid for tid, count in degree.items() if count)
    if cyclic:
        lines.append('Cycle or downstream of a cycle: ' + ', '.join(cyclic))
    if not tasks:
        lines.append('(no tasks)')
    return '\n'.join(lines)
