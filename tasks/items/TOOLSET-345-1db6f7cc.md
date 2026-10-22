+++
schema = 1
id = "TOOLSET-345-1db6f7cc"
title = "restart --stop-workers waits for a merge in flight instead of cutting it off"
short = "Restart waits for merges"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 31000
depends_on = ["TOOLSET-310-50", "TOOLSET-330-c2"]
touches = ["pi-autowork/pi_autowork/command.py", "pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/coordinator.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py", "pi-autowork/README.md", "docs/cross-host.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: three `autowork restart --stop-workers` calls in 25 minutes, each only to load a newer toolset, paused every worker and cut off a batch's full check halfway; the batch of six landed nothing and was checked again from the start. `restart --stop-workers` now waits while the runner has a merge in flight (a batch or merge-train full check, an integration review or a merge resolution): it prints what it waits for, and restarts the service once that ends. A bounded wait (default 30 min) ends with a refusal naming the operation, never a restart. `--now` keeps today's immediate restart. Plain `autowork restart` (reload in place) is unchanged."
acceptance = ["With a batch full check running, `autowork restart --stop-workers` does not stop the service before the check ends: it names the batch it waits for, then restarts, and the batch's result is recorded, not discarded.", "With no merge in flight it restarts at once, as before.", "When the wait bound passes, it exits non-zero naming the operation still running, and the service keeps running.", "`autowork restart --stop-workers --now` restarts at once even with a merge in flight; the help text and runner docs describe both."]
checks = ["python3 scripts/check.py"]
exclusions = []
+++
- Coordination: Overlap repair: keep the restart/check-result path together; waiting, timeout refusal and --now must be tested through the command and coordinator, so a help-only split cannot deliver independent Acceptance. Wait for TOOLSET-310-50 (candidate 91cfc443e6edfad1e9b0b3666066751135cc7318; command.py and component README) and the earlier-ranked TOOLSET-330-c2 (command.py and command/runner tests), whose dependency TOOLSET-325-d4 also changes service.py and command.py in candidate 16ffb2039f9e52337731c2bbfd88be28832b2bc9. Evidence: their attempt-1/report.json files under slot-data in the Git common execution directory; at that inspection 310-50 was integrating (it has since landed) and 325-d4 was reported and is still open. Touches replaces directory-wide tests/docs claims with the existing restart tests in tests/test_autowork_command.py, coordinator coverage in tests/test_pi_autowork.py, and the restart contracts in the component README and docs/cross-host.md. No Acceptance or priority changes; plain restart remains unchanged.
