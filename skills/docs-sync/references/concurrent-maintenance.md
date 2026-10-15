# Concurrent ledger maintenance

## One canonical owner

Use one integration owner for repository-root `goals.json`, `TODO.md`, and their task bodies.
Workers may edit and validate branch-local task files in linked worktrees, then
return scoped changes for normal review and integration, not replacement ledger snapshots.
A proposal names the goal/task IDs, base revision, intended CLI operations, evidence,
source identity, and complete task-body changes. It does not authorize a new goal,
change acceptance, or close the parent milestone.

The integration owner checks each proposal against the current canonical ledger.
Apply accepted operations through `scripts/goals.py`. Do not copy a worker's
`goals.json` or `TODO.md` over the canonical files. Allocate task IDs against the
current ledger under owner control. An occupied ID requires reconciliation,
not overwrite or automatic reinterpretation of the proposal.

## Reconcile a stale or occupied target

Use after a `stale revision`/`stale write` refusal, a baseline mismatch, or when
an actual concurrent writer holds the target. A process name, historical card or
claim alone does not establish a conflicting write; check actual activity.

1. Preserve the rejected proposal and its evidence. Reread sanitized Git HEAD/status,
   canonical ledger/TODO, target task/goal, affected blocks, focus and ownership.
   Compare by stable IDs; a whole-file revision change does not say what changed.
2. If the target was completed, claimed, re-scoped or reprioritized, or landed work
   satisfies the proposal, reconcile that outcome and withdraw obsolete edits. Keep
   another writer's equivalent repair; never reopen done work, widen an active
   worker's contract or change its admission pins. Re-pin to the new base and rerun
   the discriminating source check before allocating; IDs and meanings can shift.
3. If the target is unchanged, keep only the scoped old/new replacements and intended
   operations. Under the lock, build from the latest bytes so unrelated tasks,
   transitions, evidence and order survive. Apply ledger changes through supported
   operations with a fresh `revision` per mutation; normal stale refusal still holds.
4. If the user keeps another session as integration owner, leave TODO, ledger,
   blockers and archive untouched, including `fmt`/`render`/`archive`. Save the
   targeted patch (relative to captured baselines, with its repository-root working
   directory), complete proposed bodies, intended operations, base, provisional IDs
   and consumer-gate reasons in an authorized durable location; mark partial
   proposals partial. Report absent proposed tasks as pending integration, not ready.
5. After integration run `fmt`, `validate`, `render` and the same consumer gate once
   on the final batch. Rerun only checks whose code/test/dependency/environment
   inputs changed, not checks invalidated only by unrelated ledger additions.

The canonical owner already has this clerical authority within scope; do not turn
safe reconciliation into a permission question. If a safe integration route exists,
complete it rather than stopping at a proposal.

## Executable coordination

Every CLI command takes an exclusive advisory lock before reading the ledger.
The lock covers loading, command validation, mutation, replacement, and rendering
for that invocation. In Git repositories, the lock lives at
`<git-common-dir>/.docs-sync-goals.lock`. Primary and linked worktrees share it.
Without Git metadata, local fixtures use `<resolved-repo>/.docs-sync-goals.lock`.
Do not remove an active lock file: replacing its inode can create two lock owners.
A non-CLI read/compare/write must acquire the exact lock path of the helper actually
invoked; a legacy alias lock name does not serialize the same writes.

Before Git repository-identity subprocesses, construct an environment that removes
all inherited `GIT_*` overrides while retaining unrelated process settings.
Repository, worktree, common-directory, index, object-store and config overrides
can redirect discovery even when `cwd` names the intended checkout. Apply the
same sanitization to canonical-target validation and lock discovery; otherwise
one invocation can validate one repository and lock another.

Verify this boundary with real temporary Git repositories and CLI processes:
1. Hold the intended repository's lock; inject another repository's Git overrides
   into a mutation and require it to remain excluded until the correct lock releases.
2. Invoke a linked worktree without `--canonical-repo` under primary-checkout
   overrides and require the requested worktree to remain the target, with the
   primary ledger unchanged.
