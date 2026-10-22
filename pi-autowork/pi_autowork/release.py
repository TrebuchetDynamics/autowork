"""Immutable process releases and the fleet checkpoint before a package update.

The shell calls ``launch`` before importing any runner module. Every descendant
inherits PI_AUTOWORK_TOOLSET, while PI_AUTOWORK_PACKAGE tracks the mutable update
source. Selection and pruning share a lock, held through exec so a selected release
cannot be pruned before its process environment identifies it. Linux /proc keeps
old releases alive even after a runner dies or re-executes and leaves children.

``check`` still requires schema compatibility and prefers a fleet-idle checkpoint;
its bounded wait and the update frequency are unchanged.
"""
import ast
from contextlib import contextmanager
import fcntl
import json
import time
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

STATE_FILE = 'pi-autowork/engine/parallel_state.py'


def _alive(pid):
    try:
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, TypeError):
        return False


def busy_runners(state_root, own):
    found = []
    for folder in sorted(Path(state_root).glob('*/')):
        if folder.resolve() == Path(own).resolve():
            continue
        try:
            status = json.loads((folder / 'status.json').read_text())
            runner = json.loads((folder / 'runner.json').read_text())
        except (OSError, ValueError):
            continue
        if _alive(runner.get('pid')) and int(status.get('in_flight') or 0) > 0:
            found.append(f"{Path(runner.get('repo', folder.name)).name} ({status['in_flight']} in flight)")
    return found


def schema(text, name, default):
    match = re.search(rf'^{name} = (.+)$', text, re.M)
    if not match:
        return default  # releases before the declaration wrote and read schema 1
    return ast.literal_eval(match[1].split('#')[0].strip())  # fetched text: parsed, never executed


def _git(toolset, *argv):
    # Bootstrap writes release worktrees before cli.py validates the target.
    # Never let inherited routing redirect those writes into a project checkout.
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    return subprocess.run(['git', '-C', str(toolset), *argv], env=env,
                          capture_output=True, text=True, timeout=120)


