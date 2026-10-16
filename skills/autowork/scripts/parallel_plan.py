"""Pure parallel admission; no claims, processes, filesystem reads or task writes.

Paths use case-sensitive fnmatch globs (stars can cross '/'); a trailing slash
means the whole directory. Glob intersection uses a finite product of the two
patterns, not current files, so not-yet-created files are protected too.
"""
from fnmatch import fnmatchcase
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
    result = [p.strip() for p in value.split(',') if p.strip()]
    for path in result:
        if (path.startswith('/') or '\\' in path or '\x00' in path
                or any(part in ('.', '..', '') for part in path.rstrip('/').split('/'))):
            raise ValueError('Touches must contain repository-relative paths without dot segments')
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


def _intersects(left, right):
    left = left + '*' if left.endswith('/') else left
    right = right + '*' if right.endswith('/') else right
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


def _resources(task):
    return set(re.split(r'[,\s]+', task.get('fields', {}).get('Resources', '').strip())) - {''}


def _solo(task):
    touches = _touches(task)
    if not touches:
        return 'missing Touches; must run alone'
    if _resources(task) & {'live', 'exclusive'}:
        return 'live/exclusive resource; must run alone'
    if _shared(touches, SERIAL_PATHS):
        return 'serial path; must run alone'
    return ''


def _dependencies(task):
    fields = task.get('fields', {})
    value = fields.get('Dependencies', 'None.').strip().strip('.').strip()
    if re.split(r';|\.\s', value)[0].strip().lower() in ('none', 'none required', '—', '-', ''):
        return set()
    return set(re.findall(r'`?([A-Za-z0-9][A-Za-z0-9_-]*)`?', value))


def plan(tasks, running=(), *, all_tasks=()):
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
    ``waiting`` contains {id, reason} for each non-dispatched input contract.
    """
    tasks, running, all_tasks = list(tasks), list(running), list(all_tasks)
    known = {t['id']: t for t in [*all_tasks, *tasks, *running]}
    active = {t['id']: t for t in running}
    claims = {}
    for t in known.values():
        status = re.split(r'[;.\s]', t.get('fields', {}).get('Status', 'open'))[0]
        if status == 'in_progress' and t['id'] not in active:
            claims[t['id']] = t

    def depends(a, b):
        pending, seen = list(_dependencies(a)), set()
        while pending:
            tid = pending.pop()
            if tid == b['id']:
                return True
            if tid not in seen:
                seen.add(tid)
                if tid in known:
                    pending.extend(_dependencies(known[tid]))
        return False

    def conflict(a, b, claim=False):
        if depends(a, b) or depends(b, a):
            return 'dependency conflict with ' + b['id']
        if claim:  # idle claim: only declared overlap matters
            if _shared(_touches(a), _touches(b)):
                return 'overlapping paths with in_progress ' + b['id']
            if _resources(a) & _resources(b):
                return 'shared resource with in_progress ' + b['id']
            return ''
        solo = _solo(a) or _solo(b)
        if solo:
            return solo + ' (beside ' + b['id'] + ')'
        if _shared(_touches(a), _touches(b)):
            return 'overlapping paths with ' + b['id']
        if _resources(a) & _resources(b):
            return 'shared resource with ' + b['id']
        return ''

    # Backfill: a task may start past a waiting higher-priority one only when it shares
    # nothing with it (paths, resources, dependencies), so priority still decides every
    # overlap. A waiting task that must run alone stops all lower dispatch, or backfill
    # would keep the pool from draining for it.
    dispatch, waiting, stopped, reserved = [], [], '', []
    for task in tasks:
        tid = task['id']
        if tid in active or tid in claims:
            waiting.append({'id': tid, 'reason': 'already running/live slot or in_progress'})
            continue
        reason = stopped or next((r for other in [*active.values(), *dispatch]
                                  if (r := conflict(task, other))), '') \
            or next((r for other in claims.values() if (r := conflict(task, other, claim=True))), '') \
            or next((r for other in reserved if (r := conflict(task, other))), '')
        if reason:
            if not stopped and _solo(task):
                stopped = 'priority waits for ' + tid
            reserved.append(task)
            waiting.append({'id': tid, 'reason': reason})
        else:
            dispatch.append(task)
            if _solo(task):
                stopped = 'priority task ' + tid + ': ' + _solo(task)
    return {'dispatch': dispatch, 'waiting': waiting}
