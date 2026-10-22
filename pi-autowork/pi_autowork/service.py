"""The systemd user service: pi-autowork@<repository name>.service.

One template serves every repository; the instance's env file names the repository
path. SIGINT is the runner's Ctrl+C: workers pause, finished work merges and the
next start resumes. Deliberate exits (1, 3, 4) do not restart; crashes and kills do.
A service never exits 3: it waits for another runner holding the repository to end.
"""
import json
import os
from pathlib import Path
import re
import subprocess
import time

from .common import die

ENV_NAMES = ('PI_AUTOWORK_PRIMARY', 'PI_AUTOWORK_FALLBACK', 'PI_AUTOWORK_TASK_TIMEOUT', 'PI_AUTOWORK_VERIFY_TIMEOUT',
             'PI_AUTOWORK_VALIDATE', 'PI_AUTOWORK_CHECK_SLOTS', 'PI_AUTOWORK_REVIEW', 'PI_AUTOWORK_MAX_RETRIES', 'PI_AUTOWORK_MAX_FAILURES',
             'PI_AUTOWORK_FAILURE_PAUSE', 'PI_AUTOWORK_STALL_AFTER', 'PI_AUTOWORK_LINK_PATHS',
             'PI_AUTOWORK_COOLDOWN', 'PI_AUTOWORK_BACKOFF', 'PI_AUTOWORK_MAX_RUNTIME',
             'PI_AUTOWORK_MIN_FREE_MB', 'PI_AUTOWORK_STATE_DIR', 'PI_AUTOWORK_TOOLSET',
             'PI_AUTOWORK_UPDATE_INTERVAL', 'PI_AUTOWORK_UPDATE_WAIT', 'PI_AUTOWORK_PLANNING_QUIET',
             'PI_AUTOWORK_PLAN_SETTLE', 'PI_AUTOWORK_PUSH')
# run() also accepts these through its workers argument and environment switches.
SETTING_NAMES = ENV_NAMES + ('PI_AUTOWORK_WORKERS', 'PI_AUTOWORK_ALLOW_HERMES', 'PI_AUTOWORK_NO_FALLBACK')

UNIT = """[Unit]
Description=pi-autowork for %i
Documentation=https://github.com/TrebuchetDynamics/autowork/blob/main/docs/cross-host.md#run-autowork-continuously
After=network-online.target

[Service]
WorkingDirectory=~
EnvironmentFile={env_dir}/%i.env
Environment=PI_AUTOWORK_ENV_FILE={env_dir}/%i.env
ExecStart=/bin/bash {script} --repo ${{PI_AUTOWORK_REPO}}
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGINT
TimeoutStopSec=150
SuccessExitStatus=130
# A crash (exit 70) or an OS error such as a full disk comes back; deliberate stops do not
# (1: failures the owner must see, 3: another runner holds it, 4: needs attention).
Restart=on-failure
RestartPreventExitStatus=1 3 4
RestartSec=60

[Install]
WantedBy=default.target
"""


def runner_record(state_root, repo):
    """(runner.json, its state folder) of the runner working on ``repo``, or ({}, None)."""
    for path in Path(state_root).glob('*/runner.json'):
        try:
            record = json.loads(path.read_text())
        except (OSError, ValueError):
            continue
        if record.get('repo') == str(repo):
            return record, path.parent
    return {}, None


def active_workers(folder):
    try:
        return int(json.loads((Path(folder) / 'status.json').read_text()).get('active_workers') or 0)
    except (OSError, ValueError, TypeError):
        return 0


