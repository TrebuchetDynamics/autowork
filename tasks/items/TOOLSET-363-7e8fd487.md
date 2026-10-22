+++
schema = 1
id = "TOOLSET-363-7e8fd487"
title = "test_a_candidate_finished_during_a_batch_check_rides_the_merge_train passes whichever candidate reports first"
short = "Merge-train test fixture race"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 1000
depends_on = ["TOOLSET-362-494fbe2b"]
touches = ["tests/test_pi_autowork.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Under full-suite load (clone run of 4f13bb0b, 2026-10-22) A was implemented, reviewed alone and landed before B reported, so the first batch was (B, D) and the assertion 'Batch of 2 candidates (A, B)' failed although the train behaved correctly (C rode the train, all four landed). Make the fixture deterministic (B reports before A's review can start, or assert the train behaviour without fixing which two candidates form the first batch). Test-only change."
acceptance = ["The test passes when A is reviewed alone before B reports and when A and B report together (both orders forced in the fake worker plan or as subTests)", "The assertions still fail if a candidate finished during a batch check is reviewed alone instead of riding the train (verified by breaking the train locally, not committed)"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py -k test_a_candidate_finished_during_a_batch_check_rides_the_merge_train"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-363-7e8fd487.toml"
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
