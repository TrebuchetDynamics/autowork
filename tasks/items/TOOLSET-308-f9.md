+++
schema = 1
id = "TOOLSET-308-f9"
title = "Attribute regressions to the task and commit that introduced them"
short = "Regression attribution"
status = "done"
goal = "EVALUATION"
section = "Next"
rank = 5000
depends_on = []
touches = ["pi-autowork/pi_autowork/scorecard.py", "pi-autowork/tests/", "pi-autowork/task-store.md", "skills/shared/TODO-WORKCENTER.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "A merged task regressed only through an explicit, auditable link: a later commit that reverts its receipt's integration commit (git's 'This reverts commit <sha>'), or a later task's note '- Regression of: <ID>; commit <sha>; severity low|medium|high; found by owner|check'. For each regression, record the original task, its delivered commit, the time from that delivery to the revert or the note's first commit (time to discovery), severity, and whether a person found it. Document the note in task-store.md and the shared task rules. A later edit to the same files is never a regression by itself."
acceptance = ["On fixture repositories, a reverted integration commit and a task carrying a valid 'Regression of:' note each produce one regression with original task, delivered commit, time to discovery, severity and finder.", "A revert of an unrelated commit, a later change to the same files, a note naming an unknown task and a malformed note produce no regression; the malformed note is reported as incomplete.", "task-store.md and skills/shared/TODO-WORKCENTER.md describe the note in one sentence each."]
checks = ["python3 -m unittest discover -s pi-autowork/tests", "python3 scripts/check.py"]
exclusions = ["No automatic attribution beyond reverts and the note; no change to how fixes are scheduled."]
+++

- Sources: [30-day evaluation](docs/evaluation.md#30-day-evaluation)
