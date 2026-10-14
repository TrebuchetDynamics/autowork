"""Offline registered-create CLI composition, without native writes."""
import contextlib,io,json,unittest
from pathlib import Path
from unittest.mock import patch
import start_goal as m

class RegisteredCreateTests(unittest.TestCase):
    def test_native_launcher_binds_selected_profile_and_board(self):
        import tempfile
        from types import SimpleNamespace
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'request.json'
            path.write_text(json.dumps(dict(profile_home='/selected/profile', db_path='/selected/board.db')))
            with patch.dict(m.os.environ, {'HERMES_HOME':'/foreign', 'HERMES_KANBAN_DB':'/foreign.db',
                    'HERMES_KANBAN_TASK':'worker-must-still-refuse'}), \
                    patch.object(m.subprocess, 'run', return_value=SimpleNamespace(returncode=0, stdout='{"id":"t_fixture"}')) as run:
                m.create_registered('/selected/python', path)
            env = run.call_args.kwargs['env']
            self.assertEqual(env['HERMES_HOME'], '/selected/profile')
            self.assertEqual(env['HERMES_KANBAN_DB'], '/selected/board.db')
            self.assertEqual(env['HERMES_KANBAN_BOARD'], 'default')
            self.assertEqual(env['HERMES_KANBAN_HOME'], '/selected')
            self.assertEqual(env['HERMES_KANBAN_TASK'], 'worker-must-still-refuse')

    def test_registered_creation_uses_native_transaction_request(self):
        import subprocess, re, shlex, hashlib
        from test_owner_cycle import ComposedReadyTests
        fixture = ComposedReadyTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.ready_backlog()
        repo, root = fixture.repo, fixture.root
        registry = repo / 'writers.jsonl'
        registry.write_text('')
        subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(repo), 'commit', '-qm', 'registration baseline'], check=True)
        base = subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        import source_freshness
        snapshot = root / 'sources.json'
        snapshot.write_text(json.dumps(source_freshness.capture(repo, ['code.py', 'goals.json', 'writers.jsonl'])))
        contract = root / 'contract'
        contract.write_text(''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS))
        declaration = root / 'registration.json'
        declaration.write_text(json.dumps({'registry': str(registry), 'scope': ['code.py'],
            'fields': {key: key for key in ('card', 'task', 'workspace', 'base', 'scope')}}))
        home = root / 'profile'; home.mkdir()
        card, created = {}, []
        def cli(prefix, *args):
            if args == ('config', 'get', 'terminal.cwd'): return str(repo)
            if args[:2] == ('profile', 'show'): return 'Path: ' + str(home)
            if args[:3] == ('kanban', 'boards', 'list'):
                return json.dumps([{'slug': 'default', 'id': 'board-1', 'db_path': str(home / 'board.db')}])
            if 'list' in args: return json.dumps([card] if created else [])
            if 'create' in args:
                created.append(args)
                status = args[args.index('--initial-status') + 1] if '--initial-status' in args else 'running'
                card.update(id='original', title='Fixture', board_id='board-1', assignee='fixture', status=status,
                    workspace_kind='dir', workspace_path=args[args.index('--workspace') + 1][4:],
                    completion_contract='local-only', max_retries=1, current_run_id=None, worker_pid=None,
                    goal_mode=True, goal_max_turns=100)
                return json.dumps(card)
            if 'show' in args: return json.dumps({'task': card, 'runs': []})
            raise AssertionError('Unexpected mutation: ' + repr(args))
        argv = ['start_goal.py', '--profile', 'fixture', '--workspace', str(repo), '--title', 'Fixture',
                '--contract-file', str(contract), '--source-snapshot', str(snapshot), '--base', base,
                '--goal-task', 'T1', '--pass-root', str(root / 'passes'),
                '--registration-declaration', str(declaration), '--registration-native-python', '/fixture/native-python']
        requests = []
        def native_create(python, path):
            request = json.loads(Path(path).read_text())
            requests.append(request)
            task = request['task']
            card.update(task, id='original', status='ready', board_id='board-1', current_run_id=None, worker_pid=None)
            created.append(task)
            Path(request['receipt_path']).write_text(json.dumps(dict(request['handoff_template'], task_id='original', native_create=card)))
            return card
        with patch.object(m, 'create_registered', side_effect=native_create), patch('sys.argv', argv), patch.dict(m.os.environ, {}, clear=True), \
                patch.object(m, 'run', side_effect=cli), \
                patch.object(m, 'goal_fields', return_value={'goal_mode': True, 'goal_max_turns': 100}), \
                patch.object(m, 'ensure_notification', return_value=None), contextlib.redirect_stdout(io.StringIO()):
            try:
                m.main()
            except SystemExit as error:
                self.fail('Required registration cannot reserve a blocked native card: ' + str(error))
        self.assertEqual(card['status'], 'ready')
        self.assertEqual(len(requests), 1)
        self.assertEqual(requests[0]['task']['goal_max_turns'], 100)
        self.assertEqual(requests[0]['task']['max_retries'], 1)
        receipt = json.loads((home / 'autowork/goal-handoff.json').read_text())
        self.assertEqual(receipt['outcome'], 'handed_off')
        self.assertEqual(requests[0]['manifest_sha256'], receipt['pass_manifest_sha256'])
        self.assertIn('registration_preparation', receipt['pass_manifest'])
        self.assertEqual(requests[0]['handoff_template']['workspace'], card['workspace_path'])
