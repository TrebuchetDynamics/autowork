+++
schema = 1
id = "TOOLSET-359-faf935a9"
title = "Remove the command/task_prepare/fleet_view import cycle"
short = "Break the task_prepare import cycle"
status = "open"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 49000
depends_on = ["TOOLSET-354-338c939f", "TOOLSET-318-17"]
touches = ["pi-autowork/pi_autowork/task_prepare.py", "pi-autowork/pi_autowork/command.py", "pi-autowork/pi_autowork/fleet_view.py", "tests/test_task_prepare.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "task_prepare.prepare imports command and fleet_view inside the function (task_prepare.py around line 294) while command imports task_prepare and fleet_view imports task_prepare at module level: the package's only import cycle, closed through function-level imports. Move what prepare needs from command and fleet_view (service and readiness lookups) below both modules, or pass it in, so every import is at module level and the dependency graph is acyclic. No behaviour change; no re-export shim."
acceptance = ["A test imports every pi_autowork module in isolation and asserts the import graph (module-level and function-level) has no cycle", "tests/test_task_prepare.py, pi-autowork/tests/test_fleet_view.py and tests/test_autowork_command.py pass unchanged"]
checks = ["python3 scripts/check.py tests/test_task_prepare.py pi-autowork/tests/test_fleet_view.py tests/test_autowork_command.py"]
exclusions = []
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
