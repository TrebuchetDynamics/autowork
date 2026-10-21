"""TODO text parsing, block edits, coverage rendering and archive orchestration."""
from datetime import date
import html
import importlib.util
import re
import sys
from pathlib import Path

from goals_ledger import (
    checked_bytes, errors, normalize,
)


BEGIN, END = '<!-- goals:coverage:begin -->', '<!-- goals:coverage:end -->'


def todo_text(repo):
    blob = checked_bytes(Path(repo) / 'TODO.md')
    return blob.decode('utf-8') if blob is not None else ''


def task_blocks(text):
    """Movable task blocks: an ID heading or checkbox up to the next block in its group.

    A group is a `##` section, or a heading inside it that is not a task's own ID
    heading (for example `### P2 — Parity`). Blocks never move across a group heading.
    """
    prose = task_prose(text)
    marks = list(re.finditer(TASK_MARK, prose, re.M))
    own = {block_start(prose, mark) for mark in marks}
    sections, section, level = [], '', 2
    for m in re.finditer(r'^(#{2,6})[ \t]+(.+)$', prose, re.M):
        if len(m[1]) == 2:
            section, level = m[2].strip(), 2
            sections.append((m.start(), section))
        elif m.start() not in own and len(m[1]) <= max(3, level):
            # A sibling or parent group. A deeper heading (#### Evidence) is the
            # preceding task's own subsection and moves with it.
            level = len(m[1])
            sections.append((m.start(), f'{section} / {m[2].strip()}'))
    blocks = []
    for mark in marks:
        region = max((s for s in sections if s[0] < mark.start()), default=(0, ''))
        start = block_start(prose, mark, region[0])
        blocks.append({'id': mark[2], 'mark': mark[1], 'start': start, 'region': region})
    for index, block in enumerate(blocks):
        following = blocks[index + 1] if index + 1 < len(blocks) else None
        ends = [s for s, _ in sections if s > block['start']]
        region_end = ends[0] if ends else len(text)
        block['end'] = following['start'] if following and following['region'] == block['region'] \
            and following['start'] < region_end else region_end
        chunk = text[block['start']:block['end']]
        core = chunk.rstrip()
        block['core'], block['sep'] = core, chunk[len(core):]
        inner = task_prose(chunk).split('\n')[1:]
        # Deeper subsections belong to the task; a group-level heading here is ambiguous.
        block['foreign_heading'] = any(re.match(r'#{1,3}[ \t]', line) for line in inner)
    return blocks


def render_text(repo, data, text=None):
    def cell(value):
        return (html.escape(value, quote=False).replace('|', '&#124;').replace('`', '&#96;')
                .replace('\r\n', '\n').replace('\r', '\n').replace('\n', '<br>'))

    tasks = {t['id']: t for t in data['tasks']}
    rows = ['| Goal | Status | Evidence | Task |', '| --- | --- | --- | --- |']
    def evidence_cell(entry):
        if 'summary' in entry:
            summary = cell(entry['summary'])
            if entry.get('task') and entry.get('archive'):
                # Archive links are authored by evidence(), not arbitrary scratch refs.
                from urllib.parse import quote
                anchor = entry.get('anchor', entry['task'].lower())
                target = quote(entry['archive'], safe='/.-_') + ('#' + quote(anchor, safe='-_.') if anchor else '')
                return summary + f" ([{cell(entry['task'])}]({target}))"
            return summary
        return (cell(entry['kind']) + (' (redacted historical evidence)' if entry.get('redacted') else '')
                + f" <code>{cell(entry['ref'])}</code> → {cell(entry['result'])}")

    for g in data['goals']:
        compact = [e for e in g['evidence'] if 'summary' in e and e.get('coverage_current') is True]
        # Keep an explicit identity: canonical evidence sorting is not recency.
        # Untouched legacy goals retain their existing rows and full refs.
        visible = compact if compact else g['evidence']
        ev = '; '.join(evidence_cell(e) for e in visible) or '—'
        open_t = [t for t in g['tasks'] if tasks.get(t, {}).get('status') not in ('done', 'superseded')]
        rows.append(f"| {cell(g['id'])}: {cell(g['title'])} | {cell(g['status'])} | {ev} | {cell(', '.join(open_t)) or '—'} |")
    block = '\n'.join([BEGIN, '', 'Generated from `goals.json` by `goals.py render`. `met` requires an executed, passing check.', '', *rows, '', END])
    todo = Path(repo) / 'TODO.md'
    if text is None:
        text = todo.read_bytes().decode('utf-8') if todo.exists() else '# TODO\n\n## Goal coverage\n\n'
    prose = markdown_prose(text)
    begins = list(re.finditer(re.escape(BEGIN), prose))
    ends = list(re.finditer(re.escape(END), prose))
    headings = list(re.finditer(r'^##[ \t]+Goal coverage[ \t]*\r?$', prose, re.M))
    if begins or ends:
        if len(begins) != 1 or len(ends) != 1 or begins[0].start() >= ends[0].start():
            sys.exit('ambiguous coverage markers in TODO.md; reconcile their boundaries; no write')
        text = text[:begins[0].start()] + block + text[ends[0].end():]
    elif headings:
        if len(headings) != 1:
            sys.exit('multiple Goal coverage sections in TODO.md; choose the maintained section; no write')
        heading = headings[0]
        # Replace only up to the next heading of any level: a following `### Decisions log`
        # is owner content, not part of the legacy table, and must stay byte-identical.
        nxt = re.search(r'\n#{1,6}[ \t]+', prose[heading.end():])
        rest = text[heading.end() + nxt.start():] if nxt else '\n'
        text = text[:heading.end()] + '\n\n' + block + '\n' + rest
    else:
        text = text + '\n\n## Goal coverage\n\n' + block + '\n'
    return text


