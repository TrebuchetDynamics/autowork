"""Pure parallel admission; no claims, processes, filesystem reads or task writes.

Paths use case-sensitive fnmatch globs (stars can cross '/'); a trailing slash
means the whole directory. Glob intersection uses a finite product of the two
patterns, not current files, so not-yet-created files are protected too.
"""
from fnmatch import fnmatchcase
from functools import lru_cache
import re

# Reversible built-in serial policy, including nested packages and CI files.
SERIAL_NAMES = (
    'package.json', 'package-lock.json', 'npm-shrinkwrap.json', 'yarn.lock',
    'pnpm-lock.yaml', 'bun.lock', 'bun.lockb', 'pyproject.toml', 'setup.py',
    'setup.cfg', 'requirements*.txt', 'Pipfile', 'Pipfile.lock', 'poetry.lock',
    'uv.lock', 'Cargo.toml', 'Cargo.lock', 'go.mod', 'go.sum', 'Gemfile',
    'Gemfile.lock', 'composer.json', 'composer.lock', 'pom.xml', 'build.gradle*',
    '*.csproj', 'packages.lock.json', 'mix.exs', 'mix.lock', '.gitlab-ci.yml',
    'azure-pipelines.yml', 'Jenkinsfile',
)
SERIAL_DIRS = ('migration/', 'migrations/', 'schema/', 'schemas/',
               '.github/workflows/', '.circleci/')
SERIAL_PATHS = tuple(p for name in SERIAL_NAMES for p in (name, '*/' + name)) + tuple(
    p for directory in SERIAL_DIRS for p in (directory, '*/' + directory))


def paths(value):
    """Parse a comma list; reject ambiguous/non-relative declarations fail-closed."""
    def valid(path):
        return not (path.startswith('/') or '\\' in path or '\x00' in path
                    or any(part in ('.', '..', '') for part in path.rstrip('/').split('/')))

    # A planner's placeholder for a file that does not exist yet, `migrations/<new … migration>`,
    # names new files under that directory: read it as the directory, or the worker's real new
    # file is outside Touches.
    # A following list item (`- Touches widened by ... (date): ...`, a note whose label the field
    # parser does not take), a heading or a blank line ran into the value and spoiled its last path
    # (TOOLSET-213-45). None of them is ever part of the path list.
    value = re.split(r'\n(?:[ \t]*[-*][ \t]|[ \t]*#|[ \t]*\n)', value, maxsplit=1)[0]
    result = [re.sub(r'^(.*/)<[^<>/]*>$', r'\1', p.strip()) for p in value.split(',') if p.strip()]
    # Prose often ends the last item with a period. Remove just that one,
    # never a parent segment or a dot inside a path, and only if it is safe.
    if result and result[-1].endswith('.') and not result[-1].endswith('..') and valid(result[-1][:-1]):
        result[-1] = result[-1][:-1]
    for path in result:
        if '\n' in path or path.count(' ') >= 3:  # a sentence, not a path
            raise ValueError('invalid Touches (not a list of paths): ' + ' '.join(path.split())[:80])
        if not valid(path):
            raise ValueError('invalid Touches: ' + path)
    return result


def _tokens(pattern):
    # Match fnmatch's bracket grammar; unmatched '[' is a single literal.
    tokens, i = [], 0
    while i < len(pattern):
        start = i
        i += 1
        if pattern[start] == '[':
            end = i
            if end < len(pattern) and pattern[end] == '!':
                end += 1
            if end < len(pattern) and pattern[end] == ']':
                end += 1
            while end < len(pattern) and pattern[end] != ']':
                end += 1
            if end < len(pattern):
                i = end + 1
        tokens.append(pattern[start:i])
    return tokens


GLOB = re.compile(r'[*?\[]')


@lru_cache(maxsize=1 << 16)
def _intersects(left, right):
    """Whether some path matches both patterns. Literal sides are decided at once; only two
    real globs run the product search (TOOLSET-221-8e: it made one dispatch take minutes)."""
    left_glob, right_glob = bool(GLOB.search(left)), bool(GLOB.search(right))
    if not left_glob and not right_glob:
        if left.endswith('/') and right.endswith('/'):
            return left.startswith(right) or right.startswith(left)
        if left.endswith('/') or right.endswith('/'):
            directory, path = (left, right) if left.endswith('/') else (right, left)
            return path.startswith(directory) and path != directory
        return left == right
    left = left + '*' if left.endswith('/') else left
    right = right + '*' if right.endswith('/') else right
    if not left_glob and not left.endswith('*'):
        return fnmatchcase(left, right)
    if not right_glob and not right.endswith('*'):
        return fnmatchcase(right, left)
    return _search(left, right)


