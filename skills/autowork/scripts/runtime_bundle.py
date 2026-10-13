#!/usr/bin/env python3
"""Freeze the bundled worker helper closure; verify it before every entry command."""
import hashlib
import json
from pathlib import Path
import runpy
import shlex
import shutil
import sys
import tempfile

TREES = ('autowork', 'docs-sync', 'shared', 'engineering')
MANIFEST = 'runtime-manifest.json'


def source_files(root):
    files = {}
    for name in TREES:
        tree = root / name
        if tree.is_symlink() or not tree.is_dir():
            raise ValueError('Runtime tree missing or symlink: ' + name)
        for path in sorted(tree.rglob('*')):
            relative = path.relative_to(root)
            if '__pycache__' in relative.parts or path.name.startswith('test_') or path.suffix == '.pyc':
                continue
            if path.is_symlink():
                raise ValueError('Runtime source symlink: ' + relative.as_posix())
            if path.is_dir():
                continue
            if not path.is_file():
                raise ValueError('Runtime source is not a regular file: ' + relative.as_posix())
            files[relative.as_posix()] = (path.read_bytes(), 0o555 if path.stat().st_mode & 0o111 else 0o444)
    return files


def freeze(source, destination):
    source, destination = Path(source).resolve(), Path(destination).absolute()
    files = source_files(source)
    manifest = {'version': 1, 'files': {name: {'sha256': hashlib.sha256(data).hexdigest(), 'mode': mode}
                                      for name, (data, mode) in files.items()}}
    raw = (json.dumps(manifest, sort_keys=True) + '\n').encode()
    digest = hashlib.sha256(raw).hexdigest()
    destination.mkdir(parents=True, exist_ok=True)
    root = Path(tempfile.mkdtemp(prefix=digest[:16] + '-', dir=destination))
    try:
        for name, (data, mode) in files.items():
            path = root / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            path.chmod(mode)
        (root / MANIFEST).write_bytes(raw)
        (root / MANIFEST).chmod(0o444)
        if source_files(source) != files:
            raise ValueError('Runtime source changed during snapshot; retry after source stabilizes')
        runtime = {'root': str(root), 'sha256': digest}
        verify(runtime)
        return runtime
    except BaseException:
        shutil.rmtree(root)
        raise


def verify(runtime):
    root = Path(runtime['root'])
    if not root.is_absolute() or any(p.is_symlink() for p in (root, *root.parents)):
        raise ValueError('Runtime root must be an absolute non-symlink path')
    raw = (root / MANIFEST).read_bytes()
    if hashlib.sha256(raw).hexdigest() != runtime['sha256']:
        raise ValueError('Runtime manifest changed')
    manifest = json.loads(raw)
    if manifest.get('version') != 1 or not isinstance(manifest.get('files'), dict):
        raise ValueError('Unknown runtime manifest')
    actual = set()
    for path in root.rglob('*'):
        if path.is_symlink():
            raise ValueError('Runtime symlink refused')
        if not path.is_dir():
            actual.add(path.relative_to(root).as_posix())
    if actual != set(manifest['files']) | {MANIFEST}:
        raise ValueError('Runtime file inventory changed')
    for name, record in manifest['files'].items():
        path = root / name
        if (not Path(name).parts or Path(name).is_absolute() or '..' in Path(name).parts
                or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != record['sha256']
                or path.stat().st_mode & 0o777 != record['mode']):
            raise ValueError('Runtime file changed: ' + name)
    return manifest


def command(runtime, script):
    return shlex.join([sys.executable, '-I', str(Path(runtime['root']) / 'autowork/scripts/runtime_bundle.py'),
                       runtime['root'], runtime['sha256'], script])


def main():
    if len(sys.argv) < 4:
        raise SystemExit('usage: runtime_bundle.py ROOT SHA256 SCRIPT [ARG ...]')
    root, digest, script, *args = sys.argv[1:]
    try:
        manifest = verify({'root': root, 'sha256': digest})
        if script not in manifest['files'] or not script.endswith('.py'):
            raise ValueError('Runtime entry is not a pinned Python helper')
    except (OSError, ValueError, KeyError, TypeError) as error:
        raise SystemExit(str(error)) from error
    target = Path(root) / script
    sys.dont_write_bytecode = True
    sys.path.insert(0, str(target.parent))
    sys.argv = [str(target), *args]
    runpy.run_path(str(target), run_name='__main__')


if __name__ == '__main__':
    main()
