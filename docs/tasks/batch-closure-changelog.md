# RUNTIME-BATCH-CLOSE-01: batch closure changelog snapshots

Status: implemented and independently reviewed; manually closed for offline delivery.
Integration, publication and live adoption remain separate delivery observations.

## Source and bounded contract

Under the owner's authorized implementation-through-release work, source-backed
diagnosis identified
serial predecessor closure adding CHANGELOG bytes after batch checking, causing
`worker.batched_verdict` to reject the next merge through `same_code`.
Sources: `Src/pi_autowork/worker.py` (`merge_batch_candidates`, `verify_batch`,
`batch_publications`, `batched_verdict`),
`Src/pi_autowork/engine/parallel_integrate.py` (`changelog_entry`, `close_writes`),
`Src/pi_autowork/coordinator.py` (prefix promotion and merge trains), and
[batch prefix contract](../../pi-autowork/README.md#passing-batch-prefixes).

Materialize deterministic predecessor changelog proposals in the disposable
batch chain using the existing closure renderer, before merging the next
candidate. Retain the candidate merge head before its own preview; review
HEAD^2 must remain the admitted candidate. Bind preview parentage, exact
CHANGELOG-only bytes, retained reports and task contracts. Gate and publish the
final merge, not an unchecked final closure preview. A dependent next train car
previews the previous tip task before its first merge; missing context must
fall back conservatively. Actual closure remains the serial engine operation.

## Acceptance

- Real-Git two/three-candidate batches contain generated predecessor bullets;
  actual matching later merges consume the batch verdict once without another
  model/gate run. A custom check sees exactly the expected new changelog bytes.
- Arbitrary bullet, mode/type, source, report, task contract or preview-binding
  changes reject reuse. Missing reports do not grant equivalence. Auto-skipped
  model reviews still require the exact tree and configuration.
- Conflict-skipped and failed predecessors do not authorize reuse of absent
  changes. Prefix promotion and next-train-car behavior preserve checked-tree
  identity and candidate parents.
- TDD red/green and focused affected tests provide offline evidence; independent
  review precedes manual closure. No claim of live/model qualification.

## Exclusions

No CHANGELOG metadata allowlist, cache-input or planning-only relaxation; no
synthetic closure, receipt or task completion; no mutation of candidate
worktrees, reports, canonical changelog, live runtime or services by scratch
preparation; no broad refactor. Integration/publication are separate authorized
delivery steps, not effects of preview preparation. Custom checks and exact
skipped-review trees retain their current policy. No dependency: this is an
independent bounded repair, not another task's closure.

## Offline implementation and review evidence

- The real two-candidate regression first failed with three gate executions
  instead of two, then passed with predecessor previews. Real three-candidate
  and next-car/train scenarios passed, including a gate reading exact changelog
  bytes. Prefix/failed-review regressions passed (three tests).
- Parent independently ran all 36 batch-focused worker tests and the real
  three-candidate scenario. All eight closure-specific tests passed after the
  report-identity correction, both in the parent and independent reviewer.
- Additional focused runs passed: review policy (21), main check (30), closure
  documents (five), and changelog renderer/integration (one). Counts overlap
  with review reruns and are not an aggregate unique-test total.
- Removing preview preparation, retained-input binding or mode proof caused
  the corresponding regression to fail. Restored implementation passed.
- Independent review found one compatibility defect: abbreviated report SHAs
  were being rejected despite the engine accepting them. A new real-Git test
  failed before correction, then passed with the existing engine resolution
  rule, including rejection of wrong/nonexistent/empty/non-string commits.
  Final independent review found no remaining blockers and also exercised
  candidate-parent, no-proposal, legacy and replay cases.
- The implementation delegate reached its time limit after tests/metadata,
  before committing. The parent took over, verified the retained changes,
  corrected the review finding and performed scoped closeout.
- Affected-test selection expanded to all 157 modules; no redundant full suite
  was launched. The runner retains its normal full-main check. Some existing
  batch/independent fixtures emitted subprocess ResourceWarnings; passing
  assertions do not establish absence of a runtime resource leak.
- Task-store validation and whitespace checks passed before commit. This is
  manual offline closure, not a coordinator receipt, model evaluation, live
  batch observation or production acceptance. Existing broad docs/tasks
  equivalence is unchanged and is not newly qualified here.
