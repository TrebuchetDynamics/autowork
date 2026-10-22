+++
schema = 1
id = "TOOLSET-367-071bd3ff"
title = "An unreadable task store never reads as a removed record: held work is kept, not set aside"
short = "Invalid store is not a removed record"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 1000
depends_on = []
touches = ["pi-autowork/engine/parallel_integrate.py", "pi-autowork/engine/parallel_dispatch.py", "pi-autowork/engine/test_hold_causes.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "A consumer's main gained one task file without TOML frontmatter (written by another host). The store failed validation, and in the same cycle the engine told the coordinator that a held candidate's 'task record was removed or closed while it was held' and set its attempt aside (its worktrees were kept, but the recovered candidate now reruns from scratch), while the maintainer started the LEDGER repair. A store that does not validate says nothing about any one record: while the ledger is invalid, held and reported slots must stay exactly as they are (no set-aside, no requeue, no close), and the log must name the invalid file instead. Offline test with a store made invalid by one malformed file."
acceptance = ["With one malformed record in the store and a held slot for another task, a dispatch/retry cycle leaves the held slot unchanged and reports the ledger error; after the file is repaired the slot resumes its normal recovery", "No set-aside, requeue or close event is written for any slot while task_queue reports StoreError"]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_integrate.py pi-autowork/engine/test_hold_causes.py tests/test_pi_autowork.py"]
exclusions = []
+++
- Sources: docs/plans/structural-audit-2026-10.md#hotspots
