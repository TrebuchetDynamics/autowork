"""No-push service settings against an offline, disposable bare upstream."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class PushSettingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        root = Path(self.tmp.name)
        self.remote, self.repo = root / 'upstream.git', root / 'repo'
        self.git(root, 'init', '--bare', '-q', '-b', 'main', str(self.remote))
        self.git(root, 'init', '-q', '-b', 'main', str(self.repo))
        self.git(self.repo, 'config', 'user.name', 'Test')
        self.git(self.repo, 'config', 'user.email', 'test@example.invalid')
        self.git(self.repo, 'commit', '--allow-empty', '-qm', 'shared baseline')
        self.git(self.repo, 'remote', 'add', 'origin', str(self.remote))
        self.git(self.repo, 'push', '-qu', 'origin', 'main')
        self.remote_before = self.git(self.remote, 'show-ref')
        self.git(self.repo, 'commit', '--allow-empty', '-qm', 'local work to publish')
        self.assertNotEqual(self.git(self.repo, 'rev-parse', 'main'),
                            self.git(self.remote, 'rev-parse', 'main'))
        self.runner = Coordinator.__new__(Coordinator)
        self.runner.repo, self.runner.base = str(self.repo), 'main'
        self.runner.integ, self.runner.seen = None, {}

    def git(self, repo, *args):
        return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True,
                              text=True, timeout=20).stdout.strip()

    def test_push_requires_an_explicit_grant(self):
        env = {k: v for k, v in os.environ.items() if k != 'PI_AUTOWORK_PUSH'}
        for setting in ('0', None):
            with self.subTest(setting=setting), mock.patch.dict(os.environ, env, clear=True):
                if setting is not None:
                    os.environ['PI_AUTOWORK_PUSH'] = setting
                self.runner.push()
                self.assertEqual(self.git(self.remote, 'show-ref'), self.remote_before)

    def test_sync_upstream_requires_an_explicit_grant(self):
        env = {k: v for k, v in os.environ.items() if k != 'PI_AUTOWORK_PUSH'}
        for setting in ('0', None):
            with self.subTest(setting=setting), mock.patch.dict(os.environ, env, clear=True):
                if setting is not None:
                    os.environ['PI_AUTOWORK_PUSH'] = setting
                self.runner.sync_upstream()
                self.assertFalse((self.repo / '.git' / 'FETCH_HEAD').exists())
                self.assertEqual(self.git(self.remote, 'show-ref'), self.remote_before)


if __name__ == '__main__':
    unittest.main()
