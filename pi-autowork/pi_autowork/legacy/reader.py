"""The one reader of a TODO.md + goals.json repository left after the Task Store v2 cut.

`autowork migrate` alone uses it, to convert a repository once. The modules beside it are
frozen copies of Docs Sync's parsers at the cut (goals_todo, goals_ledger, goals_queue,
todo_archive); the functions below are the engine's queue reader as it was. Nothing here
selects, dispatches or writes: it reports what the old queue says, so conversion can prove
the store selects the same.
"""
from graphlib import CycleError, TopologicalSorter
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


def _force_ledger(data, rejected):
    """Isolate invalid task rows, not goal contracts or unreadable source structure.

    Membership and priority are legacy caches: stale task references there must not
    invalidate the surviving contracts. Do not rewrite dependencies on omitted tasks;
    those remain unresolved in the converted store.
    """
    remaining = []
    for problem in goals_ledger.shape_errors(data):
        match = re.match(r'tasks\[(\d+)\](?:\.| )', problem)
        entry = data['tasks'][int(match[1])] if match else None
        if isinstance(entry, dict) and isinstance(entry.get('id'), str) and entry['id']:
            rejected[entry['id']] = problem
        elif problem.startswith('priority_order must be '):
            data.pop('priority_order', None)  # force takes the TODO order, even with a broken cache
        else:
            remaining.append(problem)
    if remaining:
        raise ValueError('; '.join(remaining))
    data['tasks'] = [t for t in data['tasks'] if t['id'] not in rejected]
    for problem in goals_ledger.errors(data):
        if any(problem == f'{t["id"]}: depends_on unknown task {tid}'
               for t in data['tasks'] for tid in rejected):
            continue  # a rejected prerequisite is unresolved, not a new defect in its dependent
        entries = [t for t in data['tasks'] if problem.startswith(t['id'] + ':')
                   or problem == f'duplicate id {t["id"]}'
                   or problem.startswith(f'invalid task ID {t["id"]!r}:')]
        if entries:
            for entry in entries:
                rejected[entry['id']] = problem
        elif (problem.startswith(('priority_order names unknown task ', 'task dependency cycle:',
                                  'cross-level dependency cycle:', 'task dependency/supersession cycle;'))
              or any(problem in (f'{g["id"]}: task membership does not match ledger',
                                 f'{g["id"]}: {g.get("status")} goal has no open task')
                     or problem.startswith(f'{g["id"]}: unknown task ') for g in data['goals'])):
            continue
        else:
            remaining.append(problem)
    if remaining:
        raise ValueError('; '.join(remaining))
    data['tasks'] = [t for t in data['tasks'] if t['id'] not in rejected]
    # The ledger emits aggregate cycle errors, not per-entry errors. Locate every
    # participating task even when stale caches suppressed the ledger's cycle pass.
    while True:
        active = {t['id']: t for t in data['tasks'] if t['status'] not in ('done', 'superseded')}
        graph = {('goal', g['id']): [('task', tid) for tid, t in active.items() if t['goal'] == g['id']]
                 for g in data['goals'] if g['status'] != 'met' or not goals_ledger.proven(g)
                 or any(t['goal'] == g['id'] for t in active.values())}
        goals = {g['id']: g for g in data['goals']}
        for task in data['tasks']:
            successors = task.get('superseded_by', []) if task['status'] == 'superseded' else []
            graph[('task', task['id'])] = [('task', dep) for dep in task.get('depends_on', []) + successors]
            if task['id'] in active:
                graph[('task', task['id'])] += [('goal', dep) for dep in goals[task['goal']].get('depends_on', [])
                                               if ('goal', dep) in graph]
        try:
            TopologicalSorter(graph).prepare()
            break
        except CycleError as exc:
            ids = {identifier for kind, identifier in exc.args[1] if kind == 'task'}
            if not ids:
                raise ValueError('goal dependency cycle') from exc
            for tid in ids:
                rejected[tid] = 'task dependency/supersession or cross-level cycle'
            data['tasks'] = [t for t in data['tasks'] if t['id'] not in ids]
    return data


def ledger(repo, *, force=False, rejected=None):
    data = goals_ledger.parse_ledger((Path(repo) / 'goals.json').read_text())
    if force:
        return goals_ledger.normalize(_force_ledger(data, rejected if rejected is not None else {}))
    problems = goals_ledger.shape_errors(data)
    if problems:
        raise ValueError('\n'.join(problems))
    problems = goals_ledger.errors(data)
    if problems:
        raise ValueError('invalid goals.json: ' + '; '.join(problems))
    return goals_ledger.normalize(data)


