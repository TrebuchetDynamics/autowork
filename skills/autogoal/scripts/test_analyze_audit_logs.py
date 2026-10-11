import json
from pathlib import Path
import tempfile
import unittest
from analyze_audit_logs import analyze


class LogAnalysisTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / 'maintenance/collector'
        directory.mkdir(parents=True)
        row = {'profile': 'sample', 'logs': [{'file': 'agent.log', 'identity': [1, 2],
               'start': 0, 'cursor': 100, 'bytes_observed': 100, 'sha256': 'a' * 64,
               'payload': 'INFO startup\nERROR admission refused token=secret-value\n[PARTIAL LAST LINE REDACTED]\n',
               'remaining_bytes': 250, 'history_gaps': ['unknown history']}]}
        path = directory / 'receipt-one.json'
        path.write_text(json.dumps({'schema': 'fleet-audit/v1', 'profiles': [row]}))
        return directory, path

    def test_analysis_deduplicates_and_does_not_change_receipts_or_cursors(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, path = self.fixture(root)
            state = root / 'maintenance/analysis'
            before = path.read_bytes()
            first = analyze(root, [directory], state, 10)
            self.assertEqual(first['new_chunks'], 1)
            self.assertEqual(first['new_chunk_bytes'], 100)
            self.assertEqual(first['profiles']['sample']['signals']['error'], 1)
            self.assertEqual(first['profiles']['sample']['redacted_lines'], 1)
            self.assertNotIn('secret-value', json.dumps(first))
            self.assertEqual(first['semantic_review'], 'not_performed')
            self.assertEqual(first['profiles']['sample']['latest_unread_bytes'], 250)
            self.assertEqual(path.read_bytes(), before)
            second = analyze(root, [directory], state, 10)
            self.assertEqual(second['new_chunks'], 0)
            self.assertEqual(second['profiles']['sample']['signals']['error'], 1)
            self.assertEqual(Path(second['report']).stat().st_mode & 0o777, 0o600)

    def test_chunk_budget_and_write_boundary(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory, _ = self.fixture(root)
            result = analyze(root, [directory], root / 'maintenance/analysis', 0)
            self.assertEqual(result['new_chunks'], 0)
            self.assertEqual(result['pending_chunks'], 1)
            with self.assertRaises(ValueError):
                analyze(root, [directory], root / 'profiles/sample/logs', 1)
            with self.assertRaises(ValueError):
                analyze(root, [root.parent], root / 'maintenance/analysis', 1)


if __name__ == '__main__':
    unittest.main()
