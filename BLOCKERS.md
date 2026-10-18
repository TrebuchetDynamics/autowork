# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-213-45 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-213-45
- Needs: worker reported a blocker: Provide a disk-backed task TMPDIR with at least 20 GB free, then rerun the full offline gate. The supplied /run/user/1000 TMPDIR filesystem is a 6.3 GB tmpfs, so it cannot satisfy the default 20 GB worker-dispatch disk guard even when empty. The actual checkout disk has approximately 415 GB free. Implementation and focused checks are ready, but full offline verification cannot finish in this envir…
- Since: 2026-10-18T17:30:47Z
- Answer: Answer in TOOLSET-213-45's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
