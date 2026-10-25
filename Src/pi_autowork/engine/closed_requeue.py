"""Reconcile a closed slot only after Git proves its verified closure was reopened.

No runtime flag or prose note alone grants another execution. Read-only evidence is
also used by status. Retirement runs under the owning coordinator's three locks;
a write-ahead archive makes every ref/data move replayable after interruption.
"""
from functools import lru_cache
from pathlib import Path
import re
import tomllib

from pi_autowork.engine import task_queue
from pi_autowork.engine import parallel_state as state
from pi_autowork.engine import task_execution as execution


def git(repo, *args):
    return task_queue._git(repo, *args).decode().strip()


def evidence(repo, slot):
    """Return committed reopen provenance, or None (including pending/manual closes).

    Bind the old verified receipt to this slot's integration, find an actual done→open
    transition on HEAD's first-parent history, then prove either a runner rollback's
    inverse diff or a stale verified contract. Current notes alone never suffice.
    """
    if slot['state'] != 'closed':
        return None
    info = slot.get('integration') or {}
    merge = info.get('commit')
    if not merge:
        return None
    revision = task_queue.commit(repo)
    proof = _evidence(str(Path(repo).resolve()), revision, slot['task_id'], merge, info.get('contract_hash'))
    return dict(proof) if proof else None


@lru_cache(maxsize=128)
def _evidence(repo, head, task, merge, contract_hash):
    # Pin every Git read, including ancestry, to one HEAD. Repeated status/refill
    # reads reuse only that repository+revision+slot-integration proof.
    current = task_queue.record(repo, task, head)
    if current is None or current.status != 'open':
        return None
    reason = task_queue.notes(current).get('Reopened', '')
    if not reason:
        return None
    try:
        git(repo, 'merge-base', '--is-ancestor', merge, head)
        commits = git(repo, 'rev-list', '--first-parent', f'{merge}..{head}').splitlines()
        for revision in commits:
            after = task_queue.record(repo, task, revision)
            before = task_queue.record(repo, task, revision + '^1')
            if after is None or before is None:
                return None  # deletion/recreation is not the old task's verified reopen
            if after.status != 'open':
                return None  # never use an older reopen across another close
            if before.status != 'done':
                continue
            if (before.closure != 'coordinator_verified'
                    or before.closure_evidence != f'tasks/evidence/{task}.toml'
                    or task_queue.notes(after).get('Reopened') != reason):
                return None
            receipt = tomllib.loads(git(repo, 'show', f'{revision}^1:tasks/evidence/{task}.toml'))
            if (receipt.get('task') != task or receipt.get('integration') != merge
                    or receipt.get('contract_hash') != contract_hash
                    or receipt.get('result') != 'pass'):
                return None
            if ('its contract changed after its verified close' in reason
                    and before.contract_hash != receipt['contract_hash']
                    and after.contract_hash == before.contract_hash):
                return dict(revision=revision, kind='stale_contract', integration=merge)
            if 'reverted by optimistic landing' not in reason:
                return None
            inverse = git(repo, 'diff', '--no-ext-diff', '--binary', merge, merge + '^1')
            for rollback in git(repo, 'rev-list', '--first-parent', f'{merge}..{revision}^1').splitlines():
                message = git(repo, 'show', '-s', '--format=%B', rollback)
                if (message.startswith(f'revert({task}): its landing broke the full check on main at ')
                        and f'This reverts commit {merge}.' in message
                        and inverse and inverse == git(repo, 'diff', '--no-ext-diff', '--binary',
                                                       rollback + '^1', rollback)):
                    return dict(revision=revision, kind='rollback', integration=merge, rollback=rollback)
            return None
    except (ValueError, OSError):
        return None  # missing/malformed history cannot authorize a new attempt
    return None


