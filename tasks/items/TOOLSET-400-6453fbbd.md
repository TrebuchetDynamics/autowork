+++
schema = 1
id = "TOOLSET-400-6453fbbd"
title = "Accept legitimate nullable main-check observations without weakening corruption guards"
short = "Read nullable check fields correctly"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["Src/pi_autowork/health.py", "pi-autowork/tests/test_health.py", "pi-autowork/tests/test_supervision_main_checks.py", "pi-autowork/README.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Repair the reproduced main-check writer/observation-reader mismatch. Exercise check_main_start through Coordinator.health_update and health.fleet using disposable state and fake subprocess/service dependencies; optional crashed and gated values written as null must not quarantine a valid runner. Audit the fields emitted by the actual writer, allow null only where the existing writer/consumer contract makes it optional, and retain required-field and wrong-non-null-type rejection. Keep healthy sibling collection, task snapshot rereads and malformed-source isolation intact. Implement regressions and only bounded local fixture/setup repairs needed by these checks; no live runtime input is required."
acceptance = ["Given the actual check_main_start writer with absent crash/gate history, when its running record passes through health publication and fleet reading, then crashed=null and gated=null remain readable and a healthy sibling stays visible. Add pi-autowork/tests/test_health.py::HealthTests.test_nullable_main_check_writer_round_trip (proposed, unrun), invoking the writer with fake process dependencies rather than only validating a hand-written record.", "Given valid non-null history and malformed optional/required fields, then valid strings retain behavior, wrong non-null types and missing required semantic values remain unavailable with source diagnostics, and reading changes no runtime bytes. Extend the same parameterized round-trip behavior and existing HealthTests.test_invalid_observation_values_do_not_prove_current_activity guards; include fleet collection and independent task inventory controls."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_health.py pi-autowork/tests/test_supervision_main_checks.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_task_snapshot.py", "python3 scripts/affected_tests.py --run", "git diff --check"]
exclusions = ["No other project files/tasks/configuration, real services or runner restart, model/device/production operation, install, remote publication or runtime record repair.", "No blanket null acceptance, weaker PID/start-tick/identity/freshness checks, admission/scheduler/receipt/claim change or reopening completed TOOLSET-399-1f9c37c3."]
+++
- Sources: docs/project.md#runner-observation-resilience
- Evidence: Source baseline 77e01425e21f404e681cac060d05c2baa1655070. supervision/main_checks.py::check_main_start writes crashed=record.get('crashed') and gated=record.get('gated'); Coordinator.health_update republishes them. health._validate_observation rejects present null values as non-strings. The earlier audit reproduced crashed=None rejection in memory; no implementation test has run.
- Planner decision: Field-specific compatibility repair, not removal of validation or a writer schema migration. Keep required rev/state values strict. Completed TOOLSET-399-1f9c37c3 is related prior work, not an open replacement task or newly verified regression attribution.
- Next action: Implement test_nullable_main_check_writer_round_trip with fake check process dependencies and observe RED on the current baseline; then repair validation and run focused checks. New fixture inputs and bounded local setup repairs belong to this task.
- Coordination: Independent of journal and reporting tasks; health/tests and README overlap the reporting task, so merge conflicts are possible but no product dependency or global exclusive resource is justified. Preserve existing goal focus and deferred TOOLSET-389/390 gates.
- Invariants: No current activity from invalid observations, no state repair, no execution-authority change; independently valid committed inventory remains readable.
- Qualification: Offline implementation only. Actual installed adoption/recovery remains unqualified and requires separately authorized Autowork-only live verification. No service operation is required to close this offline contract.
- Builder check: Fresh read-only reviewer: nothing important left. Actual writer-emitted optional fields are in the nullable audit; append-order/state replay, strict-reader preservation, null timings/rendering are specified; JSON/shared verdict and diagnostic-only idle consumers are covered. Inputs are task-owned disposable fixtures, checks are proposed/unrun rather than external blockers, and bounded setup repairs are allowed. No product dependencies; nullable/reporting overlap health.py and test_health.py, all share README, journal otherwise has a separate implementation lane. Preserve completed closures and deferred live pilots. Planner disposition: already answered; no scope change or new owner question. Readiness is not implementation or live authority.
