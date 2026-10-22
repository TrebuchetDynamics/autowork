+++
schema = 1
id = "TOOLSET-325-d4-LIVE"
title = "Live checks for TOOLSET-325-d4"
short = "Live checks for TOOLSET-325-d4"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Needs decision"
rank = 21001
depends_on = ["TOOLSET-325-d4"]
touches = ["pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/health.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py"]
resources = []
kind = "implementation"
ownership = "owner"
scope = "Run the live checks the offline work for TOOLSET-325-d4 left pending."
acceptance = ["Observe an actual systemd user service stopping without restart on setup exit 4, displaying its saved reason in the rendered TUI, and recovering after repair. Current evidence is offline; no live service or model was invoked."]
checks = ["Live qualification by an authorized person"]
exclusions = ["Offline evidence does not count"]
closure = "manual"
closure_actor = "xel"
closure_timestamp = "2026-10-22T11:50:03.408121+00:00"
closure_reason = "2026-10-22 owner decision: manually closed this live-only qualification to clear the pending queue. Offline acceptance remains; live evidence was not produced and is not claimed. Reopen when an authorized live environment and operator window are available."
+++

- Owner decision: 2026-10-22: deferred pending explicit live authorization and an operator-run qualification window. Preserve every live acceptance criterion and the offline-evidence exclusion; no live service, model, credential, proxy, billing or external repository access is authorized. Offline delivery remains separate.
