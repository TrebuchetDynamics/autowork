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
touches = ["pi-autowork/pi_autowork/legacy/conversion_audit.py", "pi-autowork/pi_autowork/task_prepare.py", "pi-autowork/task-store.md", "CHANGELOG.md", "tests/test_task_prepare.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Evidence: a read-only prepare --check over the owner's legacy repositories lists .gitattributes lines (for example a merge or diff attribute set on TODO.md and goals.json) under consumers, which blocks plain conversion and will appear as LEGACY_CONSUMER diagnostics after a forced one. Such files declare attributes for a path; they never read it, and removing the path makes the line inert. Planner's call: conversion_audit._group classifies .gitattributes, .gitignore, .git-blame-ignore-revs and the .gitattributes/.gitignore files in subdirectories as a third inventory group, git_metadata, reported with path and line like documentation_drift and never a refusal; task-store.md documents the group; the three-group shape is covered by tests. Offline tests only."
acceptance = ["A legacy fixture whose .gitattributes names TODO.md and goals.json: prepare --check reports no consumers, lists both lines under git_metadata, and plain conversion is not refused for them (tests/test_task_prepare.py)", "A tracked script that names TODO.md in the same fixture is still a consumer (tests/test_task_prepare.py)", "conversion_audit.references and retained_references return the same three groups for working-tree and retained hits (pi-autowork/tests or tests module that covers conversion_audit)"]
checks = ["python3 scripts/check.py tests/test_task_prepare.py tests/test_task_migrate.py"]
exclusions = ["No other file type is reclassified", "No rewrite of any repository file"]
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision
