"""Plan lossless TODO archival; the caller owns locking and archive-first writes."""
from collections import Counter
from pathlib import Path
import os
import re
import sys
from urllib.parse import quote, unquote


DEFAULT = 'TODO.archive.md'
LEGACY = ('todo.archive.md', 'docs/TODO-archive.md')
IDENTIFIER = r'[A-Za-z0-9][A-Za-z0-9_-]*'
TASK_HEADING = r'(' + IDENTIFIER + r')(?:[ \t]+[—–-][ \t]+|:[ \t]+)'


def local_archive(repo, name):
    path = Path(unquote(name.strip('<>')).split('#', 1)[0])
    if (path.is_absolute() or '..' in path.parts or not path.parts
            or path.as_posix() in ('TODO.md', 'goals.json') or path.suffix.lower() != '.md'):
        sys.exit('archive must be a separate Markdown file inside the repository')
    for part in (path, *path.parents):
        if (repo / part).is_symlink():
            sys.exit('refusing symlink archive path')
    return path


def archive_owner(repo, prose):
    linked = set()
    for label, target in re.findall(r'\[([^\]\n]+)\]\(([^)\n]+)\)', prose):
        if re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', target) or target.startswith('#'):
            continue
        if (re.search(r'archive|history|completed tasks', label, re.I)
                or re.search(r'todo[.-]archive\.md(?:#|$)', target, re.I)):
            linked.add(local_archive(repo, target))
    if len(linked) > 1:
        sys.exit('multiple TODO archives linked; choose one canonical history owner; no write')
    if linked:
        return linked.pop()
    existing = [Path(name) for name in (DEFAULT, *LEGACY)
                if (repo / name).exists() or (repo / name).is_symlink()]
    if len(existing) > 1:
        sys.exit('multiple TODO archives exist; link the canonical history owner; no write')
    return local_archive(repo, str(existing[0]) if existing else DEFAULT)


def entries(text, prose, known_ids):
    """Return exact top-level checkbox/heading spans, excluding fenced examples."""
    headings = list(re.finditer(r'^(#{1,6})[ \t]+([^\r\n]+)\r?$', prose, re.M))
    boxes = list(re.finditer(r'^[-*] \[([ xX])\][ \t]+(?:\*\*)?`?(' + IDENTIFIER +
                             r')`?(?:\*\*)?(?=\s|:)', prose, re.M))
    task_headings = {h.start(): re.match(TASK_HEADING, h[2]) for h in headings if len(h[1]) >= 3}
    task_headings = {start: task for start, task in task_headings.items() if task}
    known_headings = {start for start, task in task_headings.items() if task[1] in known_ids}
    records = []
    for index, match in enumerate(headings):
        task = task_headings.get(match.start())
        if not task:
            continue
        end = next((h.start() for h in headings[index + 1:] if len(h[1]) <= len(match[1])), len(text))
        first_box = next((b for b in boxes if match.start() < b.start() < end), None)
        # A separately closed heading-only task can precede an independent
        # checkbox task. An empty/mismatched wrapper cannot use this exception.
        if (first_box is not None and first_box[2] != task[1]
                and explicitly_closed(prose[match.start():first_box.start()], None)):
            end = first_box.start()
        records.append((match.start(), end, task[1], None))
    for index, match in enumerate(boxes):
        end = boxes[index + 1].start() if index + 1 < len(boxes) else len(text)
        # A heading at or above the level of the group enclosing this checkbox is a
        # sibling group, not this task's content: archiving must not carry it away.
        group = next((h for h in reversed(headings) if h.start() < match.start()
                      and h.start() not in task_headings), None)
        group_level = len(group[1]) if group is not None else 2
        # Only a known task can end this body. An unknown task-shaped heading
        # overlaps it instead: prepare() retains the ambiguous unit intact.
        # This protects both unregistered tasks and titled evidence subsections.
        end = min(end, next((h.start() for h in headings if h.start() > match.start()
                             and (len(h[1]) <= max(2, group_level) or h.start() in known_headings)),
                            len(text)))
        records.append((match.start(), end, match[2], match[1]))
    # A task heading immediately followed by its own checkbox is one source
    # unit, not two tasks. Keep other overlaps visible to prepare(): a different
    # ID, intervening metadata or another task must never authorize a partial move.
    combined, consumed = [], set()
    for start, end, tid, mark in records:
        if mark is not None:
            continue
        heading = next(h for h in headings if h.start() == start)
        children = [row for row in records if row[3] is not None and start < row[0] < end]
        if (len(children) == 1 and children[0][2] == tid
                and children[0][1] <= end
                and not text[heading.end():children[0][0]].strip()):
            child = children[0]
            combined.append((start, end, tid, child[3]))
            consumed.add(child[0])
        else:
            combined.append((start, end, tid, mark))
    combined.extend(row for row in records if row[3] is not None and row[0] not in consumed)
    return sorted(combined), headings


def rebased_references(repo, owner, block):
    """Keep original source bytes and add navigable links for a nested archive."""
    if owner.parent == Path('.'):
        return ''
    links = []
    for label, ref in re.findall(r'\[([^\]\n]+)\]\(([^)\n]+)\)', block):
        name, separator, fragment = ref.strip('<>').partition('#')
        if not name or re.match(r'^[a-zA-Z][a-zA-Z0-9+.-]*:', name) or name.startswith('/'):
            continue
        path = (repo / unquote(name)).resolve()
        if not path.is_relative_to(repo.resolve()):
            continue
        target = quote(os.path.relpath(path, repo / owner.parent), safe='/.-_') + separator + fragment
        link = f'[{label}]({target})'
        if link not in links:
            links.append(link)
    return 'References from this archive: ' + ', '.join(links) + '\n\n' if links else ''


