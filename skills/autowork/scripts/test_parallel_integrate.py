"""Offline integration acceptance using disposable real Git repositories."""
import importlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
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

    def module(self):
        try:
            return importlib.import_module('parallel_integrate')
        except ModuleNotFoundError:
            self.fail('parallel integration implementation is missing')

    def agent_process(self, cwd=None):
        fake = Path(self.temp.name) / 'hermes'
        fake.write_text('import time; time.sleep(60)')
        proc = subprocess.Popen([sys.executable, str(fake)], cwd=cwd or self.repo, start_new_session=True)
        self.addCleanup(lambda: (proc.kill(), proc.wait()) if proc.poll() is None else None)
        return proc

    def test_fresh_unknown_session_blocks_integration_before_writes(self):
        self.worker()
        self.agent_process()
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)
        self.assertFalse((self.repo.parent / (self.repo.name + '-autowork-integration')).exists())

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
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

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

    def test_isolated_pool_session_does_not_block_landing(self):
        self.worker()
        root, _ = self.worker('B')
        proc = self.agent_process(root)
        slot = state.slots(self.common)[1]
        slot.update(worker=execution.identity(proc.pid), state='running')
        execution.save(state.slot_path(self.common, 'B'), slot)
        self.assertEqual(self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)['outcome'], 'INTEGRATED')

    def test_unattributed_session_in_pool_worktree_is_not_exempt(self):
        self.worker()
        root, _ = self.worker('B')
        self.agent_process(root)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_pool_identity_never_exempts_a_canonical_writer(self):
        self.worker()
        self.worker('B')
        proc = self.agent_process()
        slot = state.slots(self.common)[1]
        slot.update(worker=execution.identity(proc.pid), state='running')
        execution.save(state.slot_path(self.common, 'B'), slot)
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
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
        self.worker()
        self.git('mv', 'A.txt', 'outside.txt')
        self.git('commit', '-qm', 'canonical rename')
        before = self.git('rev-parse', 'HEAD')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('outside.txt', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), before)
        self.assertEqual((self.repo / 'outside.txt').read_text(), 'base\n')

    def test_head_move_retry_rechecks_actual_merge_scope(self):
        self.worker()
        marker = Path(self.temp.name) / 'renamed'
        script = ('import subprocess; from pathlib import Path; '
                  f'p=Path({str(marker)!r}); r={str(self.repo)!r}; '
                  'subprocess.run(["git","-C",r,"mv","A.txt","outside.txt"],check=True) if not p.exists() else None; '
                  'subprocess.run(["git","-C",r,"commit","-qm","rename"],check=True) if not p.exists() else None; '
                  'p.write_text("yes")')
        result = self.module().integrate(self.repo, self.owner, 'A', [sys.executable, '-c', script], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('outside.txt', result['reason'])
        self.assertEqual((self.repo / 'outside.txt').read_text(), 'base\n')

    def test_outside_touches_is_held(self):
        self.worker(files={'outside.txt': 'bad'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('outside.txt', result['reason'])
        self.assertEqual(self.git('rev-parse', 'HEAD'), self.baseline)

    def test_coordinator_file_is_held_even_if_declared(self):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: A.txt, CHANGELOG.md'))
        self.worker(files={'CHANGELOG.md': 'not worker owned'})
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('CHANGELOG.md', result['reason'])

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

    def test_other_slot_actual_files_are_protected(self):
        todo = self.repo / 'TODO.md'
        todo.write_text(todo.read_text().replace('Touches: A.txt', 'Touches: A.txt, B.txt'))
        self.worker('A', {'B.txt': 'bad overlap'})
        other, commit = self.worker('B')
        result = self.module().integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertIn('B.txt', result['reason'])
        self.assertTrue(other.exists())
        self.assertEqual(self.git('rev-parse', 'autowork/B'), commit)

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
        result = self.module().integrate(self.repo, self.owner, 'A', argv, 10)
        self.assertEqual(result['outcome'], 'INTEGRATED', result)
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

    def test_interrupted_candidate_with_unexplained_head_movement_is_held(self):
        self.worker()
        module = self.module()
        from unittest.mock import patch
        with patch.object(execution, 'bounded_command', side_effect=KeyboardInterrupt):
            with self.assertRaises(KeyboardInterrupt):
                module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        (self.repo / 'B.txt').write_text('independent canonical change')
        self.git('add', 'B.txt')
        self.git('commit', '-qm', 'unexplained movement')
        head = self.git('rev-parse', 'HEAD')
        result = module.integrate(self.repo, self.owner, 'A', ['true'], 10)
        self.assertEqual(result['outcome'], 'HELD', result)
        self.assertEqual(self.git('rev-parse', 'HEAD'), head)

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

    def cleanup_failure_retry(self, failure):
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
        archived = (self.repo / 'TODO.archive.md').read_bytes()
        with patch.object(module, 'goals_command', side_effect=AssertionError('must not archive twice')):
            result = module.close(self.repo, self.owner, 'A')
            again = module.close(self.repo, self.owner, 'A')
        self.assertTrue(result['cleaned'], result)
        self.assertTrue(again['cleaned'], again)
        self.assertFalse(root.exists())
        self.assertFalse(self.git('branch', '--list', 'autowork/A'))
        self.assertEqual((self.repo / 'TODO.archive.md').read_bytes(), archived)
        events = [json.loads(line) for line in (self.common / 'journal.jsonl').read_text().splitlines()]
        self.assertEqual(sum(e['event'] == 'slot_changed' and e.get('state') == 'closed' for e in events), 1)

    def test_worktree_cleanup_failure_is_retryable_without_reclosing(self):
        self.cleanup_failure_retry(('worktree', 'remove'))

    def test_branch_cleanup_failure_is_retryable_after_worktree_removal(self):
        self.cleanup_failure_retry(('branch', '-d'))

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

    def test_held_retry_waits_for_real_running_worker_to_drain(self):
        from types import SimpleNamespace
        root, commit = self.worker()
        state.transition(self.repo, self.owner, 'A', 'held', reason='failure')
        other, other_commit = self.worker('B')
        worker = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(10)'], start_new_session=True)
        try:
            slot = state.slots(self.common)[1]
            slot.update(worker=execution.identity(worker.pid), state='running')
            execution.save(state.slot_path(self.common, 'B'), slot)
            args = SimpleNamespace(consumer=str(self.repo), owner_pid=self.owner)
            self.assertEqual(self.module().retry_held(args)['outcome'], 'WAITING')
            self.assertFalse(self.git('branch', '--list', 'autowork/A-r2'))
            self.assertEqual(self.git('rev-parse', 'autowork/A'), commit)
            self.assertEqual(self.git('rev-parse', 'autowork/B'), other_commit)
        finally:
            worker.kill()
            worker.wait()

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


if __name__ == '__main__':
    unittest.main()
