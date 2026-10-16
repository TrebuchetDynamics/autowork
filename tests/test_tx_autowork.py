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
if [[ " $* " == *" --status "* ]]; then echo "STATUS $*"; exit 0; fi
echo "runner output for $*"
trap 'echo interrupted >> "$FAKE_RUNNER_LOG"; exit 130' INT
while :; do sleep 0.1; done
'''
SYSTEMCTL = '''#!/usr/bin/env bash
state=${FAKE_SERVICE_STATE:-none}
case "$2" in
  is-active) [[ $state == active ]] ;;
  is-enabled) [[ $state == active || $state == enabled ]] ;;
  is-failed) echo inactive; exit 1 ;;
  list-units) [[ $state == none ]] || echo "pi-autowork@${FAKE_SERVICE_NAME:-svc}.service loaded active running pi-autowork" ;;
esac
'''
JOURNALCTL = '''#!/usr/bin/env bash
echo "journal $*"
if [[ " $* " == *" -f "* ]]; then sleep "${FAKE_JOURNAL_FOLLOW:-60}"; fi
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
        runner, systemctl, journal = self.base / 'pi-autowork.sh', self.base / 'systemctl', self.base / 'journalctl'
        runner.write_text(RUNNER)
        systemctl.write_text(SYSTEMCTL)
        journal.write_text(JOURNALCTL)
        for path in (tmux, runner, systemctl, journal):
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
                        TX_COLOR='never', TX_AUTOWORK_STOP_TIMEOUT='20', TX_JOURNALCTL=str(journal),
                        PI_AUTOWORK_STATE_DIR=str(self.base / 'state'))
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

    def option(self, name):
        return subprocess.run([str(self.tmux), 'show-options', '-qv', '-t', '=pi-autowork-my-repo:', name],
                              capture_output=True, text=True).stdout.strip()

    def pane(self):
        return subprocess.run([str(self.tmux), 'capture-pane', '-p', '-t', '=pi-autowork-my-repo:'],
                              capture_output=True, text=True).stdout

    def test_a_service_runner_gets_a_session_that_follows_its_journal(self):
        for state in ('active', 'enabled'):
            with self.subTest(state=state):
                service = {'FAKE_SERVICE_STATE': state}
                result = self.tx('autowork', str(self.repo), env=service)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('follows pi-autowork@my-repo.service', result.stderr)
                self.assertEqual((self.sessions(), self.option('@pi_autowork_mode')), (['pi-autowork-my-repo'], 'journal'))
                deadline = time.monotonic() + 10
                while 'journal --user -u pi-autowork@my-repo.service -n 200 -f -o cat' not in self.pane():
                    self.assertLess(time.monotonic(), deadline, self.pane())
                    time.sleep(0.05)
                self.assertEqual(self.log.read_text(), '')  # no second runner beside the service
                closed = self.tx('autowork', 'stop', 'my-repo', env=service)
                self.assertIn('pi-autowork@my-repo.service keeps running', closed.stderr)
                self.assertEqual(self.sessions(), [])

    def test_a_journal_view_becomes_a_runner_once_the_service_is_gone(self):
        self.tx('autowork', str(self.repo), env={'FAKE_SERVICE_STATE': 'active'})
        result = self.tx('autowork', str(self.repo))
        self.assertIn('replacing the journal view with a runner', result.stderr)
        self.assertEqual(self.runner_lines(1), [f'--repo {self.repo}'])
        self.assertEqual(self.option('@pi_autowork_mode'), 'runner')

    def test_tx_session_name_opens_the_runner(self):
        result = self.tx('pi-autowork-my-repo', cwd=self.repo)  # unknown name, no repository yet
        self.assertIn('no runner named my-repo', result.stderr)
        self.service_env('my-repo')
        result = self.tx('pi-autowork-my-repo')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.runner_lines(1), [f'--repo {self.repo}'])
        (self.base / 'tx.config').write_text(f'pi-autowork-alias={self.base}\n')
        aliased = self.tx('pi-autowork-alias')  # an alias of that name still wins
        self.assertNotIn('no runner named', aliased.stderr)

    def test_ls_shows_tmux_runners_and_services(self):
        self.tx('autowork', str(self.repo))
        self.runner_lines(1)
        result = self.tx('autowork', 'ls', '--brief', env={'FAKE_SERVICE_STATE': 'active'})
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = {line.split()[0]: line.split()[1] for line in result.stdout.splitlines()[1:]}
        self.assertEqual(rows, {'my-repo': 'tmux', 'svc': 'service'})
        self.assertIn('pi-autowork runners: 2 (2 unknown)', result.stdout)
        full = self.tx('autowork', 'ls', env={'FAKE_SERVICE_STATE': 'active'}).stdout
        self.assertIn('my-repo  tmux  unknown\n  tx pi-autowork-my-repo  no status yet\n', full)
        self.assertNotIn(str(self.repo), full)  # names, not paths
        empty = self.tx('autowork', 'ls', env={'TX_TMUX': '/nonexistent'})
        self.assertIn('pi-autowork runners: none', empty.stdout)

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

    def service_env(self, name='svc', repo=None):
        env_dir = self.base / 'config' / 'pi-autowork'
        env_dir.mkdir(parents=True, exist_ok=True)
        (env_dir / f'{name}.env').write_text(f'PI_AUTOWORK_REPO={repo or self.repo}\n')

    def test_a_runner_name_finds_its_repository(self):
        self.service_env('svc')  # a service's name resolves through its settings file
        viewed = self.tx('autowork', 'svc', env={'FAKE_SERVICE_STATE': 'active'})
        self.assertIn('pi-autowork-my-repo follows pi-autowork@my-repo.service', viewed.stderr)
        self.tx('autowork', 'stop', 'my-repo', env={'FAKE_SERVICE_STATE': 'active'})
        self.tx('autowork', str(self.repo))
        self.runner_lines(1)
        status = self.tx('autowork', 'status', 'my-repo')  # a tmux session's name, too
        self.assertEqual(status.returncode, 0, status.stderr)
        self.assertEqual(status.stdout.strip(), f'STATUS --repo {self.repo} --status')
        self.assertIn('no runner named nothing', self.tx('autowork', 'status', 'nothing').stderr)

    def test_status_defaults_to_the_current_repository(self):
        status = self.tx('autowork', 'status', cwd=self.repo / 'sub')
        self.assertEqual(status.stdout.strip(), f'STATUS --repo {self.repo} --status')

    def test_logs_read_the_tmux_pane_or_the_service_journal(self):
        self.tx('autowork', str(self.repo))
        self.runner_lines(1)
        deadline = time.monotonic() + 10
        while 'runner output' not in self.tx('autowork', 'logs', 'my-repo').stdout:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.1)
        self.tx('autowork', 'stop', 'my-repo')
        self.service_env('my-repo')
        journal = self.tx('autowork', 'logs', 'my-repo', env={'FAKE_SERVICE_STATE': 'active'})
        self.assertEqual(journal.stdout.strip(), 'journal --user -u pi-autowork@my-repo.service -n 200 --no-pager -o cat')
        follow = self.tx('autowork', 'logs', '-f', str(self.repo), env={'FAKE_SERVICE_STATE': 'active', 'FAKE_JOURNAL_FOLLOW': '0'})
        self.assertIn('-f -o cat', follow.stdout)
        self.assertIn('no tmux session or service', self.tx('autowork', 'logs', str(self.repo)).stderr)

    def test_ls_shows_health_from_the_runner_status(self):
        state = self.base / 'state' / 'key'
        state.mkdir(parents=True)
        (state / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': str(self.repo)}))
        (state / 'status.json').write_text(json.dumps({'state': 'working', 'since': time.time() - 300,
                                                       'active_workers': 2, 'waiting': 5}))
        self.service_env('my-repo')
        service = {'FAKE_SERVICE_STATE': 'active', 'FAKE_SERVICE_NAME': 'my-repo'}
        listing = self.tx('autowork', 'ls', env=service).stdout
        self.assertIn('pi-autowork runners: 1 (1 working)', listing)
        self.assertRegex(listing, r'my-repo  service  working [45]m\n  tx pi-autowork-my-repo  2 running, 5 waiting\n')
        self.assertRegex(self.tx('autowork', 'ls', '--brief', env=service).stdout,
                         r'my-repo\s+service\s+working [45]m\s+2 running, 5 waiting')
        status = json.loads((state / 'status.json').read_text())
        (state / 'status.json').write_text(json.dumps(dict(status, since=time.time() - 280 * 60 - 5)))
        self.assertIn('working 4h40m', self.tx('autowork', 'ls', env=service).stdout)
        (state / 'runner.json').write_text(json.dumps({'pid': 999999999, 'repo': str(self.repo)}))
        self.assertIn('not running\n  tx pi-autowork-my-repo  2 running, 5 waiting', self.tx('autowork', 'ls', env=service).stdout)
        self.tx('autowork', 'my-repo', env=service)  # its journal view is not a second runner
        self.assertIn('pi-autowork runners: 1 ', self.tx('autowork', 'ls', env=service).stdout)
        unknown = self.tx('autowork', 'ls', env={'FAKE_SERVICE_STATE': 'active', 'FAKE_SERVICE_NAME': 'other'})
        self.assertEqual(unknown.returncode, 0, unknown.stderr)  # a service without settings has no status
        self.assertIn('other  service  unknown\n  tx pi-autowork-other  no status yet', unknown.stdout)

    def test_ls_says_what_blocks_a_stalled_runner_and_lists_held_tasks(self):
        state = self.base / 'state' / 'key'
        state.mkdir(parents=True)
        (state / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': str(self.repo)}))
        roots = [{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19, 'reason': ''},
                 {'id': 'approved physical target and capture consent; preparation proceeds',
                  'kind': 'outside', 'blocks': 2, 'reason': ''},
                 {'id': 'T-9', 'kind': 'held', 'blocks': 2, 'cause': 'blocker',
                  'reason': 'worker reported a blocker: needs a key'},
                 {'id': 'T-7', 'kind': 'claim', 'blocks': 13, 'reason': 'sequential task in progress'},
                 {'id': 'T-1', 'kind': 'running', 'blocks': 4, 'reason': ''}]
        status = {'state': 'stalled', 'since': time.time() - 600, 'waiting': 23, 'roots': roots,
                  'held': [{'task': 'T-9', 'cause': 'blocker'}]}
        (state / 'status.json').write_text(json.dumps(status))
        service = {'FAKE_SERVICE_STATE': 'active', 'FAKE_SERVICE_NAME': 'my-repo', 'COLUMNS': '200'}
        self.service_env('my-repo')
        listing = self.tx('autowork', 'ls', env=service).stdout
        self.assertIn('  tx pi-autowork-my-repo  0 running, 23 waiting, 1 held\n', listing)
        blockers = listing.split('1 held\n', 1)[1].split('\n\n')[0].splitlines()
        self.assertEqual(blockers, ['  held: T-9 blocker (2)', '  claimed elsewhere: T-7 (13)',
                                    '  outside Now/Next: TASK-036 (19), approved physical target and... (2)'])
        self.assertNotIn('T-1 ', listing)  # moving work is not a blocker
        self.assertIn('(n) = waiting tasks that depend on it', listing)
        narrow = self.tx('autowork', 'ls', env={**service, 'COLUMNS': '40'}).stdout
        self.assertTrue(all(len(line) <= 40 for line in narrow.splitlines()[:-1]), narrow)
        status.update(state='working', active_workers=1)
        (state / 'status.json').write_text(json.dumps(status))
        self.assertIn('  held: T-9 blocker\n', self.tx('autowork', 'ls', env=service).stdout)

    def test_stop_points_a_service_runner_to_systemctl(self):
        self.service_env('my-repo')
        refused = self.tx('autowork', 'stop', 'my-repo', env={'FAKE_SERVICE_STATE': 'active'})
        self.assertIn('systemctl --user stop pi-autowork@my-repo', refused.stderr)


class TxPackageTests(unittest.TestCase):
    def test_the_package_installs_this_tx(self):
        """pi-toolset's tx is deprecated in favor of this one."""
        package = json.loads((ROOT / 'package.json').read_text())
        self.assertEqual(package['bin'], {'tx': 'tmux/tx'})
        self.assertIn('tmux/', package['files'])
        self.assertTrue(os.access(TX, os.X_OK))
        self.assertIn('tx pi-autowork-<name>', subprocess.run(['bash', str(TX), 'help'], capture_output=True,
                                                               text=True).stdout)


if __name__ == '__main__':
    unittest.main()
