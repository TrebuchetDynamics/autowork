+++
schema = 1
id = "TOOLSET-358-e756c4ed"
title = "fleet_view.collect, verdict and task_rows are split by concern"
short = "Decompose the fleet view builders"
status = "done"
goal = "CODE-HEALTH-2026-10"
section = "Next"
rank = 48000
depends_on = ["TOOLSET-330-c2", "TOOLSET-354-338c939f"]
touches = ["pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/test_fleet_view.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "fleet_view.collect (85 lines, cc 49), verdict (63, cc 39) and task_rows (cc 38) mix reading runner records, main-check state, questions and task rows. Split each by data source into small functions returning typed rows, so a change to one source (for example a new main-check state) edits one function. Behaviour-preserving: autowork ls --json output and every TUI label are byte-identical on the existing fixtures."
acceptance = ["collect, verdict and task_rows are each under 50 lines and cc 15", "pi-autowork/tests/test_fleet_view.py and tests/test_pi_autowork.py pass unchanged; an added fixture test compares ls --json before and after on a recorded state directory"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py tests/test_pi_autowork.py"]
exclusions = []
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-358-e756c4ed.toml"
+++

- Sources: docs/plans/structural-audit-2026-10.md#hotspots
