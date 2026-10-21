"""Optimistic landing (TOOLSET-344-7dadea23): land after review, check main afterwards, revert a
regression and reopen its task, publish only green revisions. Real Git repositories, no model."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from pi_autowork import main_check, optimistic, worker  # noqa: E402


def git(repo, *args):
    return subprocess.run(['git', '-C', str(repo), *args], check=True, capture_output=True, text=True).stdout.strip()


class Repo(unittest.TestCase):
    """main with a green base, then tasks A and B each landed as a --no-ff merge with a receipt."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name) / 'repo'
        self.repo.mkdir()
        git(self.repo, 'init', '-q', '-b', 'main')
        git(self.repo, 'config', 'user.email', 'o@example.invalid')
        git(self.repo, 'config', 'user.name', 'O')
        (self.repo / 'lib.py').write_text('def value():\n    return 1\n')
        (self.repo / 'other.py').write_text('def other():\n    return 0\n')
        git(self.repo, 'add', '-A')
        git(self.repo, 'commit', '-qm', 'base')
        self.green = git(self.repo, 'rev-parse', 'HEAD')
        self.merges = {}
        for task, path, text in (('A', 'other.py', 'def other():\n    return 5\n'),
                                 ('B', 'lib.py', 'def value():\n    return 2\n')):
            git(self.repo, 'checkout', '-q', '-b', f'task-{task}')
            (self.repo / path).write_text(text)
            git(self.repo, 'commit', '-qam', f'{task} work')
            git(self.repo, 'checkout', '-q', 'main')
            git(self.repo, 'merge', '-q', '--no-ff', '-m', f'Merge {task}', f'task-{task}')
            self.merges[task] = git(self.repo, 'rev-parse', 'HEAD')
            receipt = self.repo / 'tasks' / 'evidence' / f'{task}.toml'
            receipt.parent.mkdir(parents=True, exist_ok=True)
            receipt.write_text(f'schema = 1\ntask = "{task}"\nintegration = "{self.merges[task]}"\n')
            git(self.repo, 'add', '-A')
            git(self.repo, 'commit', '-qm', f'close {task}')
        self.rev = git(self.repo, 'rev-parse', 'HEAD')

    def log(self, path='lib.py', line=2):
        return ('FAIL: test_value (test_lib.LibTests.test_value)\n'
                '----------------------------------------------------------------------\n'
                'Traceback (most recent call last):\n'
                f'  File "/elsewhere/checkout/{path}", line {line}, in value\n'
                'AssertionError: 2 != 1\n')


class OptimisticTests(Repo):
    def test_it_is_off_unless_turned_on(self):
        self.assertFalse(optimistic.enabled({}))
        self.assertFalse(optimistic.enabled({'PI_AUTOWORK_OPTIMISTIC': '0'}))
        self.assertTrue(optimistic.enabled({'PI_AUTOWORK_OPTIMISTIC': '1'}))

    def test_the_tasks_landed_since_green_are_found_from_their_receipts(self):
        self.assertEqual(optimistic.landed(self.repo, self.green, self.rev),
                         [('B', self.merges['B']), ('A', self.merges['A'])])  # newest first
        self.assertEqual(optimistic.landed(self.repo, self.merges['A'], self.rev), [('B', self.merges['B'])])
        self.assertEqual(optimistic.landed(self.repo, None, self.rev), [])

    def test_a_failure_is_blamed_on_the_task_that_wrote_its_line(self):
        landed = optimistic.landed(self.repo, self.green, self.rev)
        failing = ['test_lib.LibTests.test_value']
        self.assertEqual(optimistic.regression(self.repo, self.rev, failing, self.log(), landed), ['B'])
        # A failure no landed change explains could be any of them: all are reverted.
        self.assertEqual(optimistic.regression(self.repo, self.rev, failing, 'FAIL: test_value (x.Y.z)\n', landed),
                         ['B', 'A'])

    def test_the_blamed_task_is_reverted_and_reopened_with_the_failing_tests(self):
        reopened = []

        def reopen(repo, task, reason):
            reopened.append((task, reason))
            item = Path(repo) / 'tasks' / 'items' / f'{task}.md'
            item.parent.mkdir(parents=True, exist_ok=True)
            item.write_text('status = "open"\n')

        done = optimistic.revert(self.repo, ['B'], self.merges, ['test_lib.LibTests.test_value'], self.rev, reopen)
        self.assertEqual(done, ['B'])
        self.assertEqual((self.repo / 'lib.py').read_text(), 'def value():\n    return 1\n')  # B undone
        self.assertEqual((self.repo / 'other.py').read_text(), 'def other():\n    return 5\n')  # A kept
        message = git(self.repo, 'log', '-1', '--format=%B', 'HEAD~1')
        self.assertIn(f'This reverts commit {self.merges["B"]}.', message)  # the scorecard counts it
        self.assertIn('test_lib.LibTests.test_value', message)
        self.assertEqual(reopened[0][0], 'B')
        self.assertIn('test_lib.LibTests.test_value', reopened[0][1])
        self.assertIn('reopen B', git(self.repo, 'log', '-1', '--format=%s'))
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')

    def test_a_revert_that_conflicts_is_skipped_and_leaves_the_checkout_clean(self):
        (self.repo / 'lib.py').write_text('def value():\n    return 3\n')
        git(self.repo, 'commit', '-qam', 'later work on the same line')
        done = optimistic.revert(self.repo, ['B'], self.merges, ['t'], self.rev, lambda *a: None)
        self.assertEqual(done, [])
        self.assertEqual(git(self.repo, 'status', '--porcelain'), '')


