"""Offline blocker-triage routing at the coordinator seam."""
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class BlockerTriageTests(unittest.TestCase):
    def test_a_task_wait_never_invokes_blocker_triage(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            subprocess.run(['git', 'init', '-q', str(root)], check=True)
            runner = Coordinator.__new__(Coordinator)
            runner.stop, runner.state, runner.repo = False, root, str(root)
            runner.cfg = {'git_common': str(root / '.git')}
            runner.pi_job = lambda *args: self.fail('task waits must not invoke a model triage')
            # The explicit field wins even for an old snapshot still labeled blocker.
            row = dict(task='A', cause='blocker', waits_for=['B'], worktree=str(root),
                       reason='Needs B to land.')
            self.assertFalse(runner.triage_blocker(row))
            self.assertFalse((root / 'triage.json').exists())
