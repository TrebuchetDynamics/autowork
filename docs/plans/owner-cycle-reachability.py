#!/usr/bin/env python3
"""TOOLSET-202-9a evidence: conservative import/path closure, not a name allowlist.

Run from the checkout: python3 docs/plans/owner-cycle-reachability.py --verify
The baseline is read from Git without importing code or changing any checkout.
"""
import argparse
import ast
from collections import defaultdict, deque
import io
import json
from pathlib import Path
import re
import subprocess
import tarfile

BASE = 'f9c49c20cb822442f9f85d767eff67e03081d67b'
# This retry reapplies the same deletion; an existing immutable commit avoids
# self-referential hashes in historical link repairs.
FIRST_REMOVAL = '026e23baf4c226aac2c672e3d0e984a77996b9da'
ENGINE = 'skills/autowork/scripts/'
ROOT = Path(__file__).resolve().parents[2]


def snapshot(revision):
    archive = subprocess.check_output(['git', 'archive', revision], cwd=ROOT)
    with tarfile.open(fileobj=io.BytesIO(archive)) as files:
        return {item.name: files.extractfile(item).read().decode('utf-8', 'replace')
                for item in files if item.isfile() and item.name.endswith(
                    ('.py', '.sh', '.md', '.mjs', '.json', '.yaml'))}


