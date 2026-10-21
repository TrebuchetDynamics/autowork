"""Bound Autoresearch Plan fallback by consumer inputs, not cron occurrences."""
import argparse
import hashlib
import json
from pathlib import Path
from progress_runtime import private_path, write
import task_queue
import task_select
from task_store import StoreError


def key(cycle):
    bound={k:cycle[k] for k in ('consumer','plan','task_ids','fingerprint')}
    return hashlib.sha256(json.dumps(bound,sort_keys=True).encode()).hexdigest()


def ready_queue(cycle):
    """The consumer's selectable tasks now, from its store at the cycle's revision (HEAD
    without one): [] when it has none, None when the store cannot be read. A queue written
    into the cycle by hand is never trusted; this is its only producer."""
    consumer = cycle.get('consumer')
    if not isinstance(consumer, str) or not Path(consumer).is_dir():
        return None
    try:
        snapshot = task_queue.store(Path(consumer), cycle.get('revision') or 'HEAD')
    except StoreError:
        return None
    return [{'id': t.id, 'title': t.title, 'goal': t.goal} for t in task_select.order(snapshot)][:3]


def decide(cycle, state):
    queue = ready_queue(cycle)
    gate=cycle.get('recovery',{}).get('gate')
    if cycle.get('coordination_mode') == 'autonomous' and gate in ('ledger', 'ownership', 'owner_authority'):
        return {'action': 'repair_local_inputs' if gate != 'ownership' else 'reconcile_live_work',
                'reason': 'The current agent coordinates local recovery; no external owner acknowledgement is required. Preserve live workers and verify existing candidates.'}
    if gate=='ownership':
        return {'action':'reconcile_owner','reason':'Planning cannot replace an existing writer'}
    if gate == 'refused':
        return {'action':'repair_execution_inputs','reason':'Planning cannot override an explicit refusal or exclusion'}
    preparation = cycle.get('admission') == 'handoff_preparation'
    held_inputs = gate in ('source_freshness', 'prerequisites', 'candidate')
    if preparation or (held_inputs and cycle.get('scope') != 'repository'):
        decision = planning_decision(cycle, state,
            'Resolve the blocked handoff or prerequisites within the authorized task scope')
        fallback = cycle.get('fallback_selection') or {}
        fallback_ready = (isinstance(fallback, dict) and fallback.get('state') == 'ready_for_autowork'
                          and isinstance(fallback.get('selected_task'), dict)
                          and fallback['selected_task'] == cycle.get('selected_task'))
        if (preparation and cycle.get('coordination_mode') == 'autonomous'
                and cycle.get('backlog_ready') is True and cycle.get('selected_task')
                and (gate in ('ready_for_autowork', 'candidate_validated') or fallback_ready)
                and decision['action'] == 'plan'):
            return {'action': 'prepare_execution_handoff', 'execution_required': True,
                    'reason': 'Accepted task is ready; missing handoff artifacts are routine preparation, not a research gap',
                    'handoff': 'Build the contract, immutable base and source snapshot from this accepted task, then retry native admission. Research only a concrete unresolved choice; preserve any prior failure receipt.'}
        return decision
    if not held_inputs and cycle.get('backlog_ready', True) and (queue or cycle.get('selected_task')):
        return {'action':'execute_ready_work','reason':'Use the existing accepted task before planning'}
    if gate=='ledger':
        return {'action':'integrate_existing_inputs','reason':'Reconcile canonical backlog with its owner; do not create another detached plan'}
    selection = cycle.get('recovery', {}).get('selection', {})
    if gate == 'consumer_readiness' and selection.get('state') == 'draft_saved':
        return planning_decision(cycle, state,
            'Repair the reported canonical documentation contract before searching for unrelated work; '
            'the same backlog errors can block every candidate. Use exact consumer reasons, '
            'preserve unresolved intent, then retry selection in this occurrence')
    if (cycle.get('scope') == 'repository' and gate in
            ('consumer_readiness','owner_authority','source_freshness','prerequisites','candidate')):
        return {'action':'discover_repository_work', 'execution_required':True,
                'skill':'autowork:plan-for-me', 'subcommand':'plan',
                'reason':'The selected task is held; repository development authority still covers independent work',
                'handoff':'Choose an evidence-backed independent maintenance slice, reconcile canonical tasks and execute it in this occurrence',
                'boundary':'Preserve the held task, ownership and live gates; this decision is not discovery execution or completion'}
    if gate in ('refused','owner_authority','source_freshness','prerequisites','candidate'):
        return {'action':'repair_execution_inputs','reason':'Planning cannot supply missing authority or execution prerequisites'}
    poor_contract=gate in ('accepted_body_repair','accepted_metadata_repair')
    empty_queue = queue == [] and not cycle.get('selected_task')
    if poor_contract or empty_queue or cycle.get('unchanged_runs',0)>=2:
        return planning_decision(cycle, state, 'Observed empty queue, incomplete task contract or repeated hold')
    return {'action':'recover_first','reason':'Attempt ordinary recovery before opening a planning pass'}


