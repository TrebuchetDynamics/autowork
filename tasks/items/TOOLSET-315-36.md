+++
schema = 1
id = "TOOLSET-315-36"
title = "Task-store validation leaves no unreachable Git objects"
short = "No objects from validation"
status = "open"
goal = "TASK-STORE-HARDENING"
section = "Next"
rank = 11000
depends_on = ["TOOLSET-304-2c", "TOOLSET-314-23"]
touches = ["pi-autowork/pi_autowork/task_commands.py", "pi-autowork/pi_autowork/task_migrate.py", "pi-autowork/engine/task_store.py", "pi-autowork/engine/test_task_store.py", "tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "validate --worktree, prepare, migrate --dry-run and task writes build throwaway commits whose objects stay loose and unreachable; with runners validating often, the canonical repository reported too many unreachable loose objects (6772 loose, 81.5 MiB on 2026-10-21) and automatic gc had stopped once on .git/gc.log. Write those throwaway objects to a temporary object directory (alternates to the repository's) so nothing lasts, and report, without pruning, which other sources produce unreachable objects and whether every set-aside commit, recovery checkpoint and worker candidate is reachable from a ref, the precondition for re-enabling automatic gc."
acceptance = ["After validate --worktree, prepare and a dry-run migration on a fixture repository, git count-objects reports no new loose objects, and the reads still validate the same stores.", "A written report in the task's Evidence note names the remaining sources of unreachable objects and whether set-aside commits, recovery checkpoints and candidates are ref-reachable."]
checks = ["python3 -m unittest discover -s tests -p test_task_*.py", "python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py", "python3 scripts/check.py"]
exclusions = ["No git gc, prune, repack or removal of .git/gc.log, and no ref deletion, in any repository: report only."]
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Coordination: Overlap repair: wait for TOOLSET-304-2c atomic writes and the earlier-ranked TOOLSET-314-23 JSON input changes before isolating throwaway Git objects in task_commands.py. Task Store v2 and the current worktree_store and migration proof paths identify the shared validation machinery; removing the CLI from Touches would conceal required work. Keep the object-isolation checks and ref-reachability report together: an inspection-only split would not implement the no-new-objects acceptance. Preserve all Acceptance, Checks, exclusions and existing priority.
