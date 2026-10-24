# TOOLSET-378: repair affected-check completeness before retrying relocation

## Disposition

Keep [TOOLSET-378-07c50be2](../../tasks/items/TOOLSET-378-07c50be2.md)
open, with every original acceptance item and its updater-only Scope, Touches,
Checks, exclusions, authority, section and rank unchanged. Add the disjoint
verification prerequisite
[TOOLSET-384-45005b0c](../../tasks/items/TOOLSET-384-45005b0c.md), before it in
Next. No task is closed, qualified, superseded or represented as delivered.

The accepted [native updater relocation](../plans/structural-audit-2026-10.md#native-updater-relocation)
and [batch verification contract](../plans/structural-audit-2026-10.md#batch-verification-and-completion)
retain focused/affected checks and a separate post-landing full main check.
[TOOLSET-338-82](../../tasks/items/TOOLSET-338-82.md) also records the accepted
rule: affected-only landing evidence must not qualify main as full-suite green.
The prerequisite repairs that existing verification contract, not updater behavior
or the flaky runner test named in its log.

## Evidence read in place

Private execution artifacts remain in their original locations, not copied into
this checkout or commit:

- `.git/autowork-execution/slot-data/TOOLSET-378-07c50be2/attempt-1/report.json`
  and `attempt-2/report.json`: both candidates changed exactly the six declared
  updater/source/test files. Attempt 2 reports 111 updater and 25 quiet-restart
  tests passing, but affected execution was terminated after 1800 admitted seconds
  (exit 143); it explicitly does not claim an aggregate pass.
- `.git/autowork-execution/slots/TOOLSET-378-07c50be2.json`: attempt 2 is held
  for validation, not running or waiting to land. Neither recorded worker PID
  existed at inspection. Both attempts have `ledger_edit_dropped = null`, and
  neither saved attempt directory contains a proposed ledger patch. There is
  no dropped proposal to apply.
- The runner state's `review-findings/TOOLSET-378-07c50be2.json` names trial
  integration `3a2d71ddecc5d88539bdb58a61213f519a0a4222` and only the finding
  “the full check stopped before its results were complete (exit 1); the rest
  never ran”. The integration receipt/log pair
  `.git/autowork-execution/936dd2fa4f0b459fb96cbf4377b2e28f.{json,log}`
  records exit 1, without a concrete updater review defect.
- In that runner state's `full-check/TOOLSET-378-07c50be2-merged.log:78,87,1321`,
  the actual run says `Offline inventory: 72 modules in 3 directories`, starts
  CHECK sections and ends `Offline result: 2 test directories passed; 1 failed;
  3 modules excluded.` This is a completed affected selection, not a nameless
  crash before results. Its three sections contain 53, 10 and 23 unittest unit
  summaries for 42, 7 and 23 modules, respectively (including the two sharded
  modules).
- The adjacent `-merged.reruns.log` records the sole named failure,
  `test_pi_autowork.EngineTests.test_a_changed_reviewer_reviews_held_commits_again_by_itself`,
  passing alone in 36.513 seconds. The adjacent `-merged.reruns.json` nevertheless
  sets `incomplete = true`; `.gate.jsonl` records that as the hold reason.
  This one isolated pass is not three-revision flaky qualification and does not
  justify a test-hardening or product-repair task for that test.
- Candidate `233d071aaa67585b37a34b140ebe0de46c469550` and its trial integration
  are not ancestors of maintainer base `0c1a5373703aa8c3e60d804a235addac9b3fb90d`.
  Retained worktrees, reports and runtime records are left untouched.

## Source-backed repair boundary

`Src/pi_autowork/main_check.py:452-497` reconstructs all discovered offline
units whenever it sees `Offline inventory:`, regardless of an affected selection.
It then requires every full-inventory directory to appear. On the current base,
a read-only call of `complete_results` on the saved log returns False: it expects
five directories, whereas the completed affected run legitimately contains three.
The same reader exists at the retained worker's base `24df62b93b4164184e0a7346218580b95a69b88d`.

`Src/pi_autowork/worker.py:606-619,653-681` has the actual landing command in
`_run_gate`, but `gate_reruns` does not pass it to `main_check.rerun_failures`.
`main_check.py:574` derives the receipt's incomplete flag from `complete_results`.
`scripts/check.py:239-321` filters affected modules before emitting inventory,
CHECK sections and the terminal result, and shards only those selected modules.

The prerequisite should characterize this mismatch in private fixtures, thread
the producing command through the gate/rerun path where needed, and derive
expected units from that command's verified selection rather than the entire
repository or untrusted counts alone. Reuse the existing checker selection and
unit APIs; do not execute arbitrary shell commands while reading evidence.
Keep missing/truncated/duplicate sections, missing shard summaries, unknown
commands, signals, timeouts and incomplete core checks fail-closed. Exercise the
real gate/rerun receipt path as well as the pure completeness reader. Preserve
full-suite behavior and the rule that affected-only green is not main full green.
No receipt/schema, authority, source-integrity or updater-policy redesign is needed.

After the prerequisite lands, resume the updater relocation against the actual
current base, preserving retained work and all three original acceptance items.
Complete its existing focused/affected checks and required review; neither the
saved worker claims nor this metadata repair establishes implementation acceptance.
Installed-profile integration and live gateway behavior remain NOT_CHECKED.

## Maintainer checklist

- [x] Read task, goal, accepted sources, prerequisite, both worker reports, held
  slot, finding, integration receipts and underlying gate/rerun evidence.
- [x] Reproduce the completeness mismatch with a read-only source call; inspect
  the selected module and shard summaries and current/retained-base reader.
- [x] Keep implementation and checker repair disjoint; record producer and
  dependency through the task CLI without changing original acceptance or scope.
- [x] Task-store validation: 147 tasks, 17 goals, no drafts. Docs check,
  original-field/acceptance/note preservation assertions, disjoint-scope/order
  assertions, local links/anchors and whitespace checks passed. Independent
  read-only review found no findings. Only the two task records and this note
  are delivered; no implementation tests, full-suite pass or live qualification
  are claimed.
