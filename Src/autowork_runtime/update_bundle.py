"""Explicit bundle updates and verified managed-checkout recovery for Hermes profiles."""
import argparse
import contextlib
import datetime
import fcntl
import hashlib
import json
import os
import re
from pathlib import Path
import shutil
import signal
import subprocess
import stat
import sys
import tempfile
import time

UPSTREAM = 'https://github.com/TrebuchetDynamics/autowork.git'
PLUGIN = 'autowork'
HOST_REFRESH_TIMEOUT_S = 300
HOST_ITEMS = ('autowork', 'tx', 'claude', 'codex')


def refresh_hosts(source):
    """Use the updated release's installer once; host failures never fail Hermes.

    Incremental JSONL receipts survive a timeout. Kill the whole installer process
    group on expiry, so a native CLI cannot keep installing after we report it.
    """
    rows = {}
    status, code = 'unavailable', None
    try:
        if not (source / 'install.sh').is_file():
            return [{'item': item, 'status': status, 'exit': code} for item in HOST_ITEMS]
        with tempfile.TemporaryDirectory(prefix='autowork-host-update-') as directory:
            report = Path(directory) / 'items.jsonl'
            env = dict(os.environ, AUTOWORK_INSTALL_REPORT=str(report), NO_COLOR='1')
            with subprocess.Popen(['bash', str(source / 'install.sh'), '--full', '--skip', 'hermes,pi', '-q'],
                                  cwd=source, stdin=subprocess.DEVNULL, env=env,
                                  start_new_session=True) as child:
                try:
                    code = child.wait(timeout=HOST_REFRESH_TIMEOUT_S)
                    status = 'failed' if code else 'unreported'
                except subprocess.TimeoutExpired:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                    status = 'timeout'
            if report.exists():
                for line in report.read_text(errors='replace').splitlines():
                    try:
                        row = json.loads(line)
                    except ValueError:
                        continue  # interrupted last write; account for it below
                    if (isinstance(row, dict) and row.get('item') in HOST_ITEMS
                            and row.get('status') in ('installed', 'failed', 'skipped')
                            and (row.get('exit') is None or type(row['exit']) is int)):
                        rows[row['item']] = {k: row.get(k) for k in ('item', 'status', 'exit')}
    except (OSError, subprocess.SubprocessError):
        status, code = 'unavailable', None
    return [rows.get(item, {'item': item, 'status': status, 'exit': code}) for item in HOST_ITEMS]


def plugin_dir(home):
    return home / 'plugins' / PLUGIN


class GitFailure(ValueError):
    def __init__(self, repo, args, code):
        self.code = code
        super().__init__(f'Git {args[0]} failed in {repo}; inspect the checkout and retry (exit {code})')


# A fetch that stalls below 1 KB/s for 30 s aborts instead of holding the update for the
# whole timeout; a normal fetch of a profile checkout takes seconds.
STALL = {'GIT_CONFIG_COUNT': '2', 'GIT_CONFIG_KEY_0': 'http.lowSpeedLimit', 'GIT_CONFIG_VALUE_0': '1000',
         'GIT_CONFIG_KEY_1': 'http.lowSpeedTime', 'GIT_CONFIG_VALUE_1': '30'}
# A fetch never waits on a person either: a url.insteadOf rewrite to SSH sat at a passphrase or
# host-key prompt, where the speed limit never applies, for the whole timeout.
UNATTENDED = {'GIT_TERMINAL_PROMPT': '0', 'SSH_ASKPASS_REQUIRE': 'never'}
SSH_OPTIONS = '-o BatchMode=yes -o ConnectTimeout=15'


def fetch_env():
    ssh = os.environ.get('GIT_SSH_COMMAND') or 'ssh'
    return {**os.environ, **STALL, **UNATTENDED, 'GIT_SSH_COMMAND': f'{ssh} {SSH_OPTIONS}'}


def git(repo, *args):
    env = fetch_env() if args[:1] == ('fetch',) else None
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=120, env=env,
                            stdin=subprocess.DEVNULL)
    if result.returncode:
        raise GitFailure(repo, args, result.returncode)
    return result.stdout


def fetch(repo, *args):
    """Fetch once more after a stall or failure: one network stall failed the Hermes update of
    every profile, and the retry a moment later fetched in two seconds."""
    try:
        return git(repo, 'fetch', *args)
    except (GitFailure, subprocess.TimeoutExpired):
        return git(repo, 'fetch', *args)


def is_ancestor(repo, before, after):
    try:
        git(repo, 'merge-base', '--is-ancestor', before, after)
        return True
    except GitFailure as error:
        if error.code == 1:
            return False
        raise


def managed_evidence(repo, profiles, upstream, *, admitted_head=None):
    """Capture install ownership and trusted HEAD evidence BEFORE fetch changes refs."""
    owners = [(name, home) for name, home in profiles if plugin_dir(home) == repo
              and not plugin_dir(home).is_symlink()]
    if len(owners) != 1:
        raise ValueError(f'Unrecognized/shared source {repo}; recovery requires a canonical managed plugin checkout')
    name, home = owners[0]
    if any(p.is_symlink() or p.stat().st_uid != os.getuid() for p in (repo, repo.parent, home)):
        raise ValueError(f'Unsafe managed checkout ownership: {repo}')
    if (not (repo / '.git').is_dir() or (repo / '.git').is_symlink()
            or (repo / '.git/objects/info/alternates').exists()):
        raise ValueError(f'Linked/shared Git directory cannot be recovered: {repo}')
    for folder, directories, files in os.walk(repo):
        for entry in directories + files:
            path = Path(folder) / entry
            if path.lstat().st_uid != os.getuid():
                raise ValueError(f'Uncertain checkout file ownership in {repo}')
            if path.is_relative_to(repo / '.git') and path.is_symlink():
                raise ValueError(f'Shared/symlinked Git storage cannot be recovered: {path}')
    if len([line for line in git(repo, 'worktree', 'list', '--porcelain').splitlines()
            if line.startswith(b'worktree ')]) != 1:
        raise ValueError(f'Extra linked worktrees consume {repo}; reconcile them before recovery')
    if not re.search(r'^name:\s*[\'\"]?autowork[\'\"]?\s*$', (repo / 'plugin.yaml').read_text(), re.M):
        raise ValueError(f'Unexpected managed plugin identity: {repo}')
    metadata = home / 'plugins/.install-metadata.json'
    safe_path(metadata)
    if metadata.exists() and metadata.stat().st_uid != os.getuid():
        raise ValueError(f'Uncertain native install metadata ownership: {metadata}')
    records = json.loads(metadata.read_text()) if metadata.exists() else {}
    record = records.get(PLUGIN) if isinstance(records, dict) else None
    if not isinstance(record, dict) or not _same_remote(str(record.get('source', '')), upstream):
        raise ValueError(f'Unregistered or untrusted source {repo}; preserve the checkout and use a reviewed native installation')
    head = git(repo, 'rev-parse', 'HEAD').decode().strip()
    tips = []
    for remote in git(repo, 'remote').decode().split():
        if _same_remote(git(repo, 'remote', 'get-url', remote).decode(), upstream):
            try:
                tips.append(git(repo, 'rev-parse', '--verify', f'refs/remotes/{remote}/main').decode().strip())
            except GitFailure:
                pass
    if head != admitted_head and head != record.get('revision') and head not in tips:
        raise ValueError(f'Ahead/diverged local work or unproven HEAD in {repo}; preserve local commits before updating')
    return {'owner': name, 'home': str(home), 'metadata': {PLUGIN: record}, 'head': head,
            'tracking_tips': tips, 'upstream': upstream}


def safe_path(path):
    if any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError(f'Refusing symlink in skill destination: {path}')
    if path.exists() and not path.is_file():
        raise ValueError(f'Not a regular file: {path}')


def files_at(repo, revision):
    result = {}
    for entry in git(repo, 'ls-tree', '-rz', revision, '--', 'skills').split(b'\0'):
        if not entry:
            continue
        info, name = entry.split(b'\t', 1)
        mode, kind, oid = info.split()
        name = name.decode('utf-8')
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise ValueError(f'Unsupported upstream skill entry: {name}')
        result[name] = git(repo, 'cat-file', 'blob', oid.decode())
    return result


HISTORY_LIMIT = 100


def historical_copy(repo, state, relative, local):
    """Recognize exact same-path bytes in bounded, trusted reachable history."""
    cache = state.setdefault('history', {})
    if relative not in cache:
        # Raw records expose both sides of changes, including an old blob whose
        # last modification falls before the bounded history window. Do not follow
        # renames or consult other refs: neither establishes this path's baseline.
        records = git(repo, 'log', '--format=', '--raw', '--no-abbrev',
                      '--no-renames', '-m', f'-{HISTORY_LIMIT}', state['after'],
                      '--', f':(literal){relative}')
        oids = set()
        for line in records.splitlines():
            if not line.startswith(b':'):
                continue
            fields = line.split(b'\t', 1)[0].split()
            if len(fields) != 5:
                continue
            for mode, oid in ((fields[0][1:], fields[2]), (fields[1], fields[3])):
                if mode in (b'100644', b'100755'):
                    oids.add(oid)
        blobs = state.setdefault('history_blobs', {})
        for oid in oids:
            if oid not in blobs:
                blobs[oid] = git(repo, 'cat-file', 'blob', oid.decode())
        cache[relative] = [blobs[oid] for oid in oids]
    return local in cache[relative]


def skill_destination(home, relative, roots):
    """Use the existing native category, matching install_skills provisioning."""
    parts = Path(relative).parts
    name = parts[1]
    if name not in roots:
        root = home / 'skills' / name
        if not root.exists() and not root.is_symlink():
            matches = [p.parent for p in (home / 'skills').glob(f'*/{name}/SKILL.md')
                       if p.is_file() and not p.relative_to(home / 'skills').parts[0].startswith('.')]
            if len(matches) > 1:
                raise ValueError(f'Ambiguous categorized skill {name}; reconcile duplicate native installations')
            if matches:
                root = matches[0]
        roots[name] = root
    return roots[name].joinpath(*parts[2:])


