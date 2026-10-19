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
    'integrating': {'integrated', 'held', 'reported'},  # reported: released unfinished (TOOLSET-194-46)
    'integrated': {'closed', 'held'},
    'closed': set(),
    'held': {'dispatched'},
    'interrupted': {'dispatched', 'held'},
    'released': {'dispatched'},
}
# Execution state format this release writes, and every format it can read. A runner
# reads a new release's STATE_SCHEMA_READS before updating to it (pi-autowork.sh).
STATE_SCHEMA = 1
STATE_SCHEMA_READS = (1,)
FIELDS = {'worker', 'report', 'commit', 'reason', 'checks', 'integration', 'log_path', 'paused', 'cause',
          'outside', 'requested', 'reviewed_by', 'check_failure_resumed', 'answered', 'merged_base',
          'merged_count', 'conflict_files'}
# Hold causes no fresh attempt can fix: the worker itself reported what it needs
# (scope_request: files outside Touches, listed in `requested`).
# scope: a commit changed files outside Touches the runner could not widen; a fresh retry
# with the same Touches cannot pass, so the files go to the owner as a question.
# Not retried with a fresh attempt. 'timeout': the host was slow, not the task; the coordinator
# reviews the same commit again with a longer limit (TOOLSET-196-fb).
# 'no_change': the worker reported, cleanly, that nothing needed changing; a fresh attempt would only
# say so again, so the docs maintainer closes or restates the task.
NEEDS_PERSON = ('blocker', 'scope_request', 'scope', 'timeout', 'no_change')
COORDINATOR_FILES = ('TODO.md', 'TODO.archive.md', 'goals.json', 'CHANGELOG.md')


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


def pause(repo, owner_pid):
    """A deliberate coordinator stop (service stop or restart, Ctrl+C): mark live workers
    before they are interrupted, so the next coordinator resumes each in its worktree on
    the same attempt instead of spending the retry or holding a second attempt."""
    common = common_dir(repo)
    paused = []
    with execution.lock(common / 'writer.lock'):
        require_owner(common, owner_pid)
        for slot in slots(common):
            if slot['state'] in ('dispatched', 'running') and worker_live(slot) and not slot.get('paused'):
                write_slot(common, dict(slot, paused=True), slot)
                paused.append(slot['task_id'])
    return {'outcome': 'PAUSED', 'paused': paused}


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


# Every worker process and its descendants carry the worktree they work in. A
# launch whose identity was never recorded, or a child that left the worker's
# process group (its own session), is still found by this marker.
WORKER_MARKER = 'AUTOWORK_WORKTREE'


def strays(worktree):
    """Live processes carrying this worktree's worker marker, from /proc."""
    if not worktree:
        return []
    marker = f'{WORKER_MARKER}={worktree}'.encode()
    found = []
    for entry in Path('/proc').glob('[0-9]*'):
        try:
            if marker in (entry / 'environ').read_bytes().split(b'\0') and execution.identity(entry.name):
                found.append(int(entry.name))
        except (OSError, ValueError):
            continue  # Exited, or another user's process.
    return found


def owns_process(leader, found):
    """Birth-checked leader/group/ancestry proof, including children that called setsid.

    Snapshot each parent link and recheck it before accepting: an exited/reused PID
    or a reparented child is not evidence of ownership. Markers alone prove nothing.
    """
    def link(expected):
        try:
            fields = Path(f'/proc/{expected["pid"]}/stat').read_text().rsplit(')', 1)[1].split()
            if (fields[0] in ('Z', 'X') or int(fields[19]) != expected['start_ticks']
                    or execution.identity(expected['pid']) != expected):
                return None
            return int(fields[1]), int(fields[2])  # parent, process group
        except (OSError, ValueError, IndexError):
            return None

    if execution.identity(leader['pid']) != leader:
        return False
    chain = {}
    current = found
    while current['pid'] not in chain:
        observed = link(current)
        if observed is None:
            return False
        chain[current['pid']] = (current, observed)
        parent_pid, group = observed
        if current == leader or (current == found and group == leader['pid']):
            return (all(link(expected) == saved for expected, saved in chain.values())
                    and execution.identity(leader['pid']) == leader)
        parent = execution.identity(parent_pid)
        if (not parent or parent['boot_id'] != current['boot_id']
                or parent['start_ticks'] > current['start_ticks']):
            return False
        current = parent
    return False


