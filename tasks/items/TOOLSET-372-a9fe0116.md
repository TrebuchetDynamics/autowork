+++
schema = 1
id = "TOOLSET-372-a9fe0116"
title = "Finish lone-file readiness and document the TUI and bootstrap changes after shared-file work lands"
short = "Force conversion: shared-file follow-up"
status = "open"
goal = "FORCE-CONVERSION"
section = "Next"
rank = 3000
depends_on = ["TOOLSET-368-51141b74", "TOOLSET-369-b3e896c2", "TOOLSET-370-af80834d", "TOOLSET-371-7795a447"]
touches = ["pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/test_fleet_view.py", "pi-autowork/task-store.md", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Shared-file follow-up split from TOOLSET-369-b3e896c2 and TOOLSET-371-7795a447, with no new product scope. After TOOLSET-371 implements lone-file detection and reporting, fleet_view.readiness marks a repository with exactly one of TODO.md and goals.json as needs tasks, not legacy planning; retain TOOLSET-369's legacy planning mark and force guidance for a repository with both files. Document the lone-file state none, NO_STORE outcome and legacy-content-to-reconcile report in pi-autowork/task-store.md. Add CHANGELOG.md entries for TOOLSET-369's confirmed TUI Force action, complete refusal/forced-step display and honest legacy mark, and TOOLSET-371's lone-file bootstrap behavior. Preserve the consumer and drift/invalid-entry documentation landed by TOOLSET-368 and TOOLSET-370. Offline tests only."
acceptance = ["fleet_view.readiness reports needs tasks, not legacy planning, for each lone-file fixture (TODO.md only and goals.json only); both legacy files still report legacy planning with prepare --force guidance, and no planning still reports needs tasks (pi-autowork/tests/test_fleet_view.py). This owns the readiness scope split from TOOLSET-371; TOOLSET-369 retains its existing fleet-view acceptance.", "pi-autowork/task-store.md documents lone-file bootstrap as state none and outcome NO_STORE, names the legacy-content-to-reconcile report, and does not imply a missing legacy file is synthesized or explicit migrate refusals changed.", "CHANGELOG.md records the TUI Force/refusal/legacy-mark changes from TOOLSET-369 and lone-file bootstrap changes from TOOLSET-371 without removing the consumer or drift/invalid-entry entries from TOOLSET-368 and TOOLSET-370."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py", "git diff --check"]
exclusions = ["No new conversion behavior or change to tasks prepare itself", "No synthesis of a missing goals.json or TODO.md", "No change to the autowork migrate command refusal", "No automatic or unconfirmed Force action"]
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision
