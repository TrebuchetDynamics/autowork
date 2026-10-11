#!/usr/bin/env python3
"""Diagnose and explicitly apply bounded owner recovery, then retry this consumer."""
import argparse
import importlib.util
import json
from pathlib import Path
import subprocess
import sys

import retry_selection
import prepare_prerequisites
import pass_workspace

goals = retry_selection.goals
# Share the canonical transaction context with the existing recovery writer.
spec = importlib.util.spec_from_file_location('owner_recovery', Path(__file__).resolve().parents[2] / 'repo-docs/scripts/recover_backlog.py')
recovery = importlib.util.module_from_spec(spec)
previous = sys.modules.get('goals')
sys.modules['goals'] = goals
try:
    spec.loader.exec_module(recovery)
finally:
    if previous is None:
        del sys.modules['goals']
    else:
        sys.modules['goals'] = previous


def run(args):
    ids = args.tasks.split(',')
    result = {'gate': 'diagnose', 'plan': args.plan, 'task_ids': ids, 'task_goals': {},
              'stages': [], 'required_inputs': [], 'live_ownership': 'unknown',
              'boundary': 'caller owner attestation, not authentication; no board, lease, worker dispatch or publication'}
    args.receipt = result
    def stage(name, repo, **details):
        result['stages'].append({'stage': name, 'revision': goals.revision(repo),
                                 'task_ids': ids, 'task_goals': result['task_goals'], **details})
    def held(gate, required, argv):
        result.update(gate=gate, required_inputs=required, next_action_argv=argv)
        return result
    command = [sys.executable, str(Path(__file__).resolve()), args.consumer,
               '--plan', args.plan, '--tasks', args.tasks]
    if args.canonical_repo:
        command += ['--canonical-repo', args.canonical_repo]
    with goals.coordination(args.consumer, args.canonical_repo) as repo:
        revision = goals.revision(repo)
        result.update(authoritative_repo=str(repo), initial_revision=revision)
        if goals.checked_bytes(repo / 'goals.json') is None:
            stage('diagnose', repo)
            return held('ledger', ['goals.json', 'existing accepted ledger from integration owner; no generated replacement'],
                        [sys.executable, str(Path(recovery.__file__).with_name('goals.py')), 'validate', str(repo)])
        data = goals.load(repo)
        problems = goals.errors(data)
        if problems:
            return held('ledger', problems, [sys.executable, str(Path(recovery.__file__).with_name('goals.py')), 'validate', str(repo)])
        tasks = {t['id']: t for t in data['tasks']}
        if len(ids) != len(set(ids)) or any(tid not in tasks for tid in ids):
            raise ValueError('unique existing literal task IDs required')
        result['task_goals'] = {tid: tasks[tid]['goal'] for tid in ids}
        stage('diagnose', repo)
        if any(tasks[tid]['status'] != 'open' for tid in ids):
            return held('ownership', ['reconcile original task ownership; only unclaimed open ledger tasks can be repaired'],
                        [sys.executable, str(Path(recovery.__file__).with_name('goals.py')), 'focus', str(repo), '--json'])
    selected = retry_selection.select(repo, plan=args.plan, task_ids=ids)
    result['selection'] = selected
    reasons = selected['reasons']
    repairable = bool(reasons) and all(reason == 'missing TODO.md' or any(reason in (
        tid + ': missing or duplicate task body', tid + ': Sources do not link accepted plan') for tid in ids)
        for reason in reasons)
    if repairable:
        required = ['authority', 'expected_revision=' + revision,
                    'source_commit (full immutable same-task history if body is absent)',
                    'owner and evidence_ref; no_overlapping_writer=true']
        if not args.apply:
            return held('accepted_body_repair', required, command + ['--apply', '--authority', '<existing-owner-authority.json>'])
        if not args.authority:
            return held('owner_authority', required, command + ['--apply', '--authority', '<existing-owner-authority.json>'])
        authority = json.loads(Path(args.authority).read_text())
        expected = {'version': 1, 'workspace': str(repo), 'plan': args.plan, 'task_ids': ids,
                    'expected_revision': revision, 'no_overlapping_writer': True}
        if (any(authority.get(k) != v for k, v in expected.items())
                or any(not isinstance(authority.get(k), str) or not authority[k].strip()
                       for k in ('owner', 'evidence_ref')) or 'source_commit' not in authority):
            raise ValueError('exact current owner/revision/source authority required')
        with goals.coordination(repo) as locked:
            if goals.revision(locked) != revision:
                raise ValueError('stale revision; no recovery write')
            repairs = recovery.repair(locked, args.plan, ids, authority['source_commit'])
            stage('repair', locked, repairs=repairs, authority=authority)
        selected = retry_selection.select(repo, plan=args.plan, task_ids=ids)
        result['selection'] = selected
        stage('retry_selection', repo, state=selected['state'])
    if selected['state'] != 'ready_for_autogoal':
        return held('consumer_readiness', selected['reasons'],
                    [sys.executable, str(Path(retry_selection.__file__)), str(repo), '--plan', args.plan, '--tasks', args.tasks])
    result['gate'] = 'ready_for_autogoal'
    if args.prerequisite_request:
        request = json.loads(Path(args.prerequisite_request).read_text())
        required = ['target', 'base', 'snapshot', 'attribution', 'profile', 'task', 'checks']
        if not args.apply:
            return held('prerequisites', required, command + ['--apply', '--prerequisite-request', args.prerequisite_request])
        if request.get('source') != str(repo) or any(k not in request for k in required):
            raise ValueError('existing explicit prerequisite request bound to canonical consumer required')
        prepared = prepare_prerequisites.prepare(repo, **{k: request[k] for k in required})
        result['prerequisites'] = prepared
        stage('prerequisites', repo, candidate_identity=prepared['candidate_identity'])
        if not prepared['source_fresh']:
            return held('source_freshness', ['reconcile changed source; do not refresh attribution'], command)
        result['selection'] = retry_selection.select(repo, plan=args.plan, task_ids=ids)
        stage('retry_selection', repo, state=result['selection']['state'])
        if result['selection']['state'] != 'ready_for_autogoal':
            return held('consumer_readiness', result['selection']['reasons'], command)
        if request.get('candidate_target'):
            candidate = pass_workspace.prepare(repo, request['candidate_target'], request['base'], prepared['commit'],
                {'refs/heads/' + prepared['branch']: prepared['commit']}, request['required_paths'])
            snapshot = request['snapshot']
            ledger = next(row['sha256'] for row in snapshot['files'] if row['path'] == 'goals.json')
            manifest = {'candidate_identity': candidate, 'source_workspace': str(repo),
                        'files': snapshot['files'], 'ledger_sha256': ledger}
            pass_workspace.verify(manifest, request['candidate_target'])
            result.update(gate='candidate_validated', candidate_manifest=manifest)
            stage('candidate_validation', repo, candidate_identity=candidate)
            return result
    if args.candidate_request:
        request = json.loads(Path(args.candidate_request).read_text())
        if request.get('source') != str(repo):
            raise ValueError('candidate request must name canonical consumer')
        if not args.apply:
            return held('candidate', ['explicit target/base/candidate/prerequisites/required_paths/snapshot'],
                        command + ['--apply', '--candidate-request', args.candidate_request])
        snapshot = request['snapshot']
        if snapshot['workspace'] != str(repo):
            raise ValueError('candidate snapshot must name canonical consumer')
        candidate = pass_workspace.prepare(repo, request['target'], request['base'], request['candidate'],
                                           request['prerequisites'], request['required_paths'])
        ledger = next(row['sha256'] for row in snapshot['files'] if row['path'] == 'goals.json')
        manifest = {'candidate_identity': candidate, 'source_workspace': str(repo),
                    'files': snapshot['files'], 'ledger_sha256': ledger}
        pass_workspace.verify(manifest, request['target'])
        result.update(gate='candidate_validated', candidate_manifest=manifest)
        stage('candidate_validation', repo, candidate_identity=candidate)
    else:
        result['required_inputs'] = ['candidate_request: explicit target/base/candidate/prerequisites/required_paths/snapshot; or prerequisite_request with existing attribution']
        result['next_action_argv'] = command + ['--apply', '--candidate-request', '<existing-candidate-request.json>']
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer')
    for name in ('plan', 'tasks'):
        parser.add_argument('--' + name, required=True)
    for name in ('canonical-repo', 'authority', 'prerequisite-request', 'candidate-request'):
        parser.add_argument('--' + name)
    parser.add_argument('--apply', action='store_true')
    args = parser.parse_args()
    try:
        result = run(args)
    except (ValueError, OSError, TypeError, KeyError, StopIteration, subprocess.SubprocessError) as error:
        result = {**getattr(args, 'receipt', {}), 'gate': 'refused', 'task_ids': args.tasks.split(','), 'plan': args.plan, 'error': str(error)}
    print(json.dumps(result, indent=2))
    return 0 if result['gate'] in ('ready_for_autogoal', 'candidate_validated') else 1


if __name__ == '__main__':
    sys.exit(main())
