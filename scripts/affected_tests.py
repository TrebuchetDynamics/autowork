#!/usr/bin/env python3
"""Which offline test modules a change can affect, and why; `--run` runs only those.

    python3 scripts/affected_tests.py [--base REV] [--run] [--json] [-k PATTERN]

The change is everything between BASE (default: where HEAD left origin/main, else main) and the
working tree, untracked files included. A test module is selected when it changed itself, or
when it reaches a changed file through what it imports (``import parallel_integrate``,
``from pi_autowork import coordinator``) or the repository files it names (a script it runs, a
document it reads), followed transitively. Each selection prints the chain that selected it.
A change to the check itself, CI or packaging selects the whole suite, as does `--full`.

Workers and reviewers ran whole test directories, or the full check, for a change that two
modules could reach; this runs those two.
"""
import argparse
import ast
from collections import deque
import runpy
from types import SimpleNamespace
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
TEXT = ('.py', '.sh', '.md', '.json', '.toml', '.yml', '.yaml', '.js', '.mjs', '.txt', '.cfg')
# What every test depends on without naming it: the whole suite.
FULL = ('scripts/check.py', 'scripts/affected_tests.py', 'requirements-test.txt', 'package.json', '.github/')
MENTION = re.compile(r'[A-Za-z0-9_./-]*[A-Za-z0-9_-]\.(?:py|sh|md|json|toml|ya?ml|js|mjs|txt|cfg)\b')


def git(*args):
    result = subprocess.run(['git', '-C', str(ROOT), *args], capture_output=True, text=True)
    return result.stdout if result.returncode == 0 else None


def default_base():
    for ref in ('origin/main', 'main'):
        if (base := git('merge-base', 'HEAD', ref)):
            return base.strip()
    return 'HEAD'


def changed_files(base):
    tracked = (git('diff', '--name-only', '--no-renames', base) or '').split('\n')
    untracked = (git('ls-files', '--others', '--exclude-standard') or '').split('\n')
    return sorted({p for p in tracked + untracked if p})


def check_module():
    # Loading the inventory must not leave bytecode in a landing checkout.
    return SimpleNamespace(**runpy.run_path(str(ROOT / 'scripts/check.py')))


def repository_files():
    listed = (git('ls-files') or '').split('\n') + (git('ls-files', '--others', '--exclude-standard') or '').split('\n')
    # Extensionless scripts too (tmux/tx): tests name them by path.
    return sorted({p for p in listed if p and (p.endswith(TEXT) or '.' not in Path(p).name) and (ROOT / p).is_file()})


def module_name(path):
    """Canonical source names, including the stable pre-Src public entry names."""
    name = path.removesuffix('.py').replace('/', '.')
    if name.startswith('Src.'):
        name = name[4:]
    elif name.startswith('pi-autowork.pi_autowork.'):
        name = name[len('pi-autowork.'):]
    elif name.startswith('pi-autowork.engine.'):
        name = 'pi_autowork.engine.' + name[len('pi-autowork.engine.'):]
    return name.removesuffix('.__init__')


def python_references(source, path=''):
    """(top and lazy imported module names, text of string literals). Paths count
    only in string literals, not comments or docstrings: a comment naming pi-autowork.sh made a
    state module depend on the whole runner."""
    try:
        tree = ast.parse(source)
    except (SyntaxError, ValueError):
        return set(), set(), source
    top, lazy, strings = set(), set(), []
    docstrings = {id(node.body[0].value) for node in ast.walk(tree)
                  if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                  and node.body and isinstance(node.body[0], ast.Expr)
                  and isinstance(node.body[0].value, ast.Constant)}
    module_level = {id(node) for node in tree.body}
    for node in ast.walk(tree):
        names = None
        if isinstance(node, ast.Import):
            names = {alias.name for alias in node.names}
        elif isinstance(node, ast.ImportFrom):
            prefix = node.module or ''
            if node.level:
                package = module_name(path).split('.')
                if Path(path).name != '__init__.py':
                    package.pop()
                package = package[:len(package) - node.level + 1]
                prefix = '.'.join([*package, *([prefix] if prefix else [])])
            names = {prefix, *(prefix + '.' + alias.name for alias in node.names if alias.name != '*')} - {''}
        elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
            strings.append(node.value)
        if names:
            (top if id(node) in module_level else lazy).update(names)
    return top, lazy, '\n'.join(strings)


