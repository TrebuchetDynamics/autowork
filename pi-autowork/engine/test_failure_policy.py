"""Failure type and resolution ownership stay separate, with stable incident identity."""
import unittest

import failure_policy


class FailurePolicyTests(unittest.TestCase):
    def test_exhausted_technical_work_is_not_an_owner_decision(self):
        for cause, failure_class in (
                ('reviewed_twice', 'VALIDATION_FAILURE'),
                ('validation', 'VALIDATION_FAILURE'),
                ('crash', 'PROCESS_INTERRUPTED'),
                ('empty', 'PROCESS_INTERRUPTED'),
                ('timeout', 'PROCESS_TIMEOUT'),
                ('conflict', 'MERGE_CONFLICT'),
                ('report', 'EVIDENCE_MISSING'),
                ('task_wait', 'DEPENDENCY_WAIT'),
                ('no_change', 'CONTRACT_MISMATCH')):
            with self.subTest(cause=cause):
                values = failure_policy.classify(cause)
                self.assertEqual(values['failure_class'], failure_class)
                self.assertNotEqual(values['resolution_owner'], failure_policy.OWNER)
                self.assertFalse(values['owner_decision_required'])
                self.assertTrue(failure_policy.technical(cause))

    def test_only_genuine_owner_inputs_are_owner_questions(self):
        for cause in ('blocker', 'scope', 'scope_request'):
            with self.subTest(cause=cause):
                values = failure_policy.classify(cause)
                self.assertEqual(values['resolution_owner'], failure_policy.OWNER)
                self.assertTrue(values['owner_decision_required'])
                self.assertFalse(failure_policy.technical(cause))

    def test_unknown_evidence_is_investigated_by_the_engine(self):
        values = failure_policy.classify(None, 'held with no attempt left')
        self.assertEqual((values['failure_class'], values['resolution_owner'], values['state']),
                         ('UNKNOWN_FAILURE', failure_policy.ENGINE, 'investigation_required'))
        self.assertFalse(values['owner_decision_required'])

    def test_repeated_polling_keeps_one_incident_until_the_failure_materially_changes(self):
        first = failure_policy.incident_id('/repo', 'T-1', 'reviewed_twice', 'abc123',
                                           'Missing annotation on line 4 after attempt 1 in 2.4s')
        again = failure_policy.incident_id('/repo', 'T-1', 'reviewed_twice', 'abc123',
                                           'Missing   annotation on line 4 after attempt 2 in 9.1s')
        changed = failure_policy.incident_id('/repo', 'T-1', 'reviewed_twice', 'abc123',
                                             'Performance target still unproven')
        self.assertEqual(first, again)
        self.assertNotEqual(first, changed)
        self.assertNotEqual(first, failure_policy.incident_id('/repo', 'T-1', 'reviewed_twice',
                                                              'def456', 'Missing annotation'))

    def test_failed_review_and_process_death_have_distinct_dispositions(self):
        review = failure_policy.classify('reviewed_twice')
        dead = failure_policy.classify('empty')
        self.assertEqual((review['state'], review['next_action']),
                         ('engineering_stuck', 'resume_repair_with_new_evidence'))
        self.assertEqual((dead['resolution_owner'], dead['state'], dead['next_action']),
                         (failure_policy.ENGINE, 'recovery_required', 'requeue_safely'))


if __name__ == '__main__':
    unittest.main()