3. Exercise config-based overrides as well as directory/index/object overrides;
   retain ordinary aliases, no-Git fixtures and explicit canonical-target tests.
Run `python -m unittest test_goal_concurrency -v` from the scripts directory after
changing identity discovery. Passing ordinary concurrent-update tests alone does
not exercise redirected lock identity.

Commands read and write the requested checkout by default, including a linked
worktree. The shared lock serializes cooperating commands across those checkouts;
it does not merge their task files or grant integration authority. An explicit
`--canonical-repo` selects another verified checkout of the same Git repository:

```sh
python <skill>/scripts/goals.py revision <worker>
python <skill>/scripts/goals.py evidence <worker> GOAL-1 --expected-revision <revision> --kind executed --ref '<exact check>' --result pass
```

Legacy `repoDocs.backlogAuthority` configuration is ignored. It cannot redirect
reads/writes or turn a historical native binding into an execution gate. Apply
reviewed changes to the canonical checkout under existing ownership and publication
policy; preserve newer task entries and concurrent changes.

Use `revision <repo>` to get a SHA-256 token over the exact ledger and TODO bytes,
including a missing-file distinction. Pass `--expected-revision <token>` to a
later command. A mismatch exits nonzero with `stale revision` before either
content file is written. Obtain a fresh token after each accepted operation.
Do not retry a rejected snapshot blindly. Re-read current state and reconcile.

The CLI rechecks the transaction snapshot immediately before `os.replace`.
A detected out-of-band edit exits nonzero with `stale write`; temporary output
is removed. Replacement uses a flushed, fsynced temporary file in the same
directory. Existing permission bits are retained. Repository path aliases are
resolved before coordination. Symlink ledger, TODO, and lock files are refused.
Git targets must name their repository root, not a subdirectory.

`render` reads both files under the same lock and replaces only the coverage
block. Complete task bodies and their continuation bytes outside an existing
marked block remain unchanged, including CRLF and trailing blank lines.
When no coverage section exists, rendering appends it without trimming existing
bytes. An existing unmarked `## Goal coverage` section retains its legacy
migration behavior. Rendering does not invent task bodies. It archives explicitly completed or
superseded bodies under the separate archive contract.
Fenced examples are not replacement targets. Unmatched, reversed or duplicate
coverage markers are rejected before writing; reconcile their intended boundaries
without deleting task bodies. Generated table values are escaped so multiline
titles and evidence cannot become task entries or coverage markers. Redaction
preflights this rendering before changing the ledger or archiving originals.
`validate` also checks goal/task membership and the task-ID spelling supported by
TODO bodies; `add-task` refuses unsupported IDs before writing.
After all accepted mutations, run `validate` and a final `render` against the
canonical target. Mutations retain the existing CLI behavior: they do not
implicitly render. A render before a later mutation describes its own snapshot,
not the later ledger revision.

### Limits

This is local POSIX advisory coordination, not a distributed transaction,
authorization system, or new tracker. It requires `fcntl` and local filesystem
lock/rename behavior. Direct writes that ignore the lock cannot be made fully
atomic with the comparison: a hostile or uncoordinated writer can change a file
between the final comparison and rename. All participating writers must use this
CLI, or acquire the same lock and reconcile current bytes. The stale guard detects
observed edits before comparison; it does not promise protection against hostile
filesystem races, NFS semantics, or crash-atomic updates of multiple files.
Python helper imports are not the serialized user interface. Use the CLI.

Keep full task-body edits under the integration owner. If a separate tool edits
TODO, it must share this lock across read/compare/write. Otherwise return the body
change as a proposal and let the integration owner apply it with current-byte
comparison. Never publish a worker's stale full-file rewrite.

For a scoped dirty-worktree documentation proposal:
1. Capture exact baseline bytes for each writable document and author against a
   private pinned candidate containing those bytes, not HEAD alone. With `GIT_*`
   overrides removed, discover context via `git diff HEAD --name-only -z` plus
   `git ls-files --others --exclude-standard -z`; `git ls-files -m` misses
   staged-only changes. Copy only inspected required inputs, never credentials or
   runtime state, and keep foreign overlays separate from authored replacements.
