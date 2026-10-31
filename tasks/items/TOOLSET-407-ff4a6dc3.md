+++
schema = 1
id = "TOOLSET-407-ff4a6dc3"
title = "An installer keeps a Claude Code marketplace the owner already configured"
short = "Keep the configured Claude marketplace"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Now"
rank = 1000
depends_on = []
touches = ["scripts/install_menu.py", "tests/test_install_menu.py", "docs/installation.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "install.sh's Claude Code item must not fail when the user's Claude Code settings already list the autowork marketplace from another source, such as a local checkout, because Claude Code then refuses plugin marketplace add TrebuchetDynamics/autowork. Reuse that configured source, let the existing update step prove it is usable, and install the plugin. Do not change, remove or re-add the configured source, tolerate unrelated failures, or touch other hosts' items. Inspect the sources first and make only the bounded installer change with its fixture and documentation."
acceptance = ["A fixture whose claude plugin marketplace add exits 1 with the extraKnownMarketplaces source-mismatch text installs the plugin and reports the kept configuration; an unrelated marketplace add failure still fails the item and runs no install step.", "Existing install_menu items, ordering, dry-run, retry and report behaviour stay unchanged; the fixture writes no owner settings, marketplace entry or host configuration.", "docs/installation.md states that an already configured marketplace source is reused. python3 scripts/check.py tests/test_install_menu.py passes. This is offline installer evidence, not live plugin acceptance."]
checks = ["python3 scripts/check.py tests/test_install_menu.py", "./install.sh --only claude"]
exclusions = ["No changes to Claude Code settings, marketplace sources, other host items, host permissions, network behaviour, or any live plugin acceptance claim."]
closure = "manual"
closure_actor = "interactive session (owner-authorized install run)"
closure_timestamp = "2026-10-31T04:31:51.935687+00:00"
closure_reason = "Installer reuses an already configured Claude Code marketplace source instead of failing. Fixtures cover the kept source and an unrelated failure; python3 scripts/check.py tests/test_install_menu.py, tests/test_install.py and tests/test_repo_docs_graphify.py passed (38+install+2 tests). A real ./install.sh run installed the plugin from the configured local source. Live plugin behaviour in a new session remains unqualified."
closure_evidence = "./install.sh --only claude; python3 scripts/check.py tests/test_install_menu.py tests/test_install.py tests/test_repo_docs_graphify.py"
+++
