# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-125-3c — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-125-3c — Runners report unlanded work in health and BLOCKERS.md
- Needs: merge conflict; worker and canonical checkout preserved; adopted 1 of 3; conflict in: tests/test_pi_autowork.py
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-125-3c/), then rescope or split TOOLSET-125-3c in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-200-c1 — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-200-c1 — A status read waits for the writer lock, and a failed read never means nothing is running
- Needs: merge conflict; worker and canonical checkout preserved; adopted 2 of 3; conflict in: pi-autowork/pi_autowork/coordinator.py, pi-autowork/tests/test_maintainer.py
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-200-c1/), then rescope or split TOOLSET-200-c1 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-118-68 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-118-68 — Separate worker, test and memory budgets in the parallel resource gate
- Needs: merge conflict; worker and canonical checkout preserved; adopted 1 of 3; conflict in: tests/test_pi_autowork.py
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-118-68/), then rescope or split TOOLSET-118-68 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-153-64 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-153-64 — A planning hold lets repository agents repair the queue without stopping the runner
- Needs: merge conflict; worker and canonical checkout preserved; adopted 1 of 3; conflict in: pi-autowork/pi_autowork/command.py, tests/test_pi_autowork.py
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-153-64/), then rescope or split TOOLSET-153-64 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-252-4c — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-252-4c — A worker blocker that names another open task waits for that task, occupies nothing meanwhile, and resumes when it lands
- Needs: merge conflict; worker and canonical checkout preserved
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-252-4c/), then rescope or split TOOLSET-252-4c in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

### Q-TOOLSET-261-15 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-261-15 — A worker's long test runs take a host check slot
- Needs: merge conflict; worker and canonical checkout preserved; adopted 1 of 3; conflict in: docs/reference.md, skills/autowork/scripts/parallel_dispatch.py, skills/autowork/scripts/test_parallel_dispatch.py
- Since: 2026-10-20T19:33:17Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-261-15/), then rescope or split TOOLSET-261-15 in its TODO.md entry. The runner reruns it when the entry changes.
- Kind: held

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
