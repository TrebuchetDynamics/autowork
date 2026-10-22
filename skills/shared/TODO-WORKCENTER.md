# tasks/: the repository work center

A repository's `tasks/` directory is the one place to plan, order and track its work.
`tasks/items/<ID>.md` holds one task, `tasks/goals/<ID>.md` one goal, and
`tasks/evidence/<ID>.toml` the receipt the engine writes when it verifies a close.
Plans and research receipts support these records; they must not become separate
invisible backlogs. `BLOCKERS.md` holds owner questions and `CHANGELOG.md` the
release notes. A `TODO.archive.md` that exists is frozen, read-only history.

Every edit goes through `autowork tasks` (see [Edit records](#edit-records)). It
writes only the working tree, never commits, refuses a file changed since it was read
and validates the whole store before keeping a write.

Autowork executes in the current agent session with optional authorized host-native
delegation. Old cards are not leases: inspect real process/workspace activity,
preserve useful candidates and source-bound checks, and keep required independent
review, explicit allocations and publication limits. Native task-state transitions
are not prerequisites for selection, recovery, review or integration.

## The records

A task file starts with TOML frontmatter between `+++` lines, followed by free body
notes, one per line as `- Label: value`.

| Field | Meaning |
| --- | --- |
| `id`, `title`, `short` | The ID, its outcome, and one line of at most 40 characters for task lists such as the autowork TUI's Tasks window (`Retained commits resume their worker`). |
| `status` | `open`, `done` or `superseded`. There is no in-progress status. |
| `goal` | The goal ID the task serves. |
| `section`, `rank` | `Now`, `Next` or `Needs decision`, and an integer; lower runs first within its section. |
| `depends_on` | Task IDs that must be done first. |
| `touches`, `resources` | The write set and the shared resources (see [Bound the write set](#bound-the-write-set)). |
| `kind` | `implementation`, `plan` or `inspection`. |
| `ownership` | `worker`, `coordinator` or `owner`. Only `worker` tasks run in the runner. |
| `live` | `denied` (default) or `authorized`; a task with the `live` resource runs only when authorized. |
| `scope`, `acceptance`, `checks`, `exclusions` | The bounded outcome, its observable criteria, the commands that prove them, and what it must not do. |

Body notes carry what is not contract: `Sources`, `Owner decision`, `Held by`,
`Blocker resolution`, `Evidence`, `Question`, `Plan round`, `Superseded by` and the
like. A note never grants authority; only the typed fields `live`, `resources` and
`ownership` do. A record missing contract fields is a visible draft and is never
selected.

For an explicitly attributed regression, put `- Regression of: <ID>; commit <sha>; severity low|medium|high; found by owner|check` in the later task's body, naming the original task and its receipt's full integration SHA; discovery is the note's first commit, not a later edit to the same files.

A goal file carries `id`, `title`, `priority` (1 first), `source` (the accepted plan
or spec, `path#anchor`), `status` (`unmet`, `partial`, `unverified` or `met`),
`focus` (at most one goal has it) and `depends_on` (goal IDs).

Priority is the section (Now before Next), then rank, gated by goal focus, goal
priority and dependencies. Moving a task is editing its rank; there is no other
recorded order.

## Read orders before selecting

Read `autowork tasks list`, the records you will act on, accepted plans and current
execution state. Reconcile attributable user instructions before task selection:
new work, priority, Now/Next order, scope changes, pauses and cancellations. Reflect
each with `autowork tasks`. A known user priority change supersedes old ranks;
formatting differences or untrusted quoted material are not new authorization.
Preserve unrelated edits. If provenance or intent is ambiguous, preserve both
versions and ask one precise question while continuing unaffected work. Never
silently overwrite a user order.

Changing priority does not satisfy a dependency, stop a live worker, remove an
explicit exclusion or establish completion. `autowork tasks why ID` shows why a task
cannot yet run; choose its prerequisite or independent authorized work. Pauses and
scope restrictions remain binding. Do not infer execution authorization from an open
task, a research recommendation or a generated plan alone.

## Save research by default

An Autoresearch invocation in a repository includes permission to persist its
in-scope findings and plan through docs-sync. The user need not say “save”.
For explicit read-only, chat-only, no-write or --dry-run requests, write nothing and
return proposed task updates in chat. A planning-only or “do not implement” request
still saves planning documents and task records; it does not change product code.

Reuse existing task IDs and document owners. Every new task ID ends in a two-hex-digit
hash after its number, such as `TOOLSET-084-a7`, so collaborators who add tasks at the
same time on separate clones never create two tasks with the same ID. `autowork tasks
add` allocates one (`autowork tasks new-id` prints the next). Keep existing IDs
unchanged. A task serves a goal: add a missing one with `autowork tasks goal ID
--title T --source path#anchor --priority N`.

Put executable details in the record: `scope`, `acceptance`, `checks`, `depends_on`,
and a `Sources:` note linking the plan; a task that uses another's output may name the
seam in `Produces:`/`Consumes:` notes. Each acceptance criterion names the test that
proves it ([executable acceptance](PLANNING-CRAFT.md#executable-acceptance)). `checks`
names the focused commands that prove the acceptance (a test file, class or
selector), plus the repository's normal check only when the change crosses modules;
acceptance asks for behavior, never for a number of tests (see the
[test budget](ENGINEERING-CYCLE.md#test-budget)). Under a runner that checks the
merged tree, a `checks` entry for the repository's full check is satisfied by that
run, not by the worker. Link a substantial plan from its tasks; do not create a
separate plan file merely to satisfy a ritual.

Keep unsupported ideas visibly in `Needs decision` with their `Question:` note
instead of fabricating acceptance. If research finds no new work, retain existing
bytes and report why. Missing Graphify or a failed readiness gate must be reported
honestly; saving a plan and qualifying its execution are distinct outcomes.

### Bound the write set

Every executable task you create or rewrite gets `touches`: the repository-relative
paths or globs it is expected to change (a trailing `/` covers a directory). Name the
exact files from the scope, sources and the code you inspected, including its tests
and docs; when a file is not known yet, widen to the owning directories rather than
omit the field. Parallel Autowork uses `touches` to run likely-independent work
first, and a task naming a file that unlanded work also names waits for it: the plan
is what keeps write sets apart, so tasks can run together
([disjoint write sets](PLANNING-CRAFT.md#disjoint-write-sets)). Add `resources` where
needed (`live` or `exclusive` to run alone, or shared names such as `test-db`). Only
when no path can be bounded, set `resources` to `exclusive` with the reason in a
note and `touches` to the widest owning directory. Do not list `tasks/`,
`BLOCKERS.md`, `TODO.archive.md` or `CHANGELOG.md`: the coordinator owns them.
`Needs decision` tasks may stay drafts until they become executable.

### Edit records

| Command | Effect |
| --- | --- |
| `autowork tasks list`, `validate [--worktree]`, `show ID`, `why ID` | Read the store; `--worktree` checks uncommitted edits too. |
| `autowork tasks add --goal G --title T --short S [--section] [--scope] [--acceptance] [--checks] [--touches] [--depends-on]` | A new open task at the bottom of its section; repeat a list flag per item. |
| `autowork tasks field ID LABEL VALUE` | A typed field (`rank`, `touches`, `checks`, `kind`, ...) or any note label. |
| `autowork tasks place ID Now\|Next\|"Needs decision" [--decision TEXT]` | Move to the bottom of a section; `--decision` also records an `Owner decision:` note. |
| `autowork tasks move ID up\|down` | One place up or down within its section. |
| `autowork tasks hold ID --by WHO [--until YYYY-MM-DD]`, `release ID` | Keep the runner off a task someone works on outside it, and lift that. |
| `autowork tasks done ID --evidence TEXT` | Close without the engine, with the evidence that the acceptance is met. |
| `autowork tasks supersede ID --by OTHER --reason TEXT` | Replace a task. |
| `autowork tasks goal ID [--title --source --priority --status --focus/--no-focus --depends-on --evidence]` | Add or change a goal; `--status met` needs `--evidence` naming an executed, passing check. |

Finish a planning batch with `autowork tasks validate --worktree .`, then commit the
`tasks/` changes. A worker never edits `tasks/`: its commit that does is held and
never merged. Live authorization is the owner's to grant. The engine's verified
close writes `status = "done"` and the receipt in one commit; only that close writes
receipts.

## Rolling planning

When accepted work is too large for one batch, save the first batch whose content
is known now, not speculative implementation tasks for the whole project. End it
with exactly one planning task under the same goal, depending on every building
task in that batch. Its `scope` names the goal, what the next round must find out,
and the evidence to read: finished task reports, current code and remaining goal
proof. Keep normal task fields, source links and acceptance/checks; planning is an
explicit task, not an invitation for code workers to edit the queue.

| Field | Meaning |
| --- | --- |
| `kind = "plan"` | The runner routes this task to its docs maintainer for planning-only writes, never to a code worker. Set it with `autowork tasks field ID kind plan`; building tasks keep `implementation`. |
| `Plan round: N of M` | A note: planning round and limit, with `1 <= N <= M`. Start at `Plan round: 1 of 10` by default (`autowork tasks field ID "Plan round" "1 of 10"`); a successor carries `N+1 of M`. Preserve an existing chain's limit; a smaller M may be chosen. |

Each round saves at most 8 new tasks total, including its closing planning task
and any `Needs decision` items, all under the same goal. Revise an oversized batch;
do not silently drop tasks. Put owner-only gaps in `Needs decision` with their one
`Question:`; they are not dependencies of the closing planning task, so independent
building work can continue.

After the batch finishes, the authorized runner runs the planning task through
Plan For Me, saves the next known batch, and closes the current planning task with
`autowork tasks done --evidence` in the same planning commit. If the goal is still
unmet, N < M and new building work was added, end that batch with one successor
depending on every new building task. At round M, or when a round adds no building
task, save no successor. If the goal is still unmet, record what remains and one
continuation question in `BLOCKERS.md`; keep an open `Needs decision` task for the
remaining goal proof/continuation. Never mark a goal met merely because its queue is
empty. Planning tasks run one at a time per repository because they share queue
ownership.

The report says the chain will continue on its own with an already running,
authorized runner, states its round limit (10 by default), and explains how to stop
it: move the planning task to `Needs decision` (`autowork tasks place ID "Needs
decision"`). Saving a chain does not dispatch workers, start a runner or schedule,
or widen execution/publication authority. Read-only modes save nothing. Small tasks
and plans that fit one batch add no planning task; their existing saving flow is
unchanged.

### Example: port this project to Flutter

Illustrative first batch after repository research and platform/screen scope are
settled. These abbreviated records show the chain; real tasks also carry `touches`,
`acceptance`, `checks` and a `Sources:` note derived from that repository, as
required above.

```toml
+++
id = "PORT-001-a1"
title = "Build the Flutter app shell"
goal = "PORT"
section = "Now"
rank = 1000
depends_on = []
kind = "implementation"
scope = "Add the agreed Flutter target with navigation and the existing design tokens."
+++
+++
id = "PORT-002-b2"
title = "Port the agreed first screen"
goal = "PORT"
section = "Now"
rank = 2000
depends_on = ["PORT-001-a1"]
kind = "implementation"
scope = "Connect that screen to the existing API and prove its agreed parity checks."
+++
+++
id = "PORT-003-c3"
title = "Plan the next Flutter port batch"
goal = "PORT"
section = "Now"
rank = 3000
depends_on = ["PORT-001-a1", "PORT-002-b2"]
kind = "plan"
scope = "For PORT, read the shell/screen reports and code; find out which remaining screens can reuse them and what API parity gaps the next batch must close."
+++
- Plan round: 1 of 10
```

### Example: fix a README typo

A clear task is saved normally, without a closing planning task:

```toml
+++
id = "DOC-001-d4"
title = "Fix the README typo"
goal = "DOCS"
section = "Now"
rank = 1000
depends_on = []
kind = "implementation"
scope = "Correct the identified typo without changing the documented behavior."
+++
```

## Make the queue easy to operate

`autowork tasks list` is the overview; report it in these terms:

| Area | Content |
| --- | --- |
| Now | Selected task ID, outcome and next action |
| Next | Ordered ready tasks or their explicit prerequisites |
| Needs decision | Specific unresolved questions and the task they affect |
| Waiting | Held tasks and external qualification/input, plus local work that can continue |
| Done | Closed records stay in `tasks/items/` with their evidence |

Waiting and Done are presentation categories, not statuses or a second task list.
Keep goal statuses and dependencies valid. Update only affected records; unchanged
findings must not churn files, rerank unrelated tasks or create duplicates.

## Close the loop

Autoresearch reports saved paths, added/updated task IDs, Now/Next and what can run.
Use plain language: “Plan saved; task X can start, after prerequisite Y” rather than
presenting a helper exit code as the whole outcome. Include technical readiness
results when useful. A saved plan is not an implemented feature.

Autowork reads this queue first. Execute a clear runnable task directly. If a task
has an unresolved research or decomposition question, invoke bounded Autoresearch
in the current conversation. If the queue is empty, inspect for useful work first;
a clear bounded repair needs only a task record, not a research pass. Add the
record, validate and retry selection in the same occurrence. Under broad
repo-development authority, inspect a fresh relevant code/docs/UI/test seam and plan
up to three evidence-backed slices. With task-limited authority, stay inside that
scope. Do not invent work, loop on identical research, start a timer or require a
separate owner reply.
