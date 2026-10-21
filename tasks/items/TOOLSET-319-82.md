+++
schema = 1
id = "TOOLSET-319-82"
title = "Conversion keeps the non-task content of TODO.md"
short = "Keep TODO.md non-task content"
status = "superseded"
goal = "TASK-STORE"
section = "Next"
rank = 15000
depends_on = []
touches = ["pi-autowork/pi_autowork/task_migrate.py", "pi-autowork/pi_autowork/legacy/", "tests/", "pi-autowork/task-store.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: one repository's TODO.md held a 749-line product checklist (milestones, MVP acceptance checklist, completion audit, owner answers) above its autowork queue, plus a Backlog (not ready) list; conversion removed TODO.md and kept only task entries, so that content survived only in Git history and the repository's audits failed. Conversion must account for every line: task entries become records, the generated goal-coverage block is dropped, and any other content is either written to a document the conversion names (for example CHECKLIST.md, lines kept at their numbers) or makes the conversion refuse with the line ranges it would lose."
acceptance = ["On a fixture whose TODO.md has a checklist above the queue and a free backlog list, the dry run names those line ranges, and the conversion keeps them byte for byte in the named document.", "A TODO.md that is only a queue converts exactly as before."]
checks = ["python3 -m unittest discover -s tests -p test_task_*.py", "python3 scripts/check.py"]
exclusions = ["No edits to any consumer repository."]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Superseded by: TOOLSET-318-17; Merged into TOOLSET-318-17 before either task started: both change the converter, conversion tests and task-store reference. The successor retains both original scopes, every Acceptance item, the union of Touches and both Checks, and explicitly waits for the reported TOOLSET-307-5a candidate.
