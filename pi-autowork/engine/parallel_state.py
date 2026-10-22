"""Repository-local parallel leases and worker recovery; no process launch or merge.

All mutations share the sequential writer lock. Process birth identity, never age,
controls liveness. Slot records describe execution evidence, not TODO acceptance.
"""
import hashlib
import os
from pathlib import Path
import re
import time

import task_execution as execution
import execution_journal as journal
import failure_policy

# Public readers of the existing journal, not a second telemetry store.
lifecycle_events = journal.lifecycle_events


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
FIELDS = {'worker', 'report', 'commit', 'reason', 'checks', 'integration', 'log_path', 'paused', 'paused_claim', 'cause',
          'outside', 'requested', 'reviewed_by', 'check_failure_resumed', 'answered', 'merged_base',
          'merged_count', 'merged_authored_planning', 'conflict_files', 'closing', 'tip', 'waits_for', 'wait_since',
          'landed_tasks', 'landed_revisions', 'hold_policy', 'telemetry_end_revision'}
# Hold causes no fresh attempt can fix: the worker itself reported what it needs
# (scope_request: files outside Touches, listed in `requested`).
# scope: a commit changed files outside Touches the runner could not widen; a fresh retry
# with the same Touches cannot pass, so the files go to the owner as a question.
# Not retried with a fresh attempt. 'timeout': the host was slow, not the task; the coordinator
# reviews the same commit again with a longer limit (TOOLSET-196-fb).
# 'no_change': the worker reported, cleanly, that nothing needed changing; a fresh attempt would only
# say so again, so the docs maintainer closes or restates the task.
# Recovery policy, not permission to skip evidence or spend another attempt. A
# reoffer requires repaired evidence and is once per cause; otherwise its ordinary
# first-attempt retry (or owner hold for scope) still applies. Timeout recovery is
# coordinator reverify, never a fresh worker; scope_request resumes the same attempt.
HOLD_CAUSES = {
    'scope': 'reoffer_once',
    'overlap': 'reoffer_once',
    'report': 'reoffer_once',
    'validation': 'reoffer_once',
    'stale_validation': 'reoffer_once',
    'conflict': 'resolve_conflict',
    'blocker': 'ask_owner',
    # A slow host, a worker that found nothing to change and a second failed review are
    # engineering dispositions: the coordinator re-verifies, an agent repairs, or the task
    # becomes a visible engineering hold. None is a product decision (failure_policy).
    'timeout': 'reverify',
    'no_change': 'engineering_stuck',
    'reviewed_twice': 'engineering_stuck',
    'task_wait': 'wait_for_task',
    'scope_request': 'rerun',
    'runner_merged': 'rerun',
    'contract_changed': 'rerun',
    'moved': 'rerun',
    'crash': 'rerun',
    'empty': 'rerun',
    'diverged': 'rerun',
    'launch': 'rerun',
}
NEEDS_PERSON = tuple(cause for cause in HOLD_CAUSES
                     if failure_policy.owner_decision_required(cause))
COORDINATOR_FILES = ('tasks/', 'TODO.archive.md', 'CHANGELOG.md')


def close_files(repo, task=None):
    """The files a close writes, repository-relative: the task's record and its receipt (and a
    live follow-up beside them). Without a task, the whole store a close may write in. It lives
    here so parallel_integrate can re-export it for callers that stage a close's own file set."""
    if task is None:
        return ['tasks/items/', 'tasks/evidence/']
    return [f'tasks/items/{task}.md', f'tasks/evidence/{task}.toml', f'tasks/items/{task}-LIVE.md']


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
    """Caller holds writer.lock; telemetry never changes an execution decision."""
    try:
        if kind == 'slot_changed':
            fields['lifecycle'] = fields['slot'].get('lifecycle', [])
        elif kind in ('coordinator_claimed', 'coordinator_released'):
            fields['lifecycle'] = fields['coordinator'].get('lifecycle', [])
        elif kind in ('blocker_answered', 'replayed_close'):
            slot = execution.read(slot_path(common, fields['task_id'])) or {'task_id': fields['task_id']}
            facts = list(slot.get('lifecycle', []))
            if kind == 'replayed_close':
                replay = journal.fact(journal.context(common, slot), kind)
                if not any(e['event_id'] == replay['event_id'] for e in facts):
                    facts.append(replay)
                    execution.save(slot_path(common, fields['task_id']), dict(slot, lifecycle=facts))
            fields['lifecycle'] = facts
        return journal.append(common, kind, fields)
    except (OSError, ValueError):
        return False


