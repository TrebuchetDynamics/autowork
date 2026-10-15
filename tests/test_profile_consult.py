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

    def cron_output(self, response='Held at original gate', when='2026-10-14 00:00:00'):
        return ('# Cron Job: Audit\n\n**Job ID:** job\n**Run Time:** ' + when +
                '\n**Schedule:** every 10 minutes\n\n**Prompt Characters:** 5\n## Prompt\n\naudit\n\n' +
                '**Response Characters:** ' + str(len(response)) + '\n## Response\n\n' + response + '\n')

    def reuse_fixture(self, root, name):
        import json
        import sqlite3
        self.history(root, name, [('original', 'cli', 'Project', None, None, name, None, 1)])
        home = root / 'profiles' / name
        (home / 'config.yaml').write_text('model: fixture\n')
        (home / 'autowork').mkdir()
        (home / 'autowork/goal-handoff.json').write_text('{"task_id":"original"}')
        (home / 'cron/output/job').mkdir(parents=True)
        (home / 'cron/output/job/2026-10-14.md').write_text(self.cron_output())
        (home / 'cron/jobs.json').write_text(json.dumps({'jobs': [{'id': 'job', 'enabled': False}]}))
        with sqlite3.connect(home / 'cron/executions.db') as db:
            db.execute('CREATE TABLE executions (id TEXT, job_id TEXT, status TEXT, started_at TEXT, finished_at TEXT, error TEXT)')
            db.execute("INSERT INTO executions VALUES ('run1','job','completed','1','2',NULL)")
        return home

    def fake_transport(self, calls, failed=None):
        def execute(argv, *args):
            if argv[1:3] == ['profile', 'list']:
                return {'stdout': ' ◆default model\n one model\n two model\n',
                        'stderr': '', 'returncode': 0, 'timed_out': False}
            calls.append(argv[2])
            code = 1 if failed and argv[2] in failed else 0
            return {'stdout': '{"type":"result","exit_code":' + str(code) + ',"text":"suggestion"}',
                    'stderr': '', 'returncode': code, 'timed_out': False}
        return execute

    def test_reuse_preserves_coverage_and_current_self_assessment_without_new_calls(self):
        import json
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for name in ('one', 'two'):
                self.reuse_fixture(root, name)
            calls = []
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                m.run_all(root, root / 'maintenance/first', 'first self', 'hermes', 10, reuse_within_seconds=600)
                rows = m.run_all(root, root / 'maintenance/second', 'current self', 'hermes', 10, reuse_within_seconds=600)
            self.assertEqual(sorted(calls), ['one', 'two'])
            self.assertEqual([r['status'] for r in rows], ['replied', 'reused', 'reused'])
            receipt = json.loads((root / 'maintenance/second/one.json').read_text())
            self.assertEqual(receipt['mode'], 'historical-reuse')
            self.assertGreaterEqual(receipt['reuse_age_seconds'], 0)
            self.assertIn('original_reply_at', receipt)
            self.assertEqual(json.loads((root / 'maintenance/second/default.json').read_text())['reply'], 'current self')
            self.assertEqual((root / 'maintenance/.profile-consult-cache.json').stat().st_mode & 0o777, 0o600)

    def test_changed_subject_inputs_only_refresh_that_subject(self):
        import sqlite3
        from unittest.mock import patch
        for change in ('anchor', 'user', 'output', 'handoff', 'config', 'missing'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                m = self.load(); root = Path(d)
                one = self.reuse_fixture(root, 'one'); self.reuse_fixture(root, 'two')
                calls = []
                with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                    m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, reuse_within_seconds=600)
                    if change == 'anchor':
                        with sqlite3.connect(one / 'state.db') as db:
                            db.execute("UPDATE messages SET content='Changed owner reply'")
                    elif change == 'user':
                        with sqlite3.connect(one / 'state.db') as db:
                            db.execute("INSERT INTO messages VALUES (2,'original','user','New direction')")
                    elif change == 'execution':
                        with sqlite3.connect(one / 'cron/executions.db') as db:
                            db.execute("INSERT INTO executions VALUES ('run2','job','completed','3','4',NULL)")
                    else:
                        paths = {'output': 'cron/output/job/2026-10-14.md',
                                 'output_identity': 'cron/output/job/2026-10-15.md',
                                 'handoff': 'autowork/goal-handoff.json', 'config': 'config.yaml',
                                 'missing': 'autowork/goal-handoff.json'}
                        target = one / paths[change]
                        if change == 'missing': target.unlink()
                        else: target.write_text('{}' if change == 'handoff' else 'changed')
                    rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, reuse_within_seconds=600)
                self.assertEqual(calls.count('one'), 2)
                self.assertEqual(calls.count('two'), 1)
                self.assertEqual(rows[2]['status'], 'reused')

    def test_expiry_failure_corruption_and_context_changes_force_fresh(self):
        from unittest.mock import patch
        for change in ('expiry', 'failure', 'corruption', 'context', 'cache_symlink', 'input_symlink'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                m = self.load(); root = Path(d)
                one = self.reuse_fixture(root, 'one'); self.reuse_fixture(root, 'two')
                calls = []; failed = {'one'} if change == 'failure' else set()
                with patch.object(m, 'execute', side_effect=self.fake_transport(calls, failed)):
                    m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                    failed.clear()
                    cache = root / 'maintenance/.profile-consult-cache.json'
                    if change == 'corruption': cache.write_text('{broken')
                    if change == 'context': m.QUESTION += ' Changed question.'
                    if change == 'cache_symlink':
                        foreign = root / 'foreign'; foreign.write_text('private foreign data')
                        cache.unlink(); cache.symlink_to(foreign)
                    if change == 'input_symlink':
                        handoff = one / 'autowork/goal-handoff.json'
                        handoff.unlink(); handoff.symlink_to(root / 'profiles/two/autowork/goal-handoff.json')
                    clock = time.time() + (601 if change == 'expiry' else 0)
                    with patch.object(m.time, 'time', return_value=clock):
                        rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                self.assertEqual(calls, ['one', 'one'])
                self.assertEqual([r['profile'] for r in rows], ['default', 'one'])
                self.assertEqual(rows[1]['status'], 'replied')
                if change == 'cache_symlink': self.assertEqual(foreign.read_text(), 'private foreign data')

    def test_reuse_is_opt_in_and_ttl_is_bounded(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.reuse_fixture(root, 'one'); calls = []
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                for number in range(2):
                    m.run_all(root, root / f'maintenance/{number}', 'self', 'hermes', 10, profiles=['one'])
                for ttl in (-1, 3601):
                    with self.assertRaises(ValueError):
                        m.run_all(root, root / 'maintenance/bad', 'self', 'hermes', 10, reuse_within_seconds=ttl)
            self.assertEqual(calls, ['one', 'one'])

    def test_unsafe_or_unknown_evidence_never_reuses_success(self):
        import sqlite3
        from unittest.mock import patch
        for change in ('oversized_output', 'oversized_anchor', 'failed_execution', 'unreadable', 'raw_secret', 'tools', 'two_searches'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                m = self.load(); root = Path(d); home = self.reuse_fixture(root, 'one'); calls = []
                transport = self.fake_transport(calls)
                def execute(argv, *args):
                    result = transport(argv, *args)
                    if change in ('tools', 'two_searches') and argv[1] == '-p':
                        event = '{"type":"tool_use","name":"' + ('write_file' if change == 'tools' else 'session_search') + '"}\n'
                        result['stdout'] = event * (2 if change == 'two_searches' else 1) + result['stdout']
                    return result
                with patch.object(m, 'execute', side_effect=execute):
                    m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                    if change == 'oversized_output':
                        (home / 'cron/output/job/2026-10-14.md').write_bytes(b'x' * (256 * 1024 + 1))
                    elif change in ('oversized_anchor', 'raw_secret'):
                        with sqlite3.connect(home / 'state.db') as db:
                            value = 'x' * 65537 if change == 'oversized_anchor' else 'password=changed-private-value'
                            db.execute('UPDATE messages SET content=?', (value,))
                    elif change == 'failed_execution':
                        with sqlite3.connect(home / 'cron/executions.db') as db:
                            db.execute("INSERT INTO executions VALUES ('run2','job','failed','3','4','new failure')")
                    elif change == 'unreadable':
                        (home / 'cron/jobs.json').write_text('unreadable schema')
                    rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                self.assertEqual(calls, ['one', 'one'])
                self.assertEqual(rows[1]['status'], 'replied')
                self.assertNotIn('changed-private-value', (root / 'maintenance/.profile-consult-cache.json').read_text())

    def test_default_fresh_failure_invalidates_earlier_cached_success(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.reuse_fixture(root, 'one'); calls = []; failed = set()
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls, failed)):
                m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                failed.add('one')
                m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'])
                failed.clear()
                rows = m.run_all(root, root / 'maintenance/third', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
            self.assertEqual(calls, ['one', 'one', 'one'])
            self.assertEqual(rows[1]['status'], 'replied')

    def test_hits_do_not_extend_original_expiry(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); self.reuse_fixture(root, 'one'); calls = []; start = time.time()
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                for number, offset in enumerate((0, 590, 601)):
                    with patch.object(m.time, 'time', return_value=start + offset):
                        rows = m.run_all(root, root / f'maintenance/{number}', 'self', 'hermes', 10,
                                         profiles=['one'], reuse_within_seconds=600)
                    self.assertEqual(rows[1]['status'], ('replied', 'reused', 'replied')[number])
            self.assertEqual(calls, ['one', 'one'])

    def test_cache_bound_replaces_previous_entries_instead_of_retaining_stale_success(self):
        import json
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / 'cache.json'
            path.write_text('{"version":1,"entries":{"stale":{}}}')
            m.save_cache(path, {str(i): {'reply': 'x' * 65536} for i in range(32)})
            self.assertLessEqual(path.stat().st_size, 1024 * 1024)
            self.assertNotIn('stale', json.loads(path.read_text())['entries'])

    def test_old_anchor_tail_changes_invalidate_even_with_many_newer_user_messages(self):
        import sqlite3
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); home = self.reuse_fixture(root, 'one'); calls = []
            with sqlite3.connect(home / 'state.db') as db:
                db.execute('UPDATE messages SET content=?', ('a' * 2000 + 'original tail',))
                db.executemany("INSERT INTO messages VALUES (?,'original','user','new direction')",
                               [(i,) for i in range(2, 60)])
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                with sqlite3.connect(home / 'state.db') as db:
                    db.execute('UPDATE messages SET content=? WHERE id=1', ('a' * 2000 + 'changed tail',))
                rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
            self.assertEqual(calls, ['one', 'one'])
            self.assertEqual(rows[1]['status'], 'replied')

    def test_corrupt_cache_evidence_or_paths_force_fresh_and_keep_reporting(self):
        import json
        from unittest.mock import patch
        for change in ('error', 'evidence', 'symlink_loop', 'huge_time'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                m = self.load(); root = Path(d); self.reuse_fixture(root, 'one'); calls = []
                with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                    m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                    cache = root / 'maintenance/.profile-consult-cache.json'
                    data = json.loads(cache.read_text())
                    if change == 'symlink_loop':
                        cache.unlink(); cache.symlink_to(cache)
                    else:
                        result = data['entries']['one']['result']
                        if change == 'error': result['error'] = 'unverified transport'
                        elif change == 'huge_time': result['started_at'] = 10 ** 400
                        else: result['original_evidence'] = {'status': 'unavailable'}
                        cache.write_text(json.dumps(data))
                    rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                self.assertEqual(calls, ['one', 'one'])
                self.assertEqual(rows[1]['status'], 'replied')

    def test_new_completed_occurrence_with_identical_response_reuses_advice(self):
        import json
        import sqlite3
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); home = self.reuse_fixture(root, 'one'); calls = []
            jobs = {'jobs': [{'id': 'job', 'enabled': False, 'last_run_at': '1', 'next_run_at': '2',
                              'repeat': {'times': None, 'completed': 1}}]}
            (home / 'cron/jobs.json').write_text(json.dumps(jobs))
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                jobs['jobs'][0].update(last_run_at='3', next_run_at='4', repeat={'times': None, 'completed': 2})
                (home / 'cron/jobs.json').write_text(json.dumps(jobs))
                (home / 'cron/output/job/2026-10-15.md').write_text(self.cron_output(when='2026-10-15 00:00:00'))
                with sqlite3.connect(home / 'cron/executions.db') as db:
                    db.execute("INSERT INTO executions VALUES ('run2','job','completed','3','4',NULL)")
                rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
            self.assertEqual(calls, ['one'])
            self.assertEqual(rows[1]['status'], 'reused')
            receipt = json.loads((root / 'maintenance/second/one.json').read_text())
            self.assertEqual(receipt['reuse_observation']['outputs'][0]['execution_id'], 'run2')
            self.assertEqual(receipt['reuse_observation']['outputs'][0]['filename'], '2026-10-15.md')

    def test_changed_response_error_pause_or_prompt_invalidates_stable_advice(self):
        import json
        import sqlite3
        from unittest.mock import patch
        for change in ('response', 'execution_error', 'job_error', 'pause', 'prompt', 'frame', 'finite_repeat'):
            with self.subTest(change=change), tempfile.TemporaryDirectory() as d:
                m = self.load(); root = Path(d); home = self.reuse_fixture(root, 'one'); calls = []
                if change == 'finite_repeat':
                    (home / 'cron/jobs.json').write_text(json.dumps({'jobs': [{'id': 'job', 'enabled': False, 'repeat': {'times': 3, 'completed': 2}}]}))
                with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                    m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                    if change in ('response', 'frame'):
                        data = self.cron_output('new problem') if change == 'response' else self.cron_output().replace('Response Characters:** 21', 'Response Characters:** 999')
                        (home / 'cron/output/job/2026-10-14.md').write_text(data)
                    elif change == 'execution_error':
                        with sqlite3.connect(home / 'cron/executions.db') as db:
                            db.execute("UPDATE executions SET error='unknown delivery error'")
                    else:
                        job = {'id': 'job', 'enabled': False}
                        job.update({'job_error': {'last_delivery_error': 'failed'}, 'pause': {'enabled': True},
                                    'prompt': {'prompt': 'new task'},
                                    'finite_repeat': {'repeat': {'times': 3, 'completed': 3}}}[change])
                        (home / 'cron/jobs.json').write_text(json.dumps({'jobs': [job]}))
                    rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                self.assertEqual(calls, ['one', 'one'])
                self.assertEqual(rows[1]['status'], 'replied')

    def test_opt_in_unknown_original_evidence_does_not_launch_empty_consultation(self):
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); calls = []
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                rows = m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10,
                                 profiles=['one'], reuse_within_seconds=600)
            self.assertEqual(calls, [])
            self.assertEqual(rows[1]['status'], 'unavailable')
            import json
            receipt = json.loads((root / 'maintenance/first/one.json').read_text())
            self.assertEqual(receipt['mode'], 'not-consulted')
            self.assertNotIn('reply', receipt)

    def test_unchanged_failed_occurrence_can_reuse_successful_advice(self):
        import sqlite3
        from unittest.mock import patch
        m = self.load()
        with tempfile.TemporaryDirectory() as d:
            root = Path(d); home = self.reuse_fixture(root, 'one'); calls = []
            with sqlite3.connect(home / 'cron/executions.db') as db:
                db.execute("UPDATE executions SET status='failed', error='same gate'")
            with patch.object(m, 'execute', side_effect=self.fake_transport(calls)):
                m.run_all(root, root / 'maintenance/first', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
                with sqlite3.connect(home / 'cron/executions.db') as db:
                    db.execute("INSERT INTO executions VALUES ('run2','job','failed','3','4','same gate')")
                rows = m.run_all(root, root / 'maintenance/second', 'self', 'hermes', 10, profiles=['one'], reuse_within_seconds=600)
            self.assertEqual(calls, ['one'])
            self.assertEqual(rows[1]['status'], 'reused')

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
            self.assertEqual(db.read_bytes(), before)
            self.assertEqual(evidence['anchor_excerpt'], 'owner-private-content')
            self.assertFalse(evidence['anchor_truncated'])
            with sqlite3.connect(db) as connection:
                connection.execute('UPDATE messages SET content=? WHERE id=3',
                                   ('token=private-value ' + 'x' * 3000,))
            bounded = m.original_evidence('one', root)
            self.assertNotIn('private-value', bounded['anchor_excerpt'])
            self.assertLessEqual(len(bounded['anchor_excerpt']), 2000)
            self.assertTrue(bounded['anchor_truncated'])
            import json
            for content, omitted in [
                    (json.dumps({'password': 'prefix ' + 'LEAK_MARKER ' * 300}), False),
                    ('x' * 1975 + ' token=a END_MARKER', True),
                    ('x' * 65537, True),
                    ('prefix\x00' + 'x' * 65537, True),
                    ('é' * 40000, True)]:
                with sqlite3.connect(db) as connection:
                    connection.execute('UPDATE messages SET content=? WHERE id=3', (content,))
                actual = m.original_evidence('one', root)
                self.assertNotIn('LEAK_MARKER', actual['anchor_excerpt'])
                self.assertLessEqual(len(actual['anchor_excerpt']), 2000)
                if omitted:
                    self.assertTrue(actual['anchor_truncated'])
                if len(content.encode()) > 65536:
                    self.assertEqual(actual['anchor_excerpt'], '')
            with sqlite3.connect(db) as connection:
                connection.execute('UPDATE messages SET content=? WHERE id=3', ('owner-private-content',))
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

    def test_metadata_is_redacted_before_truncation(self):
        import json
        m = self.load()
        with tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
            root = Path(d)
            secret = 'prefix ' + 'LEAK_MARKER ' * 40
            metadata = json.dumps({'password': secret, 'keep': True})
            self.history(root, 'one', [('a', 'cli', metadata, metadata, metadata,
                                       'one', None, 1)])
            result = m.original_evidence('one', root)
            self.assertNotIn('LEAK_MARKER', str(result))
            for field in ('title', 'cwd', 'git_repo_root'):
                self.assertEqual(json.loads(result[field]),
                                 {'password': '[REDACTED]', 'keep': True})
            import sqlite3
            with sqlite3.connect(root / 'profiles/one/state.db') as db:
                db.execute('UPDATE sessions SET title=?', ('prefix\x00' + 'x' * 65537,))
            self.assertEqual(m.original_evidence('one', root)['title'], '')
            with sqlite3.connect(root / 'profiles/one/state.db') as db:
                db.execute('UPDATE sessions SET title=NULL, cwd=NULL, git_repo_root=NULL')
            result = m.original_evidence('one', root)
            for field in ('title', 'cwd', 'git_repo_root'):
                self.assertIsNone(result[field])

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

    def test_bare_github_tokens_are_redacted_through_saved_consult_receipts(self):
        import json
        import sqlite3
        from unittest.mock import patch
        m = self.load()
        tokens = [prefix + 'SYNTHETIC_MARKER' for prefix in
                  ('ghp_', 'gho_', 'ghu_', 'ghs_', 'ghr_', 'github_pat_')]
        tokens.append('ghs_SYNTHETIC_HEADER.SYNTHETIC_PAYLOAD.SYNTHETIC_SIGNATURE')
        for token in tokens:
            with self.subTest(token=token), tempfile.TemporaryDirectory(dir=os.environ.get('TMPDIR')) as d:
                text = 'before (' + token + ') after'
                expected = 'before ([REDACTED]) after'
                nested = {'items': [text, {'message': token}], 'keep': True}
                sanitized = {'items': [expected, {'message': '[REDACTED]'}], 'keep': True}
                self.assertEqual(m.redact(text), expected)
                self.assertEqual(json.loads(m.redact(json.dumps(nested))), sanitized)
                self.assertEqual(m.redact(m.redact(text)), expected)
                root = Path(d)
                db = self.history(root, 'one', [('original', 'cli', text, text, text,
                                                'one', None, 1)])
                with sqlite3.connect(db) as connection:
                    connection.execute('UPDATE messages SET content=?', (json.dumps(nested),))
                connection.close()
                before = db.read_bytes()
                evidence = m.original_evidence('one', root)
                self.assertEqual(json.loads(evidence['anchor_excerpt']), sanitized)
                for field in ('title', 'cwd', 'git_repo_root'):
                    self.assertEqual(evidence[field], expected)
                self.assertEqual(db.read_bytes(), before)
                event = json.dumps({'type': 'result', 'exit_code': 0, 'text': text,
                                    'details': nested})
                with patch.object(m, 'execute', return_value={'stdout': event, 'stderr': text,
                        'returncode': 0, 'timed_out': False}) as run:
                    result = m.consult('one', root, 'offline-fixture', 10)
                run.assert_called_once()
                self.assertNotIn(token, run.call_args.args[0][-1])
                self.assertEqual(result['status'], 'replied')
                self.assertEqual(result['original_evidence'], evidence)
                self.assertEqual(result['reply'], expected)
                self.assertEqual(result['receipt']['stderr'], expected)
                self.assertEqual(json.loads(result['receipt']['stdout'])['details'], sanitized)
                saved = root / 'receipt.json'
                m.private_json(saved, result)
                self.assertEqual(json.loads(saved.read_text()), result)
                self.assertNotIn('SYNTHETIC_', saved.read_text())
                self.assertEqual(saved.stat().st_mode & 0o777, 0o600)
        for prefix in ('sk-', 'ghp-', 'gho-', 'xoxb-', 'xoxp-'):
            with self.subTest(legacy=prefix):
                self.assertEqual(m.redact(prefix + 'SYNTHETIC_MARKER'), '[REDACTED]')
        self.assertEqual(m.redact('ghp_ ghs_ github_pat_ ordinary_text'),
                         'ghp_ ghs_ github_pat_ ordinary_text')

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

    def test_quoted_assignment_credentials_are_redacted_in_full(self):
        import json
        m = self.load()
        for text in ('password="prefix LEAK_MARKER tail" keep',
                     "secret='prefix LEAK_MARKER tail' keep",
                     'authorization="prefix \\" LEAK_MARKER tail" keep',
                     'token="prefix\nLEAK_MARKER tail" keep',
                     'password="prefix\\\nLEAK_MARKER tail" keep',
                     "secret='prefix\\\nLEAK_MARKER tail' keep"):
            for wrapped in (text, json.dumps({'text': text, 'keep': True})):
                with self.subTest(wrapped=wrapped):
                    sanitized = m.redact(wrapped)
                    self.assertNotIn('LEAK_MARKER', sanitized)
                    self.assertIn('keep', sanitized)
                    self.assertEqual(m.redact(sanitized), sanitized)

    def test_unterminated_quoted_credentials_fail_closed(self):
        import json
        m = self.load()
        for text in ('password="prefix LEAK_MARKER tail',
                     "secret='prefix LEAK_MARKER tail",
                     'token="prefix\\\nLEAK_MARKER tail',
                     'authorization="prefix LEAK_MARKER tail\\',
                     '{"password": "prefix LEAK_MARKER tail',
                     "{'secret': 'prefix LEAK_MARKER tail",
                     '{"token": "prefix LEAK_MARKER tail\\'):
            for wrapped in (text, json.dumps({'text': text, 'keep': True})):
                with self.subTest(wrapped=wrapped):
                    sanitized = m.redact(wrapped)
                    self.assertNotIn('LEAK_MARKER', sanitized)
                    self.assertEqual(m.redact(sanitized), sanitized)
                    if wrapped != text:
                        self.assertTrue(json.loads(sanitized)['keep'])

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

    def test_native_discovery_includes_long_profile_with_single_space(self):
        from unittest.mock import patch
        m = self.load()
        listing = (' ◆default         gpt-6.1-sol                  running      —            —\n'
                   '  example-long-profile-xyz gpt-6.1-sol                  running      example-long-profile-xyz —\n')
        with patch.object(m, 'execute', return_value={'stdout': listing, 'stderr': '', 'returncode': 0, 'timed_out': False}):
            self.assertEqual(m.discover(Path('/home/o/.hermes'), 'hermes'),
                             ['default', 'example-long-profile-xyz'])

    def test_native_discovery_refuses_malformed_output(self):
        from unittest.mock import patch
        m = self.load()
        for listing in ('garbage', '  named model\n', ' ◆default model\n ◆default model\n',
                        ' ◆Default model\n', ' ◆' + 'a' * 65 + ' model\n'):
            with self.subTest(listing=listing), patch.object(m, 'execute', return_value={
                    'stdout': listing, 'stderr': '', 'returncode': 0, 'timed_out': False}):
                with self.assertRaises(RuntimeError):
                    m.discover(Path('/home/o/.hermes'), 'hermes')

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
