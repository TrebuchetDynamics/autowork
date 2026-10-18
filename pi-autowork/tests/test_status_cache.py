"""One engine status snapshot serves a cycle step; the runner's own engine commands drop it."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator  # noqa: E402


class StatusCacheTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.calls = Path(tmp.name) / 'calls'
        engine = Path(tmp.name) / 'engine.py'
        # Each status call counts itself; the answer says how many came before.
        engine.write_text('import json, sys\nfrom pathlib import Path\n'
                          f'p = Path({str(self.calls)!r})\n'
                          'n = int(p.read_text()) + 1 if p.exists() else 1\n'
                          'p.write_text(str(n))\n'
                          'print(json.dumps({"outcome": "PARALLEL_STATUS", "tasks": [{"task": "A", "state": "running", "n": n}]}))\n')
        runner = Coordinator.__new__(Coordinator)
        runner.engine_path, runner.integ, runner.state = engine, tmp.name, Path(tmp.name)
        self.runner = runner

    def count(self):
        return int(self.calls.read_text())

    def test_calls_within_a_step_share_one_engine_process(self):
        """Each call was a new engine process (1.5 to 3.6 s of CPU), about 10 times in 30 s."""
        self.assertTrue(self.runner.in_flight())
        self.runner.tasks()
        self.runner.status()
        self.assertEqual(self.count(), 1)

    def test_the_runners_own_engine_command_and_time_refresh_it(self):
        self.runner.status()
        self.runner.engine('--apply')  # it can start or change any slot
        self.assertEqual(self.runner.tasks()[0]['n'], 3)
        with mock.patch('pi_autowork.coordinator.time.monotonic', return_value=10 ** 9):
            self.runner.status()  # older than STATUS_FRESH
        self.assertEqual(self.count(), 4)

    def test_a_failed_read_is_not_reused(self):
        """A status read finding the writer lock held answers ACTION_REQUIRED with no tasks."""
        self.runner.engine_path.write_text('import json\nfrom pathlib import Path\n'
                                           f'p = Path({str(self.calls)!r})\n'
                                           'p.write_text(str(int(p.read_text()) + 1 if p.exists() else 1))\n'
                                           'print(json.dumps({"outcome": "ACTION_REQUIRED", "reason": "busy"}))\n')
        self.runner.status()
        self.runner.status()
        self.assertEqual(self.count(), 2)

    def test_another_directory_is_not_answered_from_the_cache(self):
        self.runner.status()
        self.runner.status(directory=self.runner.state / 'other')
        self.assertEqual(self.count(), 2)


if __name__ == '__main__':
    unittest.main()
