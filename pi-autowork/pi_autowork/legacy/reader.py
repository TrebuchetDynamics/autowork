"""The one reader of a TODO.md + goals.json repository left after the Task Store v2 cut.

`autowork migrate` alone uses it, to convert a repository once. The modules beside it are
frozen copies of Docs Sync's parsers at the cut (goals_todo, goals_ledger, goals_queue,
todo_archive); the functions below are the engine's queue reader as it was. Nothing here
selects, dispatches or writes: it reports what the old queue says, so conversion can prove
the store selects the same.
"""
import hashlib
from pathlib import Path
import re
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parents[1] / 'engine'))
import goals_ledger  # noqa: E402
import goals_queue  # noqa: E402
import goals_todo  # noqa: E402
import todo_archive  # noqa: E402
import parallel_plan  # noqa: E402

task_bodies = goals_todo.task_bodies
task_fields = goals_todo.task_fields
task_checks = goals_todo.task_checks
CHECK_LABELS = goals_todo.CHECK_LABELS


def task_field_list(body):
    """Every `Label: value` of an entry in order, repeated labels included: task_fields() drops a
    label written twice, which would lose a note on conversion."""
    prose = goals_todo.task_prose(body)
    matches = list(re.finditer(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):(?:\*\*)?[ \t]*', prose, re.M))
    found = []
    for i, match in enumerate(matches):
        end = matches[i + 1].start() if i + 1 < len(matches) else len(prose)
        value = prose[match.end():end].strip()
        if value:
            found.append((match[1], value))
    return found


class Drift(ValueError):
    """TODO.md's order differs from the recorded priority order."""


def _text(path):
    return Path(path).read_text().replace('\r\n', '\n').replace('\r', '\n')


def ledger(repo):
    data = goals_ledger.parse_ledger((Path(repo) / 'goals.json').read_text())
    problems = goals_ledger.shape_errors(data)
    if problems:
        raise ValueError('\n'.join(problems))
    problems = goals_ledger.errors(data)
    if problems:
        raise ValueError('invalid goals.json: ' + '; '.join(problems))
    return goals_ledger.normalize(data)


def inputs(repo):
    """The parsed queue: bodies, ledger, the ledger's order and its tasks by ID."""
    text = _text(Path(repo) / 'TODO.md')
    bodies = task_bodies(text)
    data = ledger(repo)
    picks, priority = goals_queue.queue(data, text, allow_drift=True, bodies=bodies)
    if priority['state'] == 'drift':
        named = '; '.join(f'{key}: {", ".join(priority[key])}' for key in ('duplicates', 'moved', 'added', 'missing')
                          if priority.get(key))
        raise Drift(named or 'the order differs')
    return dict(bodies=bodies, ledger=data, ordered=[t['id'] for t, _ in picks],
                indexed={t['id']: t for t in data['tasks']}, known=set(bodies) | {t['id'] for t in data['tasks']})


def archive_file(repo):
    text = _text(Path(repo) / 'TODO.md')
    navigation = todo_archive.navigation(text, goals_todo.markdown_prose(text), set(task_bodies(text)))
    try:
        return Path(repo) / todo_archive.archive_owner(Path(repo), navigation)
    except SystemExit as exc:
        raise ValueError(str(exc)) from exc


def archived_done(repo):
    """IDs closed in the TODO archive; an ambiguous archive closes nothing."""
    try:
        archive = archive_file(repo)
    except ValueError:
        return set()
    if not archive.is_file():
        return set()
    text = _text(archive)
    bodies = task_bodies(text)
    prose = re.sub(r'<!--.*?-->', lambda m: re.sub(r'[^\r\n]', ' ', m[0]),
                   goals_todo.markdown_prose(text), flags=re.S)
    records, _ = todo_archive.entries(text, prose, set(bodies))
    headings = {tid for start, end, tid, mark in records
                if mark is None and todo_archive.explicitly_closed(prose[start:end], mark)}
    records, _ = todo_archive.entries(text, prose, set(bodies) | headings)
    return {tid for start, end, tid, mark in records
            if sum(row[2] == tid for row in records) == 1
            and not any(other_start < end and start < other_end
                        for other_start, other_end, other_id, _ in records if other_id != tid)
            and todo_archive.explicitly_closed(prose[start:end], mark)}


def _labels(body):
    return re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):', goals_todo.task_prose(body), re.M)


def _reason(repo, tid, data, done, archived=frozenset()):
    """The old queue's eligibility rules (task and ledger agreement, contract fields,
    dependencies), as the engine applied them before the cut."""
    bodies, indexed = data['bodies'], data['indexed']
    if tid not in bodies:
        return 'missing TODO contract'
    body, mark, section = bodies[tid][0]
    fields, labels = task_fields(body), _labels(body)
    if (any(labels.count(label) > 1 for label in ('Scope', 'Acceptance', 'Checks', 'Verification',
                                                   'Dependencies', 'Status', 'Sources'))
            or all(label in labels for label in CHECK_LABELS)):
        return 'duplicate task contract fields'
    if mark.lower() == 'x' or section not in ('Now', 'Next'):
        return 'completed or decision-held'
    task = indexed.get(tid)
    if task is None:
        return f'{tid} is missing from goals.json'
    if task['status'] != 'done' and tid in archived:
        return f"{tid} is {task['status']} in goals.json but archived as done"
    status = re.split(r'[;\.\s]', fields.get('Status', task['status']))[0]
    if status != task['status'] or task['section'] != section or task['status'] in ('done', 'superseded'):
        return 'TODO.md and goals.json disagree'
    for dep in task['depends_on']:
        if indexed.get(dep, {}).get('status') != 'done':
            return f'dependency {dep} is unfinished'
    goals = {g['id']: g for g in data['ledger']['goals']}
    goal = goals[task['goal']]
    if goal['status'] == 'met' or any(goals[d]['status'] != 'met' for d in goal['depends_on']):
        return 'goal met or its dependency unmet'
    if not (fields.get('Scope') and fields.get('Acceptance') and task_checks(fields)):
        return 'needs unique Scope, Acceptance and Checks fields'
    ids = parallel_plan.dependency_ids(fields.get('Dependencies', 'None.').strip().strip('.').strip(), data['known'])
    if ids and any(item not in done for item in ids):
        return 'unresolved dependency'
    return None


def order(repo, data=None):
    """Task IDs the old queue would select, highest priority first (planning tasks included)."""
    data = data or inputs(repo)
    archived = archived_done(repo)
    done = {key for key, items in data['bodies'].items() if items[0][1].lower() == 'x'}
    done |= archived
    done |= {key for key, task in data['indexed'].items() if task['status'] == 'done'}
    return [tid for tid in data['ordered'] if _reason(repo, tid, data, done, archived) is None]


def digest(repo):
    """What the converter read, so a write can refuse files that changed meanwhile."""
    return {name: hashlib.sha256((Path(repo) / name).read_bytes()).hexdigest()
            for name in ('TODO.md', 'goals.json') if (Path(repo) / name).exists()}
