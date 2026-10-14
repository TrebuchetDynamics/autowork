"""Transactional registration fixtures: real Git and SQLite, fake native API."""
import contextlib
import hashlib
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import unittest
from unittest.mock import patch

import test_pass_workspace


class NativeFixture:
    @contextlib.contextmanager
    def write_txn(self, conn):
        conn.execute('BEGIN IMMEDIATE')
        try:
            yield conn
            conn.commit()
        except BaseException:
            conn.rollback()
            raise

    def create_task(self, conn, **task):
        task.pop('board', None)
        task['project_id'] = None
        conn.execute('INSERT INTO tasks VALUES (?,?,?)', ('t_fixture', json.dumps(task), task['idempotency_key']))
        return 't_fixture'

    def get_task(self, conn, card):
        row = conn.execute('SELECT data FROM tasks WHERE id=?', (card,)).fetchone()
        return SimpleNamespace(id=card, status='ready', **json.loads(row[0])) if row else None

    def list_runs(self, conn, card):
        return []

    def add_comment(self, conn, card, author, body):
        conn.execute('INSERT INTO comments VALUES (?)', (body,))


class RegistrationAdmissionTests(unittest.TestCase):
    def setUp(self):
        f = test_pass_workspace.PassWorkspaceTests()
        f.setUp()
        self.addCleanup(f.doCleanups)
        self.fixture = f
        self.guard, manifest, worker = f.worker_transition_fixture()
        import writer_registration, runtime_bundle
        root = Path(f.tmp.name)
        registry = f.root / 'writers.jsonl'
        registry.write_text('')
        manifest['registration_preparation'] = writer_registration.capture_declaration(
            dict(registry=str(registry), scope=['owned.py'], fields={k:k for k in
                ('card','task','workspace','base','scope')}), f.root, manifest['files'], [])
        manifest['helper_runtime'] = runtime_bundle.freeze(Path(__file__).resolve().parents[2], root / 'runtime')
        journal = root / 'journal'; journal.mkdir()
        path = journal / 'pass.json'; path.write_text(json.dumps(manifest))
        self.registry = registry
        self.request = dict(db_path=str(root / 'board.db'), profile='fixture', manifest_path=str(path),
            manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(), receipt_path=str(journal / 'reservation-pass.json'),
            handoff_template=dict(profile='fixture', board_id=str(root / 'board.db'), goal_task='T1',
                workspace=str(worker), source_workspace=str(f.root), helper_runtime=manifest['helper_runtime'],
                goal_mode=True, goal_max_turns=50, max_retries=1, pass_manifest=manifest,
                pass_manifest_path=str(path), pass_manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest()),
            task=dict(title='Fixture', body='Execute guarded fixture', assignee='fixture', workspace_kind='dir',
                workspace_path=str(worker), goal_mode=True, goal_max_turns=50, max_retries=1,
                completion_contract='local-only', created_by='autowork', idempotency_key='autowork:fixture'))
        self.conn = sqlite3.connect(self.request['db_path'])
        self.addCleanup(self.conn.close)
        self.conn.executescript('CREATE TABLE tasks (id TEXT, data TEXT, idempotency_key TEXT); CREATE TABLE comments (body TEXT);')

    def test_registration_is_verified_before_card_becomes_visible(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('registration_admission'), 'Transactional admission is missing')
        import registration_admission as admission
        observer = sqlite3.connect(self.request['db_path'])
        self.addCleanup(observer.close)
        verify = admission.pass_workspace.verify
        def checked(*args, **kwargs):
            self.assertEqual(observer.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)
            self.assertTrue(Path(self.request['receipt_path']).exists())
            return verify(*args, **kwargs)
        with patch.object(admission.pass_workspace, 'verify', side_effect=checked):
            result = admission.create_registered(NativeFixture(), self.conn, self.request)
        self.assertEqual(result['id'], 't_fixture')
        self.assertEqual(observer.execute('SELECT count(*) FROM tasks').fetchone()[0], 1)
        row = json.loads(self.registry.read_text())
        self.assertEqual(row['card'], result['id'])
        self.assertEqual(row['scope'], ['owned.py'])
        self.assertEqual(self.conn.execute('SELECT count(*) FROM comments').fetchone()[0], 1)
        original = Path(self.request['manifest_path']).read_bytes()
        self.assertEqual(hashlib.sha256(original).hexdigest(), self.request['manifest_sha256'])
        with self.assertRaises(ValueError):
            admission.create_registered(NativeFixture(), self.conn, self.request)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 1)

    def test_failed_admission_rolls_back_card_and_preserves_attributed_append(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('registration_admission'), 'Transactional admission is missing')
        import registration_admission as admission
        with patch.object(admission.pass_workspace, 'verify', side_effect=ValueError('source changed')):
            with self.assertRaisesRegex(ValueError, 'source changed'):
                admission.create_registered(NativeFixture(), self.conn, self.request)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)
        self.assertEqual(json.loads(self.registry.read_text())['card'], 't_fixture')
        receipt = json.loads(Path(self.request['receipt_path']).read_text())
        self.assertEqual(receipt['task_id'], 't_fixture')
        self.assertEqual(receipt['native_commit'], 'unverified')

    def test_failed_attempt_cannot_be_rebased_into_new_card(self):
        import registration_admission as admission
        with patch.object(admission.pass_workspace, 'verify', side_effect=ValueError('source changed')):
            with self.assertRaises(ValueError):
                admission.create_registered(NativeFixture(), self.conn, self.request)
        before = self.registry.read_bytes()
        manifest = self.request['handoff_template']['pass_manifest']
        manifest['registration_preparation'].update(baseline=before.decode(),
            baseline_sha256=hashlib.sha256(before).hexdigest())
        path = Path(self.request['manifest_path']).with_name('another-pass.json')
        path.write_text(json.dumps(manifest))
        self.request.update(manifest_path=str(path), manifest_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),
            receipt_path=str(path.with_name('reservation-another.json')))
        self.request['handoff_template'].update(pass_manifest_path=str(path), pass_manifest_sha256=self.request['manifest_sha256'])
        with self.assertRaisesRegex(ValueError, 'Retained registration attempt'):
            admission.create_registered(NativeFixture(), self.conn, self.request)
        self.assertEqual(self.registry.read_bytes(), before)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)

    def test_original_writer_race_is_refused_inside_creation_transaction(self):
        import registration_admission as admission
        self.request['handoff_template']['disjoint_fallback'] = dict(original_card='t_old',
            original_workspace='/original/worker', original_body_sha256=hashlib.sha256(b'original').hexdigest(),
            original_run_id=3)
        native = NativeFixture()
        original = SimpleNamespace(status='running', assignee='fixture', workspace_path='/original/worker',
            current_run_id=4, worker_pid=123, claim_lock='active', body='original')
        with patch.object(native, 'get_task', return_value=original), \
                patch.object(native, 'list_runs', return_value=[]):
            with self.assertRaisesRegex(ValueError, 'ownership changed'):
                admission.create_registered(native, self.conn, self.request)
        self.assertEqual(self.registry.read_bytes(), b'')
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)

    def test_drift_or_foreign_binding_refuses_before_create(self):
        import importlib.util
        self.assertIsNotNone(importlib.util.find_spec('registration_admission'), 'Transactional admission is missing')
        import registration_admission as admission
        for key, value in [('assignee','foreign'),('workspace_path','/foreign'),('goal_max_turns',100),
                           ('max_retries',2),('completion_contract','protected-pr')]:
            with self.subTest(key=key), patch.dict(self.request['task'], {key:value}):
                with self.assertRaises(ValueError):
                    admission.create_registered(NativeFixture(), self.conn, self.request)
            self.assertEqual(self.registry.read_bytes(), b'')
        self.registry.write_text('{}\n')
        with self.assertRaises(ValueError):
            admission.create_registered(NativeFixture(), self.conn, self.request)
        self.assertEqual(self.conn.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)


