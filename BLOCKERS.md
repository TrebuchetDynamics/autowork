# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-200-c1 — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-200-c1 — A status read waits for the writer lock, and a failed read never means nothing is running
- Needs: merge conflict; worker and canonical checkout preserved
- Since: 2026-10-20T06:38:05Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-200-c1/), then rescope or split TOOLSET-200-c1 in its TODO.md entry. The runner reruns it when the entry changes.

### Q-TOOLSET-234-d4 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-234-d4 — A main-repair worker gets the runner's main-check evidence: log, exit code, revisions and isolated reruns
- Needs: abandoned integration lacks exact candidate/contract/branch evidence
- Since: 2026-10-20T06:38:05Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-234-d4/), then rescope or split TOOLSET-234-d4 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
