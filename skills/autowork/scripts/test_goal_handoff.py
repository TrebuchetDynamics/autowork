"""Offline CLI-boundary regressions; no real cards/messages are created."""
import importlib.util
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('start_goal', Path(__file__).with_name('start_goal.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class HandoffTests(unittest.TestCase):
    def test_required_registration_reserves_blocked_and_retains_original_evidence(self):
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
                '--registration-declaration', str(declaration)]
        with patch('sys.argv', argv), patch.dict(m.os.environ, {}, clear=True), \
                patch.object(m, 'run', side_effect=cli), \
                patch.object(m, 'goal_fields', return_value={'goal_mode': True, 'goal_max_turns': 100}), \
                patch.object(m, 'ensure_notification', return_value=None), contextlib.redirect_stdout(io.StringIO()):
            try:
                m.main()
            except SystemExit as error:
                self.fail('Required registration cannot reserve a blocked native card: ' + str(error))
        self.assertEqual(card['status'], 'blocked')
        receipt_path = home / 'autowork/goal-handoff.json'
        original = receipt_path.read_bytes()
        receipt = json.loads(original)
        self.assertEqual(receipt['outcome'], 'registration_pending')
        body = created[0][created[0].index('--body') + 1]
        guard = re.search(r'Before initial design, tests or any production edit, run `([^`]+)`', body).group(1)
        result = subprocess.run(shlex.split(guard), capture_output=True, text=True)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('registration preparation', result.stderr)
        expected = dict(card='original', task='T1', workspace=card['workspace_path'], base=base, scope=['code.py'])
        registry.write_text(json.dumps(expected) + '\n')
        import writer_registration
        import pass_workspace
        frozen_manifest = dict(receipt['pass_manifest'])
        frozen_manifest.pop('registration_preparation')
        with self.assertRaisesRegex(ValueError, 'Source changed before worker start: writers.jsonl'):
            pass_workspace.verify(frozen_manifest, card['workspace_path'])
        output = root / 'prepared'
        original_open = Path.open
        @contextlib.contextmanager
        def interrupted_write(path, mode='r', *args, **kwargs):
            with original_open(path, mode, *args, **kwargs) as stream:
                if path.parent == output and mode in ('xb', 'wb'):
                    stream.write(b'partial-write')
                    stream.flush()
                    raise OSError('fixture interrupted evidence write')
                yield stream
        with patch.object(Path, 'open', interrupted_write), self.assertRaisesRegex(OSError, 'interrupted'):
            writer_registration.prepare_handoff(receipt_path, hashlib.sha256(original).hexdigest(),
                {'task': card, 'runs': []}, output)
        self.assertFalse((output / 'original-handoff.json').exists(),
                         'An interrupted write must not publish a partial immutable artifact')
        prepared = writer_registration.prepare_handoff(receipt_path, hashlib.sha256(original).hexdigest(),
            {'task': card, 'runs': []}, output)
        self.assertEqual(prepared['outcome'], 'registration_prepared_native_transition_unavailable')
        admitted = subprocess.run(shlex.split(guard), capture_output=True, text=True)
        self.assertEqual(admitted.returncode, 0, admitted.stderr)
        self.assertEqual(json.loads(admitted.stdout)['outcome'], 'worker_start_admitted')
        self.assertEqual(receipt_path.read_bytes(), original)
        self.assertEqual(prepared['expected'], expected)
        self.assertTrue((output / 'original-handoff.json').exists())
        self.assertTrue((output / 'requirement.json').exists())
        (output / 'requirement.json').unlink()  # Retry an interrupted evidence write.
        self.assertEqual(writer_registration.prepare_handoff(receipt_path, hashlib.sha256(original).hexdigest(),
            {'task': card, 'runs': []}, output), prepared)
        reservation = next((home / 'autowork').glob('reservation-*.json'))
        reserved = writer_registration.prepare_handoff(reservation,
            hashlib.sha256(reservation.read_bytes()).hexdigest(), {'task': card, 'runs': []}, root / 'reserved-preparation')
        self.assertEqual(reserved['expected'], expected)
        # The reservation remains usable if native readback/notification was interrupted.
        argv_prepare = ['writer_registration.py', '--prepare-handoff', str(receipt_path),
                        '--handoff-sha256', hashlib.sha256(original).hexdigest(), '--output', str(output)]
        with patch('sys.argv', argv_prepare), patch.object(writer_registration, 'native_observation',
                return_value={'task': card, 'runs': []}), contextlib.redirect_stdout(io.StringIO()) as stdout:
            writer_registration.main()
        self.assertEqual(json.loads(stdout.getvalue()), prepared)
        for changed in ({'runs': [{'id': 'started'}]}, {'task': dict(card, worker_pid=42)},
                        {'task': dict(card, status='running')}, {'task': dict(card, board_id='foreign')},
                        {'task': dict(card, goal_max_turns=50)}, {'task': dict(card, max_retries=2)}):
            with self.subTest(changed=changed), self.assertRaises(ValueError):
                writer_registration.prepare_handoff(receipt_path, hashlib.sha256(original).hexdigest(),
                    dict(task=card, runs=[], **{}) | changed, root / 'refused')
        (repo / 'code.py').write_text('unrelated source drift\n')
        with self.assertRaisesRegex(ValueError, 'Source changed'):
            writer_registration.prepare_handoff(receipt_path, hashlib.sha256(original).hexdigest(),
                {'task': card, 'runs': []}, root / 'refused')
        self.assertFalse((root / 'refused').exists())
        # Retry the launcher after an interrupted reservation: do not create a replacement.
        with patch('sys.argv', argv), patch.dict(m.os.environ, {}, clear=True), \
                patch.object(m, 'run', side_effect=cli), \
                patch.object(m, 'goal_fields', return_value={'goal_mode': True, 'goal_max_turns': 100}), \
                patch.object(m, 'ensure_notification', return_value=None), contextlib.redirect_stdout(io.StringIO()) as stdout:
            m.main()
        self.assertEqual(json.loads(stdout.getvalue())['outcome'], 'already_owned')
        self.assertEqual(len(created), 1)
        self.assertEqual(receipt_path.read_bytes(), original)

    def test_composed_command_reaches_real_admission_once_offline(self):
        import owner_cycle
        import subprocess
        import os
        import re
        import shlex
        from test_owner_cycle import ComposedReadyTests
        fixture = ComposedReadyTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.ready_backlog()
        home = fixture.root / 'profile'
        home.mkdir()
        created = []
        card = {}
        calls = []
        def cli(prefix, *args):
            if args == ('config', 'get', 'terminal.cwd'):
                return str(fixture.repo)
            if args[:2] == ('profile', 'show'):
                return 'Path: ' + str(home)
            if args[:3] == ('kanban', 'boards', 'list'):
                return json.dumps([{'slug': 'default', 'db_path': str(home / 'board.db')}])
            if 'list' in args:
                return '[]'
            if 'create' in args:
                created.append(args)
                card.update(id='original', title=args[4], assignee='fixture', status='ready',
                            workspace_kind='dir', workspace_path=args[args.index('--workspace') + 1][4:],
                            completion_contract='local-only', max_retries=1)
                return json.dumps(card)
            if 'show' in args:
                return json.dumps({'task': card, 'runs': []})
            raise AssertionError(args)
        real_run = subprocess.run
        def boundary(argv, **kwargs):
            if len(argv) > 1 and Path(argv[1]).name == 'start_goal.py':
                calls.append(argv)
                with patch.object(sys, 'argv', argv[1:]), contextlib.redirect_stdout(io.StringIO()) as output:
                    m.main()
                return subprocess.CompletedProcess(argv, 0, output.getvalue(), '')
            return real_run(argv, **kwargs)
        import sys
        with patch.object(owner_cycle.reconcile, 'profile_home', return_value=home), \
                patch.object(owner_cycle.reconcile, 'reconcile', return_value={'outcome': 'no_handoff'}), \
                patch.object(owner_cycle.subprocess, 'run', side_effect=boundary), \
                patch.object(m, 'run', side_effect=cli), \
                patch.object(m, 'goal_fields', return_value={'goal_mode': True, 'goal_max_turns': 100}), \
                patch.object(m, 'ensure_notification', return_value={'fixture': True}), \
                patch.dict(os.environ, {}, clear=True), \
                patch.object(owner_cycle.backlog_plan, 'decide', side_effect=AssertionError('no planning')), \
                contextlib.redirect_stdout(io.StringIO()):
            code = owner_cycle.main([str(fixture.repo),
                '--profile', 'fixture', '--state-dir', str(fixture.state), '--source-path', 'code.py',
                '--pass-root', str(fixture.root / 'passes'), '--apply'])
        receipt = json.loads((fixture.state / 'unblock-latest.json').read_text())
        self.assertEqual(code, 0, receipt)
        self.assertEqual(len(calls), 1)
        self.assertNotIn('--validate-only', calls[0])
        self.assertEqual(len(created), 1)
        self.assertEqual(receipt['handoff']['result']['task_id'], 'original')
        self.assertEqual(json.loads((fixture.repo / 'goals.json').read_text())['tasks'][0]['status'], 'in_progress')
        self.assertNotIn('primary_milestone', json.loads((fixture.repo / 'goals.json').read_text()))
        body = created[0][created[0].index('--body') + 1]
        self.assertNotIn('ENGINEERING-CYCLE.md', body)
        guard = re.search(r'Before initial design, tests or any production edit, run `([^`]+)`', body).group(1)
        result = real_run(shlex.split(guard), capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'worker_start_admitted')
        manifest = receipt['handoff']['result']['pass_manifest']
        import runtime_bundle
        files = runtime_bundle.verify(manifest['helper_runtime'])['files']
        self.assertIn('autowork/scripts/ready_preflight.py', files)
        self.assertIn('autowork/scripts/retry_selection.py', files)

    def test_proposal_handoff_reaches_native_create_with_uncommitted_planning_only(self):
        import subprocess
        with tempfile.TemporaryDirectory() as directory:
            root=Path(directory);repo=root/'repo';repo.mkdir();home=root/'profile';home.mkdir()
            def git(*args):return subprocess.check_output(['git','-C',str(repo),*args],text=True).strip()
            git('init','-q');git('config','user.name','Fixture');git('config','user.email','fixture@local')
            (repo/'code.py').write_text('print("fixture")\n')
            git('add','code.py');git('commit','-qm','base');base=git('rev-parse','HEAD')
            (repo/'goals.json').write_text(json.dumps({'version':1,'primary_milestone':'G1',
                'goals':[{'id':'G1','title':'Fixture','status':'unmet','priority':1,'source':'PLAN.md#slice','tasks':['T1']}],
                'tasks':[{'id':'T1','title':'Fixture','goal':'G1','status':'open','section':'Now'}]}))
            (repo/'TODO.md').write_text('T1 fixture task')
            (repo/'PLAN.md').write_text('# Slice\nStatus: Accepted\n')
            snapshot=root/'snapshot.json';snapshot.write_text(json.dumps({'version':1,'workspace':str(repo),
                'files':[{'path':n,'sha256':m.hashlib.sha256((repo/n).read_bytes()).hexdigest()}
                         for n in ['code.py','goals.json','TODO.md','PLAN.md']]}))
            contract=root/'contract';contract.write_text(''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS))
            before=git('status','--porcelain');created=[]
            def cli(prefix,*args):
                if args[:3]==('config','get','terminal.cwd'):return str(repo)
                if args[:2]==('profile','show'):return 'Path: '+str(home)
                if args[:3]==('kanban','boards','list'):return json.dumps([{'slug':'default','id':'fixture','db_path':str(home/'board.db')}])
                if 'list' in args:return '[]'
                if 'create' in args:
                    created.append(args)
                    raise RuntimeError('fixture native create boundary')
                raise AssertionError(args)
            argv=['start_goal.py','--profile','fixture','--workspace',str(repo),'--title','Fixture',
                '--contract-file',str(contract),'--source-snapshot',str(snapshot),'--base',base,
                '--goal-task','T1','--ledger-mode','proposal','--integration-owner','parent',
                '--pass-root',str(root/'passes'),'--required-path','PLAN.md','--required-path','code.py']
            missing_base = argv.copy()
            position = missing_base.index('--base')
            del missing_base[position:position + 2]
            with patch('sys.argv',missing_base),patch.dict(m.os.environ,{},clear=True),patch.object(m,'run',side_effect=cli):
                with self.assertRaises(SystemExit): m.main()
            self.assertEqual(list((home / 'autowork/runtimes').glob('*')), [],
                             'Pre-create refusal must not retain an unreferenced runtime')
            original_snapshot = snapshot.read_bytes()
            freeze = m.runtime_bundle.freeze
            def change_source_after_freeze(*args):
                runtime = freeze(*args)
                snapshot.write_bytes(original_snapshot + b' ')
                return runtime
            with patch('sys.argv',argv),patch.dict(m.os.environ,{},clear=True),patch.object(m,'run',side_effect=cli), \
                 patch.object(m.runtime_bundle, 'freeze', side_effect=change_source_after_freeze):
                with self.assertRaisesRegex(SystemExit, 'Source snapshot changed during assembly'): m.main()
            self.assertEqual(list((home / 'autowork/runtimes').glob('*')), [])
            snapshot.write_bytes(original_snapshot)
            with patch('sys.argv',argv),patch.dict(m.os.environ,{},clear=True),patch.object(m,'run',side_effect=cli):
                with self.assertRaisesRegex(RuntimeError,'fixture native create boundary'):m.main()
            self.assertEqual(len(created),1)
            body = created[0][created[0].index('--body')+1]
            self.assertNotIn(str(Path(m.__file__).resolve().parents[2]), body)
            manifests = list((home / 'autowork').glob('pass-*.json'))
            manifests = [path for path in manifests
                         if Path(json.loads(path.read_text())['helper_runtime']['root']).exists()]
            self.assertEqual(len(manifests), 1)
            runtime = json.loads(manifests[0].read_text())['helper_runtime']
            self.assertIn(runtime['root'], body)
            self.assertIn(runtime['sha256'], body)
            import runtime_bundle
            frozen = runtime_bundle.verify(runtime)
            self.assertIn('autowork/scripts/writer_registration.py', frozen['files'])
            self.assertIn('autowork/scripts/agent_commit.sh', frozen['files'])
            self.assertIn('docs-sync/scripts/todo_archive.py', frozen['files'])
            import re, shlex
            guard = re.search(r'Before initial design, tests or any production edit, run `([^`]+)`', body).group(1)
            admitted = subprocess.run(shlex.split(guard), text=True, capture_output=True)
            self.assertEqual(admitted.returncode, 0, admitted.stderr)
            self.assertEqual(json.loads(admitted.stdout)['outcome'], 'worker_start_admitted')
            self.assertIn('READ-ONLY PLANNING CONTEXT', body)
            self.assertIn('INITIAL IMPLEMENTATION ONLY', body)
            self.assertIn('does not apply to review entry or review rework', body)
            self.assertIn('REVIEW ENTRY (same original card)', body)
            self.assertIn('Do not rerun pass_workspace.py', body)
            self.assertIn('original pre-edit admission', body)
            self.assertIn('finish_task.py receipt', body)
            self.assertIn('foreign changes', body)
            self.assertIn('missing or forged admission', body)
            self.assertIn('moved task ref', body)
            self.assertEqual(git('status','--porcelain'),before)
            self.assertEqual(git('rev-parse','HEAD'),base)

    def test_progress_contract_requires_concrete_fields(self):
        validator = getattr(m, 'validate_contract', None)
        self.assertTrue(callable(validator), 'Handoff needs a structured contract preflight')
        with self.assertRaisesRegex(ValueError, 'Project payoff'):
            validator('Objective: Fix cancellation\nScope: src/client.py\nVerification: focused test\nSource: accepted issue\n')
        text = ('Objective: Fix cancellation\nScope: src/client.py and tests/test_client.py\n'
                'Verification: pytest tests/test_client.py, confirm failure before fix\n'
                'Source: accepted lifecycle contract\nProject payoff: prevent requests surviving owner disposal\n'
                'Current evidence: src/client.py:31 misses cancellation on disposal\n'
                'Expected change: cancel owned request and retain lifecycle regression\n'
                'Acceptance: disposal cancels one request; normal completion unchanged\n'
                'Stop conditions: complete after passing focused regression, or block on conflicting ownership\n'
                'Repo-docs pass: Maintain; lifecycle contract and TODO checked against src/client.py; no doc drift\n')
        self.assertEqual(validator(text)['Expected change'], 'cancel owned request and retain lifecycle regression')
    def test_invalid_contract_stops_before_any_cli_call(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / 'contract.txt'
            contract.write_text('Objective: another generic audit\n')
            argv = ['start_goal.py', '--profile', 'fixture', '--workspace', directory,
                    '--title', 'Unspecified task', '--contract-file', str(contract)]
            with patch('sys.argv', argv), patch.dict(m.os.environ, {}, clear=True), \
                    patch.object(m, 'run', return_value=directory) as cli:
                with self.assertRaisesRegex(SystemExit, 'Missing or empty contract field: Scope'):
                    m.main()
                cli.assert_not_called()

    def test_new_handoff_requires_repo_docs_pass_record(self):
        text = ''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS
                       if key != 'Repo-docs pass')
        with self.assertRaisesRegex(ValueError, 'Missing or empty contract field: Repo-docs pass'):
            m.validate_contract(text)
        recorded = text + 'Repo-docs pass: Maintain; README and TODO checked against src/client.py; profile-local journal receipt\n'
        self.assertIn('Maintain', m.validate_contract(recorded)['Repo-docs pass'])

    def test_dispatch_requires_unchanged_source_snapshot(self):
        preflight=getattr(m,'require_fresh_sources',None)
        self.assertTrue(callable(preflight),'Dispatch needs source-freshness preflight')
        with tempfile.TemporaryDirectory() as directory:
            r=Path(directory)
            with self.assertRaisesRegex(ValueError,'Source snapshot required'):
                preflight(None,r)
            source=r/'client.py';source.write_text('pending fix\n')
            digest=m.hashlib.sha256(source.read_bytes()).hexdigest()
            snapshot=r/'snapshot.json';snapshot.write_text(json.dumps({'version':1,'workspace':str(r.resolve()),'files':[{'path':'client.py','sha256':digest}]}))
            self.assertTrue(preflight(snapshot,r)['fresh'])
            source.write_text('completed by another owner\n')
            with self.assertRaisesRegex(ValueError,'Source changed since selection'):
                preflight(snapshot,r)

    def test_main_stale_snapshot_never_creates_card(self):
        with tempfile.TemporaryDirectory() as directory:
            r=Path(directory);source=r/'client.py';source.write_text('pending\n')
            snapshot=r/'snapshot.json';snapshot.write_text(json.dumps({'version':1,'workspace':str(r.resolve()),'files':[{'path':'client.py','sha256':m.hashlib.sha256(source.read_bytes()).hexdigest()}]}))
            source.write_text('already repaired\n')
            contract=r/'contract.txt';contract.write_text(''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS))
            argv=['start_goal.py','--profile','fixture','--workspace',directory,'--title','Repair','--contract-file',str(contract),'--source-snapshot',str(snapshot)]
            def cli(prefix,*args):
                if args[:3]==('config','get','terminal.cwd'):return directory
                if args[:2]==('profile','show'):return 'Path: '+directory
                if 'list' in args:return '[]'
                raise AssertionError('Unexpected CLI mutation: '+repr(args))
            with patch('sys.argv',argv),patch.dict(m.os.environ,{},clear=True),patch.object(m,'run',side_effect=cli) as calls:
                with self.assertRaisesRegex(SystemExit,'Source changed since selection'):m.main()
                self.assertFalse(any('create' in call.args for call in calls.call_args_list))

    def test_duplicate_field_is_not_silently_overwritten(self):
        text = ''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS)
        with self.assertRaisesRegex(ValueError, 'Duplicate contract field: Scope'):
            m.validate_contract(text + 'Scope: expanded beyond original boundaries\n')

    def test_empty_fields_and_inline_labels_do_not_pass(self):
        text = ''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS)
        with self.assertRaisesRegex(ValueError, 'Missing or empty contract field: Acceptance'):
            m.validate_contract(text.replace('Acceptance: concrete Acceptance', 'Acceptance:'))
        with self.assertRaisesRegex(ValueError, 'Missing or empty contract field: Acceptance'):
            m.validate_contract(text.replace('Acceptance: concrete Acceptance', 'A paragraph mentions Acceptance: without a field'))

    def test_worker_body_makes_completion_evidence_explicit(self):
        builder = getattr(m, 'build_task_body', None)
        self.assertTrue(callable(builder), 'Native goal judge needs an evidence-bearing completion contract')
        text = ''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS)
        body = builder(text)
        self.assertIn('Before calling kanban_complete', body)
        self.assertIn('Acceptance evidence:', body)
        self.assertIn('NOT_CHECKED', body)
        self.assertIn('100-turn budget', body)
        self.assertTrue(body.startswith(m.REVIEW_DOD + '\n\n' + text))
        self.assertIn('NOT part of this goal', body)

    def test_worker_owns_debug_fix_test_review_without_intermediate_cards(self):
        body = m.build_task_body('Objective: implement scoped repair\n', 100)
        self.assertIn('Own debugging, fixes, focused tests and review handoff on this card', body)
        self.assertIn('5 consecutive attempts without new evidence', body)
        self.assertIn('Stop at acceptance; do not burn unused turns', body)
        self.assertIn('One native review lane', body)
        self.assertIn('100-turn budget', body)

    def test_worker_checks_changed_dependency_delivery_boundary(self):
        body = m.build_task_body('Objective: add shared CLI error serializer\n')
        self.assertIn('Trace changed imports to their runtime delivery boundary', body)
        self.assertIn('checkout tests do not prove packaged execution', body)
        self.assertIn('image build/run/deployment NOT_CHECKED', body)
        self.assertIn('explicit scope excludes packaging edits', body)

    def test_review_handoff_is_not_circular_completion_requirement(self):
        body = m.build_task_body('Objective: implement scoped repair\n')
        self.assertIn('Review handoff finishes this worker card, not the product milestone', body)
        self.assertIn('pending review is not a missing implementation criterion', body)
        self.assertIn('never invent approval', body)
        self.assertIn('preserve exact receipts and original card', body)
        self.assertIn('Only the authorized review lane can approve closure', body)

    def test_circular_entry_retries_once_without_waiving_review(self):
        body = m.build_task_body('Objective: implement scoped repair\n')
        self.assertIn('one corrected review request', body)
        self.assertIn('citing the card Definition of done', body)
        self.assertNotIn('administrative review-entry assessment', body)
        self.assertNotIn('stop for operator resolution', body)
        self.assertIn('never invent approval, force a live claim, replace the card, waive review', body)
        self.assertIn('preserve exact receipts and original card', body)

    def test_validate_only_is_real_preflight_without_cli_or_journal_writes(self):
        with tempfile.TemporaryDirectory() as directory:
            contract = Path(directory) / 'contract.txt'
            contract.write_text(''.join(f'{key}: concrete {key}\n' for key in m.CONTRACT_FIELDS))
            argv = ['start_goal.py', '--profile', 'fixture', '--workspace', directory,
                    '--title', 'Fixture', '--contract-file', str(contract), '--validate-only']
            output = io.StringIO()
            with patch('sys.argv', argv), patch.dict(m.os.environ, {}, clear=True), \
                    patch.object(m, 'run') as cli, contextlib.redirect_stdout(output):
                try:
                    m.main()
                except SystemExit as error:
                    self.fail(f'Validation-only unexpectedly exited: {error}')
                cli.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['outcome'], 'contract_validated')
            self.assertFalse(json.loads(output.getvalue())['factual_validation'])
            self.assertEqual(list(Path(directory).iterdir()), [contract])

    def test_subscribes_and_reads_back_passive_profile_route(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.env').write_text('TELEGRAM_HOME_CHANNEL=12345\n')
            subscriptions = []
            def cli(prefix, *args):
                if 'notify-subscribe' in args:
                    subscriptions.append({'task_id': 't_fixture', 'platform': 'telegram', 'chat_id': '12345', 'notifier_profile': 'fixture', 'delivery_mode': 'notify'})
                    return 'Subscribed'
                if 'notify-list' in args:
                    return json.dumps(subscriptions)
                raise AssertionError(args)
            with patch.object(m, 'run', side_effect=cli):
                result = m.ensure_notification(['hermes', '-p', 'fixture'], 't_fixture', home, 'fixture')
            self.assertEqual(result['delivery_mode'], 'notify')
            self.assertEqual(result['notifier_profile'], 'fixture')

    def test_no_home_preserves_local_only(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(m, 'run') as cli:
            self.assertIsNone(m.ensure_notification(['hermes'], 't_fixture', Path(directory), 'default'))
            cli.assert_not_called()

    def test_notification_readback_failure_is_not_success(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory)
            (home / '.env').write_text('TELEGRAM_HOME_CHANNEL=12345\n')
            with patch.object(m, 'run', side_effect=['Subscribed', '[]']):
                with self.assertRaisesRegex(RuntimeError, 'notification subscription was not verified'):
                    m.ensure_notification(['hermes'], 't_fixture', home, 'fixture')

    def test_blocked_same_title_survives_contract_wording_changes(self):
        task = {'id': 't_blocked', 'assignee': 'fixture', 'status': 'blocked', 'title': 'Selected slice'}
        self.assertEqual(m.existing_task([task], 'fixture', 'Selected slice'), task)
        self.assertIsNone(m.existing_task([task], 'fixture', 'Disjoint slice'))

    def test_profile_home_uses_cli_path_not_launch_home(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(m, 'run', return_value='Profile: fixture\nPath:    ' + directory + '\n'):
                self.assertEqual(m.profile_home(['hermes', '-p', 'fixture']), Path(directory).resolve())

    def test_nested_continuation_receipt_can_be_archived_before_next_handoff(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory)
            prior = {'task_id': None, 'current_handoff': {'task_id': 't_old',
                     'board_id': 'default', 'created_at': '2026-01-01T00:00:00Z'},
                     'notes': 'retain original history'}
            original = json.dumps(prior).encode()
            (journal/'goal-handoff.json').write_bytes(original)
            new = {'task_id': 't_new', 'board_id': 'default', 'created_at': '2026-01-02T00:00:00Z'}
            m.save_receipt(journal, new)
            self.assertEqual(json.loads((journal/'goal-handoff.json').read_text()), new)
            self.assertEqual((journal/'handoffs/t_old.json').read_bytes(), original)
            archives = list((journal/'handoffs').glob('2026-01-01*.json'))
            self.assertEqual(len(archives), 1)
            self.assertEqual(archives[0].read_bytes(), original)

    def test_invalid_nested_identity_preserves_receipt_without_archival(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory)
            target = journal/'goal-handoff.json'
            for task_id in (None, '', '..', '../escape', 123):
                original = json.dumps({'task_id': None, 'current_handoff': {'task_id': task_id}}).encode()
                target.write_bytes(original)
                with self.subTest(task_id=task_id), self.assertRaisesRegex(ValueError, 'prior task ID'):
                    m.save_receipt(journal, {'task_id': 't_new'})
                self.assertEqual(target.read_bytes(), original)
                self.assertFalse((journal/'handoffs').exists())

    def test_receipt_survives_notification_failure_preserves_previous(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = Path(directory)
            previous = {'task_id': 't_old', 'status': 'ready'}
            (journal / 'goal-handoff.json').write_text(json.dumps(previous))
            receipt = {'task_id': 't_new', 'status': 'ready'}
            with patch.object(m, 'ensure_notification', side_effect=RuntimeError('delivery unavailable')):
                result = m.record_handoff(['hermes'], journal, journal.parent, 'fixture', receipt)
            self.assertEqual(result['outcome'], 'notification_blocked')
            saved = json.loads((journal / 'goal-handoff.json').read_text())
            self.assertEqual(saved['task_id'], 't_new')
            self.assertIn('delivery unavailable', saved['notification_error'])
            self.assertEqual(json.loads((journal / 'handoffs/t_old.json').read_text()), previous)

    def test_dated_history_conserves_exact_original_bytes_and_board_identity(self):
        (Path.home() / '.hermes/cache/scratch').mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory(dir=Path.home() / '.hermes/cache/scratch') as directory:
            journal = Path(directory)
            old = {'task_id': 'same_card', 'board_id': 'board_a', 'created_at': '2026-10-07T12:00:00Z', 'note': 'original'}
            raw = json.dumps(old, separators=(',', ':')) + '\n\n'
            (journal / 'goal-handoff.json').write_text(raw)
            new = {**old, 'board_id': 'board_b', 'created_at': '2026-10-08T12:00:00Z', 'note': 'next'}
            m.save_receipt(journal, new)
            dated = list((journal / 'handoffs').glob('2026-10-07*.json'))
            self.assertEqual(len(dated), 1)
            self.assertEqual(dated[0].read_text(), raw)
            # Reusing a native ID on a different board must not overwrite either original.
            first_files = {p.name: p.read_bytes() for p in (journal / 'handoffs').iterdir()}
            m.save_receipt(journal, {'task_id': 'third', 'board_id': 'board_a', 'created_at': '2026-10-09T12:00:00Z'})
            for name, content in first_files.items():
                self.assertEqual((journal / 'handoffs' / name).read_bytes(), content)
            archived = [json.loads(p.read_text()) for p in (journal / 'handoffs').glob('2026-*.json')]
            self.assertIn(old, archived)
            self.assertIn(new, archived)

    def test_same_workspace_other_profile_blocks_handoff(self):
        task = {'id': 't_other', 'assignee': 'other', 'status': 'running', 'workspace_kind': 'dir', 'workspace_path': '/project'}
        self.assertEqual(m.existing_task([task], 'fixture', 'Other slice', '/project'), task)
        self.assertIsNone(m.existing_task([task], 'fixture', 'Other slice', '/disjoint'))

    def test_running_task_wins_over_new_slice(self):
        task = {'id': 't_live', 'assignee': 'fixture', 'status': 'running', 'title': 'Existing slice'}
        self.assertEqual(m.existing_task([task], 'fixture', 'Other slice'), task)
        self.assertIsNone(m.existing_task([task], 'other-profile', 'Other slice'))

if __name__ == '__main__':
    unittest.main()