def worker_live(slot):
    """Workers lead their own process group; a surviving child keeps the slot live,
    and so does any process still carrying the slot's worker marker."""
    worker = slot.get('worker')
    if worker is not None and (execution.active_owner({'owner': worker}) or group_alive(worker['pid'])):
        return True
    return bool(strays(slot.get('worktree')))


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
    # A worker stopped by a deliberate coordinator stop resumes the same attempt.
    resume = bool(old.get('paused')) and old['state'] in ('interrupted', 'released')
    if retry:
        if old['attempt'] >= 2 and not resume:
            raise ValueError('second failure stays held; no third attempt')
        if worker_live(old):
            raise ValueError('cannot restart a live worker')
        if old['state'] == 'held':
            live = [s for s in slots(common) if worker_live(s)]
            if live:
                import parallel_dispatch
                repo = Path(lease(common)['workspace'])
                admitted = parallel_dispatch.retry_plan(repo, slots(common), old['task_id'])
                if old['task_id'] not in {task['id'] for task in admitted['dispatch']}:
                    raise ValueError('held retry conflicts with worker pool')
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
        if not resume:  # A fresh worker commit is not a re-review of the held attempt.
            for key in ('reverified', 'reverify_verdict'):
                value.pop(key, None)
        value.update(attempt=old['attempt'] if resume else 2, worker=None, started_at=time.time())
    if updates.get('worker') is not None:
        execution.active_owner({'owner': updates['worker']})
    if target in ('interrupted', 'released') and old['attempt'] == 2 and not updates.get('paused', old.get('paused')):
        target = 'held'
        # A worker that stopped with nothing at all did not necessarily crash: say so.
        updates.setdefault('cause', 'empty' if str(updates.get('reason', '')).startswith(EMPTY) else 'crash')
    value.update(updates)
    value['state'] = target
    return write_slot(common, value, old)


SCOPE_HOLD = 'changed files violate Touches'
EMPTY = 'dead worker without a commit or changes'


def held_first_attempt(slot):
    """The first attempt's held record. Its history may also hold a pause or an
    interruption of that attempt, which an earlier rule mistook for a second attempt."""
    held = [h for h in slot.get('previous_attempts') or [] if h.get('state') == 'held']
    return held[0] if len(held) == 1 else {}


def readoptable(slot):
    """A held retry that produced nothing, after a first commit held only for scope.

    Scope can change after a hold (recorded Touches, ownership rules), and a retry
    usually cannot fix a scope hold itself; other holds keep the fresh-retry rule.
    """
    first = held_first_attempt(slot)
    return (slot['state'] == 'held' and slot['attempt'] == 2 and not slot.get('commit')
            and not slot.get('readopted') and not worker_live(slot)
            and first.get('state') == 'held' and bool(first.get('commit'))
            and str(first.get('reason', '')).startswith(SCOPE_HOLD))


def rescopable(slot, touches, *, touches_only=False):
    """A scope-held commit whose outside files are now covered.

    The automatic offer is once per slot (``rescoped``). A new, Touches-only
    contract answer may offer it again; integration still checks every other
    slot's files, protected-file admission and coordinator files.
    """
    import parallel_plan
    outside = slot.get('outside') or []
    declared = parallel_plan.paths(touches) if touches.strip() else []
    return (slot['state'] == 'held' and slot.get('cause') == 'scope' and bool(slot.get('commit'))
            and (not slot.get('rescoped') or touches_only) and not worker_live(slot)
            and bool(outside) and bool(declared)
            and not parallel_plan.overlap(outside, declared, [])['outside'])


def overlap_held(slot):
    """A commit held only because another slot owned some of its files (TOOLSET-157-cd)."""
    return slot['state'] == 'held' and slot.get('cause') == 'overlap' and not worker_live(slot)