def observe_history(repo, *, delivered_rev=None):
    """Observe committed acceptance/hand closure/delivery; never edit the task store.

    A busy writer or unreadable history simply defers observation to the next cycle.
    Saved slot facts also repair a crash between the slot replace and journal append.
    """
    import lifecycle_history
    lifecycle_history.observe(repo, delivered_rev)


def claim(repo, owner_pid, *, profile='', max_workers=2):
    owner = execution.owner_identity(owner_pid)
    if type(max_workers) is not int or not 1 <= max_workers <= 16:
        raise ValueError('max_workers must be between 1 and 16')
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
        facts = list((current or {}).get('lifecycle', []))
        for slot in slots(common):
            if slot['state'] not in ('closed', 'held'):
                ctx = journal.context(common, slot)
                recovered = [journal.fact(ctx, 'restart', key=str(value['started_at']))]
                if worker_live(slot):
                    recovered.append(journal.fact(ctx, 'worker_adopted', key=str(value['started_at'])))
                facts.extend(recovered)
        if facts:
            value['lifecycle'] = facts
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
        current = require_owner(common, owner_pid)
        for slot in slots(common):
            if slot['state'] in ('dispatched', 'running') and worker_live(slot) and not slot.get('paused'):
                write_slot(common, dict(slot, paused=True, paused_claim=current['started_at']), slot)
                paused.append(slot['task_id'])
    return {'outcome': 'PAUSED', 'paused': paused}


def release(repo, owner_pid):
    common = common_dir(repo)
    with execution.lock(common / 'writer.lock'):
        current = require_owner(common, owner_pid)
        # Replay saved claim facts before removing their durable lease. A crash
        # before/during this append leaves them available to the next claimant.
        if not event(common, 'coordinator_released', coordinator=current):
            # A journal-only outage must not hold release or discard recovery
            # intent. Reuse existing attempt metadata, leaving slot bytes alone.
            for slot in slots(common):
                facts = [e for e in current.get('lifecycle', [])
                         if e['task_id'] == slot['task_id']]
                if not facts:
                    continue
                try:
                    data = common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}'
                    meta = execution.read(data / 'meta.json') or {}
                    known = {e['event_id'] for e in meta.get('lifecycle', [])}
                    pending = [e for e in facts if e['event_id'] not in known]
                    execution.save(data / 'meta.json', dict(meta, lifecycle=meta.get('lifecycle', []) + pending))
                except (OSError, ValueError):
                    pass
        (common / 'coordinator.json').unlink()
    # Slots and workers survive the coordinator; a later owner adopts them.
    return {'outcome': 'RELEASED'}


# A reported commit refused for a live writer steps aside in priority order for this long,
# so one waiting candidate never holds back the rest (TOOLSET-223-8e).
WRITERS_BUSY_SKIP = 600


def writers_busy(slot, now=None):
    """A reported task refused for a live writer is skipped for a bounded window."""
    try:
        stamp = float(slot.get('writers_busy_at'))
    except (TypeError, ValueError):
        return False
    return (time.time() if now is None else now) - stamp < WRITERS_BUSY_SKIP


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
        if value['state'] == 'held':
            value = dict(value, cause=hold_cause(value))
        result.append(value)
    return result


def hold_cause(slot):
    """Old missing/unknown causes are crash holds, without rewriting runtime files."""
    cause = slot.get('cause')
    return cause if isinstance(cause, str) and cause in HOLD_CAUSES else 'crash'


def legacy_hold(slot):
    """Compatibility for pre-cause holds only; new recovery never parses display text.

    Keep these historical signatures at the state boundary, not in retry_held's
    dispatch policy. Unknown old causes still read as crash, including these records.
    """
    # Native holds use structured evidence. Only pre-table records may need the
    # old signatures, even when an earlier release already recorded their cause.
    if (slot.get('hold_policy') == 1 and isinstance(slot.get('cause'), str)
            and slot['cause'] in HOLD_CAUSES):
        return None
    cause = hold_cause(slot)
    reason = str(slot.get('reason') or '')
    if cause == 'crash':
        if reason.startswith('live or unknown external writer'):
            return 'writer'
        if reason == 'unexpected worker branch':
            return 'branch'
        if reason == 'missing, failed, stale or mismatched integration validation':
            return 'stale_validation'
        if reason.startswith('integration validation failed'):
            return 'validation'
    if ((cause == 'crash' and reason.startswith(SCOPE_HOLD))
            or (cause == 'scope' and SCOPE_HOLD in reason)):
        return 'scope'
    return None