2. Return targeted old/new replacements and a baseline-to-candidate patch; a
   repository-wide Git diff includes unrelated pre-existing work. Anchor insertions
   to a unique heading or paragraph, not a blank line from a generic diff opcode:
   repeated whitespace makes automatic replacements ambiguous. After a partial
   patch failure, inspect which replacements landed and resume only unapplied
   hunks, rather than replaying the batch. For a scoped whitespace check,
   `git diff --no-index --check -- <baseline> <candidate>` exits 1 for any difference:
   accept 0 or 1 only with empty stdout and stderr.
3. Under the shared lock, compare all targeted canonical baselines, and the source/
   test/dependency bytes candidate checks used, before applying replacements. If
   only the valid marked coverage block changed, require all other bytes to match
   and keep the fresh block. If other changes are disjoint, apply only the attributed
   baseline-to-candidate patch and verify both survive; otherwise reconcile from the
   new baseline. Verify that integrated authored bytes equal the reconciled candidate.
4. Release the manually held lock before invoking `goals.py`, because the CLI
   acquires that lock itself. Apply evidence/status operations only through the CLI.
5. Run `fmt`, `validate` and `render` against the canonical target. Confirm every
   live ledger ID has a task body outside the generated coverage block. Repeat
   `fmt`/`render` and compare both files byte-for-byte; unchanged inputs should yield
   a no-op, while a concurrent update requires a fresh snapshot rather than a
   nondeterminism claim.

### Verify task-only additions without absorbing foreign changes

1. Save exact canonical `TODO.md` and `goals.json` baselines before authoring.
   Prepare a targeted insertion in the private pinned worktree; do not use its
   HEAD version as the baseline when canonical documents already contain edits.
2. Allocate each numeric ID from the current ledger immediately before `add-task`.
   Obtain a fresh `revision` token for each mutation and pass `--expected-revision`;
   reserving a sequence in memory does not protect it from another writer.
3. After integration and `fmt`/`validate`/`render`, compare pre-existing task
   objects by stable ID, not by zipping serialized arrays: normalization can reorder
   rows without changing their meaning. Require unchanged statuses, dependencies,
   sections and focus except for explicitly authorized deltas. When a cancellation
   relocates a body, compare priority sequences with that moved ID removed to prove
   all other relative ordering survived; do not require an unchanged whole sequence
   or excuse unrelated reordering. For each affected goal, allow only intended
   membership changes. For an evidence-only addition, remove the exact authored
   record once and require prior evidence unchanged; `fmt` sorts evidence, so the
   new record need not be last.
4. For an insertion-only TODO change, normalize only the marked generated coverage
   block in both snapshots, remove the exact authored insertion once, and require
   the remaining bytes to equal the baseline. Check insertion multiplicity so this
   comparison cannot hide a duplicated body or an unrelated deletion.
5. Match all open/in-progress ledger IDs to actual task-entry markers outside the
   generated coverage block. Do not count incidental prose or table references as
   complete bodies. Validate added links and anchors in the canonical checkout and
   the artifact-free documentation candidate, then repeat `fmt`/`render` and require
   byte-identical ledger and TODO output when no concurrent change occurred.
6. Report the new outcomes and first eligible open slice separately from in-progress
   entries. State that backlog validation proves neither worker dispatch nor product
   qualification; do not add its passing checks as evidence that a feature is met.

Preserve completed task statuses, priorities and historical plan bodies during
source-study adoption. Record research as inspection evidence for the owning goals,
not as executed proof that the requested product outcome works.

## Reconcile after workflow updates

Resolve the loaded skill's installed helper and verify its bytes against the
qualified rollout revision; a surviving compatibility copy or a dirty source
checkout does not prove the updated rules ran. Keep old helper-bound receipts as
history. Then reconcile as below, applying routine broken-link and stale-source
wording repairs in the same batch rather than leaving them as owner decisions.
Before reporting, reread every receipt-bound input and the helper fingerprint;
rerun receipts whose input closure changed, since one shared ledger edit can
invalidate several plan checks. Preserve later owner progress; never revert
another owner's claim to make a preservation check pass. Respect an intentionally
Markdown-only queue without manufacturing a ledger or native admission.

