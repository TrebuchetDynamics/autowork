+++
schema = 1
id = "TOOLSET-353-9db87df7"
title = "Make automatic push opt-in for new repository runners"
short = "New repositories: explicit push grant"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 36000
depends_on = []
touches = ["pi-autowork/pi_autowork/", "tests/test_autowork_push_setting.py", "tests/test_autowork_command.py", "pi-autowork/README.md", "docs/cross-host.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Implement the owner decision on TOOLSET-326-fb: new repository runners default to no automatic push; an explicit per-repository grant is persisted and reused without asking on every cycle. Use the supported settings interface. Preserve existing saved settings and explicit publication permissions; do not migrate running services or infer a grant for another repository. Update the owning setup documentation after offline verification."
acceptance = ["A new repository fixture without a grant cannot push through either normal publication or upstream-sync publication.", "An explicit grant persists for one repository only, survives a later load, and does not require approval on each cycle.", "Existing saved on/off settings are byte-preserved unless explicitly edited for that repository; the effective setting is visible without lifecycle changes."]
checks = ["python3 scripts/check.py tests/test_autowork_push_setting.py tests/test_autowork_command.py"]
exclusions = ["No actual push or network publication, service lifecycle change, live profile/job settings, credential access or installed-runtime migration."]
+++

- Sources: tasks/items/TOOLSET-326-fb.md
