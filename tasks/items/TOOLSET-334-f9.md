+++
schema = 1
id = "TOOLSET-334-f9"
title = "Reviews and full checks of different candidates run in parallel; only the landing is serial"
short = "Parallel reviews, serial landing"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 27000
depends_on = ["TOOLSET-333-34", "TOOLSET-335-89", "TOOLSET-337-e0"]
touches = ["pi-autowork/engine/parallel_integrate.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/worker.py", "pi-autowork/engine/test_parallel_integrate.py", "tests/test_pi_autowork.py", "pi-autowork/tests/test_landing.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "integrate() (pi-autowork/engine/parallel_integrate.py:750-924) holds integration.lock for a candidate's whole integration, including bounded_command at about line 857: pi-autowork.sh --verify runs the full scripts/check.py gate and the Pi review, minutes per task. So only one candidate is reviewed at a time; batches and the merge train (coordinator.py:343-393, worker.py --verify-batch) help, but every other close, set-aside, clear-held, reverify and retry waits behind it. Redesign: prepare each candidate in its own integration worktree (merge onto the session head it starts from) and run its check and review without integration.lock, several at once within the host's check-slot admission; take integration.lock (and writer.lock) only for the short landing: confirm the session head is unchanged or that the candidate still merges cleanly onto the new head with the same tree it verified (otherwise re-verify only what changed, or re-queue it), then fast-forward the session and record the receipt. Keep every guarantee: no unverified tree lands, contract hashes are checked at landing, receipts name the verified tree, one landing at a time."
acceptance = ["Two candidates with disjoint touches are reviewed and checked at the same time (offline test with fake reviewer and check recording overlapping start and end times), and both land", "A candidate whose verified tree is no longer what would land (the session moved and the merge result differs) is re-verified or re-queued, never landed unverified", "integration.lock is held only for the landing step: a set-aside or clear-held issued during a running review completes without waiting for the review", "Receipts still name the verified tree and contract hash; the existing integrate, batch and merge-train acceptance tests pass unchanged in assertion"]
checks = ["python3 scripts/check.py pi-autowork/engine/test_parallel_integrate.py tests/test_pi_autowork.py pi-autowork/tests/test_landing.py"]
exclusions = []
+++
- Coordination: TOOLSET-342-0153a52b covers one case of this: a failed batch of two or three checked side by side. Whichever lands second replaces the other's mechanism with its own, so failed-batch candidates are checked concurrently one way, not two.
- Dependencies: TOOLSET-333-34, TOOLSET-335-89, TOOLSET-337-e0
- Scheduling: Overlap repair: retain TOOLSET-333-34; wait for TOOLSET-335-89 (coordinator.py, parallel_integrate.py and their tests) and TOOLSET-337-e0 (tests/test_pi_autowork.py). Both prerequisite slots were running when inspected; neither record was edited. The accepted parallel-review/verified-tree/serial-landing contract in 5033935c and the coordination note in d07af414 remain unchanged. There is no independently acceptable slice with disjoint declared Touches: the landing and review guarantees require the shared engine/coordinator paths. Keep all existing Touches, Acceptance and Checks; this is scheduling only.