def reload_in_place(systemctl, unit, state_root, repo, wait=None):
    """Reload a running runner without stopping its workers (TOOLSET-174-1d): SIGHUP to the
    main process, which re-executes in place at its next safe point. Returns (done, message);
    done is None when the runner predates reloading and must be restarted instead."""
    record, folder = runner_record(state_root, repo)
    if not record:
        # A runner re-executing (a reload or self-update a moment ago) has removed its record and
        # not written the new one yet (TOOLSET-191-0a: such a runner was restarted, pausing its
        # worker). The record it writes shows the current release and settings already.
        end = time.monotonic() + float(os.environ.get('PI_AUTOWORK_RECORD_WAIT', '10'))
        while not record and time.monotonic() < end:
            time.sleep(0.25)
            record, folder = runner_record(state_root, repo)
        if 'reloads' in record:
            return True, f'Reloaded {unit}; {active_workers(folder)} worker(s) kept running.'
    if 'reloads' not in record:
        return None, ''
    wait = float(os.environ.get('PI_AUTOWORK_RELOAD_WAIT', '150') if wait is None else wait)
    if subprocess.run([systemctl, '--user', 'kill', '--kill-whom=main', '--signal=SIGHUP', unit]).returncode:
        return False, f'could not signal {unit}'
    end = time.monotonic() + wait
    while time.monotonic() < end:
        now, _ = runner_record(state_root, repo)
        if now.get('pid') == record['pid'] and int(now.get('reloads') or 0) > int(record['reloads']):
            return True, f'Reloaded {unit}; {active_workers(folder)} worker(s) kept running.'
        if now.get('pid') and now['pid'] != record['pid']:
            return True, f'Restarted {unit} (its runner exited meanwhile); workers resume on the same attempt.'
        time.sleep(0.5)
    return False, (f'{unit} asked to reload, but it has not within {wait:g}s; it reloads once its running review '
                   f'or Pi job ends. To restart it now (workers pause and resume): autowork restart --stop-workers '
                   f'{unit[len("pi-autowork@"):-len(".service")]}')


def service_path(env):
    """This login's PATH without uv's temporary environments. Installing from the TUI, which
    runs inside `uv run`, saved them first in PATH; uv deletes them later, and the runner's
    `python3` then named a file that no longer existed."""
    caches = {Path.home() / '.cache/uv', Path(env.get('XDG_CACHE_HOME') or Path.home() / '.cache') / 'uv'}
    if env.get('UV_CACHE_DIR'):
        caches.add(Path(env['UV_CACHE_DIR']))
    caches = {cache.resolve() for cache in caches}
    kept = []
    for part in env.get('PATH', '').split(os.pathsep):
        path = Path(part).absolute()
        resolved = path.resolve()
        if (not part or not path.is_dir() or any(resolved.is_relative_to(cache) for cache in caches)
                or any(p.startswith('.tmp') for p in (*path.parts, *resolved.parts))):
            continue
        if part not in kept:
            kept.append(part)
    return os.pathsep.join(kept)


def _escape(*args):
    return subprocess.run(['systemd-escape', *args], capture_output=True, text=True).stdout.strip()


