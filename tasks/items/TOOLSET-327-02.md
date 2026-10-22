+++
schema = 1
id = "TOOLSET-327-02"
title = "Play on a repository without a task store offers to prepare it through autowork tasks prepare"
short = "Prepare from Play in the TUI (issue 9)"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 41000
depends_on = ["TOOLSET-316-d5"]
touches = ["pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/test_fleet_view.py", "pi-autowork/tests/tui_pilot.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 9 (onboarding part; the tree and Play already share fleet_view.readiness): in the TUI New browser, Play on a repository that is not ready shows only a notice. Offer Prepare (and Prepare and start) that runs autowork tasks prepare on it and shows the outcome code and next step. A legacy repository converts or defers; NO_STORE says to plan with Docs Sync and never invents goals or tasks; MIGRATION_DEFERRED, MIGRATION_BLOCKED and TOOLCHAIN or INVALID outcomes are shown as they are, never as ready. Start runs only after readiness passes."
acceptance = ["In a headless TUI test, Play on a legacy repository offers Prepare; choosing it converts the repository and the node then shows ready", "On a repository with no accepted intent, Prepare reports NO_STORE and creates no task file", "On a repository with work in flight, Prepare reports MIGRATION_DEFERRED and Start stays unavailable"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py tests/test_task_prepare.py"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/9
- Dependencies: TOOLSET-316-d5
- Touches: pi-autowork/pi_autowork/tui.py, pi-autowork/pi_autowork/fleet_view.py, pi-autowork/tests/test_fleet_view.py, pi-autowork/tests/tui_pilot.py
- Coordination: Wait for TOOLSET-316-d5: its reported candidate c1e94f7d07bef1d6ad89d769257c376de805c189 changes fleet_view.py and tests/test_fleet_view.py (Git common execution directory: slot-data/TOOLSET-316-d5/attempt-1/report.json). That candidate supplies setup labels, not the Prepare action; BrowseScreen.action_start still only notifies when unready. Do not edit the reported task or merge this acceptance into it. There is no useful disjoint split: the Prepare, NO_STORE and MIGRATION_DEFERRED cases all need the BrowseScreen flow in tui.py and its headless fixtures, while 316-d5 also declares tui.py and the component tests directory. Keep all three acceptance items here and preserve Next priority. Include tests/tui_pilot.py in Touches: test_fleet_view.py:test_the_tui_drives_the_same_actions_headless invokes that helper, which already exercises BrowseScreen Play and is the existing fixture to extend. Sources and acceptance remain unchanged.
- Reopened: its landing broke the full check on main at 9cb0dfa: test_pi_autowork.EngineTests.test_a_stalled_service_says_so_once_and_the_fleet_view_shows_why; reverted by optimistic landing. Fix those tests in the next attempt
