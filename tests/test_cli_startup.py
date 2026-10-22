"""Stopping the runner while it still starts up (journal, 2026-10-19).

systemd sends SIGINT to stop a unit; a runner that was replacing itself after a toolset update
received it while `cli.py` was still reading Pi's model catalog, before the coordinator had
installed its signal handler. The default handler turned that into a KeyboardInterrupt traceback
in the journal. A stop is deliberate: one line and exit 130, which the unit treats as success.
"""
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]


class StartupInterruptTests(unittest.TestCase):
    def test_an_interrupt_during_startup_is_a_deliberate_stop_not_a_traceback(self):
        base = Path(tempfile.mkdtemp(prefix='aw-startup-'))
        self.addCleanup(lambda: subprocess.run(['rm', '-rf', str(base)]))
        (base / 'bin').mkdir()
        pi = base / 'bin' / 'pi'
        # `pi --list-models` hangs: startup is interrupted while it waits on the catalog.
        started = base / 'catalog-read-started'
        pi.write_text(f'#!/usr/bin/env bash\ncase "$1" in --list-models) touch {started}; sleep 30;; esac\n')
        pi.chmod(0o755)
        repo = base / 'repo'
        subprocess.run(['git', 'init', '-q', '-b', 'main', str(repo)], check=True)
        subprocess.run(['cp', '-r', str(ROOT / 'tasks'), str(repo / 'tasks')], check=True)
        subprocess.run(['git', '-C', str(repo), 'add', '-A'], check=True)
        subprocess.run(['git', '-C', str(repo), '-c', 'user.name=T', '-c', 'user.email=t@example.invalid',
                        'commit', '-qm', 'plan'], check=True)
        env = dict(os.environ, PI_BIN=str(pi), PI_AUTOWORK_TOOLSET=str(ROOT), PI_AUTOWORK_STATE_DIR=str(base / 'state'),
                   PI_AUTOWORK_HERMES_HOME=str(base / 'no-hermes'), PI_AUTOWORK_PUSH='0')
        runner = subprocess.Popen([sys.executable, str(ROOT / 'pi-autowork/pi_autowork/cli.py'), '--repo', str(repo), '--once'],
                                  cwd=repo, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
                                  # systemd starts the unit with the default disposition; a test
                                  # runner may have inherited SIG_IGN, which Python would keep.
                                  preexec_fn=lambda: signal.signal(signal.SIGINT, signal.SIG_DFL))
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not started.exists() and runner.poll() is None:
            time.sleep(0.05)  # until the catalog read is in progress
        if runner.poll() is not None:
            self.fail('the runner ended before reading the catalog: %s %s' % runner.communicate())
        runner.send_signal(signal.SIGINT)
        out, err = runner.communicate(timeout=30)
        self.assertEqual(runner.returncode, 130, out + err)
        self.assertNotIn('Traceback', err, err)
        self.assertIn('stopped during startup', err)


if __name__ == '__main__':
    unittest.main()
