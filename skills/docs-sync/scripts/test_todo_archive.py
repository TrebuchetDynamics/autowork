"""Lossless completed-task archival through the actual docs-sync CLI."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

import goals

SCRIPT = Path(goals.__file__)


class TodoArchiveTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.repo = Path(temporary.name)
        self.todo = self.repo / 'TODO.md'
        self.archive = self.repo / 'TODO.archive.md'
        self.ledger = self.repo / 'goals.json'
        self.done = '- [x] T1: Completed slice\n  Checks: fixture passed\n  Evidence: keep `exact bytes`\n\n'
        self.open = '- [ ] T2: Independent work\n  Scope: keep this entire body\n\n'
        self.todo.write_text('# TODO\n\n## Now\n\n' + self.open + '## Done\n\n' + self.done)
        self.data = {'version': 1, 'goals': [
            {'id': 'G', 'title': 'Outcome', 'source': 'SPEC.md', 'status': 'partial',
             'tasks': ['T1', 'T2'], 'evidence': []}], 'tasks': [
            {'id': 'T1', 'goal': 'G', 'title': 'Completed slice', 'status': 'done', 'section': 'Done'},
            {'id': 'T2', 'goal': 'G', 'title': 'Independent work', 'status': 'open', 'section': 'Now'}]}
        self.ledger.write_text(json.dumps(self.data))

    def cli(self, command, *args, expected=0):
        result = subprocess.run([sys.executable, str(SCRIPT), command, str(self.repo), *args],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, expected, result.stdout + result.stderr)
        return result

    def test_render_automatically_moves_completed_bodies_and_keeps_ledger(self):
        ledger = self.ledger.read_bytes()
        self.cli('render')
        self.assertNotIn(self.done, self.todo.read_text())
        self.assertIn(self.open, self.todo.read_text())
        self.assertIn(self.done, self.archive.read_text())
        self.assertIn('TODO.archive.md', self.todo.read_text())
        self.assertEqual(self.ledger.read_bytes(), ledger)
        before = (self.todo.read_bytes(), self.archive.read_bytes())
        self.cli('render')
        self.cli('archive')
        self.assertEqual((self.todo.read_bytes(), self.archive.read_bytes()), before)

    def test_archive_reuses_existing_owner_and_preserves_crlf_bytes(self):
        for name in ('todo.archive.md', 'docs/TODO-archive.md', 'docs/completed.md'):
            with self.subTest(name=name):
                archive = self.repo / name
                archive.parent.mkdir(exist_ok=True)
                old = b'# Existing history\r\n\r\nPrivate fixture wording stays here.\r\n'
                archive.write_bytes(old)
                done = self.done.replace('\n', '\r\n').encode()
                live = self.open.replace('\n', '\r\n').encode()
                self.todo.write_bytes(f'# TODO\r\n\r\n[History]({name})\r\n\r\n## Now\r\n'.encode() +
                                      live + b'## Done\r\n' + done)
                self.cli('render')
                self.assertTrue(archive.read_bytes().startswith(old))
                self.assertIn(done, archive.read_bytes())
                self.assertIn(live, self.todo.read_bytes())
                self.assertNotIn(done, self.todo.read_bytes())
                self.assertFalse(self.archive.exists())
                archive.unlink()

    def test_reopened_and_unverified_tasks_stay_live(self):
        self.todo.write_text('# TODO\n\n## Now\n' + self.open +
                             self.done.replace('[x]', '[ ]') +
                             '- [x] T3: No ledger record\n  Checks: claimed pass\n')
        before = self.todo.read_bytes()
        self.cli('archive')
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_task_source_links_cannot_select_or_conflict_with_archive_owner(self):
        for linked in (False, True):
            with self.subTest(linked=linked):
                owner = self.repo / ('docs/completed.md' if linked else 'TODO.archive.md')
                owner.parent.mkdir(exist_ok=True)
                owner.write_text('# Existing history\n')
                reference = self.repo / 'docs/todo-archive.md'
                reference.parent.mkdir(exist_ok=True)
                reference.write_text('# Archive contract; keep unchanged\n')
                source = ('  Sources: [archive contract](docs/todo-archive.md), '
                          '[archive regression tests](test_archive.py)\n\n')
                done, active = self.done + source, self.open + source
                navigation = '[History](docs/completed.md)\n\n' if linked else ''
                self.todo.write_text('# TODO\n\n' + navigation + '## Now\n' + active +
                                     '## Done\n' + done)
                result = json.loads(self.cli('archive').stdout)
                self.assertEqual(result['archive'], owner.relative_to(self.repo).as_posix())
                self.assertIn(done, owner.read_text())
                self.assertIn(active, self.todo.read_text())
                self.assertEqual(reference.read_text(), '# Archive contract; keep unchanged\n')
                self.assertFalse((self.repo / 'test_archive.py').exists())
                stable = (self.todo.read_bytes(), owner.read_bytes())
                self.cli('archive')
                self.assertEqual((self.todo.read_bytes(), owner.read_bytes()), stable)
                owner.unlink()

    def test_closed_checkbox_cannot_override_open_ledger_or_open_subtask(self):
        for body in (self.open.replace('[ ]', '[x]'),
                     self.done + '  - [ ] remaining qualification\n'):
            with self.subTest(body=body):
                self.todo.write_text('# TODO\n\n## Done\n' + body)
                before = self.todo.read_bytes()
                self.cli('archive')
                self.assertEqual(self.todo.read_bytes(), before)
                self.assertFalse(self.archive.exists())

    def test_fenced_examples_and_generated_coverage_are_not_archived(self):
        text = ('# TODO\n\n```md\n' + self.done + '```\n\n' + goals.BEGIN + '\n' +
                self.done + goals.END + '\n\n## Now\n' + self.open)
        self.todo.write_text(text)
        self.cli('archive')
        self.assertEqual(self.todo.read_text(), text)
        self.assertFalse(self.archive.exists())

    def test_generated_coverage_without_heading_stays_in_live_todo(self):
        coverage = goals.BEGIN + '\nKeep this generated region live.\n' + goals.END + '\n'
        self.todo.write_text(self.todo.read_text() + coverage)
        self.cli('archive')
        self.assertIn(coverage, self.todo.read_text())
        self.assertNotIn(coverage, self.archive.read_text())
        self.assertIn(self.done, self.archive.read_text())

    def test_matching_heading_and_checkbox_move_as_one_complete_unit(self):
        for newline in ('\n', '\r\n'):
            with self.subTest(newline=newline):
                done = ('### T1 — Completed slice\n\n' + self.done +
                        '#### Evidence\n\n```md\n- [ ] EXAMPLE\n```\n\n').replace('\n', newline).encode()
                self.todo.write_bytes(b'# TODO\n\n## Done\n' + done + b'## Now\n' + self.open.encode())
                ledger = self.ledger.read_bytes()
                result = json.loads(self.cli('archive').stdout)
                self.assertEqual(result['moved'], ['T1'])
                self.assertEqual(result['retained'], [])
                self.assertNotIn(b'### T1', self.todo.read_bytes())
                self.assertEqual(self.archive.read_bytes().count(done), 1)
                self.assertIn(self.open.encode(), self.todo.read_bytes())
                self.assertEqual(self.ledger.read_bytes(), ledger)
                self.cli('render')
                stable = (self.todo.read_bytes(), self.archive.read_bytes())
                self.cli('archive')
                self.cli('render')
                self.assertEqual((self.todo.read_bytes(), self.archive.read_bytes()), stable)
                self.archive.unlink()

    def test_heading_checkbox_conflicts_remain_whole_and_live(self):
        for heading, body in (
                ('T1', self.done.replace('[x]', '[ ]')),
                ('T1', self.done + '- Status: open\n'),
                ('T1', self.done + '#### Acceptance\n\n  - [ ] pending\n'),
                ('T2', self.done),
                ('UNKNOWN', self.done)):
            with self.subTest(heading=heading, body=body):
                text = '# TODO\n\n## Done\n### ' + heading + ' — Task\n\n' + body
                self.todo.write_text(text)
                result = json.loads(self.cli('archive').stdout)
                self.assertEqual(self.todo.read_text(), text)
                self.assertFalse(self.archive.exists())
                self.assertEqual(result['moved'], [])

    def test_matching_unit_retry_and_verified_legacy_archive(self):
        self.ledger.unlink()
        done = '### T1 — Completed slice\n\n' + self.done
        self.todo.write_text('# TODO\n\n## Done\n' + done + '## Now\n' + self.open)
        # Simulate an archive-first interruption with the entire unit present.
        self.archive.write_text('# History\n\n' + done)
        history = self.archive.read_bytes()
        self.cli('archive', '--verified-tasks', 'T1')
        self.assertEqual(self.archive.read_bytes(), history)
        self.assertNotIn('### T1', self.todo.read_text())
        stable = self.todo.read_bytes()
        self.cli('archive', '--verified-tasks', 'T1')
        self.assertEqual(self.todo.read_bytes(), stable)
        self.assertEqual(self.archive.read_bytes(), history)

    def test_multiple_checkboxes_and_intervening_metadata_are_ambiguous(self):
        for body in (self.done + self.done,
                     '- Status: open\n\n' + self.done,
                     '<!-- owner note stays live -->\n\n' + self.done):
            with self.subTest(body=body):
                text = '# TODO\n\n## Done\n### T1 — Completed slice\n\n' + body
                self.todo.write_text(text)
                self.cli('archive')
                self.assertEqual(self.todo.read_text(), text)
                self.assertFalse(self.archive.exists())

    def test_heading_task_preserves_nested_sections_and_fenced_receipts(self):
        done = ('### T1 — Completed slice\n\n- Status: done (offline scope).\n'
                '- Checks: fixture passed.\n\n#### Evidence\n\n```md\n'
                '- [ ] NOT-A-TASK\n```\n\n')
        self.todo.write_text('# TODO\n\n## Done\n\n' + done + '### T2 — Still open\n\n- Status: open\n')
        self.cli('archive')
        self.assertIn(done, self.archive.read_text())
        self.assertNotIn(done, self.todo.read_text())
        self.assertIn('### T2 — Still open\n\n- Status: open\n', self.todo.read_text())

    def test_checkbox_continuation_includes_nested_evidence_headings(self):
        done = self.done + '#### Evidence\n\nA complete receipt stays with T1.\n\n'
        self.todo.write_text('# TODO\n\n## Done\n' + done + '## Now\n' + self.open)
        self.cli('archive')
        self.assertIn(done, self.archive.read_text())
        self.assertNotIn('A complete receipt', self.todo.read_text())
        self.assertIn(self.open, self.todo.read_text())

    def test_sibling_group_heading_after_a_done_task_stays_in_live_todo(self):
        done = self.done + '#### Evidence\n\nA receipt stays with T1.\n\n'
        self.todo.write_text('# TODO\n\n## Now\n\n### Core work\n\n' + done +
                             '### Later group\n\n' + self.open)
        self.cli('archive')
        self.assertIn(done, self.archive.read_text())
        self.assertNotIn('Later group', self.archive.read_text())
        self.assertEqual(self.todo.read_text().count('### Later group\n\n' + self.open), 1)

    def test_unchecked_qualification_after_nested_heading_prevents_archival(self):
        for heading in ('#### Evidence', '#### Evidence: test results', '#### Evidence — test results'):
            with self.subTest(heading=heading):
                done = self.done + heading + '\n\nA receipt\n\n  - [ ] pending qualification\n'
                self.todo.write_text('# TODO\n\n## Done\n' + done)
                before = self.todo.read_bytes()
                result = self.cli('archive')
                self.assertEqual(self.todo.read_bytes(), before)
                self.assertFalse(self.archive.exists())
                self.assertEqual(json.loads(result.stdout)['retained'], ['T1'])

    def test_nested_archive_has_rebased_references_outside_original_block(self):
        archive = self.repo / 'docs/TODO-archive.md'
        archive.parent.mkdir()
        archive.write_text('# History\n')
        (self.repo / 'SPEC.md').write_text('# Accepted\n')
        done = self.done + '  Sources: [Proof](SPEC.md#accepted) and [External](https://example.invalid/proof)\n'
        self.todo.write_text('# TODO\n\n## Done\n' + done)
        self.cli('archive')
        history = archive.read_text()
        self.assertIn(done, history)
        self.assertIn('[Proof](../SPEC.md#accepted)', history.replace(done, ''))
        self.assertEqual(history.count('https://example.invalid/proof'), 1)

    def test_no_ledger_requires_explicit_verified_ids_for_legacy_tasks(self):
        self.ledger.unlink()
        done = '### T1 — Complete\n\n- Status: done (local only).\n- Checks: fixture passed.\n\n'
        self.todo.write_text('# TODO\n\n## Done\n\n' + done + self.open)
        before = self.todo.read_bytes()
        self.cli('archive')
        self.assertEqual(self.todo.read_bytes(), before)
        self.cli('archive', '--verified-tasks', 'T1')
        self.assertIn(done, self.archive.read_text())
        self.assertIn(self.open, self.todo.read_text())
        self.assertFalse(self.ledger.exists())
        before = (self.todo.read_bytes(), self.archive.read_bytes())
        self.cli('archive', '--verified-tasks', 'T1')
        self.assertEqual((self.todo.read_bytes(), self.archive.read_bytes()), before)

    def test_nested_task_headings_are_retained_as_an_ambiguous_unit(self):
        self.data['tasks'][1]['status'] = 'done'
        self.ledger.write_text(json.dumps(self.data))
        self.todo.write_text('# TODO\n\n## Done\n\n### T1 — Parent\n\n- Status: done\n\n'
                             '#### T2 — Child\n\n- Status: done\n\n')
        before = self.todo.read_bytes()
        self.cli('archive')
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_unknown_heading_task_is_not_absorbed_by_a_completed_checkbox(self):
        for metadata in ('- Status: done\n', '- Status: open\n', '- Status: in_progress\n',
                         '- Scope: New work\n- Acceptance: feature passes\n', ''):
            with self.subTest(metadata=metadata):
                unknown = '### T3 — Unreconciled task\n\n' + metadata
                self.todo.write_text('# TODO\n\n## Done\n' + self.done + unknown)
                before = self.todo.read_bytes()
                self.cli('archive')
                self.assertEqual(self.todo.read_bytes(), before)
                self.assertFalse(self.archive.exists())

    def test_repeated_source_blocks_preserve_multiplicity(self):
        self.todo.write_text('# TODO\n\n## Done\n' + self.done * 2)
        self.cli('archive')
        self.assertEqual(self.archive.read_text().count(self.done), 2)
        self.assertNotIn(self.done, self.todo.read_text())

    def test_interrupted_move_retries_without_duplicating_archive(self):
        original_write = goals.atomic_write
        before = self.todo.read_bytes()
        def interrupted(path, text, **kwargs):
            if path.name == 'TODO.md':
                raise OSError('simulated interruption after archival')
            return original_write(path, text, **kwargs)
        with goals.coordination(self.repo), patch.object(goals, 'atomic_write', side_effect=interrupted):
            with self.assertRaisesRegex(OSError, 'simulated interruption'):
                goals.render(self.repo, goals.normalize(self.data))
        self.assertEqual(self.todo.read_bytes(), before)
        archive = self.archive.read_bytes()
        self.cli('render')
        self.assertEqual(self.archive.read_bytes(), archive)
        self.assertNotIn(self.done, self.todo.read_text())

    def test_archive_failure_never_removes_source(self):
        self.archive.symlink_to(self.repo / 'elsewhere.md')
        before = self.todo.read_bytes()
        result = self.cli('render', expected=1)
        self.assertIn('symlink', result.stderr)
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertFalse((self.repo / 'elsewhere.md').exists())

    def test_read_only_commands_never_archive(self):
        before = self.todo.read_bytes()
        for command in ('validate', 'next', 'revision'):
            self.cli(command)
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_invalid_coverage_refuses_before_archiving(self):
        self.todo.write_text(self.todo.read_text() + '\n' + goals.BEGIN + '\n')
        before = self.todo.read_bytes()
        self.cli('render', expected=1)
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertFalse(self.archive.exists())

    def test_concurrent_todo_edit_is_retained_after_archive_write(self):
        original_write = goals.atomic_write
        before = self.todo.read_bytes()
        def concurrent(path, text, **kwargs):
            result = original_write(path, text, **kwargs)
            if path == self.archive:
                self.todo.write_bytes(before + b'Owner continuation\n')
            return result
        with goals.coordination(self.repo), patch.object(goals, 'atomic_write', side_effect=concurrent):
            with self.assertRaisesRegex(SystemExit, 'stale write'):
                goals.render(self.repo, goals.normalize(self.data))
        self.assertEqual(self.todo.read_bytes(), before + b'Owner continuation\n')
        self.assertIn(self.done, self.archive.read_text())

    def test_concurrent_archive_append_is_preserved_without_removing_source(self):
        original_write = goals.atomic_write
        before = self.todo.read_bytes()
        def concurrent(path, text, **kwargs):
            result = original_write(path, text, **kwargs)
            if path == self.archive:
                with path.open('ab') as stream:
                    stream.write(b'Other writer history\n')
            return result
        with goals.coordination(self.repo), patch.object(goals, 'atomic_write', side_effect=concurrent):
            with self.assertRaisesRegex(SystemExit, 'archive verification failed'):
                goals.render(self.repo, goals.normalize(self.data))
        self.assertEqual(self.todo.read_bytes(), before)
        archive = self.archive.read_bytes()
        self.cli('archive')
        self.assertEqual(self.archive.read_bytes(), archive)
        self.assertNotIn(self.done, self.todo.read_text())

    def test_archive_changed_before_replace_is_not_overwritten(self):
        self.archive.write_text('# Existing history\n')
        before = self.todo.read_bytes()
        original_replace = goals.os.fsync
        def concurrent(fd):
            with self.archive.open('ab') as stream:
                stream.write(b'Other writer history\n')
            return original_replace(fd)
        with goals.coordination(self.repo), patch.object(goals.os, 'fsync', side_effect=concurrent):
            with self.assertRaisesRegex(SystemExit, 'file changed during command'):
                goals.render(self.repo, goals.normalize(self.data))
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertEqual(self.archive.read_text(), '# Existing history\nOther writer history\n')

    def test_existing_owner_conflicts_and_symlink_parents_refuse_safely(self):
        (self.repo / 'todo.archive.md').write_text('# Legacy\n')
        self.archive.write_text('# New\n')
        before = self.todo.read_bytes()
        self.cli('archive', expected=1)
        self.assertEqual(self.todo.read_bytes(), before)
        self.assertEqual(self.archive.read_text(), '# New\n')
        with tempfile.TemporaryDirectory() as external:
            (self.repo / 'history').symlink_to(external, target_is_directory=True)
            self.todo.write_text('[History](history/archive.md)\n\n' + before.decode())
            current = self.todo.read_bytes()
            self.cli('archive', expected=1)
            self.assertEqual(self.todo.read_bytes(), current)
            self.assertEqual(list(Path(external).iterdir()), [])


if __name__ == '__main__':
    unittest.main()
