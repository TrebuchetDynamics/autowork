"""Real, isolated Linux process trees; no Pi installation or model calls."""
import ctypes
import importlib.util
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import sys
import tempfile
import time
import unittest


WRAPPER = Path(__file__).resolve().parents[1] / 'pi_autowork' / 'pi_process.py'


def identity(pid):
    try:
        fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
        return fields[19]
    except FileNotFoundError:
        return None


@unittest.skipUnless(sys.platform == 'linux' and hasattr(os, 'pidfd_open'), 'Linux pidfds required')
class PiProcessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Adopt the wrapper in the parent-death test so even its zombie is reaped.
        cls.libc = ctypes.CDLL(None, use_errno=True)
        previous = ctypes.c_int()
        assert cls.libc.prctl(37, ctypes.byref(previous), 0, 0, 0) == 0
        cls.previous_subreaper = previous.value
        assert cls.libc.prctl(36, 1, 0, 0, 0) == 0

    @classmethod
    def tearDownClass(cls):
        cls.libc.prctl(36, cls.previous_subreaper, 0, 0, 0)

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.metadata = self.root / 'identity.json'
        self.children = []
        self.addCleanup(self.cleanup)

    def cleanup(self):
        for child in self.children:
            if child.poll() is None:
                child.terminate()
                try:
                    child.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    child.kill()
                    child.wait(timeout=3)
            for stream in (child.stdin, child.stdout, child.stderr):
                if stream:
                    stream.close()
        # Test fallback only: use pinned pidfds, never stale PID-only kills.
        for path in self.root.glob('*.pid'):
            try:
                pid, started = json.loads(path.read_text())
                fd = os.pidfd_open(pid)
                try:
                    if identity(pid) == started:
                        signal.pidfd_send_signal(fd, signal.SIGKILL)
                finally:
                    os.close(fd)
                try:
                    os.waitpid(pid, 0)
                except ChildProcessError:
                    pass
            except (OSError, ValueError):
                pass

    def command(self, executable, *args, deadline=5, parent=None):
        expected = [] if parent is None else ['--parent-pid', str(parent[0]),
                                               '--parent-start', parent[1]]
        return [sys.executable, str(WRAPPER), '--identity', str(self.metadata),
                '--deadline', str(deadline), *expected, '--', executable, *args]

    def launch(self, command, **kwargs):
        child = subprocess.Popen(command, start_new_session=True, **kwargs)
        self.children.append(child)
        return child

    def wait_for(self, predicate, timeout=4):
        end = time.monotonic() + timeout
        while time.monotonic() < end:
            result = predicate()
            if result:
                return result
            time.sleep(.01)
        self.fail('timed out waiting for subprocess evidence')

    def metadata_ready(self):
        if not self.metadata.exists():
            return None
        data = json.loads(self.metadata.read_text())
        return data if data.get('pi_pid') else None

    def assert_finished(self, wrapper, code):
        self.assertEqual(wrapper.wait(timeout=4), code)
        data = json.loads(self.metadata.read_text())
        self.assertEqual(data['pid'], wrapper.pid)
        self.assertTrue(data['start_time'])
        self.assertTrue(data['cleanup_complete'], data)
        self.assertEqual(data['exit_code'], code)
        self.assertEqual(stat.S_IMODE(self.metadata.stat().st_mode), 0o600)
        return data

    def tree(self, normal_exit=False):
        # Pi -> real /bin/sh -> ordinary and setsid children, all inheriting stdio.
        # Removing subreaping, escalation or escaped-tree discovery leaks a PID.
        recorder = """import json, os, pathlib, signal, sys, time
p = os.getpid()
s = pathlib.Path('/proc/%d/stat' % p).read_text().rsplit(')', 1)[1].split()[19]
signal.signal(signal.SIGTERM, signal.SIG_IGN)
signal.signal(signal.SIGINT, signal.SIG_IGN)
pathlib.Path(sys.argv[1]).write_text(json.dumps([p, s]))
time.sleep(60)
"""
        script = self.root / 'child.py'
        script.write_text(recorder)
        shell = self.root / 'tree.sh'
        shell.write_text('"$1" "$2" "$3/ordinary.pid" &\n'
                         'setsid "$1" "$2" "$3/escaped.pid" &\nwait\n')
        pi = self.root / 'pi.py'
        pi.write_text("""import json, os, pathlib, subprocess, sys, time
root = pathlib.Path(sys.argv[1])
p = subprocess.Popen(['/bin/sh', str(root/'tree.sh'), sys.executable, str(root/'child.py'), str(root)])
s = pathlib.Path('/proc/%d/stat' % p.pid).read_text().rsplit(')', 1)[1].split()[19]
(root/'shell.pid').write_text(json.dumps([p.pid, s]))
while not all((root/name).exists() for name in ['ordinary.pid', 'escaped.pid']):
    time.sleep(.005)
""" + ('sys.exit(7)\n' if normal_exit else 'time.sleep(60)\n'))
        return [sys.executable, str(pi), str(self.root)]

    def wait_tree(self):
        self.wait_for(lambda: all((self.root / name).exists()
                                 for name in ['shell.pid', 'ordinary.pid', 'escaped.pid']))
        records = [json.loads(path.read_text()) for path in self.root.glob('*.pid')]
        self.assertEqual(len(records), 3)
        return records

    def assert_gone(self, records):
        # Zombies count as leaks: complete must mean reaped, not merely signalled.
        for pid, started in records:
            self.assertNotEqual(identity(pid), started, f'owned process {pid} remains')

    def test_version_and_nonzero_exit_are_transparent(self):
        wrapper = self.launch(self.command(sys.executable, '--version'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        out, err = wrapper.communicate(timeout=4)
        expected = subprocess.run([sys.executable, '--version'], capture_output=True, check=True)
        self.assertEqual((out, err), (expected.stdout, expected.stderr))
        self.assert_finished(wrapper, 0)
        wrapper = self.launch(self.command(sys.executable, '-c', 'raise SystemExit(23)'),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
        self.assert_finished(wrapper, 23)

    def test_stdio_is_inherited_without_protocol_or_prompt_metadata(self):
        wrapper = self.launch(self.command(sys.executable, '-c',
                              'import os; os.write(1, os.read(0, 100)); os.write(2, b"diagnostic")'),
                              stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(wrapper.communicate(b'private prompt\x00\xff\n', timeout=4),
                         (b'private prompt\x00\xff\n', b'diagnostic'))
        self.assert_finished(wrapper, 0)
        self.assertNotIn('private prompt', self.metadata.read_text())
        self.assertNotIn('os.write', self.metadata.read_text())

    def test_deadline_kills_shell_tree_and_escaped_child_not_sentinel(self):
        sentinel = self.launch([sys.executable, '-c', 'import time; time.sleep(60)'])
        started = time.monotonic()
        wrapper = self.launch(self.command(*self.tree(), deadline=.8),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        records = self.wait_tree()
        initial = self.wait_for(self.metadata_ready)
        self.assertFalse(initial['cleanup_complete'])
        self.assertEqual(identity(initial['pi_pid']), initial['pi_start_time'])
        self.assertNotEqual(os.getpgid(initial['pi_pid']), os.getpgid(wrapper.pid))
        self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
        self.assert_finished(wrapper, 124)
        self.assertLess(time.monotonic() - started, 2.8)
        self.assert_gone(records)
        self.assertIsNone(sentinel.poll())

    def test_normal_exit_cleans_inherited_stdio_and_escaped_descendants(self):
        wrapper = self.launch(self.command(*self.tree(normal_exit=True)),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        records = self.wait_tree()
        self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
        self.assert_finished(wrapper, 7)
        self.assert_gone(records)

    def test_worker_group_term_and_direct_int_clean_tree(self):
        for sig in (signal.SIGTERM, signal.SIGINT):
            with self.subTest(signal=sig):
                for path in self.root.glob('*.pid'):
                    path.unlink()
                wrapper = self.launch(self.command(*self.tree()))
                records = self.wait_tree()
                started = time.monotonic()
                if sig == signal.SIGTERM:
                    os.killpg(wrapper.pid, sig)
                else:
                    wrapper.send_signal(sig)
                self.assert_finished(wrapper, 128 + sig)
                self.assertLess(time.monotonic() - started, 2)
                self.assert_gone(records)

    def test_parent_death_cleans_and_wrapper_stays_in_worker_group(self):
        command = self.command(*self.tree())
        launcher = self.launch([sys.executable, '-c',
                               'import subprocess,sys,time; subprocess.Popen(sys.argv[1:]); time.sleep(60)',
                               *command], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        records = self.wait_tree()
        data = self.wait_for(self.metadata_ready)
        self.assertEqual(os.getpgid(data['pid']), launcher.pid)
        launcher.kill()
        launcher.wait(timeout=3)
        self.wait_for(lambda: json.loads(self.metadata.read_text()).get('cleanup_complete'))
        pid, status = os.waitpid(data['pid'], 0)
        self.assertEqual(pid, data['pid'])
        self.assertEqual(os.waitstatus_to_exitcode(status), 128 + signal.SIGTERM)
        self.assertEqual(launcher.communicate(timeout=3), (b'', b''))
        self.assert_gone(records)

    def test_expected_parent_allows_live_match_and_refuses_wrong_identity(self):
        for parent, code in [((os.getpid(), identity(os.getpid())), 0),
                             ((os.getpid(), '0'), 143),
                             ((os.getppid(), identity(os.getppid())), 143)]:
            with self.subTest(parent=parent):
                marker = self.root / 'payload-ran'
                marker.unlink(missing_ok=True)
                wrapper = self.launch(self.command(sys.executable, '-c',
                                      'import pathlib,sys; pathlib.Path(sys.argv[1]).touch()',
                                      str(marker), parent=parent),
                                      stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
                data = self.assert_finished(wrapper, code)
                self.assertEqual(marker.exists(), code == 0)
                if code != 0:
                    self.assertIsNone(data['pi_pid'])
                    self.assertIsNone(data['pi_start_time'])

    def test_parent_arguments_must_be_a_valid_pair(self):
        for arguments in [ ['--parent-pid', str(os.getpid())],
                           ['--parent-start', identity(os.getpid())],
                           ['--parent-pid', '0', '--parent-start', '1'],
                           ['--parent-pid', '-1', '--parent-start', '1'],
                           ['--parent-pid', 'bad', '--parent-start', '1'],
                           ['--parent-pid', str(os.getpid()), '--parent-start', ''],
                           ['--parent-pid', str(os.getpid()), '--parent-start', 'bad'] ]:
            with self.subTest(arguments=arguments):
                marker = self.root / 'payload-ran'
                command = self.command(sys.executable, '-c',
                                       'import pathlib,sys; pathlib.Path(sys.argv[1]).touch()',
                                       str(marker))
                command[2:2] = arguments
                wrapper = self.launch(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
                self.assertEqual(wrapper.returncode, 125)
                self.assertFalse(marker.exists())

    def test_expected_parent_blocks_delayed_start_after_subreaper_adoption(self):
        # This test process is the ancestor subreaper. The worker exits normally
        # BEFORE a gate allows the guard interpreter to start, so its first
        # getppid() observes us, not its original worker. No timing sleeps decide
        # that order. Legacy omission demonstrates the otherwise unsafe launch.
        delayed = self.root / 'delayed.py'
        delayed.write_text('import os,pathlib,sys,time\n'
                           'while not pathlib.Path(sys.argv[1]).exists(): time.sleep(.005)\n'
                           'os.execv(sys.argv[2], sys.argv[2:])\n')
        worker_code = """import json, os, pathlib, subprocess, sys
root = pathlib.Path(sys.argv[1])
command = sys.argv[3:]
if sys.argv[2] == 'explicit':
    started = pathlib.Path('/proc/%d/stat' % os.getpid()).read_text().rsplit(')', 1)[1].split()[19]
    command[2:2] = ['--parent-pid', str(os.getpid()), '--parent-start', started]
p = subprocess.Popen([sys.executable, str(root/'delayed.py'), str(root/'gate'), *command])
started = pathlib.Path('/proc/%d/stat' % p.pid).read_text().rsplit(')', 1)[1].split()[19]
(root/'delayed.pid').write_text(json.dumps([p.pid, started]))
"""
        for mode, code in [('legacy', 0), ('explicit', 143)]:
            with self.subTest(mode=mode):
                gate, marker = self.root / 'gate', self.root / 'payload-ran'
                for path in (gate, marker, self.metadata):
                    path.unlink(missing_ok=True)
                command = self.command(sys.executable, '-c',
                                       'import pathlib,sys; pathlib.Path(sys.argv[1]).touch()',
                                       str(marker))
                worker = self.launch([sys.executable, '-c', worker_code,
                                      str(self.root), mode, *command],
                                     stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                self.assertEqual(worker.wait(timeout=4), 0)
                pid, started = json.loads((self.root / 'delayed.pid').read_text())
                fields = Path(f'/proc/{pid}/stat').read_text().rsplit(')', 1)[1].split()
                self.assertEqual(int(fields[1]), os.getpid())
                self.assertEqual(fields[19], started)
                gate.touch()
                self.assertEqual(worker.communicate(timeout=4), (b'', b''))
                waited, status = os.waitpid(pid, 0)
                self.assertEqual(waited, pid)
                self.assertEqual(os.waitstatus_to_exitcode(status), code)
                self.assertEqual(marker.exists(), mode == 'legacy')
                data = json.loads(self.metadata.read_text())
                self.assertEqual(data['pid'], pid)
                self.assertEqual(data['start_time'], started)
                self.assertTrue(data['cleanup_complete'])
                self.assertEqual(data['exit_code'], code)
                if mode == 'explicit':
                    self.assertIsNone(data['pi_pid'])
                    self.assertIsNone(data['pi_start_time'])

    def test_inherited_sigchld_ignore_does_not_lose_exit_status(self):
        launcher = self.launch([sys.executable, '-c',
                               'import os,signal,sys; signal.signal(signal.SIGCHLD, signal.SIG_IGN); '
                               'os.execv(sys.argv[1], sys.argv[1:])',
                               *self.command(sys.executable, '-c', 'raise SystemExit(19)')],
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(launcher.communicate(timeout=4), (b'', b''))
        self.assert_finished(launcher, 19)

    def test_missing_executable_is_private_failure_with_cleanup_receipt(self):
        wrapper = self.launch(self.command(str(self.root / 'missing-private-executable')),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
        self.assert_finished(wrapper, 125)
        self.assertNotIn('missing-private-executable', self.metadata.read_text())

    def test_shell_forked_by_nonleader_thread_is_owned(self):
        command = self.tree()
        host = self.root / 'host.py'
        host.write_text('import subprocess,sys,threading,time\n'
                        'def run():\n'
                        '    subprocess.Popen(sys.argv[1:]).wait()\n'
                        'threading.Thread(target=run).start()\n'
                        'time.sleep(60)\n')
        wrapper = self.launch(self.command(sys.executable, str(host), *command),
                              stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        records = self.wait_tree()
        wrapper.terminate()
        self.assertEqual(wrapper.communicate(timeout=4), (b'', b''))
        self.assert_finished(wrapper, 143)
        self.assert_gone(records)

    def test_stale_identity_file_is_not_kill_authority(self):
        sentinel = self.launch([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.metadata.write_text(json.dumps({'pid': sentinel.pid, 'start_time': identity(sentinel.pid),
                                            'pi_pid': sentinel.pid, 'pi_start_time': 'stale',
                                            'cleanup_complete': True, 'exit_code': 0}))
        wrapper = self.launch(self.command(sys.executable, '-c', 'pass'))
        self.assert_finished(wrapper, 0)
        self.assertIsNone(sentinel.poll())

    def test_sibling_in_same_worker_group_survives_cleanup(self):
        sentinel_file = self.root / 'sentinel.pid'
        launcher_code = """import json, os, pathlib, subprocess, sys
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(60)'],
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
s = pathlib.Path('/proc/%d/stat' % p.pid).read_text().rsplit(')', 1)[1].split()[19]
pathlib.Path(sys.argv[1]).write_text(json.dumps([p.pid, s]))
raise SystemExit(subprocess.call(sys.argv[2:]))
"""
        launcher = self.launch([sys.executable, '-c', launcher_code, str(sentinel_file),
                                *self.command(sys.executable, '-c', 'import time; time.sleep(60)')],
                               stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        data = self.wait_for(self.metadata_ready)
        sentinel_pid, sentinel_start = json.loads(sentinel_file.read_text())
        self.assertEqual(os.getpgid(sentinel_pid), launcher.pid)
        self.assertEqual(os.getpgid(data['pid']), launcher.pid)
        fd = os.pidfd_open(data['pid'])
        try:
            self.assertEqual(identity(data['pid']), data['start_time'])
            signal.pidfd_send_signal(fd, signal.SIGTERM)
        finally:
            os.close(fd)
        self.assertEqual(launcher.communicate(timeout=4), (b'', b''))
        self.assertEqual(launcher.returncode, 143)
        self.assertTrue(json.loads(self.metadata.read_text())['cleanup_complete'])
        self.assertEqual(identity(sentinel_pid), sentinel_start)
        self.assert_gone([(data['pi_pid'], data['pi_start_time'])])

    def test_stale_start_ticks_cannot_pin_a_live_pid(self):
        self.assertTrue(WRAPPER.exists(), 'process supervisor has not been implemented')
        spec = importlib.util.spec_from_file_location('pi_process', WRAPPER)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        sentinel = self.launch([sys.executable, '-c', 'import time; time.sleep(60)'])
        self.assertIsNone(module._pin(sentinel.pid, 'stale'))
        self.assertIsNone(sentinel.poll())


if __name__ == '__main__':
    unittest.main()
