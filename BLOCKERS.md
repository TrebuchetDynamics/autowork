# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-200-c1 — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-200-c1 — A status read waits for the writer lock, and a failed read never means nothing is running
- Needs: merge adoption limit reached; adopted 3 of 3; conflict in: pi-autowork/pi_autowork/coordinator.py
- Since: 2026-10-20T21:39:03Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-200-c1/), then rescope or split TOOLSET-200-c1 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-099-87 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-099-87 — Run as many independent tasks at once as possible
- Needs: merge adoption limit reached; adopted 3 of 3; conflict in: pi-autowork/pi_autowork/touches_inference.py, skills/autowork/references/parallel-workers.md
- Since: 2026-10-20T21:52:46Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-099-87/), then rescope or split TOOLSET-099-87 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
