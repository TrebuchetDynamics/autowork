"""fleet_view: runners from systemd and status.json; blockers; actions. Fakes only."""
import contextlib
import io
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
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from pi_autowork import fleet_view  # noqa: E402
from pi_autowork.processes import start_time  # noqa: E402
import store_fixture  # noqa: E402

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

    def with_inventory(self, runner, states, decisions=()):
        """Explicit committed census and identity-bearing observations for count fixtures."""
        import task_queue
        from pi_autowork import task_snapshot
        repo = self.base / 'inventory'
        repo.mkdir(exist_ok=True)
        dependencies = {t: g['label'].split()[0] for g in runner.stopped_groups for t in g.get('tasks') or []}
        store_fixture.write_todo(repo, '## Now\n' + ''.join(f'- [ ] {t} — {t}\n' +
                                (f'- Dependencies: {dependencies[t]}\n' if t in dependencies else '') for t, *_ in states)
                                + '\n## Needs decision\n' + ''.join(f'- [ ] {t} — {t}\n' for t in decisions))
        store = task_queue.store(repo)
        rows = [dict(task=task, state=state, cause=cause, reason=reason,
                     contract_hash=store.tasks[task].contract_hash,
                     admitted_contract_hash=store.tasks[task].contract_hash, attempt=1, started_at=time.time() - 60)
                for task, state, cause, reason in states]
        for lane in runner.lanes:
            row = next(r for r in rows if r['task'] == lane.task)
            lane.slot_state, lane.contract_hash = row['state'], row['admitted_contract_hash']
            lane.started_at, lane.phase_at = row['started_at'], time.time() - 30
        observation = dict(task_source=dict(workspace=str(repo), repository_identity=str(repo / '.git'),
                                           revision=store.rev, observed_at=time.time()), tasks=rows,
                           lanes=runner.lanes, questions=runner.questions, stopped_groups=runner.stopped_groups)
        runner.repo = str(repo)
        runner.snapshot = task_snapshot.capture(repo, engine_observation=observation, generation=1)
        return runner

    def test_pending_delete_projection_preserves_committed_authority_and_diagnostics(self):
        from dataclasses import replace
        runner = self.with_inventory(fleet_view.Runner('fixture'), [
            ('T-1', 'waiting', '', ''), ('T-2', 'held', 'blocker', '')], decisions=['T-3'])
        original = runner.snapshot
        runner.display_deleted = ('T-1', 'T-2', 'T-3')
        self.assertEqual(fleet_view.task_counts(runner), (0, 0, 0, 0, 0, 0))
        self.assertEqual(fleet_view.task_rows(runner), [])
        self.assertEqual(fleet_view.waiting_parts(runner), [])
        self.assertEqual(fleet_view.blocker_parts(runner), '')
        self.assertIn('Idle', fleet_view.verdict(runner)[0])
        self.assertIs(runner.snapshot, original)
        self.assertEqual(original.counts[-1], 3)
        self.assertEqual(len(original.store.tasks), 3)
        row = replace(original.rows[0], question=True)
        runner.snapshot = replace(original, rows=(row, *original.rows[1:]))
        annotation = fleet_view.task_view(fleet_view.task_rows(runner), 'questions')
        self.assertEqual([(r.task, r.kind) for r in annotation], [('T-1', 'annotation')])
        self.assertEqual(fleet_view.task_actions(runner, row, command='aw', script='unused'), [])
        lane = fleet_view.Lane('T-1', 'running')
        runner.snapshot = replace(runner.snapshot, joined_lanes=(('T-1', 1, 'running'),))
        self.assertIn('Annotation', fleet_view.lane_status(runner, lane)[0])
        runner.snapshot = replace(original, counts=None, freshness='unavailable')
        self.assertIsNone(fleet_view.task_counts(runner))
        self.assertIn('deletion pending commit', fleet_view.freshness(runner))

    def test_runner_display_observation_is_explicit_and_absent_from_ls_json(self):
        from dataclasses import replace
        from pi_autowork import command, task_snapshot
        snapshot = task_snapshot.TaskSnapshot('/repo', '/repo/.git', 'abc', 1, time.time())
        runner = fleet_view.Runner(
            name='repo', repo='/repo', snapshot=snapshot, preparation='prepared',
            question_provenance={'source': 'session'}, acquisition_errors=['read failed'])
        copied = replace(runner, name='copy')
        self.assertIs(copied.snapshot, snapshot)
        self.assertEqual(copied.preparation, 'prepared')
        self.assertEqual(copied.question_provenance, {'source': 'session'})
        self.assertEqual(copied.acquisition_errors, ['read failed'])
        self.assertIs(fleet_view.snapshot_for(copied), snapshot)
        record = command.runner_json(copied)
        for key in command.DISPLAY_ONLY_RUNNER_FIELDS:
            self.assertNotIn(key, record)
        self.assertEqual(record['name'], 'copy')

    def runner_state(self, repo, **status):
        source = status.setdefault('task_source', dict(workspace=repo, repository_identity=repo + '/.git',
                                                      revision='fixture', observed_at=time.time()))
        status.setdefault('snapshot_at', source.get('observed_at'))
        folder = self.state / Path(repo).name
        folder.mkdir(parents=True)
        (folder / 'runner.json').write_text(json.dumps(
            {'pid': os.getpid(), 'start_time': start_time(os.getpid()), 'repo': repo}))
        (folder / 'status.json').write_text(json.dumps({'repo': repo, 'updated_at': time.time(), **status}))

    def collect(self, units=''):
        os.environ['FAKE_UNITS'] = units
        self.addCleanup(os.environ.pop, 'FAKE_UNITS', None)
        return {r.name: r for r in fleet_view.collect(self.state, self.env, systemctl=self.systemctl)}

    def test_fleet_rows_are_a_pure_projection(self):
        from pi_autowork import task_snapshot
        snapshot = task_snapshot.TaskSnapshot('/repo', '/repo/.git', 'abc', 1, time.time(),
                                              counts=(1, 0, 1, 0, 2, 4))
        runner = fleet_view.Runner(name='repo', state='working', snapshot=snapshot, decisions=2)
        row = fleet_view.runner_rows([runner])[0]
        self.assertEqual(row['Runner'], ('repo', ''))
        self.assertEqual(row['State'], ('working', 'bold green'))
        self.assertEqual(row['Active'], ('1', 'green'))
        self.assertEqual(row['Waiting'], ('1', ''))
        self.assertEqual(row['Decision'], ('2', 'yellow'))
        self.assertEqual(row['Total'], ('4', 'bold'))
        self.assertIn('2 tasks in Needs decision', row['Needs'][0])

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
        self.assertEqual(fleet_view.blockers(sierra), [('blocker', 'TASK-023 blocker (2)')])
        self.assertEqual(fleet_view.summary(found.values()), [('working', 1), ('stalled', 1)])

    def test_ls_json_matches_the_pre_refactor_recorded_fleet(self):
        """Keep legacy merging stable except unknown counts and additive provenance."""
        from pi_autowork import command
        fixture = Path(__file__).with_name('fixtures') / 'fleet'
        for folder in ('state', 'env', 'session'):
            shutil.copytree(fixture / folder, self.base / folder, dirs_exist_ok=True)
            for path in (self.base / folder).rglob('*'):
                if path.is_file():
                    path.write_text(path.read_text().replace('$BASE', str(self.base)).replace('$PID', str(os.getpid()))
                                    .replace('$START', start_time(os.getpid())))
                    if path.suffix == '.in':
                        path.rename(path.with_suffix(''))
        units = 'pi-autowork@demo-escaped.service loaded active running demo\n'
        with mock.patch.dict(os.environ, FAKE_UNITS=units, FAKE_ENABLED='1'), \
                mock.patch.object(fleet_view.time, 'time', return_value=2000000000), \
                contextlib.redirect_stdout(io.StringIO()) as output:
            result = command.cmd_ls(type('Args', (), {'json': True})(), dict(
                state_root=self.state, env_dir=self.env, systemctl=self.systemctl))
        self.assertEqual(result, 0)
        expected = json.loads((fixture / 'ls.json').read_text())
        expected['runners'][0].update(running=None, waiting=None, stopped=None, observation=dict(
            runner_alive=True, health_written_at=2000000000, snapshot_at=None, snapshot_age_seconds=None,
            task_state='unknown', error=None))
        self.assertEqual(json.loads(output.getvalue().replace(str(self.base), '$BASE')), expected)

    def test_a_dead_main_check_is_interrupted_even_when_the_health_snapshot_says_running(self):
        self.runner_state('/git/india', main_check={'state': 'running', 'rev': 'old'})
        (self.env / 'india.env').write_text('PI_AUTOWORK_REPO=/git/india\n')
        path = self.state / 'india' / 'main_check.json'
        for pid, start in ((None, None), (2**30, '1'),
                           (os.getpid(), 'not-this-process')):
            with self.subTest(pid=pid, start=start):
                path.write_text(json.dumps(dict(state='running', rev='abcdef123', pid=pid,
                                                start_time=start, check_slot={'state': 'waiting'})))
                text = fleet_view.main_check.line(self.collect()['india'].main_check)
                self.assertIn('interrupted', text)
                self.assertIn('abcdef1', text)
                self.assertNotIn('running', text)
                self.assertNotIn('waiting', text)

    def test_a_main_check_of_a_superseded_revision_names_the_current_head(self):
        repo = self.base / 'india'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        def commit():
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Test', '-c', 'user.email=test@example.com',
                            'commit', '-qm', 'revision', '--allow-empty'], check=True)
            return subprocess.check_output(['git', '-C', str(repo), 'rev-parse', 'HEAD'], text=True).strip()
        old = commit()
        head = commit()
        self.runner_state(str(repo), main_check={'state': 'green', 'rev': old})
        (self.env / 'india.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
        record = dict(state='running', rev=old, pid=os.getpid(),
                      start_time=fleet_view.main_check.start_time(os.getpid()), started=time.time())
        path = self.state / 'india' / 'main_check.json'
        path.write_text(json.dumps(record))
        for state, rev, receipt in (('running', old, True), ('running', head, True),
                                     ('green', old, True), ('green', old, False)):
            with self.subTest(state=state, rev=rev, receipt=receipt):
                path.write_text(json.dumps(dict(record, state=state, rev=rev)))
                if not receipt:
                    path.unlink()  # the cached health result must also be revision-bound
                text = fleet_view.main_check.line(self.collect()['india'].main_check)
                if state == 'running':
                    self.assertIn('running', text)
                    self.assertEqual('superseded' in text, rev == old, text)
                else:
                    self.assertEqual(text, f'Last green: {old[:7]} · HEAD: {head[:7]} · verification pending')
                if rev == old:
                    self.assertIn(head[:7], text)

    def test_fleet_puts_owner_questions_and_setup_before_idle_and_working(self):
        for name, state in (('a-idle', 'idle'), ('b-working', 'working'),
                            ('y-setup', 'idle'), ('z-question', 'idle')):
            repo = self.base / name
            repo.mkdir()
            if name != 'y-setup':
                store_fixture.write_todo(repo, '- [ ] T-1 — Work\n')
            else:
                subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (self.env / f'{name}.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
            self.runner_state(str(repo), state=state)
        (self.base / 'z-question' / 'BLOCKERS.md').write_text(
            '<!-- pi-autowork:questions:start -->\n'
            '### Q-T-1 — USER_DECISION — effort decision — unblocks 1\n'
            '- Needs: choose a target\n<!-- pi-autowork:questions:end -->\n')
        units = '\n'.join(f'pi-autowork@{name}.service loaded active running x'
                          for name in ('a-idle', 'b-working', 'y-setup', 'z-question'))
        self.assertEqual(list(self.collect(units)), ['y-setup', 'z-question', 'a-idle', 'b-working'])

    def test_prepare_states_label_setup_migration_and_repair_instead_of_idle(self):
        runner = fleet_view.Runner('repo', repo=str(self.base), state='idle')
        for state, label in (
                ('none', 'Setup required — run /docs_sync'),
                ('legacy', 'Migration required — Force converts legacy planning'),
                ('conversion_pending', 'Task store needs repair'),
                ('invalid', 'Task store needs repair'),
                ('uncommitted', 'Setup required — run /docs_sync'),
                ('no_repository', 'Setup required — run /docs_sync'),
                ('converted', '')):
            with self.subTest(state=state), mock.patch(
                    'pi_autowork.task_prepare.prepare', return_value={'state': state}) as prepare:
                self.assertEqual(fleet_view.verdict(runner),
                                 (label, 'bold yellow') if label else
                                 ('Idle — nothing left to run in Now/Next', 'bold green'))
                self.assertEqual(fleet_view.needs(runner), label)
                self.assertTrue(all(call == mock.call(str(self.base), mode='check')
                                    for call in prepare.call_args_list), 'display must remain read-only')

    def test_tui_envelope_refreshes_inventory_but_bounds_and_invalidates_preparation(self):
        repo = self.base / 'cached'
        repo.mkdir()
        store_fixture.write_todo(repo, '- [ ] A — Alpha\n')
        settings = self.env / 'cached.env'
        settings.write_text(f'PI_AUTOWORK_REPO={repo}\n')
        def collect(now, cached=None):
            return fleet_view.collect_for_tui(self.state, self.env, systemctl=self.systemctl,
                                              now=now, generation=int(now), cached_preparation=cached)
        with mock.patch.object(fleet_view.task_prepare, 'prepare', wraps=fleet_view.task_prepare.prepare) as audit:
            first = collect(100)
            self.assertEqual(fleet_view.task_counts(first.runners[0]), (0, 0, 1, 0, 0, 1))
            self.assertEqual(first.snapshots[0].generation, 100)
            second = collect(110, first)
            self.assertEqual(second.runners[0].preparation.observed_at, 100)
            self.assertEqual(audit.call_count, 1)
            (repo / 'tasks/items/A.md').write_text((repo / 'tasks/items/A.md').read_text() + '\nPending\n')
            third = collect(111, second)
            self.assertEqual(third.runners[0].preparation.observed_at, 111)
            self.assertTrue(third.snapshots[0].rows[0].pending)
            fourth = collect(142, third)
            self.assertEqual(fourth.runners[0].preparation.observed_at, 142)
            settings.write_text(settings.read_text() + 'PI_AUTOWORK_PRIMARY=changed/model\n')
            fifth = collect(143, fourth)
            self.assertEqual(fifth.runners[0].preparation.observed_at, 143)
            self.assertEqual(collect(144).runners[0].preparation.observed_at, 144)  # explicit refresh

    def test_tui_acquisition_failures_are_not_empty_success(self):
        repo = self.base / 'failure'
        repo.mkdir()
        store_fixture.write_todo(repo, '- [ ] A — Alpha\n')
        (self.env / 'failure.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
        import task_queue
        store = task_queue.store(repo)
        self.runner_state(str(repo), task_source=dict(workspace=str(repo), repository_identity=str(repo / '.git'),
                          revision=store.rev, observed_at=time.time()))
        run = subprocess.run
        def bounded(argv, **kw):
            if 'is-enabled' in argv:
                self.assertEqual(kw.get('timeout'), 10)
                raise subprocess.TimeoutExpired(argv, 10)
            return run(argv, **kw)
        with mock.patch.object(fleet_view.subprocess, 'run', side_effect=bounded):
            result = fleet_view.collect_for_tui(self.state, self.env, systemctl=self.systemctl, generation=1)
        self.assertEqual(len(result.runners), 1)
        self.assertIn('enabled', ' '.join(result.errors))
        self.assertEqual(result.snapshots[0].counts[-1], 1)
        self.assertEqual(result.snapshots[0].engine_freshness, 'fresh')
        failed = self.fake('broken-systemctl', 'exit 2')
        unavailable = fleet_view.collect_for_tui(self.state, self.env, systemctl=failed, generation=2)
        self.assertTrue(unavailable.errors)
        later = result.runners[0].observation['snapshot_at'] + 601
        retained = fleet_view.collect_for_tui(self.state, self.env, systemctl=failed, generation=3,
                                             last_good=result, now=later)
        self.assertEqual((retained.snapshots[0].revision, retained.snapshots[0].captured_at),
                         (result.snapshots[0].revision, result.snapshots[0].captured_at))
        self.assertEqual(retained.snapshots[0].freshness, 'stale')
        self.assertNotEqual(retained.snapshots[0].engine_freshness, 'fresh')
        runner = retained.runners[0]
        self.assertEqual((runner.observation['task_state'], runner.observation['snapshot_age_seconds']),
                         ('unavailable', 601))
        self.assertTrue(runner.observation['runner_alive'])
        self.assertIsNone(runner.running)
        self.assertIn('service query', fleet_view.verdict(runner)[0])
        self.assertIn('task state unavailable', fleet_view.verdict(runner)[0])
        empty_env = self.base / 'empty-env'
        empty_env.mkdir()
        empty = fleet_view.collect_for_tui(self.state, empty_env, systemctl=self.systemctl, generation=3)
        self.assertEqual((empty.runners, empty.errors), ((), ()))

    def test_activity_does_not_freshen_task_observations(self):
        from pi_autowork import command, health
        import task_queue
        now = 2000000000
        for name in ('good', 'bad'):
            repo = self.base / name
            repo.mkdir()
            store_fixture.write_todo(repo, '- [ ] A — Alpha\n')
            source = dict(workspace=str(repo), repository_identity=str(repo / '.git'),
                          revision=task_queue.store(repo).rev, observed_at=now)
            self.runner_state(str(repo), state='working', updated_at=now, snapshot_at=now,
                              task_source=source, active_workers=2)
            (self.env / f'{name}.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
        folder = self.state / 'bad'
        status = json.loads((folder / 'status.json').read_text())
        identity = json.loads((folder / 'runner.json').read_text())
        units = ''.join(f'pi-autowork@{name}.service loaded active running fixture\n' for name in ('good', 'bad'))
        cases = [('current', 0, True, None, None),
                 ('stale', 601, True, None, None),
                 ('unavailable', 30, True, 'writer lock held', None),
                 ('unknown', None, True, None, None),
                 ('current', 0, False, None, None),
                 ('stale', 601, True, None, 'job'),
                 ('unavailable', 30, True, 'writer lock held', 'paused')]
        for expected, age, alive, error, special in cases:
            with self.subTest(expected=expected, alive=alive, special=special):
                value = dict(status, snapshot_at=now - age if age is not None else None,
                             task_source=dict(status['task_source'], observed_at=now - age) if age is not None else {})
                if error:
                    value.update(status_unavailable_since=now, status_reason=error)
                if special == 'job':
                    value['updated_at'] = now - 601
                    (folder / 'job.json').write_text(json.dumps(dict(identity, role='maintainer',
                                                                    task='DOCS-MAINTAINER', started=now - 10)))
                else:
                    (folder / 'job.json').unlink(missing_ok=True)
                (folder / 'status.json').write_text(json.dumps(value))
                (folder / 'runner.json').write_text(json.dumps(dict(identity, start_time=identity['start_time'] if alive else 'reused')))
                if special == 'paused':
                    fleet_view.paused_marker(self.env, 'bad').write_text('paused\n')
                before = {p: p.read_bytes() for p in self.state.rglob('*.json')}
                with mock.patch.dict(os.environ, FAKE_UNITS=units if special != 'paused' else units.splitlines(True)[0]), \
                        mock.patch.object(fleet_view.time, 'time', return_value=now):
                    cli = fleet_view.collect(self.state, self.env, systemctl=self.systemctl)
                    tui = fleet_view.collect_for_tui(self.state, self.env, systemctl=self.systemctl, generation=1)
                    paths = dict(state_root=self.state, env_dir=self.env, systemctl=self.systemctl)
                    with contextlib.redirect_stdout(io.StringIO()) as output:
                        command.cmd_ls(type('Args', (), {'json': True})(), paths)
                    with contextlib.redirect_stdout(io.StringIO()) as plain:
                        command.cmd_ls(type('Args', (), {'json': False, 'long': False})(), paths)
                record = next(r for r in json.loads(output.getvalue())['runners'] if r['name'] == 'bad')
                self.assertIn('observation', record)
                self.assertEqual(record['observation']['task_state'], expected)
                if expected != 'current':
                    self.assertIn('task state ' + expected, plain.getvalue())
                    self.assertIn('? running', plain.getvalue())
                for runners in (cli, tui.runners):
                    bad = next(r for r in runners if r.name == 'bad')
                    good = next(r for r in runners if r.name == 'good')
                    self.assertEqual(good.observation['task_state'], 'current')
                    self.assertEqual(good.running, 2)
                    self.assertEqual(bad.observation, record['observation'])
                    self.assertEqual(bad.observation['runner_alive'], alive)
                    self.assertEqual(bad.observation['snapshot_age_seconds'], age)
                    self.assertEqual(bad.running, 2 if expected == 'current' and alive else None)
                    self.assertEqual(fleet_view.task_counts(bad)[-1], 1)  # independent committed inventory
                    text = fleet_view.verdict(bad)[0]
                    if expected != 'current' and special != 'paused':
                        self.assertIn('task state ' + expected, text)
                    if error and special != 'paused':
                        self.assertIn(error, text)
                    if special == 'job':
                        self.assertEqual((bad.state, bad.job['role']), ('working', 'maintainer'))
                    if special == 'paused':
                        self.assertEqual(bad.state, 'paused')
                    if not alive:
                        self.assertEqual(bad.state, 'not running')
                self.assertEqual({p: p.read_bytes() for p in before}, before)

    def test_one_bad_runtime_source_preserves_healthy_fleet(self):
        repos = {name: self.base / name for name in ('good', 'bad')}
        for name, repo in repos.items():
            repo.mkdir()
            store_fixture.write_todo(repo, '- [ ] A — Alpha\n')
            (self.env / f'{name}.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
            self.runner_state(str(repo), state='working', active_workers=2)
        units = ''.join(f'pi-autowork@{name}.service loaded active running fixture\n' for name in repos)
        cases = [('status.json', []), ('runner.json', 7),
                 ('status.json', dict(repo=str(repos['bad']), state='working', updated_at='NaN')),
                 ('status.json', dict(repo=str(repos['bad']), roots=[None]))]
        original = {p: p.read_bytes() for p in (self.state / 'bad').iterdir()}
        ready = fleet_view.readiness(repos['bad'])
        for source, value in cases:
            with self.subTest(source=source, value=value):
                for path, data in original.items():
                    path.write_bytes(data)
                (self.state / 'bad' / source).write_text(json.dumps(value))
                before = {p: p.read_bytes() for p in (self.state / 'bad').iterdir()}
                cli = self.collect(units)
                tui = fleet_view.collect_for_tui(self.state, self.env, systemctl=self.systemctl, generation=1)
                for found in (cli, {r.name: r for r in tui.runners}):
                    self.assertEqual(found['good'].state, 'working')
                    self.assertEqual(found['bad'].state, 'unavailable')
                    self.assertIsNone(found['bad'].running)
                    self.assertEqual(fleet_view.task_counts(found['bad'])[-1], 1)
                    self.assertIn(source, ' '.join(found['bad'].snapshot.errors))
                    self.assertEqual(found['bad'].snapshot.engine_freshness, 'unknown')
                    self.assertIn('unavailable', fleet_view.verdict(found['bad'])[0].lower())
                    self.assertFalse(any('start' in a.argv for a in fleet_view.actions(
                        found['bad'], command='aw', script='unused')))
                self.assertIn(source, ' '.join(tui.errors))
                self.assertEqual({p: p.read_bytes() for p in before}, before)
        # Old folders advertising the same repository cannot replace verified live data.
        history = self.state / 'z-history'
        history.mkdir()
        (history / 'runner.json').write_text(json.dumps(dict(repo=str(repos['good']), pid=99999999)))
        (history / 'status.json').write_text('[]')
        found = self.collect(units)
        self.assertEqual((found['good'].state, found['good'].running), ('working', 2))
        self.assertIn('z-history/status.json', ' '.join(found['good'].snapshot.errors))
        # The independent snapshot reread must reject a value changed after acquisition.
        direct = fleet_view.Runner('bad', repo=str(repos['bad']), state='working', running=2,
                                   state_dir=str(self.state / 'bad'))
        (self.state / 'bad' / 'status.json').write_text(json.dumps(dict(tasks=4)))
        snap = fleet_view.snapshot_for(direct)
        self.assertEqual(snap.counts[-1], 1)
        self.assertIn('status.json', ' '.join(snap.errors))
        self.assertEqual(direct.state, 'unavailable')
        self.assertIsNone(direct.running)
        self.assertEqual(fleet_view.readiness(repos['bad']), ready)
        marker = fleet_view.paused_marker(self.env, 'bad')
        marker.write_text('paused\n')
        paused = self.collect('pi-autowork@good.service loaded active running fixture\n')['bad']
        self.assertEqual(paused.state, 'paused')
        self.assertTrue(marker.exists())
        self.assertIn('status.json', ' '.join(paused.snapshot.errors))

    def test_unknown_runtime_identity_is_diagnosed_without_guessing(self):
        self.runner_state('/git/unknown', state='working')
        (self.env / 'unknown.env').write_text('PI_AUTOWORK_REPO=/git/registered\n')
        for repo in ([], {}, 7, True, '', '   '):
            with self.subTest(repo=repo):
                for source in ('runner.json', 'status.json'):
                    (self.state / 'unknown' / source).write_text(json.dumps(dict(repo=repo)))
                result = fleet_view.collect_for_tui(self.state, self.env, systemctl=self.systemctl, generation=1)
                runner, = result.runners
                self.assertEqual(runner.repo, '/git/registered')
                self.assertEqual(runner.state_dir, '')
                self.assertNotEqual(runner.state, 'working')
                self.assertIn(str(self.state / 'unknown'), ' '.join(result.errors))
                self.assertIn('repo', ' '.join(result.errors))
                stderr = io.StringIO()
                with contextlib.redirect_stderr(stderr):
                    cli = self.collect()
                self.assertEqual(cli['unknown'].repo, '/git/registered')
                self.assertEqual(cli['unknown'].state_dir, '')
                self.assertIn(str(self.state / 'unknown'), stderr.getvalue())

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
        india = fleet_view.Runner(name='india', repo='/git/india', mode='service', service='running', held=[['T-9', 'conflict']],
                                  questions=[fleet_view.Question('T-9', 'input', 1, 'a key')])
        running = keys(india, agent=['claude'])
        self.assertTrue(running['l'].interactive and running['l'].argv == [])  # the TUI's own log view
        self.assertTrue(running['t'].interactive and running['t'].argv == [])  # and its Tasks window
        self.assertEqual(running['s'].argv, ['aw', 'stop', 'india'])
        self.assertEqual(running['r'].argv, ['aw', 'restart', 'india'])
        self.assertEqual((running['p'].label, running['p'].argv), ('Pause', ['aw', 'pause', 'india']))
        self.assertEqual(running['m'].argv, ['aw', 'model', 'india'])
        self.assertNotIn('u', running)  # remove only a stopped service
        for key in ('s', 'r', 'p'):
            self.assertTrue(running[key].confirm, key)
        # One key per action, the first letter of its one-word label.
        for action in running.values():
            self.assertEqual((action.label.lower()[0], ' ' in action.label), (action.key, False), action)
        paused = keys(fleet_view.Runner(name='india', repo='/git/india', mode='service', service='dead', state='paused'))
        self.assertEqual((paused['p'].label, paused['p'].argv), ('Play', ['aw', 'resume', 'india']))
        self.assertEqual(paused['u'].argv, ['aw', 'remove', 'india'])
        stopped = keys(fleet_view.Runner(name='india', repo='/git/india'))
        self.assertEqual((stopped['p'].label, stopped['p'].argv), ('Play', ['aw', 'start', '/git/india']))
        self.assertNotIn('s', stopped)
        # A task's own actions, in the Tasks window.
        held = fleet_view.TaskRow('T-9', 'Short', 'Now', 'held: conflict', 'held', question=True)
        task = {a.key: a for a in fleet_view.task_actions(india, held, command='aw', script='pa.sh', agent=['claude'])}
        self.assertEqual(task['u'].argv, ['aw', 'tasks', 'move', 'T-9', 'up', 'india'])
        self.assertEqual(task['d'].argv, ['aw', 'tasks', 'move', 'T-9', 'down', 'india'])
        self.assertEqual(task['c'].argv, ['aw', 'clear-held', 'india', 'T-9'])
        self.assertEqual(task['a'].argv, ['pa.sh', '--repo', '/git/india', '--set-aside', 'T-9'])
        self.assertEqual(task['b'].argv, ['aw', 'blockers', '/git/india'])
        for key in ('c', 'a'):
            self.assertTrue(task[key].confirm, key)
        ready = fleet_view.TaskRow('T-1', 'Short', 'Now', 'ready', 'ready')
        self.assertEqual(sorted(a.key for a in fleet_view.task_actions(india, ready, command='aw', script='pa.sh')),
                         ['d', 's', 'u', 'x'])  # nothing held, no agent: re-sort, re-section and delete
        closed = fleet_view.TaskRow('T-8', 'Short', 'Now', 'closed', 'closed')
        closed_actions = fleet_view.task_actions(india, closed, command='aw', script='pa.sh')
        self.assertEqual([(a.key, a.label, a.argv) for a in closed_actions],
                         [('x', 'Delete', ['aw', 'tasks', 'delete', 'T-8', '/git/india'])])
        self.assertTrue(closed_actions[0].confirm)

    def test_questions_are_answered_where_the_runner_reads_them(self):
        """From the TUI: each answer writes a note in the task's record, or moves it."""
        import datetime
        india = fleet_view.Runner(name='india', repo='/git/india')
        day = datetime.date(2026, 10, 20)
        def keys(question):
            return {a.key: a for a in fleet_view.answers(india, question, command='aw', today=day)}
        held = keys(fleet_view.Question('T-2', 'input', 1, 'quick hold', kind='quick_hold',
                                        answer='To rerun, add `Blocker resolution: ab12cd; <producer>` to it.'))
        self.assertEqual(held['r'].argv, ['aw', 'tasks', 'field', 'T-2', 'Blocker resolution', 'ab12cd; {text}', 'india'])
        self.assertEqual(held['w'].argv, ['aw', 'tasks', 'field', 'T-2', 'Owner decision', '2026-10-20: {text}', 'india'])
        self.assertEqual(held['d'].argv, ['aw', 'tasks', 'place', 'T-2', 'Needs decision', 'india',
                                          '--decision', '2026-10-20: deferred: {text}'])
        self.assertNotIn('o', held)
        for answer in held.values():
            self.assertEqual(answer.label.lower()[0], answer.key)
        self.assertEqual(keys(fleet_view.Question('FULL-CHECK', 'input', 0, 'no gate')), {})  # an agent answers it
        blockers = self.base / 'BLOCKERS.md'
        blockers.write_text('<!-- pi-autowork:questions:start -->\n\n### Q-T-2 — USER_INPUT — effort input — unblocks 1\n\n'
                            '- Needs: quick hold\n- Answer: add `Blocker resolution: ab12cd; x`\n- Kind: quick_hold\n\n'
                            '<!-- pi-autowork:questions:end -->\n')
        question = fleet_view.read_questions(str(self.base))[0]
        self.assertEqual((question.id, question.kind, question.answer), ('T-2', 'quick_hold', 'add `Blocker resolution: ab12cd; x`'))

    def test_fleet_counts_match_store(self):
        """The Tasks window counts what the store holds: open tasks per section, in rank order;
        done and superseded tasks, and a draft's missing fields, change nothing."""
        import task_queue
        repo = self.base / 'counted'
        repo.mkdir()
        store_fixture.write_todo(repo, '# TODO\n\n## Now\n\n- [ ] N-1 — One\n\n- [ ] N-2 — Two\n\n- [x] N-0 — Done\n\n'
                                       '## Next\n\n- [ ] X-1 — Next one\n\n- [ ] X-2 — Next two\n\n'
                                       '## Needs decision\n\n- [ ] D-1 — Asked\n')
        import task_store
        path = repo / 'tasks/items/X-1.md'
        path.write_text(task_store.set_note(task_store.edit(path.read_text(), {'status': 'superseded'}),
                                            'Superseded by', 'X-2; one task does both'))
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qam', 'X-2 supersedes X-1'], check=True)
        store = task_queue.store(repo)
        rows = fleet_view.task_rows(fleet_view.Runner(name='counted', repo=str(repo), state_dir=str(self.base / 'none')))
        expected = sorted((t for t in store.tasks.values() if t.status == 'open'),
                          key=lambda t: (['Now', 'Next', 'Needs decision'].index(t.section), t.rank, t.id))
        self.assertEqual([r.task for r in rows], [t.id for t in expected])
        for section in ('Now', 'Next', 'Needs decision'):
            self.assertEqual(sum(r.section == section for r in rows),
                             sum(t.status == 'open' and t.section == section for t in store.tasks.values()), section)
        self.assertEqual([r.task for r in rows], ['N-1', 'N-2', 'X-2', 'D-1'])
        self.assertEqual(sorted(g for g, _ in fleet_view.open_goals(fleet_view.Runner(name='counted', repo=str(repo)))),
                         sorted(g.id for g in store.goals.values() if g.status != 'met'))
        # An uncommitted edit shows as pending; the committed record still decides.
        with (repo / 'tasks/items/N-2.md').open('a') as record:
            record.write('- Owner decision: 2026-10-21: later\n')
        rows = fleet_view.task_rows(fleet_view.Runner(name='counted', repo=str(repo), state_dir=str(self.base / 'none')))
        self.assertEqual([r.task for r in rows if r.pending], ['N-2'])
        self.assertIn('Edit not committed', next(r.state for r in rows if r.task == 'N-2'))

    def test_tasks_list_every_open_task_in_order_with_what_the_runner_says(self):
        repo = self.base / 'repo'
        repo.mkdir()
        store_fixture.write_todo(repo,
            '# TODO\n\n## Now\n\n- [ ] T-1 — A first task whose title runs well past forty characters\n'
            '- Short: First task\n\n- [ ] T-2 — Second task\n\n- [x] T-0 — Done task\n\n'
            '## Next\n\n- [ ] T-3 — Third task with a title longer than forty characters\n\n'
            '## Needs decision\n\n- [ ] T-4 — Asked\n')
        state = self.base / 'state' / 'key'
        state.mkdir(parents=True)
        import task_queue
        store = task_queue.store(repo)
        fleet_view.health.update(state, dict(outcome='PARALLEL_STATUS',
            task_source=dict(workspace=str(repo), repository_identity=str(repo / '.git'),
                             revision=store.rev, observed_at=time.time()),
            tasks=[dict(task=t, state=s, cause=c, reason=r,
                        contract_hash=store.tasks[t].contract_hash,
                        admitted_contract_hash=store.tasks[t].contract_hash)
                   for t, s, c, r in [('T-1', 'running', '', ''), ('T-2', 'held', 'conflict', 'merge conflict'),
                                      ('T-3', 'waiting', '', 'dependency: T-1')]]))
        runner = fleet_view.Runner(name='repo', repo=str(repo), state_dir=str(state),
                                   lanes=[fleet_view.Lane(task='T-1', phase='implementing')],
                                   questions=[fleet_view.Question('T-4', 'decision', 2, 'pick one')])
        rows = fleet_view.task_rows(runner)
        self.assertEqual([(r.task, r.short, r.state, r.kind) for r in rows], [
            ('T-1', 'First task', 'Active · Implementing', 'working'),
            ('T-2', 'Second task', 'Blocker · Conflict · Agent repair', 'held'),
            ('T-3', 'Third task with a title longer than for…', 'Waiting', 'waiting'),
            ('T-4', 'Asked', 'Waiting · Needs decision', 'waiting')])
        self.assertEqual((rows[2].why, rows[3].why), ('dependency: T-1', 'in Needs decision; you: pick one'))
        self.assertEqual([r.task for r in fleet_view.task_view(rows, 'questions')], ['T-4'])
        self.assertEqual([r.task for r in fleet_view.task_view(rows, 'held')], ['T-2'])

    def test_readiness_needs_a_committed_task_store_and_main(self):
        repo = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        ready = fleet_view.readiness(repo)
        self.assertEqual((ready.ready, ready.problems, ready.mark), (False, ['tasks'], 'needs tasks'))
        self.assertIn(f'autowork tasks prepare {repo}', ' '.join(fleet_view.how_to_fix(ready)))
        for name in ('TODO.md', 'goals.json'):
            with self.subTest(lone_file=name):
                (repo / name).write_text('legacy content to reconcile\n')
                ready = fleet_view.readiness(repo)
                self.assertEqual((ready.ready, ready.problems, ready.mark),
                                 (False, ['tasks'], 'needs tasks'))
                hints = ' '.join(fleet_view.how_to_fix(ready))
                self.assertIn(f'autowork tasks prepare {repo}', hints)
                self.assertNotIn('--force', hints)
                (repo / name).unlink()
        for name in ('TODO.md', 'goals.json'):
            (repo / name).write_text('legacy planning\n')
        ready = fleet_view.readiness(repo)
        self.assertEqual((ready.ready, ready.problems, ready.mark),
                         (False, ['legacy planning'], 'legacy planning'))
        self.assertIn(f'autowork tasks prepare --force {repo}', ' '.join(fleet_view.how_to_fix(ready)))
        with mock.patch.object(fleet_view.task_prepare, 'detect', return_value='conversion_pending'):
            self.assertEqual(fleet_view.readiness(repo).problems, ['legacy planning'])
        for name in ('TODO.md', 'goals.json'):
            (repo / name).unlink()
        store_fixture.write_todo(repo, '- [ ] T-1 — First\n', commit=False)
        ready = fleet_view.readiness(repo)
        self.assertFalse(ready.ready)
        self.assertIn('commit tasks/ on main first', ' '.join(fleet_view.how_to_fix(ready)))
        subprocess.run(['git', '-C', str(repo), 'add', 'tasks'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'planning'], check=True)
        self.assertTrue(fleet_view.readiness(repo).ready)
        # Start must still reach its existing service-copy upgrade/restart path.
        with mock.patch.object(fleet_view.task_prepare, 'runner', return_value=dict(
                running=True, release='legacy-runner', reads_tasks=False)):
            self.assertTrue(fleet_view.readiness(repo).ready)
        (repo / 'sub').mkdir()
        self.assertIn(f'its repository root ({repo})', fleet_view.readiness(repo / 'sub').problems)
        subprocess.run(['git', '-C', str(repo), 'checkout', '-q', '-b', 'feature'], check=True)
        self.assertEqual(fleet_view.readiness(repo).problems, ['main checked out'])
        self.assertEqual(fleet_view.readiness(self.base).mark, 'not a repository')
        subprocess.run(['git', '-C', str(repo), 'checkout', '-q', 'main'], check=True)
        (repo / 'tasks/items/T-1.md').write_text('not a task record\n')
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qam', 'broken store'], check=True)
        ready = fleet_view.readiness(repo)
        self.assertFalse(ready.ready, 'a committed directory alone is not a valid task store')
        self.assertIn('INVALID_STORE', ' '.join(ready.problems))

    def test_models_come_from_pi_and_settings_keep_other_lines(self):
        pi = self.fake('pi', 'echo "provider  model  context"; echo "openrouter  deepseek/deepseek-v4.1-flash  128K"')
        self.assertEqual(fleet_view.models(pi), ['openrouter/deepseek/deepseek-v4.1-flash'])
        self.fake('pi', 'echo "No models available. Use /login to authenticate."')
        with self.assertRaisesRegex(ValueError, 'setup-portal'):
            fleet_view.models(pi)
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

    def test_planning_stop_questions_reach_ls_and_the_tui_without_rewriting_blockers(self):
        from pi_autowork import command
        repo, session = self.base / 'planned', self.base / 'session'
        repo.mkdir()
        session.mkdir()
        store_fixture.write_todo(repo, '## Now\n\n- [ ] T-1 — Build\n\n- [x] PLAN-1 — Plan the batch\n'
                                       '\n## Needs decision\n\n- [ ] CONTINUE — Continue the goal\n')
        (repo / 'BLOCKERS.md').write_text('# Not merged yet\n')
        (self.env / 'planned.env').write_text(f'PI_AUTOWORK_REPO={repo}\n')
        self.runner_state(str(repo), state='idle')
        state = self.state / 'planned'
        (state / 'session.json').write_text(json.dumps({'path': str(session)}))
        engine = ('<!-- pi-autowork:questions:start -->\n'
                  '### Q-T-1 — USER_INPUT — effort input — unblocks 1\n'
                  '- Needs: a key\n- Kind: held\n<!-- pi-autowork:questions:end -->\n')
        for prefix, body in ((engine, '- Task: PLAN-1 — Plan the batch\n- Question: Continue goal FIXTURE?\n'),
                             ('', '- Task: PLAN-1 — Plan the batch\n- Question: Continue goal FIXTURE?\n'),
                             ('', 'Goal FIXTURE needs more proof; continue?\n')):
            with self.subTest(engine=bool(prefix), body=body):
                (session / 'BLOCKERS.md').write_text(prefix + '\n### Q-PLAN-1 — Planning stopped\n\n' + body
                                                     + '\n### Other notes\n- Question: Not a planning stop\n')
                before = [(folder / 'BLOCKERS.md').read_bytes() for folder in (repo, session)]
                runner = self.collect('pi-autowork@planned.service loaded active running planned')['planned']
                expected = ['T-1', 'PLAN-1'] if prefix else ['PLAN-1']
                self.assertEqual([q.id for q in runner.questions], expected)
                planning = runner.questions[-1]
                self.assertEqual((planning.kind, planning.effort, planning.unblocks), ('decision', 'decision', 1))
                self.assertIn(body.splitlines()[-1].removeprefix('- Question: '), planning.needs)
                self.assertNotIn('Not a planning stop', planning.needs)
                rows = fleet_view.task_rows(runner, include_closed=True)
                self.assertEqual([r.task for r in fleet_view.task_view(rows, 'questions')], expected)
                self.assertEqual(sum(r.task == 'PLAN-1' for r in rows), 1)
                with contextlib.redirect_stdout(io.StringIO()) as output:
                    result = command.cmd_ls(type('Args', (), {'json': False, 'long': True})(), dict(
                        state_root=self.state, env_dir=self.env, systemctl=self.systemctl))
                self.assertEqual(result, 0)
                self.assertIn(f'{len(expected)} question', output.getvalue())
                self.assertEqual([(folder / 'BLOCKERS.md').read_bytes() for folder in (repo, session)], before)

    def test_wrapped_planning_fields_keep_choices_and_owner_context_without_granting_authority(self):
        repo = self.base / 'wrapped-planning'
        repo.mkdir()
        store_fixture.write_todo(repo, '## Now\n\n- [x] PLAN-1 — Plan the batch\n')
        text = ('# BLOCKERS\n\n## Active\n\n### Q-PLAN-1 — Planning stopped\n\n'
                '- Task: PLAN-1 — Plan the batch and\n'
                '  choose its continuation\n'
                '- Question: Supply the signed artifact,\n'
                '  arrange an exclusive-access handoff, or\n'
                '  defer the live qualification?\n'
                '- Owner decision: The earlier planning choice is resolved;\n'
                '  this does not authorize live work.\n'
                '- Evidence: unrelated field\n'
                '  must not leak into the question\n'
                '#### Details\n'
                '- Question: This detail is not another planning field\n'
                '  heading content must not leak either\n'
                '### Q-PLAN-2 — Planning stopped\n'
                '- Question: Which input?\n'
                '  - Another bullet is not a continuation\n'
                '    nor is its wrapped content\n')
        (repo / 'BLOCKERS.md').write_text(text)
        found = fleet_view.read_questions(repo)
        self.assertEqual([q.id for q in found], ['PLAN-1', 'PLAN-2'])
        self.assertEqual(found[0].needs,
                         'Task: PLAN-1 — Plan the batch and choose its continuation '
                         'Question: Supply the signed artifact, arrange an exclusive-access handoff, or '
                         'defer the live qualification? Owner decision: The earlier planning choice is resolved; '
                         'this does not authorize live work.')
        self.assertEqual(found[1].needs, 'Question: Which input?')
        self.assertEqual(found[0].kind, 'decision')
        self.assertEqual((repo / 'BLOCKERS.md').read_text(), text)

    def test_resolved_planning_stops_do_not_become_questions_for_the_owner(self):
        repo = self.base / 'resolved-planning'
        repo.mkdir()
        stop = ('### Q-PLAN-OLD — Planning stopped\n\n'
                '- Status: RESOLVED — existing deferral, not completed proof.\n'
                '- Task: CONTINUE — owner-only deferred continuation.\n')
        engine = '<!-- pi-autowork:questions:start -->\n<!-- pi-autowork:questions:end -->\n'
        for text in ('# BLOCKERS\n\n## Active\n' + engine + '\n## Resolved\n' + stop,
                     '# BLOCKERS\n\n## Active\n' + stop,
                     '# BLOCKERS\n\n## Active\n' + stop.replace('- Status: RESOLVED', '- Status: OPEN\n- Status: RESOLVED'),
                     '# BLOCKERS\n\n## Resolved\n' + stop.replace('- Status: RESOLVED — existing deferral, not completed proof.\n', '')):
            with self.subTest(text=text):
                (repo / 'BLOCKERS.md').write_text(text)
                found = fleet_view.read_questions(repo)
                self.assertEqual(found, [], 'resolved history is not an unanswered planning stop')
                runner = fleet_view.Runner('example', questions=found)
                self.assertEqual(fleet_view.question_summary(runner), '')
                self.assertEqual((repo / 'BLOCKERS.md').read_text(), text, 'reading does not rewrite history')

    def test_active_planning_questions_survive_resolved_history_and_session_fallback(self):
        repo, session, state = (self.base / name for name in ('questions-repo', 'questions-session', 'questions-state'))
        for folder in (repo, session, state):
            folder.mkdir()
        active = ('## Active\n### Q-PLAN-NEW — Planning stopped\n'
                  '- Status: UNRESOLVED\n- Question: Which newly unavailable input?\n')
        history = ('## Resolved\n### Q-PLAN-OLD — Planning stopped\n'
                   '- Status: RESOLVED\n- Question: Previous continuation?\n')
        (repo / 'BLOCKERS.md').write_text('# BLOCKERS\n' + history + active)
        (session / 'BLOCKERS.md').write_text('# BLOCKERS\n' + history)
        (state / 'session.json').write_text(json.dumps({'path': str(session)}))
        found = fleet_view.read_questions(repo, state)
        self.assertEqual([q.id for q in found], ['PLAN-NEW'])
        self.assertIn('newly unavailable input', found[0].needs)
        (repo / 'BLOCKERS.md').write_text(history + active.replace(
            '- Status: UNRESOLVED', '- Status: RESOLVED\n- Status: UNRESOLVED'))
        self.assertEqual([q.id for q in fleet_view.read_questions(repo, state)], ['PLAN-NEW'])
        # An explicitly empty engine block in the preferred session is still authoritative.
        (session / 'BLOCKERS.md').write_text('<!-- pi-autowork:questions:start -->\n'
                                           '<!-- pi-autowork:questions:end -->\n' + history)
        self.assertEqual(fleet_view.read_questions(repo, state), [])

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
             'Working — 1 of 1 worker busy; 15 commits waiting'),
            (R('a', state='working', running=1, lanes=[L('T1', 'implementing'), L('M', 'integrated')]),
             'Working — 1 worker busy; 1 mergeable'),
            (R('a', state='blocked', held=[('T-2', 'conflict')]), 'Blocker — T-2: Conflict · Agent repair'),
            (R('a', state='working', running=1, lanes=[L('T1', 'implementing')], gate='load average 27 >= 24 CPUs',
               questions=[Q('X', 'quick', 4, 'answer it')]),
             'Working — 1 worker busy; no more start: load average 27 >= 24 CPUs; 1 question for you'),
            (R('a', state='stalled', minutes=42, questions=[Q('TOOLSET-157-cd', 'quick', 4, 'widen Touches')]),
             'Waiting on you — 1 question, easiest TOOLSET-157-cd (unblocks 4): widen Touches'),
            (R('a', state='stalled', minutes=42, roots=[root]),
             "Waiting — TASK-140 (held: changed another task's files; offered again once they are free, holds 23)"),
            (R('a', state='blocked', waiting=2,
               waiting_groups=[{'label': 'wait for deferred D', 'count': 2}]),
             'Waiting — 2 wait for deferred D'),
            (R('a', state='stalled', waiting=3,
               waiting_groups=[{'label': 'wait for TASK-140 (overlapping files)', 'count': 3}]),
             'Waiting — 3 wait for TASK-140 (overlapping files)'),
            (R('a', state='blocked', waiting=1,
               waiting_groups=[{'label': 'on dependencies', 'count': 1}]),
             'Waiting — 1 on dependencies'),
            (R('a', state='blocked', roots=[{'id': 'D', 'kind': 'outside', 'deferred': True, 'blocks': 2}]),
             'Waiting — D (deferred by owner, holds 2)'),
            (R('a', state='blocked', minutes=3, blocker='no usable model: quota'), 'Stuck 3m — no usable model: quota'),
            (R('a', state='blocked', gate='memory 2900 MB available, need 6000 MB'),
             'Host busy — memory 2900 MB available, need 6000 MB'),
            (R('a', state='restarting', restarting='onto 0c41776'), 'Restarting onto 0c41776'),
            (R('a', state='restarting', restarting='service'), 'Restarting'),
            (R('a', state='paused'), 'Paused — p resumes it'),
            (R('a', state='not running'), 'Not running — p starts its service'),
            (R('a', state='idle', questions=[Q('T-1', 'decision', 1, 'choose a target')]),
             'Waiting on you — 1 question, easiest T-1 (unblocks 1): choose a target'),
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
        # `autowork plan` (the TUI's Plan) is /plan_for_me with Docs Sync, in the same spelling.
        claude, pi = fleet_view.plan_prompt(['claude'], '/r'), fleet_view.plan_prompt(['pi'], '/r')
        self.assertTrue(claude.startswith('/autowork:plan-for-me Plan the work of /r'), claude)
        self.assertIn('/autowork:docs-sync', claude)
        self.assertTrue(pi.startswith('/plan_for_me Plan the work of /r'), pi)
        self.assertIn('/docs_sync', pi)
        self.assertIn('Do not invent intent', pi)

    def test_a_runner_without_tasks_offers_planning_in_an_agent(self):
        repo = self.base / 'unplanned'
        repo.mkdir()
        keys = lambda runner, **kw: {a.key: a for a in fleet_view.actions(runner, command='aw', script='pa.sh', **kw)}
        unplanned = fleet_view.Runner(name='unplanned', repo=str(repo), prepare_state='none')
        backlog = keys(unplanned, agent=['claude'])['b']
        self.assertEqual((backlog.label, backlog.argv, backlog.interactive),
                         ('Backlog', ['aw', 'plan', str(repo)], True))
        self.assertNotIn('b', keys(unplanned), 'no agent, no planning session')
        planned = fleet_view.Runner(name='planned', repo=str(repo), prepare_state='converted')
        self.assertNotIn('b', keys(planned, agent=['claude']), 'a prepared store is planned through its tasks')

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
        # The finished commit waiting to land sorts below the task being worked on, whatever its name.
        (slots / 'T-0.json').write_text(json.dumps({'task_id': 'T-0', 'state': 'reported', 'attempt': 1}))
        self.assertEqual([lane.task for lane in fleet_view.lanes(runner)], ['T-1', 'T-0', 'T-2'])

    def test_a_workers_actions_read_as_a_log_oldest_first_with_their_times(self):
        """The worker view listed its last 10 actions newest first: upside down for a log, and
        too short to follow what a 15-minute attempt did."""
        state = self.base / 'state' / 'key'
        (state / 'sessions').mkdir(parents=True)
        start = time.time() - 600
        events = [{'type': 'message', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%S.000Z', time.gmtime(start + i)),
                   'message': {'role': 'assistant', 'content': [
                       {'type': 'toolCall', 'name': 'bash', 'arguments': json.dumps({'command': f'echo step {i}'})}]}}
                  for i in range(40)]
        (state / 'sessions' / '2026-10-21T08-00-00-000Z_pi-autowork-T-1-attempt-1.jsonl').write_text(
            '\n'.join(json.dumps(e) for e in events) + '\n')
        runner = fleet_view.Runner(name='repo', state_dir=str(state))
        log = fleet_view.action_log(runner, 'T-1')
        self.assertEqual(len(log), 40)  # far more than the old 10
        self.assertEqual([text for text, _, _ in log], [fleet_view.doing_text(f'bash: echo step {i}') for i in range(40)])
        self.assertEqual([int(at) for _, _, at in log], [int(start) + i for i in range(40)])
        self.assertEqual(fleet_view.action_log(runner, 'T-1', n=3), log[-3:])  # the newest three, still in order
        self.assertEqual(fleet_view.recent_actions(runner, 'T-1', n=2), [(t, a) for t, a, _ in log[-2:]])

    def test_the_question_count_says_how_it_relates_to_the_blockers(self):
        """Blocker 1 in the table and '2 questions for you' below read as a contradiction: one of
        the two was a question about the runner that blocks no task."""
        Q = fleet_view.Question
        runner = fleet_view.Runner(name='a', held=[('T-8', 'conflict')],
                                   questions=[Q('T-8', 'investigate', 1, 'merge limit'), Q('FULL-CHECK', 'input', 0, 'no gate')])
        self.assertEqual(fleet_view.question_summary(runner),
                         '2 questions for you in BLOCKERS.md: 1 for the blocker above, 1 that blocks no task')
        self.with_inventory(runner, [('T-8', 'held', 'conflict', '')])
        self.assertEqual(fleet_view.task_counts(runner)[3], 1)  # the Blocker count is still held tasks
        runner.questions = runner.questions[:1]
        self.assertEqual(fleet_view.question_summary(runner), '1 question for you in BLOCKERS.md')  # nothing to explain
        runner.questions = [Q('W-1', 'quick', 3, 'claim'), Q('W-2', 'quick', 1, 'claim'), Q('X', 'input', 0, 'setup')]
        self.assertEqual(fleet_view.question_summary(runner),
                         '3 questions for you in BLOCKERS.md: 2 on waiting tasks, 1 that blocks no task')
        self.assertEqual(fleet_view.question_summary(fleet_view.Runner(name='b')), '')

    def test_a_review_that_died_is_not_verifying(self):
        """Three tasks read "verifying" for 13 to 25 hours after their reviews died: the runner log's
        last word is not a live review."""
        state = self.base / 'state' / 'key'
        proc = self.base / 'proc'
        for pid, argv in ((10, ['python3', 'worker.py', '--verify', str(state), 'A']),
                          (11, ['bash', 'pa.sh', '--verify-batch', str(state), '/s', 'pa.sh', 'B', 'C']),
                          (12, ['python3', 'worker.py', '--verify', '/elsewhere', 'D'])):
            (proc / str(pid)).mkdir(parents=True)
            (proc / str(pid) / 'cmdline').write_bytes('\0'.join(argv).encode() + b'\0')
        state.mkdir(parents=True)
        self.assertEqual(fleet_view.reviews(str(state), proc=str(proc)), ({'A'}, {'B', 'C'}))
        repo = self.base / 'repo'
        subprocess.run(['git', 'init', '-q', str(repo)], check=True)
        slots = repo / '.git' / 'autowork-execution' / 'slots'
        slots.mkdir(parents=True)
        for task in 'ABE':
            (slots / f'{task}.json').write_text(json.dumps({'task_id': task, 'state': 'integrating', 'attempt': 1}))
        (state / 'runner.log').write_text(''.join(f'2026-10-20T14:00:00-06:00 {t}: verifying\n' for t in 'ABE'))
        runner = fleet_view.Runner(name='repo', repo=str(repo), state_dir=str(state))
        with mock.patch.object(fleet_view, 'reviews', return_value=({'A'}, {'B'})):
            found = {lane.task: fleet_view.status(lane) for lane in fleet_view.lanes(runner)}
        self.assertEqual(found, {'A': ('Active', 'Verifying'), 'B': ('Waiting', 'Batch check'),
                                 'E': ('Waiting', 'Merge turn')})
        # A finished commit a running batch is checking reads as in the batch check, not idle.
        for task in 'FG':
            (slots / f'{task}.json').write_text(json.dumps({'task_id': task, 'state': 'reported', 'attempt': 1}))
        with mock.patch.object(fleet_view, 'reviews', return_value=(set(), {'F'})):
            found = {lane.task: fleet_view.status(lane) for lane in fleet_view.lanes(runner)}
        self.assertEqual((found['F'], found['G']), (('Waiting', 'Batch check'), ('Waiting', 'Implemented')))

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
                         f'/py {tui_web.TUI} --command /bin/autowork --script /opt/pa.sh --mouse')
        self.assertTrue(tui_web.command('autowork', 'pa.sh', view_only=True).endswith('--view-only'))

    @unittest.skipUnless(shutil.which('uv'), 'uv is not installed')
    def test_implemented_is_waiting_not_mergeable(self):
        """TOOLSET-289-71: an implemented commit has not been checked yet; "Land" counted it as ready."""
        L = fleet_view.Lane
        self.assertEqual(fleet_view.status(L('T', 'implemented')), ('Waiting', 'Implemented'))
        self.assertEqual(fleet_view.status(L('T', 'waiting to integrate')), ('Waiting', 'Merge turn'))
        runner = fleet_view.Runner(name='a', lanes=[L('A', 'implementing'), L('B', 'implemented'), L('C', 'verifying')],
                                   waiting=2, held=[('D', 'conflict')])
        self.with_inventory(runner, [('A', 'running', '', ''), ('B', 'reported', '', ''),
                                     ('C', 'integrating', '', ''), ('D', 'held', 'conflict', ''),
                                     ('W-1', 'waiting', '', 'dependency'), ('W-2', 'waiting', '', 'dependency')])
        self.assertEqual(fleet_view.task_counts(runner), (2, 0, 3, 1, 0, 6))

    def test_total_counts_every_open_task(self):
        """The fleet's Total read 12 for a store of 20 open tasks: three a restart had paused were in
        no column, and four in Needs decision never reach the engine's status."""
        from pi_autowork import health
        with tempfile.TemporaryDirectory() as folder:
            snapshot = {'outcome': 'PARALLEL_STATUS', 'active_workers': 0, 'roots': [],
                        'tasks': [{'task': 'A', 'state': 'waiting'}, {'task': 'B', 'state': 'interrupted', 'paused': True}]}
            health.update(folder, snapshot, now=1000)
            self.assertEqual(json.loads((Path(folder) / 'status.json').read_text())['waiting'], 2)
        runner = fleet_view.Runner(name='a', waiting=2, decisions=4)
        self.with_inventory(runner, [('A', 'waiting', '', 'dependency'), ('B', 'interrupted', '', '')],
                            decisions=['D-1', 'D-2', 'D-3', 'D-4'])
        self.assertEqual(fleet_view.task_counts(runner), (0, 0, 2, 0, 4, 6))
        self.assertEqual(fleet_view.needs(fleet_view.Runner(name='a', state='idle', decisions=4)),
                         '4 tasks in Needs decision')

    def test_waiting_row_adds_up_to_the_waiting_count(self):
        """TOOLSET-351-54bd774c: the Waiting row read '8: 6 on dependencies · 2 …' beside '15 waiting':
        it left out commits in flight and overlap holds. Every waiting task is in a labelled part."""
        L = fleet_view.Lane
        runner = fleet_view.Runner(name='a', lanes=[L('A', 'implemented'), L('B', 'implemented'),
                                                    L('C', 'waiting to integrate'), L('D', 'verifying')],
                                   waiting=5, waiting_groups=[{'count': 3, 'label': 'on dependencies'}],
                                   held=[('E', 'overlap'), ('F', 'conflict')], decisions=2)
        self.with_inventory(runner, [('A', 'reported', '', ''), ('B', 'reported', '', ''),
                                     ('C', 'integrating', '', ''), ('D', 'integrating', '', ''),
                                     *[(f'W-{i}', 'waiting', '', 'on dependencies' if i < 3 else 'waiting for another reason')
                                       for i in range(5)],
                                     ('E', 'held', 'overlap', ''), ('F', 'held', 'conflict', '')],
                            decisions=['Q-1', 'Q-2'])
        active, mergeable, waiting, blocker, decision, total = fleet_view.task_counts(runner)
        self.assertEqual((active, mergeable, waiting, blocker, decision, total), (1, 0, 9, 1, 2, 13))
        self.assertEqual(sum(n for n, _ in fleet_view.waiting_parts(runner)), waiting)
        self.assertEqual(fleet_view.waiting_detail(runner),
                         "9: 2 implemented, waiting for review · 1 reviewed, waiting for their merge turn · "
                         "3 on dependencies · 2 waiting for another reason · 1 waiting for another task's files")
        self.assertEqual(fleet_view.waiting_detail(fleet_view.Runner(name='b')), '')

    def test_stopped_waits_are_blockers(self):
        """TOOLSET-352-8337d438: a waiting task stopped behind a question or an outside condition is a
        Blocker; the columns still add up to Total and the Blocker row names what stops them."""
        runner = fleet_view.Runner(name='a', waiting=2, stopped=1, held=[('B', 'conflict'), ('E', 'overlap')],
                                   stopped_groups=[{'label': 'Q-1 (outside condition or task not in Now/Next)',
                                                    'count': 1, 'tasks': ['A']}])
        self.with_inventory(runner, [('B', 'held', 'conflict', ''),
                                     ('A', 'waiting', '', 'Q-1 (outside condition or task not in Now/Next)'),
                                     ('W-1', 'waiting', '', 'dependency'), ('W-2', 'waiting', '', 'dependency'),
                                     ('E', 'held', 'overlap', '')])
        self.assertEqual(fleet_view.task_counts(runner), (0, 0, 3, 2, 0, 5))
        self.assertEqual(fleet_view.blocker_parts(runner),
                         '2: B Conflict · Agent repair · A Q-1 (outside condition or task not in Now/Next)')
        self.assertEqual(fleet_view.blocker_parts(fleet_view.Runner(name='b', held=[('E', 'overlap')])), '')

    def test_mergeable_needs_passed_gates(self):
        """Only an integrated commit (checks and review passed, on the session branch) is Mergeable;
        a commit being verified or merged is Active."""
        L = fleet_view.Lane
        self.assertEqual(fleet_view.status(L('T', 'integrated')), ('Mergeable', 'Verified'))
        for phase, detail in (('verifying', 'Verifying'), ('integrating', 'Merging'), ('landing', 'Merging'),
                              ('starting', 'Starting'), ('running', 'Implementing')):
            self.assertEqual(fleet_view.status(L('T', phase)), ('Active', detail), phase)
        runner = fleet_view.Runner(name='a', lanes=[L('A', 'integrated'), L('B', 'verifying')])
        self.with_inventory(runner, [('A', 'integrated', '', ''), ('B', 'integrating', '', '')])
        self.assertEqual(fleet_view.task_counts(runner), (1, 1, 0, 0, 0, 2))

    def test_blocker_names_its_resolver(self):
        """A hold is the runner's repair unless the owner has an open question for it."""
        self.assertEqual(fleet_view.blocker_detail('conflict'), 'Conflict · Agent repair')
        self.assertEqual(fleet_view.blocker_detail('validation'), 'Validation · Agent repair')
        self.assertEqual(fleet_view.blocker_detail('blocker', asked=True), 'Blocker · Needs you')
        self.assertEqual(fleet_view.blocker_detail(None), 'Held · Agent repair')
        # An overlap hold is lifted by the engine itself once the files are free: it waits.
        runner = fleet_view.Runner(name='a', held=[('A', 'overlap'), ('B', 'conflict')])
        self.with_inventory(runner, [('A', 'held', 'overlap', ''), ('B', 'held', 'conflict', '')])
        self.assertEqual(fleet_view.task_counts(runner), (0, 0, 1, 1, 0, 2))

    @unittest.skipUnless(shutil.which('uv'), 'uv is not installed')
    def test_the_tui_drives_the_same_actions_headless(self):
        """Textual is not a runner dependency: the pilot runs under uv, from its cache only."""
        result = subprocess.run(['uv', 'run', '--offline', '--quiet', '--no-project', '--with', 'textual==8.2.8',
                                 'python3', str(PILOT)], capture_output=True, text=True, timeout=180)
        if result.returncode == 2 and 'textual' in result.stderr.lower() and 'offline' in result.stderr.lower():
            self.skipTest('textual==8.2.8 is not in the uv cache (offline)')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn('PILOT OK', result.stdout)


class ActionStyleTests(unittest.TestCase):
    """TOOLSET-343-9356fe48: each action line is colored by its kind and fits one line."""

    def test_each_kind_of_action_gets_its_color(self):
        cases = {
            'editing pi-autowork/x.py': 'cyan',
            fleet_view.doing_text('bash: python3 scripts/check.py tests/test_x.py'): 'yellow',
            fleet_view.doing_text('bash: rg -n foo src'): 'dim',
            fleet_view.doing_text('grep: foo'): 'dim',
            fleet_view.doing_text('bash: ruff check .'): 'dim',
            fleet_view.doing_text('bash: git status --short'): 'blue',
            fleet_view.doing_text('bash: python3 - <<PY'): 'blue',
            fleet_view.doing_text('subagent: start'): 'magenta',
            fleet_view.doing_text('subagent_wait: x'): 'magenta',
            'reviewer: editing a.py': 'cyan',
            'landing: passed in its batch': 'green',
            'said: PI_AUTOWORK_VERIFY: pass — acceptance met': 'bold green',
            'said: PI_AUTOWORK_RESULT: completed, then a sentence': 'bold green',
            'said: PI_AUTOWORK_VERIFY: fail — the timing cause remains': 'bold red',
            'said: PI_AUTOWORK_RESULT: blocked — needs a decision': 'bold red',
            'reviewer: committed as `d3ce7ecc`. Notes follow': 'bold',
            'said: Committed TOOLSET-1 locally': 'bold',
            'something new': '',
        }
        for line, style in cases.items():
            with self.subTest(line=line):
                self.assertEqual(fleet_view.action_style(line), style)

    def test_task_states_get_their_colors(self):
        row = lambda **kw: fleet_view.TaskRow(**{**dict(task='T', short='s', section='Next', state='ready',
                                                        kind='ready', why=''), **kw})
        cases = ((row(kind='working', state='implementing'), 'bold green'),
                 (row(kind='waiting', state='waiting'), 'bold yellow'),
                 (row(kind='held', state='held'), 'bold red'),
                 (row(kind='waiting', state='failed', why='merge conflict'), 'bold red'),
                 (row(section='Needs decision', state='open'), 'bold magenta'),
                 (row(state='done'), 'dim'), (row(), ''))
        for value, style in cases:
            with self.subTest(row=value):
                self.assertEqual(fleet_view.state_style(value), style)

    def test_a_long_action_fits_one_line_with_an_ellipsis(self):
        long = 'running tests: ' + ' '.join(f'tests/test_{i}.py' for i in range(30))
        fitted = fleet_view.fit_line(long, 60)
        self.assertEqual(len(fitted), 60)
        self.assertTrue(fitted.endswith('…'))
        self.assertNotIn('\n', fleet_view.fit_line('a\nb  c', 80))
        self.assertEqual(fleet_view.fit_line('short', 60), 'short')
        self.assertEqual(fleet_view.fit_line(long, 0), ' '.join(long.split()))  # no width: whole


if __name__ == '__main__':
    unittest.main()
