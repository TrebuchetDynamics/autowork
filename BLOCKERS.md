# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-215-91 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-215-91 — Bundle skills load read-only from the plugin, so the skill review never edits them
- Needs: worker reported a blocker: Provide an installed upstream Hermes revision that refuses background_review edits, patches, and supporting-file writes to skills.external_dirs, then rerun the native safety probe before implementing this migration. Current Hermes e06df9c2eae6901f4c88f464e0ae6e753c0428b8 allows the demonstrated patch. Task scope item 4 requires stopping rather than shipping a weaker rule, and task exclusions prohi…
- Since: 2026-10-18T19:00:42Z
- Answer: Answer in TOOLSET-215-91's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-FULL-CHECK — USER_INPUT — effort input — unblocks 0

- Task: the repository's whole offline test suite
- Needs: no full-suite gate: a commit can land while breaking tests its own task never ran, and main is never checked
- Since: 2026-10-18T19:01:11Z
- Answer: Add one line to AGENTS.md, `Full check: <command>` (the command that runs the whole offline suite), or set PI_AUTOWORK_VALIDATE in the runner's settings.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
