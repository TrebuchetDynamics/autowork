+++
schema = 1
id = "TOOLSET-336-3c"
title = "A batch check stands in for the main check of its base; the runner never runs two full checks of the same base at once"
short = "No duplicate full checks of main"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 2000
depends_on = []
touches = ["pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/main_check.py", "pi-autowork/tests/test_main_check.py", "tests/test_pi_autowork.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Today the runner checked main in the background (python3 scripts/check.py, 7-15 min) right after each landing while the next batch ran its own full check on main plus its candidates (8-25 min), two full suites at once on a host already at load 25-50, which roughly doubles both. A batch's merged tree contains main: when a batch check starts on base B, do not start a separate main check of B; when it passes, record B as green from it; when it fails, run the main check of B (as today) to tell new failures from old. Run main's own check only when no batch on that base is pending or running. Keep the existing new-failure comparison, flaky handling and red-main repair task unchanged."
acceptance = ["Offline test: a landing followed by a batch on the new main runs one full check, and main is recorded green from the passing batch", "A failing batch still gets main's own check of its base, and the comparison names only the batch's new failures, as today", "With no batch pending, main is checked after a landing as today"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_main_check.py tests/test_pi_autowork.py"]
exclusions = []
+++

- Held by: owner's interactive session (supervisor), implementing it now
