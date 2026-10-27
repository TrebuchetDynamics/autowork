+++
schema = 1
id = "PLANNING-AUTONOMOUS-01"
title = "Align Plan For Me recovery and portable handoff with Autowork ownership"
short = "Clarify decisive planner handoff"
status = "done"
goal = "TASK-STORE-HARDENING"
section = "Now"
rank = 4000
depends_on = []
touches = ["skills/plan-for-me/SKILL.md", "adapters/skills/plan-for-me/SKILL.md", "tests/test_planning_cli_contract.py", "docs/plans/planning-skills-current-autowork.md"]
resources = []
kind = "implementation"
ownership = "coordinator"
scope = "Extend the verified planning-skill work in the current isolated branch to Plan For Me. Preserve decisive engineering choices, no-goal discovery, complete batches and shared decision closure. Replace the native blanket fix-or-skip paragraph with evidence-based routing: decide in-scope planning choices; return an existing failed operation/task/attempt/candidate to the same coordinator for supported recovery; keep genuinely unavailable owner/external inputs pending without inventing authority, duplicating tasks or automatically splitting acceptance. Align native and portable entrypoints on committed selection versus runtime admission/dispatch and branch-local versus actual consumer inclusion. Portable capability/preparation guidance may link/reuse the existing Docs Sync flow without duplicating its conversion matrix or installing/updating during planning. Update focused source-contract tests and the existing evidence owner only."
acceptance = ["New or expanded tests/test_planning_cli_contract.py source guards fail on the baseline blanket fix-or-skip/automatic-split instruction and missing portable selection/runtime/delivery disclosure, then pass after the minimal changes. Existing Plan With Me tests continue to pass; both modes return existing failed task/attempt evidence rather than manufacturing a new plan or redispatch.", "Native/portable Plan For Me preserve discovery without an interview, planner-resolvable engineering choices, real dependency and live/owner boundaries, exact checks, literal JSON/CAS, complete-batch persistence and no execution inside standalone planning. Task splitting requires supported scoped evidence and preserves original acceptance/history; a runtime failure alone is not justification.", "Focused CLI/decision/discovery/decomposition/specimen checks and fresh independent review pass. Claims stay limited to instruction-source correctness; no measured model adherence, runtime recovery, publication or installation is implied. Canonical concurrent writer's staged/archive/journal-repair changes remain untouched."]
checks = ["python3 scripts/check.py tests/test_planning_cli_contract.py tests/test_planning_decision_closure.py tests/test_planning_decomposition_contract.py tests/test_plan_for_me_discovery.py tests/test_planning_specimens.py", "python3 scripts/affected_tests.py --run", "python3 pi-autowork/pi_autowork/command.py tasks validate --worktree .", "git diff --check"]
exclusions = ["No rewriting shared planning contracts, weakening owner/external/lease/attempt or qualification gates, adding schema/approval steps, forced acceptance splitting, recurring planning, task duplication, runtime/source evidence fabrication, external library or upstream Hermes changes. No canonical writer/index edits, push, installation or services in this slice."]
closure = "manual"
closure_actor = "pi"
closure_timestamp = "2026-10-27T02:59:27.818018+00:00"
closure_reason = "Bounded native/portable Plan For Me instruction alignment complete with RED/GREEN and fresh independent review; manual source closure only, not a coordinator receipt, installed adoption or model qualification."
closure_evidence = "docs/plans/planning-skills-current-autowork.md#planning-autonomous-01-checked-source-correction"
+++
- Sources: Current /goal improve both planning skills for Autowork; native/portable Plan For Me entrypoints; shared RESEARCH-PLAN/PLAN-HANDOFF decision and authority contracts; plan-for-me special-cases Blockers section; tests/test_planning_cli_contract.py.
- Evidence: Native/portable recovery taxonomy and handoff parity implemented; original task/candidate/acceptance and true external gates preserved. Static baseline RED8 tests30 assertion/subtest failures; complete GREEN30 focused tests. Fresh independent review found no blockers, verified31 links/anchors, independently reproduced baseline30/current0 assertions and reran25 tests. Parent reran8 CLI tests. No model-adherence, runtime recovery, canonical delivery, installation or publication is claimed; concurrent canonical staged work remains untouched.
- Planner call: This is a bounded alignment of existing policy, not a new workflow or questionnaire. Keep Plan For Me decisive for engineering and Plan With Me interactive for intent. Real physical access, signed artifacts or explicit scope restrictions cannot be wished away by a planner call; runtime unknown is not zero work. Worker chooses concise wording and focused assertions. No new interview or external permission prerequisite is needed.
- Prior slice: PLANNING-INTERACTIVE-01 is manually complete at 8fbb4419 with 22 focused tests, fresh review17 and parent CLI7. Its source files remain exact while this slice extends the other mode. The isolated branch includes main through f653f564; canonical main has another writer's staged/deleted and journal-repair files, so no integration may touch that checkout until safe.
- Verification boundary: Static RED/GREEN and existing fixture mechanics are source checks, not new model-performance evidence. Existing baseline/control samples were already safe. Model evaluation and installed/runtime adoption remain separate. One sole writer here, followed by fresh independent review; no edits to other preserved worktrees.
- Held by: interactive goal-mode instruction repair
