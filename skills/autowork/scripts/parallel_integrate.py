"""Serialized, validated local integration. Worker reports are evidence, not acceptance."""
import math
from datetime import datetime
import json
import os
from pathlib import Path
import subprocess
import re
import sys
import time


import parallel_dispatch as dispatch
import parallel_plan as plan
import parallel_state as state
from parallel_state import close_files  # the close's own file set; re-exported for callers
import task_execution as execution
from worktree_paths import canonical_root, worktree_path


def git(repo, *argv, raw=False):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *argv], env=env,
                            capture_output=True, text=not raw, timeout=60)
    if result.returncode:
        error = result.stderr.decode(errors='replace') if raw else result.stderr
        raise ValueError('git ' + argv[0] + ' failed: ' + error.strip())
    return result.stdout if raw or '-z' in argv else result.stdout.strip()


def ancestor(repo, older, newer):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', older, newer], env=env,
                          capture_output=True, timeout=60).returncode == 0


def changed(repo, baseline, commit):
    # Disable rename folding so both the deleted source and new destination are checked.
    value = git(repo, 'diff', '--name-only', '--no-renames', '-z', baseline + '..' + commit)
    return value.rstrip('\0').split('\0') if value else []


def context(repo, owner_pid):
    repo = Path(execution.git(Path(repo).resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common = state.common_dir(repo)
    owner = state.require_owner(common, owner_pid)
    if owner['workspace'] != str(repo):
        raise ValueError('integration must target the coordinator canonical checkout')
    return repo, common


def slot_for(common, task):
    return next((s for s in state.slots(common) if s['task_id'] == task), None)


class Hold(ValueError):
    """A check that holds the slot, with a machine-readable cause and details.

    Causes: scope (changed files outside Touches; ``outside`` lists them), overlap
    (another slot's or a coordinator file), report, conflict, validation,
    contract_changed, moved (canonical HEAD moved twice), blocker, runner_merged
    (the branch moved past its commit only through session merges; ``tip`` names it).
    """
    def __init__(self, cause, reason, **details):
        super().__init__(reason)
        self.cause, self.details = cause, details


class ReportedBlocker(Hold):
    """The worker's own report names work it could not finish."""
    def __init__(self, reason):
        super().__init__('blocker', reason)


def hold(common, slot, reason, **updates):
    slot = state.change(common, slot, 'held', dict(updates, reason=reason))
    return {'outcome': 'HELD', 'task': slot['task_id'], 'reason': reason,
            **{k: updates[k] for k in ('cause', 'outside', 'requested') if k in updates}}


BRANCH_HOLD = 'unexpected worker branch'
STALE_VALIDATION = 'missing, failed, stale or mismatched integration validation'


def landed(repo, commit):
    """Whether ``commit`` is in the canonical HEAD; None when that cannot be told."""
    if not commit:
        return None
    try:
        return git(repo, 'merge-base', commit, 'HEAD') == commit
    except ValueError:
        return None


def expected_branch(slot):
    """A held task's retry runs on a fresh -r2 branch; an interrupted or released
    worker restarts on its original branch, even though both count as attempt 2.
    A worker paused by a deliberate stop resumes the same attempt on the same branch,
    so its paused record is judged by the attempts before it."""
    history = slot.get('previous_attempts') or []
    previous = history[-1] if history else {}
    if (previous.get('paused') and previous.get('state') in ('interrupted', 'released')
            and previous.get('attempt') == slot['attempt']):
        return expected_branch(dict(previous, previous_attempts=history[:-1]))
    retried = slot['attempt'] == 2 and previous.get('state') == 'held' and not slot.get('readopted')
    return 'autowork/' + slot['task_id'] + ('-r2' if retried else '')


def live_items(value):
    """A report's pending live checks as non-empty strings, whatever shape the worker wrote:
    a string, a list of strings, or objects with their text. A finished commit is never
    held, and its task never rerun, over the format of this list (india, TASK-011)."""
    items = value if isinstance(value, list) else [value] if value else []
    texts = []
    for item in items:
        if isinstance(item, dict):
            item = ' — '.join(str(item[k]) for k in ('check', 'command', 'summary', 'description', 'reason')
                              if item.get(k)) or json.dumps(item, sort_keys=True)
        text = ' '.join(str(item).split()) if item is not None else ''
        if text:
            texts.append(text)
    return texts


def verify(repo, common, slot, contracts):
    task = contracts.get(slot['task_id'])
    if task is None:
        raise ValueError('task contract is no longer eligible')
    if state.worker_live(slot):
        raise ValueError('worker still running')
    state.workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
    if slot['branch'] != expected_branch(slot):
        raise ValueError(BRANCH_HOLD)
    abort_abandoned_merge(common, slot)
    tip = runner_merged_tip(repo, slot)
    if tip and not adopt_runner_merged(repo, common, slot, tip):
        raise Hold('runner_merged', f'its branch moved past the reported commit {slot["commit"][:12]} to {tip[:12]} '
                   'only through merges of the session; the runner reruns it from that tip', tip=tip)
    commit = slot.get('commit', '')
    try:
        lineage = git(repo, 'merge-base', slot['baseline'], commit) == slot['baseline'] if commit else False
    except ValueError:
        lineage = False
    if (not commit or commit == slot['baseline'] or git(repo, 'rev-parse', '--verify', commit + '^{commit}') != commit
            or git(repo, 'rev-parse', 'refs/heads/' + slot['branch']) != commit or not lineage):
        raise ValueError('reported commit/branch/lineage mismatch')
    report = execution.read(dispatch.data_dir(common, slot) / 'report.json')
    if not isinstance(report, dict):
        # Said first: the checks below would otherwise blame a field of a report that is
        # not there (india, TASK-011: "pending_live must be a list of strings").
        raise Hold('report', 'the worker wrote no report.json')
    files = changed(repo, slot['baseline'], commit)
    blockers = state.report_blockers(common, slot)
    if blockers:
        raise ReportedBlocker(state.blocker_reason(blockers))
    for field in ('pending_live', 'unrelated_failures', 'environment_failures'):
        report[field] = live_items(report.get(field))
    mismatch = report_mismatch(repo, report, slot['task_id'], commit, files)
    if mismatch:
        raise Hold('report', 'report.json does not match worker commit/files or reports failure: ' + mismatch)
    verify_scope(repo, common, slot, contracts, files)
    return files, report


def abort_abandoned_merge(common, slot):
    """Abort a conflict-free merge a resolver left uncommitted in the task worktree (TOOLSET-280-4f).
    verify runs only with no worker and no resolver in that worktree, so nobody is finishing it,
    and the resolver can merge again. One with unmerged paths is left for the conflict hold."""
    root = execution.safe_path(slot['worktree'])
    marker = Path(git(root, 'rev-parse', '--path-format=absolute', '--git-path', 'MERGE_HEAD'))
    if not marker.is_file() or git(root, 'diff', '--name-only', '--diff-filter=U'):
        return
    merging = marker.read_text().strip()
    git(root, 'merge', '--abort')
    state.event(common, 'abandoned_merge_aborted', task_id=slot['task_id'], merge_head=merging)


def runner_merged_tip(repo, slot):
    """The branch tip, when it moved past the recorded commit only through merges whose other
    parents are canonical revisions; else None. One fleet runner's resolver merged the session
    into two held branches 13 and 15 times while adoption was refused, and the next verify asked
    the owner to rescope both tasks for a 'reported commit/branch/lineage mismatch'."""
    commit = slot.get('commit') or ''
    try:
        tip = git(repo, 'rev-parse', '--verify', 'refs/heads/' + slot['branch'])
        if not commit or tip == commit or not ancestor(repo, commit, tip):
            return None
        head = git(repo, 'rev-parse', 'HEAD')
        steps = git(repo, 'rev-list', '--first-parent', '--parents', f'{commit}..{tip}').splitlines()
    except ValueError:
        return None
    for line in steps:
        parents = line.split()[1:]
        if len(parents) < 2 or not all(ancestor(repo, p, head) for p in parents[1:]):
            return None  # a commit nobody recorded: the owner question names it
    return tip


def adopt_runner_merged(repo, common, slot, tip):
    """Adopt a runner-merged tip as a resolver's merge is adopted, within the same three adoptions;
    False when the limit is reached or the worktree is not clean on that tip. Updates ``slot``."""
    count = slot.get('merged_count', 1 if slot.get('merged_base') else 0)
    root = execution.safe_path(slot['worktree'])
    try:
        if (count >= 3 or git(root, 'rev-parse', 'HEAD') != tip
                or git(root, 'status', '--porcelain', '--untracked-files=no')):
            return False
        base = git(repo, 'merge-base', 'HEAD', tip)
    except ValueError:
        return False
    data = dispatch.data_dir(common, slot)
    report = execution.read(data / 'report.json')
    if not isinstance(report, dict) or report.get('task') != slot['task_id']:
        return False
    report.update(commit=tip, changed_files=changed(repo, base, tip))
    execution.save(data / 'report.json', report)
    value = dict(slot, baseline=base, commit=tip, merged_base=base, merged_count=count + 1)
    slot.update(state.write_slot(common, value, slot))
    state.event(common, 'runner_merged_adopted', task_id=slot['task_id'], commit=tip, merged_count=count + 1)
    return True


def report_mismatch(repo, report, task, commit, files):
    """What in report.json disagrees with the worker's commit, or ''. A commit written as an
    abbreviated SHA that names the same commit is the same commit."""
    if report.get('task') != task:
        return f'task is {report.get("task")!r}'
    named = report.get('commit')
    if named != commit:
        try:
            same = isinstance(named, str) and len(named) >= 7 and git(repo, 'rev-parse', '--verify',
                                                                      named + '^{commit}') == commit
        except ValueError:
            same = False
        if not same:
            return f'commit is {named!r}, the branch is at {commit[:12]}'
    changed_files = report.get('changed_files')
    if not isinstance(changed_files, list) or not all(isinstance(p, str) for p in changed_files):
        return 'changed_files is not a list of paths'
    if sorted(changed_files) != sorted(files):
        missing, extra = sorted(set(files) - set(changed_files)), sorted(set(changed_files) - set(files))
        return f'changed_files differ from the commit (missing {missing[:5]}, extra {extra[:5]})'
    if report.get('blockers') != []:
        return 'it reports blockers'
    checks = report.get('checks')
    if not isinstance(checks, list) or any(not isinstance(c, dict) or c.get('result') != 'pass' for c in checks):
        return 'a check did not pass'
    return ''


def passed(check):
    """A validation run passed: it exited 0 with its inputs unchanged. Build daemons it left
    behind (Gradle, Kotlin, Flutter) were killed at the boundary before anything is judged,
    and the integration tree is checked separately, so they alone do not fail it."""
    receipt = (check or {}).get('command_receipt') or {}
    return (check or {}).get('outcome') == 'EXECUTED' or (
        check.get('outcome') == 'CHILDREN_TERMINATED' and receipt.get('exit_code') == 0
        and receipt.get('inputs_match') is True)


def validation_reason(check, limit=600):
    """': <why>' from the validation's own `AUTOWORK_HOLD_REASON: <why>` line, or '' (TOOLSET-180-72:
    a retry, a person and the DOCS-MAINTAINER see which tests the candidate broke)."""
    try:
        text = Path(((check or {}).get('command_receipt') or {}).get('log') or '').read_text(errors='replace')
    except (OSError, TypeError):
        return ''
    found = [line[len('AUTOWORK_HOLD_REASON: '):].strip() for line in text.splitlines()
             if line.startswith('AUTOWORK_HOLD_REASON: ')]
    return (': ' + found[-1][:limit]) if found and found[-1] else ''


def report_matches(repo, common, slot):
    report = execution.read(dispatch.data_dir(common, slot) / 'report.json')
    if not isinstance(report, dict):
        return False
    try:
        return not report_mismatch(repo, report, slot['task_id'], slot['commit'],
                                   changed(repo, slot['baseline'], slot['commit']))
    except ValueError:
        return False


def verify_scope(repo, common, slot, contracts, files):
    """Undeclared protected files hold; coordinator files are stripped before validation:
    Touches schedule work and never hold it, and two tasks editing the same file are settled
    by the merge into the base, in priority order (TOOLSET-161-17)."""
    # A broad directory alone does not reserve hypothetical future manifests.
    # Require an explicit serial declaration before accepting newly created shared
    # build/schema/CI state, even if other workers have already finished.
    protected = [p for p in files if plan.protected_path(p)]
    if protected:
        rescoped = slot.get('rescoped_contract') if slot.get('rescoped') else None
        contract = rescoped or dispatched_contract(common, slot)
        admitted = {'fields': execution.goals_module().task_fields(contract)} if contract else None
        inventory = dispatch.protected_files(repo, slot['baseline'])
        if rescoped:
            # An answered rescope admits only the protected paths it actually reserves.
            # A different manifest, or an ordinary directory naming a new one, is not enough.
            declared = plan.paths(admitted['fields'].get('Touches', ''))
            outside = []
            for path in protected:
                matching = [p for p in declared if not plan.overlap([path], [p], [])['outside']]
                if not plan._solo({'fields': {'Touches': ', '.join(matching)}},
                                  [path] if path in inventory else []):
                    outside.append(path)
            if outside:
                raise Hold('scope', 'rescoped contract does not reserve protected files: ' + str(outside)
                           + '; a rerun or a contract change is needed', outside=outside)
        elif not admitted or not plan._solo(admitted, inventory):
            raise Hold('scope', 'protected files need serial admission in the original task contract: '
                       + str(protected), outside=protected)


def head_conflicts(repo, commit):
    """The files ``commit`` conflicts in with canonical HEAD when merge_candidate would hold it
    for them; [] when it merges, or its conflicts are only ledgers merge_candidate resolves."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), 'merge-tree', '--write-tree', '--name-only', '--no-messages',
                             'HEAD', commit], env=env, capture_output=True, text=True, timeout=60)
    files = [p for p in result.stdout.splitlines()[1:] if p] if result.returncode == 1 else []
    return files if set(files) - set(dispatch.COORDINATOR_FILES) else []


def merge_candidate(root, slot, baseline):
    """Merge every candidate, including adopted resolver merges, without its ledger edits.

    Save original proposal hunks, not concurrent coordinator edits. A base rename can
    redirect work into a ledger path: capture that delta before resolving its conflicts.
    Other conflicts still hold. Raw bytes keep blank context, CRLF and binary patches intact.
    """
    owned = set(dispatch.COORDINATOR_FILES)
    proposed = sorted(owned.intersection(changed(root, slot['baseline'], slot['commit'])))
    redirected, patch = [], b''
    try:
        git(root, 'merge', '--no-ff', '--no-edit', slot['commit'])
    except ValueError:
        conflicts = git(root, 'diff', '--name-only', '--diff-filter=U', '-z').rstrip('\0').split('\0')
        if not conflicts or set(conflicts) - owned:
            git(root, 'merge', '--abort')
            raise Hold('conflict', 'merge conflict; worker and canonical checkout preserved',
                       conflict_files=[p for p in conflicts if p])
        redirected = sorted(set(conflicts) - set(proposed))
        for path in redirected:
            if ' 3\t' in git(root, 'ls-files', '--unmerged', '--', path):
                git(root, 'restore', '--theirs', '--worktree', '--', path)
                git(root, 'add', '--', path)
            else:  # worker deleted the source that canonical renamed into a ledger path
                git(root, 'rm', '-f', '--', path)
        if redirected:
            patch = git(root, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--no-renames',
                        '--cached', baseline, '--', *redirected, raw=True)
        existing = [p for p in conflicts if git(root, 'ls-tree', baseline, '--', p)]
        deleted = sorted(set(conflicts) - set(existing))
        if deleted:  # restore cannot remove an unmerged path missing from its source tree
            git(root, 'rm', '-f', '--', *deleted)
        if existing:
            git(root, 'restore', '--source=' + baseline, '--staged', '--worktree', '--', *existing)
        git(root, 'commit', '--no-edit', '--allow-empty')
    actual = sorted(owned.intersection(changed(root, baseline, 'HEAD')))
    paths = sorted(set(proposed) | set(actual) | set(redirected))
    if not paths:
        return None
    for before, after, names in ((slot['baseline'], slot['commit'], proposed),
                                (baseline, 'HEAD', sorted(set(actual) - set(proposed)))):
        if names:
            patch += git(root, 'diff', '--no-ext-diff', '--no-textconv', '--binary', '--no-renames',
                         before, after, '--', *names, raw=True)
    if actual:
        # restore also removes worker-created ledger paths absent from the base.
        git(root, 'restore', '--source=' + baseline, '--staged', '--worktree', '--', *actual)
        git(root, 'commit', '--amend', '--no-edit', '--allow-empty')
    return {'paths': paths, 'patch': patch}


class WritersBusy(ValueError):
    """Another live agent session works in the canonical checkout: wait, it is no verdict."""


WRITER_HOLD = 'live or unknown external writer'
# The owner's uncommitted planning files do not stop a merge elsewhere: landing reconciles
# them or keeps the branch (TOOLSET-223-8e). A planning file the session holds open for
# writing still counts (it stays in ``mine``).
PLANNING_FILES = ('TODO.md', 'TODO.archive.md', 'todo.archive.md', 'goals.json', 'BLOCKERS.md')
WRITERS_BUSY_SKIP = state.WRITERS_BUSY_SKIP
writers_busy = state.writers_busy


def main_checkout(repo):
    try:
        return str(canonical_root(repo))
    except ValueError:
        return None


def planning_only(paths):
    """Whether every path is a planning file or under docs/ (TOOLSET-233-ba): a session that moved
    only by such commits during validation changed nothing the validation judged."""
    return bool(paths) and all(p in PLANNING_FILES or p.startswith('docs/') for p in paths)


def remerge_planning(repo, root, merge, head):
    """The validated ``merge`` on top of a session head that moved only by planning commits:
    a merge of ``head`` into it in the integration worktree, or None when that conflicts or
    would change anything else."""
    try:
        git(root, 'merge', '--no-ff', '--no-edit', head)
    except ValueError:
        git(root, 'merge', '--abort')
        return None
    remerged = git(root, 'rev-parse', 'HEAD')
    brought = changed(repo, merge, remerged)
    if brought and not planning_only(brought):
        git(root, 'checkout', '-q', '--detach', merge)
        return None
    return remerged


def touches_none_of(worker, files, main):
    """A session working in the main checkout that neither holds open nor has left uncommitted
    any of ``files`` (sierra, 2026-10-16: TASK-026 waited an hour on an unrelated session).

    Other checkouts the same session also has open are irrelevant: the merge writes only
    ``files`` in the canonical checkout, and those paths are what this compares."""
    if files is None or main not in (worker.get('workspaces') or []):
        return False
    mine = {os.path.relpath(path, main) for path in worker.get('written') or []}
    listing = git(main, 'status', '--porcelain', '-z', '--untracked-files=all')
    dirty = {entry[3:] for entry in listing.split('\0') if entry} if listing else set()
    dirty -= set(PLANNING_FILES)
    return not (set(files) & (mine | dirty))


def slot_workspace_roots(common, slot):
    """Read the slot's saved temp allocation without allocating or migrating it."""
    roots = [Path(slot['worktree'])]
    try:
        data = dispatch.data_dir(common, slot)
        allocation = execution.read(data.parent / 'tmp.json')
        temporary = (dispatch._tmp_record(common, allocation) if allocation is not None
                     else execution.safe_path(data / 'tmp'))  # older attempt-local TMPDIR
        if temporary.is_dir() and temporary.stat().st_uid == os.getuid():
            roots.append(temporary)
    except (OSError, ValueError):
        pass  # Missing or unsafe temp evidence never widens containment.
    return roots


def require_no_writers(repo, files=None):
    """Refuse while another agent may be writing. With ``files`` (the paths the write
    changes), a session in the main checkout blocks only when it holds one of them open or
    has left one uncommitted there, whichever checkout the write happens in. Its presence,
    its activity and any other checkout it has open never block. Sessions that work in a
    worker's worktree and Autowork commands block as before."""
    workers = execution.external_workers(repo)
    main = main_checkout(repo)
    common = state.common_dir(repo)
    pool = [(slot, slot_workspace_roots(common, slot)) for slot in state.slots(common)]
    if main:
        # A person's session in the canonical checkout never gates work by existing, being
        # busy or having another checkout open: only a file it holds open or has left
        # uncommitted there, and only for a write that touches that same file, waits. A
        # process inside a slot's worktree is not covered: it is judged as before below.
        roots = [root for _, roots in pool for root in roots]
        leaders = [slot['worker'] for slot, _ in pool if slot.get('worker')]
        def in_pool(worker):
            return any(Path(w).is_relative_to(root)
                       for w in worker.get('workspaces') or [] for root in roots)
        def recorded(worker):  # a slot's leader running somewhere the record does not say
            return any(execution.identity(worker['pid']) == leader for leader in leaders)
        workers = [w for w in workers
                   if not (w['kind'] == 'session' and touches_none_of(w, files, main)
                           and not in_pool(w) and not recorded(w))]
    blocking = execution.blocking_workers(workers, repo)
    unattributed = {}
    for worker in workers:
        if worker['active'] is False:
            continue
        # Workspace containment is necessary, not proof of pool membership. A
        # child in a new session still belongs to its birth-checked live leader.
        attributed = False
        for slot, roots in pool:
            inside = [any(Path(w).is_relative_to(root) for root in roots) for w in worker['workspaces']]
            if not any(inside):
                continue
            leader = slot.get('worker')
            if not all(inside):
                why = 'process uses workspaces outside the slot'
            elif slot['state'] not in ('dispatched', 'running'):
                why = 'slot is not dispatched/running'
            elif not leader:
                why = 'no recorded worker leader'
            elif execution.identity(leader['pid']) != leader:
                why = 'leader identity is dead or changed'
            elif not state.owns_process(leader, {k: worker[k] for k in ('pid', 'start_ticks', 'boot_id')}):
                why = 'parent chain/group does not prove live leader ownership'
            else:
                attributed = True
                break
            unattributed[worker['pid']] = f"unattributed process in {slot['task_id']}'s worktree: {why}"
        # Never exempt a process already blocked by the checkout/command rule;
        # it still benefits from slot diagnostics when it also touches a worker.
        if not attributed and worker not in blocking:
            blocking.append(worker)
    # A process that exited during these checks (a short tool run) writes nothing; only a
    # writer still alive with the same birth identity blocks.
    blocking = [w for w in blocking
                if execution.identity(w['pid']) == {k: w.get(k) for k in ('pid', 'start_ticks', 'boot_id')}]
    if blocking:
        def describe(worker):
            name = Path((execution.argv_of(worker['pid']) or ['?'])[0]).name or '?'
            detail = unattributed.get(worker['pid']) or worker.get('evidence') or worker.get('kind', '')
            return (f"pid {worker['pid']} {name} in {', '.join(worker.get('workspaces') or ['?'])}"
                    f" ({detail})")
        raise WritersBusy('live or unknown external writer/session; preserve canonical checkout: '
                         + '; '.join(describe(w) for w in blocking[:3]))


def integration_worktree(repo, common, baseline):
    path = worktree_path(repo, 'autowork-integration')
    if path.exists():
        if not dispatch.created_by_autowork(common, path, '(detached)'):
            raise ValueError('integration worktree was not created by this coordinator')
        if state.common_dir(path) != common or git(path, 'rev-parse', '--show-toplevel') != str(path):
            raise ValueError('integration worktree identity changed')
        if git(path, 'status', '--porcelain', '--untracked-files=all'):
            # Validation or review left changes in this exclusive, journaled, disposable
            # worktree (integration.lock is held). Keep them as a patch, then reset it;
            # never anywhere else.
            residue = execution.safe_path(common / 'integration-residue')
            residue.mkdir(exist_ok=True, mode=0o700)
            git(path, 'add', '-A')
            patch = residue / (time.strftime('%Y%m%d-%H%M%S') + '-' + git(path, 'rev-parse', '--short', 'HEAD') + '.patch')
            patch.write_text(git(path, 'diff', '--cached', '--binary', 'HEAD'))
            git(path, 'reset', '-q', '--hard', 'HEAD')
            state.event(common, 'integration_residue_saved', worktree=str(path), patch=str(patch))
        if git(path, 'rev-parse', '--abbrev-ref', 'HEAD') != 'HEAD':
            raise ValueError('integration worktree is no longer detached')
        git(path, 'checkout', '--detach', baseline)
    else:
        git(repo, 'worktree', 'add', '--detach', str(path), baseline)
        state.event(common, 'worktree_created', worktree=str(path), branch='(detached)', baseline=baseline)
    return path


# Once a slot is integrating, its later writer.lock acquisitions wait this long: the runner's own
# loop takes the lock for a moment every cycle beside the review (TOOLSET-194-46), and a lost
# race left the slot integrating, to be held later as an abandoned integration.
LOCK_WAIT = float(os.environ.get('AUTOWORK_LOCK_WAIT', '60'))


def release_unfinished(repo, common, owner_pid, task):
    """Return an integrating slot to reported, dropping its integration checkout; BUSY. It waits
    longer than the integration did: this review runs beside the loop, and the slot must not stay
    integrating."""
    try:
        with execution.lock(common / 'writer.lock', wait=5 * LOCK_WAIT):
            state.require_owner(common, owner_pid)
            slot = slot_for(common, task)
            if slot and slot['state'] == 'integrating':
                root = (slot.get('integration') or {}).get('worktree')
                if root and Path(root).is_dir():
                    subprocess.run(['git', '-C', str(repo), 'worktree', 'remove', '--force', root], capture_output=True)
                state.change(common, slot, 'reported', {'integration': None, 'checks': None})
    except BlockingIOError:
        pass  # still integrating: the next call revalidates it, as before
    return {'outcome': 'BUSY', 'task': task, 'reason': 'the repository writer lock stayed busy; integrating again later'}


def integrate(repo, owner_pid, task, argv, timeout, reviewer=None, base=None, batch_order=()):
    if not argv or timeout is None or not math.isfinite(timeout) or timeout <= 0:
        raise ValueError('--integrate requires --run argv and a positive finite --timeout')
    repo, common = context(repo, owner_pid)
    # Separate from writer.lock: validation never holds the shared state lock.
    with execution.lock(common / 'integration.lock'):
        with execution.lock(common / 'writer.lock'):
            state.require_owner(common, owner_pid)
            slot = slot_for(common, task)
            if not slot or slot['state'] not in ('reported', 'integrating'):
                raise ValueError('integration requires a reported or abandoned integrating slot')
            if slot['state'] == 'reported' and task in dispatch.retired(repo, base):
                # Closed meanwhile (TOOLSET-218-d0): a duplicate of finished work never lands.
                with execution.lock(common / 'dispatch.lock'):
                    aside = _retire(repo, common, dict(slot, cause='closed_on_base'), False)
                state.event(common, 'closed_on_base', task_id=task, base=base or '')
                return dict(aside, reason=f'{task} is closed on {base or "this branch"}; its commit is set aside')
            contracts = {t['id']: t for t in dispatch.contracts(repo)}
            slots = {s['task_id']: s for s in state.slots(common) if s['state'] in ('reported', 'integrating')}
            # A candidate refused for a live writer steps aside for a bounded window, so one
            # waiting commit never stops the rest from integrating (TOOLSET-223-8e).
            available = {tid for tid, held in slots.items() if not writers_busy(held)} or set(slots)
            # A changed reviewer's second look never jumps ahead of a fresh candidate.
            # Stable sorting preserves TODO priority within each group.
            ordered = sorted((t for t in contracts if t in available), key=lambda t: bool(slots[t].get('reverified')))
            # Candidates verified together land first, in the order they were verified: each verdict
            # holds only for its step of that chain, and a task landing between them voided them all.
            chain = [t for t in batch_order if t in available]
            ordered = chain + [t for t in ordered if t not in chain]
            first = next(iter(ordered), None)
            if first != task:  # it names the one, so the runner starts it next (TOOLSET-238-11)
                # Holding a conflict lands nothing, so it needs no turn: behind one long review
                # nine conflicting candidates waited hours for the resolver that only a hold starts.
                conflicts = head_conflicts(repo, slot['commit'])
                if conflicts:
                    return hold(common, slot, 'merge conflict; worker and canonical checkout preserved',
                                cause='conflict', conflict_files=conflicts)
                raise ValueError(f'integrate the highest-priority reported task first: {first}')
            try:
                files, report = verify(repo, common, slot, contracts)
                require_no_writers(repo, files)
                if slot['state'] == 'integrating':
                    recovered = recover_integration(repo, common, slot, contracts)
                    if recovered:
                        return recovered
            except WritersBusy as exc:
                # The commit stays reported and integrates once that session is gone; the stamp
                # lets the next reported task go first until the window passes (TOOLSET-223-8e).
                slot = state.write_slot(common, dict(slot, writers_busy_at=time.time(),
                                                     writers_busy_reason=str(exc)), slot)
                return {'outcome': 'BUSY', 'task': task, 'reason': str(exc)}
            except Hold as exc:
                return hold(common, slot, str(exc), cause=exc.cause, **exc.details)
            except (ValueError, OSError) as exc:
                return hold(common, slot, str(exc))
            if slot['state'] == 'reported':
                slot = state.change(common, slot, 'integrating', {'report': report})
        check, queued = None, 0
        def save_receipt(path, value):
            nonlocal slot
            with execution.lock(common / 'writer.lock', wait=LOCK_WAIT):
                state.require_owner(common, owner_pid)
                execution.save(path, value)
                slot = state.write_slot(common, dict(slot, checks=value), slot)

        try:
            for attempt in range(2):
                with execution.lock(common / 'writer.lock', wait=LOCK_WAIT):
                    state.require_owner(common, owner_pid)
                    require_no_writers(repo, changed(repo, slot['baseline'], slot['commit']))
                    baseline = git(repo, 'rev-parse', 'HEAD')
                    if git(repo, 'merge-base', baseline, slot['commit']) == slot['commit']:
                        raise ValueError('worker commit already in canonical HEAD; no fresh two-parent integration')
                    canonical_branch = git(repo, 'symbolic-ref', 'HEAD')
                    root = integration_worktree(repo, common, baseline)
                    dropped = merge_candidate(root, slot, baseline)
                    if dropped:
                        target = execution.safe_path(dispatch.data_dir(common, slot) / 'ledger-edit.patch')
                        target.write_bytes(dropped['patch'])
                        dropped['patch'] = str(target)
                    merge = git(root, 'rev-parse', 'HEAD')
                    if git(repo, 'rev-list', '--parents', '-n', '1', merge).split()[1:] != [baseline, slot['commit']]:
                        raise ValueError('integration candidate must have canonical and worker parents')
                    files = changed(repo, baseline, merge)
                    verify_scope(repo, common, slot, contracts, files)
                    run_id = execution.uuid.uuid4().hex
                    integration = {'commit': merge, 'baseline': baseline, 'changed_files': files, 'worktree': str(root),
                                   'check_receipt': str(common / (run_id + '.json')),
                                   'task_contract': contracts[task]['contract'], 'canonical_branch': canonical_branch}
                    # Durable intent precedes validation and FF. An abandoned helper
                    # can only recover this exact candidate, never infer a landing.
                    slot = state.write_slot(common, dict(slot, integration=integration, checks=None,
                                                         ledger_edit_dropped=dropped), slot)
                inputs = {p: execution.digest(root / p) for p in ('TODO.md', 'goals.json')}
                check = execution.bounded_command(argv, root, common, task, timeout, inputs,
                            receipt_context={'integration_commit': merge}, receipt_writer=save_receipt, run_id=run_id,
                            check_slot_wait=True)
                queued += (check or {}).get('command_receipt', {}).get('check_slot_wait_seconds', 0)
                if (check or {}).get('outcome') == 'TIMED_OUT':
                    # The host's speed, not the task (TOOLSET-196-fb): its own cause, reverified
                    # with a longer limit instead of spending an attempt.
                    receipt = check.get('command_receipt') or {}
                    raise Hold('timeout', f"integration validation ran out of time after "
                                          f"{receipt.get('elapsed_seconds') or 0:.0f}s (limit {timeout:g}s)")
                if (not passed(check) or git(root, 'rev-parse', 'HEAD') != merge
                        or git(root, 'status', '--porcelain', '--untracked-files=all')):
                    why = validation_reason(check)
                    # The reviewer ran out of its time: the same host-speed cause as the check's.
                    raise Hold('timeout' if why.startswith(': the review ran out of time') else 'validation',
                               'integration validation failed or changed the integration tree' + why)
                with execution.lock(common / 'writer.lock', wait=LOCK_WAIT):
                    state.require_owner(common, owner_pid)
                    # Re-read report, refs, scopes and source contracts after arbitrary validation.
                    fresh_contracts = {t['id']: t for t in dispatch.contracts(repo)}
                    verify(repo, common, slot, fresh_contracts)
                    verify_scope(repo, common, slot, fresh_contracts, changed(repo, baseline, merge))
                    if display_free(fresh_contracts[task]['contract']) != display_free(contracts[task]['contract']):
                        raise Hold('contract_changed', 'task contract changed during validation')
                    require_no_writers(repo, changed(repo, baseline, merge))
                    if git(repo, 'symbolic-ref', 'HEAD') != canonical_branch:
                        raise ValueError('canonical branch changed during validation')
                    head = git(repo, 'rev-parse', 'HEAD')
                    if head != baseline:
                        # Moved only by planning commits (the runner takes main between and beside
                        # reviews, TOOLSET-233-ba): land the validated merge on top, unvalidated again.
                        remerged = (remerge_planning(repo, root, merge, head)
                                    if ancestor(repo, baseline, head) and planning_only(changed(repo, baseline, head))
                                    else None)
                        if remerged:
                            state.event(common, 'integration_head_moved_planning_only', task_id=task, head=head)
                            merge = integration['remerged'] = remerged
                        else:
                            state.event(common, 'integration_head_moved', task_id=task, attempt=attempt + 1)
                            if attempt == 0:
                                continue
                            raise Hold('moved', 'canonical HEAD moved twice; fresh integration required')
                    # This is the only canonical history-changing command. Git protects dirty files.
                    git(repo, 'merge', '--ff-only', merge)
                    if git(repo, 'rev-parse', 'HEAD') != merge:
                        raise ValueError('canonical fast-forward readback mismatch')
                    state.change(common, slot, 'integrated', {'integration': integration, 'checks': check})
                    return {'outcome': 'INTEGRATED', 'task': task, 'integration': integration,
                            'ledger_edit_dropped': slot.get('ledger_edit_dropped'),
                            'check_slot_wait_seconds': queued}
        except WritersBusy as exc:
            # Not a verdict: an integrating candidate is revalidated on the next call.
            return {'outcome': 'BUSY', 'task': task, 'reason': str(exc)}
        except BlockingIOError:
            # Not a verdict either, and not an abandoned integration: give the slot back so the
            # commit integrates afresh (TOOLSET-194-46). An OSError handler would hold it.
            return release_unfinished(repo, common, owner_pid, task)
        except (ValueError, OSError, subprocess.SubprocessError) as exc:
            with execution.lock(common / 'writer.lock', wait=LOCK_WAIT):
                state.require_owner(common, owner_pid)
                details = {'cause': exc.cause, **exc.details} if isinstance(exc, Hold) else {}
                if reviewer:
                    details['reviewed_by'] = reviewer  # which validation held it, for reverify
                return dict(hold(common, slot, str(exc), **details, **({'checks': check} if check is not None else {})),
                            check_slot_wait_seconds=queued)


def validated_receipt(repo, common, slot):
    info, checks = slot.get('integration') or {}, slot.get('checks') or {}
    receipt_path = Path(info.get('check_receipt', ''))
    if receipt_path.parent != common or receipt_path.suffix != '.json':
        raise ValueError('validation receipt must be in repository execution state')
    saved = execution.read(receipt_path)
    if (saved != checks or not passed(checks)
            or checks.get('context', {}).get('integration_commit') != info.get('commit')
            or checks.get('command_receipt', {}).get('exit_code') != 0
            or checks['command_receipt'].get('task_id') != slot['task_id']
            or checks['command_receipt'].get('receipt') != str(receipt_path)
            or checks['command_receipt'].get('inputs_match') is not True
            or git(repo, 'merge-base', info['commit'], 'HEAD') != info['commit']
            or git(repo, 'rev-list', '--parents', '-n', '1', info['commit']).split()[1:]
               != [info['baseline'], slot['commit']]):
        raise ValueError(STALE_VALIDATION)
    return info, checks


def recover_integration(repo, common, slot, contracts):
    """Called only under integration.lock: no cooperating validation is alive.

    Before FF, require exact baseline and an unmodified isolated candidate and
    rerun validation. After FF, require durable passing evidence for that exact
    landed merge. Missing or contradictory evidence is held, never adopted.
    """
    info = slot.get('integration') or {}
    if (not info.get('commit') or not info.get('baseline')
            or display_free(info.get('task_contract')) != display_free(contracts[slot['task_id']]['contract'])
            or info.get('canonical_branch') != git(repo, 'symbolic-ref', 'HEAD')
            or git(repo, 'rev-list', '--parents', '-n', '1', info['commit']).split()[1:]
               != [info['baseline'], slot['commit']]):
        raise ValueError('abandoned integration lacks exact candidate/contract/branch evidence')
    files = changed(repo, info['baseline'], info['commit'])
    verify_scope(repo, common, slot, contracts, files)
    if files != info.get('changed_files'):
        raise ValueError('abandoned integration delta does not match intent')
    if not landed(repo, info['commit']):
        # Never landed: remerge on the current head and revalidate, retaining the worker attempt.
        # The head may have moved, since the runner lands its session beside a running review.
        # Its integration tree is not needed (a restart left one with a review's files in it):
        # the next integration keeps what is in it as a patch before reusing it.
        return None
    # Older intents have no path. Recover only an unambiguous journaled checkout
    # with the exact candidate, including a retained pre-upgrade sibling tree.
    journal = common / 'journal.jsonl'
    paths = {info['worktree']} if info.get('worktree') else {
        entry['worktree'] for entry in map(json.loads, journal.read_text().splitlines())
        if entry.get('event') == 'worktree_created' and entry.get('branch') == '(detached)'
    } if journal.exists() else set()
    candidates = []
    for raw in paths:
        root = execution.safe_path(raw)
        if (root.is_dir() and dispatch.created_by_autowork(common, root, '(detached)')
                and state.common_dir(root) == common
                and git(root, 'rev-parse', 'HEAD') == info['commit']
                and not git(root, 'status', '--porcelain', '--untracked-files=all')):
            candidates.append(root)
    if len(candidates) != 1:
        raise ValueError('abandoned integration tree changed or ambiguous; preserve for diagnosis')
    validated_receipt(repo, common, slot)
    state.change(common, slot, 'integrated', {})
    return {'outcome': 'INTEGRATED', 'task': slot['task_id'], 'integration': info,
            'ledger_edit_dropped': slot.get('ledger_edit_dropped')}


def goals_command(repo, *argv):
    script = Path(__file__).resolve().parents[2] / 'docs-sync/scripts/goals.py'
    result = subprocess.run([sys.executable, str(script), argv[0], str(repo), *argv[1:]],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('goals.py failed: ' + result.stderr.strip())
    return result.stdout


def live_followup(repo, task, items, indexed):
    """Record a report's pending live checks as their own task, exactly once.

    Offline completion never qualifies live behavior (AGENTS.md): the task closes and
    `TASK-LIVE` waits in Needs decision, depending on it. A retried close finds the
    follow-up already present and adds nothing.
    """
    goals = execution.goals_module()
    followup = task + '-LIVE'
    if indexed:
        ledger = {t['id']: t for t in goals.normalize(goals.load(repo))['tasks']}
        if followup not in ledger:
            goals_command(repo, 'add-task', followup, '--goal', ledger[task]['goal'], '--title',
                          'Live checks for ' + task, '--section', 'Needs decision', '--depends-on', task)
    with goals.coordination(repo):
        todo = repo / 'TODO.md'
        before = todo.read_bytes()
        text = before.decode()
        if followup in goals.task_bodies(text):
            return followup
        body = (f'- [ ] {followup} — Live checks for {task}\n'
                f'  Scope: Run the live checks the offline work for {task} left pending.\n'
                '  Acceptance: Each check passes on the real target:\n'
                + ''.join(f'  - {" ".join(item.split())}\n' for item in items) +
                '  Checks: Live qualification by an authorized person; offline evidence does not count.\n'
                f'  Dependencies: {task}.\n'
                '  Status: open\n')
        heading = re.search(r'^## Needs decision[ \t]*\r?\n', text, re.M)
        if heading:
            end = re.compile(r'^## ', re.M).search(text, heading.end())
            at = end.start() if end else len(text)
            text = text[:at].rstrip('\n') + '\n\n' + body + ('\n' + text[at:] if end else '')
        else:
            coverage = re.search(r'^## Goal coverage', text, re.M)
            at = coverage.start() if coverage else len(text)
            text = (text[:at].rstrip('\n') + '\n\n## Needs decision\n\n' + body
                    + ('\n' + text[at:] if coverage else ''))
        require_no_writers(repo, close_files(repo))
        goals.atomic_write(todo, text, expected_bytes=before)
    if indexed:
        # Record the follow-up's place in the priority order, or the ledger reports drift
        # and stops all dispatch (flutter, TASK-008). Only when it is the sole
        # difference: someone else's unrecorded reordering is not this close's to accept.
        status = goals.priority_status(goals.normalize(goals.load(repo)), (repo / 'TODO.md').read_text())
        if (status['state'] == 'drift' and status['added'] == [followup]
                and not (status['moved'] or status['missing'] or status['duplicates'])):
            goals_command(repo, 'reorder', '--expected-revision', goals_command(repo, 'revision').strip())
    return followup


def archive_path(repo):
    """Reuse Docs Sync's history-owner rules, including legacy and linked archives."""
    return execution.archive_file(repo)


# How a task is shown or ordered, not what it asks: adding `Short:` to every entry sent each held
# task's finished work aside as if its contract had changed.
DISPLAY_FIELDS = ('Short', 'Priority reason')
_DISPLAY_LINE = re.compile(r'(?m)^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?(?:Short|Priority reason[^:\n]*):[^\n]*\n?')


def display_free(contract):
    """The contract without its display-only lines, for comparing two versions of one entry."""
    return _DISPLAY_LINE.sub('', contract or '').strip()


def require_task_contract(items, expected, *, archived=False):
    """Only closure-owned checkbox/status changes may differ from validation."""
    closed = re.sub(r'(?m)^([ \t]*(?:[-*][ \t]+)?Status:)[^\n]*', r'\1 done', expected)
    if archived and len(items) > 1:
        # History can hold an older entry for the same ID (sierra TASK-029): the closed
        # entry matching this contract is the one this close wrote.
        items = [item for item in items if item[1].lower() == 'x'
                 and display_free(item[0]) in (display_free(expected), display_free(closed))]
    if len(items) != 1:
        raise ValueError('task contract provenance missing or ambiguous; no close')
    body, mark, _ = items[0]
    # A live body may already read `Status: done` with its box unchecked: an earlier
    # close that wrote the status but missed a bold `**ID**` checkbox.
    if ((archived and mark.lower() != 'x') or display_free(body) not in
            ({display_free(expected), display_free(closed)} if mark.lower() == 'x' or not archived
             else {display_free(expected)})):
        raise ValueError(CONTRACT_CHANGED)


def close(repo, owner_pid, task):
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'dispatch.lock'), execution.lock(common / 'integration.lock'), \
            execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        # Only the files a close writes: a person's session in the main checkout that is not
        # editing them does not keep finished work open (interactive sessions work there).
        require_no_writers(repo, close_files(repo))
        slot = slot_for(common, task)
        if not slot or slot['state'] not in ('integrated', 'closed'):
            raise ValueError('close requires an integrated slot with passing validation')
        info, checks = validated_receipt(repo, common, slot)
        if slot['state'] == 'closed':
            archive = archive_path(repo)
            archived = execution.goals_module().task_bodies(archive.read_text()) if archive.exists() else {}
            require_task_contract(archived.get(task, []), info.get('task_contract', ''), archived=True)
            dispatch.cleanup_tmpdir(common, slot)
            return {'outcome': 'CLOSED', 'task': task, 'cleaned': cleanup_worker(repo, common, slot)}
        # The helper has no TODO-only `task` CLI. Use its same coordination and
        # atomic writer in this narrow adapter instead of creating a goals ledger.
        goals = execution.goals_module()
        current = goals.task_bodies((repo / 'TODO.md').read_text()).get(task, [])
        expected_contract = info.get('task_contract', '')
        if current:
            require_task_contract(current, expected_contract)
        else:
            archive = archive_path(repo)
            archived = goals.task_bodies(archive.read_text()) if archive.exists() else {}
            require_task_contract(archived.get(task, []), expected_contract, archived=True)
        indexed = (repo / 'goals.json').exists()
        # All or nothing: a close that fails after writing would leave these uncommitted in
        # the session, where every later merge refuses them (bravo, TASK-010).
        touched = [repo / 'TODO.md', repo / 'goals.json', archive_path(repo)]
        before = {path: path.read_bytes() if path.exists() else None for path in touched}
        try:
            archive, followup = _close_writes(repo, slot, task, indexed, goals)
        except BaseException:
            for path, data in before.items():
                if data is None:
                    path.unlink(missing_ok=True)
                elif not path.exists() or path.read_bytes() != data:
                    path.write_bytes(data)
            raise
        slot = state.change(common, slot, 'closed', {})
        dispatch.cleanup_tmpdir(common, slot)
        files = ['TODO.md', *(['goals.json'] if indexed else []), archive.relative_to(repo).as_posix()]
        return {'outcome': 'CLOSED', 'task': task, 'cleaned': cleanup_worker(repo, common, slot),
                'files': files, **({'live_followup': followup} if followup else {})}


def _close_writes(repo, slot, task, indexed, goals):
    """The close's writes to TODO.md, goals.json and the archive; (archive, live follow-up)."""
    if indexed:
        require_no_writers(repo, close_files(repo))
        goals_command(repo, 'task', task, 'done')
    # `goals.py task` updates the index, not the authored checkbox/body.
    # Update that exact body under the helper's own stale-write guard too.
    with goals.coordination(repo):
        todo = repo / 'TODO.md'
        before = todo.read_bytes()
        text = before.decode()
        blocks = [b for b in goals.task_blocks(text) if b['id'] == task]
        if len(blocks) > 1:
            raise ValueError('TODO task duplicated; no close')
        if blocks:
            block = blocks[0]
            body = text[block['start']:block['end']]
            # IDs may be bold or code: `- [ ] **T-1 — Title**` (sierra).
            body = re.sub(r'(?m)^([ \t]*[-*] \[)[ xX](\][ \t]+(?:\*\*)?`?' + re.escape(task) + r'\b)', r'\g<1>x\2', body)
            body = re.sub(r'(?m)^([ \t]*(?:[-*][ \t]+)?Status:)[^\n]*', r'\1 done', body)
            require_no_writers(repo, close_files(repo))
            goals.atomic_write(todo, text[:block['start']] + body + text[block['end']:], expected_bytes=before)
    live = live_items((slot.get('report') or {}).get('pending_live'))
    followup = live_followup(repo, task, live, indexed) if live else None
    require_no_writers(repo, close_files(repo))
    archived_result = json.loads(goals_command(repo, 'archive', *([] if indexed else ['--verified-tasks', task])))
    # Read back exact target before journaling closure; archive can fail safely
    # after task mutation, in which case slot stays integrated and is retryable.
    # The archive command can return null on an idempotent retry.
    archive = repo / archived_result['archive'] if archived_result.get('archive') else archive_path(repo)
    archived = goals.task_bodies(archive.read_text()) if archive.exists() else {}
    # The contract was checked before any write. The archiver cuts a body at the next
    # group heading, which the contract parser keeps, so compare presence, not bytes.
    if task not in archived or task in goals.task_bodies((repo / 'TODO.md').read_text()):
        raise ValueError('archive did not move the task; no close')
    return archive, followup


CONTRACT_CHANGED = 'task contract changed since integration; no close'


def dispatched_contract(common, slot):
    """The TODO contract this slot's current attempt was given: its contract.txt, or for
    attempts dispatched before that record, the contract section of its prompt."""
    data = dispatch.data_dir(common, slot)
    try:
        return (data / 'contract.txt').read_text().strip()
    except OSError:
        pass
    try:
        text = (data / 'prompt.md').read_text()
    except (OSError, ValueError):
        return None
    marker = '\nTask contract from TODO.md:\n\n'
    if marker not in text:
        return None
    return text.split(marker, 1)[1].split('\nFresh retry after a held integration.', 1)[0].strip()


def entry_changes(repo, common, slot):
    """Changed field names since dispatch or the last rescope; None without evidence.

    Keep raw field bodies (including continuations, duplicate fields and free text)
    rather than comparing only the planner's recognized, nonempty field values.
    """
    previous = slot.get('rescoped_contract') or dispatched_contract(common, slot)
    if previous is None:
        return None  # no record to compare with: never guess
    goals = execution.goals_module()
    items = goals.task_bodies((repo / 'TODO.md').read_text()).get(slot['task_id'], [])
    if len(items) != 1:
        return ['Entry']  # removed or duplicated: never a Touches-only answer

    def fields(text):
        # Use prose offsets so field-looking text inside a fenced example is not a field.
        marks = list(re.finditer(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][^:\r\n]*?):(?:\*\*)?[ \t]*',
                                 goals.task_prose(text), re.M))
        result = {'Entry': [text[:marks[0].start()].rstrip() if marks else text]}
        for index, mark in enumerate(marks):
            end = marks[index + 1].start() if index + 1 < len(marks) else len(text)
            result.setdefault(mark[1], []).append(text[mark.start():end].rstrip())
        return result

    before, after = fields(previous.strip()), fields(items[0][0].strip())
    return sorted(key for key in before.keys() | after.keys()
                  if not key.startswith(DISPLAY_FIELDS) and before.get(key) != after.get(key))