@unittest.skipUnless(__import__('os').environ.get('HERMES_NATIVE_REGISTRATION_TEST') == '1',
                     'explicit isolated native registration qualification only')
class NativeRegistrationTests(unittest.TestCase):
    def test_installed_native_creation_is_atomic_and_failure_rolls_back(self):
        import os
        import registration_admission as admission
        from hermes_cli import kanban_db as kb
        from hermes_cli.kanban_db_connect import connect_closing
        for fail in (False, True):
            with self.subTest(fail=fail):
                fixture = RegistrationAdmissionTests(); fixture.setUp()
                self.addCleanup(fixture.doCleanups)
                fixture.conn.close()
                db = Path(fixture.request['db_path']); db.unlink()
                root = db.parent
                with patch.dict(os.environ, {'HERMES_HOME':str(root/'native-home'),
                        'HERMES_KANBAN_HOME':str(root/'native-board')}, clear=True), \
                        connect_closing(db_path=db) as conn:
                    observer = sqlite3.connect(str(db)); self.addCleanup(observer.close)
                    verify = admission.pass_workspace.verify
                    def checked(*args, **kwargs):
                        self.assertEqual(observer.execute('SELECT count(*) FROM tasks').fetchone()[0], 0)
                        if fail:
                            raise ValueError('fixture final guard failure')
                        return verify(*args, **kwargs)
                    with patch.object(admission.pass_workspace, 'verify', side_effect=checked):
                        if fail:
                            with self.assertRaisesRegex(ValueError, 'fixture final guard'):
                                admission.create_registered(kb, conn, fixture.request)
                        else:
                            result = admission.create_registered(kb, conn, fixture.request)
                            card = kb.get_task(conn, result['id'])
                            self.assertEqual((card.status, card.goal_max_turns, card.max_retries), ('ready',50,1))
                            self.assertEqual(kb.list_runs(conn, card.id), [])
                    self.assertEqual(observer.execute('SELECT count(*) FROM tasks').fetchone()[0], 0 if fail else 1)
