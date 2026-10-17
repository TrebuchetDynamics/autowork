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
        self.systemctl = self.fake('systemctl', '[[ $2 == is-enabled ]] && { [[ -n ${FAKE_ENABLED:-} ]]; exit; }\n'
                                                'printf "%s" "${FAKE_UNITS:-}"')

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

    def test_actions_are_autowork_commands(self):
        def keys(runner, **kw):
            return {a.key: a for a in fleet_view.actions(runner, command='aw', script='pa.sh', **kw)}
        running = keys(fleet_view.Runner(name='india', repo='/git/india', mode='service', service='running'),
                       agent=['claude'], task='T-9')
        self.assertTrue(running['enter'].interactive and running['enter'].argv == [])  # the TUI's own log view
        self.assertEqual(running['s'].argv, ['aw', 'stop', 'india'])
        self.assertEqual(running['R'].argv, ['aw', 'restart', 'india'])
        self.assertEqual(running['p'].argv, ['aw', 'pause', 'india'])
        self.assertEqual(running['m'].argv, ['aw', 'model', 'india'])
        self.assertEqual(running['x'].argv, ['pa.sh', '--repo', '/git/india', '--set-aside', 'T-9'])
        self.assertEqual(running['b'].argv, ['aw', 'blockers', '/git/india'])
        self.assertNotIn('u', running)  # remove only a stopped service
        for key in ('s', 'R', 'p', 'x'):
            self.assertTrue(running[key].confirm, key)
        paused = keys(fleet_view.Runner(name='india', repo='/git/india', mode='service', service='dead', state='paused'))
        self.assertEqual(paused['p'].argv, ['aw', 'resume', 'india'])
        self.assertEqual(paused['a'].argv, ['aw', 'start', '/git/india'])
        self.assertEqual(paused['u'].argv, ['aw', 'remove', 'india'])
        self.assertNotIn('b', paused)  # no agent available

    def test_readiness_needs_todo_goals_and_main(self):
        repo = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        ready = fleet_view.readiness(repo)
        self.assertEqual((ready.ready, ready.problems), (False, ['TODO.md', 'goals.json']))
        self.assertIn('Create goals.json from TODO.md', ' '.join(fleet_view.how_to_fix(ready)))
        (repo / 'TODO.md').write_text('# TODO\n')
        (repo / 'goals.json').write_text('{}\n')
        self.assertTrue(fleet_view.readiness(repo).ready)
        (repo / 'sub').mkdir()
        self.assertIn(f'its repository root ({repo})', fleet_view.readiness(repo / 'sub').problems)
        subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-b', 'feature'], check=True)
        self.assertEqual(fleet_view.readiness(repo).problems, ['main checked out'])
        self.assertEqual(fleet_view.readiness(self.base).mark, 'not a repository')

    def test_models_come_from_pi_and_settings_keep_other_lines(self):
        pi = self.fake('pi', 'echo "provider  model  context"; echo "openrouter  deepseek/deepseek-v4.1-flash  128K"')
        self.assertEqual(fleet_view.models(pi), ['openrouter/deepseek/deepseek-v4.1-flash'])
        settings = self.base / 'india.env'
        settings.write_text('PI_AUTOWORK_REPO=/git/india\nPATH=/bin\nPI_AUTOWORK_PRIMARY=old/model\n')
        fleet_view.write_env(settings, {'PI_AUTOWORK_PRIMARY': 'openai-codex/gpt-6-luna', 'PI_AUTOWORK_FALLBACK': 'x/y'})
        self.assertEqual(settings.read_text(), 'PI_AUTOWORK_REPO=/git/india\nPATH=/bin\n'
                                               'PI_AUTOWORK_PRIMARY=openai-codex/gpt-6-luna\nPI_AUTOWORK_FALLBACK=x/y\n')
        self.assertEqual(oct(settings.stat().st_mode & 0o777), '0o600')
        fleet_view.write_env(settings, {'PI_AUTOWORK_FALLBACK': None})
        self.assertNotIn('FALLBACK', settings.read_text())

    def test_a_stopped_disabled_service_is_listed_from_its_settings_and_paused_only_when_paused(self):
        (self.env / 'india.env').write_text('PI_AUTOWORK_REPO=/git/india\nPI_AUTOWORK_PRIMARY=openai-codex/gpt-6-luna\n')
        self.runner_state('/git/india', state='stalled', since=time.time() - 60)
        india = self.collect()['india']  # systemd lists nothing: unloaded once stopped and disabled
        self.assertEqual((india.mode, india.state, india.model, india.fallback),
                         ('service', 'not running', 'openai-codex/gpt-6-luna', fleet_view.DEFAULT_FALLBACK))
        fleet_view.paused_marker(self.env, 'india').write_text('paused\n')  # `autowork pause` leaves this
        self.assertEqual(self.collect()['india'].state, 'paused')

    def test_agent_for_blockers(self):
        self.assertEqual(fleet_view.blockers_agent({'AUTOWORK_AGENT': 'pi --model x', 'PATH': ''}), ['pi', '--model', 'x'])
        bin_dir = self.base / 'bin'
        bin_dir.mkdir()
        self.fake('bin/pi', 'true')
        self.assertEqual(fleet_view.blockers_agent({'PATH': str(bin_dir)}), ['pi'])
        self.assertIsNone(fleet_view.blockers_agent({'PATH': str(self.base / 'nothing')}))

    def test_lanes_show_what_each_task_in_flight_is_doing(self):
        repo = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        slots = repo / '.git' / 'autowork-execution' / 'slots'
        slots.mkdir(parents=True)
        started = time.time() - 14 * 60
        for task, state in (('T-1', 'running'), ('T-2', 'reported'), ('T-3', 'closed'), ('T-4', 'held')):
            (slots / f'{task}.json').write_text(json.dumps({'task_id': task, 'state': state, 'attempt': 2,
                                                            'started_at': started}))
        state = self.base / 'state' / 'key'
        (state / 'sessions').mkdir(parents=True)
        (state / 'runner.log').write_text(
            '2026-10-16T16:00:00-06:00 T-2: implemented\n'
            '2026-10-16T16:01:00-06:00 T-2: waiting to integrate until another session leaves the main checkout (pid 7)\n')
        stamp = time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(time.time() - 20))
        (state / 'sessions' / '2026-10-16T22-00-00-000Z_pi-autowork-T-1-attempt-2.jsonl').write_text('\n'.join(json.dumps(e) for e in [
            {'type': 'message', 'timestamp': stamp, 'message': {'role': 'assistant', 'content': [
                {'type': 'toolCall', 'name': 'bash', 'arguments': json.dumps({'command': 'pytest -q tests/\necho done'})}]}},
            {'type': 'message', 'timestamp': stamp, 'message': {'role': 'toolResult', 'content': [{'type': 'text', 'text': 'ok'}]}},
        ]) + '\n')
        runner = fleet_view.Runner(name='repo', repo=str(repo), state_dir=str(state))
        lanes = {lane.task: lane for lane in fleet_view.lanes(runner)}
        self.assertEqual(sorted(lanes), ['T-1', 'T-2'])  # closed and held are not in flight
        one, two = lanes['T-1'], lanes['T-2']
        self.assertEqual((one.phase, one.attempt, fleet_view.duration(one.minutes)), ('implementing', 2, '14m'))
        self.assertEqual(one.activity, 'bash: pytest -q tests/')
        self.assertRegex(fleet_view.ago(one.activity_age), r'^(1|2)\ds ago$')
        self.assertEqual((two.phase, two.detail), ('waiting to integrate', 'until another session leaves the main checkout (pid 7)'))
        self.assertEqual((two.activity, two.activity_age), ('', None))

    def test_phase_text_is_split_into_a_short_phase_and_its_detail(self):
        self.assertEqual(fleet_view._split_phase('verifying'), ('verifying', ''))
        self.assertEqual(fleet_view._split_phase('failed — validation failed'), ('failed', 'validation failed'))
        self.assertEqual(fleet_view._split_phase('its TODO entry changed while it was held'),
                         ('its TODO entry', 'changed while it was held'))
        self.assertEqual(fleet_view.ago(45), '45s ago')
        self.assertEqual(fleet_view.ago(3 * 3600), '3h00m ago')

    def test_web_serves_the_tui_on_this_machine_by_default(self):
        from pi_autowork import tui_web
        self.assertTrue(tui_web.loopback('127.0.0.1') and tui_web.loopback('localhost') and tui_web.loopback('::1'))
        self.assertFalse(tui_web.loopback('0.0.0.0') or tui_web.loopback('100.64.0.5'))
        self.assertEqual(tui_web.command('/bin/autowork', '/opt/pa.sh', python='/py'),
                         f'/py {tui_web.TUI} --command /bin/autowork --script /opt/pa.sh')
        self.assertTrue(tui_web.command('autowork', 'pa.sh', view_only=True).endswith('--view-only'))

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
