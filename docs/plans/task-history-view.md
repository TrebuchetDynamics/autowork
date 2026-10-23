# Open tasks and closed history in the fleet TUI

Status: Accepted

## Requirement

The owner requested a fix after the default Tasks list mixed closed records into
“All” and displayed an old closure without provenance as “Manual”. Default to
**1 Open**: only the committed open inventory, not closures or independent question
annotations. Preserve **Active**, **Blocker**, **Waiting** and **Questions**, and add
**6 Closed** for retained completion history. Tab/Shift+Tab and number keys select
views. Counts use the same snapshot as their rows; closed history does not inflate
open work. Question annotations remain accessible in Questions, even when outside
current inventory. Closed records with an independent question must remain visible
in Closed too.

History is read-only: its detail can show the record, closure context and a related
question, but cannot change section or answer/repair a question. Answering an
independent question from Questions stays separate. Keep existing normal/open-task
controls and view-only restrictions. Tabs must remain visible at 80/120 columns.

## Closure provenance

- A valid coordinator receipt remains **Verified**; an invalid or missing receipt
  must not gain verification.
- Explicit manual closure remains **Manual**, with its recorded actor, timestamp
  and reason, and a clear not-coordinator-verified explanation.
- A historical done record lacking a recorded method is **Unknown closure**, not
  an inferred manual action. Say provenance/verification is not recorded.

Do not reopen, delete, relabel persisted statuses or backfill historical receipts,
actors, dates or reasons. This fixes presentation, not evidence or acceptance of
any old task, and grants no authority over another repository or live device.

## Implementation and checks

Use the incoming committed-snapshot implementation from
`TOOLSET-379-cf40090d`; it owns membership and closed rows. Keep the active worker's
workspace, candidate, contract and integration untouched. Implement this follow-up
in its own isolated checkout and compose only after that ownership releases.

Regression coverage uses a real disposable committed TaskStore with open, explicit
manual and legacy closures; verifies read-only byte preservation, annotation
separation and verified/invalid-receipt labels; and renders pinned Textual at
80/120 by 24 columns in normal/view-only modes for Open/Closed counts, number/Tab
navigation, history detail, question context and mutation denial. Run the affected
tests from the actual implementation base, plus task/docs validation. No remote
installation, service operation, publication or fabricated historical proof.
