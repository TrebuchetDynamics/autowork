"""Producer-to-health provenance on committed private repositories; no live workers."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork.coordinator import Coordinator, task_revision  # noqa: E402
from pi_autowork import health  # noqa: E402
import store_fixture  # noqa: E402


class StatusProvenanceTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.root = Path(tmp.name)
        self.repo = self.root / 'repo'
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        self.todo = ('## Now\n- [ ] A — task A\n  Scope: a.py\n  Acceptance: works\n'
                     '  Checks: true\n  Dependencies: None.\n')
        store_fixture.write_todo(self.repo, self.todo)
        self.state = self.root / 'state'
        self.state.mkdir()
        runner = Coordinator.__new__(Coordinator)
        runner.repo, runner.integ, runner.state = self.repo, self.repo, self.state
        runner.engine_path = Path(__file__).resolve().parents[1] / 'engine/owner_cycle.py'
        self.runner = runner

    def test_status_cache_tracks_workspace_revision_lifetime_and_mutations(self):
        with patch('pi_autowork.coordinator.time.monotonic', return_value=10):
            first = self.runner.status()
            health.update(self.state, first, now=first['task_source']['observed_at'] + 10)
            alias = self.root / 'alias'
            alias.symlink_to(self.repo, target_is_directory=True)
            cached = self.runner.status(directory=alias)
            self.assertEqual(cached, first)
            health.update(self.state, cached, now=first['task_source']['observed_at'] + 20)
            saved = json.loads((self.state / 'status.json').read_text())
            self.assertEqual(saved['task_source'], first['task_source'])
            self.assertEqual(saved['snapshot_age_seconds'], 20)
            store_fixture.write_todo(self.repo, self.todo.replace('task A', 'renamed A'))
            changed = self.runner.status()
            self.assertNotEqual(changed['task_source']['revision'], first['task_source']['revision'])
            other = self.root / 'other'
            subprocess.run(['git', 'clone', '-q', str(self.repo), str(other)], check=True)
            elsewhere = self.runner.status(directory=other)
            self.assertEqual(elsewhere['task_source']['workspace'], str(other))
            self.assertNotEqual(elsewhere['task_source']['repository_identity'],
                                changed['task_source']['repository_identity'])
            linked = self.root / 'linked'
            subprocess.run(['git', '-C', str(self.repo), 'worktree', 'add', '-q', '--detach', str(linked)], check=True)
            linked_status = self.runner.status(directory=linked)
            self.assertEqual(linked_status['task_source']['workspace'], str(linked))
            self.assertEqual(linked_status['task_source']['repository_identity'],
                             changed['task_source']['repository_identity'])
            self.runner.status()
            self.runner.engine('--parallel-status', '--json', owned=False)
            refreshed = self.runner.status()
            self.assertGreater(refreshed['task_source']['observed_at'], changed['task_source']['observed_at'])
        with patch('pi_autowork.coordinator.time.monotonic', return_value=20):
            expired = self.runner.status()
        self.assertGreater(expired['task_source']['observed_at'], refreshed['task_source']['observed_at'])
        self.runner.snapshot = None

        def advance_after_preflight(where):
            revision = task_revision(where)
            store_fixture.write_todo(self.repo, self.todo.replace('task A', 'raced A'))
            return revision

        with patch('pi_autowork.coordinator.task_revision', side_effect=advance_after_preflight):
            raced = self.runner.status()
        self.assertNotEqual(raced['task_source']['revision'], expired['task_source']['revision'])
        # The engine's source wins over the older preflight, so the next read is cached.
        self.assertEqual(self.runner.status(), raced)


if __name__ == '__main__':
    unittest.main()
