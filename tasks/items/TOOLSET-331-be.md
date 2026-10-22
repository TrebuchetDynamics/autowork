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
touches = ["pi-autowork/README.md", "pi-autowork/engine/parallel_dispatch.py", "pi-autowork/engine/test_parallel_dispatch.py", "pi-autowork/pi_autowork/janitor.py", "pi-autowork/tests/test_janitor.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "2026-10-21: a research task held on an owner question lost the pinned tool binary its campaign used, because the /tmp sweep (PI_AUTOWORK_TMP_STALE) removed the held attempt's temp directory; and when the task later ran fresh, its new attempt did not get the uncommitted campaign kept in the set-aside worktree, so the worker reported the data lost until a person pointed at it. The sweep skips temp directories of held or interrupted slots, and a fresh attempt after a set-aside is told which set-aside worktree holds uncommitted work and where."
acceptance = ["A held slot's temp directory survives the stale-temp sweep; it is removed once the slot is set aside, closed or released.", "After a set-aside whose worktree kept uncommitted files, the next attempt's prompt names that worktree and its uncommitted paths."]
checks = ["python3 scripts/check.py"]
exclusions = []
+++

- Sources: [Task Store v2](docs/project.md#task-store-v2-2026-10-20)
- Touches: narrowed from four whole directories to the five files the reverted landing c64a0a20aa7e532c349631b84b7c47ac7aa18b56 changed, so this task no longer claims every path under pi-autowork/engine/, pi-autowork/pi_autowork/, tests/ and pi-autowork/tests/; a re-attempt extends them only with evidence.
- Reopened: optimistic landing reverted c64a0a20aa7e532c349631b84b7c47ac7aa18b56 in e5e18a40, blaming test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why on main at 9cb0dfa. That assertion predated every affected landing, was fixed separately in a215993d and passes on main, so it is not this task's defect and needs no work here (TOOLSET-353-9db87df7 and TOOLSET-327-02 were re-landed unchanged for the same reason in e5162924). Next attempt: re-land or re-verify the reverted commit above with this contract and Acceptance unchanged.
