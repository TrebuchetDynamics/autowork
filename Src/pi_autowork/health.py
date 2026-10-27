"""Runner health: one status file per runner, stall detection and a fleet view.

The engine stays the only lifecycle authority. This module only reads its
``--parallel-status --json`` snapshot and records what the runner observed, so a
service that cannot make progress says so once, with the root blockers, instead
of polling quietly (four runners idled for seven hours on 2026-10-16).

    health.py update STATE_DIR < snapshot.json   # prints an announcement or nothing
    health.py fleet STATE_ROOT                   # one line per runner
"""
import hashlib
import json
import math
import os
import re
from pathlib import Path
import subprocess
import sys
import time

from pi_autowork.processes import running, start_time  # noqa: E402
from pi_autowork.engine import failure_policy  # noqa: E402

SCHEMA = 1
STALL_AFTER = 1800      # seconds with nothing running while work waits
STALE_AFTER = 600       # a status this old means the runner is not cycling
MOVING = ('running', 'integrating', 'restarting')
IN_FLIGHT = ('dispatched', 'running', 'reported', 'integrating', 'integrated')  # unsafe to update under
ACTION_ROOTS = ('runner', 'held', 'claim', 'contract', 'outside', 'cycle')
HOST_WAIT = 'waiting for the host'
LOAD_WAIT = r'^resource gate: load average (\S+) >= (\S+) CPUs$'


def needs_person(root):
    """Whether a root genuinely needs an owner decision. A held root is judged by the shared
    failure policy, not by its display kind: an exhausted technical hold is still visible, but it
    is Agent repair or engine recovery, not a question."""
    return failure_policy.disposition(root)['resolution_owner'] == failure_policy.OWNER


def requires_action(root):
    """A dependency cannot clear by ordinary waiting, regardless of who repairs its root."""
    return (root.get('kind') in ACTION_ROOTS
            and not (root.get('kind') == 'held' and root.get('cause') in ('overlap', 'task_wait')))


def classify(snapshot, *, paused=False, stuck=0):
    """Working, paused, idle (nothing waits or is held), host-waiting (load only), or blocked.

    ``stuck`` integrations only wait for another session to leave the main checkout:
    they are in flight but make no progress (flutter, 2026-10-16)."""
    if snapshot.get('active_workers') or (snapshot.get('integration_queue') or 0) > stuck:
        return 'working'
    if paused:
        return 'paused'
    waiting = [t for t in snapshot.get('tasks', []) if t.get('state') in ('waiting', 'held')]
    if waiting and not stuck and all(t.get('state') == 'waiting'
                                    and re.match(LOAD_WAIT, str(t.get('reason') or '')) for t in waiting):
        return HOST_WAIT
    return 'blocked' if waiting or stuck else 'idle'


