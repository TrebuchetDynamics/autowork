"""Offline integration acceptance using disposable real Git repositories."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch
import unittest.mock

sys.path.insert(0, str(Path(__file__).resolve().parent))
from offline_fixtures import fixture_runtime_root
import parallel_dispatch as dispatch
import parallel_state as state
import task_execution as execution


class IntegrationTests(unittest.TestCase):
    def setUp(self):
        # bounded_command sets the CLI helper as a subreaper. These direct unit
        # calls share a process with other modules; restore that process setting.
        import ctypes
        libc = ctypes.CDLL(None)
        previous = ctypes.c_int()
        self.assertEqual(libc.prctl(37, ctypes.byref(previous), 0, 0, 0), 0)
        self.addCleanup(lambda: libc.prctl(36, previous.value, 0, 0, 0))
        # Bootstrap independently of the invoking session's runtime dir.
        self.runtime = tempfile.TemporaryDirectory(prefix='awt-', dir=fixture_runtime_root())
        self.addCleanup(self.runtime.cleanup)
        runtime_env = patch.dict(os.environ, XDG_RUNTIME_DIR=self.runtime.name,
                                 PI_AUTOWORK_WORKER_ROOT=self.runtime.name)
        runtime_env.start()
        self.addCleanup(runtime_env.stop)
        self.temp = tempfile.TemporaryDirectory(prefix='toolset-088-', dir=os.environ.get('TMPDIR'))
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name) / 'repo'
        self.repo.mkdir()
        self.git('init', '-q', '-b', 'main')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Offline fixture')
        self.repo.joinpath('TODO.md').write_text('# TODO\n\n## Next\n\n' + '\n'.join(
            f'- [ ] {t} — Task {t}\n  Scope: {t}.txt\n  Touches: {t}.txt\n  Acceptance: offline fixture\n  Checks: true\n  Dependencies: None.\n  Status: open\n'
            for t in ('A', 'B')))
        for t in ('A', 'B'):
            self.repo.joinpath(t + '.txt').write_text('base\n')
        self.git('add', '.')
        self.git('commit', '-qm', 'baseline')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.owner = os.getppid()
        state.claim(self.repo, self.owner)
        self.common = state.common_dir(self.repo)

    def git(self, *args, cwd=None):
        p = subprocess.run(['git', '-C', str(cwd or self.repo), *args], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stderr)
        return p.stdout.strip()

    def worker(self, task='A', files=None):
        root, branch, base = dispatch.create_worktree(self.repo, self.common, task, self.baseline)
        state.create_slot(self.repo, self.owner, task, worktree=str(root), branch=branch, baseline=base)
        for name, text in (files or {task + '.txt': 'worker\n'}).items():
            (root / name).write_text(text)
        self.git('add', '.', cwd=root)
        self.git('commit', '-qm', 'worker ' + task, cwd=root)
        commit = self.git('rev-parse', 'HEAD', cwd=root)
        slot = state.transition(self.repo, self.owner, task, 'reported', commit=commit)
        data = dispatch.data_dir(self.common, slot)
        execution.save(data / 'report.json', {'task': task, 'commit': commit,
                       'changed_files': list(files or {task + '.txt': ''}), 'checks': [], 'blockers': [], 'changelog': 'fixture'})
        return root, commit

    def retain_evidence(self):
        """Retain command receipts, child output and slot state before fixture cleanup."""
        import shutil
        target = Path(tempfile.mkdtemp(prefix='integration-evidence-', dir=tempfile.gettempdir()))
        for source in [*self.common.glob('*.json'), *self.common.glob('*.log'),
                       *self.common.glob('slots/*.json')]:
            if source.is_file():
                dest = target / source.relative_to(self.common)
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, dest)
        (target / 'children.json').write_text(json.dumps({
            'children': execution.child_pids(os.getpid()),
            'slots': state.slots(self.common)}, indent=2))
        print(f'FIXTURE_EVIDENCE {target}', flush=True)

    def module(self):
        try:
            return importlib.import_module('parallel_integrate')
        except ModuleNotFoundError:
            self.fail('parallel integration implementation is missing')

    def agent_process(self, cwd=None):
        fake = Path(self.temp.name) / 'hermes'
        fake.write_text('import time; time.sleep(60)')
        proc = subprocess.Popen([sys.executable, str(fake)], cwd=cwd or self.repo, start_new_session=True)
        self.sessions = getattr(self, 'sessions', []) + [proc]
        self.addCleanup(lambda: (proc.kill(), proc.wait()) if proc.poll() is None else None)
        return proc

    def owner_commit_during_validation(self, path):
        """A validation command that commits ``path`` to the session once while it runs, as the
        runner does when it takes main beside a review (TOOLSET-233-ba), counting its runs."""
        runs = Path(self.temp.name) / 'runs'
        script = (f'echo run >> {runs}; if [ ! -e {runs}.moved ]; then touch {runs}.moved; '
                  f'mkdir -p "$(dirname {self.repo / path})"; echo note > {self.repo / path}; '
                  f'git -C {self.repo} add {path} && git -C {self.repo} -c user.email=o@example.invalid '
                  f'-c user.name=Owner commit -qm "owner {path}"; fi')
        return ['bash', '-c', script], runs

    def test_a_session_moved_only_by_planning_commits_lands_the_validated_merge_without_revalidating(self):
        self.worker()
        module = self.module()
        argv, runs = self.owner_commit_during_validation('docs/owner-plan.md')
        result = module.integrate(self.repo, self.owner, 'A', argv, 30)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(runs.read_text().count('run'), 1)  # validated once
        self.assertEqual((self.repo / 'A.txt').read_text(), 'worker\n')
        self.assertEqual((self.repo / 'docs/owner-plan.md').read_text(), 'note\n')
        self.assertEqual(self.git('status', '--porcelain'), '')

    def test_a_session_moved_by_a_code_commit_is_validated_again(self):
        self.worker()
        module = self.module()
        argv, runs = self.owner_commit_during_validation('src/owner.py')
        result = module.integrate(self.repo, self.owner, 'A', argv, 30)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(runs.read_text().count('run'), 2)  # the moved path validated again
        self.assertTrue((self.repo / 'src/owner.py').exists())

    def test_new_protected_file_needs_explicit_serial_scope(self):
        module = self.module()
        slot = {'task_id': 'A', 'baseline': self.baseline, 'attempt': 1}
        contracts = {'A': {'fields': {'Touches': 'src/'}}}
        with self.assertRaises(module.Hold):
            module.verify_scope(self.repo, self.common, slot, contracts, ['src/go.mod'])
        contracts['A']['fields']['Touches'] = 'src/, src/go.mod'
        data = dispatch.data_dir(self.common, slot)
        data.mkdir(parents=True, exist_ok=True)
        (data / 'contract.txt').write_text('Scope: src\nTouches: src/, src/go.mod\n')
        module.verify_scope(self.repo, self.common, slot, contracts, ['src/go.mod'])

    def test_existing_protected_file_under_directory_glob_is_accepted(self):
        path = self.repo / 'packages/api/go.mod'
        path.parent.mkdir(parents=True)
        path.write_text('module example.invalid/api\n')
        self.git('add', 'packages/api/go.mod')
        self.git('commit', '-qm', 'existing manifest')
        slot = {'task_id': 'A', 'baseline': self.git('rev-parse', 'HEAD'), 'attempt': 1}
        contracts = {'A': {'fields': {'Touches': 'packages/*/'}}}
        data = dispatch.data_dir(self.common, slot)
        data.mkdir(parents=True, exist_ok=True)
        (data / 'contract.txt').write_text('Scope: packages\nTouches: packages/*/\n')
        self.module().verify_scope(self.repo, self.common, slot, contracts, ['packages/api/go.mod'])

    def test_changed_contract_cannot_retroactively_make_protected_edit_serial(self):
        slot = {'task_id': 'A', 'baseline': self.baseline, 'attempt': 1}
        data = dispatch.data_dir(self.common, slot)
        data.mkdir(parents=True, exist_ok=True)
        (data / 'contract.txt').write_text('Scope: src\nTouches: src/\n')
        for fields in ({'Touches': 'src/, src/go.mod'},
                       {'Touches': 'src/', 'Resources': 'exclusive'}):
            with self.subTest(fields=fields), self.assertRaises(self.module().Hold):
                self.module().verify_scope(self.repo, self.common, slot,
                                           {'A': {'fields': fields}}, ['src/go.mod'])

    def hold_writer_lock_during_validation(self, seconds):
        """The runner's loop takes writer.lock for a moment each cycle beside a review: a validation
        command that announces itself, and a thread that holds the lock from then on."""
        import fcntl, threading
        started = Path(tempfile.mkdtemp()) / 'validating'
        argv = [sys.executable, '-c', f'open({str(started)!r}, "w").close(); import time; time.sleep(1)']

        def hold():
            while not started.exists():
                time.sleep(0.05)
            fd = os.open(self.common / 'writer.lock', os.O_CREAT | os.O_RDWR)
            fcntl.flock(fd, fcntl.LOCK_EX)
            time.sleep(seconds)
            os.close(fd)
        holder = threading.Thread(target=hold)
        holder.start()
        self.addCleanup(holder.join)
        return argv, holder

    def test_an_integration_waits_out_the_loops_brief_hold_of_the_writer_lock(self):
        """TOOLSET-194-46: the review lost the race for writer.lock to the loop's dispatch,
        answered BUSY with its slot left integrating, and the work was later abandoned."""
        self.worker()
        argv, holder = self.hold_writer_lock_during_validation(2.5)
        result = self.module().integrate(self.repo, self.owner, 'A', argv, 30)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def test_an_integration_that_cannot_get_the_lock_gives_its_slot_back(self):
        self.worker()
        module = self.module()
        argv, holder = self.hold_writer_lock_during_validation(1.6)  # past the wait, not past the release
        with unittest.mock.patch.object(module, 'LOCK_WAIT', 0.4):
            result = module.integrate(self.repo, self.owner, 'A', argv, 30)
        self.assertEqual(result['outcome'], 'BUSY', result)
        holder.join()
        self.assertEqual(state.slots(self.common)[0]['state'], 'reported')  # not left integrating
        again = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(again['outcome'], 'INTEGRATED', again)

    def test_a_validation_that_runs_out_of_time_holds_as_timeout_and_can_be_reverified(self):
        """TOOLSET-196-fb: two reviews timed out on a slow host and spent both attempts."""
        self.worker()
        module = self.module()
        result = module.integrate(self.repo, self.owner, 'A', [sys.executable, '-c', 'import time; time.sleep(5)'], 1,
                                  reviewer='r1')
        self.assertEqual(result['outcome'], 'HELD', result)
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['cause'], slot['attempt']), ('timeout', 1))
        self.assertIn('ran out of time', slot['reason'])
        self.assertEqual(module.reverify(self.repo, self.owner, 'A', 'r1.t3600')['outcome'], 'REVERIFY')
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_fresh_unknown_session_blocks_integration_before_writes(self):
        self.worker()
        self.agent_process()
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'BUSY', result)  # no verdict: the commit waits
        self.assertEqual(state.slot_path(self.common, 'A').exists() and state.slots(self.common)[0]['state'], 'reported')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        self.assertFalse((self.repo / '.worktrees/autowork-integration').exists())

    def test_session_appearing_during_validation_blocks_landing(self):
        self.worker()
        module = self.module()
        original = execution.bounded_command
        from unittest.mock import patch
        def validate(*args, **kwargs):
            result = original(*args, **kwargs)
            self.agent_process()
            return result
        with patch.object(execution, 'bounded_command', side_effect=validate):
            result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'BUSY', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrating')  # kept for revalidation
        for proc in self.sessions:
            proc.kill(); proc.wait()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_a_commit_an_earlier_release_held_for_a_live_session_is_offered_again(self):
        """flutter: three commits were held while a person's pi session was in the main checkout."""
        self.worker()
        slot = state.slots(self.common)[0]
        held = dict(slot, state='held', reason='live or unknown external writer/session; preserve canonical checkout: pid 1 pi')
        execution.save(state.slot_path(self.common, 'A'), held)
        result = self.module().retry_held(self.retry_args())
        self.assertEqual((result['outcome'], result['task']), ('REOFFERED', 'A'))
        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_an_abbreviated_commit_in_the_report_is_the_same_commit(self):
        """A complete bootstrap was held on its last attempt because the report named `29a464c3`."""
        module = self.module()
        _, commit = self.worker()
        data = dispatch.data_dir(self.common, state.slots(self.common)[0])
        report = execution.read(data / 'report.json')
        execution.save(data / 'report.json', dict(report, commit=commit[:8]))
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_a_report_mismatch_says_what_differs_and_a_misread_hold_is_offered_again_once(self):
        module = self.module()
        _, commit = self.worker()
        data = dispatch.data_dir(self.common, state.slots(self.common)[0])
        report = execution.read(data / 'report.json')
        execution.save(data / 'report.json', dict(report, commit='0' * 12))
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertIn("commit is '000000000000', the branch is at " + commit[:12], result['reason'])
        # As an earlier release held a correct abbreviated SHA: offered again, once.
        execution.save(data / 'report.json', dict(report, commit=commit[:8]))
        self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'REOFFERED')
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_a_commit_held_for_overlap_owns_nothing_and_is_offered_again_once_free(self):
        """TOOLSET-157-cd: two commits on the same file must not hold each other forever."""
        module = self.module()
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('  Touches: B.txt\n', '  Touches: B.txt, A.txt\n'))
        self.git('commit', '-qam', 'B declares A.txt too')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker('A')
        self.worker('B', {'A.txt': 'b\n'})
        slot = next(s for s in state.slots(self.common) if s['task_id'] == 'B')
        execution.save(state.slot_path(self.common, 'B'),
                       dict(slot, state='held', cause='overlap', reason='changed files violate Touches or ownership'))
        # TOOLSET-161-17: it no longer waits for A to settle; the merge into main decides.
        result = module.retry_held(self.retry_args())
        self.assertEqual((result['outcome'], result['task']), ('REOFFERED', 'B'))
        again = dict(next(s for s in state.slots(self.common) if s['task_id'] == 'B'), state='held', cause='overlap')
        execution.save(state.slot_path(self.common, 'B'), again)
        self.assertNotEqual(module.retry_held(self.retry_args()).get('outcome'), 'REOFFERED')  # once only
        execution.save(state.slot_path(self.common, 'B'), dict(again, state='reported'))
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        held = module.integrate(self.repo, self.owner, 'B', ['true'], 10)  # both rewrote A.txt's one line
        self.assertEqual((held['outcome'], held['cause']), ('HELD', 'conflict'), held)

    def test_an_existing_overlap_hold_is_offered_again_and_integrates(self):
        """TOOLSET-161-17: a commit an earlier release held for overlap integrates by merge."""
        module = self.module()
        _, commit = self.worker('B')
        slot = state.slots(self.common)[0]
        execution.save(state.slot_path(self.common, 'B'), dict(
            slot, state='held', cause='overlap', reason='changed files violate Touches or coordinator/other-slot ownership'))
        self.assertEqual(module.retry_held(self.retry_args()), {'outcome': 'REOFFERED', 'task': 'B', 'commit': commit})
        self.assertEqual(module.integrate(self.repo, self.owner, 'B', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual((self.repo / 'B.txt').read_text(), 'worker\n')

    def session_checkout(self):
        """Integrate in a separate session worktree, as pi-autowork does."""
        session = Path(self.temp.name) / 'session'
        self.git('worktree', 'add', '-q', '-b', 'session', str(session), self.baseline)
        state.release(self.repo, self.owner)
        state.claim(session, self.owner)
        return session

    def holder(self, path):
        """An agent in the main checkout holding ``path`` open for writing."""
        fake = Path(self.temp.name) / 'hermes'
        fake.write_text('import sys, time\nheld = open(sys.argv[1], "a")\ntime.sleep(60)\n')
        proc = subprocess.Popen([sys.executable, str(fake), str(path)], cwd=self.repo, start_new_session=True)
        self.addCleanup(lambda: (proc.kill(), proc.wait()) if proc.poll() is None else None)
        time.sleep(0.5)
        return proc

    def test_a_main_checkout_session_blocks_only_the_files_it_touches(self):
        """sierra TASK-026 waited an hour on owner sessions that touched none of its files."""
        session = self.session_checkout()
        self.worker()
        module = self.module()
        self.agent_process()  # idle at nothing relevant, in the main checkout
        (self.repo / 'B.txt').write_text('owner edit\n')  # uncommitted, but not a file A changes
        self.assertEqual(module.integrate(session, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_a_main_checkout_session_on_the_same_files_still_waits(self):
        session = self.session_checkout()
        self.worker()
        module = self.module()
        self.agent_process()
        (self.repo / 'A.txt').write_text('owner edit\n')  # the owner is changing A's file
        self.assertEqual(module.integrate(session, self.owner, 'A', ['true'], 10)['outcome'], 'BUSY')
        (self.repo / 'A.txt').write_text('base\n')
        self.holder(self.repo / 'A.txt')  # or holds it open for writing
        self.assertEqual(module.integrate(session, self.owner, 'A', ['true'], 10)['outcome'], 'BUSY')

    def test_a_main_checkout_session_blocks_a_close_only_through_the_files_it_writes(self):
        """TOOLSET-223-8e: an uncommitted planning edit is reconciled by the landing step, so it
        no longer blocks a close; a session holding a close file open still does."""
        self.ledger()  # with goals.json, as every real repository: the indexed close path too
        session = self.session_checkout()
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(session, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.agent_process()
        (self.repo / 'TODO.md').write_text((self.repo / 'TODO.md').read_text() + '\n')  # owner planning edit
        held = self.holder(self.repo / 'TODO.md')  # held open for writing: still a block
        with self.assertRaisesRegex(ValueError, 'writer|session'):
            module.close(session, self.owner, 'A')
        held.kill()
        held.wait()
        self.assertEqual(module.close(session, self.owner, 'A')['outcome'], 'CLOSED')

    def test_fresh_session_blocks_close_without_task_writes(self):
        self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        before = (self.repo / 'TODO.md').read_bytes()
        self.agent_process()
        with self.assertRaisesRegex(ValueError, 'writer|session'):
            module.close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        self.assertFalse((self.repo / 'TODO.archive.md').exists())

    def test_a_close_that_fails_after_writing_leaves_no_writes(self):
        """bravo TASK-010: a close failed after archiving and its writes stayed in the
        session uncommitted, where every later merge refused them."""
        self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        files = [self.repo / name for name in ('TODO.md', 'goals.json', 'TODO.archive.md')]
        before = [f.read_bytes() if f.exists() else None for f in files]
        original = module.goals_command
        def archive_then_fail(repo, *argv):
            out = original(repo, *argv)
            if argv[0] == 'archive':
                raise ValueError('fixture failure after the archive')
            return out
        from unittest.mock import patch
        with patch.object(module, 'goals_command', side_effect=archive_then_fail):
            with self.assertRaisesRegex(ValueError, 'fixture failure'):
                module.close(self.repo, self.owner, 'A')
        self.assertEqual([f.read_bytes() if f.exists() else None for f in files], before)
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrated')  # retryable
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')

    def test_session_appearing_during_close_checks_blocks_first_task_write(self):
        self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        before = (self.repo / 'TODO.md').read_bytes()
        original = module.validated_receipt
        from unittest.mock import patch
        def checked(*args):
            result = original(*args)
            self.agent_process()
            return result
        with patch.object(module, 'validated_receipt', side_effect=checked):
            with self.assertRaisesRegex(ValueError, 'writer|session'):
                module.close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        self.assertFalse((self.repo / 'TODO.archive.md').exists())

    def test_a_writer_that_exits_during_the_check_does_not_block(self):
        """A worker's short tool run seen by the scan and gone by the check blocked a close."""
        from unittest.mock import patch
        gone = {'pid': 2 ** 22 + 13, 'start_ticks': 1, 'boot_id': 'x', 'kind': 'session', 'active': True,
                'workspaces': [str(self.repo)], 'evidence': 'running commands'}
        module = self.module()
        with patch.object(execution, 'external_workers', return_value=[gone]):
            module.require_no_writers(self.repo)  # no error: nothing alive to protect against
        alive = dict(gone, pid=os.getpid(), **{k: v for k, v in execution.identity(os.getpid()).items() if k != 'pid'})
        with patch.object(execution, 'external_workers', return_value=[alive]), \
                self.assertRaisesRegex(ValueError, 'live or unknown external writer'):
            module.require_no_writers(self.repo)

    def test_uncommitted_planning_files_do_not_block_a_merge(self):
        """TOOLSET-223-8e: the owner's uncommitted TODO.md made every candidate's session a
        blocker; landing already reconciles planning edits, so only real files count."""
        module = self.module()
        main = module.main_checkout(self.repo)
        proc = self.agent_process()
        worker = {'pid': proc.pid, 'kind': 'session', 'active': True, 'written': [],
                  'workspaces': [main], 'evidence': 'running commands',
                  **{k: v for k, v in execution.identity(proc.pid).items() if k != 'pid'}}
        (self.repo / 'TODO.md').write_text('# TODO\n\n## Next\n\nan owner edit\n')
        self.assertTrue(module.touches_none_of(worker, ['TODO.md'], main))
        (self.repo / 'A.txt').write_text('an owner edit\n')
        self.assertFalse(module.touches_none_of(worker, ['A.txt'], main))
        worker['written'] = [main + '/TODO.md']  # held open for writing still blocks
        self.assertFalse(module.touches_none_of(worker, ['TODO.md'], main))

    def test_a_refused_candidate_records_the_writer_window_on_its_slot(self):
        """TOOLSET-223-8e: a WritersBusy refusal is remembered on the slot, not only in memory."""
        module = self.module()
        self.worker('A')
        with patch.object(module, 'require_no_writers', side_effect=module.WritersBusy('live writer')):
            result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'BUSY', result)
        slot = state.slots(self.common)[0]
        self.assertTrue(module.writers_busy(slot))
        self.assertIn('live writer', slot.get('writers_busy_reason') or '')

    def test_a_writers_busy_candidate_lets_the_next_reported_task_integrate(self):
        """TOOLSET-223-8e: A is first in TODO order but waits for a writer; B integrates,
        and A integrates in its place once the bounded window passes."""
        module = self.module()
        self.worker('A')
        self.worker('B')
        a = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        a.update(writers_busy_at=time.time(), writers_busy_reason='live or unknown external writer/session')
        state.write_slot(self.common, a, a)
        self.assertEqual(module.integrate(self.repo, self.owner, 'B', ['true'], 10)['outcome'], 'INTEGRATED')
        a = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        a['writers_busy_at'] = time.time() - module.WRITERS_BUSY_SKIP - 1
        state.write_slot(self.common, a, a)
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_the_writers_busy_window_is_bounded(self):
        module = self.module()
        self.assertTrue(module.writers_busy({'writers_busy_at': time.time()}))
        self.assertFalse(module.writers_busy({'writers_busy_at': time.time() - module.WRITERS_BUSY_SKIP - 1}))
        self.assertFalse(module.writers_busy({}))

    def test_isolated_pool_session_does_not_block_landing(self):
        self.worker()
        root, _ = self.worker('B')
        fake = Path(self.temp.name) / 'hermes'
        fake.write_text('''import json, os, subprocess, sys
child = None
try:
    depth = int(sys.argv[1])
    pids = [os.getpid()]
    if depth:
        child = subprocess.Popen([sys.executable, __file__, str(depth - 1)],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, start_new_session=True)
        pids += json.loads(child.stdout.readline())
    print(json.dumps(pids), flush=True)
    sys.stdin.read(1)
finally:
    if child:
        child.communicate('x', timeout=5)
''')
        slot = state.slots(self.common)[1]
        for phase in ('running', 'dispatched'):  # resumed with a new leader after coordinator restart
            with self.subTest(phase=phase):
                proc = subprocess.Popen([sys.executable, str(fake), '2'], cwd=root,
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True, start_new_session=True)
                self.addCleanup(lambda p=proc: p.communicate('x', timeout=5) if p.poll() is None else None)
                pids = json.loads(proc.stdout.readline())
                self.assertEqual(len({os.getpgid(pid) for pid in pids}), 3)
                self.assertTrue(set(pids) <= {w['pid'] for w in execution.external_workers(self.repo)})
                slot.update(worker=execution.identity(proc.pid), state=phase)
                execution.save(state.slot_path(self.common, 'B'), slot)
                state.release(self.repo, self.owner)
                state.claim(self.repo, self.owner)
                state.reconcile(self.repo, self.owner)
                try:
                    self.module().require_no_writers(self.repo)
                    if phase == 'dispatched':
                        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
                finally:
                    proc.communicate('x', timeout=5)

    def test_only_live_slot_descendants_in_their_own_temporary_directory_are_exempt(self):
        self.worker('A')
        root, _ = self.worker('B')
        slots = {s['task_id']: s for s in state.slots(self.common)}
        temps = {task: dispatch.worker_tmpdir(dispatch.data_dir(self.common, slot), index)
                 for index, (task, slot) in enumerate(slots.items(), 1)}
        self.addCleanup(lambda: [dispatch.cleanup_tmpdir(self.common, slot) for slot in slots.values()])
        # This test is the live intermediate between the recorded leader and its
        # grandchild; the child starts a new session, as fixture runners do.
        leader = execution.identity(os.getppid())
        unrelated = self.agent_process(root)
        execution.save(state.slot_path(self.common, 'A'),
                       dict(slots['A'], state='running', worker=execution.identity(unrelated.pid)))
        data = dispatch.data_dir(self.common, slots['B'])
        allocation = execution.read(data.parent / 'tmp.json')
        module = self.module()
        identity = execution.identity
        for case, cwd, owner, dead_link, extra, blocked in (
                ('own temp', temps['B'] / 'state/releases/fixture', leader, False, [], False),
                ('worktree and own temp', temps['B'], leader, False, [str(root)], False),
                ('other slot temp', temps['A'], leader, False, [], True),
                ('dead parent link', temps['B'], leader, True, [], True),
                ('unrelated in own temp', temps['B'], identity(unrelated.pid), False, [], True),
                ('unowned var/tmp', Path('/var/tmp'), identity(unrelated.pid), False, [], True),
                ('temp and canonical', temps['B'], leader, False, [str(self.repo)], True),
                ('legacy attempt temp', data / 'tmp', leader, False, [], False)):
            with self.subTest(case=case):
                if case == 'legacy attempt temp':
                    (data.parent / 'tmp.json').unlink()
                    self.addCleanup(execution.save, data.parent / 'tmp.json', allocation)
                cwd.mkdir(parents=True, exist_ok=True)
                proc = self.agent_process(cwd)
                observed = dict(identity(proc.pid), kind='session', active=None, written=[],
                                workspaces=[str(cwd), *extra], evidence='session: activity unknown')
                execution.save(state.slot_path(self.common, 'B'),
                               dict(slots['B'], state='running', worker=owner))
                def live(pid):
                    return None if dead_link and pid == os.getpid() else identity(pid)
                with patch.object(execution, 'external_workers', return_value=[observed]), \
                        patch.object(execution, 'identity', side_effect=live):
                    if blocked:
                        with self.assertRaises(module.WritersBusy):
                            module.require_no_writers(self.repo)
                    else:
                        module.require_no_writers(self.repo)
                proc.kill()
                proc.wait()

    def test_unattributed_session_in_pool_worktree_is_not_exempt(self):
        self.worker()
        root, _ = self.worker('B')
        proc = self.agent_process(root)
        leader = self.agent_process(root)  # unrelated: its parent chain cannot own proc
        slot = state.slots(self.common)[1]
        for fields, why in (
                ({}, 'slot is not dispatched/running'),
                ({'state': 'running', 'worker': None}, 'no recorded worker leader'),
                ({'state': 'running', 'worker': execution.identity(leader.pid)}, 'parent chain'),
                ({'state': 'running', 'worker': dict(execution.identity(proc.pid), start_ticks=1)}, 'leader identity'),
                ({'state': 'running', 'worker': {'pid': 2 ** 22 + 13, 'start_ticks': 1, 'boot_id': 'x'}}, 'leader identity')):
            with self.subTest(why=why):
                execution.save(state.slot_path(self.common, 'B'), dict(slot, **fields))
                result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
                self.assertEqual(result['outcome'], 'BUSY', result)
                self.assertIn("unattributed process in B's worktree: " + why, result['reason'])
                self.assertEqual(state.slots(self.common)[0]['state'], 'reported')
                self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_pool_identity_never_exempts_a_canonical_writer(self):
        self.worker()
        root, _ = self.worker('B')
        proc = self.agent_process()
        slot = state.slots(self.common)[1]
        slot.update(worker=execution.identity(proc.pid), state='running')
        execution.save(state.slot_path(self.common, 'B'), slot)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'BUSY', result)  # no verdict: the commit waits
        self.assertEqual(state.slot_path(self.common, 'A').exists() and state.slots(self.common)[0]['state'], 'reported')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        proc.kill(); proc.wait()
        # Main cwd plus an explicit worker path: still blocks, now explains the slot mismatch.
        mixed = subprocess.Popen([sys.executable, str(Path(self.temp.name) / 'hermes'), str(root / 'B.txt')],
                                 cwd=self.repo, start_new_session=True)
        self.addCleanup(lambda: (mixed.kill(), mixed.wait()) if mixed.poll() is None else None)
        slot['worker'] = execution.identity(mixed.pid)
        execution.save(state.slot_path(self.common, 'B'), slot)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'BUSY', result)
        self.assertIn("unattributed process in B's worktree: process uses workspaces outside the slot", result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_clean_merge_validates_without_sequential_lease(self):
        root, commit = self.worker()
        result = self.module().integrate(self.repo, self.owner, 'A', [sys.executable, '-c',
                    'from pathlib import Path; assert Path("A.txt").read_text()=="worker\\n"'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'integrated')
        self.assertEqual(self.git('rev-parse', 'HEAD^2'), commit)
        self.assertFalse((self.common / 'active.json').exists())
        self.assertTrue(root.exists())


    def test_close_requires_validation_and_archives_only_integrated_task(self):
        root, commit = self.worker()
        module = self.module()
        before = (self.repo / 'TODO.md').read_bytes()
        with self.assertRaises(ValueError):
            module.close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        result = module.close(self.repo, self.owner, 'A')
        self.assertEqual(result['outcome'], 'CLOSED', result)
        self.assertFalse(root.exists())
        self.assertFalse(self.git('branch', '--list', 'autowork/A'))
        self.assertIn('A — Task A', (self.repo / 'TODO.archive.md').read_text())
        self.assertIn('B — Task B', (self.repo / 'TODO.md').read_text())
        self.assertEqual(state.slots(self.common)[0]['state'], 'closed')

    def test_a_missing_report_says_so_and_object_live_checks_keep_their_text(self):
        """india TASK-011: no report.json was held as 'pending_live must be a list of strings'."""
        _, commit = self.worker()
        data = dispatch.data_dir(self.common, state.slots(self.common)[0])
        report = execution.read(data / 'report.json')
        (data / 'report.json').unlink()
        held = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual((held['outcome'], held['reason']), ('HELD', 'the worker wrote no report.json'))
        slot = state.slots(self.common)[0]
        state.write_slot(self.common, dict(slot, state='reported', reason=None, cause=None), slot)
        execution.save(data / 'report.json', dict(report, pending_live=[{'check': 'run on a phone', 'reason': 'device'}]))
        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(state.slots(self.common)[0]['report']['pending_live'], ['run on a phone — device'])
        self.assertEqual(self.module().live_items('on a phone'), ['on a phone'])
        self.assertEqual(self.module().live_items(['a', '', '  ', None, {'command': 'adb'}]), ['a', 'adb'])
        self.assertEqual(self.module().live_items(None), [])

    def test_advisory_check_failures_integrate_but_do_not_override_the_gate(self):
        self.worker()
        slot = state.slots(self.common)[0]
        data = dispatch.data_dir(self.common, slot) / 'report.json'
        report = execution.read(data)
        execution.save(data, dict(report, unrelated_failures=' test_old ',
                                  environment_failures=[{'command': 'flutter test', 'summary': 'tool crashed'}, '', None]))
        held = self.module().integrate(self.repo, self.owner, 'A', ['false'], 10)
        self.assertEqual((held['outcome'], held['cause']), ('HELD', 'validation'))
        self.module().reverify(self.repo, self.owner, 'A', 'fixed-gate')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        saved = state.slots(self.common)[0]['report']
        self.assertEqual(saved['unrelated_failures'], ['test_old'])
        self.assertEqual(saved['environment_failures'], ['flutter test — tool crashed'])

    def test_held_retry_is_fresh_once_and_preserves_first_branch(self):
        root, commit = self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='fixture failure')
        module = self.module()
        from types import SimpleNamespace
        args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, profile='', parallel=2,
            max_workers=None, worker_command='["true"]', worker_host='auto', worker_profile=None,
            worker_timeout=10, min_free_mem_mb=0, tasks=None, plan=None)
        # Exercise a real bounded local process, never an installed model host.
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(.3)'])
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):
            retried = module.retry_held(args)
            self.assertEqual(retried['outcome'], 'RETRIED')
            slot = state.slots(self.common)[0]
            self.assertEqual(slot['attempt'], 2)
            self.assertEqual(slot['branch'], 'autowork/A-r2')
            self.assertEqual(self.git('rev-parse', 'HEAD', cwd=slot['worktree']), self.git('rev-parse', 'HEAD'))
            self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)
            self.assertTrue(root.exists())
            dispatch.stop(slot['worker'])
            state.transition(self.repo, self.owner, 'A', 'held', reason='second failure')
            self.assertEqual(module.retry_held(args)['outcome'], 'IDLE')


    def readopt_fixture(self):
        root, commit = self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason=state.SCOPE_HOLD + " or ownership: {'outside': ['A.txt']}")
        from types import SimpleNamespace
        args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, profile='', parallel=2,
            max_workers=None, worker_command=json.dumps([sys.executable, '-c', 'pass']), worker_host='auto',
            worker_profile=None, worker_timeout=10, min_free_mem_mb=0, tasks=None, plan=None)
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):
            self.assertEqual(self.module().retry_held(args)['outcome'], 'RETRIED')
        slot = state.slots(self.common)[0]
        dispatch.stop(slot['worker'])
        state.transition(self.repo, self.owner, 'A', 'held', reason='retry made no change')
        return args, commit

    def test_a_retry_without_a_commit_reverifies_the_first_commit_once(self):
        args, commit = self.readopt_fixture()
        module = self.module()
        result = module.retry_held(args)
        self.assertEqual(result, {'outcome': 'READOPTED', 'task': 'A', 'commit': commit})
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot['branch']), ('reported', 2, 'autowork/A'))
        self.assertEqual(len(slot['previous_attempts']), 2)
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def test_an_earlier_interruption_of_the_first_attempt_does_not_stop_its_readoption(self):
        """A retry ran for 19 seconds without a result, and the first commit was never offered again."""
        args, commit = self.readopt_fixture()
        slot = state.slots(self.common)[0]
        first = slot['previous_attempts'][0]
        paused = dict(first, state='interrupted', paused=True, reason='dead worker with uncommitted changes')
        paused.pop('commit', None)
        execution.save(state.slot_path(self.common, 'A'), dict(slot, previous_attempts=[paused, first]))
        result = self.module().retry_held(args)
        self.assertEqual(result, {'outcome': 'READOPTED', 'task': 'A', 'commit': commit})

    def test_a_retry_that_stops_with_nothing_is_not_called_a_crash(self):
        self.readopt_fixture()
        slot = state.slots(self.common)[0]
        value = dict(slot, state='running')
        execution.save(state.slot_path(self.common, 'A'), value)
        state.reconcile(self.repo, self.owner)
        self.assertEqual(state.slots(self.common)[0]['cause'], 'empty')

    def test_a_readopted_commit_is_judged_by_the_scope_it_was_dispatched_with(self):
        args, _ = self.readopt_fixture()
        prompt = self.common / 'slot-data' / 'A' / 'attempt-1' / 'prompt.md'
        prompt.parent.mkdir(parents=True, exist_ok=True)
        prompt.write_text('- Work only inside x; change only paths within Touches: (none declared)\n')
        todo = self.repo / 'TODO.md'  # Touches recorded after the hold no longer cover A.txt
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: other.txt'))
        self.git('commit', '-qam', 'later Touches')
        module = self.module()
        self.assertEqual(module.retry_held(args)['outcome'], 'READOPTED')
        self.assertEqual(state.slots(self.common)[0]['touches'], '')
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def test_a_readopted_commit_that_fails_again_stays_held(self):
        args, _ = self.readopt_fixture()
        module = self.module()
        self.assertEqual(module.retry_held(args)['outcome'], 'READOPTED')
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['false'], 10)['outcome'], 'HELD')
        self.assertEqual(module.retry_held(args)['outcome'], 'IDLE')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def exhaust(self, task='A'):
        root, commit = self.worker(task)
        state.transition(self.repo, self.owner, task, 'held', reason='fixture failure')
        slot = state.slots(self.common)[0]
        retry = Path(str(root) + '-r2')
        self.git('worktree', 'add', '-q', '-b', 'autowork/' + task + '-r2', str(retry), self.baseline)
        state.change(self.common, slot, 'dispatched', {'worktree': str(retry), 'branch': 'autowork/' + task + '-r2',
                                                         'baseline': self.baseline})
        (retry / 'wip.txt').write_text('unsaved\n')
        state.transition(self.repo, self.owner, task, 'released')  # second failure: held
        return root, retry, commit

    def paused_retry(self):
        """A held task's -r2 retry, paused by a runner stop, resumed and reported."""
        root, _ = self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='fixture failure')
        retry = Path(str(root) + '-r2')
        self.git('worktree', 'add', '-q', '-b', 'autowork/A-r2', str(retry), self.baseline)
        state.change(self.common, state.slots(self.common)[0], 'dispatched',
                     {'worktree': str(retry), 'branch': 'autowork/A-r2', 'baseline': self.baseline})
        state.transition(self.repo, self.owner, 'A', 'interrupted', paused=True)
        resumed = state.change(self.common, state.slots(self.common)[0], 'dispatched', {})
        self.assertEqual((resumed['attempt'], resumed['branch']), (2, 'autowork/A-r2'))
        (retry / 'A.txt').write_text('retried\n')
        self.git('add', '.', cwd=retry)
        self.git('commit', '-qm', 'retry A', cwd=retry)
        commit = self.git('rev-parse', 'HEAD', cwd=retry)
        slot = state.transition(self.repo, self.owner, 'A', 'reported', commit=commit)
        execution.save(dispatch.data_dir(self.common, slot) / 'report.json', {
            'task': 'A', 'commit': commit, 'changed_files': ['A.txt'], 'checks': [], 'blockers': [],
            'changelog': 'fixture'})
        return commit

    def test_a_paused_and_resumed_held_retry_integrates_from_r2(self):
        """sierra TASK-026: a runner stop paused the -r2 retry; after the resume it was held as
        'unexpected worker branch' instead of being verified."""
        self.paused_retry()
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'retried\n')

    def test_a_retry_held_for_its_own_branch_by_an_earlier_release_is_offered_again(self):
        commit = self.paused_retry()
        slot = state.slots(self.common)[0]
        state.write_slot(self.common, dict(slot, state='held', reason='unexpected worker branch'), slot)
        from types import SimpleNamespace
        args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, tasks=None, plan=None, worker_timeout=10)
        module = self.module()
        self.assertEqual(module.retry_held(args), {'outcome': 'REOFFERED', 'task': 'A', 'commit': commit})
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_an_exhausted_hold_is_set_aside_with_its_work_kept(self):
        root, retry, commit = self.exhaust()
        module = self.module()
        self.assertTrue(state.exhausted(state.slots(self.common)[0]))
        # Dispatch may already have preserved an orphan branch before this slot existed.
        self.git('branch', 'autowork/A-set-aside-1', self.baseline)
        result = module.set_aside(self.repo, self.owner, 'A')
        self.assertEqual((result['outcome'], result['previous_state']), ('SET_ASIDE', 'held'))
        self.assertEqual(state.slots(self.common), [])
        self.assertFalse(root.exists() or retry.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), self.baseline)
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-2'), commit)
        self.assertEqual(Path(str(retry) + '-set-aside-2', 'wip.txt').read_text(), 'unsaved\n')  # dirty: kept
        # TOOLSET-210-53: the clean first attempt's worktree (and its build output) is gone; its branch is kept.
        self.assertFalse(Path(str(root) + '-set-aside-2').exists())
        self.assertTrue(any(r.get('worktree_removed') for r in result['renamed']), result['renamed'])
        self.assertTrue((self.common / 'slot-history' / 'A' / '2' / 'slot.json').exists())
        self.assertFalse((self.common / 'slot-data' / 'A').exists())
        # The task dispatches fresh under its original names.
        fresh, branch, _ = dispatch.create_worktree(self.repo, self.common, 'A', self.baseline)
        self.assertEqual((fresh, branch), (root, 'autowork/A'))
        self.assertEqual(self.git('rev-parse', 'HEAD', cwd=fresh), self.baseline)

    def test_a_finished_commit_is_set_aside_on_request_with_its_commit_kept(self):
        """Stale commits written against code main had redesigned only conflicted, and the
        owner's set-aside request was refused because they were waiting to merge."""
        self.worker('A')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'reported')
        result = self.module().set_aside(self.repo, self.owner, 'A')
        self.assertEqual((result['outcome'], result['previous_state']), ('SET_ASIDE', 'reported'))
        self.assertEqual(state.slots(self.common), [])
        self.assertEqual(self.git('rev-parse', 'autowork/A-set-aside-1'), slot['commit'])

    def test_close_and_set_aside_remove_only_the_retired_slots_temporary_directory(self):
        module = self.module()
        temps = {}
        for task in ('A', 'B'):
            self.worker(task)
            slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
            temps[task] = dispatch.worker_tmpdir(dispatch.data_dir(self.common, slot), 1)
            (temps[task] / 'fixture').write_text(task)
        self.assertNotEqual(temps['A'], temps['B'])
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        self.assertFalse(temps['A'].exists())
        self.assertEqual((temps['B'] / 'fixture').read_text(), 'B')
        # Repeating close must not delete another task's allocation at the old path.
        self.worker('C')
        slot_c = next(s for s in state.slots(self.common) if s['task_id'] == 'C')
        reused = dispatch.worker_tmpdir(dispatch.data_dir(self.common, slot_c), 1)
        self.assertEqual(reused, temps['A'])
        (reused / 'keep').write_text('C')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        self.assertEqual((reused / 'keep').read_text(), 'C')
        state.transition(self.repo, self.owner, 'B', 'held', reason='fixture blocker', cause='blocker')
        self.assertEqual(module.set_aside(self.repo, self.owner, 'B')['outcome'], 'SET_ASIDE')
        self.assertFalse(temps['B'].exists())

    def test_set_aside_refuses_an_integrated_task_that_still_matches_its_entry(self):
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        with self.assertRaisesRegex(ValueError, 'close it instead'):
            module.set_aside(self.repo, self.owner, 'A')
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrated')

    def test_an_integrated_task_whose_entry_changed_is_set_aside_and_queued_again(self):
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Acceptance: offline fixture', 'Acceptance: a rewritten scope', 1))
        self.git('commit', '-qam', 'rewrite A')
        with self.assertRaisesRegex(ValueError, module.CONTRACT_CHANGED):
            module.close(self.repo, self.owner, 'A')
        merged = self.git('rev-parse', 'HEAD')
        self.assertEqual(module.set_aside(self.repo, self.owner, 'A')['outcome'], 'SET_ASIDE')
        self.assertEqual(self.git('rev-parse', 'HEAD'), merged)
        self.assertIn('A', [t['id'] for t in execution.select_all(self.repo, None, None)])

    def test_an_integrated_task_archived_by_someone_else_is_set_aside_not_requeued(self):
        """bravo TASK-001: another writer archived the entry, edited, after the merge."""
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'
        text = todo.read_text()
        start, end = text.index('- [ ] A'), text.index('- [ ] B')
        (self.repo / 'TODO.archive.md').write_text('# Completed\n\n' + text[start:end].replace('- [ ] A', '- [x] A')
                                                   .replace('offline fixture', 'edited while archiving'))
        todo.write_text(text[:start] + text[end:])
        self.git('add', '-A')
        self.git('commit', '-qm', 'someone archives A')
        with self.assertRaisesRegex(ValueError, module.CONTRACT_CHANGED):
            module.close(self.repo, self.owner, 'A')
        result = module.set_aside(self.repo, self.owner, 'A')
        self.assertEqual((result['outcome'], result['requeued']), ('SET_ASIDE', False))
        self.assertNotIn('A', [t['id'] for t in dispatch.contracts(self.repo)])

    def test_an_exhausted_hold_does_not_hold_other_work_at_integration(self):
        self.exhaust('A')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: B.txt', 'Touches: A.txt, B.txt'))
        self.git('commit', '-qam', 'B also owns A.txt')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker('B', {'A.txt': 'overlap\n', 'B.txt': 'worker\n'})
        result = self.module().integrate(self.repo, self.owner, 'B', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def report(self, **fields):
        path = dispatch.data_dir(self.common, state.slots(self.common)[0]) / 'report.json'
        execution.save(path, dict(execution.read(path), **fields))

    def test_a_commit_whose_report_has_blockers_is_held_for_a_person(self):
        self.worker()
        self.report(blockers=['Physical device check not run'])
        module = self.module()
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['cause'], 'blocker')
        self.assertTrue(state.exhausted(slot))
        from types import SimpleNamespace
        args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, profile='', parallel=2,
            max_workers=None, worker_command='["true"]', worker_host='auto', worker_profile=None,
            worker_timeout=10, min_free_mem_mb=0, tasks=None, plan=None)
        self.assertEqual(module.retry_held(args)['outcome'], 'IDLE')

    def test_pending_live_checks_integrate_and_close_into_one_live_followup(self):
        """flutter TASK-013: offline work passed twice but was held for device checks."""
        self.worker()
        self.report(pending_live=['TalkBack scrolling on a physical phone', 'Hardware GPU frame rate'])
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        result = module.close(self.repo, self.owner, 'A')
        self.assertEqual((result['outcome'], result['live_followup']), ('CLOSED', 'A-LIVE'))
        todo = (self.repo / 'TODO.md').read_text()
        self.assertIn('## Needs decision\n\n- [ ] A-LIVE — Live checks for A\n', todo)
        self.assertIn('  - TalkBack scrolling on a physical phone\n', todo)
        self.assertIn('  Dependencies: A.\n', todo)
        self.assertNotIn('- [ ] A — Task A', todo)
        tasks = execution.goals_module().task_bodies(todo)
        self.assertEqual(list(tasks).count('A-LIVE'), 1)
        # A live check is never dispatched to an offline worker.
        self.assertNotIn('A-LIVE', [t['id'] for t in dispatch.contracts(self.repo)])

    def test_a_retried_close_adds_no_second_live_followup(self):
        self.worker()
        self.report(pending_live=['Production smoke test'])
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        from unittest.mock import patch
        real = module.goals_command
        def archive_fails(repo, *argv):
            if argv[0] == 'archive':
                raise ValueError('injected archive failure')
            return real(repo, *argv)
        with patch.object(module, 'goals_command', archive_fails), self.assertRaises(ValueError):
            module.close(self.repo, self.owner, 'A')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        self.assertEqual((self.repo / 'TODO.md').read_text().count('- [ ] A-LIVE'), 1)

    def test_retry_refill_enforces_running_retry_timeout(self):
        import time
        from types import SimpleNamespace
        self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='fixture failure')
        args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, profile='', parallel=2,
            max_workers=None, worker_command=json.dumps([sys.executable, '-c', 'import time; time.sleep(60)']),
            worker_host='auto', worker_profile=None, worker_timeout=.1,
            min_free_mem_mb=0, tasks=None, plan=None)
        module = self.module()
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):
            self.assertEqual(module.dispatch_with_retries(args)['outcome'], 'RETRIED')
            worker = state.slots(self.common)[0]['worker']
            self.addCleanup(dispatch.stop, worker)
            time.sleep(.2)
            module.dispatch_with_retries(args)
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'held')
        self.assertIn('timeout', slot['reason'])
        self.assertFalse(state.worker_live(slot))

    def test_a_close_works_when_history_already_holds_an_older_entry_for_the_id(self):
        """sierra TASK-029: an older, unchecked TASK-029 sat in the archive; every close read two."""
        (self.repo / 'TODO.archive.md').write_text('# Completed\n\n- [ ] A — An older A\n  Scope: earlier\n'
                                                   '  Status: superseded\n')
        self.git('add', '-A')
        self.git('commit', '-qm', 'history with an older A')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')  # a retried close too
        self.assertIn('An older A', (self.repo / 'TODO.archive.md').read_text())  # history kept

    def test_archived_task_cannot_close_changed_acceptance(self):
        root, _ = self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('- [ ] A', '- [x] A').replace(
            'Acceptance: offline fixture', 'Acceptance: changed unvalidated requirement', 1).replace(
            'Status: open', 'Status: done', 1))
        module.goals_command(self.repo, 'archive', '--verified-tasks', 'A')
        before = (self.repo / 'TODO.archive.md').read_bytes()
        with self.assertRaisesRegex(ValueError, 'contract|provenance'):
            module.close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.archive.md').read_bytes(), before)
        self.assertTrue(root.exists())
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrated')

    def test_checked_task_cannot_archive_changed_acceptance(self):
        root, _ = self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('- [ ] A', '- [x] A').replace(
            'Acceptance: offline fixture', 'Acceptance: changed unvalidated requirement', 1))
        before = todo.read_bytes()
        with self.assertRaisesRegex(ValueError, 'contract changed'):
            module.close(self.repo, self.owner, 'A')
        self.assertEqual(todo.read_bytes(), before)
        self.assertFalse((self.repo / 'TODO.archive.md').exists())
        self.assertTrue(root.exists())

    def test_failed_validation_refuses_close_without_ledger_writes(self):
        root, commit = self.worker()
        before = (self.repo / 'TODO.md').read_bytes()
        result = self.module().integrate(self.repo, self.owner, 'A', ['false'], 10)
        self.assertEqual(result['outcome'], 'HELD')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        with self.assertRaises(ValueError):
            self.module().close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        self.assertTrue(root.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)

    def test_conflict_adoptions_follow_canonical_revisions_up_to_three_per_attempt(self):
        import parallel_status
        root, _ = self.worker()
        module = self.module()
        for count in range(1, 5):
            (self.repo / 'A.txt').write_text(f'canonical {count}\n')
            self.git('commit', '-qam', f'canonical {count}')
            base = self.git('rev-parse', 'HEAD')
            held = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
            self.assertEqual(held['cause'], 'conflict', held)
            before = {p: p.read_bytes() for p in [state.slot_path(self.common, 'A'),
                                                 self.common / 'journal.jsonl']}
            row = parallel_status.snapshot(self.repo)['tasks'][0]
            self.assertEqual({p: p.read_bytes() for p in before}, before)
            self.assertEqual(row['merge_adoption']['allowed'], count <= 3)
            if count == 4:
                self.assertIn('A.txt', row['reason'])
                self.assertIn('3 of 3', row['reason'])
                self.assertTrue(state.exhausted(state.slots(self.common)[0]))
                with self.assertRaisesRegex(ValueError, '3 of 3'):
                    module.merged(self.repo, self.owner, 'A')
                break
            merge = subprocess.run(['git', '-C', str(root), 'merge', '--no-edit', base], capture_output=True)
            self.assertEqual(merge.returncode, 1)
            self.git('checkout', '--ours', 'A.txt', cwd=root)
            self.git('add', 'A.txt', cwd=root)
            self.git('commit', '-qm', 'resolve', cwd=root)
            adopted = module.merged(self.repo, self.owner, 'A')
            self.assertEqual(adopted['merged_count'], count)
            slot = state.slots(self.common)[0]
            self.assertEqual((slot['state'], slot['baseline'], slot['merged_base']), ('reported', base, base))
            if count == 1:  # old boolean records stored the adopted revision in baseline
                slot['merged_base'] = True
                slot.pop('merged_count')
                slot = state.write_slot(self.common, slot, slot)
            module.hold(self.common, slot, 'merge conflict', cause='conflict', conflict_files=['A.txt'])
            row = parallel_status.snapshot(self.repo)['tasks'][0]
            self.assertFalse(row['merge_adoption']['allowed'])
            self.assertIn(f'{count} of 3', row['reason'])
            with self.assertRaises(ValueError):
                module.merged(self.repo, self.owner, 'A')
            slot = state.slots(self.common)[0]
            state.write_slot(self.common, dict(slot, state='reported'), slot)

    def test_merge_conflict_preserves_canonical_dirty_files_and_other_slot(self):
        root, commit = self.worker()
        other, other_commit = self.worker('B')
        (self.repo / 'A.txt').write_text('canonical conflict\n')
        self.git('add', 'A.txt')
        self.git('commit', '-qm', 'concurrent canonical change')
        head = self.git('rev-parse', 'HEAD')
        (self.repo / 'B.txt').write_text('dirty user text\n')
        status = self.git('status', '--porcelain')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('conflict', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(self.git('status', '--porcelain'), status)
        self.assertEqual((self.repo / 'B.txt').read_text(), 'dirty user text\n')
        self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)
        self.assertEqual(self.git('rev-parse', 'autowork/B'), other_commit)
        self.assertTrue(root.exists() and other.exists())
        self.assertEqual(state.slots(self.common)[1]['state'], 'reported')

    def test_canonical_rename_cannot_redirect_worker_delta_outside_scope(self):
        """TOOLSET-161-17: outside Touches is no longer out of scope; a coordinator file still is."""
        self.worker()
        self.git('mv', 'A.txt', 'CHANGELOG.md')
        self.git('commit', '-qm', 'canonical rename')
        before = self.git('rev-parse', 'HEAD')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('CHANGELOG.md', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual((self.repo / 'CHANGELOG.md').read_text(), 'base\n')

    def test_head_move_retry_rechecks_actual_merge_scope(self):
        self.worker()
        marker = Path(self.temp.name) / 'renamed'
        script = ('import subprocess; from pathlib import Path; '
                  f'p=Path({str(marker)!r}); r={str(self.repo)!r}; '
                  'subprocess.run(["git","-C",r,"mv","A.txt","CHANGELOG.md"],check=True) if not p.exists() else None; '
                  'subprocess.run(["git","-C",r,"commit","-qm","rename"],check=True) if not p.exists() else None; '
                  'p.write_text("yes")')
        result = self.module().integrate(self.repo, self.owner, 'A', [sys.executable, '-c', script], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('CHANGELOG.md', result['reason'])  # a coordinator file (TOOLSET-161-17)
        self.assertEqual((self.repo / 'CHANGELOG.md').read_text(), 'base\n')

    def test_a_change_outside_touches_integrates_when_it_merges_and_passes(self):
        """TOOLSET-161-17: Touches schedule work and never hold it."""
        self.worker(files={'A.txt': 'worker\n', 'outside.txt': 'needed\n'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual((self.repo / 'outside.txt').read_text(), 'needed\n')
        self.assertEqual(state.slots(self.common)[0]['attempt'], 1)

    def test_two_candidates_editing_the_same_file_integrate_in_priority_order(self):
        """TOOLSET-161-17: the merge settles a shared file; no new implementation run."""
        module = self.module()
        (self.repo / 'shared.txt').write_text('one\ntwo\nthree\nfour\nfive\n')
        self.git('add', 'shared.txt')
        self.git('commit', '-qm', 'shared file')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker('A', {'shared.txt': 'ONE\ntwo\nthree\nfour\nfive\n'})
        self.worker('B', {'shared.txt': 'one\ntwo\nthree\nfour\nFIVE\n'})
        with self.assertRaisesRegex(ValueError, 'highest-priority'):
            module.integrate(self.repo, self.owner, 'B', ['true'], 10)
        for task in ('A', 'B'):
            self.assertEqual(module.integrate(self.repo, self.owner, task, ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual((self.repo / 'shared.txt').read_text(), 'ONE\ntwo\nthree\nfour\nFIVE\n')
        self.assertEqual([s['attempt'] for s in state.slots(self.common)], [1, 1])
        self.assertFalse(self.git('branch', '--list', '*-r2'))

    def retry_args(self):
        from types import SimpleNamespace
        return SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner, profile='', parallel=2,
            max_workers=None, worker_command=json.dumps([sys.executable, '-c', 'pass']), worker_host='auto',
            worker_profile=None, worker_timeout=10, min_free_mem_mb=0, tasks=None, plan=None)

    def test_three_quick_identical_input_holds_require_a_named_resolution(self):
        import parallel_status
        module = self.module()
        todo = self.repo / 'TODO.md'
        for task, third_reason, seconds, cause, resumed, stopped in (
                ('A', 'missing receipt', 60, 'blocker', False, True),
                ('B', 'missing credentials', 60, 'blocker', False, False),
                ('C', 'missing receipt', 601, 'blocker', False, False),
                ('D', 'missing receipt', 60, 'validation', False, False),
                ('E', 'missing receipt', 700, 'blocker', True, False),
                ('F', 'missing receipt', 30, 'blocker', True, True)):
            with self.subTest(task=task):
                if task not in 'AB':
                    todo.write_text(todo.read_text() + f'\n- [ ] {task} — Task {task}\n  Scope: fixture\n'
                                    f'  Touches: {task}.txt\n  Acceptance: fixture\n  Checks: true\n'
                                    '  Dependencies: None.\n  Status: open\n')
                for attempt in range(1, 4):
                    self.worker(task)
                    slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
                    contract = execution.goals_module().task_bodies(todo.read_text())[task][0][0].strip()
                    (dispatch.data_dir(self.common, slot) / 'contract.txt').write_text(contract + '\n')
                    slot = state.write_slot(self.common, dict(slot, state='running' if resumed else 'reported',
                                                             started_at=time.time() - seconds), slot)
                    if resumed:
                        state.transition(self.repo, self.owner, task, 'interrupted', paused=True)
                        slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
                        slot = state.change(self.common, slot, 'dispatched', {})
                        start = time.time() - 30
                        state.write_slot(self.common, dict(slot, started_at=start, runtime_started_at=start), slot)
                    reason = (third_reason if attempt == 3 else 'missing receipt')
                    reason += f' /var/tmp/run-{attempt}/receipt.json for TASK-{attempt}'
                    state.transition(self.repo, self.owner, task, 'held', reason=reason, cause=cause)
                    todo.write_text(todo.read_text().replace(contract, contract + f'\n  Evidence: edit {attempt}', 1))
                    result = module.retry_held(self.retry_args())
                    if attempt < 3 or not stopped:
                        self.assertEqual(result['outcome'], 'REQUEUED', result)
                if stopped:
                    self.assertEqual(result['outcome'], 'IDLE', result)
                    row = next(r for r in parallel_status.snapshot(self.repo)['tasks'] if r['task'] == task)
                    hold = row['quick_hold']
                    self.assertEqual(len(hold['attempts']), 3)
                    self.assertTrue(all(60 <= a['seconds'] < 61 for a in hold['attempts']))
                    self.assertEqual(len({a['reason'] for a in hold['attempts']}), 3)
                    self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'IDLE')
                    with self.assertRaisesRegex(ValueError, 'Blocker resolution'):
                        module.set_aside(self.repo, self.owner, task)
                    with self.assertRaisesRegex(ValueError, 'answer is only'):
                        module.answer(self.repo, self.owner, task, 'try again')
                    current = execution.goals_module().task_bodies(todo.read_text())[task][0][0].strip()
                    resolved = current.replace('Dependencies: None.', 'Dependencies: INPUT-1')
                    resolved += f'\n  Blocker resolution: {hold["fingerprint"]}; INPUT-1 produces the receipt'
                    todo.write_text(todo.read_text().replace(current, resolved, 1))
                    self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'REQUEUED')
                    # If that answer failed, formatting it differently is not a new answer.
                    self.worker(task)
                    slot = state.slots(self.common)[0]
                    (dispatch.data_dir(self.common, slot) / 'contract.txt').write_text(resolved + '\n')
                    state.transition(self.repo, self.owner, task, 'held', reason=reason, cause=cause)
                    todo.write_text(todo.read_text().replace('  Blocker resolution:', '   Blocker resolution:'))
                    self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'IDLE')
                    state.slot_path(self.common, task).unlink()  # next fixture case starts without a live slot

    def test_a_scope_hold_records_its_cause_and_outside_files(self):
        # TOOLSET-161-17: only an undeclared protected file or a coordinator file is out of scope.
        self.worker(files={'A.txt': 'worker\n', 'go.mod': 'module x\n'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual((result['cause'], result['outside']), ('scope', ['go.mod']))
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['cause'], slot['outside']), ('scope', ['go.mod']))

    def test_other_contract_answers_requeue_even_when_touches_cover_the_commit(self):
        module = self.module()
        for index, field in enumerate(('Scope', 'Acceptance', 'Checks', 'Dependencies')):
            with self.subTest(field=field):
                task = 'ABCD'[index]
                todo = self.repo / 'TODO.md'
                if task in 'CD':
                    todo.write_text(todo.read_text() + f'\n- [ ] {task} — Task {task}\n  Scope: fixture\n'
                                    f'  Touches: {task}.txt\n  Acceptance: fixture\n  Checks: true\n'
                                    '  Dependencies: None.\n  Status: open\n')
                self.worker(task, files={'go.mod': 'x\n'})  # an undeclared protected file (TOOLSET-161-17)
                slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
                contract = execution.goals_module().task_bodies(todo.read_text())[task][0][0].strip()
                (dispatch.data_dir(self.common, slot) / 'contract.txt').write_text(contract + '\n')
                self.assertEqual(module.integrate(self.repo, self.owner, task, ['true'], 10)['cause'], 'scope')
                slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
                state.write_slot(self.common, dict(slot, rescoped=index % 2 == 1), slot)
                revised = contract.replace(f'Touches: {task}.txt', f'Touches: {task}.txt, go.mod')
                revised = revised.replace(field + ': ', field + ': revised ', 1)
                todo.write_text(todo.read_text().replace(contract, revised, 1))
                self.git('commit', '-qam', 'answer ' + task)
                result = module.retry_held(self.retry_args())
                try:
                    self.assertEqual((result['outcome'], result.get('task')), ('REQUEUED', task))
                    self.assertTrue(self.git('branch', '--list', 'autowork/' + task + '-set-aside-1'))
                    events = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
                    changes = [e['changed_fields'] for e in events if e['event'] == 'task_entry_changed']
                    self.assertEqual(changes[-1], sorted([field, 'Touches']))
                finally:
                    state.slot_path(self.common, task).unlink(missing_ok=True)

    def test_a_validation_hold_is_reverified_once_per_reviewer_version(self):
        """A changed verdict earns another look; the same failure, apart from SHAs, does not."""
        root, _ = self.worker()
        module = self.module()
        def fail(line, reviewer):
            argv = ['bash', '-c', f'echo "AUTOWORK_HOLD_REASON: {line}"; exit 1']
            self.assertEqual(module.integrate(self.repo, self.owner, 'A', argv, 10, reviewer)['outcome'], 'HELD')
        fail('fail — missing device at 123abcd', 'r0')
        with self.assertRaisesRegex(ValueError, 'once per validator version'):
            module.reverify(self.repo, self.owner, 'A', 'r0')
        self.assertEqual(module.reverify(self.repo, self.owner, 'A', 'r1')['outcome'], 'REVERIFY')
        slot = state.slots(self.common)[0]
        self.assertEqual((slot['state'], slot['attempt'], slot['reverified']), ('reported', 1, 'r1'))
        long_failure = 'fail — required offline checks are red: ' + 'test_name ' * 65
        fail(long_failure + 'first failure at 123abcd', 'r1')
        with self.assertRaisesRegex(ValueError, 'once per validator version'):
            module.reverify(self.repo, self.owner, 'A', 'r1')
        self.assertEqual(module.reverify(self.repo, self.owner, 'A', 'r2')['outcome'], 'REVERIFY')
        fail(long_failure + 'different failure at 123abcd', 'r2')
        self.assertEqual(module.reverify(self.repo, self.owner, 'A', 'r3')['outcome'], 'REVERIFY')
        fail(long_failure + 'different failure at fedcba9876543210', 'r3')
        with self.assertRaisesRegex(ValueError, 'same verdict'):
            module.reverify(self.repo, self.owner, 'A', 'r4')
        self.assertEqual(state.slots(self.common)[0]['state'], 'held')
        # A new worker commit is not bound by the old commit's repeated verdict.
        (root / 'A.txt').write_text('fixed\n')
        self.git('commit', '-qam', 'fix', cwd=root)
        commit = self.git('rev-parse', 'HEAD', cwd=root)
        slot = state.slots(self.common)[0]
        state.write_slot(self.common, dict(slot, commit=commit), slot)
        report_path = dispatch.data_dir(self.common, slot) / 'report.json'
        execution.save(report_path, dict(execution.read(report_path), commit=commit))
        self.assertEqual(module.reverify(self.repo, self.owner, 'A', 'r4')['outcome'], 'REVERIFY')
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10, 'r4')['outcome'], 'INTEGRATED')

    def test_only_validation_holds_are_reverified(self):
        self.worker(files={'CHANGELOG.md': 'coordinator owned'})  # a scope hold (TOOLSET-161-17)
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['cause'], 'scope')
        with self.assertRaisesRegex(ValueError, 'only for a commit held by validation'):
            module.reverify(self.repo, self.owner, 'A', 'r1')
        legacy = dict(state.slots(self.common)[0], reason='integration validation failed or changed the integration tree')
        legacy.pop('cause')
        self.assertTrue(module.reverifiable(legacy, 'r1'))  # holds from before causes existed

    def test_coordinator_file_is_held_even_if_declared(self):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: A.txt, CHANGELOG.md'))
        self.worker(files={'CHANGELOG.md': 'not worker owned'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('CHANGELOG.md', result['reason'])

    def test_a_task_source_link_labelled_history_does_not_select_the_archive(self):
        """sierra: bold task IDs stayed unchecked on close, and the archive fallback then
        took '[Patrol history/events surface](patrol.go)' for the archive."""
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('- [ ] A — Task A', '- [ ] **A — Task A**').replace(
            '  Scope: B.txt\n', '  Scope: B.txt\n  Sources: [Patrol history/events surface](src/patrol.go)\n'))
        self.git('commit', '-qam', 'source link')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        result = module.close(self.repo, self.owner, 'A')
        self.assertEqual(result['outcome'], 'CLOSED', result)
        self.assertIn('- [x] **A — Task A**', (self.repo / 'TODO.archive.md').read_text())
        self.assertEqual(module.archive_path(self.repo), self.repo / 'TODO.archive.md')

    def test_a_half_closed_task_still_closes(self):
        """sierra: an earlier close wrote Status: done but left the box unchecked."""
        self.worker()
        module = self.module()
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'
        text = todo.read_text()
        a = text.index('- [ ] A')
        todo.write_text(text[:a] + text[a:].replace('Status: open', 'Status: done', 1))
        result = module.close(self.repo, self.owner, 'A')
        self.assertEqual(result['outcome'], 'CLOSED', result)
        self.assertIn('- [x] A — Task A', (self.repo / 'TODO.archive.md').read_text())

    def test_closed_slot_releases_ownership_for_followup_task(self):
        self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        module.close(self.repo, self.owner, 'A')
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: B.txt', 'Touches: A.txt'))
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker('B', {'A.txt': 'followup\n'})
        result = module.integrate(self.repo, self.owner, 'B', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'followup\n')

    def test_report_mismatch_and_non_descendant_are_held(self):
        self.worker()
        slot = state.slots(self.common)[0]
        path = dispatch.data_dir(self.common, slot) / 'report.json'
        report = execution.read(path)
        report['commit'] = self.baseline
        execution.save(path, report)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('report.json', result['reason'])

    def test_lineage_mismatch_is_held(self):
        root, commit = self.worker()
        self.git('checkout', '--orphan', 'unrelated', cwd=root)
        self.git('commit', '-qm', 'unrelated root', cwd=root)
        unrelated = self.git('rev-parse', 'HEAD', cwd=root)
        self.git('checkout', 'autowork/A', cwd=root)
        slot = state.slots(self.common)[0]
        slot['baseline'] = unrelated
        execution.save(state.slot_path(self.common, 'A'), slot)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('lineage', result['reason'])

    def test_reverified_candidates_follow_fresh_candidates_then_keep_task_priority(self):
        module = self.module()
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text() + ''.join(
            f'\n- [ ] {t} — Task {t}\n  Scope: {t}.txt\n  Touches: {t}.txt\n'
            '  Acceptance: fixture\n  Checks: true\n  Dependencies: None.\n  Status: open\n' for t in ('C', 'D')))
        self.git('commit', '-qam', 'add C and D')
        self.baseline = self.git('rev-parse', 'HEAD')
        for task in ('A', 'B'):
            self.worker(task)
            self.assertEqual(module.integrate(self.repo, self.owner, task, ['false'], 10, 'r0')['outcome'], 'HELD')
        for task in ('A', 'B'):
            module.reverify(self.repo, self.owner, task, 'r1')
        self.worker('C')
        with self.assertRaisesRegex(ValueError, 'highest-priority reported task first: C'):
            module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(module.integrate(self.repo, self.owner, 'C', ['true'], 10)['outcome'], 'INTEGRATED')
        with self.assertRaisesRegex(ValueError, 'highest-priority reported task first: A'):
            module.integrate(self.repo, self.owner, 'B', ['true'], 10)
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['false'], 10, 'r1')['outcome'], 'HELD')
        # A newly implemented retry is fresh, not a re-review of the old commit.
        slot = module.slot_for(self.common, 'A')
        retry = Path(slot['worktree'] + '-r2')
        self.git('worktree', 'add', '-q', '-b', 'autowork/A-r2', str(retry), self.baseline)
        state.change(self.common, slot, 'dispatched', {'worktree': str(retry), 'branch': 'autowork/A-r2',
                                                     'baseline': self.baseline})
        (retry / 'A.txt').write_text('fixed\n')
        self.git('commit', '-qam', 'retry A', cwd=retry)
        commit = self.git('rev-parse', 'HEAD', cwd=retry)
        slot = state.transition(self.repo, self.owner, 'A', 'reported', commit=commit)
        execution.save(dispatch.data_dir(self.common, slot) / 'report.json', {
            'task': 'A', 'commit': commit, 'changed_files': ['A.txt'], 'checks': [], 'blockers': [], 'changelog': 'fix'})
        self.worker('D')
        for task in ('A', 'D', 'B'):
            self.assertEqual(module.integrate(self.repo, self.owner, task, ['true'], 10)['outcome'], 'INTEGRATED')

    def test_priority_order_is_enforced(self):
        self.worker('B')
        self.worker('A')
        with self.assertRaisesRegex(ValueError, 'highest-priority'):
            self.module().integrate(self.repo, self.owner, 'B', ['true'], 10)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def moving_validation(self, twice=False):
        marker = Path(self.temp.name) / 'moves'
        script = ('import subprocess; from pathlib import Path; '
                  f'p=Path({str(marker)!r}); r=Path({str(self.repo)!r}); '
                  'n=int(p.read_text()) if p.exists() else 0; '
                  f'move=n<({2 if twice else 1}); '
                  'p.write_text(str(n+1)); '
                  '(r/"B.txt").write_text(str(n)) if move else None; '
                  'subprocess.run(["git","-C",str(r),"add","B.txt"],check=True) if move else None; '
                  'subprocess.run(["git","-C",str(r),"commit","-qm","moved HEAD"],check=True) if move else None')
        return [sys.executable, '-c', script], marker

    def test_worker_commit_landed_during_validation_is_not_invalid_integration(self):
        _, commit = self.worker()
        script = ('import subprocess; subprocess.run(["git","-C",'
                  f'{str(self.repo)!r},"merge","--ff-only",{commit!r}],check=True)')
        result = self.module().integrate(self.repo, self.owner, 'A', [sys.executable, '-c', script], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('already', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), commit)
        self.assertEqual(state.slots(self.common)[0]['state'], 'held')
        with self.assertRaises(ValueError):
            self.module().close(self.repo, self.owner, 'A')

    def test_moved_head_is_remerged_and_revalidated_once(self):
        self.worker()
        argv, marker = self.moving_validation()
        argv[2] = ('import os,time; fd=int(os.environ["AUTOWORK_CHECK_WAIT_FD"]); '
                   'os.write(fd,f"{time.monotonic()} 1\\n".encode()); time.sleep(.25); '
                   'os.write(fd,f"{time.monotonic()} 0\\n".encode()); ' + argv[2])
        result = self.module().integrate(self.repo, self.owner, 'A', argv, 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertGreaterEqual(result['check_slot_wait_seconds'], .5)  # both attempts, not just the final one
        self.assertEqual(marker.read_text(), '2')
        self.assertEqual(self.git('show', 'HEAD^1:B.txt'), '0')
        self.assertEqual((self.repo / 'A.txt').read_text(), 'worker\n')
        self.assertEqual(self.git('rev-list', '--count', self.baseline + '..HEAD'), '3')

    def test_second_head_move_holds_without_landing_candidate(self):
        self.worker()
        argv, marker = self.moving_validation(twice=True)
        result = self.module().integrate(self.repo, self.owner, 'A', argv, 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('moved twice', result['reason'])
        self.assertEqual(marker.read_text(), '2')
        self.assertEqual((self.repo / 'A.txt').read_text(), 'base\n')

    def test_dirty_canonical_overlap_refuses_ff_without_discarding_user_bytes(self):
        self.worker()
        (self.repo / 'A.txt').write_text('user edit\n')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual((self.repo / 'A.txt').read_text(), 'user edit\n')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_legacy_candidate_revalidates_after_location_upgrade(self):
        self.worker()
        module = self.module()
        from unittest.mock import patch
        legacy = self.repo.parent / 'legacy-integration'
        with patch.object(module, 'worktree_path', return_value=legacy), \
                patch.object(execution, 'bounded_command', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        slot = state.slots(self.common)[0]
        slot['integration'].pop('worktree', None)  # pre-upgrade intent format
        execution.save(state.slot_path(self.common, 'A'), slot)
        state.reconcile(self.repo, self.owner)
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertTrue(legacy.is_dir())  # never discard prior evidence

    def test_legacy_landed_candidate_recovers_after_location_upgrade(self):
        module = self.module()
        from unittest.mock import patch
        legacy = self.repo.parent / 'legacy-integration'
        with patch.object(module, 'worktree_path', return_value=legacy):
            self.interrupted_after_landing()
        slot = state.slots(self.common)[0]
        slot['integration'].pop('worktree', None)
        execution.save(state.slot_path(self.common, 'A'), slot)
        with patch.object(execution, 'bounded_command', side_effect=AssertionError('already validated')):
            result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def test_interrupted_validation_can_revalidate_abandoned_candidate(self):
        self.worker()
        module = self.module()
        from unittest.mock import patch
        with patch.object(execution, 'bounded_command', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        state.reconcile(self.repo, self.owner)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(state.slots(self.common)[0]['attempt'], 1)
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')

    def interrupted_after_landing(self):
        self.worker()
        module = self.module()
        original = module.git
        from unittest.mock import patch
        def interrupt(repo, *argv):
            value = original(repo, *argv)
            if Path(repo) == self.repo and argv[:2] == ('merge', '--ff-only'):
                raise KeyboardInterrupt
            return value
        with patch.object(module, 'git', side_effect=interrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrating')
        return module

    def test_interrupted_after_ff_recovers_only_exact_validated_landed_candidate(self):
        module = self.interrupted_after_landing()
        head = self.git('rev-parse', 'HEAD')
        from unittest.mock import patch
        with patch.object(execution, 'bounded_command', side_effect=AssertionError('must not rerun landed validation')):
            result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(result['integration']['commit'], head)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')

    def test_interrupted_landed_candidate_without_receipt_is_held(self):
        module = self.interrupted_after_landing()
        slot = state.slots(self.common)[0]
        Path(slot['integration']['check_receipt']).unlink()
        head = self.git('rev-parse', 'HEAD')
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)
        self.assertFalse((self.repo / 'TODO.archive.md').exists())

    def interrupted_while_main_moved(self):
        self.worker()
        module = self.module()
        from unittest.mock import patch
        with patch.object(execution, 'bounded_command', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        (self.repo / 'B.txt').write_text('independent canonical change')
        self.git('add', 'B.txt')
        self.git('commit', '-qm', 'the session landed beside the review')
        return module, self.git('rev-parse', 'HEAD')

    def test_interrupted_candidate_that_never_landed_merges_again_on_the_moved_head(self):
        module, head = self.interrupted_while_main_moved()
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(self.git('rev-parse', 'HEAD^1'), head)
        self.assertEqual(state.slots(self.common)[0]['attempt'], 1)

    def test_a_held_review_whose_merge_never_landed_is_offered_again_once(self):
        module, head = self.interrupted_while_main_moved()
        slot = state.slots(self.common)[0]
        held = module.hold(self.common, slot, module.STALE_VALIDATION)
        self.assertEqual(held['outcome'], 'HELD')
        self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'REOFFERED')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['state'], 'reported')
        self.assertIn('stale_validation', state.reoffered(slot))
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(self.git('rev-parse', 'HEAD^1'), head)

    def test_real_validation_interrupt_stops_child_before_recovery(self):
        self.worker()
        cli = Path(__file__).with_name('owner_cycle.py')
        script = 'import os, signal, time; os.kill(os.getppid(), signal.SIGINT); time.sleep(60)'
        proc = subprocess.run([sys.executable, str(cli), str(self.repo), '--owner-pid', str(self.owner),
                               '--integrate', 'A', '--timeout', '10', '--run', sys.executable, '-c', script],
                              capture_output=True, text=True, timeout=15)
        self.assertNotEqual(proc.returncode, 0)
        self.assertIn('KeyboardInterrupt', proc.stderr)
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrating')
        self.assertFalse(execution.external_workers(self.repo))
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)

    def test_validation_runs_without_writer_lock_and_has_timeout(self):
        self.worker()
        script = ('import fcntl; from pathlib import Path; '
                  f'p=Path({str(self.common)!r}); '
                  'f=open(p/"writer.lock","a"); fcntl.flock(f,fcntl.LOCK_EX|fcntl.LOCK_NB); '
                  'assert not (p/"active.json").exists(); import time; time.sleep(5)')
        result = self.module().integrate(self.repo, self.owner, 'A', [sys.executable, '-c', script], .15)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(state.slots(self.common)[0]['checks']['outcome'], 'TIMED_OUT')
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_a_build_daemon_left_behind_by_a_passing_validation_does_not_fail_it(self):
        """A Flutter task's checks passed, but the Gradle and Kotlin daemons they started held it."""
        self.worker()
        daemon = 'import subprocess, sys; subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])'
        module = self.module()
        killpg = os.killpg

        def settled_kill(group, sig):
            # Force the legitimate scheduling case where SIGKILL has completed
            # before descendant accounting runs, without reaping the zombie.
            children = [pid for pid in execution.child_pids(os.getpid()) if os.getpgid(pid) == group]
            killpg(group, sig)
            for pid in children:
                os.waitid(os.P_PID, pid, os.WEXITED | os.WNOWAIT)

        with patch.object(execution.os, 'killpg', side_effect=settled_kill):
            result = module.integrate(self.repo, self.owner, 'A', [sys.executable, '-c', daemon], 20)
        self.retain_evidence()
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(state.slots(self.common)[0]['checks']['outcome'], 'CHILDREN_TERMINATED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')

    def test_a_failing_validation_with_a_daemon_still_holds_and_old_daemon_holds_are_offered_again(self):
        self.worker()
        module = self.module()
        failing = 'import subprocess, sys; subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"]); sys.exit(1)'
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', [sys.executable, '-c', failing], 20)['outcome'],
                         'HELD')
        slot = state.slots(self.common)[0]
        self.retain_evidence()
        self.assertEqual(slot['checks']['outcome'], 'CHILDREN_TERMINATED')
        self.assertFalse(module.passed(slot['checks']))  # exit 1: a real failure, never offered again
        # As an earlier release held a passing run that left a daemon: offered again, once.
        checks = dict(slot['checks'], command_receipt=dict(slot['checks']['command_receipt'], exit_code=0))
        execution.save(state.slot_path(self.common, 'A'), dict(slot, checks=checks))
        self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'REOFFERED')

    def test_each_hold_cause_is_offered_again_once(self):
        """A commit offered again for a misread report was then held by the daemon rule, and its
        one-time flag kept it from the second, unrelated, offer."""
        self.worker()
        module = self.module()
        slot = state.slots(self.common)[0]
        checks = {'outcome': 'CHILDREN_TERMINATED', 'command_receipt': {'exit_code': 0, 'inputs_match': True}}
        execution.save(state.slot_path(self.common, 'A'),
                       dict(slot, state='held', cause='validation', checks=checks, reoffered=True))
        self.assertEqual(module.retry_held(self.retry_args())['outcome'], 'REOFFERED')
        slot = state.slots(self.common)[0]
        self.assertEqual(slot['reoffered'], ['overlap', 'report', 'validation'])
        execution.save(state.slot_path(self.common, 'A'), dict(slot, state='held', cause='validation', checks=checks))
        self.assertNotEqual(module.retry_held(self.retry_args()).get('outcome'), 'REOFFERED')

    def test_cli_integrate_and_close(self):
        self.worker()
        cli = Path(__file__).with_name('owner_cycle.py')
        p = subprocess.run([sys.executable, str(cli), str(self.repo), '--owner-pid', str(self.owner),
                            '--integrate', 'A', '--timeout', '10', '--run', 'true'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)['outcome'], 'INTEGRATED')
        p = subprocess.run([sys.executable, str(cli), str(self.repo), '--owner-pid', str(self.owner),
                            '--parallel-close', 'A'], capture_output=True, text=True)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        self.assertEqual(json.loads(p.stdout)['outcome'], 'CLOSED')

    def test_sequential_command_output_is_byte_identical_to_original(self):
        from types import SimpleNamespace
        from unittest.mock import patch
        args = SimpleNamespace(run=['true'], timeout=10, budget_seconds=None, source_path=[], plan=None, owner_pid=None)
        fixed = SimpleNamespace(hex='fixed-offline-receipt')
        with patch.object(execution.uuid, 'uuid4', return_value=fixed), patch.object(execution.time, 'monotonic', return_value=1):
            with execution.lock(self.common / 'writer.lock') as fd:
                result = execution.command(args, self.repo, self.common, self.common, {'id': 'A'}, {}, fd)
        # Golden field order, values and JSON bytes captured against pre-factor
        # command() in the initial real-process comparison (not self-comparison
        # against whatever happens to be the checkout's current HEAD).
        import shutil
        resolved = shutil.which('true')
        inputs = {'TODO.md': execution.digest(self.repo / 'TODO.md')}
        expected = {'outcome': 'EXECUTED', 'command_receipt': {
            'task_id': 'A', 'workspace': str(self.repo), 'exit_code': 0,
            'argv': ['true'], 'reusable_acceptance': False, 'terminated_descendants': [],
            'elapsed_seconds': 0, 'timeout_seconds': 10,
            'inputs_before': inputs, 'inputs_after': inputs, 'inputs_match': True,
            'executable': resolved, 'executable_sha256': execution.digest(Path(resolved).resolve()),
            'log': str(self.common / (fixed.hex + '.log')),
            'receipt': str(self.common / (fixed.hex + '.json'))}}
        self.assertEqual(json.dumps(result, indent=2), json.dumps(expected, indent=2))


    def ledger(self):
        data = {'version': 1, 'goals': [{'id': 'G', 'title': 'offline fixture', 'source': 'TODO.md',
            'status': 'partial', 'tasks': ['A', 'B'], 'priority': 1, 'depends_on': []}],
            'tasks': [{'id': t, 'title': 'Task ' + t, 'goal': 'G', 'status': 'open',
                       'section': 'Next', 'depends_on': []} for t in ('A', 'B')]}
        (self.repo / 'goals.json').write_text(json.dumps(data))
        self.git('add', 'goals.json')
        self.git('commit', '-qm', 'ledger fixture')
        self.baseline = self.git('rev-parse', 'HEAD')

    def test_failed_validation_keeps_existing_ledger_byte_identical(self):
        self.ledger()
        root, commit = self.worker()
        before = {name: (self.repo / name).read_bytes() for name in ('TODO.md', 'goals.json')}
        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['false'], 10)['outcome'], 'HELD')
        with self.assertRaises(ValueError):
            self.module().close(self.repo, self.owner, 'A')
        self.assertEqual({name: (self.repo / name).read_bytes() for name in before}, before)
        self.assertTrue(root.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)

    def test_existing_ledger_closes_with_real_goals_commands(self):
        self.ledger()
        self.worker()
        before = (self.repo / 'goals.json').read_bytes()
        with self.assertRaises(ValueError):
            self.module().close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'goals.json').read_bytes(), before)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(self.module().close(self.repo, self.owner, 'A')['outcome'], 'CLOSED')
        data = json.loads((self.repo / 'goals.json').read_text())
        self.assertEqual({t['id']: t['status'] for t in data['tasks']}, {'A': 'done', 'B': 'open'})

    def record_order(self):
        module = self.module()
        dry = json.loads(module.goals_command(self.repo, 'bootstrap-order', '--dry-run'))
        module.goals_command(self.repo, 'bootstrap-order', '--expected-revision', dry['revision'])
        self.git('commit', '-qam', 'record order')

    def test_a_live_followup_in_a_ledger_repository_keeps_priority_in_sync(self):
        """flutter: closing TASK-013 added TASK-008 unrecorded; drift then stopped all dispatch."""
        self.ledger()
        module = self.module()
        self.record_order()  # a recorded human order, as in fleet repositories
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker()
        self.report(pending_live=['Device check'])
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        self.assertEqual(module.close(self.repo, self.owner, 'A')['live_followup'], 'A-LIVE')
        goals = execution.goals_module()
        status = goals.priority_status(goals.normalize(goals.load(self.repo)), (self.repo / 'TODO.md').read_text())
        self.assertEqual(status['state'], 'synced', status)
        self.assertEqual([t['id'] for t in dispatch.contracts(self.repo)], ['B'])  # no PRIORITY_DRIFT

    def test_a_close_never_records_someone_elses_reordering(self):
        self.ledger()
        module = self.module()
        self.record_order()
        self.baseline = self.git('rev-parse', 'HEAD')
        self.worker()
        self.report(pending_live=['Device check'])
        self.assertEqual(module.integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')
        todo = self.repo / 'TODO.md'  # a person adds C before B without recording the order
        todo.write_text(todo.read_text().replace('- [ ] B', '- [ ] C — Task C\n  Scope: C\n  Acceptance: c\n'
                                                 '  Checks: true\n  Dependencies: None.\n  Status: open\n- [ ] B'))
        module.goals_command(self.repo, 'add-task', 'C', '--goal', 'G', '--title', 'Task C')
        self.git('commit', '-qam', 'human adds C')
        module.close(self.repo, self.owner, 'A')
        goals = execution.goals_module()
        status = goals.priority_status(goals.normalize(goals.load(self.repo)), todo.read_text())
        self.assertEqual(status['state'], 'drift')  # left for the documented reorder, not blessed here

    def test_tampered_receipt_refuses_close_without_writes(self):
        self.worker()
        self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        before = (self.repo / 'TODO.md').read_bytes()
        slot = state.slots(self.common)[0]
        path = Path(slot['integration']['check_receipt'])
        receipt = execution.read(path)
        receipt['command_receipt']['exit_code'] = 1
        execution.save(path, receipt)
        with self.assertRaises(ValueError):
            self.module().close(self.repo, self.owner, 'A')
        self.assertEqual((self.repo / 'TODO.md').read_bytes(), before)
        self.assertEqual(state.slots(self.common)[0]['state'], 'integrated')

    def cleanup_failure_retry(self, failure, archive_name='TODO.archive.md'):
        archive = self.repo / archive_name
        if archive_name != 'TODO.archive.md':
            archive.parent.mkdir(parents=True, exist_ok=True)
            archive.write_text('# Completed tasks\n')
            if archive_name not in ('todo.archive.md', 'docs/TODO-archive.md'):
                todo = self.repo / 'TODO.md'
                todo.write_text('[Completed tasks](' + archive_name + ')\n\n' + todo.read_text())
                self.git('add', 'TODO.md')
                self.git('commit', '-qm', 'linked archive owner')
                self.baseline = self.git('rev-parse', 'HEAD')
        root, commit = self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        original = module.git
        from unittest.mock import patch
        def fail(repo, *argv):
            if argv[:2] == failure:
                raise ValueError('injected cleanup failure')
            return original(repo, *argv)
        with patch.object(module, 'git', side_effect=fail):
            with self.assertRaisesRegex(ValueError, 'injected cleanup'):
                module.close(self.repo, self.owner, 'A')
        self.assertEqual(state.slots(self.common)[0]['state'], 'closed')
        archived = archive.read_bytes()
        with patch.object(module, 'goals_command', side_effect=AssertionError('must not archive twice')):
            result = module.close(self.repo, self.owner, 'A')
            again = module.close(self.repo, self.owner, 'A')
        self.assertTrue(result['cleaned'], result)
        self.assertTrue(again['cleaned'], again)
        self.assertFalse(root.exists())
        self.assertFalse(self.git('branch', '--list', 'autowork/A'))
        self.assertEqual(archive.read_bytes(), archived)
        events = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['event'] == 'slot_changed' and e.get('state') == 'closed' for e in events), 1)

    def test_worktree_cleanup_failure_is_retryable_without_reclosing(self):
        self.cleanup_failure_retry(('worktree', 'remove'))

    def test_branch_cleanup_failure_is_retryable_after_worktree_removal(self):
        self.cleanup_failure_retry(('branch', '-d'))

    def test_legacy_archive_cleanup_retry(self):
        self.cleanup_failure_retry(('worktree', 'remove'), 'todo.archive.md')

    def test_nested_legacy_archive_cleanup_retry(self):
        self.cleanup_failure_retry(('branch', '-d'), 'docs/TODO-archive.md')

    def test_linked_archive_cleanup_retry(self):
        self.cleanup_failure_retry(('worktree', 'remove'), 'history/completed.md')

    def test_closed_cleanup_retry_preserves_changed_worker_branch(self):
        root, _ = self.worker()
        module = self.module()
        module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        (root / 'notes').write_text('keep')
        self.assertFalse(module.close(self.repo, self.owner, 'A')['cleaned'])
        (root / 'notes').unlink()
        (root / 'A.txt').write_text('new unlanded work')
        self.git('add', '.', cwd=root)
        self.git('commit', '-qm', 'new worker work', cwd=root)
        head = self.git('rev-parse', 'HEAD', cwd=root)
        self.assertFalse(module.close(self.repo, self.owner, 'A')['cleaned'])
        self.assertTrue(root.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/A'), head)

    def test_dirty_successful_worker_is_retained_on_close(self):
        root, commit = self.worker()
        (root / 'notes').write_text('uncommitted diagnosis')
        self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertFalse(self.module().close(self.repo, self.owner, 'A')['cleaned'])
        self.assertTrue(root.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)

    def test_canonical_only_uses_ff_only_and_preserves_staged_unrelated_file(self):
        self.worker()
        (self.repo / 'B.txt').write_text('user staged text')
        self.git('add', 'B.txt')
        index = self.git('ls-files', '-s', 'B.txt')
        module = self.module()
        from unittest.mock import patch
        with patch.object(module, 'git', wraps=module.git) as calls:
            result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        canonical_mutations = [c.args[1:] for c in calls.call_args_list
            if Path(c.args[0]) == self.repo and c.args[1] in ('merge', 'reset', 'checkout', 'rebase', 'cherry-pick')]
        self.assertEqual(len(canonical_mutations), 1)
        self.assertEqual(canonical_mutations[0][:2], ('merge', '--ff-only'))
        self.assertEqual(self.git('ls-files', '-s', 'B.txt'), index)
        self.assertEqual((self.repo / 'B.txt').read_text(), 'user staged text')

    def test_newline_and_bracket_filenames_use_literal_overlap(self):
        name = 'odd[\nname.txt'
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: odd*'))
        self.worker(files={name: 'literal filename'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
        self.assertEqual(result['integration']['changed_files'], [name])

    def start_sleeping_slot(self, task):
        args = self.retry_args()
        args.tasks = task
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(60)'])
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):
            result = dispatch.dispatch(args)
        self.assertEqual(result['outcome'], 'DISPATCHED', result)
        slot = next(s for s in state.slots(self.common) if s['task_id'] == task)
        self.addCleanup(dispatch.stop, slot['worker'])
        return slot

    def test_bounded_retry_runs_beside_independent_worker(self):
        root, commit = self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='failure')
        other = self.start_sleeping_slot('B')
        args = self.retry_args()
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(60)'])
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value='') as gate:
            result = self.module().retry_held(args)
        self.assertEqual(result['outcome'], 'RETRIED', result)
        slot = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
        self.addCleanup(dispatch.stop, slot['worker'])
        self.assertTrue(state.worker_live(slot) and state.worker_live(other))
        self.assertNotEqual(dispatch.meta(self.common, slot)['slot_index'],
                            dispatch.meta(self.common, other)['slot_index'])
        gate.assert_called_once_with(1, 0, unittest.mock.ANY)  # and the repository, for the disk gate
        self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)
        self.assertTrue(root.exists())

    def test_directory_retry_runs_beside_independent_worker(self):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: component-a/')
                        .replace('Touches: B.txt', 'Touches: component-b/'))
        self.git('add', 'TODO.md')
        self.git('commit', '-qm', 'directory scopes')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.test_bounded_retry_runs_beside_independent_worker()

    def test_running_retry_does_not_block_independent_dispatch(self):
        self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='failure')
        args = self.retry_args()
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(60)'])
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):
            first = self.module().dispatch_with_retries(args)
            self.assertEqual(first['outcome'], 'RETRIED', first)
            self.addCleanup(dispatch.stop, first['slot']['worker'])
            second = self.module().dispatch_with_retries(args)
        self.assertEqual(second['outcome'], 'DISPATCHED', second)
        slot = next(s for s in state.slots(self.common) if s['task_id'] == 'B')
        self.addCleanup(dispatch.stop, slot['worker'])
        self.assertEqual(second['active_workers'], 2)

    def test_two_retries_and_fresh_tasks_fill_eight_worker_slots(self):
        todo = self.repo / 'TODO.md'
        with todo.open('a') as out:
            for task in 'CDEFGHI':
                out.write(f'\n- [ ] {task} — Task {task}\n  Scope: {task}.txt\n'
                          f'  Touches: {task}.txt\n  Acceptance: offline fixture\n'
                          '  Checks: true\n  Dependencies: None.\n  Status: open\n')
        self.git('commit', '-qam', 'nine independent tasks')
        self.baseline = self.git('rev-parse', 'HEAD')
        for task in 'AB':
            self.worker(task)
            state.transition(self.repo, self.owner, task, 'held', reason='failure')
        args = self.retry_args()
        args.parallel = args.max_workers = 8
        # Supervise the whole bounded scenario, not the retry harness's 10-second window.
        args.worker_timeout = 90
        deadline = time.monotonic() + args.worker_timeout
        signals = Path(self.temp.name) / 'signals'
        signals.mkdir()
        release, spec, log = (signals / name for name in ('release', 'spec.json', 'workers.jsonl'))
        spec.write_text(json.dumps({task: {'ready': str(signals / task), 'release': str(release)}
                                    for task in 'ABCDEFGH'}))
        args.worker_command = json.dumps([sys.executable, str(Path(__file__).with_name('fixtures') / 'fake_worker.py'),
                                          '{prompt_file}', '{worktree}'])
        from unittest.mock import patch
        def cleanup():
            release.touch()
            for slot in state.slots(self.common):
                if slot.get('worker'):
                    dispatch.stop(slot['worker'], slot['worktree'])
        self.addCleanup(cleanup)
        with patch.dict(os.environ, FAKE_WORKER_SPEC=str(spec), FAKE_WORKER_LOG=str(log)), \
                patch.object(dispatch, 'resource_gate', return_value=''):
            for _ in range(2):
                result = self.module().dispatch_with_retries(args)
                self.assertEqual(result['outcome'], 'RETRIED', result)
            result = self.module().dispatch_with_retries(args)
            self.assertEqual(result['outcome'], 'DISPATCHED', result)
            self.assertEqual(result['active_workers'], 8)
            while not all((signals / task).exists() for task in 'ABCDEFGH'):
                self.assertLess(time.monotonic(), deadline, 'eight workers not ready')
                time.sleep(0.05)
            self.assertEqual(self.module().dispatch_with_retries(args)['outcome'], 'WAITING')
        slots = state.slots(self.common)
        self.assertEqual({s['task_id'] for s in slots}, set('ABCDEFGH'))
        self.assertEqual({dispatch.meta(self.common, s)['slot_index'] for s in slots}, set(range(1, 9)))
        self.assertEqual({s['task_id']: s['attempt'] for s in slots},
                         {'A': 2, 'B': 2, 'C': 1, 'D': 1, 'E': 1, 'F': 1, 'G': 1, 'H': 1})
        self.assertTrue(all(state.worker_live(s) for s in slots))
        self.assertLess(time.monotonic(), deadline)

    def claimed_retry_fixture(self, exhausted, requested=None):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: B.txt', 'Touches: A.txt')
                        .replace('Status: open', 'Status: in_progress') +
                        '\n- [ ] C — Independent\n  Scope: C.txt\n  Touches: C.txt\n'
                        '  Acceptance: fixture\n  Checks: true\n  Dependencies: None.\n  Status: open\n')
        self.git('commit', '-qam', 'overlapping claimed holds and independent work')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.start_sleeping_slot('C')
        for task in 'AB':
            self.worker(task)
            state.transition(self.repo, self.owner, task, 'held', reason='failure',
                             cause='blocker' if task == 'B' and exhausted else 'validation')
        args = self.retry_args()
        args.worker_command = json.dumps([sys.executable, '-c', 'import time; time.sleep(60)'])
        from unittest.mock import patch
        args.tasks = requested
        with patch.object(dispatch, 'resource_gate', return_value=''):
            result = self.module().retry_held(args)
        self.assertEqual((result['outcome'], result.get('task')), ('RETRIED', requested or 'A'), result)
        self.addCleanup(dispatch.stop, result['slot']['worker'])
        self.assertEqual(result['slot']['attempt'], 2)

    def test_retry_adapter_and_guard_agree_on_other_owned_claims(self):
        self.claimed_retry_fixture(exhausted=False)

    def test_explicit_retry_selection_keeps_other_owned_claims(self):
        self.claimed_retry_fixture(exhausted=False, requested='B')

    def test_retry_adapter_and_guard_agree_on_exhausted_claims(self):
        self.claimed_retry_fixture(exhausted=True)

    def retry_blocked_fixture(self, constraint, outcome='IDLE'):
        todo = self.repo / 'TODO.md'
        content = todo.read_text()
        if constraint == 'overlap':
            content = content.replace('Touches: A.txt', 'Touches: B.txt')
        elif constraint == 'exclusive':
            content = content.replace('Touches: A.txt', 'Touches: A.txt\n  Resources: exclusive')
        elif constraint == 'unknown':
            content = content.replace('  Touches: A.txt\n', '')
        todo.write_text(content)
        self.git('commit', '--allow-empty', '-qam', 'scope fixture')
        self.baseline = self.git('rev-parse', 'HEAD')
        self.start_sleeping_slot('B')
        self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='failure')
        args = self.retry_args()
        if constraint == 'capacity':
            args.parallel = 1
        from unittest.mock import patch
        with patch.object(dispatch, 'resource_gate', return_value=''):  # the host's load is not under test
            result = self.module().retry_held(args)
        if outcome == 'RETRIED':
            slot = next(s for s in state.slots(self.common) if s['task_id'] == 'A')
            self.addCleanup(dispatch.stop, slot['worker'])
        self.assertEqual(result['outcome'], outcome, result)
        self.assertEqual(bool(self.git('branch', '--list', 'autowork/A-r2')), outcome == 'RETRIED')

    def test_retry_respects_worker_capacity(self):
        self.retry_blocked_fixture('capacity')

    def test_retry_runs_beside_an_overlapping_worker(self):
        """TOOLSET-161-17: overlapping Touches never make a task wait."""
        self.retry_blocked_fixture('overlap', 'RETRIED')

    def test_exclusive_retry_waits_for_worker_pool(self):
        self.retry_blocked_fixture('exclusive')

    def test_a_retry_without_touches_runs_beside_the_worker_pool(self):
        """TOOLSET-161-17: a missing Touches is no hint and never makes a task run alone."""
        self.retry_blocked_fixture('unknown', 'RETRIED')

    def test_validation_cannot_mutate_candidate_then_land(self):
        self.worker()
        argv = [sys.executable, '-c', 'from pathlib import Path; Path("A.txt").write_text("unchecked")']
        result = self.module().integrate(self.repo, self.owner, 'A', argv, 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)


    def test_bounded_core_does_not_kill_unrelated_existing_child(self):
        worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'], start_new_session=True)
        try:
            result = execution.bounded_command(['true'], self.repo, self.common, 'A', 10)
            self.assertEqual(result['outcome'], 'EXECUTED', result)
            self.assertIsNone(worker.poll())
        finally:
            if worker.poll() is None:
                worker.kill()
            worker.wait()



