"""Pure Git planning-file drivers and the cross-file, pre-commit finalizer.

Drivers only write %A. Git does not promise path order (and can skip drivers),
so callers must finalize the resolved tree before committing a planning merge.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tempfile

import goals
import todo_archive


MISSING = object()


def merge_text(base, ours, theirs):
    with tempfile.TemporaryDirectory() as folder:
        paths = [Path(folder) / name for name in ('base', 'ours', 'theirs')]
        for path, text in zip(paths, (base, ours, theirs)):
            path.write_text(text, encoding='utf-8', newline='')
        result = subprocess.run(['git', 'merge-file', '-p', '-L', 'ours', '-L', 'base', '-L', 'theirs',
                                 str(paths[1]), str(paths[0]), str(paths[2])], capture_output=True)
        if result.returncode < 0 or result.returncode > 127:
            raise ValueError('git merge-file failed: ' + result.stderr.decode())
        return result.stdout.decode('utf-8'), bool(result.returncode)


def choose(base, ours, theirs):
    if ours == theirs or theirs == base:
        return ours, False
    if ours == base:
        return theirs, False
    return ours, True


def encoded(value):
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False)


def conflict_record(ours, theirs):
    def side(value):
        return encoded(value) if value is not MISSING else '/* record deleted */'
    return '<<<<<<< ours\n' + side(ours) + '\n=======\n' + side(theirs) + '\n>>>>>>> theirs'


def merge_ledger(base, ours, theirs):
    versions = [goals.normalize(goals.parse_ledger(text)) for text in (base, ours, theirs)]
    for data in versions:
        problems = goals.shape_errors(data)
        if problems:
            raise ValueError('; '.join(problems))
    fields, conflicted = [], False
    for key in sorted(set().union(*(v.keys() for v in versions))):
        values = [v.get(key, MISSING) for v in versions]
        if key in ('goals', 'tasks'):
            maps = [{row['id']: row for row in rows} for rows in values]
            if any(len(mapping) != len(rows) for mapping, rows in zip(maps, values)):
                raise ValueError('duplicate record ID')
            rows = []
            # Deterministic ID order also makes genuine conflicts local to one record.
            for identifier in sorted(set().union(*(m.keys() for m in maps))):
                old, left, right = [m.get(identifier, MISSING) for m in maps]
                value, clash = choose(old, left, right)
                conflicted |= clash
                if clash:
                    rows.append(conflict_record(left, right))
                elif value is not MISSING:
                    rows.append(encoded(value))
            fields.append(json.dumps(key) + ': [\n' + '\n,\n'.join(rows) + '\n]')
        elif key == 'priority_order':
            # Derived from the resolved TODO, never resolve a real task move here.
            value = versions[1].get(key, versions[2].get(key, MISSING))
            if value is not MISSING:
                fields.append(json.dumps(key) + ': ' + encoded(value))
        else:
            value, clash = choose(*values)
            conflicted |= clash
            if clash:
                fields.append(conflict_record(*(MISSING if value is MISSING else {key: value}
                                                for value in values[1:])))
            elif value is not MISSING:
                fields.append(json.dumps(key) + ': ' + encoded(value))
    text = '{\n' + '\n,\n'.join(fields) + '\n}\n'
    if not conflicted:
        text = encoded(goals.normalize(goals.parse_ledger(text))) + '\n'
    return text, conflicted


def without_coverage(text):
    prose = goals.markdown_prose(text)
    starts = list(re.finditer(re.escape(goals.BEGIN), prose))
    ends = list(re.finditer(re.escape(goals.END), prose))
    if not starts and not ends:
        return text
    if len(starts) != 1 or len(ends) != 1 or starts[0].start() >= ends[0].start():
        raise ValueError('ambiguous coverage markers')
    # Keep boundaries for the finalizer, but no generated rows in Git's inputs.
    return text[:starts[0].end()] + '\n' + text[ends[0].start():]


def merge_todo(base, ours, theirs):
    texts = [without_coverage(text) for text in (base, ours, theirs)]
    blocks = [goals.task_blocks(text) for text in texts]
    maps = [{b['id']: b['core'] for b in rows} for rows in blocks]
    if any(len(mapping) != len(rows) for mapping, rows in zip(maps, blocks)):
        raise ValueError('duplicate TODO task')
    merged, conflicted = {}, False
    for tid in sorted(set().union(*(mapping.keys() for mapping in maps))):
        old, left, right = [mapping.get(tid, MISSING) for mapping in maps]
        value, clash = choose(old, left, right)
        if clash:
            value, body_conflict = merge_text(*(v if v is not MISSING else '' for v in (old, left, right)))
            conflicted |= body_conflict
        if value is not MISSING:
            merged[tid] = value
    skeletons = []
    for text, rows in zip(texts, blocks):
        for block in reversed(rows):
            replacement = f'<!-- docs-sync:task:{block["id"]} -->\n\n' if block['id'] in merged else ''
            text = text[:block['start']] + replacement + text[block['end']:]
        skeletons.append(text)
    skeleton, clash = merge_text(*skeletons)
    for tid, body in merged.items():
        marker = f'<!-- docs-sync:task:{tid} -->'
        if marker not in skeleton:
            # Git may accept a skeleton deletion even though its task was modified
            # on the other side. Retain that record's conflict for the resolver.
            skeleton += '\n\n' + body
            conflicted = True
        else:
            if not clash and skeleton.count(marker) > 1:
                # Git can accept competing moves as two separate insertions.
                # Keep both candidate locations but require an explicit choice;
                # never silently duplicate a task or guess its human priority.
                body = (f'<<<<<<< keep {tid} here\n' + body.rstrip('\r\n') +
                        f'\n=======\n>>>>>>> or remove {tid} here; keep exactly one placement\n')
                conflicted = True
            skeleton = skeleton.replace(marker, body.rstrip('\r\n'))
    return skeleton, conflicted or clash


def driver(kind, base_path, ours_path, theirs_path):
    paths = [Path(p) for p in (base_path, ours_path, theirs_path)]
    texts = [p.read_bytes().decode('utf-8') for p in paths]
    try:
        if kind == 'goals':
            output, conflicted = merge_ledger(*texts)
        elif kind == 'todo':
            output, conflicted = merge_todo(*texts)
        else:
            output, conflicted = todo_archive.merge_entries(*texts, mask=goals.markdown_prose,
                                                          merge_text=merge_text)
    except (ValueError, KeyError, TypeError):
        # Unsupported/malformed inputs retain Git's original conflicts, never erase data.
        output, _ = merge_text(*texts)
        conflicted = True
    paths[1].write_bytes(output.encode('utf-8'))
    return int(conflicted)


def finalize(repo):
    """Validate all output before either write; never archive as a merge side effect."""
    repo = Path(repo)
    data = goals.normalize(goals.load(repo))
    before = goals.checked_bytes(repo / 'TODO.md')
    if before is None:
        raise ValueError('merged TODO.md is missing')
    text = before.decode('utf-8')
    if re.search(r'^(?:<{7,}|={7,}|>{7,})(?: |$)', text, re.M):
        raise ValueError('unresolved TODO.md conflict')
    active = goals.active_task_ids(data)
    bodies = goals.task_bodies(text)
    if any(len(bodies.get(tid, [])) != 1 for tid in active):
        raise ValueError('merged TODO needs exactly one body per unfinished task')
    if any(bodies[t['id']][0][2] != t['section'] for t in data['tasks'] if t['id'] in active):
        raise ValueError('merged TODO task sections differ from ledger')
    if 'priority_order' in data:
        data['priority_order'] = {'schema': goals.PRIORITY_SCHEMA,
                                  'tasks': [tid for tid in bodies if tid in active]}
    problems = goals.errors(data, allow_pending_evidence=True)
    if problems:
        raise ValueError('; '.join(problems))
    output = goals.render_text(repo, data, text)
    ledger = encoded(data) + '\n'
    goals.atomic_write(goals.path_of(repo), ledger)
    # Advance only to our own exact expected bytes, not an intervening writer's.
    digest = hashlib.sha256()
    for name, blob in (('goals.json', ledger.encode()), ('TODO.md', text.encode())):
        digest.update(name.encode() + b'\0')
        digest.update(str(len(blob)).encode() + b'\0' + blob)
    goals.TRANSACTION.set((repo, digest.hexdigest()))
    goals.atomic_write(repo / 'TODO.md', output)
