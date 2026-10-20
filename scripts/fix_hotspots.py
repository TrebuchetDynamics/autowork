#!/usr/bin/env python3
"""Report fix-of-a-fix hotspots: files that recent fix commits touch most.

A fix commit has a `fix:` or `fix(scope):` subject, or a `Fixes: <sha>` trailer. Each file
gets its fix count, its total commit count and their ratio within --since; a chain is a
file with --chain-min or more fixes inside --chain-days. Use it to choose where a
refactor or missing tests would prevent the next fix.
"""
import argparse
import json
import re
import subprocess
import sys

FIX_SUBJECT = re.compile(r'^fix(\(.+\))?!?:')
PLANNING = frozenset({'TODO.md', 'TODO.archive.md', 'goals.json', 'CHANGELOG.md', 'BLOCKERS.md'})
DAY = 86400
RECORD, FIELD = '\x1e', '\x1f'


def commits(repo, since):
    """(timestamp, is_fix, files) for each non-merge commit since ``since``."""
    fmt = f'{RECORD}%H{FIELD}%ct{FIELD}%s{FIELD}%(trailers:key=Fixes,valueonly,separator=%x2c){FIELD}'
    out = subprocess.run(['git', '-C', repo, 'log', '--no-merges', '--no-renames', f'--since={since}',
                          f'--format={fmt}', '--name-only'],
                         check=True, capture_output=True, text=True, errors='replace').stdout
    for record in out.split(RECORD)[1:]:
        _sha, stamp, subject, fixes, names = record.split(FIELD)
        files = [name for name in names.splitlines()
                 if name and name.rsplit('/', 1)[-1] not in PLANNING]
        yield int(stamp), bool(FIX_SUBJECT.match(subject) or fixes.strip()), files


def longest_chain(stamps, span):
    """Most fix timestamps inside any window of ``span`` seconds, with its start and end."""
    stamps = sorted(stamps)
    best, start = (0, 0, 0), 0
    for end, stamp in enumerate(stamps):
        while stamp - stamps[start] > span:
            start += 1
        if end - start + 1 > best[0]:
            best = (end - start + 1, stamps[start], stamp)
    return best


def report(repo, since, top, chain_days, chain_min):
    totals, fixes = {}, {}
    for stamp, is_fix, files in commits(repo, since):
        for name in files:
            totals[name] = totals.get(name, 0) + 1
            if is_fix:
                fixes.setdefault(name, []).append(stamp)
    chains = []
    for name, stamps in fixes.items():
        count, first, last = longest_chain(stamps, chain_days * DAY)
        if count >= chain_min:
            chains.append({'path': name, 'fixes': count, 'first': first, 'last': last})
    chains.sort(key=lambda chain: (-chain['fixes'], chain['path']))
    chained = {chain['path'] for chain in chains}
    rows = [{'path': name, 'fixes': len(stamps), 'commits': totals[name],
             'ratio': round(len(stamps) / totals[name], 3), 'chain': name in chained}
            for name, stamps in fixes.items()]
    rows.sort(key=lambda row: (-row['fixes'], -row['ratio'], row['path']))
    return {'since': since, 'chain_days': chain_days, 'chain_min': chain_min,
            'files': rows[:top], 'chains': chains}


def table(data):
    lines = [f"Fix hotspots since {data['since']} (fix commits per file):"]
    if not data['files']:
        return '\n'.join(lines + ['  none'])
    width = max(len(row['path']) for row in data['files'])
    lines.append(f"  {'file'.ljust(width)}  fixes  commits  ratio  chain")
    for row in data['files']:
        lines.append(f"  {row['path'].ljust(width)}  {row['fixes']:>5}  {row['commits']:>7}  "
                     f"{row['ratio']:>5.2f}  {'yes' if row['chain'] else ''}")
    shown, rest = data['chains'][:len(data['files'])], len(data['chains']) - len(data['files'])
    lines.append(f"Chains ({data['chain_min']}+ fixes within {data['chain_days']:g} days, longest first):")
    lines.extend(f"  {chain['path']}: {chain['fixes']}" for chain in shown)
    lines.append(f'  ... {rest} more (--json lists all)' if rest > 0 else '' if shown else '  none')
    return '\n'.join(line for line in lines if line)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--repo', default='.', help='repository (default: current directory)')
    parser.add_argument('--since', default='14.days', help='git --since window (default: 14.days)')
    parser.add_argument('--top', type=int, default=15, help='files to list (default: 15)')
    parser.add_argument('--chain-days', type=float, default=3, help='chain window in days (default: 3)')
    parser.add_argument('--chain-min', type=int, default=3, help='fixes that make a chain (default: 3)')
    parser.add_argument('--json', action='store_true', help='print JSON instead of a table')
    args = parser.parse_args(argv)
    try:
        data = report(args.repo, args.since, args.top, args.chain_days, args.chain_min)
    except subprocess.CalledProcessError as error:
        print(f'fix_hotspots: git failed: {error.stderr.strip()}', file=sys.stderr)
        return 2
    print(json.dumps(data, indent=2) if args.json else table(data))
    return 0


if __name__ == '__main__':
    sys.exit(main())
