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