## Reconcile divergent task contracts

1. Snapshot canonical TODO, ledger, affected plans and archive; run `validate`.
   Inventory live bodies with the maintained `goals.py` parser, not numeric-only ID
   patterns, excluding generated coverage. Archived bodies, including unchecked
   historical copies, are history rather than open work or status drift.
2. Compare each body's checkbox/section, goal and `Dependencies:` with the ledger
   in both directions. Move receipt-only or coordination mentions out of the field;
   a goal prerequisite and a same-named task are distinct. Repair edges only from
   accepted intent; never delete one to clear a cycle or create eligibility.
3. Preserve local/remote ID collisions as unresolved mappings; do not renumber or
   import statuses. Index historical tasks under existing IDs only when source and
   receipts support completion; for local-only completion keep the integration gap.
4. Check Sources against actual files/anchors and nested scope, and reconcile
   acceptance against the current deliverable, not its title. Repairing a link does
   not supply missing approval; keep proposed subdecisions proposed.
5. Apply under the lock with baseline comparison, preserving statuses, priorities,
   evidence, focus, order and archive prefix. Run `fmt`, `validate`, `render`, then
   `backlog-check` per affected accepted plan and its exact IDs; exit 2 is a
   reconciled hold, not a clerical failure. Repeat for byte stability, take the next
   task from `next --json`, and keep routine receipts out of product plans.

## Evidence and acceptance contracts

### Hypotheses are not accepted causes

Record a plausible explanation as an evidence-graded hypothesis. Name supporting
and conflicting observations, alternatives, reproduction conditions, and the
next discriminating check. Do not publish it as an accepted causal claim before
reproduction and independent verification. A passing local fixture can verify a
code path without proving a causal explanation or a deployed outcome. Keep
hypothesis, reproduced observation, independently verified cause, and accepted
decision separate. These instructions establish a workflow contract; they do not
claim that a radio, SDR, HF service, or production defect has been fixed.

### Runtime claims need measurements

Record the exact command, source/test/dependency identity, environment, date,
measured duration, exit status, and captured output. State the measured scope.
Do not replace a missing measurement with an approximate claim such as `~30s`.
Choose the cheapest sufficient focused check before expensive gates. Reuse a
receipt only when its relevant source and environment binding still matches.
A changed dependency invalidates that reuse. Full-suite, live qualification, and
mission delivery remain separate gates; focused tests do not close them.

### API route coverage is a normative contract

Compare the authoritative supported operation set with registered runtime routes
and contract-test coverage using a machine-readable comparison. Include methods,
paths, versions, authentication, responses, and errors where applicable. Report
missing, extra, and unverified operations. A manually written status table or a
valid OpenAPI document alone does not prove runtime conformance. If comparison
cannot run in scope, preserve the normative route requirement and record an
unverified gap. Do not lower the required coverage to match current code.

### RF metrics retain the accepted bar

Separate controllable implementation metrics from environmental observations.
Examples of controllable checks include configured sample-rate behavior, DSP
correctness against fixtures, buffering, and bounded recovery. RF propagation,
antennas, interference, and station availability require their own environmental
context and observation interval. Do not treat an environmental failure as proof
of a code cause, or a fixture pass as RF mission success. Record measurements,
limits, and remaining mission criteria without weakening the accepted bar.
Changes to acceptance require an authoritative owner decision, not a documentation
pass that makes the current implementation appear complete.

## Focused verification

Run the local executable checks without profiles, providers, or production:

```sh
cd <skill>/scripts
python -m unittest test_goals test_milestone_focus test_goal_concurrency -v
```

`test_goal_concurrency.py` uses real CLI processes, temporary Git repositories,
and linked worktrees. It checks shared-lock exclusion, retained parallel updates,
canonical targeting, stale TODO refusal, in-flight edit refusal, exact task-body
preservation, symlink refusal, and existing file permissions. These are fixture
results, not proof of production deployment or all workflow policy execution.
