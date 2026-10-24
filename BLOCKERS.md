# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in the [`tasks/`](tasks/) store. This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-389-6dedfd8c — USER_DECISION — effort decision — unblocks 1

- Task: TOOLSET-389-6dedfd8c — Qualify one owned installed RPC runner and matched engineering measurements
- Needs: 1 waiting task(s) depend on "TOOLSET-389-6dedfd8c", which is not a Now/Next task (an outside condition, or a task in Needs decision).
- Since: 2026-10-24T18:33:47Z
- Answer: Decide it: record the decision in the dependent tasks' `depends_on`, or move the task that owns it into Now or Next. To defer it, keep that task in Needs decision with a dated `Owner decision:` note; its dependents then wait without another question.
- Kind: outside

<!-- pi-autowork:questions:end -->

None.

## Engineering holds

Technical incidents remain visible in the runner status and fleet view; they are not owner
questions. A failed review, a dead worker, a merge conflict or exhausted reviewer rework
stays here as Agent repair until normal verification clears it. No such incident asks the
owner to decide whether incorrect work is acceptable.

## Resolved

None.
