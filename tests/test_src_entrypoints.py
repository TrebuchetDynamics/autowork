"""Public runner adapters select real, same-release source owners."""
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from src_fixture import copy_sources

ROOT = Path(__file__).resolve().parents[1]


class SrcEntrypointTests(unittest.TestCase):
    def test_legacy_and_canonical_engine_import_orders_keep_actual_owner_identity(self):
        for first in ('task_store', 'pi_autowork.engine.task_store'):
            with self.subTest(first=first):
                code = f'''import sys, importlib
from pathlib import Path
root = Path({str(ROOT)!r})
sys.path[:0] = [str(root / 'pi-autowork/engine'), str(root / 'pi-autowork')]
a = importlib.import_module({first!r})
b = importlib.import_module('pi_autowork.engine.task_store')
assert a is b is importlib.import_module('task_store')
assert Path(a.__file__) == root / 'Src/pi_autowork/engine/task_store.py'
from pi_autowork import command, task_snapshot, fleet_view
assert Path(command.__file__) == root / 'Src/pi_autowork/command.py'
assert fleet_view.TaskRow is task_snapshot.TaskRow
from pi_autowork import workspaces
from pi_autowork.engine import worktree_paths
original = worktree_paths.worktree_path
try:
    worktree_paths.worktree_path = lambda repo, name: (repo, name)
    assert workspaces.task_path(root, 'repository', 'task') == ('repository', 'task')
finally:
    worktree_paths.worktree_path = original
from pi_autowork import release
from pi_autowork.engine import parallel_state
bridge = (root / release.STATE_FILE).read_text()
for name in ('STATE_SCHEMA', 'STATE_SCHEMA_READS'):
    assert release.schema(bridge, name, None) == getattr(parallel_state, name)
'''
                result = subprocess.run([sys.executable, '-B', '-c', code], cwd=os.environ['TMPDIR'],
                                        text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)

    def test_spaced_release_commands_and_missing_owner_never_borrow_checkout(self):
        with tempfile.TemporaryDirectory() as folder:
            root = copy_sources(Path(folder) / 'selected release')
            command = root / 'pi-autowork/pi_autowork/command.py'
            env = dict(os.environ, PYTHONPATH=str(ROOT / 'pi-autowork'))
            args = [sys.executable, '-B', str(command), 'capabilities']
            commands = [(args, env),
                        ([sys.executable, '-B', '-m', 'pi_autowork.command', 'capabilities'],
                         dict(env, PYTHONPATH=str(root / 'pi-autowork')))]
            for argv, environment in commands:
                result = subprocess.run(argv, cwd=folder, env=environment,
                                        text=True, capture_output=True, timeout=30)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn('prepare_api', result.stdout)
            (root / 'Src/pi_autowork/command.py').unlink()
            for argv, environment in commands:
                result = subprocess.run(argv, cwd=folder, env=environment,
                                        text=True, capture_output=True, timeout=30)
                self.assertNotEqual(result.returncode, 0)
                self.assertIn('missing selected-release source', result.stderr)


if __name__ == '__main__':
    unittest.main()
