"""Read-only conversion inventory: tracked legacy references and non-queue source lines."""
from pathlib import Path
import re

from .reader import goals_todo, parallel_plan

NAMES = ('TODO.md', 'goals.json')
DOCUMENTS = {'.md', '.markdown', '.rst', '.adoc', '.asciidoc', '.org'}
FIELD = re.compile(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):(?:\*\*)?[ \t]*(.*)$')
SCAFFOLD = re.compile(r'(?:# (?:TODO|Work queue)|## (?:Now|Next|Now / Next|Needs decision|Goal coverage)'
                      r'|\[Completed tasks\]\(TODO\.archive\.md\))')
PRESERVED = 'CHECKLIST.md'


def _group(path):
    target = Path(path)
    if target.name in ('.gitattributes', '.gitignore') or path == '.git-blame-ignore-revs':
        return 'git_metadata'
    document = target.suffix.lower() in DOCUMENTS or (path.startswith('docs/') and target.suffix == '.txt')
    return 'documentation_drift' if document else 'consumers'


def retained_references(output, revision):
    """Inventory `git grep -n -z` hits in the snapshot the transaction retains."""
    found = dict(consumers=[], documentation_drift=[], git_metadata=[])
    pattern = re.escape(revision) + r':([^\0]+)\0([0-9]+)\0([^\n]*)(?:\n|$)'
    for match in re.finditer(pattern, output):
        path, number, line = match.groups()
        if path not in (*NAMES, 'TODO.archive.md'):
            found[_group(path)].append(dict(path=path, line=int(number),
                                           names=[name for name in NAMES if name in line]))
    return found


def references(repo, tracked):
    """Tracked working-tree text hits, without quoting potentially private source content.

    Planning inputs/history are excluded. Git metadata and documentation are inventoried
    separately; all other files, including task contracts, remain consumers. Symlinks are
    never followed outside the repository; binary files are skipped.
    """
    found = dict(consumers=[], documentation_drift=[], git_metadata=[])
    for path in sorted(tracked):
        if path in (*NAMES, 'TODO.archive.md'):
            continue
        target = Path(repo) / path
        if any(parent.is_symlink() for parent in (target, *target.parents)) or target.is_dir():
            continue  # includes tracked submodule directories; never traverse another repository
        try:
            data = target.read_bytes()
        except FileNotFoundError:
            continue  # tracked deletion: not a remaining consumer
        if b'\0' in data:
            continue
        group = _group(path)
        for number, line in enumerate(data.split(b'\n'), 1):
            if names := [name for name in NAMES if name.encode() in line]:
                found[group].append(dict(path=path, line=number, names=names))
    return found


def _lines(text):
    """LF-delimited source lines, retaining CRLF and Unicode separators as literal bytes."""
    parts = text.split('\n')
    return [part + '\n' for part in parts[:-1]] + ([parts[-1]] if parts[-1] else [])


def preservation(source, converted):
    """Return (snapshot text, extra line ranges), or (None, []).

    Only simple mapped lines are disposable: known task headings/checkboxes, mapped
    fields, standard queue headings and archive navigation. Continuations and ignored
    annotations also trigger a snapshot of the *whole* original, keeping task context too.
    This intentionally conservative copy also preserves comments, examples and formatting
    within entries that the legacy field reader masks or folds. Generated coverage alone
    is replaced by empty lines, so every retained byte stays at its original line number.
    """
    text = source.decode('utf-8')
    prose = goals_todo.markdown_prose(text)
    begins = list(re.finditer(r'^' + re.escape(goals_todo.BEGIN) + r'[ \t]*\r?$', prose, re.M))
    ends = list(re.finditer(r'^' + re.escape(goals_todo.END) + r'[ \t]*\r?$', prose, re.M))
    coverage = set()
    lines = _lines(text)
    if begins or ends:
        if len(begins) != 1 or len(ends) != 1 or begins[0].start() >= ends[0].start():
            marked = [text[:m.start()].count('\n') + 1 for m in begins + ends]
            raise ValueError(f'ambiguous coverage markers at TODO.md lines {sorted(marked)}; reconcile first')
        first = text[:begins[0].start()].count('\n')
        last = text[:ends[0].end()].count('\n')
        coverage = set(range(first, last + 1))
    accounted = set(coverage)
    # task_blocks respects sibling/group headings, unlike a last field that can swallow
    # an unrelated backlog. Only entries that actually become full records count here.
    for block in goals_todo.task_blocks(text):
        if block['id'] not in converted:
            continue
        first = text[:block['start']].count('\n')
        chunk = text[block['start']:block['end']]
        mapped_checks = goals_todo.task_checks(goals_todo.task_fields(chunk))
        visible = re.sub(r'<!--.*?(?:-->|\Z)', lambda m: re.sub(r'[^\r\n]', ' ', m[0]),
                         goals_todo.task_prose(chunk), flags=re.S)
        for offset, (raw, masked) in enumerate(zip(_lines(chunk), _lines(visible))):
            line = raw.rstrip('\r\n')
            if raw != masked or any(separator in line for separator in ('\r', '\u2028', '\u2029')):
                continue
            field = FIELD.fullmatch(line)
            if field:
                # These fields are derived or collapsed; extra annotations need the snapshot.
                label, value = field.groups()
                expected = {'Goal': (converted[block['id']]['goal'],),
                            'Status': (converted[block['id']]['status'],), 'Kind': ('plan', 'implementation')}
                if label in expected and value.strip() not in expected[label]:
                    continue
                if label in goals_todo.CHECK_LABELS and not mapped_checks:
                    continue
                if (label == 'Dependencies' and not parallel_plan.dependency_ids(value, converted)
                        and value.strip().rstrip('.').lower() not in ('', '-', '—', 'none')):
                    continue
                accounted.add(first + offset)
            elif re.match(goals_todo.TASK_MARK, line):
                accounted.add(first + offset)
            elif offset == 0 and re.match(r'#{3,6}\s', line):
                checkbox = next((row for row in _lines(chunk) if re.match(goals_todo.TASK_MARK, row)), '')
                if re.sub(r'^#{3,6}\s+', '', line).strip() == re.sub(r'^[-*] \[[ xX]\]\s+', '', checkbox).strip():
                    accounted.add(first + offset)
    extra = [i for i, line in enumerate(lines) if i not in accounted and line.strip()
             and not SCAFFOLD.fullmatch(line.strip())]
    if not extra:
        return None, []
    ranges = []
    for index in extra:
        if ranges and all(not line.strip() for line in lines[ranges[-1][1]:index]):
            ranges[-1][1] = index + 1
        else:
            ranges.append([index + 1, index + 1])
    snapshot = ''.join(re.sub(r'[^\r\n]', '', line) if i in coverage else line
                       for i, line in enumerate(lines))
    return snapshot, ranges
