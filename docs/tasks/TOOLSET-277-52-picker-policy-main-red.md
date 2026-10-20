# TOOLSET-277-52: picker-policy MAIN repair evidence

## Reported main failure

The DOCS-MAINTAINER trigger reports MAIN red at
`171b26bafd4f8045b68365f3d6d1de77d56e148d`. The runner's inspected
`main_check.json` agrees and identifies last green
`3a00a05de7f40fe8b9865a4a8ee448c2c9e76f53`. Its failures are:

- `test_picker_policy.PickerPolicyTests.test_core_stays_lean_and_points_to_every_reference`
- `test_picker_policy.PickerPolicyTests.test_no_early_exit_and_terminal_results_continue`

The original receipt is in the runner's private state directory, under
`main_check.json`, `main-check.log`, `main-check.exit` and
`main-check-reruns.log`. The expected shared
`.git/autowork-execution/main-evidence/` directory is absent at inspection;
TOOLSET-234-d4 owns making that evidence available to workers. This task does not
wait for it: both reported assertions reproduce directly from repository files.
No `slot-data/MAIN/` report exists, and this new task has no previous worker report.

## Focused reproduction

At this checkout's `2c4bf2cd895a1c9072ddd85925650365ba412bd4`, run:

```sh
python3 -m unittest discover -s skills/autowork/scripts -p test_picker_policy.py -v
```

Executed by this documentation pass: exit 1; six tests ran, four passed and the
same two tests failed. Exact assertion signals:

```text
AssertionError: 16076 not less than 16000 : core SKILL.md must stay lean; move detail to references/
AssertionError: 'version: 0.28.1' not found
```

`skills/autowork/SKILL.md` declares `version: 0.28.2`, while the test embeds
`version: 0.28.1`. All current reference files are linked from the core, checked
separately because the size assertion fails before the test's link loop.
These are deterministic structural observations, not evidence of model behavior
or a product-runtime defect. The full check was not rerun by this docs-only pass.

## Commit and path evidence

The supplied trigger truncates its tenth commit to `07b03`; the inspected runner
receipt resolves it to `07b0338` and retains this complete reported window:

```text
171b26b Merge remote-tracking branch 'origin/main'
f057d64 fix(parallel-state): reconcile survives unrelated worker history; adoption clears a stale pause
24748e1 feat(fleet): tasks being worked on list above finished commits waiting to land
653998e Merge remote-tracking branch 'origin/main'
ce092d9 fix(autowork): held conflicts are resolved side by side, beside the loop
5cfb7f8 Merge branch 'claude/agent-adbcb1a7e31dede8d'
1f6364d test(parallel-state): model-based random walks of the worker slot state machine
a41e3f0 docs(research): orchestrator reliability and plan quality; queue follow-up runner tasks
42f257a Merge branch 'claude/agent-af5f9682ed8494b25'
07b0338 feat(docs-sync): plan-lint groups Touches overlap per shared path
8b2ea7b feat(docs-sync): goals.py plan-lint checks task contracts before dispatch
440d5dc Merge branch 'claude/agent-ab694257a87bc1786'
023a76f feat(check): tree guard and fix-hotspot report
263c686 feat(planning): plan disjoint, testable batches for parallel Autowork
f5cf367 fix(autowork): held conflicts are resolved before the next review starts
db9a488 Merge branch 'main' into pi-autowork/20261017-134358
2efdafb fix(pi-autowork): the wait for a session in the main checkout is said once per session
781b8b3 Merge branch 'main' into pi-autowork/20261017-134358
```

`git show --stat` for the trigger commits shows changes to fleet display,
coordinator conflict recovery, parallel state/model tests, plan-lint, research and
planning files. Those unrelated changes are context, not proven causes or scope
to rewrite them. In the full receipt window, `263c686` changes
`skills/autowork/SKILL.md`; this and the failing test's direct file reads bound
Touches to that core, its references and `test_picker_policy.py`.

## Repair boundary

The owner explicitly requests one repair task first in Now for uncovered MAIN
failures. No open task names these failures. TOOLSET-184-b3 is already ledger-done
and archived; its older integration/scratch receipt is historical, not a reason
to reopen that task or replay its candidate. TOOLSET-126-6b is broader prose-test
optimization, not this bounded main-gate repair.

Restore the lean core and maintain useful policy regression coverage without
pinning an obsolete incidental version. Preserve all continuation, authority,
stop, reference-discovery and no-busywork semantics; neither increasing the size
limit nor deleting assertions wholesale establishes repair. Move detail into
existing references if needed and retain their links. No runner behavior change,
live operation, new authority or waiver of the full offline gate is required.
