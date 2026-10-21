+++
schema = 1
id = "TOOLSET-339-54"
title = "Two CI-only flakes pass regardless of timing: a conflicting owner plan test and the live restart waiter test"
short = "Owner-plan and restart-waiter CI flakes"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 30000
depends_on = []
touches = ["tests/test_pi_autowork.py", "tests/test_update_quiet_restart.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "CI on 5f9c2767 failed two tests that passed unchanged on the next commit: tests/test_pi_autowork.py EngineTests.test_a_conflicting_owner_plan_is_landed_after_each_task (line 2783: the fixture's git add tasks/items/C.md C.txt exited 128 in the project checkout while the runner was active, most likely its index.lock) and tests/test_update_quiet_restart.py QuietRestartTests.test_live_waiter_counts_as_a_pending_restart_and_reports_progress (line 125: pending_restart returned None for a live waiter, a race with the waiter's start). Make the first test's owner edit wait for or avoid the runner's git index lock as an owner would (retry on index.lock), and make the second decide a live waiter from the fixture's own recorded state or wait for its start event. No assertion weakened."
acceptance = ["Each test decides from fixture state or an explicit event and not a race with a background process", "Each passes 30 consecutive runs under parallel load (for example 8 concurrent copies)"]
checks = ["python3 scripts/check.py tests/test_update_quiet_restart.py tests/test_pi_autowork.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-339-54.toml"
+++

