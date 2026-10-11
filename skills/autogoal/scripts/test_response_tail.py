import tempfile
import unittest
from pathlib import Path
from audit_profiles import cron_responses


class ResponseTailTests(unittest.TestCase):
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
