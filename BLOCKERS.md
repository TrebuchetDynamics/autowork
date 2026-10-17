# External input blockers

Only confirmed USER_INPUT, SUDO or USER_DECISION blockers belong here. Internal
engineering and integration work remain in [TODO.md](TODO.md). This file creates
no extra approval step or execution authority.

## Active

<!-- pi-autowork:questions:start -->

### Q-TOOLSET-148-88 — USER_INPUT — effort input — unblocks 43

- Task: TOOLSET-148-88 — One malformed Touches field holds its task, not the whole engine
- Needs: worker reported a blocker: Widen Touches to skills/autowork/scripts/parallel_integrate.py: retry_held parses current Touches in the scope and scope_request recovery paths before planner admission, so a malformed contract can still raise ValueError and block independent dispatch. Independent review reproduced both branches; the current parser/planner-only fix cannot satisfy whole-engine isolation without repairing this calle… (+2 more in report.json)
- Since: 2026-10-17T08:34:00Z
- Answer: Answer in TOOLSET-148-88's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-154-d3 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-154-d3 — Question IDs are single-line and stable, so BLOCKERS.md changes only when questions do
- Needs: worker reported a blocker: Coordinator must provide or run the required offline inventory in a sandbox-compatible fixture environment: a short temporary root outside the repository, fixture-local Git transport permitted without bypassing this worker's push guard, and isolated runtime-test settings. Resolve or triage the remaining audit-profile failures and tests-directory timeout from $TMPDIR/check.log. The required check c…
- Since: 2026-10-17T08:29:34Z
- Answer: Answer in TOOLSET-154-d3's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

### Q-TOOLSET-155-e2 — USER_INPUT — effort input — unblocks 0

- Task: TOOLSET-155-e2 — Keep owner-listed private terms out of public commits, pushes and runner integrations
- Needs: worker reported a blocker: Provide a privacy-clean baseline for the 20 paths in needs_touches, or explicitly authorize cleanup of those paths where permitted. The new required tracked-file gate finds existing references there; the worker cannot edit outside Touches. CHANGELOG.md is explicitly coordinator-owned and needs coordinator cleanup, not merely a widened worker scope. Changes remain uncommitted as instructed. On resu…
- Since: 2026-10-17T08:18:51Z
- Answer: Answer in TOOLSET-155-e2's TODO.md entry: widen `Touches:`, supply the input, narrow the acceptance, or add a dated `Owner decision:` line. The runner reruns it when the entry changes.

<!-- pi-autowork:questions:end -->

None.

## Resolved

None.
