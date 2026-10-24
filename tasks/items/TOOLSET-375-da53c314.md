+++
schema = 1
id = "TOOLSET-375-da53c314"
title = "Native planning commands inject the current task-store handoff without changing user arguments"
short = "Correct injected planning queue"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Now"
rank = 1000
depends_on = []
touches = ["__init__.py", "tests/test_plugin.py", "tests/test_workflow_commands.py", "tests/test_plan_for_me_discovery.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Replace only stale native queue injection with tasks/ through Docs Sync/autowork tasks; preserve existing command/namespace applicability, literal arguments, aliases/challenge, authority and origin behavior. Extend existing public invocation tests, not routing architecture. Preserve current bare-command autonomous project-discovery marker and regression assertions."
acceptance = ["Existing test_plugin and test_workflow_commands cases assert actual native injected messages use tasks/ and the task CLI without imperative TODO/goals writes.", "Literal arguments mentioning old filenames/shell-like prose survive unchanged; foreign namespaces and existing alias/origin/no-write/no-execution assertions stay intact. Existing test_plan_for_me_discovery.py guards remain intact.", "Focused and selected affected checks pass without new runtime policy, destination guessing, command scope expansion or installation."]
checks = ["python3 scripts/check.py tests/test_plugin.py tests/test_workflow_commands.py tests/test_plan_for_me_discovery.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No new task/schema/allocator/scheduler/closure mechanism, legacy queue, approval system, broad refactor, force conversion, install/profile copy, model evaluation, service/job/worker interruption, publication or live qualification. Planning does not implement or dispatch."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-375-da53c314.toml"
+++
- Sources: docs/plans/planning-skills-current-autowork.md#task-a-correct-the-injected-planning-request
- Planner call: Delegated routine compatibility choices, not separately selected owner options; preserve mandatory checks, IDs, ranks and owner stops.
- Next action: Extend the named existing seam or create the proposed focused guard, implement only this slice, then run Checks on the actual implementation base.
- Evidence: Refreshed against canonical 34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa and independent read-only current-source reviews; no implementation, product tests, installed-copy or live qualification in this occurrence.
- Planning scope: Owner selected both instruction fixes and Src refresh, instruction fixes first; this occurrence saves metadata only, not execution.
- Delivery: Saved planning; consumer inclusion/selection must be checked separately from implementation and dispatch.
- Produces: Correct current task-store injected request with preserved bare-discovery, argument, namespace and origin contracts, consumed by TOOLSET-376-49034161.
