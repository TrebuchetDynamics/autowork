"""Unit tests for goals.py (no network, no LLM)."""
import json
import re
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
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


class InitializationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'consumer'
        self.repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        (self.repo / 'SPEC.md').write_text('# Slice\n\nStatus: Accepted\n')
        self.intent = self.root / 'intent.json'
        self.data = {'version': 1, 'goals': [
            {'id': 'G1', 'title': 'Startup works', 'source': 'SPEC.md#slice',
             'status': 'unmet', 'tasks': ['T1']}], 'tasks': [
            {'id': 'T1', 'goal': 'G1', 'title': 'Verify startup',
             'status': 'open', 'section': 'Now'}]}
        self.intent.write_text(json.dumps(self.data))
        self.body = ('# TODO\n\n## Now\n\n- [ ] T1: Verify startup\n'
                     '  Goal: G1\n  Scope: startup check\n'
                     '  Acceptance: startup check passes\n  Dependencies: None\n'
                     '  Status: open\n  Ownership: fixture owner\n'
                     '  Sources: [Slice](SPEC.md#slice)\n\nContinuation retained.\n')
        self.input_todo = self.root / 'tasks.md'
        self.input_todo.write_text(self.body)

    def init(self, *args):
        return run('init', str(self.repo), '--intent', str(self.intent), *args)

    def snapshot(self):
        return {name: (self.repo / name).read_bytes() if (self.repo / name).exists() else None
                for name in ('goals.json', 'TODO.md', 'TODO.archive.md')}

    def test_empty_consumer_and_unchanged_repeat(self):
        result = self.init('--todo-file', str(self.input_todo))
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.repo / 'TODO.md').read_text(), self.body)
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        for cmd in ('fmt', 'render'):
            result = run(cmd, str(self.repo))
            self.assertEqual(result.returncode, 0, result.stderr)
        first = self.snapshot()
        # Once rendered, omit --todo-file: existing TODO remains authoritative.
        self.assertEqual(self.init().returncode, 0)
        self.assertEqual(self.snapshot(), first)
        result = run('backlog-check', str(self.repo), '--plan', 'SPEC.md#slice', '--tasks', 'T1')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['state'], 'ready_for_autowork')
        for cmd in ('fmt', 'render'):
            self.assertEqual(run(cmd, str(self.repo)).returncode, 0)
        self.assertEqual(self.snapshot(), first)

    def test_documented_initialization_commands_on_empty_and_todo_only_git_consumers(self):
        source_root = SCRIPT.resolve().parents[3]
        scaffold = source_root / 'skills/docs-sync/references/document-scaffold.md'
        section = scaffold.read_text().split('## First task-index initialization\n', 1)[1].split('\n## Conditional documents', 1)[0]
        blocks = re.findall(r'```(?:markdown|json|sh)\n(.*?)\n```', section, re.S)
        self.assertEqual(len(blocks), 4)
        (self.repo / 'SPEC.md').unlink()  # The documented plan lives in the supplied TODO.
        self.intent.write_text(blocks[1] + '\n')
        self.input_todo.write_text(blocks[2] + '\n')
        commands = blocks[3].replace('/absolute/toolset', str(source_root)).replace(
            '/absolute/consumer', str(self.repo)).replace('/absolute/intent.json', str(self.intent)).replace(
                '/absolute/tasks.md', str(self.input_todo)).splitlines()
        for todo_only in (False, True):
            with self.subTest(todo_only=todo_only):
                for name in ('goals.json', 'TODO.md'):
                    (self.repo / name).unlink(missing_ok=True)
                if todo_only:
                    (self.repo / 'TODO.md').write_bytes(self.input_todo.read_bytes())
                result = None
                for index, command in enumerate(commands):
                    argv = shlex.split(command)
                    argv[0] = sys.executable
                    if todo_only and index == 0:
                        argv = argv[:-2]  # TODO-only path omits --todo-file.
                    result = subprocess.run(argv, capture_output=True, text=True, timeout=10)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                assert result is not None
                self.assertEqual(json.loads(result.stdout)['state'], 'ready_for_autowork')
                first = self.snapshot()
                self.assertEqual(self.init().returncode, 0)
                self.assertEqual(self.snapshot(), first)

    def test_todo_only_preserves_bodies_history_and_metadata(self):
        (self.repo / 'TODO.md').write_text(self.body)
        (self.repo / 'TODO.archive.md').write_text('# Prior history\n')
        self.data['primary_milestone'] = 'G1'
        self.data['tasks'][0]['owner'] = {'name': 'fixture', 'lease': 'preserved'}
        self.intent.write_text(json.dumps(self.data))
        before = self.snapshot()
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.snapshot()['TODO.md'], before['TODO.md'])
        self.assertEqual(self.snapshot()['TODO.archive.md'], before['TODO.archive.md'])
        actual = json.loads((self.repo / 'goals.json').read_text())
        self.assertEqual(actual['primary_milestone'], 'G1')
        self.assertEqual(actual['tasks'][0]['owner'], self.data['tasks'][0]['owner'])
        first = self.snapshot()
        self.assertEqual(self.init().returncode, 0)
        self.assertEqual(self.snapshot(), first)

    def test_invalid_inputs_leave_content_unchanged(self):
        cases = [self.body.replace('  Acceptance: startup check passes\n', ''),
                 self.body.replace('Ownership:', 'Owner:'),
                 self.body.replace('Goal: G1', 'Goal: G2'),
                 self.body.replace('Status: open', 'Status: done'),
                 self.body + '\n- [ ] T1: Duplicate\n',
                 self.body + '\n- [ ] T2: Unindexed\n',
                 self.body + '\n<!-- goals:coverage:begin -->\n']
        for body in cases:
            with self.subTest(body=body):
                self.input_todo.write_text(body)
                before = self.snapshot()
                result = self.init('--todo-file', str(self.input_todo))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(self.snapshot(), before)
        self.input_todo.write_text(self.body)
        (self.repo / 'SPEC.md').write_text('# Slice\n\nStatus: Proposed\n')
        before = self.snapshot()
        result = self.init('--todo-file', str(self.input_todo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('Accepted', result.stderr)
        self.assertEqual(self.snapshot(), before)

    def test_missing_and_unsafe_inputs_fail_without_partial_writes(self):
        for args in ((), ('--todo-file', str(self.root / 'missing.md'))):
            before = self.snapshot()
            result = self.init(*args)
            self.assertNotEqual(result.returncode, 0)
            self.assertEqual(self.snapshot(), before)
        (self.repo / 'TODO.md').symlink_to(self.input_todo)
        result = self.init()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('symlink', result.stderr)
        self.assertFalse((self.repo / 'goals.json').exists())

    def test_existing_or_conflicting_state_is_not_overwritten(self):
        (self.repo / 'TODO.md').write_text(self.body)
        self.assertEqual(self.init().returncode, 0)
        self.data['tasks'][0]['title'] = 'Different intent'
        self.intent.write_text(json.dumps(self.data))
        before = self.snapshot()
        result = self.init()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('existing', result.stderr)
        self.assertEqual(self.snapshot(), before)
        (self.repo / 'goals.json').write_text('{"version": 2, "goals": [], "tasks": []}')
        before = self.snapshot()
        result = self.init()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)
        self.input_todo.write_text(self.body + '\nConflicting continuation.\n')
        result = self.init('--todo-file', str(self.input_todo))
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(self.snapshot(), before)

    def test_malformed_intent_and_nonlocal_sources_are_refused(self):
        original = json.dumps(self.data)
        cases = [original.replace('"version": 1', '"version": 2'),
                 original.replace('"version": 1', '"version": 1, "version": 1'),
                 original.replace('SPEC.md#slice', '../SPEC.md#slice'),
                 original.replace('SPEC.md#slice', 'https://example.invalid/spec#slice'),
                 original.replace('SPEC.md#slice', 'SPEC.md#absent'),
                 original.replace('"tasks": ["T1"]', '"tasks": ["MISSING"]'),
                 '{malformed', '[]']
        for raw in cases:
            with self.subTest(raw=raw):
                self.intent.write_text(raw)
                before = self.snapshot()
                result = self.init('--todo-file', str(self.input_todo))
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)
                self.assertEqual(self.snapshot(), before)

    def test_in_progress_and_completed_history_are_preserved(self):
        self.data['tasks'][0]['status'] = 'in_progress'
        self.data['tasks'][0]['lease'] = {'owner': 'fixture', 'token': 'keep'}
        self.data['goals'].append({'id': 'OLD', 'title': 'Previous outcome',
                                  'source': 'SPEC.md#slice', 'status': 'met', 'tasks': [],
                                  'evidence': [{'kind': 'executed', 'ref': 'prior fixture check', 'result': 'pass'}]})
        self.intent.write_text(json.dumps(self.data))
        (self.repo / 'TODO.md').write_text(self.body.replace('Status: open', 'Status: in_progress'))
        (self.repo / 'TODO.archive.md').write_text('# Existing history\n\nKeep all bytes.\n')
        before = self.snapshot()
        result = self.init()
        self.assertEqual(result.returncode, 0, result.stderr)
        actual = json.loads((self.repo / 'goals.json').read_text())
        self.assertEqual(actual['tasks'][0]['status'], 'in_progress')
        self.assertEqual(actual['tasks'][0]['lease'], self.data['tasks'][0]['lease'])
        self.assertEqual(next(g for g in actual['goals'] if g['id'] == 'OLD')['evidence'],
                         self.data['goals'][1]['evidence'])
        self.assertEqual(before['TODO.md'], self.snapshot()['TODO.md'])
        self.assertEqual(before['TODO.archive.md'], self.snapshot()['TODO.archive.md'])
        self.assertNotIn('primary_milestone', actual)

    def test_ledger_write_failure_rolls_back_only_new_todo(self):
        import goals
        args = type('Args', (), {'repo': str(self.repo), 'intent': str(self.intent),
                                'todo_file': str(self.input_todo)})()
        original = goals.atomic_write

        def fail_ledger(path, text, **kwargs):
            if path.name == 'goals.json':
                raise OSError('fixture replacement failure')
            return original(path, text, **kwargs)

        for existing_todo in (False, True):
            if existing_todo:
                (self.repo / 'TODO.md').write_text(self.body)
            before = self.snapshot()
            with goals.coordination(self.repo), patch.object(goals, 'atomic_write', fail_ledger):
                with self.assertRaises(SystemExit):
                    goals.initialize(args)
            self.assertEqual(self.snapshot(), before)

    def test_missing_todo_with_existing_ledger_is_not_success(self):
        (self.repo / 'goals.json').write_text(json.dumps(self.data))
        before = self.snapshot()
        result = self.init('--todo-file', str(self.input_todo))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('existing goals.json', result.stderr)
        self.assertEqual(self.snapshot(), before)


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

    def test_non_string_goal_sources_are_rejected_without_writing(self):
        path = self.repo / 'goals.json'
        todo = self.repo / 'TODO.md'
        todo.write_text('# TODO\n\nKeep this task body.\n')
        for source in ({'private-source': 'sensitive-value'}, ['sensitive-value'],
                       True, 731942, {}, [], False, 0, None):
            data = sample()
            data['goals'][0]['status'] = 'unverified'
            data['goals'][0]['source'] = source
            path.write_text(json.dumps(data))
            before = (path.read_bytes(), todo.read_bytes())
            for command in (('validate',), ('next', '--json'), ('fmt',), ('render',),
                            ('task', 'TASK-001', 'done'), ('focus', 'GOAL-4')):
                with self.subTest(source=source, command=command):
                    path.write_bytes(before[0])
                    todo.write_bytes(before[1])
                    result = run(command[0], str(self.repo), *command[1:])
                    diagnostic = result.stdout + result.stderr
                    self.assertNotEqual(result.returncode, 0, diagnostic)
                    self.assertIn('goals[0].source must be a string', diagnostic)
                    for private in ('private-source', 'sensitive-value', '731942', 'Traceback'):
                        self.assertNotIn(private, diagnostic)
                    self.assertEqual((path.read_bytes(), todo.read_bytes()), before)

    def test_source_shape_api_refuses_non_strings_before_normalization(self):
        import goals
        for source in ({'secret': 'value'}, ['value'], True, 731942, {}, [], False, 0, None):
            with self.subTest(source=source):
                data = sample()
                data['goals'][0]['status'] = 'unverified'
                data['goals'][0]['source'] = source
                before = json.dumps(data)
                diagnostic = ['goals[0].source must be a string']
                self.assertEqual(goals.shape_errors(data), diagnostic)
                self.assertEqual(goals.errors(data), diagnostic)
                with self.assertRaisesRegex(ValueError, r'goals\[0\]\.source must be a string'):
                    goals.normalize(data)
                self.assertEqual(json.dumps(data), before)

    def test_valid_source_strings_remain_unchanged(self):
        import goals
        for source in ('README.md#intent', 'docs/plan with spaces.md#accepted',
                       'https://example.invalid/spec#intent'):
            with self.subTest(source=source):
                data = sample()
                data['goals'][0]['status'] = 'unverified'
                data['goals'][0]['source'] = source
                normalized = goals.normalize(data)
                self.assertEqual(goals.errors(normalized), [])
                self.assertEqual(normalized['goals'][0]['source'], source)
                self.assertTrue(goals.eligible(normalized))

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

    def test_new_id_adds_a_two_hex_hash_after_the_next_number(self):
        run('fmt', str(self.repo))
        (self.repo / 'TODO.archive.md').write_text('- [x] TASK-041: archived history\n')
        ids = {run('new-id', str(self.repo)).stdout.strip() for _ in range(8)}
        for identifier in ids:
            self.assertRegex(identifier, r'^TASK-042-[0-9a-f]{2}$')
        self.assertGreater(len(ids), 1)
        self.assertRegex(run('new-id', str(self.repo), '--prefix', 'OPS').stdout.strip(), r'^OPS-001-[0-9a-f]{2}$')
        self.assertNotEqual(run('new-id', str(self.repo), '--prefix', 'bad-prefix').returncode, 0)

    def test_new_id_counts_hashed_ids_and_works_without_a_ledger(self):
        bare = self.repo / 'bare'; bare.mkdir()
        (bare / 'TODO.md').write_text('- [ ] APP-007-3f: hashed\n- [ ] APP-002: legacy\n')
        self.assertRegex(run('new-id', str(bare)).stdout.strip(), r'^APP-008-[0-9a-f]{2}$')

    def test_add_task_without_id_allocates_a_hashed_id(self):
        run('fmt', str(self.repo))
        result = run('add-task', str(self.repo), '--goal', 'GOAL-4', '--title', 'Allocated')
        self.assertRegex(result.stdout, r'^ok TASK-004-[0-9a-f]{2} -> GOAL-4 \(Next\)')
        self.assertEqual(run('validate', str(self.repo)).stdout.strip(), 'ok')
        mixed = run('add-task', str(self.repo), 'TASK-020', '--prefix', 'OPS', '--goal', 'GOAL-4', '--title', 'x')
        self.assertNotEqual(mixed.returncode, 0)

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



