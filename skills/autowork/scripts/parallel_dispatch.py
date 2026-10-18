"""Start parallel workers in their own worktrees; no integration or task status.

A worker is a host CLI process started in its own process group with the
worktree as its working directory. Its process identity is the slot's proof of
life, so a live worker is never replaced or duplicated. Templates never add
flags that bypass host approvals or sandboxes.
"""
import errno
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import time

import parallel_claims
import parallel_plan
import parallel_state as state
import task_execution as execution
from worktree_paths import worktree_path

COORDINATOR_FILES = ('TODO.md', 'TODO.archive.md', 'goals.json', 'CHANGELOG.md')
DEFAULT_WORKERS, WORKER_CAP, HARD_LIMIT = 2, 4, 8
# Verified against the installed CLIs' --help (2026-10-15). The prompt also
# arrives on stdin, which Codex reads for `-`.
TEMPLATES = {
    'hermes': ['hermes', 'chat', '--query-file', '{prompt_file}', '--oneshot', '--in', '{worktree}',
               '--run-budget', '{timeout}', '-Q'],
    'codex': ['codex', 'exec', '-C', '{worktree}', '--sandbox', 'workspace-write',
              '--add-dir', '{git_common_dir}', '-'],
    'pi': ['pi', '-p', '@{prompt_file}'],
}
# Live qualification (TOOLSET-091-00, 2026-10-15): Codex 0.162.1 workers edit and check
# the task but cannot commit, because the workspace-write sandbox keeps Git metadata
# read-only. Without an approval bypass (never added here) they stay sequential-only.
UNQUALIFIED = {'codex': 'Codex workers cannot commit: its workspace-write sandbox keeps Git metadata read-only '
                        '(qualified 2026-10-15); pass --worker-command to supply your own worker'}
HOST_NAMES = {'hermes': 'hermes', 'hermes_cli': 'hermes', 'codex': 'codex', 'pi': 'pi', 'claude': 'claude'}
OCCUPYING = ('dispatched', 'running', 'reported', 'integrating', 'integrated', 'held', 'interrupted')


def coordinator_host(owner_pid):
    """Name the host whose session owns the coordinator, from its process ancestry."""
    pid = owner_pid
    for _ in range(8):
        try:
            argv = execution.argv_of(pid)
            stat = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        except (OSError, ValueError, IndexError):
            return ''
        names = [Path(a).name for a in argv[:3] if a and not a.startswith('-')]
        host = next((HOST_NAMES[n] for n in names if n in HOST_NAMES), '')
        if not host and execution.is_agent(argv):
            host = 'hermes'  # The installed launcher is `python3 -I -c '<... hermes_cli ...>'`.
        if host:
            return host
        pid = int(stat[1])
        if pid <= 1:
            return ''
    return ''


def worker_command(args, owner_pid):
    """Return (argv template, host label) or (None, fallback reason)."""
    if not Path('/proc/self/stat').exists():
        return None, 'parallel workers need Linux /proc process identity'
    if args.worker_command:
        try:
            template = json.loads(args.worker_command)
        except json.JSONDecodeError as exc:
            raise ValueError('--worker-command must be a JSON argv list') from exc
        if not isinstance(template, list) or not template or not all(isinstance(a, str) for a in template):
            raise ValueError('--worker-command must be a nonempty JSON list of strings')
        return template, 'custom'
    host = args.worker_host
    if host == 'auto':
        host = coordinator_host(owner_pid)
    if host == 'claude':
        return None, 'Claude Code workers need an explicit --worker-command (it chooses their approval mode)'
    if host not in TEMPLATES:
        return None, 'no worker template for this coordinator host; pass --worker-host or --worker-command'
    template = list(TEMPLATES[host])
    if host == 'hermes' and args.worker_profile:
        template[1:1] = ['-p', args.worker_profile]
    if shutil.which(template[0]) is None:
        return None, f'worker CLI {template[0]!r} is not installed'
    if host in UNQUALIFIED:
        return None, UNQUALIFIED[host]
    return template, host


def render(template, values):
    return [re.sub(r'\{(\w+)\}', lambda m: str(values[m[1]]) if m[1] in values else m[0], part)
            for part in template]


def available_memory_mb():
    for line in Path('/proc/meminfo').read_text().splitlines():
        if line.startswith('MemAvailable:'):
            return int(line.split()[1]) // 1024
    raise ValueError('MemAvailable missing from /proc/meminfo')


