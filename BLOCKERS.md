# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-318-17 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-318-17 — Convert TODO.md without overlooking consumers or losing non-task content
- Needs: integration validation failed or changed the integration tree: PI_AUTOWORK_VERIFY: fail — same-line Goal annotations are silently lost instead of preserved or refused.; this was its one rework after review, and the earlier review found: `pi-autowork/pi_autowork/legacy/conversion_audit.py:103–109` incorrectly counts all indented field continuations as preserved. Reproduced by adding an indented checklist beneath `- Goal: G2`: dry-run reports no preservation, conversion succeeds, deletes TODO.md, and loses the checklist entirely. The mapper takes Goal from the ledger and discards that continuation. This violates the every-line accounting requirement; preserve or refuse content the mapper does not retain.
- Since: 2026-10-22T00:38:20Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-318-17/), then rescope or split TOOLSET-318-17 in tasks/items/TOOLSET-318-17.md. The runner reruns it when the record changes.
- Kind: held

### Q-TOOLSET-338-82 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-338-82 — A batch check runs only the test modules its changes affect; main gets the full suite after landing
- Needs: dead worker without a commit or changes
- Since: 2026-10-21T23:59:57Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-338-82/), then rescope or split TOOLSET-338-82 in tasks/items/TOOLSET-338-82.md. The runner reruns it when the record changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
