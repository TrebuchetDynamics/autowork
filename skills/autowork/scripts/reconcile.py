#!/usr/bin/env python3
"""Read a prior autowork handoff's live card/run; never mutate or dispatch.

The CLI writes only a separate report projection cache. It always reads the board
again; an unchanged report is not permission to skip the caller's work search.
Structured evidence belongs in latest-run metadata.delivery_evidence. Only an
explicit --repo enables independent local main/ancestry verification.
"""
import argparse
import json
import hashlib
from pathlib import Path
from start_goal import run, profile_home
from delivery_state import evaluate


def reconcile(prefix, home, profile, task_id=None, repo=None):
    if task_id is None:
        receipt = home / 'autowork' / 'goal-handoff.json'
        if not receipt.exists():
            return {'profile': profile, 'outcome': 'no_handoff', 'continuity': 'missing'}
        data = json.loads(receipt.read_text())
        if (isinstance(data, dict) and data.get('task_id') is None
                and isinstance(data.get('current_handoff'), dict)):
            data = data['current_handoff']
        if (not isinstance(data, dict) or not isinstance(data.get('task_id'), str)
                or not data['task_id']):
            raise ValueError('Unknown handoff receipt schema: expected a nonempty task_id string')
        task_id = data['task_id']
    snapshot = json.loads(run(prefix, 'kanban', '--board', 'default', 'show', task_id, '--json'))
    if not isinstance(snapshot, dict):
        raise ValueError('Unknown kanban show schema: expected an object')
    task = snapshot.get('task', snapshot)
    if not isinstance(task, dict) or any(not isinstance(task.get(k), str) or not task[k]
                                         for k in ('id', 'assignee', 'status')):
        raise ValueError('Unknown task schema: expected id, assignee and status strings')
    if task.get('id') != task_id:
        raise ValueError('Readback task ID does not match the requested handoff')
    if task.get('assignee') != profile:
        raise RuntimeError('Prior handoff belongs to a different profile; do not reconcile as owned')
    runs = snapshot.get('runs', [])
    events = snapshot.get('events', [])
    if (not isinstance(runs, list) or any(not isinstance(r, dict) or
            type(r.get('id')) is not int for r in runs)):
        raise ValueError('Unknown runs schema: expected objects with integer IDs')
    if any('task_id' in r and r['task_id'] != task_id for r in runs):
        raise ValueError('Readback run task ID does not match the requested handoff')
    if not isinstance(events, list) or any(not isinstance(e, dict) for e in events):
        raise ValueError('Unknown events schema: expected an object list')
    latest = max(runs, key=lambda r: r['id']) if runs else {}
    owner = latest.get('profile')
    owner = owner if isinstance(owner, str) and owner else None
    ownership = 'current_profile' if owner == profile else 'other_profile' if owner else 'unknown'
    metadata = latest.get('metadata') or {}
    current_evidence = (metadata.get('delivery_evidence')
                        if ownership == 'current_profile' and isinstance(metadata, dict) else None)
    delivery = evaluate(current_evidence, repo)
    # A next action is a coordinator instruction, not proof of process liveness,
    # review approval, integration authority, or completed acceptance.
    if task['status'] in {'running', 'review'}:
        next_action = 'observe_current_run'
    elif task['status'] in {'ready', 'todo'}:
        next_action = 'observe_queued_card'
    elif task['status'] in {'done', 'reviewed'}:
        next_action = 'reconcile_task_and_select' if delivery['delivered'] else 'verify_and_integrate'
    elif task['status'] in {'blocked', 'failed', 'changes_requested'}:
        next_action = 'recover_original_card'
    else:
        next_action = 'reconcile_unknown_state'
    return {'profile': profile, 'task_id': task_id, 'board_id': 'default', 'status': task['status'],
            'next_action': next_action,
            'delivery': delivery, 'human_report': delivery['progress'], 'selection_required': True,
            'run_profile': owner, 'run_ownership': ownership, 'card_run_observed': bool(runs),
            'title': task.get('title'), 'run_id': latest.get('id'),
            'worker_outcome': latest.get('outcome'),
            'summary': latest.get('summary') or snapshot.get('latest_summary'),
            'error': latest.get('error') or task.get('last_failure_error'),
            'metadata': latest.get('metadata') or {},
            'latest_event': events[-1] if events else None,
            'observation': 'live_read_only', 'worker_observed': bool(runs) and owner == profile}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--profile', required=True)
    parser.add_argument('--compact', action='store_true', help='Omit raw metadata/event and bound summary; omit flag for full readback')
    parser.add_argument('--task-id')
    parser.add_argument('--repo', type=Path, help='Local Git repository for main ancestry verification')
    parser.add_argument('--report-state', type=Path, help='Report-only cache; never skips reconciliation')
    args = parser.parse_args()
    prefix = ['hermes', '-p', args.profile]
    home = profile_home(prefix)
    result = reconcile(prefix, home, args.profile, args.task_id, args.repo)
    cache = args.report_state or home / 'autowork' / 'reconcile-report.json'
    # Store only the previous validated report projection, not raw worker prose.
    projection = {k: result.get(k) for k in
                  ('profile', 'board_id', 'task_id', 'status', 'run_ownership', 'run_id',
                   'worker_outcome', 'next_action', 'delivery')}
    projection['evidence_digest'] = hashlib.sha256(json.dumps(
        {'metadata': result.get('metadata'), 'event': result.get('latest_event'),
         'error': result.get('error'), 'summary': result.get('summary')}, sort_keys=True).encode()).hexdigest()
    previous = None
    if cache.exists():
        try:
            previous = json.loads(cache.read_text())
        except (OSError, ValueError):
            pass  # A corrupt report cache cannot prevent readback or discovery.
    previous_count = previous.pop('_blocked_observations', 0) if isinstance(previous, dict) else 0
    if type(previous_count) is not int or previous_count < 0:
        previous_count = 0
    blocked_count = ((previous_count + 1 if previous == projection else 1)
                     if result.get('next_action') == 'recover_original_card' else 0)
    result['changed_fields'] = sorted(k for k, v in projection.items()
                                      if not isinstance(previous, dict) or previous.get(k) != v)
    result['continuation'] = {
        'task_id': result.get('task_id'), 'run_id': result.get('run_id'),
        'phase': result.get('status'), 'next_action': result.get('next_action'),
        'candidate': result.get('delivery', {}).get('candidate'),
        'fresh_readback_required': True,
        'unchanged_blocked_observations': blocked_count,
        'follow_up': 'change_recovery_approach' if blocked_count >= 2 else result.get('next_action'),
        'reuse': 'Resume this phase; read changed inputs and outstanding acceptance only',
        'retry_condition': ('Changed failing inputs or a different supported repair; never repeat an identical failure'
                            if result.get('next_action') == 'recover_original_card' else None)}
    if previous == projection:
        result['human_report'] = None
    result['report_changed'] = previous != projection
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = cache.with_suffix(cache.suffix + '.tmp')
    temporary.write_text(json.dumps(dict(projection, _blocked_observations=blocked_count), sort_keys=True) + '\n')
    temporary.replace(cache)
    if args.compact:
        result.pop('metadata', None)
        result.pop('latest_event', None)
        summary = result.get('summary')
        result['summary_truncated'] = isinstance(summary, str) and len(summary) > 1200
        if result['summary_truncated']:
            result['summary'] = summary[:1200]
        result['full_readback'] = 'Omit --compact to inspect full metadata and summary before an evidence-dependent action'
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    main()
