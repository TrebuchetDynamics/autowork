"""Explicit, fast-forward-only bundle updates across existing Hermes profiles."""
import argparse
import datetime
import fcntl
import json
import os
from pathlib import Path
import subprocess
import stat
import tempfile
import time

UPSTREAM = 'https://github.com/TrebuchetDynamics/hermes-toolset.git'


def git(repo, *args):
    result = subprocess.run(['git', '-C', str(repo), *args], capture_output=True, timeout=120)
    if result.returncode:
        raise ValueError(f'Git {args[0]} failed in {repo}; inspect the checkout and retry (exit {result.returncode})')
    return result.stdout


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


def merge_file(old, local, new, path):
    if local == new or new == old:
        return local
    if local == old:
        return new
    if old is None or local is None or new is None:
        raise ValueError(f'Local skill conflict: {path}; reconcile this file before updating')
    with tempfile.TemporaryDirectory() as temporary:
        paths = [Path(temporary) / str(n) for n in range(3)]
        for target, value in zip(paths, (local, old, new)):
            target.write_bytes(value)
        result = subprocess.run(['git', 'merge-file', '-p', *map(str, paths)], capture_output=True)
        if result.returncode:
            raise ValueError(f'Local skill conflict: {path}; reconcile this file before updating')
        return result.stdout


def prepare(source, profiles, *, upstream=UPSTREAM):
    """Fetch trusted main, then preflight ALL sources and destinations before writes."""
    sources = {}
    writes = []
    for name, home in profiles:
        plugin = home / 'plugins/hermes-toolset'
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
            # Explicit trusted URL: never execute a configured remote/helper supplied by a profile.
            git(repo, 'fetch', '--no-tags', upstream, 'refs/heads/main')
            after = git(repo, 'rev-parse', 'FETCH_HEAD').decode().strip()
            git(repo, 'merge-base', '--is-ancestor', before, after)
            sources[repo] = {'before': before, 'after': after,
                             'old': files_at(repo, before), 'new': files_at(repo, after),
                             'executables': {e.split(b'\t', 1)[1].decode() for e in
                                 git(repo, 'ls-tree', '-rz', after, '--', 'skills').split(b'\0')
                                 if e.startswith(b'100755 ')}}
        state = sources[repo]
        for relative in sorted(state['old'].keys() | state['new'].keys()):
            path = home / relative
            safe_path(path)
            local = path.read_bytes() if path.exists() else None
            old, new = state['old'].get(relative), state['new'].get(relative)
            # Missing native copies are provisioned, including on profiles not installed yet.
            merged = new if local is None and new is not None else merge_file(old, local, new, path)
            current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
            mode = current_mode | (0o111 if relative in state['executables'] else 0)
            if merged != local or (merged is not None and mode != current_mode):
                writes.append((path, local, merged, mode))
    return {'sources': sources, 'writes': writes, 'profiles': [n for n, _ in profiles]}


def apply(plan, backup):
    # Recheck every destination before advancing any checkout.
    for path, old, new, mode in plan['writes']:
        safe_path(path)
        if (path.read_bytes() if path.exists() else None) != old:
            raise ValueError(f'Destination changed since preflight: {path}')
    for repo, state in plan['sources'].items():
        if git(repo, 'rev-parse', 'HEAD').decode().strip() != state['before'] or git(repo, 'status', '--porcelain').strip():
            raise ValueError(f'Checkout changed since preflight: {repo}')
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


def finalize_profiles(source, root, profiles):
    results = []
    env = dict(os.environ, HERMES_HOME=str(root))
    for name, home in profiles:
        plugin = home / 'plugins/hermes-toolset'
        if not plugin.exists():
            plugin.parent.mkdir(parents=True, exist_ok=True)
            plugin.symlink_to(source, target_is_directory=True)
        enable = subprocess.run(['hermes', '-p', name, 'plugins', 'enable', 'hermes-toolset'],
                                env=env, timeout=120)
        final = subprocess.run(['hermes', '-p', name, 'toolset', 'finalize',
                                '--hermes-home', str(root), '--bundle-only'], env=env, timeout=120)
        results.append({'profile': name, 'status': 'ready' if enable.returncode == final.returncode == 0 else 'incomplete',
                        'enable_exit': enable.returncode, 'finalize_exit': final.returncode})
    return results


def root_home(home):
    home = Path(home).expanduser()
    if home.parent.name == 'profiles':
        home = home.parent.parent
    return home.resolve()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True, type=Path)
    parser.add_argument('--check', action='store_true', help='Fetch/check only; no checkout or profile updates')
    args = parser.parse_args(argv)
    from setup_bundle import live_profiles
    root = root_home(args.hermes_home)
    state_dir = root / 'maintenance/toolset-update'
    if not root.is_dir() or any(p.is_symlink() for p in (state_dir, state_dir.parent)):
        raise ValueError('Missing home or symlinked update state directory')
    state_dir.mkdir(parents=True, exist_ok=True)
    lockpath = state_dir / 'lock'
    if lockpath.is_symlink():
        raise ValueError('Symlinked updater lock')
    with lockpath.open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print('An update is already running; use /toolset update status.')
            return 1
        result = {'status': 'running', 'pid': os.getpid(), 'started_ns': time.time_ns()}
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
            plan = prepare(source, profiles)
            result['profiles'] = plan['profiles']
            result['sources'] = {str(p): {k: s[k] for k in ('before', 'after')} for p, s in plan['sources'].items()}
            result['skill_files'] = len(plan['writes'])
            changed = bool(plan['writes']) or any(s['before'] != s['after'] for s in plan['sources'].values())
            missing = any(not (h / 'plugins/hermes-toolset').exists() for _, h in profiles)
            if args.check:
                result['status'] = 'update_available' if changed or missing else 'up_to_date'
            else:
                stamp = datetime.datetime.now(datetime.timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
                result['backup'] = str(state_dir / stamp)
                apply(plan, Path(result['backup']))
                # Refresh even on equal revisions: a prior setup/reload may have failed.
                result['activation'] = finalize_profiles(source, root, profiles)
                ready = all(r['status'] == 'ready' for r in result['activation'])
                result['status'] = ('updated' if changed or missing else 'up_to_date') if ready else 'incomplete'
            result['note'] = 'Existing chats may retain loaded instructions. No worker or schedule was restarted.'
        except (ValueError, OSError, subprocess.SubprocessError) as error:
            result.update(status='incomplete', error=str(error),
                          action='Resolve the named checkout/file error and rerun /toolset update. Partial changes, if any, are retained with backups.')
        save()
        print(json.dumps(result, indent=2))
        return int(result['status'] == 'incomplete')


if __name__ == '__main__':
    raise SystemExit(main())
