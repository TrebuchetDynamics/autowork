"""`tx autowork`: pi-autowork runners in tmux, against a private tmux server.

The runner and systemctl are fakes; no Pi, model or real service is involved.
"""
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
TX = ROOT / 'tmux' / 'tx'

RUNNER = '''#!/usr/bin/env bash
printf '%s\\n' "$*" >> "$FAKE_RUNNER_LOG"
trap 'echo interrupted >> "$FAKE_RUNNER_LOG"; exit 130' INT
while :; do sleep 0.1; done
'''
SYSTEMCTL = '''#!/usr/bin/env bash
state=${FAKE_SERVICE_STATE:-none}
case "$2" in
  is-active) [[ $state == active ]] ;;
  is-enabled) [[ $state == active || $state == enabled ]] ;;
  is-failed) echo inactive; exit 1 ;;
  list-units) [[ $state == none ]] || echo "pi-autowork@svc.service loaded active running pi-autowork for svc" ;;
esac
'''


@unittest.skipUnless(shutil.which('tmux'), 'tmux is not installed')
class TxAutoworkTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.base = Path(self.tmp.name).resolve()
        socket = self.base / 'tmux.sock'
        tmux = self.base / 'tmux'
        tmux.write_text(f'#!/bin/sh\nexec tmux -S {socket} -f /dev/null "$@"\n')
        self.addCleanup(subprocess.run, [str(tmux), 'kill-server'], capture_output=True)
        runner, systemctl = self.base / 'pi-autowork.sh', self.base / 'systemctl'
        runner.write_text(RUNNER)
        systemctl.write_text(SYSTEMCTL)
        for path in (tmux, runner, systemctl):
            path.chmod(0o755)
        self.log = self.base / 'runner.log'
        self.log.touch()
        self.repo = self.base / 'my-repo'
        (self.repo / 'sub').mkdir(parents=True)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.env = {k: v for k, v in os.environ.items() if not k.startswith(('TMUX', 'GIT_'))}
        self.env.update(TX_TMUX=str(tmux), PI_AUTOWORK_SCRIPT=str(runner), PI_AUTOWORK_SYSTEMCTL=str(systemctl),
                        FAKE_RUNNER_LOG=str(self.log), TX_NO_ATTACH='1', SHELL='/bin/bash',
                        TX_CONFIG=str(self.base / 'tx.config'), XDG_CONFIG_HOME=str(self.base / 'config'),
                        TX_COLOR='never', TX_AUTOWORK_STOP_TIMEOUT='20')
        self.tmux = tmux

    def tx(self, *args, cwd=None, env=None):
        return subprocess.run(['bash', str(TX), *args], cwd=cwd or self.base, env={**self.env, **(env or {})},
                              capture_output=True, text=True, timeout=60)

    def sessions(self):
        out = subprocess.run([str(self.tmux), 'list-sessions', '-F', '#{session_name}'], capture_output=True, text=True)
        return out.stdout.split()

    def runner_lines(self, count, timeout=10):
        deadline = time.monotonic() + timeout
        while len(self.log.read_text().splitlines()) < count:
            self.assertLess(time.monotonic(), deadline, self.log.read_text())
            time.sleep(0.05)
        return self.log.read_text().splitlines()

    def test_dot_starts_the_repository_runner_in_a_named_session(self):
        result = self.tx('autowork', '.', cwd=self.repo / 'sub')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.sessions(), ['pi-autowork-my-repo'])
        self.assertEqual(self.runner_lines(1), [f'--repo {self.repo}'])
        option = subprocess.run([str(self.tmux), 'show-options', '-qv', '-t', '=pi-autowork-my-repo:', '@pi_autowork_repo'],
                                capture_output=True, text=True).stdout.strip()
        self.assertEqual(option, str(self.repo))
        again = self.tx('autowork', str(self.repo))
        self.assertEqual(again.returncode, 0, again.stderr)
        time.sleep(0.5)
        self.assertEqual(len(self.log.read_text().splitlines()), 1)  # attached, not started twice

    def test_an_enabled_service_owns_the_repository(self):
        for state in ('active', 'enabled'):
            with self.subTest(state=state):
                result = self.tx('autowork', str(self.repo), env={'FAKE_SERVICE_STATE': state})
                self.assertEqual(result.returncode, 1)
                self.assertIn(f'pi-autowork@my-repo.service is {state}', result.stderr)
                self.assertIn('systemctl --user disable --now pi-autowork@my-repo', result.stderr)
                self.assertEqual(self.sessions(), [])

    def test_ls_shows_tmux_runners_and_services(self):
        self.tx('autowork', str(self.repo))
        self.runner_lines(1)
        result = self.tx('autowork', 'ls', env={'FAKE_SERVICE_STATE': 'active'})
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {line.split()[0]: line.split()[1] for line in result.stdout.splitlines()[3:] if line.startswith('  ')}
        self.assertEqual(rows, {'my-repo': 'tmux', 'svc': 'service'})
        self.assertIn('my-repo', result.stdout)
        empty = self.tx('autowork', 'ls', env={'TX_TMUX': '/nonexistent'})
        self.assertIn('(none)', empty.stdout)

    def test_stop_interrupts_the_runner_and_closes_the_session(self):
        self.tx('autowork', str(self.repo))
        self.runner_lines(1)
        result = self.tx('autowork', 'stop', 'my-repo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('interrupted', self.log.read_text())
        self.assertEqual(self.sessions(), [])
        self.assertEqual(self.tx('autowork', 'stop', 'my-repo').returncode, 1)

    def test_the_runner_defaults_to_the_script_the_service_runs(self):
        unit = self.base / 'config' / 'systemd' / 'user' / 'pi-autowork@.service'
        unit.parent.mkdir(parents=True)
        unit.write_text(f'[Service]\nExecStart=/bin/bash {self.env["PI_AUTOWORK_SCRIPT"]} --repo ${{PI_AUTOWORK_REPO}}\n')
        env = dict(self.env)
        env.pop('PI_AUTOWORK_SCRIPT')
        result = subprocess.run(['bash', str(TX), 'autowork', str(self.repo)], env=env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.runner_lines(1), [f'--repo {self.repo}'])

    def test_dotted_repository_names_and_reserved_alias(self):
        dotted = self.base / 'site.io'
        subprocess.run(['git', 'init', '-q', str(dotted)], check=True)
        self.assertEqual(self.tx('autowork', str(dotted)).returncode, 0)
        self.assertEqual(self.sessions(), ['pi-autowork-site_io'])
        self.assertIn('reserved', self.tx('add', 'autowork', str(self.repo)).stderr)
        plain = self.base / 'plain'
        plain.mkdir()
        self.assertIn('not inside a Git repository', self.tx('autowork', str(plain)).stderr)


class TxPackageTests(unittest.TestCase):
    def test_the_package_installs_this_tx(self):
        """pi-toolset's tx is deprecated in favor of this one."""
        package = json.loads((ROOT / 'package.json').read_text())
        self.assertEqual(package['bin'], {'tx': 'tmux/tx'})
        self.assertIn('tmux/', package['files'])
        self.assertTrue(os.access(TX, os.X_OK))
        self.assertIn('tx autowork <repo|.>', subprocess.run(['bash', str(TX), 'help'], capture_output=True,
                                                               text=True).stdout)


if __name__ == '__main__':
    unittest.main()
