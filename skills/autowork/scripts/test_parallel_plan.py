"""Offline selection/planning contracts; no worker launch or repository writes."""
from copy import deepcopy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import task_execution


class RunnableTests(unittest.TestCase):
    def test_all_contracts_in_order_and_sequential_first_unchanged(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            repo.joinpath('TODO.md').write_text('''# Work
## Next
- [ ] A — first
  Scope: a.py
  Acceptance: works
  Checks: test a
  Touches: a.py
  Resources: network, port:8080
- [ ] BAD — incomplete
  Scope: missing checks
- [ ] B — second
  Scope: b.py
  Acceptance: works
  Checks: test b
''')
            self.assertTrue(hasattr(task_execution, 'select_all'), 'missing all-contract selector')
            tasks = task_execution.select_all(repo, None, None)
            self.assertEqual([t['id'] for t in tasks], ['A', 'B'])
            self.assertEqual(task_execution.select(repo, None, None), tasks[0])
            self.assertEqual(tasks[0]['fields']['Touches'], 'a.py')
            self.assertEqual(tasks[0]['fields']['Resources'], 'network, port:8080')


    def test_ledger_only_in_progress_is_not_dispatched_by_parallel_selector(self):
        import json
        from parallel_plan import plan
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            repo.joinpath('TODO.md').write_text('''# Work
## Now
- [ ] A — first
  Scope: a.py
  Acceptance: works
  Checks: test a
  Touches: a.py
''')
            repo.joinpath('goals.json').write_text(json.dumps({
                'version': 1,
                'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md',
                           'status': 'partial', 'tasks': ['A'], 'priority': 1, 'depends_on': []}],
                'tasks': [{'id': 'A', 'title': 'first', 'goal': 'G', 'status': 'in_progress',
                           'section': 'Now', 'depends_on': []}]}))
            sequential = task_execution.select(repo, None, None)
            self.assertNotIn('Status', sequential['fields'])
            result = plan(task_execution.select_all(repo))
            self.assertEqual(result['dispatch'], [])
            self.assertIn('in_progress', result['waiting'][0]['reason'])


def task(tid, touches, status='open', deps='None.', resources=''):
    return {'id': tid, 'fields': {'Touches': touches, 'Status': status,
                                'Dependencies': deps, 'Resources': resources}}