def inputs(repo, *, force=False):
    """The parsed queue; force reports defects and takes TODO.md's order."""
    text = _text(Path(repo) / 'TODO.md')
    bodies = task_bodies(text)
    rejected = {}
    data = ledger(repo, force=force, rejected=rejected)
    picks, priority = goals_queue.queue(data, text, allow_drift=True, bodies=bodies)
    drift = None
    if priority['state'] == 'drift':
        drift = '; '.join(f'{key}: {", ".join(priority[key])}' for key in ('duplicates', 'moved', 'added', 'missing')
                         if priority.get(key)) or 'the order differs'
        if not force:
            raise Drift(drift)
    if force:
        data['priority_order'] = dict(schema=goals_ledger.PRIORITY_SCHEMA,
                                      tasks=[tid for tid in bodies if tid in goals_queue.active_task_ids(data)])
        picks = goals_queue.eligible(data)
    return dict(bodies=bodies, ledger=data, drift=drift, rejected=rejected, ordered=[t['id'] for t, _ in picks],
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


def contract_error(tid, data, archived, released=()):
    """Validate a whole entry before eligibility can short-circuit on a wait. ``released``:
    claims a drain set aside, whose ledger row already reads ``open`` while TODO.md still
    says ``in_progress``; that pair agrees."""
    rows = data['bodies'].get(tid, [])
    if len(rows) != 1:
        return 'needs exactly one TODO.md entry'
    task = data['indexed'].get(tid)
    if task is None:
        return f'{tid} is missing from goals.json'
    body, mark, section = rows[0]
    fields, labels = task_fields(body), _labels(body)
    if (any(labels.count(label) > 1 for label in ('Scope', 'Acceptance', 'Checks', 'Verification',
                                                 'Dependencies', 'Status', 'Sources'))
            or all(label in labels for label in CHECK_LABELS)):
        return 'duplicate task contract fields'
    status = re.split(r'[;\.\s]', fields.get('Status', task['status']))[0]
    agreed = {task['status']} | ({'in_progress'} if tid in released and task['status'] == 'open' else set())
    if mark.lower() == 'x' or status not in agreed or section != task['section']:
        return 'TODO.md and goals.json disagree'
    if tid in archived:
        return f'{tid} is {task["status"]} in goals.json but archived as done'
    deps = parallel_plan.dependency_ids(fields.get('Dependencies', 'None.'), data['known'])
    named = {dep for dep in deps if dep in data['known'] or parallel_plan.TASK_ID.fullmatch(dep)}
    # Archive-only prerequisites need no ledger row; explicitly rejected rows do not
    # become archive-only just because force removed them from the parsed ledger.
    named -= archived - set(data['indexed']) - set(data['rejected'])
    if named != set(task['depends_on']):
        return 'TODO.md and goals.json dependencies disagree'
    if not (fields.get('Scope') and fields.get('Acceptance') and task_checks(fields)):
        return 'needs unique Scope, Acceptance and Checks fields'
    return None


def _reason(repo, tid, data, done, archived=frozenset(), released=frozenset()):
    """The old queue's eligibility rules (task and ledger agreement, contract fields,
    dependencies), as the engine applied them before the cut. ``released``: claims a
    drain set aside, open in the ledger again while TODO.md still says in_progress."""
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
    agreed = {task['status']} | ({'in_progress'} if tid in released and task['status'] == 'open' else set())
    if status not in agreed or task['section'] != section or task['status'] in ('done', 'superseded'):
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


def order(repo, data=None, released=frozenset()):
    """Task IDs the old queue would select, highest priority first (planning tasks included).
    ``released`` claims (set aside by a drain) count as open, as build() records them."""
    data = data or inputs(repo)
    archived = archived_done(repo)
    done = {key for key, items in data['bodies'].items() if items[0][1].lower() == 'x'}
    done |= archived
    done |= {key for key, task in data['indexed'].items() if task['status'] == 'done'}
    return [tid for tid in data['ordered'] if _reason(repo, tid, data, done, archived, released) is None]


def digest(repo):
    """What the converter read, so a write can refuse files that changed meanwhile."""
    return {name: hashlib.sha256((Path(repo) / name).read_bytes()).hexdigest()
            for name in ('TODO.md', 'goals.json') if (Path(repo) / name).exists()}
