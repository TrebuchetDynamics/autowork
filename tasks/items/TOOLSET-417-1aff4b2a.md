+++
schema = 1
id = "TOOLSET-417-1aff4b2a"
title = "Give the remaining native skills a real interview boundary"
short = "Give the remaining native skills a real intervie"
status = "open"
goal = "SKILL-STYLE"
section = "Next"
rank = 3000
depends_on = []
touches = ["tests/test_skill_standard.py"]
resources = []
kind = "plan"
ownership = "worker"
scope = "Several skills name no sibling because they have none; confirm each blank case (apk-get, ponytail-gain, profile-create) is genuinely unpaired or name the sibling that fits, so the boundary table in docs/skill-standard.md stays true. Acceptance: the table and the skills agree, and the standard test still passes."
checks = ["python3 scripts/check.py tests/test_skill_standard.py"]
exclusions = ["No new skill, no upstream edit, no authority change, no model-behavior claim."]
+++
