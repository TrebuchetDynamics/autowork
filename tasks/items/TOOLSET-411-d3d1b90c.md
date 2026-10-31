+++
schema = 1
id = "TOOLSET-411-d3d1b90c"
title = "Remove the cron-autowork skill"
short = "Delete cron-autowork"
status = "open"
goal = "SKILL-STYLE"
section = "Now"
rank = 1000
depends_on = []
touches = ["skills/cron-autowork", "adapters/skills/cron-autowork", "adapters/pi.mjs", "Src/autowork_runtime/telegram_menu_policy.py", "Src/autowork_runtime/bundle.py", "tests/test_cron_autowork.py", "tests/test_workflow_commands.py", "tests/test_telegram_menu_policy.py", "tests/portable_pi.test.mjs", "tests/test_portable_package.py", "tests/test_doctor_modes.py", "docs", "README.md", "CHANGELOG.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Delete the cron-autowork skill, its portable adapters, its Pi command, its Telegram menu priority and its documentation. Keep the autowork-start-notice.py pre-run script at its existing path because saved cron jobs and the plugin's provisioning reference it, and mark its folder as script-only so no host discovers a skill there. Add cron_autowork to the policy's retired names so existing menus drop it. Say how to schedule work without the skill."
acceptance = ["No skill folder, adapter, Pi command, menu priority or documented command remains for cron-autowork; the folder keeps only its pre-run script and a README that says it is not a skill.", "cron_autowork is in the menu policy retired set so a stored menu drops it, and the pre-run script path in CRON_SCRIPTS and its start-notice test still resolve.", "The affected offline checks pass: workflow commands, menu policy, start notice, doctor modes, portable package, bundle, plugin, Ponytail bundle, skill descriptions and node --test tests/portable_pi.test.mjs. This is offline evidence; no Hermes profile or saved job was changed."]
checks = ["python3 scripts/check.py tests/test_workflow_commands.py tests/test_telegram_menu_policy.py tests/test_start_notice.py tests/test_doctor_modes.py tests/test_portable_package.py tests/test_bundle.py tests/test_plugin.py tests/test_ponytail_bundle.py", "node --test tests/portable_pi.test.mjs"]
exclusions = ["No change to cron job contents, profile state, the start-notice script's behavior or path, Hermes timers, or any live schedule. No deletion of installed profile files by hand; the update path retires them."]
+++
