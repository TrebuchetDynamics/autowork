+++
schema = 1
id = "TOOLSET-374-1a612dab"
title = "Verify prepare git-metadata reporting and document the audit classification after shared-file work lands"
short = "Git metadata: prepare and docs follow-up"
status = "done"
goal = "FORCE-CONVERSION"
section = "Next"
rank = 5000
depends_on = ["TOOLSET-368-51141b74", "TOOLSET-373-9eb7b08f", "TOOLSET-370-af80834d"]
touches = ["pi-autowork/pi_autowork/task_prepare.py", "pi-autowork/task-store.md", "CHANGELOG.md", "tests/test_task_prepare.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Shared-file follow-up split from TOOLSET-373-9eb7b08f, with no new product scope. TOOLSET-373 owns classification in conversion_audit and standalone inventory tests. After it and TOOLSET-368 land, cover prepare's git_metadata report and non-refusal behavior in tests/test_task_prepare.py; adjust task_prepare only if needed to expose the inventory group already returned by task_migrate.reference_inventory. Document git_metadata in pi-autowork/task-store.md and record the classification change in CHANGELOG.md, preserving the force-consumer reporting behavior from TOOLSET-368. The recognized metadata files remain .gitattributes, .gitignore, .git-blame-ignore-revs and nested .gitattributes/.gitignore only. Offline tests only."
acceptance = ["A legacy fixture whose .gitattributes names TODO.md and goals.json: prepare --check reports no consumers, lists both lines under git_metadata, and plain conversion is not refused for them (tests/test_task_prepare.py)", "A tracked script that names TODO.md in the same fixture is still a consumer (tests/test_task_prepare.py)", "pi-autowork/task-store.md documents the third inventory group git_metadata with path and line reporting, never a conversion refusal; CHANGELOG.md records the git-metadata classification change."]
checks = ["python3 scripts/check.py tests/test_task_prepare.py tests/test_task_migrate.py", "git diff --check"]
exclusions = ["No other file type is reclassified", "No rewrite of any repository file"]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-374-1a612dab.toml"
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision; tasks/items/TOOLSET-373-9eb7b08f.md (original git-metadata contract and acceptance split).
- Split evidence: TOOLSET-368-51141b74 is running and declares task_prepare.py, task-store.md, CHANGELOG.md and tests/test_task_prepare.py; these shared paths and the first two original TOOLSET-373 acceptance items move here. The third original acceptance item remains in TOOLSET-373. pi-autowork/pi_autowork/task_migrate.py reference_inventory merges groups generically, and task_prepare.py _prepare updates its report from that inventory, so classification can land independently.
- Overlap resolution: TOOLSET-370-af80834d must land first: its running attempt declares tests/test_task_prepare.py, pi-autowork/task-store.md and CHANGELOG.md, all required here. A changelog-only split would still overlap the prepare fixture tests and inventory documentation; task_prepare.py changes are conditional on those tests, so no independent implementation slice is established. The tasks deliver distinct accepted behavior (forced drift/invalid-entry preservation versus git_metadata reporting), so neither merging into the running task nor superseding this follow-up is justified. Preserve all Touches, Acceptance and Checks and the existing Next rank; add only the explicit dependency. Evidence: both task records and docs/plans/2026-10-22-force-conversion.md#decision; TOOLSET-373 worker report at candidate d42d25184700a1fbc0c4d4818eff535887bde81e assigns the remaining prepare fixture and documentation work here. TOOLSET-374 has no slot or worker report; TOOLSET-370 has a running slot and no report yet. Earlier Split evidence describes the original split, not current worker status.
- Ledger edit disposition: Dropped the saved attempt-1 CHANGELOG.md expansion: closure commit 3f0babf16cea8417be7853196fdc455890e5b271 already records the git-metadata classification and retained script-consumer refusal under Unreleased/Changed. The worker report for candidate 74d695f4d9aca6e6c2f2bdaef1dd60a1e653a752 proposes the same behavior; pi-autowork/task-store.md and tests/test_task_prepare.py retain its documentation and fixture coverage. tasks/evidence/TOOLSET-374-1a612dab.toml is valid coordinator closure evidence. No duplicate changelog entry, reopening, contract change or goal qualification is needed.
