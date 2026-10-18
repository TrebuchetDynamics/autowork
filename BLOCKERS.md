# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-138-62 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-138-62 — Reconcile the fleet's unmerged parallel-admission branch into main
- Needs: worker reported a blocker: Coordinator must reconcile the original versus current-history commit identities and provide an executable acceptance contract: either authorize an integration path preserving original 3848aaa ancestry, or explicitly update the acceptance and dependent TOOLSET-139-62 pin handling to verified current-history identities. Original merge de02326 exists but is not in main/origin/main/worker history; cu…
- Since: 2026-10-18T22:14:18Z
- Answer: Answer in TOOLSET-138-62's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-139-62 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-139-62 — Heal toolset pin drift so every runner receives released fixes
- Needs: worker reported a blocker: Provide a disk-backed task TMPDIR with at least 20 GB free (plus fixture headroom), or authorize relocating test scratch inside this task worktree, then rerun the resource-blocked offline modules. The supplied /run/user/1000/aw/aaf6b379/18 is on a 6.3 GB tmpfs and cannot satisfy the unchanged production guard. The worktree filesystem has approximately 400 GB free, but temporary paths were kept wit…
- Since: 2026-10-18T22:14:18Z
- Answer: Answer in TOOLSET-139-62's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-147-54 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-147-54 — Merge pending names its real cause and clears a dirty integration worktree safely
- Needs: worker reported a blocker: Provide an approved short disk-backed task TMPDIR outside every Git checkout, with at least 20 GB free for the unchanged fixture dispatch gate. The currently supplied /run/user/1000/aw/aaf6b379/23 is on a 6.3 GB tmpfs and cannot satisfy that gate. Resume this worktree's restored, staged candidate and rerun focused checks followed by independent review and the full offline gate; do not reimplement …
- Since: 2026-10-18T22:14:18Z
- Answer: Answer in TOOLSET-147-54's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-170-f6 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-170-f6 — Closeout waits only for a main-checkout session that holds the files it writes
- Needs: worker reported a blocker: Provide a lower-load offline validation host or a quiet validation window to rerun the required full gate without the unrelated budget-controller timing failure and resource-gated skips. The implementation and focused checks are finished, but the full gate remains red even at two test processes; no commit was made, as required for a blocked worker. Preserve this worktree's four modified files. Ind…
- Since: 2026-10-18T22:14:18Z
- Answer: Answer in TOOLSET-170-f6's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-215-91 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-215-91 — Bundle skills load read-only from the plugin, so the skill review never edits them
- Needs: worker reported a blocker: Provide an installed upstream Hermes revision that refuses background_review edits, patches, and supporting-file writes to skills.external_dirs, then rerun the native safety probe before implementing this migration. Current Hermes e06df9c2eae6901f4c88f464e0ae6e753c0428b8 allows the demonstrated patch. Task scope item 4 requires stopping rather than shipping a weaker rule, and task exclusions prohi…
- Since: 2026-10-18T19:00:42Z
- Answer: Answer in TOOLSET-215-91's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
