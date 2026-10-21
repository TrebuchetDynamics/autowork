> Historical native-card reference. Card-specific prerequisites and commands below
> are retained for evidence only and are superseded by [current execution](owner-cycle.md).
> They do not govern current Autowork selection, recovery, review or integration.
> Deleted script paths resolve through the [removal commit](https://github.com/TrebuchetDynamics/autowork/commit/026e23baf4c226aac2c672e3d0e984a77996b9da); see the [removal record](../../../docs/plans/2026-10-20-owner-cycle-retirement.md).
> The current task store is `tasks/`, edited through `autowork tasks`; the TODO.md, goals.json and `goals.py` named below no longer exist.

# Executable blocker recovery

Use this after a demonstrated prerequisite/consumer/publication failure. Reconcile
exact live ownership first. These helpers repair engineering preparation, not owner
intent, review approval, native admission, credentials or delivery destinations.

## Recover locally before declaring a blocker

Check what the task and its actual consumer require. For scope, attribution or a
harness boundary, inspect the accepted spec and predecessor integration receipts,
not only Git refs. Verify the receipt's task, relevant artifact and source binding;
use evidence that satisfies that requirement. A missing named ref is not a blocker
unless that ref is actually required. Attribution does not replace a separately
required immutable commit, file hash, ancestry check or executable acceptance.

Reconstruct recoverable spec patches, fixtures and local inputs within existing
authorization now, in an owned isolated candidate when needed. Use the saved plan
and retained complete artifacts; do not request implementation permission again or
create a planning/recovery task merely to prepare inputs for the current task.
Restoring a pinned artifact requires equality with its original pin. Implementing
an accepted change without such a pin uses the task's checks; do not invent a
byte-equality requirement. Preserve foreign work, original admission evidence and
consumed budget. Retry the failed consumer after repair, then continue execution.

If a tool returns `pending_approval`, preserve its operation, resume step and request
ID when supplied; a missing display ID does not hold independent work. The host
approval applies to that operation and work that
depends on it; it is not missing product intent or a veto on independent work.
Use the host's supported approval/resume mechanism when available. Do not approve
it yourself, submit equivalent operations through another channel, or treat silence
as approval. The coordinator checks dependencies and live resource ownership and
continues independently authorized work in the same run; an assigned worker stays
inside its contract. Report the exact pending request once, not repeated planning.

## Accepted task contracts

As the canonical integration owner, use `terminal` to get `goals.py revision` and run:

```sh
python3 <skills-root>/docs-sync/scripts/recover_backlog.py /absolute/consumer \
  --plan docs/spec.md#accepted-slice --tasks TASK1 \
  --expected-revision <current-token> --source-commit <full-immutable-commit>
```

`--source-commit` is optional for accepted-source link repair and identical duplicate
removal. Missing bodies require an immutable regular-file TODO and ledger with the
same task ID, goal, title, dependencies and goal intent source. Restore the complete
body under its current ledger section; do not reopen completion or reset a lease.
The helper writes only TODO, leaves the ledger/plan unchanged, checks the consumer
again and returns the backlog-check state/exit. A second unchanged pass is byte-stable.
Only byte-identical duplicate bodies in the same section/checkbox state are removed.
Conflicting bodies, changed intent and missing acceptance remain unreconciled.

Existing accepted goal intent supplies a missing Sources link, not a new approval.
The referenced section must already say `Status: Accepted`. If acceptance metadata
or the plan itself is absent, recover actual owner evidence and reconcile that owner
through docs-sync first; do not insert approval merely to obtain a passing gate.
The consumer supports header-inline Goal, continued Sources and an explicit `Section:`
within `## Now / Next`; ambiguous sections still refuse. No product/profile changes
are authorized by this command. Linked worktrees still require canonical authority.

## Attributed immutable prerequisites

A source-freshness snapshot is not ownership. Recover the actual integration owner's
attribution receipt before running `prepare_prerequisites.py`. Its JSON contains:
`version: 1`, exact `workspace`, immutable `base`, nonempty `owner`/`evidence_ref`, and
`files` equal to the snapshot's explicit `path`/`sha256` rows. A caller attestation
is labeled as such; the helper does not independently certify the issuer.
Never create this receipt for foreign edits or infer it from a clean status.

```sh
python3 <toolset>/pi-autowork/engine/prepare_prerequisites.py \
  --source /absolute/consumer --target /absolute/private-input-worktree \
  --base <full-base> --snapshot /private/source-snapshot.json \
  --attribution /private/existing-owner-attribution.json --profile worker \
  --task inputs-task --check-json '["python3", "scripts/check_inputs.py"]'
```

The helper copies only those exact non-secret regular-file bytes into a new detached
base worktree, executes supplied acceptance checks and uses the existing finish-task
commit helper. It reads back the commit/ref and each attributed blob. Source HEAD,
index and working bytes are untouched; stale input, inherited symlinks, missing
provenance, failed checks and an existing task ref refuse. Failed preparation removes
its own private worktree. Keep the returned receipt and immutable commit, then give
that candidate to the existing `start_goal.py --candidate` assembly and initial guard.
A stale-source exit can retain a private commit: reconcile it, never report admission.
Do not publish private input ancestry merely because a local commit was prepared.

## Retry against the consumer, not a docs scratch tree

After the bounded docs-sync fallback has reconciled its proposal into the real
consumer, use `terminal` to run:

```sh
python3 <toolset>/pi-autowork/engine/retry_selection.py /absolute/consumer
# For an explicit named slice, preserve both bounds:
python3 <toolset>/pi-autowork/engine/retry_selection.py /absolute/consumer \
  --plan docs/spec.md#accepted-slice --tasks TASK1,TASK2
```

Selection and consumer readiness are reread under the shared ledger lock; cached
`none` or a passing scratch validation cannot substitute. Native canonical binding
is honored. No backlog stays draft; dependencies, in-progress ownership and unrelated
focus remain held. A ready receipt carries the exact selected open task, but live
lease availability and execution permission remain unknown until native handoff.

## Publication readiness

Forward existing exact worker publication authority through `start_goal.py`; do not
invent a remote because one is called origin or choose among several push URLs.
For an attributed completed source commit, use `terminal` to run:

```sh
python3 <toolset>/pi-autowork/engine/publication.py --repo /absolute/consumer \
  --base <full-base> --commit <receipt-full-sha> --profile worker --task TASK1 \
  --contract-file /private/exact-contract.txt --authority /private/owner-publication.json
```

The existing authority validator binds workspace/profile/task/contract and one exact
owned task ref. The helper reads the authorized remote's actual push destination,
not a different fetch URL or stale tracking ref. Missing authority, multiple push
URLs, unavailable remote/ancestry and divergence remain explicit holds. It never
pushes, fetches, forces, merges or calls a task-ref match main delivery. Readiness
also does not qualify secrets/private history, required review or protected-main
checks. Gate the public candidate separately; publish only under existing authority
and read back this exact target afterward.

## Verification

Run the real-Git `test_backlog_recovery`, `test_prerequisite_recovery`,
`test_retry_selection` and bare-remote `test_publication_readiness` fixtures, followed
by `python scripts/check.py --timeout 180` from the toolset root. Offline tests prove
these helpers, not that a live picker followed them or a native worker was admitted.
