+++
schema = 1
id = "TOOLSET-304-9e"
title = "Docs Sync prepares the task store itself"
short = "Docs Sync prepares the task store"
status = "done"
goal = "TASK-STORE"
section = "Next"
rank = 2000
depends_on = []
touches = ["pi-autowork/pi_autowork/", "pi-autowork/task-store.md", "pi-autowork/README.md", "skills/docs-sync/", "adapters/", "tests/", "docs/", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "autowork tasks prepare detects the store state, converts or finishes converting a TODO.md + goals.json repository through autowork migrate's transaction, lists accepted headings for a new repository and reports evidence-repairable diagnostics; docs-sync on every host runs it first. Task writes take a lock, accept --expect, and refuse contract changes to live attempts."
acceptance = ["tests/test_task_prepare.py covers bootstrap, legacy conversion, staged conversion, interrupted conversion, active-worker refusal, audit read-only, repair, concurrency, idempotency and selection on disposable repositories"]
checks = ["python3 -m unittest discover -s tests -p 'test_task_*.py'", "python3 scripts/check.py"]
exclusions = ["No conversion of fleet repositories; no runner, service or schedule change"]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Evidence: Offline only: python3 -m unittest discover -s tests -p 'test_task_*.py' 46 tests OK (test_task_prepare 23); python3 scripts/check.py twice: 4 of 5 directories passed, tests/ failed on one load-dependent test each run (test_pi_autowork stalled-service status EAGAIN; test_update_bundle slot-move), each passes alone and neither touches task code; no model-driven /docs_sync run and no live repository conversion
