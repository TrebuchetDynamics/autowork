"""Direct selection honors each task's rank, the human priority; no model calls."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import task_queue
import task_select

HERE = Path(__file__).resolve().parent
SCRIPT = HERE / 'owner_cycle.py'
COMMAND = HERE.parent / 'pi_autowork' / 'command.py'


def record(tid, rank, title):
    return '\n'.join(['+++', 'schema = 1', f'id = "{tid}"', f'title = "{title}"', f'short = "{title}"',
                      'status = "open"', 'goal = "G"', 'section = "Now"', f'rank = {rank}', 'depends_on = []',
                      f'touches = ["{tid.lower()}.py"]', 'resources = []', 'kind = "implementation"',
                      'ownership = "worker"', 'scope = "x"', 'acceptance = ["x"]', 'checks = ["true"]',
                      'exclusions = []', '+++', ''])


class PrioritySelectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        (self.repo / 'tasks/items').mkdir(parents=True)
        (self.repo / 'tasks/goals').mkdir()
        (self.repo / 'tasks/goals/G.md').write_text('+++\nschema = 1\nid = "G"\ntitle = "g"\npriority = 1\n'
                                                    'source = "docs/plan.md#g"\nstatus = "partial"\nfocus = false\n+++\n')
        (self.repo / 'tasks/items/T1.md').write_text(record('T1', 1000, 'old'))
        (self.repo / 'tasks/items/T2.md').write_text(record('T2', 2000, 'urgent'))
        self.state = Path(self.tmp.name) / 'state'
        self.state.mkdir()
        self.git('init', '-q')
        self.commit()

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid', '-c', 'user.name=F', *args],
                       check=True, capture_output=True)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'tasks')

    def select(self):
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--state-dir', str(self.state)],
                           capture_output=True, text=True, timeout=30)
        return p, json.loads(p.stdout)

    def test_the_lowest_rank_is_selected(self):
        p, r = self.select()
        self.assertEqual(p.returncode, 0, r)
        self.assertEqual((r['outcome'], r['task']['id']), ('READY', 'T1'))

    def test_moving_a_task_up_changes_the_pick_and_only_its_file(self):
        moved = subprocess.run([sys.executable, str(COMMAND), 'tasks', 'move', 'T2', 'up', str(self.repo)],
                               capture_output=True, text=True, timeout=30)
        self.assertEqual(moved.returncode, 0, moved.stderr)
        status = subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'], capture_output=True, text=True)
        self.assertEqual(status.stdout.split(), ['M', 'tasks/items/T2.md'])
        self.commit()
        p, r = self.select()
        self.assertEqual((p.returncode, r['task']['id']), (0, 'T2'))

    def test_store_next_and_direct_selection_agree(self):
        _, r = self.select()
        self.assertEqual(task_select.next(task_queue.store(self.repo)).id, r['task']['id'])


if __name__ == '__main__':
    unittest.main()
