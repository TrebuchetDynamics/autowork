"""Opt-in native Pi/Autowork boundary checks, with an offline model/tool double.

AUTOWORK_TEST_PI=/absolute/path/to/pi \
    python3 pi-autowork/tests/test_installed_pi_contract.py -v

Run directly: scripts/check.py intentionally removes AUTOWORK_* environment flags.

No installs, real provider calls, operator configuration or credentials. Ordinary
suite discovery skips these checks unless an executable is explicitly selected.
This qualifies adapter mechanics, not model quality, sandboxing or live recovery.
"""
from concurrent.futures import ThreadPoolExecutor
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import pi_runtime  # noqa: E402

PI = os.environ.get('AUTOWORK_TEST_PI')
PROVIDER = Path(__file__).resolve().parents[1] / 'spikes/runtime-comparison/provider.mjs'


@unittest.skipUnless(PI, 'set AUTOWORK_TEST_PI to explicitly qualify an installed Pi')
class InstalledPiContractTests(unittest.TestCase):
    def setUp(self):
        executable = Path(PI)
        self.assertTrue(executable.is_absolute() and executable.is_file()
                        and os.access(executable, os.X_OK),
                        'AUTOWORK_TEST_PI must name an absolute executable path')
        temporary = tempfile.TemporaryDirectory(prefix='autowork-native-pi-')
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.cwd = self.root / 'workspace'
        self.cwd.mkdir()
        home = self.root / 'home'
        home.mkdir()
        # An allowlist, not an inherited environment with just the known keys removed.
        # --offline prevents catalog refresh, not model calls: the explicit provider
        # below is the repository's deterministic double and never calls a network.
        env = dict(PATH=os.environ['PATH'], HOME=str(home), TMPDIR=str(self.root),
                   XDG_CONFIG_HOME=str(home / 'config'), XDG_CACHE_HOME=str(home / 'cache'),
                   XDG_DATA_HOME=str(home / 'data'), XDG_STATE_HOME=str(home / 'state'),
                   PI_CODING_AGENT_DIR=str(home / 'pi'), PI_OFFLINE='1', PI_TELEMETRY='0')
        isolated = patch.dict(os.environ, env, clear=True)
        isolated.start()
        self.addCleanup(isolated.stop)
        self.version = subprocess.check_output([PI, '--version'], text=True, timeout=15).strip()
        self.assertTrue(self.version, 'Pi did not report its installed version')
        self.settings = pi_runtime.Settings(self.root / 'state', {'PI_BIN': PI, 'PI_AUTOWORK_TRANSPORT': 'json'})
        self.flags = ['--offline', '--no-extensions', '--no-skills', '--no-context-files',
                      '--no-prompt-templates', '--no-themes', '--no-mcp',
                      '--extension', str(PROVIDER), '--tools', 'fixture_safe,fixture_unsafe',
                      '--exclude-tools', 'fixture_unsafe']

    def run_pi(self, operation, session='native-worker-attempt-1'):
        return pi_runtime.run_pi(self.settings, self.cwd,
                                 'FIXTURE_JSON:' + json.dumps(dict(op=operation, safe=True)),
                                 session, 'offline/fixture', 45, self.flags)

    def assert_finished(self, result):
        self.assertEqual((result['rc'], result['settled'], result['aborted'], result['stop']),
                         (0, True, False, 'stop'), (self.version, result))
        self.assertEqual(list((self.settings.state / 'runs').iterdir()), [],
                         'raw event/error files must be removed after analysis')

    def test_agent_end_before_continuation_is_not_terminal_success(self):
        """Catch accepting agent_end before Pi's automatic continuation settles."""
        barrier = self.cwd / '.fixture-before-settle'
        release = self.cwd / '.fixture-settle-release'
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(self.run_pi, 'settle')
            try:
                deadline = time.monotonic() + 30
                while not barrier.exists():
                    if future.done():
                        self.fail(f'Pi {self.version} exited before the barrier: {future.result()}')
                    if time.monotonic() >= deadline:
                        self.fail(f'Pi {self.version} did not reach the settlement barrier')
                    time.sleep(.02)
                self.assertFalse(future.done())
                self.assertEqual((self.cwd / '.fixture-events').read_text().splitlines(), ['agent_end'])
                raw = next(p for p in (self.settings.state / 'runs').iterdir()
                           if not p.name.endswith('.err'))
                partial = raw.read_text()
                events = [json.loads(line) for line in partial.split('\n') if line]
                self.assertIn('tool_execution_end', [e['type'] for e in events])
                self.assertFalse(pi_runtime.analyse(partial)['settled'])
            finally:
                # Always unblock our fixture before joining, including assertion failures.
                release.touch()
            self.assert_finished(future.result(timeout=180))
        self.assertEqual((self.cwd / '.fixture-events').read_text().splitlines(),
                         ['agent_end', 'agent_end', 'agent_settled'])

    def test_resume_retains_context_but_a_review_session_is_fresh(self):
        """Catch loss of same-attempt history, role mixing, or widened tool selection."""
        self.assert_finished(self.run_pi('finish'))
        sessions = self.settings.state / 'sessions'
        (worker_file,) = sessions.glob('*.jsonl')
        original = worker_file.read_bytes()
        self.assert_finished(self.run_pi('finish'))
        self.assertEqual(list(sessions.glob('*.jsonl')), [worker_file])
        self.assertTrue(worker_file.read_bytes().startswith(original))
        resumed = worker_file.read_bytes()
        self.assertGreater(len(resumed), len(original))
        self.assert_finished(self.run_pi('finish', session='native-review-1'))
        self.assertEqual(worker_file.read_bytes(), resumed)
        files = list(sessions.glob('*.jsonl'))
        self.assertEqual(len(files), 2)
        for path in files:
            entries = [json.loads(line) for line in path.read_text().split('\n') if line]
            users = [e for e in entries if e.get('message', {}).get('role') == 'user']
            self.assertEqual(len(users), 2 if path == worker_file else 1)
            tools = {tool['name'] for entry in entries
                     for tool in entry.get('message', {}).get('toolsAdded', [])}
            self.assertEqual(tools, {'fixture_safe'}, 'allowlist + denylist must not load ambient tools')


if __name__ == '__main__':
    unittest.main()
