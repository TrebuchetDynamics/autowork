+++
schema = 1
id = "TOOLSET-346-ea1cc425"
title = "tasks add takes list fields in the same forms as tasks field"
short = "tasks add list fields"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 32000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/pi_autowork/", "tests/test_task_commands.py", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: `autowork tasks add --touches '[\"a\", \"b\"]'` (also --acceptance, --checks, --depends-on, --resources, --exclusions) stored the JSON text as one list item, touches = [\"[\\\"a\\\", \\\"b\\\"]\"], and validate accepted it. add takes one item per repeated flag, while `tasks field` takes a JSON list or a comma list, so the same value written two ways gave different records. Twice in one day a task was added this way and had to be repaired with `tasks field`; a depends_on written so named a task that does not exist. Make add accept a JSON list and repeated flags alike, and make validate refuse a list item that is itself a JSON list."
acceptance = ["`tasks add --touches '[\"a\", \"b\"]'` and `--touches a --touches b` write the same record, touches = [\"a\", \"b\"]; likewise for every list flag.", "`tasks validate` refuses a record whose list item is a JSON-encoded list, naming the task and field.", "`tasks add --depends-on` naming no existing task is refused, naming the missing ID."]
checks = ["python3 -m unittest discover -s tests -p 'test_task_*.py'", "python3 scripts/check.py"]
exclusions = []
+++