def planning_decision(cycle, state, reason):
    token=key(cycle)
    path=private_path(Path(state)/'planning'/f'{token}.json')
    if path.exists():
        try:
            receipt=json.loads(path.read_text())
            if (not isinstance(receipt, dict) or receipt.get('version') != 1
                    or receipt.get('input_key') != token or receipt.get('consumer') != cycle['consumer']
                    or receipt.get('outcome') not in ('canonical_reconciled', 'integration_pending', 'no_supported_delta')
                    or not isinstance(receipt.get('evidence'), str) or not receipt['evidence'].strip()):
                raise ValueError('planning receipt schema or binding mismatch')
        except (ValueError, OSError):
            return {'action':'inspect_planning_receipt','receipt':str(path),'execution_required':True,
                    'reason':'Saved planning evidence is unreadable or mismatched; preserve it and inspect current state before any retry',
                    'handoff':'Reconcile the original task/card and planning evidence; repair the receipt only from verified inputs. Do not restart planning or dispatch a replacement.'}
        common = {'receipt':str(path), 'execution_required':True,
                  'outcome':receipt['outcome'], 'evidence':receipt['evidence']}
        if receipt['outcome'] == 'no_supported_delta':
            return dict(common, action='resolve_recorded_blocker',
                reason='The previous investigation found no supported change; no executable repair was established',
                handoff='Read the saved evidence and exact failed operation. Reconcile continuation/accounting on the original card through supported controls, preserving consumed budget and partial work. Do not repeat unchanged planning. If no supported recovery exists, state the precise required input and select independent work only within existing repository authority.')
        return dict(common, action='reuse',
            reason='Resume the recorded repair/integration and retry selection; do not repeat unchanged planning',
            handoff=('Read the saved evidence, verify changed inputs, then retry canonical selection without re-planning'
                     if receipt['outcome'] == 'canonical_reconciled' else
                     'Read the saved evidence and complete the pending supported integration before retrying selection; preserve active writers'))
    return {'action':'plan','input_key':token,'skill':'autowork:plan-for-me',
            'subcommand':'plan','reason':reason,'execution_required':True,
            'handoff':'Run bounded planning now -> docs_sync canonical TODO/goals -> retry selection and supported handoff in this occurrence',
            'boundary':'Keep the authorized scope, explicit exclusions and live writers; never import forbidden edits. This instruction is not model execution or task completion'}


def record(cycle,state,evidence,outcome):
    if not isinstance(evidence,str) or not evidence.strip():raise ValueError('actual planning evidence required')
    if outcome not in ('canonical_reconciled','integration_pending','no_supported_delta'):
        raise ValueError('unknown planning outcome')
    token=key(cycle)
    path=private_path(Path(state)/'planning'/f'{token}.json')
    write(path,{'version':1,'input_key':token,'consumer':cycle['consumer'],
                'evidence':evidence,'outcome':outcome,'boundary':'recorded planning result, not task completion'})
    return str(path)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('action',choices=('check','record'))
    p.add_argument('--cycle',required=True);p.add_argument('--state-dir',required=True)
    p.add_argument('--evidence');p.add_argument('--outcome')
    a=p.parse_args();cycle=json.loads(private_path(a.cycle).read_text())
    result=decide(cycle,a.state_dir) if a.action=='check' else {'receipt':record(cycle,a.state_dir,a.evidence,a.outcome)}
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
