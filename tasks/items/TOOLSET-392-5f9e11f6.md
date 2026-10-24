+++
schema = 1
id = "TOOLSET-392-5f9e11f6"
title = "Keep maintainer overlap repair from inventing product dependencies"
short = "No dependencies for overlap alone"
status = "done"
goal = "EVALUATION"
section = "Now"
rank = 5000
depends_on = []
touches = ["Src/pi_autowork/maintainer.py", "pi-autowork/tests/test_maintainer.py", "tests/test_planning_decomposition_contract.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Align only DOCS-MAINTAINER overlap instructions with the existing scheduler and PLANNING-CRAFT: distinguish real producer dependencies from hot-file/resource admission and cold-path ranking. Permit leaving legitimate waits unchanged. Merge/split only for source-backed cohesion/conflict benefit, preserving acceptance and priority; no automatic graph rewrite."
acceptance = ["Given a shared path without a producer/consumer prerequisite, the maintainer prompt does not demand a dependency or mandatory recut; extend the existing overlap prompt test in test_maintainer.py.", "Given a real producer, held/live peer or hot-to-cold overlap, guidance preserves genuine prerequisites, no active-contract edits and scheduler/resource policy; extend test_planning_decomposition_contract.py's existing source-contract oracle. Wording tests are not model adherence."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_maintainer.py tests/test_planning_decomposition_contract.py"]
exclusions = ["No fleet/model changes, live experiments, service restarts or remote publication.", "Preserve typed authority, leases, contract/tree evidence, independent complete-candidate review and serialized integration."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-392-5f9e11f6.toml"
+++
- Sources: docs/evaluation.md#delivery-pipeline-optimization; docs/research/delivery-pipeline-2026-10-24.md; Src/pi_autowork/maintainer.py:162-171; skills/shared/PLANNING-CRAFT.md:170-182
- Relationship: Residual maintainer inconsistency after closed TOOLSET-377-e8117892 and TOOLSET-341-eb82856d; retain completed history and existing dependency edges.
- Next action: Extend the existing overlap prompt test to expose the contradictory instruction; no new fixture subsystem.
- Stop: Never remove an existing dependency without prerequisite evidence or weaken hot-file/protected-resource admission. Actual model adherence needs separately authorized evaluation.
- Estimate: S quick win; medium potential scheduling benefit, low source-change risk; no measured speedup.
- Pending live: Actual DOCS-MAINTAINER model adherence and any scheduling/productivity benefit require separately authorized evaluation; no live experiment was run.
