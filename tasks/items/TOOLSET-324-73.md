+++
schema = 1
id = "TOOLSET-324-73"
title = "A runner pushes only as its effective settings say, and status shows it"
short = "Push setting honoured and shown (issue 4)"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 20000
depends_on = []
touches = ["pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/command.py", "pi-autowork/pi_autowork/coordinator.py", "pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/fleet_view.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 4: PI_AUTOWORK_PUSH=0 autowork start is silently ignored when the service env file already exists, and the runner pushes. autowork start must apply a requested PI_AUTOWORK_PUSH (and other service settings it accepts) to the service env file, or refuse naming the conflict, never ignore it. autowork status, autowork ls --json and the TUI show the effective push setting. The default (push on) is unchanged here; whether it becomes opt-in is a separate owner decision."
acceptance = ["autowork start with PI_AUTOWORK_PUSH=0 on a repository whose service env file says push on either writes 0 to it or exits non-zero naming the conflict; it never starts with the old value silently", "status, ls --json and the TUI show the effective push setting read from the service env", "A runner whose effective setting is 0 makes no push and no upstream sync push in an offline test with a bare upstream (sync_upstream and push both)"]
checks = ["python3 scripts/check.py tests/test_autowork_command.py tests/test_pi_autowork.py pi-autowork/tests/test_fleet_view.py"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4
