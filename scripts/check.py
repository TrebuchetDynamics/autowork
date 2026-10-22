#!/usr/bin/env python3
"""Run owned offline unittest suites; never import tests while building inventory."""
import argparse
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
from fnmatch import fnmatchcase
import math
import runpy
import os
from pathlib import Path
import signal
import subprocess
import sys
import time

TEST_DIRS = ('tests', 'pi-autowork/engine', 'skills/docs-sync/scripts',
             'skills/git-commit-push/scripts', 'pi-autowork/tests')
EXCLUSIONS = {
    'tests/integration_plugin.py':
        ('integration', 'requires the optional Hermes loader environment'),
    'tests/integration_autoresearch.py':
        ('integration', 'requires Hermes loader, CLI queue and gateway routing; no model or network calls'),
    'tests/integration_bundle.py':
        ('integration', 'requires an existing isolated Hermes installation'),
}
# Modules whose tests run in several processes: tests/test_pi_autowork.py alone took
# 764s of a 1324s run as one process, while its tests are independent runner fixtures.
SPLIT = {'tests/test_pi_autowork.py': 12, 'pi-autowork/engine/test_parallel_integrate.py': 4}
LIVE_FLAGS = ('CONTAINMENT_LINUX_TESTS', 'RUN_CONTROLLER_BRIDGE_LINUX',
              'HERMES_NATIVE_HANDOFF_TEST', 'HERMES_NATIVE_REGISTRATION_TEST')


def discover_tests(root):
    """Only direct test_*.py children of the maintained test directories."""
    root = Path(root).resolve()
    tests = []
    for directory in TEST_DIRS:
        folder = root / directory
        if (not folder.is_dir()
                or any((root / parent).is_symlink()
                       for parent in (Path(directory), *Path(directory).parents)
                       if parent != Path('.'))):
            continue
        for path in sorted(folder.glob('test_*.py')):
            if (path.is_file() and not path.is_symlink()
                    and path.relative_to(root).as_posix() not in EXCLUSIONS):
                tests.append(path)
    return tests


def test_ids(path):
    """`module.Class.test_name` for each test method, read with ast so nothing is imported;
    empty when the module defines none that way."""
    try:
        tree = ast.parse(path.read_text(encoding='utf-8'), str(path))
    except (OSError, SyntaxError, ValueError):
        return []
    return [f'{path.stem}.{node.name}.{item.name}' for node in tree.body if isinstance(node, ast.ClassDef)
            for item in node.body if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
            and item.name.startswith('test')]


def units(root, tests, pattern=None):
    """Each module runs in its own process; a module in SPLIT spreads its tests round-robin
    over that many processes."""
    for path in tests:
        shards = SPLIT.get(path.relative_to(root).as_posix(), 1)
        ids = test_ids(path) if shards > 1 else []
        if len(ids) > 1:
            if pattern:
                match = pattern if '*' in pattern else f'*{pattern}*'
                ids = [name for name in ids if fnmatchcase(name, match)]
            for index in range(min(shards, len(ids))):
                yield path.parent, ids[index::shards]
        else:
            yield path.parent, [path.stem]


def run_unit(directory, names, env, timeout, pattern=None):
    """Use the module runner so multiprocessing spawn has a real entry point.

    Returns (passed, output); the caller prints output so concurrent processes
    never interleave."""
    command = [sys.executable, '-m', 'unittest', *(['-k', pattern] if pattern else []), *names]
    with subprocess.Popen(command, cwd=directory, env=env, text=True,
                          encoding='utf-8', errors='replace',
                          stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                          start_new_session=os.name == 'posix') as process:
        try:
            output, _ = process.communicate(timeout=timeout)
        except subprocess.TimeoutExpired:
            if os.name == 'posix':
                os.killpg(process.pid, signal.SIGKILL)
            else:
                process.kill()
            output, _ = process.communicate()
            return False, output + f'TIMEOUT: {directory} after {timeout:g}s\n'
    return process.returncode == 0, output


def _cpu_times():
    """The host's aggregate CPU times from /proc/stat: user, nice, system, idle, iowait, ..."""
    with open('/proc/stat') as stat:
        return [int(x) for x in stat.readline().split()[1:]]


