"""Landing planning commits while a review runs (TOOLSET-190-bf)."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import time
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class Review:
    """A review still running: what `session_busy` polls."""
    def poll(self):
        return None


class LandingBesideReviewTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        self.integ = Path(tmp.name) / 'session'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(self.repo)], check=True)
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'base')
        self.git(self.repo, 'worktree', 'add', '-q', '-b', 'pi-autowork/s', str(self.integ), 'main')
        self.git(self.integ, 'commit', '-q', '--allow-empty', '-m', 'docs(blockers): questions for the owner')
        runner = Coordinator.__new__(Coordinator)
        runner.repo, runner.base, runner.integ, runner.integ_branch = str(self.repo), 'main', str(self.integ), 'pi-autowork/s'
        runner.integration, runner.child = {'proc': Review()}, None
        runner.land_soon, runner.landed_at, runner.land_every = True, time.monotonic(), 600
        self.runner = runner
        patcher = mock.patch.dict(os.environ, {'PI_AUTOWORK_PUSH': '0'})  # no upstream in this fixture
        patcher.start()
        self.addCleanup(patcher.stop)

    def git(self, where, *args):
        return subprocess.run(['git', '-C', str(where), '-c', 'user.email=t@example.invalid', '-c', 'user.name=T',
                               *args], check=True, capture_output=True, text=True).stdout.strip()

    def head(self, ref):
        return self.git(self.repo, 'rev-parse', ref)

    def test_a_landing_that_needs_no_merge_does_not_wait_for_the_review(self):
        session = self.head('pi-autowork/s')
        self.runner.land_planning()
        self.assertEqual(self.head('main'), session)
        self.assertEqual(self.head('pi-autowork/s'), session)  # the review's branch is untouched
        self.assertFalse(self.runner.land_soon)

    def test_with_the_base_moved_the_landing_waits_for_the_review(self):
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'an outside commit to main')
        main, session = self.head('main'), self.head('pi-autowork/s')
        with mock.patch.object(Coordinator, 'merge_main') as merge:
            self.runner.land_planning()
        merge.assert_not_called()  # a merge would move the session under the review
        self.assertEqual((self.head('main'), self.head('pi-autowork/s')), (main, session))
        self.assertTrue(self.runner.land_soon)  # still due: it lands after the review


if __name__ == '__main__':
    unittest.main()
