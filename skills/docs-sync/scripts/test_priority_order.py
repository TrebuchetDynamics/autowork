"""TODO.md-owned priority order: drift guard, reconciliation and bootstrap.

Only temporary fixture repositories are written; no consumer repository is touched.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import goals

SCRIPT = Path(__file__).with_name('goals.py')


def body(tid, title, *, scope='x', deps='None.'):
    return (f'### {tid} — {title}\n\n'
            f'- [ ] {tid} — {title}\n'
            f'  Status: open\n  Scope: {scope}\n  Acceptance: x\n  Checks: true\n'
            f'  Dependencies: {deps}\n\n')


def todo(now=(), nxt=(), decision=()):
    parts = ['# Work\n\n## Now\n\n', *now, '## Next\n\n', *nxt]
    if decision:
        parts += ['## Needs decision\n\n', *decision]
    return ''.join(parts) + '## Goal coverage\n\n'


def ledger(tasks, goal_rows=None):
    goal_rows = goal_rows or [{'id': 'G', 'priority': 1}]
    rows = []
    for g in goal_rows:
        rows.append({'id': g['id'], 'title': g['id'], 'source': 'TODO.md', 'status': g.get('status', 'partial'),
                     'priority': g['priority'], 'depends_on': [],
                     'tasks': [t['id'] for t in tasks if t.get('goal', 'G') == g['id']]})
    return {'version': 1, 'goals': rows,
            'tasks': [{'id': t['id'], 'title': t['id'], 'goal': t.get('goal', 'G'),
                       'status': t.get('status', 'open'), 'section': t.get('section', 'Now'),
                       'depends_on': t.get('depends_on', [])} for t in tasks]}


class PriorityOrderTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.repo = Path(self.directory.name)
        self.todo = self.repo / 'TODO.md'
        self.goals = self.repo / 'goals.json'

    def write(self, text, data):
        self.todo.write_text(text)
        goals.dump(self.repo, data)

    def cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPT), args[0], str(self.repo), *args[1:]],
                              capture_output=True, text=True)

    def next_ids(self):
        result = self.cli('next', '--json')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return [row['task']['id'] for row in json.loads(result.stdout)]

    def bootstrap(self):
        plan = self.cli('bootstrap-order', '--dry-run')
        self.assertEqual(plan.returncode, 0, plan.stdout + plan.stderr)
        plan = json.loads(plan.stdout)
        applied = self.cli('bootstrap-order', '--expected-revision', plan['revision'])
        self.assertEqual(applied.returncode, 0, applied.stdout + applied.stderr)
        return plan, json.loads(applied.stdout)

    def swap_t1_t2(self):
        text = self.todo.read_text()
        one, two = body('T1', 'old'), body('T2', 'urgent')
        self.assertIn(one + two, text)
        self.todo.write_text(text.replace(one + two, two + one))

    def t1_t2_fixture(self):
        # Ledger (legacy) order T1, T2; TODO order T2, T1 before migration.
        self.write(todo(now=[body('T2', 'urgent'), body('T1', 'old')]), ledger([{'id': 'T1'}, {'id': 'T2'}]))

    def test_t1_t2_migration_preserves_then_human_reorder_changes_selection(self):
        self.t1_t2_fixture()
        before_blocks = {tid: body(tid, title) for tid, title in (('T1', 'old'), ('T2', 'urgent'))}
        self.assertEqual(self.next_ids(), ['T1', 'T2'])

        plan, applied = self.bootstrap()
        self.assertEqual(plan['outcome'], 'BOOTSTRAP_PLAN')
        self.assertEqual(plan['regions'], [{'heading': 'Now', 'before': ['T2', 'T1'], 'after': ['T1', 'T2']}])
        self.assertEqual(applied['outcome'], 'BOOTSTRAPPED')
        self.assertEqual(self.todo.read_text(), todo(now=[before_blocks['T1'], before_blocks['T2']]))
        self.assertEqual(json.loads(self.goals.read_text())['priority_order'],
                         {'schema': 1, 'tasks': ['T1', 'T2']})
        self.assertEqual(self.next_ids(), ['T1', 'T2'])

        self.swap_t1_t2()
        drift = self.cli('next', '--json')
        self.assertEqual(drift.returncode, 3, drift.stdout + drift.stderr)
        report = json.loads(drift.stdout)
        self.assertEqual(report['outcome'], 'PRIORITY_DRIFT')
        self.assertEqual((report['todo_order'], report['recorded_order']), (['T2', 'T1'], ['T1', 'T2']))
        self.assertEqual(report['moved'], ['T1', 'T2'])
        self.assertIn('goals.py reorder', report['action'])
        self.assertEqual(self.cli('next').returncode, 3)

        todo_bytes = self.todo.read_bytes()
        reconciled = self.cli('reorder', '--expected-revision', report['revision'])
        self.assertEqual(reconciled.returncode, 0, reconciled.stdout + reconciled.stderr)
        self.assertEqual(json.loads(reconciled.stdout)['outcome'], 'RECONCILED')
        self.assertEqual(self.todo.read_bytes(), todo_bytes)
        self.assertEqual(self.next_ids(), ['T2', 'T1'])

        ledger_bytes = self.goals.read_bytes()
        again = self.cli('reorder')
        self.assertEqual(json.loads(again.stdout)['outcome'], 'UNCHANGED')
        self.assertEqual(self.goals.read_bytes(), ledger_bytes)

    def test_unmigrated_ledger_keeps_legacy_order_with_visible_flag(self):
        self.t1_t2_fixture()
        data = goals.normalize(goals.load(self.repo))
        self.assertEqual(goals.priority_status(data, self.todo.read_text())['state'], 'unmigrated')
        text = self.cli('next')
        self.assertEqual(text.returncode, 0, text.stderr)
        self.assertTrue(text.stdout.startswith('T1'))
        self.assertIn('UNMIGRATED', text.stderr)
        rows = json.loads(self.cli('next', '--json').stdout)
        self.assertEqual({row['priority_state'] for row in rows}, {'unmigrated'})
        refused = self.cli('reorder')
        self.assertNotEqual(refused.returncode, 0)
        self.assertIn('bootstrap-order', refused.stdout + refused.stderr)

    def test_bootstrap_is_idempotent_and_requires_dry_run_revision(self):
        self.t1_t2_fixture()
        original = (self.todo.read_bytes(), self.goals.read_bytes())
        missing = self.cli('bootstrap-order')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('--dry-run', missing.stdout + missing.stderr)
        stale = self.cli('bootstrap-order', '--expected-revision', '0' * 64)
        self.assertNotEqual(stale.returncode, 0)
        self.assertEqual((self.todo.read_bytes(), self.goals.read_bytes()), original)
        self.bootstrap()
        migrated = (self.todo.read_bytes(), self.goals.read_bytes())
        self.swap_t1_t2()  # disagreement must never rerun bootstrap
        swapped = self.todo.read_bytes()
        for args in (('--dry-run',), ('--expected-revision', goals.revision(self.repo))):
            result = self.cli('bootstrap-order', *args)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['outcome'], 'ALREADY_BOOTSTRAPPED')
        self.assertEqual((self.todo.read_bytes(), self.goals.read_bytes()), (swapped, migrated[1]))

    def test_matching_repository_gets_snapshot_without_todo_rewrite(self):
        self.write(todo(now=[body('T1', 'old'), body('T2', 'urgent')]), ledger([{'id': 'T1'}, {'id': 'T2'}]))
        before = self.todo.read_bytes()
        plan, applied = self.bootstrap()
        self.assertFalse(plan['rewrite_todo'])
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertEqual(json.loads(self.goals.read_text())['priority_order']['tasks'], ['T1', 'T2'])

    def test_bootstrap_ranks_blocked_and_later_eligible_tasks(self):
        # A is blocked by D; legacy goal priority still ranks A above B once D is done.
        rows = [{'id': 'GA', 'priority': 1}, {'id': 'GB', 'priority': 2}, {'id': 'GD', 'priority': 3}]
        self.write(todo(now=[body('B', 'b'), body('A', 'a', deps='D.')], nxt=[body('D', 'd')]),
                   ledger([{'id': 'A', 'goal': 'GA', 'depends_on': ['D']}, {'id': 'B', 'goal': 'GB'},
                           {'id': 'D', 'goal': 'GD', 'section': 'Next'}], rows))
        self.assertEqual(self.next_ids(), ['B', 'D'])
        self.bootstrap()
        self.assertEqual(self.next_ids(), ['B', 'D'])
        self.assertEqual(json.loads(self.goals.read_text())['priority_order']['tasks'], ['A', 'B', 'D'])
        data = json.loads(self.goals.read_text())
        next(t for t in data['tasks'] if t['id'] == 'D')['status'] = 'done'
        self.goals.write_text(json.dumps(data))
        self.assertEqual(self.next_ids(), ['A', 'B'])

    def test_human_order_outranks_goal_priority_across_goals(self):
        rows = [{'id': 'G1', 'priority': 1}, {'id': 'G2', 'priority': 2}]
        self.write(todo(now=[body('T1', 'old'), body('T2', 'urgent')]),
                   ledger([{'id': 'T1', 'goal': 'G1'}, {'id': 'T2', 'goal': 'G2'}], rows))
        self.bootstrap()
        self.swap_t1_t2()
        self.assertEqual(self.cli('reorder').returncode, 0)
        self.assertEqual(self.next_ids(), ['T2', 'T1'])

    def test_focus_constrains_selection_without_rewriting_recorded_intent(self):
        rows = [{'id': 'G1', 'priority': 1}, {'id': 'G2', 'priority': 2}]
        self.write(todo(now=[body('T1', 'old'), body('T2', 'urgent')]),
                   ledger([{'id': 'T1', 'goal': 'G1'}, {'id': 'T2', 'goal': 'G2'}], rows))
        self.bootstrap()
        self.assertEqual(self.cli('focus', 'G1').returncode, 0)
        self.swap_t1_t2()
        result = self.cli('reorder')
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report['priority_order'], ['T2', 'T1'])
        self.assertTrue(any('focus' in note and 'T2' in note for note in report['notes']), report)
        self.assertEqual(self.next_ids(), ['T1', 'T2'])
        self.assertEqual(json.loads(self.goals.read_text())['priority_order']['tasks'], ['T2', 'T1'])

    def test_reorder_refuses_missing_or_duplicate_bodies_without_writing(self):
        self.t1_t2_fixture()
        self.bootstrap()
        ledger_bytes = self.goals.read_bytes()
        self.todo.write_text(self.todo.read_text().replace(body('T2', 'urgent'), ''))
        missing = self.cli('reorder')
        self.assertNotEqual(missing.returncode, 0)
        self.assertIn('T2', missing.stdout + missing.stderr)
        self.todo.write_text(todo(now=[body('T1', 'old'), body('T2', 'urgent'), body('T2', 'urgent')]))
        duplicate = self.cli('reorder')
        self.assertNotEqual(duplicate.returncode, 0)
        self.assertEqual(self.goals.read_bytes(), ledger_bytes)

    def test_stale_reorder_revision_writes_nothing(self):
        self.t1_t2_fixture()
        self.bootstrap()
        self.swap_t1_t2()
        before = self.goals.read_bytes()
        result = self.cli('reorder', '--expected-revision', '0' * 64)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('stale revision', result.stderr)
        self.assertEqual(self.goals.read_bytes(), before)

    def test_render_prose_edits_and_completion_do_not_create_drift(self):
        self.t1_t2_fixture()
        self.bootstrap()
        self.assertEqual(self.cli('render').returncode, 0)
        self.todo.write_text(self.todo.read_text().replace('Scope: x', 'Scope: clarified wording', 1))
        self.assertEqual(self.next_ids(), ['T1', 'T2'])
        self.assertEqual(self.cli('task', 'T1', 'done').returncode, 0)
        self.assertEqual(self.next_ids(), ['T2'])

    def test_added_task_is_drift_until_reconciled_at_its_todo_position(self):
        self.t1_t2_fixture()
        self.bootstrap()
        self.assertEqual(self.cli('add-task', 'T3', '--goal', 'G', '--title', 'T3', '--section', 'Now').returncode, 0)
        self.todo.write_text(self.todo.read_text().replace('## Now\n\n', '## Now\n\n' + body('T3', 'T3'), 1))
        drift = json.loads(self.cli('next', '--json').stdout)
        self.assertEqual((drift['outcome'], drift['added']), ('PRIORITY_DRIFT', ['T3']))
        self.assertEqual(self.cli('reorder').returncode, 0)
        self.assertEqual(self.next_ids(), ['T3', 'T1', 'T2'])

    def test_bootstrap_refuses_section_disagreement(self):
        self.write(todo(now=[body('T1', 'old')], nxt=[body('T2', 'urgent')]),
                   ledger([{'id': 'T1'}, {'id': 'T2'}]))
        result = self.cli('bootstrap-order', '--dry-run')
        self.assertNotEqual(result.returncode, 0)
        report = json.loads(result.stdout)
        self.assertEqual(report['outcome'], 'BOOTSTRAP_CONFLICT')
        self.assertTrue(any('T2' in reason for reason in report['reasons']))

    def test_backlog_check_holds_on_drift(self):
        self.t1_t2_fixture()
        self.bootstrap()
        self.swap_t1_t2()
        data = goals.normalize(goals.load(self.repo))
        with self.assertRaises(goals.PriorityDrift):
            goals.queue(data, self.todo.read_text())
        picks, status = goals.queue(data, self.todo.read_text(), allow_drift=True)
        self.assertEqual(status['state'], 'drift')
        self.assertEqual([t['id'] for t, _ in picks], ['T1', 'T2'])


class TaskBodyTests(unittest.TestCase):
    def test_next_task_id_heading_does_not_leak_into_last_field(self):
        text = todo(now=[body('T1', 'old'), body('T2', 'urgent')])
        fields = goals.task_fields(goals.task_bodies(text)['T1'][0][0])
        self.assertEqual(fields['Dependencies'], 'None.')
        group = '# Work\n\n## Now\n\n- [ ] T1 — a\n  Dependencies: None.\n\n### Later group\n\n- [ ] T2 — b\n'
        self.assertIn('Later group', goals.task_bodies(group)['T1'][0][0])


class EntryPointTests(unittest.TestCase):
    def test_selection_entry_points_use_the_shared_guard(self):
        root = Path(__file__).resolve().parents[2]
        offenders = []
        for path in root.rglob('*.py'):
            if path.name.startswith('test_') or path.name == 'goals.py':
                continue
            if 'eligible(' in path.read_text() and 'def eligible' not in path.read_text():
                if '.eligible(' in path.read_text():
                    offenders.append(str(path.relative_to(root)))
        self.assertEqual(offenders, [], 'call goals.queue(data, todo_text) so drift cannot be bypassed')


if __name__ == '__main__':
    unittest.main()
