#!/usr/bin/env python3
"""Retry selection against the canonical consumer after bounded docs-sync maintenance."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import re
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('retry_goals', Path(__file__).resolve().parents[2] / 'docs-sync/scripts/goals.py')
assert spec is not None and spec.loader is not None
goals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(goals)


REGISTRY = 'docs/coordination/worktree-registry.jsonl'


def registered_claims(repo):
    """Read the repository's append-only claims; never infer release from age."""
    blob = goals.checked_bytes(Path(repo) / REGISTRY)
    latest = {}
    for number, line in enumerate((blob or b'').decode('utf-8').splitlines(), 1):
        if not line.strip():
            continue
        location = f'invalid worktree registry {REGISTRY}:{number}'
        try:
            row = json.loads(line)
        except json.JSONDecodeError as exc:
            raise ValueError(f'{location}: malformed JSON; reconcile repository ownership') from exc
        if not isinstance(row, dict):
            raise ValueError(f'{location}: expected object; reconcile repository ownership')
        missing = [key for key in ('task', 'worktree', 'status', 'owner')
                   if not isinstance(row.get(key), str) or not row[key]]
        if missing:
            raise ValueError(f'{location}: nonempty string required for {", ".join(missing)}; '
                             'reconcile repository ownership')
        latest[(row['task'], row['worktree'])] = row
    # Completed/reviewed candidates still need owner integration. Only explicit
    # release/integration ends this adapter's hold, and native checks still run.
    held = [r for r in latest.values() if r['status'].upper() not in ('RELEASED', 'INTEGRATED')]
    return held, blob