def resource_gate(running, min_free_mb):
    # Available memory already excludes what running workers use: one more worker needs its own
    # budget plus as much spare, however many run (TOOLSET-162-d2). Reserving a budget for each
    # running worker again capped every runner at two or three workers.
    memory = available_memory_mb()
    if memory < 2 * min_free_mb:
        return f'resource gate: {memory} MB available, need {2 * min_free_mb} MB for one more worker'
    # AUTOWORK_GATE_CPUS lowers the threshold so a test can force a refusal (TOOLSET-193-54);
    # scripts/check.py removes AUTOWORK_* from test processes, so a runner's value never leaks in.
    load, cpus = os.getloadavg()[0], float(os.environ.get('AUTOWORK_GATE_CPUS') or 0) or os.cpu_count() or 1
    if load >= cpus:
        return f'resource gate: load average {load:.2f} >= {cpus:g} CPUs'
    return ''


def data_dir(common, slot):
    # A readopted slot keeps the first attempt's report and logs.
    return execution.safe_path(common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}')


def meta(common, slot):
    return execution.read(data_dir(common, slot) / 'meta.json') or {}


def earlier_task_work(worktree, task_id, branch, baseline):
    """Local task branches, newest tip first, with their delta from shared history.

    Include both retired attempts (including retired -r2 retries) and the prior
    branch of a fresh retry. Full refs avoid ambiguity with similarly named tags.
    """
    safe = re.sub(r'[^A-Za-z0-9._-]+', '-', task_id)
    pattern = re.compile(r'autowork/' + re.escape(safe) + r'(?:-r[0-9]+)?(?:-set-aside-[0-9]+)?')
    refs = execution.git(worktree, 'for-each-ref', '--sort=refname', '--sort=-committerdate',
                         '--format=%(refname)%00%(objectname)%00%(committerdate:iso-strict)',
                         'refs/heads/autowork/')
    work = []
    for line in refs.splitlines():
        ref, tip, date = line.split('\0')
        name = ref.removeprefix('refs/heads/')
        if name == branch or not pattern.fullmatch(name):
            continue
        base = execution.git(worktree, 'merge-base', baseline, tip)
        # A status prefix protects leading filename whitespace from git()'s strip().
        files = execution.git(worktree, 'diff', '--name-status', '-z', '--no-renames', base, tip, '--')
        changed = files.split('\0')[1::2]
        work.append(f'- branch {name}; tip {tip}; date {date}; changed files: {json.dumps(changed)}')
    return work