def _search(left, right):
    a, b = _tokens(left), _tokens(right)
    # Predicates change only at literal/class/range boundaries. One character
    # from each resulting interval is enough, even for negated Unicode ranges.
    points = {0, 0x10ffff}
    for char in left + right:
        points.update(n for n in (ord(char)-1, ord(char), ord(char)+1) if 0 <= n <= 0x10ffff)
    alphabet = [chr(n) for n in points]
    pending, seen = [(0, 0)], set()
    while pending:
        i, j = pending.pop()
        if (i, j) in seen:
            continue
        seen.add((i, j))
        if i == len(a) and j == len(b):
            return True
        if i < len(a) and a[i] == '*':
            pending.append((i+1, j))
        if j < len(b) and b[j] == '*':
            pending.append((i, j+1))
        if i < len(a) and j < len(b) and any(
                fnmatchcase(c, a[i]) and fnmatchcase(c, b[j]) for c in alphabet):
            pending.append((i if a[i] == '*' else i+1, j if b[j] == '*' else j+1))
    return False


def _shared(left, right):
    return any(_intersects(a, b) for a in left for b in right)


def overlap(actual_paths, declared, other_sets):
    """Return actual filenames outside Touches or conflicting with other sets.

    Arguments are path lists, not TODO comma strings. An empty declaration never
    authorizes a changed file; an empty other set means unknown concurrent scope
    and conflicts with every actual file. Filenames are literal, not patterns.
    """
    actual_paths, declared = list(actual_paths), list(declared)
    other_sets = [list(group) for group in other_sets]

    def matches(path, patterns):
        return any(fnmatchcase(path, p + '*' if p.endswith('/') else p)
                   for p in patterns)

    return {'outside': sorted({p for p in actual_paths if not matches(p, declared)}),
            'conflicts': sorted({p for p in actual_paths
                                 if any(not group or matches(p, group) for group in other_sets)})}


def _touches(task):
    return paths(task.get('fields', {}).get('Touches', ''))


def _hint(task):
    """Declared Touches as a scheduling hint (TOOLSET-161-17): missing or invalid is no hint."""
    try:
        return _touches(task)
    except ValueError:
        return []


def _resources(task):
    return set(re.split(r'[,\s]+', task.get('fields', {}).get('Resources', '').strip())) - {''}


def authorization_wait(task):
    """An unattended runner needs an explicit record for owner-only or live work.

    Name the missing authorization as an outside condition, not a running claim,
    so status roots and owner questions also work when this is the only task.
    """
    fields = task.get('fields', {})
    ownership = ' '.join(fields.get('Ownership', '').split()).strip(' .`*_')
    owner_only = re.fullmatch(r'owner(?: only| or (?:a )?coordinator with live authorization)?',
                              ownership, re.I)
    duplicates = task.get('authorization_duplicates', [])
    if duplicates or ((owner_only or 'live' in _resources(task))
                      and not fields.get('Live authorization', '').strip()):
        reason = ('duplicate authorization fields: ' + ', '.join(duplicates) if duplicates
                  else 'requires owner action or recorded Live authorization')
        return {'id': task['id'], 'reason': reason,
                'blocked_by': ['Live authorization: ' + task['id']]}
    return None


def protected_path(path):
    """Whether a concrete repository path changes shared build/schema/CI state."""
    return any(fnmatchcase(path, p + '*' if p.endswith('/') else p) for p in SERIAL_PATHS)


SERIAL_REASON = 'serial path; must run alone'


def _solo(task, protected_files=None):
    # Touches only schedule (TOOLSET-161-17): a task without them runs beside other work.
    touches = _hint(task)
    if _resources(task) & {'live', 'exclusive'}:
        return 'live/exclusive resource; must run alone'
    if protected_files is None:
        serial = _shared(touches, SERIAL_PATHS)
    else:
        # A directory can hypothetically contain every manifest name. Use the
        # actual inventory for directories, keeping explicit new protected paths
        # and named schema/CI directories exclusive even before they exist.
        serial = any(
            (protected_path(p + '.autowork-probe')
             or any(fnmatchcase(f, p + '*') for f in protected_files)) if p.endswith('/')
            else _shared([p], SERIAL_PATHS)
            for p in touches)
    if serial:
        return SERIAL_REASON
    return ''


