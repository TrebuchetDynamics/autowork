import importlib.util
import os
from pathlib import Path
import tempfile
import time
import unittest

SCRIPT = Path(__file__).parents[1] / 'scripts/profile-consult.py'

class ConsultationTests(unittest.TestCase):
    def load(self):
        self.assertTrue(SCRIPT.exists(), 'shared executable consultation transport missing')
        spec = importlib.util.spec_from_file_location('consult', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module

    def test_explicit_scope_contacts_only_requested_profiles(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            root.mkdir()
            with patch.object(m, 'discover', return_value=['default', 'one', 'two', 'other']), \
                    patch.object(m, 'consult', side_effect=lambda name, *a: {'profile': name, 'status': 'replied'}) as call:
                rows = m.run_all(root, root / 'maintenance/scoped', 'self', 'hermes', 10, profiles=['two', 'one'])
            self.assertEqual({c.args[0] for c in call.call_args_list}, {'one', 'two'})
            self.assertEqual([r['profile'] for r in rows], ['default', 'two', 'one'])
            import json
            saved = json.loads((root / 'maintenance/scoped/index.json').read_text())
            self.assertEqual(saved['targets'], ['default', 'two', 'one'])

    def test_invalid_scope_refuses_before_provider_calls(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            root.mkdir()
            for scope in (['missing'], ['one', 'one'], ['default']):
                with patch.object(m, 'discover', return_value=['default', 'one']), patch.object(m, 'consult') as call:
                    with self.assertRaises(ValueError):
                        m.run_all(root, root / 'maintenance/scoped', 'self', 'hermes', 10, profiles=scope)
                    call.assert_not_called()

    def history(self, root, name, rows):
        import sqlite3
        home = root / 'profiles' / name
        home.mkdir(parents=True)
        with sqlite3.connect(home / 'state.db') as db:
            db.execute('CREATE TABLE sessions (id TEXT, source TEXT, title TEXT, cwd TEXT, git_repo_root TEXT, profile_name TEXT, parent_session_id TEXT, started_at REAL)')
            db.executemany('INSERT INTO sessions VALUES (?,?,?,?,?,?,?,?)', rows)
            db.execute('CREATE TABLE messages (id INTEGER PRIMARY KEY, session_id TEXT, role TEXT, content TEXT)')
            db.executemany('INSERT INTO messages VALUES (?,?,?,?)',
                           [(i, row[0], 'assistant', 'Bounded owner reply') for i, row in enumerate(rows, 1)])
        return home / 'state.db'

    def test_consultation_heavy_history_binds_original_without_transcripts(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            original = ('original', 'telegram', 'Project repair', '/repo/one', '/repo/one', 'one', None, 1)
            rows = [original] + [(str(i), 'oneshot', 'Shared hermes-toolset feedback', '/maintenance', None, 'one', None, i) for i in range(2, 502)]
            rows += [('older', 'cli', 'Older project', None, None, 'one', None, 0),
                     ('cron', 'cron', 'Project repair', None, None, 'one', None, 600),
                     ('worker', 'kanban', 'Project repair', None, None, 'one', None, 601),
                     ('synthetic-cli', 'cli', 'Propose shared hermes-toolset improvements', None, None, 'one', None, 602),
                     ('foreign', 'cli', 'Foreign project', None, None, 'two', None, 603),
                     ('child', 'telegram', 'Project repair', None, None, 'one', 'original', 604)]
            db = self.history(root, 'one', rows)
            before = db.read_bytes()
            evidence = m.original_evidence('one', root)
            self.assertEqual(evidence['session_id'], 'original')
            self.assertEqual(evidence['cwd'], '/repo/one')
            self.assertEqual(db.read_bytes(), before)
            with patch.object(m, 'execute', return_value={'stdout': '{"type":"result","exit_code":0,"text":"ok"}', 'stderr': '', 'returncode': 0, 'timed_out': False}) as run:
                result = m.consult('one', root, 'hermes', 65)
            run.assert_called_once()
            prompt = run.call_args.args[0][-1]
            self.assertIn('session_id', prompt)
            self.assertIn('original', prompt)
            self.assertIn('Do not keyword-search', prompt)
            self.assertIn('only for profile one', prompt)
            self.assertNotIn('Foreign project', prompt)
            self.assertEqual(result['original_evidence'], evidence)
            self.assertEqual(run.call_args.args[3], 75)

    def test_read_is_anchored_to_latest_owner_reply_not_session_bookends(self):
        import sqlite3
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            db = self.history(root, 'one', [('original', 'telegram', 'Project', None, None, 'one', None, 1)])
            with sqlite3.connect(db) as connection:
                connection.executemany('INSERT INTO messages VALUES (?,?,?,?)', [
                    (2, 'original', 'assistant', ''),
                    (3, 'original', 'assistant', 'owner-private-content'),
                    (4, 'original', 'tool', 'tool dump'),
                    (5, 'foreign', 'assistant', 'foreign reply')])
            before = db.read_bytes()
            evidence = m.original_evidence('one', root)
            self.assertEqual(evidence['around_message_id'], 3)
            self.assertNotIn('owner-private-content', str(evidence))
            self.assertEqual(db.read_bytes(), before)
            with patch.object(m, 'execute', return_value={'stdout': '{"type":"result","exit_code":0,"text":"ok"}', 'stderr': '', 'returncode': 0, 'timed_out': False}) as call:
                m.consult('one', root, 'hermes', 65)
            prompt = call.call_args.args[0][-1]
            self.assertIn('around_message_id', prompt)
            self.assertIn('window=20', prompt)
            self.assertIn('role_filter="user,assistant"', prompt)

    def test_history_unavailable_is_explicit_and_does_not_search_or_request_links(self):
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            self.assertFalse((root / 'profiles').exists())
            self.history(root, 'one', [('only', 'oneshot', 'Feedback', None, None, 'one', None, 1)])
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            self.assertIn('Do not search', m.QUESTION)
            self.assertIn('Do not ask the user', m.QUESTION)

    def test_evidence_is_bounded_redacted_and_profile_isolated(self):
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            self.history(root, 'one', [('a', 'cli', 'token=private-value ' + 'x' * 1000, None, None, None, None, 1)])
            other = self.history(root, 'two', [('b', 'cli', 'Other project', None, None, 'two', None, 2)])
            evidence = m.original_evidence('one', root)
            self.assertNotIn('private-value', str(evidence))
            self.assertLessEqual(len(evidence['title']), 240)
            self.assertEqual(evidence['session_id'], 'a')
            db = root / 'profiles/one/state.db'
            db.unlink()
            db.symlink_to(other)
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            for name in ('default', '../two', 'One'):
                with self.assertRaises(ValueError):
                    m.original_evidence(name, root)

    def test_unusable_history_fails_closed(self):
        import sqlite3
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            db = self.history(root, 'one', [('bad id', 'cli', 'Project', None, None, 'one', None, 1)])
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            with sqlite3.connect(db) as connection:
                connection.execute('DROP TABLE sessions')
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            db.write_bytes(b'not a sqlite database')
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')
            db.unlink()
            (root / 'profiles/one').rmdir()
            (root / 'profiles').rmdir()
            foreign = root / 'foreign'
            foreign.mkdir()
            (root / 'profiles').symlink_to(foreign, target_is_directory=True)
            self.history(root, 'one', [('other', 'cli', 'Foreign', None, None, 'one', None, 1)])
            self.assertEqual(m.original_evidence('one', root)['status'], 'unavailable')

    def test_filtered_environment(self):
        m = self.load()
        env = m.filtered_env(Path('/home/owner/.hermes'), {'PATH': '/bin', 'HOME': '/foreign', 'OPENAI_API_KEY': 'secret', 'GIT_DIR': '/foreign/git', 'HERMES_PROFILE': 'wrong', 'SSH_AUTH_SOCK': '/sock', 'HTTPS_PROXY': 'http://user:pass@proxy'})
        self.assertEqual(env['HOME'], '/home/owner')
        self.assertEqual(env['HERMES_HOME'], '/home/owner/.hermes')
        for key in ('OPENAI_API_KEY', 'GIT_DIR', 'HERMES_PROFILE', 'SSH_AUTH_SOCK', 'HTTPS_PROXY'):
            self.assertNotIn(key, env)

    def test_every_profile_and_self_no_recursion(self):
        m = self.load()
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            root.mkdir()
            out = root / 'maintenance' / 'feedback'
            with patch.object(m, 'discover', return_value=['default', 'one', 'two']), patch.object(m, 'consult', side_effect=lambda name, *a: {'profile': name, 'status': 'replied', 'reply': 'suggestion'}) as call:
                results = m.run_all(root, out, 'self evidence', 'hermes', 10)
            self.assertEqual({r['profile'] for r in results}, {'default', 'one', 'two'})
            self.assertEqual({c.args[0] for c in call.call_args_list}, {'one', 'two'})
            self.assertTrue(all(r['status'] == 'replied' for r in results))
            self.assertEqual((out / 'index.json').stat().st_mode & 0o777, 0o600)

    def test_timeout_kills_child_tree_and_redacts(self):
        m = self.load()
        import sys
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            marker = Path(d) / 'escaped'
            code = 'import subprocess,time,sys; subprocess.Popen([sys.executable,"-c",' + repr('import time; from pathlib import Path; time.sleep(1); Path(' + repr(str(marker)) + ').touch()') + ']); print("OPENAI_API_KEY=«redacted:sk-…»", flush=True); time.sleep(5)'
            result = m.execute([sys.executable, '-c', code], dict(os.environ), Path(d), .1)
            time.sleep(1.2)
            self.assertFalse(marker.exists())
            self.assertTrue(result['timed_out'])
            self.assertNotIn('«redacted:sk-…»', m.redact(result['stdout']))

    def test_command_is_fresh_narrow_and_bounded(self):
        m = self.load()
        from unittest.mock import patch
        with patch.object(m, 'execute', return_value={'stdout': '{"type":"result","exit_code":0,"text":"feedback"}', 'stderr': '', 'returncode': 0, 'timed_out': False}) as run:
            result = m.consult('one', Path('/home/owner/.hermes'), 'hermes', 12)
        argv = run.call_args.args[0]
        self.assertEqual(argv[:4], ['hermes', '-p', 'one', 'chat'])
        self.assertEqual(argv[argv.index('--toolsets') + 1], 'session_search')
        self.assertEqual(argv[argv.index('--max-turns') + 1], '3')
        self.assertEqual(argv[argv.index('--run-budget') + 1], '12')
        self.assertEqual(result['status'], 'replied')
        self.assertFalse(set(argv) & {'--resume', '--continue', '--yolo', '--accept-hooks', '--ignore-rules'})
        with self.assertRaises(ValueError):
            m.consult('default', Path('/home/owner/.hermes'), 'hermes', 12)

    def test_escaped_json_credentials_are_fully_redacted_in_saved_receipts(self):
        import json
        from unittest.mock import patch
        m = self.load()
        for value in ('prefix\"retained-tail', 'prefix\\retained-tail', 'line\nretained-tail'):
            with self.subTest(value=value), tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
                raw = json.dumps({'password': value, 'note': 'keep'})
                self.assertEqual(json.loads(m.redact(raw)), {'password': '[REDACTED]', 'note': 'keep'})
                event = json.dumps({'type': 'assistant', 'text': raw}) + '\n' + json.dumps(
                    {'type': 'result', 'exit_code': 0, 'text': raw})
                for wrapped in (raw, '```json\n' + raw + '\n```', 'Evidence: ' + raw, json.dumps(raw)):
                    self.assertNotIn('retained-tail', m.redact(wrapped))
                    self.assertNotIn('retained-tail', m.redact(json.dumps({'text': wrapped})))
                with patch.object(m, 'execute', return_value={'stdout': event, 'stderr': raw,
                        'returncode': 0, 'timed_out': False}):
                    result = m.consult('one', Path(d), 'hermes', 10)
                saved = Path(d) / 'receipt.json'
                m.private_json(saved, result)
                self.assertNotIn('retained-tail', saved.read_text())
                self.assertEqual(json.loads(result['receipt']['stderr'])['password'], '[REDACTED]')

    def test_redaction_preserves_json_structure_for_plain_text_secrets(self):
        import json
        m = self.load()
        for text in ('Bearer synthetic-token', 'token=synthetic-token',
                     'https://owner:synthetic-token@example.test/path'):
            with self.subTest(text=text):
                raw = json.dumps({'message': text, 'keep': True})
                sanitized = json.loads(m.redact(raw))
                self.assertTrue(sanitized['keep'])
                self.assertNotIn('synthetic-token', sanitized['message'])
                self.assertEqual(m.redact(m.redact(raw)), m.redact(raw))

    def test_json_secret_redaction_and_private_scope(self):
        m = self.load()
        self.assertNotIn('private-key-value', m.redact('{"api_key": "private-key-value"}'))
        with self.assertRaises(ValueError):
            m.run_all(Path('/home/o/.hermes/profiles/one'), Path('/home/o/.hermes/profiles/one/maintenance/x'), 'self', 'hermes', 10)

    def test_existing_output_refuses_before_contacting_profiles(self):
        m = self.load()
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            output = root / 'maintenance/results'
            output.mkdir(parents=True)
            (output / 'index.json').write_text('{}')
            with patch.object(m, 'discover') as discover:
                with self.assertRaises(ValueError):
                    m.run_all(root, output, 'self', 'hermes', 10)
                discover.assert_not_called()

    def test_overlapping_consultations_are_refused_without_provider_calls(self):
        m = self.load()
        import fcntl
        from unittest.mock import patch
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            maintenance = root / 'maintenance'
            maintenance.mkdir(parents=True)
            with (maintenance / '.profile-consult.lock').open('a') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with patch.object(m, 'discover') as discover:
                    with self.assertRaises(ValueError):
                        m.run_all(root, maintenance / 'results', 'self', 'hermes', 10)
                    discover.assert_not_called()

    def test_native_discovery_and_failure_does_not_skip_remaining(self):
        m = self.load()
        from unittest.mock import patch
        listing = ' Profile  Model\n ◆default         model\n  zed             model\n  alpha           model\n'
        with patch.object(m, 'execute', return_value={'stdout': listing, 'stderr': '', 'returncode': 0, 'timed_out': False}):
            self.assertEqual(m.discover(Path('/home/o/.hermes'), 'hermes'), ['default', 'alpha', 'zed'])
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d) / '.hermes'
            root.mkdir()
            with patch.object(m, 'discover', return_value=['default', 'alpha', 'zed']), patch.object(m, 'consult', side_effect=[RuntimeError('bad target'), {'profile': 'zed', 'status': 'replied', 'reply': 'ok'}]):
                results = m.run_all(root, root / 'maintenance' / 'results', 'self', 'hermes', 10)
            self.assertEqual({r['profile']: r['status'] for r in results}, {'default': 'replied', 'alpha': 'failed', 'zed': 'replied'})

if __name__ == '__main__':
    unittest.main()