def prompt(task, worktree, branch, baseline, report, resume=False, adopted=None):
    touches = task['fields'].get('Touches', '(none declared)')
    earlier = earlier_task_work(worktree, task['id'], branch, baseline)
    lines = [
        'You are an Autowork worker for exactly one task.',
        f'Task: {task["id"]}',
        f'Title: {task["title"]}',
        f'Worktree: {worktree}',
        f'Branch: {branch}',
        f'Baseline: {baseline}',
        f'Report file: {report}',
        '',
        'Implement exactly this one task. The coordinator selected it; do not run Autowork task',
        'selection, start other Autowork workers, or pick other tasks. You may use your host\'s',
        'own subagents for this task.',
        '',
        'Rules:',
        f'- Work only inside {worktree}; change only paths within Touches: {touches}',
        '- New dependency manifests, lock files, schema/migration or CI files need an explicit',
        '  protected path in Touches before editing; a broad directory alone does not reserve them.',
        '- Never edit ' + ', '.join(COORDINATOR_FILES) + '; the coordinator owns them.',
        '  Put a one-line CHANGELOG proposal in the report instead.',
        '- Tests: add or extend at most one focused test per behavior you change, at its public seam,',
        '  preferably as a new case in an existing test; none for docs, config or renames, and none that',
        '  repeats an existing case. Keep each test small. While working run the focused tests and the',
        '  task\'s Checks, not the whole suite after every edit.',
        '- Run the task\'s relevant offline checks. Report each check once, with its final result',
        '  on your commit; do not list earlier failing runs you have since fixed (a listed failure',
        '  holds the task). Put every temporary file and copy under $TMPDIR, never directly under',
        '  /tmp: /tmp may be RAM. For a scratch copy of this checkout use',
        '  `git worktree add --detach "$TMPDIR/copy" HEAD`, not a file copy. Install SDKs, toolchains',
        '  and package caches under $AUTOWORK_CACHE/<name>-<version>, shared by this repository\'s',
        '  tasks and reviews (reuse one that is already there); $TMPDIR goes with the task. Use only',
        '  ports from $AUTOWORK_PORT_BASE to $AUTOWORK_PORT_BASE+99.',
        f'- When done, commit once on {branch}. Never push, rebase, switch branches, or touch',
        '  another worktree. ' + ('Merge or cherry-pick only as permitted in Earlier task work below.'
                                 if earlier else 'Never merge or cherry-pick.'),
        '  A finished commit is not task completion; the coordinator integrates.',
        '- Finally write JSON to the report file: {"task": ID, "commit": SHA or null,',
        '  "changed_files": [...], "checks": [{"command": ..., "result": "pass"|"fail", "summary": ...}],',
        '  "blockers": [...], "pending_live": [...], "needs_touches": [...], "changelog": "..."}.',
        '- "blockers" is only for work in this task\'s offline scope you could not finish; each says',
        '  what a person must decide or provide (for example a path outside Touches you need, or a',
        '  missing dependency). If blocked, report commit null with blockers and stop.',
        '- If you are blocked only because you must change files outside Touches, also list exactly',
        '  those repository-relative paths in "needs_touches": [...] and leave your work uncommitted.',
        '  If Touches are widened you resume in this worktree with your changes intact.',
        '- "pending_live" lists checks you cannot run here: physical devices, production or live',
        '  services, hardware, or human review. They become a separate live task and do not hold',
        '  this one; never list them as blockers or as failed checks.',
    ]
    if earlier:
        lines += ['', 'Earlier task work:',
                  'These branches are reachable in this worktree in the same repository; no fetch is needed.',
                  'Changed files are each tip\'s delta from its merge-base with this attempt\'s baseline.',
                  *earlier,
                  'Only when this task asks to keep or continue earlier work, you may merge or cherry-pick',
                  'from these tips into your assigned branch; otherwise ignore them. Inspect the diff first:',
                  'earlier work is evidence, not accepted work, and may no longer fit the current task.',
                  'The current entry\'s Touches still apply: bring in nothing outside them, including',
                  'coordinator-owned files or unreserved protected paths. For a mixed-scope tip, reuse only',
                  'allowed paths instead of merging or cherry-picking the whole commit.',
                  'Keep one final task commit (for example cherry-pick --no-commit or merge --squash).',
                  'Never modify the earlier branches or their worktrees; no work is applied automatically.']
    if adopted:
        hours = adopted['idle_seconds'] // 3600
        lines += ['', f'This task was marked in_progress by another session that has been idle for {hours} h',
                  '(no task, branch or worktree change and no live agent). Earlier work may exist:']
        lines += [f'- branch {w["branch"]}' + (f' (worktree {w["worktree"]})' if w['worktree'] else '')
                  for w in adopted['prior_work']] or ['- none found']
        lines += ['Inspect it and reuse attributable in-scope work in your own worktree; never modify',
                  'those branches or worktrees.']
    if resume:
        lines += ['', 'A previous attempt was interrupted. Its uncommitted changes are still in the',
                  'worktree: inspect git status and continue from them rather than starting over.']
    return '\n'.join(lines + ['', 'Task contract from TODO.md:', '', task['contract'], ''])


def created_by_autowork(common, path, branch):
    journal = common / 'journal.jsonl'
    return journal.exists() and any(
        e.get('event') == 'worktree_created' and e.get('worktree') == str(path) and e.get('branch') == branch
        for e in map(json.loads, journal.read_text().splitlines()))


def create_worktree(repo, common, task_id, baseline):
    """Return (path, branch, baseline); adopt only a worktree the journal shows Autowork created."""
    safe = re.sub(r'[^A-Za-z0-9._-]+', '-', task_id)
    branch = 'autowork/' + safe
    path = worktree_path(repo, 'autowork-' + safe)
    exists = path.exists() or bool(execution.git(repo, 'branch', '--list', branch))
    if exists and created_by_autowork(common, path, branch) and path.is_dir():
        # A previous dispatch stopped between creating the worktree and its slot.
        return path, branch, execution.git(path, 'merge-base', baseline, 'HEAD')
    if exists:
        raise ValueError(f'{path} or branch {branch} already exists and was not created by parallel '
                         'Autowork; resolve it by hand')
    result = subprocess.run(['git', '-C', str(repo), 'worktree', 'add', '-q', '-b', branch, str(path), baseline],
                            capture_output=True, text=True, timeout=60)
    if result.returncode:
        raise ValueError('git worktree add failed: ' + result.stderr.strip())
    with execution.lock(common / 'writer.lock'):
        state.event(common, 'worktree_created', task_id=task_id, worktree=str(path), branch=branch,
                    baseline=baseline)
    return path, branch, baseline