@contextmanager
def release_lock(state_root):
    root = Path(state_root).resolve() / 'releases'
    root.mkdir(parents=True, exist_ok=True)
    with open(root / '.lock', 'a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        yield root


def prune(root, keep=(), proc='/proc'):
    """Retain the newest two snapshots and releases used by processes.

    Unreadable environments of interpreter processes mean usage is unknown:
    retain everything. Ignore privileged system daemons and exited zombies;
    other users cannot select this user's private state root. A process with no command line
    is exiting (its memory is gone): it can select nothing, so it does not count.
    """
    used = set(map(str, keep))
    for process in Path(proc).glob('[0-9]*'):
        try:
            if process.stat().st_uid != os.getuid():
                continue
            for entry in (process / 'environ').read_bytes().split(b'\0'):
                if entry.startswith(b'PI_AUTOWORK_TOOLSET='):
                    used.add(os.fsdecode(entry.split(b'=', 1)[1]))
        except FileNotFoundError:
            continue  # exited while reading
        except PermissionError:
            try:
                command = (process / 'cmdline').read_bytes().split(b'\0')[0]
                state = (process / 'stat').read_text().rsplit(')', 1)[1].split()[0]
            except FileNotFoundError:
                continue
            except OSError:
                return
            # Exiting processes (no command line, state R or D) stopped every fourth prune while
            # processes churned, as under the full check: the release a runner left stayed on disk.
            if command and state != 'Z' and re.search(rb'(python[^/]*|bash|node|pi)$', command):
                return  # an interpreter whose environment we cannot inspect
        except OSError:
            return  # cannot prove unused
    snapshots = [p for p in root.iterdir() if re.fullmatch(r'[0-9a-f]{40,64}', p.name)
                 and (p / '.git').is_file()]
    snapshots.sort(key=lambda p: (p / '.git').stat().st_mtime_ns, reverse=True)
    for folder in snapshots[2:]:
        if str(folder) not in used:
            # Only our detached snapshots, including their disposable Python caches.
            _git(folder, 'worktree', 'remove', '--force', str(folder))


def _prepare(root, toolset, revision='HEAD'):
    resolved = _git(toolset, 'rev-parse', '--verify', revision + '^{commit}')
    sha = resolved.stdout.strip()
    if resolved.returncode or not re.fullmatch(r'[0-9a-f]{40,64}', sha):
        raise RuntimeError(f'cannot resolve a committed toolset release at {toolset}')
    target = root / sha
    if not target.exists():
        result = _git(toolset, 'worktree', 'add', '--detach', '-q', str(target), sha)
        if result.returncode:
            raise RuntimeError('cannot create toolset release: ' + result.stderr.strip())
    elif _git(target, 'rev-parse', 'HEAD').stdout.strip() != sha:
        raise RuntimeError(f'invalid toolset release at {target}')
    prune(root, keep=(target,))
    return target


def prepare(state_root, toolset, revision='HEAD'):
    """Materialize a commit without ever updating a previously selected directory."""
    with release_lock(state_root) as root:
        return _prepare(root, toolset, revision)


def installed_toolset(pi):
    """Bootstrap discovery without importing mutable runner modules."""
    listing = subprocess.run([pi, 'list'], capture_output=True, text=True, timeout=60).stdout
    found, source = [], ''
    for line in listing.splitlines():
        line = line.strip()
        if line.startswith('/'):
            path = Path(line)
            if (path / 'pi-autowork/pi_autowork/cli.py').is_file():
                found.append((source.split()[:1] != ['git:github.com/TrebuchetDynamics/autowork'], path))
        else:
            source = line
    return next((p for other, p in found if not other), found[0][1] if found else None)


def repository_option(argv):
    """The last --repo value, respecting options that consume the next token."""
    args, repo = iter(argv), None
    for arg in args:
        if arg in ('--repo', '--workers', '--interval', '--max-cycles', '--set-aside'):
            value = next(args, None)
            if arg == '--repo':
                repo = value
    return repo


def repository_identity(path, *, clean=False):
    """Probe the toplevel and common directory independently of inherited routing."""
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')} if clean else None
    try:
        result = subprocess.run(['git', '-C', str(path), 'rev-parse', '--path-format=absolute',
                                 '--show-toplevel', '--git-common-dir'],
                                env=env, capture_output=True, text=True, timeout=120)
    except (OSError, subprocess.SubprocessError):
        return None
    parts = result.stdout.splitlines()
    return tuple(map(os.path.realpath, parts)) if result.returncode == 0 and len(parts) == 2 else None


def startup_target(argv, script):
    """The configured target, even when option validation or Git is unavailable."""
    configured = repository_option(argv)
    if configured:
        return os.path.realpath(configured)
    identity = repository_identity(Path(script).parent, clean=True)
    toolset = identity and all((Path(identity[0]) / 'pi-autowork/engine' / name).is_file()
                              for name in ('owner_cycle.py', 'task_store.py'))
    return identity[0] if identity and not toolset else os.path.realpath(os.getcwd())


def repository_matches(start, identity):
    return bool(identity and repository_identity(start) == identity
                and repository_identity(identity[0], clean=True) == identity)


def bootstrap_settings(script, argv):
    """Read selection settings before pinning; keep CLI imports out of bootstrap."""
    start = repository_option(argv)
    if not start:
        top = _git(Path(script).parent, 'rev-parse', '--show-toplevel').stdout.strip()
        start = top if top and not (Path(top) / 'pi-autowork/pi_autowork/cli.py').is_file() else os.getcwd()
    repo = _git(start, 'rev-parse', '--show-toplevel').stdout.strip()
    if not repo:
        return
    name = Path(repo).name
    if not re.fullmatch(r'[A-Za-z0-9._-]+', name):
        name = subprocess.run(['systemd-escape', name], capture_output=True, text=True).stdout.strip()
    config = Path(os.environ.get('XDG_CONFIG_HOME') or Path.home() / '.config')
    path = Path(os.environ.get('PI_AUTOWORK_ENV_DIR') or config / 'pi-autowork') / f'{name}.env'
    try:
        values = dict(line.split('=', 1) for line in path.read_text().splitlines()
                      if '=' in line and not line.startswith('#'))
    except OSError:
        return
    if values.get('PI_AUTOWORK_REPO') not in (None, repo):
        return
    for key in ('PI_AUTOWORK_TOOLSET', 'PI_AUTOWORK_STATE_DIR'):
        if key in values and key not in os.environ:
            os.environ[key] = values[key]


def launch(component, script, argv):
    """Pin before cli.py imports the coordinator; children keep their inherited pin."""
    env = os.environ
    start = startup_target(argv, script)
    identity = repository_identity(start, clean=True)
    if (any(not shutil.which(tool) for tool in ('git', 'timeout', 'systemd-escape'))
            or not repository_matches(start, identity)):
        # No release worktree write before identity validation: the configured
        # target can itself be the toolset. The CLI owns refusal/stop reporting.
        env['PI_AUTOWORK_SCRIPT'] = script
        os.execv(sys.executable, [sys.executable, str(Path(component) / 'pi_autowork/cli.py'), *argv])
    bootstrap_settings(script, argv)
    reselect = env.pop('PI_AUTOWORK_RESELECT', '')
    package = env.get('PI_AUTOWORK_PACKAGE') if reselect != 'auto' else None
    selected = package if reselect else env.get('PI_AUTOWORK_TOOLSET')
    revision = env.pop('PI_AUTOWORK_NEXT_REVISION', 'HEAD')
    if not package or reselect:
        try:
            installed = installed_toolset(env.get('PI_BIN', 'pi'))
        except (OSError, subprocess.SubprocessError):
            installed = None
        fallback = Path(script).resolve().parent.parent
        if not (fallback / 'pi-autowork/pi_autowork/cli.py').is_file():
            fallback = Path(component).resolve().parent
        selected = Path(selected).resolve() if selected else installed or fallback
        env['PI_AUTOWORK_PACKAGE_INSTALLED'] = '1' if installed and selected == installed.resolve() else '0'
    selected = Path(selected).resolve()
    env['PI_AUTOWORK_PACKAGE'] = str(Path(package).resolve()) if package else str(selected)
    env['PI_AUTOWORK_SCRIPT'] = script  # stable launcher, never a prunable snapshot
    state_root = env.get('PI_AUTOWORK_STATE_DIR') or str(
        Path(env.get('XDG_STATE_HOME') or Path.home() / '.local/state') / 'pi-autowork')
    # These commands perform no engine work and need no snapshot.
    inspect_only = any(a in argv for a in ('--help', '-h', '--status', '--fleet', '--install-service', '--remove-service'))
    if inspect_only:
        env['PI_AUTOWORK_TOOLSET'] = str(selected)
        env['PI_AUTOWORK_COMPONENT'] = str(selected / 'pi-autowork')
        os.execv(sys.executable, [sys.executable, str(selected / 'pi-autowork/pi_autowork/cli.py'), *argv])
    with release_lock(state_root) as root:
        # An inherited snapshot is already immutable. Never consult the mutable
        # package for a worker/reviewer launched by an older engine.
        if selected.parent == root and re.fullmatch(r'[0-9a-f]{40,64}', selected.name):
            target = selected
        else:
            target = _prepare(root, selected, revision)
        env['PI_AUTOWORK_TOOLSET'] = str(target)
        env['PI_AUTOWORK_COMPONENT'] = str(target / 'pi-autowork')
        os.execv(sys.executable, [sys.executable, str(target / 'pi-autowork/pi_autowork/cli.py'), *argv])


def first_seen(state_root, rev, now):
    """When this release was first found waiting, shared by every runner."""
    path = Path(state_root) / 'toolset-update.json'
    try:
        record = json.loads(path.read_text())
        if record.get('rev') == rev:
            return float(record['since'])
    except (OSError, ValueError, KeyError, TypeError):
        pass
    try:
        path.write_text(json.dumps({'rev': rev, 'since': now}) + '\n')
    except OSError:
        pass
    return now


def check(state_root, own, toolset, wait=600, now=None, current_toolset=None):
    now = time.time() if now is None else now
    fetched = _git(toolset, 'fetch', '-q', 'origin', 'HEAD')
    if fetched.returncode:
        return dict(ok=False, reason='could not fetch the toolset: ' + fetched.stderr.strip()[:200])
    new_rev = _git(toolset, 'rev-parse', '--short', 'FETCH_HEAD').stdout.strip()
    if new_rev and new_rev == _git(toolset, 'rev-parse', '--short', 'HEAD').stdout.strip():
        return dict(ok=False, current=True, reason='already at the newest release')
    shown = _git(toolset, 'show', f'FETCH_HEAD:{STATE_FILE}')
    if shown.returncode:
        return dict(ok=False, reason=f'the new release {new_rev} has no {STATE_FILE}')
    try:
        current = schema((Path(current_toolset or toolset) / STATE_FILE).read_text(), 'STATE_SCHEMA', 1)
        reads = schema(shown.stdout, 'STATE_SCHEMA_READS', (1,))
    except (OSError, SyntaxError, ValueError, TypeError):
        return dict(ok=False, reason='could not read the state schema declarations')
    if current not in tuple(reads):
        return dict(ok=False, reason=f'release {new_rev} cannot read this state (schema {current}; it reads {list(reads)})')
    busy = busy_runners(state_root, own)
    if busy:
        left = wait - (now - first_seen(state_root, new_rev, now))
        if left > 0:
            return dict(ok=False, reason=f'other runners have work in flight: {", ".join(busy)}; '
                                         f'updating to {new_rev} anyway in {max(1, round(left / 60))} min')
        return dict(ok=True, new_rev=new_rev, schema=current,
                    note=f'updating to {new_rev} with work in flight ({", ".join(busy)}); '
                         'existing children keep their release')
    return dict(ok=True, new_rev=new_rev, schema=current)


def main(argv):
    if len(argv) >= 3 and argv[0] == 'launch':
        try:
            launch(argv[1], argv[2], argv[3:])
        except (OSError, RuntimeError, subprocess.SubprocessError) as exc:
            print(f'pi-autowork: {exc}', file=sys.stderr)
            return 2
    if len(argv) == 4 and argv[0] == 'check':
        result = check(*argv[1:])
        print(json.dumps(result))
        return 0 if result['ok'] else 1
    print('usage: release.py check STATE_ROOT OWN_STATE_DIR TOOLSET | launch COMPONENT SCRIPT [ARGS...]', file=sys.stderr)
    return 2


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
