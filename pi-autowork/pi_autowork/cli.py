"""pi-autowork command line: options, repository and toolset resolution, status,
dry run, requests, the fleet view and the service; then the coordinator loop.

`scripts/pi-autowork.sh` only finds this component and runs it. After resolving the
toolset release (PI_AUTOWORK_TOOLSET, the package Pi loads, or the script's own
checkout), a run continues in that release's component, so the runner, workers and
engine always come from one release.
"""
import fcntl
import glob
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import health, pi_runtime, service, worker  # noqa: E402
from pi_autowork.common import LOG, die, dirty, git, git_ok, lifecycle, model_of, provider_of, push_guard  # noqa: E402
from pi_autowork.coordinator import Coordinator  # noqa: E402

USAGE = """Usage: pi-autowork.sh [options]

Runs Autowork through Pi until stopped: the toolset's Parallel
Autowork engine runs up to N tasks at once (default 8), each Pi worker in its own Git
worktree, and integrates verified results one at a time. Targets the Git repository
of the current directory (or of this script, when it was copied into a repository),
which must have its main branch checked out and a TODO.md.

Each session builds on an integration branch (pi-autowork/<session>) in its own
worktree; after each closed task, and when the queue drains or the runner stops, the
session is merged into the main branch (Pi resolves conflicts with newer main commits)
and main is pushed to its upstream, fast-forward only. Workers never push.

Options:
  --once               Run at most one task, then exit
  --until-empty        Exit when no runnable task remains
  --dry-run            Show what would run; change nothing
  --status             Show the session, budget and each task's state; change nothing
  --fleet              One line per pi-autowork runner on this machine: service, health
                       (working, blocked, stalled, paused, not running) and root blockers
  --set-aside TASK     Ask this repository's runner to retire TASK's stuck slot (held with
                       no attempt left, or merged with a changed TODO entry); its work is
                       kept under renamed branches and the task runs fresh
  --repo PATH          Use the repository at PATH
  --workers N          Tasks run at once, 1-8 (default 8; PI_AUTOWORK_WORKERS); the engine's
                       memory and load gate starts fewer when the machine is busy
  --interval SECONDS   Longest idle wait (default 60); a change to TODO.md, goals.json,
                       BLOCKERS.md or the main branch ends it within seconds
  --max-cycles N       Start at most N Pi workers, then finish
  --no-fallback        Never switch to the fallback model
  --allow-hermes       Run although a Hermes Autowork cron job targets this repository
  --install-service    Install and start a systemd user service running this for the repository
  --remove-service     Stop and remove the repository's service
  --help               Show this help

Environment (optional):
  PI_AUTOWORK_PRIMARY       provider/model (default openai-codex/gpt-6.1-sol)
  PI_AUTOWORK_FALLBACK      provider/model (default openrouter/deepseek/deepseek-v4.1-flash)
  PI_AUTOWORK_WORKERS       default for --workers (default 8)
  PI_AUTOWORK_INFER_TOUCHES 0 to stop proposing Touches: for tasks that lack them
  PI_AUTOWORK_UPDATE_INTERVAL seconds between idle `pi update` checks of the toolset package;
                            new toolset code restarts the runner (default 120; 0 off)
  PI_AUTOWORK_UPDATE_WAIT   seconds a new release waits for no runner to have work in
                            flight before it is installed anyway (default 600)
  PI_AUTOWORK_TASK_TIMEOUT  seconds per worker (default 5400)
  PI_AUTOWORK_VERIFY_TIMEOUT seconds for verifying one task (default 1800)
  PI_AUTOWORK_VALIDATE      command run before the Pi reviewer on every integrated task
  PI_AUTOWORK_REVIEW        0 to skip the Pi reviewer (PI_AUTOWORK_VALIDATE alone decides)
  PI_AUTOWORK_MAX_RETRIES   provider/crash retries per Pi run (default 3)
  PI_AUTOWORK_MAX_FAILURES  consecutive failed tasks before stopping (default 3); a service
                            pauses new tasks for PI_AUTOWORK_FAILURE_PAUSE seconds (3600) instead
  PI_AUTOWORK_CLAIM_IDLE    adopt another session's in_progress claim after this many seconds
                            with no task, branch or worktree change and no live agent
                            (default 21600; 0 never adopts)
  PI_AUTOWORK_LINK_PATHS    comma-separated gitignored paths (say vendor/sdk) to mirror from the
                            main checkout into each task and review worktree with hard links;
                            only paths Git ignores there; cooperative, not write-protected
  PI_AUTOWORK_PLANNING_QUIET seconds uncommitted planning (TODO.md, goals.json, BLOCKERS.md,
                            the archive) must rest before the runner commits it so its merge
                            can land; any other uncommitted file keeps the merge pending (600)
  PI_AUTOWORK_PLAN_SETTLE   seconds a plan change must be quiet before an idle runner reads it
                            (default 3)
  PI_AUTOWORK_PUSH          0 keeps merged main local; otherwise it is pushed to its upstream
  PI_AUTOWORK_STALL_AFTER   seconds with nothing running while work waits before the runner
                            announces STALLED with its root blockers (default 1800)
  PI_AUTOWORK_COOLDOWN      seconds on the fallback before trying the primary again (default 1800)
  PI_AUTOWORK_BACKOFF       first retry delay in seconds, doubling to 600 (default 30)
  PI_AUTOWORK_MAX_RUNTIME   stop starting tasks after this many seconds (default 0, unlimited)
  PI_AUTOWORK_MAX_COST      USD limit on reported cost within the budget window (default 0, unlimited)
  PI_AUTOWORK_COST_WINDOW   budget window in hours, counted across restarts (default 24)
  PI_AUTOWORK_MIN_FREE_MB   memory one more worker needs; twice it must be available (default 3000)
  PI_AUTOWORK_TMP_STALE     remove /tmp scratch untouched this many seconds (default 7200, 0 off)
  PI_AUTOWORK_STATE_DIR     state root (default ${XDG_STATE_HOME:-~/.local/state}/pi-autowork)
  PI_AUTOWORK_TOOLSET       autowork checkout or Pi package path (default: auto)
  PI_AUTOWORK_ALLOW_HERMES  1 to run although a Hermes Autowork cron job targets this repository
  PI_BIN                    Pi command (default pi)

Exit status: 0 done, 1 stopped on a failure or blocker, 2 setup error,
3 another runner holds this repository, 4 needs attention, 130 interrupted.
"""
COMPONENT = Path(__file__).resolve().parents[1]


