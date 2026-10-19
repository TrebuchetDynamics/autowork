# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-200-c1 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-200-c1 — A status read waits for the writer lock, and a failed read never means nothing is running
- Needs: changed files the coordinator owns: goals.json
- Since: 2026-10-19T08:56:50Z
- Answer: Answer in TOOLSET-200-c1's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-215-91 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-215-91 — Bundle skills load read-only from the plugin, so the skill review never edits them
- Needs: worker reported a blocker: Provide an installed upstream Hermes revision that refuses background_review edits, patches, and supporting-file writes to skills.external_dirs, then rerun the native safety probe before implementing this migration. Current Hermes e06df9c2eae6901f4c88f464e0ae6e753c0428b8 allows the demonstrated patch. Task scope item 4 requires stopping rather than shipping a weaker rule, and task exclusions prohi…
- Since: 2026-10-18T19:00:42Z
- Answer: Answer in TOOLSET-215-91's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-252-4c — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-252-4c — A worker blocker that names another open task waits for that task, occupies nothing meanwhile, and resumes when it lands
- Needs: changed files the coordinator owns: TODO.md, goals.json
- Since: 2026-10-19T11:30:10Z
- Answer: Answer in TOOLSET-252-4c's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-164-f1 — USER_DECISION — effort investigate — unblocks 0

- Task: TOOLSET-164-f1 — A standing DOCS-MAINTAINER worker repairs, re-sorts and syncs each repository's task docs
- Needs: worker timeout after 5400 s
- Since: 2026-10-19T08:56:50Z
- Answer: Read the evidence (the worker's report and validation log under .git/autowork-execution/slot-data/TOOLSET-164-f1/), then rescope or split TOOLSET-164-f1 in its TODO.md entry. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
