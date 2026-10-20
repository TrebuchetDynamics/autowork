"""The spike's public boundary must fence receipts and refuse unsafe crash replay."""
import importlib.util
import json
import os
import signal
import subprocess
from pathlib import Path
import sys
import tempfile
import unittest

SPIKE = Path(__file__).resolve().parents[1] / 'spikes/runtime-comparison'
sys.path.insert(0, str(SPIKE))


class BoundaryTests(unittest.TestCase):
    def test_stale_receipt_and_unsafe_resume(self):
        # Removing the launch-token fence would deliver this superseded success;
        # blindly respawning a dead CLI would replay an unknown external effect.
        spec = importlib.util.find_spec('boundary')
        self.assertIsNotNone(spec, 'runtime boundary is not implemented')
        from boundary import Runtime
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            runtime = Runtime('cli', root, {'pi': 'unused'})
            handle = {'token': 'new', 'backend': 'cli', 'cwd': tmp,
                      'directory': tmp, 'worker': None}
            (root / 'active.json').write_text(json.dumps({'token': 'new'}))
            (root / 'result.json').write_text(json.dumps({'token': 'old', 'status': 'completed'}))
            self.assertEqual(runtime.observe(handle)['status'], 'interrupted')
            self.assertEqual(runtime.resume(handle)['status'], 'interrupted')
            self.assertIn('not replayed', runtime.resume(handle)['message'])

    def test_recycled_group_is_never_signalled(self):
        from boundary import Runtime, execution
        with tempfile.TemporaryDirectory() as tmp:
            runtime = Runtime('cli', Path(tmp), {'pi': 'unused'})
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                                     start_new_session=True)
            try:
                worker = execution.identity(child.pid)
                worker['start_ticks'] += 1  # unrelated process reused a recorded numeric PID
                handle = dict(token='active', backend='cli', cwd=tmp, directory=tmp, worker=worker)
                (Path(tmp) / 'active.json').write_text(json.dumps({'token': 'active'}))
                self.assertEqual(runtime.stop(handle)['status'], 'interrupted')
                self.assertIsNone(child.poll(), 'an unrelated process group was signalled')
            finally:
                child.kill()
                child.wait()

    def test_cwd_alias_cannot_start_a_second_writer(self):
        from boundary import Runtime
        with tempfile.TemporaryDirectory() as tmp:
            cwd = Path(tmp) / 'worker'
            cwd.mkdir()
            runtime = Runtime('cli', Path(tmp) / 'state', {'pi': 'unused'})
            child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'],
                env={**os.environ, 'AUTOWORK_WORKTREE': str(cwd.resolve())}, start_new_session=True)
            try:
                with self.assertRaisesRegex(RuntimeError, 'live writer'):
                    runtime.launch(cwd / '..' / 'worker', {'op': 'wait'})
            finally:
                child.kill()
                child.wait()
                for supervisor in runtime.children:
                    if supervisor.poll() is None:
                        os.killpg(supervisor.pid, signal.SIGKILL)
                    supervisor.wait()


if __name__ == '__main__':
    unittest.main()
