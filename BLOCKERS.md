# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-315-36 — USER_INPUT — effort input — unblocks 3

- Task: TOOLSET-315-36 — Task-store validation leaves no unreachable Git objects
- Needs: the worker edited the task store, which only the coordinator writes: tasks/items/TOOLSET-315-36.md
- Since: 2026-10-22T10:23:31Z
- Answer: Answer in tasks/items/TOOLSET-315-36.md: widen `touches`, supply the input, narrow the acceptance, or add a dated `Owner decision:` note. The runner reruns it when the record changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