class LandingFlowTests(unittest.TestCase):
    def test_the_verify_step_skips_the_full_suite_and_still_reviews(self):
        with tempfile.TemporaryDirectory() as tmp, \
                mock.patch.dict(os.environ, {'PI_AUTOWORK_OPTIMISTIC': '1'}), \
                mock.patch.object(worker, 'full_suite_gate', side_effect=AssertionError('the gate ran')), \
                mock.patch.object(worker, 'review', return_value=0) as review, \
                mock.patch.object(worker, 'review_root', return_value=Path(tmp)), \
                mock.patch.object(worker, 'review_port_lease', return_value=None), \
                mock.patch.object(worker, 'link_ignored'), mock.patch.object(worker, 'drop_dead_scratch'), \
                mock.patch.object(worker, 'git', return_value='abc'), \
                mock.patch.object(worker, 'batched_verdict', return_value=None):
            here = os.getcwd()
            self.addCleanup(os.chdir, here)
            os.chdir(tmp)
            self.assertEqual(worker.verify(tmp, 'T'), 0)
            os.chdir(here)
            self.assertIn('optimistic landing', review.call_args[0][4])

    def test_no_batch_starts(self):
        from pi_autowork.coordinator import Coordinator
        with tempfile.TemporaryDirectory() as tmp, mock.patch.dict(os.environ, {'PI_AUTOWORK_OPTIMISTIC': '1'}):
            runner = Coordinator.__new__(Coordinator)
            runner.state, runner.seen = Path(tmp), {}
            self.assertEqual(runner.batch_due([('A', 'a'), ('B', 'b'), ('C', 'c')]), [])

    def test_only_the_last_green_revision_is_pushed(self):
        from pi_autowork.coordinator import Coordinator
        with tempfile.TemporaryDirectory() as tmp:
            upstream, repo = Path(tmp) / 'up.git', Path(tmp) / 'repo'
            subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(upstream)], check=True)
            subprocess.run(['git', 'clone', '-q', str(upstream), str(repo)], check=True, capture_output=True)
            git(repo, 'config', 'user.email', 'o@example.invalid')
            git(repo, 'config', 'user.name', 'O')
            for n in range(3):
                (repo / 'f').write_text(str(n))
                git(repo, 'add', '-A')
                git(repo, 'commit', '-qm', f'c{n}')
                if n == 0:
                    git(repo, 'push', '-q', 'origin', 'main')
                if n == 1:
                    green = git(repo, 'rev-parse', 'HEAD')
            state = Path(tmp) / 'state'
            state.mkdir()
            runner = Coordinator.__new__(Coordinator)
            runner.repo, runner.base, runner.state, runner.seen, runner.integ = str(repo), 'main', state, {}, None
            with mock.patch.dict(os.environ, {'PI_AUTOWORK_OPTIMISTIC': '1', 'PI_AUTOWORK_PUSH': '1'}), \
                    mock.patch('pi_autowork.coordinator.telemetry.observe'):
                main_check.write(state, {'state': 'running', 'green': None})
                runner.push()  # nothing green yet: nothing pushed
                self.assertNotEqual(git(upstream, 'rev-parse', 'main'), green)
                main_check.write(state, {'state': 'green', 'green': green})
                runner.push()
                self.assertEqual(git(upstream, 'rev-parse', 'main'), green)  # green, not main's unchecked tip
                self.assertNotEqual(git(repo, 'rev-parse', 'main'), green)


if __name__ == '__main__':
    unittest.main()
