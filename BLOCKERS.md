# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

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
