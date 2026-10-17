# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-099-87 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-099-87 — Run as many independent tasks at once as possible
- Needs: worker reported a blocker: Coordinator must widen Touches to include pi-autowork/pi_autowork/coordinator.py. The continuous runner remembers NONE tasks in touches_tried for its entire lifetime, so expired 24-hour cache entries cannot be reconsidered; infer_touches must permit expiry-based retries. The authorized legacy scripts only delegate to this migrated component. No implementation outside Touches was edited, and no com…
- Since: 2026-10-17T05:18:21Z
- Answer: Answer in TOOLSET-099-87's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