def explicitly_closed(body, mark):
    statuses = re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?Status:(?:\*\*)?[ \t]*([^\r\n]*)', body, re.M | re.I)
    closed_status = len(statuses) == 1 and re.match(r'done\b', statuses[0], re.I)
    closed = mark in ('x', 'X') if mark is not None else bool(closed_status)
    return bool(closed and (not statuses or closed_status)
                and not re.search(r'^[ \t]*[-*] \[ \]', body, re.M))


def prepare(repo, data, text, *, mask, checked_bytes, verified_tasks=(), boundaries=()):
    """Select closed/done or explicitly superseded bodies; never infer task completion."""
    repo = Path(repo)
    prose = re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\r\n]', ' ', m[0]), mask(text), flags=re.S)
    verified = set(verified_tasks)
    if data is not None and verified:
        sys.exit('--verified-tasks is only for repositories without goals.json; reconcile the ledger first')
    tasks = {t['id']: t for t in data['tasks']} if data is not None else {}
    records, headings = entries(text, prose, set(tasks) | verified)
    records = [(start, min([end] + [point for point in boundaries if point > start]), tid, mark)
               for start, end, tid, mark in records]
    # Task sources may link to archive code, policies or another task's history.
    # Only navigation outside task bodies can designate the live TODO's owner.
    navigation = list(prose)
    for start, end, _, _ in records:
        navigation[start:end] = re.sub(r'[^\r\n]', ' ', prose[start:end])
    navigation = ''.join(navigation)
    overlapping = set()
    for index, row in enumerate(records):
        for following in range(index + 1, len(records)):
            if records[following][0] >= row[1]:
                break
            overlapping.update((index, following))
    selected, retained = [], []
    for index, (start, end, tid, mark) in enumerate(records):
        body = prose[start:end]
        closed = explicitly_closed(body, mark)
        task = tasks.get(tid, {})
        superseded = bool(task.get('status') == 'superseded' and task.get('superseded_by')
                          and task.get('supersession_reason', '').strip())
        eligible = (task.get('status') == 'done' or superseded) if data is not None else tid in verified
        if (not closed and not superseded) or not eligible or index in overlapping:
            if eligible or closed:
                retained.append(tid)
            continue
        section = next((h[2] for h in reversed(headings) if h.start() < start and len(h[1]) <= 2), 'Tasks')
        block = text[start:end]
        if superseded:
            block = ('Disposition: Superseded; not completed\nSuccessors: ' +
                     ', '.join(task['superseded_by']) + '\nReason: ' + task['supersession_reason'] +
                     '\nOriginal task and unchecked acceptance retained below.\n\n' + block)
        selected.append((start, end, tid, section, block))
    unselected = verified - {row[2] for row in selected}
    if unselected:
        if unselected & {row[2] for row in records}:
            sys.exit('verified task is not explicitly closed or has ambiguous boundaries in TODO.md; no write')
        # An exact command retry after success has no live body left to move.
        # Only recognize closed historical entries; never use an ID to discard live text.
        owner = archive_owner(repo, navigation)
        history = (checked_bytes(repo / owner) or b'').decode('utf-8')
        historical = mask(history)
        archived, _ = entries(history, historical, unselected)
        closed_ids = {tid for start, end, tid, mark in archived
                      if explicitly_closed(historical[start:end], mark)}
        if unselected - closed_ids:
            sys.exit('verified task is absent from TODO.md and closed archive history; no write')
    if not selected:
        return {'text': text, 'moved': [], 'retained': sorted(set(retained)), 'archive': None}
    owner = archive_owner(repo, navigation)
    path = repo / owner
    before = checked_bytes(path)
    history = (before or b'').decode('utf-8')
    needed = Counter(row[4] for row in selected)
    missing = {block: max(0, count - history.count(block)) for block, count in needed.items()}
    additions = ''
    for _, _, _, section, block in selected:
        if missing[block]:
            additions += ('\n\n<!-- archived from TODO.md -->\n\nSource section: ' + section + '\n\n' +
                          rebased_references(repo, owner, block) + block)
            missing[block] -= 1
    has_superseded = any(tasks.get(row[2], {}).get('status') == 'superseded' for row in selected)
    after = (history or ('# Task history\n' if has_superseded else '# Completed tasks\n')) + additions
    if any(after.count(block) < count for block, count in needed.items()):
        sys.exit('archive conservation check failed; no write')
    live, cursor = [], 0
    for start, end, _, _, _ in selected:
        live.append(text[cursor:start])
        cursor = end
    live.append(text[cursor:])
    result = ''.join(live)
    if not re.search(r'\]\(<?' + re.escape(quote(owner.as_posix(), safe='/.-_')) + r'(?:>|#|\))', result):
        label = 'Task history' if has_superseded else 'Completed tasks'
        link = '[' + label + '](' + quote(owner.as_posix(), safe='/.-_') + ')\n\n'
        title = re.search(r'^#[ \t]+[^\r\n]*(?:\r?\n|$)', result, re.M)
        at = title.end() if title else 0
        result = result[:at] + '\n' + link + result[at:]
    return {'text': result, 'moved': [row[2] for row in selected],
            'retained': sorted(set(retained)), 'archive': owner.as_posix(),
            'path': path, 'before': before, 'after': after}