def accepted_task_plan(repo, task, goal):
    def accepted(ref):
        problems = []
        section = goals.local_reference(repo, ref, {}, problems)
        return '#' in ref and not problems and not goals.plan_acceptance_error(section)
    plan = goals.reference_key(goal['source'])
    todo = goals.checked_bytes(repo / 'TODO.md')
    entries = goals.task_bodies(todo.decode('utf-8')).get(task['id'], []) if todo else []
    sources = goals.task_fields(entries[0][0]).get('Sources', '') if len(entries) == 1 else ''
    candidates = sorted({goals.reference_key(ref) for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', sources) if accepted(ref)})
    if plan in candidates:
        return plan
    if len(candidates) > 1:
        raise ValueError('multiple accepted task-source plans; preserve an explicit named slice')
    return candidates[0] if candidates else plan


def select(consumer, *, canonical_repo=None, plan=None, task_ids=None, require_owner=False):
    if (plan is None) != (task_ids is None):
        raise ValueError('named-plan retry requires both plan and task IDs')
    with goals.coordination(consumer, canonical_repo) as repo:
        result = {'state': 'draft_saved', 'authoritative_repo': str(repo), 'selected_task': None,
                  'live_ownership': 'unknown', 'reasons': [],
                  'boundary': 'fresh consumer selection only; no dispatch or implementation authority'}
        if not (repo / 'goals.json').is_file():
            result['reasons'] = ['consumer backlog absent; docs-only scratch does not qualify']
            return result
        initial_revision = goals.revision(repo)
        data = goals.load(repo)
        problems = goals.errors(data)
        if problems:
            result['reasons'] = problems
            return result
        claims, registry_blob = registered_claims(repo)
        held_ids = {row['task'] for row in claims} if require_owner else set()
        result['recorded_claims'] = claims
        result['held_claims'] = claims if require_owner else []
        picks = [(task, goal) for task, goal in goals.eligible(goals.normalize(data))
                 if task['id'] not in held_ids]
        result['reconciliation_task_ids'] = [t['id'] for t in data['tasks']
                                              if t['status'] == 'in_progress']
        # Existing work belongs to reconciliation, not another new dispatch.
        # Retain the diagnostic path when there is no open alternative.
        open_picks = [(task, goal) for task, goal in picks if task['status'] == 'open']
        # Explicit recovery must diagnose contracts even when execution is gated.
        # Eligibility still runs inside backlog_check after contract validation.
        if not picks and plan is None:
            result.update(state='backlog_reconciled_not_eligible', reasons=['no current dependency-ready ledger task'])
            return result
        if plan is None:
            first, owner = (open_picks or picks)[0]
            if data.get('primary_milestone') and first['goal'] != data['primary_milestone']:
                result.update(state='backlog_reconciled_not_eligible',
                              reasons=['focused milestone has no eligible slice; unrelated fallback needs attestation'])
                return result
            task_ids = [first['id']]
            try:
                plan = accepted_task_plan(repo, first, owner)
            except ValueError as exc:
                result['reasons'] = [str(exc)]
                return result
        assert task_ids is not None
        args = argparse.Namespace(repo=str(repo), plan=plan, tasks=','.join(task_ids), receipt=None)
        output = io.StringIO()
        with redirect_stdout(output):
            goals.backlog_check(args)
        receipt = json.loads(output.getvalue())
        result.update(receipt)
        if (goals.revision(repo) != initial_revision or
                goals.checked_bytes(repo / REGISTRY) != registry_blob):
            result.update(state='draft_saved', reasons=receipt['reasons'] + ['consumer changed during retry'])
            return result
        if held_ids.intersection(task_ids):
            result.update(state='backlog_reconciled_not_eligible',
                reasons=[f"{r['task']}: registered writer {r['owner']} ({r['status']}) at {r['worktree']}"
                         for r in claims if r['task'] in task_ids])
            return result
        ordering_holds = {f'current frontier {tid} precedes requested plan' for tid in held_ids}
        if (result['state'] == 'backlog_reconciled_not_eligible' and result['reasons']
                and set(result['reasons']) <= ordering_holds):
            result.update(state='ready_for_autowork', reasons=[],
                          skipped_registered_claims=sorted(held_ids))
        if result['state'] == 'ready_for_autowork':
            result['selected_task'] = next((task for task, _ in picks
                                           if task['id'] in task_ids and task['status'] == 'open'), None)
            if result['selected_task'] is None:
                result.update(state='backlog_reconciled_not_eligible', reasons=['requested slice has no unclaimed open task'])
        return result


def repository_frontier(consumer, limit=3, *, require_owner=False):
    """Find alternatives without changing focus, task status, claims or admission."""
    with goals.coordination(consumer) as repo:
        revision = goals.revision(repo)
        data = goals.load(repo)
        problems = goals.errors(data)
        if problems:
            raise ValueError('; '.join(problems))
        claims, registry_blob = registered_claims(repo)
    held_ids = {r['task'] for r in claims} if require_owner else set()
    candidates, rejected = [], []
    for task, goal in goals.eligible(goals.normalize(data)):
        if task['status'] != 'open' or task['id'] in held_ids:
            continue
        try:
            plan = accepted_task_plan(repo, task, goal)
            checked = select(repo, plan=plan, task_ids=[task['id']], require_owner=require_owner)
        except ValueError as exc:
            rejected.append({'task_id': task['id'], 'reasons': [str(exc)]})
            continue
        if checked['state'] != 'ready_for_autowork':
            rejected.append({'task_id': task['id'], 'reasons': checked['reasons']})
            continue
        candidates.append({'task': task, 'plan': plan,
            'requires_fallback_attestation': bool(data.get('primary_milestone') and
                                                   task['goal'] != data['primary_milestone'])})
        if len(candidates) >= limit:
            break
    if (goals.revision(repo) != revision or
            goals.checked_bytes(repo / REGISTRY) != registry_blob):
        raise ValueError('consumer changed during frontier search; retry selection')
    return {'state': 'candidates_found' if candidates else 'no_unclaimed_candidate',
            'candidates': candidates, 'recorded_claims': claims,
            'held_claims': claims if require_owner else [], 'rejected': rejected,
            'boundary': 'Read-only candidates, not dispatch authorization. Check file-scope overlap, current owner and native admission.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer', help='actual repository consumer, not the documentation scratch checkout')
    parser.add_argument('--canonical-repo')
    parser.add_argument('--require-owner', action='store_true', help='Opt into recorded owner release gates')
    parser.add_argument('--repository-frontier', action='store_true')
    parser.add_argument('--plan')
    parser.add_argument('--tasks')
    args = parser.parse_args()
    try:
        if args.repository_frontier:
            if args.plan or args.tasks or args.canonical_repo:
                parser.error('frontier takes the canonical consumer without named-task options')
            result = repository_frontier(args.consumer, require_owner=args.require_owner)
            print(json.dumps(result, indent=2))
            return 0 if result['candidates'] else 2
        result = select(args.consumer, canonical_repo=args.canonical_repo, plan=args.plan,
                        task_ids=args.tasks.split(',') if args.tasks is not None else None, require_owner=args.require_owner)
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
    return {'ready_for_autowork': 0, 'draft_saved': 1, 'backlog_reconciled_not_eligible': 2}[result['state']]


if __name__ == '__main__':
    sys.exit(main())
