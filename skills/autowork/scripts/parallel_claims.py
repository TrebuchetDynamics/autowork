"""Which in_progress claims are verifiably idle, so parallel dispatch may adopt them.

AGENTS.md: a historical claim alone is not a permanent veto. Check actual
worker/session activity and candidate changes; adopt an idle candidate only after
verifying it is no longer being written, and preserve prior work. A claim is idle
only when every check passes:

- its TODO.md / goals.json entry has not changed for ``idle_after`` seconds;
- no branch named for the task has a commit, and no worktree on such a branch has
  a file change, within that time;
- no live agent process works in such a worktree, and no active agent session is
  in the canonical checkout (its task cannot be attributed, so nothing is adopted).

Prior work is never modified: adoption only lets a fresh worker start, and its
prompt names the branches and worktrees to inspect and reuse.
"""
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


def idle_claims(repo, claims, idle_after, *, now=None, workers=None):
    """{task: evidence} for the claims in ``claims`` (task IDs) that are idle."""
    if not claims or idle_after <= 0:
        return {}
    now = time.time() if now is None else now
    repo = Path(repo).resolve()
    workers = execution.external_workers(repo) if workers is None else workers
    # This pool's own workers (kind 'autowork') are not claims' owners; other sessions are.
    live = [w for w in workers if w.get('kind') == 'session' and w.get('active') is not False]
    main = execution.git(repo, 'worktree', 'list', '--porcelain').splitlines()[0][len('worktree '):]
    if any({str(repo), main} & set(w.get('workspaces', [])) for w in live):
        return {}  # an active session in the canonical or session checkout: its task is unknown
    busy = {path for w in live for path in w.get('workspaces', [])}
    worktrees = _worktrees(repo)
    result = {}
    for task in claims:
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
