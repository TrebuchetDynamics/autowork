"""Technical triage failures are diagnostics, never inferred owner verdicts."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pi_autowork import blockers_report, command, fleet_view


class FleetRecoveryTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.reason = 'Worker reports an unavailable operator and target handoff'
        self.key = hashlib.sha256(self.reason.encode()).hexdigest()[:16]
        self.marker = dict(key=self.key, attempts=3, phase='failed',
                           failure='triage_snapshot_unavailable', replay_blocked=False)
        self.row = dict(name='fixture', repo=str(self.root), state_dir=str(self.root), state='stalled',
                        held=[dict(task='T-1', cause='blocker', reason=self.reason)],
                        roots=[], since=1,
                        observation=fleet_view.health.observation(dict(snapshot_at=100, task_source=dict(
                            observed_at=100, workspace=str(self.root), repository_identity=str(self.root / '.git'),
                            revision='a' * 40)), alive=True, now=100))
        self.runner = fleet_view.Runner('fixture', repo=str(self.root), service='running', prepare_state='converted',
            questions=[fleet_view.Question('T-1', 'input', 1, self.reason, kind='held')])

    def project(self, marker):
        (self.root / 'triage.json').write_text(json.dumps({'T-1': marker}))
        with patch.object(fleet_view.main_check, 'read', return_value={}):
            return fleet_view._health_runner({'fixture': self.runner}, self.row, 100)

    def test_matching_exhausted_triage_is_not_presented_as_owner_verdict(self):
        runner = self.project(self.marker)
        text, _ = fleet_view.verdict(runner)
        self.assertIn('triage', text.lower())
        self.assertNotIn('Waiting on you', text)
        self.assertEqual(runner.held, [('T-1', 'blocker')], 'Do not release genuine operator holds')
        self.assertEqual(runner.questions, self.runner.questions, 'Preserve recorded question provenance')
        self.assertIn('triage_snapshot_unavailable', fleet_view.recovery_detail(runner))
        self.assertIn('not an owner verdict', fleet_view.recovery_detail(runner))
        (self.root / 'status.json').write_text(json.dumps(self.row))
        with patch.object(fleet_view, 'task_store', return_value=None):
            report = blockers_report.summary(blockers_report.build(runner))
        self.assertIn('triage_snapshot_unavailable', report)
        self.assertIn(self.reason, report)
        self.assertNotIn('Awaiting owner decisions', report)
        self.assertNotIn('triage_failures', command.runner_json(runner), 'Keep the existing CLI JSON contract')

    def test_old_or_completed_or_retrying_markers_do_not_override_current_question(self):
        for marker in (self.key, dict(self.marker, key='different'), dict(self.marker, attempts=1),
                       dict(self.marker, phase='in_flight'), dict(self.marker, attempts=True)):
            with self.subTest(marker=marker):
                runner = self.project(marker)
                self.assertIn('Waiting on you', fleet_view.verdict(runner)[0])

    def test_reason_fingerprint_normalizes_whitespace_but_not_changed_input(self):
        self.row['held'][0]['reason'] = '  ' + self.reason.replace(' ', '\n\t') + ' '
        self.assertIn('triage', fleet_view.verdict(self.project(self.marker))[0].lower())
        self.row['held'][0]['reason'] = 'An unrelated new incident'
        self.assertIn('Waiting on you', fleet_view.verdict(self.project(self.marker))[0])

    def test_recovery_observation_errors_are_visible_without_erasing_questions(self):
        (self.root / 'triage.json').write_text('invalid json')
        with patch.object(fleet_view.main_check, 'read', return_value={}):
            runner = fleet_view._health_runner({'fixture': self.runner}, self.row, 100)
        self.assertTrue(any('recovery observation unavailable' in error for error in runner.acquisition_errors))
        self.assertEqual(runner.questions, self.runner.questions)
        self.assertFalse(runner.triage_failures)

    def test_recovery_hold_is_diagnostic_without_overriding_service_pause(self):
        self.runner.state = 'paused'
        self.row['state'] = 'paused'
        runner = self.project(dict(self.marker, attempts=1, replay_blocked=True))
        self.assertIn('Paused', fleet_view.verdict(runner)[0])
        self.assertIn('automatic replay held', fleet_view.recovery_detail(runner))


if __name__ == '__main__':
    unittest.main()