def blocker_resolved(repo, common, slot, hold):
    """An explicit answer names this blocker and its producer/evidence, not a cosmetic edit.

    The runner cannot judge prose semantically. Require a fresh, blocker-specific
    resolution field; the maintainer/owner supplies the evidence, normal checks judge it.
    """
    if 'Blocker resolution' not in (entry_changes(repo, common, slot) or []):
        return False
    goals = execution.goals_module()
    items = goals.task_bodies((repo / 'TODO.md').read_text()).get(slot['task_id'], [])
    if len(items) != 1:
        return False
    value = ' '.join(goals.task_fields(items[0][0]).get('Blocker resolution', '').split())
    previous = slot.get('rescoped_contract') or dispatched_contract(common, slot)
    before = ' '.join(goals.task_fields(previous or '').get('Blocker resolution', '').split())
    prefix = hold['fingerprint'] + ';'
    return (value.casefold() != before.casefold() and value.startswith(prefix)
            and bool(value[len(prefix):].strip()))


def entry_changed(repo, common, slot):
    """A changed entry, or for a repeated quick hold, an answer to its named blocker."""
    hold = state.quick_hold(common, slot)
    return bool(entry_changes(repo, common, slot)) and (not hold or blocker_resolved(repo, common, slot, hold))


def _retire(repo, common, slot, requeued):
    """Keep every attempt's work under -set-aside-N names and move the slot to history.

    Caller holds dispatch.lock, integration.lock and writer.lock."""
    task = slot['task_id']
    hold = state.quick_hold(common, slot)
    if requeued and hold and not blocker_resolved(repo, common, slot, hold):
        raise ValueError(f'repeated quick hold: add Blocker resolution: {hold["fingerprint"]}; '
                         'producer task or decision evidence to the entry before rerunning')
    dispatch.cleanup_tmpdir(common, slot)
    history = execution.safe_path(common / 'slot-history' / task)
    number = 1 + sum(1 for _ in history.glob('*')) if history.exists() else 1
    pairs = []
    for attempt in [*slot.get('previous_attempts', []), slot]:
        pair = (attempt.get('worktree'), attempt.get('branch'))
        if pair[1] and pair not in pairs:
            pairs.append(pair)
    while True:
        number = dispatch.set_aside_number(repo, pairs, number)
        target = history / str(number)
        if not target.exists():
            break
        number += 1
    moved = []
    try:
        for worktree, branch in pairs:
            suffix = f'-set-aside-{number}'
            record = {'worktree': worktree, 'branch': branch}
            if worktree and Path(worktree).is_dir():
                record['worktree_now'] = worktree + suffix
                git(repo, 'worktree', 'move', worktree, record['worktree_now'])
            if git(repo, 'branch', '--list', branch):
                record['branch_now'] = branch + suffix
                git(repo, 'branch', '-m', branch, record['branch_now'])
            moved.append(record)
    except ValueError:
        for record in reversed(moved):  # Leave names as they were; nothing else changed yet.
            if 'branch_now' in record:
                git(repo, 'branch', '-m', record['branch_now'], record['branch'])
            if 'worktree_now' in record:
                git(repo, 'worktree', 'move', record['worktree_now'], record['worktree'])
        raise
    # A clean set-aside worktree holds nothing its branch does not (its build output aside, many
    # GB of it): remove it, keep the branch (TOOLSET-210-53). Uncommitted work keeps its worktree.
    for record in moved:
        path = record.get('worktree_now')
        if path and record.get('branch_now') and Path(path).is_dir():
            try:
                clean = not git(path, 'status', '--porcelain', '--untracked-files=all')
            except ValueError:
                clean = False
            if clean:
                try:
                    git(repo, 'worktree', 'remove', '--force', path)
                    record['worktree_removed'] = True
                except ValueError:
                    pass
    target.mkdir(parents=True, mode=0o700)
    data = common / 'slot-data' / task
    if data.exists():
        data.rename(target / 'slot-data')
    execution.save(target / 'slot.json', dict(slot, set_aside={'renamed': moved}))
    state.slot_path(common, task).unlink()
    state.event(common, 'slot_set_aside', task_id=task, state=slot['state'], renamed=moved,
                history=str(target))
    return {'outcome': 'SET_ASIDE', 'task': task, 'previous_state': slot['state'],
            'renamed': moved, 'history': str(target), 'requeued': requeued}


