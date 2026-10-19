"""Runner health: status file, one stall announcement per episode, fleet view."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import health  # noqa: E402

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

    def test_waiting_tasks_are_grouped_by_why_they_wait(self):
        """TOOLSET-166-b4: the view shows why tasks wait without calling the engine."""
        reasons = ['overlapping paths with TASK-140', 'overlapping paths with in_progress TASK-140',
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
        self.assertTrue({'wait behind TASK-9, which runs alone', 'on host memory or load', 'for a free worker slot',
                         'something new', 'wait for deferred TASK-D'} <= labels, labels)
        health.update(self.state, dict(snapshot(), tasks=tasks, max_workers=8), now=0)
        self.assertEqual(self.status()['waiting_groups'], groups)
        self.assertEqual(self.status()['max_workers'], 8)

    def test_an_unanswered_status_read_shows_snapshot_age_and_keeps_the_stall_clock(self):
        """A busy lock must not leave yesterday's rows looking like a current observation."""
        from pi_autowork import fleet_view
        folder = self.state / 'repo'
        folder.mkdir()
        runner = dict(repo='/x/repo', pid=os.getpid())
        (folder / 'runner.json').write_text(json.dumps(runner))
        health.update(folder, snapshot(), now=1000, runner=runner)
        busy = {'outcome': 'ACTION_REQUIRED', 'reason': 'Repository execution lock is held by a live operation.'}
        for now in (2000, 2500):
            self.assertIsNone(health.update(folder, busy, now=now, runner=runner))
            record = json.loads((folder / 'status.json').read_text())
            self.assertEqual((record['state'], record['since']), ('unavailable', 1000))
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
        self.assertIsNotNone(health.update(folder, snapshot(), now=2800, runner=runner))
        record = json.loads((folder / 'status.json').read_text())
        self.assertEqual((record['state'], record['since']), ('stalled', 1000))
        self.assertNotIn('status_error', record)
        (folder / 'status.json').unlink()
        health.update(folder, busy, now=3000, runner=runner)
        record = json.loads((folder / 'status.json').read_text())
        self.assertIsNone(record['snapshot_at'])
        self.assertIn('no successful snapshot', record['status_error'])

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
        (folder / 'runner.json').write_text(json.dumps({'pid': os.getpid(), 'repo': '/x/busy'}))
        (folder / 'status.json').write_text(json.dumps({'state': 'stalled', 'since': 0, 'repo': '/x/busy',
                                                        'updated_at': 1000 - health.STALE_AFTER - 1}))
        health.job_started(folder, 'maintainer', 'DOCS-MAINTAINER', now=700)
        row = health.fleet(self.state, now=1000, service=lambda name: 'active')[0]
        self.assertEqual((row['state'], row['job']['role']), ('working', 'maintainer'))
        job = json.loads((folder / 'job.json').read_text())
        (folder / 'job.json').write_text(json.dumps(dict(job, pid=2 ** 22 + 7)))  # its runner died mid-job
        self.assertEqual(health.fleet(self.state, now=1000, service=lambda name: 'active')[0]['state'], 'not cycling')
        health.job_finished(folder)
        self.assertFalse((folder / 'job.json').exists())

    def test_fleet_flags_dead_and_silent_runners(self):
        def runner(key, repo, pid, updated, state='working'):
            folder = self.state / key
            folder.mkdir()
            (folder / 'runner.json').write_text(json.dumps({'pid': pid, 'repo': repo}))
            (folder / 'status.json').write_text(json.dumps({
                'state': state, 'since': 0, 'updated_at': updated, 'active_workers': 0, 'waiting': 3,
                'repo': repo, 'roots': [HELD]}))
        runner('a', '/x/alive', os.getpid(), 1000)
        runner('b', '/x/dead', 2 ** 22 + 7, 1000)
        runner('c', '/x/silent', os.getpid(), 1000 - health.STALE_AFTER - 1, state='blocked')
        rows = {r['name']: r for r in health.fleet(self.state, now=1000, service=lambda name: 'active')}
        self.assertEqual(rows['alive']['state'], 'working')
        self.assertEqual(rows['dead']['state'], 'not running')
        self.assertEqual(rows['silent']['state'], 'not cycling')
        text = health.render(list(rows.values()), now=1000)
        self.assertIn('dead                     service active    not running', text)
        self.assertIn('    blocked by T-9 (held for a person: its worker reported a blocker, holds 4)', text)


if __name__ == '__main__':
    unittest.main()