def next_action(slot):
    """Recovery policy for a held slot; execution still checks evidence and budgets.

    Only pre-cause compatibility can override the table: an old non-verdict is
    offered back to integration, rather than rerunning finished work as a crash.
    A saved dependency wait also takes precedence over old cause labels.
    """
    if slot.get('state') != 'held':
        return None
    if slot.get('waits_for'):
        return 'wait_for_task'
    if legacy_hold(slot) in ('writer', 'branch', 'stale_validation'):
        return 'reoffer_once'
    return HOLD_CAUSES[hold_cause(slot)]


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


def write_slot(common, slot, previous=None, *, observations=()):
    # Keep the attempt's runtime separate from started_at (the per-resume timeout
    # clock). Paused/held time is not work, and resuming is not a new attempt.
    stamp = time.time()
    stopped = ('held', 'interrupted', 'released')
    if slot['state'] in stopped and (not previous or previous['state'] not in stopped):
        seconds = slot.get('runtime_seconds', 0) + max(0, stamp - slot.get('runtime_started_at', slot['started_at']))
        slot = dict(slot, runtime_seconds=seconds)
    elif slot['state'] not in stopped and previous and previous['state'] in stopped:
        slot = dict(slot, runtime_started_at=stamp)
    if slot['state'] == 'held' and (not previous or previous['state'] != 'held'
                                   or previous.get('reason') != slot.get('reason')):
        slot = dict(slot, held_at=stamp, held_seconds=slot.get('runtime_seconds'))
    slot = journal.slot_facts(common, slot, previous, observations)
    execution.save(slot_path(common, slot['task_id']), slot)
    event(common, 'slot_changed', task_id=slot['task_id'], state=slot['state'],
          previous_state=previous['state'] if previous else None, slot=slot)
    return slot


def blocker_class(reason):
    """Ignore volatile paths, revisions and identifiers, not the missing-input prose."""
    text = re.sub(r"(?:[A-Za-z]:[\\\\/]|/|\b\.{1,2}/)[^\s,;\"'()]+|\b[\w.-]+(?:/[\w.-]+)+", '<path>', reason)
    text = re.sub(r'\b[0-9a-fA-F]{7,}\b|\b(?:[A-Z][A-Z0-9]*(?:[-_][A-Za-z0-9]+)+|[A-Z]|[\w-]*\d[\w-]*)\b',
                  '<id>', text)
    return ' '.join(text.casefold().split())


def quick_hold(common, slot):
    """Three consecutive quick planning holds, across fresh slots as well as -r2.

    Missing timing evidence breaks the streak. Resumes/re-reviews of one attempt
    count once; failures on the work (validation/crash/timeout) never trip this gate.
    """
    if slot['state'] != 'held':
        return None
    history = common / 'slot-history' / slot['task_id']
    paths = sorted((p for p in history.glob('*') if p.name.isdigit()), key=lambda p: int(p.name))
    attempts = []
    for generation, record in enumerate([*(execution.read(p / 'slot.json') or {} for p in paths), slot], 1):
        distinct = {}
        for attempt in [*record.get('previous_attempts', []), record]:
            distinct[(attempt.get('branch'), attempt.get('attempt'))] = attempt
        for attempt in distinct.values():
            attempts.append(dict(attempt=f'{generation}/{attempt.get("attempt", "?")}',
                                 reason=attempt.get('reason') or '', seconds=attempt.get('held_seconds'),
                                 held_at=attempt.get('held_at'), cause=attempt.get('cause'), state=attempt.get('state')))
    recent = attempts[-3:]
    if len(recent) != 3 or any(a['state'] != 'held' or a['cause'] not in (
            'blocker', 'scope_request', 'scope', 'contract_changed') or a['seconds'] is None
            or not 0 <= a['seconds'] <= 600 for a in recent):
        return None
    reasons = {blocker_class(a['reason']) for a in recent}
    if len(reasons) != 1 or not next(iter(reasons)):
        return None
    fingerprint = hashlib.sha256(next(iter(reasons)).encode()).hexdigest()[:12]
    return dict(fingerprint=fingerprint, reason=slot.get('reason') or '', attempts=recent)


def create_slot(repo, owner_pid, task, *, worktree, branch, baseline, worker=None, host=None, model=None):
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
                                       attempt=1, started_at=time.time(),
                                       host=journal.label(host or os.environ.get('AUTOWORK_TELEMETRY_HOST')),
                                       model=journal.label(model or os.environ.get('AUTOWORK_TELEMETRY_MODEL'))))


