+++
schema = 1
id = "TOOLSET-398-2d05d7ae"
title = "Add planning specimens for late decision and prerequisite stalls"
short = "stall specimens"
status = "open"
goal = "TASK-STORE-HARDENING"
section = "Now"
rank = 14000
depends_on = []
touches = ["tests/fixtures/planning/scenarios.py", "tests/fixtures/planning/README.md", "tests/test_planning_specimens.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Extend the existing disposable planning specimens and manual rubric with both entrypoints for evidence-resolvable technical choice, local fixture repair, unavailable external input beside independent work, owner-only destructive scope, and builder-finding closure."
acceptance = ["Existing specimen tests verify five synthetic stall cases for each native/portable entrypoint, valid native-store seeds and reuse/preservation of existing records; no private fleet data is introduced.", "Offline tests retain forbidden code/test/skill/receipt/Git-write and no-write protections; the README states these mechanics do not grade model decision quality.", "The manual rubric evaluates saved decisions/evidence, precise pending inputs, independent tasks, exact checks and builder-finding disposition from actual traces and source hashes; missing model runs remain unrun rather than scored passes."]
checks = ["python3 scripts/check.py tests/test_planning_specimens.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No runtime/schema/scheduler changes, new approval systems, live operations, installation or publication.", "Do not infer owner authorization, relax acceptance or change unrelated tasks/skills."]
+++
- Sources: docs/plans/planning-skills-current-autowork.md#stall-focused-evaluation-specimens
- Decisions and handoff: Independent lane: fixture specification is fixed in the cited plan and needs no implementation output from the instruction slices. Start with failing mechanics tests in tests/test_planning_specimens.py, then add seeds/rubric. Planner call: extend the existing builder, not a new automated semantic grader. No paid/live model run, installation or provider configuration is needed for offline completion.
- Verification: Commands are proposed/unrun during planning. Use --base REV for affected tests when the implementation change base is not origin/main. Review the bounded diff independently; no static test proves fewer model stalls.