def busy_cpus(sample=0.5):
    """CPUs kept busy at normal priority over ``sample`` seconds, leaving out niced work: an
    Autowork runner nices its workers, so their load yields to this check rather than
    competing with it."""
    first = _cpu_times()
    time.sleep(sample)
    delta = [b - a for a, b in zip(first, _cpu_times())]
    total = sum(delta[:8]) or 1
    nice, idle, iowait = delta[1], delta[3], delta[4]
    return (os.cpu_count() or 1) * (total - nice - idle - iowait) / total


def default_jobs():
    """The CPUs the host has idle, 4 to 8: tests with fixed timing limits failed when 16
    processes ran at once on a host already at a load of 25 on 22 CPUs. Niced work does not
    count against a check that is not niced itself (the integration check every finished task
    waits on); a niced one, a worker's own check, counts the whole load as before."""
    try:
        if os.getpriority(os.PRIO_PROCESS, 0) == 0:
            idle = (os.cpu_count() or 1) - math.ceil(busy_cpus())
        else:
            idle = (os.cpu_count() or 1) - int(os.getloadavg()[0])
    except (OSError, ValueError):
        idle = 4
    return max(4, min(8, idle))


PUSH_GUARD = 'pi-autowork-push-disabled'


def without_push_guard(env):
    """``env`` without the runner's push guard (TOOLSET-186-07): a runner's main check and its
    reviewers inherit GIT_CONFIG_* entries that fail every push, and fixtures push to their own
    temporary repositories. Other GIT_CONFIG_* entries are kept, renumbered."""
    try:
        count = int(env.get('GIT_CONFIG_COUNT') or 0)
    except ValueError:
        return env
    entries = [(env.get(f'GIT_CONFIG_KEY_{i}', ''), env.get(f'GIT_CONFIG_VALUE_{i}', '')) for i in range(count)]
    kept = [(key, value) for key, value in entries if PUSH_GUARD not in key]
    if len(kept) == len(entries):
        return env
    env = {k: v for k, v in env.items() if k != 'GIT_CONFIG_COUNT' and not k.startswith(('GIT_CONFIG_KEY_', 'GIT_CONFIG_VALUE_'))}
    for i, (key, value) in enumerate(kept):
        env[f'GIT_CONFIG_KEY_{i}'], env[f'GIT_CONFIG_VALUE_{i}'] = key, value
    if kept:
        env['GIT_CONFIG_COUNT'] = str(len(kept))
    return env


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def affected_selection(root, revision_range):
    """Select on the merged checkout; invalid revision ranges never become empty successes."""
    root = Path(root).resolve()
    if revision_range.count('..') != 1 or '...' in revision_range or not all(revision_range.split('..')):
        raise ValueError('--affected requires BASE..HEAD')
    revisions = []
    for rev in revision_range.split('..'):
        result = subprocess.run(['git', '-C', str(root), 'rev-parse', '--verify', '--end-of-options',
                                 rev + '^{commit}'], capture_output=True, text=True)
        if result.returncode:
            raise ValueError(f'cannot resolve affected revision: {rev}')
        revisions.append(result.stdout.strip())
    result = subprocess.run(['git', '-C', str(root), 'diff', '--name-only', '-z', '--no-renames',
                             *revisions, '--'], capture_output=True, text=True, check=True)
    changed = sorted(p for p in result.stdout.split('\0') if p)
    selector = runpy.run_path(str(root / 'scripts/affected_tests.py'))
    tests, reasons, full = selector['select'](changed, revisions[0], conservative=True)
    return dict(base=revisions[0], head=revisions[1], changed=changed, tests=tests,
                reasons=reasons, full=full, core=['tree_guard', 'docs check', 'task-store validate'])