def reoffered(slot):
    """The hold causes this slot was already offered again for. ``True`` is the record of the
    first releases, which offered again only for overlap or a misread report."""
    value = slot.get('reoffered')
    return {'overlap', 'report'} if value is True else set(value or [])


def reoffer(common, old):
    """Offer a held commit to integration again, once per hold cause: an overlap hold after
    the slots it conflicted with have settled, or a report or validation an earlier release
    misread. Integration repeats every check on current main. Caller holds writer.lock."""
    value = {k: v for k, v in old.items() if k not in ('reason', 'cause')}
    value.update(state='reported', reoffered=sorted(reoffered(old) | {old.get('cause')}))
    return write_slot(common, value, old)


def rescope(common, old, touches, *, contract=None):
    """Return a scope-held commit to ``reported``, judged by ``touches``. Caller holds writer.lock."""
    value = {k: v for k, v in old.items() if k not in ('reason', 'cause', 'outside')}
    value.update(state='reported', rescoped=True, touches=touches)
    if contract is not None:
        # Consume this answer without overwriting the original admission evidence.
        value['rescoped_contract'] = contract.strip()
    return write_slot(common, value, old)


def merge_adoption(repo, slot):
    """Read-only eligibility shared by adoption and the runner's status preflight.

    Legacy boolean merged_base records keep the adopted revision in baseline.
    A fresh attempt clears adoption evidence with the other attempt-local fields.
    """
    base = execution.git(repo, 'rev-parse', 'HEAD')
    previous = slot.get('merged_base')
    count = slot.get('merged_count', 1 if previous else 0)
    previous = slot['baseline'] if previous is True else previous
    reason = None
    if (slot['state'] != 'held' or slot.get('cause') != 'conflict' or not slot.get('commit')
            or worker_live(slot)):
        reason = 'merged is only for an idle conflict-held commit'
    elif count >= 3:
        reason = 'merge adoption limit reached'
    elif previous and (previous == base or execution.git(repo, 'merge-base', previous, base) != previous):
        reason = 'canonical HEAD has not advanced past the last adopted revision'
    files = slot.get('conflict_files')
    if files is None:  # pre-upgrade holds have no exact list; retain their task paths
        files = (execution.git(repo, 'diff', '--name-only', slot['baseline'], slot['commit']).splitlines()
                 if slot.get('commit') else [])
    if reason:
        reason += f'; adopted {count} of 3; conflict in: ' + (', '.join(files) or '(unknown files)')
    return dict(allowed=reason is None, baseline=base, merged_count=count, reason=reason, files=files)


def exhausted(slot):
    """A held slot no fresh attempt should replace; a resolver can still adopt its commit."""
    return (slot['state'] == 'held' and (slot['attempt'] >= 2 or slot.get('cause') in NEEDS_PERSON
            or (slot.get('cause') == 'conflict' and bool(slot.get('merged_base'))))
            and not readoptable(slot))


def report_blockers(common, slot):
    """Blockers from this attempt's report.json, or None without a valid report."""
    data = common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}'
    try:
        report = execution.read(execution.safe_path(data / 'report.json'))
    except (ValueError, OSError):
        return None
    blockers = report.get('blockers') if isinstance(report, dict) and report.get('task') == slot['task_id'] else None
    if not isinstance(blockers, list) or not all(isinstance(b, str) for b in blockers):
        return None
    return [b.strip() for b in blockers if b.strip()]


def resume_widened(common, old):
    """A scope request whose Touches now cover it resumes in its worktree on the same
    attempt (it was not a failure). Caller holds writer.lock."""
    value = {k: v for k, v in old.items() if k not in ('reason', 'cause', 'requested', 'outside')}
    value.update(state='interrupted', paused=True)
    return write_slot(common, value, old)


