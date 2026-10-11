#!/usr/bin/env python3
"""Commit explicitly attributed prerequisite bytes in a private pinned worktree.

Attribution is the integration owner's caller attestation, not invented approval.
Never publishes, changes the source index/HEAD or adopts files outside the receipt.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

import candidate_identity
import source_freshness


def prepare(source, target, base, snapshot, attribution, profile, task, checks, timeout=180):
    source = Path(source).resolve(strict=True)
    target = Path(target).resolve()
    candidate_identity.capture(source, base, base)
    if (target.exists() or target == source or target.is_relative_to(source)
            or source.is_relative_to(target)):
        raise ValueError('new private worktree outside the source required')
    if (not isinstance(attribution, dict) or attribution.get('version') != 1
            or attribution.get('workspace') != str(source) or attribution.get('base') != base
            or attribution.get('files') != snapshot.get('files')
            or any(not isinstance(attribution.get(k), str) or not attribution[k].strip()
                   for k in ('owner', 'evidence_ref'))):
        raise ValueError('exact owner-attributed prerequisite files, base and provenance required')
    if (not checks or timeout <= 0 or any(not isinstance(c, list) or not c
            or any(not isinstance(a, str) or not a for a in c) for c in checks)):
        raise ValueError('explicit nonempty acceptance argv checks required')
    for token in (profile, task):
        if not re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.-]*', token) or '..' in token or token.endswith(('.', '.lock')):
            raise ValueError('literal valid profile/task ref components required')
    ref = 'refs/heads/agent/' + profile + '/' + task
    env = {k: v for k, v in os.environ.items() if not k.startswith('GIT_')}
    exists = subprocess.run(['git', '-C', str(source), 'show-ref', '--verify', '--quiet', ref], env=env)
    if exists.returncode != 1:
        raise ValueError('prerequisite ref already exists or cannot be inspected; reconcile instead of overwrite')
    if not source_freshness.check(snapshot, source)['fresh']:
        raise ValueError('stale attributed source inputs')
    inputs = {}
    for row in snapshot['files']:
        if row['sha256'] is None:
            raise ValueError('prerequisite files must exist; deletions require separate reconciliation')
        data = (source / row['path']).read_bytes()
        if hashlib.sha256(data).hexdigest() != row['sha256']:
            raise ValueError('source changed while reading attributable input')
        inputs[row['path']] = data
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(['git', '-C', str(source), 'worktree', 'add', '--detach', str(target), base],
                   env=env, check=True, capture_output=True, timeout=30)
    try:
        for name, data in inputs.items():
            source_freshness.capture(target, [name])  # Refuse inherited symlinks/credential paths too.
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        if not source_freshness.check(snapshot, source)['fresh']:
            raise ValueError('source changed before prerequisite verification')
        command = [sys.executable, str(Path(__file__).with_name('finish_task.py')),
                   '--repo', str(target), '--profile', profile, '--card', task,
                   '--message', 'Prepare attributed backlog prerequisites', '--timeout', str(timeout)]
        for check in checks:
            command += ['--check-json', json.dumps(check)]
        command += list(inputs)
        result = subprocess.run(command, env={**env, 'AGENT_COMMIT_EXPECTED_BASE': base},
                                capture_output=True, text=True,
                                timeout=timeout * (len(checks) + 1) + 10)
        if result.returncode:
            raise ValueError('prerequisite acceptance/commit failed: ' + result.stdout + result.stderr)
        receipt = json.loads(result.stdout)
        if receipt['status'] not in ('committed', 'no_changes'):
            raise ValueError('prerequisite commit did not complete')
        commit = receipt.get('commit', receipt.get('source_commit'))
        identity = candidate_identity.capture(source, base, commit)
        for name, data in inputs.items():
            actual = subprocess.check_output(['git', '-C', str(source), 'show', commit + ':' + name], env=env, timeout=10)
            if actual != data:
                raise ValueError('committed prerequisite bytes differ from attribution')
        fresh = source_freshness.check(snapshot, source)['fresh']
        return {**receipt, 'candidate_identity': identity, 'source_fresh': fresh,
                'attribution': attribution, 'workspace': str(target),
                'authority_validation': 'caller_attribution_not_independent_authorization',
                'publication': 'not_authorized_by_preparation',
                'boundary': 'immutable inputs only; recheck consumer readiness and live ownership before dispatch'}
    except Exception:
        subprocess.run(['git', '-C', str(source), 'worktree', 'remove', '--force', str(target)],
                       env=env, check=True, capture_output=True, timeout=30)
        raise


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('source', 'target', 'base', 'snapshot', 'attribution', 'profile', 'task'):
        parser.add_argument('--' + name, required=True)
    parser.add_argument('--check-json', action='append', required=True)
    parser.add_argument('--timeout', type=int, default=180)
    args = parser.parse_args()
    try:
        result = prepare(args.source, args.target, args.base, json.loads(Path(args.snapshot).read_text()),
                         json.loads(Path(args.attribution).read_text()), args.profile, args.task,
                         [json.loads(check) for check in args.check_json], args.timeout)
    except (ValueError, OSError, subprocess.SubprocessError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['source_fresh'] else 1


if __name__ == '__main__':
    sys.exit(main())
