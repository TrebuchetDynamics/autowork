+++
schema = 1
id = "TOOLSET-333-34"
title = "The runner never pauses a whole cycle or reports 'Repository busy' for a lock its own background job holds"
short = "No 'Repository busy' pauses on its own locks"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["pi-autowork/pi_autowork/coordinator.py", "pi-autowork/engine/parallel_integrate.py", "pi-autowork/engine/parallel_dispatch.py", "pi-autowork/engine/task_execution.py", "tests/test_pi_autowork.py", "pi-autowork/engine/test_parallel_dispatch.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Today the runner logged 'Repository busy (Repository execution lock is held by a live operation.); checking again in 60s' ten times, each a full-interval pause shown as a blocker. The holder is the runner's own background integration or review job (TOOLSET-183-d6 runs it beside the loop): integrate() holds integration.lock then writer.lock for its merge and close steps, and the dispatch call (dispatch_with_retries: retire_closed and dispatch.dispatch) takes dispatch.lock and writer.lock with wait=0, so it fails at once with BlockingIOError, task_execution.py turns that into outcome BUSY, and coordinator.py (outcome == 'BUSY', continuous mode) calls blocked_pause for a whole interval. Make contention with this runner's own helper ordinary: the dispatch path waits briefly for these short-held locks (a few seconds) and, if still held by its own background job, the loop retries within seconds without a log line or a health blocker. Keep BUSY, its message and the blocker only when the holder is another process (another runner or a live sequential lease), and when its own job holds a lock for longer than a bound (say 10 min), report that job by name. No lock is removed or weakened: the same mutual exclusion holds."
acceptance = ["With a background integration job holding writer.lock or dispatch.lock for a few seconds, the next dispatch cycle succeeds without logging 'Repository busy' and without a health blocker (offline test with a lock held by a helper of the same coordinator)", "A lock held by a different live process still yields BUSY, its log line and the blocker, as today", "Its own job holding a lock past the bound is reported once, naming the job and task"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py pi-autowork/engine/test_parallel_dispatch.py pi-autowork/engine/test_parallel_integrate.py"]
exclusions = []
+++

- Held by: owner's interactive session (supervisor), implementing it now
