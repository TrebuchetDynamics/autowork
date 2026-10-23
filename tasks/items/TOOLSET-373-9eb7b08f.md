+++
schema = 1
id = "TOOLSET-373-9eb7b08f"
title = "Git attribute and ignore files that name TODO.md or goals.json are not legacy consumers"
short = "gitattributes is not a consumer"
status = "open"
goal = "FORCE-CONVERSION"
section = "Next"
rank = 4000
depends_on = []
touches = ["pi-autowork/pi_autowork/legacy/conversion_audit.py", "tests/test_conversion_audit.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Evidence: a read-only prepare --check over the owner's legacy repositories lists .gitattributes lines (for example a merge or diff attribute set on TODO.md and goals.json) under consumers, which blocks plain conversion and will appear as LEGACY_CONSUMER diagnostics after a forced one. Such files declare attributes for a path; they never read it, and removing the path makes the line inert. Independent implementation slice: conversion_audit._group classifies .gitattributes, .gitignore, .git-blame-ignore-revs and the .gitattributes/.gitignore files in subdirectories as a third inventory group, git_metadata, reported with path and line like documentation_drift and never a refusal. Both references and retained_references return the same three groups; cover classification, path/line/name reporting and retained/working-tree parity in a new standalone tests/test_conversion_audit.py without editing shared prepare or migration tests. TOOLSET-374-1a612dab owns the original prepare fixture acceptance, any required prepare report plumbing, task-store.md documentation and CHANGELOG.md entry after TOOLSET-368 and this slice land. Offline tests only."
acceptance = ["conversion_audit.references and retained_references return the same three groups for working-tree and retained hits (pi-autowork/tests or tests module that covers conversion_audit)"]
checks = ["python3 scripts/check.py tests/test_conversion_audit.py tests/test_task_prepare.py tests/test_task_migrate.py"]
exclusions = ["No other file type is reclassified", "No rewrite of any repository file"]
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision
- Split evidence: TOOLSET-368-51141b74 has a running slot and owns the shared prepare, documentation, changelog and prepare-test files; TOOLSET-373 has no slot or worker report. The first two original acceptance items and all shared-file work move intact to TOOLSET-374-1a612dab, dependent on TOOLSET-368 and TOOLSET-373. The original third acceptance item remains here. task_migrate.py reference_inventory merges inventory groups generically and task_prepare.py _prepare updates the report from that inventory, so the audit classification and standalone tests can run with disjoint Touches now. No change to TOOLSET-368, goal qualification or owner priority.
