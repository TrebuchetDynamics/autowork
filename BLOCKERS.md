# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-157-cd — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-157-cd — Held slots release file ownership so holds cannot deadlock the queue
- Needs: worker reported a blocker: Coordinator must widen Touches to the six paths in needs_touches. Scope (5) requires changing the runner loop in pi-autowork/pi_autowork/coordinator.py: commit_owner_changes is called only from merge_main, after its ahead == 0 early return, while follow_base only reads committed main history. That module also owns the existing Pi merge resolver and configured stall threshold. Scope (4) requires he…
- Since: 2026-10-17T15:38:16Z
- Answer: Answer in TOOLSET-157-cd's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
