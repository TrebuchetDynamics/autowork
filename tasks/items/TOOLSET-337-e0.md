+++
schema = 1
id = "TOOLSET-337-e0"
title = "The runner end-to-end tests (tests/test_pi_autowork.py) run in a fraction of their time"
short = "Faster runner end-to-end tests"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 28000
depends_on = []
touches = ["tests/test_pi_autowork.py", "scripts/check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "scripts/check.py splits tests/test_pi_autowork.py into 12 shards (SPLIT), and they are the full check's long poles: 100-260 s each under load, against a suite whose other modules mostly take seconds. Profile them (python3 -m unittest --durations 40 test_pi_autowork) and cut wall time where tests wait on real clocks: runner intervals, poll sleeps, busy-wait bounds, settle and quiet periods, reload waits. Prefer injected settings (short intervals and bounds via the env the tests already pass) and event waits over sleeps; share one fixture toolset build per module where it is rebuilt. No assertion weakened and no test removed; record before and after durations in the commit message."
acceptance = ["The slowest shard takes at most half its current time on an idle host, with before and after --durations output in the commit message", "Every test in tests/test_pi_autowork.py still runs and its assertions are unchanged (diff shows timing and fixture changes only)", "The full check passes three times in a row under the runner's normal load"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py"]
exclusions = []
+++

