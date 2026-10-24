+++
schema = 1
id = "FLEET-OBSERVER-01"
title = "Distinguish explicitly verified read-only monitors from competing Hermes writers"
short = "Fix observer overlap refusal"
status = "open"
goal = "FLEET-RECOVERY"
section = "Now"
rank = 1000
depends_on = []
touches = ["Src/pi_autowork/cli.py", "Src/pi_autowork/service.py", "Src/pi_autowork/settings.py", "Src/pi_autowork/hermes_observers.py", "tests/test_pi_autowork.py", "tests/test_autowork_command.py", "tests/test_hermes_observers.py", "pi-autowork/README.md"]
resources = ["autowork-runtime-core"]
kind = "implementation"
ownership = "worker"
scope = "Repair the reproduced startup exit-4 false positive in hermes_jobs: an explicitly read-only progress monitor mentioning autowork is currently classified as a writer. Implement the smallest fail-closed per-repository mechanism for a reviewed observer identity and exact execution-contract binding, consistently consumed by installation and startup. Unknown, changed, ambiguous and development-writer jobs must still block. Do not infer harmlessness from prompt keywords alone or enable blanket ALLOW_HERMES. Keep local configuration private and examples generic. Read current source/tests and native service settings persistence before changing contracts. Deliver offline implementation/docs/tests only; operational activation and competing interactive-writer handoff remain separate."
acceptance = ["An offline fixture reproduces the current enabled read-only observer refusal; explicit correctly bound observer classification permits that observer without suppressing another active writer.", "Unknown identity, malformed exemption, changed workdir/prompt/skill/tool contract, duplicate or ambiguous identity and actual Autowork development-writer selection fail closed; paused/disabled jobs preserve current behavior.", "Settings survive supported service installation/restart paths without replacing unrelated policy. No private job IDs, profile identities, credentials or runtime state enter Git.", "Focused regression checks and independent review pass. Docs explain exact binding/review and invalidation, identify classification versus sandbox limits, and give a supported private configuration path without blanket bypass."]
checks = ["python3 scripts/affected_tests.py --run", "git diff --check"]
exclusions = ["No RPC branch integration/activation, model/provider changes, cron mutation, monitor renaming, upstream Hermes edits, global overlap bypass or disabling safety gates.", "No service restart, production access, trading, deployment, publication authority changes, forced cleanup, writer claim removal or interrupted-attempt reset.", "No prompt-only heuristic that can exempt an arbitrary writing job; no private runtime/profile data in fixtures."]
+++
- Sources: docs/plans/2026-10-24-fleet-recovery.md#observer-overlap-defect
