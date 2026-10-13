"""Bound dependency parsing work without machine-dependent timing assertions."""
import cProfile
import json
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

import retry_selection


class SelectionCostTests(unittest.TestCase):
    def test_backlog_dependency_search_work_grows_linearly(self):
        size = 80
        with tempfile.TemporaryDirectory() as directory:
            repo = Path(directory)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / 'SPEC.md').write_text('# Accepted\n\nStatus: Accepted\n')
            tasks = [dict(id=f'T{i:04d}', goal='G1', title=f'Task {i}', status='open', section='Now')
                     for i in range(size)]
            (repo / 'goals.json').write_text(json.dumps(dict(version=1,
                goals=[dict(id='G1', title='Fixture', status='unmet', source='SPEC.md#accepted',
                            tasks=[task['id'] for task in tasks])], tasks=tasks)))
            (repo / 'TODO.md').write_text('# TODO\n\n## Now\n\n' + ''.join(
                f'- [ ] {task["id"]}: Task\n  Goal: G1\n  Scope: fixture.py\n'
                '  Acceptance: tests pass\n  Dependencies: None\n  Sources: [Plan](SPEC.md#accepted)\n\n'
                for task in tasks))
            before = {name: (repo / name).read_bytes() for name in ('SPEC.md', 'TODO.md', 'goals.json')}
            profiler = cProfile.Profile()
            with profiler:
                result = retry_selection.select(repo)
            self.assertEqual(result['state'], 'ready_for_autowork', result)
            self.assertEqual(result['selected_task']['id'], 'T0000')
            for name, content in before.items():
                self.assertEqual((repo / name).read_bytes(), content)
            # Regressing to a regex per known ID per task exceeds this budget.
            searches = sum(entry.callcount for entry in profiler.getstats()
                           if entry.code is re.search.__code__)
            self.assertLessEqual(searches, size * 8,
                                 'Dependency validation must not rescan every known ID for every task')


if __name__ == '__main__':
    unittest.main()
