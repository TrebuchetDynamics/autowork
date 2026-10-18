# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-197-4f — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-197-4f — An invalid goals.json is a DOCS-MAINTAINER trigger, not an endless engine-attention loop
- Needs: worker reported a blocker: The required full offline gate cannot pass because two existing daemon-lifecycle fixtures in skills/autowork/scripts/test_parallel_integrate.py fail intermittently with differing receipt classifications. Authorize widening Touches to that exact test file so its daemon fixtures can be stabilized, or provide a baseline on which the full offline gate passes. The ledger implementation and all task-spe…
- Since: 2026-10-18T17:30:47Z
- Answer: Answer in TOOLSET-197-4f's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-213-45 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-213-45 — A Touches value that is not a list of paths is a contract error, not a silent outside-Touches hold
- Needs: worker reported a blocker: Provide a disk-backed task TMPDIR with at least 20 GB free, then rerun the full offline gate. The supplied /run/user/1000 TMPDIR filesystem is a 6.3 GB tmpfs, so it cannot satisfy the default 20 GB worker-dispatch disk guard even when empty. The actual checkout disk has approximately 415 GB free. Implementation and focused checks are ready, but full offline verification cannot finish in this envir…
- Since: 2026-10-18T17:30:47Z
- Answer: Answer in TOOLSET-213-45's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-214-5b — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-214-5b — A deferred dependency asks nothing, and only owner questions read as Waiting on you
- Needs: worker reported a blocker: Coordinator must widen Touches to skills/autowork/scripts/parallel_status.py and skills/autowork/scripts/test_parallel_status.py to satisfy scope item (4)'s source fix. In parallel_status._snapshot, the source selection for an ordinary nondependency task reuses historical dispatch_observed data without invalidating ownership waits when the blocker finishes. An in-memory diagnostic exercising the r…
- Since: 2026-10-18T17:30:47Z
- Answer: Answer in TOOLSET-214-5b's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