def is_toolset(path):
    return (Path(path) / 'skills/autowork/scripts/owner_cycle.py').is_file() and \
        (Path(path) / 'skills/docs-sync/scripts/goals.py').is_file()


PI_SOURCE = 'git:github.com/TrebuchetDynamics/autowork'


def installed_toolset(pi):
    """The autowork package Pi loads, from `pi list`: the one installed from PI_SOURCE, else
    the first other package that is an Autowork toolset (Pi lists a source, then its path).
    The package installed under the old hermes-toolset name came first in the list and
    kept every runner on it after the renamed one was installed."""
    try:
        listing = subprocess.run([pi, 'list'], capture_output=True, text=True, timeout=60).stdout
    except (OSError, subprocess.SubprocessError):
        return None
    found, source = [], ''
    for line in listing.splitlines():
        line = line.strip()
        if line.startswith('/'):
            if is_toolset(line):
                found.append((source.split()[:1] != [PI_SOURCE], str(Path(line).resolve())))
        else:
            source = line
    return next((path for other, path in found if not other), found[0][1] if found else None)


def parse(argv):
    opts = dict(mode='continuous', repo=None, interval='60', max_cycles='0', service=None, status=False,
                set_aside=None, fleet=False, dry_run=False, workers=os.environ.get('PI_AUTOWORK_WORKERS', '8'))
    args = list(argv)
    while args:
        arg = args.pop(0)
        def value(name):
            if not args:
                print(f'pi-autowork.sh: {arg} needs {name}', file=sys.stderr)
                sys.exit(2)
            return args.pop(0)
        if arg == '--once':
            opts['mode'] = 'once'
        elif arg == '--until-empty':
            opts['mode'] = 'until-empty'
        elif arg == '--dry-run':
            opts['dry_run'] = True
        elif arg == '--status':
            opts['status'] = True
        elif arg == '--fleet':
            opts['fleet'] = True
        elif arg == '--set-aside':
            opts['set_aside'] = value('a task ID')
        elif arg == '--repo':
            opts['repo'] = value('a path')
        elif arg == '--workers':
            opts['workers'] = value('a number')
        elif arg == '--interval':
            opts['interval'] = value('seconds')
        elif arg == '--max-cycles':
            opts['max_cycles'] = value('a number')
        elif arg == '--no-fallback':
            os.environ['PI_AUTOWORK_NO_FALLBACK'] = '1'
        elif arg == '--allow-hermes':
            os.environ['PI_AUTOWORK_ALLOW_HERMES'] = '1'
        elif arg == '--install-service':
            opts['service'] = 'install'
        elif arg == '--remove-service':
            opts['service'] = 'remove'
        elif arg in ('-h', '--help'):
            print(USAGE, end='')
            sys.exit(0)
        else:
            print(f'Unknown option: {arg}\n', file=sys.stderr)
            print(USAGE, end='', file=sys.stderr)
            sys.exit(2)
    claim_idle = os.environ.get('PI_AUTOWORK_CLAIM_IDLE', '21600')
    for item in (opts['interval'], opts['max_cycles'], opts['workers'], claim_idle):
        if not re.fullmatch(r'[0-9]+', item):
            print(f'Expected a whole number, got: {item}', file=sys.stderr)
            sys.exit(2)
    opts.update(interval=int(opts['interval']), max_cycles=int(opts['max_cycles']), workers=int(opts['workers']),
                claim_idle=int(claim_idle))
    if not 1 <= opts['workers'] <= 8:
        die(2, '--workers must be 1 to 8')
    if opts['mode'] == 'once':
        opts['workers'] = 1
    return opts


