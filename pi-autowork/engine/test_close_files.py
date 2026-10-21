"""The close file set stays importable from ``parallel_integrate``.

Two independent changes met at this name: an integration refactor moved the closeout
off the working copy and deleted the local ``close_files`` definition, while archive
reconciliation in the coordinator stages that file set through
``parallel_integrate.close_files``. Moving the helper to ``parallel_state`` and
re-exporting it keeps both true.
"""
from pathlib import Path
import sys
import unittest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


class CloseFilesTests(unittest.TestCase):
    def test_parallel_integrate_re_exports_the_shared_helper(self):
        import parallel_integrate
        import parallel_state
        self.assertIs(parallel_integrate.close_files, parallel_state.close_files)

    def test_close_files_name_the_task_record_its_receipt_and_its_live_followup(self):
        import parallel_integrate
        self.assertEqual(parallel_integrate.close_files('/repo', 'A'),
                         ['tasks/items/A.md', 'tasks/evidence/A.toml', 'tasks/items/A-LIVE.md'])
        self.assertEqual(parallel_integrate.close_files('/repo'), ['tasks/items/', 'tasks/evidence/'])


if __name__ == '__main__':
    unittest.main()
