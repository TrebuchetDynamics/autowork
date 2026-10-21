+++
schema = 1
id = "TOOLSET-330-0a"
title = "Task records end without a trailing blank line"
short = "No blank line at end of records"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 24000
depends_on = []
touches = ["pi-autowork/engine/", "pi-autowork/pi_autowork/", "tests/", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "task_store.render(fields, '\\n') writes a blank line at the end of any record without notes (cmd_add, the engine's -LIVE follow-up). A repository whose pre-commit hook runs git diff --cached --check refused the engine's close commit for that reason (2026-10-21): the close stayed staged in the session, the task stayed open on main, and the runner stalled re-dispatching it with 'slot already exists'. Rendered records end with exactly one newline, and a close commit refused by a hook is reported with the hook's output instead of being logged as done."
acceptance = ["A record rendered with no notes, by add and by the -LIVE follow-up, ends with exactly one newline and passes git diff --check.", "On a fixture repository whose pre-commit hook rejects the close commit, the runner reports the hook's failure, keeps the task's slot integrated rather than closed, and does not re-dispatch it."]
checks = ["python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py", "python3 scripts/check.py"]
exclusions = []
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
