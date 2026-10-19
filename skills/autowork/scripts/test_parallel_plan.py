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
                            self.assertIn('T-1', [t['id'] for t in result['dispatch']])
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

    def test_ledger_holds_name_the_task_and_disagreement(self):
        import json
        import parallel_status
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            repo.joinpath('TODO.md').write_text('''## Now
- [ ] B — dependent
  Scope: b.py
  Acceptance: works
  Checks: test b
  Dependencies: A.
  Status: open
''')
            ledger = {
                'version': 1,
                'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md',
                           'status': 'partial', 'tasks': ['A', 'B', 'SPARE'], 'priority': 1, 'depends_on': []}],
                'tasks': [{'id': 'A', 'title': 'prerequisite', 'goal': 'G', 'status': 'open',
                           'section': 'Next', 'depends_on': []},
                          {'id': 'B', 'title': 'dependent', 'goal': 'G', 'status': 'open',
                           'section': 'Now', 'depends_on': ['A']},
                          {'id': 'SPARE', 'title': 'remaining proof', 'goal': 'G', 'status': 'open',
                           'section': 'Needs decision', 'depends_on': []}]}
            for case, want in (
                    ('archived', 'ledger: A is open in goals.json but archived as done'),
                    ('outside', 'ledger: dependency A is open in goals.json in Needs decision (outside Now/Next)'),
                    ('missing', 'ledger: B is missing from goals.json'),
                    ('status', 'ledger: B is done in goals.json but open in TODO.md; files disagree'),
                    ('section', 'ledger: B is in Next in goals.json but Now in TODO.md; files disagree'),
                    ('goal', 'ledger: goal dependency H is partial in goals.json')):
                with self.subTest(case=case):
                    data = deepcopy(ledger)
                    archive = repo / 'TODO.archive.md'
                    archive.write_text('## Done\n- [x] A — prerequisite\n  Status: done\n')
                    if case == 'outside':
                        archive.unlink()
                        data['tasks'][0]['section'] = 'Needs decision'
                    elif case == 'missing':
                        data['tasks'].pop(1)
                        data['goals'][0]['tasks'] = ['A', 'SPARE']
                    elif case in ('status', 'section', 'goal'):
                        data['tasks'][0]['status'] = 'done'
                        if case == 'status':
                            data['tasks'][1]['status'] = 'done'
                        elif case == 'section':
                            data['tasks'][1]['section'] = 'Next'
                        else:
                            data['goals'][0]['depends_on'] = ['H']
                            data['goals'].append(dict(id='H', title='prerequisite goal', source='TODO.md',
                                status='partial', tasks=['H1'], priority=2, depends_on=[]))
                            data['tasks'].append(dict(id='H1', title='proof', goal='H', status='open',
                                section='Needs decision', depends_on=[]))
                    repo.joinpath('goals.json').write_text(json.dumps(data))
                    with self.assertRaises(task_execution.NoEligibleTask) as caught:
                        task_execution.select(repo, 'B', None)
                    self.assertEqual(str(caught.exception), 'B: ' + want)
                    self.assertEqual(parallel_status.pending_tasks(repo)[0]['reason'], 'not runnable: ' + want)
            # An ordinary unmet dependency is not a docs-repair or planning trigger.
            repo.joinpath('goals.json').write_text(json.dumps(ledger))
            repo.joinpath('TODO.archive.md').write_text('')
            todo = repo / 'TODO.md'
            todo.write_text(todo.read_text() + '  Kind: plan\n')
            self.assertEqual(parallel_status.pending_tasks(repo)[0]['reason'], 'dependency: A')
            repo.joinpath('goals.json').unlink()
            for tail in ('### Evidence — latest acceptance\n  Status: open\n',
                         '### Acceptance — remaining criteria\n  - [ ] device proof\n'):
                with self.subTest(ambiguous_archive=tail):
                    repo.joinpath('TODO.archive.md').write_text(
                        '## Done\n- [x] A — prerequisite\n  Status: done\n' + tail)
                    with self.assertRaises(task_execution.NoEligibleTask):
                        task_execution.select(repo, 'B', None)

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
        result = plan([task('X', 'x.py', resources='exclusive'), task('B', 'b.py')], [task('RUN', 'run.py')])
        self.assertEqual(result['dispatch'], [])  # still drains the pool for it
        # TOOLSET-161-17: missing Touches is no hint, not a reason to run alone.
        result = plan([task('X', ''), task('B', 'b.py')], [task('RUN', 'run.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B', 'X'])  # ranked after hinted work

    def test_nothing_waits_to_run_alone_beside_a_finished_worker(self):
        """One runner idled 54 minutes: an exclusive task waited out another task's review."""
        from parallel_plan import plan
        done = task('DONE', 'd.py')  # its commit awaits review; no worker runs
        result = plan([task('X', 'x.py', resources='exclusive'), task('B', 'b.py')], [done], finished={'DONE'})
        self.assertEqual([t['id'] for t in result['dispatch']], ['X'])  # X then runs alone
        result = plan([task('B', 'b.py')], [task('X', 'x.py', resources='exclusive')], finished={'X'})
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])
        result = plan([task('X', 'x.py', resources='exclusive')], [done])
        self.assertEqual(result['dispatch'], [])  # a running worker still makes it wait

    def test_resources_are_the_names_a_line_starts_with_not_its_explanation(self):
        """Every word counted: a line saying it was changed from exclusive ran alone for 5 hours."""
        from parallel_plan import _resources
        cases = {'exclusive': {'exclusive'}, 'live, device-lab': {'live', 'device-lab'},
                 'exclusive — serialize the shared fixture': {'exclusive'},
                 'install-transaction — changed from exclusive; need not run alone.': {'install-transaction'},
                 'exclusive managed installation publication; preserve coordinators.': {'exclusive'},
                 'Documentation review only; the external live checks are separate': set()}
        for line, expected in cases.items():
            with self.subTest(line=line):
                self.assertEqual(_resources({'fields': {'Resources': line}}), expected)

    def test_conflicts_serialize_in_priority_order(self):
        from parallel_plan import plan
        cases = [  # overlapping Touches no longer serialize (TOOLSET-161-17); these still do
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

    def test_overlapping_touches_never_hold_a_task_and_independent_work_ranks_first(self):
        """TOOLSET-161-17: Touches schedule work but never hold it; integration settles overlap."""
        from parallel_plan import plan
        claim = task('CL', 'shared/', status='in_progress')
        tasks = [task('T1', 'shared/x.py'), task('T2', 'shared/x.py'), task('T3', 'free.py'),
                 task('T4', 'other.py', resources='db'), task('T5', 'more.py', resources='db')]
        result = plan(tasks, all_tasks=[claim, *tasks])
        # T2 shares T1's file: it still runs, after the independent work; T5 shares a resource.
        self.assertEqual([t['id'] for t in result['dispatch']], ['T1', 'T3', 'T4', 'T2'])
        self.assertEqual([w['id'] for w in result['waiting']], ['T5'])
        self.assertIn('shared resource', result['waiting'][0]['reason'])
        result = plan([task('B', 'run.py'), task('C', 'c.py')], [task('RUN', 'run.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['C', 'B'])  # B overlaps running work: last
        # A serial S is not exclusive (TOOLSET-160-df): independent T3 runs beside it.
        tasks = [task('T1', 'shared/x.py'), task('S', 'package.json'), task('T3', 'free.py')]
        result = plan(tasks, all_tasks=[claim, *tasks], protected_files=[])  # shared/ holds no manifest
        self.assertEqual([t['id'] for t in result['dispatch']], ['T1', 'S', 'T3'])
        self.assertEqual(result['waiting'], [])
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
        for solo in (live, task('A', 'a.py', resources='exclusive')):
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
        self.assertEqual([t['id'] for t in early['dispatch']], ['B', 'C'])  # other work backfills
        reasons = {w['id']: w['reason'] for w in early['waiting']}
        self.assertIn('must run alone', reasons['X'])
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
        # An idle claim's declared files do not hold others either (TOOLSET-161-17).
        self.assertEqual([t['id'] for t in plan([running, task('B', 'a.py')])['dispatch']], ['B'])
        # An idle in_progress claim without Touches no longer blocks unrelated work
        # (it is not running); it still blocks dependents and declared overlap.
        running['fields']['Touches'] = ''
        result = plan([running, task('B', 'b.py')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])
        self.assertEqual(plan([running, task('C', '')])['dispatch'][0]['id'], 'C')  # solo task runs alone
        self.assertEqual(plan([running, task('D', 'd.py', deps='A')])['dispatch'], [])
        running['fields']['Touches'] = 'a.py'
        self.assertEqual([t['id'] for t in plan([running, task('E', 'a.py', status='open')])['dispatch']], ['E'])
        # A live slot without Touches holds nothing either: it is no hint (TOOLSET-161-17).
        result = plan([task('B', 'b.py')], [task('L', '')])
        self.assertEqual([t['id'] for t in result['dispatch']], ['B'])


class TouchesParsingTests(unittest.TestCase):
    def setUp(self):
        import parallel_plan
        self.paths = parallel_plan.paths

    def test_a_note_heading_or_blank_line_after_touches_is_not_part_of_it(self):
        """TOOLSET-213-45: a parenthesised note ran into Touches and spoiled its last path, so the
        worker's own file was held as outside Touches."""
        value = ('a/x.py, tests/test_y.py\n- Touches widened by the owner session (2026-10-18): tests/test_y.py, '
                 'which the worker adjusted while merging main into its branch.')
        self.assertEqual(self.paths(value), ['a/x.py', 'tests/test_y.py'])
        self.assertEqual(self.paths('docs/quality/\n\n### **P4** — Extended experiences'), ['docs/quality/'])
        self.assertEqual(self.paths('docs/\n### Next section'), ['docs/'])

    def test_prose_in_touches_is_a_contract_error(self):
        with self.assertRaisesRegex(ValueError, r'not a list of paths\): which the worker adjusted'):
            self.paths('a/x.py, which the worker adjusted while merging')
        self.assertEqual(self.paths('docs/My File.md'), ['docs/My File.md'])  # a path with a space is fine


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

    def test_literal_short_cuts_agree_with_the_full_intersection_search(self):
        """TOOLSET-221-8e: literal sides skip the product search; the answer must not change."""
        import random
        import parallel_plan
        parts = ['a', 'b', 'ab', 'src', 'x.py', 'test_a.py']
        globs = ['*', '*.py', 'a*', '?', 'test_[a-b].py', '[!a]']
        rng = random.Random(221)

        def path(glob):
            items = [rng.choice(parts) for _ in range(rng.randint(1, 3))]
            if glob:
                items[rng.randrange(len(items))] = rng.choice(globs)
            return '/'.join(items) + ('/' if rng.random() < 0.3 else '')

        for _ in range(3000):
            left, right = path(rng.random() < 0.3), path(rng.random() < 0.3)
            full = lambda p: p + '*' if p.endswith('/') else p
            with self.subTest(left=left, right=right):
                self.assertEqual(parallel_plan._intersects(left, right),
                                 parallel_plan._search(full(left), full(right)))

    def test_a_deep_queue_plans_in_seconds(self):
        """TOOLSET-221-8e: 58 runnable tasks took minutes to plan, almost all in path overlap."""
        import time
        import parallel_plan
        shapes = ['src/mod{i}/file{j}.py', 'docs/area{i}/', 'tests/test_{i}_{j}.py', 'pkg{i}/*.go',
                  'web/{i}/[a-c]{j}.ts', 'services/{i}/package.json']

        def task(n):
            touches = ', '.join(shapes[(n + j) % len(shapes)].format(i=n % 17, j=j) for j in range(10))
            return {'id': f'T-{n}', 'fields': {'Touches': touches, 'Dependencies': f'T-{n - 3}.' if n % 5 == 0 and n > 3 else 'None.',
                                               'Status': 'open'}}

        everything = [task(n) for n in range(158)]
        running, queue = everything[:8], everything[8:]
        started = time.monotonic()
        result = parallel_plan.plan(queue, running, all_tasks=everything, protected_files=['services/1/package.json'])
        self.assertLess(time.monotonic() - started, 10)  # under 2 s on an idle host; 10 tolerates a busy one
        self.assertEqual(len(result['dispatch']) + len(result['waiting']), len(queue))

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
