+++
schema = 1
id = "TOOLSET-322-87"
title = "The draining-restart test decides from its fixture, not the host's processes"
short = "Draining restart CI flake"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 18000
depends_on = []
touches = ["tests/test_update_quiet_restart.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "tests/test_update_quiet_restart.py RestartOutcomeTests.test_a_draining_restart_is_not_finished_yet was the only failure of main's CI run on 9b91302e: finish_restart returned {'gateway_restart': 'completed', 'gateway_restart_result': {'gateway_pid': 134108, ...}} instead of None for a draining restart. The test (unchanged since 7dee68e6, 2026-10-18; passes locally) spawns a real 'gateway restart' process and points the restart marker at its pid, so the outcome depends on reading that live process from the host (its /proc entry, possibly before the child has exec'd under load). Make the draining case come only from state the fixture injects, never from the host's processes; harden only test-owned setup unless the product read itself is shown to race."
acceptance = ["tests cover: the draining case is decided only from the fixture's injected gateway state, never the host's processes; the test passes 50 repeated runs under parallel load (for example alongside a full check); no assertion is weakened."]
checks = ["python3 scripts/check.py tests/test_update_quiet_restart.py; python3 scripts/check.py"]
exclusions = []
+++

