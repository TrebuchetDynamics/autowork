+++
schema = 1
id = "TOOLSET-304-2c"
title = "Serialize task-store writes and make multi-file edits all-or-nothing"
short = "Task store write lock"
status = "done"
goal = "TASK-STORE"
section = "Next"
rank = 2000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "task_commands._write compares then replaces a task file without a lock, and its validation rollback writes the old bytes back over any concurrent change; cmd_move and goal focus write several files one at a time. Add a write lock around compare-replace-validate, make the rollback restore only bytes this call wrote, and make multi-file edits (move, goal focus) apply all or none."
acceptance = ["tests cover: two concurrent writes to the same task file neither lose an edit nor roll back the other's change; an edit interrupted between files of a multi-file move or focus change leaves every file at its old or its new state as one set."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

- Coordination: TOOLSET-304-9e landed a per-checkout write lock around every autowork tasks write (task_commands.locked) and --expect REV; still open here: rollback restoring only this call's bytes, and all-or-nothing multi-file move and goal focus.
