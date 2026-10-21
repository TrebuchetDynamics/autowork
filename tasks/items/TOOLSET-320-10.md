+++
schema = 1
id = "TOOLSET-320-10"
title = "A session with staged edits merges main instead of reporting unknown conflicts"
short = "Staged session edit blocks merge"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 16000
depends_on = []
touches = ["pi-autowork/pi_autowork/", "pi-autowork/engine/", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: a runner's own BLOCKERS.md edit stayed staged in its session worktree after a commit failed (the repository's pre-commit hook ran a red make check). git merge refuses while the index differs from HEAD, the runner reported 'conflicts with main in: (unknown files)', asked Pi to resolve a merge with no conflicts, and stayed Merge pending until a person unstaged the edit. The runner must commit or unstage its own staged bookkeeping before merging main, report a merge git refuses to start by git's own message (not as a conflict), and say when its own commit was refused by a hook."
acceptance = ["On a fixture session with a staged BLOCKERS.md edit, merging main succeeds and the edit is kept.", "A merge git refuses to start is reported with git's message, never as 'unknown files'; a bookkeeping commit refused by a pre-commit hook is reported as such."]
checks = ["python3 -m unittest discover -s pi-autowork/tests", "python3 scripts/check.py"]
exclusions = ["No bypass of a repository hook for work commits."]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
