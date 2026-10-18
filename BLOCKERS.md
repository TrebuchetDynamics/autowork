# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-184-b3 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-184-b3 — Restore the full offline check after the red main at 36e2b7c
- Needs: worker reported a blocker: Coordinator must preallocate and authorize a private physical task TMPDIR with no ancestor containing .git, then supply its resolved path to both the resumed worker and reviewer. The current supplied slot-data TMPDIR still violates that explicit prerequisite; no descendant can satisfy it. Preserve/reconcile the retained 19-file repair candidate from the previous continuation: the newly assigned ch…
- Since: 2026-10-18T02:30:38Z
- Answer: Answer in TOOLSET-184-b3's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
