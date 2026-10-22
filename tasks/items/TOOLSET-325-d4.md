+++
schema = 1
id = "TOOLSET-325-d4"
title = "An unusable repository stops the service with a needs-attention exit instead of restarting every 60 s"
short = "No restart loop on an unusable repo (issue 6)"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 21000
depends_on = ["TOOLSET-316-d5", "TOOLSET-324-73"]
touches = ["pi-autowork/pi_autowork/cli.py", "pi-autowork/pi_autowork/service.py", "pi-autowork/pi_autowork/health.py", "tests/test_autowork_command.py", "tests/test_pi_autowork.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "GitHub issue 6: when repository discovery or setup fails the runner exits 2, which the unit's RestartPreventExitStatus=1 3 4 does not cover, so systemd restarts it every 60 s forever. Setup failures that a restart cannot fix (not a Git repository, detached HEAD, wrong branch, missing tools, invalid --workers) exit with a code the unit treats as a deliberate stop, and record the reason where status and the TUI show it. Before any write, the runner checks the repository identity it resolved (git common dir and toplevel) against its configured repository, with inherited GIT_* variables removed from that check."
acceptance = ["Each setup failure above exits with a deliberate-stop code listed in the generated unit's RestartPreventExitStatus; a test reads the generated unit and the exit code together", "autowork status shows the stop reason for such a runner", "An inherited GIT_DIR or GIT_WORK_TREE pointing elsewhere does not make the runner act on another repository: offline fault-injection test on disposable repositories leaves the canonical fixture checkout unchanged"]
checks = ["python3 scripts/check.py tests/test_autowork_command.py tests/test_pi_autowork.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-325-d4.toml"
+++

- Sources: https://github.com/TrebuchetDynamics/autowork/issues/6
- Coordination: Wait for TOOLSET-316-d5 to land its reported cli.py change (candidate c1e94f7d07bef1d6ad89d769257c376de805c189; slot-data/TOOLSET-316-d5/attempt-1/report.json in the Git common execution directory), then TOOLSET-324-73 for shared service.py and tests/test_autowork_command.py. Issue 6 setup exits, stop-reason reporting and the pre-write repository identity guard remain one checked startup path in cli.py:main; no acceptance is dropped or delivered by the display-only 316-d5 candidate. TOOLSET-330-c2 follows this task for shared cli.py and status tests; no Now priority is changed.
- Next action: 2026-10-21 blocker diagnosis: preserve reported first-attempt commit 16ffb2039f9e52337731c2bbfd88be28832b2bc9 and all staged changes in the retained retry worktree. The retry worker is gone and attempt 2 has no final report; its log records Pi extension/MCP loading errors, not a completed failing suite. The existing Pi execution owner must diagnose that startup boundary and recover the same task, retaining its code and required checks. Do not discard staged work, manufacture a report, reverify an old commit as if it included the retry, or launch a competing repair worker.
