+++
schema = 1
id = "PI-TOOLSET-SPECIALISTS-01"
title = "Bundle four reviewed instruction-only specialists on all hosts"
short = "Bundle pi-toolset specialists"
status = "done"
goal = "PI-TOOLSET-SPECIALISTS"
section = "Next"
rank = 5000
depends_on = []
touches = ["skills/", "adapters/", "tests/", "docs/", "README.md", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "coordinator"
scope = "Add pinned bug-harvest, autonomous-codebase-improver, skill-folder-refactor and unused-code instructions, portable adapters and Pi aliases with existing Ponytail and task-store authority."
acceptance = ["Pinned source hashes and MIT licenses preserved; no upstream executable surface imported.", "Native provisioning, portable resource closure, explicit-only metadata and literal Pi command dispatch verified offline.", "Read-only decision probes and independent review disclose scope and live-evidence limits."]
checks = ["python3 scripts/check.py tests/test_pi_toolset_bundle.py tests/test_plugin.py tests/test_portable_package.py tests/test_ponytail_bundle.py tests/test_skill_descriptions.py tests/test_install_skills.py tests/test_native_provisioning.py", "node --test tests/portable_pi.test.mjs"]
exclusions = ["No personal/global skill changes, live installation, service activation, push or deployment."]
closure = "manual"
closure_actor = "interactive coding session"
closure_timestamp = "2026-10-27T17:17:51.130798+00:00"
closure_reason = "Offline implementation accepted in the task worktree after independent review; not committed, integrated, installed live or pushed."
closure_evidence = "42 Python tests across 7 focused modules passed; 3 Node dispatch/package/archive tests passed; 12 imported resources match pinned Git objects; read-only before/after probes establish four new reachable specialist routes and correct scoped decisions, not live execution; fresh reviewer 72bc45d4-7f68-493e-8be4-d5342c08b351 found no issues. Logs: /tmp/autowork-pi-toolset-focused.log and /tmp/autowork-pi-toolset-pi.log."
+++
- Sources: docs/cross-host.md#pi-toolset-specialists
- Held by: interactive skill integration; implementation and review in feat/pi-toolset-skills