def archive_tasks(repo, data, *, render_coverage=False, verified_tasks=(), write):
    """Save and verify history before removing live bodies, under coordination()."""
    spec = importlib.util.spec_from_file_location('docs_sync_todo_archive', Path(__file__).with_name('todo_archive.py'))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    if data is not None:
        problems = errors(normalize(data), allow_pending_evidence=True)
        if problems:
            sys.exit('\n'.join(problems))
    todo = Path(repo) / 'TODO.md'
    before = checked_bytes(todo)
    text = before.decode('utf-8') if before is not None else '# TODO\n\n'
    if data is not None:
        # Archival must not hide an invalid generated region inside a moved body.
        render_text(repo, data, text)
    plan = module.prepare(repo, data, text, mask=task_prose, checked_bytes=checked_bytes,
                          verified_tasks=verified_tasks,
                          boundaries=[m.start() for m in re.finditer(re.escape(BEGIN), markdown_prose(text))])
    output = render_text(repo, data, plan['text']) if render_coverage else plan['text']
    if plan['archive']:
        path = plan['path']
        path.parent.mkdir(parents=True, exist_ok=True)
        expected = plan['after'].encode('utf-8')
        if plan['before'] != expected:
            write(path, plan['after'], expected_bytes=plan['before'])
        if checked_bytes(path) != expected:
            sys.exit('archive verification failed; TODO.md retained; retry after reconciliation')
    if output.encode('utf-8') != before and (before is not None or render_coverage):
        write(todo, output, expected_bytes=before)
    return {key: plan[key] for key in ('moved', 'retained', 'archive')}


def render(repo, data, *, archive=True, write):
    if archive:
        return archive_tasks(repo, data, render_coverage=True, write=write)
    write(Path(repo) / 'TODO.md', render_text(repo, data))


def markdown_prose(text):
    """Mask fenced examples without changing offsets used for clerical repairs."""
    lines = []
    fence = None
    for line in text.splitlines(keepends=True):
        if fence is not None:
            lines.append(re.sub(r'[^\r\n]', ' ', line))
            if re.fullmatch(r' {0,3}' + re.escape(fence[0]) +
                            '{' + str(len(fence)) + r',}[ \t]*(?:\r?\n)?', line):
                fence = None
            continue
        opening = re.match(r' {0,3}(`{3,}|~{3,})([^\r\n]*)', line)
        if opening and not (opening[1][0] == '`' and '`' in opening[2]):
            fence = opening[1]
            lines.append(re.sub(r'[^\r\n]', ' ', line))
        else:
            lines.append(line)
    return ''.join(lines)


def heading_rows(text):
    """(anchor, start, end, level) of each Markdown heading in fence-masked text."""
    headings = []
    counts = {}
    for match in re.finditer(r'^(#{1,6})[ \t]+(.+?)[ \t]*#*[ \t]*\r?$', text, re.M):
        slug = re.sub(r'[^\w\- ]', '', match[2].lower()).replace(' ', '-')
        count = counts.get(slug, 0)
        counts[slug] = count + 1
        headings.append((slug + (f'-{count}' if count else ''), match.start(), match.end(), len(match[1])))
    return headings


def task_prose(text):
    """Ignore examples and generated coverage while retaining source offsets."""
    return re.sub(re.escape(BEGIN) + r'.*?' + re.escape(END),
                  lambda m: re.sub(r'[^\r\n]', ' ', m[0]), markdown_prose(text), flags=re.S)


CHECK_LABELS = ('Checks', 'Verification')


def task_checks(fields):
    """A task's verification commands; `Verification:` is an accepted spelling of `Checks:`."""
    present = [label for label in CHECK_LABELS if fields.get(label)]
    return fields[present[0]] if len(present) == 1 else None


def task_fields(body):
    """Read maintained fields, including continued Sources and header-inline Goal."""
    body = task_prose(body)
    matches = list(re.finditer(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):(?:\*\*)?[ \t]*', body, re.M))
    fields = {}
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(body)
        value = body[match.end():end].strip()
        if value:
            fields.setdefault(match[1], []).append(value)
    inline = re.match(r'^\s*[—–-]\s+Goal:[ \t]*(\S[^\n]*)', body)
    if inline:
        fields.setdefault('Goal', []).append(inline[1])
    return {label: values[0] for label, values in fields.items() if len(values) == 1}


TASK_MARK = r'^[-*] \[([ xX])\]\s+(?:\*\*)?`?([A-Za-z0-9][A-Za-z0-9_-]*)`?(?:\*\*)?(?=\s|:)'


def block_start(prose, mark, floor=0):
    """A task block begins at its own ID heading when one directly precedes the checkbox."""
    before = prose[floor:mark.start()].rstrip()
    last_line = before.rsplit('\n', 1)[-1]
    if re.match(r'#{3,6}[ \t]', last_line) and re.search(
            r'(?<![\w-])' + re.escape(mark[2]) + r'(?![\w-])', last_line):
        return floor + len(before) - len(last_line)
    return mark.start()


def task_bodies(text):
    """Only checkbox entries outside generated coverage are task contracts."""
    prose = task_prose(text)
    matches = list(re.finditer(TASK_MARK, prose, re.M))
    bodies = {}
    for i, match in enumerate(matches):
        # The next task's own ID heading belongs to that task, not this body's last field.
        end = block_start(prose, matches[i + 1], match.end()) if i + 1 < len(matches) else len(text)
        section_end = re.search(r'^##\s', prose[match.end():end], re.M)
        if section_end:
            end = match.end() + section_end.start()
        block = text[match.end():end]
        # Trim CRLF `\r` and trailing blanks so `## Now \r` names the ledger section `Now`.
        sections = re.findall(r'^##[ \t]+([^\r\n]*)', prose[:match.start()], re.M)
        section = sections[-1].strip() if sections else ''
        if section == 'Now / Next':
            explicit = re.findall(r'(?:^|\.\s+)Section:[ \t]*(Now|Next|Needs decision)(?=\.|\s*$)', prose[match.end():end], re.M)
            if len(explicit) == 1:
                section = explicit[0]
        bodies.setdefault(match[2], []).append((block, match[1], section))
    return bodies


def deferred_tasks(bodies):
    """Owner-answered deferrals from parsed TODO bodies, not unanswered decisions."""
    deferred = set()
    for task, entries in bodies.items():
        if len(entries) != 1:
            continue
        body, mark, section = entries[0]
        if section != 'Needs decision' or mark.lower() == 'x':
            continue
        decision = task_fields(body).get('Owner decision', '')
        stamp = re.search(r'\b(\d{4}-\d{2}-\d{2})\b', decision)
        if stamp:
            try:
                date.fromisoformat(stamp[1])
            except ValueError:
                continue
            deferred.add(task)
    return deferred


def move_block(text, task, step):
    """(new TODO.md text, '') with open task ``task`` swapped with the open task ``step`` places
    away in its own group (-1 up, 1 down), or (None, why it cannot move). Blocks never cross a
    group heading, and every block keeps its exact bytes."""
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    peers = [b for b in blocks if b['region'] == block['region'] and b['mark'] == ' ']
    index = peers.index(block) + step
    if not 0 <= index < len(peers):
        where = block['region'][1] or 'its section'
        return None, f'{task} is already {"first" if step < 0 else "last"} in {where}'
    other = peers[index]
    if block['foreign_heading'] or other['foreign_heading']:
        return None, f'{task} or {other["id"]} contains another heading; move it by hand'
    swap = {id(block): other, id(other): block}
    output, cursor = [], 0
    for b in blocks:
        output.append(text[cursor:b['start']] + swap.get(id(b), b)['core'] + b['sep'])
        cursor = b['end']
    new_text = ''.join(output) + text[cursor:]
    if sorted(b['core'] for b in blocks) != sorted(b['core'] for b in task_blocks(new_text)):
        return None, 'task block bytes would change'
    return new_text, ''


def set_field(text, task, label, value):
    """(new TODO.md text, '') with ``label: value`` the one such line of open task ``task``'s entry,
    replacing an earlier one, or (None, why). Two lines of one label would hide both from
    task_fields, so an answer replaces; Git keeps the earlier one."""
    value = ' '.join(str(value).split())
    if not value or not re.fullmatch(r'[A-Za-z][A-Za-z /-]*', label):
        return None, 'a field is a label and a one-line value'
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    lines = block['core'].split('\n')
    pattern = re.compile(r'^([ \t]*(?:[-*][ \t]+)?(?:\*\*)?)' + re.escape(label) + r':(?:\*\*)?(?:[ \t]|$)')
    hits = [i for i, line in enumerate(lines) if pattern.match(line)]
    if len(hits) > 1:
        return None, f'{task} has {len(hits)} {label}: lines; keep one by hand'
    if hits:
        lines[hits[0]] = f'{pattern.match(lines[hits[0]])[1]}{label}: {value}'
    else:  # right under the checkbox: never inside another field's continued value
        mark = next(i for i, line in enumerate(lines) if re.match(TASK_MARK, line))
        lines.insert(mark + 1, f'- {label}: {value}')
    new_text = text[:block['start']] + '\n'.join(lines) + text[block['start'] + len(block['core']):]
    entry = task_bodies(new_text).get(task) or []
    if len(entry) != 1 or ' '.join(task_fields(entry[0][0]).get(label, '').split()) != value:
        return None, f'{label}: would not read back from {task}\'s entry'
    return new_text, ''


def place_block(text, task, section):
    """(new TODO.md text, '') with open task ``task``'s entry moved, bytes intact, to the top of
    `## <section>`, or (None, why)."""
    blocks = task_blocks(text)
    block = next((b for b in blocks if b['id'] == task), None)
    if block is None:
        return None, f'{task} has no TODO.md entry'
    if block['mark'] != ' ':
        return None, f'{task} is checked off'
    if block['region'][1].split(' / ')[0] == section:
        return None, f'{task} is already in {section}'
    if block['foreign_heading']:
        return None, f'{task} contains another heading; move it by hand'
    rest = text[:block['start']] + text[block['end']:]
    heading = re.search(r'^##[ \t]+' + re.escape(section) + r'[ \t]*\r?$', rest, re.M)
    if heading is None:
        return None, f'TODO.md has no "## {section}" section'
    at = heading.end() + len(re.match(r'(?:\r?\n)*', rest[heading.end():])[0])
    new_text = rest[:at] + block['core'] + '\n\n' + rest[at:]
    moved = next((b for b in task_blocks(new_text) if b['id'] == task), None)
    if (sorted(b['core'] for b in blocks) != sorted(b['core'] for b in task_blocks(new_text))
            or moved is None or moved['region'][1].split(' / ')[0] != section):
        return None, 'task block bytes would change'
    return new_text, ''
