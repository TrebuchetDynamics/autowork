import tempfile
import unittest
from pathlib import Path
from audit_profiles import cron_responses


class ResponseTailTests(unittest.TestCase):
    def test_ready_status_keeps_full_preparation_in_private_receipt(self):
        import owner_cycle
        result = {'outcome': 'QUEUED', 'selected_task': {'id': 'T1'},
                  'dispatch_attempted': True, 'next_action': 'Observe original native card',
                  'handoff': {'result': {'task_id': 'original', 'contract': 'large private input'}},
                  'recovery': {'stages': ['private source history']}}
        status = owner_cycle.compact(result, '/private/state')
        self.assertEqual(status['native_card'], 'original')
        self.assertEqual(status['completed_tasks'], [])
        self.assertNotIn('recovery', status)
        self.assertNotIn('handoff', status)
        self.assertEqual(status['receipt'], '/private/state/unblock-latest.json')

    def test_two_newest_outputs_retained_without_mutating_sources(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            paths = [output / f'2026-10-{day}.md' for day in (10, 11, 12)]
            for path in paths:
                path.write_text('prompt filler\n' * 5000 + '\nResponse: ' + path.name + '\ntoken=private-value\n')
            (output / '2026-10-13.md').symlink_to(paths[0])
            before = {path: path.read_bytes() for path in paths}
            gaps = []
            rows = cron_responses(home, [{'id': 'j1'}], gaps)
            self.assertEqual([row['path'] for row in rows], list(map(str, paths[-2:])))
            self.assertEqual([row['output_rank'] for row in rows], [2, 1])
            self.assertEqual([row['latest'] for row in rows], [False, True])
            for row in rows:
                self.assertEqual(row['job_id'], 'j1')
                self.assertEqual(row['bytes_observed'], 32768)
                self.assertIn(Path(row['path']).name, row['payload'])
                self.assertNotIn('private-value', row['payload'])
                self.assertIn('filename order', row['boundary'])
                self.assertIn('exact execution association not proved', row['boundary'])
            self.assertEqual(before, {path: path.read_bytes() for path in paths})

    def test_symlinked_output_directory_cannot_supply_foreign_responses(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            home = root / 'profile'
            output = home / 'cron/output'
            output.mkdir(parents=True)
            foreign = root / 'foreign'
            foreign.mkdir()
            (foreign / '2026-10-11.md').write_text('foreign owner response\n')
            (output / 'j1').symlink_to(foreign, target_is_directory=True)
            gaps = []
            self.assertEqual(cron_responses(home, [{'id': 'j1'}], gaps), [])
            self.assertIn('cron response directory outside profile: j1', gaps)

    def test_one_output_and_missing_job_keep_compatibility(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            path.write_bytes(b'one output\n')
            gaps = []
            rows = cron_responses(home, [{'id': 'j1'}, {'id': 'missing'}], gaps)
            self.assertEqual(len(rows), 1)
            self.assertEqual(rows[0]['path'], str(path))
            self.assertEqual(rows[0]['payload'], 'one output\n')
            self.assertEqual(rows[0]['output_rank'], 1)
            self.assertTrue(rows[0]['latest'])
            self.assertEqual(gaps, ['cron response missing: missing'])
            self.assertEqual(path.read_bytes(), b'one output\n')

    def test_large_prompt_does_not_hide_response_and_boundary_is_explicit(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            path.write_text('# Prompt\n' + 'prompt filler\n' * 5000 + '\n## Response\n\nHELD: canonical ledger missing\ntoken=private-value\n')
            before = path.read_bytes()
            gaps = []
            row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
            self.assertIn('HELD: canonical ledger missing', row['payload'])
            self.assertNotIn('private-value', row['payload'])
            self.assertEqual(row['start'], len(before) - 32768)
            self.assertEqual(row['remaining_bytes'], row['start'])
            self.assertEqual(row['bytes_observed'], 32768)
            self.assertIn('cron response truncated: j1', gaps)
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