class PlanTests(unittest.TestCase):
    def test_independent_tasks_selected_without_mutating_inputs(self):
        spec = importlib.util.spec_from_file_location('parallel_plan', SCRIPTS / 'parallel_plan.py')
        self.assertTrue(Path(spec.origin).exists(), 'missing pure planner')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        tasks = [task('A', 'src/a.py'), task('B', 'src/b.py')]
        before = deepcopy(tasks)
        self.assertEqual(module.plan(tasks), {'dispatch': tasks, 'waiting': []})
        self.assertEqual(tasks, before)


    def test_conflicts_serialize_in_priority_order(self):
        from parallel_plan import plan
        cases = [
            (task('A', 'src/'), task('B', 'src/b.py'), 'path'),
            (task('A', 'src/test_[ab].txt'), task('B', 'src/test_b.txt'), 'paths'),
            (task('A', 'src/test_b.txt'), task('B', 'src/test_[ab].txt'), 'paths'),
            (task('A', 'a.py', resources='db:test network'),
             task('B', 'b.py', resources='db:test'), 'resource'),
            (task('A', 'a.py'), task('B', 'b.py', deps='A.'), 'dependency'),
            (task('A', 'a.py', deps='B.'), task('B', 'b.py'), 'dependency'),
        ]
        for a, b, reason in cases:
            with self.subTest(reason=reason, tasks=(a, b)):
                from parallel_plan import _solo
                result = plan([a, b, task('C', 'other/c.py')])
                # C shares nothing with A or the waiting B, so it does not wait behind B
                # (unless A must run alone).
                alone = bool(_solo(a))
                self.assertEqual([t['id'] for t in result['dispatch']], ['A'] if alone else ['A', 'C'])
                self.assertEqual([w['id'] for w in result['waiting']], ['B', 'C'] if alone else ['B'])
                self.assertIn(reason, result['waiting'][0]['reason'])

    def test_independent_work_backfills_past_a_waiting_task_but_never_takes_its_paths(self):
        """sierra: one task blocked by another session's claim held back 33 independent tasks."""
        from parallel_plan import plan
        claim = task('CL', 'shared/', status='in_progress')
        tasks = [task('T1', 'shared/x.py'), task('T2', 'shared/x.py'), task('T3', 'free.py'),
                 task('T4', 'other.py', resources='db'), task('T5', 'more.py', resources='db')]
        result = plan(tasks, all_tasks=[claim, *tasks])
        self.assertEqual([t['id'] for t in result['dispatch']], ['T3', 'T4'])
        self.assertEqual([w['id'] for w in result['waiting']], ['T1', 'T2', 'T5'])
        self.assertIn('in_progress CL', result['waiting'][0]['reason'])
        # Sharing a path only with the waiting T1 (not with the claim) still waits for T1.
        tasks = [task('T1', 'shared/x.py, lib/y.py'), task('T7', 'lib/y.py'), task('T3', 'free.py')]
        result = plan(tasks, all_tasks=[claim, *tasks])
        self.assertEqual([t['id'] for t in result['dispatch']], ['T3'])
        self.assertEqual(result['waiting'][1], {'id': 'T7', 'reason': 'overlapping paths with T1'})
        # A task that must run alone and waits on running work stops everything below it
        # so the pool drains; a waiting T1 does not keep it from running alone now.
        result = plan([task('S', ''), task('B', 'b.py')], [task('RUN', 'run.py')])
        self.assertEqual(result['dispatch'], [])
        tasks = [task('T1', 'shared/x.py'), task('S', 'package.json'), task('T3', 'free.py')]
        result = plan(tasks, all_tasks=[claim, *tasks])
        self.assertEqual([t['id'] for t in result['dispatch']], ['S'])
        self.assertEqual([w['id'] for w in result['waiting']], ['T1', 'T3'])
        # Once T1 runs, S waits on running work and stops lower dispatch until the pool drains.
        result = plan([task('S', 'package.json'), task('T3', 'free.py')], [tasks[0]])
        self.assertEqual(result['dispatch'], [])

    def test_transitive_dependencies_include_nonrunnable_contracts(self):
        from parallel_plan import plan
        a, b, c = task('A', 'a.py'), task('B', 'b.py', deps='X.'), task('X', 'x.py', deps='A.')
        result = plan([a, b], all_tasks=[a, b, c])
        self.assertEqual([t['id'] for t in result['dispatch']], ['A'])
        self.assertIn('dependency', result['waiting'][0]['reason'])

    def test_solo_task_drains_pool_and_blocks_lower_priorities(self):
        from parallel_plan import plan
        for solo in (task('A', ''), task('A', 'a.py', resources='live'),
                     task('A', 'a.py', resources='exclusive'), task('A', 'package.json'),
                     task('A', 'sub/uv.lock'), task('A', 'db/migrations/'),
                     task('A', 'schema/*.sql'), task('A', '.github/workflows/test.yml')):
            with self.subTest(solo=solo):
                tasks = [solo, task('B', 'b.py')]
                self.assertEqual([t['id'] for t in plan(tasks)['dispatch']], ['A'])
                result = plan(tasks, [task('RUN', 'run.py')])
                self.assertEqual(result['dispatch'], [])
                self.assertEqual([w['id'] for w in result['waiting']], ['A', 'B'])

    def test_running_in_progress_and_live_slot_tasks_never_redispatched(self):
        from parallel_plan import plan
        running = task('A', 'a.py', status='in_progress; prior work')
        result = plan([running, task('B', 'b.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])
        self.assertIn('in_progress', result['waiting'][0]['reason'])
        self.assertEqual(plan([task('A', 'a.py')], [task('A', 'a.py')])['dispatch'], [])
        self.assertEqual(plan([running, task('B', 'a.py')])['dispatch'], [])
        # An idle in_progress claim without Touches no longer blocks unrelated work
        # (it is not running); it still blocks dependents and declared overlap.
        running['fields']['Touches'] = ''
        result = plan([running, task('B', 'b.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])
        self.assertEqual(plan([running, task('C', '')])['dispatch'][0]['id'], 'C')  # solo task runs alone
        self.assertEqual(plan([running, task('D', 'd.py', deps='A')])['dispatch'], [])
        running['fields']['Touches'] = 'a.py'
        self.assertEqual(plan([running, task('E', 'a.py', status='open')])['dispatch'], [])
        # A live slot is still running work: missing Touches keeps everything else waiting.
        live = task('L', '')
        result = plan([task('B', 'b.py')], [live])
        self.assertEqual(result['dispatch'], [])
        self.assertIn('Touches', result['waiting'][0]['reason'])


class OverlapTests(unittest.TestCase):
    def test_actual_paths_stay_declared_and_do_not_overlap_other_work(self):
        import parallel_plan
        self.assertTrue(hasattr(parallel_plan, 'overlap'), 'missing integration overlap check')
        check = parallel_plan.overlap
        self.assertEqual(check(['src/a.py'], ['src/'], [['tests/']]),
                         {'outside': [], 'conflicts': []})
        self.assertEqual(check(['src/a.py', 'other.py'], ['src/*.py'], [['src/a.*']]),
                         {'outside': ['other.py'], 'conflicts': ['src/a.py']})
        self.assertEqual(check(['a.py'], [], []), {'outside': ['a.py'], 'conflicts': []})
        self.assertEqual(check(['a.py'], ['a.py'], [[]]),
                         {'outside': [], 'conflicts': ['a.py']})
        self.assertEqual(check(['src/pkg/a.py'], ['src/*/'], [['src/*/']]),
                         {'outside': [], 'conflicts': ['src/pkg/a.py']})

    def test_glob_intersection_is_symmetric_including_future_files(self):
        import parallel_plan
        self.assertTrue(hasattr(parallel_plan, 'overlap'), 'missing integration overlap check')
        for a, b, expected in [('src/a.py', 'src/b.py', False),
                               ('src/', 'src2/a.py', False),
                               ('src/test_[a-c].py', 'src/test_[c-e].py', True),
                               ('src/test_[a-b].py', 'src/test_[c-e].py', False),
                               ('src/[!a].py', 'src/a.py', False),
                               ('src/*.py', 'src/a.*', True),
                               ('src/[[]x.py', 'src/[[]*.py', True),
                               ('src/[α-ω].py', 'src/β.py', True),
                               ('src/[]', 'src/[]', True),
                               ('src/[!]', 'src/[!]', True),
                               ('src/a\nb', 'src/a?b', True)]:
            with self.subTest(a=a, b=b):
                for left, right in ((a, b), (b, a)):
                    self.assertEqual(parallel_plan._shared([left], [right]), expected)

    def test_invalid_path_declarations_refuse_instead_of_becoming_disjoint(self):
        from parallel_plan import plan
        for path in ('../src/a.py', '/src/a.py', './src/a.py', 'src//a.py', 'src/../a.py'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                plan([task('A', path)])


if __name__ == '__main__':
    unittest.main()
