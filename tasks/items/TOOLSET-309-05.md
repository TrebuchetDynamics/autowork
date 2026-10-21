+++
schema = 1
id = "TOOLSET-309-05"
title = "Attribute cost and owner attention to tasks"
short = "Per-task cost and attention"
status = "open"
goal = "EVALUATION"
section = "Next"
rank = 6000
depends_on = ["TOOLSET-307-5a"]
touches = ["pi-autowork/pi_autowork/", "pi-autowork/tests/", "pi-autowork/README.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Per attempt and per task, from the Pi runs already logged in runner state runs.jsonl and the lifecycle telemetry: input and output tokens, provider-reported spend when available, split by role (worker, reviewer, coordinator), and total cost per verified task and per delivered task. Missing provider billing is unknown, never zero; subscription-based usage reports tokens with cost unknown, with no invented prices. Human interventions are counted by category from the telemetry. Owner attention time: an autowork blockers session times itself, and a new 'autowork attention MINUTES [--task ID] [--note TEXT]' records any other owner time in private runner state; unrecorded time stays unknown."
acceptance = ["Fixture runs for one task (worker, review, a retried worker) sum to its cost once per run, by role; a retry adds its cost but not a second verified task.", "A run with tokens but no reported cost, and a subscription-billed run, make that task's cost unknown, reported apart from measured cost; nothing is priced from a table.", "Runs from two hosts or models for one task are attributed to each; an incomplete run record (missing role or task) is counted as unattributed, never dropped silently.", "'autowork attention 15 --task ID' adds 15 owner minutes to that task; a blockers session records its own duration; a task with neither reports owner minutes unknown."]
checks = ["python3 -m unittest discover -s pi-autowork/tests", "python3 scripts/check.py"]
exclusions = ["No billing API calls, pricing tables or budget-enforcement changes.", "Usage records and attention logs stay in private runner state and are never committed."]
+++

- Sources: [30-day evaluation](docs/evaluation.md#30-day-evaluation)
