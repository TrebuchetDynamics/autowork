+++
schema = 1
id = "TOOLSET-350-0f7fc340"
title = "The stuck-command dispatch test stops what it starts before its temporary directory is removed"
short = "Stuck-command test cleanup race in CI"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 36000
depends_on = []
touches = ["pi-autowork/engine/test_parallel_dispatch.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "CI on be7f56d7 and on db3578f8 failed pi-autowork/engine/test_parallel_dispatch.py DispatchTests.test_slot_waiting_is_not_a_stuck_command_but_running_still_is with an ERROR in tempfile cleanup: OSError [Errno 39] Directory not empty (a process the test started still wrote into its TemporaryDirectory). It passes locally. TOOLSET-323-c7 (done) reworked this test's timing; the leftover process looks new. Make the test stop and wait for every process it starts (or any slot worker it launches) before the directory is removed, and register cleanups in order; no assertion weakened."
acceptance = ["The test waits for or stops every process it started before its temporary directory is removed (addCleanup order or explicit wait)", "It passes 30 consecutive runs under parallel load and leaves no process running afterwards"]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_dispatch.py"]
exclusions = []
closure = "manual"
closure_actor = "interactive session (owner request: implement easy tasks now)"
closure_timestamp = "2026-10-21T21:27:43.069227+00:00"
closure_reason = "Implemented directly in commit 597fad59; the runner would otherwise dispatch a worker for finished work."
closure_evidence = "Offline: cleanup kills and waits for every process carrying the test's PI_AUTOWORK_CHECK_ROOT before its directory is removed; 30 of 30 runs passed 6 in parallel with no process left; python3 scripts/check.py pi-autowork/engine/test_parallel_dispatch.py passed. The CI-only leftover did not reproduce locally."
+++