class HeadingLineEndingTests(unittest.TestCase):
    """CRLF and trailing-space headings parse like LF ones (TOOLSET-047)."""

    INTENT = {'version': 1, 'goals': [
        {'id': 'G1', 'title': 'Goal one', 'source': 'PLAN.md#goal-one', 'status': 'unmet',
         'tasks': ['T1', 'T2'], 'priority': 1}], 'tasks': [
        {'id': 'T1', 'goal': 'G1', 'title': 'First', 'status': 'open', 'section': 'Now'},
        {'id': 'T2', 'goal': 'G1', 'title': 'Second', 'status': 'open', 'section': 'Next',
         'depends_on': ['T1']}]}
    TODO = ('# TODO\n\n## Now\n\n- [ ] T1: First\n  Goal: G1\n  Scope: do it\n'
            '  Acceptance: it works\n  Dependencies: None\n  Sources: [Plan](PLAN.md#goal-one)\n'
            '  Ownership: unclaimed\n\n## Next\n\n- [ ] T2: Second\n  Goal: G1\n  Scope: do more\n'
            '  Acceptance: more works\n  Dependencies: T1\n  Sources: [Plan](PLAN.md#goal-one)\n'
            '  Ownership: unclaimed\n')

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)

    def outcome(self, name, todo):
        repo = self.root / name
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        (repo / 'PLAN.md').write_text('# Plan\n\n## Goal one\n\nStatus: Accepted\n\nBuild the thing.\n')
        intent = self.root / f'{name}-intent.json'
        intent.write_text(json.dumps(self.INTENT))
        source = self.root / f'{name}-todo.md'
        source.write_bytes(todo.encode('utf-8'))
        results = {}
        for label, args in (('init', ('init', str(repo), '--intent', str(intent), '--todo-file', str(source))),
                            ('validate', ('validate', str(repo))),
                            ('next', ('next', str(repo), '--json')),
                            ('backlog', ('backlog-check', str(repo), '--plan', 'PLAN.md#goal-one',
                                         '--tasks', 'T1')),
                            ('bootstrap', ('bootstrap-order', str(repo), '--dry-run'))):
            result = run(*args)
            stdout = result.stdout.replace(str(repo), 'REPO')
            if stdout.startswith(('{', '[')):
                stdout = json.loads(stdout)
                if isinstance(stdout, dict):  # Hashes of the differently-encoded bytes legitimately differ.
                    stdout.pop('sha256', None)
                    stdout.pop('revision', None)
            results[label] = (result.returncode, stdout, result.stderr)
        return repo, results

    def assert_like_lf(self, name, todo):
        _, expected = self.outcome('lf', self.TODO)
        self.assertEqual(expected['init'][0], 0, expected['init'])
        repo, actual = self.outcome(name, todo)
        for label in expected:
            with self.subTest(command=label):
                self.assertEqual(actual[label][:2], expected[label][:2], actual[label][2])
        self.assertEqual(actual['backlog'][1]['state'], 'ready_for_autowork')
        self.assertEqual([p['task']['id'] for p in actual['next'][1]], ['T1'])
        return repo

    def test_crlf_todo_initializes_selects_and_checks_like_lf(self):
        crlf = self.TODO.replace('\n', '\r\n')
        repo = self.assert_like_lf('crlf', crlf)
        self.assertEqual((repo / 'TODO.md').read_bytes(), crlf.encode('utf-8'))
        self.assertEqual(run('render', str(repo)).returncode, 0)
        rendered = (repo / 'TODO.md').read_bytes()
        self.assertTrue(rendered.startswith(crlf.encode('utf-8')), rendered[:200])

    def test_trailing_space_section_heading_matches_ledger_section(self):
        self.assert_like_lf('space', self.TODO.replace('## Now\n', '## Now \n').replace('## Next\n', '## Next\t\n'))

    def test_render_keeps_level_three_content_after_legacy_coverage(self):
        repo = self.root / 'legacy'
        repo.mkdir()
        (repo / 'goals.json').write_text(json.dumps(sample()))
        self.assertEqual(run('fmt', str(repo)).returncode, 0)
        tail = ('### Decisions log\n\n- 2026-10-01: keep the legacy layout.\n- 2026-10-02: ship it.\n\n'
                '## Now\n\n- [ ] TASK-001\n')
        (repo / 'TODO.md').write_text('# TODO\n\n## Goal coverage\n\nold table\n\n' + tail)
        result = run('render', str(repo))
        self.assertEqual(result.returncode, 0, result.stderr)
        text = (repo / 'TODO.md').read_text()
        self.assertTrue(text.endswith(tail), text)
        self.assertNotIn('old table', text)
        self.assertIn('| GOAL-4: Decrement floors at 0 | unmet | — | TASK-001 |', text)
        self.assertEqual(run('render', str(repo)).returncode, 0)
        self.assertEqual((repo / 'TODO.md').read_text(), text)


if __name__ == '__main__':
    unittest.main()