def set_aside(repo, owner_pid, task):
    """Retire a slot that can never finish, so its task can dispatch fresh.

    Only for a finished commit waiting to merge (on request), a held slot no attempt can finish, or an integrated one whose TODO
    entry was rewritten after validation (its merge stays in main; the new entry
    is new work) or was archived or removed by someone else (``requeued`` false). Every attempt's worktree and branch is kept, renamed with a
    ``-set-aside-N`` suffix, and the slot record and its data move to
    ``slot-history/TASK/N``; the next refill treats the task as never dispatched.
    """
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'dispatch.lock'), execution.lock(common / 'integration.lock'), \
            execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        slot = slot_for(common, task)
        if slot is None or state.worker_live(slot):
            raise ValueError('set-aside needs an existing slot with no live worker')
        requeued = True
        if slot['state'] == 'integrated':
            current = execution.goals_module().task_bodies((repo / 'TODO.md').read_text()).get(task, [])
            if not current:
                # Someone else archived or removed the entry after the merge (bravo
                # TASK-001): the merge stays and nothing is queued again.
                requeued = False
            else:
                try:
                    require_task_contract(current, (slot.get('integration') or {}).get('task_contract', ''))
                except ValueError as exc:
                    if str(exc) != CONTRACT_CHANGED:
                        raise
                else:
                    raise ValueError('integrated task still matches its contract; close it instead')
        elif slot['state'] != 'reported' and not state.exhausted(slot):
            # A finished commit too, on a person's request: stale ones written against code main had
            # since redesigned only conflicted, and the request was refused.
            raise ValueError('set-aside is only for a finished commit, a held slot with no attempt left, or an '
                             'integrated task whose TODO entry changed')
        return _retire(repo, common, slot, requeued)


