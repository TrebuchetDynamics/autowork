# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-140-f4 — USER_INPUT — effort input — unblocks 46

- Task: TOOLSET-140-f4 — Give workers a short temporary directory that browsers and sockets accept
- Needs: changed files violate Touches or coordinator/other-slot ownership: {'outside': ['pi-autowork/pi_autowork/worker.py', 'pi-autowork/tests/test_worker_tmp.py'], 'conflicts': []}
- Since: 2026-10-17T19:57:32Z
- Answer: Answer in TOOLSET-140-f4's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-099-87 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-099-87 — Run as many independent tasks at once as possible
- Needs: worker reported a blocker: Combined offline qualification cannot pass in the supplied worker environment. Coordinator must provide an approved task-owned TMPDIR outside any Git checkout, short enough for AF_UNIX socket filenames and without autowork in its path, plus an isolated offline-test environment that does not inherit worker model settings and that permits only local fixture Git transport. The current explicitly supp…
- Since: 2026-10-17T19:43:20Z
- Answer: Answer in TOOLSET-099-87's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-142-85 — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-142-85 — Query pending and completed tasks from repository evidence without writes
- Needs: integration validation failed or changed the integration tree
- Since: 2026-10-17T19:04:24Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-142-85/), then rescope or split TOOLSET-142-85 in its TODO.md entry. The runner reruns it when the entry changes.

### Q-TOOLSET-154-d3 — USER_DECISION — effort investigate — unblocks 1

- Task: TOOLSET-154-d3 — Question IDs are single-line and stable, so BLOCKERS.md changes only when questions do
- Needs: abandoned integration tree changed or ambiguous; preserve for diagnosis
- Since: 2026-10-17T18:42:47Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-154-d3/), then rescope or split TOOLSET-154-d3 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
