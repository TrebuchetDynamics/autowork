#!/usr/bin/env python3
"""Run owned offline unittest suites; never import tests while building inventory."""
import argparse
import ast
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import math
import os
from pathlib import Path
import signal
import subprocess
import sys

TEST_DIRS = ('tests', 'skills/autowork/scripts', 'skills/docs-sync/scripts',
             'skills/git-commit-push/scripts', 'pi-autowork/tests')
EXCLUSIONS = {
    'skills/docs-sync/scripts/test_goal_gap_regression.py':
        ('model', 'runs Hermes chat and writes profile receipts at import'),
    'skills/autowork/scripts/test_native_lifecycle_controls.py':
        ('native', 'requires an installed Hermes interpreter and native CLI'),
    'skills/autowork/scripts/test_native_handoff.py':
        ('native', 'optional installed Hermes native handoff suite'),
    'skills/autowork/scripts/test_native_containment_linux.py':
        ('native', 'optional installed Linux containment backend'),
    'skills/autowork/scripts/test_controller_bridge_linux.py':
        ('native', 'optional installed Linux controller/backend composition'),
    'tests/integration_plugin.py':
        ('integration', 'requires the optional Hermes loader environment'),
    'tests/integration_autoresearch.py':
        ('integration', 'requires Hermes loader, CLI queue and gateway routing; no model or network calls'),
    'tests/integration_bundle.py':
        ('integration', 'requires an existing isolated Hermes installation'),
}
# Modules whose tests run in several processes: tests/test_pi_autowork.py alone took
# 764s of a 1324s run as one process, while its tests are independent runner fixtures.
SPLIT = {'tests/test_pi_autowork.py': 12, 'skills/autowork/scripts/test_parallel_integrate.py': 4}
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


def units(root, tests):
    """Each module runs in its own process; a module in SPLIT spreads its tests round-robin
    over that many processes."""
    for path in tests:
        shards = SPLIT.get(path.relative_to(root).as_posix(), 1)
        ids = test_ids(path) if shards > 1 else []
        if len(ids) > 1:
            for index in range(min(shards, len(ids))):
                yield path.parent, ids[index::shards]
        else:
            yield path.parent, [path.stem]


def run_unit(directory, names, env, timeout):
    """Use the module runner so multiprocessing spawn has a real entry point.

    Returns (passed, output); the caller prints output so concurrent processes
    never interleave."""
    command = [sys.executable, '-m', 'unittest', *names]
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


def positive_int(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError('must be a positive integer')
    return number


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--list', action='store_true', help='list inventory without importing or running tests')
    parser.add_argument('--timeout', type=float, default=1800, help='seconds allowed per test process (default: 1800)')
    parser.add_argument('--jobs', type=positive_int,
                        help='test processes run at once (default: CPU count, at most 16; 1 runs them in order)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.timeout) or args.timeout <= 0:
        parser.error('--timeout must be positive')
    root = Path(__file__).resolve().parents[1]
    tests = discover_tests(root)
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
    if not tests:
        print('FAIL: no offline tests found', flush=True)
        return 1
    env = dict(os.environ)
    for flag in LIVE_FLAGS:
        env.pop(flag, None)
    passed = failed = 0
    work = list(units(root, tests))
    # Modules (and shards of split ones) are independent processes; output is still printed
    # whole, by directory and in order.
    with ThreadPoolExecutor(max_workers=args.jobs or min(16, os.cpu_count() or 1)) as pool:
        runs = [(directory, pool.submit(run_unit, directory, names, env, args.timeout)) for directory, names in work]
        for directory, modules in groups.items():
            print(f'CHECK {directory.relative_to(root)} ({len(modules)} modules)', flush=True)
            ok = True
            for result in [run for where, run in runs if where == directory]:
                unit_ok, output = result.result()
                print(output, end='', flush=True)
                ok = ok and unit_ok
            if ok:
                passed += 1
            else:
                failed += 1
    print(f'Offline result: {passed} test directories passed; {failed} failed; '
          f'{excluded} modules excluded.', flush=True)
    return int(bool(failed))


if __name__ == '__main__':
    sys.exit(main())
