# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-209-55 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-209-55 — Workers run the runner suite sharded, and a worker timeout names the command it cut off
- Needs: worker reported a blocker: The coordinator must migrate TODO.md Checks lines that run SPLIT modules serially, or explicitly authorize this worker to make that migration despite the coordinator-owned-file prohibition. Scope (2) and acceptance require this edit, but the worker rules forbid editing TODO.md even though it is in Touches. The prior integration log (.git/autowork-execution/22425219148b4d55ae247984e67cd422.log) con…
- Since: 2026-10-18T14:58:20Z
- Answer: Answer in TOOLSET-209-55's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-165-f7 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-165-f7 — A runner's own worker processes never count as an outside session in the main checkout
- Needs: missing, failed, stale or mismatched integration validation
- Since: 2026-10-18T04:36:31Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-165-f7/), then rescope or split TOOLSET-165-f7 in its TODO.md entry. The runner reruns it when the entry changes.

### Q-TOOLSET-204-f2 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-204-f2 — The main check reruns its failures alone before calling main red; tests that pass alone are reported as flaky
- Needs: worker timeout after 5400 s
- Since: 2026-10-18T13:12:55Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-204-f2/), then rescope or split TOOLSET-204-f2 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
