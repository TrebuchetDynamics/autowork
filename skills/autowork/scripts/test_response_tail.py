import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "tests/fixtures"))
import tempfile
import unittest
from pathlib import Path
from audit_profiles import cron_responses


class ResponseTailTests(unittest.TestCase):
    def test_quoted_credentials_are_masked_before_field_delimiters(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            values = ('first,private-tail', 'first;private-tail', 'first\nprivate-tail',
                      'first\\"private-tail', 'first\\\'private-tail')
            for key in ('api_key', 'token', 'password', 'secret', 'authorization', 'cookie'):
                for quote in ('"', "'"):
                    for value in values:
                        for closed in (True, False):
                            with self.subTest(key=key, quote=quote, value=value, closed=closed):
                                response = key + '=' + quote + value + (quote if closed else '')
                                path.write_text('## Response\n\nstatus: held\n' + response)
                                before = path.read_bytes()
                                row = cron_responses(home, [{'id': 'j1'}], [])[0]
                                self.assertNotIn('private-tail', row['payload'])
                                self.assertIn('status: held', row['payload'])
                                self.assertIn('[REDACTED]', row['payload'])
                                self.assertEqual(path.read_bytes(), before)

    def test_json_encoded_credentials_are_redacted_after_decoding(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            cases = ({'password': 'first,private-tail', 'status': 'held'},
                     {'message': 'password="first,private-tail"', 'status': 'held'},
                     {'message': json.dumps({'password': 'first,private-tail'}), 'status': 'held'})
            for case in cases:
                with self.subTest(case=case):
                    path.write_text('## Response\n\n' + json.dumps(case))
                    before = path.read_bytes()
                    row = cron_responses(home, [{'id': 'j1'}], [])[0]
                    self.assertNotIn('private-tail', row['payload'])
                    self.assertIn('held', row['payload'])
                    self.assertEqual(path.read_bytes(), before)

    def test_ready_status_keeps_full_preparation_in_private_receipt(self):
        import legacy_owner_cycle as owner_cycle
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

    def test_unreadable_output_does_not_hide_healthy_selected_output(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            paths = [output / f'2026-10-{day}.md' for day in (10, 11, 12)]
            for path in paths:
                path.write_text(path.name + '\n')
            before = {path: path.read_bytes() for path in paths}
            original_open = Path.open
            for failed, healthy, rank in ((paths[1], paths[2], 1), (paths[2], paths[1], 2)):
                with self.subTest(failed=failed.name):
                    def open_output(path, *args, **kwargs):
                        if path == failed:
                            raise OSError('deterministic unreadable output')
                        return original_open(path, *args, **kwargs)
                    gaps = []
                    with patch.object(Path, 'open', open_output):
                        rows = cron_responses(home, [{'id': 'j1'}], gaps)
                    self.assertEqual([row['path'] for row in rows], [str(healthy)])
                    self.assertEqual(rows[0]['output_rank'], rank)
                    self.assertEqual(rows[0]['latest'], rank == 1)
                    self.assertEqual(rows[0]['payload'], healthy.name + '\n')
                    self.assertIn('exact execution association not proved', rows[0]['boundary'])
                    self.assertEqual(gaps, ['cron response unreadable: j1: ' + failed.name])
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

    def test_looping_output_directory_does_not_abort_collection(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output'
            output.mkdir(parents=True)
            (output / 'j1').symlink_to('j1', target_is_directory=True)
            gaps = []
            self.assertEqual(cron_responses(home, [{'id': 'j1'}], gaps), [])
            self.assertIn('cron response directory unresolvable: j1', gaps)

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

    def test_current_response_excludes_prompt_and_embedded_earlier_response(self):
        import hashlib
        from audit_profiles import safe
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            response = 'HELD: current result\ntoken=private-value\nhttps://example.test/private\n'
            for prefix in ('', 'large prompt filler\n' * 5000):
                with self.subTest(truncated=bool(prefix)):
                    path.write_text('# Cron Job\n\n## Prompt\n\n' + prefix +
                                    'saved previous output\n## Response\n\nOLD RESULT\n' +
                                    'repeated user instructions\n## Response\n\n' + response)
                    before = path.read_bytes()
                    gaps = []
                    row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
                    self.assertEqual(row['payload'], safe(response))
                    self.assertEqual(row['start'], max(0, len(before) - 32768))
                    self.assertEqual(row['bytes_observed'], min(len(before), 32768))
                    self.assertEqual(row['remaining_bytes'], row['start'])
                    self.assertEqual(row['sha256'], hashlib.sha256(before[row['start']:]).hexdigest())
                    self.assertIn('last exact Response delimiter in observed tail', row['boundary'])
                    self.assertIn('full output coverage not proved', row['boundary'])
                    self.assertEqual(row['output_rank'], 1)
                    self.assertTrue(row['latest'])
                    self.assertEqual(path.read_bytes(), before)

    def test_missing_exact_response_delimiter_keeps_compatibility_tail(self):
        from audit_profiles import safe
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            cases = (
                '# Cron Job\n\n## Prompt\n\ninline ## Response\n\nnot a header\n',
                '## Response extra\n\nnot exact\ntoken=private-value\n',
                '## Response\nmissing blank line\n',
                '# Cron Job\n\n## Response\n\n' + 'long response\n' * 5000 + 'token=private-value\n',
                # The tail starts mid-line on a lookalike delimiter; it is not a header.
                'prefix## Response\n\n' + 'x\n' * 16377 + 'end\n',
            )
            for text in cases:
                with self.subTest(prefix=text[:40]):
                    path.write_text(text)
                    before = path.read_bytes()
                    tail = before[-32768:].decode()
                    if len(before) > 32768:
                        tail = '[EARLIER OUTPUT OMITTED; PARTIAL FIRST LINE REDACTED]\n' + tail.partition('\n')[2]
                    gaps = []
                    row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
                    self.assertEqual(row['payload'], safe(tail))
                    self.assertIn('Response delimiter absent from observed tail; compatibility tail only', row['boundary'])
                    self.assertIn('full output coverage not proved', row['boundary'])
                    self.assertEqual(row['analysis'], 'not_analyzed')
                    self.assertNotIn('private-value', row['payload'])
                    self.assertEqual(path.read_bytes(), before)

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
