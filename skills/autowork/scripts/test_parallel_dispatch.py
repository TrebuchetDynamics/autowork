"""Offline parallel dispatch checks with a deterministic fake worker CLI."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
import parallel_dispatch as dispatch
import parallel_state as state
import task_execution as execution

FAKE = SCRIPTS / 'fixtures' / 'fake_worker.py'


def task(tid, touches, depends='None'):
    lines = [f'- [ ] {tid} — Task {tid}', f'- Scope: change {touches}.', '- Acceptance: changed.',
             '- Checks: inspect.', f'- Dependencies: {depends}.']
    if touches:
        lines.append(f'- Touches: {touches}')
    return '\n'.join(lines) + '\n'


class DispatchTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo = self.root / 'repo'
        self.repo.mkdir()
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'), task('C', 'c.txt', 'A'),
                        task('E', 'e.txt'), task('D', 'a.txt'))
        self.git('add', '.')
        self.git('commit', '-qm', 'base')
        self.owner = os.getppid()
        self.common = state.common_dir(self.repo)
        self.spec = self.root / 'spec.json'
        self.log = self.root / 'workers.jsonl'
        self.log.touch()
        self.set_spec({})
        for patcher in (patch.dict(os.environ, FAKE_WORKER_SPEC=str(self.spec), FAKE_WORKER_LOG=str(self.log)),
                        patch.object(dispatch, 'available_memory_mb', return_value=10 ** 6),
                        patch.object(os, 'getloadavg', return_value=(0.0, 0.0, 0.0))):
            patcher.start()
            self.addCleanup(patcher.stop)
        self.addCleanup(self.stop_workers)

    def stop_workers(self):
        for slot in state.slots(self.common) if (self.common / 'slots').exists() else ():
            if state.worker_live(slot):
                dispatch.stop(slot['worker'], slot['worktree'])

    def git(self, *args, repo=None):
        return execution.git(repo or self.repo, *args)

    def write_todo(self, *bodies):
        (self.repo / 'TODO.md').write_text('# Work queue\n\n## Next\n\n' + '\n'.join(bodies))

    def set_spec(self, spec):
        self.spec.write_text(json.dumps(spec))

    def run_cli(self, *args, worker=True):
        argv = [str(self.repo), '--owner-pid', str(self.owner), *args]
        if worker:
            argv += ['--worker-command', json.dumps([sys.executable, str(FAKE), '{prompt_file}', '{worktree}'])]
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = execution.main(argv)
        return code, json.loads(out.getvalue())

    def apply(self, *extra):
        return self.run_cli('--apply', '--parallel', *extra)

    def wait(self, timeout=20, *extra):
        return self.run_cli('--parallel', '--wait', '--timeout', str(timeout), *extra)

    def events(self):
        return [json.loads(line) for line in self.log.read_text().splitlines()]

    def wait_until_idle(self):
        for _ in range(40):
            _, result = self.wait(20)
            if result['active_workers'] == 0:
                return result
        self.fail('workers did not finish')

    def test_independent_tasks_run_together_in_separate_worktrees(self):
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 1.0},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 1.0}})
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (0, 'DISPATCHED'), result)
        self.assertEqual([s['task'] for s in result['dispatched']], ['A', 'B'])
        self.assertEqual({w['id']: w['reason'] for w in result['waiting']}['D'], 'overlapping paths with A')
        self.assertIn('all 2 worker slots busy', {w['id']: w['reason'] for w in result['waiting']}['E'])
        self.assertNotIn('C', [w['id'] for w in result['waiting']])  # C's dependency is unfinished
        _, again = self.apply()
        self.assertEqual((again['outcome'], again['dispatched']), ('WAITING', []))  # no duplicate start
        self.wait_until_idle()
        times = {(e['task'], e['event']): e for e in self.events()}
        self.assertLess(times['A', 'start']['time'], times['B', 'end']['time'])
        self.assertLess(times['B', 'start']['time'], times['A', 'end']['time'])
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 2)
        slots = {s['task_id']: s for s in state.slots(self.common)}
        for tid, slot_no in (('A', '1'), ('B', '2')):
            worktree = self.repo / '.worktrees' / f'autowork-{tid}'
            self.assertEqual(Path(times[tid, 'start']['cwd']), worktree)
            self.assertEqual(slots[tid]['state'], 'reported')
            self.assertEqual(slots[tid]['commit'], self.git('rev-parse', 'HEAD', repo=worktree))
            self.assertEqual(self.git('symbolic-ref', '--short', 'HEAD', repo=worktree), 'autowork/' + tid)
            self.assertEqual(times[tid, 'start']['slot'], slot_no)
            self.assertEqual(times[tid, 'start']['port_base'], str(20000 + 100 * int(slot_no)))
            self.assertTrue(times[tid, 'start']['tmpdir'].startswith(str(self.common / 'slot-data' / tid)))
            self.assertFalse(times[tid, 'start']['marker'])
        prompt = (self.common / 'slot-data/A/attempt-1/prompt.md').read_text()
        for text in ('Task: A', 'Touches: a.txt', 'Never edit TODO.md', 'Report file: ', '- Touches: a.txt'):
            self.assertIn(text, prompt)
        self.assertEqual(self.git('status', '--porcelain'), '')  # canonical checkout untouched
        journal = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        moment = {(e['task_id'], e['state']): e['timestamp'] for e in journal if e['event'] == 'slot_changed'}
        self.assertLess(moment['B', 'running'], moment['A', 'reported'])
        self.assertLess(moment['A', 'running'], moment['B', 'reported'])

    def test_directory_containing_manifest_is_serial_beside_independent_work(self):
        """TOOLSET-160-df: it never runs beside other serial work, but no longer alone."""
        for tracked in (True, False):
            with self.subTest(tracked=tracked):
                self.write_todo(task('A', 'component/'), task('B', 'other/'), task('C', 'go.sum'))
                (self.repo / 'component').mkdir(exist_ok=True)
                manifest = self.repo / 'component/go.mod'
                manifest.write_text('module example.invalid/component\n')
                if tracked:
                    self.git('add', 'component/go.mod')
                    self.git('commit', '-qm', 'protected manifest')
                else:
                    self.git('rm', '--cached', 'component/go.mod')
                self.assertEqual(dispatch.protected_files(self.repo), ['component/go.mod'])
                planned = dispatch.parallel_plan.plan(execution.select_all(self.repo),
                                                      protected_files=dispatch.protected_files(self.repo))
                self.assertEqual([t['id'] for t in planned['dispatch']], ['A', 'B'])
                self.assertEqual(planned['waiting'][0]['reason'], 'serial path shared with A')

    def test_eight_disjoint_directory_workers_launch_together(self):
        self.write_todo(*(task(f'T{i}', f'component{i}/') for i in range(8)))
        self.git('add', 'TODO.md')
        self.git('commit', '-qm', 'directory task scopes')
        self.set_spec({f'T{i}': {'sleep': 60} for i in range(8)})
        code, result = self.apply('8', '--max-workers', '8')
        self.assertEqual((code, result['active_workers']), (0, 8), result)
        self.assertEqual({s['slot'] for s in result['dispatched']}, set(range(1, 9)))

    def test_refill_starts_next_task_when_a_worker_finishes(self):
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.2},
                       'B': {'files': {'b.txt': 'b'}, 'sleep': 3.0},
                       'E': {'files': {'e.txt': 'e'}, 'sleep': 0.2}})
        self.apply()
        _, changed = self.wait(20)
        self.assertEqual([c['task'] for c in changed['changed']], ['A'])
        _, refill = self.apply()
        # E takes the free slot; D still overlaps A's unintegrated commit.
        self.assertEqual([s['task'] for s in refill['dispatched']], ['E'])
        self.assertEqual(refill['dispatched'][0]['slot'], 1)
        self.wait_until_idle()
        times = {(e['task'], e['event']): e['time'] for e in self.events()}
        self.assertLess(times['E', 'start'], times['B', 'end'])

    def test_dependent_task_waits_until_its_dependency_is_done(self):
        self.write_todo(task('A', 'a.txt'), task('C', 'c.txt', 'A'))
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.2}})
        _, result = self.apply()
        self.assertEqual([s['task'] for s in result['dispatched']], ['A'])
        self.wait_until_idle()
        _, result = self.apply()
        self.assertEqual(result['dispatched'], [])  # A is reported, not done

    def test_timed_out_worker_is_stopped_and_its_worktree_kept(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 60, 'commit': False}})
        self.apply('--worker-timeout', '1')
        started = time.time()
        _, result = self.wait(20, '--worker-timeout', '1')
        self.assertLess(time.time() - started, 15)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'interrupted')
        self.assertIn('timeout', slot['reason'])
        self.assertFalse(state.worker_live(slot))
        self.assertEqual((self.repo / '.worktrees/autowork-A/a.txt').read_text(), 'partial')

    def test_crashed_worker_restarts_once_in_the_same_worktree(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('interrupted', 1))
        _, retry = self.apply()
        self.assertEqual([(s['task'], s['attempt']) for s in retry['dispatched']], [('A', 2)])
        self.assertEqual(retry['dispatched'][0]['worktree'], slot['worktree'])
        self.assertIn('previous attempt was interrupted', (self.common / 'slot-data/A/attempt-2/prompt.md')
                      .read_text().lower())
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'held')  # second failure stays held
        _, after = self.apply()
        self.assertEqual(after['dispatched'], [])
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 2)

    def test_a_held_slot_of_a_closed_task_stops_occupying(self):
        """india: Plan For Me superseded a held second attempt, and its must-run-alone
        successor waited beside the dead slot for ever."""
        self.write_todo(task('A', 'a.txt'), task('S', ''))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        for _ in range(2):  # crash, restart once, crash again: held for good
            _, first = self.apply()
            self.assertEqual([d['task'] for d in first['dispatched']], ['A'])  # S must run alone
            self.wait_until_idle()
        self.assertEqual((state.slots(self.common)[0]['state'], state.slots(self.common)[0]['cause']), ('held', 'crash'))
        # An exhausted hold waits for a person, not the pool: S starts at once, and
        # closing A meanwhile keeps it out of the way too.
        _, freed = self.apply()
        self.assertEqual([d['task'] for d in freed['dispatched']], ['S'])
        self.assertEqual(next(s for s in state.slots(self.common) if s['task_id'] == 'A')['state'], 'held')

    def test_a_retryable_slot_of_a_closed_task_stops_occupying(self):
        self.write_todo(task('A', 'a.txt'), task('S', ''))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        self.apply()
        self.wait_until_idle()  # crashed once: interrupted, with its restart still to come
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('interrupted', 1))
        self.write_todo(task('A', 'a.txt').replace('- [ ] A', '- [x] A'), task('S', ''))
        _, freed = self.apply()
        self.assertEqual([d['task'] for d in freed['dispatched']], ['S'])

    def test_a_worker_that_reports_a_blocker_is_held_for_a_person_not_resumed(self):
        """sierra TASK-022: a worker stopped on purpose with blockers, was read as a crash,
        resumed, and spent both attempts on the same wall."""
        self.write_todo(task('A', 'a.txt'), task('S', ''))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Needs src/other.go, outside Touches']},
                       'S': {'files': {'s.txt': 'done'}, 'sleep': 0.1}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause'], slot['attempt']), ('held', 'blocker', 1))
        self.assertEqual(slot['reason'], 'worker reported a blocker: Needs src/other.go, outside Touches')
        self.assertEqual((Path(slot['worktree']) / 'a.txt').read_text(), 'partial')
        _, refill = self.apply()  # no resume, no fresh retry; the must-run-alone S proceeds
        self.assertEqual([d['task'] for d in refill['dispatched']], ['S'])
        self.wait_until_idle()
        self.assertEqual([e['task'] for e in self.events() if e['event'] == 'start'], ['A', 'S'])

    def test_an_idle_claim_is_adopted_only_when_asked_and_names_its_prior_work(self):
        """sierra: 28 of 36 tasks were in_progress claims of sessions idle for a day."""
        self.write_todo(task('A', 'a.txt') + '- Status: in_progress\n')
        self.git('commit', '-qam', 'A claimed elsewhere')
        self.git('branch', 'agent/x/A-planning')
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1}})
        time.sleep(1.2)
        _, plain = self.apply()
        self.assertEqual(plain['dispatched'], [])
        _, adopted = self.apply('--adopt-idle-claims', '1')
        self.assertEqual([d['task'] for d in adopted['dispatched']], ['A'])
        prompt = (dispatch.data_dir(self.common, state.slots(self.common)[0]) / 'prompt.md').read_text()
        self.assertIn('marked in_progress by another session that has been idle', prompt)
        self.assertIn('- branch agent/x/A-planning', prompt)
        journal = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        self.assertEqual([e['task_id'] for e in journal if e['event'] == 'claim_adopted'], ['A'])
        self.wait_until_idle()

    def test_a_worker_asking_for_more_files_resumes_in_place_once_touches_cover_them(self):
        """sierra TASK-024: a worker needed one test file outside Touches and could only stop."""
        self.write_todo(task('A', 'a.txt'))
        self.git('add', '.')
        self.git('commit', '-qm', 'A')
        self.set_spec({'A': {'files': {'a.txt': 'half', 'b.txt': 'needed'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['b.txt is outside Touches'], 'needs_touches': ['b.txt'],
                             'then': {'files': {'a.txt': 'done', 'b.txt': 'done'}, 'sleep': 0.1}}})
        self.apply()
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['cause'], slot['requested']), ('held', 'scope_request', ['b.txt']))
        _, again = self.apply()
        self.assertEqual(again['outcome'], 'IDLE')  # not covered yet: waits for a person or the runner
        self.write_todo(task('A', 'a.txt, b.txt'))
        self.git('commit', '-qam', 'widen A')
        _, resumed = self.apply()
        self.assertEqual(resumed['outcome'], 'RESUMED')
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 1, True))
        self.assertEqual((Path(slot['worktree']) / 'b.txt').read_text(), 'needed')  # its work is intact
        _, dispatched = self.apply()
        self.assertEqual([d['task'] for d in dispatched['dispatched']], ['A'])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('reported', 1))  # same attempt, now committed
        prompt = (dispatch.data_dir(self.common, slot) / 'prompt.md').read_text()
        self.assertIn('change only paths within Touches: a.txt, b.txt', prompt)

    def test_an_answered_question_requeues_the_held_task_once(self):
        """TOOLSET-120-fc: the owner answers by editing the task's entry; nobody runs a command."""
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        self.git('add', '.')
        self.git('commit', '-qm', 'A and B')
        self.set_spec({'A': {'files': {'a.txt': 'half'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Which unit should the output use?'],
                             'then': {'files': {'a.txt': 'done'}, 'sleep': 0.1}},
                       'B': {'files': {'b.txt': 'half'}, 'sleep': 0.1, 'commit': False,
                             'blockers': ['Needs a decision too']}})
        self.apply()
        self.wait_until_idle()
        self.assertEqual({s['task_id']: s['cause'] for s in state.slots(self.common)}, {'A': 'blocker', 'B': 'blocker'})
        _, unchanged = self.apply()
        self.assertEqual(unchanged['outcome'], 'IDLE')  # no answer yet: both stay held
        self.write_todo(task('A', 'a.txt').replace('- Acceptance: changed.', '- Acceptance: changed, in metres.'),
                        task('B', 'b.txt'))
        self.git('commit', '-qam', 'owner answers A')
        _, requeued = self.apply()
        self.assertEqual((requeued['outcome'], requeued['task'], requeued['requeued']), ('REQUEUED', 'A', True))
        self.assertIn('autowork/A-set-aside-1', self.git('branch', '--list', 'autowork/*'))
        _, fresh = self.apply()
        self.assertEqual([d['task'] for d in fresh['dispatched']], ['A'])
        self.wait_until_idle()
        slots = {s['task_id']: s for s in state.slots(self.common)}
        self.assertEqual((slots['A']['state'], slots['A']['attempt']), ('reported', 1))
        self.assertEqual(slots['B']['state'], 'held')  # unchanged entry: still waiting for its answer

    def test_a_held_task_whose_entry_is_removed_is_set_aside_without_requeue(self):
        self.write_todo(task('A', 'a.txt'), task('B', 'b.txt'))
        self.git('add', '.')
        self.git('commit', '-qm', 'A and B')
        self.set_spec({'A': {'files': {'a.txt': 'half'}, 'sleep': 0.1, 'commit': False, 'blockers': ['Drop this?']}})
        self.apply()
        self.wait_until_idle()
        self.write_todo(task('B', 'b.txt'))
        self.git('commit', '-qam', 'owner drops A')
        _, result = self.apply()
        self.assertEqual((result['outcome'], result['task'], result['requeued']), ('REQUEUED', 'A', False))
        self.assertNotIn('A', [s['task_id'] for s in state.slots(self.common)])

    def pause_and_stop(self):
        """What a deliberate coordinator stop does: mark live workers, then interrupt them."""
        _, paused = self.run_cli('--parallel-pause', worker=False)
        self.assertEqual(paused['outcome'], 'PAUSED')
        for slot in state.slots(self.common):
            if state.worker_live(slot):
                dispatch.stop(slot['worker'], slot['worktree'])
        return paused['paused']

    def test_a_paused_worker_resumes_the_same_attempt(self):
        """india: a service restart interrupted attempt 2 of TASK-015 and held it for good."""
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.apply()
        self.wait_until_idle()  # a real crash: the retry is spent
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 30, 'commit': False}})
        _, second = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in second['dispatched']], [('A', 2)])
        self.assertEqual(self.pause_and_stop(), ['A'])
        self.wait_until_idle()
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot.get('paused')), ('interrupted', 2, True))
        self.set_spec({'A': {'files': {'a.txt': 'done'}, 'sleep': 0.1}})
        _, resumed = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in resumed['dispatched']], [('A', 2)])
        self.assertEqual(resumed['dispatched'][0]['worktree'], slot['worktree'])
        self.assertNotIn('paused', state.slots(self.common)[0])
        self.wait_until_idle()
        self.assertEqual(state.slots(self.common)[0]['state'], 'reported')

    def test_a_paused_first_attempt_keeps_its_retry(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 30, 'commit': False}})
        self.apply()
        self.pause_and_stop()
        self.wait_until_idle()
        _, resumed = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in resumed['dispatched']], [('A', 1)])
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'exit': 1}})
        self.stop_workers()
        self.wait_until_idle()  # this unpaused death spends attempt 1 as before
        _, retry = self.apply()
        self.assertEqual([(d['task'], d['attempt']) for d in retry['dispatched']], [('A', 2)])

    def test_low_memory_holds_dispatch(self):
        with patch.object(dispatch, 'available_memory_mb', return_value=1000):
            _, result = self.apply()
        self.assertEqual(result['outcome'], 'IDLE')
        self.assertEqual(result['dispatched'], [])
        self.assertTrue(all('resource gate' in w['reason'] for w in result['waiting']
                            if w['id'] in ('A', 'B')))
        self.assertFalse((self.common / 'slots').exists() and state.slots(self.common))

    def test_existing_user_branch_or_folder_is_refused_untouched(self):
        self.write_todo(task('A', 'a.txt'))
        self.git('branch', 'autowork/A')
        before = self.git('rev-parse', 'autowork/A')
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'))
        self.assertIn('already exists', result['reason'])
        self.assertEqual(self.git('rev-parse', 'autowork/A'), before)
        self.git('branch', '-D', 'autowork/A')
        folder = self.repo / '.worktrees/autowork-A'
        folder.mkdir(parents=True)
        (folder / 'mine').write_text('user data')
        _, result = self.apply()
        self.assertIn('already exists', result['reason'])
        self.assertEqual(sorted(p.name for p in folder.iterdir()), ['mine'])
        self.assertEqual(self.events(), [])
        journal = self.common / 'journal.jsonl'
        self.assertNotIn('worktree_created', journal.read_text() if journal.exists() else '')

    def test_unsupported_host_falls_back_to_the_sequential_contract(self):
        for args in (('--worker-host', 'claude'), ('--worker-host', 'hermes')):
            with self.subTest(args=args), patch.object(dispatch.shutil, 'which', return_value=None):
                code, result = self.run_cli('--apply', '--parallel', *args, worker=False)
                self.assertEqual((code, result['outcome']), (0, 'SEQUENTIAL_FALLBACK'))
                self.assertEqual(result['task']['id'], 'A')
                self.assertFalse((self.common / 'coordinator.json').exists())
        self.assertEqual(self.events(), [])

    def test_templates_never_bypass_approvals_and_use_scoped_write_roots(self):
        for host, template in dispatch.TEMPLATES.items():
            text = ' '.join(template)
            for flag in ('--yolo', 'bypass', 'danger', 'skip-permissions', '--approve'):
                self.assertNotIn(flag, text, host)
        self.assertIn('{git_common_dir}', dispatch.TEMPLATES['codex'])
        codex = type('Args', (), {'worker_command': None, 'worker_host': 'codex', 'worker_profile': None})
        with patch.object(dispatch.shutil, 'which', return_value='/bin/codex'):
            self.assertEqual(dispatch.worker_command(codex, self.owner)[0], None)  # not qualified live
            self.assertIn('read-only', dispatch.worker_command(codex, self.owner)[1])
        args = type('Args', (), {'worker_command': None, 'worker_host': 'hermes', 'worker_profile': 'work'})
        with patch.object(dispatch.shutil, 'which', return_value='/bin/hermes'):
            template, host = dispatch.worker_command(args, self.owner)
        self.assertEqual((template[:4], host), (['hermes', '-p', 'work', 'chat'], 'hermes'))

    def test_hermes_launcher_process_is_detected_as_the_coordinator_host(self):
        process = subprocess.Popen([sys.executable, '-I', '-c', 'import time  # hermes_cli.main\ntime.sleep(30)'])
        self.addCleanup(process.wait)
        self.addCleanup(process.kill)
        time.sleep(0.2)
        self.assertEqual(dispatch.coordinator_host(process.pid), 'hermes')

    def test_worker_keeps_the_timeout_it_was_started_with(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 60, 'commit': False}})
        self.apply('--worker-timeout', '1')
        _, result = self.wait(20)  # default --worker-timeout 3600 on this call
        self.assertEqual(state.slots(self.common)[0]['state'], 'interrupted')

    def test_surviving_child_keeps_the_slot_live_until_the_group_is_stopped(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'partial'}, 'sleep': 0.1, 'commit': False, 'orphan': True}})
        self.apply('--worker-timeout', '3')
        _, first = self.wait(1.5)
        self.assertEqual(first['outcome'], 'TIMEOUT')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'running')
        self.assertTrue(state.worker_live(slot))
        _, again = self.apply()
        self.assertEqual(again['dispatched'], [])  # no second writer beside the orphan
        _, stopped = self.wait(20)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'interrupted')
        self.assertFalse(state.group_alive(slot['worker']['pid']))
        self.assertEqual(len([e for e in self.events() if e['event'] == 'start']), 1)

    def test_dispatch_interrupted_before_its_slot_adopts_the_recorded_worktree(self):
        self.write_todo(task('A', 'a.txt'))
        self.set_spec({'A': {'files': {'a.txt': 'a'}, 'sleep': 0.1}})
        with patch.object(state, 'create_slot', side_effect=ValueError('lost lease')):
            code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'))
        self.assertTrue((self.repo / '.worktrees/autowork-A').is_dir())
        _, result = self.apply()
        self.assertEqual([(s['task'], s['attempt']) for s in result['dispatched']], [('A', 1)])
        self.assertEqual(result['dispatched'][0]['worktree'], str(self.repo / '.worktrees/autowork-A'))

    def test_launch_failure_is_held_with_its_cause_without_a_retry(self):
        self.write_todo(task('A', 'a.txt'))
        code, result = self.run_cli('--apply', '--parallel', '--worker-command', json.dumps([str(self.root / 'missing')]),
                                    worker=False)
        self.assertEqual(result['dispatched'], [])
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt']), ('held', 1))
        self.assertIn('worker launch failed', slot['reason'])

    def test_malformed_queue_is_reported_not_treated_as_idle(self):
        self.write_todo(task('A', 'a.txt'), task('A', 'b.txt'))
        code, result = self.apply()
        self.assertEqual((code, result['outcome']), (1, 'ACTION_REQUIRED'))
        self.assertIn('duplicate TODO task IDs', result['reason'])

    def test_sequential_apply_is_unchanged_by_parallel_support(self):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = execution.main([str(self.repo), '--apply', '--owner-pid', str(self.owner)])
        result = json.loads(out.getvalue())
        self.assertEqual((code, result['outcome'], result['task']['id']), (0, 'EXECUTE', 'A'))
        self.assertFalse((self.common / 'coordinator.json').exists())
        self.assertFalse((self.common / 'journal.jsonl').exists())

    def test_parallel_needs_owner_and_valid_limits(self):
        for argv in ([str(self.repo), '--apply', '--parallel'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--apply', '--parallel', '5'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--apply', '--parallel', '3',
                      '--max-workers', '9'],
                     [str(self.repo), '--owner-pid', str(self.owner), '--parallel', '--wait']):
            out = io.StringIO()
            with self.subTest(argv=argv[1:]), contextlib.redirect_stdout(out):
                self.assertEqual(execution.main(argv), 1)
            self.assertEqual(json.loads(out.getvalue())['outcome'], 'ACTION_REQUIRED')
        code, result = self.apply('5', '--max-workers', '6')
        self.assertEqual((code, result['max_workers']), (0, 5))


