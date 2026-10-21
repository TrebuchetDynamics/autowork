+++
schema = 1
id = "TOOLSET-306-3a"
title = "Widen new task ID suffixes so concurrent planners do not collide"
short = "Wider task ID suffix"
status = "open"
goal = "TASK-STORE"
section = "Next"
rank = 3000
depends_on = ["TOOLSET-304-2c"]
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/engine/", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "new_id appends a 2-hex suffix, so two planners taking the same next number collide 1 time in 256. Widen new suffixes (for example 8 hex); existing IDs stay valid and unchanged."
acceptance = ["tests cover: new IDs carry the wider suffix and still parse and sort with existing 2-hex IDs; validate accepts both."]
checks = ["python3 -m unittest discover -s pi-autowork/tests; python3 scripts/check.py"]
exclusions = []
+++

- Dependencies: TOOLSET-304-2c
- Coordination: Run after TOOLSET-304-2c: both tasks edit pi-autowork/pi_autowork/task_commands.py and pi-autowork/tests/. TOOLSET-304-2c is running, so its contract stays unchanged. The wider-ID change requires new_id in that shared file; no independent implementation slice can start with disjoint Touches. Preserve this task’s scope, acceptance, checks and Next rank.