def closure(files):
    python = {path for path in files if path.endswith('.py')}
    by_name = defaultdict(set)
    for path in python:
        by_name[Path(path).stem].add(path)
    # SKILL.md explicitly separates these evidence documents from current guidance.
    historical = set(re.findall(r'references/[\w/-]+\.md',
        files['skills/autowork/SKILL.md'].split(
            'Historical native-card evidence, not instructions or prerequisites:', 1)[1]))
    historical = {'skills/autowork/' + path for path in historical}
    historical.update(path for path, text in files.items()
                      if text.startswith('> Historical native-card reference.'))
    roots = {path for path in files if (
        (path.startswith('scripts/') and len(Path(path).parts) == 2
         and path.endswith(('.py', '.sh')))
        or (path.startswith('pi-autowork/pi_autowork/')
            and path.endswith(('.py', '.sh')))
        or (path.startswith(('skills/', 'adapters/skills/')) and path.endswith('/SKILL.md'))
        or (path.startswith('adapters/') and path.endswith('.mjs')))}
    roots.update({ENGINE + 'owner_cycle.py', ENGINE + 'worktree_closeout.py',
                  'adapters/skills/COMMON.md',
                  # AGENTS.md links this current host-hook installation contract;
                  # installed copies are an external consumer of checkout_lock.
                  'docs/worktree-placement.md'})
    # Explicit task-contract retention: only a historical command currently names
    # this collector. Keep it, but do not mislabel it as independently live.
    protected = {ENGINE + 'analyze_audit_logs.py'}
    roots |= protected
    parent = {path: '<entry point>' for path in roots if path in files}
    queue = deque(sorted(parent))
    while queue:
        path = queue.popleft()
        text = files[path]
        targets = set()
        if path.endswith('.py'):
            tree = ast.parse(text, path)
            # Imports (including imports inside functions) and literal file paths
            # model dynamic loaders/subprocesses. Comments, docstrings and bare
            # dictionary keys such as check_receipt are not executable edges.
            docstrings = {id(node.value) for node in ast.walk(tree)
                          if isinstance(node, ast.Expr)
                          and isinstance(node.value, ast.Constant)
                          and isinstance(node.value.value, str)}
            strings = []
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        targets |= by_name[alias.name.split('.')[-1]]
                elif isinstance(node, ast.ImportFrom):
                    targets |= by_name[(node.module or '').split('.')[-1]]
                    for alias in node.names:
                        targets |= by_name[alias.name]
                elif isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in docstrings:
                    strings.append(node.value)
            text = '\n'.join(strings)
        elif path.endswith(('.sh', '.mjs')):
            text = '\n'.join(line.split('#', 1)[0] for line in text.splitlines())
        elif path.endswith('.md'):
            # Bare Reference-map paths matter as well as Markdown links. Historical
            # documents are excluded even when a current page links them as evidence.
            if path == 'skills/autowork/SKILL.md':
                text = text.split('Historical native-card evidence, not instructions or prerequisites:', 1)[0]
            for ref in re.findall(r'\]\(([^)#]+)(?:#[^)]*)?\)|((?:\.\./|references/)[\w./-]+\.md)', text):
                value = ref[0] or ref[1]
                if '://' not in value:
                    resolved = (ROOT / path).parent.joinpath(value).resolve()
                    if resolved.is_relative_to(ROOT):
                        target = resolved.relative_to(ROOT).as_posix()
                        if target.endswith('.md') and target.startswith(('skills/', 'adapters/skills/')):
                            targets.add(target)
        for name in re.findall(r'(?<![\w-])([A-Za-z_]\w*)\.py\b', text):
            # Test discovery/exclusion inventories are not live invocation edges.
            # Explicit imports still reach test_parallel_e2e from bench_parallel.
            if not name.startswith('test_'):
                targets |= by_name[name]
        # Shell entry points and wrappers can refer to the owned shell helper.
        if re.search(r'\bagent_commit\.sh\b', text):
            targets.add(ENGINE + 'agent_commit.sh')
        for target in sorted(targets):
            if target in files and target not in historical and target not in parent:
                parent[target] = path
                queue.append(target)
    modules = {path for path in files if path.startswith(ENGINE)
               and len(Path(path).parts) == 4 and path.endswith('.py')
               and not Path(path).name.startswith('test_')}
    return modules - parent.keys(), parent, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true', help='also assert deletions and live closure in checkout')
    args = parser.parse_args()
    files = snapshot(BASE)
    retired, reached, protected = closure(files)
    result = {'baseline': BASE, 'retired': sorted(retired),
              'production_lines_removed': sum(len(files[path].splitlines()) for path in retired),
              'retained_witnesses': {path: reached[path] for path in sorted(reached)
                                     if path.startswith(ENGINE) and not Path(path).name.startswith('test_')},
              'explicit_retention_not_liveness': sorted(protected)}
    if args.verify:
        names = subprocess.check_output(['git', 'ls-files', '-z'], cwd=ROOT).decode().split('\0')
        current = {path: (ROOT / path).read_text(errors='replace') for path in names
                   if path.endswith(('.py', '.sh', '.md', '.mjs', '.json', '.yaml'))
                   and (ROOT / path).is_file()}
        _, live, _ = closure(current)
        remaining = sorted(path for path in retired if (ROOT / path).exists())
        dangling = sorted(path for path in live if path in retired)
        # Resolve edges using baseline names as well: absent imports must not be
        # invisible simply because their module no longer exists in the checkout.
        augmented = dict(current, **{path: files[path] for path in retired})
        _, live_with_missing, _ = closure(augmented)
        dangling += sorted(retired & live_with_missing.keys())
        history_errors = []
        history_repairs = 0
        for path, original in files.items():
            if not path.startswith('skills/autowork/references/') or not path.endswith('.md'):
                continue
            updated = current.get(path, original)
            if updated == original:
                continue
            normalized = ''.join(line for line in updated.splitlines(keepends=True)
                if not line.startswith(('> Deleted script paths resolve through ',
                                        '> Retired helper paths below resolve through ',
                                        '> See the [removal record]')))
            normalized = re.sub(r'\[([^\]]+) \(archived source\)\]\(https://github.com/'
                r'TrebuchetDynamics/autowork/commit/' + FIRST_REMOVAL + r'\)', r'\1', normalized)
            if normalized != original:
                history_errors.append(path)
            history_repairs += 1
        previously_removed = set(subprocess.check_output(
            ['git', 'diff-tree', '--no-commit-id', '--name-only', '--diff-filter=D',
             '-r', FIRST_REMOVAL], cwd=ROOT).decode().splitlines())
        unproven_links = sorted(retired - previously_removed)
        result['verification'] = {'removal_link_missing_deletions': unproven_links,
                                  'retired_still_present': remaining,
                                  'live_edges_to_deleted': sorted(set(dangling)),
                                  'historical_source_link_repairs': history_repairs,
                                  'historical_body_changes': history_errors}
        print(json.dumps(result, indent=2))
        return int(bool(remaining or dangling or history_errors or unproven_links))
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
