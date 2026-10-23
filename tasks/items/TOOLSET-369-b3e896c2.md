+++
schema = 1
id = "TOOLSET-369-b3e896c2"
title = "The TUI offers Force for a legacy repository, shows the whole refusal and the forced step, and marks legacy planning honestly"
short = "TUI: Force, full refusals, legacy mark"
status = "open"
goal = "FORCE-CONVERSION"
section = "Now"
rank = 2000
depends_on = []
touches = ["pi-autowork/pi_autowork/tui.py", "pi-autowork/pi_autowork/fleet_view.py", "pi-autowork/tests/tui_pilot.py", "pi-autowork/tests/test_fleet_view.py", "pi-autowork/README.md"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "In pi_autowork/tui.py the browser's PrepareRepository dialog gains a Force button (id force) that first confirms, naming what force does (stops the service and live workers, sets attempts aside with worktrees, branches and files kept, commits planning edits, converts, restarts), then runs autowork tasks prepare --force <repo> through the existing run_prepare worker; the info pane lists every entry of refusals and, for a forced report, the step summary (stopped, set_aside, landed, committed, commit) from report['forced']['step']. In fleet_view: readiness marks a repository whose task_prepare.detect state is legacy or conversion_pending as 'legacy planning' (problem text) instead of 'needs tasks'; how_to_fix names autowork tasks prepare --force for that case; SETUP_LABELS['legacy'] says that Force converts. Pilot and unit tests cover the button, the confirm, the argv, the refusal listing and the mark. pi-autowork/README.md TUI section documents Force."
acceptance = ["Pilot: on a legacy fixture, p opens the dialog with Prepare, Prepare and start, Plan, Force and Cancel; Force asks for confirmation; escape runs nothing; y runs [aw, tasks, prepare, --force, <repo>] once and the pane shows the forced step summary or the full refusal list (pi-autowork/tests/tui_pilot.py)", "fleet_view.readiness on a TODO.md + goals.json repository reports the problem as legacy planning and how_to_fix names prepare --force; a repository with no planning at all still reports needs tasks (pi-autowork/tests/test_fleet_view.py)", "A MIGRATION_BLOCKED report with two refusals shows both lines in the browser pane (pi-autowork/tests/tui_pilot.py)"]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py", "cd pi-autowork && uv run --with textual==8.2.8 python tests/tui_pilot.py"]
exclusions = ["Force is never run without the confirmation", "No change to tasks prepare itself"]
+++
- Sources: docs/plans/2026-10-22-force-conversion.md#decision
- Overlap repair: CHANGELOG.md work moves to TOOLSET-372-a9fe0116, which depends on this task and TOOLSET-368/370/371. The accepted plan calls for the TUI slice in parallel with TOOLSET-368; its TUI, fleet-view, pilot, unit-test and README scope and every Acceptance item remain here. This task does not edit CHANGELOG.md.
