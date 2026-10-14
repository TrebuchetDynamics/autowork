"""Explicit, fast-forward-only bundle updates across existing Hermes profiles."""
import argparse
import datetime
import fcntl
import json
import os
import re
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
    drift = []
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
        skill_roots = {}
        for relative in sorted(state['old'].keys() | state['new'].keys()):
            path = skill_destination(home, relative, skill_roots)
            safe_path(path)
            local = path.read_bytes() if path.exists() else None
            old, new = state['old'].get(relative), state['new'].get(relative)
            # Missing native copies are provisioned, including on profiles not installed yet.
            if local is None and new is not None:
                merged = new
            elif local is not None and local != new and local != old and historical_copy(repo, state, relative, local):
                merged = new
            else:
                merged = merge_file(old, local, new, path)
                if old == new and local != new:
                    drift.append({'profile': name, 'path': str(path),
                                  'reason': 'Local bytes differ from current upstream and no exact historical baseline was found'})
            current_mode = stat.S_IMODE(path.stat().st_mode) if path.exists() else 0o644
            mode = current_mode | (0o111 if relative in state['executables'] else 0)
            if merged != local or (merged is not None and mode != current_mode):
                writes.append((path, local, merged, mode))
    return {'sources': sources, 'writes': writes, 'drift': drift, 'profiles': [n for n, _ in profiles]}


def apply(plan, backup):
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


def native_call(action, home, stage, revision, python):
    """Run native admission in a fresh process bound only to the selected home."""
    from setup_preflight import selected_source
    source = selected_source()
    if source is None:
        raise ValueError('Cannot resolve source for Hermes selected on PATH; native admission unverified')
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


