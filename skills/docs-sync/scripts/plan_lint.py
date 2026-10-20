#!/usr/bin/env python3
"""Deterministic, read-only lint of TODO.md task contracts before a runner picks them up.

`goals.py plan-lint REPO [--tasks ID,ID,...] [--json] [--strict]`

Errors (exit 1) are contracts the runner refuses or mis-schedules: the fields
`task_execution.contract_reason` requires, Touches the engine cannot parse or that
name coordinator files, unknown or cyclic dependencies, and Checks commands whose
test file or module does not exist and is not created by the task's own Touches.
Warnings (exit 0 unless --strict) are plans likely to collide or sprawl.

The default scope is every open task in Now/Next; --tasks names tasks explicitly.
Overlap and hot-file counts always use every open task as context. Field, Touches
and dependency parsing reuse goals.py and the autowork engine (parallel_plan,
task_execution); without the engine the lint degrades and says so.
"""
import argparse
from fnmatch import fnmatchcase
import json
import os
from pathlib import Path
import re
import shlex
import sys

HERE = Path(__file__).resolve().parent
if str(HERE) not in sys.path:
    sys.path.insert(0, str(HERE))
import goals  # noqa: E402  (inside `goals.py`, sys.modules['goals'] is that running module)

ENGINE_DIR = HERE.parents[1] / 'autowork' / 'scripts'

# contract_reason's duplicate-label set; Checks/Verification together are duplicates too.
DUPLICATE_LABELS = ('Scope', 'Acceptance', 'Checks', 'Verification', 'Dependencies', 'Status', 'Sources', 'Touches')
REQUIRED = ('Scope', 'Acceptance')
# The coordinator's own files (parallel_state.COORDINATOR_FILES) plus the planning files
# integration never takes from a worker (parallel_integrate.PLANNING_FILES).
PLANNING_FILES = ('BLOCKERS.md', 'todo.archive.md')
FALLBACK_COORDINATOR = ('TODO.md', 'TODO.archive.md', 'goals.json', 'CHANGELOG.md')
HOT_TASKS, HOT_LINES = 3, 1500
MAX_TOUCHES, MAX_ACCEPTANCE, MAX_BODY = 5, 3, 6000
SHOW_OTHERS = 5
SKIP_DIRS = {'.git', '.worktrees', 'node_modules', '__pycache__', '.venv', 'venv', '.tox'}
CODE_EXT = ('.py', '.js', '.mjs', '.cjs', '.ts', '.mts', '.cts')


def engine():
    """(parallel_plan, parallel_state, task_execution) from the sibling autowork skill, or None."""
    if str(ENGINE_DIR) not in sys.path:
        sys.path.insert(0, str(ENGINE_DIR))
    try:
        import parallel_plan
        import parallel_state
        import task_execution
    except Exception:  # noqa: BLE001 - any import failure means the same degraded lint
        return None
    return parallel_plan, parallel_state, task_execution


class Parsers:
    """The engine's parsers, or plain fallbacks when the autowork skill is not installed beside docs-sync."""

    def __init__(self):
        loaded = engine()
        self.available = loaded is not None
        self.protected = None
        if loaded:
            self.plan, state, self.execution = loaded
            self.coordinator = set(state.COORDINATOR_FILES) | set(PLANNING_FILES)
        else:
            self.plan = self.execution = None
            self.coordinator = set(FALLBACK_COORDINATOR) | set(PLANNING_FILES)

    def labels(self, body):
        if self.execution:
            return list(self.execution.contract_labels(body))
        return list(goals.task_fields(body))  # no duplicate detection without the engine

    def paths(self, value):
        if self.plan:
            return self.plan.paths(value)
        return [p.strip() for p in value.split(',') if p.strip()]

    def dependency_ids(self, value, known):
        if self.plan:
            return self.plan.dependency_ids(value, known)
        return {token for token in re.findall(goals.TASK_ID, value) if token in known}

    def task_shaped(self, token):
        return bool(self.plan and self.plan.TASK_ID.fullmatch(token))

    def exclusive(self, fields):
        return bool(self.plan) and 'exclusive' in self.plan._resources({'fields': fields})

    def intersects(self, left, right):
        if self.plan:
            return self.plan._intersects(left, right)
        return left.rstrip('/') == right.rstrip('/')

    def serial(self, repo, path):
        """Whether the engine runs a task naming `path` as serial work (parallel_plan._solo with the
        dispatcher's protected-file inventory, so a directory counts only if it holds a protected file)."""
        if not self.plan:
            return False
        if self.protected is None:
            self.protected = self._protected(repo)
        return self.plan._solo({'fields': {'Touches': path}}, self.protected) == self.plan.SERIAL_REASON

    def _protected(self, repo):
        try:
            import parallel_dispatch
            return parallel_dispatch.protected_files(repo)
        except Exception:  # noqa: BLE001 - not a repository or no dispatcher: inventory the disk
            return [f.relative_to(repo).as_posix() for f in _walk(repo)
                    if self.plan.protected_path(f.relative_to(repo).as_posix())]


