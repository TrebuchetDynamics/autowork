"""App-owned planning turns survive navigation; one physical writer per session."""
from pathlib import Path
import sys
import threading
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


class PlanningHubTests(unittest.TestCase):
    def test_single_writer_cancel_and_bounded_event_projection(self):
        from pi_autowork.planning_hub import PlanningHub
        entered = threading.Event()
        class Planner:
            repo = '/repo'
            def send(self, sid, message, on_event, cancel):
                entered.set()
                for _ in range(20):
                    on_event({'type': 'message_update', 'assistantMessageEvent':
                              {'type': 'text_delta', 'delta': 'x' * 100}})
                cancel.wait(5)
                return {'status': 'cancelled', 'text': 'Cancelled; proposal retained.'}
        hub = PlanningHub(max_text=500)
        self.addCleanup(hub.close)
        planner = Planner()
        hub.start('/repo', planner, 's', 'hello')
        self.assertTrue(entered.wait(2))
        with self.assertRaisesRegex(ValueError, 'already running'):
            hub.start('/repo', planner, 's', 'duplicate')
        state = hub.snapshot('/repo', 's')
        self.assertLessEqual(len(state['text']), 500)
        hub.cancel('/repo', 's')
        hub.turns[('/repo', 's')].future.result(3)
        self.assertEqual(hub.snapshot('/repo', 's')['status'], 'cancelled')

    def test_error_is_not_success_and_other_repository_is_independent(self):
        from pi_autowork.planning_hub import PlanningHub
        class Planner:
            def send(self, *args, **kwargs):
                raise RuntimeError('provider unavailable')
        hub = PlanningHub()
        self.addCleanup(hub.close)
        hub.start('/a', Planner(), 'same-id', '')
        hub.start('/b', Planner(), 'same-id', '')
        for turn in hub.turns.values():
            turn.future.result(3)
        for repo in ('/a', '/b'):
            result = hub.snapshot(repo, 'same-id')
            self.assertEqual(result['status'], 'failed')
            self.assertIn('provider unavailable', result['text'])

if __name__ == '__main__':
    unittest.main()
