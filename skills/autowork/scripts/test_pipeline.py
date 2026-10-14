import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests/fixtures"))
"""Composed picker/dispatch/worker/reconcile fixture, not a native worker run."""
import contextlib
import hashlib
import io
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import start_goal
import source_freshness
import reconcile
import check_receipt
import pass_workspace

ROOT = Path(__file__).resolve().parents[2]


class PipelineTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory(prefix='pipeline-')
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        ledger = {'version': 1, 'goals': [{'id': 'G', 'title': 'Fixture output',
                  'source': 'README.md', 'status': 'unmet', 'tasks': ['T'], 'priority': 1}],
                  'tasks': [{'id': 'T', 'goal': 'G', 'title': 'Create artifact',
                             'status': 'open', 'section': 'Now'}]}
        (self.repo / 'goals.json').write_text(json.dumps(ledger))
        for args in (('init',), ('add', 'goals.json'),
                     ('-c', 'user.name=Pipeline fixture', '-c', 'user.email=fixture@local',
                      'commit', '-m', 'Committed fixture base')):
            subprocess.run(['git', '-C', str(self.repo), *args], check=True,
                           capture_output=True, text=True, timeout=30)
        self.base = subprocess.run(['git', '-C', str(self.repo), 'rev-parse', 'HEAD'],
                                   check=True, capture_output=True, text=True, timeout=30).stdout.strip()
        result = subprocess.run([sys.executable, str(ROOT / 'docs-sync/scripts/goals.py'),
                                 'next', str(self.repo), '--json'], check=True,
                                capture_output=True, text=True, timeout=30)
        self.selected = json.loads(result.stdout)[0]['task']
        self.assertEqual(self.selected['id'], 'T')
        self.contract = self.root / 'contract.txt'
        self.contract.write_text(''.join(f'{key}: fixture {key}\n' for key in start_goal.CONTRACT_FIELDS))
        self.snapshot = self.root / 'snapshot.json'
        self.snapshot.write_text(json.dumps(source_freshness.capture(self.repo, ['goals.json'])))
        self.db = self.root / 'board.db'
        with sqlite3.connect(self.db) as db:
            db.execute('CREATE TABLE tasks (id TEXT, goal_mode INTEGER, goal_max_turns INTEGER)')
        self.tasks, self.runs, self.created = [], [], 0
        self.expected_budget = 100
        self.created_body = ''

    def cli(self, prefix, *args):
        if args == ('config', 'get', 'terminal.cwd'):
            return str(self.repo)
        if args == ('profile', 'show', 'fixture'):
            return f'Path: {self.home}'
        if args == ('kanban', 'boards', 'list', '--json'):
            return json.dumps([{'slug': 'default', 'db_path': str(self.db)}])
        self.assertEqual(args[:3], ('kanban', '--board', 'default'))
        if args[3] == 'list':
            return json.dumps(self.tasks)
        if args[3] == 'create':
            self.created += 1
            self.assertEqual(args[args.index('--max-retries') + 1], '1')
            budget = int(args[args.index('--goal-max-turns') + 1])
            self.assertEqual(budget, self.expected_budget)
            self.created_body = args[args.index('--body') + 1]
            digest = hashlib.sha256(('fixture\n' + str(self.repo) + '\n' + self.selected['title'] +
                                     '\n' + self.contract.read_text().strip()).encode()).hexdigest()
            self.assertEqual(args[args.index('--idempotency-key') + 1], 'autowork:' + digest)
            self.assertEqual(args[args.index('--completion-contract') + 1], 'local-only')
            workspace = args[args.index('--workspace') + 1]
            self.assertTrue(workspace.startswith('dir:'))
            self.worker_repo = Path(workspace.removeprefix('dir:'))
            self.assertNotEqual(self.worker_repo, self.repo)
            self.assertTrue(self.worker_repo.is_relative_to(self.root / 'passes'))
            self.assertEqual(subprocess.run(['git', '-C', str(self.worker_repo), 'rev-parse', 'HEAD'],
                                           check=True, capture_output=True, text=True,
                                           timeout=30).stdout.strip(), self.base)
            task = {'id': 't_fixture', 'title': self.selected['title'], 'assignee': 'fixture',
                    'workspace_kind': 'dir', 'workspace_path': str(self.worker_repo),
                    'completion_contract': 'local-only', 'status': 'ready', 'max_retries': getattr(self, 'readback_retries', 1)}
            self.tasks.append(task)
            with sqlite3.connect(self.db) as db:
                db.execute('INSERT INTO tasks VALUES (?, ?, ?)', ('t_fixture', 1, budget))
            return json.dumps(task)
        if args[3] == 'show':
            self.assertEqual(args[4], 't_fixture')
            return json.dumps({'task': self.tasks[0], 'runs': self.runs})
        raise AssertionError(args)

    def dispatch(self, *extra, include_base=True):
        argv = ['start_goal.py', '--profile', 'fixture', '--workspace', str(self.repo),
                '--title', self.selected['title'], '--contract-file', str(self.contract),
                '--source-snapshot', str(self.snapshot), '--pass-root', str(self.root / 'passes'),
                *(['--base', self.base] if include_base else []), *extra]
        with patch.object(start_goal, 'run', side_effect=self.cli), \
                patch.object(sys, 'argv', argv), patch.dict(os.environ, {}, clear=True), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            start_goal.main()
        return json.loads(output.getvalue())

    def test_native_retry_readback_mismatch_preserves_created_card(self):
        self.readback_retries = 3
        with self.assertRaisesRegex(ValueError, 'retry limit differs'):
            self.dispatch()
        self.assertEqual(self.created, 1)
        self.assertEqual(self.tasks[0]['id'], 't_fixture')
        self.assertEqual(self.tasks[0]['max_retries'], 3)

    def test_failure_after_native_create_never_reports_no_create(self):
        self.readback_retries = 3
        with contextlib.redirect_stdout(io.StringIO()) as output, \
                self.assertRaisesRegex(ValueError, 'retry limit differs'):
            self.dispatch('--admission-attempt', 'a' * 32,
                          '--admission-request-sha256', 'b' * 64)
        self.assertEqual(self.created, 1)
        self.assertNotIn('refused_before_create', output.getvalue())

    def test_pre_create_transport_timeout_is_unknown(self):
        with patch.object(start_goal, 'run', side_effect=subprocess.TimeoutExpired('hermes', 30)), \
                patch.object(sys, 'argv', ['start_goal.py', '--profile', 'fixture',
                    '--workspace', str(self.repo), '--title', 'fixture', '--contract-file', str(self.contract),
                    '--admission-attempt', 'a' * 32, '--admission-request-sha256', 'b' * 64]), \
                contextlib.redirect_stdout(io.StringIO()) as output, \
                self.assertRaises(subprocess.TimeoutExpired):
            start_goal.main()
        self.assertEqual(output.getvalue(), '')
        self.assertEqual(self.created, 0)

    def test_selected_task_executes_and_fixture_review_acknowledges_exact_candidate(self):
        first = self.dispatch()
        self.assertEqual(first['outcome'], 'handed_off')
        self.assertEqual(first['max_retries'], 1)
        self.assertFalse(first['budget_policy']['automatic_failure_retries'])
        self.assertEqual(first['budget_policy']['cumulative_enforcement'], 'not_available')
        self.assertEqual(first['goal_max_turns'], 100)
        self.assertIn('100-turn budget', self.created_body)
        self.assertEqual(self.dispatch()['outcome'], 'already_owned')
        self.assertEqual(self.created, 1)
        self.assertEqual(first['workspace'], self.tasks[0]['workspace_path'])
        self.assertEqual(first['source_workspace'], str(self.repo))
        self.assertTrue(pass_workspace.verify(first['pass_manifest'], self.worker_repo))
        artifact = self.worker_repo / 'artifact.txt'
        # Explicit fixture worker: a real bounded subprocess, no LLM or native scheduler.
        subprocess.run([sys.executable, '-c',
                        'from pathlib import Path; Path("artifact.txt").write_text("portable\\n")'],
                       cwd=self.worker_repo, check=True, timeout=30)
        command = [sys.executable, '-c',
                   'from pathlib import Path; assert Path("artifact.txt").read_text() == "portable\\n"']
        (self.worker_repo / 'dependencies.lock').write_text('fixture uses Python stdlib only\n')
        (self.worker_repo / 'environment.json').write_text(json.dumps({'backend': 'fixture', 'python': sys.version}))
        checked = check_receipt.execute(self.worker_repo, ['artifact.txt', 'dependencies.lock', 'environment.json'], command, 30)
        self.assertTrue(check_receipt.reusable(checked, self.worker_repo, command))
        with self.assertRaisesRegex(ValueError, 'different workspace'):
            check_receipt.reusable(checked, self.repo, command)
        for name in ('artifact.txt', 'dependencies.lock', 'environment.json'):
            self.assertFalse((self.repo / name).exists())
        self.assertEqual(subprocess.run(['git', '-C', str(self.repo), 'status', '--porcelain'],
                                       check=True, capture_output=True, text=True,
                                       timeout=30).stdout, '')
        receipt = {'task': self.selected['id'], 'candidate_sha256': hashlib.sha256(artifact.read_bytes()).hexdigest(),
                   'check': checked, 'boundary': 'fixture review only'}
        # The fake review sink acknowledges precisely this candidate and receipt.
        self.tasks[0]['status'] = 'review'
        self.runs.append({'id': 1, 'task_id': 't_fixture', 'profile': 'fixture',
                          'outcome': 'review', 'metadata': {'review_ack': receipt}})
        with patch.object(reconcile, 'run', side_effect=self.cli):
            observed = reconcile.reconcile(['hermes', '-p', 'fixture'], self.home, 'fixture')
        self.assertTrue(observed['worker_observed'])
        self.assertEqual(observed['status'], 'review')
        self.assertEqual(observed['metadata']['review_ack'], receipt)
        self.assertEqual(self.dispatch()['outcome'], 'already_owned')
        self.assertEqual(self.created, 1)

    def test_default_100_budget_matches_body_native_readback_and_journal(self):
        self.expected_budget = 100
        contract = self.contract.read_bytes()
        result = self.dispatch()
        self.assertEqual(result['goal_max_turns'], 100)
        self.assertEqual(result['max_retries'], 1)
        self.assertFalse(result['budget_policy']['automatic_failure_retries'])
        self.assertIn('100-turn budget', self.created_body)
        self.assertIn('Goal budget rationale:', self.created_body)
        self.assertEqual(self.contract.read_bytes(), contract)
        self.assertEqual(json.loads((self.home / 'autowork/goal-handoff.json').read_text()), result)

    def test_owner_cycle_inherits_default_and_preserves_explicit_50(self):
        import legacy_owner_cycle as owner_cycle
        from types import SimpleNamespace
        request = self.root / 'handoff.json'
        options = {'profile': 'fixture', 'title': self.selected['title'],
                   'contract-file': str(self.contract), 'source-snapshot': str(self.snapshot)}
        args = SimpleNamespace(consumer=str(self.repo), handoff_request=str(request))
        run = subprocess.run
        for budget in (None, 50):
            with self.subTest(budget=budget):
                if budget is not None:
                    options['goal-max-turns'] = budget
                request.write_text(json.dumps({'consumer': str(self.repo), 'task_id': 'T', 'options': options}))
                with patch.object(owner_cycle.subprocess, 'run',
                                  side_effect=lambda argv, **kwargs: run(argv + ['--validate-only'], **kwargs)) as cli:
                    result = owner_cycle.handoff(args, self.selected)
                self.assertEqual(result['exit_code'], 0, result)
                self.assertEqual(result['result']['goal_max_turns'], 100 if budget is None else budget)
                cli.assert_called_once()
                if budget is None:
                    self.assertNotIn('--goal-max-turns', result['argv'])
        self.assertFalse((self.home / 'autowork').exists())

    def test_explicit_100_budget_matches_body_native_readback_and_journal(self):
        self.expected_budget = 100
        self.contract.write_text(self.contract.read_text() +
                                 'Goal budget rationale: one coherent implementation and recovery outcome\n')
        result = self.dispatch('--goal-max-turns', '100')
        self.assertEqual(result['goal_max_turns'], 100)
        self.assertIn('100-turn budget', self.created_body)
        self.assertNotIn('50-turn budget', self.created_body)
        self.assertEqual(json.loads((self.home / 'autowork/goal-handoff.json').read_text()), result)

    def test_source_drift_refuses_new_dispatch(self):
        (self.repo / 'goals.json').write_text('{}')
        with self.assertRaisesRegex(SystemExit, 'Source changed'):
            self.dispatch()
        self.assertEqual(self.created, 0)
        self.assertEqual(self.tasks, [])

    def test_base_free_new_dispatch_refuses_without_native_card_or_pass(self):
        with self.assertRaisesRegex(SystemExit, 'New write passes require --base'):
            self.dispatch(include_base=False)
        self.assertEqual(self.created, 0)
        self.assertEqual(self.tasks, [])
        self.assertFalse((self.root / 'passes').exists())
        self.assertFalse((self.home / 'autowork/goal-handoff.json').exists())

    def test_worker_start_source_drift_refuses_writes_preserving_original_card(self):
        original = self.dispatch()
        receipt = (self.home / 'autowork/goal-handoff.json').read_bytes()
        self.runs.append({'id': 1, 'profile': 'fixture',
                          'metadata': {'worker_session_id': 'fixture_session'}})
        (self.repo / 'goals.json').write_text('{}')
        with self.assertRaisesRegex(ValueError, 'Source changed before worker start'):
            pass_workspace.run_checked(original['pass_manifest'], self.worker_repo,
                                       [sys.executable, '-c',
                                        'from pathlib import Path; Path("artifact.txt").write_text("forbidden")'])
        self.assertFalse((self.worker_repo / 'artifact.txt').exists())
        self.assertFalse((self.repo / 'artifact.txt').exists())
        self.assertEqual(self.dispatch()['outcome'], 'already_owned')
        self.assertEqual(self.created, 1)
        self.assertEqual(self.tasks[0]['workspace_path'], original['workspace'])
        self.assertEqual(self.runs[0]['metadata']['worker_session_id'], 'fixture_session')
        self.assertEqual((self.home / 'autowork/goal-handoff.json').read_bytes(), receipt)

    def test_100_requires_rationale_before_cli_or_journal_mutation(self):
        for suffix in ('', 'Goal budget rationale:   \n'):
            with self.subTest(suffix=suffix):
                self.contract.write_text(''.join(f'{key}: fixture {key}\n' for key in start_goal.CONTRACT_FIELDS) + suffix)
                with patch.object(self, 'cli', side_effect=AssertionError('CLI reached before budget rationale validation')) as cli:
                    with self.assertRaisesRegex(SystemExit, 'Goal budget rationale'):
                        self.dispatch('--goal-max-turns', '100')
                    cli.assert_not_called()
                self.assertFalse((self.home / 'autowork').exists())

    def test_default_100_refuses_supplied_empty_rationale_before_cli(self):
        self.contract.write_text(self.contract.read_text() + 'Goal budget rationale:   \n')
        with patch.object(self, 'cli') as cli:
            with self.assertRaisesRegex(SystemExit, 'Goal budget rationale'):
                self.dispatch()
            cli.assert_not_called()
        self.assertFalse((self.home / 'autowork').exists())

    def test_invalid_budget_rejects_before_any_cli_or_journal_mutation(self):
        for budget in ('0', '20', '51', '101', '-1', '100.0', 'many'):
            with self.subTest(budget=budget), patch.object(self, 'cli') as cli, contextlib.redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit) as error:
                    self.dispatch('--goal-max-turns', budget)
                self.assertEqual(error.exception.code, 2)
                cli.assert_not_called()
                self.assertFalse((self.home / 'autowork').exists())

    def test_duplicate_budget_selection_preserves_original_card_session_and_receipt(self):
        self.contract.write_text(self.contract.read_text() + 'Goal budget rationale: coherent larger outcome\n')
        self.expected_budget = 50
        original = self.dispatch('--goal-max-turns', '50')
        receipt = (self.home / 'autowork/goal-handoff.json').read_bytes()
        self.tasks[0]['status'] = 'running'
        self.runs.append({'id': 1, 'profile': 'fixture', 'metadata': {'worker_session_id': 'fixture_session'}})
        result = self.dispatch()
        self.assertEqual(result['task_id'], original['task_id'])
        self.assertEqual(result['goal_max_turns'], 50)
        self.assertEqual(self.created, 1)
        self.assertEqual(self.runs[0]['metadata']['worker_session_id'], 'fixture_session')
        self.assertEqual((self.home / 'autowork/goal-handoff.json').read_bytes(), receipt)

    def test_default_100_preserves_exhausted_original_card_and_cumulative_history(self):
        self.expected_budget = 50
        original = self.dispatch('--goal-max-turns', '50')
        self.tasks[0].update(status='triage', goal_turns_used=50)
        self.runs.append({'id': 1, 'profile': 'fixture', 'outcome': 'max_turns',
                          'metadata': {'worker_session_id': 'fixture_session', 'goal_turns_used': 50}})
        history = json.dumps({'tasks': self.tasks, 'runs': self.runs}, sort_keys=True)
        receipt = (self.home / 'autowork/goal-handoff.json').read_bytes()
        result = self.dispatch()
        self.assertEqual(result['outcome'], 'already_owned')
        self.assertEqual(result['task_id'], original['task_id'])
        self.assertEqual(result['goal_max_turns'], 50)
        self.assertEqual(self.created, 1)
        self.assertEqual(json.dumps({'tasks': self.tasks, 'runs': self.runs}, sort_keys=True), history)
        self.assertEqual((self.home / 'autowork/goal-handoff.json').read_bytes(), receipt)

    def test_validate_only_reports_selected_budget_without_cli_or_writes(self):
        self.contract.write_text(self.contract.read_text() + 'Goal budget rationale: coherent larger outcome\n')
        for budget in ('50', '100'):
            with self.subTest(budget=budget), patch.object(self, 'cli') as cli:
                result = self.dispatch('--goal-max-turns', budget, '--validate-only')
                self.assertEqual(result['goal_max_turns'], int(budget))
                cli.assert_not_called()
                self.assertFalse((self.home / 'autowork').exists())

    def test_timeout_preserves_original_card_for_reconciliation(self):
        self.dispatch()
        self.runs.append({'id': 1, 'profile': 'fixture', 'metadata': {'worker_session_id': 'fixture_session'}})
        original = (self.home / 'autowork/goal-handoff.json').read_bytes()
        with patch.object(reconcile, 'run', side_effect=subprocess.TimeoutExpired(['hermes'], 30)):
            with self.assertRaises(subprocess.TimeoutExpired):
                reconcile.reconcile(['hermes'], self.home, 'fixture')
        self.assertEqual((self.home / 'autowork/goal-handoff.json').read_bytes(), original)
        self.assertEqual(self.dispatch()['outcome'], 'already_owned')
        self.assertEqual(self.created, 1)
        with patch.object(reconcile, 'run', side_effect=self.cli):
            observed = reconcile.reconcile(['hermes'], self.home, 'fixture')
        self.assertEqual(observed['metadata']['worker_session_id'], 'fixture_session')
        self.assertEqual(observed['task_id'], 't_fixture')
        self.assertEqual(observed['run_id'], 1)


if __name__ == '__main__':
    unittest.main()