# ---------------------------------------------------------------- Checks commands

def _clean(rel):
    rel = rel.strip()
    while rel.startswith('./'):
        rel = rel[2:]
    if not rel or rel.startswith('/') or rel.startswith('~') or '..' in rel.split('/') or '$' in rel:
        return None
    return rel


def _covered(rel, touches):
    """Whether the task's own Touches creates (or owns) `rel`."""
    for path in touches:
        if path == rel or (path.endswith('/') and rel.startswith(path)) or fnmatchcase(rel, path):
            return True
    return False


def _exists(repo, rel, touches):
    return (repo / rel).exists() or _covered(rel, touches)


def _walk(root):
    for folder, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        for name in files:
            yield Path(folder, name)


def _discover(repo, args, touches):
    start, pattern, positional, i = '.', 'test*.py', [], 0
    while i < len(args):
        arg = args[i]
        if arg in ('-s', '--start-directory', '-p', '--pattern', '-t', '--top-level-directory', '-k'):
            if i + 1 >= len(args):
                return []
            if arg in ('-s', '--start-directory'):
                start = args[i + 1]
            elif arg in ('-p', '--pattern'):
                pattern = _strip(args[i + 1])
            i += 2
            continue
        if not arg.startswith('-'):
            positional.append(arg)
        i += 1
    flagged = any(arg in ('-s', '--start-directory', '-p', '--pattern') for arg in args)
    if positional and not flagged:  # with flags, trailing words are prose
        start = positional[0]
        if len(positional) > 1:
            pattern = _strip(positional[1])
    start = _clean(start)
    if start is None:
        return []
    prefix = '' if start in ('', '.') else start.rstrip('/') + '/'
    root = repo / start
    if any(p.endswith('/') and prefix.startswith(p) for p in touches):
        return []  # Touches owns the whole start directory
    owned = [p for p in touches if p.startswith(prefix)]
    if not root.is_dir() and not owned:
        return [f'unittest discover start directory `{start}`']
    if any(fnmatchcase(p.rstrip('/').rsplit('/', 1)[-1], pattern) or p.endswith('/') for p in owned):
        return []
    if root.is_dir() and any(fnmatchcase(f.name, pattern) for f in _walk(root)):
        return []
    return [f'unittest discover pattern `{pattern}` under `{start}` (no match)']


def _module(repo, name, touches):
    parts = name.split('.')
    if not all(re.fullmatch(r'[A-Za-z_]\w*', part) for part in parts):
        return []
    for i in range(len(parts), 0, -1):
        rel = '/'.join(parts[:i])
        if _exists(repo, rel + '.py', touches):
            return []
    if _exists(repo, '/'.join(parts), touches) or _exists(repo, '/'.join(parts) + '/', touches):
        return []
    if (repo / parts[0]).is_dir() or (repo / (parts[0] + '.py')).is_file():
        return [f'unittest module `{name}`']
    return []  # an installed or stdlib module is not the repository's to judge


def _file(repo, token, touches, label):
    rel = _clean(token)
    if rel is None:
        return []
    return [] if _exists(repo, rel, touches) else [f'{label} `{rel}`']


def _path_like(token):
    return bool(re.fullmatch(r'[\w./*?\[\]-]+', token)) and (token.endswith(CODE_EXT) or '/' in token)


def _strip(token):
    return token.rstrip('.,);:') if token.rstrip('.,);:').endswith(CODE_EXT) else token