def no_change_summary(common, slot):
    """What a report with nothing to change said: its notes and checks, briefly."""
    data = common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}'
    try:
        report = execution.read(execution.safe_path(data / 'report.json'))
    except (ValueError, OSError):
        report = None
    if not isinstance(report, dict):
        return 'see report.json'
    known = {'task', 'commit', 'changed_files', 'checks', 'blockers', 'pending_live', 'unrelated_failures',
             'environment_failures', 'changelog'}
    notes = [str(v) for k, v in report.items() if k not in known and isinstance(v, str) and v.strip()]
    checks = [f"{c.get('command')}: {c.get('result')}" for c in report.get('checks') or [] if isinstance(c, dict)]
    text = ' '.join('; '.join(notes + checks).split()) or 'see report.json'
    return text[:400] + ('…' if len(text) > 400 else '')


def blocker_reason(blockers):
    first = ' '.join(blockers[0].split())
    more = f' (+{len(blockers) - 1} more in report.json)' if len(blockers) > 1 else ''
    return 'worker reported a blocker: ' + (first[:400] + '…' if len(first) > 400 else first) + more


def readopt(common, old):
    """Offer a first attempt's held commit to integration once more.

    Caller holds writer.lock. Integration repeats every check on that commit; the
    slot stays attempt 2, so a further hold is final.
    """
    if not readoptable(old):
        raise ValueError('only a held retry without a commit can readopt its first attempt')
    first = held_first_attempt(old)
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
            # Also recover reports an older runner already held as a person's question.
            old_blocker = (slot['state'] == 'held' and slot.get('cause') == 'blocker'
                           and not slot.get('commit') and not worker_live(slot))
            if slot['state'] not in ('dispatched', 'running') and not old_blocker:
                result.append(slot)
                continue
            if old_blocker:
                import parallel_dispatch as dispatch
                if not dispatch.check_only_blockers(report_blockers(common, slot)):
                    result.append(slot)
                    continue  # no valid host-only report: preserve the original hold
            updates = {}
            if worker_live(slot):
                target = 'running'
            else:
                root = workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
                head = execution.git(root, 'rev-parse', 'HEAD')
                dirty = bool(execution.git(root, 'status', '--porcelain', '--untracked-files=all'))
                if old_blocker and (head != slot['baseline'] or not dirty):
                    result.append(slot)
                    continue  # only a dirty, uncommitted candidate can resume an old blocker
                if head != slot['baseline']:
                    # merge-base equality proves descent without treating divergence as a result.
                    if execution.git(root, 'merge-base', slot['baseline'], head) != slot['baseline']:
                        target, updates = 'held', {'reason': 'worker HEAD does not descend from baseline'}
                    else:
                        target, updates = 'reported', {'commit': head}
                        if dirty:
                            updates['reason'] = 'commit retained; uncommitted work also preserved'
                elif blockers := report_blockers(common, slot):
                    import parallel_dispatch as dispatch
                    if dirty and dispatch.check_only_blockers(blockers):
                        # One same-attempt resume, durable in the slot history. A repeated
                        # report waits for the coordinator's quieter-host timeout recovery.
                        repeated = dispatch.check_failure_resumed(slot)
                        target = 'held' if repeated else 'interrupted'
                        updates = {'reason': blocker_reason(blockers), 'check_failure_resumed': True,
                                   'paused': not repeated, 'cause': 'timeout' if repeated else None}
                        if old_blocker:
                            slot = write_slot(common, dict(slot, state=target, **updates), slot)
                            result.append(slot)
                            continue
                    else:
                        # A genuine missing input still waits for a person; preserve its work.
                        target, updates = 'held', {'reason': blocker_reason(blockers), 'cause': 'blocker'}
                elif blockers == [] and not dirty and not slot.get('paused'):
                    # A report with no commit and no blockers says nothing needed changing: rerun, it
                    # said so again, three times in an hour for one task.
                    target, updates = 'held', {'reason': 'its worker found nothing to change: ' + no_change_summary(
                        common, slot), 'cause': 'no_change'}
                else:
                    target = 'interrupted' if dirty else 'released'
                    reason = ('dead worker with uncommitted changes' if dirty else EMPTY)
                    if slot.get('paused'):
                        reason = f'stopped by a runner restart; resumes on attempt {slot["attempt"]}'
                        if dirty:
                            reason += ' with uncommitted changes'
                    updates = {'reason': reason}
            if target != slot['state']:
                slot = change(common, slot, target, updates)
            result.append(slot)
        return result
