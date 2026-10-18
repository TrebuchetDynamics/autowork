"""Which in_progress claims are verifiably idle, so parallel dispatch may adopt them.

AGENTS.md: a historical claim alone is not a permanent veto. Check actual
worker/session activity and candidate changes; adopt an idle candidate only after
verifying it is no longer being written, and preserve prior work. A claim is idle
only when every check passes:

- its TODO.md / goals.json entry has not changed for ``idle_after`` seconds;
- no branch named for the task has a commit, and no worktree on such a branch has
  a file change, within that time;
- no live agent process works in such a worktree, and no active agent session in the
  canonical checkout holds open a file inside the task's Touches (a task without Touches
  waits for every such session: its files are unknown); idle sessions never count;
- no note holds it: its own TODO entry, or any TODO.md line naming it, says to keep
  it open, holds it, forbids dispatch, or names a missing authority or approval.

Prior work is never modified: adoption only lets a fresh worker start, and its
prompt names the branches and worktrees to inspect and reuse.
"""
import os
from pathlib import Path
import re
import time

import task_execution as execution


def _token(task):
    # TASK-038 matches agent/x/TASK-038-planning but not T-9690. Matching a suffixed ID such
    # as TASK-017 too only finds more activity, which errs toward not adopting.
    return r'(^|[^A-Za-z0-9_-])' + re.escape(task) + r'([^A-Za-z0-9]|$)'


def _last_change(repo, task):
    stamp = execution.git(repo, 'log', '-1', '--format=%ct', '-E', '-G', _token(task), '--',
                          'TODO.md', 'goals.json')
    return int(stamp) if stamp else None


def _worktrees(repo):
    result, current = {}, {}
    for line in execution.git(repo, 'worktree', 'list', '--porcelain').splitlines() + ['']:
        if line.startswith('worktree '):
            current = {'path': line[9:]}
        elif line.startswith('branch refs/heads/'):
            current['branch'] = line[len('branch refs/heads/'):]
        elif not line and current.get('branch'):
            result[current['branch']] = current['path']
            current = {}
    return result


def _newest_change(path):
    """Newest mtime among a worktree's changed files (0 when clean or gone)."""
    root = Path(path)
    try:
        listing = execution.git(root, 'status', '--porcelain', '-z', '--untracked-files=all')
    except (ValueError, OSError):
        return 0
    newest = 0
    for entry in filter(None, listing.split('\0')):
        try:
            newest = max(newest, (root / entry[3:]).stat().st_mtime)
        except OSError:
            continue
    return newest


def prior_work(repo, task, worktrees=None):
    """Branches named for the task (as a whole token) and their worktrees."""
    worktrees = _worktrees(repo) if worktrees is None else worktrees
    pattern = re.compile(_token(task))
    found = []
    for line in execution.git(repo, 'for-each-ref', 'refs/heads', '--format=%(refname:short)\t%(committerdate:unix)').splitlines():
        branch, _, stamp = line.partition('\t')
        if pattern.search(branch):
            found.append(dict(branch=branch, committed=int(stamp or 0), worktree=worktrees.get(branch)))
    return found


# A person's or planner's note that a claim must stay as it is (sierra, 2026-10-16: "retain
# TASK-030/TASK-029/TASK-014 open for that exact missing authority", and TASK-029 was adopted).
HOLD_NOTE = re.compile(
    r'\b(retain|keep|leave)\b[^.;\n]{0,80}\b(open|in[_ ]progress|claimed)\b'
    r'|\bon hold\b|\bheld open\b|\bhold (it|this|the task|open)\b'
    r'|\bdo not (adopt|dispatch|execute|run|start|integrate|merge|take over)\b'
    r'|\bno worker (is )?dispatched\b|\bmust not be dispatched\b'
    r'|\b(requires?|needs?|missing|without|until|awaiting)\b[^.;\n]{0,40}'
    r'\b(authority|authori[sz]ation|approval|owner decision)\b', re.I)


def hold_note(text, task):
    """The first note holding ``task``: in its own TODO entry, or on any line naming it."""
    try:
        bodies = execution.goals_module().task_bodies(text).get(task) or []
    except (ValueError, AttributeError):
        bodies = []
    own = [line for body in bodies for line in body[0].splitlines()]
    pattern = re.compile(_token(task))
    # Table rows (Goal coverage) summarize evidence; they are not notes about the task.
    named = [line for line in text.splitlines() if pattern.search(line) and not line.lstrip().startswith('|')]
    for line in own + named:
        match = HOLD_NOTE.search(line)
        if match:
            return ' '.join(line[max(0, match.start() - 80):match.end() + 80].split())
    return None


def attributable(todo, task, held):
    """Whether a live session in the main checkout may be serving ``task``: it holds open a
    file inside the task's Touches, or the task declares no Touches (its files are unknown)."""
    import parallel_plan
    try:
        bodies = execution.goals_module().task_bodies(todo).get(task) or []
        touches = execution.goals_module().task_fields(bodies[0][0]).get('Touches', '') if bodies else ''
        declared = parallel_plan.paths(touches) if touches.strip() else []
    except (ValueError, AttributeError):
        return True
    if not declared:
        return True
    held = sorted(held)
    return bool(held) and len(parallel_plan.overlap(held, declared, [])['outside']) < len(held)


def idle_claims(repo, claims, idle_after, *, now=None, workers=None):
    """{task: evidence} for the claims in ``claims`` (task IDs) that are idle."""
    if not claims or idle_after <= 0:
        return {}
    now = time.time() if now is None else now
    repo = Path(repo).resolve()
    workers = execution.external_workers(repo) if workers is None else workers
    # This pool's own workers (kind 'autowork') are not claims' owners; other sessions are.
    live = [w for w in workers if w.get('kind') == 'session' and w.get('active') is not False]
    main = str(execution.canonical_root(repo))
    # Active sessions in the canonical or session checkout: which claim they serve is known
    # only from the files they hold open for writing (TOOLSET-120-fc 3).
    shared = [w for w in live if {str(repo), main} & set(w.get('workspaces', []))]
    held = {os.path.relpath(path, main) for w in shared for path in w.get('written') or []
            if Path(path).is_relative_to(main)}
    busy = {path for w in live for path in w.get('workspaces', [])} - {str(repo), main}
    worktrees = _worktrees(repo)
    try:
        todo = (repo / 'TODO.md').read_text()
    except OSError:
        return {}  # without the backlog, no note can be ruled out
    result = {}
    for task in claims:
        if hold_note(todo, task):
            continue  # someone said to keep this claim as it is
        if shared and attributable(todo, task, held):
            continue  # a live session there may be working on it
        changed = _last_change(repo, task)
        if changed is None or now - changed < idle_after:
            continue
        work = prior_work(repo, task, worktrees)
        if any(now - item['committed'] < idle_after for item in work):
            continue
        if any(item['worktree'] and (item['worktree'] in busy
                                     or now - _newest_change(item['worktree']) < idle_after) for item in work):
            continue
        result[task] = dict(claim_changed=changed, idle_seconds=int(now - changed), prior_work=work)
    return result
