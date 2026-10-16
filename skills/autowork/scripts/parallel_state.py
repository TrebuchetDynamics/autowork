"""Repository-local parallel leases and worker recovery; no process launch or merge.

All mutations share the sequential writer lock. Process birth identity, never age,
controls liveness. Slot records describe execution evidence, not TODO acceptance.
"""
import json
import os
from pathlib import Path
import re
import time

import task_execution as execution


TRANSITIONS = {
    'dispatched': {'running', 'reported', 'held', 'interrupted', 'released'},
    'running': {'reported', 'held', 'interrupted', 'released'},
    'reported': {'integrating', 'held'},
    'integrating': {'integrated', 'held'},
    'integrated': {'closed', 'held'},
    'closed': set(),
    'held': {'dispatched'},
    'interrupted': {'dispatched', 'held'},
    'released': {'dispatched'},
}
FIELDS = {'worker', 'report', 'commit', 'reason', 'checks', 'integration', 'log_path'}


def common_dir(repo):
    return execution.safe_path(Path(execution.git(repo, 'rev-parse', '--path-format=absolute',
                                                  '--git-common-dir')) / 'autowork-execution')


def lease(common):
    path = common / 'coordinator.json'
    value = execution.read(path)
    if value is None and path.exists():
        raise ValueError('null parallel coordinator lease')
    if value is not None:
        execution.active_owner(value)  # Reject malformed state, including {}.
    return value


def live_coordinator(common):
    value = lease(common)
    return value if value is not None and execution.active_owner(value) else None


def event(common, kind, **fields):
    """Caller holds writer.lock; append a complete JSON line and durably flush it."""
    path = execution.safe_path(common / 'journal.jsonl')
    data = (json.dumps(dict(timestamp=time.time(), event=kind, **fields), allow_nan=False) + '\n').encode()
    fd = os.open(path, os.O_WRONLY | os.O_APPEND | os.O_CREAT | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'ab') as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def claim(repo, owner_pid, *, profile='', max_workers=2):
    owner = execution.owner_identity(owner_pid)
    if type(max_workers) is not int or not 1 <= max_workers <= 8:
        raise ValueError('max_workers must be between 1 and 8')
    common = common_dir(repo)
    workspace = str(Path(execution.git(repo, 'rev-parse', '--show-toplevel')).resolve())
    with execution.lock(common / 'writer.lock'):
        sequential_path = common / 'active.json'
        sequential = execution.read(sequential_path)
        if sequential is None and sequential_path.exists():
            raise ValueError('null sequential execution lease')
        if sequential is not None and execution.active_owner(sequential):
            return {'outcome': 'BUSY', 'reason': 'Live sequential owner', 'owner': sequential['owner']}
        current = lease(common)
        if current is not None and execution.active_owner(current):
            if current['owner'] != owner or current['workspace'] != workspace or current['profile'] != profile:
                return {'outcome': 'BUSY', 'reason': 'Live parallel coordinator', 'owner': current['owner']}
            return dict(current, outcome='CLAIMED')
        value = dict(owner=owner, workspace=workspace, profile=profile,
                     max_workers=max_workers, started_at=time.time())
        execution.save(common / 'coordinator.json', value)
        event(common, 'coordinator_claimed', coordinator=value, previous=current)
        return dict(value, outcome='CLAIMED')


def require_owner(common, owner_pid):
    owner = execution.owner_identity(owner_pid)
    current = live_coordinator(common)
    if current is None or current['owner'] != owner:
        raise ValueError('operation requires the live parallel coordinator owner')
    return current


def release(repo, owner_pid):
    common = common_dir(repo)
    with execution.lock(common / 'writer.lock'):
        current = require_owner(common, owner_pid)
        (common / 'coordinator.json').unlink()
        event(common, 'coordinator_released', coordinator=current)
    # Slots and workers survive the coordinator; a later owner adopts them.
    return {'outcome': 'RELEASED'}


def slot_path(common, task):
    if not isinstance(task, str) or not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', task):
        raise ValueError('invalid slot task identifier')
    return execution.safe_path(common / 'slots' / (task + '.json'))


