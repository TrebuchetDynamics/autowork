"""Card-free TODO execution with real Git/process fixtures, no model calls."""
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPT=Path(__file__).with_name('owner_cycle.py')

class DirectExecutionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.repo=Path(self.tmp.name)/'repo';self.repo.mkdir()
        subprocess.run(['git','init','-q',str(self.repo)],check=True)
        self.state=Path(self.tmp.name)/'state';self.state.mkdir()
        self.todo=self.repo/'TODO.md'
        self.todo.write_text('''# Work
## Now
- [ ] T1 — repair fixture
  Status: open
  Scope: fixture.py only
  Acceptance: fixture records execution
  Checks: run fixture
  Dependencies: None.
  Ownership: current coordinator
## Next
- [ ] T2 — successor
  Status: open
  Scope: fixture.py
  Acceptance: successor works
  Checks: run fixture
  Dependencies: T1.
''')
        self.fixture=self.repo/'fixture.py'
        self.fixture.write_text("from pathlib import Path\nPath('worked').write_text('yes')\n")
        self.env=dict(os.environ,HERMES_KANBAN_TASK='old-card',HERMES_KANBAN_DB='/missing/board')
    def call(self,*args):
        p=subprocess.run([sys.executable,str(SCRIPT),str(self.repo),'--state-dir',str(self.state),*args],
                         env=self.env,capture_output=True,text=True,timeout=15)
        self.assertTrue(p.stdout,p.stderr)
        return p,json.loads(p.stdout)
    def test_todo_only_default_needs_no_profile_board_or_registration(self):
        for value in ('broken JSON',json.dumps({'task_id':'old','status':'blocked'}),json.dumps({'status':'done'})):
            (self.state/'goal-handoff.json').write_text(value)
            p,r=self.call()
            self.assertEqual(p.returncode,0,r)
            self.assertEqual(r['task']['id'],'T1')
            self.assertEqual(r['outcome'],'READY')
            self.assertFalse((self.repo/'goals.json').exists())
            self.assertEqual((self.state/'goal-handoff.json').read_text(),value)
    def test_default_import_does_not_load_native_pipeline(self):
        code="import owner_cycle,sys; assert not ({'reconcile','start_goal','ready_preflight','owner_unblock'} & set(sys.modules))"
        p=subprocess.run([sys.executable,'-c',code],cwd=SCRIPT.parent,capture_output=True,text=True)
        self.assertEqual(p.returncode,0,p.stderr)
    def test_bounded_run_performs_useful_action_without_card_or_completion_claim(self):
        before=self.todo.read_bytes()
        p,r=self.call('--apply','--timeout','5','--source-path','fixture.py','--run',sys.executable,'fixture.py')
        self.assertEqual(p.returncode,0,r)
        self.assertEqual(r['outcome'],'EXECUTED')
        self.assertEqual((self.repo/'worked').read_text(),'yes')
        self.assertEqual(r['completed_tasks'],[])
        self.assertEqual(self.todo.read_bytes(),before)
        self.assertTrue(r['command_receipt']['inputs_match'])
    def test_named_task_dependencies_and_decision_hold_are_respected(self):
        p,r=self.call('--tasks','T2')
        self.assertEqual(p.returncode,1)
        self.assertIn('dependency',str(r).lower())
        self.todo.write_text(self.todo.read_text().replace('## Now','## Needs decision'))
        p,r=self.call('--tasks','T1')
        self.assertEqual(p.returncode,1)
    def test_claiming_a_task_removes_finished_worktrees_and_keeps_unfinished_ones(self):
        git=lambda root,*a:subprocess.run(['git','-C',str(root),'-c','user.name=Fixture','-c','user.email=fixture@local',*a],
                                          check=True,capture_output=True,text=True).stdout.strip()
        git(self.repo,'switch','-q','-c','main');git(self.repo,'add','.');git(self.repo,'commit','-qm','base')
        done,open_=Path(self.tmp.name)/'done',Path(self.tmp.name)/'open'
        for path in (done,open_):
            git(self.repo,'worktree','add','-q','-b','autowork/'+path.name,str(path))
            (path/'new').write_text(path.name);git(path,'add','new');git(path,'commit','-qm',path.name)
            gitdir=Path(git(path,'rev-parse','--absolute-git-dir'))
            for name in ('HEAD','logs/HEAD','ORIG_HEAD'):
                if (gitdir/name).exists():os.utime(gitdir/name,(0,0))
        git(self.repo,'merge','-q','--ff-only','autowork/done')
        p,r=self.call('--apply','--owner-pid',str(os.getpid()))
        self.assertEqual(r['outcome'],'EXECUTE',r)
        self.assertEqual([x['path'] for x in r['worktree_cleanup']['removed']],[str(done.resolve())])
        self.assertFalse(done.exists())
        self.assertIn('not integrated',r['worktree_cleanup']['kept'][0]['reason'])
        self.assertTrue(open_.is_dir())
        self.call('--release','--owner-pid',str(os.getpid()))
    def test_live_ancestor_claim_persists_across_calls_and_releases(self):
        p,r=self.call('--apply','--owner-pid',str(os.getpid()))
        self.assertEqual(p.returncode,0,r)
        self.assertEqual(r['outcome'],'EXECUTE')
        self.assertEqual(self.call('--apply','--owner-pid',str(os.getpid()))[1]['outcome'],'EXECUTE')
        self.assertEqual(self.call('--release','--owner-pid',str(os.getpid()))[1]['outcome'],'RELEASED')
    def test_invalid_owner_never_claims(self):
        p,r=self.call('--apply','--owner-pid','1')
        self.assertEqual(p.returncode,1)
        self.assertFalse((self.repo/'.git/autowork-execution/active.json').exists())
    def test_running_direct_command_blocks_other_profile_and_worktree(self):
        self.fixture.write_text("import time\nfrom pathlib import Path\nPath('entered').touch()\ntime.sleep(2)\n")
        first=subprocess.Popen([sys.executable,str(SCRIPT),str(self.repo),'--apply','--profile','one',
            '--timeout','5','--run',sys.executable,'fixture.py'],stdout=subprocess.PIPE,stderr=subprocess.PIPE,text=True)
        self.addCleanup(lambda: first.poll() is None and first.kill())
        import time
        deadline=time.monotonic()+5
        while not (self.repo/'entered').exists() and time.monotonic()<deadline: time.sleep(.02)
        p,r=self.call('--apply','--profile','two','--timeout','5','--run',sys.executable,'fixture.py')
        self.assertEqual(r['outcome'],'BUSY')
        out,err=first.communicate(timeout=10)
        self.assertEqual(first.returncode,0,err+out)
    def test_changed_source_does_not_create_reusable_passing_receipt(self):
        self.fixture.write_text("from pathlib import Path\nPath('fixture.py').write_text('# changed')\n")
        p,r=self.call('--apply','--timeout','5','--source-path','fixture.py','--run',sys.executable,'fixture.py')
        self.assertEqual(r['outcome'],'SOURCE_CHANGED')
        self.assertFalse(r['command_receipt']['inputs_match'])
    def test_timeout_budget_cannot_be_refilled_by_next_tick(self):
        self.fixture.write_text('import time\ntime.sleep(1)\n')
        p,r=self.call('--apply','--timeout','1','--budget-seconds','.05','--run',sys.executable,'fixture.py')
        self.assertEqual(r['outcome'],'TIMED_OUT')
        self.assertEqual(self.call('--apply','--timeout','1','--budget-seconds','10','--run',sys.executable,'fixture.py')[1]['outcome'],'LIMIT_REQUIRED')
    def test_ordinary_apply_without_owner_does_not_fake_dispatch(self):
        p,r=self.call('--apply')
        self.assertEqual(r['outcome'],'OWNER_REQUIRED')
        self.assertFalse((self.repo/'worked').exists())

