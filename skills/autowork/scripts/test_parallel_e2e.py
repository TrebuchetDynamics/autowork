"""Real CLI / real Git ABC acceptance; fake local workers only, no model hosts.

The reusable workload also powers scripts/bench_parallel.py. Serial uses the same
CLI pipeline with a single slot, so Git/validation work is identical in both runs.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import parallel_status as status
from gate_skip import skip_if_gated

CLI = Path(__file__).with_name('owner_cycle.py')
WORKER = '''import json, os, re, subprocess, sys, time
from pathlib import Path
prompt, delay, barrier = Path(sys.argv[1]), float(sys.argv[2]), sys.argv[3]
text = prompt.read_text()
task = re.search(r'^Task: (.+)$', text, re.M)[1]
report = Path(re.search(r'^Report file: (.+)$', text, re.M)[1])
started = time.time()
if task == 'C':
    assert Path('A.txt').read_text() == 'done A\\n'
    assert '- [x] A' in Path('TODO.archive.md').read_text()
if barrier == 'yes' and task in ('A', 'B'):
    root = report.parents[3]
    (root / ('ready-' + task)).write_text('ready')
    deadline = time.monotonic() + 15
    while not all((root / ('ready-' + t)).exists() for t in ('A', 'B')):
        assert time.monotonic() < deadline, 'overlap barrier timed out'
        time.sleep(.01)
time.sleep(delay)
Path(task + '.txt').write_text('done ' + task + '\\n')
subprocess.run([sys.executable, 'check_fixture.py'], check=True)
subprocess.run(['git', 'add', task + '.txt'], check=True)
subprocess.run(['git', 'commit', '-qm', 'fake worker ' + task], check=True)
commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip()
report.write_text(json.dumps(dict(task=task, commit=commit, changed_files=[task + '.txt'],
    checks=[dict(command='check_fixture.py', result='pass', summary='fixture check')],
    blockers=[], changelog='Complete fixture ' + task, started=started, finished=time.time())))
'''
CHECK = '''from pathlib import Path
import sys
for task in ('A', 'B', 'C'):
    text = Path(task + '.txt').read_text()
    assert text in ('base\\n', 'done ' + task + '\\n')
    if '--complete' in sys.argv:
        assert text == 'done ' + task + '\\n'
if Path('C.txt').read_text() != 'base\\n':
    assert Path('A.txt').read_text() == 'done A\\n'
'''


class ABCWorkload:
    def __init__(self, workers=2, delay=.5):
        self.workers, self.delay = workers, delay

    def __enter__(self):
        self.temp = tempfile.TemporaryDirectory(prefix='toolset-089-', dir=os.environ.get('TMPDIR'))
        self.root = Path(self.temp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Offline ABC')
        self.worker = self.root / 'fake_worker.py'
        self.worker.write_text(WORKER)
        (self.repo / 'check_fixture.py').write_text(CHECK)
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Next\n\n' + '\n'.join(
            f'- [ ] {t} — Task {t}\n  Scope: Complete {t}.txt\n  Touches: {t}.txt\n'
            f'  Acceptance: Fixture check passes\n  Checks: python3 check_fixture.py\n'
            f'  Dependencies: {"A" if t == "C" else "None"}.\n  Status: open\n' for t in 'ABC'))
        for t in 'ABC':
            (self.repo / (t + '.txt')).write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture baseline')
        self.common = self.repo / '.git/autowork-execution'
        return self

    def __exit__(self, *exc):
        # Failure must not leave detached fixture workers writing after cleanup.
        if self.common.exists():
            import parallel_dispatch
            import parallel_state
            for slot in parallel_state.slots(self.common):
                if slot.get('worker'):
                    parallel_dispatch.stop(slot['worker'], slot['worktree'])
        self.temp.cleanup()

    def git(self, *args):
        p = subprocess.run(['git', '-C', str(self.repo), *args], capture_output=True, text=True, timeout=20)
        if p.returncode:
            raise AssertionError(p.stderr)
        return p.stdout.strip()

    def cli(self, *args):
        p = subprocess.run([sys.executable, str(CLI), str(self.repo), *args], capture_output=True,
                           text=True, timeout=40,
                           env={**os.environ, 'PI_AUTOWORK_MIN_FREE_DISK_GB': '0'})  # tiny fixture, not a model checkout
        if p.returncode:
            raise AssertionError(f'CLI {args}: {p.stdout}\n{p.stderr}')
        return json.loads(p.stdout)

    def dispatch(self):
        return self.cli('--apply', '--parallel', str(self.workers), '--owner-pid', str(os.getpid()),
                        '--worker-command', json.dumps([sys.executable, str(self.worker), '{prompt_file}',
                                                       str(self.delay), 'yes' if self.workers == 2 else 'no']),
                        '--worker-timeout', '30', '--min-free-mem-mb', '0')

    def run(self):
        started = time.perf_counter()
        first = self.dispatch()
        expected = ['A', 'B'] if self.workers == 2 else ['A']
        if [t['task'] for t in first['dispatched']] != expected:
            skip_if_gated(first)  # a busy host refused the dispatch: not a failure of this code
            raise AssertionError(f'Expected initial {expected}; real resource gates are not bypassed: {first}')
        self.initial = self.cli('--parallel-status', '--json')
        deadline = time.monotonic() + 60
        closed, answers = [], []
        while len(closed) < 3:
            if time.monotonic() > deadline:
                skip_if_gated(*answers)
                raise AssertionError('ABC coordinator exceeded deadline')
            self.cli('--parallel', str(self.workers), '--wait', '--timeout', '5', '--owner-pid', str(os.getpid()))
            snapshot = self.cli('--parallel-status', '--json')
            for row in snapshot['tasks']:
                if row['state'] == 'reported':
                    task = row['task']
                    result = self.cli('--integrate', task, '--owner-pid', str(os.getpid()), '--timeout', '10',
                                      '--run', sys.executable, 'check_fixture.py')
                    if result['outcome'] != 'INTEGRATED':
                        raise AssertionError(result)
                    self.cli('--parallel-close', task, '--owner-pid', str(os.getpid()))
                    self.git('add', 'TODO.md', 'TODO.archive.md')
                    self.git('commit', '-qm', 'close ' + task)
                    closed.append(task)
            if len(closed) < 3:
                answers.append(self.dispatch())
        subprocess.run([sys.executable, 'check_fixture.py', '--complete'], cwd=self.repo, check=True, timeout=10)
        self.cli('--parallel', str(self.workers), '--release', '--owner-pid', str(os.getpid()))
        elapsed = time.perf_counter() - started
        final = self.cli('--parallel-status', '--json')
        reports = {t: json.loads((self.common / 'slot-data' / t / 'attempt-1/report.json').read_text()) for t in 'ABC'}
        events = status.journal(self.common)
        a_closed = next(e['timestamp'] for e in events if e['event'] == 'slot_changed'
                        and e['task_id'] == 'A' and e['state'] == 'closed')
        assert reports['C']['started'] >= a_closed
        if self.workers == 2:
            assert max(reports[t]['started'] for t in 'AB') < min(reports[t]['finished'] for t in 'AB')
            assert final['metrics']['peak_workers'] == 2
        assert final['completed'] == 3 and final['failed'] == 0 and final['integration_queue'] == 0
        assert not self.git('status', '--porcelain')
        assert not self.git('remote')
        assert self.git('log', '--merges', '--format=%s').count('Merge commit') == 3
        assert all(not Path(row['worktree']).exists() for row in final['tasks'])
        return dict(elapsed_seconds=elapsed, workers=self.workers, delay_seconds=self.delay,
                    controlled_critical_path_seconds=self.delay * (2 if self.workers == 2 else 3),
                    overhead_seconds=elapsed - self.delay * (2 if self.workers == 2 else 3),
                    metrics=final['metrics'])


class EndToEndTests(unittest.TestCase):
    def test_a_busy_host_skips_the_workload_instead_of_failing_it(self):
        """TOOLSET-193-54: the fleet's own load refused these dispatches and main read red."""
        import contextlib, io
        from unittest import mock
        marker = io.StringIO()  # kept from the output: this skip is forced, not the host's
        with mock.patch.dict(os.environ, AUTOWORK_GATE_CPUS='0.001'), ABCWorkload() as workload:
            with self.assertRaisesRegex(unittest.SkipTest, 'host busy: resource gate: load average'), \
                    contextlib.redirect_stderr(marker):
                workload.run()
        self.assertIn('RESOURCE_GATE_SKIP: resource gate: load average', marker.getvalue())

    def test_abc_real_cli(self):
        with ABCWorkload() as workload:
            workload.run()
            self.assertEqual({r['task'] for r in workload.initial['tasks']}, set('ABC'))
            self.assertEqual({r['slot'] for r in workload.initial['tasks'] if r['task'] in 'AB'}, {1, 2})
            # Dispatch history proves peak concurrency even if both workers
            # finish before this observation. run() verifies report-time overlap.
            self.assertEqual(workload.initial['metrics']['peak_workers'], 2)
            c = next(r for r in workload.initial['tasks'] if r['task'] == 'C')
            self.assertEqual(c['state'], 'waiting')
            self.assertIn('dependency', c['reason'])

    def test_abc_with_delayed_initial_observation(self):
        from unittest.mock import patch
        original = ABCWorkload.cli
        observed = False

        def delayed(workload, *args):
            nonlocal observed
            if args == ('--parallel-status', '--json') and not observed:
                observed = True
                time.sleep(1)
            return original(workload, *args)

        with patch.object(ABCWorkload, 'cli', delayed):
            self.test_abc_real_cli()
        self.assertTrue(observed)

    def test_serial_control(self):
        with ABCWorkload(workers=1, delay=.05) as workload:
            workload.run()


