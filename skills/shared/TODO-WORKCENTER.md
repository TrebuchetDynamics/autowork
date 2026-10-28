# tasks/: the repository work center

A repository's `tasks/` directory is the one place to plan, order and track its work.
`tasks/items/<ID>.md` holds one task, `tasks/goals/<ID>.md` one goal, and
`tasks/evidence/<ID>.toml` the receipt the engine writes when it verifies a close.
Plans and research receipts support these records; they must not become separate
invisible backlogs. `BLOCKERS.md` holds owner questions and `CHANGELOG.md` the
release notes. A `TODO.archive.md` that exists is frozen, read-only history.

Every edit goes through `autowork tasks` (see [Edit records](#edit-records)). It
writes only the working tree, never commits, and validates the whole store before
keeping a write. Its operation-local conflict check protects the CLI's own read;
carry `record_revision` to `--expect REV` to protect an earlier planning read across
calls (see [Edit records](#edit-records)).

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
| `depends_on`, `verified_depends_on` | Task IDs that must be done first; the verified subset additionally requires verification or an explicit owner exception. |
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
explicit exclusion or establish completion. `autowork tasks why ID` explains
committed-store selection eligibility and position, not admission, capacity,
current ownership or dispatch; choose its prerequisite or independent authorized work. Pauses and
scope restrictions remain binding. Do not infer execution authorization from an open
task, a research recommendation or a generated plan alone.

## Save research by default

An Autoresearch invocation in a repository includes permission to persist its
in-scope findings and plan through docs-sync. The user need not say “save”.
For explicit read-only, chat-only, no-write or --dry-run requests, write nothing and
return proposed task updates in chat. A planning-only or “do not implement” request
still saves planning documents and task records; it does not change product code.

Reuse existing task IDs and document owners. New allocation uses an eight-hex-digit
suffix after the number, such as `TOOLSET-084-a7b8c9d0`, reducing collision risk
across clones, not guaranteeing uniqueness. `autowork tasks add` allocates one
(`autowork tasks new-id` prints a candidate, not a reservation). Keep existing IDs unchanged,
including legacy IDs with shorter suffixes or none; never normalize them. A discovery pass that finds the existing backlog already covers the
evidenced gaps reports that and changes nothing; a short queue is not permission to
invent work. A task serves a goal: add a missing one with `autowork tasks goal ID
--title T --source path#anchor --priority N`.

Put executable details in the record: `scope`, `acceptance`, `checks`, `depends_on`,
and a `Sources:` note linking the plan; a task that uses another's output may name the
seam in `Produces:`/`Consumes:` notes. Each acceptance criterion names the test that
proves it ([executable acceptance](PLANNING-CRAFT.md#executable-acceptance)). `checks`
names the focused commands that prove the acceptance (a test file, class or
selector); preserve all task-required commands and mandatory checks. Acceptance
asks for behavior, never for a number of tests (see the
[test budget](ENGINEERING-CYCLE.md#test-budget)). Workers run focused/task checks.
For this repository's standard check runner, landing runs affected checks on the
merged candidate; main separately runs the full check after landing. An affected
pass is not a full-main pass. A task's full-check entry is satisfied by the runner's
full merged-tree gate, not repeated by a worker; custom required checks remain binding. Link a substantial plan from its tasks; do not create a
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
omit the field. Parallel Autowork uses `touches` to rank likely-independent work
first. A shared literal hot production file (named by at least three unfinished
contracts) gates overlapping work; test modules are exempt from that hot-file gate.
Overlapping cold files, directories and globs are scheduling hints, not blanket
serialization. Report possible merge conflicts honestly; do not invent product
`depends_on` edges for file overlap. Keep real prerequisites and
[bounded write sets](PLANNING-CRAFT.md#disjoint-write-sets). Add `resources` where
needed (`live` or `exclusive` to run alone, or shared names such as `test-db`);
resource and protected manifest/lock/schema/migration/CI gates still apply. Only
when no path can be bounded, set `resources` to `exclusive` with the reason in a
note and `touches` to the widest owning directory. Do not list `tasks/`,
`BLOCKERS.md`, `TODO.archive.md` or `CHANGELOG.md`: the coordinator owns them.
`Needs decision` tasks may stay drafts until they become executable.

### Task holds require an explicit user request

Leave accepted tasks open in `Now` or `Next`, available to the authorized runner.
A skill may add or renew `Held by:` or run `autowork tasks hold` only when the user
explicitly asks to hold or pause the affected task. Record that request and its
scope; a skill name such as `PLAN-FOR-ME` is not authorization to hold work.
This rule applies to planning, Docs Sync, manual execution and delivery alike.

“Plan only”, “no code this pass” and “do not implement in this session” limit the
current session. They do not pause an existing authorized runner or require a later
implementation order in the saved task's exclusions. Do not substitute a goal pause,
`Needs decision`, a fake dependency or an incomplete contract to reserve accepted
work. Keep genuine unresolved decisions, prerequisites and approval limits explicit;
open does not mean dependency-ready, admitted or authorized for live operations.

Use supported execution leases, workspace locks and current worker checks to prevent
duplicate execution, not an unrequested task hold. Preserve existing user pauses,
live claims, runtime failure holds and safety gates; this rule does not clear them.
If this pass added a planning-only hold without a user request, remove only that
attributable hold before handoff with `autowork tasks release`, after verifying no
live owner or explicit pause relies on it. Preserve other notes and exclusions, and
use `--expect REV` after an earlier read. Unknown ownership needs investigation,
not blanket release. Report remaining real blockers separately from skill-created
reservations.

### Edit records

| Command | Effect |
| --- | --- |
| `autowork tasks list`, `validate`, `show ID`, `why ID` | Read the committed store; `list`, `validate` and `show` also accept `--worktree` for uncommitted edits. `why` is selection evidence only. |
| `autowork tasks add --goal G --title T --short S [--section] [--scope] [--acceptance] [--checks] [--touches] [--depends-on]` | A new open task at the bottom of its section; repeat a list flag per item. |
| `autowork tasks field ID LABEL VALUE` | A typed field (`rank`, `touches`, `checks`, `kind`, ...) or any note label. |
| `autowork tasks place ID Now\|Next\|"Needs decision" [--decision TEXT]` | Move to the bottom of a section; `--decision` also records an `Owner decision:` note. |
| `autowork tasks move ID up\|down` | One place up or down within its section. |
| `autowork tasks hold ID --by WHO [--until YYYY-MM-DD]`, `release ID` | Apply an explicitly user-requested task pause, or release a reconciled hold under the policy above. |
| `autowork tasks done ID --by WHO --reason TEXT [--evidence REF]` | Manual close of any task kind; optional evidence is a reference, not verified acceptance. |
| `autowork tasks supersede ID --by OTHER --reason TEXT` | Replace a task. |
| `autowork tasks goal ID [--title --source --priority --status --focus/--no-focus --depends-on --evidence]` | Add or change a goal; `--status met` needs evidence and all non-superseded owned tasks done and qualified. |

**Pass prose as literal JSON.** For quotes, backticks, `$` (including `$(...)`
and `$VAR`) or newlines, write a UTF-8 JSON object with a file-writing tool; from
the consumer repository run `autowork tasks add --json task.json`,
`autowork tasks field ID --json field.json`, or
`autowork tasks goal ID --json goal.json`. Stdin uses `--json - < task.json`.
Never interpolate prose into shell arguments, `echo` or an unquoted heredoc.
Keys mirror options with underscores, list options take arrays, and field uses
`{"label": "scope", "value": "text"}` (arrays for list fields). Add's `notes`
and field label `notes` preserve the entire raw multiline Markdown body; read it
first and retain Sources, holds and other notes. Do not mix JSON with value flags
or label/value arguments. See [literal input](../../pi-autowork/task-store.md#literal-prose-input---json)
for all keys/types. Validation, authority checks and `--expect REV` still apply.

**Protect an earlier read across calls.** Read the current working-tree record,
retain its `record_revision`, decide the attributable delta, then supply that digest
as `REV` (not HEAD, `rev` or `contract_hash`):

```sh
autowork tasks show ID --worktree
autowork tasks field ID --json field.json --expect REV
```

Write `field.json` with a file-writing tool as described above. JSON protects literal
prose, not freshness. On refusal, reread the latest record, compare changes and
reapply only the still-authorized delta using its new `record_revision`. Preserve
other edits, notes, ranks, holds and transitions; withdraw obsolete changes. Never
replay a stale full snapshot or blind retry with a freshly substituted digest. The
operation-local check alone cannot protect decisions from an earlier call.

Finish a planning batch with `autowork tasks validate --worktree .`, then commit the
`tasks/` changes. A worker never edits `tasks/`: its commit that does is held and
never merged. Live authorization is the owner's to grant.

### Manual is not verified

A manual close records `closure = "manual"`, actor, timestamp, reason and optional
reference. It writes no receipt, check result or verification claim. Ordinary
`depends_on` accepts a manual done task; `verified_depends_on` additionally requires
verification or an explicit owner exception. A manually closed owned task cannot
qualify `goal --status met` without an owner-recorded `owner_waiver` (exact criterion,
reason and risk) or `owner_qualification` (qualification and evidence). Never invent
these attestations from a planner decision or passing report, or manually close
implementation acceptance just to make the queue green. Honor explicit owner stops
without relabelling unmet acceptance as verified. Only the engine's verified close
writes `closure = "coordinator_verified"` and its receipt with `status = "done"`
in one commit; planning never fabricates or edits that receipt.

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
`autowork tasks done ID --by WHO --reason TEXT [--evidence REF]` in the same planning
commit. This closes the planning activity manually, not the implementation's
acceptance or remaining goal proof. If the goal is still
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
