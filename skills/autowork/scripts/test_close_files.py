"""The close file set stays importable from ``parallel_integrate``.

Two independent changes met at this name: an integration refactor moved the closeout
off the working copy and deleted the local ``close_files`` definition, while archive
reconciliation in the coordinator stages that file set through
``parallel_integrate.close_files``. Moving the helper to ``parallel_state`` and
re-exporting it keeps both true.
"""
from pathlib import Path
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))


class CloseFilesTests(unittest.TestCase):
    def test_parallel_integrate_re_exports_the_shared_helper(self):
        import parallel_integrate
        import parallel_state
        self.assertIs(parallel_integrate.close_files, parallel_state.close_files)

    def test_close_files_names_todo_goals_and_the_archive(self):
        import parallel_integrate
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'TODO.md').write_text('# TODO\n\n## Next\n\n- [ ] A — a thing\n')
            (repo / 'goals.json').write_text('{"version": 1, "goals": [], "tasks": []}')
            self.assertEqual(parallel_integrate.close_files(repo),
                             ['TODO.md', 'goals.json', 'TODO.archive.md'])

    def test_a_linked_archive_is_named_relative_to_the_repository(self):
        import parallel_integrate
        with tempfile.TemporaryDirectory() as tmp:
            repo = Path(tmp)
            (repo / 'docs').mkdir()
            (repo / 'docs' / 'TODO-archive.md').write_text('# Archive\n')
            (repo / 'TODO.md').write_text('See [history](docs/TODO-archive.md).\n')
            self.assertEqual(parallel_integrate.close_files(repo)[2], 'docs/TODO-archive.md')


if __name__ == '__main__':
    unittest.main()
