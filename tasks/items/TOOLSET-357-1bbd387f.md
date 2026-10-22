+++
schema = 1
id = "TOOLSET-357-1bbd387f"
title = "The worker's full-check gate is split into verdict, evidence and prompt builders with table-driven tests"
short = "Decompose the worker gate"
status = "open"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 47000
depends_on = ["TOOLSET-338-82"]
touches = ["pi-autowork/pi_autowork/worker.py", "pi-autowork/tests/test_gate_command.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "worker._run_gate (90 lines, cc 41), gate_note (55, cc 40) and verify_batch (101, cc 36) decide which trees land. Separate the pure verdict (merged result, reruns, base result -> pass or reason) from running suites and writing receipts, and the prompt text from the receipt validation in gate_note, so each decision is a function of its inputs with a table-driven test over recorded receipt fixtures (pass, flaky-excused, incomplete, crash on base, new failures, legacy record). Behaviour-preserving: same reasons, same receipts."
acceptance = ["A table-driven test feeds recorded gate inputs to the pure verdict function and asserts each documented reason string", "_run_gate, gate_note and verify_batch are each under 50 lines and cc 15", "tests/test_gate_command.py, tests/test_pi_autowork.py and pi-autowork/tests/test_optimistic.py pass unchanged"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_gate_command.py pi-autowork/tests/test_optimistic.py tests/test_pi_autowork.py"]
exclusions = []
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