def hermes_jobs(repo):
    home = os.environ.get('PI_AUTOWORK_HERMES_HOME') or str(Path.home() / '.hermes')
    repo = os.path.realpath(repo)
    found = []
    for path in [os.path.join(home, 'cron/jobs.json')] + sorted(glob.glob(os.path.join(home, 'profiles/*/cron/jobs.json'))):
        try:
            data = json.load(open(path))
        except (OSError, ValueError):
            continue
        jobs = data.get('jobs', []) if isinstance(data, dict) else data
        for job in jobs if isinstance(jobs, list) else []:
            if not isinstance(job, dict) or not job.get('workdir'):
                continue
            if os.path.realpath(job['workdir']) != repo or job.get('enabled') is False:
                continue
            if job.get('paused_at') or job.get('state') == 'paused':
                continue
            text = ' '.join([str(job.get('skill') or ''), *map(str, job.get('skills') or []), str(job.get('prompt') or '')])
            if 'autowork' in text.lower():
                relative = os.path.relpath(path, home).split(os.sep)
                profile = relative[1] if relative[0] == 'profiles' else 'default'
                found.append(f"{profile}: {job.get('name') or job.get('id')}")
    return '\n'.join(found)


def settings_file(repo):
    """The repository's settings: the env file `--install-service` writes, read by every
    launcher (systemd, `tx autowork`, a terminal), so settings follow the repository."""
    config = os.environ.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    name = Path(repo).name
    if not re.fullmatch(r'[A-Za-z0-9._-]+', name):
        name = subprocess.run(['systemd-escape', name], capture_output=True, text=True).stdout.strip()
    return Path(os.environ.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork') / f'{name}.env'


def load_repo_settings(repo):
    """PI_AUTOWORK_* settings from the repository's settings file; the environment wins."""
    try:
        lines = settings_file(repo).read_text().splitlines()
    except OSError:
        return
    values = dict(line.split('=', 1) for line in lines if '=' in line and not line.startswith('#'))
    if values.get('PI_AUTOWORK_REPO') and values['PI_AUTOWORK_REPO'] != str(repo):
        return  # another repository with the same name owns this file
    for key, value in values.items():
        if key.startswith('PI_AUTOWORK_') and key != 'PI_AUTOWORK_REPO' and key not in os.environ:
            os.environ[key] = value


def in_catalog(pi, model):
    try:
        out = subprocess.run([pi, '--list-models', model_of(model)], capture_output=True, text=True, timeout=120).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    return any(line.split()[:2] == [provider_of(model), model_of(model)] for line in out.splitlines())


def main(argv):
    script = os.environ.get('PI_AUTOWORK_SCRIPT') or str(Path(__file__).resolve().parents[2] / 'scripts/pi-autowork.sh')
    if argv[:1] in (['--worker'], ['--verify']):
        return worker.main(argv)
    opts = parse(argv)
    pi = os.environ.get('PI_BIN', 'pi')
    for tool in ('git', 'timeout', 'systemd-escape'):
        if not shutil.which(tool):
            die(2, f'Missing required command: {tool}')
    if not shutil.which(pi):
        die(2, f'Pi not found ({pi}). Install Pi, then: pi install git:github.com/TrebuchetDynamics/autowork')
    state_root = os.environ.get('PI_AUTOWORK_STATE_DIR') or \
        os.path.join(os.environ.get('XDG_STATE_HOME') or str(Path.home() / '.local/state'), 'pi-autowork')
    if opts['fleet']:
        print(health.render(health.fleet(state_root)))
        return 0

    # Repository
    def script_repo():
        top = git(Path(script).parent, 'rev-parse', '--show-toplevel')
        return None if not top or is_toolset(top) else top  # the shipped copy targets the caller's repository
    start = opts['repo'] or script_repo() or os.getcwd()
    repo = git(start, 'rev-parse', '--show-toplevel')
    if not repo:
        die(2, f'Not inside a Git repository: {start}')
    if not (Path(repo) / 'TODO.md').is_file():
        die(2, f'No TODO.md at {repo}. Create the backlog first, for example with /docs_sync in Pi.')
    base = git(repo, 'symbolic-ref', '--short', '-q', 'HEAD')
    if not base:
        die(2, f'{repo} has a detached HEAD; check out its main branch first.')
    default = (git(repo, 'symbolic-ref', '--short', '-q', 'refs/remotes/origin/HEAD') or '').removeprefix('origin/')
    if base not in (default or 'main', 'main', 'master'):
        die(2, f'{repo} is on branch {base}. Run the runner from the checkout of the main branch'
               f'{f" ({default})" if default else ""}; task work happens in worktrees and is merged back there.')
    git_common = git(repo, 'rev-parse', '--path-format=absolute', '--git-common-dir')
    load_repo_settings(repo)
    # Settings read while parsing options, before the repository was known.
    for key, name in (('workers', 'PI_AUTOWORK_WORKERS'), ('claim_idle', 'PI_AUTOWORK_CLAIM_IDLE')):
        if key == 'workers' and '--workers' in argv:
            continue
        value = os.environ.get(name)
        if value is not None:
            if not re.fullmatch(r'[0-9]+', value):
                die(2, f'Expected a whole number, got: {value}')
            opts[key] = int(value)
    if not 1 <= opts['workers'] <= 8:
        die(2, '--workers must be 1 to 8')
    if opts['mode'] == 'once':
        opts['workers'] = 1

    # Toolset: prefer the package Pi has installed, so every run uses what Pi loads.
    skill_args = []
    if os.environ.get('PI_AUTOWORK_TOOLSET'):
        if not is_toolset(os.environ['PI_AUTOWORK_TOOLSET']):
            die(2, f'PI_AUTOWORK_TOOLSET is not an Autowork checkout: {os.environ["PI_AUTOWORK_TOOLSET"]}')
        toolset = str(Path(os.environ['PI_AUTOWORK_TOOLSET']).resolve())
        if installed_toolset(pi) != toolset:
            skill_args = ['--skill', f'{toolset}/adapters/skills/git-commit-push']
    elif (found := installed_toolset(pi)):
        toolset = found
    elif is_toolset(Path(script).resolve().parents[1]):
        toolset = str(Path(script).resolve().parents[1])
        skill_args = ['--skill', f'{toolset}/adapters/skills/git-commit-push']
        print(f'pi-autowork: autowork is not installed in Pi; using {toolset}. Install the package: '
              'pi install git:github.com/TrebuchetDynamics/autowork', file=sys.stderr, flush=True)
    else:
        die(2, 'Autowork not found. Install it in Pi (pi install git:github.com/TrebuchetDynamics/autowork) '
               'or set PI_AUTOWORK_TOOLSET.')
    component = Path(toolset) / 'pi-autowork'
    if not (component / 'pi_autowork/cli.py').is_file():
        die(2, f'{toolset} has no pi-autowork component; update the toolset '
               '(pi update git:github.com/TrebuchetDynamics/autowork)')
    if component.resolve() != COMPONENT:
        # Continue in the resolved release's own component: one release per run.
        os.environ['PI_AUTOWORK_SCRIPT'] = script
        os.execv(sys.executable, [sys.executable, str(component / 'pi_autowork/cli.py'), *argv])
    os.environ.update(PI_AUTOWORK_SKILL_ARGS=' '.join(skill_args), PI_AUTOWORK_REPO=repo,
                      PI_AUTOWORK_COMPONENT=str(component), PI_AUTOWORK_SCRIPT=script)
    toolset_rev = git(toolset, 'rev-parse', '--short', 'HEAD') or 'unknown'
    settings = pi_runtime.Settings(state_root)
    if not opts['status'] and not opts['service']:
        if not in_catalog(pi, settings.primary):
            die(2, f"Primary model {settings.primary} is not in Pi's model catalog (pi --list-models).")
        if settings.fallback_enabled and not in_catalog(pi, settings.fallback):
            die(2, f"Fallback model {settings.fallback} is not in Pi's model catalog; fix PI_AUTOWORK_FALLBACK "
                   'or use --no-fallback.')
    jobs = hermes_jobs(repo)
    state = Path(state_root) / hashlib.sha256(git_common.encode()).hexdigest()[:16]

    # A request for the running runner, which owns the engine lease; nothing else changes.
    if opts['set_aside']:
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9._-]*', opts['set_aside']):
            die(2, f'Not a task ID: {opts["set_aside"]}')
        try:
            (state / 'requests').mkdir(parents=True, exist_ok=True)
        except OSError:
            die(2, f'Cannot create {state / "requests"}')
        (state / 'requests' / f'set-aside-{opts["set_aside"]}').touch()
        print(f'Requested: set aside {opts["set_aside"]}. The runner for {repo} acts on it within one cycle; see its log.')
        return 0
    if opts['service']:
        if opts['dry_run']:
            die(2, '--dry-run cannot be combined with --install-service or --remove-service')
        return service.run(opts['service'], repo=repo, base=base, script=script, workers=opts['workers'],
                           state_root=state_root, hermes_jobs=jobs, argv0=script)

    settings = pi_runtime.Settings(state)
    if opts['dry_run']:
        os.environ['PI_AUTOWORK_DRY_RUN'] = '1'
        settings.dry_run = True
    if opts['status'] or opts['dry_run']:
        summarize(repo, base, toolset, toolset_rev, skill_args, opts, settings, state)
        if jobs:
            allowed = os.environ.get('PI_AUTOWORK_ALLOW_HERMES', '0') == '1'
            print('Hermes Autowork cron jobs target this repository'
                  + (' (allowed; the engine lease keeps them apart)' if allowed else ' (the runner would refuse)')
                  + ':\n' + jobs)
        status_view(repo, base, toolset, state)
        if not opts['status']:
            print('Dry run: nothing was changed.')
        return 0
    if jobs and os.environ.get('PI_AUTOWORK_ALLOW_HERMES', '0') != '1':
        die(4, 'A Hermes Autowork cron job already works on this repository; two agents would write at once:\n'
               f'{jobs}\nPause it, or set PI_AUTOWORK_ALLOW_HERMES=1 (the engine lease then lets only one of them '
               'work at a time).')
    try:
        for part in ('sessions', 'runs', 'worktrees'):
            (state / part).mkdir(parents=True, exist_ok=True)
    except OSError:
        die(2, f'Cannot create state directory {state}')
    LOG.state = state
    lock = open(state / 'lock', 'a')
    for _ in range(150):  # a coordinator that was just killed can leave a helper holding it briefly
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            break
        except BlockingIOError:
            import time
            time.sleep(0.1)
    else:
        try:
            owner = json.loads((state / 'runner.json').read_text())
            owner = f"PID {owner['pid']}, started {owner['started']}"
        except (OSError, ValueError, KeyError):
            owner = 'unknown owner'
        if not (os.environ.get('INVOCATION_ID') and opts['mode'] == 'continuous'):
            die(3, f'Another pi-autowork runner holds {repo} ({owner}).')
        # A service exiting 3 is never restarted, so it would stay down after the other runner
        # (an old tmux runner, a manual run) ends; wait for the lock instead. Stopping the unit
        # interrupts the wait.
        LOG.warn(f'Another pi-autowork runner holds {repo} ({owner}); waiting for it to exit.')
        try:
            fcntl.flock(lock, fcntl.LOCK_EX)
        except KeyboardInterrupt:
            print('Stopped while waiting for the other runner.', flush=True)
            return 130
        LOG.say('The other runner exited; starting.')
    (state / 'runner.json').write_text(json.dumps({
        'pid': os.getpid(), 'started': datetime.now().astimezone().isoformat(timespec='seconds'), 'repo': repo}))
    push_guard()
    os.environ.update(PI_BIN=pi)
    summarize(repo, base, toolset, toolset_rev, skill_args, opts, settings, state)
    cfg = dict(repo=repo, base=base, toolset=toolset, toolset_rev=toolset_rev, state=str(state),
               state_root=state_root, git_common=git_common, script=script, argv=argv, pi=pi,
               skill_args=skill_args, mode=opts['mode'], workers=opts['workers'], interval=opts['interval'],
               max_cycles=opts['max_cycles'], claim_idle=opts['claim_idle'])
    return Coordinator(cfg).run()