def contract(tid, touches):
    return {'id': tid, 'fields': {'Touches': touches, 'Status': 'open', 'Dependencies': 'None.'}}


class AdmitTests(unittest.TestCase):
    """TOOLSET-157-cd: admission and integration agree about interrupted slots."""

    def admit(self, candidates, running=(), restartable=(), occupying=(), parked=()):
        return dispatch.admit(list(candidates), list(running), {t: {} for t in restartable},
                              [{'task_id': t} for t in occupying], everything=list(candidates) + list(running)
                              + list(parked), parked=list(parked), adopted=set(), protected=None)

    def test_an_interrupted_candidate_resumes_before_fresh_work_on_its_files(self):
        fresh, interrupted = contract('FRESH', 'lib/x.dart'), contract('OLD', 'lib/x.dart, test/x_test.dart')
        result = self.admit([fresh, interrupted], restartable={'OLD'}, occupying={'OLD'})
        self.assertEqual([t['id'] for t in result['dispatch']], ['OLD'])
        self.assertEqual({w['id']: w['reason'] for w in result['waiting']},
                         {'FRESH': 'overlapping paths with OLD'})

    def test_an_interrupted_task_that_cannot_start_still_owns_its_files(self):
        blocker = contract('LIVE', 'lib/y.dart, lib/x.dart')
        interrupted, fresh, other = contract('OLD', 'lib/x.dart'), contract('FRESH', 'lib/x.dart'), contract('C', 'c.py')
        result = self.admit([interrupted, fresh, other], running=[blocker], restartable={'OLD'},
                            occupying={'OLD', 'LIVE'})
        self.assertEqual([t['id'] for t in result['dispatch']], ['C'])
        reasons = {w['id']: w['reason'] for w in result['waiting']}
        self.assertEqual(reasons['OLD'], 'overlapping paths with LIVE')
        self.assertIn(reasons['FRESH'], ('overlapping paths with LIVE', 'overlapping paths with interrupted OLD'))

    def test_a_commit_held_for_overlap_stops_nothing_but_its_dependents(self):
        held, interrupted = contract('HELD', 'lib/x.dart'), contract('OLD', 'lib/x.dart')
        fresh, other = contract('FRESH', 'lib/y.dart'), contract('DEP', 'z.py')
        other['fields']['Dependencies'] = 'HELD.'
        result = self.admit([interrupted, fresh, other], restartable={'OLD'}, occupying={'OLD', 'HELD'},
                            parked=[held])
        self.assertEqual([t['id'] for t in result['dispatch']], ['OLD', 'FRESH'])
        self.assertEqual(result['waiting'], [{'id': 'DEP', 'reason': 'dependency: held HELD', 'blocked_by': ['HELD']}])

    def test_only_a_commit_held_for_overlap_counts_as_overlap_held(self):
        self.assertTrue(state.overlap_held({'state': 'held', 'cause': 'overlap'}))
        for slot in ({'state': 'held', 'cause': 'scope'}, {'state': 'reported', 'cause': 'overlap'}):
            self.assertFalse(state.overlap_held(slot))


if __name__ == '__main__':
    unittest.main()
