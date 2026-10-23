+++
schema = 1
id = "TOOLSET-377-199b6bb6"
title = "Fleet controls no longer offer Fallback or Nous Portal shortcuts"
short = "Remove extra fleet hotkeys"
status = "done"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 1000
depends_on = []
touches = ["pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/tui_pilot.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Remove global fleet Fallback (f) and Nous Portal (o) bindings and all corresponding menu/help/palette exposure, including an empty fleet. Filter fallback in FleetApp.available, preserving shared fleet_view.actions and backend/CLI capabilities. Keep Model and other runner/task/navigation actions plus read-only fallback details; do not ban child-local keys or typed characters. Preserve internal PortalSetup privacy/consent tests by directly opening the isolated component rather than keeping the removed shortcut."
acceptance = ["Extend existing tui_pilot.py rendered-menu assertions at 80/120 columns: selected running/stopped/paused, empty fleet and view-only surfaces expose neither Fallback nor Nous Portal global controls/bindings. Pressing f/o on the fleet screen opens no picker/modal and performs no probe/write/runner command; Model/navigation still work.", "Existing backend fallback config/execution and CLI model --fallback/setup-portal stay unchanged. Pilot Portal preview/redaction/refusal/confirmation assertions remain via direct isolated modal invocation; do not delete coverage or restore a fleet shortcut.", "Existing native mouse/copy and child-screen key behavior remains intact. The Textual headless pilot actually runs under focused/affected checks; report skips or unavailable cached Textual as missing rendered coverage, never a visual pass."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_tui_mouse.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No fallback engine/provider/CLI removal, model or profile configuration changes, full-suite policy repair, task-count/blocker cleanup, live service/Play/restart action, remote-host operation, new dependency, timer, install or publication. This invocation plans only."]
live = "denied"
closure = "coordinator_verified"
closure_evidence = "tasks/evidence/TOOLSET-377-199b6bb6.toml"
+++
- Sources: docs/project.md#fleet-tui-action-surface
- Owner decision: Remove Fallback and Nous Research hotkeys from the shown TUI. Planner interpretation: Nous Research refers to the displayed Nous Portal action; only interaction surface changes, backend support stays.
- Evidence: Pinned source 911d1b2855c94eaedfa07102434d95d139f0ab13; FleetApp.BINDINGS/show_detail/available and tui_pilot existing menu/Portal cases inspected. Supplied other-host listing is context only, not reproduced local state or operational authority.
- Next action: Update the existing headless pilot to fail on the two exposed fleet actions, remove only their fleet bindings/menu routes, adapt isolated Portal coverage, then run Checks on the actual implementation base.
- Planning checks: Future product/pilot checks unrun. Clear single outcome; no additional builder interview or rolling planning successor needed. Preserve old records, ordering, goal priority/focus and completed Portal decisions.
