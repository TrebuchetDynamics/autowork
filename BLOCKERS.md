# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-115-bf — USER_INPUT — effort input — unblocks 3

- Task: TOOLSET-115-bf — Redesign pi-autowork around one lifecycle authority
- Needs: worker reported a blocker: Provide a short writable task TMPDIR outside every Git checkout (preferably a path below 40 characters), so the mandatory offline inventory can create AF_UNIX socket fixtures and test non-Git directories correctly. Retain this worktree and its uncommitted changes. On resumption, isolate fixture subprocesses from inherited worker-specific model/push settings without weakening production guards, con…
- Since: 2026-10-17T05:54:02Z
- Answer: Answer in TOOLSET-115-bf's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-099-87 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-099-87 — Run as many independent tasks at once as possible
- Needs: worker reported a blocker: Coordinator must widen Touches to include pi-autowork/pi_autowork/coordinator.py. The continuous runner remembers NONE tasks in touches_tried for its entire lifetime, so expired 24-hour cache entries cannot be reconsidered; infer_touches must permit expiry-based retries. The authorized legacy scripts only delegate to this migrated component. No implementation outside Touches was edited, and no com…
- Since: 2026-10-17T05:18:21Z
- Answer: Answer in TOOLSET-099-87's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