TASK_ID = re.compile(r'[A-Z][A-Z0-9]*(?:-[A-Za-z0-9]+)+')


def dependency_ids(value, known=()):
    """Task IDs a Dependencies field names; prose around them is not a dependency.

    A first clause starting with "none" declares none ("none for this slice; ...").
    A token counts when it is shaped like a task ID (``TASK-022``, ``TASK-009``)
    or is a known task ID, so words such as "for", "Section", "Next" or goal gates
    ("G1") never hold a task (bravo, 2026-10-16). A line with no task ID at
    all is returned whole, so it still holds the task.
    """
    value = value.strip().strip('.').strip()
    first = re.split(r';|\.\s', value)[0].strip().lower()
    if first in ('—', '-', '') or re.match(r'none\b', first):
        return set()
    known = set(known)
    ids = {token for token in re.findall(r'[A-Za-z0-9][A-Za-z0-9_-]*', value)
           if TASK_ID.fullmatch(token) or token in known}
    # A line naming no task ("approved device access") is an outside condition:
    # it stays an unresolved dependency rather than meaning "none".
    return ids or {value}


def _dependencies(task, known=()):
    return dependency_ids(task.get('fields', {}).get('Dependencies', 'None.'), known)


def plan(tasks, running=(), *, all_tasks=(), parked=(), adopted=(), protected_files=None, drain_after=None,
         waited=None, finished=()):
    """Plan ordered runnable contracts against running contracts/live slots.

    ``running`` contains task contracts held by live slots. Also pass every
    repository contract via ``all_tasks``: this supplies transitive dependency
    edges and in_progress tasks which are not in the runnable list. No capacity
    limit is applied here; the dispatcher consumes the returned ordered prefix.

    An in_progress task without a live slot is a claim, not running work: the
    dispatcher only plans while it holds the repository lease, which excludes a
    live sequential Autowork owner. A claim is never dispatched and still blocks
    its dependents and tasks whose declared Touches or Resources overlap it, but
    its missing Touches does not force unrelated tasks to wait (sierra, 2026-10-15:
    32 handed-off claims without Touches blocked every task).
    ``parked`` contains contracts of held slots no attempt can finish. Their work
    waits for a person, not for the pool, and only ever reruns fresh from the code
    of that time, so they block their dependents only (2026-10-16: one exhausted
    hold idled every runner for seven hours; then one held task's wide Touches
    still held 34 sierra tasks).
    ``adopted`` names in_progress claims verified idle (parallel_claims): they are
    planned like open tasks.
    ``waiting`` contains {id, reason} for each non-dispatched input contract.
    ``drain_after`` (seconds) and ``waited`` ({task: seconds waiting so far}): an exclusive
    task that waits on running work stops lower dispatch only once it has waited that long;
    until then it reserves what it declares, like any waiting task (TOOLSET-171-35). None
    drains at once.
    ``finished`` names running contracts whose worker has ended (the commit awaits review or
    integration): they still own their files, but nothing runs beside them, so the must-run-alone
    rule ignores them (one runner idled 54 minutes while an exclusive task waited out a review).
    """
    tasks, running, all_tasks, parked = list(tasks), list(running), list(all_tasks), list(parked)
    # Each task's answers once per call, not once per pair (TOOLSET-221-8e).
    solos, resource_sets, hints = {}, {}, {}
    def solo(task):
        if id(task) not in solos:
            solos[id(task)] = _solo(task, protected_files)
        return solos[id(task)]

    def resources(task):
        if id(task) not in resource_sets:
            resource_sets[id(task)] = _resources(task)
        return resource_sets[id(task)]

    def hint(task):
        if id(task) not in hints:
            hints[id(task)] = _hint(task)
        return hints[id(task)]
    # A serial file (manifest, lockfile, CI, migration) conflicts only with other serial
    # work: each worker has its own worktree, so it cannot break a neighbour's build
    # (TOOLSET-160-df). Only an exclusive task runs alone and stops lower dispatch.
    serial = lambda task: solo(task) == SERIAL_REASON
    exclusive = lambda task: '' if serial(task) else solo(task)
    known = {t['id']: t for t in [*all_tasks, *tasks, *running, *parked]}
    active = {t['id']: t for t in running}
    claims = {}
    for t in known.values():
        status = re.split(r'[;.\s]', t.get('fields', {}).get('Status', 'open'))[0]
        if status == 'in_progress' and t['id'] not in active and t['id'] not in adopted:
            claims[t['id']] = t
    held = {t['id'] for t in parked}
    claims.update((t['id'], t) for t in parked)

    closures = {}

    def depends(a, b):
        if id(a) not in closures:
            pending, seen = list(_dependencies(a, known)), set()
            while pending:
                tid = pending.pop()
                if tid not in seen:
                    seen.add(tid)
                    if tid in known:
                        pending.extend(_dependencies(known[tid], known))
            closures[id(a)] = seen
        return b['id'] in closures[id(a)]

    def conflict(a, b, claim=False, reserved=False):
        if b['id'] in held:  # waits for a person; only what needs it waits too
            return 'dependency: held ' + b['id'] if depends(a, b) else ''
        if depends(a, b) or depends(b, a):
            return 'dependency conflict with ' + b['id']
        # Overlapping Touches never hold a task (TOOLSET-161-17): integration merges in priority
        # order and settles a real conflict there. Resources, serial and exclusive rules stay.
        if claim or reserved:  # idle claim or waiting task
            other = ('in_progress ' if claim else '') + b['id']
            if resources(a) & resources(b):
                return 'shared resource with ' + other
            if serial(a) and serial(b):
                return 'serial path shared with ' + other
            return ''
        alone = '' if b['id'] in finished else exclusive(a) or exclusive(b)
        if alone:
            return alone + ' (beside ' + b['id'] + ')'
        if serial(a) and serial(b):
            return 'serial path shared with ' + b['id']
        if resources(a) & resources(b):
            return 'shared resource with ' + b['id']
        return ''

    # Backfill: a task may start past a waiting higher-priority one only when it shares
    # nothing with it (paths, resources, dependencies), so priority still decides every
    # overlap. An exclusive task (it must run alone) that waits on running or just-dispatched work
    # stops all lower dispatch, or backfill would keep the pool from draining for it;
    # one waiting only on a claim or another waiting task gains nothing from a stop.
    def first(task, others, **kind):
        """(reason, blocking task ID) for the first conflict, or ('', None)."""
        return next(((r, other['id']) for other in others if (r := conflict(task, other, **kind))), ('', None))

    # Each waiting entry names what holds it in ``blocked_by``, so a stalled queue can be
    # traced to its root blockers without parsing reason text.
    dispatch, waiting, stopped, reserved = [], [], ('', None), []
    for task in tasks:
        tid = task['id']
        if gate := authorization_wait(task):
            waiting.append(gate)
            continue
        if tid in active or tid in claims:
            waiting.append({'id': tid, 'reason': 'already running/live slot or in_progress', 'blocked_by': [tid]})
            continue
        busy = first(task, [*active.values(), *dispatch])
        reason, by = (stopped if stopped[0] else busy if busy[0] else first(task, claims.values(), claim=True))
        if not reason:
            reason, by = first(task, reserved, reserved=True)
        if reason:
            if not stopped[0] and busy[0] and exclusive(task):
                waited_for = (waited or {}).get(tid, 0)
                if drain_after is None:
                    stopped = ('priority waits for ' + tid, tid)
                elif waited_for >= drain_after:
                    stopped = (f'priority waits for {tid} (draining, waited {int(waited_for // 60)}m)', tid)
            reserved.append(task)
            waiting.append({'id': tid, 'reason': reason, 'blocked_by': [by]})
        else:
            dispatch.append(task)
            if exclusive(task):
                stopped = ('priority task ' + tid + ': ' + exclusive(task), tid)
    # Likely-independent work first: a task whose declared Touches overlap running or
    # earlier-chosen work ranks lower for the free slots, but is not held (TOOLSET-161-17).
    chosen, ranked = {path for t in running for path in hint(t)}, []
    for task in dispatch:
        ranked.append((bool(_shared(hint(task), chosen)) if hint(task) else True, task))
        chosen.update(hint(task))
    return {'dispatch': [task for _, task in sorted(ranked, key=lambda pair: pair[0])], 'waiting': waiting}
