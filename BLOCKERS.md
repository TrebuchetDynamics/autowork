# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-120-fc — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-120-fc — Hands-off runners: the owner only plans and answers questions
- Needs: worker reported a blocker: Provide or authorize a short canonical TMPDIR outside every Git checkout (for example a dedicated directory under /tmp, with a path that does not contain 'autowork'), and resume this worktree. The mandated attempt TMPDIR is nested inside hermes-toolset/.git and is too long for AF_UNIX sockets; the required offline inventory cannot pass there without unrelated fixture changes outside Touches. Prese…
- Since: 2026-10-17T08:03:38Z
- Answer: Answer in TOOLSET-120-fc's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
