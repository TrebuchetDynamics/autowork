+++
schema = 1
id = "TOOLSET-313-cf"
title = "A main check whose process is gone stops reading as running"
short = "Orphaned main check"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 9000
depends_on = []
touches = ["pi-autowork/pi_autowork/main_check.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/cli.py", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "main_check.summary prints 'main check running on REV (Nm)' from the record alone: after a runner stopped, the TUI showed a check 'running' for 476 minutes whose process was gone. Check the recorded check process (its pid and start identity) before saying running; show a dead one as interrupted, and flag a live one past its timeout policy or one checking a revision that is no longer main's head."
acceptance = ["tests cover: a running record whose process is gone reads interrupted, not running; a live check past its time limit is flagged; a check of a superseded revision says so."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

