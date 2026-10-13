"""Unit tests for goals.py (no network, no LLM)."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).with_name('goals.py')


def run(*args):
    return subprocess.run([sys.executable, str(SCRIPT), *args], capture_output=True, text=True)


def sample():
    return {
        'version': 1,
        'goals': [
            {'id': 'GOAL-1', 'title': 'Starts at 0', 'source': 'README.md#intent', 'status': 'met',
             'evidence': [{'kind': 'inspection', 'ref': 'test/counter_test.dart', 'result': 'pass'}],
             'tasks': ['TASK-002'], 'priority': 1},
            {'id': 'GOAL-4', 'title': 'Decrement floors at 0', 'source': 'README.md#intent', 'status': 'unmet',
             'tasks': ['TASK-001'], 'priority': 4},
            {'id': 'GOAL-5', 'title': 'Undo', 'source': 'PRD.md#req-5', 'status': 'unmet',
             'tasks': ['TASK-003'], 'depends_on': ['GOAL-4'], 'priority': 5},
        ],
        'tasks': [
            {'id': 'TASK-001', 'goal': 'GOAL-4', 'title': 'Implement decrement', 'status': 'open', 'section': 'Now'},
            {'id': 'TASK-002', 'goal': 'GOAL-1', 'title': 'Run counter test', 'status': 'open', 'section': 'Now'},
            {'id': 'TASK-003', 'goal': 'GOAL-5', 'title': 'Implement undo', 'status': 'open', 'section': 'Next'},
        ],
    }


class GoalsTests(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.TemporaryDirectory()
        self.repo = Path(self.dir.name)
        (self.repo / 'goals.json').write_text(json.dumps(sample()))

    def tearDown(self):
        self.dir.cleanup()

    def data(self):
        return json.loads((self.repo / 'goals.json').read_text())

    def test_met_without_executed_evidence_is_invalid_then_downgraded(self):
        r = run('validate', str(self.repo))
        self.assertEqual(r.returncode, 1)
        self.assertIn('GOAL-1: met without executed+pass evidence', r.stdout)
        run('fmt', str(self.repo))
        self.assertEqual(self.data()['goals'][0]['status'], 'unverified')
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')

    def test_fmt_is_byte_stable(self):
        run('fmt', str(self.repo)); first = (self.repo / 'goals.json').read_bytes()
        run('fmt', str(self.repo)); self.assertEqual(first, (self.repo / 'goals.json').read_bytes())

    def test_commands_reject_unsupported_version_without_writing(self):
        path = self.repo / 'goals.json'
        todo = self.repo / 'TODO.md'
        todo.write_text('# TODO\n\nKeep this task body.\n')
        for version in (2, True, '1', None):
            data = sample()
            data['version'] = version
            path.write_text(json.dumps(data))
            before = (path.read_bytes(), todo.read_bytes())
            for command in (('fmt',), ('render',), ('next', '--json'), ('validate',),
                            ('task', 'TASK-001', 'done'), ('focus', 'GOAL-4')):
                with self.subTest(version=version, command=command):
                    path.write_bytes(before[0])
                    todo.write_bytes(before[1])
                    result = run(command[0], str(self.repo), *command[1:])
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('version must be 1', result.stdout + result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual((path.read_bytes(), todo.read_bytes()), before)

    def test_fmt_preserves_extension_metadata(self):
        data = sample()
        data['maintenance'] = {'owner': 'fixture', 'revision': 'preserve-me'}
        data['goals'][0]['custom'] = {'note': 'goal metadata'}
        data['tasks'][0]['custom'] = ['task metadata']
        path = self.repo / 'goals.json'
        path.write_text(json.dumps(data))
        for command in (('fmt',), ('task', 'TASK-001', 'in_progress')):
            result = run(command[0], str(self.repo), *command[1:])
            self.assertEqual(result.returncode, 0, result.stderr)
            actual = self.data()
            self.assertEqual(actual['maintenance'], data['maintenance'])
            self.assertEqual(actual['goals'][0]['custom'], data['goals'][0]['custom'])
            task = next(t for t in actual['tasks'] if t['id'] == 'TASK-001')
            self.assertEqual(task['custom'], data['tasks'][0]['custom'])

    def test_malformed_fields_are_rejected_before_normalization(self):
        cases = [
            ('tasks', 'depends_on', 'TASK-002'),
            ('goals', 'depends_on', 'GOAL-4'),
            ('goals', 'tasks', 'TASK-002'),
            ('tasks', 'depends_on', [{}]),
            ('goals', 'evidence', 'pass'),
            ('goals', 'evidence', [None]),
            ('goals', 'evidence', [{'kind': [], 'ref': 'check', 'result': 'pass'}]),
            ('goals', 'priority', 'first'),
            ('goals', 'id', []),
        ]
        path = self.repo / 'goals.json'
        for collection, field, value in cases:
            data = sample()
            data[collection][0][field] = value
            path.write_text(json.dumps(data))
            before = path.read_bytes()
            for command in ('fmt', 'validate', 'next'):
                with self.subTest(collection=collection, field=field, value=value, command=command):
                    path.write_bytes(before)
                    result = run(command, str(self.repo))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn(field, result.stdout + result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(path.read_bytes(), before)

    def test_malformed_containers_have_actionable_diagnostics(self):
        path = self.repo / 'goals.json'
        for data, diagnostic in (([], 'must be an object'),
                                 ({'version': 1, 'goals': {}, 'tasks': []}, 'goals must be a list'),
                                 ({'version': 1, 'goals': [None], 'tasks': []}, 'goals[0] must be an object')):
            path.write_text(json.dumps(data))
            before = path.read_bytes()
            result = run('fmt', str(self.repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn(diagnostic, result.stderr)
            self.assertNotIn('Traceback', result.stderr)
            self.assertEqual(path.read_bytes(), before)

    def test_ambiguous_json_keys_are_never_silently_discarded(self):
        path = self.repo / 'goals.json'
        original = json.dumps(sample())
        cases = [original.replace('"version": 1', '"version": 2, "version": 1'),
                 original.replace('"status": "open"', '"status": "done", "status": "open"', 1),
                 original.replace('"result": "pass"', '"result": "fail", "result": "pass"'),
                 original.replace('"version": 1', '"private-key": "first", "private-key": "last", "version": 1')]
        for raw in cases:
            for command in ('fmt', 'validate', 'next', 'render'):
                with self.subTest(command=command, raw=raw):
                    path.write_text(raw)
                    result = run(command, str(self.repo))
                    self.assertNotEqual(result.returncode, 0)
                    self.assertIn('duplicate JSON key', result.stdout + result.stderr)
                    self.assertNotIn('private-key', result.stdout + result.stderr)
                    self.assertNotIn('Traceback', result.stderr)
                    self.assertEqual(path.read_text(), raw)

    def test_met_goal_with_open_work_is_invalid_and_fmt_reopens_it(self):
        data = sample()
        evidence = [{'kind': 'executed', 'result': 'pass', 'ref': 'prior check'}]
        data['goals'][0]['evidence'] = evidence
        path = self.repo / 'goals.json'
        path.write_text(json.dumps(data))
        self.assertIn('GOAL-1: met goal has unfinished tasks', run('validate', str(self.repo)).stdout)
        before = path.read_bytes()
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertEqual(picks[0]['task']['id'], 'TASK-002')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(run('fmt', str(self.repo)).returncode, 0)
        self.assertEqual(self.data()['goals'][0]['status'], 'partial')
        self.assertEqual(self.data()['goals'][0]['evidence'], evidence)
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')

    def test_cross_level_dependency_cycle_is_diagnosed(self):
        data = sample()
        data['goals'][0]['status'] = 'unverified'
        # GOAL-4 needs TASK-001, which needs TASK-003, which waits for GOAL-4.
        data['tasks'][0]['depends_on'] = ['TASK-003']
        path = self.repo / 'goals.json'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        for command in ('validate', 'next'):
            result = run(command, str(self.repo))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('cross-level dependency cycle', result.stdout + result.stderr)
            self.assertIn('TASK-001', result.stdout + result.stderr)
        self.assertEqual(path.read_bytes(), before)
        # A forward dependency between goals remains valid and runnable.
        data['tasks'][0].pop('depends_on')
        data['tasks'][2]['depends_on'] = ['TASK-001']
        path.write_text(json.dumps(data))
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')

    def test_cross_level_graph_separates_goal_and_task_ids(self):
        data = sample()
        data['goals'][0]['status'] = 'unverified'
        data['goals'][0]['id'] = 'TASK-002'
        data['tasks'][1]['goal'] = 'TASK-002'
        (self.repo / 'goals.json').write_text(json.dumps(data))
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertEqual(picks[0]['task']['id'], 'TASK-002')

    def test_completed_dependency_does_not_create_cross_level_deadlock(self):
        data = sample()
        data['goals'][0]['status'] = 'unverified'
        data['goals'][2]['status'] = 'met'
        data['goals'][2]['evidence'] = [{'kind': 'executed', 'result': 'pass', 'ref': 'historical check'}]
        data['tasks'][2]['status'] = 'done'
        data['tasks'][0]['depends_on'] = ['TASK-003']
        (self.repo / 'goals.json').write_text(json.dumps(data))
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertIn('TASK-001', [row['task']['id'] for row in picks])

    def test_next_orders_by_priority_then_status_and_respects_dependencies(self):
        run('fmt', str(self.repo))
        self.assertTrue(run('next', str(self.repo)).stdout.startswith('TASK-002'))  # GOAL-1 priority 1 first
        d = self.data(); d['goals'][0]['priority'] = 9   # demote the unverified goal below GOAL-4 (priority 4)
        (self.repo / 'goals.json').write_text(json.dumps(d))
        self.assertTrue(run('next', str(self.repo)).stdout.startswith('TASK-001'))  # priority beats status
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertNotIn('TASK-003', [p['task']['id'] for p in picks])  # GOAL-5 waits for GOAL-4

    def test_next_rejects_invalid_task_state_and_conflicting_ids(self):
        path = self.repo / 'goals.json'
        for defect, diagnostic in (('status', 'status must be one of'),
                                   ('duplicate', 'duplicate id'),
                                   ('membership', 'task membership does not match ledger')):
            data = sample()
            if defect == 'status':
                data['tasks'][0]['status'] = 'blocked'
            elif defect == 'duplicate':
                data['tasks'].append(dict(data['tasks'][0], status='done'))
            else:
                data['goals'][1]['tasks'] = []
            path.write_text(json.dumps(data))
            before = path.read_bytes()
            with self.subTest(defect=defect):
                result = run('next', str(self.repo), '--json')
                self.assertNotEqual(result.returncode, 0)
                self.assertIn(diagnostic, result.stdout + result.stderr)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(path.read_bytes(), before)

    def test_next_keeps_pending_evidence_gated_without_blocking_independent_work(self):
        data = sample()
        data['tasks'][0]['status'] = 'done'
        path = self.repo / 'goals.json'
        path.write_text(json.dumps(data))
        before = path.read_bytes()
        result = run('next', str(self.repo), '--json')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual([row['task']['id'] for row in json.loads(result.stdout)], ['TASK-002'])
        self.assertIn('GOAL-4: unmet goal has no open task', run('validate', str(self.repo)).stdout)
        self.assertEqual(path.read_bytes(), before)

    def test_executed_pass_promotes_only_when_tasks_done(self):
        run('fmt', str(self.repo))
        self.assertIn('GOAL-1 → unverified', run('evidence', str(self.repo), 'GOAL-1', '--kind', 'executed',
                                                  '--ref', 'flutter test', '--result', 'pass').stdout)
        run('task', str(self.repo), 'TASK-002', 'done')
        self.assertIn('GOAL-1 → met', run('evidence', str(self.repo), 'GOAL-1', '--kind', 'executed',
                                           '--ref', 'flutter test', '--result', 'pass').stdout)
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        self.assertIn('GOAL-1 → partial', run('evidence', str(self.repo), 'GOAL-1', '--kind', 'executed',
                                               '--ref', 'flutter test', '--result', 'fail').stdout)

    def test_render_replaces_only_the_marked_block(self):
        run('fmt', str(self.repo))
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Goal coverage\n\nold table\n\n## Now\n\n- [ ] TASK-001\n')
        run('render', str(self.repo)); first = (self.repo / 'TODO.md').read_text()
        self.assertIn('| GOAL-4: Decrement floors at 0 | unmet | — | TASK-001 |', first)
        self.assertIn('## Now\n\n- [ ] TASK-001', first)
        self.assertNotIn('old table', first)
        run('render', str(self.repo)); self.assertEqual(first, (self.repo / 'TODO.md').read_text())

    def test_non_met_goal_without_open_task_is_invalid(self):
        d = sample(); d['tasks'][0]['status'] = 'done'
        (self.repo / 'goals.json').write_text(json.dumps(d))
        self.assertIn('GOAL-4: unmet goal has no open task', run('validate', str(self.repo)).stdout)


    def test_add_task_registers_and_validates(self):
        run('fmt', str(self.repo))
        self.assertIn('ok TASK-009 -> GOAL-4 (Now)', run('add-task', str(self.repo), 'TASK-009', '--goal', 'GOAL-4',
                                                         '--title', 'Follow-up', '--section', 'Now', '--depends-on', 'TASK-001').stdout)
        self.assertIn('TASK-009', next(g for g in self.data()['goals'] if g['id'] == 'GOAL-4')['tasks'])
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        self.assertNotEqual(run('add-task', str(self.repo), 'TASK-009', '--goal', 'GOAL-4', '--title', 'dup').returncode, 0)
        self.assertNotEqual(run('add-task', str(self.repo), 'TASK-010', '--goal', 'NOPE', '--title', 'x').returncode, 0)

    def test_add_task_rejects_ids_that_todo_cannot_parse(self):
        run('fmt', str(self.repo))
        path = self.repo / 'goals.json'
        before = path.read_bytes()
        for identifier in ('TASK 1', 'TASK.1', '_TASK', 'TASK:1', ''):
            with self.subTest(identifier=identifier):
                result = run('add-task', str(self.repo), identifier, '--goal', 'GOAL-4', '--title', 'Work')
                self.assertNotEqual(result.returncode, 0, result.stdout)
                self.assertIn('invalid task ID', result.stderr)
                self.assertEqual(path.read_bytes(), before)

    def test_validate_detects_missing_or_wrong_goal_task_membership(self):
        run('fmt', str(self.repo))
        original = self.data()
        for members in ([], ['TASK-001']):
            with self.subTest(members=members):
                data = json.loads(json.dumps(original))
                data['goals'][0]['tasks'] = members
                path = self.repo / 'goals.json'
                path.write_text(json.dumps(data))
                before = path.read_bytes()
                result = run('validate', str(self.repo))
                self.assertEqual(result.returncode, 1, result.stdout)
                self.assertIn('GOAL-1: task membership does not match ledger', result.stdout)
                self.assertEqual(path.read_bytes(), before)


    def test_section_moves_task_out_of_selection(self):
        run('fmt', str(self.repo))
        self.assertIn('ok TASK-002 -> Needs decision', run('section', str(self.repo), 'TASK-002', 'Needs decision').stdout)
        picks = [p['task']['id'] for p in json.loads(run('next', str(self.repo), '--json').stdout)]
        self.assertNotIn('TASK-002', picks)

    def test_dependency_cycles_are_reported_without_mutation(self):
        run('fmt', str(self.repo))
        original = self.data()
        for kind, key, ids in (('task', 'tasks', ['TASK-001', 'TASK-002']),
                               ('goal', 'goals', ['GOAL-1', 'GOAL-4'])):
            for members in (ids[:1], ids):
                with self.subTest(kind=kind, members=members):
                    data = json.loads(json.dumps(original))
                    rows = {row['id']: row for row in data[key]}
                    for i, identifier in enumerate(members):
                        rows[identifier]['depends_on'] = [members[(i + 1) % len(members)]]
                    path = self.repo / 'goals.json'
                    path.write_text(json.dumps(data))
                    before = path.read_bytes()
                    result = run('validate', str(self.repo))
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(kind + ' dependency cycle:', result.stdout)
                    for identifier in members:
                        self.assertIn(identifier, result.stdout)
                    self.assertEqual(path.read_bytes(), before)
                    result = run('next', str(self.repo), '--json')
                    self.assertEqual(result.returncode, 1, result.stdout + result.stderr)
                    self.assertIn(kind + ' dependency cycle:', result.stderr)
                    self.assertEqual(path.read_bytes(), before)

    def finish_goal(self):
        self.assertEqual(run('fmt', str(self.repo)).returncode, 0)
        self.assertEqual(run('task', str(self.repo), 'TASK-002', 'done').returncode, 0)
        result = run('evidence', str(self.repo), 'GOAL-1', '--kind', 'executed',
                     '--ref', 'fixture test', '--result', 'pass')
        self.assertEqual(result.returncode, 0, result.stderr)
        return next(g for g in self.data()['goals'] if g['id'] == 'GOAL-1')['evidence']

    def test_reopened_task_returns_to_queue_and_reopens_completed_goal(self):
        evidence = self.finish_goal()
        result = run('task', str(self.repo), 'TASK-002', 'open')
        self.assertEqual(result.returncode, 0, result.stderr)
        task = next(t for t in self.data()['tasks'] if t['id'] == 'TASK-002')
        goal = next(g for g in self.data()['goals'] if g['id'] == 'GOAL-1')
        self.assertEqual(task['section'], 'Next')
        self.assertEqual(goal['status'], 'partial')
        self.assertEqual(goal['evidence'], evidence)
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertIn('TASK-002', [p['task']['id'] for p in picks])

    def test_new_followup_reopens_completed_goal_without_erasing_evidence(self):
        evidence = self.finish_goal()
        result = run('add-task', str(self.repo), 'TASK-009', '--goal', 'GOAL-1',
                     '--title', 'Follow-up', '--section', 'Now')
        self.assertEqual(result.returncode, 0, result.stderr)
        goal = next(g for g in self.data()['goals'] if g['id'] == 'GOAL-1')
        self.assertEqual(goal['status'], 'partial')
        self.assertEqual(goal['evidence'], evidence)
        picks = json.loads(run('next', str(self.repo), '--json').stdout)
        self.assertIn('TASK-009', [p['task']['id'] for p in picks])


if __name__ == '__main__':
    unittest.main()