def _private_tmp_dir(path, *, create=True):
    """Check ownership without following links before restricting permissions."""
    path = execution.safe_path(path)
    if create:
        path.mkdir(mode=0o700, exist_ok=True)
    fd = os.open(path, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        if os.fstat(fd).st_uid != os.getuid():
            raise ValueError(f'temporary directory has a foreign owner: {path}')
        os.fchmod(fd, 0o700)
    finally:
        os.close(fd)
    return path


def _tmp_record(common, value):
    """Validate durable allocation before reusing or deleting an external path."""
    key = hashlib.sha256(str(common.parent).encode()).hexdigest()[:8]
    if (not isinstance(value, dict) or type(value.get('slot')) is not int or value['slot'] < 1
            or not isinstance(value.get('path'), str)):
        raise ValueError('invalid temporary directory allocation')
    path = execution.safe_path(value['path'])
    number = str(value['slot'])
    runtime_suffix = ('aw', key, number)
    fallback = Path(f'/tmp/aw-{os.getuid()}-{key}-{number}')
    if (not Path(value['path']).is_absolute() or '..' in path.parts
            or len(os.fsencode(path)) > 47
            or (path != fallback and path.parts[-3:] != runtime_suffix)):
        raise ValueError('invalid temporary directory path')
    return path


def worker_tmpdir(data, slot_index):
    """Allocate under dispatch.lock; a task keeps its temp slot across attempts.

    Worker lanes/ports can be reused while reported or paused tasks retain their
    files, so the compact temp slot number has its own durable reservation.
    """
    common = data.parents[2]
    record = data.parent / 'tmp.json'
    saved = execution.read(record)
    if saved is not None:
        path = _tmp_record(common, saved)
        if path.parent != Path('/tmp'):
            for parent in (path.parents[2], path.parents[1], path.parent):
                _private_tmp_dir(parent)
        return _private_tmp_dir(path)
    used = set()
    for other in (common / 'slot-data').glob('*/tmp.json'):
        value = execution.read(other)
        _tmp_record(common, value)
        used.add(value['slot'])
    number = slot_index if slot_index not in used else next(i for i in range(1, len(used) + 2) if i not in used)
    key = hashlib.sha256(str(common.parent).encode()).hexdigest()[:8]
    runtime = os.environ.get('XDG_RUNTIME_DIR', '')
    path = None
    if runtime and Path(runtime).is_absolute():
        candidate = Path(runtime) / 'aw' / key / str(number)
        if (len(os.fsencode(candidate)) <= 47 and Path(runtime).is_dir()
                and not any((p / '.git').exists() for p in candidate.parents)):
            try:
                for parent in (Path(runtime), candidate.parent.parent, candidate.parent, candidate):
                    _private_tmp_dir(parent)
                path = candidate
            except OSError as exc:
                if exc.errno not in (errno.EACCES, errno.ENOENT, errno.EROFS, errno.ENOSPC, errno.EDQUOT):
                    raise
                # Unavailable runtime storage: use the short /tmp fallback.
    if path is None:
        path = Path(f'/tmp/aw-{os.getuid()}-{key}-{number}')
        _tmp_record(common, {'path': str(path), 'slot': number})
        _private_tmp_dir(path)
    execution.save(record, {'path': str(path), 'slot': number})
    return path


def cleanup_tmpdir(common, slot):
    """Retirement only; forget the reservation after removal, making retries safe."""
    if state.worker_live(slot):
        return
    record = common / 'slot-data' / slot['task_id'] / 'tmp.json'
    saved = execution.read(record)
    if saved is None:
        return  # Slots created before short temp directories have no allocation.
    path = _tmp_record(common, saved)
    try:
        _private_tmp_dir(path, create=False)
    except FileNotFoundError:
        pass
    else:
        shutil.rmtree(path)
    record.unlink()


def launch(argv, worktree, data, slot_index, stdin_path):
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    temporary = str(worker_tmpdir(data, slot_index))
    env = {k: v for k, v in os.environ.items()
           if k != 'AUTOWORK_EXECUTION_COMMON' and not k.startswith('GIT_')}
    # One cache per repository (<git common dir>/autowork-execution/cache), kept across tasks:
    # a pinned SDK one task installs is the next task's and every reviewer's too (TOOLSET-169-1d).
    cache = data.parents[2] / 'cache'
    cache.mkdir(exist_ok=True, mode=0o700)
    env.update(TMPDIR=temporary, TMP=temporary, TEMP=temporary, AUTOWORK_CACHE=str(cache), AUTOWORK_SLOT=str(slot_index),
               AUTOWORK_PORT_BASE=str(20000 + 100 * slot_index))
    env[state.WORKER_MARKER] = str(Path(worktree).resolve())
    with open(data / 'worker.log', 'ab') as log, open(stdin_path, 'rb') as stdin:
        process = subprocess.Popen(argv, cwd=worktree, env=env, stdin=stdin, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(50):
        found = execution.identity(process.pid)
        if found:
            return found
        time.sleep(0.01)
    raise ValueError('worker exited before its identity could be recorded; see ' + str(data / 'worker.log'))


def stop(worker, worktree=None):
    """Stop a worker's whole process group and every process carrying its worktree
    marker (children that left the group), escalating while any of them survives."""
    slot = {'worker': worker, 'worktree': worktree}
    for sig, pause in ((signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
        if not state.worker_live(slot):
            return
        if worker is not None:
            try:
                os.killpg(worker['pid'], sig)
            except ProcessLookupError:
                pass
        for pid in state.strays(worktree):
            try:
                os.kill(pid, sig)
            except ProcessLookupError:
                pass
        deadline = time.time() + pause
        while time.time() < deadline and state.worker_live(slot):
            time.sleep(0.05)


def enforce_timeouts(repo, owner_pid, common, default_timeout):
    """Each worker keeps the timeout it was started with (saved in its meta.json)."""
    stopped = []
    for slot in state.slots(common):
        limit = meta(common, slot).get('worker_timeout', default_timeout)
        if (slot['state'] in ('dispatched', 'running') and state.worker_live(slot)
                and time.time() - slot['started_at'] > limit):
            stop(slot['worker'], slot['worktree'])
            stopped.append(state.transition(repo, owner_pid, slot['task_id'], 'interrupted',
                                            reason=f'worker timeout after {limit:g} s'))
    return stopped


def summary(common, slot):
    info = meta(common, slot)
    return {'task': slot['task_id'], 'state': slot['state'], 'attempt': slot['attempt'],
            'worktree': slot['worktree'], 'branch': slot['branch'], 'baseline': slot['baseline'],
            'worker_pid': (slot.get('worker') or {}).get('pid'), 'slot': info.get('slot_index'),
            'command': info.get('command'), 'log': slot.get('log_path'), 'reason': slot.get('reason'),
            'commit': slot.get('commit')}


def capacity(args):
    count = args.parallel
    limit = args.max_workers or WORKER_CAP
    if not 1 <= limit <= HARD_LIMIT:
        raise ValueError(f'--max-workers must be between 1 and {HARD_LIMIT}')
    if not 1 <= count <= limit:
        raise ValueError(f'--parallel must be between 1 and {limit} (raise --max-workers up to {HARD_LIMIT})')
    return count


def fallback(repo, args, reason):
    task = execution.select(repo, args.tasks, args.plan)
    return {'outcome': 'SEQUENTIAL_FALLBACK', 'reason': reason, 'workspace': str(repo),
            'priority': task.pop('priority'), 'task': task,
            'next': 'Run the ordinary owner_cycle.py --apply for this task in the current session.'}


def retired(repo):
    """Task IDs closed since their slot stopped: done or superseded in goals.json, or
    checked off in TODO.md or its archive. A held or interrupted slot of such a task is
    history and occupies nothing; Plan For Me's supersession of a held second attempt
    otherwise left a must-run-alone successor waiting beside it for ever."""
    goals = execution.goals_module()
    ids = set()
    if (repo / 'goals.json').is_file():
        ids.update(t['id'] for t in goals.load(repo).get('tasks', [])
                   if t.get('status') in ('done', 'superseded'))
    for name in ('TODO.md', 'TODO.archive.md', 'todo.archive.md'):
        path = repo / name
        if path.is_file():
            ids.update(key for key, items in goals.task_bodies(path.read_text()).items()
                       if items and items[0][1].lower() == 'x')
    return ids


def contracts(repo, requested=None, plan=None):
    try:
        return execution.select_all(repo, requested, plan)
    except execution.NoEligibleTask:
        return []  # Malformed queues still raise and report ACTION_REQUIRED.


def protected_files(repo, revision=None):
    """Inventory shared build/schema/CI files without interpreting names as globs."""
    args = ('ls-tree', '-rz', '--name-only', revision) if revision else (
        'ls-files', '-z', '--cached', '--others', '--exclude-standard')
    names = execution.git(repo, *args).split('\0')
    return [name for name in names if name and parallel_plan.protected_path(name)]


def retry_plan(repo, current, requested=None, plan_path=None):
    """One admission policy for the retry adapter and its lifecycle transition guard."""
    held = {s['task_id'] for s in current if s['state'] == 'held' and s['attempt'] == 1
            and not state.exhausted(s) and not state.worker_live(s)}
    everything = contracts(repo)
    by_id = {t['id']: t for t in everything}
    tasks = contracts(repo, requested, plan_path) if (requested or plan_path) else everything
    contract = lambda s: by_id.get(s['task_id'], {'id': s['task_id'], 'fields': {}})
    occupying = [s for s in current if s['state'] in OCCUPYING and s['task_id'] not in held]
    parked = [s for s in occupying if state.exhausted(s)]
    # Retained slots are this coordinator's work, not outside claims. Exhausted
    # holds reserve only dependencies, just as they do for ordinary dispatch.
    return parallel_plan.plan([t for t in tasks if t['id'] in held],
                              [contract(s) for s in occupying if s not in parked],
                              all_tasks=everything, parked=[contract(s) for s in parked], adopted=held,
                              protected_files=protected_files(repo))


JOURNAL_TAIL = 8 * 2 ** 20  # the journal grows to tens of MB; hours of observations fit in this


def drain_after(env=os.environ):
    """Seconds an exclusive task waits before it drains the pool (TOOLSET-171-35)."""
    try:
        return max(0, int(env.get('PI_AUTOWORK_DRAIN_AFTER', '1800')))
    except ValueError:
        return 1800


def waiting_streaks(common, now=None):
    """{task: seconds it has waited without a break as a task that must run alone beside running
    work}, from the journal's dispatch observations, so a coordinator restart keeps the clock."""
    now = time.time() if now is None else now
    since = {}
    try:
        with open(common / 'journal.jsonl', 'rb') as stream:
            stream.seek(0, os.SEEK_END)
            stream.seek(max(0, stream.tell() - JOURNAL_TAIL))
            lines = stream.read().decode(errors='replace').splitlines()[1:]  # the first may be cut
    except OSError:
        return {}
    for line in lines:
        if '"dispatch_observed"' not in line:
            continue
        try:
            event = json.loads(line)
        except ValueError:
            continue
        # The drain clock: waiting as a task that must run alone, beside running work.
        ids = {v.get('id') for v in event.get('waiting') or []
               if isinstance(v, dict) and 'must run alone (beside ' in str(v.get('reason', ''))}
        since = {tid: since.get(tid, event.get('timestamp', now)) for tid in ids}
    return {tid: now - start for tid, start in since.items()}


def admit(candidates, running, restartable, occupying, *, everything, parked, adopted, protected,
          drain_after=None, waited=None):
    """Admission in two passes, so it agrees with integration about who owns a file
    (TOOLSET-157-cd). Interrupted candidates go first: their work already exists, and a
    held commit that only conflicts with them at integration does not stop them, or each
    would wait on the other. One that does not start this cycle still owns its declared
    files against fresh work, as integration counts it as an owner. (A commit held for
    overlap is parked by the caller, so it never stops either pass.)"""
    slotted = {s['task_id'] for s in occupying}
    resumable = [t for t in candidates if t['id'] in restartable]
    fresh = [t for t in candidates if t['id'] not in slotted and t['id'] not in restartable]
    options = dict(all_tasks=everything, parked=parked, adopted=adopted, protected_files=protected,
                   drain_after=drain_after, waited=waited)
    first = parallel_plan.plan(resumable, running, **options) if resumable else {'dispatch': [], 'waiting': []}
    resumed = {t['id'] for t in first['dispatch']}
    second = parallel_plan.plan(fresh, running + first['dispatch'], **options)
    by_id = {t['id']: t for t in everything}
    waiting_owners = [by_id[tid] for tid in restartable if tid not in resumed and tid in by_id]
    dispatch, waiting = [], first['waiting'] + second['waiting']
    def shares(task, other):
        try:
            return parallel_plan._shared(parallel_plan._touches(task), parallel_plan._touches(other))
        except ValueError:  # invalid Touches hold their own task (plan); they reserve nothing
            return False

    for task in second['dispatch']:
        owner = next((o['id'] for o in waiting_owners if shares(task, o)), None)
        if owner:
            waiting.append({'id': task['id'], 'reason': 'overlapping paths with interrupted ' + owner,
                            'blocked_by': [owner]})
        else:
            dispatch.append(task)
    return {'dispatch': first['dispatch'] + dispatch, 'waiting': waiting}


def dispatch(args):
    repo = Path(execution.git(Path(args.consumer).expanduser().resolve(), 'rev-parse', '--show-toplevel')).resolve()
    count = capacity(args)
    template, host = worker_command(args, args.owner_pid)
    if template is None:
        return fallback(repo, args, host)
    claimed = state.claim(repo, args.owner_pid, profile=args.profile, max_workers=count)
    if claimed['outcome'] != 'CLAIMED':
        return claimed
    common = state.common_dir(repo)
    # One dispatch or wait pass at a time; a separate file so it never nests with writer.lock.
    with execution.lock(common / 'dispatch.lock'):
        return dispatch_locked(args, repo, common, count, template, host)


def dispatch_locked(args, repo, common, count, template, host):
    timeouts = enforce_timeouts(repo, args.owner_pid, common, args.worker_timeout)
    current = state.reconcile(repo, args.owner_pid)
    everything = contracts(repo)
    by_id = {t['id']: t for t in everything}
    candidates = contracts(repo, args.tasks, args.plan) if (args.tasks or args.plan) else everything
    closed = retired(repo)
    occupying = [s for s in current if s['state'] in OCCUPYING
                 and not (s['state'] in ('held', 'interrupted') and s['task_id'] in closed)]
    contract = lambda s: by_id.get(s['task_id'], {'id': s['task_id'], 'fields': {}})
    # A second failure gets no further attempt: it waits for a person, not the pool. A commit
    # held for overlap owns nothing while it waits either (integration agrees): it is offered
    # again once its files are free, and a real conflict goes to the merge resolver.
    parked = [s for s in occupying if state.exhausted(s) or state.overlap_held(s)]
    running = [contract(s) for s in occupying if s not in parked]
    live = [s for s in current if s['state'] in ('dispatched', 'running') and state.worker_live(s)]
    restartable = {s['task_id']: s for s in current if s['state'] in ('interrupted', 'released')
                   and (s['attempt'] == 1 or s.get('paused'))}
    # A restartable slot's own files are not someone else's running work.
    running = [t for t in running if t['id'] not in restartable]
    slotted = {s['task_id'] for s in current}
    claimed = [t['id'] for t in candidates if t['id'] not in slotted
               and re.split(r'[;.\s]', t['fields'].get('Status', 'open'))[0] == 'in_progress']
    idle = parallel_claims.idle_claims(repo, claimed, getattr(args, 'adopt_idle_claims', 0)) if claimed else {}
    planned = admit(candidates, running, restartable, occupying, everything=everything,
                    parked=[contract(s) for s in parked], adopted=set(idle), protected=protected_files(repo),
                    drain_after=drain_after(), waited=waiting_streaks(common))
    used = {meta(common, s).get('slot_index') for s in live}
    baseline = execution.git(repo, 'rev-parse', 'HEAD')
    started, waiting = [], list(planned['waiting'])
    for task in planned['dispatch']:
        if len(live) + len(started) >= count:
            waiting.append({'id': task['id'], 'reason': f'all {count} worker slots busy', 'blocked_by': []})
            continue
        gate = resource_gate(len(live) + len(started), args.min_free_mem_mb)
        if gate:
            waiting.append({'id': task['id'], 'reason': gate, 'blocked_by': []})
            continue
        previous = restartable.get(task['id'])
        if previous:
            worktree, branch, base = Path(previous['worktree']), previous['branch'], previous['baseline']
        else:
            worktree, branch, base = create_worktree(repo, common, task['id'], baseline)
            state.create_slot(repo, args.owner_pid, task['id'], worktree=str(worktree), branch=branch,
                              baseline=base)
        slot = next(s for s in state.slots(common) if s['task_id'] == task['id'])
        attempt = slot['attempt'] + (1 if previous and not previous.get('paused') else 0)
        data = execution.safe_path(common / 'slot-data' / task['id'] / f'attempt-{attempt}')
        data.mkdir(parents=True, exist_ok=True, mode=0o700)
        report = data / 'report.json'
        if previous and previous.get('paused'):
            report.unlink(missing_ok=True)  # a resumed attempt reports afresh
        prompt_file = data / 'prompt.md'
        (data / 'contract.txt').write_text(task['contract'].strip() + '\n')  # what an answer is compared with
        prompt_file.write_text(prompt(task, worktree, branch, base, report, resume=bool(previous),
                                      adopted=idle.get(task['id'])))
        if task['id'] in idle:
            with execution.lock(common / 'writer.lock'):
                state.event(common, 'claim_adopted', task_id=task['id'], evidence=idle[task['id']])
        index = next(i for i in range(1, HARD_LIMIT + 1) if i not in used)
        used.add(index)
        argv = render(template, {'worktree': worktree, 'prompt_file': prompt_file, 'timeout': int(args.worker_timeout),
                                 'report_file': report, 'git_common_dir': common.parent})
        if previous:
            state.transition(repo, args.owner_pid, task['id'], 'dispatched', worktree=str(worktree),
                             branch=branch, baseline=base)
        execution.save(data / 'meta.json', {'slot_index': index, 'command': argv, 'host': host,
                                            'prompt_file': str(prompt_file), 'report_file': str(report),
                                            'worker_timeout': args.worker_timeout})
        try:
            worker = launch(argv, worktree, data, index, prompt_file)
        except (OSError, ValueError) as exc:
            # A launch failure is not an interrupted attempt: hold it with the cause.
            slot = state.transition(repo, args.owner_pid, task['id'], 'held', reason='worker launch failed: ' + str(exc),
                                    cause='launch',
                                    log_path=str(data / 'worker.log'))
            waiting.append({'id': task['id'], 'reason': slot['reason']})
            used.discard(index)
            continue
        slot = state.transition(repo, args.owner_pid, task['id'], 'running', worker=worker,
                                log_path=str(data / 'worker.log'))
        started.append(summary(common, slot))
    slots = [summary(common, s) for s in state.slots(common)]
    active = sum(1 for s in state.slots(common) if s['state'] in ('dispatched', 'running') and state.worker_live(s))
    outcome = 'DISPATCHED' if started else ('WAITING' if active else 'IDLE')
    with execution.lock(common / 'writer.lock'):
        state.require_owner(common, args.owner_pid)
        from parallel_status import pending_tasks
        pending_ids = {v['id'] for v in waiting}
        pending = waiting + [v for v in pending_tasks(repo, {s['task_id'] for s in state.slots(common)})
                             if v['id'] not in pending_ids]
        state.event(common, 'dispatch_observed', waiting=pending, max_workers=count)
    return {'outcome': outcome, 'workspace': str(repo), 'host': host, 'max_workers': count,
            'active_workers': active, 'dispatched': started, 'waiting': waiting,
            'adopted': [d['task'] for d in started if d['task'] in idle],
            'timed_out': [s['task_id'] for s in timeouts], 'slots': slots,
            'next': {'DISPATCHED': 'Run --wait to block until a worker finishes, then review its report.',
                     'WAITING': 'Run --wait; no other task can start beside the running workers.',
                     'IDLE': 'No runnable task and no running worker.'}[outcome]}


def wait(args, timeout):
    """Block in the helper (no model tokens) until a worker exits or the timeout passes."""
    repo = Path(execution.git(Path(args.consumer).expanduser().resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common = state.common_dir(repo)
    state.require_owner(common, args.owner_pid)
    before = {s['task_id']: s['state'] for s in state.slots(common)}
    deadline = time.time() + timeout
    while True:
        try:
            with execution.lock(common / 'dispatch.lock'):
                timed_out = enforce_timeouts(repo, args.owner_pid, common, args.worker_timeout)
                finished = [s for s in state.slots(common)
                            if s['state'] in ('dispatched', 'running') and not state.worker_live(s)]
                if timed_out or finished or time.time() >= deadline:
                    current = state.reconcile(repo, args.owner_pid)
                    changed = [summary(common, s) for s in current if before.get(s['task_id']) != s['state']]
                    active = sum(1 for s in current
                                 if s['state'] in ('dispatched', 'running') and state.worker_live(s))
                    return {'outcome': 'CHANGED' if changed else 'TIMEOUT', 'workspace': str(repo),
                            'active_workers': active, 'changed': changed,
                            'next': 'Review reported slots, then run --apply --parallel again to refill.'}
        except BlockingIOError:
            pass  # A dispatch pass is running; look again shortly.
        time.sleep(0.2)
