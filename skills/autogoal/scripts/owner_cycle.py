#!/usr/bin/env python3
"""Run bounded owner recovery, persist evidence, and optionally use native handoff.

Missing canonical inputs become deduplicated integration requests, never invented
backlogs. Request acknowledgement is caller evidence, not authentication.
"""
import argparse
from contextlib import redirect_stdout
from datetime import datetime, timezone
import fcntl
import hashlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import uuid

import owner_unblock
import retry_selection


def read_json(path, default=None):
    if path.is_symlink():
        raise ValueError('refuse symlinked state file')
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    if path.is_symlink() or path.parent.is_symlink():
        raise ValueError('refuse symlinked receipt destination')
    path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd, temporary = tempfile.mkstemp(prefix='.cycle-', dir=path.parent)
    try:
        with os.fdopen(fd, 'w') as stream:
            stream.write(value if isinstance(value, str) else json.dumps(value, indent=2) + '\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary): os.unlink(temporary)


def fingerprint(data):
    return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def handoff(args, task, consumer=None):
    request = read_json(Path(args.handoff_request))
    consumer = consumer or str(Path(args.consumer).resolve())
    if not isinstance(request, dict):
        raise ValueError('handoff request must be an object')
    if (request.get('consumer') != consumer or
            request.get('task_id') != task['id']):
        raise ValueError('handoff request must bind the same consumer and selected task')
    options = request.get('options', {})
    allowed = {'profile', 'title', 'contract-file', 'ledger-mode', 'integration-owner',
               'publication-authority', 'goal-max-turns', 'source-snapshot', 'base',
               'candidate', 'required-path', 'prerequisite', 'pass-root', 'disjoint-terminal-triage'}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError('unsupported native handoff options')
    argv = [sys.executable, str(Path(__file__).with_name('start_goal.py')),
            '--workspace', request['consumer'], '--goal-task', task['id']]
    for key, value in options.items():
        for item in value if isinstance(value, list) else [value]:
            if not isinstance(item, (str, int)) or isinstance(item, bool):
                raise ValueError('invalid handoff option value')
            argv += ['--' + key, str(item)]
    # The existing helper owns live ownership, admission, snapshot and duplicate
    # card checks. A timeout is not permission to retry an uncertain dispatch.
    result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    try:
        payload = json.loads(result.stdout)
        if not isinstance(payload, dict):
            raise ValueError('native result must be an object')
    except ValueError:
        payload = {'outcome': 'unverified', 'error': result.stderr[-2000:]}
    return {'argv': argv, 'exit_code': result.returncode, 'result': payload}


def cycle(args):
    if args.acknowledge and (not args.apply or not args.integration_owner or not args.owner_evidence):
        raise ValueError('acknowledgement requires --apply, named owner and evidence')
    state = Path(args.state_dir).expanduser().absolute()
    if any(p.is_symlink() for p in (state, *state.parents)):
        raise ValueError('receipt directory must not traverse symlinks')
    state.mkdir(parents=True, exist_ok=True, mode=0o700)
    fd = os.open(state / '.owner-cycle.lock', os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    with os.fdopen(fd, 'a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as exc:
            raise ValueError('owner cycle already running; preserve that occurrence') from exc
        return run_locked(args, state)


def run_locked(args, state):
    previous = read_json(state / 'unblock-latest.json', {})
    now = datetime.now(timezone.utc).isoformat()
    result = {'version': 1, 'timestamp': now, 'run_id': uuid.uuid4().hex,
              'task_ids': args.tasks.split(','), 'plan': args.plan, 'completed_tasks': [],
              'dispatch_attempted': False, 'implementation': 'not_executed',
              'delivery': 'no product commit or push by this runner', 'outcome': 'BLOCKED',
              'work_search': {'state': 'not_evaluated'},
              'ownership': 'unverified; native handoff must reconcile current ownership'}
    try:
        with redirect_stdout(io.StringIO()):
            recovery = owner_unblock.run(args)
    except (ValueError, OSError, TypeError, AttributeError, KeyError, StopIteration, SystemExit, subprocess.SubprocessError) as exc:
        recovery = {**getattr(args, 'receipt', {}), 'gate': 'refused', 'error': str(exc)}
    result['recovery'] = recovery
    consumer = recovery.get('authoritative_repo', str(Path(args.consumer).resolve()))
    result['consumer'] = consumer
    plan_path = Path(consumer) / args.plan.split('#', 1)[0]
    # Content identity, not run timestamps or mutable audit text.
    plan_digest = None
    if plan_path.resolve().is_relative_to(Path(consumer).resolve()) and plan_path.is_file() and not plan_path.is_symlink():
        plan_digest = hashlib.sha256(plan_path.read_bytes()).hexdigest()
    key = fingerprint({'consumer': consumer, 'plan': args.plan, 'plan_digest': plan_digest,
                       'tasks': result['task_ids'], 'revision': recovery.get('initial_revision'),
                       'gate': recovery['gate'], 'reasons': recovery.get('required_inputs', []),
                       'selection': recovery.get('selection', {}).get('reasons', [])})
    result.update(fingerprint=key, unchanged_runs=(previous.get('unchanged_runs', 0) + 1
                  if previous.get('fingerprint') == key else 1))
    selection = recovery.get('selection', {})
    result['selected_task'] = selection.get('selected_task')
    ready = recovery['gate'] in ('ready_for_autogoal', 'candidate_validated')
    if ready:
        result.update(outcome='READY', action='prepare_native_handoff',
                      next_action='Use the existing native handoff with explicit contract and source snapshot')
        if any(s.get('stage') == 'repair' for s in recovery.get('stages', [])):
            result['outcome'] = 'PROGRESS'
        if args.handoff_request and args.apply and result['selected_task']:
            result['dispatch_attempted'] = True
            try:
                result['handoff'] = handoff(args, result['selected_task'], consumer)
                native = result['handoff']['result']
                if result['handoff']['exit_code'] != 0:
                    result.update(outcome='FAILED', next_action='Reconcile native state before retry; dispatch outcome may be unknown')
                elif native.get('outcome') == 'handed_off':
                    result['outcome'] = 'QUEUED'  # card status alone is not worker liveness
                    result['next_action'] = 'Observe original native card/run; do not dispatch a replacement'
                elif native.get('outcome') in ('already_owned', 'workspace_owned'):
                    result.update(outcome='BLOCKED', next_action='Reconcile the original native owner/card')
                else:
                    result.update(outcome='BLOCKED', next_action='Native admission not established; inspect handoff receipt')
            except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
                result.update(outcome='FAILED', handoff={'error': str(exc)},
                              next_action='Reconcile native state before retry; dispatch outcome may be unknown')
    else:
        result['action'] = 'owner_followup_required' if result['unchanged_runs'] >= 2 else 'owner_input_required'
        request_id = fingerprint({'consumer': consumer, 'plan': args.plan, 'tasks': result['task_ids'],
                                  'owner': args.integration_owner, 'blocker': key})
        path = state / 'requests' / (request_id + '.json')
        request = read_json(path)
        if request is None:
            request = {'version': 1, 'request_id': request_id, 'created_at': now, 'status': 'pending',
                       'owner': args.integration_owner or 'unassigned', 'consumer': consumer,
                       'plan': args.plan, 'task_ids': result['task_ids'], 'gate': recovery['gate'],
                       'required_inputs': recovery.get('required_inputs', []),
                       'proposal': args.proposal, 'evidence': args.owner_evidence,
                       'instruction': 'Reconcile accepted canonical inputs under existing integration ownership, then rerun owner cycle',
                       'boundary': 'Local request only; not delivered, acknowledged or integration authority'}
            save(path, request)
        updates = request.setdefault('evidence_updates', [])
        evidence = {'proposal': args.proposal, 'evidence': args.owner_evidence}
        if any(evidence.values()) and evidence not in updates:
            updates.append(evidence)
            save(path, request)
        if args.acknowledge:
            if not args.apply or not args.integration_owner or not args.owner_evidence:
                raise ValueError('acknowledgement requires --apply, named owner and evidence')
            request.update(status='acknowledged', acknowledged_at=now,
                           acknowledgement={'owner': args.integration_owner, 'evidence': args.owner_evidence,
                                            'verification': 'caller-supplied; not authentication'})
            save(path, request)
        result.update(integration_request=str(path), request_status=request['status'],
                      next_action=('Follow up existing integration request with its owner; do not repeat unchanged validation'
                                   if result['unchanged_runs'] >= 2 else
                                   'Integration owner must reconcile canonical inputs; see integration request'))
        # One bounded canonical selection, never an invented task or a focus change.
        try:
            alternate = retry_selection.select(consumer)
            result['work_search'] = {'state': alternate['state'], 'candidate': alternate.get('selected_task'),
                                     'reasons': alternate.get('reasons', []),
                                     'boundary': 'canonical selector only; source/test seam search still required when no eligible candidate'}
        except (ValueError, OSError, TypeError, KeyError, SystemExit) as exc:
            result['work_search'] = {'state': 'unavailable', 'reason': str(exc)}
    save(state / 'history' / (result['run_id'] + '.json'), result)
    save(state / 'unblock-latest.json', result)
    save(state / 'report-latest.txt', render(result))
    return result


def render(result):
    task = result.get('selected_task') or {}
    label = task.get('id') or ', '.join(result['task_ids'])
    title = task.get('title', 'title unverified')
    return (f"{result['outcome']} — 0 tasks completed by this cycle\n"
            f"Task: {label} — {title}\n"
            f"Recovery: {result['recovery']['gate']}; unchanged runs: {result['unchanged_runs']}\n"
            f"Next: {result['next_action']}\nDelivery: {result['delivery']}\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer')
    parser.add_argument('--plan', required=True)
    parser.add_argument('--tasks', required=True)
    parser.add_argument('--state-dir', required=True, help='Private owning-profile autogoal directory')
    for name in ('canonical-repo', 'authority', 'prerequisite-request', 'candidate-request',
                 'handoff-request', 'integration-owner', 'proposal', 'owner-evidence'):
        parser.add_argument('--' + name)
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--acknowledge', action='store_true', help='Record supplied owner acknowledgement, not inferred consent')
    args = parser.parse_args(argv)
    try:
        result = cycle(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result, indent=2))
    return 0 if result['outcome'] in ('READY', 'PROGRESS', 'QUEUED') else 1


if __name__ == '__main__':
    raise SystemExit(main())
