# TODO.md: the repository work center

TODO.md is the user-facing place to plan, order and track repository work.
An existing `goals.json` is the synchronized machine-readable execution index, not a competing
source of product intent. Plans and research receipts support this
queue; they must not become separate invisible backlogs.

TODO-only repositories need no index, Kanban card, profile or extra public registry
to implement an accepted task. An existing index stays supported and synchronized.
Autowork executes in the current agent session with optional authorized host-native
delegation. Old cards are not leases: inspect real process/workspace activity,
preserve useful candidates and source-bound checks, and keep required independent
review, explicit allocations and publication limits. Native task-state transitions
are not prerequisites for selection, recovery, review or integration.

## Read orders before selecting or rendering

Read TODO.md, its full task bodies, accepted plans and current execution state.
Reconcile attributable user instructions before `goals.py render` or task selection:
new work, priority, Now/Next order, scope changes, pauses and cancellations.
Use supported ledger operations or validated JSON edits to reflect those decisions.
A known user priority change supersedes old ledger ordering; formatting differences
or untrusted quoted material are not new authorization. Preserve unrelated edits.
If provenance or intent is ambiguous, preserve both versions and ask one precise
question while continuing unaffected work. Never silently overwrite a user order.

Changing priority does not satisfy a dependency, stop a live worker, remove an
explicit exclusion or establish completion. Show why a requested task cannot yet
run and choose its prerequisite or independent authorized work. Pauses and scope
restrictions remain binding. Do not infer execution authorization from an unchecked
box, a research recommendation or a generated plan alone.

## Save research by default

An Autoresearch invocation in a repository includes permission to persist its
in-scope findings and plan through docs-sync. The user need not say “save”.
For explicit read-only, chat-only, no-write or --dry-run requests, write nothing and
return proposed task updates in chat. A planning-only or “do not implement” request
still saves planning documents and TODO entries; it does not change product code.