def prepare(source, profiles, *, upstream=UPSTREAM):
    """Fetch trusted main, then preflight ALL sources and destinations before writes."""
    sources = {}
    writes = []
    drift = []  # Legacy receipt key: profile edits are now merged into local_edits.
    local_edits = []
    for name, home in profiles:
        plugin = plugin_dir(home)
        if (home / 'plugins').is_symlink() or (plugin.is_symlink() and not plugin.exists()):
            raise ValueError(f'Unsafe or dangling plugin path: {plugin}')
        repo = plugin.resolve() if plugin.exists() else source.resolve()
        if repo not in sources:
            top = Path(git(repo, 'rev-parse', '--show-toplevel').decode().strip()).resolve()
            if top != repo:
                raise ValueError(f'Plugin must be a standalone Git checkout: {repo}')
            if git(repo, 'status', '--porcelain', '--untracked-files=all').strip():
                raise ValueError(f'Preserved local changes in {repo}; commit or move reviewed changes before updating')
            before = git(repo, 'rev-parse', 'HEAD').decode().strip()
            # Preserve pre-fetch provenance even when ancestry later proves negative.
            try:
                evidence, refusal = managed_evidence(repo, profiles, upstream), None
            except (ValueError, OSError) as error:
                evidence, refusal = None, str(error)
            # Never execute a configured remote/helper. One bounded trusted history fetch.
            shallow = git(repo, 'rev-parse', '--is-shallow-repository').strip() == b'true'
            fetch(repo, '--no-tags', *(['--deepen=1000'] if shallow else []), upstream, 'refs/heads/main')
            after = git(repo, 'rev-parse', 'FETCH_HEAD').decode().strip()
            recovery = not is_ancestor(repo, before, after)
            if recovery:
                if git(repo, 'rev-parse', '--is-shallow-repository').strip() == b'true':
                    raise ValueError(f'Incomplete/shallow ancestry in {repo} after bounded trusted fetch; review history before retrying')
                if is_ancestor(repo, after, before):
                    raise ValueError(f'Locally advanced checkout {repo}; preserve local commits before updating')
                if evidence is None:
                    raise ValueError(refusal)
            sources[repo] = {'before': before, 'after': after, 'recovery': evidence if recovery else None,
                             'old': files_at(repo, before), 'new': files_at(repo, after),
                             'executables': {e.split(b'\t', 1)[1].decode() for e in
                                 git(repo, 'ls-tree', '-rz', after, '--', 'skills').split(b'\0')
                                 if e.startswith(b'100755 ')}}
        state = sources[repo]
        if state.get('recovery'):
            continue  # Recovery uses the journaled native transaction and three-way merge below.
        skill_roots = {}
        for relative in sorted(state['old'].keys() | state['new'].keys()):
            path = skill_destination(home, relative, skill_roots)
            safe_path(path)
            local = path.read_bytes() if path.exists() else None
            old, new = state['old'].get(relative), state['new'].get(relative)
            # A released skill is the release, byte for byte, and a removed one goes. A profile's
            # edited copy (Hermes' skill review rewrites them) is reset or removed and reported,
            # its bytes in the update's backup: kept edits blocked every later release of that
            # file and were reported again on every run.
            merged = new
            if local not in (None, old, new) and not historical_copy(repo, state, relative, local):
                local_edits.append({'profile': name, 'path': str(path),
                                    'action': 'reset' if new is not None else 'removed', 'base': None})
            current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
            mode = current_mode | (0o111 if relative in state['executables'] else 0)
            if merged != local or (merged is not None and mode != current_mode):
                writes.append((path, local, merged, mode))
        # A shared checkout that advanced before this update has old == new, so a
        # skill removed from the bundle never shows up above. Remove installed copies
        # of any path deleted in history once their bytes match a released version.
        if 'retired' not in state:
            deleted = git(repo, 'log', '--format=', '--name-only', '--diff-filter=D',
                          '--no-renames', state['after'], '--', 'skills').decode().splitlines()
            # Required external skills (graphify, omh-plan) may reuse a once-bundled name.
            external = set(json.loads((Path(__file__).resolve().parent / 'plugins/defaults.json')
                                      .read_text()).get('required_skills', []))
            state['retired'] = sorted({r for r in deleted if r and r not in state['new']
                                       and Path(r).parts[1] not in external})
        for relative in state['retired']:
            if relative in state['old']:
                continue
            path = skill_destination(home, relative, skill_roots)
            safe_path(path)
            if not path.is_file():
                continue
            local = path.read_bytes()
            writes.append((path, local, None, stat.S_IMODE(path.stat().st_mode)))
            if not historical_copy(repo, state, relative, local):
                local_edits.append({'profile': name, 'path': str(path), 'action': 'removed', 'base': None})
    return {'sources': sources, 'writes': writes, 'drift': drift, 'local_edits': local_edits,
            'profiles': [n for n, _ in profiles]}


def prune_empty_skill_dirs(folder):
    """Remove folders a deletion emptied, up to the skills root; bytecode caches do not count."""
    while folder.name != 'skills' and folder.parent.name != '' and not folder.is_symlink():
        try:
            entries = list(folder.iterdir())
        except OSError:
            return
        if any(e.name != '__pycache__' or e.is_symlink() or not e.is_dir() for e in entries):
            return
        for cache in entries:
            shutil.rmtree(cache)
        folder.rmdir()
        folder = folder.parent


def apply(plan, backup, *, _saved=False):
    if plan.get('drift'):
        raise ValueError('Unresolved native skill drift; reconcile the reported files before updating')
    # Recheck every destination before advancing any checkout.
    for path, old, new, mode in plan['writes']:
        safe_path(path)
        if (path.read_bytes() if path.exists() else None) != old:
            raise ValueError(f'Destination changed since preflight: {path}')
    for repo, state in plan['sources'].items():
        if git(repo, 'rev-parse', 'HEAD').decode().strip() != state['before'] or git(repo, 'status', '--porcelain').strip():
            raise ValueError(f'Checkout changed since preflight: {repo}')
    if plan['writes'] and not _saved:  # a run with nothing to write leaves no backup behind
        backup.mkdir(parents=True, exist_ok=False)
        records = []
        for index, (path, old, new, mode) in enumerate(plan['writes']):
            if old is not None:
                (backup / str(index)).write_bytes(old)
            records.append({'path': str(path), 'backup': str(index) if old is not None else None,
                            'mode': stat.S_IMODE(path.stat().st_mode) if path.exists() else None})
        (backup / 'manifest.json').write_text(json.dumps(records, indent=2) + '\n')
    for path, old, new, mode in plan['writes']:
        safe_path(path)
        if (path.read_bytes() if path.exists() else None) != old:
            raise ValueError(f'Destination changed since preflight: {path}; partial update, backups at {backup}')
        if new is None:
            path.unlink()
            prune_empty_skill_dirs(path.parent)
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                temporary = Path(stream.name)
                stream.write(new)
            try:
                temporary.chmod(mode)
                temporary.replace(path)
            finally:
                temporary.unlink(missing_ok=True)

    # Advance sources only after ALL skill writes. An interrupted publication can
    # then retry against the original merge base; already-written files equal new.
    for repo, state in plan['sources'].items():
        if git(repo, 'rev-parse', 'HEAD').decode().strip() != state['before'] or git(repo, 'status', '--porcelain').strip():
            raise ValueError(f'Checkout changed since preflight: {repo}; skills updated, rerun after reconciliation')
        if state['before'] != state['after']:
            git(repo, 'merge', '--ff-only', state['after'])


STARTUP_WAIT_S = 5 * 60
WIRING_RETRY_S = (15, 30, 60)


def gateway_state(root):
    try:
        return json.loads((root / 'gateway_state.json').read_text()).get('gateway_state')
    except (OSError, ValueError, AttributeError):
        return None


def wait_for_gateway(root, folder, limit=STARTUP_WAIT_S, poll=5):
    """While a restart this updater requested is between gateways (the old one gone, the new one
    starting), wait for the new one: activation checks command wiring, which no gateway answers
    then, so a rerun at that moment reported `incomplete`. A draining gateway still serves, and the
    update joins its restart as before. True if it waited."""
    deadline, waited = time.monotonic() + limit, False
    while time.monotonic() < deadline:
        pending = pending_restart(folder)
        restarting = pending is not None and pending.get('mode') != 'deferred'
        if not (restarting and (gateway_state(root) == 'starting' or not gateway_running(root))):
            return waited
        waited = True
        time.sleep(poll)
    return waited


def finalize_profiles(source, root, profiles, retries=()):
    """Enable and finalize each profile; a profile left incomplete is finalized again after each
    delay in `retries` (a just-restarted gateway wires its commands a little after it serves)."""
    results = []
    env = dict(os.environ, HERMES_HOME=str(root))
    for name, home in profiles:
        plugin = plugin_dir(home)
        if not plugin.exists():
            plugin.parent.mkdir(parents=True, exist_ok=True)
            plugin.symlink_to(source, target_is_directory=True)
        enable = subprocess.run(['hermes', '-p', name, 'plugins', 'enable', PLUGIN],
                                env=env, timeout=120)
        final = subprocess.run(['hermes', '-p', name, 'autowork', 'finalize',
                                '--hermes-home', str(root), '--bundle-only'], env=env, timeout=120)
        results.append({'profile': name, 'status': 'ready' if enable.returncode == final.returncode == 0 else 'incomplete',
                        'enable_exit': enable.returncode, 'finalize_exit': final.returncode})
    for delay in retries:
        if all(r['status'] == 'ready' for r in results):
            break
        time.sleep(delay)
        for row in results:
            if row['status'] == 'ready' or row['enable_exit']:
                continue
            final = subprocess.run(['hermes', '-p', row['profile'], 'autowork', 'finalize', '--hermes-home', str(root),
                                    '--bundle-only'], env=env, timeout=120)
            row.update(status='ready' if final.returncode == 0 else 'incomplete', finalize_exit=final.returncode)
    return results


def config_snapshot(profiles):
    """Profile config bytes, to see which profiles plugin activation healed."""
    snapshot = {}
    for name, home in profiles:
        path = home / 'config.yaml'
        snapshot[name] = path.read_bytes() if path.is_file() and not path.is_symlink() else None
    return snapshot


def env_value(raw):
    """One `.env` value as python-dotenv reads it: quoted content, or text before ` #`."""
    raw = raw.strip()
    if raw[:1] in ('"', "'"):
        match = re.match(r'"((?:\\.|[^"\\])*)"|\'((?:\\.|[^\'\\])*)\'', raw)
        if match and (match.end() == len(raw) or re.match(r'\s*(#.*)?$', raw[match.end():])):
            return match.group(1) if match.group(1) is not None else match.group(2)
        return raw.strip('"\'')
    return re.sub(r'\s+#.*', '', raw).strip()


def read_env(path):
    values = {}
    try:
        lines = path.read_text().splitlines()
    except (OSError, UnicodeDecodeError):
        return values
    for line in lines:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            key, value = line.split('=', 1)
            values[key.removeprefix('export ').strip()] = env_value(value)
    return values


def telegram_call(token, method, **params):
    import urllib.parse
    import urllib.request
    data = urllib.parse.urlencode({k: json.dumps(v) for k, v in params.items()}).encode()
    with urllib.request.urlopen(f'https://api.telegram.org/bot{token}/{method}', data, timeout=20) as reply:
        body = json.load(reply)
    if not body.get('ok'):
        raise OSError(body.get('description', 'Telegram API error'))
    return body['result']


def heal_chat_menus(profiles, call=telegram_call):
    """Drop leftover chat-scoped Telegram menus that still list retired commands."""
    results, seen = [], set()
    for name, home in profiles:
        env = read_env(home / '.env')
        token = env.get('TELEGRAM_BOT_TOKEN')
        if not token or token in seen:
            continue
        seen.add(token)
        policy = _AUTOWORK_COMPAT.peer(globals(), 'telegram_menu_policy')
        chat_ids, stale_chat_menus = policy.chat_ids, policy.stale_chat_menus
        failed = []
        try:
            cleared = stale_chat_menus(env, lambda method, **kw: call(token, method, **kw), failed)
        except (OSError, ValueError) as error:
            results.append({'profile': name, 'status': 'unreachable', 'error': type(error).__name__})
            continue
        # Chat IDs stay out of the receipt beyond their last digits.
        def masked(chats): return [f'...{str(c)[-4:]}' for c in chats]
        result = {'profile': name, 'status': 'cleared' if cleared else 'unreachable'}
        if cleared:
            result['chats'] = masked(cleared)
        if failed and len(failed) < len(chat_ids(env)):
            result['failed'] = masked(chat for chat, _ in failed)
        if failed:
            result['error'] = failed[0][1]
        if cleared or failed:
            results.append(result)
    return results


def gateway_running(root):
    try:
        pid = json.loads((root / 'gateway.pid').read_text())['pid']
        os.kill(int(pid), 0)
        return True
    except (OSError, ValueError, KeyError, TypeError):
        return False


def request_gateway_restart(root, log):
    """Graceful restart: Hermes drains in-flight turns, then reconnects and re-pushes menus."""
    with log.open('ab') as stream:
        stream.write(f'--- toolset update: gateway restart requested {time.time_ns()}\n'.encode())
        stream.flush()
        process = subprocess.Popen(['hermes', 'gateway', 'restart'], stdin=subprocess.DEVNULL, stdout=stream,
                                   stderr=stream, start_new_session=True, env=dict(os.environ, HERMES_HOME=str(root)))
    return process.pid


# Gateway states in which Hermes serves turns and publishes a trustworthy active_agents.
SERVING_STATES = ('running', 'degraded')
QUIET_POLL_S = 30
QUIET_WINDOW_S = 6 * 3600


def gateway_pid(root):
    """PID of the live gateway recorded in the root's gateway.pid, or None."""
    try:
        pid = int(json.loads((root / 'gateway.pid').read_text())['pid'])
        os.kill(pid, 0)
        return pid
    except (OSError, ValueError, KeyError, TypeError):
        return None


