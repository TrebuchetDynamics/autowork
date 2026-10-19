"""Chat repository status runs only the existing read-only runner command."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


class RepositoryStatusTests(unittest.TestCase):
    def setUp(self):
        spec = importlib.util.spec_from_file_location('repo_status_bundle', ROOT / 'bundle.py')
        assert spec is not None and spec.loader is not None
        self.bundle = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self.bundle)
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        command = self.root / 'pi-autowork/pi_autowork/command.py'
        command.parent.mkdir(parents=True)
        command.write_text('import json, sys\nprint(json.dumps(sys.argv[1:]))\n')
        setattr(self.bundle, 'ROOT', self.root)

    def test_status_preserves_literal_named_or_absolute_target(self):
        for argument, target in [('ExampleRepo', 'ExampleRepo'),
                                 ('"/example/My Repo; not-a-shell"', '/example/My Repo; not-a-shell')]:
            with self.subTest(argument=argument):
                output = self.bundle.maintenance_reply('STATUS ' + argument)
                self.assertIsNotNone(output)
                self.assertEqual(json.loads(output.splitlines()[1]), ['status', target])

    def test_status_failures_never_look_like_a_successful_empty_fleet(self):
        import subprocess
        import types
        cases = [
            types.SimpleNamespace(returncode=1, stdout='', stderr='no runner named Example'),
            types.SimpleNamespace(returncode=0, stdout='', stderr=''),
            subprocess.TimeoutExpired(['python', 'command.py'], 20),
            OSError('not executable'),
        ]
        for outcome in cases:
            with self.subTest(outcome=type(outcome).__name__):
                effect = outcome if isinstance(outcome, Exception) else None
                value = None if effect is not None else outcome
                with patch.object(self.bundle.subprocess, 'run', side_effect=effect, return_value=value):
                    output = self.bundle.maintenance_reply('status Example')
                self.assertIn('Repository status unavailable', output)
                self.assertNotIn('0 held', output)

    def test_status_rejects_flags_relative_paths_and_bad_quotes_without_execution(self):
        for args in ['status .', 'status ../Repo', 'status --help', "status ''", 'status "unfinished']:
            with self.subTest(args=args), patch.object(self.bundle.subprocess, 'run') as run:
                self.assertIn('Usage:', self.bundle.maintenance_reply(args))
                run.assert_not_called()

    def test_plugin_status_preserves_setup_diagnostics(self):
        with patch.object(self.bundle, 'list_commands', return_value='PLUGIN HEALTH') as inventory, \
                patch.object(self.bundle.subprocess, 'run') as run:
            self.assertEqual(self.bundle.maintenance_reply('plugin status'), 'PLUGIN HEALTH')
        inventory.assert_called_once_with('')
        run.assert_not_called()

    def test_native_text_is_literal_and_bounded_for_gateway_delivery(self):
        import types
        for body in ['Repository: /example/receipt.json\n```inject\nMEDIA:/example/receipt.json', '🙂' * 6000]:
            with self.subTest(large=len(body) > 4000), patch.object(self.bundle.subprocess, 'run',
                    return_value=types.SimpleNamespace(returncode=0, stdout=body, stderr='')):
                output = self.bundle.maintenance_reply('status Example')
            self.assertTrue(output.startswith('```text\n'))
            self.assertEqual(output.count('```'), 2)
            self.assertLessEqual(len(output.encode('utf-16-le')) // 2, 4096)
            if len(body) > 4000:
                self.assertIn('truncated', output.lower())

    def test_status_uses_bundled_reader_not_inherited_older_launcher(self):
        keys = ['PI_AUTOWORK_SCRIPT', 'PI_AUTOWORK_COMPONENT', 'PI_AUTOWORK_TOOLSET',
                'PI_AUTOWORK_PACKAGE', 'PI_AUTOWORK_RESELECT']
        command = self.root / 'pi-autowork/pi_autowork/command.py'
        command.write_text('import json, os\nprint(json.dumps({k: os.environ.get(k) for k in ' + repr(keys) + '}))\n')
        with patch.dict('os.environ', {k: 'older-reader' for k in keys}):
            output = self.bundle.maintenance_reply('status Example')
        actual = json.loads(output.splitlines()[1])
        self.assertEqual(actual, {'PI_AUTOWORK_SCRIPT': str(self.root / 'scripts/pi-autowork.sh'),
                                 'PI_AUTOWORK_COMPONENT': str(self.root / 'pi-autowork'),
                                 'PI_AUTOWORK_TOOLSET': str(self.root),
                                 'PI_AUTOWORK_PACKAGE': str(self.root), 'PI_AUTOWORK_RESELECT': ''})

    def test_named_status_does_not_convert_an_unknown_engine_read_into_zero_workers(self):
        import contextlib
        import io
        import sys
        import types
        with patch.object(sys, 'path', [str(ROOT / 'pi-autowork'), *sys.path]):
            from pi_autowork import cli
        for reply in ['not JSON', '[]', '{"outcome":"BUSY","reason":"writer lock busy"}']:
            with self.subTest(reply=reply), patch.object(cli, 'dirty', return_value=False), \
                    patch.object(cli.subprocess, 'run', return_value=types.SimpleNamespace(stdout=reply)):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    cli.status_view(str(self.root), 'main', str(ROOT), self.root / 'missing-state')
            self.assertIn('Workers:    unavailable', output.getvalue())
            self.assertNotIn('0 running', output.getvalue())

    def test_native_named_status_does_not_check_or_refresh_authentication(self):
        import os
        import subprocess
        import sys
        repo = self.root / 'repo'
        repo.mkdir()
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        (repo / 'TODO.md').write_text('# Fixture backlog\n')
        subprocess.run(['git', '-C', str(repo), 'add', 'TODO.md'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture'], check=True)
        calls = self.root / 'pi-calls.jsonl'
        pi = self.root / 'fake-pi'
        pi.write_text('#!/usr/bin/env python3\nimport json, sys\n'
                      f'with open({str(calls)!r}, "a") as out: out.write(json.dumps(sys.argv[1:])+"\\n")\n'
                      'print("[]")\n')
        pi.chmod(0o755)
        env = {k: v for k, v in os.environ.items() if not k.startswith(('PI_AUTOWORK_', 'GIT_'))}
        env.update(PI_BIN=str(pi), HOME=str(self.root), PI_AUTOWORK_TOOLSET=str(ROOT),
                   PI_AUTOWORK_STATE_DIR=str(self.root / 'state'),
                   PI_AUTOWORK_ENV_DIR=str(self.root / 'settings'),
                   PI_AUTOWORK_HERMES_HOME=str(self.root / 'hermes'),
                   PI_AUTOWORK_PRIMARY='fixture-primary/test-model',
                   PI_AUTOWORK_FALLBACK='fixture-fallback/test-model', PI_AUTOWORK_NO_FALLBACK='0')
        result = subprocess.run([sys.executable, str(ROOT / 'pi-autowork/pi_autowork/cli.py'),
                                 '--repo', str(repo), '--status'], env=env, capture_output=True,
                                text=True, timeout=30)
        self.assertEqual(result.returncode, 0, result.stderr)
        argv = [json.loads(line) for line in calls.read_text().splitlines()]
        self.assertTrue(argv, 'the real native status path must reach the fixture Pi inventory')
        self.assertFalse(any(a[:2] == ['auth', 'check'] for a in argv), argv)
        self.assertIn('fixture-primary/test-model (not checked: read-only status)', result.stdout)
        self.assertIn('fixture-fallback/test-model (not checked: read-only status)', result.stdout)

    def test_status_runs_read_only_fleet_command_not_plugin_inventory(self):
        with patch.object(self.bundle, 'list_commands', return_value='PLUGIN HEALTH') as inventory:
            output = self.bundle.maintenance_reply('status')
        self.assertEqual(output.splitlines()[1], '["ls"]')
        inventory.assert_not_called()
        self.assertIn('/autowork status NAME', output)


if __name__ == '__main__':
    unittest.main()
