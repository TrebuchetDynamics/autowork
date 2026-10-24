+++
schema = 1
id = "TOOLSET-393-f5116fdc"
title = "Retry safely failed maintainer calls without spending semantic repair opportunities"
short = "Bounded maintainer technical retry"
status = "open"
goal = "EVALUATION"
section = "Now"
rank = 6000
depends_on = []
touches = ["Src/pi_autowork/coordinator.py", "Src/pi_autowork/maintainer.py", "pi-autowork/tests/test_maintainer.py", "pi-autowork/tests/test_recovery_runtime_failures.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Propagate role-local structured failure/acceptance/cleanup evidence into ordinary, background, ledger and rolling-plan maintainer results. Reuse the existing durable technical-recovery reservation/backoff mechanism, capped at three safe submissions per unchanged incident. Retry only proven pre-acceptance or confirmed-safe technical failures; completed semantic no-change/blocked/refused repairs remain deduplicated. Do not reuse global last-job failure state for background results."
acceptance = ["Given a safe pre-submission no-model failure followed by restored readiness, the same unchanged maintainer item is retried only when due and at most three submissions across restart; proposed test_recovery_runtime_failures.py::test_maintainer_safe_failure_retries_with_durable_budget proves ordinary/background behavior.", "Given completed no-change/blocked/refused repair, it stays deduplicated; ledger and rolling-plan technical failures do not masquerade as completed semantic repair. Extend existing test_maintainer.py receipt/due tests.", "Given ambiguous acceptance, unproven scratch cleanup, or another role's failure record, no replacement submission or scratch deletion occurs; extend recovery-runtime fixtures without resetting engine attempts/review budgets."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_maintainer.py pi-autowork/tests/test_recovery_runtime_failures.py"]
exclusions = ["No fleet/model changes, live experiments, service restarts or remote publication.", "Preserve typed authority, leases, contract/tree evidence, independent complete-candidate review and serialized integration."]
+++
- Sources: docs/evaluation.md#delivery-pipeline-optimization; docs/research/delivery-pipeline-2026-10-24.md; Src/pi_autowork/coordinator.py:2334-2467; Src/pi_autowork/maintainer.py:438-548
- Relationship: Distinct maintainer consumer of the technical-recovery mechanism reconciled by live-owned TOOLSET-385-6021ba81; inspect its latest landed delta and retained evidence first, do not duplicate or amend that active contract. No product dependency is invented merely for file overlap.
- Next action: Add the named safe-failure regression using existing fake-job fixtures; preserve existing reservation/backoff and uncertainty fences.
- Stop: Unknown submission/cleanup is not retry permission. If the existing helper cannot safely serve this role within declared files, return the bounded seam issue rather than build another recovery engine.
- Estimate: M; medium potential owner-intervention reduction, medium state/replay risk; current incident frequency unknown.
