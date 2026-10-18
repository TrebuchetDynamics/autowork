# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-189-96 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-189-96 — A new runner starts cleanly: a lasting PATH and committed planning files
- Needs: changed files violate Touches or coordinator/other-slot ownership: {'outside': ['pi-autowork/tests/test_status_cache.py'], 'conflicts': []}
- Since: 2026-10-18T16:38:56Z
- Answer: Answer in TOOLSET-189-96's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-210-53 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-210-53 — A runner keeps the disk from filling: a free-space gate, build caches pruned from idle worktrees, and a restart after it fails
- Needs: worker reported a blocker: Widen Touches to include tests/test_pi_autowork.py. Its existing ServiceTests.test_install_names_the_unit_after_the_repository assertion (line 2094) requires Restart=on-abnormal, contradicting this task's required Restart=on-failure policy. The mandatory full offline gate cannot pass the requested change without updating that assertion. No implementation changes or commits were made; no checks wer…
- Since: 2026-10-18T16:24:03Z
- Answer: Answer in TOOLSET-210-53's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