CAUSES = {'blocker': 'its worker reported a blocker', 'scope': 'changed files outside Touches',
          'scope_request': 'its worker needs files outside Touches',
          'overlap': "changed another task's files; offered again once they are free", 'report': 'report did not match its commit',
          'conflict': 'merge conflict', 'validation': 'validation failed', 'crash': 'worker died twice',
          'empty': 'its worker stopped without a commit, changes or report',
          'no_change': 'its worker found nothing to change',
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
    if root['kind'] == 'outside' and root.get('deferred'):
        kind = 'deferred by owner'
    if root['kind'] == 'held' and root.get('cause') == 'overlap':
        kind = 'held'  # the engine offers it again by itself; no person is needed
    elif root['kind'] == 'held' and not needs_person(root):
        kind = 'engineering hold'  # visible, but an agent or the engine clears it
    if root['kind'] == 'held' and root.get('cause'):
        kind += ': ' + CAUSES.get(root['cause'], root['cause'])
    return f"{label(root)} ({kind}, holds {root['blocks']})"


# Why a task waits, as a person reads it: (pattern, group key, label). The key keeps one
# group per blocking task; the label names it. First match wins.
WAIT_KINDS = (
    (r'^wait for deferred (.+)$', 'deferred:{0}', 'wait for deferred {0}'),
    (r'^wait for (\d+) finished commits to merge', 'merge_backlog', 'wait for {0} finished commits to merge'),
    (r'^overlapping paths with (?:held |interrupted )?(\S+)', 'overlap:{0}', 'wait for {0} (overlapping files)'),
    (r'^serial path shared with (?:held )?(\S+)', 'serial:{0}', 'wait for {0} (serial files)'),
    (r'^priority (?:waits for|task) (\S+?):?(?:\s|$)', 'priority:{0}', 'wait behind {0}, which runs alone'),
    (r'^shared resource with (?:held )?(\S+)', 'resource:{0}', 'share a resource with {0}'),
    (r'^dependency', 'dependency', 'on dependencies'),
    (LOAD_WAIT, 'load', HOST_WAIT + ' (load {0} on {1} CPUs)'),
    (r'^resource gate', 'gate', 'on host memory or disk'),
    (r'^all \d+ worker slots busy', 'slots', 'for a free worker slot'),
    (r'^already running/live slot or held', 'claim', 'held by its record'),
    (r'^sequential task in progress', 'sequential', 'behind a sequential task'),
    (r'^not runnable', 'contract', 'not runnable as written'),
)


def waiting_groups(tasks, limit=8):
    """Waiting tasks grouped by why they wait, largest group first: [{label, count, tasks}]."""
    groups = {}
    for task in tasks:
        if task.get('state') != 'waiting':
            continue
        reason = ' '.join(str(task.get('reason') or 'waiting').split())
        for pattern, key, label in WAIT_KINDS:
            match = re.match(pattern, reason)
            if match:
                key, label = key.format(*match.groups()), label.format(*match.groups())
                break
        else:
            key, label = 'other:' + reason[:60], reason[:60]
        group = groups.setdefault(key, dict(label=label, count=0, tasks=[]))
        group['count'] += 1
        if len(group['tasks']) < 20:
            group['tasks'].append(task.get('task') or task.get('id') or '?')
    return sorted(groups.values(), key=lambda g: -g['count'])[:limit]


def stopped(tasks, roots):
    """(IDs, groups) of the waiting tasks that cannot move until something is resolved: their
    wait ends at a root that needs a person or a repair. An overlap hold lifts by itself, so the
    tasks behind it still wait; a runner blocker stops every waiting task. Groups are
    [{label, count, tasks}], largest first."""
    waiting = [t.get('task') for t in tasks if t.get('state') == 'waiting' and t.get('task')]
    ids, groups = set(), []
    for root in roots:
        if not requires_action(root):
            continue
        held = waiting if root.get('kind') == 'runner' else [t for t in root.get('tasks') or [] if t in waiting]
        fresh = [t for t in held if t not in ids]
        if fresh:
            ids.update(fresh)
            groups.append(dict(label=describe(root).rsplit(', holds ', 1)[0] + ')', count=len(fresh), tasks=fresh[:20]))
    return ids, sorted(groups, key=lambda g: -g['count'])


def status_error(status, now):
    """Failure text includes the age of evidence, not the age of this file write."""
    since = status['status_unavailable_since']
    stamp = status.get('snapshot_at')
    age = f'last snapshot {max(0, int(now - stamp))}s old' if stamp is not None else 'no successful snapshot'
    return f"status unavailable since {since:.0f}: {status['status_reason']}; {age}"


def write_status(path, value):
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps(value, indent=2) + '\n')
    os.replace(tmp, path)


def state_directory(state_root, repo, git_common=None):
    """Use the normal repository key, or recover it when Git cannot be read."""
    normal = Path(state_root) / hashlib.sha256((git_common or str(repo)).encode()).hexdigest()[:16]
    if normal.is_dir():
        return normal
    for folder in Path(state_root).glob('*/'):
        for name in ('status.json', 'runner.json'):
            try:
                if json.loads((folder / name).read_text()).get('repo') == str(repo):
                    return folder
            except (OSError, ValueError, AttributeError):
                pass
    return normal


def setup_stop(state_dir):
    try:
        runner = json.loads((Path(state_dir) / 'runner.json').read_text())
    except (OSError, ValueError):
        runner = {}
    if running(runner):
        return None
    try:
        return json.loads((Path(state_dir) / 'status.json').read_text()).get('stop_reason')
    except (OSError, ValueError):
        return None