def clear_held(repo, owner_pid, task=None):
    """Return held commit(s) to integration on an explicit request: technical recovery, not a
    person's decision. Each commit and its worktrees are kept and every check repeats; the
    prior re-offer marks are forgotten so a hold can be retried again. ``task`` is one ID, a
    comma/space-separated list, or empty for every held commit."""
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'dispatch.lock'), execution.lock(common / 'integration.lock'), \
            execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        wanted = {t for t in re.split(r'[,\s]+', task or '') if t and t.lower() != 'all'}
        held = [s for s in state.slots(common) if s['state'] == 'held' and s.get('commit')
                and not state.worker_live(s) and (not wanted or s['task_id'] in wanted)]
        if not held:
            raise ValueError('no held commit to clear' + (f' for {", ".join(sorted(wanted))}' if wanted else ''))
        cleared = []
        for slot in held:
            value = {k: v for k, v in slot.items() if k not in ('reason', 'cause', 'reoffered')}
            value['state'] = 'reported'
            state.write_slot(common, value, slot)
            cleared.append(slot['task_id'])
        return {'outcome': 'CLEARED', 'tasks': cleared}


VALIDATION_HOLD = 'integration validation failed'


def validation_verdict(slot):
    """A failure line belongs to the worker commit, not the changing integration revision."""
    # The display reason is shortened; compare the full line from its receipt when available.
    reason = validation_reason(slot.get('checks'), limit=None) or str(slot.get('reason') or '')
    line = re.sub(r'\b[0-9a-fA-F]{7,40}\b', '<revision>', reason)
    return {'commit': slot.get('commit'), 'line': ' '.join(line.split())}


