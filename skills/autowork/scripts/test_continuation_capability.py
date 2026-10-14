"""Offline contract doubles; no installed native runtime is qualified here."""
import copy
import unittest
try:
    import continuation_capability as adapter
except ModuleNotFoundError:
    adapter = None

ALLOCATION = dict(amount=10, unit='goal_iterations')
IDENTITY = dict(board_id='default', task_id='original', profile='fixture',
                session_id='original-session', allocation_id='original-allocation', claim_id='claim-1')

class NativeFixture:
    """Explicit atomic runtime contract fixture, never a CLI implementation."""
    def __init__(self):
        self.contract = dict(version=1, accounting=True, atomic_continue=True,
            cumulative_cap=True, compare_and_swap=True, idempotent=True, same_session=True,
            retry_rework_cap=True, completed_rework=True)
        self.state = dict(identity=IDENTITY.copy(), revision='r1', status='blocked',
            claim_active=False, allocation=dict(amount=10, unit='goal_iterations'),
            complete=True, unknown_charges=False, attempt_ids=['a1', 'a2'],
            attempts=[dict(id='a1', session_id='original-session', unit='goal_iterations', consumed=3),
                      dict(id='a2', session_id='original-session', unit='goal_iterations', consumed=2)])
        self.calls = []
        self.interrupt = False
        self.race = False

    def capabilities(self):
        return copy.deepcopy(self.contract)

    def read_accounting(self, identity):
        return copy.deepcopy(self.state)

    def continue_atomic(self, request):
        if self.race:
            self.state['revision'] = 'raced'
            self.state['identity']['claim_id'] = 'another-claim'
        if request['expected'] != self.state:
            return dict(outcome='refused', reason='changed_claim_or_accounting')
        self.calls.append(copy.deepcopy(request))
        attempt_id = 'a' + str(len(self.state['attempts']) + 1)
        self.state['attempt_ids'].append(attempt_id)
        self.state['attempts'].append(dict(id=attempt_id, session_id='original-session', unit='goal_iterations', consumed=2))
        self.state['revision'] = 'r' + str(len(self.calls) + 1)
        if self.interrupt:
            raise TimeoutError('response lost after native commit')
        return dict(outcome='accepted', request_id=request['request_id'],
                    identity=IDENTITY.copy(), remaining_cap=request['remaining_cap'], unit='goal_iterations')

class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.assertIsNotNone(adapter, 'original-card continuation capability adapter is missing')
        self.native = NativeFixture()

    def test_missing_runtime_reports_external_prerequisite(self):
        result = adapter.assess(IDENTITY)
        self.assertEqual(result['outcome'], 'unavailable')
        self.assertIn('atomic', result['reason'])
        self.assertIsNone(result['remaining'])

    def test_supported_fixture_caps_same_card_in_exact_units(self):
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'accepted')
        request = self.native.calls[0]
        self.assertEqual(request['remaining_cap'], 5)
        self.assertEqual(request['expected']['identity'], IDENTITY)
        self.assertEqual(request['expected']['attempt_ids'], ['a1', 'a2'])
        self.assertEqual(request['unit'], 'goal_iterations')

    def test_incomplete_or_invalid_accounting_never_dispatches(self):
        for change in [dict(complete=False), dict(unknown_charges=True), dict(attempt_ids=['a1']),
                       dict(attempt_ids=['a1', 'a2', 'missing']), dict(attempts=[]),
                       dict(claim_active=True), dict(claim_active=None), dict(status='running')]:
            with self.subTest(change=change):
                self.native = NativeFixture()
                self.native.state.update(change)
                self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
                self.assertEqual(self.native.calls, [])

    def test_units_exhaustion_and_malformed_values_refuse(self):
        for field, value in [('unit', 'assistant_messages'), ('consumed', None),
                             ('consumed', True), ('consumed', -1), ('consumed', 1.5),
                             ('consumed', 8), ('session_id', 'replacement-session')]:
            with self.subTest(field=field, value=value):
                self.native = NativeFixture()
                self.native.state['attempts'][0][field] = value
                self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
                self.assertEqual(self.native.calls, [])

    def test_missing_native_guarantees_never_dispatch(self):
        for capability in self.native.contract:
            with self.subTest(capability=capability):
                native = NativeFixture()
                native.contract[capability] = False
                self.assertEqual(adapter.resume(IDENTITY, native, original_allocation=ALLOCATION, rework=True)['outcome'], 'unavailable')
                self.assertEqual(native.calls, [])

    def test_claim_change_before_or_during_operation_refuses(self):
        self.native.state['identity']['claim_id'] = 'different'
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
        self.assertEqual(self.native.calls, [])
        self.native = NativeFixture()
        self.native.race = True
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
        self.assertEqual(self.native.calls, [])

    def test_interrupted_response_requires_readback_without_replenishment(self):
        self.native.interrupt = True
        result = adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)
        self.assertEqual(result['outcome'], 'unverified')
        self.assertTrue(result['fresh_readback_required'])
        self.assertEqual(len(self.native.calls), 1)
        self.assertEqual(adapter.assess(IDENTITY, self.native, original_allocation=ALLOCATION)['remaining'], 3)
        self.native.interrupt = False
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'accepted')
        self.assertEqual(self.native.calls[-1]['remaining_cap'], 3)
        self.assertEqual(self.native.state['allocation']['amount'], 10)

    def test_changed_response_is_unverified_and_does_not_retry(self):
        native_call = self.native.continue_atomic
        def corrupt(request):
            receipt = native_call(request)
            receipt['identity']['session_id'] = 'replacement'
            return receipt
        self.native.continue_atomic = corrupt
        result = adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)
        self.assertEqual(result['outcome'], 'unverified')
        self.assertEqual(len(self.native.calls), 1)

    def test_allocation_values_require_exact_integer_units(self):
        for allocation in [dict(amount=True, unit='goal_iterations'),
                           dict(amount=10.0, unit='goal_iterations'),
                           dict(amount=10, unit=''), dict(amount=0, unit='goal_iterations')]:
            with self.subTest(allocation=allocation):
                self.native.state['allocation'] = allocation
                self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=allocation)['outcome'], 'refused')
        self.assertEqual(self.native.calls, [])

    def test_original_history_cannot_duplicate_or_replace_attempts(self):
        self.native.state['attempts'][1]['id'] = 'a1'
        self.native.state['attempt_ids'] = ['a1', 'a1']
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
        self.assertEqual(self.native.calls, [])

    def test_changed_or_unbound_original_allocation_cannot_replenish(self):
        self.native.state['allocation']['amount'] = 20
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
        self.assertEqual(self.native.calls, [])
        self.assertEqual(adapter.resume(IDENTITY, self.native)['outcome'], 'refused')

    def test_done_requires_explicit_rework_and_native_control(self):
        self.native.state['status'] = 'done'
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION)['outcome'], 'refused')
        self.native.contract['completed_rework'] = False
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION, rework=True)['outcome'], 'unavailable')
        self.native.contract['completed_rework'] = True
        self.assertEqual(adapter.resume(IDENTITY, self.native, original_allocation=ALLOCATION, rework=True)['outcome'], 'accepted')
        self.assertEqual(self.native.calls[0]['operation'], 'rework')
        self.assertEqual(self.native.calls[0]['remaining_cap'], 5)

if __name__ == '__main__':
    unittest.main()
