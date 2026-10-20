"""A toolset update goes only to a release that reads current state, preferably fleet-idle."""
import json
import os
from pathlib import Path
import shlex
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import release  # noqa: E402

STATE = 'skills/autowork/scripts/parallel_state.py'


class ReleaseCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        self.origin, self.toolset, self.work = root / 'origin.git', root / 'toolset', root / 'work'
        self.state_root, self.own = root / 'state', root / 'state' / 'own'
        self.own.mkdir(parents=True)
        self.git(root, 'init', '-q', '--bare', '-b', 'main', str(self.origin))
        self.git(root, 'clone', '-q', str(self.origin), str(self.work))
        self.publish('STATE_SCHEMA = 1\nSTATE_SCHEMA_READS = (1,)\n', 'release 1')
        self.git(root, 'clone', '-q', str(self.origin), str(self.toolset))

    def git(self, cwd, *args):
        subprocess.run(['git', '-C', str(cwd), '-c', 'user.email=f@example.invalid', '-c', 'user.name=F', *args],
                       check=True, capture_output=True)

    def publish(self, text, message):
        path = self.work / STATE
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text)
        self.git(self.work, 'add', '-A')
        self.git(self.work, 'commit', '-qm', message)
        self.git(self.work, 'push', '-q', 'origin', 'HEAD:main')

    def check(self):
        return release.check(self.state_root, self.own, self.toolset)

    def runner(self, name, in_flight, pid):
        folder = self.state_root / name
        folder.mkdir()
        (folder / 'runner.json').write_text(json.dumps({'pid': pid, 'repo': '/x/' + name}))
        (folder / 'status.json').write_text(json.dumps({'in_flight': in_flight}))

    def test_late_imports_keep_the_selected_release_while_unused_releases_are_pruned(self):
        for name, text in {'first.py': 'def run():\n    from second import old_api\n    return old_api\n',
                           'second.py': 'old_api = 1\n'}.items():
            (self.work / name).write_text(text)
        self.publish('STATE_SCHEMA = 1\n', 'old API')
        self.git(self.toolset, 'pull', '-q', '--ff-only')
        selected = release.prepare(self.state_root, self.toolset)
        child = subprocess.Popen([sys.executable, '-u', '-c',
                                  'import sys; sys.path.insert(0, sys.argv[1]); '
                                  'import first; print("ready", flush=True); input(); '
                                  'print(first.run())', str(selected)],
                                 env=dict(os.environ, PI_AUTOWORK_TOOLSET=str(selected)),
                                 stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        self.addCleanup(lambda: child.poll() is None and (child.kill(), child.wait()))
        self.assertEqual(child.stdout.readline().strip(), 'ready')
        for number in range(2, 5):
            (self.work / 'first.py').write_text('from second import new_api\n')
            (self.work / 'second.py').write_text(f'new_api = {number}\n')
            self.publish(f'STATE_SCHEMA = 1\n# {number}\n', f'release {number}')
            self.git(self.toolset, 'pull', '-q', '--ff-only')
            latest = release.prepare(self.state_root, self.toolset)
        self.assertTrue(selected.is_dir())  # a live child's old release is not pruned
        out, err = child.communicate('\n', timeout=10)
        self.assertEqual((child.returncode, out.strip()), (0, '1'), err)
        release.prepare(self.state_root, self.toolset)
        self.assertFalse(selected.exists())
        self.assertTrue(latest.is_dir())
        self.assertEqual(len(list((self.state_root / 'releases').glob('*/'))), 2)

    def test_legacy_driver_pins_a_stopped_runners_release_until_registration_moves(self):
        # Isolate driver references from live-process retention on a busy host.
        glob = Path.glob
        self.enterContext(patch.object(Path, 'glob', lambda path, pattern:
            iter(()) if path == Path('/proc') else glob(path, pattern)))
        selected = release.prepare(self.state_root, self.toolset)
        (self.own / 'status.json').write_text(json.dumps({'repo': str(self.work)}))
        key = 'merge.docs-sync-archive.driver'
        self.git(self.work, 'config', '--local', key,
                 f'{shlex.quote(sys.executable)} '
                 f'{shlex.quote(str(selected / "skills/docs-sync/scripts/goals.py"))} '
                 'merge-driver archive %O %A %B')
        for number in (2, 3):
            self.publish(f'STATE_SCHEMA = 1\n# {number}\n', f'release {number}')
            self.git(self.toolset, 'pull', '-q', '--ff-only')
            release.prepare(self.state_root, self.toolset)
        self.assertTrue(selected.is_dir(), 'Git still names this release even though its runner stopped')
        self.git(self.work, 'config', '--local', key,
                 f'{shlex.quote(sys.executable)} '
                 f'{shlex.quote(str(self.toolset / "skills/docs-sync/scripts/goals.py"))} '
                 'merge-driver archive %O %A %B')
        release.prepare(self.state_root, self.toolset)
        self.assertFalse(selected.exists(), 'a replaced registration must no longer pin the old release')

    def test_status_does_not_create_or_prune_release_worktrees(self):
        cli = self.toolset / 'pi-autowork/pi_autowork/cli.py'
        cli.parent.mkdir(parents=True)
        cli.write_text('print("STATUS fixture")\n')
        before = subprocess.check_output(['git', '-C', str(self.toolset), 'worktree', 'list', '--porcelain'])
        env = dict(os.environ, PYTHONPATH=str(Path(release.__file__).resolve().parents[1]),
                   PI_AUTOWORK_PACKAGE=str(self.toolset), PI_AUTOWORK_TOOLSET=str(self.toolset),
                   PI_AUTOWORK_RESELECT='', PI_AUTOWORK_STATE_DIR=str(self.state_root),
                   PI_AUTOWORK_ENV_DIR=str(self.state_root / 'settings'))
        result = subprocess.run([sys.executable, '-c',
                                 'from pi_autowork import release; import sys; '
                                 'release.launch(sys.argv[1], sys.argv[2], ["--status", "--repo", sys.argv[3]])',
                                 str(cli.parent.parent), str(self.toolset / 'scripts/pi-autowork.sh'), str(self.work)],
                                env=env, text=True, capture_output=True, timeout=30)
        self.assertFalse((self.state_root / 'releases').exists(), 'a read-only status created release state')
        self.assertEqual(subprocess.check_output(['git', '-C', str(self.toolset), 'worktree', 'list', '--porcelain']), before)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stdout.strip(), 'STATUS fixture')

    def test_a_compatible_release_may_be_installed(self):
        self.assertEqual(self.check(), dict(ok=False, current=True, reason='already at the newest release'))
        self.publish('STATE_SCHEMA = 2\nSTATE_SCHEMA_READS = (1, 2)\n', 'release 2 reads 1')
        result = self.check()
        self.assertTrue(result['ok'], result)
        self.assertEqual(result['schema'], 1)
        self.assertEqual((self.toolset / STATE).read_text(), 'STATE_SCHEMA = 1\nSTATE_SCHEMA_READS = (1,)\n')  # untouched

    def test_a_release_that_cannot_read_this_state_is_refused(self):
        self.publish('STATE_SCHEMA = 2\nSTATE_SCHEMA_READS = (2,)\n', 'release 2 only')
        result = self.check()
        self.assertFalse(result['ok'])
        self.assertIn('cannot read this state (schema 1; it reads [2])', result['reason'])

    def test_fetched_declarations_are_parsed_never_executed(self):
        self.publish("STATE_SCHEMA_READS = __import__('os').system('touch pwned')\n", 'hostile')
        self.assertEqual(self.check()['reason'], 'could not read the state schema declarations')
        self.assertFalse(Path('pwned').exists())

    def test_another_runner_with_work_in_flight_defers_the_update(self):
        self.publish('STATE_SCHEMA = 1\nSTATE_SCHEMA_READS = (1,)\n# 2\n', 'release 2')
        self.runner('idle', 0, os.getpid())
        self.runner('gone', 3, 2 ** 22 + 11)  # a dead runner's record does not count
        self.assertTrue(self.check()['ok'])
        self.runner('sierra', 2, os.getpid())
        result = release.check(self.state_root, self.own, self.toolset, wait=1800, now=1000.0)
        self.assertFalse(result['ok'])
        self.assertRegex(result['reason'], r'^other runners have work in flight: sierra \(2 in flight\); '
                                           r'updating to \w+ anyway in 30 min$')
        # Four always-busy runners never reach a checkpoint: once the wait from the first
        # sighting (shared by every runner) is over, the update goes ahead anyway.
        self.assertFalse(release.check(self.state_root, self.own, self.toolset, wait=1800, now=2700.0)['ok'])
        result = release.check(self.state_root, self.own, self.toolset, wait=1800, now=2801.0)
        self.assertTrue(result['ok'], result)
        self.assertIn('with work in flight (sierra (2 in flight))', result['note'])



