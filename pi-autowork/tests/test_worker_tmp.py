"""The reviewer finds what the worker provisioned under its own $TMPDIR."""
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import fleet_view, worker  # noqa: E402


def setUpModule():
    """Reviews in these tests keep their scratch in a temporary folder, never the host's /var/tmp."""
    global _root, _environment
    _root = tempfile.TemporaryDirectory()
    _environment = patch.dict(os.environ, PI_AUTOWORK_REVIEW_ROOT=_root.name, XDG_RUNTIME_DIR=_root.name)
    _environment.start()


def tearDownModule():
    _environment.stop()
    _root.cleanup()


class WorkerTmpTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.repo = Path(self.temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.execution = self.repo / '.git' / 'autowork-execution'
        (self.execution / 'slots').mkdir(parents=True)

    def slot(self, **fields):
        (self.execution / 'slots' / 'T-1.json').write_text(json.dumps({'task_id': 'T-1', 'attempt': 2, **fields}))

    def test_full_suites_share_host_slots_without_spending_their_timeout_waiting(self):
        """A competing runner must wait, survive its outer timeout, and recover a killed holder."""
        component = str(Path(worker.__file__).resolve().parents[1])
        engine = str(Path(__file__).resolve().parents[2] / 'skills/autowork/scripts')
        with patch.dict(os.environ, XDG_RUNTIME_DIR=self.temp.name):
            for slots, killed in [('1', False), ('1', True), ('0', False)]:
                with self.subTest(slots=slots, killed=killed):
                    root = self.repo / f'case-{slots}-{killed}'
                    root.mkdir()
                    self.slot(state='integrating')
                    env = dict(os.environ, PI_AUTOWORK_CHECK_SLOTS=slots)
                    script = ('import sys,json; from pathlib import Path; '
                              f'sys.path[:0] = {[component, engine]!r}; '
                              'from pi_autowork import worker; import task_execution as execution; ')
                    hold_command = ('echo $$ > holder.pid; exec sleep 30' if killed else
                                    'sleep 30 & echo $! > daemon.pid; echo $$ > holder.pid; wait')
                    holder = subprocess.Popen([sys.executable, '-c', script +
                        f'worker.run_suite({hold_command!r}, {str(root)!r}, 40, '
                        f'Path({str(root / "holder.log")!r}))'], env=env)
                    contender = None
                    try:
                        deadline = time.monotonic() + 10
                        while not (root / 'holder.pid').exists():
                            self.assertIsNone(holder.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        command = [sys.executable, '-c', script +
                            f'r = worker.run_suite("sleep .1; touch ran", {str(root)!r}, .5, '
                            f'Path({str(root / "full-check/second.log")!r}), '
                            f'Path({str(root / "full-check/T-1.status.json")!r})); sys.exit(r["code"])']
                        contender = subprocess.Popen([sys.executable, '-c', script +
                            f'r = execution.bounded_command({command!r}, Path({str(root)!r}), '
                            f'Path({str(root)!r}), "T", .6, check_slot_wait=True); '
                            f'Path({str(root / "result.json")!r}).write_text(json.dumps(r))'], env=env)
                        progress = root / 'full-check/T-1.status.json'
                        deadline = time.monotonic() + 10
                        while not progress.exists() and not (root / 'result.json').exists():
                            self.assertIsNone(contender.poll())
                            self.assertLess(time.monotonic(), deadline)
                            time.sleep(.01)
                        if slots == '1':
                            self.assertEqual(json.loads(progress.read_text())['ahead'], 1)
                            runner = fleet_view.Runner('fixture', repo=str(self.repo), state_dir=str(root))
                            lane = fleet_view.lanes(runner)[0]
                            self.assertEqual((lane.phase, lane.detail), ('waiting for a check slot', '1 ahead'))
                            self.assertEqual(fleet_view.doing(lane), 'waiting for a check slot, 1 ahead')
                            lane.activity_age = 600
                            self.assertEqual(fleet_view.quiet(lane), '')
                            time.sleep(.8)  # longer than both execution budgets
                            self.assertIsNone(contender.poll())
                            self.assertFalse((root / 'ran').exists())
                        else:
                            self.assertEqual(contender.wait(timeout=10), 0)
                            self.assertTrue((root / 'ran').exists())  # no slot even while holder runs
                        if killed:
                            os.kill(int((root / 'holder.pid').read_text()), signal.SIGKILL)
                        else:
                            os.kill(int((root / 'holder.pid').read_text()), signal.SIGTERM)
                        self.assertEqual(holder.wait(timeout=10), 0)
                        self.assertEqual(contender.wait(timeout=10), 0)
                        result = json.loads((root / 'result.json').read_text())
                        self.assertEqual(result['outcome'], 'EXECUTED')
                        self.assertTrue((root / 'ran').exists())
                    finally:
                        for name in ('holder.pid', 'daemon.pid'):
                            if (root / name).exists():
                                try:
                                    os.kill(int((root / name).read_text()), signal.SIGKILL)
                                except ProcessLookupError:
                                    pass
                        for process in (holder, contender):
                            if process is not None and process.poll() is None:
                                process.kill()
                                process.wait()

    def test_the_gate_runs_once_per_merged_tree_and_the_reviewer_is_told_its_result(self):
        """TOOLSET-227-a8: one candidate's full suite ran four or five times."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'a.txt').write_text('base\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        (self.repo / 'a.txt').write_text('merged\n')
        git('commit', '-qam', 'merged')
        runs = Path(self.temp.name) / 'runs'
        state = Path(self.temp.name) / 'state'
        os.environ['PI_AUTOWORK_VALIDATE'] = f'echo ran >> {runs}'
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_VALIDATE', None)
        for _ in range(2):  # a re-review of the same tree, as after a reviewer change
            self.assertEqual(worker.full_suite_gate(state, 'T-1', str(self.repo)), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 1)
        note = worker.gate_note(state, 'T-1', str(self.repo))
        self.assertIn(f'`echo ran >> {runs}`', note)
        self.assertIn('it passed', note)
        self.assertIn(str(worker.gate_log(state, 'T-1')), note)
        self.assertIn('Do not run the full check again', note)
        (self.repo / 'a.txt').write_text('changed\n')  # a new tree runs it again
        git('commit', '-qam', 'changed')
        worker.full_suite_gate(state, 'T-1', str(self.repo))
        self.assertEqual(runs.read_text().count('ran'), 2)
        os.environ.pop('PI_AUTOWORK_VALIDATE')
        self.assertEqual(worker.gate_note(state, 'T-1', str(self.repo)), '')

    def test_failures_that_pass_alone_need_no_base_suite(self):
        """A base suite as long as the merged one ran on nearly every review, even when each failure
        passed when rerun alone; a failure that stays red still gets the base comparison."""
        git = lambda *a: subprocess.run(['git', '-C', str(self.repo), '-c', 'user.email=t@example.invalid',
                                         '-c', 'user.name=T', *a], check=True, capture_output=True, text=True)
        (self.repo / 'test_mod.py').write_text('import unittest\nclass T(unittest.TestCase):\n'
                                               '    def test_ok(self): pass\n'
                                               '    def test_red(self): self.fail()\n')
        git('add', '-A')
        git('commit', '-qm', 'base')
        runs = Path(self.temp.name) / 'runs'
        os.environ['PI_AUTOWORK_VALIDATE'] = f'echo ran >> {runs}; echo "FAIL: test_ok (test_mod.T.test_ok)"; exit 1'
        self.addCleanup(os.environ.pop, 'PI_AUTOWORK_VALIDATE', None)
        state = Path(self.temp.name) / 'flaky'
        (self.repo / 'a.txt').write_text('merged\n')
        git('add', '-A')
        git('commit', '-qm', 'merged')
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), os.environ['PI_AUTOWORK_VALIDATE']), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 1)  # the merged run only
        os.environ['PI_AUTOWORK_VALIDATE'] = f'echo ran >> {runs}; echo "FAIL: test_red (test_mod.T.test_red)"; exit 1'
        self.assertEqual(worker.run_gate(state, 'T-1', str(self.repo), os.environ['PI_AUTOWORK_VALIDATE']), (True, ''))
        self.assertEqual(runs.read_text().count('ran'), 3)  # red alone too: the base, red as well, decides

    def test_the_worker_tmpdir_of_the_slot_attempt_is_found(self):
        self.slot()
        tmp = self.execution / 'slot-data' / 'T-1' / 'attempt-2' / 'tmp'
        (tmp / 'flutter-sdk').mkdir(parents=True)
        self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), tmp)

    def test_a_durable_allocation_is_authoritative_for_a_readopted_worker(self):
        self.slot(data_attempt=1)
        task_data = self.execution / 'slot-data' / 'T-1'
        (task_data / 'attempt-1' / 'tmp' / 'legacy-sdk').mkdir(parents=True)
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'allocated'
            record = task_data / 'tmp.json'
            record.write_text(json.dumps({'path': str(path), 'slot': 3}))
            for contents, expected in (('missing', None), ('empty', None), ('sdk', path)):
                with self.subTest(contents=contents):
                    if contents != 'missing':
                        path.mkdir(exist_ok=True)
                    if contents == 'sdk':
                        (path / 'sdk').mkdir()
                    self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), expected)

    def test_a_readopted_slot_uses_its_data_attempt(self):
        self.slot(data_attempt=1)
        tmp = self.execution / 'slot-data' / 'T-1' / 'attempt-1' / 'tmp'
        (tmp / 'sdk').mkdir(parents=True)
        self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), tmp)

    def test_nothing_is_offered_without_a_slot_or_provisioned_files(self):
        self.assertIsNone(worker.worker_tmp(str(self.repo), 'T-1'))
        self.slot()
        (self.execution / 'slot-data' / 'T-1' / 'attempt-2' / 'tmp').mkdir(parents=True)
        self.assertIsNone(worker.worker_tmp(str(self.repo), 'T-1'))  # empty: nothing to point at


class ReviewScratchTests(unittest.TestCase):
    """Reviewers copied whole repositories into RAM-backed /tmp and left them there."""

    def test_a_review_gets_its_own_tmpdir_which_is_removed_afterwards(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
            state.mkdir()
            seen = {}

            def job(settings, role, task, checkout, prompt, *rest):
                seen['tmp'] = Path(os.environ['TMPDIR'])
                seen['real'] = seen['tmp'].resolve()
                seen['prompt'] = prompt
                (seen['tmp'] / 'copy.txt').write_text('scratch')
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []), \
                        patch.dict(os.environ, {'PI_AUTOWORK_REVIEW_ROOT': str(state)}):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp
            # A real directory, not a link: code that resolves links must get the same short path,
            # so a socket under it fits the 108-byte AF_UNIX limit.
            self.assertEqual(seen['real'], seen['tmp'].absolute())
            self.assertEqual(seen['tmp'].parent, state)
            self.assertTrue(seen['tmp'].name.startswith(f'aw-r-{os.getpid()}-'), seen['tmp'])
            self.assertFalse(seen['tmp'].exists())
            self.assertIn('never directly under /tmp', seen['prompt'])
            cache = repo / '.git' / 'autowork-execution' / 'cache'
            self.assertIn(f'are in {cache} (AUTOWORK_CACHE', seen['prompt'])
            self.assertTrue(cache.is_dir())

    def test_a_review_unregisters_only_its_own_scratch_worktrees(self):
        from unittest.mock import patch
        import shutil
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            git = lambda *argv: subprocess.run(['git', '-C', str(repo), *argv], check=True,
                                               capture_output=True, text=True).stdout
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'base')
            state.mkdir()
            # Someone else's registration whose directory is gone: the runner restores such
            # worktrees, so a review must not prune it.
            other = Path(folder) / 'someone-else'
            git('worktree', 'add', '-q', '--detach', str(other), 'HEAD')
            shutil.rmtree(other)

            used = {}

            def job(settings, role, task, checkout, prompt, *rest):
                tmp = used['tmp'] = Path(os.environ['TMPDIR'])
                git('worktree', 'add', '-q', '--detach', str(tmp / 'copy'), 'HEAD')
                git('worktree', 'add', '-q', '--detach', str(tmp / 'gone'), 'HEAD')
                shutil.rmtree(tmp / 'gone')  # a reviewer that deleted its copy itself
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []), \
                        patch.dict(os.environ, {'PI_AUTOWORK_REVIEW_ROOT': str(state)}):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp
            registered = [Path(line[len('worktree '):]) for line in git('worktree', 'list', '--porcelain').splitlines()
                          if line.startswith('worktree ')]
            self.assertIn(other.resolve(), [p.resolve() for p in registered])
            # Only the review's own scratch counts: run inside a review, the test's own folder
            # lies under that review's `aw-r-` scratch too.
            scratch = used['tmp'].resolve()
            self.assertFalse([p for p in registered if p.resolve() == scratch or scratch in p.resolve().parents])


class DeadReviewScratchTests(unittest.TestCase):
    """A review killed at its timeout never runs its own cleanup."""

    def test_scratch_of_dead_reviews_goes_and_live_ones_stay(self):
        with tempfile.TemporaryDirectory() as folder:
            repo, scratch = Path(folder) / 'repo', Path(folder) / 'review-tmp'
            git = lambda *argv: subprocess.run(['git', '-C', str(repo), *argv], check=True,
                                               capture_output=True, text=True).stdout
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            git('-c', 'user.name=t', '-c', 'user.email=t@example.invalid', 'commit', '-q', '--allow-empty', '-m', 'base')
            dead = subprocess.Popen(['true'])
            dead.wait()
            gone, live = scratch / f'aw-r-{dead.pid}-abc', scratch / f'aw-r-{os.getpid()}-def'
            for path in (gone, live):
                path.mkdir(parents=True)
            git('worktree', 'add', '-q', '--detach', str(gone / 'copy'), 'HEAD')
            worker.drop_dead_scratch(str(repo), scratch)
            self.assertFalse(gone.exists())
            self.assertTrue(live.exists())
            self.assertNotIn(str((gone / 'copy').resolve()), git('worktree', 'list', '--porcelain'))


class EnvironmentMarkerTests(unittest.TestCase):
    """TOOLSET-173-94: 'could not check' is recorded apart from 'checked and wrong'."""

    def test_a_review_that_could_not_run_records_what_was_missing(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            repo, state = Path(folder) / 'repo', Path(folder) / 'state'
            subprocess.run(['git', 'init', '-q', str(repo)], check=True)
            subprocess.run(['git', '-C', str(repo), '-c', 'user.name=t', '-c', 'user.email=t@example.invalid',
                            'commit', '-q', '--allow-empty', '-m', 'base'], check=True)
            state.mkdir()
            verdicts = iter(['PI_AUTOWORK_VERIFY: fail environment — flutter SDK 3.44 (ENVIRONMENT.md)',
                             'PI_AUTOWORK_VERIFY: pass all good',
                             'PI_AUTOWORK_VERIFY: fail — the Back behaviour is not verified',
                             'PI_AUTOWORK_VERIFY: pass now'])
            job = lambda *a: {'ok': True, 'text': next(verdicts)}
            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 1)
                    marker = worker.environment_marker(state, 'T-1')
                    self.assertEqual(json.loads(marker.read_text())['missing'], 'flutter SDK 3.44 (ENVIRONMENT.md)')
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
                    self.assertFalse(marker.exists())
                    self.assertEqual(worker.review_findings(state, 'T-1'), '')  # an environment miss is no finding
                    self.assertEqual(worker.verify(str(state), 'T-1'), 1)
                    self.assertEqual(worker.review_findings(state, 'T-1'),
                                     'PI_AUTOWORK_VERIFY: fail — the Back behaviour is not verified')
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
                    self.assertEqual(worker.review_findings(state, 'T-1'), '')
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp


if __name__ == '__main__':
    unittest.main()
