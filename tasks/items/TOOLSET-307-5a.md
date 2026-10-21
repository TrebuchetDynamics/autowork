+++
schema = 1
id = "TOOLSET-307-5a"
title = "Record task lifecycle telemetry in the existing journal"
short = "Lifecycle telemetry"
status = "open"
goal = "EVALUATION"
section = "Next"
rank = 4000
depends_on = []
touches = ["pi-autowork/engine/", "pi-autowork/pi_autowork/", "pi-autowork/tests/", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Extend the engine journal (autowork-execution/journal.jsonl, parallel_state.event) and closure receipts, not a second event system, so every task attempt leaves structured lifecycle events: accepted (task record first committed), admitted, dispatched, held, resumed, reviewed, integrated, closed and delivered (pushed or merged to main), each with timestamp, repository, task ID, attempt ID, host and model. Record retries, verification failures, recovery events (restart, adopted worker, replayed close) and human intervention events (blocker answered, clear-held, hand closure, owner edit to the task's contract during an attempt). Writes are one appended line, nonblocking and crash-safe; a reader skips a torn final line. Per-attempt events stay distinct from per-task aggregates. Telemetry stays in the Git common directory and runner state: local, private, never committed."
acceptance = ["One fixture task run end to end leaves every lifecycle event once, in order, with attempt ID, host and model; a retry adds a second attempt without a second accepted, closed or delivered event.", "An execution interrupted between dispatch and integration, then resumed, records interrupted and resumed events and still exactly one closed event; a replayed close adds no duplicate.", "A duplicated or torn journal line is skipped by readers and counted, not double-counted; existing journal consumers (parallel_status, scorecard, fleet view) pass unchanged.", "Nothing under tasks/ or any committed path holds telemetry; a test asserts no prompt text, credential or absolute path is written to an event."]
checks = ["python3 -m unittest discover -s pi-autowork/engine", "python3 -m unittest discover -s pi-autowork/tests", "python3 scripts/check.py"]
exclusions = ["No second event store, database, background service or new dependency.", "No change to dispatch, integration, closure or authority decisions: telemetry observes only."]
+++

- Sources: [30-day evaluation](docs/evaluation.md#30-day-evaluation)
