"""Small TODO execution boundary. Repository files remain the task authority.

Private state contains a live process lease and command receipts, never task
statuses. A successful command is not task acceptance, review or completion.
"""
import argparse
import ctypes
from contextlib import contextmanager
import fcntl
import hashlib
import importlib.util
import json
import math
import os
from pathlib import Path
import re
import shutil
import signal
import subprocess
import tempfile
import time
import uuid


class PriorityDriftError(ValueError):
    """Default selection would run a stale order; reconcile before selecting."""
    def __init__(self, status):
        self.status = status
        super().__init__(status['action'])


def goals_module():
    path = Path(__file__).resolve().parents[2] / 'docs-sync/scripts/goals.py'
    spec = importlib.util.spec_from_file_location('todo_goals', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def unique(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError('duplicate private evidence field')
        result[key] = value
    return result


def safe_path(path):
    path = Path(path).absolute()
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('refuse symlinked execution state')
    return path


def read(path):
    path = safe_path(path)
    return json.loads(path.read_text(), object_pairs_hook=unique) if path.exists() else None


def save(path, value):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.execution-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            json.dump(value, stream, indent=2, allow_nan=False)
            stream.write('\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


@contextmanager
def lock(path):
    path = safe_path(path)
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        yield fd
    finally:
        os.close(fd)


def git(repo, *args):
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    result = subprocess.run(['git', '-C', str(repo), *args], env=env,
                            capture_output=True, text=True, timeout=10)
    if result.returncode:
        raise ValueError('consumer must be an existing Git workspace')
    return result.stdout.strip()


def identity(pid):
    try:
        if isinstance(pid, bool) or int(pid) <= 1:
            return None
        fields = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()
        if fields[0] in ('Z', 'X'):
            return None
        return {'pid': int(pid), 'start_ticks': int(fields[19]),
                'boot_id': Path('/proc/sys/kernel/random/boot_id').read_text().strip()}
    except (OSError, ValueError, IndexError):
        return None


def ancestors():
    found = set()
    pid = os.getpid()
    while pid > 1 and pid not in found:
        found.add(pid)
        try:
            pid = int(Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()[1])
        except (OSError, ValueError, IndexError):
            break
    return found


def owner_identity(pid):
    result = identity(pid) if pid else None
    if not result or pid not in ancestors() or pid == os.getpid():
        raise ValueError('--owner-pid must name a live persistent ancestor, not PID 1 or the helper')
    return result


def active_owner(claim):
    if not isinstance(claim, dict) or not isinstance(claim.get('owner'), dict):
        raise ValueError('malformed execution lease; inspect active.json without changing task evidence')
    owner = claim['owner']
    if (set(owner) != {'pid', 'start_ticks', 'boot_id'} or type(owner['pid']) is not int or owner['pid'] <= 1
            or type(owner['start_ticks']) is not int or owner['start_ticks'] <= 0
            or not isinstance(owner['boot_id'], str) or not owner['boot_id']):
        raise ValueError('malformed process identity in execution lease')
    return identity(owner['pid']) == owner


def external_workers(repo):
    """Observe live agent processes, never infer activity from historical cards.

    This supplements cooperative Git-common-dir locking; it cannot lock an
    unaware editor or a writer on another machine.
    """
    workspaces = [Path(line[9:]).resolve() for line in
                  git(repo, 'worktree', 'list', '--porcelain').splitlines()
                  if line.startswith('worktree ')]
    own = ancestors()
    workers = []
    marker = ('HERMES_TOOLSET_EXECUTION_COMMON=' + git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')).encode()
    for entry in Path('/proc').glob('[0-9]*'):
        pid = int(entry.name)
        if pid in own or not identity(pid):
            continue
        try:
            argv = (entry / 'cmdline').read_bytes().decode(errors='replace').split('\0')
            # A detached command still carries its repository attribution after
            # its launching helper crashes. Never adopt while it is alive.
            if marker in (entry / 'environ').read_bytes().split(b'\0'):
                workers.append(identity(pid))
                continue
            names = {Path(arg).name for arg in argv[:3] if arg and not arg.startswith('-')}
            if not names.intersection({'hermes', 'hermes_cli', 'codex', 'claude', 'aider', 'pi', 'run_agent.py'}):
                continue
            cwd = (entry / 'cwd').resolve(strict=True)
            paths = [cwd] + [Path(arg).resolve() for arg in argv if arg.startswith('/')]
            # Native/manual agents can launch outside the workspace. Inspect
            # explicit argv paths and currently open writable files as well.
            for link in (entry / 'fd').iterdir():
                try:
                    info = (entry / 'fdinfo' / link.name).read_text()
                    flags = int(re.search(r'^flags:\s+([0-7]+)', info, re.M)[1], 8)
                    if flags & os.O_ACCMODE:
                        paths.append(link.resolve(strict=True))
                except (OSError, TypeError):
                    continue
            if any(path == root or root in path.parents for path in paths for root in workspaces):
                workers.append(identity(pid))
        except (OSError, ValueError):
            continue
    return workers


def subreaper():
    """Adopt orphaned grandchildren so setsid/close_fds cannot escape cleanup."""
    if not Path('/proc/self/task').is_dir():
        raise ValueError('bounded command descendant cleanup requires Linux process inspection on this host')
    libc = ctypes.CDLL(None, use_errno=True)
    if libc.prctl(36, 1, 0, 0, 0) != 0:  # PR_SET_CHILD_SUBREAPER
        raise OSError(ctypes.get_errno(), 'cannot establish command descendant cleanup')


def reap_children():
    """Stop before walking each child's descendants; signal through stable pidfds."""
    terminated = []
    def reap(parent):
        path = Path(f'/proc/{parent}/task/{parent}/children')
        try:
            children = [int(pid) for pid in path.read_text().split()]
        except FileNotFoundError:
            return
        for pid in children:
            try:
                fd = os.pidfd_open(pid)
            except ProcessLookupError:
                continue
            try:
                if identity(pid):
                    signal.pidfd_send_signal(fd, signal.SIGSTOP)
                    terminated.append(pid)
                reap(pid)
                signal.pidfd_send_signal(fd, signal.SIGKILL)
            except ProcessLookupError:
                pass
            finally:
                os.close(fd)
    reap(os.getpid())
    # Reap adopted descendants as well as original direct children.
    while True:
        try:
            os.waitpid(-1, 0)
        except ChildProcessError:
            break
    return terminated


def local_path(repo, value):
    path = Path(value)
    if path.is_absolute() or '..' in path.parts:
        raise ValueError('input paths must be repository-relative')
    result = (repo / path).resolve()
    if result != repo and repo not in result.parents:
        raise ValueError('input escapes repository')
    return result


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


def select(repo, requested, plan):
    goals = goals_module()
    todo = repo / 'TODO.md'
    bodies = goals.task_bodies(todo.read_text())
    if any(len(items) != 1 for items in bodies.values()):
        raise ValueError('duplicate TODO task IDs; reconcile the repository contract')
    wanted = requested.split(',') if requested else None
    if wanted and (len(set(wanted)) != len(wanted) or
                   any(not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_-]*', item) for item in wanted)):
        raise ValueError('--tasks must name unique TODO IDs')
    ledger_path = repo / 'goals.json'
    ledger = goals.load(repo) if ledger_path.exists() else None
    if ledger:
        problems = goals.errors(ledger)
        if problems:
            raise ValueError('invalid goals.json: ' + '; '.join(problems))
        ledger = goals.normalize(ledger)
        # Named tasks and an owner's active claim are explicit; only default selection
        # would execute a stale priority, so only it stops on drift.
        try:
            picks, priority = goals.queue(ledger, todo.read_text(), allow_drift=bool(wanted))
        except goals.PriorityDrift as drift:
            raise PriorityDriftError(drift.status) from None
        ordered = [task['id'] for task, _ in picks]
        indexed = {task['id']: task for task in ledger['tasks']}
    else:
        ordered = sorted(bodies, key=lambda key: {'Now': 0, 'Next': 1}.get(bodies[key][0][2], 2))
        indexed = {}
        priority = {'state': 'todo_only'}
    reasons = []
    for tid in (wanted or ordered):
        if tid not in bodies:
            reasons.append(f'{tid}: missing TODO contract')
            continue
        body, mark, section = bodies[tid][0]
        fields = goals.task_fields(body)
        labels = re.findall(r'^[ \t]*(?:[-*][ \t]+)?(?:\*\*)?([A-Za-z][A-Za-z /-]*):', goals.task_prose(body), re.M)
        if any(labels.count(label) > 1 for label in ('Scope', 'Acceptance', 'Checks', 'Dependencies', 'Status', 'Sources')):
            reasons.append(f'{tid}: duplicate task contract fields')
            continue
        if mark.lower() == 'x' or section not in ('Now', 'Next'):
            reasons.append(f'{tid}: completed or decision-held')
            continue
        if ledger and tid not in ordered:
            reasons.append(f'{tid}: ledger dependency or disposition holds execution')
            continue
        if any(not fields.get(key) for key in ('Scope', 'Acceptance', 'Checks')):
            reasons.append(f'{tid}: needs unique Scope, Acceptance and Checks fields')
            continue
        deps = fields.get('Dependencies', 'None.').strip().strip('.').strip()
        if deps.lower() not in ('none', 'none required', '—', '-', ''):
            ids = re.findall(r'`?([A-Za-z0-9][A-Za-z0-9_-]*)`?', deps)
            # Dependencies must be explicit IDs; unknown prose is not evidence of completion.
            done = {key for key, items in bodies.items() if items[0][1].lower() == 'x'}
            archive = repo / 'TODO.archive.md'
            if archive.is_file():
                done.update(key for key, items in goals.task_bodies(archive.read_text()).items()
                            if len(items) == 1 and items[0][1].lower() == 'x')
            done.update(key for key, task in indexed.items() if task['status'] == 'done')
            if any(item not in done for item in ids):
                reasons.append(f'{tid}: unresolved dependency {deps}')
                continue
        if ledger:
            task = indexed[tid]
            status = re.split(r'[;\.\s]', fields.get('Status', task['status']))[0]
            if task['section'] != section or status != task['status']:
                reasons.append(f'{tid}: TODO and goals.json disagree; repair from source evidence')
                continue
        if plan:
            sources = re.findall(r'\]\(([^)]+)\)', fields.get('Sources', ''))
            if plan not in sources:
                reasons.append(f'{tid}: not linked to the named plan')
                continue
            path, _, anchor = plan.partition('#')
            source = local_path(repo, path)
            if not source.is_file():
                raise ValueError('named plan does not exist')
            if anchor and anchor not in {re.sub(r'[^\w -]', '', heading.lower()).replace(' ', '-')
                                        for heading in re.findall(r'^#+\s+(.+)', source.read_text(), re.M)}:
                raise ValueError('named plan heading does not exist')
        return {'id': tid, 'title': body.splitlines()[0].strip(' —:-'),
                'section': section, 'contract': body.strip(), 'fields': fields, 'priority': priority}
    raise ValueError('; '.join(reasons) or 'no eligible TODO task; inspect source and record a bounded improvement')


def command(args, repo, state, common, task, lease, lock_fd):
    if not args.timeout or not math.isfinite(args.timeout) or args.timeout <= 0:
        raise ValueError('--run requires a positive finite --timeout')
    if args.budget_seconds is not None and (not math.isfinite(args.budget_seconds) or args.budget_seconds <= 0):
        raise ValueError('--budget-seconds must be positive and finite')
    budget_path = common / ('budget-' + task['id'] + '.json')
    budget = read(budget_path)
    if budget is None and budget_path.exists():
        return {'outcome': 'LIMIT_REQUIRED', 'reason': 'Retained allowance is null; unknown usage is not a new allocation.'}
    timeout = args.timeout
    if budget is not None:
        if (not isinstance(budget, dict) or type(budget.get('allocation')) not in (int, float) or
                not math.isfinite(budget['allocation']) or budget['allocation'] <= 0 or
                budget.get('pending') is not False or type(budget.get('remaining')) not in (int, float) or
                not math.isfinite(budget['remaining']) or budget['remaining'] <= 0 or
                budget['remaining'] > budget['allocation'] or
                (args.budget_seconds is not None and args.budget_seconds != budget.get('allocation'))):
            return {'outcome': 'LIMIT_REQUIRED', 'reason': 'Retained command allowance exhausted, changed or usage unknown; no automatic reset.'}
        timeout = min(timeout, budget['remaining'])
    elif args.budget_seconds is not None:
        budget = {'allocation': args.budget_seconds, 'remaining': args.budget_seconds, 'pending': False}
        timeout = min(timeout, args.budget_seconds)
    paths = ['TODO.md'] + (['goals.json'] if (repo / 'goals.json').exists() else []) + args.source_path
    if args.plan:
        paths.append(args.plan.split('#', 1)[0])
    before = {name: digest(local_path(repo, name)) for name in dict.fromkeys(paths)}
    if any(value is None for value in before.values()):
        raise ValueError('--source-path must bind existing regular files, not directories or missing inputs')
    # Resolve against the child working directory, including relative PATH entries.
    executable = args.run[0]
    search_path = os.pathsep.join(str((repo / part).resolve()) if not Path(part).is_absolute() else part
                                  for part in os.environ.get('PATH', os.defpath).split(os.pathsep))
    resolved = str(local_path(repo, executable)) if '/' in executable and not Path(executable).is_absolute() else executable
    resolved = shutil.which(resolved, path=search_path)
    if not resolved:
        raise ValueError('command executable not found')
    executable_before = digest(Path(resolved).resolve())
    subreaper()
    run_id = uuid.uuid4().hex
    log = common / (run_id + '.log')
    if budget:
        save(budget_path, dict(budget, pending=run_id))
    started = time.monotonic()
    timed_out = False
    terminated = []
    try:
        with os.fdopen(os.open(safe_path(log), os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600), 'wb') as stream:
            env = dict(os.environ, HERMES_TOOLSET_EXECUTION_COMMON=str(common.parent))
            child = subprocess.Popen([resolved, *args.run[1:]], cwd=repo, env=env, stdout=stream, stderr=subprocess.STDOUT,
                                     start_new_session=True, pass_fds=(lock_fd,))
            running = dict(lease, owner=identity(child.pid), command_group=child.pid)
            save(common / 'active.json', running)
            try:
                code = child.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                timed_out = True
                os.killpg(child.pid, signal.SIGKILL)
                code = child.wait()
            finally:
                # A successful shell must not leave background writers past the boundary.
                try:
                    os.killpg(child.pid, signal.SIGKILL)
                except ProcessLookupError:
                    pass
                terminated = reap_children()
    finally:
        elapsed = time.monotonic() - started
        if budget:
            budget['remaining'] = max(0, budget['remaining'] - elapsed)
            budget['pending'] = False
            save(budget_path, budget)
        if args.owner_pid:
            save(common / 'active.json', lease)
        else:
            (common / 'active.json').unlink(missing_ok=True)
    after = {name: digest(local_path(repo, name)) for name in before}
    inputs_match = before == after and executable_before == digest(Path(resolved).resolve())
    result = {'outcome': 'TIMED_OUT' if timed_out else 'CHILDREN_TERMINATED' if terminated else 'SOURCE_CHANGED' if not inputs_match else 'EXECUTED' if code == 0 else 'CHECK_FAILED',
              'command_receipt': {'task_id': task['id'], 'workspace': str(repo), 'exit_code': code,
                                  'argv': args.run, 'reusable_acceptance': False, 'terminated_descendants': terminated,
                                  'elapsed_seconds': elapsed, 'timeout_seconds': timeout,
                                  'inputs_before': before, 'inputs_after': after, 'inputs_match': inputs_match,
                                  'executable': resolved, 'executable_sha256': executable_before,
                                  'log': str(log), 'receipt': str(common / (run_id + '.json'))}}
    save(common / (run_id + '.json'), result)
    return result


def execute(args):
    repo = Path(git(Path(args.consumer).expanduser().resolve(), 'rev-parse', '--show-toplevel')).resolve()
    common_git = Path(git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir'))
    common = safe_path(common_git / 'autowork-execution')
    state = safe_path(Path(args.state_dir).expanduser()) if args.state_dir else common
    with lock(state / 'goal-handoff.lock'), lock(common / 'writer.lock') as fd:
        claim_path = common / 'active.json'
        claim = read(claim_path)
        if claim is None and claim_path.exists():
            raise ValueError('null execution lease; inspect current process evidence before repairing it')
        if claim is not None:
            active_owner(claim)  # Validate even empty or otherwise false-valued evidence.
        owner = owner_identity(args.owner_pid) if args.owner_pid else None
        if claim and active_owner(claim) and (claim['owner'] != owner or claim.get('workspace') != str(repo)
                                             or claim.get('profile') != args.profile):
            return {'outcome': 'BUSY', 'reason': 'A live writer owns this repository.', 'owner': claim['owner']}
        if args.release:
            if not claim or claim['owner'] != owner:
                raise ValueError('release requires the matching live owner')
            claim_path.unlink()
            return {'outcome': 'RELEASED'}
        requested = args.tasks
        if not requested and claim and active_owner(claim) and claim['owner'] == owner:
            requested = claim.get('task_id')
        selection_paths = ['TODO.md', 'goals.json'] + ([args.plan.split('#', 1)[0]] if args.plan else [])
        selected_inputs = {path: digest(local_path(repo, path)) for path in selection_paths}
        task = select(repo, requested, args.plan)
        if selected_inputs != {path: digest(local_path(repo, path)) for path in selection_paths}:
            raise ValueError('repository task inputs changed during selection; reread current files')
        result = {'outcome': 'READY', 'task': task, 'completed_tasks': [], 'workspace': str(repo),
                  'priority': task.pop('priority')}
        if not args.apply:
            return result
        if not args.run and not owner:
            return dict(result, outcome='OWNER_REQUIRED', reason='Use a persistent coordinator ancestor PID or one bounded --run command.')
        if claim and active_owner(claim) and claim.get('task_id') != task['id']:
            return dict(result, outcome='BUSY', reason='Release the current task before claiming another.')
        workers = external_workers(repo)
        if workers:
            return dict(result, outcome='BUSY', reason='Live agent process in this repository; reconcile its work first.', owners=workers)
        lease = {'task_id': task['id'], 'workspace': str(repo), 'profile': args.profile,
                 'owner': owner or identity(os.getpid()), 'selected_inputs': selected_inputs}
        save(claim_path, lease)
        pointer = {'claim_path': str(claim_path), 'task_id': task['id']}
        key = hashlib.sha256(str(common).encode()).hexdigest()
        save(state / 'task-execution-claims' / (key + '.json'), pointer)
        save(state / 'task-execution-latest.json', pointer)
        if args.run:
            result.update(command(args, repo, state, common, task, lease, fd))
        else:
            result['outcome'] = 'EXECUTE'
            result['reason'] = 'Current coordinator owns this TODO task; implement, check, review and record completion in repository files.'
        return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer')
    parser.add_argument('--state-dir')
    parser.add_argument('--profile', default='')
    parser.add_argument('--tasks')
    parser.add_argument('--scope', choices=('repository', 'tasks'), default='repository',
                        help='Repository work or an explicitly named task-only filter.')
    parser.add_argument('--plan')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--owner-pid', type=int)
    parser.add_argument('--release', action='store_true')
    parser.add_argument('--timeout', type=float)
    parser.add_argument('--budget-seconds', type=float, help='Optional cumulative command walltime; not a model spending limit.')
    parser.add_argument('--source-path', action='append', default=[])
    parser.add_argument('--run', nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)
    try:
        if args.scope == 'tasks' and not args.tasks:
            raise ValueError('--scope tasks requires an explicit --tasks filter')
        if args.run is None and (args.timeout is not None or args.budget_seconds is not None):
            raise ValueError('--timeout and --budget-seconds bound --run commands only; use actual host limits for coordinator work')
        if args.run is not None and (not args.run or not args.apply or args.release):
            raise ValueError('--run requires --apply and a nonempty argv; cannot combine with --release')
        result = execute(args)
    except BlockingIOError:
        result = {'outcome': 'BUSY', 'reason': 'Repository or helper publication lock is held by a live operation.'}
    except PriorityDriftError as exc:
        result = dict(exc.status, outcome='PRIORITY_DRIFT', reason=str(exc))
    except (ValueError, OSError, subprocess.SubprocessError, SystemExit) as exc:
        result = {'outcome': 'ACTION_REQUIRED', 'reason': str(exc)}
    print(json.dumps(result, indent=2))
    return 0 if result['outcome'] in ('READY', 'EXECUTE', 'EXECUTED', 'RELEASED') else 1
