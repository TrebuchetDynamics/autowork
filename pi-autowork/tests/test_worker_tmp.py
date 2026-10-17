"""The reviewer finds what the worker provisioned under its own $TMPDIR."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import worker  # noqa: E402


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

    def test_the_worker_tmpdir_of_the_slot_attempt_is_found(self):
        self.slot()
        tmp = self.execution / 'slot-data' / 'T-1' / 'attempt-2' / 'tmp'
        (tmp / 'flutter-sdk').mkdir(parents=True)
        self.assertEqual(worker.worker_tmp(str(self.repo), 'T-1'), tmp)

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
                seen['prompt'] = prompt
                (seen['tmp'] / 'copy.txt').write_text('scratch')
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []):
                    self.assertEqual(worker.verify(str(state), 'T-1'), 0)
            finally:
                os.chdir(old_cwd)
                if old_tmp is None:
                    os.environ.pop('TMPDIR', None)
                else:
                    os.environ['TMPDIR'] = old_tmp
            self.assertTrue(str(seen['tmp']).startswith(str(state / 'review-tmp')), seen['tmp'])
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

            def job(settings, role, task, checkout, prompt, *rest):
                tmp = Path(os.environ['TMPDIR'])
                git('worktree', 'add', '-q', '--detach', str(tmp / 'copy'), 'HEAD')
                git('worktree', 'add', '-q', '--detach', str(tmp / 'gone'), 'HEAD')
                shutil.rmtree(tmp / 'gone')  # a reviewer that deleted its copy itself
                return {'ok': True, 'text': 'PI_AUTOWORK_VERIFY: pass all good'}

            old_cwd, old_tmp = os.getcwd(), os.environ.get('TMPDIR')
            os.chdir(repo)
            try:
                with patch.object(worker.pi_runtime, 'job', job), patch.object(worker, 'pending_live', lambda c, t: []):
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
            self.assertFalse([p for p in registered if (state / 'review-tmp').resolve() in p.resolve().parents])


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
