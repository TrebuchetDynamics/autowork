+++
schema = 1
id = "TOOLSET-305-7b"
title = "Tell manual closures from coordinator-verified closures"
short = "Manual vs verified closure"
status = "open"
goal = "TASK-STORE"
section = "Needs decision"
rank = 1000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "cmd_done closes any task with any non-empty evidence string and writes no receipt, so a hand closure reads like a coordinator-verified one (tasks/evidence receipt). Record manual closures distinctly (for example a closed_by = manual marker, shown by list/show/why and the fleet view) and decide which task kinds may be closed by hand."
acceptance = ["tests cover: a hand closure is marked manual and shows so in tasks show and the fleet view; a coordinator closure still writes its receipt; a task kind the decision reserves for the coordinator is refused by autowork tasks done."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

