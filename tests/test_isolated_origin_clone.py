"""Real-Git regression for delivery clones with shallow local references."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'skills/git-pull-merge/scripts/isolated-origin-clone.py'

class IsolatedOriginCloneTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.origin = self.root / 'origin'
        self.git('init', '-b', 'main', str(self.origin))
        self.git('-C', str(self.origin), 'config', 'user.name', 'Fixture')
        self.git('-C', str(self.origin), 'config', 'user.email', 'fixture@example.invalid')
        for value in ('first', 'second'):
            (self.origin / 'payload').write_text(value)
            self.git('-C', str(self.origin), 'add', 'payload')
            self.git('-C', str(self.origin), 'commit', '-m', value)
        self.sha = self.git('-C', str(self.origin), 'rev-parse', 'HEAD').stdout.strip()
        self.shallow = self.root / 'shallow reference'
        self.git('clone', '--depth', '1', self.origin.as_uri(), str(self.shallow))

    def git(self, *args):
        return subprocess.run(['git', '-c', 'core.hooksPath=/dev/null', *args], capture_output=True, text=True, check=True)

    def invoke(self, destination, expected=None, env=None):
        return subprocess.run([sys.executable, str(HELPER), self.origin.as_uri(), str(destination), '--expected-main', expected or self.sha], capture_output=True, text=True, env=env)

    def test_shallow_reference_failure_is_avoided_without_borrowed_objects(self):
        old = subprocess.run(['git', 'clone', '--reference', str(self.shallow), self.origin.as_uri(), str(self.root / 'old')], capture_output=True, text=True)
        self.assertNotEqual(old.returncode, 0)
        self.assertIn('shallow', old.stderr.lower())
        result = self.invoke(self.root / 'new clone')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['origin_main'], self.sha)
        self.assertEqual(self.git('-C', str(self.root / 'new clone'), 'rev-list', '--count', 'HEAD').stdout.strip(), '2')
        self.assertFalse((self.root / 'new clone/.git/objects/info/alternates').exists())

    def test_existing_destination_is_never_modified(self):
        destination = self.root / 'existing'
        destination.mkdir()
        marker = destination / 'owner'
        marker.write_bytes(b'preserve')
        result = self.invoke(destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('already exists', result.stderr)
        self.assertEqual(marker.read_bytes(), b'preserve')
        self.assertEqual(list(destination.iterdir()), [marker])

    def test_dangling_symlink_is_never_replaced(self):
        destination = self.root / 'linked'
        destination.symlink_to(self.root / 'missing', target_is_directory=True)
        result = self.invoke(destination)
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(destination.is_symlink())

    def test_changed_origin_pin_holds_without_integration_or_deletion(self):
        destination = self.root / 'changed'
        result = self.invoke(destination, expected='0' * 40)
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('clone held', result.stderr)
        self.assertEqual((destination / 'payload').read_text(), 'second')

    def test_malformed_pin_is_rejected_before_clone(self):
        destination = self.root / 'invalid'
        result = self.invoke(destination, expected='HEAD')
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(destination.exists())

    def test_foreign_shallow_selector_cannot_truncate_history(self):
        foreign = self.shallow / '.git/shallow'
        original = foreign.read_bytes()
        env = dict(os.environ, GIT_SHALLOW_FILE=str(foreign))
        destination = self.root / 'full history'
        result = self.invoke(destination, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.git('-C', str(destination), 'rev-list', '--count', 'HEAD').stdout.strip(), '2')
        self.git('-C', str(destination), 'fsck', '--full')
        self.assertFalse((destination / '.git/shallow').exists())
        self.assertFalse((destination / '.git/objects/info/alternates').exists())
        self.assertEqual(foreign.read_bytes(), original)

    def test_inherited_repository_selectors_do_not_redirect_clone(self):
        env = os.environ.copy()
        env.update(GIT_DIR=str(self.shallow / '.git'), GIT_WORK_TREE=str(self.shallow),
                   GIT_INDEX_FILE=str(self.root / 'foreign-index'),
                   GIT_OBJECT_DIRECTORY=str(self.shallow / '.git/objects'),
                   GIT_ALTERNATE_OBJECT_DIRECTORIES=str(self.origin / '.git/objects'))
        destination = self.root / 'isolated'
        result = self.invoke(destination, env=env)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['origin_main'], self.sha)
        self.assertFalse((self.root / 'foreign-index').exists())
        self.assertEqual(self.git('-C', str(self.shallow), 'rev-parse', '--is-shallow-repository').stdout.strip(), 'true')

if __name__ == '__main__':
    unittest.main()
