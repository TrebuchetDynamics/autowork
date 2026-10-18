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


    def test_owner_or_live_work_waits_for_recorded_authorization(self):
        import json
        from types import SimpleNamespace
        import parallel_dispatch as dispatch
        import parallel_status
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            common = repo / 'execution'
            common.mkdir()
            for fields in ('Ownership: Owner', 'Ownership: owner only.',
                           'Ownership: Owner or a coordinator with live authorization.',
                           'Resources: live', 'Resources: network, live'):
                for authorization in ('', 'Live authorization:   ',
                                      'Live authorization: owner approved this run on 2026-10-17'):
                    with self.subTest(fields=fields, authorization=authorization):
                        repo.joinpath('TODO.md').write_text(f'''# Work
## Now
- [ ] T-1 — Live migration
  Scope: installed profiles
  Acceptance: migration verified
  Checks: verify migration
  {fields}
  {authorization}
- [ ] T-2 — Offline repair
  Scope: b.py
  Acceptance: works
  Checks: test b
  Touches: b.py
  Ownership: Toolset coordinator.
''')
                        tasks = dispatch.contracts(repo)
                        result = dispatch.admit(tasks, [], set(), [], everything=tasks,
                                                parked=[], adopted=set(), protected=[])
                        common.joinpath('journal.jsonl').write_text(json.dumps(dict(
                            event='dispatch_observed', timestamp=1, waiting=result['waiting'])) + '\n')
                        status = parallel_status._snapshot(repo, common, 2)
                        if 'owner approved' in authorization:
                            self.assertEqual([t['id'] for t in result['dispatch']], ['T-1'])
                            self.assertFalse(any(r['kind'] == 'outside' for r in status['roots']))
                        else:
                            self.assertEqual([t['id'] for t in result['dispatch']], ['T-2'])
                            self.assertEqual([(r['id'], r['kind']) for r in status['roots']],
                                             [('Live authorization: T-1', 'outside')])
                            fallback = dispatch.fallback(repo, SimpleNamespace(tasks='T-1', plan=None), 'no host')
                            self.assertEqual(fallback['outcome'], 'WAITING')
                            self.assertNotIn('task', fallback)

    def test_duplicate_authorization_fields_never_authorize_dispatch(self):
        import parallel_dispatch as dispatch
        from parallel_plan import plan
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            for fields in ('Ownership: Owner\n  Ownership: Toolset coordinator.',
                           'Resources: live\n  Resources: network',
                           'Ownership: Owner\n  Live authorization: approved\n  Live authorization: another approval'):
                with self.subTest(fields=fields):
                    repo.joinpath('TODO.md').write_text(f'''## Now
- [ ] T-1 — migration
  Scope: profiles
  Acceptance: verified
  Checks: verify
  {fields}
''')
                    tasks = dispatch.contracts(repo)
                    self.assertEqual(plan(tasks)['dispatch'], [])
                    self.assertIn('duplicate', plan(tasks)['waiting'][0]['reason'])

    def test_authorization_status_tracks_current_contract_without_dispatch(self):
        import json
        import subprocess
        import parallel_status as status
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            common = status.state.common_dir(repo)
            (common / 'slots').mkdir(parents=True)
            todo = '''## Now
- [ ] T-1 — migration
  Scope: profiles
  Acceptance: verified
  Checks: verify
  Ownership: Owner or a coordinator with live authorization.
'''
            slot_path = common / 'slots' / 'T-1.json'
            for phase in ('fresh', 'interrupted', 'released', 'held'):
                with self.subTest(phase=phase):
                    if phase != 'fresh':
                        slot_path.write_text(json.dumps(dict(task_id='T-1', state=phase, attempt=1,
                                                            started_at=1, worktree=str(repo / 'worker'))))
                    repo.joinpath('TODO.md').write_text(todo)
                    snapshot = status.snapshot(repo, now=2)
                    self.assertEqual(snapshot['tasks'][0]['state'], 'waiting')
                    self.assertEqual([(r['id'], r['kind']) for r in snapshot['roots']],
                                     [('Live authorization: T-1', 'outside')])
                    common.joinpath('journal.jsonl').write_text(json.dumps(dict(
                        event='dispatch_observed', timestamp=1, waiting=status.pending_tasks(repo))) + '\n')
                    repo.joinpath('TODO.md').write_text(todo + '  Live authorization: owner approved this run\n')
                    self.assertFalse(any(r['kind'] == 'outside' for r in status.snapshot(repo, now=3)['roots']))

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


    def test_directory_scopes_use_actual_protected_files(self):
        from parallel_plan import plan
        tasks = [task('A', 'test/shaders/'), task('B', 'lib/models/'), task('C', 'docs/research/')]
        self.assertEqual(plan(tasks, protected_files=[])['dispatch'], tasks)
        # TOOLSET-160-df: a serial directory runs beside independent work, never beside
        # other serial work.
        result = plan(tasks + [task('D', 'go.sum')], protected_files=['lib/models/go.mod'])
        self.assertEqual([t['id'] for t in result['dispatch']], ['A', 'B', 'C'])
        self.assertEqual(result['waiting'][0]['reason'], 'serial path shared with B')
        for scope in ('src/package.json', 'db/migrations/', 'scripts/research/schemas/',
                      '.github/workflows/', 'src/go.mod'):
            with self.subTest(scope=scope):
                candidates = [task('A', scope), task('B', 'independent.py'), task('C', 'yarn.lock')]
                result = plan(candidates, protected_files=[])
                self.assertEqual(result['dispatch'], candidates[:2])
                self.assertEqual(result['waiting'][0]['reason'], 'serial path shared with A')

    def test_glob_directory_containing_manifest_is_serial(self):
        from parallel_plan import plan
        for scope, manifest in [('packages/*/', 'packages/api/package.json'),
                                ('components/[ab]/', 'components/a/go.mod')]:
            with self.subTest(scope=scope):
                tasks = [task('A', scope), task('B', 'independent.py'), task('C', 'Cargo.lock')]
                result = plan(tasks, protected_files=[manifest])
                self.assertEqual(result['dispatch'], tasks[:2])
                self.assertEqual([w['id'] for w in result['waiting']], ['C'])

    def test_only_exclusive_tasks_run_alone_and_stop_lower_dispatch(self):
        """TOOLSET-160-df: one manifest task idled every worker in three runners."""
        from parallel_plan import plan
        result = plan([task('S', 'package.json'), task('B', 'b.py'), task('C', 'c.py')], [task('RUN', 'run.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['S', 'B', 'C'])
        result = plan([task('S', 'package.json'), task('B', 'b.py')], [task('RUN', 'yarn.lock')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])  # a serial S waits, but stops nothing
        self.assertEqual(result['waiting'][0]['reason'], 'serial path shared with RUN')
        for alone in (task('X', ''), task('X', 'x.py', resources='exclusive')):
            with self.subTest(alone=alone['fields']):
                result = plan([alone, task('B', 'b.py')], [task('RUN', 'run.py')])
                self.assertEqual(result['dispatch'], [])  # still drains the pool for it

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
                alone = False  # TOOLSET-160-df: none of these is exclusive; a serial one runs beside C
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
        self.assertEqual(result['waiting'][1], {'id': 'T7', 'reason': 'overlapping paths with T1', 'blocked_by': ['T1']})
        # A task that must run alone and waits on running work stops everything below it
        # so the pool drains; a waiting T1 does not keep it from running alone now.
        result = plan([task('S', ''), task('B', 'b.py')], [task('RUN', 'run.py')])
        self.assertEqual(result['dispatch'], [])
        # A serial S is not exclusive (TOOLSET-160-df): independent T3 runs beside it.
        tasks = [task('T1', 'shared/x.py'), task('S', 'package.json'), task('T3', 'free.py')]
        result = plan(tasks, all_tasks=[claim, *tasks], protected_files=[])  # shared/ holds no manifest
        self.assertEqual([t['id'] for t in result['dispatch']], ['S', 'T3'])
        self.assertEqual([w['id'] for w in result['waiting']], ['T1'])
        result = plan([task('S', 'package.json'), task('T3', 'free.py')], [tasks[0]])
        self.assertEqual([t['id'] for t in result['dispatch']], ['S', 'T3'])

    def test_transitive_dependencies_include_nonrunnable_contracts(self):
        from parallel_plan import plan
        a, b, c = task('A', 'a.py'), task('B', 'b.py', deps='X.'), task('X', 'x.py', deps='A.')
        result = plan([a, b], all_tasks=[a, b, c])
        self.assertEqual([t['id'] for t in result['dispatch']], ['A'])
        self.assertIn('dependency', result['waiting'][0]['reason'])

    def test_solo_task_drains_pool_and_blocks_lower_priorities(self):
        from parallel_plan import plan
        live = task('A', 'a.py', resources='live')
        live['fields']['Live authorization'] = 'owner approved this run on 2026-10-17'
        for solo in (task('A', ''), live, task('A', 'a.py', resources='exclusive')):
            with self.subTest(solo=solo):
                tasks = [solo, task('B', 'b.py')]
                self.assertEqual([t['id'] for t in plan(tasks)['dispatch']], ['A'])
                result = plan(tasks, [task('RUN', 'run.py')])
                self.assertEqual(result['dispatch'], [])
                self.assertEqual([w['id'] for w in result['waiting']], ['A', 'B'])
        # Serial files are not exclusive (TOOLSET-160-df): they run beside independent work.
        for serial in (task('A', 'package.json'), task('A', 'sub/uv.lock'), task('A', 'db/migrations/'),
                       task('A', 'schema/*.sql'), task('A', '.github/workflows/test.yml')):
            with self.subTest(serial=serial):
                tasks = [serial, task('B', 'b.py')]
                self.assertEqual([t['id'] for t in plan(tasks)['dispatch']], ['A', 'B'])
                self.assertEqual([t['id'] for t in plan(tasks, [task('RUN', 'run.py')])['dispatch']], ['A', 'B'])

    def test_an_exclusive_task_drains_the_pool_only_after_its_grace_period(self):
        """TOOLSET-171-35: 28 independent tasks idled behind one exclusive task."""
        from parallel_plan import plan
        exclusive = task('X', 'x.py', resources='exclusive')
        tasks = [exclusive, task('B', 'b.py'), task('C', 'x.py')]
        running = [task('RUN', 'run.py')]
        early = plan(tasks, running, drain_after=1800, waited={'X': 60})
        self.assertEqual([t['id'] for t in early['dispatch']], ['B'])  # independent work backfills
        reasons = {w['id']: w['reason'] for w in early['waiting']}
        self.assertIn('must run alone', reasons['X'])
        self.assertEqual(reasons['C'], 'overlapping paths with X')  # it still reserves its files
        late = plan(tasks, running, drain_after=1800, waited={'X': 1900})
        self.assertEqual(late['dispatch'], [])
        self.assertEqual({w['id']: w['reason'] for w in late['waiting']}['B'],
                         'priority waits for X (draining, waited 31m)')
        self.assertEqual(plan(tasks, running)['dispatch'], [])  # no drain_after: drains at once, as before

    def test_an_exhausted_hold_blocks_only_its_dependents(self):
        from parallel_plan import plan
        held = task('H', '')  # failed twice, no Touches: would otherwise force everything to wait
        tasks = [task('S', 'package.json'), task('B', 'b.py'), task('D', 'd.py', deps='H.'),
                 task('O', 'h.py')]
        result = plan(tasks, parked=[held])
        self.assertEqual([t['id'] for t in result['dispatch']], ['S', 'B', 'O'])
        result = plan(tasks[1:], parked=[held])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B', 'O'])
        self.assertEqual(result['waiting'], [{'id': 'D', 'reason': 'dependency: held H', 'blocked_by': ['H']}])
        # Its declared paths hold nothing: it reruns fresh from later code, never merges as is.
        self.assertEqual([t['id'] for t in plan([task('O', 'h.py')], parked=[task('H', 'h.py')])['dispatch']], ['O'])
        prerequisite = plan([task('P', 'p.py')], parked=[task('H', 'h.py', deps='P.')])
        self.assertEqual([t['id'] for t in prerequisite['dispatch']], ['P'])  # what H needs still runs

    def test_dependencies_name_task_ids_not_the_prose_around_them(self):
        from parallel_plan import dependency_ids
        known = {'T-1', 'TASK-019', 'X9'}
        for value, expected in (
                ('None.', set()), ('none for this shared-client slice. Existing authority', set()),
                ('None required; ask first.', set()), ('—', set()),
                ('TASK-004; not eligible until that task is done.', {'TASK-004'}),
                ('BACKEND-SSH-CONNECT. Section: Next. Ownership: unclaimed.', {'BACKEND-SSH-CONNECT'}),
                ('TASK-033, TASK-032; goal gates: G1.', {'TASK-033', 'TASK-032'}),
                ('TASK-018. TASK-019 (goal prerequisite).', {'TASK-018', 'TASK-019'}),
                ('`T-1` and X9', {'T-1', 'X9'}),
                ('approved device access', {'approved device access'}), ('H', {'H'})):
            with self.subTest(value=value):
                self.assertEqual(dependency_ids(value, known), expected)

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

    def test_path_declarations_tolerate_only_a_final_sentence_period(self):
        from parallel_plan import paths
        for value, expected in (
                ('x/, docs/notes/.', ['x/', 'docs/notes/']),
                ('a.py.', ['a.py']), ('a/.b/', ['a/.b/']),
                ('a.py., b.py', ['a.py.', 'b.py']),
                ('a..', ['a..']), ('a/...', ['a/...']),
                ('src/, migrations/<new compatible provenance migration path>', ['src/', 'migrations/']),
                ('docs/<name>.md', ['docs/<name>.md'])):  # only a whole last segment is a placeholder
            with self.subTest(value=value):
                self.assertEqual(paths(value), expected)
        for path in ('../a', '/abs', './src/a.py', 'src//a.py', 'a/./b', 'a/../b',
                     'a/..', '..', '.', 'a/., b.py', 'a/../.', '/abs.',
                     'a\\b', 'a\x00b'):
            with self.subTest(path=path), self.assertRaises(ValueError):
                paths(path)


if __name__ == '__main__':
    unittest.main()