CODE = ('.py', '.sh', '.js', '.mjs')


def dependency_graph(files, tests=(), *, conservative=False):
    """{file: {files it imports or names}}. Only code depends on anything: a document or data
    file is read, it does not run what it mentions (CHANGELOG.md and TODO.archive.md name
    hundreds of files, and through them every change reached 107 of 120 test modules).
    Conservative landing selection also retains named test-file dependencies."""
    tests = set(tests)
    stems, basenames, modules = {}, {}, {}
    for path in files:
        name = Path(path).name
        basenames.setdefault(name, set()).add(path)
        if path.endswith('.py'):
            stems.setdefault(Path(path).stem, set()).add(path)
            modules.setdefault(module_name(path), set()).add(path)
            if conservative and Path(path).name == '__init__.py':
                stems.setdefault(Path(path).parent.name, set()).add(path)
    known = set(files)
    extensionless = {p for p in files if '/' in p and '.' not in Path(p).name}
    graph = {}
    for path in files:
        # A file whose change already selects the whole suite needs no dependencies of its own:
        # check.py names every excluded module, and through them tests that run it reached a
        # skill's SKILL.md.
        if not (path.endswith(CODE) or path in extensionless) or path.startswith(FULL):
            continue
        try:
            text = (ROOT / path).read_text(errors='replace')
        except OSError:
            continue
        deps = set()
        # Public adapter -> canonical owner, even while independent migrations land.
        canonical = module_name(path)
        if path.startswith('pi-autowork/'):
            deps |= {p for p in modules.get(canonical, ()) if p.startswith('Src/')}
        if conservative and path.endswith('.py'):
            # Loading a package member executes every ancestor package initializer,
            # including unchanged initializers that import a changed dependency.
            deps |= {str(parent / '__init__.py') for parent in Path(path).parents
                     if parent != Path('.') and str(parent / '__init__.py') in known}
        if path.endswith('.py'):
            # An import inside a function is a dependency of the module that makes it, not of
            # everything above it: task_prepare imports fleet_view for one path, and through the
            # shared store fixture that tied 60 engine tests to the fleet view.
            top, lazy, text = python_references(text, path)
            for name in top | (lazy if conservative or path in tests else set()):
                deps |= modules.get(name, set())
                if '.' not in name:
                    # Old flat engine imports and test-specific path setup can be ambiguous.
                    deps |= stems.get(name, set())
                for index in range(1, len(name.split('.'))):
                    prefix = '.'.join(name.split('.')[:index])
                    deps |= {p for p in modules.get(prefix, ()) if Path(p).name == '__init__.py'}
        for token in set(MENTION.findall(text)):
            token = token.lstrip('./')
            candidates = basenames.get(Path(token).name, set())
            if conservative:
                # Split paths such as ROOT / 'data' / 'config.json' can be ambiguous.
                # All plausible targets are safer than silently discarding an edge.
                named = ({p for p in candidates if p == token or p.endswith('/' + token)}
                         if '/' in token else candidates)
            elif token in known:
                named = {token}
            else:  # advisory mode prefers precision over the landing gate's conservatism
                named = ({p for p in candidates if p.endswith('/' + token)} if '/' in token
                         else candidates if len(candidates) == 1 else set())
            deps |= named if conservative else named - tests
        deps |= {p for p in extensionless if p in text}
        deps.discard(path)
        graph[path] = deps
    return graph


