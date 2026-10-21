+++
schema = 1
id = "TOOLSET-323-c7"
title = "The stuck-command test decides waiting vs running from injected state, not wall time"
short = "Stuck-command timing flake"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 19000
depends_on = []
touches = ["pi-autowork/engine/test_parallel_dispatch.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "pi-autowork/engine/test_parallel_dispatch.py DispatchTests.test_slot_waiting_is_not_a_stuck_command_but_running_still_is failed on main's CI run for f589211d, its only failure (also seen in earlier CI runs). It is a CI-only timing flake: the test holds a worker check slot, sleeps 0.6 s and expects pi_runtime.stop_stuck_commands(pid, 0.4, ...) to find no stuck command while the command waits for the slot, which depends on wall time and on how fast the queued process reaches its waiting state on a loaded runner. Make the test decide stuck-vs-waiting from an injected clock and state; harden only test-owned setup unless the product's own classification is shown to race."
acceptance = ["tests cover: the stuck-vs-waiting decision comes from an injected clock and slot state, never wall time or host load; the test passes 50 repeated runs under parallel load (for example beside a full check); no assertion is weakened."]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_dispatch.py; python3 scripts/check.py"]
exclusions = []
+++

