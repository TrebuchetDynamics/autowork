#!/usr/bin/env python3
"""Read exact publication readiness; never push or equate a task ref with main delivery."""
import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import candidate_identity
from start_goal import validate_publication_authority


def readiness(repo, base, commit, authority, profile, task, contract):
    repo = Path(repo).resolve(strict=True)
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', commit):
        raise ValueError('publication requires an exact full commit ID, not HEAD')
    identity = candidate_identity.capture(repo, base, commit)
    result = {'state': 'publication_decision_required', 'candidate': identity,
              'remote': None, 'ref': None, 'remote_commit': None, 'main_delivered': False,
              'boundary': 'read-only readiness; no secret/history qualification or independent permission proof'}
    if authority is None:
        result['reason'] = 'missing exact owner-authorized remote/task ref; do not guess origin'
        return result
    bound = validate_publication_authority(authority, repo, profile, task, contract)
    result.update(remote=bound['remote'], ref=bound['ref'], authority_validation=bound['authority_validation'])
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    def git(*args):
        return subprocess.run(['git', '-C', str(repo), *args], env=env,
                              capture_output=True, text=True, timeout=30)
    configured = git('remote', 'get-url', '--push', '--all', bound['remote'])
    urls = configured.stdout.splitlines()
    if configured.returncode or len(urls) != 1 or not urls[0]:
        result['reason'] = 'authorized remote absent or has multiple push destinations; owner must resolve target'
        return result
    live = git('ls-remote', '--heads', urls[0], bound['ref'])
    if live.returncode:
        result.update(state='publication_unverified', reason='exact push destination cannot be read')
        return result
    rows = [line.split() for line in live.stdout.splitlines()]
    if (len(rows) > 1 or any(len(row) != 2 or row[1] != bound['ref']
            or not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', row[0]) for row in rows)):
        result.update(state='publication_unverified', reason='unexpected exact remote ref response')
        return result
    tip = rows[0][0] if rows else None
    result['remote_commit'] = tip
    if tip == commit:
        result['state'] = 'published_exact_ref'
    elif tip is None:
        result['state'] = 'ready_to_publish'
    else:
        ancestry = git('merge-base', '--is-ancestor', tip, commit)
        result['state'] = ('ready_to_publish' if ancestry.returncode == 0 else
                           'publication_conflict' if ancestry.returncode == 1 else 'publication_unverified')
        result['reason'] = ('observed remote tip is a local ancestor; ordinary fast-forward only' if ancestry.returncode == 0
                            else 'remote tip diverges or ancestry object is absent; never force or guess')
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('repo', 'base', 'commit', 'profile', 'task', 'contract-file'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--authority', help='Existing exact publication owner-evidence JSON; absence remains held')
    args = parser.parse_args()
    try:
        result = readiness(args.repo, args.base, args.commit,
                           json.loads(Path(args.authority).read_text()) if args.authority else None,
                           args.profile, args.task, Path(args.contract_file).read_text().strip())
    except (ValueError, OSError, subprocess.SubprocessError, KeyError, TypeError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['state'] in ('ready_to_publish', 'published_exact_ref') else 1


if __name__ == '__main__':
    sys.exit(main())
