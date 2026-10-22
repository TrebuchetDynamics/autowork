+++
schema = 1
id = "TOOLSET-331-be"
title = "A held attempt keeps its temp tools and its restored work"
short = "Held attempts keep their files"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 42000
depends_on = []
touches = ["pi-autowork/engine/", "pi-autowork/pi_autowork/", "tests/", "pi-autowork/tests/"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: a research task held on an owner question lost the pinned tool binary its campaign used, because the /tmp sweep (PI_AUTOWORK_TMP_STALE) removed the held attempt's temp directory; and when the task later ran fresh, its new attempt did not get the uncommitted campaign kept in the set-aside worktree, so the worker reported the data lost until a person pointed at it. The sweep skips temp directories of held or interrupted slots, and a fresh attempt after a set-aside is told which set-aside worktree holds uncommitted work and where."
acceptance = ["A held slot's temp directory survives the stale-temp sweep; it is removed once the slot is set aside, closed or released.", "After a set-aside whose worktree kept uncommitted files, the next attempt's prompt names that worktree and its uncommitted paths."]
checks = ["python3 scripts/check.py"]
exclusions = []
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Reopened: its landing broke the full check on main at 9cb0dfa: test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why; reverted by optimistic landing. Fix those tests in the next attempt