def retire(repo, common, owner_pid, slot):
    """Supported closed-slot set-aside. Caller holds dispatch/integration/writer locks.

    The manifest precedes every mutation. Old attempt refs (even ones cleaned up on
    close) are kept, dirty worktrees move intact, and slot data moves before the slot
    disappears. Reentry finishes that same archive, never consumes another attempt.
    """
    state.require_owner(common, owner_pid)
    proof = evidence(repo, slot)
    if proof is None:
        raise ValueError('closed slot needs committed verified reopen/rollback evidence; do not reset it')
    if any(state.worker_live(attempt) for attempt in [slot, *slot.get('previous_attempts', [])]):
        raise ValueError('cannot requeue a closed slot with a live worker')
    task = slot['task_id']
    if git(repo, 'status', '--porcelain', '--', f'tasks/items/{task}.md'):
        raise ValueError('cannot requeue over uncommitted task bookkeeping')
    history = execution.safe_path(common / 'slot-history' / task)
    data = execution.safe_path(common / 'slot-data' / task)
    manifest = execution.safe_path(common / 'closed-requeue' / f'{task}.json')
    execution.safe_path(state.slot_path(common, task))
    transaction = execution.read(manifest)
    if transaction and transaction['slot'] != slot:
        archived = execution.read(Path(transaction['target']) / 'slot.json') or {}
        if (archived.get('reopened') != transaction['proof']
                or any(archived.get(k) != v for k, v in transaction['slot'].items())):
            raise ValueError('closed requeue provenance changed; inspect retained transaction')
        # Crash after unlinking the prior slot: its complete archive proves retirement.
        manifest.unlink()
        transaction = None
    if transaction and transaction['proof'] != proof:
        raise ValueError('closed requeue provenance changed; inspect retained transaction')
    if not transaction:
        number = 1
        attempts = [*slot.get('previous_attempts', []), slot]
        refs = [ref.removeprefix('refs/heads/') for ref in
                git(repo, 'for-each-ref', '--format=%(refname)', 'refs/heads/').splitlines()]
        if any(a['branch'].startswith(ref + '/') for ref in refs for a in attempts):
            raise ValueError('set-aside ref namespace has an existing ancestor; preserve it and inspect')
        def collision(branch):
            return any(ref == branch or ref.startswith(branch + '/') or branch.startswith(ref + '/')
                       for ref in refs)
        while ((history / str(number)).exists()
               or any(collision(a['branch'] + f'-set-aside-{number}')
                      or Path(a['worktree'] + f'-set-aside-{number}').exists() for a in attempts)):
            number += 1
        moves = []
        for attempt in attempts:
            branch, worktree = attempt['branch'], attempt['worktree']
            if any(move['branch'] == branch for move in moves):
                continue
            tip = git(repo, 'rev-parse', '--verify', '--quiet', f'refs/heads/{branch}') if git(
                repo, 'branch', '--list', branch) else attempt.get('commit')
            if not tip:
                raise ValueError('closed attempt has no retained commit')
            moves.append(dict(branch=branch, worktree=worktree, tip=tip,
                              branch_now=branch + f'-set-aside-{number}',
                              worktree_now=worktree + f'-set-aside-{number}'))
        cleanup = [str(path) for path in common.glob(f'cleanup-{task}-*.json')
                   if re.fullmatch(r'cleanup-' + re.escape(task) + r'-[0-9]+\.json', path.name)]
        transaction = dict(slot=slot, proof=proof, target=str(history / str(number)), moves=moves,
                           cleanup=cleanup)
    # Validate every source and destination before the manifest or any move/ref write.
    # In particular Path.rename itself does not reject symlinked archive parents.
    target = execution.safe_path(Path(transaction['target']))
    execution.safe_path(target / 'slot-data')
    execution.safe_path(target / 'slot.json')
    for path in transaction.get('cleanup', []):
        execution.safe_path(path)
        execution.safe_path(target / Path(path).name)
    for move in transaction['moves']:
        execution.safe_path(move['worktree'])
        execution.safe_path(move['worktree_now'])
    if not manifest.exists():
        execution.save(manifest, transaction)
    for move in transaction['moves']:
        old, new = Path(move['worktree']), Path(move['worktree_now'])
        if old.exists():
            git(repo, 'worktree', 'move', str(old), str(new))
        elif new.exists():
            # An interrupted prior move is acceptable only as a registered worktree.
            trees = git(repo, 'worktree', 'list', '--porcelain').splitlines()
            if f'worktree {new}' not in trees:
                raise ValueError('set-aside destination is not the retained worktree')
        branches = git(repo, 'branch', '--list', move['branch'], move['branch_now'])
        if git(repo, 'branch', '--list', move['branch_now']):
            if (git(repo, 'rev-parse', move['branch_now']) != move['tip']
                    or git(repo, 'branch', '--list', move['branch'])):
                raise ValueError('retained branch changed during closed requeue')
        elif branches:
            if git(repo, 'rev-parse', move['branch']) != move['tip']:
                raise ValueError('worker branch changed during closed requeue')
            git(repo, 'branch', '-m', move['branch'], move['branch_now'])
        else:
            git(repo, 'branch', move['branch_now'], move['tip'])
    target.mkdir(parents=True, exist_ok=True, mode=0o700)
    if data.exists():
        data.rename(target / 'slot-data')
    for path in transaction.get('cleanup', []):
        source = Path(path)
        destination = target / source.name
        if source.exists():
            if destination.exists():
                raise ValueError('cleanup archive collision; retain both and inspect')
            source.rename(destination)
    execution.save(target / 'slot.json', dict(slot, set_aside={'renamed': transaction['moves']},
                                             reopened=proof))
    state.slot_path(common, task).unlink()
    state.event(common, 'slot_set_aside', task_id=task, state='closed', renamed=transaction['moves'],
                history=str(target), reopened=proof)
    manifest.unlink()
    return dict(outcome='SET_ASIDE', task=task, previous_state='closed', requeued=True,
                renamed=transaction['moves'], history=str(target), reopened=proof)
