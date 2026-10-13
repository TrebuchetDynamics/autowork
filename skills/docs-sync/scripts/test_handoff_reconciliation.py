"""Read-only consumer checks and clerical repair, using real isolated Git ledgers."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPT = Path(__file__).with_name('goals.py')


class HandoffReconciliationTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.plan = self.repo / 'SPEC.md'
        self.plan.write_text('# Slice\n\nStatus: Accepted (implementation only)\n\n'
                             'Approval evidence: fixture owner approved this slice.\n')
        self.todo = self.repo / 'TODO.md'
        self.body = ('# TODO\n\n## Now\n\n- [ ] T1: Verify startup\n'
                     '  Goal: G1\n  Scope: startup check\n'
                     '  Acceptance: startup check passes\n  Dependencies: None\n'
                     '  Ownership: fixture owner\n  Sources: [Slice](SPEC.md#slice)\n')
        self.todo.write_text(self.body)
        (self.repo / 'goals.json').write_text(json.dumps({
            'version': 1,
            'goals': [{'id': 'G1', 'title': 'Startup works', 'source': 'SPEC.md#slice',
                       'status': 'unmet', 'priority': 1, 'tasks': ['T1']}],
            'tasks': [{'id': 'T1', 'goal': 'G1', 'title': 'Verify startup',
                       'status': 'open', 'section': 'Now'}]}))
        subprocess.run([sys.executable, str(SCRIPT), 'fmt', str(self.repo)],
                       check=True, capture_output=True)

    def check(self):
        before = {p.name: p.read_bytes() for p in self.repo.iterdir() if p.is_file()}
        result = subprocess.run([sys.executable, str(SCRIPT), 'backlog-check',
                                 str(self.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(before, {p.name: p.read_bytes() for p in self.repo.iterdir() if p.is_file()})
        return result.returncode, json.loads(result.stdout)

    def test_missing_status_does_not_hide_missing_task_contract(self):
        self.todo.write_text('# TODO\n\n## Now\n')
        code, receipt = self.check()
        self.assertEqual(code, 1)
        self.assertEqual(receipt['state'], 'draft_saved')
        self.assertIn('plan section lacks explicit Status: Accepted', receipt['reasons'])
        self.assertIn('T1: missing or duplicate task body', receipt['reasons'])

    def test_clerical_repair_makes_same_slice_ready_without_claiming_it(self):
        self.assertEqual(self.check()[0], 1)
        ledger = (self.repo / 'goals.json').read_bytes()
        self.plan.write_text(self.plan.read_text().replace(
            'Status: Accepted (implementation only)', 'Status: Accepted\n\nScope: implementation only'))
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'))
        self.assertEqual(receipt['eligible_task_ids'], ['T1'])
        self.assertEqual(ledger, (self.repo / 'goals.json').read_bytes())
        self.assertEqual(receipt, self.check()[1])

    def test_bold_task_ids_are_ready_without_changing_identifiers(self):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        for heading in ('**T1**:', '**`T1`**:', '**T1:**', '**T1: Verify startup**'):
            with self.subTest(heading=heading):
                self.todo.write_text(self.body.replace('T1: Verify startup', heading))
                code, receipt = self.check()
                self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'))
                self.assertEqual(receipt['eligible_task_ids'], ['T1'])

    def test_bold_task_ids_do_not_bypass_duplicate_or_unknown_checks(self):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        for extra, reason in (('T1', 'T1: missing or duplicate task body'),
                              ('T10', 'T10: executable body has no ledger task')):
            with self.subTest(extra=extra):
                self.todo.write_text(self.body + f'\n- [ ] **{extra}**: duplicate or unknown\n')
                code, receipt = self.check()
                self.assertEqual(code, 1)
                self.assertIn(reason, receipt['reasons'])

    def test_proposed_plan_stays_draft_even_with_complete_eligible_backlog(self):
        self.plan.write_text('# Slice\n\nStatus: Proposed\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (1, 'draft_saved'))
        self.assertIn('plan section lacks explicit Status: Accepted', receipt['reasons'])

    def test_fenced_task_examples_are_not_executable_contracts(self):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        for fence in ('```', '~~~~', '   ```markdown'):
            with self.subTest(fence=fence):
                closing = '~~~' if fence == '~~~~' else '```'
                # A shorter closing fence must not end a four-character block.
                end = '\n~~~~\n' if fence == '~~~~' else '\n'
                self.todo.write_text(self.body + '\n' + fence + '\n'
                                     '## Needs decision\n- [ ] T1: example only\n'
                                     '  Goal: EXAMPLE\n' + closing + end)
                code, receipt = self.check()
                self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'), receipt)

    def test_fenced_heading_does_not_steal_real_plan_anchor(self):
        self.plan.write_text('```markdown\n# Slice\nStatus: Proposed\n```\n\n'
                             '# Slice\n\nStatus: Accepted\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'), receipt)

    def test_fenced_fields_and_headings_do_not_end_the_real_task(self):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        self.todo.write_text(self.body.replace('  Acceptance: startup check passes',
            '  ```markdown\n## Example\n  Goal: EXAMPLE\n  ```\n'
            '  Acceptance: startup check passes'))
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'), receipt)

    def test_unclosed_fence_cannot_supply_plan_acceptance(self):
        self.plan.write_text('# Slice\n\n```markdown\nStatus: Accepted\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (1, 'draft_saved'), receipt)

    def test_fenced_example_links_are_not_required_inputs(self):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        self.todo.write_text(self.body + '\n```markdown\n[Example](missing-example.md)\n```\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'), receipt)

    def test_generated_coverage_fields_are_not_part_of_task_contract(self):
        import goals
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        self.todo.write_text(self.body + '\n' + goals.BEGIN + '\nScope: generated example\n'
                            '[Example](missing-example.md)\n' + goals.END + '\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'), receipt)

    def test_generated_coverage_cannot_supply_missing_acceptance(self):
        import goals
        self.plan.write_text('# Slice\n\nStatus: Accepted\n')
        self.todo.write_text(self.body.replace('  Acceptance: startup check passes\n', '')
                            + '\n' + goals.BEGIN + '\nAcceptance: example only\n'
                            + goals.END + '\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (1, 'draft_saved'), receipt)
        self.assertIn('T1: missing Acceptance', receipt['reasons'])

    def test_fenced_acceptance_example_does_not_accept_proposed_plan(self):
        self.plan.write_text('# Slice\n\nStatus: Proposed\n\n'
                             '```markdown\nStatus: Accepted\n```\n')
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (1, 'draft_saved'), receipt)
        self.assertIn('plan section lacks explicit Status: Accepted', receipt['reasons'])

    def add_frontier(self, same_goal=False):
        self.plan.write_text('# Slice\n\nStatus: Accepted\n\n# Other\n\nStatus: Accepted\n')
        data = json.loads((self.repo / 'goals.json').read_text())
        goal = 'G1' if same_goal else 'G2'
        if same_goal:
            data['goals'][0]['tasks'].insert(0, 'T0')
        else:
            data['primary_milestone'] = 'G2'
            data['goals'].append({'id': 'G2', 'title': 'Other work', 'source': 'SPEC.md#other',
                                  'status': 'unmet', 'priority': 0, 'tasks': ['T0']})
        data['tasks'].insert(0, {'id': 'T0', 'goal': goal, 'title': 'Earlier work',
                                 'status': 'open', 'section': 'Now'})
        (self.repo / 'goals.json').write_text(json.dumps(data))
        self.todo.write_text(self.body + f'\n- [ ] T0: Earlier work\n'
                             f'  Goal: {goal}\n  Scope: separate check\n'
                             '  Acceptance: check passes\n  Dependencies: None\n'
                             '  Ownership: fixture owner\n  Sources: [Other](SPEC.md#other)\n')
        subprocess.run([sys.executable, str(SCRIPT), 'fmt', str(self.repo)],
                       check=True, capture_output=True)

    def test_other_goal_frontier_does_not_starve_named_ready_plan(self):
        self.add_frontier()
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (0, 'ready_for_autowork'))
        self.assertEqual(receipt['primary_milestone'], 'G2')
        self.assertTrue(receipt['focus_fallback_required'])
        self.assertEqual(receipt['live_ownership'], 'unknown')
        self.assertIn('T0', receipt['eligible_task_ids'])

    def test_same_goal_frontier_order_remains_required(self):
        self.add_frontier(same_goal=True)
        code, receipt = self.check()
        self.assertEqual((code, receipt['state']), (2, 'backlog_reconciled_not_eligible'))
        self.assertIn('current frontier T0 precedes requested plan', receipt['reasons'])

    def test_invalid_ledger_is_reported_alongside_missing_status(self):
        (self.repo / 'goals.json').write_text('{bad json')
        code, receipt = self.check()
        self.assertEqual(code, 1)
        self.assertTrue(any(reason.startswith('invalid backlog:') for reason in receipt['reasons']))


if __name__ == '__main__':
    unittest.main()