def _unittest(repo, args, touches):
    if args and args[0] == 'discover':
        return _discover(repo, args[1:], touches)
    missing, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg == '-k':
            skip = True
            continue
        if arg.startswith('-'):
            continue
        arg = _strip(arg)
        if arg.endswith('.py') or '/' in arg:
            missing += _file(repo, arg, touches, 'unittest file')
        else:
            missing += _module(repo, arg, touches)
    return missing


PYTEST_VALUE = ('-k', '-m', '-p', '-c', '-o', '-n', '--deselect', '--rootdir', '--ignore', '--junitxml', '--maxfail')


def _pytest(repo, args, touches):
    missing, skip = [], False
    for arg in args:
        if skip:
            skip = False
            continue
        if arg in PYTEST_VALUE:
            skip = True
            continue
        if arg.startswith('-'):
            continue
        path = _strip(arg).split('::', 1)[0]
        if _path_like(path) and not re.search(r'[*?\[]', path):
            missing += _file(repo, path, touches, 'pytest path')
    return missing


def _node(repo, args, touches):
    if '--test' not in args:
        return []
    missing = []
    for arg in args[args.index('--test') + 1:]:
        if arg.startswith('-'):
            continue
        arg = _strip(arg)
        rel = _clean(arg)
        if rel is None or not _path_like(rel):
            continue
        if re.search(r'[*?\[]', rel):
            if not list(repo.glob(rel)) and not any(fnmatchcase(p, rel) for p in touches):
                missing.append(f'node --test glob `{rel}`')
        else:
            missing += _file(repo, rel, touches, 'node --test file')
    return missing


PY_VALUE = ('-X', '-W', '-Q')


def _python(repo, args, touches):
    i = 0
    while i < len(args) and args[i].startswith('-') and args[i] not in ('-m', '-c'):
        i += 2 if args[i] in PY_VALUE else 1
    if i >= len(args) or args[i] == '-c':
        return []
    if args[i] == '-m':
        if i + 1 >= len(args):
            return []
        module, rest = args[i + 1], args[i + 2:]
        if module == 'unittest':
            return _unittest(repo, rest, touches)
        if module == 'pytest':
            return _pytest(repo, rest, touches)
        return []
    script = _strip(args[i])
    if not script.endswith('.py'):
        return []
    missing = _file(repo, script, touches, 'script')
    for arg in args[i + 1:]:
        arg = _strip(arg)
        if not arg.startswith('-') and _path_like(arg) and arg.endswith(CODE_EXT) and not re.search(r'[*?\[]', arg):
            missing += _file(repo, arg, touches, 'file argument')
    return missing


COMMAND = re.compile(r'(?:^|(?<=[\s(:]))(?:[A-Z_][A-Z0-9_]*=\S*\s+)*((?:python3?(?:\.\d+)?|pytest|node)\s.*)$', re.S)


def commands(checks):
    """Shell-split commands in a Checks value; prose, unbalanced quotes and anything after `cd` are skipped."""
    found = []
    for segment in re.split(r'`|;|&&|\|\||\||\n', checks or ''):
        segment = segment.strip()
        if re.match(r'cd\s', segment):
            break  # later commands run elsewhere; their paths are not repository-relative
        match = COMMAND.search(segment)
        if not match:
            continue
        try:
            tokens = shlex.split(match[1])
        except ValueError:
            continue
        if tokens:
            found.append(tokens)
    return found


def missing_check_targets(repo, checks, touches):
    """Test files/modules a Checks value names that neither exist nor are created by `touches`."""
    repo, missing = Path(repo), []
    for tokens in commands(checks):
        head, args = tokens[0], tokens[1:]
        if head.startswith('python'):
            missing += _python(repo, args, touches)
        elif head == 'pytest':
            missing += _pytest(repo, args, touches)
        elif head == 'node':
            missing += _node(repo, args, touches)
    return list(dict.fromkeys(missing))


# ---------------------------------------------------------------- task lint

def _ledger_ids(repo):
    try:
        data = json.loads((repo / 'goals.json').read_text())
        return {t['id'] for t in data.get('tasks', []) if isinstance(t.get('id'), str)}
    except (OSError, ValueError, AttributeError, TypeError):
        return set()