def source_tree(source, revision):
    import hashlib
    if not re.fullmatch(r'[0-9a-f]{40}', revision):
        raise ValueError('Reviewed source must be an exact 40-character commit SHA')
    if (Path(git(source, 'rev-parse', '--show-toplevel').decode().strip()).resolve() != source
            or git(source, 'rev-parse', 'HEAD').decode().strip() != revision
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


def active_consumers(home):
    """Protect selected helper files referenced by actual same-user processes."""
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
    from setup_bundle import live_profiles
    available = dict(live_profiles(root))
    if not names or len(set(names)) != len(names) or any(n not in available for n in names):
        raise ValueError('Explicit distinct existing profile selection is required')
    return [(name, available[name]) for name in names]


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


def scoped_update(root, source, revision, names, python, *, check=False):
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
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ValueError('Another updater is running')
        receipt = state / 'scoped.json'
        safe_path(receipt)
        identity = {'source': str(source), 'revision': revision, 'selected': list(names)}
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
            safe_path(receipt)
            safe_path(state / 'scoped.tmp')
            (state / 'scoped.tmp').write_text(json.dumps(run, indent=2) + '\n')
            (state / 'scoped.tmp').replace(receipt)
            if backup.exists():
                safe_path(backup / 'manifest.json')
                safe_path(backup / 'manifest.tmp')
                (backup / 'manifest.tmp').write_text(json.dumps(run, indent=2) + '\n')
                (backup / 'manifest.tmp').replace(backup / 'manifest.json')
        plans = {}
        # Preflight every selection before staging, native scan or target writes.
        for name, home in profiles:
            row = run['profiles'].setdefault(name, {'status': 'pending'})
            try:
                reason = active_consumers(home) if row.get('phase') != 'ready' else None
                if reason:
                    raise ValueError(reason)
                plugin = home / 'plugins/hermes-toolset'
                if any(p.is_symlink() for p in plugin.parents):
                    raise ValueError('Symlinked plugin parent')
                original = backup / name / 'plugin'
                if row.get('phase') in ('backed_up', 'slot_saved', 'installed', 'ready'):
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
                    files = []
                    roots = {}
                    for relative in sorted({p for p in tree.keys() | old_tree.keys() if p.startswith('skills/')}):
                        path = skill_destination(home, relative, roots)
                        old = file_state(path)
                        new = tree.get(relative)
                        if old and old != new and old != old_tree.get(relative):
                            history = {'after': revision}
                            if not historical_copy(source, history, relative, path.read_bytes()):
                                raise ValueError(f'Native skill drift: {path}')
                        files.append({'path': str(path), 'relative': relative, 'old': old, 'new': new})
                    row.update(files=files, original_link=os.readlink(plugin) if plugin.is_symlink() else None,
                               original_tree=old_tree, original_revision=old_revision,
                               original_source=str(plugin.resolve()) if plugin.exists() else None)
                if row.get('phase') == 'ready':
                    source_tree(plugin, revision)
                    check_tree(plugin, tree)
                    if any(file_state(Path(i['path'])) != i['new'] for i in files):
                        raise ValueError('Completed deployment has installed skill drift')
                    row['status'] = 'ready'
                    continue
                row['status'] = 'pending'
                row.pop('error', None)
                plans[name] = (home, plugin, original, files)
            except (ValueError, OSError, subprocess.SubprocessError) as error:
                row.update(status='deferred', error=str(error))
        if check:
            return {**run, 'status': 'incomplete' if any(r['status'] == 'deferred' for r in run['profiles'].values())
                    else ('update_available' if plans else 'up_to_date')}
        if not plans and all(r['status'] == 'ready' for r in run['profiles'].values()):
            run['status'] = 'up_to_date'
            save()
            return run
        backup.mkdir(parents=True, exist_ok=True)
        save()
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
                    try:
                        fcntl.flock(worker_lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                    except BlockingIOError:
                        raise ValueError('Worker handoff is active')
                    stage_checkout(source, revision, stage, tree)
                    # Scan is per profile and repeated on every incomplete retry. No approval cache.
                    native_call('scan', home, stage, revision, python)
                    source_tree(source, revision)
                    source_tree(stage, revision)
                    check_tree(stage, tree)
                    reason = active_consumers(home)
                    if reason:
                        raise ValueError(reason)
                    for item in files:
                        allowed = (item['old'], item['new']) if row.get('phase') else (item['old'],)
                        if file_state(Path(item['path'])) not in allowed:
                            raise ValueError(f"Destination changed since preflight: {item['path']}")
                    if not row.get('phase'):
                        if plugin.exists():
                            if row['original_link'] is not None:
                                if not plugin.is_symlink() or os.readlink(plugin) != row['original_link']:
                                    raise ValueError('Plugin link changed since preflight')
                            source_tree(plugin.resolve(), row['original_revision'])
                            check_tree(plugin.resolve(), row['original_tree'])
                        elif row['original_tree']:
                            raise ValueError('Plugin changed since preflight')
                        if row['original_link'] is not None:
                            snapshot = stage.parent / 'original-source'
                            stage_checkout(Path(row['original_source']), row['original_revision'],
                                           snapshot, row['original_tree'])
                        for index, item in enumerate(files):
                            if item['old'] is not None:
                                dest = stage.parent / f'file-{index}'
                                dest.write_bytes(Path(item['path']).read_bytes())
                        row['phase'] = 'backed_up'
                        save()
                    if row['phase'] == 'backed_up':
                        # Journal intent before rename, so a killed process can recover the slot.
                        row['phase'] = 'slot_saved'
                        save()
                        if plugin.exists() or plugin.is_symlink():
                            plugin.rename(original)
                    if row['phase'] == 'slot_saved':
                        if row['original_tree'] and (plugin.exists() or plugin.is_symlink()) and not (original.exists() or original.is_symlink()):
                            # Intent was journaled but the slot rename was interrupted.
                            source_tree(plugin.resolve(), row['original_revision'])
                            check_tree(plugin.resolve(), row['original_tree'])
                            plugin.rename(original)
                        if plugin.exists() and not plugin.is_symlink():
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
                                stream.write((stage / item['relative']).read_bytes())
                            try:
                                temp.chmod(item['new']['mode'])
                                temp.replace(path)
                            finally:
                                temp.unlink(missing_ok=True)
                    verified = native_call('verify', home, plugin, revision, python)
                    if not verified.get('commands'):
                        raise ValueError('Native registration probe returned no commands')
                    source_tree(plugin, revision)
                    check_tree(plugin, tree)
                    if any(file_state(Path(i['path'])) != i['new'] for i in files):
                        raise ValueError('Installed skill hash readback failed')
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
        run['status'] = 'updated' if all(r['status'] == 'ready' for r in run['profiles'].values()) else 'incomplete'
        save()
        return run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--hermes-home', required=True, type=Path)
    parser.add_argument('--check', action='store_true', help='Fetch/check only; no checkout or profile updates')
    parser.add_argument('--profile', action='append', help='Explicit selected profile; repeatable in local mode')
    parser.add_argument('--source', type=Path, help='Reviewed clean local Git checkout; no fetch')
    parser.add_argument('--revision', help='Exact reviewed 40-character local commit')
    parser.add_argument('--native-python', help='Python from the selected Hermes installation')
    args = parser.parse_args(argv)
    if any((args.profile, args.source, args.revision, args.native_python)):
        if not all((args.profile, args.source, args.revision, args.native_python)):
            parser.error('local deployment requires --profile, --source, --revision and --native-python')
        result = scoped_update(args.hermes_home, args.source, args.revision, args.profile,
                               args.native_python, check=args.check)
        print(json.dumps(result, indent=2))
        return int(result['status'] == 'incomplete')
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
            result['drift'] = plan['drift']
            if plan['drift']:
                result.update(status='incomplete',
                              action='Review the listed native skill files, back up customizations or intentional pins, and reconcile them with the fetched revision before rerunning /toolset update. No checkout or profile changes were applied.')
            elif args.check:
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