def summarize(repo, base, toolset, rev, skill_args, opts, settings, state):
    print('PI AUTOWORK')
    print(f'Repository: {repo} (merges into {base})')
    print(f'Toolset:    {toolset} at {rev} ({"not a Pi package" if skill_args else "Pi package"})')
    print(f'Engine:     Parallel Autowork, up to {opts["workers"]} worker(s)')
    ready = lambda model: 'ready' if pi_runtime.auth_ready(settings, model) else 'not ready'
    print(f'Primary:    {settings.primary} ({ready(settings.primary)})')
    print(f'Fallback:   {settings.fallback} ({ready(settings.fallback)})' if settings.fallback_enabled
          else 'Fallback:   disabled')
    if settings.max_cost != '0':
        print(f'Budget:     ${pi_runtime.spent(settings)} of ${settings.max_cost} in the last {settings.window_text} h')
    print(f'Mode:       {opts["mode"]}; state in {state}; new worktrees in {repo}/.worktrees', flush=True)


def status_view(repo, base, toolset, state):
    lock = state / 'lock'
    running = False
    if lock.exists():
        with open(lock, 'a') as handle:
            try:
                fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
                fcntl.flock(handle, fcntl.LOCK_UN)
            except BlockingIOError:
                running = True
    if running:
        try:
            owner = json.loads((state / 'runner.json').read_text())
            print(f"Runner:     running (PID {owner['pid']}, since {owner['started']})")
        except (OSError, ValueError, KeyError):
            print('Runner:     running ()')
    else:
        print('Runner:     not running')
    view = repo
    try:
        session = json.loads((state / 'session.json').read_text())
        branch, path = session['branch'], session['path']
        if not git_ok(repo, 'show-ref', '--verify', '-q', f'refs/heads/{branch}') or not Path(path).is_dir():
            raise KeyError
        print(f'Session:    {branch}, {git(repo, "rev-list", "--count", f"{base}..{branch}")} commit(s) not yet '
              f'merged into {base}')
        view = path
    except (OSError, ValueError, KeyError):
        print(f'Session:    none; a new integration branch would start from {base}')
    if dirty(repo):
        print(f'Note:       {repo} has uncommitted changes; the final merge stops if it would touch them')
    out = subprocess.run([sys.executable, str(Path(toolset) / 'skills/autowork/scripts/owner_cycle.py'), view,
                          '--parallel-status', '--json'], capture_output=True, text=True).stdout
    try:
        snapshot = json.loads(out)
    except ValueError:
        return
    print(f"Workers:    {snapshot.get('active_workers') or 0} running; {snapshot.get('completed') or 0} done, "
          f"{snapshot.get('failed') or 0} failed, {snapshot.get('integration_queue') or 0} awaiting integration")
    try:
        record = json.loads((state / 'status.json').read_text())
        line = f"Health:     {record['state']} since {datetime.fromtimestamp(int(record['since'])):%Y-%m-%d %H:%M}"
        roots = [r for r in record.get('roots') or [] if r.get('kind') in health.NEEDS_PERSON][:3]
        if roots:
            line += '; blocked by ' + '; '.join(
                f"{' '.join(str(r['id']).split())[:60]} ({r['kind']}, holds {r['blocks']})" for r in roots)
        print(line)
    except (OSError, ValueError, KeyError):
        pass
    for row in (snapshot.get('tasks') or [])[:40]:
        print(f"  {str(row.get('task')):<12} {lifecycle(row.get('state') or ''):<12} "
              f"{row.get('reason') or row.get('blocked_reason') or ''}")


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
