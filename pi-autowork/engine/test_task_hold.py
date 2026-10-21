"""A task whose record says `Held by:` is a claim: never selected or dispatched, and it still
blocks what shares its resources, until the note is removed or its date passes."""
import datetime
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

import parallel_plan
import task_queue
import task_select

FIXTURE = Path(__file__).parent / 'fixtures' / 'task_store'


class HeldTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        shutil.copytree(FIXTURE, self.repo)
        base = (self.repo / 'tasks/items/T-1.md').read_text()
        base = base.replace('touches = ["src/"]', 'touches = ["src/a.py"]')
        (self.repo / 'tasks/items/T-1.md').write_text(
            base.replace('resources = []', 'resources = ["db"]') + '- Held by: an interactive session; until 2999-01-01\n')
        (self.repo / 'tasks/items/T-2.md').write_text(
            base.replace('"T-1"', '"T-2"').replace('rank = 1', 'rank = 2').replace('resources = []', 'resources = ["db"]')
            .replace('src/a.py', 'src/b.py'))
        (self.repo / 'tasks/items/T-3.md').write_text(
            base.replace('"T-1"', '"T-3"').replace('rank = 1', 'rank = 3').replace('src/a.py', 'docs/c.md'))
        self.git('init', '-q')
        self.commit()

    def git(self, *args):
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=f@example.invalid', '-c', 'user.name=F', *args],
                       check=True, capture_output=True)

    def commit(self):
        self.git('add', '-A')
        self.git('commit', '-q', '--allow-empty', '-m', 'tasks')

    def test_a_held_task_is_never_dispatched(self):
        chosen, reasons = task_queue.selectable(self.repo)
        self.assertEqual([c['id'] for c in chosen], ['T-2', 'T-3'])
        self.assertIn('T-1: held by an interactive session; until 2999-01-01', reasons)
        context = task_queue.unfinished(self.repo)
        planned = parallel_plan.plan(chosen, all_tasks=context)
        self.assertEqual([t['id'] for t in planned['dispatch']], ['T-3'])
        self.assertEqual(planned['waiting'], [{'id': 'T-2', 'reason': 'shared resource with held T-1',
                                               'blocked_by': ['T-1']}])
        # Even named explicitly, a held task does not reach the planner.
        named, why = task_queue.selectable(self.repo, 'T-1')
        self.assertEqual((named, why), ([], ['T-1: held by an interactive session; until 2999-01-01']))

    def test_an_expired_hold_releases_the_task(self):
        record = task_queue.store(self.repo).tasks['T-1']
        self.assertEqual(task_select.held_by(record), 'an interactive session; until 2999-01-01')
        self.assertIsNone(task_select.held_by(record, today=datetime.date(3000, 1, 1)))
        path = self.repo / 'tasks/items/T-1.md'
        path.write_text(path.read_text().replace('until 2999-01-01', 'until 2000-01-01'))
        self.commit()
        chosen, _ = task_queue.selectable(self.repo)
        self.assertEqual([c['id'] for c in chosen], ['T-1', 'T-2', 'T-3'])
        self.assertNotIn('Held by', chosen[0]['fields'], 'an expired hold is history, not a claim')


if __name__ == '__main__':
    unittest.main()
