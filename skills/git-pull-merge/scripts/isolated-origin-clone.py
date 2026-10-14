#!/usr/bin/env python3
"""Clone an explicit delivery origin without local references or shared objects."""
import argparse
import json
import os
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('origin')
    parser.add_argument('destination', type=Path)
    parser.add_argument('--expected-main', required=True, help='Previously observed exact origin/main commit')
    args = parser.parse_args()
    destination = args.destination.absolute()
    if destination.exists() or destination.is_symlink():
        parser.error('destination already exists; preserve it and use a new private path')
    if len(args.expected_main) not in (40, 64) or any(c not in '0123456789abcdef' for c in args.expected_main):
        parser.error('--expected-main requires an exact lowercase commit hash')
    env = os.environ.copy()
    for name in ('GIT_DIR', 'GIT_WORK_TREE', 'GIT_INDEX_FILE', 'GIT_COMMON_DIR',
                 'GIT_OBJECT_DIRECTORY', 'GIT_ALTERNATE_OBJECT_DIRECTORIES', 'GIT_NAMESPACE'):
        env.pop(name, None)
    git = ['git', '-c', 'core.hooksPath=/dev/null', '-c', 'core.fsmonitor=false']
    subprocess.run(git + ['clone', '--no-local', '--branch', 'main', '--', args.origin, str(destination)], env=env, check=True)
    def read(*arguments):
        return subprocess.check_output(git + ['-C', str(destination), *arguments], env=env, text=True).strip()
    actual = read('rev-parse', 'refs/remotes/origin/main')
    alternates = Path(read('rev-parse', '--git-path', 'objects/info/alternates'))
    if not alternates.is_absolute():
        alternates = destination / alternates
    if actual != args.expected_main or read('rev-parse', '--is-shallow-repository') != 'false' or alternates.exists():
        raise SystemExit('clone held: origin/main changed, shallow history or borrowed objects; retained destination, no integration')
    print(json.dumps({'status': 'prepared', 'destination': str(destination), 'origin_main': actual,
                      'shallow': False, 'borrowed_objects': False, 'integration': False, 'push': False}))


if __name__ == '__main__':
    main()
