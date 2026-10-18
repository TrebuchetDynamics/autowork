"""Stale agent scratch in /tmp is removed; anything recent, in use or not ours stays (TOOLSET-162-d2)."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import janitor  # noqa: E402

HOUR = 3600


def age(path, seconds):
    old = time.time() - seconds
    for root, dirs, files in os.walk(path):
        for name in dirs + files:
            os.utime(os.path.join(root, name), (old, old), follow_symlinks=False)
    os.utime(path, (old, old), follow_symlinks=False)


class JanitorTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.tmp = Path(temp.name)

    def make(self, name, hours, deep_recent=False):
        path = self.tmp / name
        (path / 'sub').mkdir(parents=True)
        (path / 'sub' / 'big.bin').write_bytes(b'x' * 4096)
        age(path, hours * HOUR)
        if deep_recent:
            (path / 'sub' / 'big.bin').touch()  # a build still writing deep inside
        return path

    def test_only_stale_unused_entries_are_removed(self):
        stale = self.make('task-review.AbC123', 3)
        recent = self.make('task-verify.XyZ789', 0.5)
        deep = self.make('task-review.Deep01', 3, deep_recent=True)
        cwd = self.make('task-review.Cwd001', 3)
        held = self.make('task-review.Open01', 3)
        kept = self.make('tmux-1000', 3)
        sock = self.tmp / 'agent.sock'
        server = socket.socket(socket.AF_UNIX)
        server.bind(str(sock))
        self.addCleanup(server.close)
        age(sock, 3 * HOUR)
        busy = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(30)'], cwd=cwd)
        self.addCleanup(lambda: (busy.kill(), busy.wait()))
        handle = open(held / 'sub' / 'big.bin', 'rb')
        self.addCleanup(handle.close)
        time.sleep(0.2)
        count, freed = janitor.sweep(str(self.tmp))
        self.assertEqual(count, 1)
        self.assertGreaterEqual(freed, 4096)
        self.assertFalse(stale.exists())
        for path in (recent, deep, cwd, held, kept, sock):
            self.assertTrue(os.path.lexists(path), path)

    def test_another_users_entry_and_a_disabled_janitor_remove_nothing(self):
        self.make('task-review.AbC123', 3)
        self.assertEqual(janitor.candidates(str(self.tmp), uid=os.getuid() + 1, used=set()), [])
        self.assertEqual(janitor.candidates(str(self.tmp), stale=0, used=set()), [])

    def test_build_output_of_idle_worktrees_goes_and_nothing_else(self):
        """TOOLSET-210-53: one repository's worktrees held 87 GB of build output and filled the disk."""
        with tempfile.TemporaryDirectory() as root:
            worktrees = Path(root) / '.worktrees'
            def tree(name, ignore='target/\nbuild/\n'):
                path = worktrees / name
                path.mkdir(parents=True)
                subprocess.run(['git', 'init', '-q', str(path)], check=True)
                (path / '.gitignore').write_text(ignore)
                for cache in ('target', 'build'):
                    (path / cache).mkdir()
                    (path / cache / 'blob').write_bytes(b'x' * 1000)
                    os.utime(path / cache / 'blob', (time.time() - 9000,) * 2)
                    os.utime(path / cache, (time.time() - 9000,) * 2)
                (path / 'src.rs').write_text('fn main() {}\n')
                return path
            idle, busy, tracked = tree('autowork-A-set-aside-1'), tree('autowork-B'), tree('autowork-C', ignore='')
            session, fresh = tree('pi-autowork-20261018-000000'), tree('autowork-D')
            os.utime(fresh / 'target' / 'blob', None)  # used a moment ago
            count, freed = janitor.prune_build_caches(worktrees, busy=[str(busy)])
            self.assertEqual(count, 3)  # idle's target/ and build/, and fresh's old build/
            self.assertGreaterEqual(freed, 3000)
            self.assertFalse((idle / 'target').exists() or (idle / 'build').exists())
            self.assertTrue((idle / 'src.rs').exists())  # sources stay
            for kept in (busy / 'target', tracked / 'target', session / 'target', fresh / 'target'):
                self.assertTrue(kept.exists(), kept)  # running, not ignored, a session, recently used
            self.assertEqual(janitor.prune_build_caches(worktrees, busy=[str(busy)], urgent=True)[0], 1)
            self.assertFalse((fresh / 'target').exists())  # a low disk does not wait for its age

    def test_one_sweep_per_host_per_interval(self):
        state = self.tmp / 'state'
        stale = self.make('task-review.AbC123', 3)
        old = os.environ.get('PI_AUTOWORK_TMP_STALE')
        self.addCleanup(lambda: os.environ.__setitem__('PI_AUTOWORK_TMP_STALE', old) if old is not None
                        else os.environ.pop('PI_AUTOWORK_TMP_STALE', None))
        os.environ['PI_AUTOWORK_TMP_STALE'] = str(2 * HOUR)
        now = time.time()
        self.assertEqual(janitor.sweep_if_due(state, str(self.tmp), now=now)[0], 1)
        self.assertFalse(stale.exists())
        self.make('task-review.Again1', 3)
        self.assertIsNone(janitor.sweep_if_due(state, str(self.tmp), now=now + 60))  # not due yet
        self.assertEqual(json.loads((state / 'janitor.json').read_text())['removed'], 1)
        self.assertEqual(janitor.sweep_if_due(state, str(self.tmp), now=now + janitor.SWEEP_EVERY)[0], 1)


if __name__ == '__main__':
    unittest.main()
