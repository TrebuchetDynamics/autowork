"""Adversarial worker races from reference Pi orchestrators, as offline fixtures.

TOOLSET-116-c1 ports scenarios, not code, from the projects compared in
docs/research/pi-autowork-reference-architectures.md. Each test names the upstream
case it mirrors. Workers are the deterministic fixtures/fake_worker.py; no model
host, network or live Pi runtime is involved.
"""
import ctypes
import json
import os
from pathlib import Path
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import parallel_dispatch as dispatch
import parallel_integrate as integrate
import parallel_state as state
import test_parallel_dispatch as base
from offline_fixtures import idle_host_env
from gate_skip import skip_if_gated

FAKE, task = base.FAKE, base.task

CLI = SCRIPTS / 'owner_cycle.py'


def no_subreaper():
    """In-process integration makes this process a child subreaper; orphaned workers of
    later CLI coordinators would then turn into zombies only this process reaps, and
    their process groups would look alive to every later test."""
    ctypes.CDLL(None, use_errno=True).prctl(36, 0, 0, 0, 0)  # PR_SET_CHILD_SUBREAPER off
    while True:
        try:
            if os.waitpid(-1, os.WNOHANG) == (0, 0):
                return
        except ChildProcessError:
            return


class AdversarialWorkerTests(unittest.TestCase):
    # The dispatch harness: real Git, a real CLI pass and the deterministic fake worker.
    stop_workers, git, write_todo, set_spec, run_cli, apply, wait, events, wait_until_idle = (
        getattr(base.DispatchTests, name) for name in ('stop_workers', 'git', 'write_todo', 'set_spec',
                                                       'run_cli', 'apply', 'wait', 'events', 'wait_until_idle'))

    def setUp(self):
        no_subreaper()
        self.addCleanup(no_subreaper)
        base.DispatchTests.setUp(self)

    def commit_todo(self, *bodies):
        self.write_todo(*bodies)
        self.git('add', 'TODO.md')
        self.git('commit', '-qm', 'queue')

    def starts(self, tid=None):
        return [e for e in self.events() if e['event'] == 'start' and tid in (None, e['task'])]

    def slot(self, tid='A'):
        return next(s for s in state.slots(self.common) if s['task_id'] == tid)

    def land(self, tid):
        return integrate.integrate(self.repo, self.owner, tid, ['true'], 10)

    def test_a_late_report_from_a_superseded_attempt_never_completes_the_retry(self):
        """AgwaB pi-subagent `commitAttemptResultIfActive`; Kyle Boas pi-orchestrator: an old
        final answer must not complete a new assignment. Attempt 1 dies; its report shows up
        after attempt 2 committed without one."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.apply()
        self.wait_until_idle()
        self.assertEqual((self.slot()['state'], self.slot()['attempt']), ('interrupted', 1))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1, 'report': False}})
        self.apply()
        self.wait_until_idle()
        retry = self.slot()
        self.assertEqual((retry['state'], retry['attempt']), ('reported', 2))
        late = self.common / 'slot-data/A/attempt-1/report.json'
        late.write_text(json.dumps({'task': 'A', 'commit': retry['commit'], 'changed_files': ['a.txt'],
                                    'checks': [], 'blockers': [], 'pending_live': [], 'changelog': ''}))
        self.wait(1)  # a reconcile pass sees the late report and must ignore it
        self.assertEqual(self.slot()['state'], 'reported')
        result = self.land('A')
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('report', self.slot()['reason'])
        self.assertNotIn(retry['commit'], self.git('log', '--format=%H', 'HEAD'))

    def test_a_paused_attempt_resumes_without_its_earlier_report(self):
        """AgwaB generation-guarded results: a resumed attempt keeps its number, so a report
        written for the earlier run must not stand in for the resumed one."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 30, 'commit': False}})
        self.apply()
        state.pause(self.repo, self.owner)
        self.stop_workers()
        self.wait_until_idle()
        stale = self.common / 'slot-data/A/attempt-1/report.json'
        stale.write_text(json.dumps({'task': 'A', 'commit': None, 'changed_files': [], 'checks': [],
                                     'blockers': ['stale blocker from the paused run'], 'changelog': ''}))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1, 'report': False}})
        _, resumed = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in resumed['dispatched']], [('A', 1)])
        self.assertFalse(stale.exists())
        self.wait_until_idle()
        self.assertEqual(self.slot()['state'], 'reported')  # not held on the stale blocker
        self.assertEqual(self.land('A')['outcome'], 'HELD')  # and no report of its own: not landed

    def test_launch_with_a_lost_receipt_is_still_seen_as_running(self):
        """Gas Town `RunPlan`: a launch that happened while its receipt write failed must
        become reconciliation, not a blind second dispatch into the same worktree."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 2.0}})
        real = state.transition

        def lose_running(repo, owner, tid, target, **updates):
            if target == 'running':
                raise ValueError('coordinator died after launch')
            return real(repo, owner, tid, target, **updates)

        with patch.object(state, 'transition', side_effect=lose_running):
            code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'), result)
        self.assertEqual(self.slot()['worker'], None)  # nothing recorded the live worker
        _, again = self.apply()
        self.assertEqual(again['dispatched'], [], 'a second writer started beside the unrecorded worker')
        self.assertEqual(self.slot()['state'], 'running')
        self.wait_until_idle()
        slot = self.slot()
        self.assertEqual((slot['state'], slot['attempt']), ('reported', 1))
        self.assertEqual(len(self.starts('A')), 1)
        self.assertEqual(self.land('A')['outcome'], 'INTEGRATED')

    def test_a_process_that_escaped_its_stopped_worker_is_stopped_too(self):
        """Kyle Boas pi-orchestrator / pi-rukas `killProcessTree`; Saify Matteo cancellation
        during spawn: a child in its own session outlives a timed-out worker's process group
        and would keep writing into the worktree the retry reuses."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 60, 'commit': False, 'escape': 4}})
        self.apply('--worker-timeout', '1')
        _, stopped = self.wait(20)
        slot = self.slot()
        self.assertEqual(slot['state'], 'interrupted', stopped)
        self.assertEqual(state.strays(slot['worktree']), [], 'the escaped child survived the stop')
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1}})
        _, retry = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in retry['dispatched']], [('A', 2)])
        self.wait_until_idle()
        time.sleep(4.5)  # past the moment the escaped child would have written
        self.assertFalse((Path(slot['worktree']) / 'escaped.txt').exists())
        self.assertEqual(self.land('A')['outcome'], 'INTEGRATED')

    def test_a_worker_that_exits_while_its_escaped_child_writes_is_not_reported(self):
        """Agent Orchestrator `ActivitySignal`: activity outlives the launch identity. The
        leader commits and exits; a child it left in another session still writes."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1, 'escape': 2}})
        self.apply()
        deadline = time.monotonic() + 20
        while not [e for e in self.events() if e['event'] == 'end']:
            self.assertLess(time.monotonic(), deadline)
            time.sleep(0.05)
        self.wait(0.5)
        self.assertEqual(self.slot()['state'], 'running', 'reported while a descendant still writes')
        self.wait_until_idle()
        slot = self.slot()
        self.assertEqual(slot['state'], 'reported')
        result = self.land('A')
        # The late write is uncommitted residue in the worker's worktree, not part of its commit.
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(self.git('show', '--name-only', '--format=', slot['commit']).split(), ['a.txt'])

    def test_out_of_order_completion_lands_each_commit_once(self):
        """Symphony reconcile-before-dispatch; AgwaB out-of-order completion: the later task
        finishes first. Both land exactly once and neither loses the other's change."""
        self.commit_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 2.0}, 'B': {'files': {'b.txt': 'b'}, 'sleep': 0.1}})
        _, first = self.apply()
        self.assertEqual([d['task'] for d in first['dispatched']], ['A', 'B'])
        deadline = time.monotonic() + 20
        while self.slot('B')['state'] != 'reported':
            self.assertLess(time.monotonic(), deadline)
            self.wait(1)
        self.assertEqual(self.slot('A')['state'], 'running')
        self.assertEqual(self.land('B')['outcome'], 'INTEGRATED')
        self.wait_until_idle()
        self.assertEqual(self.land('A')['outcome'], 'INTEGRATED')
        merges = self.git('log', '--merges', '--format=%P').splitlines()
        landed = [parents.split()[1] for parents in merges]
        self.assertEqual(sorted(landed), sorted([self.slot('A')['commit'], self.slot('B')['commit']]))
        self.assertEqual(((self.repo / 'a.txt').read_text(), (self.repo / 'b.txt').read_text()), ('a', 'b'))
        with self.assertRaises(ValueError):
            self.land('A')  # an integrated slot is never landed twice

    def test_a_report_written_after_a_coordinator_restart_is_adopted(self):
        """Gas Town reconciliation; Agent Orchestrator launch identity: the coordinator dies
        mid-task, the worker finishes and reports, and a new coordinator lands it without
        spending an attempt or starting a duplicate."""
        self.commit_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 2.0}})
        command = [sys.executable, str(CLI), str(self.repo), '--owner-pid', '$$']
        worker = json.dumps([sys.executable, str(FAKE), '{prompt_file}', '{worktree}'])
        env = idle_host_env(self.root)

        def coordinator(*steps):
            # bash is the coordinator: its PID is the owner and it exits afterwards.
            script = '; '.join(' '.join(map(lambda a: a if a == '$$' else "'" + a + "'", command + list(step)))
                               for step in steps) + '; true'
            out = subprocess.run(['bash', '-c', script], env=env, capture_output=True, text=True, timeout=240)
            return [json.loads(chunk) for chunk in out.stdout.replace('}\n{', '}\x00{').split('\x00') if chunk.strip()]

        first = coordinator(['--apply', '--parallel', '--worker-command', worker])
        if [d['task'] for d in first[0]['dispatched']] != ['A']:
            skip_if_gated(first)
        self.assertEqual([d['task'] for d in first[0]['dispatched']], ['A'])
        self.assertEqual(state.live_coordinator(self.common), None)  # the first coordinator is gone
        later = coordinator(['--apply', '--parallel', '--worker-command', worker],
                            ['--parallel', '--wait', '--timeout', '90'],  # generous on a loaded host
                            ['--integrate', 'A', '--timeout', '10', '--run', 'true'])
        self.assertEqual(later[0]['dispatched'], [])  # the live worker was adopted, not duplicated
        self.assertEqual(later[-1]['outcome'], 'INTEGRATED', json.dumps(later, indent=1)[-3000:])
        slot = self.slot()
        self.assertEqual((slot['state'], slot['attempt']), ('integrated', 1))
        self.assertEqual(len(self.starts('A')), 1)


if __name__ == '__main__':
    unittest.main()
