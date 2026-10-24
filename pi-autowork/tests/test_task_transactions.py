"""Task command transactions against a real checkout, without services or models."""
from concurrent.futures import ThreadPoolExecutor, TimeoutError
import json
import multiprocessing
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import threading
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / 'pi-autowork'))
from pi_autowork import task_commands as commands  # noqa: E402


def interrupt_batch(repo, action, phase):
    """Bypass cleanup during writing, rollback, or just before the commit point."""
    replace, rename, link, unlink = os.replace, os.rename, os.link, Path.unlink

    def die_after_replace(source, target):
        replace(source, target)
        if Path(target).suffix == '.md':
            if phase == 'exit':
                os._exit(23)
            if phase in ('undo_exit', 'restore_exit'):
                raise KeyboardInterrupt('start rollback')

    def die_after_claim(source, target):
        rename(source, target)
        if phase == 'undo_exit':
            os._exit(23)

    def die_after_restore(source, target):
        link(source, target)
        if phase == 'restore_exit':
            os._exit(23)

    def die_before_commit(path, *args, **kwargs):
        if phase == 'commit_exit' and path.name == 'autowork-tasks.transaction':
            os._exit(23)
        return unlink(path, *args, **kwargs)

    with patch.object(commands.os, 'replace', die_after_replace), \
            patch.object(commands.os, 'rename', die_after_claim), \
            patch.object(commands.os, 'link', die_after_restore), \
            patch.object(Path, 'unlink', die_before_commit):
        action(repo)


def change_title(repo):
    commands.cmd_field(repo, 'T-1', 'title', 'pending')


def move(repo):
    commands.cmd_move(repo, 'T-3', 'up')


def focus(repo):
    commands.cmd_goal(repo, 'G-2', focus=True)


def add_focused_goal(repo):
    commands.cmd_goal(repo, 'G-3', title='Three', source='docs/plan.md', priority=3, focus=True)


class TaskTransactionTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.repo = Path(tmp.name) / 'repo'
        shutil.copytree(ROOT / 'pi-autowork/engine/fixtures/task_store', self.repo)
        for args in (('init', '-q'), ('add', '-A'), ('commit', '-qm', 'fixture')):
            subprocess.run(['git', '-C', str(self.repo), '-c', 'user.name=Fixture',
                            '-c', 'user.email=fixture@example.invalid', *args], check=True,
                           capture_output=True)

    def records(self):
        return {p.relative_to(self.repo): p.read_bytes() for p in (self.repo / 'tasks').glob('*/*.md')}

    def test_concurrent_commands_keep_both_notes(self):
        # Without a lock covering read-modify-write, Alpha reads before Beta and
        # either overwrites Beta or is spuriously refused after Beta succeeds.
        paused, release, started = threading.Event(), threading.Event(), threading.Event()
        set_note = commands.task_store.set_note

        def pause_alpha(text, label, value):
            if label == 'Alpha':
                paused.set()
                if not release.wait(10):
                    raise AssertionError('writer was not released')
            return set_note(text, label, value)

        def edit_beta():
            started.set()
            commands.cmd_field(self.repo, 'T-1', 'Beta', 'two')

        with patch.object(commands.task_store, 'set_note', pause_alpha), ThreadPoolExecutor(2) as pool:
            first = pool.submit(commands.cmd_field, self.repo, 'T-1', 'Alpha', 'one')
            try:
                self.assertTrue(paused.wait(10))
                second = pool.submit(edit_beta)
                self.assertTrue(started.wait(10))
                try:
                    second.result(timeout=0.3)
                except TimeoutError:
                    pass  # a serialized writer must wait until Alpha releases the lock
            finally:
                release.set()
            first.result(timeout=10)
            second.result(timeout=10)
        body = commands.worktree_store(self.repo).tasks['T-1'].body
        self.assertIn('- Alpha: one', body)
        self.assertIn('- Beta: two', body)

    def test_validation_rollback_preserves_external_bytes(self):
        # An editor that does not take our lock must not lose its bytes to undo.
        path = self.repo / 'tasks/items/T-1.md'
        original = path.read_bytes()
        external = original + b'\n- External: keep this edit\n'
        newer = original + b'\n- External: a second edit\n'
        read_store, contents = commands.worktree_store, commands._contents
        restore = commands._restore_missing
        for moment in ('validation', 'undo', 'restore', 'linked_restart'):
            with self.subTest(moment=moment):
                path.write_bytes(original)
                if moment == 'linked_restart':
                    child = multiprocessing.get_context('spawn').Process(
                        target=interrupt_batch, args=(self.repo, change_title, 'restore_exit'))
                    child.start()
                    child.join(15)
                    if child.is_alive():
                        child.kill()
                        child.join()
                    self.assertEqual(child.exitcode, 23)
                    path.write_bytes(external)  # also changes the surviving staging hard link
                    with self.assertRaises(commands.CommandError):
                        commands.cmd_validate(self.repo, worktree=True)
                    self.assertEqual(path.read_bytes(), external)
                    continue

                def reject_our_edit(repo):
                    if b'goal = "NOPE"' in path.read_bytes():
                        if moment == 'validation':
                            path.write_bytes(external)
                        raise commands.StoreError('injected validation failure')
                    return read_store(repo)

                def edit_after_undo_read(target):
                    data = contents(target)
                    if moment != 'validation' and target == path and b'goal = "NOPE"' in (data or b''):
                        path.write_bytes(external)
                    return data

                def recreate_before_restore(target, source):
                    if moment == 'restore' and target == path:
                        path.write_bytes(newer)
                    return restore(target, source)

                with patch.object(commands, 'worktree_store', reject_our_edit), \
                        patch.object(commands, '_contents', edit_after_undo_read), \
                        patch.object(commands, '_restore_missing', recreate_before_restore):
                    with self.assertRaises(commands.CommandError) as error:
                        commands.cmd_field(self.repo, 'T-1', 'goal', 'NOPE')
                self.assertEqual(path.read_bytes(), newer if moment == 'restore' else external)
                if moment == 'restore':
                    saved = commands._claimed_path(path)
                    self.assertEqual(saved.read_bytes(), external)
                    self.assertIn(str(saved.relative_to(self.repo)), str(error.exception))
                    saved.unlink()  # this fixture has inspected/reconciled the displaced edit
                self.assertIn('- External:', read_store(self.repo).tasks['T-1'].body)

    def test_delete_validation_failure_restores_the_record(self):
        path = self.repo / 'tasks/items/T-1.md'
        before = path.read_bytes()
        real = commands.worktree_store

        def reject_after_delete(repo):
            if not path.exists():
                raise commands.StoreError('injected after deletion')
            return real(repo)

        with patch.object(commands, 'worktree_store', reject_after_delete):
            with self.assertRaises(commands.CommandError):
                commands.cmd_delete(self.repo, 'T-1')
        self.assertEqual(path.read_bytes(), before)
        self.assertEqual(commands.worktree_store(self.repo).tasks['T-1'].title, 'Read tasks')

    def test_an_interrupted_delete_journal_restores_the_record(self):
        path = self.repo / 'tasks/items/T-1.md'
        before = path.read_bytes()
        git_dir = Path(commands._git(self.repo, 'rev-parse', '--absolute-git-dir'))
        journal = git_dir / 'autowork-tasks.transaction'
        journal.write_text(json.dumps([['tasks/items/T-1.md', before.hex(), None]]))
        path.unlink()
        commands.cmd_validate(self.repo, worktree=True)
        self.assertEqual(path.read_bytes(), before)
        self.assertFalse(journal.exists())

    def test_interrupted_batches_restore_the_whole_set(self):
        # Per-file writes leave partial ranks/focus after exceptions or process death.
        commands.cmd_goal(self.repo, 'G-2', title='Two', source='docs/plan.md', priority=2)
        for tid in ('T-2', 'T-3', 'T-4'):
            commands.cmd_add(self.repo, 'G-1', tid, tid, task_id=tid)
        for tid, rank in (('T-1', 1), ('T-2', 2), ('T-3', 3), ('T-4', 5000)):
            commands.cmd_field(self.repo, tid, 'rank', str(rank))
        for action in (move, focus, add_focused_goal):
            for failure in ('exception', 'exit', 'undo_exit', 'commit_exit'):
                with self.subTest(action=action.__name__, failure=failure):
                    before = self.records()
                    if failure != 'exception':
                        child = multiprocessing.get_context('spawn').Process(
                            target=interrupt_batch, args=(self.repo, action, failure))
                        child.start()
                        child.join(15)
                        if child.is_alive():
                            child.kill()
                            child.join()
                        self.assertEqual(child.exitcode, 23)
                    else:
                        replace = os.replace
                        interrupted = False

                        def fail_once(source, target):
                            nonlocal interrupted
                            replace(source, target)
                            if Path(target).suffix == '.md' and not interrupted:
                                interrupted = True
                                raise KeyboardInterrupt('between files')

                        with patch.object(commands.os, 'replace', fail_once):
                            with self.assertRaises(KeyboardInterrupt):
                                action(self.repo)
                        self.assertEqual(self.records(), before)
                    commands.cmd_validate(self.repo, worktree=True)  # recovers a dead writer
                    self.assertEqual(self.records(), before)
        move(self.repo)
        store = commands.worktree_store(self.repo)
        self.assertEqual(sorted(store.tasks, key=lambda tid: store.tasks[tid].rank),
                         ['T-1', 'T-3', 'T-2', 'T-4'])
        focus(self.repo)
        self.assertEqual([g.id for g in commands.worktree_store(self.repo).goals.values() if g.focus], ['G-2'])
        add_focused_goal(self.repo)
        self.assertEqual([g.id for g in commands.worktree_store(self.repo).goals.values() if g.focus], ['G-3'])


if __name__ == '__main__':
    unittest.main()