def affected_core(root):
    """Cheap repository contracts, even when no test modules were selected."""
    docs = root / 'skills/docs-sync/scripts/docs.py'
    tasks = root / 'pi-autowork/bin/autowork'
    commands = []
    if docs.is_file():
        commands.append([sys.executable, str(docs), 'check', str(root)])
    if tasks.is_file() and (root / 'tasks').is_dir():
        commands.append([str(tasks), 'tasks', 'validate', '--worktree', str(root)])
    return all(subprocess.run(command, cwd=root).returncode == 0 for command in commands)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('paths', nargs='*', help='owned test modules or directories (default: all offline tests)')
    parser.add_argument('-k', dest='pattern', help='unittest name pattern for focused reproduction (default: all tests)')
    parser.add_argument('--list', action='store_true', help='list inventory without importing or running tests')
    parser.add_argument('--affected', metavar='BASE..HEAD',
                        help='run affected modules and core contracts; unresolved changes select the full suite')
    parser.add_argument('--timeout', type=float, default=1800, help='seconds allowed per test process (default: 1800)')
    parser.add_argument('--jobs', type=positive_int,
                        help='test processes run at once (default: idle CPUs, 4 to 8; 1 runs them in order)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be positive')
    root = Path(__file__).resolve().parents[1]
    tests = discover_tests(root)
    selection = None
    if args.affected:
        if args.paths or args.pattern:
            parser.error('--affected cannot be combined with paths or -k')
        try:
            selection = affected_selection(root, args.affected)
        except (OSError, ValueError, subprocess.SubprocessError) as error:
            parser.error(str(error))
        print('Affected selection: ' + ('whole suite' if selection['full'] else 'affected modules'), flush=True)
        for name in selection['tests']:
            print(f'  {name} ({selection["reasons"][name]})', flush=True)
        print('Always run: ' + ', '.join(selection['core']), flush=True)
        tests = [test for test in tests if test.relative_to(root).as_posix() in selection['tests']]
    if args.paths:
        selected = set()
        for name in args.paths:
            path = (root / name).resolve()
            matches = [test for test in tests if test == path or path in test.parents]
            if not path.is_relative_to(root) or not matches:
                parser.error(f'no owned offline tests match: {name}')
            selected.update(matches)
        tests = [test for test in tests if test in selected]
    groups = defaultdict(list)
    for path in tests:
        groups[path.parent].append(path)
        if args.list:
            print(f'RUN {path.relative_to(root)}')
    excluded = 0
    for name, (category, reason) in EXCLUSIONS.items():
        if (root / name).is_file():
            print(f'EXCLUDE {name} [{category}]: {reason}', flush=True)
            excluded += 1
    print(f'Offline inventory: {len(tests)} modules in {len(groups)} directories; '
          f'{excluded} excluded. No model/native qualification.', flush=True)
    if args.list:
        return 0
    if not tests and (selection is None or selection['full']):
        print('FAIL: no offline tests found', flush=True)
        return 1
    # Cheap first: conflict markers, Python that does not compile or invalid JSON fail
    # every later test less clearly (markers twice reached main in Python modules).
    guard = root / 'scripts/tree_guard.py'
    if guard.is_file() and subprocess.run([sys.executable, str(guard), '--repo', str(root)]).returncode:
        print('FAIL: the tree guard refused this tree; no tests ran', flush=True)
        return 1
    if selection is not None and not affected_core(root):
        print('FAIL: an affected core contract refused this tree; no tests ran', flush=True)
        return 1
    # No live-test flags, and no settings of the runner whose worker or reviewer runs this:
    # tests start their own runners, and a service's PI_AUTOWORK_MAIN_CHECK and
    # PI_AUTOWORK_NO_FALLBACK failed them.
    env = without_push_guard({k: v for k, v in os.environ.items()
                              if k not in LIVE_FLAGS and not k.startswith(('PI_AUTOWORK_', 'AUTOWORK_'))})
    passed = failed = gated = 0
    work = list(units(root, tests, args.pattern))
    # Modules (and shards of split ones) are independent processes; output is still printed
    # whole, by directory and in order. Shards of split modules are the longest, so they start
    # first.
    order = sorted(range(len(work)), key=lambda i: len(work[i][1]) == 1 and '.' not in work[i][1][0])
    with ThreadPoolExecutor(max_workers=args.jobs or default_jobs()) as pool:
        futures = {i: pool.submit(run_unit, *work[i], env, args.timeout, args.pattern) for i in order}
        runs = [(work[i][0], futures[i]) for i in range(len(work))]
        for directory, modules in groups.items():
            print(f'CHECK {directory.relative_to(root)} ({len(modules)} modules)', flush=True)
            ok = True
            for result in [run for where, run in runs if where == directory]:
                unit_ok, output = result.result()
                print(output, end='', flush=True)
                gated += output.count('RESOURCE_GATE_SKIP:')
                ok = ok and unit_ok
            if ok:
                passed += 1
            else:
                failed += 1
    print(f'Offline result: {passed} test directories passed; {failed} failed; '
          f'{excluded} modules excluded.', flush=True)
    if gated:  # skipped, not failed: the host was busy (TOOLSET-193-54); a quieter run checks them
        print(f'Skipped by the host resource gate: {gated} test(s); run again at a lower load to check them.',
              flush=True)
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
