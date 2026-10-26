"""Runner health: status file, one stall announcement per episode, fleet view."""
import json
import os
from pathlib import Path
import sys
import subprocess
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import health  # noqa: E402
from pi_autowork.processes import start_time  # noqa: E402

HELD = {'id': 'T-9', 'kind': 'held', 'blocks': 4, 'cause': 'blocker', 'reason': 'needs a device'}


def snapshot(*, workers=0, queue=0, waiting=('A',), roots=(HELD,)):
    tasks = [{'task': t, 'state': 'waiting', 'blocked_by': ['T-9']} for t in waiting]
    tasks.append({'task': 'T-9', 'state': 'held', 'cause': 'blocker', 'reason': 'needs a device'})
    return {'outcome': 'PARALLEL_STATUS', 'active_workers': workers, 'integration_queue': queue,
            'tasks': tasks, 'roots': list(roots)}


class HealthTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.state = Path(self.temp.name)

    def status(self):
        return json.loads((self.state / 'status.json').read_text())

    def test_a_stall_is_announced_once_after_the_threshold(self):
        self.assertIsNone(health.update(self.state, snapshot(), now=1000))
        self.assertEqual(self.status()['state'], 'blocked')
        self.assertIsNone(health.update(self.state, snapshot(), now=1000 + 1799))
        line = health.update(self.state, snapshot(), now=1000 + 1800)
        self.assertEqual(line, 'STALLED for 30 min: no task can run. Root blockers: '
                               'T-9 (held for a person: its worker reported a blocker, holds 4). '
                               'See pi-autowork.sh --status.')
        self.assertEqual(self.status()['state'], 'stalled')
        self.assertIsNone(health.update(self.state, snapshot(), now=1000 + 4000))  # not again
        self.assertEqual(self.status()['since'], 1000)

    def test_exhausted_review_work_is_engineering_not_a_person(self):
        """Running out of reviewer rework does not turn a defect into an owner decision."""
        engineering = {'id': 'T-8', 'kind': 'held', 'cause': 'reviewed_twice', 'blocks': 1,
                       'tasks': ['A'], 'reason': 'validation failed; its one rework failed too'}
        self.assertFalse(health.needs_person(engineering))
        self.assertTrue(health.needs_person(HELD))
        health.update(self.state, snapshot(waiting=('A',), roots=(engineering,)), now=0)
        status = self.status()
        self.assertEqual((status['stopped'], status['waiting']), (1, 0))
        self.assertEqual(status['stopped_groups'][0]['tasks'], ['A'])
        # It becomes a visible engineering stall, never a person's question.
        line = health.update(self.state, snapshot(waiting=('A',), roots=(engineering,)), now=1800)
        self.assertIn('engineering hold', line)
        self.assertNotIn('held for a person', line)
        self.assertEqual(self.status()['state'], 'stalled')

    def test_action_required_is_separate_from_owner_required(self):
        for kind, cause in (('held', 'reviewed_twice'), ('held', 'crash'),
                            ('contract', None), ('cycle', None), ('runner', None)):
            with self.subTest(kind=kind, cause=cause):
                root = dict(id='T-8', kind=kind, cause=cause, blocks=1, tasks=['A'])
                self.assertFalse(health.needs_person(root))
                ids, groups = health.stopped([dict(task='A', state='waiting'),
                                             dict(task='B', state='waiting')], [root])
                self.assertEqual(ids, {'A', 'B'} if kind == 'runner' else {'A'})
                self.assertTrue(groups)

    def test_holds_that_only_own_each_others_files_are_named_a_deadlock(self):
        """TOOLSET-157-cd: two commits held for overlap looked like work for a person."""
        overlap = dict(HELD, cause='overlap')
        health.update(self.state, snapshot(roots=(overlap,)), now=0)
        line = health.update(self.state, snapshot(roots=(overlap,)), now=1800)
        self.assertTrue(line.startswith('STALLED for 30 min: no task can run (held-ownership deadlock; '
                                        'resolving itself). Root blockers: T-9 (held: '
                                        "changed another task's files; offered again once they are free"), line)
        mixed = health.update(self.state, snapshot(roots=(overlap, {'id': 'T-5', 'kind': 'claim', 'blocks': 1})),
                              now=1900)
        self.assertNotIn('deadlock', mixed)

    def test_a_wait_that_cannot_clear_by_itself_is_stopped_not_waiting(self):
        """TOOLSET-352-8337d438: a blocked runner showed Blocker 0 and its stuck task as Waiting. A
        wait ending at a root that needs a person is stopped; one behind an overlap hold still waits."""
        outside = {'id': 'Q-1', 'kind': 'outside', 'blocks': 1, 'tasks': ['A']}
        overlap = {'id': 'T-7', 'kind': 'held', 'cause': 'overlap', 'blocks': 1, 'tasks': ['B']}
        snap = snapshot(waiting=('A', 'B', 'C'), roots=(outside, overlap))
        health.update(self.state, snap, now=0)
        status = json.loads((Path(self.state) / 'status.json').read_text())
        self.assertEqual((status['waiting'], status['stopped']), (2, 1))
        self.assertEqual(status['stopped_groups'],
                         [{'label': 'Q-1 (outside condition or task not in Now/Next)', 'count': 1, 'tasks': ['A']}])
        self.assertEqual(sum(g['count'] for g in status['waiting_groups']), 2)
        # A runner blocker stops every waiting task.
        health.update(self.state, snapshot(waiting=('A', 'B'), roots=()), now=10, runner={'blocker': 'no model'})
        status = json.loads((Path(self.state) / 'status.json').read_text())
        self.assertEqual((status['waiting'], status['stopped']), (0, 2))

    def test_waiting_tasks_are_grouped_by_why_they_wait(self):
        """TOOLSET-166-b4: the view shows why tasks wait without calling the engine."""
        reasons = ['overlapping paths with TASK-140', 'overlapping paths with held TASK-140',
                   'dependency: TASK-1', 'dependency: TASK-2, TASK-3', 'priority waits for TASK-9',
                   'resource gate: load average 27.16 >= 24 CPUs', 'all 8 worker slots busy', 'something new',
                   'wait for deferred TASK-D']
        tasks = [{'task': f'W{i}', 'state': 'waiting', 'reason': r} for i, r in enumerate(reasons)]
        tasks.append({'task': 'R', 'state': 'running'})
        groups = health.waiting_groups(tasks)
        self.assertEqual([(g['label'], g['count']) for g in groups[:2]],
                         [('wait for TASK-140 (overlapping files)', 2), ('on dependencies', 2)])
        self.assertEqual(sum(g['count'] for g in groups), len(reasons))
        labels = {g['label'] for g in groups}
        self.assertTrue({'wait behind TASK-9, which runs alone', 'waiting for the host (load 27.16 on 24 CPUs)',
                         'for a free worker slot', 'something new', 'wait for deferred TASK-D'} <= labels, labels)
        health.update(self.state, dict(snapshot(), tasks=tasks, max_workers=8), now=0)
        self.assertEqual(self.status()['waiting_groups'], groups)
        self.assertEqual(self.status()['max_workers'], 8)
        # Every task, for the Tasks window: a group keeps only 20.
        many = [{'task': f'D{i}', 'state': 'waiting', 'reason': 'dependency: TASK-1'} for i in range(25)]
        health.update(self.state, dict(snapshot(), tasks=many + [{'task': 'H', 'state': 'held', 'cause': 'conflict',
                                                                   'reason': 'merge conflict'}]), now=0)
        self.assertEqual(len(self.status()['waiting_groups'][0]['tasks']), 20)
        self.assertEqual(len(self.status()['tasks']), 26)
        self.assertEqual(self.status()['tasks'][-1], ['H', 'held', 'conflict', 'merge conflict'])

    def test_only_load_waits_are_host_waiting_not_blocked_or_stalled(self):
        from pi_autowork import fleet_view
        reason = 'resource gate: load average 27.16 >= 24 CPUs'
        snap = {'outcome': 'PARALLEL_STATUS', 'active_workers': 0, 'integration_queue': 0,
                'tasks': [dict(task=t, state='waiting', reason=reason) for t in ('A', 'B')], 'roots': []}
        runner = dict(repo='/x/repo', pid=os.getpid(), start_time=start_time(os.getpid()))
        folder = self.state / 'repo'
        folder.mkdir()
        (folder / 'runner.json').write_text(json.dumps(runner))
        for now in (1000, 1000 + health.STALL_AFTER, 1000 + 2 * health.STALL_AFTER):
            self.assertIsNone(health.update(folder, snap, now=now, runner=runner))
            status = json.loads((folder / 'status.json').read_text())
            self.assertEqual((status['state'], status['since']), ('waiting for the host', 1000))
            self.assertEqual(status['stall_roots'], [])
        row, = health.fleet(self.state, now=now, service=lambda name: 'active')
        text = 'waiting for the host (load 27.16 on 24 CPUs)'
        self.assertIn(text, health.render([row], now=now))
        view = fleet_view.Runner(name='repo', state=row['state'], waiting_groups=row['waiting_groups'])
        self.assertEqual(fleet_view.verdict(view), (text, 'bold yellow'))
        self.assertEqual(view.color, 'yellow')
        # A host wait must not hide a different reason, an integration hold or a runner failure.
        for other in ('resource gate: 1000 MB available, need 3000 MB for one more worker',
                      'resource gate: 1.0 GB free on the repository disk, need 20 GB', 'dependency: C'):
            with self.subTest(reason=other):
                mixed = dict(snap, tasks=snap['tasks'] + [dict(task='C', state='waiting', reason=other)])
                self.assertEqual(health.classify(mixed), 'blocked')
        self.assertEqual(health.classify(snap, paused=True), 'paused')
        self.assertEqual(health.classify(dict(snap, active_workers=1)), 'working')
        self.assertEqual(health.classify(dict(snap, integration_queue=1), stuck=1), 'blocked')
        failed = dict(runner, blocker='no usable model')
        health.update(folder, snap, now=now + 1, runner=failed)
        self.assertIsNotNone(health.update(folder, snap, now=now + 1 + health.STALL_AFTER, runner=failed))

    def test_merge_backlog_is_a_wait_with_one_pause_and_resume_announcement(self):
        snap = snapshot(queue=3, roots=())
        snap['tasks'] = [{'task': 'F', 'state': 'waiting',
                          'reason': 'wait for 3 finished commits to merge', 'blocked_by': []}]
        snap['merge_backlog'] = {'paused': True, 'count': 3,
                                 'reason': 'waiting to integrate until another session leaves the main checkout: pid 123 pi'}
        line = health.update(self.state, snap, now=0)
        self.assertIn('Fresh dispatch paused: wait for 3 finished commits to merge', line)
        self.assertIn('pid 123 pi', line)
        self.assertEqual(self.status()['waiting_groups'],
                         [{'label': 'wait for 3 finished commits to merge', 'count': 1, 'tasks': ['F']}])
        self.assertEqual(self.status()['stall_roots'], [])
        self.assertIsNone(health.update(self.state, snap, now=1900))
        # An unavailable status is not a resume and does not reset the announcement.
        self.assertIsNone(health.update(self.state, {'outcome': 'BUSY'}, now=2000))
        self.assertIsNone(health.update(self.state, snap, now=2100))
        snap['merge_backlog'] = {'paused': False, 'count': 2}
        snap['tasks'] = [{'task': 'F', 'state': 'running'}]
        snap['active_workers'] = 1
        line = health.update(self.state, snap, now=2200)
        self.assertIn('Fresh dispatch resumed', line)
        self.assertIsNone(health.update(self.state, snap, now=2300))

    def test_an_unanswered_status_read_shows_snapshot_age_and_keeps_the_stall_clock(self):
        """A busy lock must not leave yesterday's rows looking like a current observation."""
        from pi_autowork import fleet_view
        folder = self.state / 'repo'
        folder.mkdir()
        runner = dict(repo='/x/repo', pid=os.getpid(), start_time=start_time(os.getpid()))
        (folder / 'runner.json').write_text(json.dumps(runner))
        health.update(folder, dict(snapshot(), task_source={'observed_at': 1000}), now=1000, runner=runner)
        busy = {'outcome': 'ACTION_REQUIRED', 'reason': 'Repository execution lock is held by a live operation.'}
        for now in (2000, 2500):
            self.assertIsNone(health.update(folder, busy, now=now, runner=runner))
            record = json.loads((folder / 'status.json').read_text())
            self.assertEqual((record['state'], record['since']),
                             ('blocked' if now == 2000 else 'unavailable', 1000))
            self.assertEqual((record['snapshot_at'], record['status_unavailable_since']), (1000, 2000))
            self.assertEqual(record['snapshot_age_seconds'], now - 1000)
            self.assertIn('status unavailable since 2000:', record['status_error'])
            self.assertIn(busy['reason'], record['status_error'])
        row = health.fleet(self.state, now=2600, service=lambda name: 'active')[0]
        self.assertEqual(row['state'], 'unavailable')
        self.assertIn('last snapshot 1600s old', health.render([row], now=2600))
        systemctl = self.state / 'systemctl'
        systemctl.write_text('#!/bin/sh\n[ "$2" != list-units ] || '
                             'echo "pi-autowork@repo.service loaded active running"\nexit 0\n')
        systemctl.chmod(0o755)
        view, = fleet_view.collect(self.state, self.state, systemctl=str(systemctl), now=2600)
        self.assertEqual((view.state, view.minutes), ('unavailable', 26))  # TUI's persistent State column
        self.assertIn('last snapshot 1600s old', fleet_view.verdict(view)[0])
        self.assertIsNotNone(health.update(folder, dict(snapshot(), task_source={'observed_at': 2800}),
                                           now=2800, runner=runner))
        record = json.loads((folder / 'status.json').read_text())
        self.assertEqual((record['state'], record['since']), ('stalled', 1000))
        self.assertNotIn('status_error', record)
        (folder / 'status.json').unlink()
        health.update(folder, busy, now=3000, runner=runner)
        record = json.loads((folder / 'status.json').read_text())
        self.assertIsNone(record['snapshot_at'])
        self.assertIn('no successful snapshot', record['status_error'])

    def test_one_failed_read_preserves_working_but_repeated_failures_are_unavailable(self):
        folder = self.state / 'repo'
        folder.mkdir()
        runner = dict(repo='/x/repo', pid=os.getpid(), start_time=start_time(os.getpid()))
        (folder / 'runner.json').write_text(json.dumps(runner))
        busy = {'outcome': 'BUSY', 'reason': 'writer lock busy'}
        working = dict(snapshot(workers=1), task_source={'observed_at': 1000})
        health.update(folder, working, now=1000, runner=runner)
        for now, reply, expected, failed_since in (
                (1010, busy, 'working', 1010), (1020, working, 'working', None),
                (1030, busy, 'working', 1030), (1040, busy, 'unavailable', 1030),
                (1050, busy, 'unavailable', 1030), (1060, working, 'working', None)):
            with self.subTest(now=now):
                health.update(folder, reply, now=now, runner=runner)
                record = json.loads((folder / 'status.json').read_text())
                self.assertEqual((record['state'], record['since']), (expected, 1000))
                self.assertEqual(record.get('status_unavailable_since'), failed_since)
                row, = health.fleet(self.state, now=now, service=lambda name: 'active')
                self.assertEqual(row['state'], expected)
                if failed_since is not None:
                    self.assertLess(record['snapshot_at'], now)
                    self.assertIn('last snapshot', row['blocker'])
                else:
                    self.assertNotIn('status_error', record)

    def test_cached_and_failed_reads_keep_source_time_and_legacy_time_unknown(self):
        source = dict(workspace='/session/repo', repository_identity='/repo/.git',
                      revision='committed-source', observed_at=100)
        snap = dict(snapshot(workers=1), task_source=source)
        busy = {'outcome': 'BUSY', 'reason': 'writer lock busy'}
        for now, reply, state in ((110, snap, 'working'), (120, snap, 'working'),
                                  (130, busy, 'working'), (140, busy, 'unavailable'),
                                  (150, snap, 'working')):
            with self.subTest(now=now):
                health.update(self.state, reply, now=now)
                value = self.status()
                self.assertEqual(value['task_source'], source)
                self.assertEqual(value['snapshot_at'], 100)
                self.assertEqual(value['snapshot_age_seconds'], now - 100)
                self.assertEqual(value['updated_at'], now)
                self.assertEqual(value['state'], state)
        fresh = dict(snap, task_source=dict(source, observed_at=160))
        health.update(self.state, fresh, now=170)
        self.assertEqual(self.status()['snapshot_at'], 160)
        health.update(self.state, snapshot(workers=1), now=180)
        self.assertEqual(self.status()['task_source'], dict(workspace=None, repository_identity=None,
                                                          revision=None, observed_at=None))
        self.assertIsNone(self.status()['snapshot_at'])
        health.update(self.state, busy, now=190)
        self.assertIsNone(self.status()['snapshot_age_seconds'])
        self.assertEqual(self.status()['state'], 'unavailable')

    def test_new_root_blockers_are_announced_again(self):
        health.update(self.state, snapshot(), now=0)
        self.assertIsNotNone(health.update(self.state, snapshot(), now=2000))
        claim = {'id': 'T-5', 'kind': 'claim', 'blocks': 1}
        line = health.update(self.state, snapshot(roots=(HELD, claim)), now=2100)
        self.assertIn('T-5 (claimed by another session, holds 1)', line)

    def test_working_ends_the_episode(self):
        health.update(self.state, snapshot(), now=0)
        health.update(self.state, snapshot(), now=2000)
        self.assertIsNone(health.update(self.state, snapshot(workers=1), now=2100))
        self.assertEqual(self.status()['state'], 'working')
        health.update(self.state, snapshot(), now=2200)
        self.assertEqual(self.status()['since'], 2200)  # a new episode starts its own clock
        self.assertIsNone(health.update(self.state, snapshot(), now=2300))

    def test_a_held_only_queue_is_a_wait_not_an_empty_queue(self):
        from pi_autowork import fleet_view
        snap = dict(snapshot(waiting=(), roots=()), tasks=[
            {'task': 'T-9', 'state': 'held', 'cause': 'overlap'}])
        health.update(self.state, snap, now=0)
        record = self.status()
        self.assertEqual(record['state'], 'blocked')
        runner = fleet_view.Runner('r', state=record['state'],
                                   held=[(h['task'], h['cause']) for h in record['held']])
        headline = fleet_view.verdict(runner)[0]
        self.assertTrue(headline.startswith('Waiting — T-9:'), headline)
        self.assertIn("another task's files", headline)
        self.assertNotIn('on you', headline)

    def test_moving_work_or_a_pause_is_not_a_stall(self):
        moving = {'id': 'R', 'kind': 'running', 'blocks': 2}
        health.update(self.state, snapshot(roots=(moving,)), now=0)
        self.assertIsNone(health.update(self.state, snapshot(roots=(moving,)), now=9999))
        self.assertEqual(self.status()['state'], 'blocked')
        self.assertIsNone(health.update(self.state, snapshot(), now=0, runner={'paused_until': '5000'}))
        self.assertEqual(self.status()['state'], 'paused')
        self.assertEqual(health.classify(dict(snapshot(waiting=()), tasks=[])), 'idle')
        self.assertEqual(health.classify(snapshot(queue=1)), 'working')

    def test_a_runner_that_cannot_dispatch_is_a_stall_too(self):
        ready = {'outcome': 'PARALLEL_STATUS', 'active_workers': 0,
                 'tasks': [{'task': 'A', 'state': 'waiting', 'blocked_by': []}], 'roots': []}
        runner = {'blocker': 'no usable model: primary and fallback not ready'}
        health.update(self.state, ready, now=0, runner=runner)
        line = health.update(self.state, ready, now=1800, runner=runner)
        self.assertIn('no usable model: primary and fallback not ready (the runner cannot proceed, holds 1)', line)
        self.assertIsNone(health.update(self.state, ready, now=1900))  # ready again: not a stall

    def test_integrations_waiting_on_another_session_are_a_stall_not_work(self):
        """flutter: three verified commits waited on an owner session; health said working."""
        snap = dict(snapshot(waiting=(), roots=()), integration_queue=3)
        runner = {'stuck_integrations': '3', 'blocker': '3 verified commit(s) wait for another session '
                                                        'in the main checkout: pid 2353411 pi'}
        self.assertIsNone(health.update(self.state, snap, now=0, runner=runner))
        self.assertEqual(self.status()['state'], 'blocked')
        line = health.update(self.state, snap, now=1800, runner=runner)
        self.assertIn('pid 2353411 pi (the runner cannot proceed, holds 3)', line)
        self.assertEqual(health.classify(snap, stuck=2), 'working')  # one still progresses

    def test_a_runner_busy_with_its_own_job_is_working_not_silent(self):
        """TOOLSET-177-d0: a five-minute DOCS-MAINTAINER run read as `not cycling 3h46m`."""
        folder = self.state / 'busy'
        folder.mkdir()
        (folder / 'runner.json').write_text(json.dumps(
            {'pid': os.getpid(), 'start_time': start_time(os.getpid()), 'repo': '/x/busy'}))
        (folder / 'status.json').write_text(json.dumps({'state': 'stalled', 'since': 0, 'repo': '/x/busy',
                                                        'updated_at': 1000 - health.STALE_AFTER - 1}))
        health.job_started(folder, 'maintainer', 'DOCS-MAINTAINER', now=700)
        row = health.fleet(self.state, now=1000, service=lambda name: 'active')[0]
        self.assertEqual((row['state'], row['job']['role']), ('working', 'maintainer'))
        job = json.loads((folder / 'job.json').read_text())
        ticks = Path(f'/proc/{os.getpid()}/stat').read_text().rsplit(')', 1)[1].split()[19]
        self.assertEqual(job.get('start_time'), ticks)
        (folder / 'job.json').write_text(json.dumps(dict(job, start_time=str(int(ticks) + 1))))
        self.assertIsNone(health.current_job(folder), 'a reused PID does not own the job')
        (folder / 'job.json').write_text(json.dumps(dict(job, pid=2 ** 22 + 7)))  # its runner died mid-job
        self.assertEqual(health.fleet(self.state, now=1000, service=lambda name: 'active')[0]['state'], 'not cycling')
        health.job_finished(folder)
        self.assertFalse((folder / 'job.json').exists())

    def test_stale_working_counts_are_not_current_work_without_a_verified_job(self):
        folder = self.state / 'repo'
        folder.mkdir()
        runner = dict(repo='/x/repo', pid=os.getpid(), start_time=start_time(os.getpid()))
        (folder / 'runner.json').write_text(json.dumps(runner))
        source = dict(workspace='/session/repo', repository_identity='/repo/.git',
                      revision='committed-source', observed_at=1000)
        health.update(folder, dict(snapshot(workers=3, queue=2), task_source=source), now=1000, runner=runner)
        before = (folder / 'status.json').read_bytes()
        for age, expected in ((health.STALE_AFTER, 'working'), (health.STALE_AFTER + 1, 'not cycling')):
            with self.subTest(age=age):
                row, = health.fleet(self.state, now=1000 + age, service=lambda name: 'active')
                self.assertEqual(row['state'], expected)
                self.assertEqual((row['workers'], row['waiting'], row['updated_at']), (3, 1, 1000))
                self.assertEqual((row['snapshot_at'], row['snapshot_age_seconds']), (1000, age))
                self.assertEqual(row['task_source'], source)
                self.assertIsNone(row['job'])
        # Separately verified work still overrides an old working snapshot.
        health.job_started(folder, 'maintainer', 'DOCS-MAINTAINER', now=1000)
        row, = health.fleet(self.state, now=1000 + health.STALE_AFTER + 1, service=lambda name: 'active')
        self.assertEqual((row['state'], row['job']['role']), ('working', 'maintainer'))
        self.assertEqual((folder / 'status.json').read_bytes(), before)

    def test_fleet_flags_dead_and_silent_runners(self):
        def runner(key, repo, pid, updated, state='working', **identity):
            folder = self.state / key
            folder.mkdir()
            (folder / 'runner.json').write_text(json.dumps(
                {'pid': pid, 'repo': repo, 'start_time': start_time(pid), **identity}))
            (folder / 'status.json').write_text(json.dumps({
                'state': state, 'since': 0, 'updated_at': updated, 'active_workers': 0, 'waiting': 3,
                'repo': repo, 'roots': [HELD]}))
        runner('a', '/x/alive', os.getpid(), 1000)
        runner('b', '/x/dead', 2 ** 22 + 7, 1000)
        runner('c', '/x/silent', os.getpid(), 1000 - health.STALE_AFTER - 1, state='blocked')
        unrelated = subprocess.Popen(['sleep', '30'])
        self.addCleanup(unrelated.wait)
        self.addCleanup(unrelated.terminate)
        ticks = Path(f'/proc/{unrelated.pid}/stat').read_text().rsplit(')', 1)[1].split()[19]
        runner('d', '/x/reused', unrelated.pid, 1000, start_time=str(int(ticks) + 1))
        runner('e', '/x/matching', unrelated.pid, 1000, start_time=ticks)
        runner('f', '/x/legacy', unrelated.pid, 1000, start_time=None)
        rows = {r['name']: r for r in health.fleet(self.state, now=1000, service=lambda name: 'active')}
        self.assertEqual(rows['reused']['state'], 'not running')
        self.assertEqual(rows['matching']['state'], 'working')
        self.assertEqual(rows['legacy']['state'], 'not running')
        self.assertEqual(rows['alive']['state'], 'working')
        self.assertEqual(rows['dead']['state'], 'not running')
        self.assertEqual(rows['silent']['state'], 'not cycling')
        text = health.render(list(rows.values()), now=1000)
        self.assertIn('dead                     service active    not running', text)
        self.assertIn('    blocked by T-9 (held for a person: its worker reported a blocker, holds 4)', text)


if __name__ == '__main__':
    unittest.main()
