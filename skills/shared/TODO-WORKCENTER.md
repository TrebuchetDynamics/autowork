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
status and next action. `Checks:` names the focused commands that prove the
acceptance (a test file, class or selector), plus the repository's normal check
only when the change crosses modules; acceptance asks for behavior, never for a
number of tests (see the [test budget](ENGINEERING-CYCLE.md#test-budget)).
Reconcile matching goals.json entries. Link a substantial
plan from its tasks; do not create a separate plan file merely to satisfy a ritual.
Every executable task you create or rewrite gets `Touches:`: the repository-relative
paths or globs it may change (a trailing `/` covers a directory). Derive it from the
scope, sources and the code you inspected, including its tests and docs. When unsure,
widen to the owning directories rather than omit the field: a worker that changes a
file outside `Touches:` is held and retried alone, so a slightly broad list costs less
than a missing one. Add `Resources:` where needed (`live` or `exclusive` to run alone,
or shared names such as `test-db`). Only when no path can be bounded, write
`Resources: exclusive` with the reason instead of leaving `Touches:` out. Parallel
Autowork runs a task beside others only when these prove it independent; a task
without `Touches:` runs alone and holds back every lower-priority task while it is
first. Do not list the root `TODO.md`, `TODO.archive.md`, `goals.json` or
`CHANGELOG.md`: the coordinator owns them. Proposed or Needs-decision tasks may
leave `Touches:` until they become executable.
Keep unsupported ideas visibly Proposed/Needs decision instead of fabricating
acceptance. If research finds no new work, retain existing bytes and report why.
Missing Graphify or a failed readiness gate must be reported honestly; saving a
plan and qualifying its execution are distinct outcomes.

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
