"""TaskStore's public read boundary, using real local Git commits."""
from dataclasses import FrozenInstanceError
import hashlib
from pathlib import Path
import os
import shutil
import subprocess
import tempfile
import unittest

from task_store import TaskStore, StoreError, Kind, Ownership, LiveAuthorization


FIXTURE = Path(__file__).parent / 'fixtures' / 'task_store'


class TaskStoreTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        shutil.copytree(FIXTURE, self.repo, dirs_exist_ok=True)
        self.git('init', '-q')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('config', 'user.name', 'Fixture')
        self.rev = self.commit()
        self.path = self.repo / 'tasks/items/T-1.md'
        self.original = self.path.read_text()

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def commit(self):
        self.git('add', '.')
        self.git('commit', '-qm', 'fixture')
        return self.git('rev-parse', 'HEAD')

    def load_edit(self, text):
        self.path.write_text(text)
        return TaskStore.at(self.repo, self.commit()).tasks['T-1']

    def test_reads_the_pinned_commit_not_the_worktree(self):
        self.path.write_text('not even TOML')
        store = TaskStore.at(self.repo, self.rev)
        task = store.tasks['T-1']
        self.assertEqual((store.rev, task.title, task.depends_on),
                         (self.rev, 'Read tasks', ()))
        self.assertEqual((store.goals['G-1'].priority, store.goals['G-1'].focus), (1, True))
        self.assertTrue(task.runnable)
        self.assertEqual(task.record_revision, hashlib.sha256(
            (FIXTURE / 'tasks/items/T-1.md').read_bytes()).hexdigest())
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').rev, self.rev)
        with self.assertRaises(FrozenInstanceError):
            task.title = 'mutated'
        with self.assertRaises(TypeError):
            store.tasks['other'] = task
        self.assertIsInstance(task.checks, tuple)
        self.load_edit(self.original.replace('title = "Read tasks"', 'title = "Later"'))
        self.git('replace', self.rev, self.git('rev-parse', 'HEAD'))
        self.assertEqual(TaskStore.at(self.repo, self.rev).tasks['T-1'].title, 'Read tasks')

    def test_uncommitted_edit_is_pending(self):
        index = self.repo / '.git/index'
        before = index.read_bytes()
        stat = self.path.stat()
        os.utime(self.path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 2_000_000_000))
        with self.subTest(read_only_index=True):
            self.assertEqual(TaskStore.pending(self.repo), ())
            self.assertEqual(index.read_bytes(), before, 'pending must not refresh the index')
        self.path.write_text('malformed draft')
        added = self.repo / 'tasks/items/untracked.md'
        added.write_text('also malformed')
        self.git('mv', 'tasks/goals/G-1.md', 'tasks/goals/renamed.md')
        (self.repo / 'unrelated.txt').write_text('not a task')
        self.assertEqual(TaskStore.pending(self.repo),
                         ('tasks/goals/G-1.md', 'tasks/goals/renamed.md',
                          'tasks/items/T-1.md', 'tasks/items/untracked.md'))
        self.assertEqual(set(TaskStore.at(self.repo, self.rev).tasks), {'T-1'})
        self.git('mv', 'tasks/goals/renamed.md', 'outside.md')
        expected = ('outside.md', 'tasks/goals/G-1.md', 'tasks/items/T-1.md',
                    'tasks/items/untracked.md')
        with self.subTest(rename_out=True):
            self.assertEqual(TaskStore.pending(self.repo), expected)
        self.commit()
        self.git('mv', 'outside.md', 'tasks/goals/G-1.md')
        self.assertEqual(TaskStore.pending(self.repo), ('outside.md', 'tasks/goals/G-1.md'))

    def test_contract_hash_ignores_rank_and_title(self):
        base = TaskStore.at(self.repo, self.rev).tasks['T-1']
        edits = (
            ('rank = 1', 'rank = 8', False),
            ('title = "Read tasks"', 'title = "New title"', False),
            ('short = "Read tasks"', 'short = "New short"', False),
            ('section = "Now"', 'section = "Next"', False),
            ('Free notes.', 'Different notes.', False),
            ('rank = 1', 'rank  =  1 # presentation only', False),
            ('acceptance = ["Pinned reads"]', 'acceptance = ["Other proof"]', True),
            ('checks = ["python3 -m unittest"]', 'checks = ["other command"]', True),
            ('touches = ["src/"]', 'touches = ["other/"]', True),
            ('scope = "Read only"', 'scope = "Read and write"', True),
            ('exclusions = []', 'exclusions = ["No writes"]', True),
            ('section = "Now"', 'section = "Needs decision"', True),
            ('status = "open"', 'status = "superseded"', True),
            ('ownership = "worker"', 'ownership = "owner"', True),
            ('kind = "implementation"', 'kind = "plan"', True),
            ('resources = []', 'resources = ["live"]', True),
            ('live = "denied"', 'live = "authorized"', True),
            ('depends_on = []', 'depends_on = ["T-1"]', True),
        )
        for before, after, changes in edits:
            with self.subTest(field=before):
                task = self.load_edit(self.original.replace(before, after))
                self.assertEqual(task.contract_hash != base.contract_hash, changes)
                self.assertNotEqual(task.record_revision, base.record_revision)

    def test_absent_authority_grants_nothing(self):
        text = self.original.replace('resources = []\n', '').replace('live = "denied"\n', '')
        task = self.load_edit(text)
        self.assertEqual(task.resources, ())
        self.assertEqual(task.live, LiveAuthorization.DENIED)
        self.assertFalse(task.runnable)
        task = self.load_edit(self.original.replace('live = "denied"\n', '')
                              .replace('resources = []', 'resources = ["live"]'))
        self.assertFalse(task.runnable)
        task = self.load_edit(self.original.replace('kind = "implementation"\n', '')
                              .replace('ownership = "worker"\n', ''))
        self.assertEqual((task.kind, task.ownership), (Kind.UNKNOWN, Ownership.UNKNOWN))
        self.assertFalse(task.runnable)
        task = self.load_edit(self.original.replace('resources = []', 'resources = ["live"]')
                              .replace('live = "denied"', 'live = "authorized"'))
        self.assertTrue(task.runnable)

    def test_corrupt_store_fails_closed(self):
        corruptions = (
            ('schema = 1', 'schema = 99'),
            ('schema = 1\n', ''),
            ('schema = 1', 'schema = true'),
            ('rank = 1', 'rank = ['),
            ('rank = 1', 'rank = ' + '9' * 5000),
            ('goal = "G-1"', 'goal = "unknown"'),
            ('kind = "implementation"', 'kind = "magic"'),
            ('ownership = "worker"', 'ownership = "anybody"'),
            ('live = "denied"', 'live = true'),
            ('resources = []', 'resources = "live"'),
            ('checks = ["python3 -m unittest"]', 'checks = [false]'),
            ('section = "Now"', 'section = "Soon"'),
        )
        for before, after in corruptions:
            with self.subTest(field=before, value=after[:80]):
                self.path.write_text(self.original.replace(before, after))
                rev = self.commit()
                with self.assertRaisesRegex(StoreError, r'tasks/items/T-1.md:\d+:'):
                    TaskStore.at(self.repo, rev)
        self.path.write_text(self.original)
        duplicate = self.repo / 'tasks/items/duplicate.md'
        duplicate.write_text(self.original)
        with self.assertRaisesRegex(StoreError, r'tasks/items/duplicate.md:\d+:.*duplicate ID'):
            TaskStore.at(self.repo, self.commit())
        duplicate.unlink()
        for directory in ('tasks', 'tasks/items', 'tasks/goals', 'tasks/items/T-1.md'):
            with self.subTest(symlink=directory):
                target, saved = self.repo / directory, self.repo / 'saved'
                shutil.move(target, saved)
                target.symlink_to(self.repo / 'missing')
                try:
                    with self.assertRaisesRegex(StoreError, rf'{directory}:\d+:'):
                        TaskStore.at(self.repo, self.commit())
                finally:
                    target.unlink()
                    shutil.move(saved, target)

    def test_draft_is_visible_not_runnable(self):
        task = self.load_edit(self.original.replace('acceptance = ["Pinned reads"]\n', ''))
        self.assertTrue(task.draft)
        self.assertIn('acceptance', task.missing_fields)
        self.assertFalse(task.runnable)


if __name__ == '__main__':
    unittest.main()