def slots(common):
    folder = execution.safe_path(common / 'slots')
    result = []
    for path in sorted(folder.glob('*.json')):
        value = execution.read(slot_path(common, path.stem))
        if (not isinstance(value, dict) or value.get('task_id') != path.stem
                or value.get('state') not in TRANSITIONS or value.get('attempt') not in (1, 2)):
            raise ValueError('malformed worker slot')
        result.append(value)
    return result


def group_alive(pgid):
    """A process group ID cannot be reused while any member lives; zombies are reaped first."""
    try:
        os.waitpid(pgid, os.WNOHANG)  # Reap our own exited child so it stops counting.
    except ChildProcessError:
        pass
    try:
        os.killpg(pgid, 0)
        return True
    except ProcessLookupError:
        return False
    except PermissionError:
        return True


def worker_live(slot):
    """Workers lead their own process group; a surviving child keeps the slot live."""
    worker = slot.get('worker')
    if worker is None:
        return False
    return execution.active_owner({'owner': worker}) or group_alive(worker['pid'])


def workspace(common, worktree, branch, baseline):
    path = Path(worktree).resolve()
    if common_dir(path) != common:
        raise ValueError('worker worktree belongs to another repository')
    if Path(execution.git(path, 'rev-parse', '--show-toplevel')).resolve() != path:
        raise ValueError('worker path must be a worktree root')
    if execution.git(path, 'symbolic-ref', '--short', 'HEAD') != branch:
        raise ValueError('worker branch does not match worktree')
    commit = execution.git(path, 'rev-parse', '--verify', baseline + '^{commit}')
    if commit != baseline:
        raise ValueError('baseline must be an immutable full commit ID')
    return str(path)


def write_slot(common, slot, previous=None):
    execution.save(slot_path(common, slot['task_id']), slot)
    event(common, 'slot_changed', task_id=slot['task_id'], state=slot['state'],
          previous_state=previous['state'] if previous else None, slot=slot)
    return slot


def create_slot(repo, owner_pid, task, *, worktree, branch, baseline, worker=None):
    common = common_dir(repo)
    with execution.lock(common / 'writer.lock'):
        require_owner(common, owner_pid)
        path = slot_path(common, task)
        if path.exists():
            raise ValueError('slot already exists; transition it without discarding history')
        root = workspace(common, worktree, branch, baseline)
        if worker is not None:
            execution.active_owner({'owner': worker})
        return write_slot(common, dict(task_id=task, worktree=root, branch=branch,
                                       baseline=baseline, worker=worker, state='dispatched',
                                       attempt=1, started_at=time.time()))


def change(common, old, target, updates):
    if target not in TRANSITIONS[old['state']]:
        raise ValueError(f'illegal slot transition: {old["state"]} -> {target}')
    extra = set(updates) - FIELDS
    retry = target == 'dispatched'
    if retry:
        extra -= {'worktree', 'branch', 'baseline'}
    if extra:
        raise ValueError('unsupported slot fields: ' + ', '.join(sorted(extra)))
    value = dict(old)
    if retry:
        if old['attempt'] >= 2:
            raise ValueError('second failure stays held; no third attempt')
        if worker_live(old):
            raise ValueError('cannot restart a live worker')
        if old['state'] == 'held':
            if any(worker_live(s) for s in slots(common)):
                raise ValueError('held retry requires a drained worker pool')
            if updates.get('branch') != 'autowork/' + old['task_id'] + '-r2':
                raise ValueError('held retry requires a fresh -r2 branch')
            if not updates.get('worktree') or Path(updates['worktree']).resolve() == Path(old['worktree']):
                raise ValueError('held retry must preserve the original worktree')
            updates['worktree'] = workspace(common, updates['worktree'], updates['branch'],
                                            updates.get('baseline', ''))
        elif any(updates.get(k, old[k]) != old[k] for k in ('worktree', 'branch', 'baseline')):
            raise ValueError('interrupted/released retry must reuse its worktree and branch')
        value['previous_attempts'] = old.get('previous_attempts', []) + [
            {k: v for k, v in old.items() if k != 'previous_attempts'}]
        for key in FIELDS:
            value.pop(key, None)
        value.update(attempt=2, worker=None, started_at=time.time())
    if updates.get('worker') is not None:
        execution.active_owner({'owner': updates['worker']})
    if target in ('interrupted', 'released') and old['attempt'] == 2:
        target = 'held'
    value.update(updates)
    value['state'] = target
    return write_slot(common, value, old)


