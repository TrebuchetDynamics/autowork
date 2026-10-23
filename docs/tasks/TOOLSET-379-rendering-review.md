# TOOLSET-379: make unavailable task inventory visibly distinct from empty

## Evidence and disposition

The accepted [snapshot contract](../plans/tui-responsiveness.md#one-committed-task-snapshot)
already requires unavailable/invalid inventory to render unknown, not zero, and
last-good data to retain its original revision/age and stale/error state.
[TOOLSET-379-cf40090d](../../tasks/items/TOOLSET-379-cf40090d.md) remains open;
its prerequisite TOOLSET-378 is done and TOOLSET-380 still depends on it.

Evidence read in place (private execution artifacts are not copied here):

- `.git/autowork-execution/slot-data/TOOLSET-379-cf40090d/attempt-1/report.json`
  and `attempt-2/report.json`: candidate claims and exact changed-file lists.
- `.git/autowork-execution/slots/TOOLSET-379-cf40090d.json`: attempt 2 is held
  for validation, not running or waiting to land. Its recorded worker PID was
  absent at inspection. `ledger_edit_dropped` is null and no ledger-edit patch
  exists in this task's saved attempt directories; no proposal is applied.
- `.git/autowork-execution/942de240ea214d74bc973f61491b0d21.log`: review
  rejected the rendered unknown-versus-empty behavior; required suites were
  satisfied by the accepted gate, but that is not acceptance of the candidate.
- Candidate `53c049a2ad7aedfc7b2a1eb3be5e135c79b1345a`,
  `pi-autowork/pi_autowork/tui.py:433,465–471`: TasksScreen fixes
  `#task-views` at one line, counts empty rows as zero and appends freshness on
  the next line. The review's rendered unavailable case showed “All 0”, other
  zero counts and “No task in this view”; the error was clipped.
- The same candidate's `pi-autowork/tests/tui_pilot.py:163–172` checks
  unavailable/stale data in the fleet detail, not the TasksScreen viewport.
  `pi-autowork/tests/test_fleet_view.py:923–932` already invokes the offline
  Textual pilot and can skip when its dependencies are absent.

Neither that candidate nor trial integration
`fffea407f452bfba8e31f0657f7cb5a8716786a6` is an ancestor of this repair's
base `2694fce5215e1f255cd6a33ca3b8ae23e2dc1da6`. Thus no part is closed or
represented as delivered. Restating the existing task avoids inventing a
completed slice or a duplicate follow-up.

## Bounded repair

- Preserve all three acceptance items and clarify their unknown-versus-empty
  requirement with the concrete TasksScreen finding: visible errors/freshness,
  unknown counts without verified data, and explicitly stale original-age
  last-good data. Verified empty remains zero.
- Require an actually rendered TasksScreen regression for unavailable, valid
  empty and stale last-good states, including a narrow viewport. Inspect visible
  output/layout, not only the underlying Static text, so clipping fails the test.
- Extend Touches only with `health.py`, `task_status.py` and the component README,
  all named in the attempt-2 report. They support the existing provenance,
  classification and documentation contract, not new product scope.
- Retain Checks, dependency, rank, section, authority and exclusions. The focused
  fleet suite already runs the pilot; a skipped pilot is NOT_CHECKED, not rendered
  proof. Retain attempt-1 count/detail consistency and stale-slot regressions.
- Leave nonblocking reads to TOOLSET-380 and live SSH/service qualification
  unclaimed. Do not operate services or adopt/change retained worker checkouts.

## Maintainer checklist

- [x] Read task, accepted source, prerequisite/dependent records, both worker
  reports, held slot, review log and candidate renderer/pilot source.
- [x] Restate only the existing rendering contract and report-backed file scope
  through `autowork tasks field`; preserve every original acceptance item.
- [x] Validate the working task store: 133 tasks, 17 goals, no drafts. Structural
  assertions preserve every original acceptance item, all other typed fields and
  existing notes except Next action; Touches matches the saved worker report.
  Local links/accepted anchor resolve; independent read-only review found no
  blocker. No product tests were rerun for this docs-only repair; these checks
  neither accept the implementation nor qualify live behavior.
