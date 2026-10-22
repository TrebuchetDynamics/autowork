"""Public setup and consumer seams with disposable config and a health-only proxy."""
import http.server
import json
import os
from pathlib import Path
import sys
import tempfile
import threading
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import portal, pi_runtime  # noqa: E402


class PortalTests(unittest.TestCase):
    def test_health_only_preflight_has_actionable_errors_and_no_authentication(self):
        health = {'status': 'ok', 'upstream': 'Nous Portal', 'authenticated': True}
        requests = []

        class Handler(http.server.BaseHTTPRequestHandler):
            def do_GET(self):
                requests.append((self.path, self.headers.get('Authorization')))
                self.send_response(200)
                self.end_headers()
                self.wfile.write(json.dumps(health).encode())

            def log_message(self, *args):
                pass

        port = int(os.environ.get('AUTOWORK_PORT_BASE', '20700')) + 2
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=folder):
            server = http.server.HTTPServer(('127.0.0.1', port), Handler)
            self.addCleanup(server.server_close)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            endpoint = f'http://127.0.0.1:{port}/v1'
            try:
                proposal = portal.propose('nous-selected', 'example', endpoint)
                portal.apply(proposal)
                self.assertEqual(proposal.proxy['state'], 'available')
                portal.check_model('nous-selected/example')
                health['authenticated'] = False
                self.assertEqual(portal.probe(endpoint)['state'], 'login_required')
                settings = pi_runtime.Settings(folder, {'PI_AUTOWORK_PRIMARY': 'nous-selected/example',
                                                       'PI_AUTOWORK_NO_FALLBACK': '1'})
                with mock.patch.object(pi_runtime, 'auth_ready', side_effect=AssertionError('Must not authenticate')):
                    chosen, reason = pi_runtime.choose(settings)
                self.assertIsNone(chosen)
                self.assertIn('hermes portal', reason)
                settings.fallback_enabled = True
                settings.fallback = 'ordinary/fallback'
                with mock.patch.object(pi_runtime, 'auth_ready', return_value=True):
                    self.assertEqual(pi_runtime.choose(settings)[0], 'ordinary/fallback')
                health.update(upstream='other', authenticated=True)
                self.assertEqual(portal.probe(endpoint)['state'], 'incompatible')
            finally:
                server.shutdown()
                server.server_close()
            self.assertEqual(portal.probe(endpoint)['state'], 'unavailable')
            with self.assertRaisesRegex(portal.SetupError, 'Proxy unavailable'):
                portal.check_model('nous-selected/example')
            self.assertEqual(set(requests), {('/health', None)})
            for bad in ('http://example.invalid:80/v1', 'http://127.0.0.1:8645/v1?token=SECRET',
                        'http://user:SECRET@127.0.0.1:8645/v1', 'http://localhost:8645/v1'):
                with self.subTest(endpoint=bad), self.assertRaises(portal.SetupError):
                    portal.propose('nous-selected', 'example', bad)

    def test_read_only_preflight_preserves_unrelated_symlinked_configuration(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=folder):
            source = Path(folder) / 'shared.json'
            original = b'{"providers":{"ordinary":{"apiKey":"not-a-portal-key"}}}\n'
            source.write_bytes(original)
            path = Path(folder) / 'models.json'
            path.symlink_to(source)
            portal.check_model('ordinary/example')
            self.assertTrue(path.is_symlink())
            self.assertEqual(source.read_bytes(), original)
            with self.assertRaisesRegex(portal.SetupError, 'symlink'):
                portal.propose('nous', 'example')

    def test_model_overrides_cannot_bypass_the_selected_proxy(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=folder), \
                mock.patch.object(portal, 'probe', return_value={'state': 'available', 'message': 'offline stub'}):
            path = Path(folder) / 'models.json'
            for override in ({'baseUrl': 'https://example.invalid/v1'}, {'api': 'anthropic-messages'},
                             {'headers': {'Authorization': '!secret-command'}}, {'maxTokens': -1}):
                with self.subTest(override=override):
                    entry = {'baseUrl': portal.DEFAULT_ENDPOINT, 'api': 'openai-completions',
                             'apiKey': portal.PLACEHOLDER, 'models': [{'id': 'example', **override}]}
                    original = json.dumps({'providers': {'nous-selected': entry}}).encode()
                    path.write_bytes(original)
                    with self.assertRaises(portal.SetupError):
                        portal.propose('nous-selected', 'example')
                    settings = pi_runtime.Settings(folder, {'PI_AUTOWORK_PRIMARY': 'nous-selected/example',
                                                           'PI_AUTOWORK_NO_FALLBACK': '1'})
                    with mock.patch.object(pi_runtime, 'auth_ready', side_effect=AssertionError('Must not authenticate')):
                        chosen, reason = pi_runtime.choose(settings)
                    self.assertIsNone(chosen)
                    self.assertIn('model', reason.lower())
                    self.assertEqual(path.read_bytes(), original)

    def test_changed_proposal_and_failed_replace_leave_config_intact(self):
        with tempfile.TemporaryDirectory() as folder, mock.patch.dict(os.environ, PI_CODING_AGENT_DIR=folder), \
                mock.patch.object(portal, 'probe', return_value={'state': 'unavailable', 'message': 'offline'}):
            path = Path(folder) / 'models.json'
            path.write_text('{"providers":{}}\n')
            proposal = portal.propose('nous', 'example')
            changed = b'{"providers":{},"concurrent":"edit"}\n'
            path.write_bytes(changed)
            with self.assertRaisesRegex(portal.SetupError, 'changed since proposal'):
                portal.apply(proposal)
            self.assertEqual(path.read_bytes(), changed)
            proposal = portal.propose('nous', 'example')
            with mock.patch.object(portal.os, 'replace', side_effect=OSError('disk full')):
                with self.assertRaisesRegex(portal.SetupError, 'atomically'):
                    portal.apply(proposal)
            self.assertEqual(path.read_bytes(), changed)
            self.assertEqual(sorted(p.name for p in path.parent.iterdir()), ['.autowork-models.lock', 'models.json'])
