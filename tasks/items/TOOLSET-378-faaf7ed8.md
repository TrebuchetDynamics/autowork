+++
schema = 1
id = "TOOLSET-378-faaf7ed8"
title = "Engine and health snapshots retain the committed source and true observation time"
short = "Bind status to source and time"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 2000
depends_on = []
touches = ["pi-autowork/engine/parallel_status.py", "pi-autowork/engine/task_queue.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/health.py", "pi-autowork/engine/test_parallel_status.py", "pi-autowork/engine/test_task_queue.py", "pi-autowork/tests/test_health.py", "pi-autowork/tests/test_status_provenance.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Capture one immutable TaskStore/revision at engine status entry and reuse it throughout current-record reads. Add task_source workspace/repository_identity/revision/observed_at and row current/admitted contract hashes separately; unknown legacy identity stays unknown. Sanitize task_queue.commit Git routing consistently with TaskStore, preserving unborn semantics without swallowing real errors. Cache coordinator status by workspace/revision/lifetime and preserve source time through health writes/failures; no task/receipt/state schema changes."
acceptance = ["Existing parallel-status/task-queue fixtures and proposed test_status_provenance.py prove one pinned revision across an answer, separate current/admitted hashes, hostile inherited Git/replace-ref isolation and explicit legacy unknown metadata.", "Coordinator revision/cache fixtures and health failure/recovery tests preserve original observed_at on cached/failed reads, separate write time, invalidate on source/mutation changes and retain failure escalation; no freshness laundering.", "Existing status/classification/lifecycle and focused/affected assertions pass without changing slots, locks, authority, task schemas or claiming a deployed process loaded the source."]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_status.py pi-autowork/engine/test_task_queue.py pi-autowork/tests/test_health.py pi-autowork/tests/test_status_provenance.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No task/attempt/receipt schema or authority changes, branch-task union, skipped required review/checks, restored removed fleet shortcuts, unrelated Src migration, service/job/profile/model operations, SSH/network tuning, dependency additions or publication. Preserve active contracts and existing pauses."]
live = "denied"
+++
- Sources: docs/plans/tui-responsiveness.md#producer-provenance
- Planner call: Source-backed repair design, not a proven remote SSH diagnosis; routine defaults and exact interfaces are in the accepted source. Future tests are task-owned inputs to create, not unavailable external prerequisites.
- Produces: Additive task_source {workspace,repository_identity,revision,observed_at}, separate row current/admitted contract_hash and truthful cached-health age.
- Consumes: Existing immutable TaskStore, source/slot contracts and sanitized Git helper; preserve all schema/lifecycle authority.
- Next action: Add/extend the named deterministic private fixture at the public data/event seam before changing implementation, then run Checks on the actual implementation base.
- Evidence: Read-only source reviews at 911d1b2855c94eaedfa07102434d95d139f0ab13; planning base 614bdf8e after canonical delivery of the hotkey task. Existing worker receipt is distinct from implementation acceptance.
- Delivery: Branch-local planning until canonical inclusion and consumer readback; no implementation, rendered or SSH pass claimed.
