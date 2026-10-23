+++
schema = 1
id = "TOOLSET-382-fcc9aa05"
title = "Separate open tasks from closed history and disclose unknown closures"
short = "Separate open tasks and history"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 6000
depends_on = ["TOOLSET-379-cf40090d"]
touches = ["pi-autowork/engine/task_store.py", "pi-autowork/pi_autowork/task_snapshot.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/test_task_history.py", "pi-autowork/tests/task_history_pilot.py", "pi-autowork/README.md", "docs/testing.md", "CHANGELOG.md", "tests/test_task_commands.py", "pi-autowork/tests/tui_pilot.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Adopt the already implemented and reviewed code-only candidate 27e8ca54 after snapshot prerequisite 379 completes. Reconcile its open/closed filtering, closure labels, readonly history and bounded copyable diagnostics with actual current main and any subsequent async TUI changes; preserve their behavior and rerun the required checks. Do not reimplement from scratch or cherry-pick task bookkeeping. No historical record/evidence changes, service operations or publication."
acceptance = ["Default Open rows/count exclude all closed records and independent question annotations; Closed remains accessible via numeric/Tab navigation with full retained records.", "Explicit manual and valid/invalid coordinator closures remain distinguishable; legacy missing provenance says Unknown closure with honest context and no backfill, reopening or verification promotion.", "Closed-history detail cannot execute section/answer/repair actions; independently actionable questions remain accessible outside history and normal open-task controls/view-only restrictions are preserved.", "Real committed-store tests and actual pinned Textual 80/120x24 normal/view-only pilots pass with unchanged record bytes, related closed questions and visible tabs; affected and docs/task checks pass."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_task_history.py pi-autowork/tests/test_task_snapshot.py pi-autowork/tests/test_fleet_view.py", "python3 scripts/affected_tests.py --base 53c049a2ad7aedfc7b2a1eb3be5e135c79b1345a --run", "autowork tasks validate --worktree .", "python3 skills/docs-sync/scripts/docs.py check ."]
exclusions = ["No actual historical task/status/receipt changes or invented closure actor/date/reason/verification.", "No live service, external project/device, model/provider/scheduler or publication operations; preserve admitted 379/380/381 contracts and candidates."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-382-fcc9aa05.toml"
+++
- Sources: docs/plans/task-history-view.md#open-tasks-and-closed-history-in-the-fleet-tui
- Candidate: 27e8ca54 code-only commit on fix/task-history, based on committed snapshot candidate 53c049a2. Preserve the existing implementation and tests; cherry-pick/reconcile only this code commit after the prerequisite and overlap gates permit. Source/task bookkeeping is delivered separately.
- Evidence: Reviewed code at staged tree e86d7cddb8b0e84576843c0bd0a51543b4a368f2: real Git tests, strict CLI closure-context checks, fleet pilot and dense 20-annotation Textual 80/120x24 normal/view-only checks pass. Affected selection77 had one transient fixture FileNotFound in long-review concurrency; that exact test passed isolated on unchanged source. This is composed qualification with a disclosed flaky signal, not a clean first-pass aggregate or historical verification receipt.
- Review: Initial independent review found only an unbounded diagnostics header that hid rows. Negative reproduction confirmed height1; separate bounded readonly TextArea plus Info focus fixed it. Focused independent recheck found P2 resolved and no consequential regression; observed table13/14 rows at80/120, full clipboard equality, numeric/Tab navigation and readonly history guards passed.
- Remaining: Queued adoption/qualification only after 379 is done and no live overlapping TUI owner is writing. The existing runner may execute this worker-owned successor under its current admission gates; no new worker or service was dispatched by the interactive session. Keep the task open until actual code integration/verification; no historical backfill.
