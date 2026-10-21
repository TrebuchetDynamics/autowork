+++
schema = 1
id = "TOOLSET-330-c2"
title = "Status, fleet JSON and the TUI show the effective service push setting"
short = "Show effective push setting (issue 4 follow-up)"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 22000
depends_on = ["TOOLSET-316-d5", "TOOLSET-324-73", "TOOLSET-325-d4"]
touches = ["pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/command.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 4 display slice split from TOOLSET-324-73: autowork status, autowork ls --json and the TUI show the effective push setting read from the service env. The start/settings and offline no-push acceptance remain in TOOLSET-324-73. The default (push on) is unchanged here; whether it becomes opt-in is a separate owner decision."
acceptance = ["status, ls --json and the TUI show the effective push setting read from the service env"]
checks = ["python3 scripts/check.py tests/test_autowork_command.py tests/test_pi_autowork.py pi-autowork/tests/test_fleet_view.py"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4; split from [TOOLSET-324-73](TOOLSET-324-73.md)
- Coordination: Owns verbatim the status/ls --json/TUI acceptance formerly in TOOLSET-324-73. Wait for the reported TOOLSET-316-d5 candidate (cli.py, fleet_view.py and component tests), the service-setting slice TOOLSET-324-73, and TOOLSET-325-d4 (cli.py and command/runner tests) before display edits. Touches includes tui.py because FleetApp renders runner details there (current model/fallback rendering at tui.py:833-836); fleet_view.py:collect reads service env settings and command.py:cmd_ls serializes Runner with dataclasses.asdict. Offline fixtures only; no push-default decision or live service change is authorized.
