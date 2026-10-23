"""Open work and retained closed history are distinct; no receipt backfill."""
from dataclasses import replace
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'engine'))
from task_store import TaskStore, edit
from pi_autowork import fleet_view, task_snapshot


class TaskHistoryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.repo = Path(self.tmp.name)
        shutil.copytree(Path(__file__).resolve().parents[1] / 'engine/fixtures/task_store', self.repo,
                        dirs_exist_ok=True)
        source = (self.repo / 'tasks/items/T-1.md').read_text()
        (self.repo / 'tasks/items/LEGACY.md').write_text(edit(source.replace('id = "T-1"', 'id = "LEGACY"'), {'status': 'done'}))
        (self.repo / 'tasks/items/MANUAL.md').write_text(edit(source.replace('id = "T-1"', 'id = "MANUAL"'), {
            'status': 'done', 'closure': 'manual', 'closure_actor': 'fixture owner',
            'closure_timestamp': '2026-01-01T00:00:00+00:00', 'closure_reason': 'Stopped without qualification'}))
        self.git('init', '-q')
        self.git('config', 'user.name', 'Fixture')
        self.git('config', 'user.email', 'fixture@example.invalid')
        self.git('add', '.')
        self.git('commit', '-qm', 'history fixture')
        self.snap = task_snapshot.capture(self.repo, engine_observation=None, generation=1)
        self.runner = fleet_view.Runner('fixture', repo=str(self.repo))
        self.runner.snapshot = self.snap

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.repo), *args], text=True).strip()

    def test_default_view_contains_only_open_inventory_not_history_or_annotations(self):
        annotation = fleet_view.TaskRow('OLD-QUESTION', 'Question', 'Annotation', 'Question',
                                        'annotation', question=True)
        self.runner.snapshot = replace(self.snap, question_rows=(annotation,))
        rows = fleet_view.task_rows(self.runner, include_closed=True)
        self.assertEqual([r.task for r in fleet_view.task_view(rows, 'all')], ['T-1'])
        self.assertEqual([r.task for r in fleet_view.task_view(rows, 'questions')], ['OLD-QUESTION'])
        self.assertEqual(self.snap.counts[-1], 1)
        self.assertEqual(TaskStore.at(self.repo, 'HEAD').tasks['LEGACY'].status, 'done')

    def test_legacy_unknown_is_not_manual_or_verified_and_explicit_manual_has_context(self):
        store = TaskStore.at(self.repo, 'HEAD')
        legacy, manual = store.tasks['LEGACY'], store.tasks['MANUAL']
        self.assertEqual(legacy.closure_info['label'], 'Unknown closure')
        self.assertFalse(legacy.verified)
        self.assertEqual(manual.closure_info['label'], 'Manual')
        self.assertFalse(manual.verified)
        rows = {r.task: r for r in self.snap.closed_rows}
        self.assertIn('not recorded', rows['LEGACY'].why)
        self.assertIn('fixture owner', rows['MANUAL'].why)
        self.assertIn('not coordinator-verified', rows['MANUAL'].why)
        verified = replace(legacy, closure='coordinator_verified', receipt_valid=True)
        self.assertEqual(verified.closure_info['label'], 'Verified')
        self.assertIn('missing or invalid', replace(verified, receipt_valid=False).closure_info['label'])

    def test_closed_history_preserves_records_even_when_a_question_annotates_one(self):
        annotation = fleet_view.TaskRow('LEGACY', 'Question about closed plan', 'Annotation', 'Question',
                                        'annotation', question=True)
        self.runner.snapshot = replace(self.snap, question_rows=(annotation,))
        before = {p.relative_to(self.repo): p.read_bytes() for p in self.repo.rglob('*') if p.is_file()}
        self.assertIn('closed', fleet_view.TASK_VIEWS)
        self.assertEqual([r.task for r in fleet_view.closed_task_rows(self.runner)], ['LEGACY', 'MANUAL'])
        self.assertEqual([r.task for r in fleet_view.task_view(
            fleet_view.task_rows(self.runner, include_closed=True), 'all')], ['T-1'])
        self.assertEqual(before, {p.relative_to(self.repo): p.read_bytes()
                                  for p in self.repo.rglob('*') if p.is_file()})


class TaskHistoryPilotTests(unittest.TestCase):
    def test_pinned_textual_open_and_closed_navigation(self):
        if not shutil.which('uv'):
            self.skipTest('uv is needed for pinned Textual')
        result = subprocess.run(['uv', 'run', '--offline', '--no-project', '--with', 'textual==8.2.8',
                                 'python', str(Path(__file__).with_name('task_history_pilot.py'))],
                                capture_output=True, text=True, timeout=90)
        if result.returncode == 2 and 'offline' in result.stderr.lower() and 'textual' in result.stderr.lower():
            self.skipTest('textual==8.2.8 is not in the offline cache')
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
