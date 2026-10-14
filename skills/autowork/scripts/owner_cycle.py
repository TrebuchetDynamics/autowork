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
import progress_runtime
import backlog_plan
import ready_preflight
import reconcile
import disjoint_fallback


def read_json(path, default=None):
    if path.is_symlink():
        raise ValueError('refuse symlinked state file')
    return json.loads(path.read_text()) if path.exists() else default


def save(path, value):
    path = progress_runtime.private_path(path)
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
               'candidate', 'required-path', 'prerequisite', 'pass-root', 'disjoint-terminal-triage',
               'fallback-file', 'disjoint-blocked-handoff', 'registration-declaration',
               'registration-native-python'}
    if not isinstance(options, dict) or set(options) - allowed:
        raise ValueError('unsupported native handoff options')
    argv = [sys.executable, str(Path(__file__).with_name('start_goal.py')),
            '--workspace', request['consumer'], '--goal-task', task['id']]
    if getattr(args, '_admission_attempt', None):
        if (hashlib.sha256(Path(args.handoff_request).read_bytes()).hexdigest() != args._admission_request_sha256
                or hashlib.sha256(Path(argv[1]).read_bytes()).hexdigest() != args._admission_launcher_sha256):
            raise ValueError('admission request or trusted launcher changed before launch')
        argv += ['--admission-attempt', args._admission_attempt,
                 '--admission-request-sha256', args._admission_request_sha256]
    for key, value in options.items():
        for item in value if isinstance(value, list) else [value]:
            if not isinstance(item, (str, int)) or isinstance(item, bool):
                raise ValueError('invalid handoff option value')
            argv += ['--' + key, str(item)]
    # The existing helper owns live ownership, admission, snapshot and duplicate
    # card checks. A timeout is not permission to retry an uncertain dispatch.
    result = subprocess.run(argv, capture_output=True, text=True, timeout=120)
    if (getattr(args, '_admission_attempt', None)
            and hashlib.sha256(Path(argv[1]).read_bytes()).hexdigest() != args._admission_launcher_sha256):
        raise ValueError('trusted launcher changed during admission; reconcile original attempt')
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
    # Reuse an existing exact authority, never synthesize or refresh its revision.
    if args.apply and not args.authority and (state / 'recovery-authority.json').is_file():
        args.authority = str(progress_runtime.private_path(state / 'recovery-authority.json'))
    result = {'version': 1, 'timestamp': now, 'run_id': uuid.uuid4().hex,
              'task_ids': args.tasks.split(',') if args.tasks else [], 'plan': args.plan, 'completed_tasks': [],
              'scope': getattr(args, 'scope', 'tasks'),
              'coordination_mode': 'owner' if getattr(args, 'require_owner', False) else 'autonomous',
              'dispatch_attempted': False, 'implementation': 'not_executed', 'unchanged_runs': 0,
              'delivery': 'no product commit or push by this runner', 'outcome': 'BLOCKED',
              'work_search': {'state': 'not_evaluated'},
              'ownership': 'unverified; native handoff must reconcile current ownership'}
    composed = bool(getattr(args, 'profile', None) and args.apply and not args.handoff_request)
    if composed:
        try:
            prefix = ['hermes', '-p', args.profile]
            policy_path = getattr(args, 'local_policy', None)
            policy = json.loads(Path(policy_path).read_text()) if policy_path else None
            if policy_path and not isinstance(policy, dict):
                raise ValueError('local policy must be an object')
            prior = reconcile.reconcile(prefix, reconcile.profile_home(prefix), args.profile,
                                        repo=Path(args.consumer), local_policy=policy)
            result['reconciliation'] = prior
            distinct = None
            if getattr(args, 'disjoint_blocked_handoff', None):
                if prior.get('next_action') != 'recover_original_card' or not args.tasks or ',' in args.tasks:
                    raise ValueError('Disjoint fallback requires one explicit accepted task and original blocked card')
                distinct = disjoint_fallback.verify(args.disjoint_blocked_handoff,
                    reconcile.profile_home(prefix) / 'autowork/goal-handoff.json',
                    args.consumer, args.profile, args.tasks, args.registration_declaration)
                if distinct['original_card'] != prior.get('task_id'):
                    raise ValueError('Fallback original card differs from current reconciliation')
                result['disjoint_fallback'] = distinct
            # Historical closeout may bind different implementation/review runs;
            # ownership still describes the latest run, not an adopted worker.
            if (prior.get('next_action') == 'reconcile_task_and_select'
                    and not prior.get('delivery', {}).get('delivered')):
                raise ValueError('Historical closeout lacks verified delivery')
            # Historical verified delivery releases selection only. Fresh target,
            # ownership and admission checks still belong to the next handoff;
            # never repeat the old merge or infer publication from this readback.
            if not distinct and prior.get('outcome') != 'no_handoff' and prior.get('next_action') != 'reconcile_task_and_select':
                action = prior['next_action']
                # A live/queued card needs observation, and terminal work needs
                # coordinator action. Neither is an unavailable prerequisite.
                outcome = ('WAITING' if action in ('observe_current_run', 'observe_queued_card') else
                           'ACTION_REQUIRED' if action in ('verify_and_integrate', 'reconcile_run_state') else
                           'BLOCKED')
                result.update(outcome=outcome, action='reconcile_original_card',
                              next_action=action, selected_task=None,
                              held_task_ids=[], recovery={'gate': 'native_continuity'}, repairs=[], blocker=[])
                capability = prior.get('continuation_capability')
                if (prior.get('next_action') == 'recover_original_card'
                        and isinstance(capability, dict) and capability.get('outcome') != 'ready'):
                    result['recovery']['continuation_capability'] = capability
                    result['blocker'] = [capability['reason']]
                save(state / 'history' / (result['run_id'] + '.json'), result)
                save(state / 'unblock-latest.json', result)
                save(state / 'report-latest.txt', render(result))
                return result
            if args.plan is None:
                selected = retry_selection.select(args.consumer, canonical_repo=args.canonical_repo,
                                                  require_owner=args.require_owner)
                if selected['state'] != 'ready_for_autowork' or not selected.get('selected_task'):
                    result.update(outcome='PREPARATION_REQUIRED', action='prepare_missing_inputs',
                                  next_action='; '.join(selected['reasons']) or selected['state'],
                                  selected_task=selected.get('selected_task'), held_task_ids=[],
                                  recovery={'gate': 'selection', 'selection': selected}, repairs=[], blocker=selected['reasons'])
                    save(state / 'history' / (result['run_id'] + '.json'), result)
                    save(state / 'unblock-latest.json', result)
                    save(state / 'report-latest.txt', render(result))
                    return result
                args.plan = selected['plan']
                args.tasks = selected['selected_task']['id']
                result.update(plan=args.plan, task_ids=[args.tasks])
        except (ValueError, OSError, RuntimeError, KeyError, subprocess.SubprocessError) as exc:
            result.update(outcome='FAILED', action='reconcile_original_card', next_action=str(exc),
                          selected_task=None, held_task_ids=[], recovery={'gate': 'native_continuity'}, repairs=[], blocker=[str(exc)])
            save(state / 'history' / (result['run_id'] + '.json'), result)
            save(state / 'unblock-latest.json', result)
            save(state / 'report-latest.txt', render(result))
            return result
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
    ready = recovery['gate'] in ('ready_for_autowork', 'candidate_validated')
    result['held_task_ids'] = []
    result['ready_queue'] = []
    try:
        queue = progress_runtime.ready_queue(consumer, require_owner=getattr(args, "require_owner", False))
        result['ready_queue'] = queue['tasks']
        result['queue_shortfall'] = queue['shortfall']
        alternate = queue['selection']
        permitted_goals = set(recovery.get('task_goals', {}).values())
        if (not ready and getattr(args, 'allow_ready_fallback', False)
                and recovery['gate'] == 'consumer_readiness'
                and (alternate.get('selected_task') or {}).get('goal') in permitted_goals
                and alternate['state'] == 'ready_for_autowork'):
            result['held_task_ids'] = result['task_ids']
            result['fallback_selection'] = alternate
            result['selected_task'] = alternate['selected_task']
            ready = True
    except (ValueError, OSError, TypeError, KeyError, AttributeError) as exc:
        result['queue_gap'] = str(exc)
    result['backlog_ready'] = ready
    result['resolved_requests'] = []
    if ready and composed and result['selected_task']:
        try:
            result['preparation'] = ready_preflight.compose(args, result['selected_task'], consumer, state, save,
                                                          result.get('fallback_selection', selection))
            args.handoff_request = result['preparation']['handoff_request']
        except (ValueError, OSError, TypeError, KeyError, subprocess.SubprocessError) as exc:
            result['preparation_error'] = str(exc)
    if ready and args.apply and not args.handoff_request and result['selected_task'] and not composed:
        saved = state / 'handoff-requests' / (result['selected_task']['id'] + '.json')
        if saved.is_file():
            retained = read_json(progress_runtime.private_path(
                state / 'ready-preflights' / result['selected_task']['id'] / 'preparation.json'), {})
            if not isinstance(retained, dict):
                raise ValueError('invalid original preparation receipt; retain it for reconciliation')
            if retained.get('dispatch_attempted'):
                result.update(outcome='BLOCKED', action='reconcile_original_card',
                    dispatch_attempted=True, preparation=retained,
                    next_action='Prior dispatch attempted; reconcile original native card and consumed budget, never replay saved handoff')
                save(state / 'history' / (result['run_id'] + '.json'), result)
                save(state / 'unblock-latest.json', result)
                save(state / 'report-latest.txt', render(result))
                return result
            args.handoff_request = str(progress_runtime.private_path(saved))
    preparation = ready and not args.handoff_request
    required_inputs = list(recovery.get('required_inputs', []))
    if preparation:
        required_inputs.append(result.get('preparation_error') or 'handoff_request: same consumer/task, explicit contract, immutable base and source snapshot')
        result.update(outcome='PREPARATION_REQUIRED', admission='handoff_preparation')
        ready = False
    if ready:
        result.update(outcome='READY', action='prepare_native_handoff',
                      next_action='Use the existing native handoff with explicit contract and source snapshot')
        if any(s.get('stage') == 'repair' for s in recovery.get('stages', [])):
            result['outcome'] = 'PROGRESS'
        if args.handoff_request and args.apply and result['selected_task']:
            result['dispatch_attempted'] = True
            try:
                if composed:
                    result['preparation'] = ready_preflight.mark_attempt(state, result['preparation'], save)
                    args._admission_attempt = result['preparation']['attempt_id']
                    args._admission_request_sha256 = result['preparation']['sha256']['handoff_request']
                    args._admission_launcher_sha256 = result['preparation']['launcher_sha256']
                result['handoff'] = handoff(args, result['selected_task'], consumer)
                native = result['handoff']['result']
                if (composed and result['handoff']['exit_code'] == 1
                        and ready_preflight.proven_no_create(result['preparation'], native)):
                    result['preparation'] = ready_preflight.record_refusal(
                        state, result['preparation'], native, save)
                    result.update(outcome='PREPARATION_REQUIRED',
                        next_action='Correct the local prerequisite, then prepare again: ' + native['reason'])
                elif result['handoff']['exit_code'] != 0:
                    result.update(outcome='FAILED', next_action='Reconcile native state on the original card before retry; dispatch outcome may be unknown')
                elif ((native.get('outcome') == 'handed_off' and
                       (not composed or (isinstance(native.get('task_id'), str) and native['task_id'].strip()
                                         and native.get('goal_mode') is True))) or
                      (native.get('outcome') == 'notification_blocked'
                       and isinstance(native.get('task_id'), str) and native['task_id'].strip()
                       and native.get('goal_mode') is True)):
                    result['outcome'] = 'QUEUED'  # card status alone is not worker liveness
                    result['next_action'] = 'Observe original native card/run; do not dispatch a replacement'
                    if composed:
                        goals = retry_selection.goals
                        with goals.coordination(consumer, None) as repo, redirect_stdout(io.StringIO()):
                            snapshot = json.loads(Path(result['preparation']['snapshot']).read_text())
                            if not ready_preflight.source_freshness.check(snapshot, repo)['fresh']:
                                raise ValueError('source changed after native handoff; preserve original card, repair bookkeeping only')
                            goals.execute(argparse.Namespace(cmd='task', repo=str(repo), task=result['selected_task']['id'], status='in_progress'))
                        result['bookkeeping'] = 'in_progress; not acceptance or closure'
                    if native.get('outcome') == 'notification_blocked':
                        result['notification_warning'] = native.get('notification_error') or 'Notification setup failed'
                        result['next_action'] += '; repair its notification separately without repeating admission'
                elif native.get('outcome') in ('already_owned', 'workspace_owned'):
                    result.update(outcome='BLOCKED', next_action='Reconcile the original native owner/card')
                else:
                    result.update(outcome='BLOCKED', next_action='Native admission not established; inspect handoff receipt')
            except (ValueError, OSError, TypeError, KeyError, SystemExit, subprocess.SubprocessError) as exc:
                result.setdefault('handoff', {})['error'] = str(exc)
                result.update(outcome='FAILED',
                              next_action='Reconcile native state on the original card before retry; dispatch outcome may be unknown')
    elif getattr(args, 'require_owner', False):
        result['action'] = 'owner_followup_required' if result['unchanged_runs'] >= 2 else 'owner_input_required'
        request_tasks = [result['selected_task']['id']] if preparation and result['selected_task'] else result['task_ids']
        request_binding = {'consumer': consumer, 'plan': args.plan, 'tasks': request_tasks,
                           'owner': args.integration_owner, 'blocker': key}
        if preparation: request_binding['admission'] = 'handoff_preparation'
        # Bind an explicitly designated session before deduplication; a sibling
        # cron using the same profile is not the parent integration session.
        target_session = None
        if args.apply:
            try:
                owner_route = read_json(state / 'owner-route.json')
                if (isinstance(owner_route, dict) and owner_route.get('consumer') == consumer
                        and owner_route.get('owner') == (args.integration_owner or 'unassigned')):
                    target_session = owner_route.get('target_session')
                    if target_session is not None:
                        if not isinstance(target_session, str) or not target_session.strip():
                            raise ValueError('owner route target_session must be a nonempty session ID')
                        request_binding['target_session'] = target_session
            except (ValueError, OSError) as exc:
                result['routing_gap'] = str(exc)
        request_id = fingerprint(request_binding)
        path = state / 'requests' / (request_id + '.json')
        request = read_json(path)
        if request is None:
            request = {'version': 1, 'request_id': request_id, 'created_at': now, 'status': 'pending',
                       'owner': args.integration_owner or 'unassigned', 'consumer': consumer,
                       'plan': args.plan, 'task_ids': request_tasks,
                       'gate': 'handoff_preparation' if preparation else recovery['gate'],
                       'required_inputs': required_inputs,
                       'proposal': args.proposal, 'evidence': args.owner_evidence,
                       'instruction': ('Prepare attributed execution prerequisites and the same-task handoff under existing authority; do not replan a ready task' if preparation else
                                       'Reconcile accepted canonical inputs under existing integration ownership, then rerun owner cycle'),
                       'boundary': 'Local request only; not delivered, acknowledged or integration authority'}
            if target_session is not None:
                request['target_session'] = target_session
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
        if args.apply:
            try:
                route = read_json(state / 'owner-route.json')
                if route is not None:
                    if (not isinstance(route, dict) or route.get('consumer') != consumer
                            or route.get('owner') != request['owner']
                            or route.get('target_session') != request.get('target_session')):
                        raise ValueError('owner route must match canonical consumer and actual owner')
                    request['delivery'] = progress_runtime.route(request, route['state_dir'])
                    reply = progress_runtime.read_reply(request, request['delivery'])
                    if reply:
                        request.update(status=reply['status'], owner_reply=reply)
                    save(path, request)
                else:
                    result['routing_gap'] = 'No bound owner-route.json; establish actual owner inbox, do not guess'
            except (ValueError, OSError, KeyError, TypeError) as exc:
                result['routing_gap'] = str(exc)
        result.update(integration_request=str(path), request_status=request['status'],
                      next_action=('Follow up existing integration request with its owner; do not repeat unchanged validation'
                                   if result['unchanged_runs'] >= 2 else
                                   'Integration owner must reconcile canonical inputs; see integration request'))
        if preparation:
            result['next_action'] = 'Prepare the selected task handoff using existing attributable inputs; otherwise resolve the execution-input request with its actual owner'
        # One bounded canonical selection, never an invented task or a focus change.
        try:
            alternate = retry_selection.select(consumer, require_owner=getattr(args, "require_owner", False))
            result['work_search'] = {'state': alternate['state'], 'candidate': alternate.get('selected_task'),
                                     'reasons': alternate.get('reasons', []),
                                     'boundary': 'canonical selector only; source/test seam search still required when no eligible candidate'}
        except (ValueError, OSError, TypeError, KeyError, SystemExit) as exc:
            result['work_search'] = {'state': 'unavailable', 'reason': str(exc)}
    else:
        result.update(outcome='ACTION_REQUIRED', action='repair_local_inputs',
            next_action='Reconcile existing local work, repair canonical inputs and prepare execution yourself; no owner acknowledgement required. Preserve live writers and verify changes before adoption.')
    if ready and result['outcome'] == 'QUEUED':
        resolved = []
        for path in sorted((state / 'requests').glob('*.json')):
            request = read_json(path)
            request_tasks = ([result['selected_task']['id']] if isinstance(request, dict) and request.get('gate') == 'handoff_preparation'
                             else result['task_ids'])
            if (isinstance(request, dict) and request.get('consumer') == consumer
                    and request.get('plan') == args.plan and request.get('task_ids') == request_tasks
                    and request.get('status') != 'resolved' and args.apply
                    and (request.get('gate') == 'handoff_preparation' or not result['held_task_ids'])):
                request.update(status='resolved', resolved_at=now,
                               resolution={'run_id':result['run_id'], 'gate':recovery['gate'],
                                           'revision':retry_selection.goals.revision(Path(consumer))})
                save(path, request)
                resolved.append(str(path))
        result['resolved_requests'] = resolved
    if not result['backlog_ready'] and result['scope'] == 'repository':
        try:
            result['work_search'] = retry_selection.repository_frontier(consumer, require_owner=getattr(args, "require_owner", False))
        except (ValueError, OSError, TypeError, KeyError, SystemExit) as exc:
            result['work_search'] = {'state': 'unverified', 'error': str(exc)}
    result['repairs'] = [repair for stage in recovery.get('stages', [])
                         if stage.get('stage') == 'repair' for repair in stage.get('repairs', [])]
    result['blocker'] = required_inputs if not ready or result['held_task_ids'] else []
    if result.get('routing_gap') and result['unchanged_runs'] >= 2:
        result['action'] = 'escalate_missing_owner_route'
        result['next_action'] = result['routing_gap']
    result['planning'] = ({'action': 'prepare_execution_handoff', 'reason': 'Ready composed path; repair only the named missing input'}
                          if composed and result['backlog_ready'] else backlog_plan.decide(result, state))
    if result['planning']['action'] == 'discover_repository_work' and not result['dispatch_attempted']:
        result.update(action='discover_repository_work', outcome='ACTION_REQUIRED',
                      next_action=result['planning']['handoff'])
        candidates = result['work_search'].get('candidates', [])
        if candidates:
            candidate = candidates[0]
            result.update(action='prepare_independent_candidate',
                next_action=f"Check file-scope ownership for {candidate['task']['id']}; prepare its contract, snapshot and required fallback evidence, then retry this exact candidate")
    elif result['planning']['action'] in ('resolve_recorded_blocker', 'inspect_planning_receipt') and not result['dispatch_attempted']:
        result.update(action=result['planning']['action'], outcome='ACTION_REQUIRED',
                      next_action=result['planning']['handoff'])
    elif result['planning']['action'] in ('plan', 'reuse') and not result['dispatch_attempted']:
        result.update(action='plan_execution_recovery',
                      next_action=result['planning'].get('handoff', result['planning']['reason']))
    elif preparation:
        result.update(action='prepare_execution_handoff', outcome='PREPARATION_REQUIRED',
                      next_action=result.get('preparation_error') or 'Prepare the contract, base and snapshot under existing authority; a missing owner route does not delegate ordinary preparation to the user')
    save(state / 'history' / (result['run_id'] + '.json'), result)
    save(state / 'unblock-latest.json', result)
    save(state / 'report-latest.txt', render(result))
    return result


