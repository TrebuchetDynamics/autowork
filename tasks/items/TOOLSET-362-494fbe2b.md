+++
schema = 1
id = "TOOLSET-362-494fbe2b"
title = "test_candidates_held_by_conflicts_are_resolved_as_a_group_then_checked_once passes whichever worker moves the session first"
short = "Batch-conflict test fixture race"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 51000
depends_on = ["TOOLSET-361-6e5f6471"]
touches = ["tests/test_pi_autowork.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Under full-suite load (snapshot run of 1e2dced1, 2026-10-22) the test failed on 'left out (conflict): A, B' because the first batch found only A conflicting: B's commit still merged cleanly with the session as it stood and conflicted only after A's resolution landed, when the runner resolved it and landed B as well. The runner behaved correctly; the assertion assumes both fake move_session workers moved the session before the first batch merge. Make the fixture deterministic (both session moves complete before either worker reports, or assert the group outcome without fixing which batch sees both conflicts). Test-only change."
acceptance = ["The test passes when B's session move completes after the first batch merge and when it completes before (both orders forced in the fake worker plan or as subTests)", "The assertions still fail if conflicts are resolved one at a time with a check each (verified by breaking the grouping locally, not committed)"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py -k test_candidates_held_by_conflicts_are_resolved_as_a_group_then_checked_once"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-362-494fbe2b.toml"
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
