+++
schema = 1
id = "POSTMERGE-VERDICT-01"
title = "Provide the missing revision-bound post-merge admission barrier"
short = "Bound next merge to verdict"
status = "done"
goal = "EVALUATION"
section = "Now"
rank = 12000
depends_on = []
touches = ["Src/pi_autowork/coordinator.py", "Src/pi_autowork/supervision/", "Src/pi_autowork/main_check.py", "Src/pi_autowork/settings.py", "Src/pi_autowork/service.py", "Src/pi_autowork/cli.py", "Src/pi_autowork/post_merge_barrier.py", "pi-autowork/tests/test_post_merge_barrier.py", "pi-autowork/tests/test_main_check.py", "pi-autowork/tests/test_supervision_main_checks.py", "docs/cross-host.md", "pi-autowork/README.md"]
resources = ["autowork-runtime-core"]
kind = "implementation"
ownership = "worker"
scope = "Repair the concrete upstream capability prerequisite reported by the consumer post-merge check contract, acceptance item 4, under the current unblock-all request. Add an explicit opt-in supported runner policy for a bounded repository-provided post-merge check: after EVERY canonical merge/fast-forward, consume a verdict bound to that exact merged revision and refuse another merge until that verdict is green. Pending, red, crashed, missing, stale or malformed evidence must not admit another merge. A red verdict records one attributable repair task through the supported task workflow; this policy must not silently edit source, automatically revert the merge or weaken any candidate/review/check gate. Preserve the existing default asynchronous/optimistic policy for consumers that have not selected the new mode. Reuse current main-check/supervision, settings, leases and restart adoption rather than a second scheduler/database. Provide the actual supported capability/configuration and precise verdict schema/path contract; the consumer then separately implements its <=15-minute touched-project command. Do not claim that a wrapper or AGENTS declaration alone satisfies this missing capability."
acceptance = ["Offline public-seam tests exercise merge A -> pending/red -> attempted merge B refused, and green for exactly A -> B admitted. A verdict for another revision, missing/invalid verdict, incomplete check, concurrent main advance or restart cannot release the gate. Existing task/worker attempts, check history and dirty-main guards remain intact.", "Under the selected policy a red verdict creates/deduplicates a bounded repair task with exact revision/failure evidence using supported store writes; it performs no in-place source repair or automatic regression revert. Other ready work can still implement in isolated workers without bypassing the next-merge barrier. Default behavior for unconfigured consumers remains unchanged.", "Supported service/CLI settings persist the opt-in without replacing unrelated grants; docs describe exact command/verdict/timeout/recovery contract and distinguish offline tests from installed activation. Focused tests, import isolation/DAG guard and independent review pass. No full-suite, device or live acceptance is invented."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_post_merge_barrier.py pi-autowork/tests/test_main_check.py pi-autowork/tests/test_supervision_main_checks.py", "python3 scripts/affected_tests.py --run", "git diff --check"]
exclusions = ["No fleet setting changes, service restart, publication or push grant; no consumer hardware/RF/database operations; no global default change, weakened tests, reset budgets, repinned acceptance or discarded work."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/POSTMERGE-VERDICT-01.toml"
+++
- Sources: Current owner unblock-all request; consumer accepted bounded per-merge check scope/acceptance item 4 and retained blocked report; docs/cross-host.md#run-autowork-continuously; Src/pi_autowork/coordinator.py; Src/pi_autowork/main_check.py
- Pending live: Consumer separately implements and qualifies its repository-provided touched-project command, including complete inventory and actual <=15-minute execution budget.
- Pending live: Installed per-repository policy activation/service verification was not performed; no fleet settings, service restart, publication, hardware, database or live operations were authorized or executed.