class StatusTests(unittest.TestCase):
    def test_journal_metrics_intervals_retries_and_conflicts(self):
        def change(t, task, phase, attempt=1, reason=''):
            return dict(timestamp=t, event='slot_changed', task_id=task,
                        slot=dict(task_id=task, state=phase, attempt=attempt, reason=reason))
        events = [dict(timestamp=100, event='coordinator_claimed'),
                  change(100, 'A', 'running'), change(102, 'B', 'running'),
                  change(110, 'A', 'reported'), change(112, 'A', 'integrating'),
                  change(113, 'A', 'integrating'),  # receipt write, not another interval
                  change(114, 'B', 'held', reason='merge conflict'),
                  change(115, 'A', 'integrated'), change(116, 'A', 'closed'),
                  change(118, 'B', 'dispatched', 2), change(119, 'B', 'running', 2),
                  change(120, 'B', 'held', 2, 'validation failed')]
        self.assertEqual(status.metrics(events, 122), dict(wall_seconds=22, worker_seconds=23,
            integration_seconds=3, waiting_seconds=10, peak_workers=2, conflicts=1, retries=1))
        released = events + [dict(timestamp=122, event='coordinator_released')]
        self.assertEqual(status.metrics(released, 130)['wall_seconds'], 22)
        pending = [dict(timestamp=10, event='coordinator_claimed'),
                   dict(timestamp=10, event='dispatch_observed', waiting=[dict(id='C', reason='busy')]),
                   dict(timestamp=12, event='dispatch_observed', waiting=[dict(id='C', reason='busy')]),
                   change(14, 'C', 'dispatched'), change(15, 'C', 'running')]
        self.assertEqual(status.metrics(pending, 17)['waiting_seconds'], 5)
        self.assertEqual(status.metrics(pending, 17)['worker_seconds'], 2)

    def test_roots_trace_waiting_chains_to_what_holds_them(self):
        row = lambda task, state, by=(), **extra: dict(task=task, state=state, blocked_by=list(by), **extra)
        rows = [row('H', 'held', cause='blocker', reason='worker reported a blocker: needs a device'),
                row('A', 'waiting', ['H']), row('B', 'waiting', ['A']),        # a chain behind H
                row('C', 'waiting', ['C']), row('D', 'waiting', ['C']),        # C is claimed elsewhere
                row('E', 'waiting', ['approved device access']),             # an outside condition
                row('R', 'running'), row('G', 'waiting', ['R']),
                row('F', 'waiting', []),                                    # only capacity: not blocked
                row('X', 'waiting', ['Y']), row('Y', 'waiting', ['X'])]      # a cycle ends somewhere
        found = {r['id']: (r['kind'], r['blocks']) for r in status.roots(rows)}
        self.assertEqual(status.roots(rows)[0]['id'], 'H')
        self.assertEqual(found['H'], ('held', 2))
        self.assertEqual(found['C'], ('claim', 1))
        self.assertEqual(found['approved device access'], ('outside', 1))
        self.assertEqual(found['R'], ('running', 1))
        self.assertNotIn('F', found)
        self.assertNotIn('A', found)
        self.assertEqual({found[t][0] for t in ('X', 'Y')}, {'cycle'})  # each member of the cycle is named

    def test_a_task_the_engine_will_not_run_is_a_contract_root(self):
        """flutter TASK-003 showed "awaiting dispatch" though its entry lacked Checks."""
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            (repo / 'TODO.md').write_text('# TODO\n\n## Next\n\n- [ ] X — Missing checks\n  Scope: x\n'
                                          '  Dependencies: None.\n  Status: open\n')
            rows = status.pending_tasks(repo)
            self.assertEqual(rows[0]['reason'], 'not runnable: needs unique Scope, Acceptance and Checks fields')
            found = status.roots([dict(task=r['id'], state='waiting', blocked_by=r['blocked_by'],
                                       root_kind=r.get('root_kind')) for r in rows])
            self.assertEqual([(r['id'], r['kind']) for r in found], [('X', 'contract')])

    def test_status_uses_latest_dispatch_capacity(self):
        with ABCWorkload(workers=1, delay=1) as fixture:
            fixture.dispatch()
            fixture.workers = 2
            self.assertEqual(fixture.dispatch()['max_workers'], 2)
            value = fixture.cli('--parallel-status', '--json')
            self.assertEqual(value['max_workers'], 2)
            self.assertLessEqual(value['active_workers'], value['max_workers'])

    def test_fixed_journal_golden_and_json_details(self):
        with ABCWorkload() as fixture:
            common = fixture.common
            (common / 'slots').mkdir(parents=True)
            events = [dict(timestamp=100, event='coordinator_claimed', coordinator=dict(max_workers=4))]
            for task, phase in zip('ABCD', ('closed', 'held', 'reported', 'integrated')):
                slot = dict(task_id=task, state=phase, attempt=1, started_at=100,
                            worktree='/fixture/' + task, worker=None, commit='abc',
                            checks=dict(outcome='EXECUTED'), integration=dict(commit='def'))
                if task == 'B':
                    slot['reason'] = 'merge conflict'
                (common / 'slots' / (task + '.json')).write_text(json.dumps(slot))
                events.append(dict(timestamp=100, event='slot_changed', task_id=task, state=phase, slot=slot))
            (common / 'journal.jsonl').write_text(''.join(json.dumps(e) + '\n' for e in events))
            value = status.snapshot(fixture.repo, now=110)
            rendered = status.render(value)
            expected = '\n'.join([
                'AUTOWORK — PARALLEL', 'Workers: 0/4 active',
                'Task                 State        Slot   Elapsed  Blocked reason',
                'A                    closed          -      0.0s  -',
                'B                    held            -     10.0s  merge conflict',
                'C                    reported        -     10.0s  -',
                'D                    integrated      -     10.0s  -',
                'Completed: 1  Failed: 1  Integration queue: 1',
                'Wall: 10.0s  Worker: 0.0s  Integration: 0.0s  Waiting/blocked: 30.0s',
                'Peak workers: 0  Conflicts: 1  Retries: 0'])
            self.assertEqual(rendered, expected)
            self.assertLess(len(rendered.splitlines()), 25)
            cli_value = fixture.cli('--parallel-status', '--json')
            for row in cli_value['tasks']:
                for field in ('worktree', 'checks', 'commit', 'integration'):
                    self.assertIsNotNone(row[field])
            self.assertFalse((common / 'coordinator.json').exists())
            # Status did not reconcile or append to the fixed journal.
            self.assertEqual(status.journal(common), events)

    def test_empty_status_does_not_claim_or_create_runtime_state(self):
        with ABCWorkload() as fixture:
            value = fixture.cli('--parallel-status', '--json')
            self.assertEqual(value['max_workers'], 0)
            self.assertEqual(value['metrics']['wall_seconds'], 0)
            self.assertFalse(fixture.common.exists())

    def test_dependency_reason_refreshes_after_close_and_plain_cli(self):
        with ABCWorkload() as fixture:
            fixture.common.mkdir()
            event = dict(timestamp=100, event='dispatch_observed', waiting=[dict(id='C', reason='dependency: A')])
            (fixture.common / 'journal.jsonl').write_text(json.dumps(event) + '\n')
            todo = fixture.repo / 'TODO.md'
            todo.write_text(todo.read_text().replace('- [ ] A', '- [x] A'))
            value = fixture.cli('--parallel-status', '--json')
            self.assertEqual(next(r for r in value['tasks'] if r['task'] == 'C')['reason'], 'awaiting dispatch')
            p = subprocess.run([sys.executable, str(CLI), str(fixture.repo), '--parallel-status'],
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 0, p.stderr)
            self.assertTrue(p.stdout.startswith('AUTOWORK — PARALLEL\nWorkers: 0/0 active\n'))
            self.assertLess(len(p.stdout.splitlines()), 25)

    def test_status_rejects_mutating_operation_without_claim(self):
        with ABCWorkload() as fixture:
            p = subprocess.run([sys.executable, str(CLI), str(fixture.repo), '--parallel-status', '--apply'],
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 1)
            self.assertEqual(json.loads(p.stdout)['outcome'], 'ACTION_REQUIRED')
            self.assertFalse(fixture.common.exists())

    def test_partial_journal_is_reported_not_silently_ignored(self):
        with ABCWorkload() as fixture:
            fixture.common.mkdir()
            (fixture.common / 'journal.jsonl').write_text('{')
            p = subprocess.run([sys.executable, str(CLI), str(fixture.repo), '--parallel-status', '--json'],
                               capture_output=True, text=True, timeout=10)
            self.assertEqual(p.returncode, 1)
            self.assertEqual(json.loads(p.stdout)['outcome'], 'ACTION_REQUIRED')


if __name__ == '__main__':
    unittest.main()
