"""fleet_view: runners from systemd and status.json; blockers; actions. Fakes only."""
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
from unittest import mock

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

    def collect(self, units=''):
        os.environ['FAKE_UNITS'] = units
        self.addCleanup(os.environ.pop, 'FAKE_UNITS', None)
        return {r.name: r for r in fleet_view.collect(self.state, self.env, systemctl=self.systemctl)}

    def test_merges_services_and_runner_state(self):
        self.runner_state('/git/india', state='stalled', since=time.time() - 341 * 60, waiting=23,
                          roots=[{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19},
                                 {'id': 'T-1', 'kind': 'running', 'blocks': 4}])
        self.runner_state('/git/sierra', state='working', since=time.time() - 600, active_workers=1, waiting=40,
                          held=[{'task': 'TASK-023', 'cause': 'blocker'}],
                          roots=[{'id': 'TASK-023', 'kind': 'held', 'cause': 'blocker', 'blocks': 2}])
        for name in ('india', 'sierra'):
            (self.env / f'{name}.env').write_text(f'PI_AUTOWORK_REPO=/git/{name}\n')
        os.environ['FAKE_ENABLED'] = '1'
        self.addCleanup(os.environ.pop, 'FAKE_ENABLED', None)
        found = self.collect(units='pi-autowork@india.service loaded active running pi-autowork for india\n'
                                   'pi-autowork@sierra.service loaded active running pi-autowork for sierra\n')
        self.assertEqual(sorted(found), ['india', 'sierra'])
        india, sierra = found['india'], found['sierra']
        self.assertEqual((india.mode, india.state, fleet_view.duration(india.minutes), india.waiting),
                         ('service', 'stalled', '5h41m', 23))
        self.assertEqual(fleet_view.blockers(india), [('outside Now/Next', 'TASK-036 (19)')])  # moving work is not a blocker
        self.assertEqual((sierra.service, sierra.running, sierra.held), ('running', 1, [('TASK-023', 'blocker')]))
        self.assertEqual(fleet_view.blockers(sierra), [('held', 'TASK-023 blocker (2)')])
        self.assertEqual(fleet_view.summary(found.values()), [('working', 1), ('stalled', 1)])

    def test_state_without_a_service_is_history_not_a_runner(self):
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
            ('not runnable', 'D-0 (1), D-1 (1), D-2 (1), D-3 (1), D-4 (1), D-5 (1), +2 more'),
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
        ready = fleet_view.readiness(repo)
        self.assertFalse(ready.ready)
        self.assertIn('commit TODO.md and goals.json on main first', ' '.join(fleet_view.how_to_fix(ready)))
        subprocess.run(['git', '-C', str(repo), 'add', 'TODO.md', 'goals.json'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'planning'], check=True)
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

    def test_the_owners_questions_come_from_the_session_first_and_say_what_is_needed(self):
        block = ('# Blockers\n\n## Active\n\n<!-- pi-autowork:questions:start -->\n\n'
                 '### Q-TASK-036 — USER_DECISION — effort decision — unblocks 19\n\n- Task: TASK-036\n'
                 '- Needs: 19 waiting task(s) depend on "TASK-036".\n- Since: x\n- Answer: y\n\n'
                 '### Q-T-9 — USER_INPUT — effort input — unblocks 1\n\n- Needs: a key\n\n'
                 '<!-- pi-autowork:questions:end -->\n')
        repo, session, state = self.base / 'repo', self.base / 'integration', self.base / 'st'
        for folder in (repo, session, state):
            folder.mkdir()
        (repo / 'BLOCKERS.md').write_text('# Blockers\n')  # not merged yet: the session has them
        (session / 'BLOCKERS.md').write_text(block)
        (state / 'session.json').write_text(json.dumps({'path': str(session)}))
        found = fleet_view.read_questions(repo, state)
        self.assertEqual([(q.id, q.effort, q.unblocks) for q in found], [('TASK-036', 'decision', 19), ('T-9', 'input', 1)])
        self.assertEqual(found[0].needs, '19 waiting task(s) depend on "TASK-036".')
        self.assertEqual(fleet_view.read_questions(repo), [])
        runner = fleet_view.Runner(name='india', state='stalled', questions=found,
                                   roots=[{'id': 'TASK-036', 'kind': 'outside', 'blocks': 19}])
        self.assertEqual(fleet_view.needs(runner), '2 questions, easiest TASK-036')
        runner.questions = []
        self.assertEqual(fleet_view.needs(runner), 'outside Now/Next: TASK-036 (19)')
        self.assertEqual(fleet_view.needs(fleet_view.Runner(name='x', state='not running')), 'start it')

    def test_a_runner_verifying_now_is_working_whatever_its_last_status_says(self):
        """sierra: TASK-026's review ran for minutes while the status written before it said stalled."""
        (self.env / 'india.env').write_text('PI_AUTOWORK_REPO=/git/india\n')
        self.runner_state('/git/india', state='stalled', since=time.time() - 3600)
        for age, state in ((60, 'working'), (4000, 'stalled'), (None, 'stalled')):
            lane = fleet_view.Lane(task='TASK-026', phase='verifying', activity='bash: rg', activity_age=age)
            with mock.patch.object(fleet_view, 'lanes', return_value=[lane]), \
                    mock.patch.object(fleet_view.Runner, 'has_service', False):
                self.assertEqual(self.collect()['india'].state, state, age)

    def test_the_log_reads_as_events(self):
        # india's journal: systemd's unit lines, the start banner, a pending line per waiting
        # task and a result printed again are noise; a start or a stop is one rule line.
        text = '\n'.join([
            '[22:26] TASK-011: running — worker started',
            'Stopping pi-autowork@india.service - pi-autowork for india...',
            '[22:36] Stopping: pausing workers so they resume on the next start, then merging finished work',
            '[22:37] Stopped. Unfinished tasks keep their worktrees and resume on the next start.',
            'pi-autowork@india.service: Consumed 9min 11.873s CPU time, 6.0G memory peak, 0B memory swap peak.',
            'Started pi-autowork@india.service - pi-autowork for india.',
            'PI AUTOWORK', 'Repository: /r (merges into main)', 'Toolset:    /t at 3848aaa (not a Pi package)',
            'Mode:       continuous; state in /s',
            '[22:37] Started (PID 244196). Stop with Ctrl+C.',
            '[22:37] TASK-034: pending — dependency: TASK-035',
            '[22:37] TASK-011: paused — stopped by a runner restart; resumes on attempt 1',
            '[22:37] TASK-011: running — worker started',
            '[22:37] TASK-011: failed — report.json pending_live must be a list of strings',
            '[22:37] Questions for the owner in BLOCKERS.md: 4 open (easiest: TASK-036, decision)'])
        self.assertEqual(fleet_view.log_lines(text), [
            ('[22:26] TASK-011: running — worker started', 'cyan'),
            ('[22:36] ── restarted ──', 'bold'),
            ('[22:37] TASK-011: paused — stopped by a runner restart; resumes on attempt 1', 'yellow'),
            ('[22:37] TASK-011: running — worker started', 'cyan'),
            ('[22:37] TASK-011: failed — report.json pending_live must be a list of strings', 'bold red'),
            ('[22:37] Questions for the owner in BLOCKERS.md: 4 open (easiest: TASK-036, decision)', 'yellow')])

    def test_an_update_restart_is_one_line_and_repeats_are_counted(self):
        """TOOLSET-166-b4: the log opened on restart blocks and copies of the same line."""
        text = '\n'.join([
            '[10:09] No task can start now: TASK-012: not runnable',
            '[10:15] Toolset updated to 03d8f5b; restarting on it',
            '[10:15] Stopping: pausing workers so they resume on the next start, then merging finished work',
            '[10:15] Stopped. Unfinished tasks keep their worktrees and resume on the next start.',
            '[10:15] Started (PID 1). Stop with Ctrl+C.',
            '[10:15] Session pi-autowork/20261017-101500 started from main',
            '[10:15] No task can start now: TASK-012: not runnable',
            '[10:16] No task can start now: TASK-012: not runnable',
            '[10:17] No task can start now: TASK-012: not runnable',
            '[10:20] Toolset updated to 5caf145; restarting on it'])
        self.assertEqual(fleet_view.log_lines(text), [
            ('[10:09] No task can start now: TASK-012: not runnable', 'yellow'),
            ('[10:15] ── restarted onto 03d8f5b ──', 'bold'),
            ('[10:15] No task can start now: TASK-012: not runnable  ×3', 'yellow'),
            ('[10:20] ── restarting onto 5caf145 ──', 'bold')])

    def test_the_verdict_says_whether_it_is_stuck_and_why(self):
        """TOOLSET-166-b4: one sentence per state, from the runner's own status."""
        R, Q, L = fleet_view.Runner, fleet_view.Question, fleet_view.Lane
        root = {'id': 'TASK-140', 'kind': 'held', 'cause': 'overlap', 'blocks': 23}
        cases = [
            (R('a', state='working', running=2, max_workers=8, lanes=[L('T1', 'implementing'), L('T2', 'verifying')]),
             'Working — 2 of 8 workers busy'),
            (R('a', state='working', running=1, max_workers=1,
               lanes=[L('T1', 'implementing')] + [L(f'D{i}', 'implemented') for i in range(15)]),
             'Working — 1 of 1 worker busy; 15 commits waiting to merge'),
            (R('a', state='working', running=1, lanes=[L('T1', 'implementing')], gate='load average 27 >= 24 CPUs',
               questions=[Q('X', 'quick', 4, 'answer it')]),
             'Working — 1 worker busy; no more start: load average 27 >= 24 CPUs; 1 question for you'),
            (R('a', state='stalled', minutes=42, questions=[Q('TOOLSET-157-cd', 'quick', 4, 'widen Touches')]),
             'Waiting on you — 1 question, easiest TOOLSET-157-cd (unblocks 4): widen Touches'),
            (R('a', state='stalled', minutes=42, roots=[root]),
             "Stuck 42m — TASK-140 (held: changed another task's files; offered again once they are free, holds 23)"),
            (R('a', state='blocked', minutes=3, blocker='no usable model: quota'), 'Stuck 3m — no usable model: quota'),
            (R('a', state='blocked', gate='memory 2900 MB available, need 6000 MB'),
             'Host busy — memory 2900 MB available, need 6000 MB'),
            (R('a', state='restarting', restarting='onto 0c41776'), 'Restarting onto 0c41776'),
            (R('a', state='restarting', restarting='service'), 'Restarting'),
            (R('a', state='paused'), 'Paused — p resumes it'),
            (R('a', state='not running'), 'Not running — a starts its service'),
            (R('a', state='idle'), 'Idle — nothing left to run in Now/Next'),
            (R('a', state='working', minutes=5, job={'role': 'maintainer', 'task': 'DOCS-MAINTAINER'}),
             'Working — DOCS-MAINTAINER repairing task docs (5m)'),
            (R('a', state='working', minutes=2, job={'role': 'provision', 'task': 'T-1'}),
             'Working — installing what the review of T-1 needs (2m)'),
        ]
        for runner, sentence in cases:
            with self.subTest(state=runner.state, sentence=sentence):
                self.assertEqual(fleet_view.verdict(runner)[0], sentence)

    def test_workers_say_what_they_are_doing_in_plain_words(self):
        L = fleet_view.Lane
        for lane, doing in (
                (L('T', 'implementing', activity='bash: cd x && python3 -m unittest discover -s y'),
                 'running tests: python3 -m unittest discover -s y'),
                (L('T', 'implementing', activity='edit: skills/a.py'), 'editing skills/a.py'),
                (L('T', 'implementing', activity='read: TODO.md'), 'reading TODO.md'),
                (L('T', 'implementing', activity='subagent_wait: '), 'waiting on a sub-agent'),
                (L('T', 'implementing', activity='bash: cd rig && staticcheck ./...'), 'checking: staticcheck ./...'),
                (L('T', 'verifying', activity='bash: flutter test'), 'reviewer: running tests: flutter test'),
                (L('T', 'waiting to integrate', detail='until another session leaves the main checkout'),
                 'waiting to integrate: until another session leaves the main checkout'),
                (L('T', 'implementing'), 'starting')):
            with self.subTest(doing=doing):
                self.assertEqual(fleet_view.doing(lane), doing)
        self.assertEqual(fleet_view.quiet(L('T', 'implementing', activity_age=12 * 60)), 'quiet 12m')
        self.assertEqual(fleet_view.quiet(L('T', 'implementing', activity_age=60)), '')

    def test_a_self_update_shows_restarting_not_not_running(self):
        state = self.base / 'state-r'
        state.mkdir()
        stamp = lambda ago: time.strftime('%Y-%m-%dT%H:%M:%S', time.localtime(time.time() - ago)) + \
            time.strftime('%z')[:3] + ':' + time.strftime('%z')[3:]
        (state / 'runner.log').write_text(
            f'{stamp(400)} No task can start now: A: resource gate: load average 30 >= 24 CPUs\n'
            f'{stamp(30)} Toolset updated to 0c41776; restarting on it\n')
        runner = fleet_view.Runner('a', state_dir=str(state))
        self.assertEqual(fleet_view.recent_events(runner), ('onto 0c41776', ''))  # the gate line is too old
        (state / 'runner.log').write_text(f'{stamp(30)} Toolset updated to 0c41776; restarting on it\n'
                                          f'{stamp(10)} Started (PID 1). Stop with Ctrl+C.\n'
                                          f'{stamp(5)} No task can start now: A: resource gate: load 30 >= 24 CPUs\n')
        self.assertEqual(fleet_view.recent_events(runner), ('', 'load 30 >= 24 CPUs'))

    def test_agent_for_blockers(self):
        self.assertEqual(fleet_view.blockers_agent({'AUTOWORK_AGENT': 'pi --model x', 'PATH': ''}), ['pi', '--model', 'x'])
        bin_dir = self.base / 'bin'
        bin_dir.mkdir()
        self.fake('bin/pi', 'true')
        self.assertEqual(fleet_view.blockers_agent({'PATH': str(bin_dir)}), ['pi'])
        self.assertIsNone(fleet_view.blockers_agent({'PATH': str(self.base / 'nothing')}))
        # Claude Code namespaces plugin skills; the others take /blockers directly.
        self.assertEqual(fleet_view.blockers_prompt(['/usr/bin/claude'], '/r'), '/autowork:blockers /r')
        self.assertEqual(fleet_view.blockers_prompt(['pi', '--model', 'x'], '/r'), '/blockers /r')

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
        self.assertEqual(fleet_view._split_phase('paused; resumes on attempt 1 — with uncommitted changes'),
                         ('paused', 'resumes on attempt 1; with uncommitted changes'))
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
