"""An invalid selected source release must not replace a running coordinator."""
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path[:0] = [str(Path(__file__).resolve().parents[1]),
                str(Path(__file__).resolve().parents[2] / 'tests')]
from pi_autowork import coordinator
from src_fixture import copy_sources


class NestedLayoutTests(unittest.TestCase):
    def test_updater_refuses_nested_syntax_and_missing_payload_before_reexec(self):
        with tempfile.TemporaryDirectory() as folder:
            candidate = copy_sources(Path(folder) / 'candidate', entries=('scripts/pi-autowork.sh',))
            runner = coordinator.Coordinator.__new__(coordinator.Coordinator)
            runner.cfg = {'state_root': folder}
            runner.package, runner.package_rev = str(candidate), 'old'
            runner.toolset_rev, runner.mode = 'running', 'continuous'
            runner.reload = False
            cases = (candidate / 'Src/pi_autowork/legacy/reader.py',
                     candidate / 'Src/pi_autowork/engine/task_store.py',
                     candidate / 'Src/pi_autowork/worker.py',
                     candidate / 'Src/pi_autowork/coordinator.py')
            for path in cases:
                original = path.read_bytes()
                if path.name == 'reader.py':
                    path.write_text('if syntax error\n')
                else:
                    path.unlink()
                runner.package_rev = 'old'
                with self.subTest(path=path), patch.object(coordinator, 'git', return_value='new'), \
                        patch.object(coordinator.release, 'prepare', return_value=candidate), \
                        patch.object(runner, 'reexec') as reexec, patch.object(coordinator.LOG, 'say'):
                    runner.restart_if_updated()
                    reexec.assert_not_called()
                    self.assertEqual(runner.toolset_rev, 'running')
                path.write_bytes(original)


if __name__ == '__main__':
    unittest.main()
