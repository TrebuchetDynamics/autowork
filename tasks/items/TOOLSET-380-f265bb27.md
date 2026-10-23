+++
schema = 1
id = "TOOLSET-380-f265bb27"
title = "TUI keys remain responsive while bounded read jobs coalesce and publish current snapshots"
short = "Keep UI input off blocking reads"
status = "open"
goal = "RELIABILITY-2026-10"
section = "Next"
rank = 4000
depends_on = ["TOOLSET-379-cf40090d"]
touches = ["pi-autowork/pi_autowork/tui_reads.py", "pi-autowork/pi_autowork/tui.py", "pi-autowork/tests/test_tui_reads.py", "pi-autowork/tests/tui_pilot.py"]
resources = []
kind = "implementation"
ownership = "worker"
scope = "Implement tui_reads request(kind,identity,epoch,loader)->token and wire all fleet/log/task/goals/readiness/model/code-stamp readers off Textual callbacks/rendering. Four-worker bounded executor, one physical active plus replaceable pending per active resource; queued owner subscriptions retire on change. Keep UI-thread-only publication and last-good/error display. Same-epoch timer polls do not invalidate active results; stale owner/identity/epoch or older-applied completion is rejected. Physical thread completion retains slot despite wrapper cancellation. Preserve fresh readiness, action confirmations/view-only and existing interactive suspension."
acceptance = ["Proposed test_tui_reads.py and pilot Event handshakes acknowledge key/navigation/filter/close before releasing each blocked reader. Repeated refresh/resize coalesces, a slower-than-timer reader still publishes, and cached layout/filter/wrap has no synchronous I/O; no elapsed-time SSH claim.", "Fixtures prove bounded active/pending work, no replacement overlap after async wrapper cancellation, no post-unmount or stale-selection/epoch publication, retry after error, action/preparation invalidation and stable current selection/filter/scroll. Workers touch no widgets or mutable runner list.", "Consume shared TaskSnapshot/FleetSnapshot and bounded readers, separate journal/catalog/readiness keys and provider-context discovery. Preserve fresh pre-Start checks, duplicate-start protection, privacy/confirmation/view-only, native mouse/copy and landed hotkey removal; focused/affected rendered tests run, not just skip."]
checks = ["python3 scripts/check.py pi-autowork/tests/test_tui_reads.py pi-autowork/tests/test_fleet_view.py pi-autowork/tests/test_tui_mouse.py", "python3 scripts/affected_tests.py --run"]
exclusions = ["No task/attempt/receipt schema or authority changes, branch-task union, skipped required review/checks, restored removed fleet shortcuts, unrelated Src migration, service/job/profile/model operations, SSH/network tuning, dependency additions or publication. Preserve active contracts and existing pauses."]
live = "denied"
+++
- Sources: docs/plans/tui-responsiveness.md#nonblocking-read-coordination
- Planner call: Source-backed repair design, not a proven remote SSH diagnosis; routine defaults and exact interfaces are in the accepted source. Future tests are task-owned inputs to create, not unavailable external prerequisites.
- Produces: Nonblocking coalesced read coordinator integrated into existing TUI; deterministic event-loop responsiveness/cancellation/staleness oracles.
- Consumes: Task TOOLSET-379-cf40090d TaskSnapshot/FleetSnapshot and bounded readers; task TOOLSET-378-faaf7ed8 truthful observation metadata.
- Next action: Add/extend the named deterministic private fixture at the public data/event seam before changing implementation, then run Checks on the actual implementation base.
- Evidence: Read-only source reviews at 911d1b2855c94eaedfa07102434d95d139f0ab13; planning base 614bdf8e after canonical delivery of the hotkey task. Existing worker receipt is distinct from implementation acceptance.
- Delivery: Branch-local planning until canonical inclusion and consumer readback; no implementation, rendered or SSH pass claimed.