def render(result):
    task = result.get('selected_task') or {}
    prior = result.get('reconciliation') or {}
    label = task.get('id') or prior.get('task_id') or ', '.join(result['task_ids'])
    title = task.get('title') or prior.get('title') or 'title unverified'
    return (f"{result['outcome']} — 0 tasks completed by this cycle\n"
            f"Task: {label} — {title}\n"
            f"Recovery: {result['recovery']['gate']}; unchanged runs: {result['unchanged_runs']}\n"
            f"Repairs: {', '.join(result.get('repairs', [])) or 'none'}; checks: recovery/readiness only, not product acceptance\n"
            f"Held: {', '.join(result.get('held_task_ids', [])) or 'none'}; blocker: {'; '.join(result.get('blocker', [])) or 'none'}\n"
            f"Next: {result['next_action']}; ready queue: {', '.join(t['id'] for t in result.get('ready_queue', [])) or 'none'}\n"
            f"Delivery: {result['delivery']}\n")


def compact(result, state_dir):
    """Routine ready-path status; full inputs and recovery history stay private."""
    task = result.get('selected_task') or {}
    return {'outcome': result['outcome'], 'task': task.get('id'),
            'native_card': result.get('handoff', {}).get('result', {}).get('task_id') or result.get('reconciliation', {}).get('task_id'),
            'dispatch_attempted': result['dispatch_attempted'], 'completed_tasks': [],
            'next_action': result['next_action'],
            'receipt': str(Path(state_dir) / 'unblock-latest.json')}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer')
    parser.add_argument('--plan', help='Accepted named plan; omit with --tasks for default ready selection')
    parser.add_argument('--tasks', help='Named task IDs; requires --plan')
    parser.add_argument('--state-dir', required=True, help='Private owning-profile autowork directory')
    parser.add_argument('--profile', help='Normal ready path: compose inputs and invoke native admission once with --apply; omit only for recovery-only inspection')
    parser.add_argument('--local-policy', help='Trusted coordinator policy JSON for original implementation/review and local integration closeout')
    parser.add_argument('--source-path', action='append', default=[], help='Explicit executable/test/dependency-closure file to bind; repeat as needed')
    parser.add_argument('--base', help='Full immutable base; default captures current HEAD once')
    parser.add_argument('--fallback-file', help='Existing structured focused-milestone fallback evidence; never synthesized')
    parser.add_argument('--disjoint-blocked-handoff', help='Pinned original-card and distinct owned-scope evidence; preserves blocked card')
    parser.add_argument('--registration-declaration', help='Explicit owned-scope registration declaration for native admission')
    parser.add_argument('--registration-native-python', help='Installed native runtime launcher for transactional registered creation')
    parser.add_argument('--pass-root', help='Private isolated worktree root forwarded to native admission')
    parser.add_argument('--ledger-mode', choices=('worker', 'proposal'), default='worker')
    parser.add_argument('--verbose', action='store_true', help='Print full private receipt instead of compact ready-path status')
    for name in ('canonical-repo', 'authority', 'prerequisite-request', 'candidate-request',
                 'handoff-request', 'integration-owner', 'proposal', 'owner-evidence'):
        parser.add_argument('--' + name)
    parser.add_argument('--scope', choices=('tasks', 'repository'), default='tasks',
                        help='Repository-wide development authority permits independent maintenance selection; named-task calls stay scoped by default')
    parser.add_argument('--require-owner', action='store_true',
                        help='Opt into external owner requests and recorded claim release gates')
    parser.add_argument('--apply', action='store_true')
    parser.add_argument('--allow-ready-fallback', action='store_true', help='Allow an accepted same-milestone task when the preferred slice is held')
    parser.add_argument('--acknowledge', action='store_true', help='Record supplied owner acknowledgement, not inferred consent')
    args = parser.parse_args(argv)
    if args.profile and args.apply and os.environ.get('HERMES_KANBAN_TASK'):
        parser.error('Already a goal worker: execute the assigned card, never launch a nested goal')
    if (args.plan is None) != (args.tasks is None):
        parser.error('provide both --plan and --tasks, or neither for default ready selection')
    if args.plan is None and (not args.profile or not args.apply or args.handoff_request):
        parser.error('default ready selection requires --profile --apply without a manual handoff request')
    try:
        result = cycle(args)
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + '\n')
    print(json.dumps(result if args.verbose or not args.profile else compact(result, args.state_dir), indent=2))
    return 0 if result['outcome'] in ('READY', 'PROGRESS', 'QUEUED', 'WAITING') else 1


if __name__ == '__main__':
    raise SystemExit(main())
