+++
schema = 1
id = "TOOLSET-324-73"
title = "A runner honours requested service settings and does not push when disabled"
short = "Honour service push setting (issue 4)"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 20000
depends_on = []
touches = ["pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/command.py", "tests/test_autowork_command.py", "tests/test_autowork_push_setting.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 4: PI_AUTOWORK_PUSH=0 autowork start is silently ignored when the service env file already exists, and the runner pushes. autowork start must apply a requested PI_AUTOWORK_PUSH (and other service settings it accepts) to the service env file, or refuse naming the conflict, never ignore it. The default (push on) is unchanged here; whether it becomes opt-in is a separate owner decision."
acceptance = ["autowork start with PI_AUTOWORK_PUSH=0 on a repository whose service env file says push on either writes 0 to it or exits non-zero naming the conflict; it never starts with the old value silently", "A runner whose effective setting is 0 makes no push and no upstream sync push in an offline test with a bare upstream (sync_upstream and push both)"]
checks = ["python3 scripts/check.py tests/test_autowork_command.py tests/test_autowork_push_setting.py", "python3 scripts/check.py tests/test_pi_autowork.py"]
exclusions = []
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/4
- Coordination: Split the unchanged display acceptance into TOOLSET-330-c2. command.py:cmd_start and service.py:run own the start/settings fix. coordinator.py:sync_upstream and push already return immediately for PI_AUTOWORK_PUSH=0 (current lines 1255-1256 and 1280-1281): retain and prove both guards with a disposable bare upstream in the new tests/test_autowork_push_setting.py module. scripts/check.py discovers direct tests/test_*.py modules; keep tests/test_pi_autowork.py as a read-only regression check, not a write target, because newer live TOOLSET-328-2e owns it (canonical task source: commit ecd00ba6d5b474b8b0998a893c81f13bd72e7c0d). No coordinator.py change is needed for these existing guards; reported TOOLSET-320-10 owns that file. This slice does not edit cli.py, fleet_view.py, tui.py or component tests, so it is disjoint from reported TOOLSET-316-d5 candidate c1e94f7d07bef1d6ad89d769257c376de805c189. The display follow-up stays open; completing this task alone does not complete all of issue 4.
