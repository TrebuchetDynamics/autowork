import fcntl
import importlib.util
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('migrate_autowork', Path(__file__).resolve().parents[1] / 'scripts/migrate-autowork.py')
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


class MigrationTests(unittest.TestCase):
    def test_preview_and_apply_preserve_receipts_and_lock_inode(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); old = home / migration.LEGACY; old.mkdir()
            receipt = old / 'goal-handoff.json'; receipt.write_text('{"task_id":"existing"}')
            lock = old / 'goal-handoff.lock'; lock.touch(); inode = lock.stat().st_ino
            self.assertEqual(migration.migrate_state(home), 'would_migrate')
            self.assertFalse((home / 'autowork').exists())
            self.assertEqual(migration.migrate_state(home, True), 'migrated')
            self.assertEqual((home / 'autowork/goal-handoff.json').read_bytes(), receipt.read_bytes())
            self.assertEqual((home / 'autowork/goal-handoff.lock').stat().st_ino, inode)
            self.assertEqual(migration.migrate_state(home, True), 'already_migrated')

    def test_conflicting_store_and_busy_writer_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); old = home / migration.LEGACY; old.mkdir()
            (home / 'autowork').mkdir()
            with self.assertRaises(ValueError): migration.migrate_state(home, True)
            (home / 'autowork').rmdir()
            with (old / '.owner-cycle.lock').open('w') as lock:
                fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
                with self.assertRaises(BlockingIOError): migration.migrate_state(home, True)
            self.assertFalse((home / 'autowork').exists())

    def test_unexpected_symlink_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            home = Path(directory); (home / migration.LEGACY).symlink_to(home)
            with self.assertRaises(ValueError): migration.migrate_state(home, True)
