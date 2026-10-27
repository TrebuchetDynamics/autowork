+++
schema = 1
id = "SHARED-LANGUAGE-01"
title = "Apply ASD-STE100 and project glossary rules to all skill responses"
short = "Add shared writing rules"
status = "done"
goal = "SHARED-LANGUAGE"
section = "Next"
rank = 5000
depends_on = []
touches = ["skills/", "adapters/skills/", "tests/", "docs/", "README.md", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "coordinator"
scope = "Add one shared response policy and link every public skill to it. Use the target project glossary map and glossary. Preserve code, exact output formats, upstream files and prior uncommitted work."
acceptance = ["All native and portable entries directly link one shared ASD-STE100 and glossary policy.", "The policy survives package extraction and native provisioning; existing profile edits remain unchanged.", "Read-only probes preserve status facts, resolve the correct glossary, protect exact literals and no-write scope; independent review passes."]
checks = ["python3 scripts/check.py tests/test_ponytail_bundle.py tests/test_portable_package.py tests/test_skill_descriptions.py tests/test_install_skills.py tests/test_pi_toolset_bundle.py tests/test_engineering_vendor.py", "node --test tests/portable_pi.test.mjs"]
exclusions = ["No personal skills, upstream protocol edits, new glossary, live installation, commit or push. No claim of certified STE compliance."]
closure = "manual"
closure_actor = "interactive coding session"
closure_timestamp = "2026-10-27T17:48:18.063481+00:00"
closure_reason = "Shared writing rules and all 52 entry links are checked in the task working copy. The changes are not committed, merged or installed. Full ASD-STE100 compliance is not verified."
closure_evidence = "44 Python tests in 7 focused modules passed: /tmp/autowork-ste-python.log. Three package tests passed: /tmp/autowork-ste-pi.log. Fresh consumer probe da733fb6-b853-49b2-9e0b-7f4113019364 selected the supplied Billing glossary, kept literals and JSON format, preserved should versus must, kept delivery states distinct and applied the rule with Ponytail off. It made no changes. Reviewer 0e702cfa-4f9c-4490-a68f-b41da89cf4d8 found no defects; the probe requested in that review is complete. These are offline and sample-response checks, not formal compliance or live model qualification."
+++
- Sources: docs/contributing.md#add-or-update-a-skill
- Held by: interactive shared writing rule update
