+++
schema = 1
id = "TOOLSET-332-6c"
title = "test_update_bundle's unchanged-retry test passes regardless of host timing"
short = "Flaky unchanged-retry update test"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 40000
depends_on = []
touches = ["tests/test_update_bundle.py", "update_bundle.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "CI on 53073e0d failed only tests/test_update_bundle.py ScopedUpdateTests.test_unchanged_retry_is_noop_with_original_backup (line 633: the second update reported status 'updated' instead of 'up_to_date'); the next commit passed unchanged. Find what makes an unchanged retry look changed under load (for example mtimes, a consumer scan or a clock read) and decide it from the fixture's own state; no assertion weakened."
acceptance = ["The test decides up_to_date from the fixture's injected state, not wall time or host processes", "It passes 50 consecutive runs under parallel load (for example 8 concurrent copies)"]
checks = ["python3 scripts/check.py tests/test_update_bundle.py"]
exclusions = []
+++

- Also seen: CI on 15b8d15d: test_killed_after_slot_move_resumes_original_backup; CI on 5a8932d9: test_done_historical_card_does_not_veto_deployment; a local full check: test_claim_from_prior_boot_does_not_veto_install. All in ScopedUpdateTests and all passed on rerun: fix the class's shared timing cause under the same acceptance
- Reopened: its landing broke the full check on main at 9cb0dfa: test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why; reverted by optimistic landing. Fix those tests in the next attempt
