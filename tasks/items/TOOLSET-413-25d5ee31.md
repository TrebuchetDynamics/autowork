+++
schema = 1
id = "TOOLSET-413-25d5ee31"
title = "Disclose Plan With Me branch reference and deduplicate its adapter"
short = "Disclose Plan With Me reference"
status = "done"
goal = "SKILL-STYLE"
section = "Now"
rank = 1000
depends_on = []
touches = ["skills/plan-with-me/SKILL.md", "skills/plan-with-me/references/special-cases.md", "adapters/skills/plan-with-me/SKILL.md"]
resources = []
kind = "implementation"
ownership = "coordinator"
scope = "Apply the pinned writing-for-agents disclosure pass to Plan With Me. Move the branch-only audits, rolling-plan detail, method-gap routing and onboarding example into matching sections of skills/plan-with-me/references/special-cases.md behind live pointers. Cut the portable adapter to host translation plus the tested handoff, selection and recovery lines, with a pointer to the protocol. Remove the environment-cache sentence that restates the skill ID and source directory. Keep every tested phrase and every planning, authority, review and delivery rule."
acceptance = ["skills/plan-with-me/SKILL.md keeps the tested rolling-plan phrases, the blockers link, the handoff/selection phrases and every planning or authority rule; every new reference link resolves.", "skills/plan-with-me/references/special-cases.md owns the moved audit, rolling-plan, method-gap and onboarding-example detail; adapters/skills/plan-with-me/SKILL.md points to the protocol and keeps the tested host, grill-me, blockers, touches and recovery lines.", "python3 scripts/check.py tests/test_blockers.py tests/test_planning_cli_contract.py tests/test_workflow_commands.py tests/test_portable_package.py tests/test_task_touches_contract.py tests/test_planning_specimens.py passes, node --test tests/portable_pi.test.mjs passes, git diff --check is clean, pinned writing-for-agents upstream hashes are unchanged, and the local task is closed without push."]
checks = ["python3 scripts/check.py tests/test_blockers.py tests/test_planning_cli_contract.py tests/test_workflow_commands.py tests/test_portable_package.py tests/test_task_touches_contract.py tests/test_planning_specimens.py", "node --test tests/portable_pi.test.mjs", "git diff --check", "python3 -c \"import hashlib,json,pathlib; m=json.loads(pathlib.Path('skills/writing-for-agents/UPSTREAM.json').read_text())['files']; assert all(hashlib.sha256(pathlib.Path('skills/writing-for-agents', v['path']).read_bytes()).hexdigest()==v['sha256'] for v in m.values())\""]
exclusions = ["No changes to Plan With Me behavior, authority, host permissions, task-store semantics, installers or pinned upstream bytes; no push, live runner operation or model-behavior/token-savings claim."]
closure = "manual"
closure_actor = "owner"
closure_timestamp = "2026-10-31T15:12:49.958004+00:00"
closure_reason = "Plan With Me disclosure pass complete; targeted offline and portable checks passed; unrelated cron-autowork baseline failures remain; no push."
closure_evidence = "33ca1d5d39a3a51c8e737b282c6978e6ebe2c11e"
+++
- Sources: docs/contributing.md#skill-style
