+++
schema = 1
id = "RUNTIME-REAP-01"
title = "Reap adopted exited descendants while the supervisor payload is live"
short = "live supervisor reaping"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 13000
depends_on = []
touches = ["Src/pi_autowork/pi_process.py", "pi-autowork/tests/test_pi_process.py", "docs/pi-rpc.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Repair the supervisor live-wait reaping lifecycle without changing cleanup proof, task acceptance or runtime guards. Preserve direct payload exit status and resolve zombie-induced runner fixture stalls."
acceptance = ["A real Linux subprocess regression proves an adopted exited descendant and its process group disappear while the payload remains alive, and the direct payload nonzero status survives final cleanup.", "Existing signal/deadline/parent-death and permission-denied cleanup cases continue passing; uncertain live descendants never qualify cleanup-complete.", "The focused real coordinator fixture completes A/B work and verified integration rather than timing out waiting on zombie worker groups."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_pi_process.py pi-autowork/tests/test_pi_rpc.py", "cd tests && python3 -m unittest test_pi_autowork.EngineTests.test_independent_tasks_run_in_parallel_and_merge_verified_into_main"]
exclusions = ["No liveness weakening, manual slot/receipt edits, force push or unrelated runtime changes."]
+++
- Sources: docs/tasks/live-supervisor-reaping.md
