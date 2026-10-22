+++
schema = 1
id = "TOOLSET-337-e0"
title = "The runner end-to-end tests (tests/test_pi_autowork.py) run in a fraction of their time"
short = "Faster runner end-to-end tests"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 38000
depends_on = []
touches = ["tests/test_pi_autowork.py", "scripts/check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "scripts/check.py splits tests/test_pi_autowork.py into 12 shards (SPLIT), and they are the full check's long poles: 100-260 s each under load, against a suite whose other modules mostly take seconds. Profile them (python3 -m unittest --durations 40 test_pi_autowork) and cut wall time where tests wait on real clocks: runner intervals, poll sleeps, busy-wait bounds, settle and quiet periods, reload waits. Prefer injected settings (short intervals and bounds via the env the tests already pass) and event waits over sleeps; share one fixture toolset build per module where it is rebuilt. No assertion weakened and no test removed; record before and after durations in the commit message."
acceptance = ["The slowest shard takes at most half its current time on an idle host, with before and after --durations output in the commit message", "Every test in tests/test_pi_autowork.py still runs and its assertions are unchanged (diff shows timing and fixture changes only)", "The full check passes three times in a row under the runner's normal load"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py"]
exclusions = []
closure = "manual"
closure_actor = "xel"
closure_timestamp = "2026-10-22T11:50:05.053939+00:00"
closure_reason = "2026-10-22 owner decision: manually closed this deferred test-speed task to clear the pending queue. Its speedup and three-consecutive-pass acceptance remains unproven and is not marked passed; reopen on a dedicated quiet host."
+++

- Owner decision: 2026-10-22: deferred. Two attempts could not qualify the idle-host halving because the fleet host is never idle while runners work (host busy 46 to 93 percent during both measurements); the acceptance needs a quiet window the owner schedules. Dependents that only shared its files (TOOLSET-338-82, TOOLSET-361-6e5f6471) no longer wait for it while it is deferred.
