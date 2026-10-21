"""A merge never lands a close under a contract no one verified (TOOLSET-302-33 (2)).

One side closes a task (its receipt pins the contract it verified); the other changes the
task's acceptance. Git merges both cleanly; the runner, not the resolver's prompt, reopens it.
"""
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
import store_fixture  # noqa: E402
import task_queue  # noqa: E402
import task_store  # noqa: E402
from test_landing import LandingFixture  # noqa: E402

TODO = '- [ ] T — Port the tuner\n  Scope: port it\n  Acceptance: the tuner builds\n  Checks: true\n'


class ReopenTests(LandingFixture):
    def setUp(self):
        super().setUp()
        for where in (self.repo, self.integ):
            self.git(where, 'config', 'user.name', 'T')
            self.git(where, 'config', 'user.email', 't@example.invalid')
        store_fixture.write_todo(self.repo, TODO)
        self.git(self.integ, 'merge', '-q', '--no-edit', 'main')
        self.runner.integration = None
        self.runner.toolset = str(Path(__file__).resolve().parents[2])
        self.runner.state = self.repo.parent / 'state'
        self.runner.state.mkdir()
        self.runner.seen, self.runner.stop, self.runner.resolved_for = {}, False, ''

    def close_on_session(self):
        """What a verified close commits: done, and a receipt pinning the contract it verified."""
        record = task_queue.store(self.integ).tasks['T']
        path = self.integ / 'tasks/items/T.md'
        path.write_text(task_store.edit(path.read_text(), {'status': 'done'}))
        receipt = self.integ / 'tasks/evidence/T.toml'
        receipt.parent.mkdir(parents=True, exist_ok=True)
        receipt.write_text(f'schema = 1\ntask = "T"\ncontract_hash = "{record.contract_hash}"\nresult = "pass"\n')
        self.git(self.integ, 'add', '-A')
        self.git(self.integ, 'commit', '-qm', 'docs(tasks): close T')

    def edit_on_main(self, changes):
        path = self.repo / 'tasks/items/T.md'
        path.write_text(task_store.edit(path.read_text(), changes))
        self.git(self.repo, 'commit', '-qam', 'owner edit')

    def test_done_with_a_changed_contract_is_reopened(self):
        self.close_on_session()
        self.edit_on_main({'acceptance': ['the tuner builds', 'and it runs on the device']})
        self.assertTrue(self.runner.merge_main(), self.runner.merge_pending)
        self.assertEqual(self.head('main'), self.head('pi-autowork/s'))
        merged = task_queue.store(self.repo, 'main').tasks['T']
        self.assertEqual(merged.status, 'open')
        self.assertEqual(merged.acceptance, ('the tuner builds', 'and it runs on the device'))
        reason = task_queue.notes(merged)['Reopened']
        self.assertIn('its contract changed after its verified close', reason)
        self.assertEqual(task_queue.stale_closures(self.repo, 'main'), [])
        log = self.git(self.repo, 'log', '--format=%s', '-3', 'main')
        self.assertIn('docs(tasks): reopen T (pi-autowork)', log)

    def test_refused_reopening_keeps_uncommitted_session_bookkeeping(self):
        note = self.integ / 'BLOCKERS.md'
        note.write_text('old question\n')
        self.git(self.integ, 'add', 'BLOCKERS.md')
        self.git(self.integ, 'commit', '-qm', 'old question')
        self.close_on_session()
        self.edit_on_main({'acceptance': ['changed after closure']})
        note.write_text('session question not committed yet\n')
        self.git(self.integ, 'add', 'BLOCKERS.md')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\necho "pre-commit: checks failed" >&2\nexit 1\n')
        hook.chmod(0o755)
        before = self.head('pi-autowork/s')
        self.assertFalse(self.runner.merge_main())
        self.assertIn('could not be reopened', self.runner.merge_pending)
        self.assertEqual(self.head('pi-autowork/s'), before)
        self.assertEqual(note.read_text(), 'session question not committed yet\n')

    def test_reopening_does_not_discard_an_uncommitted_task_note(self):
        self.close_on_session()
        self.edit_on_main({'acceptance': ['changed after closure']})
        self.git(self.integ, 'merge', '-q', '--no-edit', 'main')  # a retained stale close
        path = self.integ / 'tasks/items/T.md'
        edited = task_store.set_note(path.read_text(), 'Note', 'keep this session note')
        path.write_text(edited)
        self.git(self.repo, 'commit', '-q', '--allow-empty', '-m', 'main moved')
        hook = self.repo / '.git/hooks/pre-commit'
        hook.write_text('#!/bin/sh\nexit 1\n')
        hook.chmod(0o755)
        self.assertFalse(self.runner.merge_main())
        self.assertEqual(path.read_text(), edited)
        self.assertIn('could not be reopened', self.runner.merge_pending)

    def test_a_rank_edit_keeps_the_close(self):
        self.close_on_session()
        self.edit_on_main({'rank': 5000})  # priority is no contract: the verification still covers it
        self.assertTrue(self.runner.merge_main(), self.runner.merge_pending)
        self.assertEqual(task_queue.store(self.repo, 'main').tasks['T'].status, 'done')

    def test_a_close_without_a_receipt_is_not_reopened(self):
        path = self.integ / 'tasks/items/T.md'  # a person's close: its evidence note, no receipt
        path.write_text(task_store.set_note(task_store.edit(path.read_text(), {'status': 'done'}),
                                            'Evidence', 'checked by hand'))
        self.git(self.integ, 'commit', '-qam', 'close by hand')
        self.edit_on_main({'acceptance': ['changed']})
        self.assertTrue(self.runner.merge_main(), self.runner.merge_pending)
        self.assertEqual(task_queue.store(self.repo, 'main').tasks['T'].status, 'done')


if __name__ == '__main__':
    unittest.main()