def chat_turns(root, homes):
    """In-flight chat and API turns, or None when the gateway's activity is unknown.

    Hermes' active_agents counts chat, cron and API work together; cron runs execute in
    restart-safe external workers that survive a restart, so their fire claims are
    subtracted. Only chat and API turns are force-interrupted after Hermes' restart wait.
    """
    try:
        state = json.loads((root / 'gateway_state.json').read_text())
        if state.get('gateway_state') not in SERVING_STATES:
            return None
        active = int(state.get('active_agents') or 0)
    except (OSError, ValueError, TypeError, AttributeError):
        return None
    cron = 0
    for home in homes:
        try:
            data = json.loads((Path(home) / 'cron/jobs.json').read_text())
        except FileNotFoundError:
            continue
        except (OSError, ValueError):
            return None
        jobs = data.get('jobs', []) if isinstance(data, dict) else data
        if not isinstance(jobs, list):
            return None
        cron += sum(1 for job in jobs if isinstance(job, dict) and job.get('fire_claim'))
    return max(0, active - cron)


def _process_argv(pid):
    """argv of a live, non-zombie process, or None."""
    try:
        argv = Path(f'/proc/{int(pid)}/cmdline').read_bytes().split(b'\0')
        state = Path(f'/proc/{int(pid)}/stat').read_text().rsplit(')', 1)[1].split()[0]
    except (OSError, ValueError, TypeError, IndexError):
        return None
    return None if state in ('Z', 'X') else argv


def pending_restart(folder):
    """A restart this updater requested or deferred that has not finished, or None."""
    try:
        record = json.loads((folder / 'restart.json').read_text())
    except (OSError, ValueError):
        return None
    if not isinstance(record, dict):
        return None
    # A recycled PID or a zombie is not the restart or waiter we started.
    if record.get('mode') == 'deferred':
        argv = _process_argv(record.get('waiter_pid'))
        return record if argv and b'--restart-when-quiet' in argv else None
    argv = _process_argv(record.get('pid'))
    if not argv or not any(argv[i:i + 2] == [b'gateway', b'restart'] for i in range(1, len(argv))):
        return None
    return record


def _write_marker(folder, record):
    marker = folder / 'restart.json'
    if marker.is_symlink():
        raise ValueError('Symlinked restart marker')
    temporary = folder / 'restart.tmp'
    temporary.write_text(json.dumps(record) + '\n')
    temporary.replace(marker)


def _read_marker(folder):
    try:
        record = json.loads((folder / 'restart.json').read_text())
    except (OSError, ValueError):
        return {}
    return record if isinstance(record, dict) else {}


def _record_restart_outcome(folder, covers, outcome, **fields):
    """Set the outcome on the latest receipt if it belongs to an update this restart covers.

    The caller holds the update lock, so no update is rewriting the receipt meanwhile.
    """
    receipt = folder / 'latest.json'
    try:
        result = json.loads(receipt.read_text())
    except (OSError, ValueError):
        return
    if result.get('started_ns') not in covers or receipt.is_symlink():
        return
    result.update(gateway_restart=outcome, gateway_restart_covers=len(covers), **fields)
    temporary = folder / 'latest.tmp'
    temporary.write_text(json.dumps(result, indent=2) + '\n')
    temporary.replace(receipt)


def _try_update_lock(folder):
    """The update lock if no update is running, else None; release by closing the file."""
    lock = (folder / 'lock').open('a')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        lock.close()
        return None
    return lock


def restart_when_quiet(root, homes, folder, *, update_id, gateway, window=QUIET_WINDOW_S, poll=QUIET_POLL_S,
                       sleep=time.sleep, clock=time.monotonic):
    """Restart the gateway once no chat turn is in flight; never force a drain.

    Every step runs under the update lock: the waiter never restarts while an update
    is applying files, and updates that join this restart (``covers``) do so atomically.
    Returns 'requested', 'reloaded' (another restart already loaded the updates) or
    'deferred_expired' (still busy when the window ended; nothing was restarted).
    """
    started = clock()
    deferred_ns = time.time_ns()
    while True:
        lock = _try_update_lock(folder)
        if lock is not None:
            with lock:
                covers = _read_marker(folder).get('covers') or [update_id]
                current = gateway_pid(root)
                if current is not None and current != gateway:
                    _record_restart_outcome(folder, covers, 'reloaded')
                    return 'reloaded'
                turns = chat_turns(root, homes)
                if turns == 0 and current is not None:
                    requested_ns = time.time_ns()
                    pid = request_gateway_restart(root, folder / 'run.log')
                    _write_marker(folder, {'pid': pid, 'requested_ns': requested_ns, 'deferred_ns': deferred_ns,
                                           'gateway_pid': current, 'covers': covers})
                    _record_restart_outcome(folder, covers, 'requested')
                    return 'requested'
                _write_marker(folder, {'mode': 'deferred', 'waiter_pid': os.getpid(), 'deferred_ns': deferred_ns,
                                       'window_s': window, 'chat_turns': turns, 'checked_ns': time.time_ns(),
                                       'covers': covers})
                if clock() - started >= window:
                    hours = round(window / 3600, 1)
                    _record_restart_outcome(
                        folder, covers, 'deferred_expired',
                        gateway_restart_action=f'The gateway was not free of chat turns for {hours} h, so it was not '
                                               'restarted. Run `hermes gateway restart` when convenient (Hermes then '
                                               'waits for chat turns up to agent.restart_after_turn_timeout), or rerun '
                                               '/autowork update.')
                    return 'deferred_expired'
        sleep(poll)


BOT_TOKEN = re.compile(r'^\s*(?:export\s+)?TELEGRAM_BOT_TOKEN\s*=\s*\S', re.M)
LOG_STAMP = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)')


def _log_lines_since(path, since, marker):
    """Lines containing marker whose leading local timestamp is at or after since."""
    try:
        with path.open('rb') as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 262144))
            text = stream.read().decode('utf-8', 'replace')
    except OSError:
        return []
    lines = []
    for line in text.splitlines():
        stamp = LOG_STAMP.match(line)
        if stamp and marker in line and stamp.group(1) >= since:
            lines.append(line)
    return lines


def _telegram_profiles(root):
    """(name, home) of the root and named profiles that configure a Telegram bot; values are never read out."""
    homes = [('default', root)] + sorted((p.name, p) for p in (root / 'profiles').glob('*') if p.is_dir())
    found = []
    for name, home in homes:
        try:
            if BOT_TOKEN.search((home / '.env').read_text(encoding='utf-8', errors='replace')):
                found.append((name, home))
        except OSError:
            continue
    return found


def finish_restart(root, folder, *, locked=False):
    """Record the outcome of a requested restart that is no longer running, once.

    Returns the outcome fields, or None while the restart is still draining, the new
    gateway has not started yet, or there is nothing to finish. The outcome is kept in
    the restart marker, so it outlives the receipt, and copied to the receipt when that
    still belongs to a covered update. Pass locked=True when holding the update lock.
    """
    record = _read_marker(folder)
    if 'pid' not in record or record.get('finished') or pending_restart(folder) is not None:
        return None
    now = gateway_pid(root)
    if now is None:
        return None  # stopped or between stop and start; check again later
    since = datetime.datetime.fromtimestamp(record.get('requested_ns', 0) / 1e9).strftime('%Y-%m-%d %H:%M:%S')
    if now == record.get('gateway_pid'):
        outcome = {'gateway_restart': 'restart_failed',
                   'gateway_restart_action': 'The restart process ended but the same gateway is still running; '
                                             'inspect maintenance/toolset-update/run.log and run `hermes gateway '
                                             'restart` if the gateway still serves the old release.'}
    else:
        resent, not_seen = [], []
        for name, home in _telegram_profiles(root):
            (resent if _log_lines_since(home / 'logs/gateway.log', since, 'Telegram menu:') else not_seen).append(name)
        interrupted = [line.split('gateway.run: ', 1)[-1] for line in
                       _log_lines_since(root / 'logs/gateway.log', since, 'Gateway drain timed out')]
        try:
            started = datetime.datetime.fromtimestamp(Path(f'/proc/{now}').stat().st_mtime).isoformat(timespec='seconds')
        except OSError:
            started = None
        outcome = {'gateway_restart': 'completed',
                   'gateway_restart_result': {'gateway_pid': now, 'gateway_started': started,
                                              'menus_resent': sorted(resent), 'menus_not_seen': sorted(not_seen),
                                              'interrupted': interrupted}}
    lock = None if locked else _try_update_lock(folder)
    if not locked and lock is None:
        return outcome  # an update is running; it records the outcome when it starts
    with lock if lock is not None else contextlib.nullcontext():
        # Reread under the lock: an update may have joined this restart since.
        current = _read_marker(folder)
        if current.get('requested_ns') != record.get('requested_ns') or current.get('finished'):
            return outcome
        fields = {k: v for k, v in outcome.items() if k != 'gateway_restart'}
        _record_restart_outcome(folder, current.get('covers') or [], outcome['gateway_restart'], **fields)
        _write_marker(folder, {**current, 'finished': outcome['gateway_restart'], 'outcome': outcome})
    return outcome


# A restart waiter holds the update lock only for a moment per check; wait this long
# before treating the lock as held by another update.
LOCK_WAIT_S = 10


def _describe_runner(folder):
    """Who holds the update lock: the running update's PID, mode and start, as far as recorded."""
    try:
        record = json.loads((folder / 'latest.json').read_text())
    except (OSError, ValueError):
        record = {}
    if isinstance(record, dict) and record.get('status') == 'running':
        started = record.get('started_ns')
        return {'pid': record.get('pid'), 'mode': record.get('mode', 'update'),
                'started': datetime.datetime.fromtimestamp(started / 1e9).isoformat(timespec='seconds')
                if isinstance(started, int) else None}
    marker = _read_marker(folder)
    if marker.get('mode') == 'deferred':
        return {'pid': marker.get('waiter_pid'), 'mode': 'restart_waiter', 'started': None}
    # No receipt or marker names the holder (a crashed update whose receipt was replaced, a
    # hung helper): name the live process that has the lock open, so the owner can stop it
    # instead of rerunning into "busy" forever (seen on a host, 2026-10-22).
    holders = _lock_holders(folder / 'lock')
    if holders:
        return {'pid': holders[0]['pid'], 'mode': 'unknown', 'started': holders[0]['started'],
                'command': holders[0]['command']}
    return {'pid': None, 'mode': 'unknown', 'started': None}


def _lock_holders(lockpath, proc='/proc'):
    """Live processes (other than this one) holding ``lockpath`` open, from procfs; each with its
    PID, command line and start time. Empty where procfs or permissions hide them."""
    found = []
    try:
        target = os.stat(lockpath)
    except OSError:
        return found
    for entry in os.scandir(proc) if os.path.isdir(proc) else ():
        if not entry.name.isdigit() or int(entry.name) == os.getpid():
            continue
        try:
            for fd in os.scandir(os.path.join(entry.path, 'fd')):
                try:
                    info = os.stat(fd.path)
                except OSError:
                    continue
                if (info.st_dev, info.st_ino) == (target.st_dev, target.st_ino):
                    command = b' '.join(Path(entry.path, 'cmdline').read_bytes().split(b'\0')).decode(errors='replace').strip()
                    started = datetime.datetime.fromtimestamp(os.stat(entry.path).st_ctime).isoformat(timespec='seconds')
                    found.append({'pid': int(entry.name), 'command': command[:200] or 'unknown', 'started': started})
                    break
        except OSError:
            continue
    return found


def running_update(folder):
    """The update currently holding the lock, described, or None when none is running."""
    lock = _try_update_lock(folder)
    if lock is not None:
        lock.close()
        return None
    return _describe_runner(folder)


def _waiter_command(root, update_id, gateway):
    return [sys.executable, str(Path(__file__).resolve()), '--hermes-home', str(root),
            '--restart-when-quiet', str(update_id), '--gateway-pid', str(gateway)]


