# Pi Autowork coordinator redesign

Status: accepted, 2026-10-16; owner decisions recorded at the end.

## Why

On 2026-10-15/16 four `pi-autowork@` runners sat idle for seven hours with
"active (running)" services. Each stall was fixed as a special case in Bash or the
engine (backfill, readopt, close retries, exhausted holds, prose dependencies). The
failures share causes that patches do not remove:

- **Lifecycle authority is split.** The engine owns slot states, but the runner
  keeps its own lifecycle (`SEEN`, `FAILURES`, `DRAINING`, close retries, Touches
  edits, session merges) in about 1,000 lines of Bash. Neither side can state which
  transitions are possible from a stuck state.
- **Worker outcomes are guessed from process state.** A worker that stopped on
  purpose and wrote `report.json` with blockers (sierra TASK-022) was classified "dead
  worker with uncommitted changes" and resumed, burning its last attempt. A worker
  whose report listed pending device checks (flutter TASK-013) was held as a
  failure twice although its offline slice passed.
- **No state means "waiting for a person".** Holds, contract changes and
  unbounded scope all became generic blocks, and nothing surfaced them.
- **Destructive Git recovery runs on shared checkouts.** The reviewer and Touches
  passes may `reset --hard`/`clean` the session checkout; closure stages
  `git add -u -- '*.md'`.
- **Silence.** A stalled runner logs one line and polls forever.

## Invariants

1. **One lifecycle authority.** Every task state transition is made by the engine
   (`owner_cycle.py`) and journaled. The runner never infers or stores task state;
   it reads `--parallel-status --json` and calls engine operations.
2. **Every state has an exit.** Each non-terminal state names the event that leaves
   it: a worker, the coordinator, time, or a person. A state whose exit is "a
   person" is `deferred` and blocks only its dependents and declared overlap.
3. **Worker outcomes come from the report, not the process.** Exit with a valid
   report decides the transition; process death without a report is the only
   "crash". A runner stop or restart never consumes an attempt.
4. **Offline completion is separate from live qualification.** A report has
   `blockers` (work not done) and `pending_live` (device, production or human
   checks for a separate task). Only blockers hold a task.
5. **Nothing unauthorized reaches main.** Scope, coordinator-file ownership and
   validation are checked on the exact merge candidate; deferral keeps the commit
   and receipt and never counts as completion.
6. **Exactly-once closure.** Integration, TODO closure, archive and the closure
   commit form one recoverable transaction keyed by the integration commit; a crash
   at any point resumes or completes it, never repeats it.
7. **Git operations are scoped.** Destructive cleanup (`reset --hard`, `clean`,
   `worktree remove`) runs only on a worktree the journal shows Autowork created,
   that is not the session or canonical checkout, with no live writer. No `stash`.
   Commits stage an explicit file list.
8. **Progress whenever independent work exists.** If no worker runs while runnable
   work exists, that is a bug surfaced as `STALLED` with the root blockers, not a
   quiet poll.
9. **Ambiguity blocks.** A dependency that names no known task is an outside
   condition and blocks; it is never read as "none".

## Task states (engine)

| State | Meaning | Leaves by |
| --- | --- | --- |
| `queued` | runnable contract, no slot | dispatch |
| `running` | live worker | worker report or crash |
| `reported` | commit + report, awaiting integration | integration |
| `verifying` | candidate merged in isolation, checks running | pass → `integrated`, fail → `retry`/`deferred` |
| `integrated` | landed on the session branch | closure transaction |
| `closed` | TODO closed, archived, committed | terminal |
| `retry` | failed, an attempt left | fresh attempt when its scope is free |
| `deferred` | needs a person or an outside condition; keeps commit, report, worktree | person, contract change, or `set-aside` |
| `blocked` | dependency or overlap with running/claimed work | the blocker clears |

`deferred` carries a machine-readable `cause`: `scope` (needs more paths),
`contract_changed`, `blocker` (report text), `validation`, `conflict`,
`attempts_exhausted`. Each cause has one automatic action where safe:

- `scope` with runner-inferred Touches: widen Touches with the paths the report
  names, record them, and resume the same worktree once. Authored Touches defer.
- `contract_changed` after integration: set aside (merge stays), re-queue.
- `conflict` with another task: revalidate against the new baseline after that
  task closes, once.
- others: wait for a person; shown in `--status` and the stall report.

## Components

```text
pi-autowork.sh            thin CLI/systemd entry: options, lock, service install, signals
  └── pi_autowork/ (Python, tested)
       coordinator.py     loop: reconcile → dispatch → integrate → close → report health
       pi_adapter.py      Pi invocation, model fallback, sessions, cost records
       worktrees.py       provisioning (linked ignored paths), scoped cleanup
       health.py          status.json, STALLED detection, needs-attention list
  └── skills/autowork/scripts (engine; single lifecycle authority, extended states)
```

The engine keeps its contracts; the redesign adds the `deferred` cause model,
report-based worker outcomes, `pending_live`, and the closure transaction. The
runner's Bash shrinks to the entry point.

## Required scenarios (controlled subprocess workers, failure injection)

1. Two tasks overlap: one integrates, the other defers and later integrates after
   revalidation.
2. Crash between integration and closure: restart closes exactly once.
3. Worker changes files outside scope: nothing reaches main; inferred scope widens
   once, authored scope defers.
4. Dependency names an outside condition: blocked, never runnable.
5. A person reorders TODO.md while workers run: running work is kept; new dispatch
   follows the reconciled order.
6. Reviewer writes unexpectedly: candidate rejected; unrelated changes kept.
7. Independent tasks finish out of order: no duplicate commits, no lost changes.
8. Worker stops with blockers in its report: deferred with that cause, no resume.
9. Report with only `pending_live`: integrates; a live follow-up stays open.
10. Runner restart mid-task: worker adopted or resumed without using an attempt.
11. Exhausted hold: blocks only dependents and overlap; the rest progresses.
12. No worker running while runnable work exists: `STALLED` is reported once with
    root causes.

## Owner decisions (2026-10-16)

1. **Self-update at a safe checkpoint only:** no live, reported or integrating
   slot, and the new release must read the current state schema version; otherwise
   keep running the current release and say why.
2. **Adopt verifiably idle claims:** an `in_progress` claim whose claiming session
   is gone and whose branch or worktree has had no writes for a set time may be
   taken over, keeping any existing work (AGENTS.md "adopt an idle candidate").
3. **Linked ignored dependencies:** the service environment file (toolset state,
   not the repository) may list gitignored paths to link read-only from the main
   checkout into each task worktree.
4. Local main's 56 unpushed commits were merged with origin and pushed (ee82575).

## Phases

1. Done (59a44cf). Worker outcomes from reports: a report with blockers defers with that cause
   instead of resuming; `pending_live` never holds; the worker prompt says which.
2. Done (50768e2). Git safety: reviewer and Touches passes in disposable worktrees; closure commits
   only the files closure changed.
3. Done. Health: `status.json`, one `STALLED` report with root blockers, `--status`
   and `--fleet`; the first module of the `pi-autowork/` component
   ([layout](pi-autowork-component-layout.md)).
4. Done. Owner decisions 1-3: safe-checkpoint self-update (fleet idle, state
   schema check before install), adoption of verifiably idle claims, linked ignored
   dependencies; plus guarded priority-drift recording and no service exit on engine
   errors.
5. Done offline. Typed hold causes with re-verification after widening inferred
   Touches; the whole runner (CLI, coordinator loop, worker modes, service, Pi job
   runtime, Touches inference) moved into the component, with `pi-autowork.sh` as a
   thin entry point. Deferred causes and their automatic actions; extract the coordinator into the
   `pi-autowork/` component per the [layout proposal](pi-autowork-component-layout.md)
   and reduce `pi-autowork.sh` to a compatibility entry point.