def run(action, *, repo, base, script, workers, state_root, hermes_jobs, argv0):
    env = os.environ
    config = env.get('XDG_CONFIG_HOME') or str(Path.home() / '.config')
    systemctl = env.get('PI_AUTOWORK_SYSTEMCTL', 'systemctl')
    unit_dir = Path(env.get('PI_AUTOWORK_UNIT_DIR') or f'{config}/systemd/user')
    env_dir = Path(env.get('PI_AUTOWORK_ENV_DIR') or f'{config}/pi-autowork')
    instance = Path(repo).name
    if not re.fullmatch(r'[A-Za-z0-9._-]+', instance):
        instance = _escape(instance)
    unit = f'pi-autowork@{instance}.service'
    env_file = env_dir / f'{instance}.env'
    try:
        owner = next((line.split('=', 1)[1] for line in env_file.read_text().splitlines()
                      if line.startswith('PI_AUTOWORK_REPO=')), '')
    except OSError:
        owner = ''
    if owner and owner != str(repo):
        die(2, f'{unit} already runs {owner}; two repositories cannot share the name {instance}. Remove that service first.')
    # Earlier releases named instances after the escaped path; replace such a unit.
    legacy = _escape('--path', str(repo))

    def ctl(*argv, quiet=False):
        return subprocess.run([systemctl, '--user', *argv],
                              stdout=subprocess.DEVNULL if quiet else None,
                              stderr=subprocess.DEVNULL if quiet else None).returncode

    def retire_legacy():
        if (env_dir / f'{legacy}.env').exists() or ctl('is-enabled', '--quiet', f'pi-autowork@{legacy}.service', quiet=True) == 0:
            ctl('disable', '--now', f'pi-autowork@{legacy}.service', quiet=True)
            (env_dir / f'{legacy}.env').unlink(missing_ok=True)
            print(f'Replaced the earlier unit pi-autowork@{legacy}.service.')

    if action == 'remove':
        if ctl('disable', '--now', unit):
            die(1, f'Could not stop {unit}')
        env_file.unlink(missing_ok=True)
        retire_legacy()
        print(f'Removed {unit}. Its state stays in {state_root}; kept worktrees and unmerged sessions remain at their recorded paths.')
        return 0
    if hermes_jobs and env.get('PI_AUTOWORK_ALLOW_HERMES', '0') != '1':
        die(4, f'A Hermes Autowork cron job already works on this repository:\n{hermes_jobs}\n'
               'Pause it, or install with --allow-hermes.')
    try:
        unit_dir.mkdir(parents=True, exist_ok=True)
        env_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        die(2, f'Cannot create {unit_dir} or {env_dir}')
    try:
        before = re.search(r'(?m)^ExecStart=.*$', (unit_dir / 'pi-autowork@.service').read_text()).group(0)
    except (OSError, AttributeError):
        before = None
    tmp = unit_dir / 'pi-autowork@.service.tmp'
    tmp.write_text(UNIT.format(env_dir=env_dir, script=script))
    os.replace(tmp, unit_dir / 'pi-autowork@.service')
    # The service sees this login's PATH (Pi, Node, Flutter and other tools); credentials stay in Pi.
    path = service_path(env)
    original = env.get('PATH', '').split(os.pathsep)
    dropped = [part for part in dict.fromkeys(original)
               if part not in path.split(os.pathsep) or original.count(part) > 1]
    if dropped:
        print('Dropped from the service PATH (missing, temporary or duplicate entries): '
              + ', '.join(part or '(empty entry)' for part in dropped))
    lines = [f'PI_AUTOWORK_REPO={repo}', f'PATH={path}']
    if env.get('PI_AUTOWORK_ALLOW_HERMES', '0') == '1':
        lines.append('PI_AUTOWORK_ALLOW_HERMES=1')
    if env.get('PI_AUTOWORK_NO_FALLBACK', '0') == '1':
        lines.append('PI_AUTOWORK_NO_FALLBACK=1')
    if workers != 8:
        lines.append(f'PI_AUTOWORK_WORKERS={workers}')
    lines += [f'{name}={env[name]}' for name in ENV_NAMES if env.get(name)]
    # A model chosen with `autowork model` survives a reinstall unless this one sets its own.
    try:
        kept = [line for line in env_file.read_text().splitlines()
                if line.split('=', 1)[0] in ('PI_AUTOWORK_PRIMARY', 'PI_AUTOWORK_FALLBACK')
                and not env.get(line.split('=', 1)[0])]
    except OSError:
        kept = []
    lines += kept
    old = os.umask(0o077)
    try:
        env_file.write_text('\n'.join(lines) + '\n')
    finally:
        os.umask(old)
    if ctl('daemon-reload'):
        die(1, 'systemctl --user daemon-reload failed')
    retire_legacy()  # stops it gracefully: finished work merges, the new unit resumes the rest
    if ctl('enable', unit, quiet=True):
        die(1, f'Could not enable {unit}')
    done = None
    if before == re.search(r'(?m)^ExecStart=.*$', UNIT.format(env_dir=env_dir, script=script)).group(0) and \
            ctl('is-active', '--quiet', unit, quiet=True) == 0:
        done, text = reload_in_place(systemctl, unit, state_root, repo)  # the same runner: keep its workers
        if text:
            print(text)
    if done is None and ctl('restart', unit):
        die(1, f'Could not start {unit}')
    print(f'Installed and started {unit} for {repo} (merges into {base}).')
    print(f'Runs: {script}')
    print(f"Logs: journalctl --user -u '{unit}' -f")
    print(f"Stop: systemctl --user stop '{unit}' (interrupts workers and merges finished work); "
          f'remove: {argv0} --remove-service --repo {repo}')
    linger = subprocess.run(['loginctl', 'show-user', env.get('USER', ''), '-p', 'Linger', '--value'],
                            capture_output=True, text=True).stdout.strip() if _has('loginctl') else ''
    if linger != 'yes':
        print('Note: user lingering is off, so the service stops at logout; enable it with: '
              f'loginctl enable-linger {env.get("USER", "")}')
    return 0


def _has(command):
    from shutil import which
    return which(command) is not None