def start_quiet_restart(root, folder, update_id, gateway):
    """Start the detached waiter that restarts the gateway once it is quiet; returns its PID."""
    with (folder / 'run.log').open('ab') as stream:
        stream.write(f'--- toolset update: gateway restart deferred {time.time_ns()}\n'.encode())
        stream.flush()
        process = subprocess.Popen(_waiter_command(root, update_id, gateway), stdin=subprocess.DEVNULL,
                                   stdout=stream, stderr=stream, start_new_session=True)
    _write_marker(folder, {'mode': 'deferred', 'waiter_pid': process.pid, 'deferred_ns': time.time_ns(),
                           'window_s': QUIET_WINDOW_S, 'chat_turns': None, 'checked_ns': None,
                           'covers': [update_id]})
    return process.pid


def gateway_drain(folder):
    """Progress of a pending updater restart, read from the restart output in run.log."""
    record = pending_restart(folder)
    if record is None:
        return None
    if record.get('mode') == 'deferred':
        return {'state': 'deferred', 'waiter_pid': record.get('waiter_pid'), 'chat_turns': record.get('chat_turns'),
                'checked_ns': record.get('checked_ns'), 'deferred_ns': record.get('deferred_ns'),
                'window_s': record.get('window_s'), 'covers': len(record.get('covers') or [])}
    progress = {'restart_pid': record['pid'], 'requested_ns': record.get('requested_ns'),
                'covers': len(record.get('covers') or [])}
    try:
        with (folder / 'run.log').open('rb') as stream:
            stream.seek(max(0, stream.seek(0, os.SEEK_END) - 65536))
            tail = stream.read().decode('utf-8', 'replace')
    except OSError:
        return progress
    tail = tail[tail.rfind('restarting gracefully'):] if 'restarting gracefully' in tail else ''
    block = tail[tail.rfind('still draining'):] if 'still draining' in tail else ''
    left = re.match(r'still draining\D*(\d+)s left', block)
    if left:
        progress['seconds_left'] = int(left.group(1))
    progress['waiting_on'] = [line.strip().lstrip('•').strip() for line in block.splitlines()
                              if line.strip().startswith('•')]
    return progress


def root_home(home):
    home = Path(home).expanduser()
    if home.parent.name == 'profiles':
        home = home.parent.parent
    return home.resolve()


def native_call(action, home, stage, revision, python):
    """Run native admission in a fresh process bound only to the selected home."""
    source = _AUTOWORK_COMPAT.peer(globals(), 'setup_preflight').selected_source()
    if source is None:
        raise ValueError('Cannot resolve source for Hermes selected on PATH; native admission unverified')
    if python is None:
        # Full-suite installation may run under system Python rather than Hermes' venv.
        launcher = Path(shutil.which('hermes')).resolve()
        import shlex
        text = launcher.read_text()
        words = shlex.split(text.split('\n', 1)[1], comments=True) if text.startswith(('#!/bin/sh', '#!/usr/bin/env sh')) else []
        if (len(words) > 2 and words[0] == 'exec' and '-c' in words
                and Path(words[1]).is_absolute() and Path(words[1]).is_file()):
            python = words[1]
        elif (source / '.venv/bin/python').is_file():
            python = str(source / '.venv/bin/python')
        else:
            python = sys.executable  # Admission still fails closed if dependencies are absent.
    # Managed launchers inject source into sys.path; the interpreter alone does not.
    bootstrap = ('import runpy, sys; sys.path.insert(0, sys.argv.pop(1)); '
                 'sys.argv.pop(0); runpy.run_path(sys.argv[0], run_name="__main__")')
    command = [python, '-B', '-c', bootstrap, str(source),
               str(Path(__file__).with_name('update_bundle_native.py')),
               action, str(home), str(stage), revision]
    env = dict(os.environ, HERMES_HOME=str(home), PYTHONDONTWRITEBYTECODE='1')
    # A caller's alternate board/profile must not redirect admission.
    for key in ('HERMES_PROFILE', 'HERMES_KANBAN_DB'):
        env.pop(key, None)
    result = subprocess.run(command, env=env, stdin=subprocess.DEVNULL,
                            capture_output=True, text=True, timeout=180)
    if result.returncode:
        raise ValueError(f'Native {action} refused: {result.stderr or result.stdout}')
    return json.loads(result.stdout.splitlines()[-1])