def change(common, old, target, updates):
    if target not in TRANSITIONS[old['state']]:
        raise ValueError(f'illegal slot transition: {old["state"]} -> {target}')
    # Refuse even when report-only recovery would later replace the supplied cause.
    if target == 'held' and 'cause' in updates:
        cause = updates['cause']
        if not isinstance(cause, str) or cause not in HOLD_CAUSES:
            raise ValueError(f'unknown hold cause: {cause!r}')
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
        # A pause or crash can precede reconciliation of landed prerequisite code.
        # Keep the immutable source guidance until the slot is retired, not just one launch.
        for key in FIELDS - {'landed_tasks', 'landed_revisions'}:
            value.pop(key, None)
        if not resume:  # A fresh worker commit is not a re-review of the held attempt.
            for key in ('reverified', 'reverify_verdict', 'runtime_seconds', 'runtime_started_at', 'held_at', 'held_seconds'):
                value.pop(key, None)
        value.update(attempt=old['attempt'] if resume else 2, worker=None, started_at=time.time())
        if resume and old.get('report_resume_attempt') == old['attempt'] and old.get('commit'):
            value['commit'] = old['commit']  # report-only identity survives launch failure and timeout
    if (target in ('held', 'interrupted', 'released') and old.get('report_resume_attempt') == old['attempt']
            and old.get('commit') and (missing := missing_commit_report(common, old))):
        target = 'held'
        updates.update(cause='report', paused=False,
                       reason=missing + '; report-only resume stopped: ' + str(updates.get('reason') or target))
    if updates.get('worker') is not None:
        execution.active_owner({'owner': updates['worker']})
    if target in ('interrupted', 'released') and old['attempt'] == 2 and not updates.get('paused', old.get('paused')):
        target = 'held'
        # A worker that stopped with nothing at all did not necessarily crash: say so.
        updates.setdefault('cause', 'empty' if str(updates.get('reason', '')).startswith(EMPTY) else 'crash')
    if target == 'held':
        cause = updates.setdefault('cause', 'crash')
        if not isinstance(cause, str) or cause not in HOLD_CAUSES:
            raise ValueError(f'unknown hold cause: {cause!r}')
    value.update(updates)
    value['state'] = target
    if target == 'held':
        value['hold_policy'] = 1
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
            and not slot.get('readopted') and not slot.get('waits_for') and not worker_live(slot)
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
        # Admission uses this answer for rescoped slots; keep the dispatch evidence intact.
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
    elif missing := missing_commit_report(common_dir(repo), slot):
        reason = missing
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
    """A held slot no fresh attempt should replace; a resolver can still adopt its commit.

    A report hold whose report-only resume was already used keeps its retained commit: no
    fresh attempt replaces it (test_report_only_resume_failures_keep_the_commit...). The
    engine has no further recovery for it, so status classifies it as an engineering hold
    that needs a person (parallel_status.failure_fields), never as a pending resume.
    """
    return (slot['state'] == 'held' and (slot.get('waits_for') or slot['attempt'] >= 2
            or slot.get('cause') in NEEDS_PERSON
            or slot.get('cause') in ('reviewed_twice', 'no_change', 'timeout')
            or (slot.get('cause') == 'report' and slot.get('report_resume_attempt') == slot['attempt'])
            or (slot.get('cause') == 'conflict' and bool(slot.get('merged_base'))))
            and not readoptable(slot))


def missing_commit_report(common, slot):
    """Report provenance only; integration still validates files, checks and blockers."""
    data = common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}'
    path = data / 'report.json'
    try:
        report = execution.read(execution.safe_path(path))
    except (ValueError, OSError):
        report = None
    named = report.get('commit') if isinstance(report, dict) else None
    if (isinstance(report, dict) and report.get('task') == slot['task_id']
            and isinstance(named, str) and re.fullmatch(r'[0-9a-fA-F]{7,40}', named)
            and (slot.get('commit') or '').startswith(named.lower())):
        return ''
    if not isinstance(report, dict):
        return f'the worker wrote no report.json: {path}'
    return (f'the worker wrote no matching report.json (task is {report.get("task")!r}; '
            f'commit is {named!r}, the branch is at {(slot.get("commit") or "")[:12]}): {path}')


def recover_reports(common, current):
    """Prepare one report-only, same-attempt resume; never manufacture a worker report.

    Caller holds writer.lock. Also repairs pre-upgrade conflict holds before any
    resolver or fresh retry can take ownership of the retained work.
    """
    result = []
    for slot in current:
        eligible = (slot['state'] == 'reported' or
                    (slot['state'] == 'held' and slot.get('cause') in ('report', 'conflict')))
        if eligible and slot.get('commit') and not worker_live(slot) and (missing := missing_commit_report(common, slot)):
            repeated = slot.get('report_resume_attempt') == slot['attempt']
            value = {k: v for k, v in slot.items() if k not in ('cause', 'reason', 'data_attempt')}
            value.update(state='held' if repeated else 'interrupted', paused=not repeated,
                         report_resume_attempt=slot['attempt'], reason=missing)
            if repeated:
                value.update(cause='report', reason=missing + '; report-only resume already used')
            if value != slot:
                slot = write_slot(common, value, slot)
        result.append(slot)
    return result


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


