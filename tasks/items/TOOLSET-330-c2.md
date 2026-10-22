+++
schema = 1
id = "TOOLSET-330-c2"
title = "Status, fleet JSON and the TUI show the effective service push setting"
short = "Show effective push setting (issue 4 follow-up)"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 22000
depends_on = ["TOOLSET-316-d5", "TOOLSET-324-73", "TOOLSET-325-d4"]
touches = ["pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/command.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 4 display slice split from TOOLSET-324-73: autowork status, autowork ls --json and the TUI show the effective push setting read from the service env. The start/settings and offline no-push acceptance remain in TOOLSET-324-73. The opt-in question this slice used to leave open is decided and landed under TOOLSET-353-9db87df7 (e5162924): a repository without a PI_AUTOWORK_PUSH=1 grant stays local (coordinator.py:1403, 1429), so this task displays that landed setting and never re-decides it. `autowork status` already prints it from cli.py:summarize (cli.py:439-440); the missing paths are `ls --json` (command.py:cmd_ls serializes fleet_view.Runner, which has no push field) and the TUI."
acceptance = ["status, ls --json and the TUI show the effective push setting read from the service env"]
checks = ["python3 scripts/check.py tests/test_autowork_command.py tests/test_pi_autowork.py pi-autowork/tests/test_fleet_view.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-330-c2.toml"
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4; split from [TOOLSET-324-73](TOOLSET-324-73.md)
- Correction: 2026-10-22 contradiction repair: the earlier sentence "the default (push on) is unchanged; whether it becomes opt-in is a separate owner decision" was overtaken by TOOLSET-353-9db87df7 and is replaced above. The status row is already delivered by that landed grant display, so the remaining Acceptance work is ls --json and the TUI (not a second status change). Acceptance, Touches, Checks and rank are unchanged.
- Coordination: Owns verbatim the status/ls --json/TUI acceptance formerly in TOOLSET-324-73. Wait for the reported TOOLSET-316-d5 candidate (cli.py, fleet_view.py and component tests), the service-setting slice TOOLSET-324-73, and TOOLSET-325-d4 (cli.py and command/runner tests) before display edits. Touches includes tui.py because FleetApp renders runner details there (current model/fallback rendering at tui.py:833-836); fleet_view.py:collect reads service env settings and command.py:cmd_ls serializes Runner with dataclasses.asdict. Offline fixtures only; no push-default decision or live service change is authorized.