class RecoveryTests(DirectExecutionTests):
    def ledger(self):
        data = {'version': 1, 'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md',
            'status': 'partial', 'tasks': ['T1', 'T2'], 'priority': 1, 'depends_on': []}],
            'tasks': [{'id': 'T1', 'title': 'repair fixture', 'goal': 'G', 'status': 'open',
                       'section': 'Now', 'depends_on': []},
                      {'id': 'T2', 'title': 'successor', 'goal': 'G', 'status': 'open',
                       'section': 'Next', 'depends_on': ['T1']}]}
        (self.repo / 'goals.json').write_text(json.dumps(data))
        return data

    def test_existing_index_and_explanatory_status_stay_unchanged(self):
        self.ledger()
        self.todo.write_text(self.todo.read_text().replace('Status: open', 'Status: open; implementation pending.'))
        before = (self.repo / 'goals.json').read_bytes()
        p, result = self.call('--tasks', 'T1')
        self.assertEqual(p.returncode, 0, result)
        self.assertEqual((self.repo / 'goals.json').read_bytes(), before)
        self.assertEqual(self.call('--tasks', 'T2')[0].returncode, 1)

    def test_index_mismatch_and_duplicate_todo_do_not_dispatch(self):
        data = self.ledger()
        data['tasks'][0]['status'] = 'in_progress'
        (self.repo / 'goals.json').write_text(json.dumps(data))
        self.assertIn('disagree', str(self.call()[1]))
        self.todo.write_text(self.todo.read_text() + '\n- [ ] T1 duplicate\n')
        self.assertIn('duplicate', str(self.call()[1]))

    def test_archive_satisfies_todo_only_dependency(self):
        original = self.todo.read_text()
        self.todo.write_text('# Work\n## Now\n' + original.split('## Next\n')[1])
        (self.repo / 'TODO.archive.md').write_text(original.split('## Next')[0].replace(
            '[ ] T1', '[x] T1').replace('Status: open', 'Status: done'))
        self.assertEqual(self.call('--tasks', 'T2')[1]['outcome'], 'READY')

    def test_actual_git_worktrees_share_writer_lease(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'fixture'], check=True)
        other = Path(self.tmp.name) / 'other'
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-qb', 'other', str(other)], check=True)
        self.assertEqual(self.call('--apply', '--owner-pid', str(os.getpid()))[1]['outcome'], 'EXECUTE')
        process = subprocess.run([sys.executable, str(SCRIPT), str(other), '--apply', '--owner-pid', str(os.getpid())],
                                 capture_output=True, text=True)
        self.assertEqual(json.loads(process.stdout)['outcome'], 'BUSY')

    def test_a_git_timeout_under_load_answers_busy_not_action_required(self):
        import contextlib, io
        import parallel_integrate, task_execution
        slow = subprocess.TimeoutExpired(['git', '-C', str(self.repo), 'worktree', 'list', '--porcelain'], 10)
        for argv, module, target in (
                ([str(self.repo)], task_execution, 'execute'),
                ([str(self.repo), '--apply', '--parallel', '2', '--owner-pid', str(os.getpid())],
                 parallel_integrate, 'dispatch_with_retries')):
            with self.subTest(target=target), patch.object(module, target, side_effect=slow):
                out = io.StringIO()
                with contextlib.redirect_stdout(out):
                    code = task_execution.main(argv)
                result = json.loads(out.getvalue())
                self.assertEqual(code, 1)
                self.assertEqual(result['outcome'], 'BUSY', result)
                self.assertRegex(result['reason'], r'^host busy: git worktree took over 10s \(load ')
                self.assertNotIn(str(self.repo), result['reason'])
        with patch.object(task_execution, 'execute',
                          side_effect=subprocess.CalledProcessError(1, ['git', 'status'])):
            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                task_execution.main([str(self.repo)])
            self.assertEqual(json.loads(out.getvalue())['outcome'], 'ACTION_REQUIRED')

    def test_dead_owner_recovery_preserves_dirty_candidate_and_bad_card(self):
        from task_execution import identity
        common = self.repo / '.git/autowork-execution'
        common.mkdir()
        stale = identity(os.getpid()); stale['start_ticks'] -= 1
        (common / 'active.json').write_text(json.dumps({'owner': stale, 'task_id': 'T1', 'workspace': str(self.repo)}))
        self.fixture.write_text('# preserved candidate\n')
        (self.state / 'goal-handoff.json').write_text('not json')
        self.assertEqual(self.call('--apply', '--owner-pid', str(os.getpid()))[1]['outcome'], 'EXECUTE')
        self.assertEqual(self.fixture.read_text(), '# preserved candidate\n')
        self.assertEqual((self.state / 'goal-handoff.json').read_text(), 'not json')

    def test_live_legacy_agent_blocks_without_reading_board(self):
        script = self.repo / 'run_agent.py'
        script.write_text('import time; time.sleep(20)')
        worker = subprocess.Popen([sys.executable, str(script)], cwd=self.repo)
        self.addCleanup(lambda: worker.poll() is None and worker.kill())
        try:
            _, result = self.call('--apply', '--owner-pid', str(os.getpid()))
            self.assertEqual(result['outcome'], 'BUSY', result)
        finally:
            worker.kill(); worker.wait()

    def session(self, cwd, quiet_seconds, env=None):
        """A real `pi`-named process on its own pseudo-terminal, last used quiet_seconds ago."""
        import pty
        bindir = Path(self.tmp.name) / 'bin'; bindir.mkdir(exist_ok=True)
        if not (bindir / 'pi').exists():
            (bindir / 'pi').symlink_to(sys.executable)
        master, slave = pty.openpty()
        self.addCleanup(os.close, master)
        worker = subprocess.Popen([str(bindir / 'pi'), '-c', 'import time; time.sleep(30)'], cwd=cwd,
                                  stdin=slave, stdout=slave, stderr=slave, env=env)
        os.close(slave)
        self.addCleanup(lambda: (worker.kill(), worker.wait()))
        tty = os.readlink(f'/proc/{worker.pid}/fd/0')
        stamp = time.time() - quiet_seconds
        os.utime(tty, (stamp, stamp))
        return worker

    def commit_fixture(self):
        subprocess.run(['git', '-C', str(self.repo), 'add', '.'], check=True)
        subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid',
                        'commit', '-qm', 'fixture'], check=True)

    def test_runner_jobs_do_not_block_integration_but_outside_scratch_sessions_do(self):
        import parallel_dispatch as dispatch
        import parallel_integrate as integrate
        import parallel_state as state
        from task_execution import git, save
        self.commit_fixture()
        for key, value in [('user.name', 'Fixture'), ('user.email', 'fixture@example.invalid')]:
            subprocess.run(['git', '-C', str(self.repo), 'config', key, value], check=True)
        owner = os.getppid()
        state.claim(self.repo, owner)
        common = state.common_dir(self.repo)
        scratch = self.repo / '.worktrees/pi-scratch-main-check-fixture'
        scratch.parent.mkdir()
        subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '--detach', str(scratch)], check=True)
        real_read = Path.read_text
        for task, source in [('T1', 'marker'), ('T2', 'cgroup')]:
            with self.subTest(source=source):
                baseline = git(self.repo, 'rev-parse', 'HEAD')
                root, branch, _ = dispatch.create_worktree(self.repo, common, task, baseline)
                state.create_slot(self.repo, owner, task, worktree=str(root), branch=branch, baseline=baseline)
                (root / 'fixture.py').write_text(f'# {task} repaired\n')
                git(root, 'add', 'fixture.py')
                git(root, 'commit', '-qm', task)
                commit = git(root, 'rev-parse', 'HEAD')
                slot = state.transition(self.repo, owner, task, 'reported', commit=commit)
                save(dispatch.data_dir(common, slot) / 'report.json',
                                        dict(task=task, commit=commit, changed_files=['fixture.py'], checks=[], blockers=[]))
                # Neither a scratch name, another repository's marker, nor another unit
                # exempts a person's process, including a fixture runner under a real service.
                if task == 'T1':
                    for cwd in (self.repo, scratch):
                        outsider = self.session(cwd, 60, dict(os.environ, AUTOWORK_EXECUTION_COMMON='/other/.git'))
                        def other_unit(path, *args, **kwargs):
                            if path == Path(f'/proc/{outsider.pid}/cgroup'):
                                return '0::/user.slice/pi-autowork@other.service\n'
                            return real_read(path, *args, **kwargs)
                        if cwd == self.repo:
                            # A canonical session waits only for a file it changed there; the
                            # attribution point is that a conflicting outsider is not exempt.
                            (self.repo / 'fixture.py').write_text('owner edit\n')
                        with patch.object(Path, 'read_text', other_unit):
                            result = integrate.integrate(self.repo, owner, task, ['true'], 10)
                        self.assertEqual(result['outcome'], 'BUSY', result)
                        self.assertIn('(session:', result['reason'])
                        (self.repo / 'fixture.py').unlink(missing_ok=True)
                        outsider.kill(); outsider.wait()
                env = dict(os.environ)
                env.pop('AUTOWORK_EXECUTION_COMMON', None)
                if source == 'marker':
                    env['AUTOWORK_EXECUTION_COMMON'] = str(common.parent)
                job = self.session(scratch, 60, env)
                def own_unit(path, *args, **kwargs):
                    if path == Path(f'/proc/{job.pid}/cgroup'):
                        return ('0::/user.slice/pi-autowork@repo.service/checks\n' if source == 'cgroup'
                                else '0::/user.slice/foreground.scope\n')
                    return real_read(path, *args, **kwargs)
                with patch.object(Path, 'read_text', own_unit):
                    result = integrate.integrate(self.repo, owner, task, ['true'], 10)
                    self.assertEqual(result['outcome'], 'INTEGRATED', result)
                    self.assertEqual(integrate.close(self.repo, owner, task)['outcome'], 'CLOSED')
                    self.assertFalse(root.exists())
                job.kill(); job.wait()

    def test_idle_terminal_session_does_not_block(self):
        worker = self.session(self.repo, 2 * 3600)
        _, result = self.call('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual(result['outcome'], 'EXECUTE', result)
        idle, = result['idle_sessions']
        self.assertEqual((idle['pid'], idle['active']), (worker.pid, False))
        self.assertIn('terminal idle 2 h', idle['evidence'])
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--writers'], capture_output=True, text=True, timeout=15)
        self.assertEqual((p.returncode, json.loads(p.stdout)['outcome']), (0, 'CLEAR'), p.stdout)

    def test_active_session_blocks_only_its_checkout_and_names_an_isolated_branch(self):
        self.commit_fixture()
        worker = self.session(self.repo, 60)
        _, result = self.call('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual(result['outcome'], 'BUSY', result)
        self.assertEqual(result['owners'][0]['pid'], worker.pid)
        self.assertIn('isolated worktree', result['reason'])
        self.assertEqual(result['isolate']['branch'], 'autowork/T1')
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--writers'], capture_output=True, text=True, timeout=15)
        self.assertEqual(json.loads(p.stdout)['blocking'][0]['pid'], worker.pid)
        command = result['isolate']['command']
        subprocess.run(command, check=True, capture_output=True)
        p = subprocess.run([sys.executable, str(SCRIPT), command[-1], '--state-dir', str(self.state),
                            '--apply', '--owner-pid', str(os.getpid())], env=self.env, capture_output=True, text=True, timeout=15)
        isolated = json.loads(p.stdout)
        self.assertEqual(isolated['outcome'], 'EXECUTE', p.stdout)
        # Active elsewhere is not idle: an integrator must not read it as safe to merge.
        self.assertNotIn('idle_sessions', isolated)
        self.assertEqual([w['pid'] for w in isolated['other_checkout_sessions']], [worker.pid])
        p = subprocess.run([sys.executable, str(SCRIPT), command[-1], '--writers'], capture_output=True, text=True, timeout=15)
        report = json.loads(p.stdout)
        self.assertEqual((report['outcome'], report['idle_sessions']), ('CLEAR', []))
        self.assertEqual([w['pid'] for w in report['other_checkout_sessions']], [worker.pid])

    def test_session_running_commands_is_active_despite_quiet_terminal(self):
        from task_execution import session_activity
        worker = subprocess.Popen(['sh', '-c', 'sleep 30 & wait'])
        self.addCleanup(lambda: (worker.kill(), worker.wait()))
        for _ in range(50):
            if session_activity(worker.pid)[1] == 'running commands':
                break
            time.sleep(0.05)
        self.assertEqual(session_activity(worker.pid), (True, 'running commands'))
        self.assertEqual(session_activity(worker.pid, writing=True)[0], True)

    def test_launcher_wrapping_an_idle_agent_is_idle(self):
        bindir = Path(self.tmp.name) / 'bin'; bindir.mkdir(exist_ok=True)
        (bindir / 'codex').symlink_to(sys.executable)
        code = f"import subprocess,time; subprocess.Popen([{str(bindir / 'codex')!r}, '-c', 'import time; time.sleep(30)']); time.sleep(30)"
        self.session(self.repo, 2 * 3600)  # creates bin/pi
        import pty
        master, slave = pty.openpty(); self.addCleanup(os.close, master)
        launcher = subprocess.Popen([str(bindir / 'pi'), '-c', code], cwd=self.repo, stdin=slave, stdout=slave, stderr=slave)
        os.close(slave)
        self.addCleanup(lambda: (subprocess.run(['pkill', '-P', str(launcher.pid)]), launcher.kill(), launcher.wait()))
        tty = os.readlink(f'/proc/{launcher.pid}/fd/0'); stamp = time.time() - 2 * 3600
        from task_execution import session_activity, child_pids
        for _ in range(50):
            if child_pids(launcher.pid):
                break
            time.sleep(0.05)
        os.utime(tty, (stamp, stamp))
        self.assertFalse(session_activity(launcher.pid)[0])
        _, result = self.call('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual(result['outcome'], 'EXECUTE', result)

    def test_verification_is_an_accepted_spelling_of_checks(self):
        self.todo.write_text(self.todo.read_text().replace('  Checks: run fixture\n', '  Verification: run fixture\n', 1))
        _, result = self.call()
        self.assertEqual((result['outcome'], result['task']['id']), ('READY', 'T1'), result)
        self.todo.write_text(self.todo.read_text().replace('  Verification: run fixture\n',
                                                           '  Verification: run fixture\n  Checks: run fixture\n', 1))
        _, result = self.call('--tasks', 'T1')
        self.assertIn('T1: duplicate task contract fields', result['reason'])

    def test_failed_command_is_not_task_completion(self):
        before = self.todo.read_bytes()
        p, result = self.call('--apply', '--timeout', '2', '--run', sys.executable, '-c', 'raise SystemExit(7)')
        self.assertEqual(result['outcome'], 'CHECK_FAILED')
        self.assertEqual(result['command_receipt']['exit_code'], 7)
        self.assertEqual(result['completed_tasks'], [])
        self.assertEqual(self.todo.read_bytes(), before)

    def test_pending_command_accounting_cannot_be_reset(self):
        common = self.repo / '.git/autowork-execution'
        common.mkdir()
        (common / 'budget-T1.json').write_text(json.dumps({'allocation': 5, 'remaining': 5, 'pending': 'interrupted'}))
        _, result = self.call('--apply', '--timeout', '2', '--run', sys.executable, 'fixture.py')
        self.assertEqual(result['outcome'], 'LIMIT_REQUIRED')
        self.assertFalse((self.repo / 'worked').exists())

    def test_relative_path_executable_is_fingerprinted_at_child_cwd(self):
        executable = self.repo / 'bin' / 'fixture-command'
        executable.parent.mkdir()
        executable.write_text('#!/bin/sh\nprintf yes > worked\n')
        executable.chmod(0o755)
        self.env['PATH'] = 'bin:' + os.environ['PATH']
        p, result = self.call('--apply', '--timeout', '2', '--run', 'fixture-command')
        self.assertEqual(p.returncode, 0, result)
        self.assertEqual(result['command_receipt']['executable'], str(executable))

    def test_symlinked_state_is_not_overwritten(self):
        target = self.repo / 'do-not-change'
        target.write_text('original')
        (self.state / 'task-execution-latest.json').symlink_to(target)
        _, result = self.call('--apply', '--owner-pid', str(os.getpid()))
        self.assertEqual(result['outcome'], 'ACTION_REQUIRED')
        self.assertEqual(target.read_text(), 'original')

    def test_duplicate_dependency_fields_are_not_treated_as_none(self):
        self.todo.write_text(self.todo.read_text().replace('Dependencies: None.', 'Dependencies: MISSING\n  Dependencies: T2.'))
        self.assertEqual(self.call('--tasks', 'T1')[0].returncode, 1)

    def test_loose_checklist_lines_without_task_ids_do_not_refuse_selection(self):
        backlog = '## Backlog\n- [ ] Add dark mode\n- [ ] Add export\n'
        self.todo.write_text(self.todo.read_text() + backlog)
        _, result = self.call()
        self.assertEqual((result['outcome'], result.get('task', {}).get('id')), ('READY', 'T1'), result)
        self.ledger()
        _, result = self.call()
        self.assertEqual((result['outcome'], result.get('task', {}).get('id')), ('READY', 'T1'), result)
        # Genuine duplicate executable IDs are still refused.
        self.todo.write_text(self.todo.read_text() + '- [ ] T2 — duplicate\n')
        self.assertIn('duplicate TODO task IDs', self.call()[1]['reason'])

    def test_none_dependency_followed_by_prose_is_no_dependency(self):
        self.todo.write_text(self.todo.read_text().replace('Dependencies: None.', 'Dependencies: None. Keep existing cards.'))
        _, result = self.call()
        self.assertEqual((result['outcome'], result.get('task', {}).get('id')), ('READY', 'T1'), result)
        self.todo.write_text(self.todo.read_text().replace('Dependencies: None. Keep existing cards.', 'Dependencies: None; keep cards.'))
        self.assertEqual(self.call()[1]['task']['id'], 'T1')
        # Real unresolved dependencies are still refused.
        self.todo.write_text(self.todo.read_text().replace('Dependencies: None; keep cards.', 'Dependencies: T2. Keep existing cards.'))
        p, result = self.call('--tasks', 'T1')
        self.assertEqual(p.returncode, 1, result)
        self.assertIn('unresolved dependency', result['reason'])

    def test_installed_hermes_launcher_is_an_agent_session(self):
        from task_execution import is_agent
        launcher = "import sys\nfrom hermes_cli.main import main\nsys.exit(main())"
        self.assertTrue(is_agent(['/usr/bin/python3', '-I', '-c', launcher, '-p', 'default']))
        self.assertTrue(is_agent(['python3', '-m', 'hermes_cli.main', 'chat']))
        self.assertFalse(is_agent(['python3', '-I', '-c', 'import time; time.sleep(1)', '-p', 'default']))
        self.assertFalse(is_agent(['python3', '-m', 'http.server', 'hermes_cli']))
        self.assertFalse(is_agent(['python3', 'tool.py', '-c', 'hermes_cli']))
        import pty
        def spawn(code):
            master, slave = pty.openpty()
            self.addCleanup(os.close, master)
            worker = subprocess.Popen([sys.executable, '-I', '-c', code, '-p', 'fixture'], cwd=self.repo,
                                      stdin=slave, stdout=slave, stderr=slave)
            os.close(slave)
            self.addCleanup(lambda: (worker.kill(), worker.wait()))
            stamp = time.time() - 60
            os.utime(os.readlink(f'/proc/{worker.pid}/fd/0'), (stamp, stamp))
            return worker
        unrelated = spawn('import time; time.sleep(30)')
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--writers'], capture_output=True, text=True, timeout=15)
        self.assertEqual(json.loads(p.stdout)['outcome'], 'CLEAR', p.stdout)
        hermes = spawn("import time\n# launcher for hermes_cli.main\ntime.sleep(30)")
        p = subprocess.run([sys.executable, str(SCRIPT), str(self.repo), '--writers'], capture_output=True, text=True, timeout=15)
        report = json.loads(p.stdout)
        self.assertEqual([w['pid'] for w in report['blocking']], [hermes.pid], p.stdout)
        self.assertNotIn(unrelated.pid, [w['pid'] for w in report.get('idle_sessions', [])])

    def test_named_plan_selects_only_tasks_linked_to_it(self):
        (self.repo / 'SPEC.md').write_text('# Slice\nOnly T2 is in this plan.\n')
        self.todo.write_text(self.todo.read_text().replace('Dependencies: T1.', 'Dependencies: None.\n  Sources: [slice](SPEC.md#slice)'))
        self.assertEqual(self.call('--plan', 'SPEC.md#slice')[1]['task']['id'], 'T2')
        self.assertEqual(self.call('--tasks', 'T1', '--plan', 'SPEC.md#slice')[0].returncode, 1)

    def test_malformed_retained_budget_never_becomes_new_allowance(self):
        common = self.repo / '.git/autowork-execution'; common.mkdir()
        for malformed in (None, {}, [], False, {'remaining': 1}, {'allocation': True, 'remaining': 1, 'pending': False}):
            (common / 'budget-T1.json').write_text(json.dumps(malformed))
            _, result = self.call('--apply', '--timeout', '1', '--budget-seconds', '1', '--run', sys.executable, 'fixture.py')
            self.assertEqual(result['outcome'], 'LIMIT_REQUIRED', malformed)
        self.assertFalse((self.repo / 'worked').exists())

    def test_directory_or_missing_check_input_is_not_fresh_evidence(self):
        (self.repo / 'src').mkdir()
        for path in ('src', 'missing.py'):
            p, result = self.call('--apply', '--timeout', '2', '--source-path', path, '--run', sys.executable, 'fixture.py')
            self.assertEqual(p.returncode, 1, result)
            self.assertFalse((self.repo / 'worked').exists())

    def test_receipt_identifies_exact_command_and_is_not_acceptance(self):
        argv = [sys.executable, '-c', 'pass']
        _, result = self.call('--apply', '--timeout', '2', '--run', *argv)
        self.assertEqual(result['command_receipt']['argv'], argv)
        self.assertFalse(result['command_receipt']['reusable_acceptance'])

    def test_legacy_writer_outside_repo_cwd_is_detected_by_workspace(self):
        script = Path(self.tmp.name) / 'run_agent.py'
        script.write_text('import time; time.sleep(20)')
        worker = subprocess.Popen([sys.executable, str(script), '--workspace', str(self.repo)], cwd=self.tmp.name)
        try:
            self.assertEqual(self.call('--apply', '--owner-pid', str(os.getpid()))[1]['outcome'], 'BUSY')
        finally:
            worker.kill(); worker.wait()

    def test_detached_descendant_cannot_escape_command_lifetime(self):
        self.fixture.write_text("import subprocess,sys\nfrom pathlib import Path\np=subprocess.Popen([sys.executable,'-c','import time; time.sleep(20)'],start_new_session=True,close_fds=True)\nPath('descendant').write_text(str(p.pid))\n")
        _, result = self.call('--apply', '--timeout', '2', '--run', sys.executable, 'fixture.py')
        from task_execution import identity
        pid = int((self.repo / 'descendant').read_text())
        try:
            self.assertIsNone(identity(pid), result)
        finally:
            if identity(pid): os.kill(pid, 9)
        self.assertEqual(result['outcome'], 'CHILDREN_TERMINATED')

class SelectionCacheTests(unittest.TestCase):
    def test_selection_reuses_parsing_without_hiding_content_changes_or_caller_mutation(self):
        import task_execution as execution
        import parallel_status
        with tempfile.TemporaryDirectory() as folder:
            repo = Path(folder)
            todo, archive = repo / 'TODO.md', repo / 'TODO.archive.md'
            todo.write_text('## Now\n- [ ] A — cached\n  Scope: a\n  Acceptance: works\n'
                            '  Checks: test a\n  Dependencies: OLD\n')
            archive.write_text('## Done\n- [x] OLD — prerequisite\n')
            goals = execution.goals_module()
            with patch.object(execution, 'goals_module', return_value=goals), \
                    patch.object(goals, 'task_bodies', wraps=goals.task_bodies) as bodies:
                first = execution.select(repo, 'A', None)
                first['fields']['Checks'] = 'caller mutation'
                first['priority']['state'] = 'caller mutation'
                self.assertEqual(execution.select(repo, 'A', None)['fields']['Checks'], 'test a')
                self.assertEqual(parallel_status.pending_tasks(repo),
                                 [dict(id='A', reason='awaiting dispatch', blocked_by=[])])
                self.assertEqual(bodies.call_count, 2)  # TODO and archive, once each
            stamp = archive.stat()
            archive.write_text(archive.read_text().replace('[x]', '[ ]'))
            os.utime(archive, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))
            with self.assertRaisesRegex(execution.NoEligibleTask, 'unresolved dependency'):
                execution.select(repo, 'A', None)
            todo.write_text(todo.read_text().replace('Dependencies: OLD', 'Dependencies: None.'))
            self.assertEqual(execution.select(repo, None, None)['priority']['state'], 'todo_only')
            ledger = {'version': 1, 'goals': [{'id': 'G', 'title': 'fixture', 'source': 'TODO.md',
                       'status': 'partial', 'tasks': ['A'], 'priority': 1, 'depends_on': []}],
                      'tasks': [{'id': 'A', 'title': 'cached', 'goal': 'G', 'status': 'open',
                                 'section': 'Now', 'depends_on': []}]}
            (repo / 'goals.json').write_text(json.dumps(ledger))
            self.assertEqual(execution.select(repo, None, None)['id'], 'A')
            ledger['tasks'][0]['status'] = 'in_progress'
            (repo / 'goals.json').write_text(json.dumps(ledger))
            self.assertEqual(execution.select_all(repo)[0]['fields']['Status'], 'in_progress')
            (repo / 'goals.json').unlink()
            self.assertNotIn('Status', execution.select_all(repo)[0]['fields'])


if __name__ == '__main__':
    unittest.main()
