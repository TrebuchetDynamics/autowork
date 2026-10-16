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

    def test_an_unanswered_status_read_keeps_the_stall_clock(self):
        """A --status reader holding the engine lock made the runner look idle and reset the clock."""
        health.update(self.state, snapshot(), now=0)
        busy = {'outcome': 'ACTION_REQUIRED', 'reason': 'Repository execution lock is held by a live operation.'}
        self.assertIsNone(health.update(self.state, busy, now=1000))
        self.assertEqual((self.status()['state'], self.status()['since']), ('blocked', 0))
        self.assertIsNotNone(health.update(self.state, snapshot(), now=1800))

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

    def test_moving_work_or_a_pause_is_not_a_stall(self):
        moving = {'id': 'R', 'kind': 'running', 'blocks': 2}
        health.update(self.state, snapshot(roots=(moving,)), now=0)
        self.assertIsNone(health.update(self.state, snapshot(roots=(moving,)), now=9999))
        self.assertEqual(self.status()['state'], 'blocked')
        self.assertIsNone(health.update(self.state, snapshot(), now=0, runner={'paused_until': '5000'}))
        self.assertEqual(self.status()['state'], 'paused')
        self.assertEqual(health.classify(snapshot(waiting=())), 'idle')
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
