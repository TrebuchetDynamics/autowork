+++
schema = 1
id = "TOOLSET-369-b5db2d3a"
title = "Main-check supervision has a Src feature owner behind unchanged Coordinator methods"
short = "Extract Src main-check supervision"
status = "done"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 11000
depends_on = ["TOOLSET-375-8e02693d"]
touches = ["Src/pi_autowork/coordinator.py", "Src/pi_autowork/supervision/__init__.py", "Src/pi_autowork/supervision/main_checks.py", "pi-autowork/tests/test_supervision_main_checks.py", "pi-autowork/tests/test_main_check.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "After runner relocation, extract exactly the eleven enumerated supervision implementations into Src/pi_autowork/supervision/main_checks.py, empty initializer and unchanged Coordinator signatures in canonical Src coordinator. Pass owner/current git keyword-only; reuse-result additionally receives current planning_path. Keep policy/state/locks in Coordinator and internal phase calls through owner methods; selected public main-check command comes from Layout, not relocated __file__."
acceptance = ["Proposed test_supervision_main_checks.py characterizes facade signatures and late-bound git/planning_path/phase override seams before and after extraction; existing wait/reap/reload/port/reuse/receipt ordering assertions stay intact.", "Existing AST phase/complexity guards follow actual Src implementations, not wrappers; local/relative reverse-import, empty-init and no-side-effect import cases remain effective.", "Existing process/lock/cleanup/result behavior and actual Src entrypaths pass focused/affected checks; no second owner, helper state or reliability-policy redesign is introduced."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_supervision_main_checks.py pi-autowork/tests/test_main_check.py tests/test_src_entrypoints.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No behavior/schema/state/receipt/lock/authority changes, production source duplication, mixed-release fallback, extra approval system, unrelated refactor/test relocation, installs/profile edits, live services/models/jobs, publication or worker interruption. Preserve standalone hook copies."]
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-369-b5db2d3a.toml"
+++
- Sources: docs/plans/structural-audit-2026-10.md#main-check-supervision--existing-toolset-369-b5db2d3a
- Skill application: User-selected SDD; skills/engineering/upstream/skills/spec-driven-development/PROTOCOL.md@1be8e34187e34647bb83adc3a1323b26ae6f6abe, verified hash c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef. Specify ownership/interfaces and behavior-to-oracle contracts before moving code; keep native task store/authority, no upstream human phase gates. Router passed; implementation and new tests NOT_CHECKED.
- Planner call: User explicitly added root Src/ (capital S), superseding only the old no-source-root-migration planner choice; preserve completed 355-359 and reuse existing IDs. SDD protocol 1be8e34187e34647bb83adc3a1323b26ae6f6abe, hash c4b97ce3d7f24be0e67fd612c7595f65504872e3a9f8d338d098b2363fdb66ef. Interfaces/behavior oracles specified before movement; no upstream human checkpoints. All implementation tests are proposed/unrun and in scope to create.
- Next action: Characterize the named compatibility seam, implement only this task on the current canonical source, then run its Checks. Proposed fixtures are owned deliverables, not missing external inputs.
- Consumes: TOOLSET-375-8e02693d: canonical Src/pi_autowork package/engine, same-object old aliases and Layout public entrypoint/implementation paths.
- Prior builder check: Independent reviewer found one missing planning_path binding; resolved by explicit keyword-only predicate injection in the reuse helper, preserving coordinator policy ownership and late-bound patch behavior. No other material unknowns reported; foundation then two parallel feature extractions confirmed.
- Owner decision: Owner added Src/ in the current standalone planning request; scope amendment only, not execution or runtime activation authority.
- Evidence: Refreshed against canonical 34aca3f6487eda7d0c45589cdd4c1b33cbe2d3fa and independent read-only current-source reviews; no implementation, product tests, installed-copy or live qualification in this occurrence.
- Planning scope: Owner selected both instruction fixes and Src refresh, instruction fixes first; this occurrence saves metadata only, not execution.
- Delivery: Saved planning; consumer inclusion/selection must be checked separately from implementation and dispatch.
