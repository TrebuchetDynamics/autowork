"""A toolset update goes only to a release that reads current state, preferably fleet-idle."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

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
            old, new = base / 'hermes-toolset', base / 'autowork'
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
            self.assertEqual(listing(('git:github.com/TrebuchetDynamics/hermes-toolset', old),
                                     ('git:github.com/TrebuchetDynamics/autowork (filtered)', new)),
                             str(new.resolve()))
            self.assertEqual(listing(('npm:other', base), ('git:github.com/TrebuchetDynamics/hermes-toolset', old)),
                             str(old.resolve()))
            self.assertIsNone(listing(('npm:other', base)))

if __name__ == '__main__':
    unittest.main()
