"""Opt-in SDK + installed Pi qualification; deterministic offline provider only.

AUTOWORK_TEST_PI=/absolute/pi /qualified/python test_installed_pi_rpc.py -v
No provider credentials, model calls, installs, services or ambient Pi resources.
"""
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import json
import os
import sys
import time
import unittest

import test_installed_pi_contract as native_fixture
from pi_autowork import pi_rpc


@unittest.skipUnless(os.environ.get('AUTOWORK_TEST_PI') and importlib.util.find_spec('pi_agent'),
                     'explicit installed Pi plus pinned SDK interpreter required')
class InstalledRpcTests(unittest.TestCase):
    def setUp(self):
        native_fixture.InstalledPiContractTests.setUp(self)
        self.settings.transport='rpc'
        self.settings.rpc_python=sys.executable

    run_pi=native_fixture.InstalledPiContractTests.run_pi
    assert_finished=native_fixture.InstalledPiContractTests.assert_finished

    def test_live_events_precede_settlement_with_real_sdk_and_pi(self):
        barrier=self.cwd/'.fixture-before-settle'
        release=self.cwd/'.fixture-settle-release'
        with ThreadPoolExecutor(max_workers=1) as pool:
            future=pool.submit(self.run_pi,'settle')
            try:
                deadline=time.monotonic()+30
                while not barrier.exists():
                    if future.done(): self.fail(f'run exited before barrier: {future.result()}')
                    if time.monotonic()>deadline: self.fail('native settlement barrier not reached')
                    time.sleep(.02)
                self.assertFalse(future.done())
                path=pi_rpc.runtime_path(self.settings.state,'native-worker-attempt-1')
                for _ in range(100):
                    progress=json.loads(path.read_text())
                    if progress['started']: break
                    time.sleep(.02)
                self.assertTrue(progress['active'])
                self.assertTrue(progress['started'])
                self.assertFalse(progress['settled'])
                self.assertEqual(progress['transport'],'rpc')
            finally:
                release.touch()
            result=future.result(timeout=60)
        self.assert_finished(result)
        self.assertTrue(result['cleanup_complete'])
        self.assertEqual((self.cwd/'.fixture-events').read_text().splitlines(),
                         ['agent_end','agent_end','agent_settled'])

    def test_rpc_resume_and_independent_review_use_distinct_histories_and_tools(self):
        native_fixture.InstalledPiContractTests.test_resume_retains_context_but_a_review_session_is_fresh(self)

    def test_json_rpc_cold_start_fixture_comparison(self):
        timings={}
        for transport in ('json','rpc'):
            self.settings.transport=transport
            timings[transport]=[]
            for index in range(3):
                started=time.monotonic()
                result=self.run_pi('finish',session=f'benchmark-{transport}-{index}')
                elapsed=time.monotonic()-started
                self.assert_finished(result)
                timings[transport].append(elapsed)
        print('\nOFFLINE_FIXTURE_SECONDS '+json.dumps(timings),flush=True)


if __name__=='__main__': unittest.main()
