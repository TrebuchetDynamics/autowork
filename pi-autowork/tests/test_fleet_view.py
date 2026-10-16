"""fleet_view: runners from tmux, systemd and status.json; blockers; actions. Fakes only."""
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import textwrap
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view  # noqa: E402

PILOT = Path(__file__).with_name('tui_pilot.py')


class FleetViewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.state, self.env = self.base / 'state', self.base / 'env'
        self.env.mkdir()
        self.tmux = self.fake('tmux', 'printf "%s" "${FAKE_TMUX_SESSIONS:-}"')
        self.systemctl = self.fake('systemctl', 'printf "%s" "${FAKE_UNITS:-}"')

    def fake(self, name, body):
        path = self.base / name
        path.write_text('#!/usr/bin/env bash\n' + body + '\n')
        path.chmod(0o755)
        return str(path)

    def runner_state(self, repo, **status):
        folder = self.state / Path(repo).name
        folder.mkdir(parents=True)
        (folder / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': repo}))
        (folder / 'status.json').write_text(json.dumps({'repo': repo, 'updated_at': time.time(), **status}))

    def collect(self, sessions='', units=''):
        os.environ['FAKE_TMUX_SESSIONS'], os.environ['FAKE_UNITS'] = sessions, units
        self.addCleanup(os.environ.pop, 'FAKE_TMUX_SESSIONS', None)
        self.addCleanup(os.environ.pop, 'FAKE_UNITS', None)
        return {r.name: r for r in fleet_view.collect(self.state, self.env, tmux=self.tmux, systemctl=self.systemctl)}

    def test_merges_tmux_sessions_services_and_runner_state(self):
        self.runner_state('/git/india', state='stalled', since=time.time() - 341 * 60, waiting=23,
                          roots=[{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19},
                                 {'id': 'T-1', 'kind': 'running', 'blocks': 4}])
        self.runner_state('/git/sierra', state='working', since=time.time() - 600, active_workers=1, waiting=40,
                          held=[{'task': 'TASK-023', 'cause': 'blocker'}],
                          roots=[{'id': 'TASK-023', 'kind': 'held', 'cause': 'blocker', 'blocks': 2}])
        (self.env / 'sierra.env').write_text('PI_AUTOWORK_REPO=/git/sierra\n')
        found = self.collect(sessions='pi-autowork-india\t/git/india\trunner\nother\t\t\npi-autowork-sierra\t/git/sierra\tjournal\n',
                             units='pi-autowork@sierra.service loaded active running pi-autowork for sierra\n')
        self.assertEqual(sorted(found), ['india', 'sierra'])
        india, sierra = found['india'], found['sierra']
        self.assertEqual((india.mode, india.state, fleet_view.duration(india.minutes), india.waiting), ('tmux', 'stalled', '5h41m', 23))
        self.assertEqual(fleet_view.blockers(india), [('outside Now/Next', 'TASK-036 (19)')])  # moving work is not a blocker
        self.assertEqual((sierra.mode, sierra.service, sierra.view, sierra.running), ('service', 'running', True, 1))
        self.assertEqual(sierra.held, [('TASK-023', 'blocker')])
        self.assertEqual(fleet_view.blockers(sierra), [('held', 'TASK-023 blocker (2)')])
        self.assertEqual(fleet_view.summary(found.values()), [('working', 1), ('stalled', 1)])

    def test_state_without_a_session_or_service_is_history_not_a_runner(self):
        self.runner_state('/git/gone', state='working', since=time.time())
        self.assertEqual(self.collect(), {})

    def test_blockers_are_grouped_in_order_and_long_groups_are_cut(self):
        roots = ([{'id': f'D-{i}', 'kind': 'contract', 'blocks': 1} for i in range(8)]
                 + [{'id': 'C-1', 'kind': 'claim', 'blocks': 13},
                    {'id': 'approved physical target and capture consent; preparation proceeds', 'kind': 'outside', 'blocks': 2},
                    {'id': 'X', 'kind': 'cycle', 'blocks': 1}])
        runner = fleet_view.Runner(name='r', roots=roots)
        self.assertEqual(fleet_view.blockers(runner), [
            ('dependency cycle', 'X (1)'),
            ('entry changed', 'D-0 (1), D-1 (1), D-2 (1), D-3 (1), D-4 (1), D-5 (1), +2 more'),
            ('claimed elsewhere', 'C-1 (13)'),
            ('outside Now/Next', 'approved physical target and... (2)')])

    def test_actions_are_the_commands_that_already_exist(self):
        def keys(runner, **kw):
            return {a.key: a for a in fleet_view.actions(runner, tx='tx', script='pa.sh', **kw)}
        tmux = keys(fleet_view.Runner(name='india', repo='/git/india', mode='tmux'), agent=['claude'], task='T-9')
        self.assertEqual(tmux['enter'].argv, ['tx', 'pi-autowork-india'])
        self.assertTrue(tmux['enter'].interactive)
        self.assertEqual(tmux['s'].argv, ['tx', 'autowork', 'stop', 'india'])
        self.assertIn('resume', tmux['s'].confirm)
        self.assertEqual(tmux['i'].argv, ['pa.sh', '--install-service', '--repo', '/git/india'])
        self.assertEqual(tmux['x'].argv, ['pa.sh', '--repo', '/git/india', '--set-aside', 'T-9'])
        self.assertEqual(tmux['b'].argv, ['claude', '/autowork blockers /git/india'])
        self.assertNotIn('u', tmux)
        service = keys(fleet_view.Runner(name='sierra', repo='/git/sierra', mode='service', service='running'))
        self.assertEqual(service['s'].argv, ['systemctl', '--user', 'stop', 'pi-autowork@sierra.service'])
        self.assertEqual(service['u'].argv, ['pa.sh', '--remove-service', '--repo', '/git/sierra'])
        self.assertNotIn('i', service)
        self.assertNotIn('b', service)  # no agent available
        stopped = keys(fleet_view.Runner(name='sierra', repo='/git/sierra', mode='service', service='dead'))
        self.assertEqual(stopped['a'].argv, ['systemctl', '--user', 'start', 'pi-autowork@sierra.service'])
        idle = keys(fleet_view.Runner(name='new', repo='/git/new'))
        self.assertEqual((idle['a'].argv, idle['a'].env), (['tx', 'autowork', 'start', '/git/new'], {'TX_NO_ATTACH': '1'}))
        self.assertFalse(any(a.confirm for a in (idle['a'], tmux['enter'])))  # only changes that stop or remove ask

    def test_agent_for_blockers(self):
        self.assertEqual(fleet_view.blockers_agent({'TX_AUTOWORK_AGENT': 'pi --model x', 'PATH': ''}), ['pi', '--model', 'x'])
        bin_dir = self.base / 'bin'
        bin_dir.mkdir()
        self.fake('bin/pi', 'true')
        self.assertEqual(fleet_view.blockers_agent({'PATH': str(bin_dir)}), ['pi'])
        self.assertIsNone(fleet_view.blockers_agent({'PATH': str(self.base / 'nothing')}))

    @unittest.skipUnless(shutil.which('uv'), 'uv is not installed')
    def test_the_tui_drives_the_same_actions_headless(self):
        """Textual is not a runner dependency: the pilot runs under uv, from its cache only."""
        result = subprocess.run(['uv', 'run', '--offline', '--quiet', '--no-project', '--with', 'textual==8.2.8',
                                 'python3', str(PILOT)], capture_output=True, text=True, timeout=180)
        if result.returncode == 2 and 'textual' in result.stderr.lower() and 'offline' in result.stderr.lower():
            self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PILOT OK', result.stdout)


if __name__ == '__main__':
    unittest.main()
