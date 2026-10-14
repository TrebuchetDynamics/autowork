"""Direct TODO selection honors the recorded human priority; no model calls."""
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'owner_cycle.py'
GOALS = HERE.parents[1] / 'docs-sync/scripts/goals.py'


def body(tid, title):
    return (f'### {tid} — {title}\n\n- [ ] {tid} — {title}\n  Status: open\n  Scope: x\n'
            f'  Acceptance: x\n  Checks: true\n  Dependencies: None.\n\n')


class PrioritySelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(); self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'; self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.state = Path(self.tmp.name) / 'state'; self.state.mkdir()
        self.todo = self.repo / 'TODO.md'
        self.todo.write_text('# Work\n\n## Now\n\n' + body('T2', 'urgent') + body('T1', 'old') + '## Next\n\n')
        task = lambda tid: {'id': tid, 'title': tid, 'goal': 'G', 'status': 'open', 'section': 'Now', 'depends_on': []}
        (self.repo / 'goals.json').write_text(json.dumps({'version': 1, 'goals': [
            {'id': 'G', 'title': 'g', 'source': 'TODO.md', 'status': 'partial', 'priority': 1,
             'tasks': ['T1', 'T2'], 'depends_on': []}], 'tasks': [task('T1'), task('T2')]}))

    def select(self, *args):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--state-dir', str(self.state), *args],
                           capture_output=True, text=True, timeout=15)
        return p, json.loads(p.stdout)

    def goals(self, *args):
        p = subprocess.run([sys.executable, str(GOALS), args[0], str(self.repo), *args[1:]],
                           capture_output=True, text=True, timeout=15)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        return json.loads(p.stdout) if p.stdout.startswith('{') else p.stdout

    def bootstrap_then_swap(self):
        plan = self.goals('bootstrap-order', '--dry-run')
        self.goals('bootstrap-order', '--expected-revision', plan['revision'])
        self.assertEqual(self.select()[1]['task']['id'], 'T1')
        text = self.todo.read_text()
        self.todo.write_text(text.replace(body('T1', 'old') + body('T2', 'urgent'), body('T2', 'urgent') + body('T1', 'old')))

    def test_unmigrated_selection_is_legacy_with_visible_flag(self):
        p, r = self.select()
        self.assertEqual(p.returncode, 0, r)
        self.assertEqual((r['outcome'], r['task']['id']), ('READY', 'T1'))
        self.assertEqual(r['priority']['state'], 'unmigrated')
        self.assertIn('UNMIGRATED', r['priority']['action'])

    def test_drift_stops_default_selection_and_reorder_changes_the_pick(self):
        self.bootstrap_then_swap()
        p, r = self.select()
        self.assertEqual(p.returncode, 1)
        self.assertEqual(r['outcome'], 'PRIORITY_DRIFT')
        self.assertNotIn('task', r)
        self.assertEqual((r['todo_order'], r['recorded_order']), (['T2', 'T1'], ['T1', 'T2']))
        applied = self.select('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual(applied[1]['outcome'], 'PRIORITY_DRIFT')
        self.assertFalse((self.repo / '.git/autowork-execution/active.json').exists())
        self.goals('reorder')
        p, r = self.select()
        self.assertEqual(p.returncode, 0, r)
        self.assertEqual((r['outcome'], r['task']['id'], r['priority']['state']), ('READY', 'T2', 'synced'))

    def test_named_task_and_active_claim_continue_through_drift(self):
        plan = self.goals('bootstrap-order', '--dry-run')
        self.goals('bootstrap-order', '--expected-revision', plan['revision'])
        claimed = self.select('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual((claimed[1]['outcome'], claimed[1]['task']['id']), ('EXECUTE', 'T1'))
        text = self.todo.read_text()
        self.todo.write_text(text.replace(body('T1', 'old') + body('T2', 'urgent'), body('T2', 'urgent') + body('T1', 'old')))
        resumed = self.select('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual((resumed[1]['outcome'], resumed[1]['task']['id']), ('EXECUTE', 'T1'))
        self.assertEqual(resumed[1]['priority']['state'], 'drift')
        self.assertEqual(self.select('--release', '--owner-pid', str(os.getpid()))[1]['outcome'], 'RELEASED')
        named = self.select('--tasks', 'T1')
        self.assertEqual((named[1]['outcome'], named[1]['priority']['state']), ('READY', 'drift'))

    def test_goals_next_and_direct_selection_agree(self):
        for step in ('unmigrated', 'migrated', 'reconciled'):
            if step == 'migrated':
                self.bootstrap_then_swap()
                self.assertEqual(subprocess.run([sys.executable, str(GOALS), 'next', str(self.repo)],
                                                capture_output=True).returncode, 3)
                self.assertEqual(self.select()[1]['outcome'], 'PRIORITY_DRIFT')
                self.goals('reorder')
            listed = json.loads(subprocess.run([sys.executable, str(GOALS), 'next', str(self.repo), '--json'],
                                               capture_output=True, text=True).stdout)
            self.assertEqual(listed[0]['task']['id'], self.select()[1]['task']['id'], step)


if __name__ == '__main__':
    unittest.main()