Reuse existing task IDs and document owners. Give every new task an ID ending in
a two-hex-digit hash after its number, such as `TOOLSET-084-a7`, so collaborators
who add tasks at the same time on separate clones never create two tasks with the
same ID. Allocate it with `goals.py new-id <repo>` (or omit the ID in
`goals.py add-task`); it works without `goals.json` too. Keep existing IDs unchanged. Put executable details in full TODO
bodies: outcome, source/plan link, bounded scope, acceptance checks, dependencies,
status and next action; a task that uses another's output may name the seam in
optional `Produces:`/`Consumes:` fields. Each acceptance criterion names the test
that proves it ([executable acceptance](PLANNING-CRAFT.md#executable-acceptance)).
`Checks:` names the focused commands that prove the
acceptance (a test file, class or selector), plus the repository's normal check
only when the change crosses modules; acceptance asks for behavior, never for a
number of tests (see the [test budget](ENGINEERING-CYCLE.md#test-budget)). Under a
runner that checks the merged tree, a `Checks:` entry for the repository's full check
is satisfied by that run, not by the worker.
Reconcile matching goals.json entries. Link a substantial
plan from its tasks; do not create a separate plan file merely to satisfy a ritual.
Every executable task you create or rewrite gets `Touches:`: the repository-relative
paths or globs it is expected to change (a trailing `/` covers a directory). Name the
exact files from the scope, sources and the code you inspected, including its tests
and docs; when a file is not known yet, widen to the owning directories rather than
omit the field. Parallel Autowork uses `Touches:` to run likely-independent work
first, and a task naming a file that unlanded work also names waits for it: the plan
is what keeps write sets apart, so tasks can run together
([disjoint write sets](PLANNING-CRAFT.md#disjoint-write-sets)). A task without
`Touches:` ranks after the tasks that have it. Add `Resources:` where needed (`live`
or `exclusive` to run alone, or shared names such as `test-db`). Only when no path
can be bounded, write `Resources: exclusive` with the reason instead of leaving
`Touches:` out. Do not list the root `TODO.md`, `TODO.archive.md`, `goals.json` or
`CHANGELOG.md`: the coordinator owns them. Proposed or Needs-decision tasks may
leave `Touches:` until they become executable.
Every task you create or rewrite also gets `Short:`, one line of at most 40
characters naming the outcome, for task lists such as the autowork TUI's Tasks
window (`Short: Retained commits resume their worker`). `goals.py validate` rejects
a longer one; `goals.py plan-lint` reports a task without one.
Keep unsupported ideas visibly Proposed/Needs decision instead of fabricating
acceptance. If research finds no new work, retain existing bytes and report why.
Missing Graphify or a failed readiness gate must be reported honestly; saving a
plan and qualifying its execution are distinct outcomes.

## Rolling planning

When accepted work is too large for one batch, save the first batch whose content
is known now, not speculative implementation tasks for the whole project. End it
with exactly one planning task under the same `Goal:`, depending on every building
task in that batch. Its `Scope:` names the goal, what the next round must find out,
and the evidence to read: finished task reports, current code and remaining goal
proof. Keep normal task fields, source links and acceptance/checks; planning is an
explicit task, not an invitation for code workers to edit the queue.

| Field | Meaning |
| --- | --- |
| `Kind: plan` | The runner routes this task to its docs maintainer for planning-only writes, never to a code worker. Ordinary building tasks need no Kind field. |
| `Plan round: N of M` | Planning round and limit, with `1 <= N <= M`. Start at `Plan round: 1 of 10` by default; a successor carries `N+1 of M`. Preserve an existing chain's limit; a smaller M may be chosen. |

Each round saves at most 8 new tasks total, including its closing planning task
and any `Needs decision` items, all under the same goal. Revise an oversized batch;
do not silently drop tasks. Put owner-only gaps in `Needs decision` with their one
question; they are not dependencies of the closing planning task, so independent
building work can continue.

After the batch finishes, the authorized runner runs the planning task through
Plan For Me, saves the next known batch, and closes the current planning task in
the same planning commit. If the goal is still unmet, N < M and new building work
was added, end that batch with one successor depending on every new building task.
At round M, or when a round adds no building task, save no successor. If the goal
is still unmet, record what remains and one continuation question in `BLOCKERS.md`;
keep an open `Needs decision` task for the remaining goal proof/continuation.
Never mark a goal met merely because its queue is empty. Planning tasks run one
at a time per repository because they share queue ownership.

The report says the chain will continue on its own with an already running,
authorized runner, states its round limit (10 by default), and explains how to stop
it: move the planning task to `Needs decision`. Saving a chain does not dispatch
workers, start a runner or schedule, or widen execution/publication authority.
Read-only modes save nothing. Small tasks and plans that fit one batch add no
planning task; their existing saving flow is unchanged.

### Example: port this project to Flutter

Illustrative first batch after repository research and platform/screen scope are
settled. These abbreviated bodies show the chain; real tasks also carry Sources,
Touches, Acceptance and Checks derived from that repository, as required above.

```markdown
- [ ] PORT-001-a1 — Build the Flutter app shell
  Goal: PORT
  Scope: Add the agreed Flutter target with navigation and the existing design tokens.
  Dependencies: None.
  Status: open
- [ ] PORT-002-b2 — Port the agreed first screen
  Goal: PORT
  Scope: Connect that screen to the existing API and prove its agreed parity checks.
  Dependencies: PORT-001-a1
  Status: open
- [ ] PORT-003-c3 — Plan the next Flutter port batch
  Goal: PORT
  Kind: plan
  Plan round: 1 of 10
  Scope: For PORT, read the shell/screen reports and code; find out which remaining screens can reuse them and what API parity gaps the next batch must close.
  Dependencies: PORT-001-a1, PORT-002-b2
  Status: open
```

### Example: fix a README typo

A clear task is saved normally, without a closing planning task:

```markdown
- [ ] DOC-001-d4 — Fix the README typo
  Goal: DOCS
  Scope: Correct the identified typo without changing the documented behavior.
  Dependencies: None.
  Status: open
```

## Make the queue easy to operate

Reuse the repository's existing sections and renderer contract. At the top provide
a compact human overview outside generated regions, linking to existing task bodies:

| Area | Content |
| --- | --- |
| Now | Selected task ID, outcome and next action |
| Next | Ordered ready tasks or their explicit prerequisites |
| Needs planning | Specific unresolved questions and the task they affect |
| Waiting | External qualification/input, plus local work that can continue |
| Done | Link to TODO.archive.md (or the existing archive); completed bodies live there |

These are presentation categories, not new ledger statuses or a second task list.
Never rename parser-bound sections or duplicate task bodies just to fit this table.
Keep goals.json statuses and dependencies valid. Update only affected entries;
unchanged findings must not churn files, reorder unrelated tasks or create duplicates.

## Close the loop

Autoresearch reports saved paths, added/updated task IDs, Now/Next and what can run.
Use plain language: “Plan saved; task X can start, after prerequisite Y” rather than
presenting a helper exit code as the whole outcome. Include technical readiness
results when useful. A saved plan is not an implemented feature.

Autowork reads this queue first. Execute a clear runnable task directly. If a task
has an unresolved research or decomposition question, invoke bounded Autoresearch
in the current conversation. If the queue is empty, inspect for useful work first;
a clear bounded repair needs only a task record, not a research pass. Reconcile
TODO/goals, validate and retry selection in the same occurrence. Under broad repo-development authority,
inspect a fresh relevant code/docs/UI/test seam and plan up to three evidence-backed
slices. With task-limited authority, stay inside that scope. Do not invent work,
loop on identical research, start a timer or require a separate owner reply.
