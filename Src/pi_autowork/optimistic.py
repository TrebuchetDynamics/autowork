"""Optimistic landing (TOOLSET-344-7dadea23, owner decision 2026-10-21).

With PI_AUTOWORK_OPTIMISTIC=1 a candidate lands after its own checks and its review, without
the full-suite gate and without batching: finished tasks waited 40 minutes to 3 hours for batch
full checks. The background full check of main becomes the gate after landing. When it finds
new failures, `regression` names the tasks landed since the last green main that the failures
point at, `revert` reverts each one's merge in the session (`git revert -m 1`, so the
scorecard counts it as that task's regression) and reopens it with the failing tests named,
and the runner lands that. Pushes publish only main's last green revision, so the upstream
never carries a tree the full check has not passed.
"""
import os
from pathlib import Path
import re
import subprocess
import tomllib


def enabled(env=os.environ):
    return (env.get('PI_AUTOWORK_OPTIMISTIC') or '0').strip() not in ('', '0', 'false', 'no')


def _git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, text=True, timeout=120)
    return result.stdout.strip() if result.returncode == 0 else None


def landed(repo, green, rev):
    """[(task, merge commit)] whose receipt's integration commit main gained since ``green``,
    newest first. Without a green revision there is no range to judge: []."""
    if not green or not rev:
        return []
    gained = (_git(repo, 'rev-list', f'{green}..{rev}') or '').split()
    order = {commit: index for index, commit in enumerate(gained)}
    found = []
    for path in sorted((Path(repo) / 'tasks' / 'evidence').glob('*.toml')):
        try:
            receipt = tomllib.loads(path.read_text())
        except (OSError, ValueError):
            continue
        merge = str(receipt.get('integration') or '')
        if merge in order:
            found.append((str(receipt.get('task') or path.stem), merge))
    return sorted(found, key=lambda pair: order[pair[1]])


FRAME = re.compile(r'^\s*File "([^"]+)", line (\d+), in ')
FAILURE = re.compile(r'^(?:FAIL|ERROR): \S+ \(([^)]+)\)')


def frames(log):
    """{test id: [(path, line)]} from unittest output: the frames of each failure."""
    found, current = {}, None
    for line in log.splitlines():
        if head := FAILURE.match(line):
            current = found.setdefault(head.group(1), [])
        elif current is not None and (frame := FRAME.match(line)):
            current.append((frame.group(1), int(frame.group(2))))
    return found


def regression(repo, rev, failing, log, candidates):
    """The landed tasks the new failures point at: each failing test's traceback lines are
    blamed (`git blame` at ``rev``) to the task whose merge brought that line. When every
    failure points at some task, those tasks; otherwise every candidate, since a failure no
    landed change explains could be any of them."""
    if not candidates:
        return []
    tracked = set((_git(repo, 'ls-files') or '').splitlines())

    def owner(commit):
        for task, merge in candidates:
            # The merge brought ``commit`` when it is reachable from the merge and not from its
            # first parent (the main line before the task landed).
            if (subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', commit, merge]).returncode == 0
                    and subprocess.run(['git', '-C', str(repo), 'merge-base', '--is-ancestor', commit,
                                        f'{merge}^1']).returncode != 0):
                return task
        return None

    traces, blamed = frames(log), set()
    for test in failing:
        hit = set()
        for path, line in traces.get(test, ()):
            parts = Path(path).parts
            relative = next(('/'.join(parts[i:]) for i in range(len(parts)) if '/'.join(parts[i:]) in tracked), None)
            if relative is None:
                continue
            out = _git(repo, 'blame', '--porcelain', '-L', f'{line},{line}', rev, '--', relative) or ''
            if task := owner(out.split(' ', 1)[0]):
                hit.add(task)
        if not hit:
            return [task for task, _ in candidates]
        blamed |= hit
    return [task for task, _ in candidates if task in blamed]


def revert(worktree, tasks, merges, failing, rev, reopen):
    """Revert each task's merge in ``worktree`` (the session), newest first, and reopen it with
    the failing tests named; one commit for the reopened records. Returns the tasks reverted.
    A revert that conflicts with later work is undone and skipped: main stays red and the
    existing repair task handles it."""
    done = []
    named = ', '.join(failing[:5]) + (f' (+{len(failing) - 5} more)' if len(failing) > 5 else '')
    for task in tasks:
        merge = merges[task]
        message = (f'revert({task}): its landing broke the full check on main at {rev[:7]}\n\n'
                   f'Failing: {named}\n\nOptimistic landing (TOOLSET-344-7dadea23): the runner reverts a landed '
                   'task that main\'s full check finds broke it, and reopens the task.')
        result = subprocess.run(['git', '-C', str(worktree), 'revert', '--no-edit', '-m', '1', merge],
                                capture_output=True, text=True)
        if result.returncode != 0:
            subprocess.run(['git', '-C', str(worktree), 'revert', '--abort'], capture_output=True)
            continue
        subprocess.run(['git', '-C', str(worktree), 'commit', '--amend', '-q', '-m', message,
                        '-m', f'This reverts commit {merge}.'], capture_output=True)
        done.append(task)
    reopened = []
    for task in done:
        try:
            reopen(worktree, task, f'its landing broke the full check on main at {rev[:7]}: {named}; '
                                   'reverted by optimistic landing. Fix those tests in the next attempt')
            reopened.append(task)
        except Exception:  # noqa: BLE001 - a task closed some other way stays as it is
            continue
    if reopened:
        paths = [f'tasks/items/{task}.md' for task in reopened]
        subprocess.run(['git', '-C', str(worktree), 'add', '--', *paths], capture_output=True)
        subprocess.run(['git', '-C', str(worktree), 'commit', '-q', '-m',
                        f'docs(tasks): reopen {", ".join(reopened)} after reverting its landing (pi-autowork)',
                        '--', *paths], capture_output=True)
    return done
