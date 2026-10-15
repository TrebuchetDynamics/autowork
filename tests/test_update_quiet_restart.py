"""Updater-requested gateway restarts wait for a quiet gateway instead of forcing a drain (TOOLSET-075)."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]


def load():
    spec = importlib.util.spec_from_file_location('update_quiet_under_test', ROOT / 'update_bundle.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class QuietRestartTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.homes = [self.root, self.root / 'profiles/work']
        for home in self.homes:
            (home / 'cron').mkdir(parents=True)
        self.state = self.root / 'maintenance/toolset-update'
        self.state.mkdir(parents=True)
        self.mod = load()

    def gateway(self, active, state='running', pid=100):
        (self.root / 'gateway_state.json').write_text(json.dumps(
            {'gateway_state': state, 'active_agents': active, 'pid': pid}))
        (self.root / 'gateway.pid').write_text(json.dumps({'pid': pid}))

    def cron(self, home, claimed):
        jobs = [{'id': f'job{i}', 'state': 'scheduled', 'fire_claim': {'at': 'now'} if i < claimed else None}
                for i in range(3)]
        (home / 'cron/jobs.json').write_text(json.dumps({'jobs': jobs}))

    def test_chat_turns_exclude_restart_safe_cron_runs(self):
        self.cron(self.homes[0], 2)
        self.cron(self.homes[1], 1)
        self.gateway(3)
        self.assertEqual(self.mod.chat_turns(self.root, self.homes), 0)
        self.gateway(5)
        self.assertEqual(self.mod.chat_turns(self.root, self.homes), 2)
        self.gateway(0)
        self.assertEqual(self.mod.chat_turns(self.root, self.homes), 0)

    def test_unknown_activity_is_never_treated_as_quiet(self):
        self.cron(self.homes[0], 0)
        self.assertIsNone(self.mod.chat_turns(self.root, self.homes))  # no gateway_state.json
        for state in ('draining', 'starting', 'stopped'):
            self.gateway(0, state=state)
            self.assertIsNone(self.mod.chat_turns(self.root, self.homes), state)
        self.gateway('many')
        self.assertIsNone(self.mod.chat_turns(self.root, self.homes))
        self.gateway(0)
        (self.homes[1] / 'cron/jobs.json').write_text('{broken')
        self.assertIsNone(self.mod.chat_turns(self.root, self.homes))

    def receipt(self, **fields):
        record = {'status': 'updated', 'pid': 1, 'started_ns': 777, 'gateway_restart': 'deferred', **fields}
        (self.state / 'latest.json').write_text(json.dumps(record))

    def wait(self, turns, *, window=100, gateway_pids=None):
        """Run the waiter with a scripted chat-turn sequence and a fake clock."""
        clock = {'now': 0.0}
        sequence = iter(turns)
        pids = iter(gateway_pids or [])
        def sleep(seconds):
            clock['now'] += seconds
        with patch.object(self.mod, 'chat_turns', side_effect=lambda *_: next(sequence)), \
             patch.object(self.mod, 'gateway_pid', side_effect=lambda *_: next(pids, 100)), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart:
            outcome = self.mod.restart_when_quiet(self.root, self.homes, self.state, update_id=777, gateway=100,
                                                  window=window, poll=10, sleep=sleep, clock=lambda: clock['now'])
        return outcome, restart, json.loads((self.state / 'latest.json').read_text())

    def test_waiter_restarts_once_when_chat_turns_finish(self):
        self.receipt()
        outcome, restart, latest = self.wait([2, 1, None, 0])
        self.assertEqual(outcome, 'requested')
        self.assertEqual(restart.call_count, 1)
        self.assertEqual(latest['gateway_restart'], 'requested')
        self.assertEqual(json.loads((self.state / 'restart.json').read_text())['pid'], 4242)

    def test_waiter_never_forces_when_the_window_ends_busy(self):
        self.receipt()
        outcome, restart, latest = self.wait([1] * 50, window=100)
        self.assertEqual(outcome, 'deferred_expired')
        self.assertEqual(restart.call_count, 0)
        self.assertEqual(latest['gateway_restart'], 'deferred_expired')
        self.assertIn('hermes gateway restart', latest['gateway_restart_action'])

    def test_another_restart_already_loaded_the_update(self):
        self.receipt()
        outcome, restart, latest = self.wait([1, 1, 1], gateway_pids=[100, 100, 205])
        self.assertEqual(outcome, 'reloaded')
        self.assertEqual(restart.call_count, 0)
        self.assertEqual(latest['gateway_restart'], 'reloaded')

    def test_waiter_never_overwrites_a_newer_update_receipt(self):
        self.receipt(started_ns=999, gateway_restart='pending')
        outcome, restart, latest = self.wait([0])
        self.assertEqual(outcome, 'requested')
        self.assertEqual(latest['started_ns'], 999)
        self.assertEqual(latest['gateway_restart'], 'pending')

    def test_live_waiter_counts_as_a_pending_restart_and_reports_progress(self):
        waiter = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)', '--restart-when-quiet'])
        self.addCleanup(waiter.wait)
        self.addCleanup(waiter.kill)
        (self.state / 'restart.json').write_text(json.dumps(
            {'mode': 'deferred', 'waiter_pid': waiter.pid, 'deferred_ns': 1, 'window_s': 21600,
             'chat_turns': 2, 'checked_ns': 5, 'covers': [1, 2]}))
        self.assertIsNotNone(self.mod.pending_restart(self.state))
        progress = self.mod.gateway_drain(self.state)
        self.assertEqual(progress['state'], 'deferred')
        self.assertEqual(progress['chat_turns'], 2)
        self.assertEqual(progress['covers'], 2)
        waiter.kill()
        waiter.wait()
        self.assertIsNone(self.mod.pending_restart(self.state))

    def test_waiter_never_restarts_while_an_update_holds_the_lock(self):
        self.receipt()
        lock = (self.state / 'lock').open('a')
        self.addCleanup(lock.close)
        import fcntl
        fcntl.flock(lock, fcntl.LOCK_EX)
        sleeps = []
        def sleep(seconds):
            sleeps.append(seconds)
            fcntl.flock(lock, fcntl.LOCK_UN)  # the update finishes during the first wait
        with patch.object(self.mod, 'chat_turns', return_value=0), \
             patch.object(self.mod, 'gateway_pid', return_value=100), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart:
            outcome = self.mod.restart_when_quiet(self.root, self.homes, self.state, update_id=777, gateway=100,
                                                  window=100, poll=10, sleep=sleep, clock=lambda: 0.0)
        self.assertEqual(outcome, 'requested')
        self.assertEqual(sleeps, [10])
        self.assertEqual(restart.call_count, 1)


class UpdateDefersRestartTests(unittest.TestCase):
    """An applied update restarts at once only when no chat turn is in flight."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.remote = self.root / 'upstream'
        self.remote.mkdir()
        self.git(self.remote, 'init', '-b', 'main')
        self.git(self.remote, 'config', 'user.email', 'fixture@example.invalid')
        self.git(self.remote, 'config', 'user.name', 'Fixture')
        (self.remote / 'skills/demo').mkdir(parents=True)
        (self.remote / 'skills/demo/SKILL.md').write_text('old\n')
        (self.remote / 'plugin.yaml').write_text('name: hermes-toolset\n')
        self.git(self.remote, 'add', '.')
        self.git(self.remote, 'commit', '-m', 'initial')
        self.repo = self.root / 'checkout'
        self.git(self.root, 'clone', str(self.remote), str(self.repo))
        self.home = self.root / 'home'
        self.profiles = [('default', self.home)]
        (self.home / 'plugins').mkdir(parents=True)
        (self.home / 'plugins/hermes-toolset').symlink_to(self.repo)
        (self.home / 'skills/demo').mkdir(parents=True)
        (self.home / 'skills/demo/SKILL.md').write_text('old\n')
        self.mod = load()
        self.stub = ModuleType('setup_bundle')
        self.stub.live_profiles = lambda root: self.profiles

    def git(self, path, *args):
        return subprocess.check_output(['git', '-C', str(path), *args], stderr=subprocess.DEVNULL, text=True).strip()

    def update(self, turns):
        (self.remote / 'skills/demo/SKILL.md').write_text(f'release {turns}\n')
        self.git(self.remote, 'commit', '-am', 'release')
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.stub}), \
             patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, p: [{'profile': n, 'status': 'ready'} for n, _ in p]), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod, 'chat_turns', return_value=turns), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart, \
             patch.object(self.mod, 'start_quiet_restart', return_value=5151) as waiter, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
        return json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text()), restart, waiter

    def test_busy_gateway_defers_instead_of_restarting(self):
        receipt, restart, waiter = self.update(2)
        self.assertEqual(receipt['gateway_restart'], 'deferred')
        self.assertEqual(receipt['gateway_restart_waiting_on'], {'chat_turns': 2})
        restart.assert_not_called()
        waiter.assert_called_once()

    def test_unknown_activity_defers_too(self):
        receipt, restart, waiter = self.update(None)
        self.assertEqual(receipt['gateway_restart'], 'deferred')
        restart.assert_not_called()
        waiter.assert_called_once()

    def test_burst_of_updates_while_busy_restarts_once_and_lists_every_update(self):
        sleeper = [sys.executable, '-c', 'import time; time.sleep(60)', '--restart-when-quiet']
        spawned = []
        def command(*_):
            return sleeper
        with patch.object(self.mod, '_waiter_command', side_effect=command):
            original = self.mod.start_quiet_restart
            def start(*args):
                pid = original(*args)
                spawned.append(pid)
                return pid
            receipts = []
            for _ in range(3):
                with patch.object(self.mod, 'start_quiet_restart', side_effect=start):
                    receipts.append(self.update_unpatched_waiter(2))
        for pid in spawned:
            self.addCleanup(lambda p=pid: (subprocess.run(['kill', str(p)]), None))
        self.assertEqual([r['gateway_restart'] for r in receipts], ['deferred', 'pending', 'pending'])
        self.assertEqual(len(spawned), 1)
        state = self.home / 'maintenance/toolset-update'
        marker = json.loads((state / 'restart.json').read_text())
        self.assertEqual(marker['covers'], [r['started_ns'] for r in receipts])
        subprocess.run(['kill', str(spawned[0])])
        with patch.object(self.mod, 'chat_turns', return_value=0), \
             patch.object(self.mod, 'gateway_pid', return_value=100), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart:
            outcome = self.mod.restart_when_quiet(self.home, [self.home], state, update_id=receipts[0]['started_ns'],
                                                  gateway=100, window=100, poll=10, sleep=lambda _: None,
                                                  clock=lambda: 0.0)
        latest = json.loads((state / 'latest.json').read_text())
        self.assertEqual(outcome, 'requested')
        self.assertEqual(restart.call_count, 1)
        self.assertEqual(latest['started_ns'], receipts[2]['started_ns'])
        self.assertEqual(latest['gateway_restart'], 'requested')
        self.assertEqual(latest['gateway_restart_covers'], 3)

    def update_unpatched_waiter(self, turns):
        (self.remote / 'skills/demo/SKILL.md').write_text(f'release {len(self.git(self.remote, "log", "--oneline").splitlines())}\n')
        self.git(self.remote, 'commit', '-am', 'release')
        self.git(self.repo, 'pull', '--ff-only')
        prepare = self.mod.prepare
        with patch.object(self.mod, 'prepare', side_effect=lambda *_: prepare(self.repo, self.profiles, upstream=str(self.remote))), \
             patch.dict('sys.modules', {'setup_bundle': self.stub}), \
             patch.object(self.mod, 'finalize_profiles', side_effect=lambda s, r, p: [{'profile': n, 'status': 'ready'} for n, _ in p]), \
             patch.object(self.mod, 'gateway_running', return_value=True), \
             patch.object(self.mod, 'gateway_pid', return_value=100), \
             patch.object(self.mod, 'chat_turns', return_value=turns), \
             patch.object(self.mod, 'request_gateway_restart', return_value=4242) as restart, \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(self.mod.main(['--hermes-home', str(self.home)]), 0)
        restart.assert_not_called()
        return json.loads((self.home / 'maintenance/toolset-update/latest.json').read_text())

    def test_quiet_gateway_restarts_at_once(self):
        receipt, restart, waiter = self.update(0)
        self.assertEqual(receipt['gateway_restart'], 'requested')
        restart.assert_called_once()
        waiter.assert_not_called()


if __name__ == '__main__':
    unittest.main()
