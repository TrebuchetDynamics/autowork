+++
schema = 1
id = "TOOLSET-328-2e"
title = "Check issue 2's worker-dependency and blocker-panel reports against the task-store runner"
short = "Recheck issue 2 parts 2 and 4"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 23000
depends_on = []
touches = ["tests/test_pi_autowork.py"]
resources = []
kind = "inspection"
ownership = "worker"
scope = "GitHub issue 2 groups five reports from the legacy runner. Parts 1, 3 and 5 are obsolete or fixed (typed depends_on with prepare's UNKNOWN_DEPENDENCY diagnostic; receipts replace archive closure; only quiet planning files are committed). Inspect parts 2 (a worker missing node_modules tools asked the owner instead of reusing a compatible install) and 4 (the blockers panel mixes real questions with technical recovery and answered decisions, and does not show saved-not-consumed answers) against the current code and tests. For each, record whether it still reproduces offline, with the test or code reference, and queue one bounded implementation task for any part that does."
acceptance = ["The worker report states for parts 2 and 4 whether each still reproduces with code or test evidence; a part that reproduces gets an offline test showing it marked expected-failure with the issue link", "Each part that still reproduces is named in the report as one bounded follow-up with scope and touches and acceptance and checks for the coordinator to queue; none is implemented here"]
checks = ["python3 scripts/check.py tests/test_pi_autowork.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-328-2e.toml"
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/2
