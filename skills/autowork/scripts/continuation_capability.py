#!/usr/bin/env python3
"""Validate an explicit native continuation contract; never emulate native caps.

No installed Hermes CLI binding is provided: unblock/edit cannot enforce a
cumulative remainder. A trusted host integration (not card metadata or a JSON
file) must supply capabilities(), read_accounting(identity), and
continue_atomic(request). See references/owner-cycle.md#original-card-continuation-capability.
"""
import copy
import hashlib
import json

IDENTITY_FIELDS = ('board_id', 'task_id', 'profile', 'session_id', 'allocation_id', 'claim_id')
REQUIRED = ('accounting', 'atomic_continue', 'cumulative_cap', 'compare_and_swap',
            'idempotent', 'same_session', 'retry_rework_cap')
PREREQUISITE = ('Supported native original-card continuation with authoritative original '
                'allocation/history and atomic cumulative accounting/cap enforcement; '
                'completed-card rework control is also required for rework')


def assess(identity, runtime=None, *, original_allocation=None, rework=False):
    """Read fresh authoritative accounting; a ready report is not a dispatch receipt."""
    result = dict(outcome='unavailable', reason=PREREQUISITE, remaining=None,
                  unit=None, fresh_readback_required=True, native_execution=False)
    if runtime is None:
        return result
    try:
        capabilities = runtime.capabilities()
        required = REQUIRED + (('completed_rework',) if rework else ())
        if (not isinstance(capabilities, dict) or type(capabilities.get('version')) is not int
                or capabilities['version'] != 1
                or any(capabilities.get(key) is not True for key in required)
                or not callable(getattr(runtime, 'read_accounting', None))
                or not callable(getattr(runtime, 'continue_atomic', None))):
            return result
        if (not isinstance(identity, dict) or set(identity) != set(IDENTITY_FIELDS)
                or any(not isinstance(identity[k], str) or not identity[k].strip() for k in IDENTITY_FIELDS)):
            raise ValueError('complete original card/session/allocation/claim identity required')
        state = copy.deepcopy(runtime.read_accounting(copy.deepcopy(identity)))
        if not isinstance(state, dict) or state.get('identity') != identity:
            raise ValueError('original identity or claim changed')
        if not isinstance(state.get('revision'), str) or not state['revision'].strip():
            raise ValueError('authoritative accounting revision required')
        if state.get('claim_active') is not False:
            raise ValueError('claim active or activity unknown')
        allowed = {'done', 'reviewed', 'changes_requested'} if rework else {'blocked', 'failed', 'interrupted', 'changes_requested'}
        if state.get('status') not in allowed:
            raise ValueError('card state requires a different supported lifecycle operation')
        if state.get('complete') is not True or state.get('unknown_charges') is not False:
            raise ValueError('incomplete accounting or unknown charges')
        allocation = state.get('allocation')
        if (not isinstance(allocation, dict) or type(allocation.get('amount')) is not int
                or allocation['amount'] <= 0 or not isinstance(allocation.get('unit'), str)
                or not allocation['unit'].strip()):
            raise ValueError('explicit original allocation in actual runtime units required')
        if allocation != original_allocation:
            raise ValueError('original allocation unbound or changed; no replenishment authorized')
        attempts, attempt_ids = state.get('attempts'), state.get('attempt_ids')
        if (not isinstance(attempts, list) or not attempts or not isinstance(attempt_ids, list)
                or any(not isinstance(i, str) or not i for i in attempt_ids)
                or len(set(attempt_ids)) != len(attempt_ids)):
            raise ValueError('complete original attempt history required')
        consumed = 0
        ids = []
        for attempt in attempts:
            if (not isinstance(attempt, dict) or attempt.get('unit') != allocation['unit']
                    or attempt.get('session_id') != identity['session_id']
                    or type(attempt.get('consumed')) is not int or attempt['consumed'] < 0):
                raise ValueError('unknown or mixed-unit/session attempt accounting')
            ids.append(attempt.get('id'))
            consumed += attempt['consumed']
        if ids != attempt_ids:
            raise ValueError('incomplete, duplicate or reordered attempt history')
        if consumed >= allocation['amount']:
            raise ValueError('original allocation exhausted; no replenishment authorized')
        result.update(outcome='ready', reason='explicit native contract and accounting validated',
                      remaining=allocation['amount'] - consumed, unit=allocation['unit'],
                      expected=state, operation='rework' if rework else 'continue')
    except (ValueError, TypeError, AttributeError, OSError) as exc:
        result.update(outcome='refused', reason=str(exc))
    return result


def resume(identity, runtime=None, *, original_allocation=None, rework=False):
    """Invoke one atomic native operation. Unknown outcomes never trigger a retry."""
    report = assess(identity, runtime, original_allocation=original_allocation, rework=rework)
    if report['outcome'] != 'ready':
        return report
    request = dict(expected=report['expected'], remaining_cap=report['remaining'],
                   unit=report['unit'], operation=report['operation'])
    request['request_id'] = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()
    try:
        receipt = runtime.continue_atomic(copy.deepcopy(request))
        if isinstance(receipt, dict) and receipt.get('outcome') == 'refused':
            return dict(outcome='refused', reason=str(receipt.get('reason', 'native refusal')),
                        fresh_readback_required=True, native_execution=False)
        if (not isinstance(receipt, dict) or receipt.get('outcome') != 'accepted'
                or receipt.get('request_id') != request['request_id']
                or receipt.get('identity') != identity or receipt.get('unit') != request['unit']
                or type(receipt.get('remaining_cap')) is not int
                or receipt['remaining_cap'] != request['remaining_cap']):
            raise ValueError('native continuation receipt does not bind the request')
        return dict(receipt, fresh_readback_required=True, native_execution=True)
    except (ValueError, TypeError, OSError) as exc:
        return dict(outcome='unverified', reason=str(exc), request_id=request['request_id'],
                    fresh_readback_required=True, native_execution='unknown')
