# Concurrent task maintenance

## One owner for task files

Only the owner, or the coordinator's own bookkeeping, edits files under `tasks/`.
A worker's commit that edits any task file is held and never merged. Workers and
other sessions return proposed task changes for the owner or coordinator to apply:
a proposal names the task/goal IDs, base commit, intended `autowork tasks` commands,
evidence and source identity. It does not authorize a new goal, change acceptance
or close a goal.

Apply accepted proposals through `autowork tasks` against the current store. Do
not copy another checkout's task files over the current ones. Allocate IDs from
the current store (`autowork tasks new-id`, or let `add` allocate); an occupied ID
requires reconciliation, not overwrite or automatic reinterpretation.

## How writes are guarded

Every `autowork tasks` write changes only the working tree and never commits. It
waits for the checkout's task lock, so two CLI writers never interleave; refuses a
file that changed since it was read, or since the `record_revision` you pass as
`--expect REV` (read it with `show ID --worktree` before deciding); refuses
contract, section and closing changes to a task whose attempt is live; and it is
undone when the resulting store does not validate. A refused write is reread and
reapplied, never forced. `autowork tasks validate --worktree .` checks uncommitted
edits without touching the index or refs. This guards cooperating writers; a
writer that edits task files directly can still race it, so use the CLI for every
edit and commit the batch once it validates.

Integration judges task edits by contract. Rank, title, short and notes are
bookkeeping. An acceptance, checks, dependency, authority or section change to an
admitted task sets its attempt aside or requires revalidation. Do not edit an
admitted task's contract while its worker runs; return the proposal to the
coordinator instead.

## Reconcile a stale or occupied target

Use after a refused write, a baseline mismatch, or when an actual concurrent
writer holds the target. A process name or historical note alone does not
establish a conflicting write; check actual activity.

1. Preserve the rejected change and its evidence. Reread sanitized Git HEAD/status,
   the target task or goal (`autowork tasks show ID`), focus, holds and ownership.
   Compare by stable IDs and fields; a changed file does not say what changed.
2. If the target was completed, held, re-scoped or reprioritized, or landed work
   satisfies the change, reconcile that outcome and withdraw obsolete edits. Keep
   another writer's equivalent repair; never reopen done work or widen an active
   worker's contract. Rerun the discriminating source check before allocating;
   IDs and meanings can shift.
3. If the target is unchanged, reapply only the scoped field and note changes with
   `autowork tasks`, so unrelated tasks, transitions, evidence and ranks survive.
4. If the user keeps another session as integration owner, leave `tasks/` and
   BLOCKERS.md untouched. Save the intended commands, complete proposed contracts,
   base and provisional IDs in an authorized durable location; mark partial
   proposals partial. Report absent proposed tasks as pending integration, not ready.
5. After integration run `autowork tasks validate --worktree .` once on the final
   batch. Rerun only checks whose code/test/dependency/environment inputs changed.

The owner or coordinator already has this clerical authority within scope; do not
turn safe reconciliation into a permission question. If a safe integration route
exists, complete it rather than stopping at a proposal.

## Verify task-only additions

1. Record the store's state before authoring (`autowork tasks list`), and the
   records you will change.
2. Add tasks with `autowork tasks add` and adjust fields with `field`, `place` or
   `move`; do not hand-write records.
3. Compare pre-existing records by ID: statuses, dependencies, sections, ranks and
   focus are unchanged except for explicitly authorized deltas. A diff of `tasks/`
   should show only the intended files.
4. Run `autowork tasks validate --worktree .`, check new `Sources:` links and
   anchors, and confirm the new tasks have no draft reasons.
5. Report the new outcomes and the first eligible open slice separately from held
   tasks. Store validation proves neither worker dispatch nor product
   qualification; do not record its passing as evidence that a feature is met.

Preserve completed tasks and historical plan bodies during source-study adoption.
Record research as inspection evidence for the owning goals, not as executed proof
that the requested product outcome works.

## Reconcile after workflow updates

Verify that the loaded skill matches the qualified rollout revision; a stale copy or
a dirty source checkout does not prove the updated rules ran. Keep old receipts as
history. Apply routine broken-link and stale-source wording repairs in the same
batch rather than leaving them as owner decisions. Before reporting, reread every
receipt-bound input; rerun receipts whose input closure changed. Preserve later
owner progress; never release another owner's hold to make a check pass.

## Reconcile divergent task contracts

1. Run `autowork tasks validate` and list the store. Records in a frozen archive
   are history, not open work or status drift.
2. Compare each open task's section, goal and `depends_on` with accepted intent.
   Move receipt-only or coordination mentions into notes; a goal prerequisite and a
   same-named task are distinct. Repair edges only from accepted intent; never
   delete one to clear a cycle or create eligibility.
3. Preserve ID collisions between checkouts as unresolved mappings; do not
   renumber or import statuses.
4. Check `Sources:` against actual files/anchors and nested scope, and reconcile
   acceptance against the current deliverable, not its title. Repairing a link does
   not supply missing approval; keep proposed subdecisions proposed.
5. Apply with `autowork tasks`, preserving statuses, ranks, evidence and focus. Run
   `validate --worktree`, then `autowork tasks why ID` for each affected task; a
   blocking dependency is a reconciled hold, not a clerical failure.

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