def reverifiable(slot, version):
    """A changed validator gets one more look, unless it repeated the same commit's verdict.
    Timeouts are not verdicts: the coordinator may still retry them with a longer limit."""
    return (slot['state'] == 'held' and bool(slot.get('commit')) and not state.worker_live(slot)
            and (slot.get('cause') in ('validation', 'reviewed_twice', 'timeout')
                 or (not slot.get('cause') and str(slot.get('reason', '')).startswith(VALIDATION_HOLD)))
            and slot.get('reverified') != version and slot.get('reviewed_by') != version
            and (slot.get('cause') == 'timeout' or slot.get('reverify_verdict') != validation_verdict(slot)))


def reverify(repo, owner_pid, task, version):
    """Send a validation-held commit back to integration once per validator ``version``.

    The coordinator passes a fingerprint of its validation (say its reviewer); when it
    changes, a commit the old one held is checked again by the new one, once. Every
    integration check repeats; the attempt is unchanged, so nothing new is dispatched.
    """
    if not isinstance(version, str) or not re.fullmatch(r'[A-Za-z0-9._:-]{1,80}', version):
        raise ValueError('--reviewer-version must be a short identifier')
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'integration.lock'), execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        slot = slot_for(common, task)
        if (slot and slot['state'] == 'held' and slot.get('cause') == 'timeout'
                and not slot.get('commit') and dispatch.check_failure_resumed(slot)
                and not state.worker_live(slot) and slot.get('reverified') != version):
            # No commit exists yet: resume its finished dirty work, never a fresh -r2 worker.
            state.workspace(common, slot['worktree'], slot['branch'], slot['baseline'])
            value = {k: v for k, v in slot.items() if k not in ('reason', 'cause')}
            value.update(state='interrupted', paused=True, reverified=version)
            state.write_slot(common, value, slot)
            return {'outcome': 'REVERIFY', 'task': task, 'version': version, 'resume_worker': True}
        if slot is None or not reverifiable(slot, version):
            raise ValueError('reverify is only for a commit held by validation, once per validator version; '
                             'the same verdict on the same commit stays held')
        value = {k: v for k, v in slot.items() if k not in ('reason', 'cause', 'checks', 'integration')}
        value.update(state='reported', reverified=version, reverify_verdict=validation_verdict(slot))
        slot = state.write_slot(common, value, slot)
        return {'outcome': 'REVERIFY', 'task': task, 'commit': slot['commit'], 'version': version}


