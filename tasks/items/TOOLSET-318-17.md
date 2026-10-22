+++
schema = 1
id = "TOOLSET-318-17"
title = "Convert TODO.md without overlooking consumers or losing non-task content"
short = "Safe TODO.md conversion"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Next"
rank = 14000
depends_on = ["TOOLSET-307-5a", "TOOLSET-305-7b", "TOOLSET-315-36"]
touches = ["pi-autowork/pi_autowork/task_migrate.py", "pi-autowork/pi_autowork/task_prepare.py", "tests/", "pi-autowork/task-store.md", "skills/docs-sync/", "adapters/skills/docs-sync/", "pi-autowork/pi_autowork/legacy/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: a repository converted cleanly, then its main went red, because its own make check and 14 of its tests read TODO.md, which the conversion removes. Before converting, autowork migrate --dry-run and tasks prepare --check list tracked files outside documentation that name TODO.md or goals.json (build files, CI workflows, hooks, source and tests), and the conversion refuses while any remain unless --accept-consumers is given; prepare reports them as diagnostics after a conversion. Documentation mentions are reported separately, not refused. 2026-10-21: one repository's TODO.md held a 749-line product checklist (milestones, MVP acceptance checklist, completion audit, owner answers) above its autowork queue, plus a Backlog (not ready) list; conversion removed TODO.md and kept only task entries, so that content survived only in Git history and the repository's audits failed. Conversion must account for every line: task entries become records, the generated goal-coverage block is dropped, and any other content is either written to a document the conversion names (for example CHECKLIST.md, lines kept at their numbers) or makes the conversion refuse with the line ranges it would lose."
acceptance = ["On a fixture repository whose Makefile and one test read TODO.md, the dry run lists both, the conversion refuses naming them, and --accept-consumers converts and reports them.", "Markdown mentions of TODO.md are reported as documentation drift and never refuse.", "On a fixture whose TODO.md has a checklist above the queue and a free backlog list, the dry run names those line ranges, and the conversion keeps them byte for byte in the named document.", "A TODO.md that is only a queue converts exactly as before."]
checks = ["python3 -m unittest discover -s tests -p 'test_task_*.py'", "python3 scripts/check.py"]
exclusions = ["No edits to any consumer repository; the converter reports, it does not rewrite their code."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-318-17.toml"
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Planning repair: Merged the unstarted TOOLSET-319-82 into this task because both edit task_migrate.py, conversion fixtures and pi-autowork/task-store.md. All four acceptance items, both scopes and the union of Touches are retained. Wait for TOOLSET-307-5a: its reported candidate b96065e8473ce56a9611702c4d4088df76ca654b edits pi-autowork/task-store.md and its declared pi-autowork/pi_autowork/ scope also covers the converter; a documentation-only split would not remove the overlap. Queue section and rank stay unchanged. Quoted the unittest glob so the shell passes one pattern to discovery.
- Dependencies: TOOLSET-307-5a, TOOLSET-305-7b, TOOLSET-315-36
- Scheduling: TOOLSET-315-36 is a prerequisite for the same reason the earlier repairs waited: it also edits pi-autowork/pi_autowork/task_migrate.py, sending migrate --dry-run's throwaway objects to a temporary object directory inside the conversion path this task makes lossless. Both are open and neither was ordered against the other, so 315-36 (earlier-ranked, 11000) goes first and this task waits rather than writing the converter twice.
- Coordination: Overlap repair: wait for TOOLSET-305-7b before conversion hardening. Its attempt-1 slot is running; its saved contract declares pi-autowork/pi_autowork/, tests/, pi-autowork/task-store.md, skills/docs-sync/ and adapters/skills/, and its working tree already edits task-store.md, tests/test_task_prepare.py and both Docs Sync skills. No worker report exists yet. TOOLSET-318-17 has no worker slot or report. Merging into the running task is prohibited, and a documentation-only split leaves the converter, tests and skill paths overlapping; no independent acceptance slice with disjoint Touches is established. Preserve all Scope, Touches, Acceptance, Checks, exclusions, section and rank, and retain TOOLSET-307-5a as a prerequisite; do not edit the running task.