def _archived_ids(repo, parsers):
    ids = set()
    for name in goals.NEW_ID_SOURCES[1:]:
        blob = goals.checked_bytes(repo / name)
        if blob is not None:
            ids.update(goals.task_bodies(blob.decode('utf-8', 'replace')))
    if parsers.execution:
        try:
            ids |= set(parsers.execution.archived_done(repo))
        except Exception:  # noqa: BLE001 - an ambiguous archive only means fewer known IDs
            pass
    return ids


def _acceptance_count(text):
    numbered = len(re.findall(r'\(\d+\)', text))
    bullets = len(re.findall(r'^\s*[-*]\s', text, re.M))
    clauses = len([c for c in text.split(';') if c.strip()])
    return max(numbered, bullets, clauses)


def _line_count(path, cache):
    if path not in cache:
        try:
            with open(path, 'rb') as handle:
                cache[path] = sum(1 for _ in handle)
        except OSError:
            cache[path] = 0
    return cache[path]


class Linter:
    def __init__(self, repo):
        self.repo = Path(repo)
        self.parsers = Parsers()
        text = goals.todo_text(self.repo)
        self.bodies = goals.task_bodies(text)
        self.errors, self.warnings = [], []
        self.lines = {}
        self.info = {}
        for tid, entries in self.bodies.items():
            body, mark, section = entries[0]
            fields = goals.task_fields(body)
            try:
                touches, bad = self.parsers.paths(fields.get('Touches', '')), None
            except ValueError as exc:
                touches, bad = [], str(exc)
            self.info[tid] = {'body': body, 'open': mark.lower() != 'x', 'section': section,
                              'fields': fields, 'touches': touches, 'bad_touches': bad}
        self.known = set(self.bodies) | _ledger_ids(self.repo) | _archived_ids(self.repo, self.parsers)
        self.deps = {tid: self._deps(tid) for tid in self.info}
        self.closures = {}

    def add(self, kind, tid, code, message):
        (self.errors if kind == 'error' else self.warnings).append({'task': tid, 'code': code, 'message': message})

    def _deps(self, tid):
        value = self.info[tid]['fields'].get('Dependencies', 'None.').strip().strip('.').strip()
        ids = self.parsers.dependency_ids(value, self.known)
        if ids == {value} and value not in self.known and not self.parsers.task_shaped(value):
            return set()  # an outside condition, not a task
        return ids

    def closure(self, tid):
        if tid not in self.closures:
            pending, seen = list(self.deps.get(tid, ())), set()
            while pending:
                dep = pending.pop()
                if dep not in seen:
                    seen.add(dep)
                    if dep in self.info and self.info[dep]['open']:
                        pending.extend(self.deps[dep])
            self.closures[tid] = seen
        return self.closures[tid]

    def cycle(self, tid):
        """A dependency path from tid back to itself through open tasks, or None."""
        parents, pending = {}, [tid]
        while pending:
            current = pending.pop(0)
            for dep in sorted(self.deps.get(current, ())):
                if dep == tid:
                    nodes = [current]
                    while nodes[-1] != tid:
                        nodes.append(parents[nodes[-1]])
                    return nodes[::-1] + [tid]
                if dep in self.info and self.info[dep]['open'] and dep not in parents:
                    parents[dep] = current
                    pending.append(dep)
        return None

    def scope(self, requested):
        if requested is not None:
            for tid in requested:
                if tid not in self.info:
                    self.add('error', tid, 'unknown-task', f'no TODO.md task {tid}; check the ID')
            return [tid for tid in requested if tid in self.info]
        return [tid for tid, info in self.info.items() if info['open'] and info['section'] in ('Now', 'Next')]

    def run(self, requested=None):
        if not self.parsers.available:
            self.add('warning', '', 'engine-unavailable',
                     f'autowork engine scripts not importable from {ENGINE_DIR.name}/; Touches, duplicate-field, '
                     'serial and dependency checks are reduced; install the autowork skill beside docs-sync')
        scoped = self.scope(requested)
        open_tasks = [tid for tid, info in self.info.items() if info['open']]
        runnable = [tid for tid in open_tasks if self.info[tid]['section'] in ('Now', 'Next')]
        context = list(dict.fromkeys(runnable + scoped))
        named = {}
        for tid in open_tasks:
            for path in self.info[tid]['touches']:
                named.setdefault(path, set()).add(tid)
        for tid in scoped:
            self.task(tid)
            hot = self.hot(tid, named)
            self.shape(tid, hot, self.overlaps(tid, context, hot))
        return {'errors': self.errors, 'warnings': self.warnings}

    def task(self, tid):
        info = self.info[tid]
        body, fields = info['body'], info['fields']
        if len(self.bodies[tid]) > 1:
            self.add('error', tid, 'duplicate-task',
                     f'{len(self.bodies[tid])} TODO.md bodies share this ID; keep one body or allocate a new ID')
        labels = self.parsers.labels(body)
        duplicated = [label for label in DUPLICATE_LABELS if labels.count(label) > 1]
        if all(label in labels for label in goals.CHECK_LABELS):
            duplicated.append('Checks and Verification')
        for label in duplicated:
            self.add('error', tid, 'duplicate-field', f'`{label}:` appears more than once; merge into one field')
        for label in REQUIRED:
            if label not in duplicated and not fields.get(label):
                self.add('error', tid, 'missing-field', f'missing `{label}:`; the runner skips a task without it')
        if (not goals.task_checks(fields) and not any(label in duplicated for label in goals.CHECK_LABELS)
                and 'Checks and Verification' not in duplicated):
            self.add('error', tid, 'missing-field',
                     'missing `Checks:`; add the exact test commands the reviewer runs')
        self.touches(tid)
        self.dependencies(tid)
        if info['open'] and 'Touches' not in duplicated:
            for what in missing_check_targets(self.repo, goals.task_checks(fields), info['touches']):
                self.add('error', tid, 'missing-check-target',
                         f'Checks target not found: {what}; it is not on disk and no Touches path creates it; '
                         'fix the command or add the new test file to `Touches:`')

    def touches(self, tid):
        info = self.info[tid]
        fields = info['fields']
        if info['bad_touches']:
            self.add('error', tid, 'invalid-touches',
                     f'{info["bad_touches"]}; write `Touches:` as a comma list of repository paths')
            return
        if not info['touches']:
            resources = fields.get('Resources', '')
            reason = re.sub(r'^[\W_]*exclusive\b[\W_]*', '', resources.strip(), flags=re.I)
            if info['open'] and info['section'] in ('Now', 'Next') and not (
                    self.parsers.exclusive(fields) and reason):
                self.add('error', tid, 'missing-touches',
                         'missing `Touches:`; list the files this task changes, or declare '
                         '`Resources: exclusive — <reason>` for a task that cannot name them')
            return
        coordinator = [p for p in info['touches']
                       if p.rstrip('/') in self.parsers.coordinator or Path(p.rstrip('/')).name == 'BLOCKERS.md']
        if coordinator:
            self.add('error', tid, 'coordinator-touches',
                     f'Touches names coordinator file(s) {", ".join(coordinator)}; the coordinator owns '
                     'them, remove them from `Touches:`')

    def dependencies(self, tid):
        unknown = sorted(dep for dep in self.deps[tid] if dep not in self.known)
        if unknown:
            self.add('error', tid, 'unknown-dependency',
                     f'Dependencies names unknown task(s) {", ".join(unknown)}; fix the ID or remove it')
        if self.info[tid]['open']:
            path = self.cycle(tid)
            if path:
                self.add('error', tid, 'dependency-cycle',
                         'dependency cycle ' + ' -> '.join(path) + '; remove one `Dependencies:` edge')

    def hot(self, tid, named):
        """{path: reason} for this task's hot paths: named by many open tasks, or a very long file."""
        found = {}
        for path in self.info[tid]['touches']:
            count = len(named.get(path, ()))
            if count >= HOT_TASKS:
                found[path] = f'named by {count} open tasks'
                continue
            target = self.repo / path
            if not path.endswith('/') and target.is_file():
                lines = _line_count(target, self.lines)
                if lines > HOT_LINES:
                    found[path] = f'{lines} lines'
        return found

    def overlaps(self, tid, context, hot):
        """One warning per shared path, naming every independent open task that also declares it.
        Returns the paths reported, whose hot-file note this line already carries."""
        reported = set()
        independent = [other for other in context if other != tid
                       and other not in self.closure(tid) and tid not in self.closure(other)]
        for path in self.info[tid]['touches']:
            # A file that does not exist yet is shared only with a task naming it exactly.
            new = not any(ch in path for ch in '*?[') and not path.endswith('/') and not (self.repo / path).exists()
            others = [other for other in independent
                      if any(q == path if new else self.parsers.intersects(path, q)
                             for q in self.info[other]['touches'])]
            if not others:
                continue
            reported.add(path)
            shown = ', '.join(others[:SHOW_OTHERS]) + (f', +{len(others) - SHOW_OTHERS}'
                                                      if len(others) > SHOW_OTHERS else '')
            subject = f'hot file {path} ({hot[path]})' if path in hot else path
            plural = 'task' if len(others) == 1 else 'tasks'
            fix = f'add `Dependencies: {others[0]}`' if len(others) == 1 else 'add `Dependencies:`'
            self.warnings.append({'task': tid, 'code': 'touches-overlap', 'others': others,
                                  'message': f'{subject} is also in Touches of {len(others)} independent open '
                                             f'{plural} ({shown}): {fix} or re-cut so one task owns it'})
        return reported

    def shape(self, tid, hot, reported):
        info = self.info[tid]
        touches, fields = info['touches'], info['fields']
        rest = [f'{path} ({why})' for path, why in hot.items() if path not in reported]
        if rest:
            self.add('warning', tid, 'hot-file', f'hot file(s) {", ".join(rest)}; expect merge conflicts, '
                     'order these tasks with `Dependencies:` or narrow the change')
        directories = [p for p in touches if p.endswith('/') or (self.repo / p).is_dir()]
        if directories:
            self.add('warning', tid, 'directory-touches',
                     f'Touches names directory {", ".join(directories)}; name the files so overlap is precise')
        serial = [p for p in touches if self.parsers.serial(self.repo, p)]
        if serial:
            self.add('warning', tid, 'serial-path',
                     f'protected/serial path(s) {", ".join(serial)} serialize this task with other serial work; '
                     'split the manifest/schema/CI change into its own small task, or narrow a glob that could match one')
        if len(touches) > MAX_TOUCHES:
            self.add('warning', tid, 'too-many-touches',
                     f'{len(touches)} Touches entries (> {MAX_TOUCHES}); split the task')
        acceptance = fields.get('Acceptance', '')
        if acceptance:
            count = _acceptance_count(acceptance)
            if count > MAX_ACCEPTANCE:
                self.add('warning', tid, 'too-many-acceptance',
                         f'{count} acceptance criteria (> {MAX_ACCEPTANCE}); split the task')
            if not re.search(r'\btest_\w|\w_test\b|\.test\.\w|\S::\w', acceptance):
                self.add('warning', tid, 'acceptance-no-test',
                         'Acceptance names no test; name the `test_...` or `path::name` that proves it')
        if len(info['body']) > MAX_BODY:
            self.add('warning', tid, 'long-body',
                     f'body is {len(info["body"])} characters (> {MAX_BODY}); move history to the archive or a linked doc')


