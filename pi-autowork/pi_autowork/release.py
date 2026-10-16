"""Decide whether the shared toolset package may be updated now.

`pi update` replaces the one package every runner on the machine loads, and the
engine is re-read on each call, so an update under a task in flight mixes two
releases. An update is safe only at a fleet-wide checkpoint, and only to a
release that can read the current execution state:

- no other live runner has a task dispatched, running, reported, integrating or
  integrated (from its status.json; this runner's caller checks itself);
- the new release, read from Git before anything is installed, lists the current
  STATE_SCHEMA in its STATE_SCHEMA_READS.

    release.py check STATE_ROOT OWN_STATE_DIR TOOLSET   # prints JSON; exit 0 when safe
"""
import ast
import json
import os
from pathlib import Path
import re
import subprocess
import sys

STATE_FILE = 'skills/autowork/scripts/parallel_state.py'


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def busy_runners(state_root, own):
    found = []
    for folder in sorted(Path(state_root).glob('*/')):
        if folder.resolve() == Path(own).resolve():
            continue
        try:
            status = json.loads((folder / 'status.json').read_text())
            runner = json.loads((folder / 'runner.json').read_text())
        except (OSError, ValueError):
            continue
        if _alive(runner.get('pid')) and int(status.get('in_flight') or 0) > 0:
            found.append(f"{Path(runner.get('repo', folder.name)).name} ({status['in_flight']} in flight)")
    return found


def schema(text, name, default):
    match = re.search(rf'^{name} = (.+)$', text, re.M)
    if not match:
        return default  # releases before the declaration wrote and read schema 1
    return ast.literal_eval(match[1].split('#')[0].strip())  # fetched text: parsed, never executed


def _git(toolset, *argv):
    return subprocess.run(['git', '-C', str(toolset), *argv], capture_output=True, text=True, timeout=120)


def check(state_root, own, toolset):
    busy = busy_runners(state_root, own)
    if busy:
        return dict(ok=False, reason='other runners have work in flight: ' + ', '.join(busy))
    fetched = _git(toolset, 'fetch', '-q', 'origin', 'HEAD')
    if fetched.returncode:
        return dict(ok=False, reason='could not fetch the toolset: ' + fetched.stderr.strip()[:200])
    new_rev = _git(toolset, 'rev-parse', '--short', 'FETCH_HEAD').stdout.strip()
    if new_rev and new_rev == _git(toolset, 'rev-parse', '--short', 'HEAD').stdout.strip():
        return dict(ok=False, current=True, reason='already at the newest release')
    shown = _git(toolset, 'show', f'FETCH_HEAD:{STATE_FILE}')
    if shown.returncode:
        return dict(ok=False, reason=f'the new release {new_rev} has no {STATE_FILE}')
    try:
        current = schema((Path(toolset) / STATE_FILE).read_text(), 'STATE_SCHEMA', 1)
        reads = schema(shown.stdout, 'STATE_SCHEMA_READS', (1,))
    except (OSError, SyntaxError, ValueError, TypeError):
        return dict(ok=False, reason='could not read the state schema declarations')
    if current not in tuple(reads):
        return dict(ok=False, reason=f'release {new_rev} cannot read this state (schema {current}; it reads {list(reads)})')
    return dict(ok=True, new_rev=new_rev, schema=current)


def main(argv):
    if len(argv) == 4 and argv[0] == 'check':
        result = check(*argv[1:])
        print(json.dumps(result))
        return 0 if result['ok'] else 1
    print('usage: release.py check STATE_ROOT OWN_STATE_DIR TOOLSET', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
