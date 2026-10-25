+++
schema = 1
id = "TOOLSET-398-debf452f"
title = "Close consequential planning decisions before declaring tasks ready"
short = "decision closure"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Now"
rank = 13000
depends_on = []
touches = ["skills/shared/RESEARCH-PLAN.md", "skills/shared/PLANNING-CRAFT.md", "skills/shared/PLAN-HANDOFF.md", "tests/test_planning_decision_closure.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Implement the shared decision-closure procedure in the cited plan: classify material choices, resolve engineering choices with evidence, disposition every builder finding, and check reachable inputs and verification without widening authority."
acceptance = ["New focused source-contract tests cover already-answered, planner-resolvable, worker-reversible and owner/external-blocked findings; shared guidance requires a disposition for every material finding before ready status.", "The guidance resolves consequential delegated engineering choices, keeps exact missing intent/authority/input on affected tasks only, and distinguishes reachable checks from task metadata validity.", "Source guards preserve Plan With Me interaction, standalone/no-write/coordinator boundaries, lightweight clear tasks, real live qualification, task-owned fixture creation and existing schemas."]
checks = ["python3 scripts/check.py tests/test_planning_decision_closure.py tests/test_planning_cli_contract.py tests/test_planning_decomposition_contract.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No runtime/schema/scheduler changes, new approval systems, live operations, installation or publication.", "Do not infer owner authorization, relax acceptance or change unrelated tasks/skills."]
closure = "manual"
closure_actor = "pi"
closure_timestamp = "2026-10-25T20:59:26.759540+00:00"
closure_reason = "Explicit later execution instruction; scoped implementation and independent review complete; composed 45-test offline check passed. Manual closure, not model/live qualification."
closure_evidence = "docs/plans/planning-skills-current-autowork.md#explicit-execution-and-checked-implementation"
+++
- Sources: docs/plans/planning-skills-current-autowork.md#closure-contract
- Decisions and handoff: Produces: shared decision-closure procedure consumed by TOOLSET-398-472870c6. Start by adding the failing focused contract tests named in Acceptance. Planner call: an existing prose decision map and four finding dispositions, not a new gate/schema. Local test creation is in scope; no external input is required. Contract tests do not prove model adherence.
- Verification: Commands are proposed/unrun during planning. Use --base REV for affected tests when the implementation change base is not origin/main. Review the bounded diff independently; no static test proves fewer model stalls.
