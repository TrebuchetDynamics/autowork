+++
schema = 1
id = "TOOLSET-345-1db6f7cc-LIVE"
title = "Live checks for TOOLSET-345-1db6f7cc"
short = "Live checks for TOOLSET-345-1db6f7cc"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 31001
depends_on = ["TOOLSET-345-1db6f7cc"]
touches = ["pi-autowork/pi_autowork/command.py", "pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/coordinator.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py", "pi-autowork/README.md", "docs/cross-host.md"]
resources = []
kind = "implementation"
ownership = "owner"
scope = "Run the live checks the offline work for TOOLSET-345-1db6f7cc left pending."
acceptance = ["Qualify restart waiting, timeout refusal and --now against a real systemd user service during in-flight merge work. Offline fixtures use fake systemctl and model processes; no live service was stopped or restarted."]
checks = ["Live qualification by an authorized person"]
exclusions = ["Offline evidence does not count"]
closure = "manual"
closure_actor = "xel"
closure_timestamp = "2026-10-22T11:50:03.972432+00:00"
closure_reason = "2026-10-22 owner decision: manually closed this live-only qualification to clear the pending queue. Offline acceptance remains; live evidence was not produced and is not claimed. Reopen when an authorized live environment and operator window are available."
+++

- Owner decision: 2026-10-22: deferred pending explicit live authorization and an operator-run qualification window. Preserve every live acceptance criterion and the offline-evidence exclusion; no live service, model, credential, proxy, billing or external repository access is authorized. Offline delivery remains separate.
