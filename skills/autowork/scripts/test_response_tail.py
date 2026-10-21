import tempfile
import unittest
from pathlib import Path
from audit_profiles import cron_responses


class ResponseTailTests(unittest.TestCase):
    @staticmethod
    def native_output(response, prompt='saved output\n## Response\n\nOLD RESULT'):
        return ('# Cron Job: Fixture\n\n**Job ID:** j1\n**Run Time:** 2026-10-16 03:00:00\n'
                '**Schedule:** every 15m\n\n**Prompt Characters:** ' + str(len(prompt)) +
                '\n## Prompt\n\n' + prompt + '\n\n**Response Characters:** ' +
                str(len(response)) + '\n## Response\n\n' + response + '\n')

    def test_native_frame_preserves_opening_blocker_and_embedded_heading(self):
        from audit_profiles import safe
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-16.md'
            response = 'BLOCKED: aprobación pendiente 🚦\n\n## Response\n\nQuoted example\ntoken=private-value'
            for prompt in ('small prompt', 'prompt 🚦\n' * 5000):
                with self.subTest(large_prompt=len(prompt) > 32768):
                    path.write_text(self.native_output(response, prompt))
                    before = path.read_bytes()
                    gaps = []
                    row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
                    self.assertEqual(row['payload'], safe(response))
                    self.assertEqual(row['bytes_observed'], len(before))
                    self.assertEqual(row['remaining_bytes'], 0)
                    self.assertIn('validated native character frame', row['boundary'])
                    self.assertNotIn('private-value', row['payload'])
                    self.assertEqual(gaps, [])
                    self.assertEqual(path.read_bytes(), before)

    def test_invalid_or_oversized_native_frame_never_guesses_a_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-16.md'
            text = self.native_output('BLOCKED\n\n## Response\n\nQuoted example')
            for value in (text[:-2], text.replace('**Job ID:** j1', '**Job ID:** other'),
                          text.replace('**Prompt Characters:**', '**Unknown Characters:**'),
                          text.replace('**Response Characters:** ' + str(len('BLOCKED\n\n## Response\n\nQuoted example')),
                                       '**Response Characters:** 999'),
                          self.native_output('result', 'x' * (256 * 1024))):
                with self.subTest(size=len(value)):
                    path.write_text(value)
                    before = path.read_bytes()
                    gaps = []
                    self.assertEqual(cron_responses(home, [{'id': 'j1'}], gaps), [])
                    self.assertTrue(any('native response' in gap for gap in gaps), gaps)
                    self.assertEqual(path.read_bytes(), before)

    def test_damaged_newest_frame_keeps_two_prior_responses_and_actual_ranks(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            for day in (10, 11):
                (output / f'2026-10-{day}.md').write_text(self.native_output(f'result {day}'))
            (output / '2026-10-12.md').write_text(self.native_output('interrupted')[:-2])
            before = {p: p.read_bytes() for p in output.iterdir()}
            gaps = []
            rows = cron_responses(home, [{'id': 'j1'}], gaps)
            self.assertEqual([r['payload'] for r in rows], ['result 10', 'result 11'])
            self.assertEqual([r['output_rank'] for r in rows], [3, 2])
            self.assertEqual([r['latest'] for r in rows], [False, False])
            self.assertEqual(gaps, ['native response frame invalid: j1'])
            self.assertEqual(before, {p: p.read_bytes() for p in output.iterdir()})

    def test_response_lookback_stops_at_twelve_candidates(self):
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            oldest = output / '2026-10-01.md'
            oldest.write_text(self.native_output('outside bound'))
            for day in range(2, 14):
                (output / f'2026-10-{day:02}.md').write_text('# Cron Job: interrupted\n')
            opened = []
            original_open = Path.open
            def open_output(path, *args, **kwargs):
                opened.append(path)
                return original_open(path, *args, **kwargs)
            gaps = []
            with patch.object(Path, 'open', open_output):
                self.assertEqual(cron_responses(home, [{'id': 'j1'}], gaps), [])
            self.assertEqual(len(opened), 12)
            self.assertNotIn(oldest, opened)
            self.assertIn('cron response lookback exhausted: j1; older files uninspected', gaps)

    def test_native_response_display_is_bounded_after_redaction(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            response = 'BLOCKED\n' + 'detail\n' * 6000
            (output / '2026-10-16.md').write_text(self.native_output(response))
            gaps = []
            row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
            self.assertTrue(row['payload'].startswith('BLOCKED\n'))
            self.assertLessEqual(len(row['payload']), 32850)
            self.assertIn('RESPONSE TAIL OMITTED', row['payload'])
            self.assertIn('native response display truncated: j1', gaps)

    def test_http_header_credentials_are_masked_through_line_end(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-16.md'
            headers = ('Cookie: first=one; second=private-tail',
                       'Authorization: Bearer first, custom=private-tail',
                       'Set-Cookie: first=one; second=private-tail',
                       'Proxy-Authorization: Digest first=one, second=private-tail',
                       '\tCoOkIe:\tfirst=one; second=private-tail')
            for header in headers:
                response = 'status: held\n' + header + '\nchecks: pending'
                for text in (self.native_output(response), '## Response\n\n' + response):
                    with self.subTest(header=header.split(':')[0], native=text.startswith('# Cron')):
                        path.write_text(text)
                        before = path.read_bytes()
                        gaps = []
                        row = cron_responses(home, [{'id': 'j1'}], gaps)[0]
                        self.assertNotIn('private-tail', row['payload'])
                        self.assertIn('status: held', row['payload'])
                        self.assertIn('checks: pending', row['payload'])
                        self.assertEqual(gaps, [])
                        self.assertEqual(path.read_bytes(), before)

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

    def test_json_projection_preserves_existing_context_and_opaque_masking(self):
        import json
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            opaque = '7' * 64
            cases = [{key: 'synthetic-private-value', 'status': 'held'}
                     for key in ('access_token', 'refresh_token', 'db_password')]
            cases += [{'value': int(opaque), 'status': 'held'}, [int(opaque), 'held']]
            for case in cases:
                with self.subTest(case_kind=type(case).__name__):
                    path.write_text(json.dumps(case))
                    before = path.read_bytes()
                    row = cron_responses(home, [{'id': 'j1'}], [])[0]
                    self.assertNotIn('synthetic-private-value', row['payload'])
                    self.assertNotIn(opaque, row['payload'])
                    self.assertIn('held', row['payload'])
                    self.assertEqual(path.read_bytes(), before)

    def test_json_object_keys_keep_existing_secret_masking(self):
        import json
        from audit_profiles import safe
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            path = output / '2026-10-11.md'
            for key in ('ghp_syntheticPrivateCredential', 'https://example.test/private', 'x' * 64):
                with self.subTest(key_kind=len(key)):
                    path.write_text(json.dumps({key: 'held', 'ordinary': 'diagnostic'}))
                    before = path.read_bytes()
                    row = cron_responses(home, [{'id': 'j1'}], [])[0]
                    self.assertNotIn(key, row['payload'])
                    self.assertEqual(json.loads(row['payload']), {safe(key): 'held', 'ordinary': 'diagnostic'})
                    self.assertEqual(path.read_bytes(), before)

    def test_deep_json_response_is_withheld_without_losing_other_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output/j1'
            output.mkdir(parents=True)
            deep = output / '2026-10-11.md'
            healthy = output / '2026-10-12.md'
            healthy.write_text('healthy response\n')
            for depth in (600, 1200):
                with self.subTest(depth=depth):
                    deep.write_text('[' * depth + '{"password":"synthetic-private-value"}' + ']' * depth)
                    before = deep.read_bytes()
                    rows = cron_responses(home, [{'id': 'j1'}], [])
                    self.assertEqual(len(rows), 2)
                    self.assertNotIn('synthetic-private-value', rows[0]['payload'])
                    self.assertEqual(rows[1]['payload'], 'healthy response\n')
                    self.assertEqual(deep.read_bytes(), before)

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
                    self.assertEqual([row['path'] for row in rows], [str(paths[0]), str(healthy)])
                    self.assertEqual([row['output_rank'] for row in rows], [3, rank])
                    self.assertEqual(rows[1]['latest'], rank == 1)
                    self.assertEqual(rows[1]['payload'], healthy.name + '\n')
                    self.assertIn('exact execution association not proved', rows[1]['boundary'])
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

    def test_in_profile_output_alias_cannot_impersonate_another_job(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            output = home / 'cron/output'
            actual = output / 'actual'
            actual.mkdir(parents=True)
            source = actual / '2026-10-11.md'
            source.write_text('another job result\n')
            (output / 'alias').symlink_to('actual', target_is_directory=True)
            gaps = []
            rows = cron_responses(home, [{'id': 'alias'}, {'id': 'actual'}], gaps)
            self.assertEqual([row['job_id'] for row in rows], ['actual'])
            self.assertIn('cron response directory aliased: alias', gaps)
            self.assertEqual(source.read_text(), 'another job result\n')

    def test_aliased_output_parent_cannot_supply_job_responses(self):
        with tempfile.TemporaryDirectory() as tmp:
            home = Path(tmp)
            actual = home / 'retained/j1'
            actual.mkdir(parents=True)
            source = actual / '2026-10-11.md'
            source.write_text('retained result\n')
            (home / 'cron').mkdir()
            (home / 'cron/output').symlink_to('../retained', target_is_directory=True)
            gaps = []
            self.assertEqual(cron_responses(home, [{'id': 'j1'}], gaps), [])
            self.assertIn('cron response directory aliased: j1', gaps)
            self.assertEqual(source.read_text(), 'retained result\n')

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
