"""Bounded Git observation outside the execution writer's critical section."""
from functools import lru_cache
from pathlib import Path
import subprocess

from pi_autowork.engine import execution_journal as journal
from pi_autowork.engine import task_execution as execution
from pi_autowork.engine import task_store

HISTORY_BUDGET = 32

# Immutable commits only. A steady poll does not reparse the entire task store.
@lru_cache(maxsize=32)
def snapshot(repo, revision):
    return task_store.TaskStore.at(repo, revision)


def observe(repo, delivered_rev=None):
    from pi_autowork.engine import parallel_state as state
    try:
        common = state.common_dir(repo)
        head = execution.git(repo, 'rev-parse', 'HEAD')
        delivered_sha = execution.git(repo, 'rev-parse', delivered_rev) if delivered_rev else None
        store = snapshot(str(repo), head)
        delivered = snapshot(str(repo), delivered_sha).tasks if delivered_sha else {}
        known = journal.known_tasks(common)
        facts, updates = [], []
        coordinator = state.lease(common) or {}
        facts.extend(coordinator.get('lifecycle', []))
        paths = sorted((common / 'slots').glob('*.json'))
        paths += sorted((common / 'slot-history').glob('*/*/slot.json'))
        current = {}
        budget = HISTORY_BUDGET  # bound full historical snapshots per poll
        for path in paths:
            slot = execution.read(path)
            if not slot:
                continue
            task = slot['task_id']
            if path.parent.name == 'slots':
                current[task] = slot
            facts.extend(slot.get('lifecycle', []))
            data = (common / 'slot-data' / task if path.parent.name == 'slots'
                    else path.parent / 'slot-data')
            for attempt in [*slot.get('previous_attempts', []), slot]:
                meta = execution.read(data / f'attempt-{attempt.get("data_attempt", attempt["attempt"])}' / 'meta.json') or {}
                facts.extend(meta.get('lifecycle', []))
            cursors = dict(slot.get('telemetry_revisions', {}))
            # A resume is the same attempt, while a retry has its own baseline/end boundary.
            attempts = {}
            for attempt in [*slot.get('previous_attempts', []), slot]:
                attempts[attempt.get('attempt_id', str(attempt.get('attempt')))] = attempt
            attempts = list(attempts.values())
            for index, attempt in enumerate(attempts):
                baseline = attempt.get('baseline')
                if not baseline or budget <= 0:
                    continue
                end = (attempts[index + 1]['baseline'] if index + 1 < len(attempts)
                       else attempt.get('telemetry_end_revision')
                       or (head if path.parent.name == 'slots' else baseline))
                identity = attempt.get('attempt_id', str(attempt.get('attempt')))
                cursor = cursors.get(identity, baseline)
                if cursor == end:
                    continue
                # Paginate a frozen DAG range by position. A SHA alone cannot
                # represent a prefix spanning sibling branches.
                start = cursor['from'] if isinstance(cursor, dict) else cursor
                target = cursor['to'] if isinstance(cursor, dict) else end
                offset = cursor['offset'] if isinstance(cursor, dict) else 0
                original = snapshot(str(repo), start).tasks.get(task)
                prior_hash = original.contract_hash if original else None
                budget -= 1
                revisions = execution.git(repo, 'log', '--reverse', '--topo-order', '--full-history', '--format=%H',
                                           start + '..' + target, '--', execution.task_path(task)).splitlines()
                selected = revisions[offset:offset + budget // 2]
                for revision in selected:
                    changed = snapshot(str(repo), revision).tasks.get(task)
                    parents = execution.git(repo, 'rev-list', '--parents', '-n', '1', revision).split()[1:]
                    # Compare each commit with its first parent, not an adjacent
                    # log row: merged side branches need not form one linear history.
                    parent = snapshot(str(repo), parents[0]).tasks.get(task) if parents else None
                    prior_hash = parent.contract_hash if parent else prior_hash
                    if changed and prior_hash and changed.contract_hash != prior_hash:
                        facts.append(journal.fact(journal.context(common, attempt), 'contract_edited',
                                                  key=revision, revision=revision))
                    if changed:
                        prior_hash = changed.contract_hash
                    budget -= 2
                done = offset + len(selected)
                if done == len(revisions):
                    cursors[identity] = target
                elif selected:
                    cursors[identity] = {'from': start, 'to': target, 'offset': done}
            if cursors != slot.get('telemetry_revisions', {}):
                updates.append((path, slot.get('attempt_id'), cursors))
        known.update((e['task_id'], e['event']) for e in facts)
        for task, record in store.tasks.items():
            ctx = journal.context(common, current.get(task, {'task_id': task}))
            if (task, 'accepted') not in known:
                if budget <= 0:
                    continue
                facts.extend(journal.acceptance(Path(repo), ctx))
                budget -= 1
            if record.status == 'done' and (task, 'closed') not in known:
                if record.closure != 'coordinator_verified':
                    facts.append(journal.fact(ctx, 'hand_closed', scope='task', revision=head))
                facts.append(journal.fact(ctx, 'closed', scope='task', revision=head))
            if (task in delivered and delivered[task].status == 'done'
                    and (record.status == 'done' or (task, 'closed') in known)
                    and (task, 'delivered') not in known):
                facts.append(journal.fact(ctx, 'delivered', scope='task', revision=delivered_sha))
        # All Git and initial journal scans above are outside writer.lock. Recheck
        # IDs on append, then advance observation cursors only after a durable write.
        facts = journal.pending(common, facts)
        if not facts and not updates:
            return
        with execution.lock(common / 'writer.lock'):
            if facts and not state.event(common, 'task_lifecycle', lifecycle=facts):
                return
            for path, attempt_id, cursors in updates:
                fresh = execution.read(path)
                if fresh and fresh.get('attempt_id') == attempt_id:
                    merged = dict(fresh.get('telemetry_revisions', {}), **cursors)
                    execution.save(path, dict(fresh, telemetry_revisions=merged))
    except (OSError, ValueError, subprocess.SubprocessError, task_store.StoreError):
        pass  # observe on the next cycle, never turn telemetry into a hold
