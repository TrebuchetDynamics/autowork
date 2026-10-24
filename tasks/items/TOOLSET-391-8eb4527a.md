+++
schema = 1
id = "TOOLSET-391-8eb4527a"
title = "Keep unknown main-check attribution from reverting unrelated landed candidates"
short = "No blanket rollback for unknown blame"
status = "done"
goal = "EVALUATION"
section = "Now"
rank = 4000
depends_on = []
touches = ["Src/pi_autowork/optimistic.py", "pi-autowork/tests/test_optimistic.py", "pi-autowork/tests/test_main_check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "In optimistic.regression, remove only the all-candidate fallback when any named failure lacks supported traceback attribution. Mixed known/unknown failures automatically revert none of that cohort; keep main red and the existing repair/last-green publication path. Preserve targeted rollback when every failure is attributed. No causal bisection subsystem or new model/check runs."
acceptance = ["Given absent/mismatched traces, pre-existing lines or mixed known/unknown failures, regression returns no automatic culprits; proposed test_optimistic.py::test_unknown_attribution_does_not_blame_the_cohort replaces only the unsafe fallback assertion.", "Given unknown attribution, main remains red, publication stays last-green and existing repair handling remains eligible; proposed test_main_check.py::test_unknown_attribution_preserves_red_repair verifies the coordinator path.", "Fully attributed rollback/reopen, conflicting revert and no-green guards retain existing behavior in test_optimistic.py; no old receipt or task history is rewritten."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_optimistic.py pi-autowork/tests/test_main_check.py"]
exclusions = ["No fleet/model changes, live experiments, service restarts or remote publication.", "Preserve typed authority, leases, contract/tree evidence, independent complete-candidate review and serialized integration."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-391-8eb4527a.toml"
+++
- Sources: docs/evaluation.md#delivery-pipeline-optimization; docs/research/delivery-pipeline-2026-10-24.md; Src/pi_autowork/optimistic.py:62-95
- Relationship: New bounded correction to closed TOOLSET-344-7dadea23; preserve TOOLSET-308-f9 attribution and historical victim tasks, not duplicate/reopen them.
- Planner decision: Unknown means no automatic culprit; do not infer innocence or broaden positive attribution. This narrows unsupported rollback, not optimistic landing or green-only publication.
- Next action: Add the named unknown-attribution regression against current code; proposed tests are not yet written or run.
- Stop: If preserving red-main repair requires bypassing evidence/ownership or changing rollback authority beyond this bounded rule, return the specific decision instead.
- Estimate: S; high expected rework reduction, medium change risk; magnitude unmeasured.
