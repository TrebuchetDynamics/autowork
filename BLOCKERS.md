# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-029 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-029 — Migrate fleet repositories to recorded TODO.md priority order
- Needs: worker reported a blocker: Scope/authority conflict: TOOLSET-029 requires migrating and committing goals.json (and sometimes TODO.md) in multiple fleet repositories, under Toolset coordinator ownership. This worker invocation explicitly restricts work to its assigned worktree, prohibits editing TODO.md and goals.json, and prohibits touching another worktree. docs/project.md#rollout confirms that fleet migration is a separat…
- Since: 2026-10-20T21:57:10Z
- Answer: Answer in TOOLSET-029's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
