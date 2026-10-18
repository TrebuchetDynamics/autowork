# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-197-4f — USER_INPUT — effort input — unblocks 64

- Task: TOOLSET-197-4f — An invalid goals.json is a DOCS-MAINTAINER trigger, not an endless engine-attention loop
- Needs: worker reported a blocker: Provide a task-specific TMPDIR with at least 1 GiB free, preferably on disk, then resume this worktree. The supplied /run/user/1000/aw/aaf6b379/4 is on a 6.3 GiB tmpfs with approximately 8 MiB remaining; serial test fixture worktree creation now fails. Other tasks' runtime state was not deleted. Changes are preserved uncommitted. Resume by rerunning focused_checks.py, checking the final DRAINING/P…
- Since: 2026-10-18T16:19:38Z
- Answer: Answer in TOOLSET-197-4f's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-189-96 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-189-96 — A new runner starts cleanly: a lasting PATH and committed planning files
- Needs: changed files violate Touches or coordinator/other-slot ownership: {'outside': ['pi-autowork/tests/test_status_cache.py'], 'conflicts': []}
- Since: 2026-10-18T15:06:41Z
- Answer: Answer in TOOLSET-189-96's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-204-f2 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-204-f2
- Needs: worker timeout after 5400 s
- Since: 2026-10-18T13:12:55Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-204-f2/), then rescope or split TOOLSET-204-f2 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
