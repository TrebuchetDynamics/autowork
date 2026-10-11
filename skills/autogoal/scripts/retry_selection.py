#!/usr/bin/env python3
"""Retry selection against the canonical consumer after bounded repo-docs maintenance."""
import argparse
from contextlib import redirect_stdout
import importlib.util
import io
import json
import re
from pathlib import Path
import sys

spec = importlib.util.spec_from_file_location('retry_goals', Path(__file__).resolve().parents[2] / 'repo-docs/scripts/goals.py')
assert spec is not None and spec.loader is not None
goals = importlib.util.module_from_spec(spec)
spec.loader.exec_module(goals)


def select(consumer, *, canonical_repo=None, plan=None, task_ids=None):
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
        picks = goals.eligible(goals.normalize(data))
        if not picks:
            result.update(state='backlog_reconciled_not_eligible', reasons=['no current dependency-ready ledger task'])
            return result
        first, owner = picks[0]
        if plan is None:
            if data.get('primary_milestone') and first['goal'] != data['primary_milestone']:
                result.update(state='backlog_reconciled_not_eligible',
                              reasons=['focused milestone has no eligible slice; unrelated fallback needs attestation'])
                return result
            plan, task_ids = owner['source'], [first['id']]
            def accepted(ref):
                problems = []
                section = goals.local_reference(repo, ref, {}, problems)
                return ('#' in ref and not problems and
                        re.search(r'^\s*(?:\*\*)?Status:(?:\*\*)?\s*Accepted\s*$', section, re.M | re.I))
            if not accepted(plan):
                todo = goals.checked_bytes(repo / 'TODO.md')
                entries = goals.task_bodies(todo.decode('utf-8')).get(first['id'], []) if todo else []
                sources = goals.task_fields(entries[0][0]).get('Sources', '') if len(entries) == 1 else ''
                candidates = sorted({ref for ref in re.findall(r'\[[^\]]*\]\(([^\s)]+)\)', sources) if accepted(ref)})
                if len(candidates) > 1:
                    result['reasons'] = ['multiple accepted task-source plans; preserve an explicit named slice']
                    return result
                if candidates:
                    plan = candidates[0]
        assert task_ids is not None
        args = argparse.Namespace(repo=str(repo), plan=plan, tasks=','.join(task_ids), receipt=None)
        output = io.StringIO()
        with redirect_stdout(output):
            goals.backlog_check(args)
        receipt = json.loads(output.getvalue())
        result.update(receipt)
        if goals.revision(repo) != initial_revision:
            result.update(state='draft_saved', reasons=receipt['reasons'] + ['consumer changed during retry'])
            return result
        if receipt['state'] == 'ready_for_autogoal':
            result['selected_task'] = next((task for task, _ in picks
                                           if task['id'] in task_ids and task['status'] == 'open'), None)
            if result['selected_task'] is None:
                result.update(state='backlog_reconciled_not_eligible', reasons=['requested slice has no unclaimed open task'])
        return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('consumer', help='actual repository consumer, not the documentation scratch checkout')
    parser.add_argument('--canonical-repo')
    parser.add_argument('--plan')
    parser.add_argument('--tasks')
    args = parser.parse_args()
    try:
        result = select(args.consumer, canonical_repo=args.canonical_repo, plan=args.plan,
                        task_ids=args.tasks.split(',') if args.tasks is not None else None)
    except (ValueError, OSError, TypeError, KeyError) as error:
        parser.exit(1, str(error) + '\n')
    print(json.dumps(result, indent=2))
    return {'ready_for_autogoal': 0, 'draft_saved': 1, 'backlog_reconciled_not_eligible': 2}[result['state']]


if __name__ == '__main__':
    sys.exit(main())
