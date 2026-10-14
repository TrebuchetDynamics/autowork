"""Read-only evidence for a distinct task while its original card remains blocked.

This checks declared file scope, not semantic independence or resource leases.
The coordinator supplies the reason/evidence and retains the original artifacts.
"""
import hashlib
import json
from pathlib import Path
import writer_registration as registration


def pinned(path, digest):
    path = Path(path)
    if not path.is_absolute() or any(p.is_symlink() for p in (path, *path.parents)):
        raise ValueError('Fallback evidence requires absolute non-symlink paths')
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError('Original fallback evidence changed: ' + str(path))
    return json.loads(raw, object_pairs_hook=registration.unique_object)


def verify(evidence_path, handoff_path, workspace, profile, goal_task, declaration_path):
    evidence = json.loads(Path(evidence_path).read_bytes(), object_pairs_hook=registration.unique_object)
    required = {'version', 'original_handoff_sha256', 'original_card', 'original_task',
                'original_workspace', 'original_base', 'original_run_id', 'original_requirement',
                'original_requirement_sha256', 'goal_task', 'scope', 'reason', 'evidence_ref'}
    if (set(evidence) != required or evidence['version'] != 1 or not declaration_path
            or any(not isinstance(evidence[k], str) or not evidence[k].strip()
                   for k in ('reason', 'evidence_ref', 'goal_task'))):
        raise ValueError('Complete explicit disjoint fallback evidence and registration required')
    handoff = pinned(handoff_path, evidence['original_handoff_sha256'])
    manifest = pinned(handoff['pass_manifest_path'], handoff['pass_manifest_sha256'])
    requirement = pinned(evidence['original_requirement'], evidence['original_requirement_sha256'])
    expected = requirement['expected']
    identity = dict(card=handoff['task_id'], task=handoff['goal_task'], workspace=handoff['workspace'],
                    base=manifest['candidate_identity']['base_commit'])
    if (manifest != handoff['pass_manifest'] or handoff['profile'] != profile
            or handoff['source_workspace'] != str(Path(workspace).resolve())
            or manifest['source_workspace'] != handoff['source_workspace']
            or manifest['goal_task'] != handoff['goal_task']
            or manifest['candidate_identity']['workspace'] != handoff['workspace']
            or any(evidence['original_' + k] != v for k, v in identity.items())
            or any(expected.get(k) != v for k, v in identity.items())
            or evidence['goal_task'] != goal_task or goal_task == identity['task']):
        raise ValueError('Fallback must preserve original identity and select a different task')
    declaration = json.loads(Path(declaration_path).read_bytes(), object_pairs_hook=registration.unique_object)
    registration.validate_scope(expected['scope'])
    registration.validate_scope(evidence['scope'])
    if declaration['scope'] != evidence['scope'] or declaration['registry'] != requirement['registry']:
        raise ValueError('Fallback owned scope/registry differs from new registration declaration')
    for old in expected['scope']:
        for new in evidence['scope']:
            if Path(old).is_relative_to(new) or Path(new).is_relative_to(old):
                raise ValueError('Fallback owned file/directory overlaps original card: ' + new)
    native = registration.native_observation(profile, identity['card'])
    task, runs = native['task'], native.get('runs')
    bindings = {'id': identity['card'], 'assignee': profile, 'board_id': handoff['board_id'],
                'workspace_path': identity['workspace'], 'workspace_kind': 'dir', 'status': 'blocked',
                'goal_max_turns': handoff['goal_max_turns'], 'max_retries': handoff['max_retries'],
                'completion_contract': 'local-only'}
    if (any(task.get(k) != v for k, v in bindings.items()) or task.get('goal_mode') not in (True, 1)
            or not {'current_run_id', 'worker_pid'} <= task.keys()
            or task['current_run_id'] is not None or task['worker_pid'] is not None
            or not isinstance(runs, list) or not runs
            or any(not r.get('ended_at') for r in runs)
            or runs[-1].get('id') != evidence['original_run_id']
            or runs[-1].get('status') not in {'blocked', 'crashed'}):
        raise ValueError('Original card must retain exact terminal run with no live or unknown claim')
    if any(value not in task.get('body', '') for value in
           (evidence['original_requirement'], evidence['original_requirement_sha256'])):
        raise ValueError('Original native contract does not bind required ownership scope')
    return dict(evidence, validation='file_scope_and_terminal_state_verified_resource_independence_attested',
                original_preserved=True, original_body_sha256=hashlib.sha256(task['body'].encode()).hexdigest())