ANSWERS = 2  # answered blockers per task; after that the hold is the owner's question


def answer(repo, owner_pid, task, text):
    """Answer a worker-reported blocker and resume its attempt in its own worktree, with the answer
    in its prompt: most blockers asked the runner for what it already provides, or for a repair the
    worker may make itself, and waited hours for a person (TOOLSET-252-4c's evidence, 2026-10-19)."""
    text = text.strip()
    if not text:
        raise ValueError('an answer needs text')
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        slot = slot_for(common, task)
        if (slot is None or slot['state'] != 'held' or slot.get('cause') != 'blocker' or state.worker_live(slot)
                or answered(slot) >= ANSWERS or state.quick_hold(common, slot)):
            raise ValueError(f'answer is only for a blocker-held task, at most {ANSWERS} times')
        with open(answers_path(common, task), 'a') as record:
            record.write(f'- {datetime.now():%Y-%m-%d %H:%M} to: {slot.get("reason") or "a blocker"}\n  {text}\n')
        value = {k: v for k, v in slot.items() if k not in ('reason', 'cause')}
        value.update(state='interrupted', paused=True, answered=answered(slot) + 1)
        slot = state.write_slot(common, value, slot)
        state.event(common, 'blocker_answered', task_id=task, answered=slot['answered'])
    return {'outcome': 'ANSWERED', 'task': task, 'answered': slot['answered']}


def answered(slot):
    """How often the runner has answered this task's blockers; a resume keeps the count in its history."""
    return max(int(s.get('answered') or 0) for s in [slot, *slot.get('previous_attempts', [])])


def answers_path(common, task):
    return execution.safe_path(common / 'slot-data' / task / 'answers.md')


