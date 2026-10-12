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
            self.assertEqual({r['profile'] for r in rows}, {'default', 'one', 'two'})

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
