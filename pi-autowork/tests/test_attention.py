"""Owner time at the command/scorecard seam, with no agent or live runner."""
import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import command, scorecard


class AttentionTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.repo = Path(temp.name)
        subprocess.run(['git', 'init', '-q', str(self.repo)], check=True)
        env = mock.patch.dict(os.environ, {'PI_AUTOWORK_STATE_DIR': str(self.repo / 'private')})
        env.start()
        self.addCleanup(env.stop)

    def test_attention_records_task_minutes_and_rejects_invalid_durations(self):
        with mock.patch.object(command, 'resolve', return_value=(str(self.repo), 'fixture')):
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(command.main(['attention', '15', '--task', 'T-1', '--note', 'review']), 0)
            for minutes in ('-1', 'nan', 'inf'):
                with contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(command.main(['attention', minutes]), 1)
        usage = scorecard.measure(self.repo, 7)['usage']
        self.assertEqual(usage['tasks']['T-1']['owner_minutes'], 15)
        self.assertEqual(usage['owner_minutes'], 15)
        log = next((self.repo / 'private').glob('*/attention.jsonl'))
        self.assertEqual(json.loads(log.read_text())['note'], 'review')
        self.assertEqual(log.stat().st_mode & 0o777, 0o600)

    def test_blockers_records_elapsed_minutes_even_when_the_agent_fails(self):
        original = Path.cwd()
        agent = self.repo / 'agent'
        agent.write_text('#!/bin/sh\nexit 7\n')
        agent.chmod(0o700)
        with mock.patch.object(command, 'resolve', return_value=(str(self.repo), 'fixture')), \
                mock.patch.object(command.fleet_view, 'blockers_agent', return_value=[str(agent)]), \
                mock.patch('time.monotonic', side_effect=[100, 220]):
            self.assertEqual(command.main(['blockers', str(self.repo)]), 7)
        usage = scorecard.measure(self.repo, 7)['usage']
        self.assertEqual(usage['owner_minutes'], 2)
        self.assertEqual(usage['unattributed_owner_minutes'], 2)
        self.assertEqual(usage['attention_categories'], {'blockers': 1})
        self.assertEqual(Path.cwd(), original)


if __name__ == '__main__':
    unittest.main()
