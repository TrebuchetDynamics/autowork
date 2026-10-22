"""Hold policy through public transitions and the real refill adapter (offline Git)."""
import copy
import unittest
from unittest.mock import patch

import test_parallel_integrate as fixtures
import parallel_dispatch as dispatch
import parallel_state as state
import task_execution as execution


class HoldCausesTests(unittest.TestCase):
    def fixture(self):
        fixture = fixtures.IntegrationTests(methodName='runTest')
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    def test_unknown_cause_refused(self):
        fx = self.fixture()
        fx.worker()
        path = state.slot_path(fx.common, 'A')
        journal = fx.common / 'journal.jsonl'
        original = state.slots(fx.common)[0]
        for report_only in (False, True):
            if report_only:
                # The report-resume guard must not silently replace a caller's typo.
                dispatch.data_dir(fx.common, original).joinpath('report.json').unlink()
                execution.save(path, dict(original, report_resume_attempt=1))
            before = path.read_bytes(), journal.read_bytes()
            for cause in ('typo', None, [], {}):
                with self.subTest(cause=cause, report_only=report_only):
                    with self.assertRaises(ValueError):
                        state.transition(fx.repo, fx.owner, 'A', 'held', cause=cause)
                    self.assertEqual((path.read_bytes(), journal.read_bytes()), before)

    def test_legacy_unknown_or_missing_cause_reads_as_crash(self):
        fx = self.fixture()
        fx.worker()
        path = state.slot_path(fx.common, 'A')
        original = state.slots(fx.common)[0]
        for cause in ('typo', None, [], {}):
            with self.subTest(cause=cause):
                legacy = dict(original, state='held', cause=cause)
                if cause is None:
                    legacy.pop('cause')
                execution.save(path, legacy)
                before = path.read_bytes()
                self.assertEqual(state.slots(fx.common)[0]['cause'], 'crash')
                self.assertEqual(path.read_bytes(), before)  # a read is not a migration write

    def test_native_scope_recovery_does_not_read_display_text(self):
        for reason in ('opaque display text', state.SCOPE_HOLD):
            with self.subTest(reason=reason):
                fx = self.fixture()
                fx.worker()
                held = state.transition(fx.repo, fx.owner, 'A', 'held', cause='scope', reason=reason)
                self.assertEqual(state.next_action(held), 'reoffer_once')
                self.assertEqual(fx.module().retry_held(fx.retry_args())['outcome'], 'IDLE')

    def test_protected_scope_is_not_readopted_after_an_empty_retry(self):
        fx = self.fixture()
        root, _ = fx.worker(files={'go.mod': 'module fixture\n'})
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='scope', outside=['go.mod'],
                         reason='protected files need serial admission in the original task contract: go.mod')
        retry = root.with_name(root.name + '-r2')
        fx.git('worktree', 'add', '-qb', 'autowork/A-r2', str(retry), fx.baseline)
        state.transition(fx.repo, fx.owner, 'A', 'dispatched', worktree=str(retry),
                         branch='autowork/A-r2', baseline=fx.baseline)
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='empty', reason='retry made no change')
        self.assertEqual(fx.module().retry_held(fx.retry_args())['outcome'], 'IDLE')

    def test_a_report_hold_after_its_resume_was_used_needs_a_person_not_a_pending_resume(self):
        """A pilot (2026-10-21) wrote no report, was resumed report-only, then reported a failed check:
        held with cause 'report' and the resume already used. The engine keeps the retained commit
        (no fresh attempt replaces it, test_parallel_state), so the policy must hand it to a person;
        classified as a pending engine resume, nothing acted on it for 14 hours."""
        import parallel_status
        import failure_policy
        fx = self.fixture()
        fx.worker()
        report = dispatch.data_dir(fx.common, state.slots(fx.common)[0]) / 'report.json'
        execution.save(report, dict(execution.read(report), commit='0' * 40))  # names another commit
        state.transition(fx.repo, fx.owner, 'A', 'held', cause='report',
                         reason='report.json does not match worker commit/files or reports failure: a check did not pass')
        path = state.slot_path(fx.common, 'A')
        execution.save(path, dict(state.slots(fx.common)[0], report_resume_attempt=1))
        held = state.slots(fx.common)[0]
        self.assertTrue(state.exhausted(held))  # the retained commit stays: no fresh attempt
        self.assertEqual(fx.module().retry_held(fx.retry_args())['outcome'], 'IDLE')
        fields = parallel_status.failure_fields(held['cause'], held['reason'], resume_used=True)
        self.assertEqual((fields['failure_class'], fields['resolution_owner'], fields['failure_state']),
                         ('EVIDENCE_MISSING', failure_policy.OWNER, 'owner_decision_required'))
        self.assertTrue(fields['owner_decision_required'])
        fresh = parallel_status.failure_fields(held['cause'], held['reason'])  # before the resume: engine recovery
        self.assertEqual((fresh['resolution_owner'], fresh['next_action']), (failure_policy.ENGINE, 'resume_report'))

    def test_each_cause_follows_its_rule(self):
        # Literal policies and observable effects: a wrong dispatch branch must fail,
        # not merely an assertion that repeats the table under test.
        cases = {
            'scope': ('reoffer_once', 'REOFFERED', 'reported'),
            'overlap': ('reoffer_once', 'REOFFERED', 'reported'),
            'report': ('reoffer_once', 'REOFFERED', 'reported'),
            'validation': ('reoffer_once', 'REOFFERED', 'reported'),
            'stale_validation': ('reoffer_once', 'REOFFERED', 'reported'),
            'conflict': ('resolve_conflict', 'IDLE', 'held'),
            'blocker': ('ask_owner', 'IDLE', 'held'),
            'timeout': ('reverify', 'IDLE', 'held'),
            'no_change': ('engineering_stuck', 'IDLE', 'held'),
            'reviewed_twice': ('engineering_stuck', 'IDLE', 'held'),
            'task_wait': ('wait_for_task', 'RESUMED', 'interrupted'),
            'scope_request': ('rerun', 'RESUMED', 'interrupted'),
            'runner_merged': ('rerun', 'REQUEUED', None),
            **{cause: ('rerun', 'RETRIED', 'running') for cause in
               ('crash', 'empty', 'diverged', 'launch', 'contract_changed', 'moved')},
        }
        self.assertEqual(set(state.HOLD_CAUSES), set(cases))
        for cause, (rule, outcome, target) in cases.items():
            with self.subTest(cause=cause):
                fx = self.fixture()
                fx.worker()
                details = {}
                if cause == 'scope':
                    details['outside'] = ['ordinary.txt']
                if cause == 'validation':
                    details['checks'] = {'outcome': 'CHILDREN_TERMINATED',
                                         'command_receipt': {'exit_code': 0, 'inputs_match': True}}
                if cause == 'stale_validation':
                    # An unlanded commit, not canonical HEAD.
                    details['integration'] = {'commit': state.slots(fx.common)[0]['commit']}
                if cause == 'task_wait':
                    details['waits_for'] = ['B']
                    entry = fx.entry('B')
                    fx.set_todo(fx.todo.replace(entry, entry.replace('- [ ] B', '- [x] B')
                                                .replace('Status: open', 'Status: done'), 1))
                    # retired() reads B as done in the store, so no new acceptance is manufactured.
                held = state.transition(fx.repo, fx.owner, 'A', 'held', cause=cause,
                                        reason='opaque display text', **details)
                before = copy.deepcopy(held)
                self.assertEqual(state.next_action(held), rule)
                self.assertEqual(held, before)
                args = fx.retry_args()
                args.worker_command = '["true"]'
                # Stop at the host execution boundary; admission, worktree creation,
                # attempt history and durable state changes remain real.
                with patch.object(dispatch, 'resource_gate', return_value=''), \
                        patch.object(dispatch, 'launch', return_value=None):
                    result = fx.module().retry_held(args)
                self.assertEqual(result['outcome'], outcome, result)
                saved = fx.module().slot_for(fx.common, 'A')
                self.assertEqual(saved['state'] if saved else None, target)
                if outcome == 'REOFFERED':
                    self.assertIn(cause, state.reoffered(saved))


if __name__ == '__main__':
    unittest.main()
