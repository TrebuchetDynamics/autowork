+++
schema = 1
id = "TOOLSET-395-6cbb101f"
title = "Land a verified contiguous batch prefix while remaining reviews continue"
short = "Land passing prefix before slow tail"
status = "open"
goal = "EVALUATION"
section = "Now"
rank = 8000
depends_on = []
touches = ["Src/pi_autowork/coordinator.py", "Src/pi_autowork/worker.py", "pi-autowork/tests/test_worker_tmp.py", "tests/test_pi_autowork.py", "pi-autowork/README.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Remove only the terminal whole-batch consumption barrier. Upgrade the existing private batch verdict channel to atomic generation-specific publication bound to admitted task/attempt/contract, candidate/base/prefix tree, producing gate and review policy; these bindings are not present today. Consume only a contiguous passing prefix of an already-gated immutable chain through current engine integration/closure; separate live producer lifetime from serial landing. Preserve current review, affected/optimistic and evidence-equivalence rules. No general lock redesign."
acceptance = ["Given fast A and blocked B reviews in an already-gated chain, proposed test_pi_autowork.py::test_batch_passing_prefix_lands_before_tail exits only after proving A lands before B finishes, without repeating A's valid checks/review; B never lands before its own verdict.", "Given failed/unreviewed predecessor, partial verdict, main/contract drift or cancellation/restart, proposed test_pi_autowork.py::test_batch_prefix_rejects_stale_and_replayed_evidence proves no skipping, stale landing or duplicate closure; reuse current requeue/reverification and cleanup paths.", "Both optimistic and affected-gated modes retain complete independent candidate review, serial landing and full-main qualification; extend batch/train fixtures in test_worker_tmp.py and test_pi_autowork.py without broadening check reuse."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_worker_tmp.py tests/test_pi_autowork.py -k batch", "python3 scripts/check.py pi-autowork/tests/test_worker_tmp.py tests/test_pi_autowork.py -k train", "python3 scripts/check.py pi-autowork/tests/test_optimistic.py pi-autowork/tests/test_main_check.py"]
exclusions = ["No fleet/model changes, live experiments, service restarts or remote publication.", "Preserve typed authority, leases, contract/tree evidence, independent complete-candidate review and serialized integration."]
+++
- Sources: docs/evaluation.md#delivery-pipeline-optimization; docs/research/delivery-pipeline-2026-10-24.md; Src/pi_autowork/worker.py:1112-1186; Src/pi_autowork/coordinator.py:1720-1724,1795-1799
- Relationship: Narrow residual after manually closed TOOLSET-334-f9, not reimplementation of parallel reviews or the already-delivered 340/342 failure-half mechanism.
- Next action: Write the fake-review barrier regression first; demonstrate old code waits for B. Future tests and speedup remain unrun/unmeasured.
- Stop: If this needs out-of-order landing, weakened locks/identity, receipt repinning, wider evidence equivalence or another scheduler, retain the barrier and return a bounded design issue. Never consume a partially written verdict.
- Estimate: M/L upper bound five owned files; potentially high tail-latency benefit, high concurrency/recovery risk; causal benefit requires matched experiment.
- Publication contract: Planner decision: follow docs/evaluation.md#prefix-publication-and-crash-contract. Use a fresh unpredictable generation and files under the existing state/batch/<generation>/ owner; write temp/flush/fsync/atomic-rename. Bind expected task, engine attempt, accepted contract hash, candidate commit, batch base/prefix tree, gate selection/command and policy from admission, never model output. Parent accepts only matching fully published records from its current owned producer. Old producers cannot overwrite current-generation paths; invalidation precedes replacement and uncertain cleanup blocks it. Restart invalidates unconsumed generations; use existing engine receipt/state recovery for integrated prefixes. Consumed verdict before integration may require re-verification; integration before closure uses idempotent close. Terminal batch results exclude already-integrated prefixes. Test stale-generation publication and each crash boundary in the named batch-prefix fixture.
