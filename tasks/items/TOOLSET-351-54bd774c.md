+++
schema = 1
id = "TOOLSET-351-54bd774c"
title = "The fleet view's task counts add up and every count says what it counts"
short = "Fleet view counts add up, with labels"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Owner report: the fleet statistics are wrong and need more labels. The runner table's Active+Mergeable+Waiting+Blocker does not reach Total (Needs-decision tasks have no column); the detail Waiting row breaks down only the queue waits (e.g. 'Waiting 8: 6 on dependencies · 2 ...' beside '15 waiting'), leaving out implemented commits waiting for review or their merge turn and overlap holds. Add a Decision column; make the Waiting row's count equal the Waiting column, labelled by reason (implemented, merge turn, batch check, paused, dependencies, overlap ...)."
acceptance = ["The runner table has a Decision column and its count columns sum to Total", "The detail Waiting row's number equals the Waiting count and its parts, each labelled, sum to it"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py"]
exclusions = []
closure = "manual"
closure_actor = "owner's interactive session (supervisor)"
closure_timestamp = "2026-10-21T21:20:59.972861+00:00"
closure_reason = "Decision column added; the Waiting row's labelled parts sum to the Waiting count"
closure_evidence = "aab33345; python3 scripts/check.py pi-autowork/tests/test_fleet_view.py: 37 tests OK (test_waiting_row_adds_up_to_the_waiting_count, TUI pilot)"
+++

- Held by: owner's interactive session (supervisor), implementing it now