def record_setup_stop(state_dir, repo, reason):
    """Persist an early refusal outside the repository, without hiding a live runner."""
    path = Path(state_dir)
    try:
        runner = json.loads((path / 'runner.json').read_text())
    except (OSError, ValueError):
        runner = {}
    if running(runner):
        return
    now = time.time()
    try:
        path.mkdir(parents=True, exist_ok=True)
        write_status(path / 'status.json', dict(schema=SCHEMA, repo=str(repo), updated_at=now, since=now,
                     state='not running', stop_reason=reason, blocker=reason, active_workers=0, waiting=0,
                     roots=[dict(id=reason, kind='runner', blocks=0)]))
    except OSError as error:
        print(f'pi-autowork: Cannot record setup stop in {path}: {error}', file=sys.stderr)


def clear_setup_stop(state_dir):
    path = Path(state_dir) / 'status.json'
    try:
        if json.loads(path.read_text()).get('stop_reason'):
            path.unlink()
    except (OSError, ValueError):
        pass


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
        # Keep the last observation and its stall clock across one failed read.
        # Repeated failures (or no observation yet) are unavailable; even during
        # this grace read, retain the evidence age rather than freshening rows.
        stamp = previous.get('snapshot_at')
        state = (previous.get('state', 'unavailable')
                 if stamp is not None and 'status_unavailable_since' not in previous else 'unavailable')
        value = dict(previous, **runner)
        value['task_source'] = previous.get('task_source') or dict(
            workspace=None, repository_identity=None, revision=None, observed_at=None)
        value.update(schema=SCHEMA, updated_at=now, state=state,
                     since=previous.get('since', now), snapshot_at=stamp,
                     snapshot_state=previous.get('snapshot_state', previous.get('state', 'unknown')),
                     snapshot_age_seconds=max(0, now - stamp) if stamp is not None else None,
                     status_unavailable_since=previous.get('status_unavailable_since', now),
                     status_reason=' '.join(str(snapshot.get('reason') or snapshot.get('outcome')
                                               or 'no answer from the engine').split()))
        value['status_error'] = status_error(value, now)
        write_status(path, value)
        return None
    paused = float(runner.get('paused_until') or 0) > now
    state = classify(snapshot, paused=paused, stuck=int(runner.get('stuck_integrations') or 0))
    if state == HOST_WAIT and runner.get('blocker'):
        state = 'blocked'  # a load observation must not hide a runner failure
    observed_state = previous.get('snapshot_state', previous.get('state', ''))
    since = previous.get('since', now) if observed_state.replace('stalled', 'blocked') == state else now
    roots = list(snapshot.get('roots', []))
    if runner.get('blocker'):  # the runner cannot dispatch or integrate: no model, busy lease, drift
        waiting = sum(t.get('state') == 'waiting' for t in snapshot.get('tasks', [])) \
            + int(runner.get('stuck_integrations') or 0)
        roots.insert(0, dict(id=runner['blocker'], kind='runner', blocks=waiting, cause=None, reason=''))
    stuck = [r for r in roots if r.get('kind') in ACTION_ROOTS]
    if state == 'blocked' and now - since >= stall_after and stuck:
        state = 'stalled'
    keys = sorted(label(r) for r in stuck)
    announce = None
    if state == 'stalled' and (observed_state != 'stalled' or previous.get('stall_roots') != keys):
        minutes = int((now - since) // 60)
        # Holds alone, each for another slot's files: the engine offers each commit again once
        # its files are free, so name it rather than leave it looking like a person's job.
        deadlock = all(r.get('kind') == 'held' and r.get('cause') == 'overlap' for r in stuck)
        announce = (f"STALLED for {minutes} min: no task can run"
                    + (' (held-ownership deadlock; resolving itself)' if deadlock else '') + ". Root blockers: "
                    + '; '.join(describe(r) for r in stuck[:5])
                    + (f' (+{len(stuck) - 5} more)' if len(stuck) > 5 else '')
                    + '. See pi-autowork.sh --status.')
    stuck_ids, stuck_groups = stopped(snapshot.get('tasks', []), roots)
    backlog = snapshot.get('merge_backlog') or {}
    was_paused = bool((previous.get('merge_backlog') or {}).get('paused'))
    if bool(backlog.get('paused')) != was_paused:
        if backlog.get('paused'):
            line = f'Fresh dispatch paused: wait for {backlog["count"]} finished commits to merge.'
            reason = backlog.get('reason') or runner.get('blocker')
            if reason:
                line += ' Integration waits: ' + ' '.join(str(reason).split())
        else:
            line = f'Fresh dispatch resumed: {backlog.get("count", 0)} finished commits remain to merge.'
        announce = '\n'.join(filter(None, (announce, line)))
    source = {key: (snapshot.get('task_source') or {}).get(key)
              for key in ('workspace', 'repository_identity', 'revision', 'observed_at')}
    stamp = source['observed_at']
    value = dict(schema=SCHEMA, updated_at=now, snapshot_at=stamp,
                 snapshot_age_seconds=max(0, now - stamp) if stamp is not None else None,
                 task_source=source, state=state, since=since,
                 active_workers=snapshot.get('active_workers', 0),
                 in_flight=sum(t.get('state') in IN_FLIGHT for t in snapshot.get('tasks', [])),
                 # A task a restart paused waits to resume: counted nowhere, it fell out of the fleet's Total.
                 # A wait that cannot clear by itself is ``stopped``, a Blocker, and not counted here.
                 waiting=sum(t.get('state') in ('waiting', 'interrupted') and t.get('task') not in stuck_ids
                             for t in snapshot.get('tasks', [])),
                 stopped=len(stuck_ids), stopped_groups=stuck_groups,
                 held=[dict(task=t['task'], cause=t.get('cause'), reason=t.get('reason'))
                       for t in snapshot.get('tasks', []) if t.get('state') == 'held'],
                 roots=roots[:10], stall_roots=keys if state == 'stalled' else [],
                 waiting_groups=waiting_groups([t for t in snapshot.get('tasks', []) if t.get('task') not in stuck_ids]),
                 merge_backlog=backlog,
                 # Every task, for the TUI's Tasks window: the groups above keep 20 of each.
                 # Additive display provenance; keep the legacy compact tasks rows intact.
                 task_observations=[dict(t) for t in snapshot.get('tasks', []) if t.get('task')],
                 tasks=[[t['task'], t.get('state') or '', t.get('cause') or '',
                          ' '.join(str(t.get('reason') or '').split())[:200]]
                        for t in snapshot.get('tasks', []) if t.get('task')],
                 max_workers=snapshot.get('max_workers'), **runner)
    write_status(path, value)
    return announce


def _service(name):
    try:
        result = subprocess.run(['systemctl', '--user', 'is-active', f'pi-autowork@{name}.service'],
                                capture_output=True, text=True, timeout=10)
    except (OSError, subprocess.SubprocessError):
        return '-'
    return result.stdout.strip() or '-'


def job_started(state_dir, role, task, now=None):
    """The runner's own Pi job (docs maintainer, provisioning, merge resolution) is running."""
    path = Path(state_dir) / 'job.json'
    tmp = path.with_suffix('.tmp')
    tmp.write_text(json.dumps({'role': role, 'task': task, 'started': time.time() if now is None else now,
                               'pid': os.getpid(), 'start_time': start_time(os.getpid())}) + '\n')
    os.replace(tmp, path)


def job_finished(state_dir):
    (Path(state_dir) / 'job.json').unlink(missing_ok=True)


def _repo(value):
    return isinstance(value, str) and bool(value.strip()) and '\0' not in value


def _time(value):
    # updated_at historically accepted numeric strings; never accept bool or NaN.
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        raise ValueError('expected finite timestamp')
    number = float(value)
    if not math.isfinite(number):
        raise ValueError('expected finite timestamp')
    return number if isinstance(value, str) else value


def _validate_observation(record, *, members=False, runner_record=False, main_check_record=False):
    """Validate only display-consumed fields, not the persisted writer schema."""
    if main_check_record and record:
        for key in ('state', 'rev'):
            if not isinstance(record.get(key), str):
                raise ValueError(f'invalid {key}: expected string')
    if 'status_unavailable_since' in record and not isinstance(record.get('status_reason'), str):
        raise ValueError('invalid status_unavailable_since: missing status_reason')
    if 'pid' in record and record['pid'] is not None:
        pid = record['pid']
        if isinstance(pid, bool) or not (type(pid) is int or isinstance(pid, str) and pid.isdecimal()):
            raise ValueError('invalid pid: expected integer process identity')
    for key in ('updated_at', 'snapshot_at', 'since', 'status_unavailable_since', 'started', 'at',
                'observed_at', 'started_at', 'phase_at', 'timeout'):
        if key == 'started' and runner_record:
            continue  # cli.acquire writes an ISO label, not a consumed job timestamp
        if key in record and record[key] is None and key in ('updated_at', 'status_unavailable_since', 'started', 'timeout'):
            raise ValueError(f'invalid {key}: expected finite timestamp')
        if record.get(key) is not None:
            try:
                record[key] = _time(record[key])
            except (ValueError, OverflowError) as exc:
                raise ValueError(f'invalid {key}: {exc}') from exc
    for key in ('active_workers', 'waiting', 'stopped', 'in_flight', 'max_workers', 'count', 'blocks', 'attempt'):
        if key in record and not (key == 'max_workers' and record[key] is None):
            if type(record[key]) is not int or record[key] < 0:
                raise ValueError(f'invalid {key}: expected nonnegative integer')
    for key in ('state', 'blocker', 'stop_reason', 'status_reason', 'role', 'task', 'id', 'kind',
                'cause', 'reason', 'label', 'workspace', 'repository_identity', 'revision',
                'rev', 'main_head', 'crashed', 'gated', 'slot_status'):
        required = key in ('state', 'blocker', 'stop_reason', 'status_reason', 'role', 'label',
                           'rev', 'crashed', 'gated')
        if main_check_record and key in ('crashed', 'gated') and record.get(key) is None:
            continue  # check_main_start carries absent crash/gate history as null
        if key in record and (required or record[key] is not None) and not isinstance(record[key], str):
            raise ValueError(f'invalid {key}: expected string')
    for key in ('task_source', 'maintainer', 'main_check', 'check_slot'):
        if key in record and record[key] is not None:
            if not isinstance(record[key], dict):
                raise ValueError(f'invalid {key}: expected object')
            try:
                _validate_observation(record[key], main_check_record=key == 'main_check')
            except ValueError as exc:
                raise ValueError(f'{key}: {exc}') from exc
    for key in ('roots', 'held', 'waiting_groups', 'stopped_groups', 'task_observations', 'tasks'):
        if key not in record:
            continue
        if not isinstance(record[key], list):
            raise ValueError(f'invalid {key}: expected array')
        if key == 'tasks' and members:
            if not all(isinstance(item, str) for item in record[key]):
                raise ValueError('invalid tasks: expected string member IDs')
            continue
        for item in record[key]:
            # Legacy compact task rows carry no execution identity.
            if key == 'tasks' and isinstance(item, list) and all(isinstance(v, str) for v in item):
                continue
            if key in ('tasks',) and isinstance(item, str):  # root/group member IDs
                continue
            if not isinstance(item, dict):
                raise ValueError(f'invalid {key}: expected object rows')
            required = ('id', 'kind', 'blocks') if key == 'roots' else (
                ('label', 'count') if key in ('waiting_groups', 'stopped_groups') else ())
            if any(field not in item for field in required):
                raise ValueError(f'invalid {key}: missing {required}')
            try:
                _validate_observation(item, members=key in ('roots', 'waiting_groups', 'stopped_groups'))
            except ValueError as exc:
                raise ValueError(f'{key}: {exc}') from exc
    for key in ('failures', 'flaky'):
        if main_check_record and key == 'failures' and record.get(key) is None:
            continue  # no previous failing check; consumers use failures or []
        if key in record and not isinstance(record[key], list):
            raise ValueError(f'invalid {key}: expected array')
    for key in ('errors', 'changed', 'triggers'):
        if key in record and not (isinstance(record[key], list)
                                 and all(isinstance(item, str) for item in record[key])):
            raise ValueError(f'invalid {key}: expected string array')


def read_observation(path):
    """Read a runtime object; quarantine bad values, retaining only valid repo identity.

    Missing files retain historical startup behavior. Errors are display-only and
    include the source path; no reader repairs or rewrites the underlying bytes.
    """
    record = {}
    try:
        record = json.loads(Path(path).read_text())
        if not isinstance(record, dict):
            raise ValueError('expected an object')
        if 'repo' in record and not _repo(record['repo']):
            raise ValueError('invalid repo: expected nonempty path string')
        _validate_observation(record, runner_record=Path(path).name == 'runner.json')
    except FileNotFoundError:
        return {}, []
    except (OSError, UnicodeError, ValueError, OverflowError, RecursionError) as exc:
        identity = record.get('repo') if isinstance(record, dict) else None
        return ({'repo': identity} if _repo(identity) else {}), [f'{path}: {exc}']
    return record, []


def current_job(folder, *, errors=None):
    """The runner's own job while its process lives, else None."""
    job, problems = read_observation(Path(folder) / 'job.json')
    if errors is not None:
        errors.extend(problems)
    return job if not problems and running(job) else None


def fleet(state_root, *, now=None, service=_service):
    """Rows for every runner state directory that has a status or runner record."""
    now = time.time() if now is None else now
    rows = []
    for folder in sorted(Path(state_root).glob('*/')):
        status, errors = read_observation(folder / 'status.json')
        runner, problems = read_observation(folder / 'runner.json')
        alive = not problems and running(runner)
        errors.extend(problems)
        repo = runner.get('repo') or status.get('repo')
        if runner.get('repo') and status.get('repo') and Path(runner['repo']) != Path(status['repo']):
            errors.append(f'{folder / "status.json"}: repo does not match runner.json')
        if not repo and not errors:
            continue
        if not repo:
            errors.append(f'{folder}: repo identity unavailable')
        name = Path(repo).name if repo else folder.name
        state = status.get('state', 'unknown')
        job = current_job(folder, errors=errors)
        if errors:
            status, job, state = {}, None, 'unavailable'
        elif not alive:
            state = 'not running'
        elif job:
            state = 'working'  # busy with its own job: the status is old because the loop waits on it
        elif status.get('state') == 'unavailable':
            state = 'unavailable'
        elif now - float(status.get('updated_at', 0)) > STALE_AFTER:
            state = 'not cycling'
        error = status_error(status, now) if 'status_unavailable_since' in status else ''
        rows.append(dict(name=name, repo=repo, service=service(name) if repo else '-', state=state,
                         state_dir=str(folder), runner_alive=alive,
                         **(dict(errors=errors) if errors else {}),
                         since=status.get('snapshot_at') if error else status.get('since'),
                         workers=status.get('active_workers', None if errors else 0),
                         waiting=status.get('waiting', None if errors else 0), roots=status.get('roots', []),
                         stopped=status.get('stopped', None if errors else 0), stopped_groups=status.get('stopped_groups', []),
                         held=status.get('held', []), waiting_groups=status.get('waiting_groups', []),
                         blocker='; '.join(errors) or error or status.get('blocker', ''),
                         stop_reason=status.get('stop_reason', ''),
                         updated_at=status.get('updated_at'),
                         task_source=status.get('task_source') or dict(
                             workspace=None, repository_identity=None, revision=None, observed_at=None),
                         snapshot_at=status.get('snapshot_at'),
                         snapshot_age_seconds=max(0, now - status['snapshot_at'])
                         if status.get('snapshot_at') is not None else None,
                         max_workers=status.get('max_workers'), maintainer=status.get('maintainer') or {},
                         main_check=status.get('main_check') or {}, job=job))
    return rows


def render(rows, *, now=None):
    now = time.time() if now is None else now
    if not rows:
        return 'No pi-autowork runners have recorded state yet.'
    lines = []
    for row in rows:
        since = f" for {int((now - row['since']) // 60)} min" if row.get('since') else ''
        word = (row['waiting_groups'][0]['label']
                if row['state'] == HOST_WAIT and row.get('waiting_groups') else row['state'])
        lines.append(f"{row['name']:<24} service {row['service']:<9} {word}{since}; "
                     f"{row['workers']} running, {row['waiting']} waiting"
                     + (f", {row['stopped']} stopped by a blocker" if row.get('stopped') else ''))
        if row.get('errors') or row.get('blocker', '').startswith('status unavailable since '):
            lines.append('    ' + row['blocker'])
        if row['state'] in ('stalled', 'blocked', 'not running', 'not cycling'):
            for root in [r for r in row['roots'] if needs_person(r)][:3]:
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


def _compat_main(argv):
    import sys
    previous = sys.argv
    sys.argv = [previous[0], *argv]
    try:
        sys.exit(main(sys.argv[1:]))
    finally:
        sys.argv = previous
