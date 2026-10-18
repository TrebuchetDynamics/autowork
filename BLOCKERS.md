# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-199-2d — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-199-2d — A task whose Ownership needs the owner or live authorization is never dispatched unattended
- Needs: worker reported a blocker: Authorize adding skills/autowork/scripts/parallel_status.py to Touches. Its pending_tasks/_snapshot logic must evaluate current authorization and preserve that outside condition for interrupted slots; otherwise the required outside root and owner question disappear. Existing allowed test_parallel_plan.py can cover these seams, so no extra test path is required. Changes remain uncommitted for resum…
- Since: 2026-10-18T10:03:30Z
- Answer: Answer in TOOLSET-199-2d's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-165-f7 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-165-f7 — A runner's own worker processes never count as an outside session in the main checkout
- Needs: missing, failed, stale or mismatched integration validation
- Since: 2026-10-18T04:36:31Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-165-f7/), then rescope or split TOOLSET-165-f7 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