SCOPE_HOLD = 'changed files violate Touches'


def readoptable(slot):
    """A held retry that produced nothing, after a first commit held only for scope.

    Scope can change after a hold (recorded Touches, ownership rules), and a retry
    usually cannot fix a scope hold itself; other holds keep the fresh-retry rule.
    """
    history = slot.get('previous_attempts') or []
    first = history[0] if len(history) == 1 else {}
    return (slot['state'] == 'held' and slot['attempt'] == 2 and not slot.get('commit')
            and not slot.get('readopted') and not worker_live(slot)
            and first.get('state') == 'held' and bool(first.get('commit'))
            and str(first.get('reason', '')).startswith(SCOPE_HOLD))


def exhausted(slot):
    """A held slot with no attempt left: it waits for a person, not for the pool."""
    return slot['state'] == 'held' and slot['attempt'] >= 2 and not readoptable(slot)


def readopt(common, old):
    """Offer a first attempt's held commit to integration once more.

    Caller holds writer.lock. Integration repeats every check on that commit; the
    slot stays attempt 2, so a further hold is final.
    """
    if not readoptable(old):
        raise ValueError('only a held retry without a commit can readopt its first attempt')
    first = old['previous_attempts'][0]
    workspace(common, first['worktree'], first['branch'], first['baseline'])
    value = {k: v for k, v in first.items() if k not in ('reason', 'checks', 'integration', 'report')}
    # Judge the commit by the scope its worker was given, not by Touches recorded
    # after the hold; the dispatch prompt is that record.
    prompt = common / 'slot-data' / old['task_id'] / f'attempt-{first["attempt"]}' / 'prompt.md'
    given = re.search(r'(?m)change only paths within Touches: (.*)$', prompt.read_text()) if prompt.is_file() else None
    if given:
        value['touches'] = '' if given.group(1).strip() == '(none declared)' else given.group(1).strip()
    value.update(attempt=2, readopted=True, data_attempt=first['attempt'], state='reported',
                 previous_attempts=[first, {k: v for k, v in old.items() if k != 'previous_attempts'}])
    return write_slot(common, value, old)


def transition(repo, owner_pid, task, target, **updates):
    common = common_dir(repo)
    with execution.lock(common / 'writer.lock'):
        require_owner(common, owner_pid)
        old = next((s for s in slots(common) if s['task_id'] == task), None)
        if old is None:
            raise ValueError('unknown worker slot')
        return change(common, old, target, updates)


def reconcile(repo, owner_pid):
    """Adopt live workers; inspect dead workers without removing their artifacts.

    Reported/integration/terminal slots belong to subsequent integration handling,
    not process recovery. Repeating observations never adds a journal event.
    """
    common = common_dir(repo)
    with execution.lock(common / 'writer.lock'):
        require_owner(common, owner_pid)
        result = []
        for slot in slots(common):
            if slot['state'] not in ('dispatched', 'running'):
                result.append(slot)
                continue
            updates = {}
            if worker_live(slot):
                target = 'running'
            else:
                root = workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
                head = execution.git(root, 'rev-parse', 'HEAD')
                dirty = bool(execution.git(root, 'status', '--porcelain', '--untracked-files=all'))
                if head != slot['baseline']:
                    # merge-base equality proves descent without treating divergence as a result.
                    if execution.git(root, 'merge-base', slot['baseline'], head) != slot['baseline']:
                        target, updates = 'held', {'reason': 'worker HEAD does not descend from baseline'}
                    else:
                        target, updates = 'reported', {'commit': head}
                        if dirty:
                            updates['reason'] = 'commit retained; uncommitted work also preserved'
                elif dirty:
                    target, updates = 'interrupted', {'reason': 'dead worker with uncommitted changes'}
                else:
                    target, updates = 'released', {'reason': 'dead worker without a commit or changes'}
            if target != slot['state']:
                slot = change(common, slot, target, updates)
            result.append(slot)
        return result
