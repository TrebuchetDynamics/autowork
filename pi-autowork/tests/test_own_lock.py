"""The runner tells its own helpers' locks from another process's (TOOLSET-333-34)."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import coordinator  # noqa: E402

ENGINE = Path(__file__).resolve().parents[1] / 'engine'


class OwnProcessTests(unittest.TestCase):
    def test_this_runner_and_its_descendants_are_its_own(self):
        child = subprocess.Popen(['sh', '-c', 'sleep 30 & echo $!; wait'], stdout=subprocess.PIPE, text=True)
        self.addCleanup(child.kill)
        grandchild = int(child.stdout.readline())
        self.addCleanup(lambda: subprocess.run(['kill', str(grandchild)], capture_output=True))
        self.assertTrue(coordinator.own_process(child.pid))
        self.assertTrue(coordinator.own_process(grandchild))

    def test_another_process_or_no_holder_is_not(self):
        self.assertFalse(coordinator.own_process(1))
        self.assertFalse(coordinator.own_process(None))
        other = subprocess.run(['sh', '-c', 'setsid sleep 30 >/dev/null 2>&1 & echo $!'], capture_output=True,
                               text=True).stdout.strip()
        self.addCleanup(lambda: subprocess.run(['kill', other], capture_output=True))
        self.assertFalse(coordinator.own_process(int(other)), 'reparented away from this runner')


class BusyAnswerTests(unittest.TestCase):
    """The engine's BUSY answer names the lock and its holder, which the runner reads."""

    def test_a_busy_dispatch_names_the_lock_and_holder(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        code = ('import sys\nsys.path.insert(0, sys.argv[1])\nimport task_execution\n'
                'from pathlib import Path\n'
                'try:\n'
                '    with task_execution.lock(Path(sys.argv[2]), wait=0):\n        pass\n'
                'except BlockingIOError as exc:\n'
                '    import json; print(json.dumps({"lock": exc.lock, "holder": exc.holder}))\n')
        hold = ('import sys, time\nsys.path.insert(0, sys.argv[1])\nimport task_execution\n'
                'from pathlib import Path\n'
                'with task_execution.lock(Path(sys.argv[2]), wait=0):\n'
                '    print("held", flush=True)\n    time.sleep(30)\n')
        path = str(Path(tmp.name) / 'writer.lock')
        holder = subprocess.Popen([sys.executable, '-c', hold, str(ENGINE), path], stdout=subprocess.PIPE, text=True)
        self.addCleanup(holder.kill)
        self.assertEqual(holder.stdout.readline().strip(), 'held')
        out = subprocess.run([sys.executable, '-c', code, str(ENGINE), path], capture_output=True, text=True)
        answer = json.loads(out.stdout)
        self.assertEqual(answer, {'lock': 'writer.lock', 'holder': holder.pid})
        self.assertTrue(coordinator.own_process(answer['holder']), "this test's own child")


if __name__ == '__main__':
    unittest.main()
