# TOOLSET-382 overlap disposition

## Evidence

- [TOOLSET-382-fcc9aa05](../../tasks/items/TOOLSET-382-fcc9aa05.md),
  admitted in `b82618ce368be59c9757bb379413ea5953e4f8fd`, retains code-only
  candidate `27e8ca54533baddc5c8bdfc3aa2f8f773155bab3` on `fix/task-history`.
  Its Scope, Candidate and Remaining notes require adopting and reconciling that
  implementation, not reimplementing it or dispatching a competing TUI owner.
  The candidate is not an ancestor of inspection base
  `63396926865ec3fe2007af261237d59bc0cc11bd`; it still awaits integration.
- The [accepted history contract](../plans/task-history-view.md#open-tasks-and-closed-history-in-the-fleet-tui)
  requires Open/Closed navigation, honest closure provenance and read-only
  history details together with real-store and rendered regression coverage.
  Candidate inspection confirms changes to both
  `pi-autowork/pi_autowork/tui.py` and `pi-autowork/tests/tui_pilot.py`.
- [TOOLSET-380-f265bb27](../../tasks/items/TOOLSET-380-f265bb27.md)
  declares those same two files. Its
  [accepted contract](../plans/tui-responsiveness.md#nonblocking-read-coordination)
  owns nonblocking readers and UI-thread publication, not the history feature.
  At inspection its private slot was running on attempt 1, with its recorded
  worker PID confirmed live. The worker log was empty and no report existed;
  no completion or review result is inferred.
- TOOLSET-379-cf40090d, the existing typed prerequisite of both tasks, is now
  recorded done with coordinator provenance. That does not release TOOLSET-380's
  current shared-file ownership. No runner slot or report directory existed for
  TOOLSET-382, and no dropped-ledger proposal was recorded for either overlap
  participant. No saved patch was applied.

## Disposition

Leave both task entries unchanged. The overlap-maintenance instruction forbids
editing an entry whose worker is running or whose commit waits to land:
TOOLSET-380 is running, and TOOLSET-382 already has the retained history candidate
awaiting adoption. This is not two unstarted implementations that can be merged
or repartitioned by the docs maintainer.

Splitting the shared-file changes would repartition an already implemented
candidate and its composed acceptance checks, not free unstarted independent
work. Dropping the shared Touches would misdescribe that candidate. The
nonblocking-read task does not deliver the separate history contract, so it
cannot justify superseding it. Even adding a typed dependency would edit the
protected pending-candidate entry. All Acceptance items, Checks, Touches,
ownership and queue order therefore remain intact.

The existing overlap gate must continue to serialize integration. After
TOOLSET-380 releases the shared files, the existing coordinator/worker path can
reconcile the retained history candidate against actual main, preserve the
nonblocking behavior and rerun TOOLSET-382's recorded checks. This maintainer
pass does not integrate code, release ownership, close or qualify a task, change
product scope, or claim rendered/live acceptance. The overlap remains blocked;
no owner decision or missing proof is invented.