def lint(repo, tasks=None):
    """{'errors': [...], 'warnings': [...]}, each {task, code, message}."""
    return Linter(repo).run(list(tasks) if tasks is not None else None)


def report(repo, tasks=None, *, as_json=False, strict=False, out=sys.stdout):
    result = lint(repo, tasks)
    if as_json:
        print(json.dumps(result, indent=2), file=out)
    else:
        for kind, rows in (('ERROR', result['errors']), ('WARNING', result['warnings'])):
            for row in rows:
                print(f"{kind} {row['task'] or '-'} {row['code']}: {row['message']}", file=out)
        if not result['errors'] and not result['warnings']:
            print('ok', file=out)
    return 1 if result['errors'] or (strict and result['warnings']) else 0


def task_list(value):
    if not value:
        return None
    return list(dict.fromkeys(t.strip() for t in value.split(',') if t.strip()))


def add_arguments(parser):
    parser.add_argument('repo')
    parser.add_argument('--tasks', default='', help='comma-separated task IDs (default: open Now/Next tasks)')
    parser.add_argument('--json', action='store_true', help='print {"errors": [...], "warnings": [...]}')
    parser.add_argument('--strict', action='store_true', help='exit 1 on warnings too')


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    add_arguments(parser)
    a = parser.parse_args(argv)
    return report(a.repo, task_list(a.tasks), as_json=a.json, strict=a.strict)


if __name__ == '__main__':
    sys.exit(main())
