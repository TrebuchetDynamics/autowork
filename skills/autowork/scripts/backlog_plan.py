"""Bound Autoresearch Plan fallback by consumer inputs, not cron occurrences."""
import argparse
import hashlib
import json
from pathlib import Path
from progress_runtime import private_path, write


def key(cycle):
    bound={k:cycle[k] for k in ('consumer','plan','task_ids','fingerprint')}
    return hashlib.sha256(json.dumps(bound,sort_keys=True).encode()).hexdigest()


def decide(cycle, state):
    gate=cycle.get('recovery',{}).get('gate')
    if gate=='ownership':
        return {'action':'reconcile_owner','reason':'Planning cannot replace an existing writer'}
    if cycle.get('admission') == 'handoff_preparation':
        return {'action':'repair_execution_inputs','reason':'Task is eligible but its execution handoff is missing; prepare inputs or follow the existing owner request, not another plan'}
    if cycle.get('backlog_ready', True) and (cycle.get('ready_queue') or cycle.get('selected_task')):
        return {'action':'execute_ready_work','reason':'Use the existing accepted task before planning'}
    if gate=='ledger':
        return {'action':'integrate_existing_inputs','reason':'Reconcile canonical backlog with its owner; do not create another detached plan'}
    if (cycle.get('scope') == 'repository' and gate in
            ('consumer_readiness','owner_authority','source_freshness','prerequisites','candidate')):
        return {'action':'discover_repository_work', 'execution_required':True,
                'skill':'hermes-toolset:autoresearch', 'subcommand':'plan',
                'reason':'The selected task is held; repository development authority still covers independent work',
                'handoff':'Choose an evidence-backed independent maintenance slice, reconcile canonical tasks and execute it in this occurrence',
                'boundary':'Preserve the held task, ownership and live gates; this decision is not discovery execution or completion'}
    if gate in ('refused','owner_authority','source_freshness','prerequisites','candidate'):
        return {'action':'repair_execution_inputs','reason':'Planning cannot supply missing authority or execution prerequisites'}
    token=key(cycle)
    path=private_path(Path(state)/'planning'/f'{token}.json')
    if path.exists():
        receipt=json.loads(path.read_text())
        if receipt.get('input_key')!=token:raise ValueError('planning receipt binding mismatch')
        return {'action':'reuse','receipt':str(path),'reason':'Same consumer inputs already planned; follow its integration or execution outcome'}
    poor_contract=gate in ('accepted_body_repair','accepted_metadata_repair')
    if poor_contract or cycle.get('unchanged_runs',0)>=2:
        return {'action':'plan','input_key':token,'skill':'hermes-toolset:autoresearch',
                'subcommand':'plan','reason':'No ready work and incomplete contracts or repeated hold',
                'handoff':'Bounded findings -> canonical repo-docs Maintain -> same-occurrence selection',
                'boundary':'Agent must run the skill; this decision is not model execution or task completion'}
    return {'action':'recover_first','reason':'Attempt ordinary recovery before opening a planning pass'}


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