def merged(repo, owner_pid, task):
    """Adopt a conflict-held commit whose worktree has merged canonical HEAD, up to three
    times per attempt, each after canonical advances past the last adopted revision.
    The merge is judged from that HEAD, so only the task's changes and resolution count."""
    repo, common = context(repo, owner_pid)
    with execution.lock(common / 'integration.lock'), execution.lock(common / 'writer.lock'):
        state.require_owner(common, owner_pid)
        slot = slot_for(common, task)
        if slot is None:
            raise ValueError('merged is only for an idle conflict-held commit')
        adoption = state.merge_adoption(repo, slot)
        if not adoption['allowed']:
            raise ValueError(adoption['reason'])
        root = execution.safe_path(slot['worktree'])
        base = adoption['baseline']
        head = git(root, 'rev-parse', 'HEAD')
        if (git(root, 'symbolic-ref', '--short', '-q', 'HEAD') != slot['branch']
                or git(root, 'status', '--porcelain', '--untracked-files=no')
                or not ancestor(repo, slot['commit'], head) or not ancestor(repo, base, head)):
            raise ValueError('the task worktree must be clean on its branch with both its commit and canonical HEAD merged')
        data = dispatch.data_dir(common, slot)
        report = execution.read(data / 'report.json')
        if not isinstance(report, dict) or report.get('task') != task:
            raise ValueError('merged needs the held commit\'s report.json')
        report.update(commit=head, changed_files=changed(repo, base, head))
        execution.save(data / 'report.json', report)
        value = {k: v for k, v in slot.items() if k not in ('reason', 'cause', 'checks', 'integration', 'conflict_files')}
        value.update(state='reported', baseline=base, commit=head, merged_base=base,
                     merged_count=adoption['merged_count'] + 1)
        slot = state.write_slot(common, value, slot)
        return {'outcome': 'MERGED', 'task': task, 'commit': head, 'baseline': base,
                'merged_count': slot['merged_count']}


def cleanup_worker(repo, common, slot):
    """Independent idempotent cleanup; never repeat the archive/closed transition."""
    root = execution.safe_path(slot['worktree'])
    if not dispatch.created_by_autowork(common, root, slot['branch']) or state.worker_live(slot):
        return False
    path = common / ('cleanup-' + slot['task_id'] + '-' + str(slot['attempt']) + '.json')
    intent = {k: slot[k] for k in ('task_id', 'attempt', 'worktree', 'branch', 'baseline', 'commit')}
    previous = execution.read(path)
    if path.exists() and previous != intent:
        raise ValueError('cleanup provenance does not match closed worker')
    if root.exists():
        state.workspace(common, root, slot['branch'], slot['baseline'])
        if (git(root, 'status', '--porcelain', '--untracked-files=all')
                or git(root, 'rev-parse', 'HEAD') != slot['commit']):
            return False
        require_no_writers(root, [])  # a session only in the main checkout never touches this worktree
        execution.save(path, intent)  # Durable before either destructive operation.
        git(repo, 'worktree', 'remove', str(root))
    elif previous != intent:
        return False  # An absent directory alone is not evidence of our removal.
    registrations = git(repo, 'worktree', 'list', '--porcelain').split('\n\n')
    if root.exists() or any('worktree ' + str(root) in block.splitlines() for block in registrations):
        raise ValueError('worker removal readback mismatch')
    if git(repo, 'branch', '--list', slot['branch']):
        if (git(repo, 'rev-parse', 'refs/heads/' + slot['branch']) != slot['commit']
                or any('branch refs/heads/' + slot['branch'] in block.splitlines() for block in registrations)):
            return False
        git(repo, 'branch', '-d', slot['branch'])
    if git(repo, 'branch', '--list', slot['branch']):
        raise ValueError('worker branch cleanup readback mismatch')
    return True


def rework_path(common, task):
    """The record of the one rework a task's review failure earned (TOOLSET-285-29)."""
    return execution.safe_path(common / 'review-rework' / (re.sub(r'[^A-Za-z0-9._-]+', '-', task) + '.json'))


def reviewer_finding(slot):
    """The reviewer's finding a held slot failed on, or '': not an environment miss or a timeout."""
    reason = str(slot.get('reason') or '')
    found = re.search(r'PI_AUTOWORK_VERIFY: fail(?! environment)\b\s*(.*)', reason, re.S)
    return ' '.join((found[1] if found else '').lstrip('—- ').split()) if slot.get('cause') == 'validation' else ''


def review_rework(repo, common, current):
    """A last attempt that failed its review was neither retried nor asked about: fresh retries are
    for first attempts, and review failures are not questions. It now gets one rework attempt with
    the finding and its kept commit; a rework that fails review too becomes a person's question
    quoting both findings. Caller holds the dispatch, integration and writer locks."""
    for slot in current:
        finding = reviewer_finding(slot)
        if slot['state'] != 'held' or not finding or state.worker_live(slot):
            continue
        marker = rework_path(common, slot['task_id'])
        earlier = execution.read(marker) if marker.exists() else None
        if isinstance(earlier, dict):
            reason = (f'{slot.get("reason")}; this was its one rework after review, and the earlier '
                      f'review found: {earlier.get("finding", "")}')
            state.write_slot(common, dict(slot, cause='reviewed_twice', reason=reason), slot)
            state.event(common, 'review_rework_failed', task_id=slot['task_id'])
        elif slot['attempt'] >= 2:
            execution.save(marker, {'finding': finding, 'tip': slot.get('commit') or '', 'at': time.time()})
            state.event(common, 'review_rework', task_id=slot['task_id'], tip=slot.get('commit') or '')
            return dict(_retire(repo, common, slot, True), outcome='REQUEUED', why='review_rework')
    return None


