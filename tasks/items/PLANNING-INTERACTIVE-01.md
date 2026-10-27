+++
schema = 1
id = "PLANNING-INTERACTIVE-01"
title = "Align Plan With Me handoff wording with Autowork selection and execution authority"
short = "Clarify interactive handoff"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Now"
rank = 1000
depends_on = []
touches = ["skills/plan-with-me/SKILL.md", "adapters/skills/plan-with-me/SKILL.md", "skills/plan-with-me/references/special-cases.md", "tests/test_planning_cli_contract.py", "docs/plans/planning-skills-current-autowork.md"]
resources = []
kind = "implementation"
ownership = "coordinator"
scope = "Improve existing native and portable Plan With Me instructions without changing the interactive planning workflow or adding approval machinery. Correct native wording that tasks why proves a task can run, disclose branch-local versus canonical consumer delivery and runtime/admission limits in both entrypoints, and remove the special-case implication that a ready continuation can execute inside standalone planning. Reuse shared decision closure and single-pass handoff; preserve settled user answers, planner calls, pending affected work, existing task IDs and same-coordinator continuation. Update the existing planning owner with actual verification and limits. No unrelated shared-skill rewrite."
acceptance = ["Instruction-contract regressions first fail on native selection-as-can-run wording and continuation-inside-planning ambiguity, then pass for both native and portable handoffs. Public task CLI examples still validate. Existing interactive, decision closure, decomposition and no-write authority tests remain green.", "Both entrypoints explicitly distinguish committed-store selection, admission, dispatch and actual consumer delivery. Runtime observation failure returns existing task/attempt evidence to the same coordinator for supported recovery, not a new product interview or replacement task. Existing fully specified and unresolved intent interview behavior remains intact.", "Focused checks, link/readback inspection and fresh independent review pass. Small baseline/control model samples are reported honestly: no authorization failure was observed, so no measured compliance/speedup or model-adherence qualification is claimed. Publication/installation are separate and not requested by this slice."]
checks = ["python3 scripts/check.py tests/test_planning_cli_contract.py tests/test_planning_decision_closure.py tests/test_planning_decomposition_contract.py tests/test_planning_specimens.py", "python3 scripts/affected_tests.py --run", "python3 pi-autowork/pi_autowork/command.py tasks validate --worktree .", "git diff --check"]
exclusions = ["No task schema, scheduler, service, runtime-state, credentials, devices, model selection, upstream Hermes or unrelated partial source edits; no new interview quota, mandatory approval, planning daemon or auto-execution grant. No remote push, installation or live qualification in this slice."]
closure = "manual"
closure_actor = "pi"
closure_timestamp = "2026-10-27T02:43:11.164899+00:00"
closure_reason = "Bounded instruction-source implementation and offline checks complete with independent review; manual closure, not a coordinator receipt, model qualification or installed-runtime proof."
closure_evidence = "docs/plans/planning-skills-current-autowork.md#planning-interactive-01-checked-source-correction"
+++
- Sources: Current owner request to improve plan_with_me skills for Autowork; skills/plan-with-me/SKILL.md Save answers and finish the plan; references/special-cases.md Continuations and live gates; adapters/skills/plan-with-me/SKILL.md; shared/PLAN-HANDOFF.md and shared/RESEARCH-PLAN.md.
- Evidence: Native/portable handoff and continuation wording corrected; three source-contract regressions failed against baseline, then 22 focused tests passed. Independent review found no blockers and reran 17 tests; parent reran all seven public CLI contract tests. Ten baseline/control model samples were already safe, so no improved model-adherence claim. Source archive and unchanged links independently verified. No source deployment or installation is asserted.
- Baseline: Five current-instruction and five no-guidance fresh samples preserved branch-only selection/runtime unknown and no-execution boundaries in the supplied scenario. No observed model authorization failure; model-compliance improvement is unreplicated. Harness acceptance wrappers are not a planning result or scoring evidence. Local run identities dd06022b-d251-41f3-bc86-ee6a3fe2ab1d and 4e8d5087-07db-427b-bd18-70e66a7eadec. No private fixture/runtime identity is needed in public instructions.
- Planner calls: Prefer small corrections and concise explicit existing handoff semantics over a new checklist or approval framework. Keep every accepted answer, dependency, ownership and operation gate. Unknown execution is not an empty queue or missing product intent. Deferred owner/external inputs stay scoped to affected work; branch commits do not claim canonical integration.
- Builder disposition: Local instruction-contract tests and shared references exist; no external prerequisites. Model baseline had no failure, so static RED/GREEN contracts can prove source correction only, not improved adherence. Worker chooses concise wording and focused assertions, then fresh reviewer checks semantic consistency.
- Delivery: Isolated implementation; no edits to the preserved campaign-input-boundaries checkout or pending fleet-recovery planning branch. Local commits/integration may follow checked work under repository rules; no remote publication or installer changes are implied.
- Held by: interactive instruction repair
