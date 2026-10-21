+++
schema = 1
id = "TOOLSET-344-7dadea23"
title = "Optimistic landing: a reviewed task lands without waiting for the full suite; main's check reverts a regression"
short = "Optimistic landing with auto-revert"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 2000
depends_on = []
touches = ["pi-autowork/pi_autowork/worker.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/main_check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Owner decision 2026-10-21: finished tasks waited 40 min to 3 h for batch full checks. With optimistic landing on, a candidate lands after its own checks and the review, without the full-suite gate and without batching; the background full check of main is the gate after landing. When main's check finds new failures, the regression is attributed to the landed task (TOOLSET-308-f9's attribution) and that task's merge is reverted on main with a commit naming the failing tests, the task reopens with those tests in a note, and nothing pushes while main is red. PI_AUTOWORK_OPTIMISTIC=0 restores the gated flow."
acceptance = ["With optimistic landing a reviewed candidate lands without a full-suite run (offline test)", "A landed task that breaks a test is reverted on main by the runner and reopened with the failing test named, and main is green again", "Pushes wait while main is red"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py pi-autowork/tests/test_main_check.py pi-autowork/tests/test_worker_tmp.py"]
exclusions = []
+++

- Owner decision: 2026-10-21 (owner): yes, optimistic landing now; land after review, check main afterwards, revert on regression
- Held by: owner's interactive session (supervisor), implementing it now
