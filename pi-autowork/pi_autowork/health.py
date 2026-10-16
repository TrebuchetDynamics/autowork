"""Runner health: one status file per runner, stall detection and a fleet view.

The engine stays the only lifecycle authority. This module only reads its
``--parallel-status --json`` snapshot and records what the runner observed, so a
service that cannot make progress says so once, with the root blockers, instead
of polling quietly (four runners idled for seven hours on 2026-10-16).

    health.py update STATE_DIR < snapshot.json   # prints an announcement or nothing
    health.py fleet STATE_ROOT                   # one line per runner
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import time

SCHEMA = 1
STALL_AFTER = 1800      # seconds with nothing running while work waits
STALE_AFTER = 600       # a status this old means the runner is not cycling
MOVING = ('running', 'integrating', 'restarting')
IN_FLIGHT = ('dispatched', 'running', 'reported', 'integrating', 'integrated')  # unsafe to update under
NEEDS_PERSON = ('runner', 'held', 'claim', 'contract', 'outside', 'cycle')


def classify(snapshot, *, paused=False, stuck=0):
    """'working', 'paused', 'idle' (nothing waits) or 'blocked' (work waits, none runs).

    ``stuck`` integrations only wait for another session to leave the main checkout:
    they are in flight but make no progress (flutter, 2026-10-16)."""
    if snapshot.get('active_workers') or (snapshot.get('integration_queue') or 0) > stuck:
        return 'working'
    if paused:
        return 'paused'
    waiting = [t for t in snapshot.get('tasks', []) if t.get('state') == 'waiting']
    return 'blocked' if waiting or stuck else 'idle'


CAUSES = {'blocker': 'its worker reported a blocker', 'scope': 'changed files outside Touches',
          'scope_request': 'its worker needs files outside Touches',
          'overlap': "changed another task's files", 'report': 'report did not match its commit',
          'conflict': 'merge conflict', 'validation': 'validation failed', 'crash': 'worker died twice',
          'launch': 'worker could not start', 'contract_changed': 'its TODO entry changed',
          'moved': 'main kept moving during validation'}


def label(root):
    text = ' '.join(str(root['id']).split())
    width = 240 if root.get('kind') == 'runner' else 60  # a runner blocker names what to act on
    return (text[:width] + '…') if len(text) > width else text


def describe(root):
    what = {'runner': 'the runner cannot proceed', 'held': 'held for a person',
            'contract': 'its TODO entry is not runnable as written', 'claim': 'claimed by another session',
            'outside': 'outside condition or task not in Now/Next', 'cycle': 'dependency cycle',
            'running': 'running', 'integrating': 'being integrated', 'restarting': 'restarting'}
    kind = what.get(root['kind'], root['kind'])
    if root['kind'] == 'held' and root.get('cause'):
        kind += ': ' + CAUSES.get(root['cause'], root['cause'])
    return f"{label(root)} ({kind}, holds {root['blocks']})"


def update(state_dir, snapshot, *, now=None, runner=None, stall_after=STALL_AFTER):
    """Write status.json; return a line to announce, or None.

    A stall is announced once when it begins and again only when its root
    blockers change; working again ends the episode.
    """
    now = time.time() if now is None else now
    runner = runner or {}
    path = Path(state_dir) / 'status.json'
    try:
        previous = json.loads(path.read_text())
    except (OSError, ValueError):
        previous = {}
    if snapshot.get('outcome') != 'PARALLEL_STATUS' or not isinstance(snapshot.get('tasks'), list):
        # The engine could not answer (say its state lock was busy with a --status
        # reader): that is no observation, so keep the record and its stall clock.
        return None
    paused = float(runner.get('paused_until') or 0) > now
    state = classify(snapshot, paused=paused, stuck=int(runner.get('stuck_integrations') or 0))
    since = previous.get('since', now) if previous.get('state', '').replace('stalled', 'blocked') == state else now
    roots = list(snapshot.get('roots', []))
    if runner.get('blocker'):  # the runner cannot dispatch or integrate: no model, busy lease, drift
        waiting = sum(t.get('state') == 'waiting' for t in snapshot.get('tasks', [])) \
            + int(runner.get('stuck_integrations') or 0)
        roots.insert(0, dict(id=runner['blocker'], kind='runner', blocks=waiting, cause=None, reason=''))
    stuck = [r for r in roots if r.get('kind') in NEEDS_PERSON]
    if state == 'blocked' and now - since >= stall_after and stuck:
        state = 'stalled'
    keys = sorted(label(r) for r in stuck)
    announce = None
    if state == 'stalled' and (previous.get('state') != 'stalled' or previous.get('stall_roots') != keys):
        minutes = int((now - since) // 60)
        announce = (f"STALLED for {minutes} min: no task can run. Root blockers: "
                    + '; '.join(describe(r) for r in stuck[:5])
                    + (f' (+{len(stuck) - 5} more)' if len(stuck) > 5 else '')
                    + '. See pi-autowork.sh --status.')
    value = dict(schema=SCHEMA, updated_at=now, state=state, since=since,
                 active_workers=snapshot.get('active_workers', 0),
                 in_flight=sum(t.get('state') in IN_FLIGHT for t in snapshot.get('tasks', [])),
                 waiting=sum(t.get('state') == 'waiting' for t in snapshot.get('tasks', [])),
                 held=[dict(task=t['task'], cause=t.get('cause'), reason=t.get('reason'))
                       for t in snapshot.get('tasks', []) if t.get('state') == 'held'],
                 roots=roots[:10], stall_roots=keys if state == 'stalled' else [], **runner)
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)
    return announce


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def _service(name):
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', f'pi-autowork@{name}.service'],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return '-'
    return result.stdout.strip() or '-'


def fleet(state_root, *, now=None, service=_service):
    """Rows for every runner state directory that has a status or runner record."""
    now = time.time() if now is None else now
    rows = []
    for folder in sorted(Path(state_root).glob('*/')):
        try:
            status = json.loads((folder / 'status.json').read_text())
        except (OSError, ValueError):
            status = {}
        try:
            runner = json.loads((folder / 'runner.json').read_text())
        except (OSError, ValueError):
            runner = {}
        repo = status.get('repo') or runner.get('repo')
        if not repo:
            continue
        name = Path(repo).name
        state = status.get('state', 'unknown')
        if not _alive(runner.get('pid')):
            state = 'not running'
        elif now - float(status.get('updated_at', 0)) > STALE_AFTER and state != 'working':
            state = 'not cycling'
        rows.append(dict(name=name, repo=repo, service=service(name), state=state,
                         since=status.get('since'), workers=status.get('active_workers', 0),
                         waiting=status.get('waiting', 0), roots=status.get('roots', []),
                         held=status.get('held', [])))
    return rows


def render(rows, *, now=None):
    now = time.time() if now is None else now
    if not rows:
        return 'No pi-autowork runners have recorded state yet.'
    lines = []
    for row in rows:
        since = f" for {int((now - row['since']) // 60)} min" if row.get('since') else ''
        lines.append(f"{row['name']:<24} service {row['service']:<9} {row['state']}{since}; "
                     f"{row['workers']} running, {row['waiting']} waiting")
        if row['state'] in ('stalled', 'blocked', 'not running', 'not cycling'):
            for root in [r for r in row['roots'] if r.get('kind') in NEEDS_PERSON][:3]:
                lines.append('    blocked by ' + describe(root))
    return '\n'.join(lines)


def main(argv):
    if len(argv) == 2 and argv[0] == 'update':
        runner = {k[len('PI_AUTOWORK_HEALTH_'):].lower(): v for k, v in os.environ.items()
                  if k.startswith('PI_AUTOWORK_HEALTH_')}
        stall = int(runner.pop('stall_after', STALL_AFTER))
        line = update(argv[1], json.load(sys.stdin), runner=runner, stall_after=stall)
        if line:
            print(line)
        return 0
    if len(argv) == 2 and argv[0] == 'fleet':
        print(render(fleet(argv[1])))
        return 0
    print('usage: health.py update STATE_DIR < snapshot.json | health.py fleet STATE_ROOT', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
