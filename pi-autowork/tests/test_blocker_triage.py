"""Offline blocker-triage routing at the coordinator seam."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

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

    def test_changed_retained_contents_block_transient_triage_replay(self):
        with tempfile.TemporaryDirectory() as temp:
            state=Path(temp)/'state'; state.mkdir()
            for task, name, symlink in (('plain','retained.txt',False),('cr','retained\r.txt',False),
                                        ('bytes',os.fsdecode(b'retained-\xff.txt'),False),
                                        ('link','retained-link',True)):
                with self.subTest(task=task):
                    root=Path(temp)/task; root.mkdir()
                    subprocess.run(['git','init','-q',str(root)],check=True)
                    retained=root/name
                    if symlink: retained.symlink_to(os.fsdecode(b'before-\xff'))
                    else: retained.write_text('before')
                    runner=Coordinator.__new__(Coordinator)
                    runner.stop=False; runner.state=state; runner.repo=str(root)
                    runner.cfg={'git_common':str(root/'.git')}; runner.last_pi_failure='timeout'
                    runner._scratch_cleanup={str(root):True}
                    calls=[]
                    def failed(*args):
                        calls.append(args)
                        if symlink:
                            retained.unlink(); retained.symlink_to(os.fsdecode(b'after-\xff'))
                        else: retained.write_text('after')
                        return False,''
                    runner.pi_job=failed
                    row=dict(task=task,cause='blocker',worktree=str(root),reason='needs diagnosis')
                    for at in (100,160):
                        with patch('pi_autowork.coordinator.time.time',return_value=at):
                            self.assertFalse(runner.triage_blocker(row))
                    self.assertEqual(len(calls),1)
                    after=os.fsencode(os.readlink(retained)) if symlink else retained.read_bytes()
                    self.assertEqual(after,b'after-\xff' if symlink else b'after')
                    marker=json.loads((state/'triage.json').read_text())[task]
                    self.assertEqual(marker['failure'],'triage_changed_worktree')
                    self.assertTrue(marker['replay_blocked'])