def select(changed, base='HEAD', *, conservative=False):
    """(tests, reasons, full): the test modules to run, why each, and whether the whole suite."""
    checker = check_module()
    tests = {p.relative_to(ROOT).as_posix() for p in checker.discover_tests(ROOT)}
    if not changed:
        return [], {}, False
    def whole(reason):
        return sorted(tests), {t: reason + ': the whole suite' for t in tests}, True

    full = [p for p in changed if p.startswith(FULL)]
    if conservative:
        # Imports cannot model implicit fixture, CI and build consumers.
        full += [p for p in changed if
                 Path(p).name in ('conftest.py', '__init__.py', 'setup.py', 'setup.cfg',
                                  'pyproject.toml', 'tox.ini', 'Makefile', 'Dockerfile')
                 or Path(p).name.startswith(('requirements', 'package', 'Pipfile', 'uv.lock', 'poetry.lock'))
                 or p.startswith(('.github/', '.gitlab', '.circleci/', 'ci/'))
                 or any(p.startswith(d + '/') for d in checker.TEST_DIRS) and p not in tests]
    if full:
        return whole(f'{full[0]} changed')
    files = repository_files()
    graph = dependency_graph(sorted(set(files) | set(changed)), tests, conservative=conservative)
    reverse = {}
    for path, deps in graph.items():
        for dep in deps:
            reverse.setdefault(dep, set()).add(path)
    if conservative:
        for changed_path in changed:
            reached, pending = set(), [changed_path]
            while pending:
                path = pending.pop()
                if path in reached:
                    continue
                reached.add(path)
                pending.extend(reverse.get(path, ()))
            if not reached & tests:
                return whole(f'{changed_path} has no resolved test mapping')
            for path in reached:
                if path.endswith('.py'):
                    try:
                        ast.parse((ROOT / path).read_text(encoding='utf-8'))
                    except (OSError, SyntaxError, ValueError, UnicodeError):
                        return whole(f'{path} cannot be resolved')
    reason, queue = {}, deque()
    for path in changed:
        reason[path] = [path]
        queue.append(path)
    while queue:
        path = queue.popleft()
        for user in sorted(reverse.get(path, ())):
            if user not in reason:
                reason[user] = reason[path] + [user]
                queue.append(user)
    chosen = sorted(t for t in tests if t in reason)
    return (chosen, {t: ' <- '.join(reversed(reason[t])) if len(reason[t]) > 1 else 'changed' for t in chosen},
            conservative and bool(tests) and set(chosen) == tests)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split('\n\n')[0])
    parser.add_argument('--base', help='revision the change starts from (default: merge-base with origin/main)')
    parser.add_argument('--run', action='store_true', help='run the selected modules with scripts/check.py')
    parser.add_argument('--json', action='store_true', help='print the selection as JSON')
    parser.add_argument('--full', action='store_true', help='select the whole suite')
    parser.add_argument('-k', dest='pattern', help='passed to scripts/check.py with --run')
    args = parser.parse_args(argv)
    base = args.base or default_base()
    changed = changed_files(base)
    if args.full:
        changed = ['scripts/check.py']
    tests, reasons, full = select(changed, base, conservative=True)
    if args.json:
        print(json.dumps({'base': base, 'changed': changed, 'full': full, 'tests': tests, 'reasons': reasons}, indent=2))
    else:
        print(f'{len(changed)} changed file(s) since {base[:12]}; '
              + (f'the whole suite ({len(tests)} modules)' if full else f'{len(tests)} test module(s) affected'))
        if not full:
            for test in tests:
                print(f'  {test}  ({reasons[test]})')
        if not tests:
            print('  no test module reaches these changes')
    if not args.run or not tests:
        return 0
    command = [sys.executable, str(ROOT / 'scripts' / 'check.py'), *([] if full else tests),
               *(['-k', args.pattern] if args.pattern else [])]
    return subprocess.run(command, cwd=ROOT).returncode


if __name__ == '__main__':
    sys.exit(main())
