+++
schema = 1
id = "TOOLSET-305-7b"
title = "Tell manual closures from coordinator-verified closures"
short = "Manual vs verified closure"
status = "open"
goal = "TASK-STORE"
section = "Next"
rank = 2500
depends_on = ["TOOLSET-304-2c", "TOOLSET-307-5a"]
touches = ["pi-autowork/engine/", "pi-autowork/pi_autowork/", "pi-autowork/tests/", "tests/", "pi-autowork/task-store.md", "skills/docs-sync/", "adapters/skills/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Approved (owner, 2026-10-21): every task kind may be closed by hand, and every closure records its provenance, manual or coordinator_verified, in the existing task state and evidence architecture (no second closure mechanism, no legacy compatibility). A manual closure records actor, timestamp, reason and an optional evidence reference; it never writes a tasks/evidence receipt or claims passing checks, and the coordinator's verified close keeps all its requirements. A manual closure is not verification: it does not by itself make a goal met, and dependent work or a goal whose acceptance needs verified evidence requires an explicit owner waiver or qualification. The CLI (list, show, why) and the TUI/fleet view show closure provenance and its evidence (receipt, or the manual reason)."
acceptance = ["autowork tasks done records provenance manual with actor, timestamp, reason and optional evidence reference, writes no receipt, and works for implementation, plan and inspection tasks; the coordinator's close records coordinator_verified with its receipt, unchanged.", "tasks show, list and why and the fleet view show Verified (receipt) or Manual (reason) for every closed task.", "goal --status met is refused while an owned task is closed manually without a recorded owner waiver or qualification; with one it proceeds and names it.", "A dependent task whose contract requires verified evidence of a prerequisite is not selectable while that prerequisite is only manually closed, until an owner waiver is recorded; other dependents are unaffected.", "Tests cover manual closure, verified closure, dependencies, goal acceptance and the closure counts the evaluation scorecard reads."]
checks = ["python3 -m unittest discover -s pi-autowork/tests", "python3 -m unittest discover -s tests -p test_task_*.py", "python3 scripts/check.py"]
exclusions = ["No receipt, check result or verification claim is ever written for a manual closure.", "No change to the coordinator verification requirements."]
+++

- Owner decision: 2026-10-21 owner: option 1, allow hand closure for every task kind and always record it as manual; a manual closure is not a verified one (see scope).
- Coordination: Overlap repair: wait for TOOLSET-307-5a lifecycle telemetry and TOOLSET-304-2c atomic writes before changing closure provenance. Both have running worker slots; the 304 attempt-1 report names task_commands.py and task-store.md, and the 307 contract names the engine, CLI, tests and task-store.md. This task needs those same areas for manual versus verified closure, dependency selection and goal qualification; no independent shared-file-free acceptance slice is established. Keep all Scope, Touches, Acceptance and Checks; do not edit either running task.
