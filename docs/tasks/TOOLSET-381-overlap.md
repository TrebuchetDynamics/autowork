# TOOLSET-381 overlap disposition

## Evidence

- [TOOLSET-381-39d82792](../../tasks/items/TOOLSET-381-39d82792.md)
  retains the tested code-only candidate `aed2987b78c750b00837615d4ec1c8c44f6a2678`
  on `feature/blockers-report`. Its Remaining and Candidate notes require
  preserving that implementation, reconciling the snapshot adapter after
  TOOLSET-379 releases the shared files, and not starting a competing worker.
  These notes were committed in `0cba5ab58cbd8b65dd2faf47ba247f24cc6e4f93`.
- That candidate changes both `pi-autowork/pi_autowork/tui.py` and
  `pi-autowork/tests/tui_pilot.py`, which are also declared by
  [TOOLSET-379-cf40090d](../../tasks/items/TOOLSET-379-cf40090d.md).
- The [accepted snapshot plan](../plans/tui-responsiveness.md#one-committed-task-snapshot)
  gives TOOLSET-379 the synchronous rendering adapters. The
  [accepted Blockers contract](../project.md#fleet-blockers-report) separately
  requires the read-only report, menu bindings and stalled-reader coverage.
  Snapshot delivery alone therefore does not supersede the Blockers task.

## Disposition

Leave both task entries unchanged. The overlap-maintenance instruction forbids
editing a running task or one whose commit waits to land. At this maintainer
inspection, TOOLSET-379's live attempt was confirmed in its slot record and
process identity; TOOLSET-381's pending candidate is explicitly retained by its
committed record. No runner attempt/report directory existed for TOOLSET-381,
and TOOLSET-379 had not yet produced its attempt report. No dropped-ledger patch
was supplied for this item.

Merging the tasks would rewrite the live snapshot contract. Splitting the report
would repartition an already implemented candidate rather than free unstarted
work. Removing the shared Touches would misdescribe the candidate. Adding a typed
dependency to TOOLSET-381 would also edit a task whose commit waits to land.
None is a permitted repair here; all Acceptance items, ownership, queue order,
Touches and Checks remain intact.

The remaining operation is the existing coordinator-owned integration: after
TOOLSET-379 releases the shared files, reconcile the retained Blockers candidate
with the delivered snapshot adapter and rerun its recorded checks. This
maintainer pass neither integrates code nor closes or qualifies either task.
The overlap remains blocked; no owner decision or new proof is invented.
