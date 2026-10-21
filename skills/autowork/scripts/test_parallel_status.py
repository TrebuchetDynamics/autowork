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
        (self.repo / 'TODO.md').write_text(self.todo)
        self.common = self.repo / '.git/autowork-execution'
        (self.common / 'slots').mkdir(parents=True)

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
                    todo = todo.replace('Status: open', 'Status: in_progress', 1)
                (self.repo / 'TODO.md').write_text(todo)
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

    def test_claim_roots_show_hold_evidence_or_the_actual_adoption_window(self):
        todo = self.todo.replace('Status: open', 'Status: in_progress', 1)
        todo = todo.replace('Task B\n', 'Task B\n  Dependencies: A.\n').replace(
            '  Checks: python3 -V\n  Dependencies: None.', '  Checks: python3 -V')
        path = self.repo / 'TODO.md'
        path.write_text(todo)
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture',
                        '-c', 'user.email=fixture@local', 'commit', '-qm', 'claim'], check=True,
                       env={**os.environ, 'GIT_AUTHOR_DATE': '@1000 +0000', 'GIT_COMMITTER_DATE': '@1000 +0000'})
        (self.common / 'journal.jsonl').write_text(json.dumps(dict(
            timestamp=1000, event='dispatch_observed', waiting=[], adopt_idle_claims=21600)) + '\n')
        note = 'canonical inclusion requires authority permitting canonical HEAD/index changes'
        for now, extra, seconds in ((2000, '', 20600), (22600, '', 0),
                                    (22600, f'  Evidence: {note}\n', None)):
            with self.subTest(now=now, note=extra):
                path.write_text(todo.replace('  Status: in_progress\n', '  Status: in_progress\n' + extra))
                with patch.object(execution, 'external_workers', return_value=[]):
                    root = status.snapshot(self.repo, now=now)['roots'][0]
                self.assertEqual((root['id'], root['kind']), ('A', 'claim'))
                if extra:
                    self.assertIn(note, root['held_by'])
                    self.assertNotIn('adoptable_after', root)
                else:
                    self.assertEqual(root['adoptable_after'], seconds)
                    if seconds == 0:
                        self.assertIn('adopted when a worker slot frees', root['reason'])
        # A legacy observation does not prove that adoption was enabled.
        path.write_text(todo)
        (self.common / 'journal.jsonl').write_text(json.dumps(dict(
            timestamp=1000, event='dispatch_observed', waiting=[])) + '\n')
        with patch.object(execution, 'external_workers', return_value=[]):
            value = status.snapshot(self.repo, now=22600)
        self.assertIsNone(value['roots'][0]['adoptable_after'])
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pi-autowork'))
        from pi_autowork import questions
        self.assertEqual([q['id'] for q in questions.build(value, todo, execution.goals_module())], ['A'])

    def test_deferred_dependencies_are_named_in_status_without_new_question_kinds(self):
        todo = self.todo.replace('Dependencies: None.', 'Dependencies: D.', 1)
        todo = todo.replace('Dependencies: None.', 'Dependencies: A.', 1)
        todo += ('\n## Needs decision\n\n- [ ] D — Device qualification\n'
                 '  Owner decision: 2026-10-18: defer until hardware arrives.\n')
        (self.repo / 'TODO.md').write_text(todo)
        value = status.snapshot(self.repo, now=10)
        self.assertEqual([(r['task'], r['reason'], r['blocked_by']) for r in value['tasks']],
                         [('A', 'wait for deferred D', ['D']), ('B', 'wait for deferred D', ['A'])])
        self.assertIn('wait for deferred D', status.render(value))
        self.assertEqual([(r['id'], r['kind'], r.get('deferred')) for r in value['roots']],
                         [('D', 'outside', True)])
        sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'pi-autowork'))
        from pi_autowork import health, questions
        self.assertEqual(questions.build(value, todo, execution.goals_module()), [])
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
            (repo / 'TODO.md').write_text(todo)
            (repo / 'TODO.archive.md').write_text('## Done\n- [x] OLD — prerequisite\n')
            subprocess.run(['git', '-C', str(repo), 'add', '.'], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@local', 'commit', '-qm', 'fixture'], check=True)
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
