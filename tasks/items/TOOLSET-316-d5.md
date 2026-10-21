+++
schema = 1
id = "TOOLSET-316-d5"
title = "Fleet setup labels follow Docs Sync, and main-check states say which revision they verify"
short = "Setup labels and check states"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 12000
depends_on = ["TOOLSET-312-fa", "TOOLSET-313-cf"]
touches = ["pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/main_check.py", "pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Follow-up to TOOLSET-312-fa and TOOLSET-313-cf, queued separately because both were already running and a contract edit would set their work aside. (1) Setup labels follow autowork tasks prepare's states, with Docs Sync (/docs_sync) as the primary action and autowork migrate kept only as the direct CLI recovery: no store -> 'Setup required — run /docs_sync'; legacy TODO.md + goals.json -> 'Migration required — run /docs_sync'; invalid or conversion_pending -> 'Task store needs repair'. (2) Main-check display states: running (verified live process, PID plus start identity), waiting (queued for a check slot), interrupted (process gone without a result), overdue (live past its limit), superseded (checks a revision older than main's head), passed (green for the stated revision). A green result for an older revision reads 'Last green: OLD · HEAD: NEW · verification pending', never as verification of the current head. Display only: nothing here stops or kills a check."
acceptance = ["tests cover: each prepare state maps to its label and names /docs_sync; each of the six main-check states renders from a fixture record; a green record for a revision behind HEAD shows last green, HEAD and verification pending; rendering an overdue check sends no signal to its process."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

