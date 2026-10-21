+++
schema = 1
id = "TOOLSET-301-32"
title = "Planning skills use the autowork CLI and this repository converts to tasks/"
short = "Skills, docs and this repo's conversion"
status = "done"
goal = "TASK-STORE"
section = "Needs decision"
rank = 6000
depends_on = ["TOOLSET-299-d9", "TOOLSET-302-33", "TOOLSET-300-68", "TOOLSET-297-41"]
touches = ["skills/autowork/", "skills/docs-sync/", "skills/plan-for-me/", "skills/blockers/", "skills/shared/TODO-WORKCENTER.md", "docs/", "README.md", "tasks/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "(1) Skills and docs name `autowork tasks ...` for every task edit and drop goals.py instructions; goals.py's task-editing commands are removed (clean cut). (2) Run `autowork migrate` on this repository and commit the result. (3) `autowork migrate` keeps a private reader for TODO.md, goals.json and the archive (moved out of docs-sync and the engine, used by nothing else), because other repositories convert after the cut; no other legacy reader remains. (4) Qualify on a disposable fixture repository: a runner converts nothing on its own, refuses before migration, and after migration selects, runs and closes one task with one receipt commit."
acceptance = ["skill tests pass with the new wording; this repository's `autowork tasks validate .` passes and `autowork tasks list .` shows the remaining TASK-STORE work; the fixture qualification (`tests/test_task_store_qualification.py`) records its commands and results (offline, not a live fleet claim)."]
checks = ["python3 scripts/check.py; autowork tasks validate ."]
exclusions = ["No conversion of fleet repositories; their owner runs `autowork migrate` one at a time."]
+++

- Owner decision: Decision 2026-10-20 (supervisor, delegated while owner AFK): built on branch task-store-v2 by an interactive session, never by the runner; it lands on main only inside TOOLSET-301-32's single merge with this repository's conversion, because any one cutover task on main stops every unconverted repository's runner, this one's included
- Payoff: Finish the cut: skills and docs describe one store, and this repository runs on it.
- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20); [Autowork skill](skills/autowork/SKILL.md); [Docs Sync](skills/docs-sync/SKILL.md); [Plan For Me](skills/plan-for-me/SKILL.md); [Blockers](skills/blockers/SKILL.md); [TODO rules](skills/shared/TODO-WORKCENTER.md).
- Evidence: Offline only: tests/test_task_store_qualification.py passes (refuse with exit 2 on an unconverted repo, migrate in one commit, one task run and closed with one receipt commit); this repository converted by autowork migrate (40b24ead) and merged in one merge (38999d67); full scripts/check.py on the merged result follows; no live qualification.
- Ownership: Toolset coordinator.
- Dependencies: TOOLSET-297-41, TOOLSET-299-d9, TOOLSET-300-68, TOOLSET-302-33.
