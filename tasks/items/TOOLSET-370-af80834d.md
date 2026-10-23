+++
schema = 1
id = "TOOLSET-370-af80834d"
title = "Under force, order drift and queue entries that do not validate are reported and preserved, not refused"
short = "Force: drift and invalid entries preserved"
status = "open"
goal = "FORCE-CONVERSION"
section = "Next"
rank = 1000
depends_on = ["TOOLSET-368-51141b74"]
touches = ["pi-autowork/pi_autowork/task_migrate.py", "pi-autowork/pi_autowork/legacy/reader.py", "pi-autowork/pi_autowork/legacy/conversion_audit.py", "pi-autowork/task-store.md", "CHANGELOG.md", "tests/test_task_prepare.py", "tests/test_task_migrate.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Planner's call: a forced conversion never stops on the legacy queue's own defects. In task_migrate.build/convert under force: a reader.Drift takes TODO.md's order and the report names the drift; a task entry the legacy reader cannot validate is left out of the converted store, its TODO.md lines are retained in the CHECKLIST.md preservation snapshot (the existing line-accounted mechanism) and the report names each left-out ID with its line range; prove() checks the legacy order over the converted IDs only. Plain conversion keeps refusing as today. task-store.md documents the forced behaviour; CHANGELOG entry. Offline tests only."
acceptance = ["A legacy fixture whose TODO.md order differs from goals.json: prepare --force converts in TODO.md order and the forced step reports the drift; plain prepare still refuses with the drift message (tests/test_task_prepare.py)", "A fixture with one entry missing from goals.json: prepare --force converts the other entries, the preserved report lists the left-out ID with its inclusive line range, CHECKLIST.md holds those bytes at their original lines, and the converted store validates (tests/test_task_migrate.py)", "No converted record, worktree or branch is dropped: the set-aside and preserved accounting covers every input line not mapped to a record (tests/test_task_migrate.py)"]
checks = ["python3 scripts/check.py tests/test_task_prepare.py tests/test_task_migrate.py"]
exclusions = ["A CHECKLIST.md collision and content that cannot be accounted for still refuse: they are data-loss guards", "Plain (unforced) conversion semantics unchanged"]
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision
