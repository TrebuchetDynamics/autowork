+++
schema = 1
id = "TOOLSET-384-f3e1e7f5"
title = "Audit installed Pi integration and qualify the native JSON adapter without changing live ownership"
short = "Audit and qualify installed Pi"
status = "done"
goal = "EVALUATION"
section = "Now"
rank = 1000
depends_on = []
touches = ["pi-autowork/tests/test_installed_pi_contract.py", "docs/research/pi-harness-audit-2026-10-24.md"]
resources = []
kind = "inspection"
ownership = "worker"
scope = "Verify current adapter and installed Pi against external harness recommendations; add explicitly opted-in native offline contract coverage using the existing deterministic provider; record ranked dependency-linked repairs without touching live migration-owned runtime files."
acceptance = ["Evidence distinguishes source inspection, native offline execution and unqualified live outcomes; JSON/RPC capabilities are verified without real credentials or provider calls.", "Native contract tests prove agent_end is not settled, partial events are observable before process exit, session-ID resumption and fresh review-session isolation, tool allowlist/denylist behavior, raw-stream cleanup and retained private session history; absent explicit native-test opt-in performs no Pi invocation."]
checks = ["PI_EXECUTABLE=$(command -v pi) && AUTOWORK_TEST_PI=\"$PI_EXECUTABLE\" python3 pi-autowork/tests/test_installed_pi_contract.py -v", "python3 scripts/check.py pi-autowork/tests/test_pi_runtime.py pi-autowork/tests/test_blocker_triage.py pi-autowork/tests/test_installed_pi_contract.py", "python3 pi-autowork/pi_autowork/command.py tasks validate --worktree ."]
exclusions = ["No production harness, scheduler, model policy, service/profile, credentials, live-worker files, remote publication or old benchmark receipt changes."]
closure = "manual"
closure_actor = "interactive Pi audit"
closure_timestamp = "2026-10-24T05:39:40.635555+00:00"
closure_reason = "Completed local source/native audit and opt-in adapter regressions with focused checks and independent review. Production recovery/accounting repairs remain open dependency-linked tasks; no claim of live or integration qualification."
closure_evidence = "docs/research/pi-harness-audit-2026-10-24.md"
+++
- Sources: docs/research/pi-harness-audit-2026-10-24.md
- Validation scope: Affected selection at base 24df62b93b4164184e0a7346218580b95a69b88d selected all 138 modules solely because the new human audit document has no test mapping. Per focused-change repository instructions, run named adapter/triage/native tests and task validation, not the full suite. Do not claim an affected-suite pass.
- Evidence: Pi 1.4.0: 2 direct installed-native tests passed; 7 focused offline tests passed with 2 intentional native skips; premature-settlement and shared-review-session mutations failed as expected; missing-Pi task command fails closed; working-tree task validation and local Markdown targets passed. No model or live qualification.
- Review: Independent read-only review identified a stale typed native-check command; fixed and re-reviewed with no remaining blockers. Reviewer did not rerun native checks or external SDK research. No integration receipt.