def blocker_updates(repo, slot, blockers):
    """Fail closed: only complete task-wait statements are machine dependencies.

    dependency_ids deliberately discards prose; doing that here would hide additional
    owner requests. Unknown wording stays with blocker triage. Workers are given a
    canonical form; the observed parser-repair wording is a narrow compatibility case.
    """
    updates = {'reason': blocker_reason(blockers), 'cause': 'blocker'}
    import task_queue
    snapshot = task_queue.store(Path(repo))
    own = slot['task_id']
    declared = set(snapshot.tasks[own].depends_on) if own in snapshot.tasks else set()
    open_ids = {tid for tid, t in snapshot.tasks.items() if t.status == 'open'}
    eligible = open_ids - declared - {own}
    # Match exact IDs (including paired backticks), never ID substrings or prose.
    ident = r'(?:`[A-Za-z0-9][A-Za-z0-9._-]*`|[A-Za-z0-9][A-Za-z0-9._-]*)'
    task_list = ident + r'(?:(?:,\s*(?:and\s+)?|\s+and\s+)' + ident + r')*'
    patterns = [r'(?:Waiting for|Wait for|Awaiting|Blocked on|Blocked by|Depends on) (' + task_list + r')',
                r'Needs? (' + task_list + r') to land',
                r'The existing (' + ident + r') owner/coordinator must supply the retained parser repair '
                r'in the combined baseline']
    waits = set()
    for blocker in blockers:
        text = ' '.join(blocker.split()).removesuffix('.')
        match = next((m for pattern in patterns if (m := re.fullmatch(pattern, text, re.I))), None)
        if match is None:
            return updates
        ids = {token.strip('`') for token in re.split(r',\s*(?:and\s+)?|\s+and\s+', match[1], flags=re.I)}
        if not ids or not ids <= eligible:
            return updates
        waits.update(ids)
    if waits:
        updates.update(cause='task_wait', waits_for=sorted(waits), wait_since=time.time())
    return updates


def resume_waited(common, old, revisions):
    """Keep the candidate and attempt; pin landed source for safe worker reconciliation."""
    value = {k: v for k, v in old.items() if k not in ('reason', 'cause', 'waits_for', 'wait_since')}
    value.update(state='interrupted', paused=True, landed_tasks=old['waits_for'], landed_revisions=revisions)
    return write_slot(common, value, old)


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
        current = require_owner(common, owner_pid)
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
                if (slot['state'] == 'running' and slot.get('paused')
                        and slot.get('paused_claim') != current['started_at']):
                    # A later coordinator adopted a worker that survived the stop that paused it:
                    # its next death is a crash, not that stop.
                    slot = write_slot(common, {k: v for k, v in slot.items()
                                               if k not in ('paused', 'paused_claim')}, slot)
            else:
                import autowork_run
                data = common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}'
                try:
                    autowork_run.report_wait(data / 'worker-checks', data / 'report.json')
                except (OSError, ValueError):
                    pass  # preserve missing/malformed reports for the usual reconciliation
                root = workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
                head = execution.git(root, 'rev-parse', 'HEAD')
                dirty = bool(execution.git(root, 'status', '--porcelain', '--untracked-files=all'))
                if old_blocker and (head != slot['baseline'] or not dirty):
                    result.append(slot)
                    continue  # only a dirty, uncommitted candidate can resume an old blocker
                if head != slot['baseline']:
                    # merge-base equality proves descent without treating divergence as a result.
                    try:
                        descends = execution.git(root, 'merge-base', slot['baseline'], head) == slot['baseline']
                    except ValueError:  # no common history: merge-base exits 1
                        descends = False
                    if not descends:
                        target, updates = 'held', {'reason': 'worker HEAD does not descend from baseline',
                                                   'cause': 'diverged'}
                    elif slot.get('paused') and slot.get('landed_tasks') and report_blockers(common, slot) is None:
                        # Resuming a task wait discards its old report, not its commit.
                        # A pause before the fresh report must continue reconciliation,
                        # not offer that retained commit as newly finished work.
                        target, updates = 'interrupted', {
                            'reason': f'stopped while reconciling landed tasks; resumes on attempt {slot["attempt"]}'}
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
                        # Record task waits before the coordinator considers blocker triage.
                        target, updates = 'held', blocker_updates(repo, slot, blockers)
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
