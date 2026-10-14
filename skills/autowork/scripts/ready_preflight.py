"""Compose a ready task's inputs; native start_goal remains the admission owner.

No provider calls, speculative cache refresh, ledger closure or automatic retries.
The owner-cycle lock serializes preparation and the durable dispatch marker.
"""
import hashlib
import json
from pathlib import Path
import re
import subprocess

import retry_selection
import source_freshness
import start_goal
import progress_runtime


def compose(args, task, consumer, state, save, selection=None):
    repo = Path(consumer).resolve(strict=True)
    directory = state / 'ready-preflights' / task['id']
    receipt_path = progress_runtime.private_path(directory / 'preparation.json')
    inputs = {'plan': args.plan, 'source_paths': args.source_path, 'base': args.base,
              'ledger_mode': args.ledger_mode, 'integration_owner': args.integration_owner if args.ledger_mode == 'proposal' else None,
              'fallback_file': args.fallback_file, 'pass_root': args.pass_root,
              **{key: getattr(args, key, None) for key in ('disjoint_blocked_handoff',
                  'registration_declaration', 'registration_native_python')}}
    if receipt_path.exists():
        receipt = json.loads(receipt_path.read_text())
        if not isinstance(receipt, dict) or receipt.get('version') != 1:
            raise ValueError('invalid original preparation receipt; retain it for reconciliation')
        if (receipt.get('consumer') != str(repo) or receipt.get('task_id') != task['id']
                or receipt.get('profile') != args.profile):
            raise ValueError('saved preparation belongs to another consumer/task/profile')
        if receipt.get('dispatch_attempted'):
            raise ValueError('prior dispatch attempted; reconcile original native card and consumed budget, never retry preparation')
        if receipt.get('inputs') != inputs:
            raise ValueError('preparation options changed; retain original inputs and reconcile')
        for key in ('snapshot', 'contract', 'handoff_request'):
            path = progress_runtime.private_path(receipt[key])
            if not path.is_relative_to(state) or hashlib.sha256(path.read_bytes()).hexdigest() != receipt['sha256'][key]:
                raise ValueError('saved preparation artifact changed; preserve original inputs')
        snapshot = json.loads(Path(receipt['snapshot']).read_text())
        if not source_freshness.check(snapshot, repo)['fresh']:
            raise ValueError('saved preparation is stale; retain original inputs and reconcile, do not refresh')
        current_base = args.base or subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, timeout=30).strip()
        if current_base != receipt['base']:
            raise ValueError('immutable preparation base changed; retain original inputs')
        return receipt

    # Accepted-body parsing is shared with docs-sync; no second planning/docs pass.
    goals = retry_selection.goals
    ledger = goals.load(repo)
    if ledger != goals.normalize(ledger):
        raise ValueError('ledger is not normalized; prepare only canonical goals.py fmt inputs before admission')
    entries = goals.task_bodies((repo / 'TODO.md').read_text()).get(task['id'], [])
    if len(entries) != 1:
        raise ValueError('missing or duplicate accepted task body')
    body = entries[0][0]
    fields = goals.task_fields(body)
    if not args.source_path:
        raise ValueError('missing explicit source-path closure; bind task code/docs/tests/dependency inputs')
    for name in ('Scope', 'Acceptance', 'Checks', 'Sources', 'Ownership'):
        if not fields.get(name, '').strip():
            raise ValueError(f'missing task {name}; prepare only this accepted input, no dispatch')
    # Explicit caller paths bind executable/test/dependency closure; local linked
    # sources and governing inputs are always included, without directory scans.
    paths = ['goals.json', 'TODO.md', args.plan.split('#', 1)[0], retry_selection.REGISTRY]
    paths += list(args.source_path)
    for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', body):
        if not re.match(r'^[A-Za-z][A-Za-z0-9+.-]*:', ref) and not ref.startswith('#'):
            paths.append(ref.split('#', 1)[0])
    for name in ('AGENTS.md', 'requirements-test.txt', 'pyproject.toml', 'package.json'):
        if (repo / name).exists():
            paths.append(name)
    paths = list(dict.fromkeys(paths))
    snapshot = source_freshness.capture(repo, paths)
    captured = {row['path']: row['sha256'] for row in snapshot['files']}
    if selection is not None and any(captured.get(name) != digest for name, digest in selection['sha256'].items()):
        raise ValueError('accepted selection changed before preparation; retain the original selection')
    # Bind the text actually read, not just a later replacement of that text.
    todo_row = next(row for row in snapshot['files'] if row['path'] == 'TODO.md')
    if todo_row['sha256'] != hashlib.sha256((repo / 'TODO.md').read_bytes()).hexdigest():
        raise ValueError('task changed during preparation')
    if goals.task_bodies((repo / 'TODO.md').read_text()).get(task['id'], []) != entries:
        raise ValueError('accepted body changed during preparation')
    base = args.base or subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True, timeout=30).strip()
    if not re.fullmatch(r'[0-9a-f]{40}|[0-9a-f]{64}', base):
        raise ValueError('base must be a full immutable commit')
    values = {
        'Objective': f"{task['id']} ({task['goal']}): {task['title']}",
        'Scope': fields['Scope'] + '\nExclusions: ' + fields.get('Exclusions', 'No upstream edits, push, deployment, profile/job changes or live qualification.'),
        'Verification': fields['Checks'],
        'Source': f"TODO.md {task['id']}; {fields['Sources']}; immutable base {base}; ownership: {fields['Ownership']}",
        'Project payoff': fields.get('Goal', task['title']),
        'Current evidence': fields.get('Evidence', 'Accepted dependency-ready task; checks not yet executed.'),
        'Expected change': fields.get('Expected change', fields['Scope']),
        'Acceptance': fields['Acceptance'],
        'Stop conditions': fields.get('Stop conditions', '') + ' One coherent task; 100 turns, max-retries 1. Preserve ownership, original card, source/base and consumed budget; unknown usage is unknown. Stop on admission refusal, conflicting writer or five attempts without new evidence. Independent exact-candidate review required; no native/model qualification without externally enforced spending and descendant limits.',
        'Repo-docs pass': f"Accepted {args.plan}; current task body only, no broad audit or priority/focus change.",
        'Goal budget rationale': 'Default allocation for one coherent implementation and recovery outcome.',
    }
    for name in ('Decision', 'Environment prerequisite', 'Decision gate', 'Dependencies'):
        if fields.get(name):
            values['Scope'] += f'\n{name}: {fields[name]}'
    contract = '\n'.join(f'{name}: {value}' for name, value in values.items()) + '\n'
    # Structural validation is in-process, not a duplicate validate-only command.
    start_goal.validate_contract(contract)
    snapshot_path = directory / 'sources.json'
    contract_path = directory / 'contract.txt'
    request_path = state / 'handoff-requests' / (task['id'] + '.json')
    save(snapshot_path, snapshot)
    save(contract_path, contract)
    options = {'profile': args.profile, 'title': f"{task['id']} — {task['title']}",
               'contract-file': str(contract_path), 'source-snapshot': str(snapshot_path),
               'base': base, 'required-path': list(args.source_path)}
    for key in ('disjoint_blocked_handoff', 'registration_declaration', 'registration_native_python'):
        if getattr(args, key, None):
            options[key.replace('_', '-')] = getattr(args, key)
    if args.fallback_file:
        options['fallback-file'] = args.fallback_file
    if args.pass_root:
        options['pass-root'] = args.pass_root
    options['ledger-mode'] = args.ledger_mode
    if args.ledger_mode == 'proposal':
        if not args.integration_owner:
            raise ValueError('proposal mode requires named integration owner')
        options['integration-owner'] = args.integration_owner
    save(request_path, {'consumer': str(repo), 'task_id': task['id'], 'options': options})
    receipt = {'version': 1, 'consumer': str(repo), 'task_id': task['id'], 'profile': args.profile,
               'base': base, 'snapshot': str(snapshot_path), 'contract': str(contract_path),
               'handoff_request': str(request_path), 'dispatch_attempted': False,
               'budget': 100, 'max_retries': 1, 'usage': 'unknown',
               'inputs': inputs,
               'sha256': {key: hashlib.sha256(path.read_bytes()).hexdigest() for key, path in
                          [('snapshot', snapshot_path), ('contract', contract_path), ('handoff_request', request_path)]},
               'boundary': 'Prepared inputs only; real native admission and review still required'}
    save(receipt_path, receipt)
    return receipt


def mark_attempt(state, receipt, save):
    receipt = dict(receipt, dispatch_attempted=True)
    save(state / 'ready-preflights' / receipt['task_id'] / 'preparation.json', receipt)
    return receipt
