"""Policy contracts only; not evidence of live automatic decisions or delivery."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]


class ScheduledProgressTests(unittest.TestCase):
    def test_progress_is_outcome_based_and_recovery_is_bounded(self):
        policy = (ROOT / 'skills/autogoal/references/scheduled-policy.md').read_text()
        for phrase in ('## Progress and decision loop', 'accepted_goal', 'eligible_task',
                       'implementation', 'passing_checks', 'authorized_publication',
                       'retry_selection.py', 'prepare_prerequisites.py', 'publication.py',
                       'same card', 'Decision:', '5 consecutive attempts',
                       'documentation churn', 'not user approval'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

    def test_direct_feedback_preserves_owner_authority_and_paused_jobs(self):
        policy = (ROOT / 'skills/autogoal/references/profile-feedback.md').read_text()
        for phrase in ('scripts/profile-consult.py', 'Fresh named consultations',
                       'replied, failed, or not reached', 'queries default recursively',
                       '--toolsets session_search', '--run-budget SECONDS',
                       'No resume, yolo, accept-hooks, ignore-rules',
                       'chat-only repair decisions', 'own scoped recovery',
                       'not be resumed, widened or overridden'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)

    def test_audit_guidance_requires_executable_coverage_and_source_only_actions(self):
        policy = (ROOT / 'skills/autogoal/references/state-and-recovery.md').read_text()
        for phrase in ('audit_profiles.py', 'collected is not analyzed',
                       'no_progress', 'unread bytes', 'every discovered profile',
                       'source-only', 'existing owner', 'observability-and-instrumentation'):
            with self.subTest(phrase=phrase):
                self.assertIn(phrase, policy)


if __name__ == '__main__':
    unittest.main()