def retry_held(args):
    """Refill adapter for held slots; first attempts and their artifacts survive."""
    repo, common = context(args.consumer, args.owner_pid)
    with execution.lock(common / 'dispatch.lock'), execution.lock(common / 'integration.lock'):
        state.require_owner(common, args.owner_pid)
        # transition() acquires writer.lock itself; never nest it under that lock.
        dispatch.enforce_timeouts(repo, args.owner_pid, common, args.worker_timeout)
        with execution.lock(common / 'writer.lock'):
            state.require_owner(common, args.owner_pid)
            current = state.slots(common)
            # No rescope, reoffer or fresh retry may bypass a repeated missing input.
            current = [s for s in current if not (hold := state.quick_hold(common, s))
                       or blocker_resolved(repo, common, s, hold)]
            # A retry that produced nothing (often because it judged the first hold
            # binding) gets the first attempt's commit re-verified once instead.
            # Earlier releases held a commit when a live session was in the canonical checkout
            # (flutter, 2026-10-16): that was no verdict, so offer such a commit again.
            # Earlier releases also held a paused-and-resumed -r2 retry as 'unexpected worker branch'
            # (sierra TASK-026); one whose branch is now the expected one is offered again too.
            busy = next((s for s in current if s['state'] == 'held' and s.get('commit') and not state.worker_live(s)
                         and (str(s.get('reason', '')).startswith(WRITER_HOLD)
                              or (s.get('reason') == BRANCH_HOLD and s['branch'] == expected_branch(s)))), None)
            if busy is not None:
                value = {k: v for k, v in busy.items() if k not in ('reason', 'cause', 'checks', 'integration')}
                value['state'] = 'reported'
                slot = state.write_slot(common, value, busy)
                return {'outcome': 'REOFFERED', 'task': slot['task_id'], 'commit': slot['commit']}
            # A new Touches-only answer keeps the candidate even after an automatic rescope.
            # Other contract edits must reach the fresh-run path below, never this shortcut.
            scoped = [s for s in current if s['state'] == 'held' and s.get('cause') == 'scope']
            if scoped:
                contracts = {t['id']: t for t in dispatch.contracts(repo, args.tasks, args.plan)}
                for candidate in scoped:
                    task = contracts.get(candidate['task_id'])
                    if task is None:
                        continue
                    changes = entry_changes(repo, common, candidate)
                    touches_only = bool(changes) and all(
                        name == 'Touches' or name.startswith('Touches widened ') for name in changes)
                    if changes and not touches_only:
                        continue
                    # Repair an older runner's re-hold against the dispatch contract, once.
                    # The saved answer must now admit the actual commit; never loop on a refusal.
                    if (not changes and candidate.get('rescoped') and candidate.get('rescoped_contract')
                            and 'scope' not in state.reoffered(candidate) and not state.worker_live(candidate)):
                        try:
                            verify_scope(repo, common, candidate, contracts,
                                         changed(repo, candidate['baseline'], candidate['commit']))
                        except Hold:
                            continue
                        slot = state.reoffer(common, candidate)
                        return {'outcome': 'REOFFERED', 'task': slot['task_id'], 'commit': slot['commit']}
                    touches = task['fields'].get('Touches', '')
                    if not state.rescopable(candidate, touches, touches_only=touches_only):
                        continue
                    slot = state.rescope(common, candidate, touches, contract=task['contract'])
                    if changes:
                        state.event(common, 'task_entry_changed', task_id=slot['task_id'],
                                    changed_fields=changes, action='rescope')
                    return {'outcome': 'RESCOPED', 'task': slot['task_id'], 'commit': slot['commit'],
                            'touches': slot['touches']}
            # A commit held only because another slot owned some of its files is offered
            # again, once, when no unsettled slot owns them any more (TOOLSET-157-cd): the
            # slot it waited for has integrated or was released. A fresh retry would only
            # reimplement the same change.
            # TOOLSET-161-17: a commit held only for Touches (overlap with another slot, or files
            # outside its Touches that are not protected) integrates by merge now. Ledger-only
            # scope holds also return unchanged: their proposals are dropped, not reimplemented.
            touches_held = [s for s in current if s['state'] == 'held' and s.get('commit') and not state.worker_live(s)
                            and s.get('cause') not in state.reoffered(s)
                            and (s.get('cause') == 'overlap'
                                 or (s.get('cause') == 'scope' and s.get('outside') and not any(
                                     plan.protected_path(p) for p in s.get('outside')))
                                 or (s.get('cause') == 'scope' and 'changed files violate Touches'
                                     in str(s.get('reason') or '') and not s.get('outside')))]
            if touches_held:
                order = [t['id'] for t in dispatch.contracts(repo)]
                touches_held.sort(key=lambda s: order.index(s['task_id']) if s['task_id'] in order else len(order))
                slot = state.reoffer(common, touches_held[0])
                return {'outcome': 'REOFFERED', 'task': slot['task_id'], 'commit': slot['commit']}
            # A commit an earlier release held by misreading its evidence is offered again once:
            # a report naming its commit by an abbreviated SHA, or a validation that passed but
            # left build daemons behind. Integration repeats every check.
            misread = next((s for s in current if s['state'] == 'held' and s.get('commit')
                            and s.get('cause') not in state.reoffered(s) and not state.worker_live(s)
                            and ((s.get('cause') == 'report' and report_matches(repo, common, s))
                                 or (s.get('cause') == 'validation' and (s.get('checks') or {}).get('outcome')
                                     == 'CHILDREN_TERMINATED' and passed(s.get('checks'))))), None)
            if misread is not None:
                slot = state.reoffer(common, misread)
                return {'outcome': 'REOFFERED', 'task': slot['task_id'], 'commit': slot['commit']}
            # Earlier releases held an interrupted review whose merge never landed when main had
            # moved meanwhile, as if it had landed without evidence: offered again once.
            unlanded = next((s for s in current if s['state'] == 'held' and s.get('commit')
                             and s.get('reason') == STALE_VALIDATION and not state.worker_live(s)
                             and 'stale_validation' not in state.reoffered(s)
                             and landed(repo, (s.get('integration') or {}).get('commit')) is False), None)
            if unlanded is not None:
                slot = state.reoffer(common, dict(unlanded, cause='stale_validation'))
                return {'outcome': 'REOFFERED', 'task': slot['task_id'], 'commit': slot['commit']}
            # A worker that asked for files outside Touches resumes in its own worktree, on
            # the same attempt, once its current Touches cover what it asked for.
            # A worker that stopped to ask for files outside Touches (an earlier release told it
            # to) resumes in its own worktree on the same attempt: it may change them now.
            requests = [s for s in current if s['state'] == 'held' and s.get('cause') == 'scope_request'
                        and not state.worker_live(s)]
            if requests:
                slot = state.resume_widened(common, requests[0])
                return {'outcome': 'RESUMED', 'task': slot['task_id'], 'touches': ''}
            again = [s for s in current if state.readoptable(s)]
            eligible = {t['id'] for t in dispatch.contracts(repo, args.tasks, args.plan)} if again else set()
            again = next((s for s in again if s['task_id'] in eligible), None)
            if again is not None:
                slot = state.readopt(common, again)
                return {'outcome': 'READOPTED', 'task': slot['task_id'], 'commit': slot['commit']}
            # An answered question (after the one-time readopt above, which keeps a commit): a
            # held task whose TODO entry changed since its attempt was dispatched runs fresh,
            # its earlier work kept on -set-aside-N names; an entry that disappeared was
            # closed or removed by a person, so nothing is queued again.
            # A branch the runner itself merged past its recorded commit, beyond the adoptions
            # allowed: a fresh attempt, its kept tip named in the prompt (TOOLSET-280-4f).
            merged_past = next((s for s in current if s['state'] == 'held' and s.get('cause') == 'runner_merged'
                                and not state.worker_live(s)), None)
            if merged_past is not None:
                state.event(common, 'runner_merged_requeued', task_id=merged_past['task_id'],
                            tip=merged_past.get('tip', ''))
                return dict(_retire(repo, common, merged_past, True), outcome='REQUEUED', why='runner_merged')
            changed_slot = next((s for s in current if s['state'] == 'held' and not state.worker_live(s)
                                 and entry_changed(repo, common, s)), None)
            if changed_slot is not None:
                rework_path(common, changed_slot['task_id']).unlink(missing_ok=True)  # a person's answer resets it
                present = bool(execution.goals_module().task_bodies((repo / 'TODO.md').read_text()).get(changed_slot['task_id']))
                state.event(common, 'task_entry_changed', task_id=changed_slot['task_id'],
                            changed_fields=entry_changes(repo, common, changed_slot), action='requeue')
                result = _retire(repo, common, changed_slot, present)
                return dict(result, outcome='REQUEUED')
            reworked = review_rework(repo, common, current)
            if reworked:
                return reworked
            # A second review failure became a person's question: read its new cause.
            fresh = {x['task_id']: x for x in state.slots(common)}
            current = [fresh.get(x['task_id'], x) for x in current]
            # A hold the worker reported a blocker for gets no fresh attempt: it needs a person.
            live = [s for s in current if state.worker_live(s)]
            capacity = dispatch.capacity(args)
            if len(live) >= capacity:
                return {'outcome': 'IDLE'}  # ordinary dispatch reports the occupied pool
            # A conflict with the session is not fixable by a fresh worker (it conflicts again):
            # the resolver merges the session into the commit, or the owner decides. Keeping it
            # out of this set lets the coordinator hold it briefly to group siblings for one check.
            held = {s['task_id']: s for s in current if s['state'] == 'held' and s['attempt'] == 1
                    and not state.exhausted(s) and not state.worker_live(s)
                    and s.get('cause') != 'conflict'}
            if not held:
                return {'outcome': 'IDLE'}
            # Attempt number is not a mutex: use ordinary parallel admission.
            planned = dispatch.retry_plan(repo, current, args.tasks, args.plan)
            # The plan covers every first-attempt hold; a conflict hold it may name first is not
            # retried here (its KeyError stopped the engine every cycle).
            task = next((t for t in planned['dispatch'] if t['id'] in held), None)
            if task is None:
                return {'outcome': 'IDLE'}  # unrelated fresh work may still fill spare slots
            template, host = dispatch.worker_command(args, args.owner_pid)
            if template is None:
                return {'outcome': 'SEQUENTIAL_FALLBACK', 'reason': host}
            gate = dispatch.resource_gate(len(live), args.min_free_mem_mb, repo)
            if gate:
                return {'outcome': 'WAITING', 'reason': gate}
            old = held[task['id']]
            baseline = git(repo, 'rev-parse', 'HEAD')
            branch = 'autowork/' + task['id'] + '-r2'
            root = worktree_path(repo, 'autowork-' + task['id'] + '-r2')
            if root.exists() or git(repo, 'branch', '--list', branch):
                raise ValueError('fresh retry branch/worktree already exists; preserve and reconcile by hand')
            git(repo, 'worktree', 'add', '-b', branch, str(root), baseline)
            state.event(common, 'worktree_created', task_id=task['id'], worktree=str(root), branch=branch, baseline=baseline)
            slot = state.change(common, old, 'dispatched', {'worktree': str(root), 'branch': branch, 'baseline': baseline})
            data = dispatch.data_dir(common, slot)
            data.mkdir(parents=True, exist_ok=True, mode=0o700)
            prompt = data / 'prompt.md'
            report = data / 'report.json'
            (data / 'contract.txt').write_text(task['contract'].strip() + '\n')
            prompt.write_text(dispatch.prompt(task, root, branch, baseline, report) +
                              '\nFresh retry after a held integration. Inspect prior failure: ' + old.get('reason', '') + '\n')
            argv = dispatch.render(template, {'worktree': root, 'prompt_file': prompt, 'timeout': int(args.worker_timeout),
                                            'report_file': report, 'git_common_dir': common.parent})
            used = {dispatch.meta(common, s).get('slot_index') for s in live}
            index = next(i for i in range(1, dispatch.HARD_LIMIT + 1) if i not in used)
            execution.save(data / 'meta.json', {'slot_index': index, 'command': argv, 'host': host,
                           'prompt_file': str(prompt), 'report_file': str(report), 'worker_timeout': args.worker_timeout})
            try:
                worker = dispatch.launch(argv, root, data, index, prompt)
                slot = state.change(common, slot, 'running', {'worker': worker, 'log_path': str(data / 'worker.log')})
            except (ValueError, OSError) as exc:
                return hold(common, slot, 'fresh retry launch failed: ' + str(exc), cause='launch')
            return {'outcome': 'RETRIED', 'task': task['id'], 'slot': slot}


# Held too: a held slot whose task was closed on main kept its place and was even retried fresh.
RETIRABLE = ('dispatched', 'running', 'interrupted', 'released', 'reported', 'held')


def retire_closed(args):
    """Stop and set aside the work of tasks closed meanwhile, here or on the base branch
    (TOOLSET-218-d0): a live worker is stopped, and its slot keeps every commit under a
    -set-aside-N name. With a review holding the integration lock, setting aside waits for a
    later cycle; the stopped slot occupies nothing and never restarts meanwhile."""
    repo = Path(args.consumer).resolve()
    common = state.common_dir(repo)
    base = getattr(args, 'base_ref', None)
    with execution.lock(common / 'dispatch.lock'):
        slots = [s for s in state.slots(common) if s['state'] in RETIRABLE]
        if not slots:
            return [], []
        closed = dispatch.retired(repo, base)
        doomed = [s for s in slots if s['task_id'] in closed]
        for slot in doomed:
            if state.worker_live(slot):
                dispatch.stop(slot.get('worker'), slot.get('worktree'))
        if not doomed:
            return [], []
        try:
            with execution.lock(common / 'integration.lock'), execution.lock(common / 'writer.lock'):
                state.require_owner(common, args.owner_pid)
                done = []
                for slot in doomed:
                    slot = slot_for(common, slot['task_id'])
                    if slot is None or slot['state'] not in RETIRABLE or state.worker_live(slot):
                        continue
                    _retire(repo, common, dict(slot, cause='closed_on_base'), False)
                    state.event(common, 'closed_on_base', task_id=slot['task_id'], base=base or '')
                    done.append(slot['task_id'])
                return done, []
        except BlockingIOError:
            # Stopped; set aside on a later cycle. Marked `closing` meanwhile, so status never reads
            # it as implemented again: 270 `done`/`implemented` lines in 11 minutes for seven tasks.
            try:
                with execution.lock(common / 'writer.lock'):
                    for slot in doomed:
                        slot = slot_for(common, slot['task_id'])
                        if slot is not None and slot['state'] in RETIRABLE and not slot.get('closing'):
                            state.write_slot(common, dict(slot, closing=True), slot)
            except BlockingIOError:
                pass  # marked on a later cycle
            return [], [s['task_id'] for s in doomed]


def dispatch_with_retries(args):
    # Original dispatch owns admission/claims and never imports this adapter.
    # Only try retries when this invocation already owns an existing lease.
    common = state.common_dir(Path(args.consumer).resolve())
    live = state.live_coordinator(common)
    if not (live and live['owner'] == execution.owner_identity(args.owner_pid)):
        if dispatch.worker_command(args, args.owner_pid)[0] is None:
            return dispatch.dispatch(args)  # no worker host: the sequential fallback claims nothing
        # A new coordinator claims the lease first (dispatch would), so its held slots are
        # handled in this same call rather than a cycle later: a one-shot run sees them too.
        claimed = state.claim(Path(args.consumer).resolve(), args.owner_pid, profile=args.profile,
                              max_workers=dispatch.capacity(args))
        if claimed['outcome'] != 'CLAIMED':
            return dispatch.dispatch(args)  # reports the BUSY owner as before
    closed, closing = retire_closed(args)
    try:
        result = retry_held(args)
    except BlockingIOError:
        # A review holds the integration lock (it runs beside the coordinator's loop,
        # TOOLSET-183-d6): held retries wait for it; independent fresh work still starts.
        result = {'outcome': 'IDLE'}
    if result['outcome'] == 'IDLE':
        result = dispatch.dispatch(args)
    news = dict(closed_on_base=closed) if closed else {}
    news.update(closing=closing) if closing else None
    return dict(result, **news)
