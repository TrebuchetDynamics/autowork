"""DOCS-MAINTAINER triggers, trigger-set key and run record (TOOLSET-164-f1)."""
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import maintainer  # noqa: E402


class MaintainerTests(unittest.TestCase):
    def test_planning_holds_and_unrunnable_tasks_trigger_and_nothing_else_does(self):
        rows = [
            {'task': 'A', 'state': 'held', 'cause': 'scope', 'reason': 'changed files violate Touches'},
            {'task': 'B', 'state': 'held', 'cause': 'blocker', 'reason': 'worker reported a blocker: which API?'},
            {'task': 'C', 'state': 'waiting', 'reason': 'not runnable: missing Checks'},
            {'task': 'D', 'state': 'held', 'cause': 'crash', 'reason': 'dead worker'},          # not planning
            {'task': 'E', 'state': 'held', 'cause': 'scope', 'worker_live': True},              # still working
            {'task': 'F', 'state': 'waiting', 'reason': 'dependency: A'},
            {'task': 'G', 'state': 'running'},
        ]
        found = maintainer.triggers(rows)
        self.assertEqual([t for t, _, _ in found], ['A', 'B', 'C'])
        self.assertEqual(maintainer.key(found), maintainer.key(maintainer.triggers(list(reversed(rows)))))
        self.assertEqual(maintainer.triggers([r for r in rows if r['task'] in 'DEFG']), [])

    def test_only_planning_files_may_change(self):
        self.assertTrue(maintainer.planning_only(['TODO.md', 'goals.json', 'docs/tasks/A.md']))
        self.assertFalse(maintainer.planning_only(['TODO.md', 'src/app.py']))
        self.assertFalse(maintainer.planning_only([]))

    def test_the_last_run_is_recorded_for_status(self):
        with tempfile.TemporaryDirectory() as state:
            found = [('A', 'held: scope', 'x')]
            maintainer.remember(state, trigger_key='k1', found=found, outcome='merged', changed=['A'], now=100)
            self.assertEqual(maintainer.last(state), {'role': 'DOCS-MAINTAINER', 'key': 'k1', 'at': 100,
                                                      'outcome': 'merged', 'triggers': ['A'], 'changed': ['A']})
            self.assertIn('- A (held: scope): x', maintainer.prompt(found, '/repo', 'goals.py'))


if __name__ == '__main__':
    unittest.main()
