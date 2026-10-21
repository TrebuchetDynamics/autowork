+++
schema = 1
id = "TOOLSET-346-ea1cc425"
title = "Fix tasks add list inputs and date tasks place owner-decision notes"
short = "Task CLI input fixes"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 32000
depends_on = ["TOOLSET-314-23", "TOOLSET-315-36"]
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/engine/task_store.py", "pi-autowork/engine/test_task_store.py", "tests/test_task_commands.py", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: `autowork tasks add --touches '[\"a\", \"b\"]'` (also --acceptance, --checks, --depends-on, --resources, --exclusions) stored the JSON text as one list item, touches = [\"[\\\"a\\\", \\\"b\\\"]\"], and validate accepted it. add takes one item per repeated flag, while `tasks field` takes a JSON list or a comma list, so the same value written two ways gave different records. Twice in one day a task was added this way and had to be repaired with `tasks field`; a depends_on written so named a task that does not exist. Make add accept a JSON list and repeated flags alike, and make validate refuse a list item that is itself a JSON list. Also owns the complete TOOLSET-347-1741c514 contract: 2026-10-21: `autowork tasks place ID SECTION --decision TEXT` wrote \"- Owner decision: TEXT\" without a date, although its help says \"(dated, one line)\" and the blockers protocol treats only a dated Owner decision on a Needs decision task as answered. Twelve deferrals recorded this way had to be dated by hand. Prefix today's date (YYYY-MM-DD: ) unless TEXT already starts with one, so a caller that supplies its own date is not doubled."
acceptance = ["`tasks add --touches '[\"a\", \"b\"]'` and `--touches a --touches b` write the same record, touches = [\"a\", \"b\"]; likewise for every list flag.", "`tasks validate` refuses a record whose list item is a JSON-encoded list, naming the task and field.", "`tasks add --depends-on` naming no existing task is refused, naming the missing ID.", "`tasks place ID 'Needs decision' --decision 'deferred'` writes \"- Owner decision: <today>: deferred\".", "A --decision that already starts with a YYYY-MM-DD date is kept as given.", "The runner treats the result as an answered decision: no question for that task in BLOCKERS.md."]
checks = ["python3 -m unittest discover -s tests -p 'test_task_*.py'", "python3 scripts/check.py"]
exclusions = []
+++
- Coordination: Overlap repair: merge unstarted TOOLSET-347-1741c514 into this unstarted task; both edit task_commands.py and tests/test_task_commands.py. All three original list-input Acceptance items and all three dated-decision Acceptance items are retained verbatim here; Checks are identical. Wait for TOOLSET-314-23 (reported candidate eae7bd1917410f8e7c95da331fe73302ac2a8b9c; attempt-1/report.json under slot-data in the Git common execution directory) and the earlier-ranked TOOLSET-315-36 validation/object-isolation work. Neither earlier task supplies JSON-list flag normalization, nested-list refusal or dated place decisions. Touches removes the whole pi_autowork/ claim and names engine/task_store.py and its tests because the shared reader validates list fields there; task_commands.py owns add flags and cmd_place. There is no disjoint CLI implementation or runnable docs split before the input/validation behavior exists. Original contracts were queued together in f18530c901815ef65b6441078b3e3b46f110de0f; Task Store v2 in docs/project.md and pi-autowork/task-store.md retain the shared-store/CLI boundary. Rank and section are unchanged.
