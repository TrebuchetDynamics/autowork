# Executable blocker recovery

Use this after a demonstrated prerequisite/consumer/publication failure. Reconcile
exact live ownership first. These helpers repair engineering preparation, not owner
intent, review approval, native admission, credentials or delivery destinations.

## Accepted task contracts

As the canonical integration owner, use `terminal` to get `goals.py revision` and run:

```sh
python3 <skills-root>/repo-docs/scripts/recover_backlog.py /absolute/consumer \
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
through repo-docs first; do not insert approval merely to obtain a passing gate.
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
python3 <autowork>/scripts/prepare_prerequisites.py \
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

After the bounded repo-docs fallback has reconciled its proposal into the real
consumer, use `terminal` to run:

```sh
python3 <autowork>/scripts/retry_selection.py /absolute/consumer
# For an explicit named slice, preserve both bounds:
python3 <autowork>/scripts/retry_selection.py /absolute/consumer \
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
python3 <autowork>/scripts/publication.py --repo /absolute/consumer \
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
