"""Start parallel workers in their own worktrees; no integration or task status.

A worker is a host CLI process started in its own process group with the
worktree as its working directory. Its process identity is the slot's proof of
life, so a live worker is never replaced or duplicated. Templates never add
flags that bypass host approvals or sandboxes.
"""
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
    memory = available_memory_mb()
    if memory < min_free_mb * (running + 1):
        return f'resource gate: {memory} MB available, need {min_free_mb * (running + 1)} MB'
    load, cpus = os.getloadavg()[0], os.cpu_count() or 1
    if load >= cpus:
        return f'resource gate: load average {load:.2f} >= {cpus} CPUs'
    return ''


def data_dir(common, slot):
    # A readopted slot keeps the first attempt's report and logs.
    return execution.safe_path(common / 'slot-data' / slot['task_id'] / f'attempt-{slot.get("data_attempt", slot["attempt"])}')


def meta(common, slot):
    return execution.read(data_dir(common, slot) / 'meta.json') or {}


def prompt(task, worktree, branch, baseline, report, resume=False, adopted=None):
    touches = task['fields'].get('Touches', '(none declared)')
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
        '- Never edit ' + ', '.join(COORDINATOR_FILES) + '; the coordinator owns them.',
        '  Put a one-line CHANGELOG proposal in the report instead.',
        '- Run the task\'s relevant offline checks. Report each check once, with its final result',
        '  on your commit; do not list earlier failing runs you have since fixed (a listed failure',
        '  holds the task). Use $TMPDIR for temporary files and only',
        '  ports from $AUTOWORK_PORT_BASE to $AUTOWORK_PORT_BASE+99.',
        f'- When done, commit once on {branch}. Never push, merge, rebase, switch branches, or touch',
        '  another worktree. A finished commit is not task completion; the coordinator integrates.',
        '- Finally write JSON to the report file: {"task": ID, "commit": SHA or null,',
        '  "changed_files": [...], "checks": [{"command": ..., "result": "pass"|"fail", "summary": ...}],',
        '  "blockers": [...], "pending_live": [...], "changelog": "..."}.',
        '- "blockers" is only for work in this task\'s offline scope you could not finish; each says',
        '  what a person must decide or provide (for example a path outside Touches you need, or a',
        '  missing dependency). If blocked, report commit null with blockers and stop.',
        '- "pending_live" lists checks you cannot run here: physical devices, production or live',
        '  services, hardware, or human review. They become a separate live task and do not hold',
        '  this one; never list them as blockers or as failed checks.',
    ]
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
    path = (repo.parent / f'{repo.name}-autowork-{safe}').resolve()
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


def launch(argv, worktree, data, slot_index, stdin_path):
    data.mkdir(parents=True, exist_ok=True, mode=0o700)
    (data / 'tmp').mkdir(exist_ok=True, mode=0o700)
    env = {k: v for k, v in os.environ.items()
           if k != 'HERMES_TOOLSET_EXECUTION_COMMON' and not k.startswith('GIT_')}
    env.update(TMPDIR=str(data / 'tmp'), AUTOWORK_SLOT=str(slot_index),
               AUTOWORK_PORT_BASE=str(20000 + 100 * slot_index))
    with open(data / 'worker.log', 'ab') as log, open(stdin_path, 'rb') as stdin:
        process = subprocess.Popen(argv, cwd=worktree, env=env, stdin=stdin, stdout=log,
                                   stderr=subprocess.STDOUT, start_new_session=True)
    for _ in range(50):
        found = execution.identity(process.pid)
        if found:
            return found
        time.sleep(0.01)
    raise ValueError('worker exited before its identity could be recorded; see ' + str(data / 'worker.log'))


def stop(worker):
    """Stop a worker's whole process group, escalating while any member survives."""
    slot = {'worker': worker}
    for sig, pause in ((signal.SIGTERM, 2.0), (signal.SIGKILL, 2.0)):
        if not state.worker_live(slot):
            return
        try:
            os.killpg(worker['pid'], sig)
        except ProcessLookupError:
            return
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
            stop(slot['worker'])
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
    # A second failure gets no further attempt: it waits for a person, not the pool.
    parked = [s for s in occupying if state.exhausted(s)]
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
    planned = parallel_plan.plan([t for t in candidates if t['id'] not in {s['task_id'] for s in occupying}
                                  or t['id'] in restartable], running, all_tasks=everything,
                                 parked=[contract(s) for s in parked], adopted=set(idle))
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
