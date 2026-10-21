"""Large queue regression at the status and dispatch entry points; no live workers."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

import parallel_status as status
import store_fixture
import task_execution as execution


class StatusWaitTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.todo = '# TODO\n\n## Now\n\n' + ''.join(
            f'- [ ] {t} — Task {t}\n  Scope: {t}.py\n  Acceptance: works\n'
            '  Checks: python3 -V\n  Dependencies: None.\n  Status: open\n' for t in ('A', 'B'))
        store_fixture.write_todo(self.repo, self.todo)
        self.common = self.repo / '.git/autowork-execution'
        (self.common / 'slots').mkdir(parents=True)

    def test_status_waits_for_a_briefly_busy_writer_lock(self):
        with execution.lock(self.common / 'writer.lock') as fd:
            flock = execution.fcntl.flock

            def release_after_contention(reader, flags):
                try:
                    return flock(reader, flags)
                except BlockingIOError:
                    # Release only once snapshot actually meets the real held lock.
                    flock(fd, execution.fcntl.LOCK_UN)
                    raise

            with patch.object(execution.fcntl, 'flock', side_effect=release_after_contention):
                value = status.snapshot(self.repo, now=10)
        self.assertEqual(value['outcome'], 'PARALLEL_STATUS')
        self.assertEqual([r['task'] for r in value['tasks']], ['A', 'B'])

    def test_completed_owners_invalidate_historical_file_waits_only(self):
        event = dict(timestamp=1, event='dispatch_observed', waiting=[
            dict(id='B', reason='overlapping paths with A', blocked_by=['A'])])
        (self.common / 'journal.jsonl').write_text(json.dumps(event) + '\n')
        for phase, obsolete in (('running', False), ('reported', False), ('integrating', False),
                                ('integrated', True), ('closing', True), ('closed', True), ('done', True),
                                ('running-done', False), ('claimed', False), ('unknown', False),
                                ('legacy-closed', True)):
            with self.subTest(phase=phase):
                slot = self.common / 'slots/A.json'
                slot.unlink(missing_ok=True)
                todo = self.todo.replace('- [ ] A', '- [x] A') if phase in ('done', 'running-done') else self.todo
                if phase == 'claimed':
                    todo = todo.replace('Status: open', 'Status: open\n  Held by: an interactive session', 1)
                store_fixture.write_todo(self.repo, todo)
                if phase not in ('done', 'claimed', 'unknown'):
                    state = 'integrated' if phase == 'closing' else phase.removeprefix('legacy-').split('-')[0]
                    slot.write_text(json.dumps(dict(task_id='A', state=state, closing=phase == 'closing',
                                                    attempt=1, started_at=0, worktree='/fixture/A', worker=None)))
                if phase == 'legacy-closed':
                    del event['waiting'][0]['blocked_by']
                    (self.common / 'journal.jsonl').write_text(json.dumps(event) + '\n')
                value = status.snapshot(self.repo, now=10)
                row = next(r for r in value['tasks'] if r['task'] == 'B')
                self.assertEqual((row['reason'], row['blocked_by']),
                                 ('awaiting dispatch', []) if obsolete else ('overlapping paths with A', ['A']))
                self.assertEqual('overlapping paths with A' in status.render(value), not obsolete)

    def test_a_held_task_is_a_claim_root_that_names_its_holder(self):
        todo = self.todo.replace('Status: open', 'Status: open\n  Held by: an interactive session; until 2999-01-01', 1)
        todo = todo.replace('Task B\n', 'Task B\n  Dependencies: A.\n').replace(
            '  Checks: python3 -V\n  Dependencies: None.', '  Checks: python3 -V')
        store_fixture.write_todo(self.repo, todo)
        (self.common / 'journal.jsonl').write_text(json.dumps(dict(
            timestamp=1000, event='dispatch_observed', waiting=[])) + '\n')
        with patch.object(execution, 'external_workers', return_value=[]):
            root = status.snapshot(self.repo, now=2000)['roots'][0]
        self.assertEqual((root['id'], root['kind']), ('A', 'claim'))
        self.assertEqual(root['held_by'], 'an interactive session; until 2999-01-01')

    def test_deferred_dependencies_are_named_in_status_without_new_question_kinds(self):
        todo = self.todo.replace('Dependencies: None.', 'Dependencies: D.', 1)
        todo = todo.replace('Dependencies: None.', 'Dependencies: A.', 1)
        todo += ('\n## Needs decision\n\n- [ ] D — Device qualification\n'
                 '  Owner decision: 2026-10-18: defer until hardware arrives.\n')
        store_fixture.write_todo(self.repo, todo)
        value = status.snapshot(self.repo, now=10)
        self.assertEqual([(r['task'], r['reason'], r['blocked_by']) for r in value['tasks']],
                         [('A', 'wait for deferred D', ['D']), ('B', 'wait for deferred D', ['A'])])
        self.assertIn('wait for deferred D', status.render(value))
        self.assertEqual([(r['id'], r['kind'], r.get('deferred')) for r in value['roots']],
                         [('D', 'outside', True)])
        sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'pi-autowork'))
        from pi_autowork import health
        self.assertEqual(health.waiting_groups(value['tasks'])[0]['label'], 'wait for deferred D')
        self.assertIn('deferred by owner', health.describe(value['roots'][0]))


class LargeQueueTests(unittest.TestCase):
    def test_large_queue_status_is_unchanged_and_dispatch_releases_its_lock_promptly(self):
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            todo = '## Now\n' + ''.join(
                f'- [ ] T-{i:03} — task {i}\n  Scope: file{i}.py\n  Acceptance: works\n'
                f'  Checks: test {i}\n  Dependencies: OLD\n'
                f'  Evidence: {"." * 3072}\n' for i in range(80))
            self.assertGreater(len(todo.encode()), 250_000)
            (repo / 'TODO.archive.md').write_text('## Done\n- [x] OLD — prerequisite\n')
            store_fixture.write_todo(repo, todo)
            start = time.monotonic()
            with patch.object(execution, 'select', wraps=execution.select) as select:
                value = status.snapshot(repo, now=100)
            self.assertLess(time.monotonic() - start, 1.5)
            rows = [dict(task=f'T-{i:03}', state='waiting', slot=None, elapsed_seconds=0,
                         reason='awaiting dispatch', worktree=None, checks=None, commit=None,
                         integration=None, attempt=0, worker_live=False, blocked_by=[]) for i in range(80)]
            self.assertEqual(value, dict(outcome='PARALLEL_STATUS', workspace=str(repo),
                active_workers=0, max_workers=0, tasks=rows, roots=[], completed=0, failed=0,
                integration_queue=0, metrics=dict(wall_seconds=0.0, worker_seconds=0.0,
                integration_seconds=0.0, waiting_seconds=0.0, peak_workers=0, conflicts=0, retries=0)))
            self.assertEqual(select.call_count, 0)  # one eligibility pass, not 80 selections
            start = time.monotonic()
            process = subprocess.run([sys.executable, str(Path(execution.__file__).with_name('owner_cycle.py')),
                str(repo), '--apply', '--parallel', '2', '--owner-pid', str(os.getpid()),
                '--worker-command', '["python3", "-c", "pass"]', '--min-free-mem-mb', str(2 ** 50)],
                capture_output=True, text=True, timeout=15)
            self.assertEqual(process.returncode, 0, process.stdout + process.stderr)
            self.assertEqual(json.loads(process.stdout)['dispatched'], [])
            self.assertLess(time.monotonic() - start, 3)
            with execution.lock(repo / '.git/autowork-execution/dispatch.lock'):
                pass


if __name__ == '__main__':
    unittest.main()