def source_tree(source, revision, *, require_head=True):
    import hashlib
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Reviewed source must be an exact 40-character commit SHA')
    if (Path(git(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != source
            or (require_head and git(source, 'rev-parse', 'HEAD').decode().strip() != revision)
            or git(source, 'status', '--porcelain', '--untracked-files=all').strip()):
        raise ValueError('Reviewed source identity/closure changed or source has local changes')
    entries = []
    for entry in git(source, 'ls-tree', '-rz', revision).split(b'\0'):
        if not entry:
            continue
        info, raw = entry.split(b'\t', 1)
        mode, kind, oid = info.split()
        name = raw.decode()
        if mode not in (b'100644', b'100755') or kind != b'blob':
            raise ValueError(f'Unsupported source closure entry: {name}')
        entries.append((name, mode, oid))
    # Batch raw blobs: git archive applies export-ignore/export-subst attributes.
    result = subprocess.run(['git', '-C', str(source), 'cat-file', '--batch'],
                            input=b''.join(oid + b'\n' for _, _, oid in entries),
                            capture_output=True, check=True, timeout=120)
    import io
    stream = io.BytesIO(result.stdout)
    tree = {}
    for name, mode, oid in entries:
        actual_oid, kind, size = stream.readline().split()
        if actual_oid != oid or kind != b'blob':
            raise ValueError('Source object changed during closure read')
        content = stream.read(int(size))
        if len(content) != int(size) or stream.read(1) != b'\n':
            raise ValueError('Incomplete source object')
        tree[name] = {'sha256': hashlib.sha256(content).hexdigest(),
                      'mode': 0o755 if mode == b'100755' else 0o644}
    if 'plugin.yaml' not in tree:
        raise ValueError('Reviewed source has no plugin.yaml')
    return tree


def file_state(path):
    import hashlib
    safe_path(path)
    if not path.exists():
        return None
    return {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(),
            'mode': 0o755 if path.stat().st_mode & 0o111 else 0o644}


def check_tree(path, tree):
    for relative, expected in tree.items():
        actual = file_state(path / relative)
        if actual != expected:
            raise ValueError(f'Installed/staged bytes changed: {path / relative}')


def direct_claim_consumer(claim_path, profile):
    """Verify one shared repository claim against its actual process identity."""
    safe_path(claim_path)
    try:
        claim = json.loads(claim_path.read_text())
    except FileNotFoundError:
        return None  # Release removes the shared claim; pointers may remain.
    if (not isinstance(claim, dict) or any(not isinstance(claim.get(key), str)
            or not claim[key].strip() for key in ('task_id', 'workspace', 'profile'))
            or not Path(claim['workspace']).is_absolute()):
        raise ValueError('invalid active claim')
    owner = claim.get('owner')
    if (not isinstance(owner, dict) or type(owner.get('pid')) is not int or owner['pid'] <= 0
            or not isinstance(owner.get('boot_id'), str) or not owner['boot_id'].strip()
            or not str(owner.get('start_ticks', '')).isdigit()):
        raise ValueError('incomplete process identity')
    if claim['profile'] != profile:
        return None
    if Path('/proc/sys/kernel/random/boot_id').read_text().strip() != owner['boot_id']:
        return None
    try:
        stat = Path(f"/proc/{owner['pid']}/stat").read_text().rsplit(')', 1)[1].split()
    except FileNotFoundError:
        return None
    if stat[0] not in ('Z', 'X') and stat[19] == str(owner['start_ticks']):
        return f"Active direct coordinator owns {claim['task_id']} (pid {owner['pid']})"
    return None


def direct_consumer(home, profile):
    """Inspect every repository pointer; a newer claim must not hide an older live one."""
    directory = home / 'autowork/task-execution-claims'
    receipt = directory
    try:
        if any(path.is_symlink() for path in (directory, *directory.parents)):
            raise ValueError('symlinked direct execution pointer directory')
        if directory.exists() and not directory.is_dir():
            raise ValueError('direct execution pointer path is not a directory')
        receipts = sorted(path for path in directory.iterdir() if path.suffix == '.json') if directory.exists() else []
        receipts.append(home / 'autowork/task-execution-latest.json')
        seen = set()
        for receipt in receipts:
            safe_path(receipt)
            try:
                pointer = json.loads(receipt.read_text())
            except FileNotFoundError:
                continue
            if (not isinstance(pointer, dict) or not isinstance(pointer.get('task_id'), str)
                    or not pointer['task_id'].strip() or not isinstance(pointer.get('claim_path'), str)):
                raise ValueError('invalid pointer')
            claim_path = Path(pointer['claim_path'])
            if not claim_path.is_absolute():
                raise ValueError('claim path is not absolute')
            safe_path(claim_path)
            identity = claim_path.resolve()
            if identity in seen:
                continue
            seen.add(identity)
            reason = direct_claim_consumer(claim_path, profile)
            if reason:
                return reason
        return None
    except (OSError, ValueError, TypeError, IndexError) as error:
        raise ValueError(f'Repair direct execution receipt/claim referenced by {receipt}: {error}') from error


def active_consumers(home, profile):
    """Protect selected helper files referenced by actual same-user processes."""
    reason = direct_consumer(home, profile)
    if reason:
        return reason
    proc = Path('/proc')
    if not proc.is_dir():
        return 'Native helper process inventory is unavailable on this host'
    prefixes = [str(home / rel) + '/' for rel in ('skills', 'plugins', 'autowork/runtimes')]
    for process in proc.iterdir():
        if not process.name.isdigit() or int(process.name) == os.getpid():
            continue
        try:
            if process.stat().st_uid != os.getuid():
                continue
            arguments = (process / 'cmdline').read_bytes().decode(errors='replace').split('\0')
        except FileNotFoundError:
            continue
        except PermissionError:
            return 'Cannot establish ownership of a same-user helper process'
        if any(argument.startswith(prefix) for argument in arguments for prefix in prefixes):
            return f'Active helper process references selected profile files (pid {process.name})'
    return None


def selected_profiles(root, names):
    live_profiles = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle').live_profiles
    available = dict(live_profiles(root))
    if not names or len(set(names)) != len(names) or any(n not in available for n in names):
        raise ValueError('Explicit distinct existing profile selection is required')
    return [(name, available[name]) for name in names]


def _same_remote(url, upstream):
    def norm(value):
        value = value.strip().rstrip('/')
        if value == 'TrebuchetDynamics/autowork':
            value = UPSTREAM
        value = value[:-4] if value.endswith('.git') else value
        return value[7:] if value.startswith('file://') else value
    return norm(url) == norm(upstream)


def _released(repo, revision, upstream):
    """Whether a revision is on the upstream main this checkout last fetched; None if unknown."""
    for remote in git(repo, 'remote').decode().split():
        try:
            if not _same_remote(git(repo, 'remote', 'get-url', remote).decode(), upstream):
                continue
            git(repo, 'rev-parse', '--verify', '--quiet', f'refs/remotes/{remote}/main')
        except ValueError:
            continue
        try:
            git(repo, 'merge-base', '--is-ancestor', revision, f'refs/remotes/{remote}/main')
            return True
        except ValueError:
            return False
    return None


def linked_profiles(profiles, *, upstream=UPSTREAM):
    """Profiles whose plugin links to a working checkout: any gateway restart loads its current files."""
    rows, checkouts = [], {}
    for name, home in profiles:
        plugin = plugin_dir(home)
        if not plugin.is_symlink():
            continue
        target = plugin.resolve()
        if target not in checkouts:
            try:
                revision = git(target, 'rev-parse', 'HEAD').decode().strip()
                checkouts[target] = {'revision': revision,
                                     'dirty': bool(git(target, 'status', '--porcelain').strip()),
                                     'released': _released(target, revision, upstream)}
            except (ValueError, OSError, subprocess.SubprocessError):
                checkouts[target] = {'revision': None, 'dirty': None, 'released': None}
        rows.append({'profile': name, 'link': os.readlink(plugin), 'target': str(target), **checkouts[target]})
    return rows


def fleet_linked_profiles(root):
    """Linked profiles of a Hermes home, loadable from the plugin process (no setup_bundle on sys.path)."""
    module = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle')
    return linked_profiles(module.live_profiles(root_home(root)))


def _pin_records(state, name):
    folder = state / 'pinned'
    return sorted(folder.glob(f'{name}-*/record.json')) if folder.is_dir() else []


def pin_profile(root, name, *, dry_run=False, upstream=UPSTREAM):
    """Replace one profile's plugin link with a clone of the same revision; the link is kept for unpin."""
    live_profiles = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle').live_profiles
    root = root_home(root)
    home = dict(live_profiles(root)).get(name)
    if home is None:
        raise ValueError(f'No profile named {name}')
    plugin = plugin_dir(home)
    if any(p.is_symlink() for p in plugin.parents):
        raise ValueError('Symlinked plugin parent')
    if not plugin.is_symlink():
        return {'profile': name, 'status': 'not_linked',
                'note': 'The plugin is not a link; it already changes only through an update.'}
    row = linked_profiles([(name, home)], upstream=upstream)[0]
    if row['revision'] is None or not plugin.exists():
        raise ValueError(f"The plugin link points to no readable checkout: {row['link']}")
    if row['dirty']:
        raise ValueError(f"{row['target']} has uncommitted changes the profile loads; commit or move them, then pin")
    if not row['released']:
        raise ValueError(f"{row['revision'][:12]} is not on upstream main yet (or the checkout has no fetched "
                         'upstream ref); the next update could not advance the pinned clone. Publish it first.')
    state = root / 'maintenance/toolset-update'
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('Symlinked updater state')
    backup = state / 'pinned' / f'{name}-{time.time_ns()}'
    result = {**row, 'status': 'would_pin' if dry_run else 'pinned', 'backup': str(backup),
              'note': 'The profile keeps this revision; only /autowork update advances it. The gateway loads the '
                      'clone at its next restart. Undo with: hermes autowork pin --unpin ' + name}
    if dry_run:
        return result
    state.mkdir(parents=True, exist_ok=True)
    lock = _try_update_lock(state)
    if lock is None:
        raise ValueError('An update is running; pin the profile after it finishes')
    with lock:
        backup.mkdir(parents=True)
        clone = backup / 'clone'
        git(backup, 'clone', '--quiet', '--no-hardlinks', '--no-checkout', row['target'], str(clone))
        git(clone, 'checkout', '--quiet', '-B', 'main', row['revision'])
        if git(clone, 'rev-parse', 'HEAD').decode().strip() != row['revision'] or git(clone, 'status', '--porcelain').strip():
            raise ValueError('The new clone does not match the linked revision')
        (backup / 'record.json').write_text(json.dumps({k: row[k] for k in ('profile', 'link', 'target', 'revision')},
                                                       indent=2) + '\n')
        if not plugin.is_symlink() or os.readlink(plugin) != row['link']:
            raise ValueError('The plugin link changed while pinning; nothing was replaced')
        plugin.rename(backup / 'link')
        try:
            clone.rename(plugin)
        except OSError:
            (backup / 'link').rename(plugin)
            raise
    return result


def unpin_profile(root, name, *, dry_run=False):
    """Restore the link saved by the latest pin; the clone is moved beside the record, not deleted."""
    live_profiles = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle').live_profiles
    root = root_home(root)
    home = dict(live_profiles(root)).get(name)
    if home is None:
        raise ValueError(f'No profile named {name}')
    records = [r for r in _pin_records(root / 'maintenance/toolset-update', name) if (r.parent / 'link').is_symlink()]
    backup = records[-1].parent if records else None
    if backup is None:
        raise ValueError(f'No saved link for {name}; nothing to restore')
    plugin = plugin_dir(home)
    if plugin.is_symlink() or not plugin.is_dir():
        raise ValueError('The plugin is not a pinned clone; nothing was changed')
    if git(plugin, 'status', '--porcelain').strip():
        raise ValueError(f'{plugin} has local changes; move them before unpinning')
    result = {'profile': name, 'status': 'would_unpin' if dry_run else 'unpinned', 'link': os.readlink(backup / 'link'),
              'clone_kept_at': str(backup / f'unpinned-{time.time_ns()}')}
    if dry_run:
        return result
    lock = _try_update_lock(root / 'maintenance/toolset-update')
    if lock is None:
        raise ValueError('An update is running; unpin the profile after it finishes')
    with lock:
        plugin.rename(result['clone_kept_at'])
        (backup / 'link').rename(plugin)
    return result


def stage_checkout(source, revision, destination, tree):
    """Publish only a completely checked-out snapshot; interrupted temporaries are unused."""
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        with tempfile.TemporaryDirectory(prefix=f'.{destination.name}.preparing-',
                                         dir=destination.parent) as directory:
            candidate = Path(directory) / 'checkout'
            git(source, 'clone', '--no-hardlinks', '--no-checkout', str(source), str(candidate))
            git(candidate, 'checkout', '--detach', revision)
            source_tree(candidate, revision)
            check_tree(candidate, tree)
            candidate.rename(destination)
    source_tree(destination, revision)
    check_tree(destination, tree)


def merge_profile_bytes(local, base, new):
    """Evidence-based three-way merge; conflicting edits remain untouched."""
    if local in (None, base, new):
        return new
    if base is None or new is None:
        raise ValueError('Native skill addition/deletion conflicts with profile customization')
    with tempfile.TemporaryDirectory(prefix='autowork-skill-merge-') as directory:
        paths = [Path(directory) / name for name in ('local', 'base', 'new')]
        for path, content in zip(paths, (local, base, new)):
            path.write_bytes(content)
        result = subprocess.run(['git', 'merge-file', '-p', *map(str, paths)],
                                capture_output=True, timeout=120)
        if result.returncode:
            raise ValueError('Native skill merge conflict; preserve customizations and reconcile before retrying')
        return result.stdout


def check_original_managed(home, evidence):
    if evidence['head'] != evidence['metadata'][PLUGIN].get('revision') and evidence['head'] not in evidence['tracking_tips']:
        raise ValueError('Original managed HEAD admission evidence is missing')
    current = managed_evidence(plugin_dir(home), [(evidence['owner'], home)], evidence['upstream'],
                               admitted_head=evidence['head'])
    if current['head'] != evidence['head'] or current['metadata'][PLUGIN] != evidence['metadata'][PLUGIN]:
        raise ValueError('Managed source/provenance changed since preflight; preserve foreign edits and reconcile')


def bind_recovered_source(home, evidence, revision, stage):
    """Keep native publication metadata and additional fields, restoring trusted binding."""
    path = home / 'plugins/.install-metadata.json'
    lockpath = path.with_name(path.name + '.lock')
    safe_path(lockpath)
    with lockpath.open('a') as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        safe_path(path)
        records = json.loads(path.read_text())
        current = records.get(PLUGIN)
        old = evidence['metadata'][PLUGIN]
        if not isinstance(current, dict):
            raise ValueError('Native install lost managed source metadata')
        if current != old and (current.get('revision') != revision
                or current.get('source') not in (old['source'], stage.as_uri())):
            raise ValueError('Managed source metadata changed during recovery; preserve it and reconcile')
        records[PLUGIN] = {**old, **current, 'source': old['source'], 'revision': revision}
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
            temporary = Path(stream.name)
            stream.write((json.dumps(records, indent=2) + '\n').encode())
        try:
            temporary.chmod(stat.S_IMODE(path.stat().st_mode))
            temporary.replace(path)
        finally:
            temporary.unlink(missing_ok=True)
        if json.loads(path.read_text()) != records:
            raise ValueError('Managed source metadata readback failed')


def recovery_consumers(root, profiles):
    selected = {plugin_dir(home) for _, home in profiles}
    targets = {plugin.resolve() for plugin in selected}
    for plugin in [root / 'plugins/autowork', *root.glob('profiles/*/plugins/autowork')]:
        if plugin not in selected and plugin.resolve() in targets:
            raise ValueError(f'Unselected shared consumer {plugin}; reconcile ownership before recovery')
    for home in {root, *(home for _, home in profiles)}:
        pidfile = home / 'gateway.pid'
        safe_path(pidfile)
        if pidfile.exists():
            try:
                pid = json.loads(pidfile.read_text())['pid']
                if type(pid) is not int or pid <= 0:
                    raise ValueError('invalid PID')
            except (ValueError, KeyError, TypeError) as error:
                raise ValueError(f'Unknown gateway consumer at {home}; reconcile its PID receipt') from error
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                pass
            except OSError as error:
                raise ValueError(f'Unknown/live gateway consumer at {home}; process ownership is not established') from error
            else:
                raise ValueError('Live gateway consumes managed plugins; quiesce it before recovery (no restart requested)')
        elif gateway_state(home) in (*SERVING_STATES, 'starting', 'draining'):
            raise ValueError(f'Unknown gateway consumer at {home}; active state has no process receipt')
    for name, home in profiles:
        reason = active_consumers(home, name)
        if reason:
            raise ValueError(reason)


def recovery_freshness(root, profiles, run):
    recovery_consumers(root, profiles)
    for name, home in profiles:
        row = run['profiles'][name]
        plugin = plugin_dir(home)
        if name in run['managed']['shared']:
            if not plugin.is_symlink() or os.readlink(plugin) != row.get('original_link'):
                raise ValueError('Shared consumer link changed since preflight')
        for item in row.get('files', []):
            allowed = (item['new'],) if row.get('phase') == 'ready' else (
                (item['old'], item['new']) if row.get('phase') else (item['old'],))
            path = Path(item['path'])
            if file_state(path) not in allowed:
                raise ValueError(f'Destination changed since preflight: {path}')
            if path.exists() and stat.S_IMODE(path.stat().st_mode) not in (item['old_mode'], item['mode']):
                raise ValueError(f'Destination permissions changed since preflight: {path}')


def scoped_update(root, source, revision, names, python, *, check=False, _recovery=None, _locked=False):
    """Deploy one reviewed local commit; never advance shared sources or frozen helpers."""
    source = Path(source).expanduser().resolve(strict=True)
    root = root_home(root)
    tree = source_tree(source, revision)
    profiles = selected_profiles(root, names)
    state = root / 'maintenance/toolset-update'
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('Symlinked updater state')
    state.mkdir(parents=True, exist_ok=True)
    safe_path(state / 'lock')
    with (state / 'lock').open('a') as lock:
        if not _locked:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError('Another updater is running')
        receipt = state / ('recovery.json' if _recovery is not None else 'scoped.json')
        safe_path(receipt)
        identity = {'source': str(source), 'revision': revision, 'selected': list(names)}
        if _recovery is not None:
            identity['managed'] = _recovery
        prior = json.loads(receipt.read_text()) if receipt.exists() else None
        same = prior and all(prior.get(k) == v for k, v in identity.items())
        if prior and prior['status'] == 'incomplete' and not same:
            raise ValueError('Resume the original source and selected profiles before a different deployment')
        if same and prior.get('tree') != tree:
            raise ValueError('Original source manifest changed')
        run = prior if same else {**identity, 'tree': tree, 'profiles': {}, 'status': 'incomplete',
                                'backup': str(state / ('scoped-' + str(time.time_ns())))}
        backup = Path(run['backup'])
        if backup.parent != state or backup.is_symlink():
            raise ValueError('Unsafe original backup record')
        def save():
            save_transaction(receipt, run)
        plans = {}
        # Preflight every selection before staging, native scan or target writes.
        for name, home in profiles:
            row = run['profiles'].setdefault(name, {'status': 'pending'})
            try:
                if _recovery is not None and row.get('phase') != 'ready':
                    recovery_consumers(root, profiles)
                reason = active_consumers(home, name) if row.get('phase') != 'ready' else None
                if reason:
                    raise ValueError(reason)
                plugin = plugin_dir(home)
                if any(p.is_symlink() for p in plugin.parents):
                    raise ValueError('Symlinked plugin parent')
                original = backup / name / 'plugin'
                shared = _recovery.get('shared', {}).get(name) if _recovery is not None else None
                if _recovery is not None and 'files' in row:
                    files = row['files']
                    if row.get('phase') and not shared:
                        if original.exists():
                            source_tree(original, row['original_revision'])
                            check_tree(original, row['original_tree'])
                        elif row['phase'] in ('installed', 'ready'):
                            raise ValueError('Original managed checkout backup is missing')
                    if row.get('phase'):
                        for index, item in enumerate(files):
                            if item['old'] is not None:
                                saved = backup / name / f'file-{index}'
                                safe_path(saved)
                                if (hashlib.sha256(saved.read_bytes()).hexdigest() != item['old']['sha256']
                                        or stat.S_IMODE(saved.stat().st_mode) != item['old_mode']):
                                    raise ValueError('Original profile backup bytes/permissions changed')
                    for item in files:
                        allowed = (item['old'], item['new']) if row.get('phase') else (item['old'],)
                        if file_state(Path(item['path'])) not in allowed:
                            raise ValueError(f"Destination changed since preflight: {item['path']}")
                    if shared and (not plugin.is_symlink() or os.readlink(plugin) != row['original_link']):
                        raise ValueError('Shared plugin link changed since preflight')
                    if row.get('phase') in ('installed', 'ready'):
                        source_tree(plugin.resolve(), revision)
                        check_tree(plugin.resolve(), tree)
                elif row.get('phase') in ('backed_up', 'slot_saved', 'installed', 'ready'):
                    files = row['files']
                    for item in files:
                        actual = file_state(Path(item['path']))
                        if actual not in (item['old'], item['new']):
                            raise ValueError(f"Destination changed since preflight: {item['path']}")
                    if row.get('phase') in ('installed', 'ready') and plugin.exists() and not plugin.is_symlink():
                        source_tree(plugin, revision)
                        check_tree(plugin, tree)
                    elif row.get('phase') in ('installed', 'ready'):
                        raise ValueError('Installed plugin changed since publication')
                else:
                    if plugin.is_symlink() and not plugin.exists():
                        raise ValueError('Dangling plugin link')
                    old_tree = {}
                    old_revision = None
                    if plugin.exists():
                        old_source = plugin.resolve()
                        old_revision = git(old_source, 'rev-parse', 'HEAD').decode().strip()
                        old_tree = source_tree(old_source, old_revision)
                        if _recovery is not None:
                            owner = shared or name
                            if old_revision != _recovery['sources'][owner]['head']:
                                raise ValueError('Managed source HEAD changed since preflight')
                            if not shared:
                                check_original_managed(home, _recovery['sources'][name])
                    files = []
                    roots = {}
                    for relative in sorted({p for p in tree.keys() | old_tree.keys() if p.startswith('skills/')}):
                        path = skill_destination(home, relative, roots)
                        old = file_state(path)
                        new = tree.get(relative)
                        merged = None
                        if _recovery is not None:
                            local = path.read_bytes() if old else None
                            base = git(plugin.resolve(), 'show', f'{old_revision}:{relative}') if relative in old_tree else None
                            incoming = (source / relative).read_bytes() if new else None
                            merged = merge_profile_bytes(local, base, incoming)
                            if merged is not None:
                                new = {'sha256': hashlib.sha256(merged).hexdigest(),
                                       'mode': (old['mode'] if old else new['mode']) | (new['mode'] if new else 0)}
                        elif old and old != new and old != old_tree.get(relative):
                            history = {'after': revision}
                            if not historical_copy(source, history, relative, path.read_bytes()):
                                raise ValueError(f'Native skill drift: {path}')
                        item = {'path': str(path), 'relative': relative, 'old': old, 'new': new}
                        if _recovery is not None:
                            item['merged'] = merged.hex() if merged is not None else None
                            item['old_mode'] = stat.S_IMODE(path.stat().st_mode) if old else None
                            item['mode'] = (item['old_mode'] if old else 0o644) | (
                                0o111 if relative in tree and tree[relative]['mode'] & 0o111 else 0)
                        files.append(item)
                    row.update(home=str(home), files=files, original_link=os.readlink(plugin) if plugin.is_symlink() else None,
                               original_tree=old_tree, original_revision=old_revision,
                               original_source=str(plugin.resolve()) if plugin.exists() else None)
                if row.get('phase') == 'ready':
                    source_tree(plugin.resolve(), revision)
                    check_tree(plugin.resolve(), tree)
                    if any(file_state(Path(i['path'])) != i['new'] for i in files):
                        raise ValueError('Completed deployment has installed skill drift')
                    if _recovery is not None:
                        for item in files:
                            path = Path(item['path'])
                            if path.exists() and stat.S_IMODE(path.stat().st_mode) != item['mode']:
                                raise ValueError(f'Completed recovery has installed permission drift: {path}')
                        if not shared:
                            metadata = home / 'plugins/.install-metadata.json'
                            safe_path(metadata)
                            record = json.loads(metadata.read_text()).get(PLUGIN, {})
                            if (record.get('revision') != revision or record.get('source') !=
                                    _recovery['sources'][name]['metadata'][PLUGIN]['source']):
                                raise ValueError('Completed recovery source binding changed')
                    row['status'] = 'ready'
                    continue
                row['status'] = 'pending'
                row.pop('error', None)
                plans[name] = (home, plugin, original, files)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                row.update(status='deferred', error=str(error))
        if _recovery is not None and any(r['status'] == 'deferred' for r in run['profiles'].values()):
            # Shared consumers are one source transaction: none can publish on a failed preflight.
            plans = {}
        if check:
            return {**run, 'status': 'incomplete' if any(r['status'] == 'deferred' for r in run['profiles'].values())
                    else ('update_available' if plans else 'up_to_date')}
        if not plans and all(r['status'] == 'ready' for r in run['profiles'].values()):
            run['status'] = 'incomplete' if run.get('ordinary_pending') else 'up_to_date'
            save()
            return {**run, 'status': 'up_to_date'}
        backup.mkdir(parents=True, exist_ok=True)
        save()
        if _recovery is not None and plans:
            # Admission is preflighted for ALL consumers before the shared source moves.
            try:
                for name, (home, plugin, original, files) in plans.items():
                    stage = backup / name / 'stage'
                    stage_checkout(source, revision, stage, tree)
                    native_call('scan', home, stage, revision, python)
                    source_tree(stage, revision)
                recovery_freshness(root, profiles, run)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                run['profiles'][name].update(status='incomplete', error=str(error))
                run['status'] = 'incomplete'
                save()
                return run
        for name, (home, plugin, original, files) in plans.items():
            row = run['profiles'][name]
            stage = backup / name / 'stage'
            try:
                # The helper launch uses the same lock; live processes are checked again below.
                journal = home / 'autowork'
                if journal.is_symlink():
                    raise ValueError('Symlinked worker journal')
                journal.mkdir(exist_ok=True)
                safe_path(journal / 'goal-handoff.lock')
                with (journal / 'goal-handoff.lock').open('a') as worker_lock:
                    if _recovery is None:  # Managed recovery holds every consumer's handoff lock.
                        try:
                            fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                        except BlockingIOError:
                            raise ValueError('Worker handoff is active')
                    stage_checkout(source, revision, stage, tree)
                    # Scan is per profile and repeated on every incomplete retry. No approval cache.
                    native_call('scan', home, stage, revision, python)
                    if _recovery is not None:
                        recovery_freshness(root, profiles, run)
                    source_tree(source, revision)
                    source_tree(stage, revision)
                    check_tree(stage, tree)
                    reason = active_consumers(home, name)
                    if reason:
                        raise ValueError(reason)
                    for item in files:
                        allowed = (item['old'], item['new']) if row.get('phase') else (item['old'],)
                        if file_state(Path(item['path'])) not in allowed:
                            raise ValueError(f"Destination changed since preflight: {item['path']}")
                    shared = _recovery.get('shared', {}).get(name) if _recovery is not None else None
                    if not row.get('phase'):
                        if shared:
                            owner = run['profiles'][shared]
                            if owner.get('phase') != 'ready' or not plugin.is_symlink() or os.readlink(plugin) != row['original_link']:
                                raise ValueError('Shared source owner is not verified ready')
                            source_tree(plugin.resolve(), revision)
                        elif plugin.exists():
                            if row['original_link'] is not None:
                                if not plugin.is_symlink() or os.readlink(plugin) != row['original_link']:
                                    raise ValueError('Plugin link changed since preflight')
                            source_tree(plugin.resolve(), row['original_revision'])
                            check_tree(plugin.resolve(), row['original_tree'])
                        elif row['original_tree']:
                            raise ValueError('Plugin changed since preflight')
                        if row['original_link'] is not None and not shared:
                            snapshot = stage.parent / 'original-source'
                            stage_checkout(Path(row['original_source']), row['original_revision'],
                                           snapshot, row['original_tree'])
                        for index, item in enumerate(files):
                            if item['old'] is not None:
                                dest = stage.parent / f'file-{index}'
                                dest.write_bytes(Path(item['path']).read_bytes())
                                if _recovery is not None:
                                    dest.chmod(item['old_mode'])
                        row['phase'] = 'backed_up'
                        save()
                    if row['phase'] == 'backed_up':
                        # A resumed backup is not permission to move a newer writer's slot.
                        if not shared and row['original_tree']:
                            if _recovery is not None:
                                check_original_managed(home, _recovery['sources'][name])
                            if plugin.is_symlink() != (row['original_link'] is not None):
                                raise ValueError('Plugin slot changed since preflight')
                            if plugin.is_symlink() and os.readlink(plugin) != row['original_link']:
                                raise ValueError('Plugin link changed since preflight')
                            source_tree(plugin.resolve(), row['original_revision'])
                            check_tree(plugin.resolve(), row['original_tree'])
                        # Journal intent before rename, so a killed process can recover the slot.
                        row['phase'] = 'slot_saved'
                        save()
                        if not shared and (plugin.exists() or plugin.is_symlink()):
                            plugin.rename(original)
                    if row['phase'] == 'slot_saved':
                        if shared:
                            source_tree(plugin.resolve(), revision)
                            check_tree(plugin.resolve(), tree)
                        elif row['original_tree'] and (plugin.exists() or plugin.is_symlink()) and not (original.exists() or original.is_symlink()):
                            # Intent was journaled but the slot rename was interrupted.
                            if _recovery is not None:
                                check_original_managed(home, _recovery['sources'][name])
                            source_tree(plugin.resolve(), row['original_revision'])
                            check_tree(plugin.resolve(), row['original_tree'])
                            plugin.rename(original)
                        if shared:
                            pass  # One canonical source publication; retain selected consumers' links.
                        elif plugin.exists() and not plugin.is_symlink():
                            source_tree(plugin, revision)
                            check_tree(plugin, tree)  # native install committed before interruption
                        else:
                            if plugin.is_symlink():
                                if original.exists() or original.is_symlink():
                                    raise ValueError('Plugin slot changed during interrupted update')
                                plugin.rename(original)
                            plugin.parent.mkdir(parents=True, exist_ok=True)
                            native_call('install', home, stage, revision, python)
                            source_tree(plugin, revision)
                            check_tree(plugin, tree)
                        row['phase'] = 'installed'
                        save()
                    for item in files:
                        path = Path(item['path'])
                        actual = file_state(path)
                        if actual == item['new']:
                            continue
                        if actual != item['old']:
                            raise ValueError(f'Destination changed since preflight: {path}')
                        if item['new'] is None:
                            path.unlink()
                        else:
                            path.parent.mkdir(parents=True, exist_ok=True)
                            with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
                                temp = Path(stream.name)
                                stream.write(bytes.fromhex(item['merged']) if _recovery is not None
                                             else (stage / item['relative']).read_bytes())
                            try:
                                temp.chmod(item.get('mode', item['new']['mode']))
                                temp.replace(path)
                            finally:
                                temp.unlink(missing_ok=True)
                    verified = native_call('verify', home, plugin, revision, python)
                    if not verified.get('commands'):
                        raise ValueError('Native registration probe returned no commands')
                    source_tree(plugin.resolve(), revision)
                    check_tree(plugin.resolve(), tree)
                    if _recovery is not None and not shared:
                        bind_recovered_source(home, _recovery['sources'][name], revision, stage)
                    if any(file_state(Path(i['path'])) != i['new'] for i in files):
                        raise ValueError('Installed skill hash readback failed')
                    if _recovery is not None and any(Path(i['path']).exists() and
                            stat.S_IMODE(Path(i['path']).stat().st_mode) != i['mode'] for i in files):
                        raise ValueError('Installed skill permission readback failed')
                    row.update(status='ready', phase='ready', commands=verified['commands'],
                               installed_hashes={p: v['sha256'] for p, v in tree.items()})
                    row.pop('error', None)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                row.update(status='incomplete', error=str(error))
                # Restore only an empty slot. Never replace native partial output or another writer.
                if row.get('phase') == 'slot_saved' and not plugin.exists() and not plugin.is_symlink():
                    if original.exists() or original.is_symlink():
                        original.rename(plugin)
                    row['phase'] = 'backed_up'
            save()
        status = 'updated' if all(r['status'] == 'ready' for r in run['profiles'].values()) else 'incomplete'
        run['status'] = 'incomplete' if run.get('ordinary_pending') else status
        save()
        return {**run, 'status': status}


def save_transaction(receipt, run):
    temporary = receipt.with_suffix('.tmp')
    safe_path(receipt)
    safe_path(temporary)
    temporary.write_text(json.dumps(run, indent=2) + '\n')
    temporary.replace(receipt)
    backup = Path(run['backup'])
    if backup.exists():
        manifest, temporary = backup / 'manifest.json', backup / 'manifest.tmp'
        safe_path(manifest)
        safe_path(temporary)
        temporary.write_text(json.dumps(run, indent=2) + '\n')
        temporary.replace(manifest)


def ordinary_snapshot(plan, profiles, selected, revision):
    homes = [home for name, home in profiles if name in selected]
    sources = {str(repo): {key: row[key] for key in ('before', 'after')}
               for repo, row in plan['sources'].items() if not row.get('recovery')
               and not any(repo == plugin_dir(home).resolve() for home in homes)}
    if any(row['after'] != revision for row in sources.values()):
        raise ValueError('Trusted main changed between source fetches; retry before publication')
    return {'sources': sources, 'writes': [
        {'path': str(path), 'old': old.hex() if old is not None else None,
         'new': new.hex() if new is not None else None, 'mode': mode,
         'old_mode': stat.S_IMODE(path.stat().st_mode) if old is not None else None}
        for path, old, new, mode in plan['writes']
        if not any(path.is_relative_to(home / 'skills') for home in homes)]}


def finish_ordinary_recovery(root, recovery):
    """Acknowledge the whole transaction only after frozen ordinary writes read back."""
    receipt = root / 'maintenance/toolset-update/recovery.json'
    safe_path(receipt)
    run = json.loads(receipt.read_text())
    if not run.get('ordinary_pending'):
        return recovery
    snapshot = run['ordinary_plan']
    backup = Path(run['ordinary_backup'])
    if backup.parent != Path(run['backup']) or not backup.name.startswith('ordinary-'):
        raise ValueError('Unsafe journaled ordinary-profile backup')
    if any(path.is_symlink() for path in (backup, *backup.parents)):
        raise ValueError('Unsafe ordinary-profile backup')
    plan = {'sources': {}, 'writes': []}
    for repo, row in snapshot['sources'].items():
        head = git(repo, 'rev-parse', 'HEAD').decode().strip()
        if head not in (row['before'], row['after']):
            raise ValueError(f'Ordinary source changed since preflight: {repo}')
        plan['sources'][Path(repo)] = {**row, 'before': head}
    records = []
    for index, item in enumerate(snapshot['writes']):
        path = Path(item['path'])
        safe_path(path)
        old, new = (bytes.fromhex(item[key]) if item[key] is not None else None for key in ('old', 'new'))
        actual = path.read_bytes() if path.exists() else None
        mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else None
        if actual not in (old, new) or mode not in (None, item['old_mode'], item['mode']):
            raise ValueError(f'Ordinary destination changed since preflight: {path}')
        if old is not None:
            backup.mkdir(parents=True, exist_ok=True)
            saved = backup / str(index)
            safe_path(saved)
            if saved.exists() and (saved.read_bytes() != old or stat.S_IMODE(saved.stat().st_mode) != item['old_mode']):
                raise ValueError('Original ordinary-profile backup changed')
            if not saved.exists():
                saved.write_bytes(old)
                saved.chmod(item['old_mode'])
        records.append({'path': str(path), 'backup': str(index) if old is not None else None,
                        'mode': item['old_mode']})
        if actual != new or (new is not None and mode != item['mode']):
            plan['writes'].append((path, actual, new, item['mode']))
    if records:
        backup.mkdir(parents=True, exist_ok=True)
        manifest = backup / 'manifest.json'
        safe_path(manifest)
        if manifest.exists() and json.loads(manifest.read_text()) != records:
            raise ValueError('Ordinary backup manifest changed')
        if not manifest.exists():
            temporary = backup / 'manifest.tmp'
            safe_path(temporary)
            temporary.write_text(json.dumps(records, indent=2) + '\n')
            temporary.replace(manifest)
    apply(plan, backup, _saved=True)
    for repo, row in snapshot['sources'].items():
        if git(repo, 'rev-parse', 'HEAD').decode().strip() != row['after'] or git(repo, 'status', '--porcelain').strip():
            raise ValueError(f'Ordinary source publication readback failed: {repo}')
    for item in snapshot['writes']:
        path = Path(item['path'])
        safe_path(path)
        actual = path.read_bytes() if path.exists() else None
        if (actual != (bytes.fromhex(item['new']) if item['new'] is not None else None)
                or (actual is not None and stat.S_IMODE(path.stat().st_mode) != item['mode'])):
            raise ValueError(f'Ordinary profile publication readback failed: {path}')
    # Ordinary publication must not turn intervening changes to an already-ready
    # native profile into a false aggregate success.
    for name, row in run['profiles'].items():
        home = Path(row['home'])
        source_tree(plugin_dir(home).resolve(), run['revision'])
        check_tree(plugin_dir(home).resolve(), run['tree'])
        for item in row['files']:
            path = Path(item['path'])
            if file_state(path) != item['new'] or (path.exists() and stat.S_IMODE(path.stat().st_mode) != item['mode']):
                raise ValueError(f'Final recovery profile bytes/permissions changed: {path}')
        if name not in run['managed']['shared']:
            metadata = home / 'plugins/.install-metadata.json'
            safe_path(metadata)
            record = json.loads(metadata.read_text()).get(PLUGIN, {})
            if record.get('revision') != run['revision'] or record.get('source') != run['managed']['sources'][name]['metadata'][PLUGIN]['source']:
                raise ValueError('Final recovery source binding changed')
    status = 'updated' if plan['writes'] or any(row['before'] != row['after']
                for row in plan['sources'].values()) else recovery['status']
    run.update(ordinary_pending=False, status=status)
    save_transaction(receipt, run)
    return run


def automatic_recovery(root, profiles, *, plan=None, prior=None, check=False):
    """Enter the existing native journal transaction with immutable trusted-source evidence."""
    state = root / 'maintenance/toolset-update'
    if prior is not None:
        managed = prior['managed']
        names, revision = prior['selected'], prior['revision']
        source = Path(prior['source'])
        if source.parent != state or source.name != 'recovery-source-' + revision:
            raise ValueError('Unsafe recovery source record')
        if set(names) - {name for name, _ in profiles}:
            raise ValueError('Original recovery consumers are no longer selected; reconcile before retrying')
        if not source.exists():
            if any(row.get('phase') for row in prior['profiles'].values()):
                raise ValueError('Original recovery stage is missing after publication began')
            evidence = next(iter(managed['sources'].values()))
            home = Path(evidence['home'])
            check_original_managed(home, evidence)
            repo = plugin_dir(home)
            if source_tree(repo, revision, require_head=False) != prior['tree']:
                raise ValueError('Trusted recovery target tree changed')
            recovery_consumers(root, [(name, dict(profiles)[name]) for name in names])
            if not check:
                stage_checkout(repo, revision, source, prior['tree'])
            else:
                return {**prior, 'status': 'update_available'}
    else:
        recovering = {repo: row for repo, row in plan['sources'].items() if row.get('recovery')}
        revisions = {row['after'] for row in recovering.values()}
        if len(revisions) != 1:
            raise ValueError('Trusted main changed between source fetches; retry before recovering any checkout')
        revision = revisions.pop()
        managed = {'sources': {row['recovery']['owner']: row['recovery'] for row in recovering.values()},
                   'shared': {}, 'ordinary': []}
        owners = list(managed['sources'])
        names = owners[:]
        for name, home in profiles:
            target = plugin_dir(home).resolve()
            if target in recovering and name not in owners:
                names.append(name)
                managed['shared'][name] = recovering[target]['recovery']['owner']
        managed['ordinary'] = [name for name, _ in profiles if name not in names]
        # Existing but non-live/unselected profiles may also consume the canonical slot.
        selected = {plugin_dir(home) for name, home in profiles if name in names}
        for plugin in [root / 'plugins/autowork', *root.glob('profiles/*/plugins/autowork')]:
            if plugin not in selected and plugin.resolve() in recovering:
                raise ValueError(f'Unselected shared consumer {plugin}; reconcile its ownership before recovery')
        recovery_consumers(root, [(name, home) for name, home in profiles if name in names])
        if check:
            return {'status': 'update_available', 'selected': names, 'revision': revision,
                    'action': 'Verified managed checkout recovery required; rerun without --check when consumers are idle'}
        source = state / ('recovery-source-' + revision)
        repo = next(iter(recovering))
        tree = source_tree(repo, revision, require_head=False)
        # Journal the trusted target and pre-fetch evidence BEFORE staging can fail.
        intent = {'source': str(source), 'revision': revision, 'selected': names, 'managed': managed,
                  'tree': tree, 'profiles': {}, 'status': 'incomplete',
                  'backup': str(state / ('scoped-' + str(time.time_ns())))}
        receipt, temporary = state / 'recovery.json', state / 'recovery.tmp'
        safe_path(receipt)
        safe_path(temporary)
        completed = json.loads(receipt.read_text()) if receipt.exists() else None
        if completed and completed['status'] != 'incomplete' and completed['revision'] == revision:
            # A newly admitted source at this same release must not discard the earlier
            # consumers' preservation bases, backups or already-verified merged output.
            if (completed['tree'] != tree or completed['source'] != str(source)
                    or set(completed['selected']) - {name for name, _ in profiles}):
                raise ValueError('Completed recovery consumers/source changed; reconcile before extending it')
            names = completed['selected'] + [name for name in names if name not in completed['selected']]
            ordinary_names = [name for name in dict.fromkeys(completed['managed']['ordinary'] + managed['ordinary'])
                              if name not in names]
            managed = {key: {**completed['managed'][key], **managed[key]} for key in ('sources', 'shared')}
            managed['ordinary'] = ordinary_names
            intent = {**completed, 'selected': names, 'managed': managed, 'status': 'incomplete'}
        intent.update(ordinary_plan=ordinary_snapshot(plan, profiles, names, revision), ordinary_pending=True,
                      ordinary_backup=str(Path(intent['backup']) / ('ordinary-' + str(time.time_ns()))))
        save_transaction(receipt, intent)
        stage_checkout(repo, revision, source, tree)
    selected = [(name, dict(profiles)[name]) for name in names]
    with contextlib.ExitStack() as locks:
        for name, home in selected:
            journal = home / 'autowork'
            if journal.is_symlink():
                raise ValueError('Symlinked worker journal')
            journal.mkdir(exist_ok=True)
            path = journal / 'goal-handoff.lock'
            safe_path(path)
            lock = locks.enter_context(path.open('a'))
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
            except BlockingIOError:
                raise ValueError(f'Worker handoff is active for {name}')
        return scoped_update(root, source, revision, names, None, check=check,
                             _recovery=managed, _locked=True)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True, type=Path)
    parser.add_argument('--check', action='store_true', help='Fetch/check only; no checkout or profile updates')
    parser.add_argument('--profile', action='append', help='Explicit selected profile; repeatable in local mode')
    parser.add_argument('--source', type=Path, help='Reviewed clean local Git checkout; no fetch')
    parser.add_argument('--revision', help='Exact reviewed 40-character local commit')
    parser.add_argument('--native-python', help='Python from the selected Hermes installation')
    parser.add_argument('--pin-profile', metavar='NAME', help='Replace this profile\'s plugin link with a clone of the same revision')
    parser.add_argument('--unpin-profile', metavar='NAME', help='Restore the plugin link saved by the last pin')
    parser.add_argument('--dry-run', action='store_true', help='Preview only; no network or recovery writes')
    parser.add_argument('--restart-when-quiet', type=int, metavar='UPDATE_ID', help=argparse.SUPPRESS)
    parser.add_argument('--gateway-pid', type=int, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.restart_when_quiet is not None:
        live_profiles = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle').live_profiles
        root = root_home(args.hermes_home)
        homes = [home for _, home in live_profiles(root)]
        print(restart_when_quiet(root, homes, root / 'maintenance/toolset-update',
                                 update_id=args.restart_when_quiet, gateway=args.gateway_pid))
        return 0
    if args.pin_profile or args.unpin_profile:
        try:
            result = (pin_profile(args.hermes_home, args.pin_profile, dry_run=args.dry_run) if args.pin_profile
                      else unpin_profile(args.hermes_home, args.unpin_profile, dry_run=args.dry_run))
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            result = {'profile': args.pin_profile or args.unpin_profile, 'status': 'refused', 'error': str(error)}
        print(json.dumps(result, indent=2))
        return int(result['status'] == 'refused')
    if any((args.profile, args.source, args.revision, args.native_python)):
        if not all((args.profile, args.source, args.revision, args.native_python)):
            parser.error('local deployment requires --profile, --source, --revision and --native-python')
        result = scoped_update(args.hermes_home, args.source, args.revision, args.profile,
                               args.native_python, check=args.check or args.dry_run)
        print(json.dumps(result, indent=2))
        return int(result['status'] == 'incomplete')
    live_profiles = _AUTOWORK_COMPAT.peer(globals(), 'setup_bundle').live_profiles
    root = root_home(args.hermes_home)
    if args.dry_run:
        print(json.dumps({'status': 'preview', 'profiles': [name for name, _ in live_profiles(root)],
                          'action': 'No network, staging or profile writes; rerun without --dry-run to update'}, indent=2))
        return 0
    state_dir = root / 'maintenance/toolset-update'
    if not root.is_dir() or any(p.is_symlink() for p in (state_dir, state_dir.parent)):
        raise ValueError('Missing home or symlinked update state directory')
    state_dir.mkdir(parents=True, exist_ok=True)
    lockpath = state_dir / 'lock'
    if lockpath.is_symlink():
        raise ValueError('Symlinked updater lock')
    with lockpath.open('a') as lock:
        deadline = time.monotonic() + LOCK_WAIT_S
        while True:
            try:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except BlockingIOError:
                if time.monotonic() >= deadline:
                    # Report the owner; its receipt stays untouched.
                    running = _describe_runner(state_dir)
                    who = (f" (PID {running['pid']}, {running.get('command') or running.get('mode')})"
                           if running.get('pid') else '')
                    print(json.dumps({'status': 'busy', 'running': running,
                                      'note': f'Another update holds the update lock{who}. Nothing was changed and its '
                                              'receipt was not replaced; use /autowork update status, then rerun '
                                              'once it finishes. A holder that no longer makes progress is stopped '
                                              'with kill <PID>; the lock frees itself when it exits.'}, indent=2))
                    return 3
                time.sleep(0.2)
        try:
            # Record a finished restart on the receipt it covers before this run replaces it.
            finish_restart(root, state_dir, locked=True)
        except (ValueError, OSError):
            pass
        result = {'status': 'running', 'pid': os.getpid(), 'started_ns': time.time_ns(),
                  'mode': 'check' if args.check else 'update'}
        receipt = state_dir / 'latest.json'
        def save():
            temporary = state_dir / 'latest.tmp'
            if temporary.is_symlink() or receipt.is_symlink():
                raise ValueError('Symlinked updater receipt')
            temporary.write_text(json.dumps(result, indent=2) + '\n')
            temporary.replace(receipt)
        save()
        try:
            source = Path(__file__).resolve().parent
            profiles = live_profiles(root)
            recovery_receipt = state_dir / 'recovery.json'
            safe_path(recovery_receipt)
            prior = json.loads(recovery_receipt.read_text()) if recovery_receipt.exists() else None
            if prior and prior['status'] == 'incomplete':
                recovery = automatic_recovery(root, profiles, prior=prior, check=args.check)
                if recovery['status'] != 'incomplete' and not args.check:
                    if set(recovery['managed']['ordinary']) - {name for name, _ in profiles}:
                        raise ValueError('Original ordinary-profile selection changed; reconcile before retrying')
                    recovery = finish_ordinary_recovery(root, recovery)
                result.update(status=recovery['status'], recovery=recovery, gateway_restart='not_requested',
                              action='Preserve the recovery backup; resolve per-profile errors and rerun ./install.sh --only hermes')
                save()
                print(json.dumps(result, indent=2))
                return int(result['status'] == 'incomplete')
            plan = prepare(source, profiles)
            recover = any(row.get('recovery') for row in plan['sources'].values())
            recovered_homes = [home for name, home in profiles if prior and name in prior['selected']]
            recovered_sources = {plugin_dir(home).resolve() for home in recovered_homes}
            unchanged_recovery = (not recover and prior and len(recovered_homes) == len(prior['selected']) and all(
                repo in plan['sources'] and plan['sources'][repo]['before'] == plan['sources'][repo]['after'] == prior['revision']
                for repo in recovered_sources))
            if unchanged_recovery and not args.check:
                snapshot = ordinary_snapshot(plan, profiles, prior['selected'], prior['revision'])
                if snapshot['writes'] or any(row['before'] != row['after'] for row in snapshot['sources'].values()):
                    prior = {**prior, 'status': 'incomplete', 'ordinary_pending': True, 'ordinary_plan': snapshot,
                             'ordinary_backup': str(Path(prior['backup']) / ('ordinary-' + str(time.time_ns()))),
                             'managed': {**prior['managed'], 'ordinary': [name for name, _ in profiles
                                                                        if name not in prior['selected']]}}
                    save_transaction(recovery_receipt, prior)
            if recover or unchanged_recovery:
                recovery = automatic_recovery(root, profiles, plan=plan,
                    prior=prior if unchanged_recovery else None, check=args.check)
                if recovery['status'] != 'incomplete' and not args.check:
                    recovery = finish_ordinary_recovery(root, recovery)
                result.update(status=recovery['status'], recovery=recovery, gateway_restart='not_requested',
                              action='Preserve the recovery backup; resolve per-profile errors and rerun ./install.sh --only hermes'
                                     if recovery['status'] == 'incomplete' else 'Recovery verified offline; no runtime activation or restart requested')
                save()
                print(json.dumps(result, indent=2))
                return int(result['status'] == 'incomplete')
            result['profiles'] = plan['profiles']
            result['sources'] = {str(p): {k: s[k] for k in ('before', 'after')} for p, s in plan['sources'].items()}
            result['skill_files'] = len(plan['writes'])
            result['linked_profiles'] = [{k: r[k] for k in ('profile', 'target')} for r in linked_profiles(profiles)]
            changed = bool(plan['writes']) or any(s['before'] != s['after'] for s in plan['sources'].values())
            missing = any(not plugin_dir(h).exists() for _, h in profiles)
            result['drift'] = plan['drift']
            # Profile edits reset to the release or removed (bytes in the backup); port any
            # lesson that should reach every profile into the bundle.
            result['local_edits'] = plan.get('local_edits', [])
            if plan['drift']:
                result.update(status='incomplete',
                              action='Review the listed native skill files, back up customizations or intentional pins, and reconcile them with the fetched revision before rerunning /autowork update. No checkout or profile changes were applied.')
            elif args.check:
                result['status'] = 'update_available' if changed or missing else 'up_to_date'
            else:
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                if plan['writes']:
                    result['backup'] = str(state_dir / stamp)
                apply(plan, state_dir / stamp)
                before = config_snapshot(profiles)
                # Refresh even on equal revisions: a prior setup/reload may have failed.
                # Plugin activation also re-applies each profile's command menu and settings.
                restarted = wait_for_gateway(root, state_dir)
                result['activation'] = finalize_profiles(source, root, profiles,
                                                         retries=WIRING_RETRY_S if restarted else ())
                healed = [name for name, value in config_snapshot(profiles).items() if value != before[name]]
                result['settings_healed'] = healed
                # Best effort: an offline bot API never fails the update.
                result['chat_menus_healed'] = heal_chat_menus(profiles)
                ready = all(r['status'] == 'ready' for r in result['activation'])
                result['status'] = ('updated' if changed or missing or healed else 'up_to_date') if ready else 'incomplete'
                if result['status'] == 'updated':
                    # The invoking helper can be outside the installed sources; use a
                    # checkout that apply() actually advanced to the fetched release.
                    host_source = source if source in plan['sources'] else next(iter(plan['sources']))
                    result['hosts'] = refresh_hosts(host_source)
                # A plugin reload rewires handlers, but Telegram menus refresh only on reconnect.
                if not ready or not (changed or missing or healed):
                    result['gateway_restart'] = 'not_needed'
                elif (pending := pending_restart(state_dir)) is not None:
                    # An outstanding restart (draining, or deferred to a quiet moment) loads this
                    # update too; join it so its outcome reaches this receipt. We hold the update lock.
                    pending['covers'] = (pending.get('covers') or []) + [result['started_ns']]
                    _write_marker(state_dir, pending)
                    result['gateway_restart'] = 'pending'
                elif gateway_running(root):
                    # Restart only while no chat turn is in flight, so Hermes never has to
                    # force one; otherwise a detached waiter restarts at the first quiet moment.
                    turns = chat_turns(root, [home for _, home in profiles])
                    if turns == 0:
                        replaced, requested_ns = gateway_pid(root), time.time_ns()
                        pid = request_gateway_restart(root, state_dir / 'run.log')
                        _write_marker(state_dir, {'pid': pid, 'requested_ns': requested_ns, 'gateway_pid': replaced,
                                                  'covers': [result['started_ns']]})
                        result['gateway_restart'] = 'requested'
                    else:
                        result['gateway_restart'] = 'deferred'
                        result['gateway_restart_waiting_on'] = {'chat_turns': turns}
                        start_quiet_restart(root, state_dir, result['started_ns'], gateway_pid(root))
                else:
                    result['gateway_restart'] = 'not_running'
            result['note'] = ('Existing chats may retain loaded instructions. The gateway restarts only when no chat '
                              'turn is in flight; while one is, the restart is deferred and retried for up to 6 h, '
                              'never forced. It then refreshes commands and Telegram menus; /autowork update status '
                              'shows what it waits on. Cron runs continue in their own workers; schedules persist.')
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            result.update(status='incomplete', error=str(error),
                          action='Resolve the named checkout/file error and rerun /autowork update. Partial changes, if any, are retained with backups.')
        save()
        print(json.dumps(result, indent=2))
        return int(result['status'] == 'incomplete')


if __name__ == '__main__':
    raise SystemExit(main())
