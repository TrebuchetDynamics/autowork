"""Repeated plugin loads preserve owners and handle concurrent publication."""
import errno
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('native_provisioning', ROOT / 'install_skills.py')
assert spec is not None and spec.loader is not None
provisioning = importlib.util.module_from_spec(spec)
spec.loader.exec_module(provisioning)


class ProvisioningTests(unittest.TestCase):
    def test_concurrent_complete_winner_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'

            def publish_winner(staged, destination):
                destination.mkdir()
                (destination / 'SKILL.md').write_text('concurrent winner')
                raise OSError(errno.ENOTEMPTY, 'destination published concurrently')

            with patch.object(provisioning, '_publish', publish_winner):
                result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 0)
            self.assertEqual((target / 'SKILL.md').read_text(), 'concurrent winner')
            self.assertEqual(sorted(p.name for p in target.parent.iterdir()), ['example'])

    def test_empty_slot_created_during_publication_is_not_replaced(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'
            publish = provisioning._publish
            original_inode = []

            def create_slot_then_publish(staged, destination):
                destination.mkdir()
                original_inode.append(destination.stat().st_ino)
                return publish(staged, destination)

            with patch.object(provisioning, '_publish', create_slot_then_publish):
                result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 1)
            self.assertEqual(target.stat().st_ino, original_inode[0])
            self.assertEqual(list(target.iterdir()), [])

    def test_invalid_existing_slot_fails_without_overwriting(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / 'source'
            skill = source / 'example'
            skill.mkdir(parents=True)
            (skill / 'SKILL.md').write_text('bundled skill')
            home = root / 'home'
            target = home / 'skills/example'
            target.mkdir(parents=True)
            (target / 'owner-note').write_text('keep me')
            result = provisioning.install(source, [('owner', home)], report=lambda message: None)
            self.assertEqual(result, 1)
            self.assertEqual((target / 'owner-note').read_text(), 'keep me')
            self.assertFalse((target / 'SKILL.md').exists())


if __name__ == '__main__':
    unittest.main()