class InstalledToolsetTests(unittest.TestCase):
    """The runner runs from the package installed under the Autowork name when Pi has several."""
    def test_the_renamed_package_wins_over_an_earlier_listed_copy(self):
        from pi_autowork import cli
        with tempfile.TemporaryDirectory() as folder:
            base = Path(folder).resolve()
            old, new = base / 'old-toolset', base / 'autowork'
            for copy in (old, new):
                for name in ('skills/autowork/scripts/owner_cycle.py', 'skills/docs-sync/scripts/goals.py'):
                    (copy / name).parent.mkdir(parents=True, exist_ok=True)
                    (copy / name).touch()
            pi = base / 'pi'

            def listing(*rows):
                pi.write_text('#!/usr/bin/env bash\necho "User packages:"\n'
                              + ''.join(f'echo "  {src}"\necho "    {path}"\n' for src, path in rows))
                pi.chmod(0o755)
                return cli.installed_toolset(str(pi))
            self.assertEqual(listing(('git:github.com/TrebuchetDynamics/old-toolset', old),
                                     ('git:github.com/TrebuchetDynamics/autowork (filtered)', new)),
                             str(new.resolve()))
            self.assertEqual(listing(('npm:other', base), ('git:github.com/TrebuchetDynamics/old-toolset', old)),
                             str(old.resolve()))
            self.assertIsNone(listing(('npm:other', base)))

if __name__ == '__main__':
    unittest.main()