class ExpectedBranchTests(unittest.TestCase):
    """Found qualifying pi-autowork: a restarted worker was held as 'unexpected worker branch'."""
    def test_restart_keeps_its_branch_and_a_held_retry_uses_r2(self):
        first = {'task_id': 'A', 'attempt': 1}
        restarted = {'task_id': 'A', 'attempt': 2, 'previous_attempts': [{'state': 'released'}]}
        interrupted = {'task_id': 'A', 'attempt': 2, 'previous_attempts': [{'state': 'interrupted'}]}
        retried = {'task_id': 'A', 'attempt': 2, 'previous_attempts': [{'state': 'held'}]}
        integrate = importlib.import_module('parallel_integrate')
        self.assertEqual([integrate.expected_branch(s) for s in (first, restarted, interrupted, retried)],
                         ['autowork/A', 'autowork/A', 'autowork/A', 'autowork/A-r2'])

    def test_a_paused_resume_keeps_the_branch_of_the_attempt_it_resumes(self):
        """sierra TASK-026: a held retry on -r2, paused by a runner stop and resumed, was held as
        'unexpected worker branch' because its last record was the paused interruption."""
        held = {'task_id': 'A', 'attempt': 1, 'state': 'held'}
        paused_retry = {'task_id': 'A', 'attempt': 2, 'state': 'interrupted', 'paused': True}
        paused_first = {'task_id': 'A', 'attempt': 1, 'state': 'interrupted', 'paused': True}
        integrate = importlib.import_module('parallel_integrate')
        cases = ({'task_id': 'A', 'attempt': 2, 'previous_attempts': [held, paused_retry]},
                 {'task_id': 'A', 'attempt': 2, 'previous_attempts': [held, paused_retry, paused_retry]},
                 {'task_id': 'A', 'attempt': 1, 'previous_attempts': [paused_first]},
                 {'task_id': 'A', 'attempt': 2, 'previous_attempts': [paused_first, {'state': 'interrupted'}]})
        self.assertEqual([integrate.expected_branch(s) for s in cases],
                         ['autowork/A-r2', 'autowork/A-r2', 'autowork/A', 'autowork/A'])


if __name__ == '__main__':
    unittest.main()
