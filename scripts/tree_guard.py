#!/usr/bin/env python3
"""Refuse a tree with conflict markers, Python that does not compile or invalid JSON.

Checks the Git-tracked files of the worktree (default), of a commit (--rev, read from
Git objects so a candidate can be vetted without a checkout) or of the index (--staged).
Prints `path:line: reason` per problem and exits 1, or one OK line and exits 0.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

MARKER = re.compile(rb'^(?:<{7}(?: |$)|={7}$|>{7}(?: |$)|\|{7}(?: |$))')
# Files that legitimately hold marker lines. A file may instead carry this comment in
# its first ALLOW_LINES lines.
ALLOW_MARKERS = frozenset()
ALLOW_COMMENT = b'tree-guard: allow-markers'
ALLOW_LINES = 5
SKIP_MODES = {'120000', '160000'}  # symlinks, submodules


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True,
                          capture_output=True).stdout


def entries(repo, rev, staged, paths):
    """(path, blob-or-None) for each tracked regular file; None means read the worktree."""
    spec = ['--', *paths] if paths else []
    if rev:
        raw = git(repo, 'ls-tree', '-r', '-z', '--full-tree', rev, *spec)
        for item in filter(None, raw.split(b'\0')):
            meta, path = item.split(b'\t', 1)
            mode, kind, blob = meta.decode().split()
            if kind == 'blob' and mode not in SKIP_MODES:
                yield path.decode('utf-8', 'surrogateescape'), blob
        return
    raw = git(repo, 'ls-files', '-s', '-z', *spec)
    seen = set()
    for item in filter(None, raw.split(b'\0')):
        meta, path = item.split(b'\t', 1)
        mode, blob, _stage = meta.decode().split()
        name = path.decode('utf-8', 'surrogateescape')
        if mode in SKIP_MODES or name in seen:  # unmerged paths list several stages
            continue
        seen.add(name)
        yield name, (blob if staged else None)


def contents(repo, items):
    """(path, bytes) for each entry; blobs are read through one `git cat-file --batch`."""
    items = list(items)
    blobs = [blob for _path, blob in items if blob]
    data = {}
    if blobs:
        out = subprocess.run(['git', '-C', str(repo), 'cat-file', '--batch'], check=True,
                             input=''.join(b + '\n' for b in blobs).encode(),
                             capture_output=True).stdout
        offset = 0
        for blob in blobs:
            end = out.index(b'\n', offset)
            size = int(out[offset:end].split()[2])
            data[blob] = out[end + 1:end + 1 + size]
            offset = end + 2 + size
    for path, blob in items:
        if blob:
            yield path, data[blob]
            continue
        file = Path(repo) / path
        if file.is_symlink() or not file.is_file():  # deleted in the worktree, or a link
            continue
        yield path, file.read_bytes()


def check(path, body):
    """Problems as (line, reason)."""
    if b'\0' in body[:8192]:
        return []
    problems = []
    head = body.split(b'\n', ALLOW_LINES)[:ALLOW_LINES]
    if path not in ALLOW_MARKERS and not any(ALLOW_COMMENT in line for line in head):
        for number, line in enumerate(body.split(b'\n'), 1):
            if MARKER.match(line.rstrip(b'\r')):
                problems.append((number, 'conflict marker'))
    if path.endswith('.py'):
        try:
            compile(body, path, 'exec', dont_inherit=True)
        except SyntaxError as error:
            problems.append((error.lineno or 1, f'python: {error.msg}'))
        except ValueError as error:
            problems.append((1, f'python: {error}'))
    elif path.endswith('.json'):
        try:
            json.loads(body.decode('utf-8'))
        except UnicodeDecodeError as error:
            problems.append((1, f'json: {error.reason}'))
        except json.JSONDecodeError as error:
            problems.append((error.lineno, f'json: {error.msg}'))
    return problems


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', default='.', help='repository to check (default: current directory)')
    source = parser.add_mutually_exclusive_group()
    source.add_argument('--rev', help='check the tree of this commit instead of the worktree')
    source.add_argument('--staged', action='store_true', help='check the index instead of the worktree')
    parser.add_argument('paths', nargs='*', help='limit the check to these pathspecs')
    args = parser.parse_args(argv)
    try:
        items = list(entries(args.repo, args.rev, args.staged, args.paths))
        files = list(contents(args.repo, items))
    except subprocess.CalledProcessError as error:
        print(f'tree_guard: git failed: {error.stderr.decode(errors="replace").strip()}', file=sys.stderr)
        return 2
    failures = 0
    for path, body in files:
        for line, reason in check(path, body):
            print(f'{path}:{line}: {reason}')
            failures += 1
    if failures:
        print(f'tree_guard: FAIL: {failures} problem(s) in {len(files)} files', flush=True)
        return 1
    python = sum(path.endswith('.py') for path, _ in files)
    data = sum(path.endswith('.json') for path, _ in files)
    print(f'tree_guard: OK: {len(files)} files ({python} Python, {data} JSON); no conflict markers',
          flush=True)
    return 0


if __name__ == '__main__':
    sys.exit(main())
