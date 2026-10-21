+++
schema = 1
id = "TOOLSET-327-02"
title = "Play on a repository without a task store offers to prepare it through autowork tasks prepare"
short = "Prepare from Play in the TUI (issue 9)"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 22000
depends_on = []
touches = ["pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 9 (onboarding part; the tree and Play already share fleet_view.readiness): in the TUI New browser, Play on a repository that is not ready shows only a notice. Offer Prepare (and Prepare and start) that runs autowork tasks prepare on it and shows the outcome code and next step. A legacy repository converts or defers; NO_STORE says to plan with Docs Sync and never invents goals or tasks; MIGRATION_DEFERRED, MIGRATION_BLOCKED and TOOLCHAIN or INVALID outcomes are shown as they are, never as ready. Start runs only after readiness passes."
acceptance = ["In a headless TUI test, Play on a legacy repository offers Prepare; choosing it converts the repository and the node then shows ready", "On a repository with no accepted intent, Prepare reports NO_STORE and creates no task file", "On a repository with work in flight, Prepare reports MIGRATION_DEFERRED and Start stays unavailable"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py tests/test_task_prepare.py"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/9
