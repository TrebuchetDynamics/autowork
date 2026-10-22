# TaskStore (schema 1)

`engine/task_store.py` is the one task store of the accepted
[Task Store v2 design](../docs/project.md#task-store-v2-2026-10-20): selection, dispatch,
integration, closure, the runner, the fleet view and `autowork tasks` all read `tasks/`
through it, at a pinned commit. Nothing reads TODO.md or goals.json; only
`autowork migrate` keeps a private reader of them, to convert a repository once.

## Snapshot API

- `TaskStore.at(repo, rev)` resolves a Git revision to a commit SHA once, then
  reads `tasks/items/<ID>.md` and `tasks/goals/<ID>.md` with `git ls-tree` and one
  `git cat-file --batch` call at that SHA, whatever the number of files. Explicit
  coordinator-verified closures read receipts and referenced Git objects in two additional
  batches, and check integration ancestry at the same pinned revision. The returned `rev` is that pinned SHA, not the input
  branch name. Working-tree edits never become records. Git replacement refs
  are disabled so they cannot substitute content for the pinned object IDs.
  Internal validation can pass an explicit `env` selecting a temporary object
  database; inherited `GIT_*` settings remain ignored. All records, receipts and
  ancestry checks are read eagerly before that database is removed.
- `store.tasks` and `store.goals` are immutable mappings keyed by ID, containing
  frozen `TaskRecord` and `GoalRecord` values. Collections inside records are
  tuples; `body` retains the Markdown after the closing delimiter.
- `TaskStore.pending(repo)` returns a sorted tuple of uncommitted task/goal paths
  (staged, unstaged, deleted and untracked). Renames include both paths, even
  when one endpoint is outside the store; unrelated changes are omitted. Git's
  optional index refresh is disabled, so reads do not rewrite the index. Pending
  content is not parsed, and completion evidence is not included.
- `StoreError` refuses the entire snapshot, with repository-relative `path:line`
  diagnostics. There is no partial success. Malformed TOML/UTF-8, unknown fields,
  wrong types, duplicate IDs (including across tasks and goals), unknown goals,
  filename/ID mismatches, non-regular or misplaced files, and symlinked store
  directories are refused.
  A commit without a `tasks/` tree is refused (`no task store`): an unconverted
  repository never reads as an empty queue. A `tasks/` tree with no records has
  empty mappings. More than one goal with `focus = true` is refused.

## File schema

Every file starts with a `+++` line, TOML frontmatter, and a closing `+++` line.
`schema = 1` is mandatory. Missing or unknown versions are refused; no version is
inferred or upgraded. IDs use letters, digits, underscores and hyphens, beginning
with a letter or digit, and match the filename without `.md`.

Task fields:

| Fields | TOML type / values |
| --- | --- |
| `id`, `title`, `short`, `goal`, `scope` | Nonempty strings; scope is contract prose, not the free-note body |
| `status` | `"open"`, `"done"`, `"superseded"` |
| `section` | `"Now"`, `"Next"`, `"Needs decision"` |
| `rank` | Integer (not a boolean); lower ranks sort first in future consumers |
| `depends_on`, `touches`, `resources`, `acceptance`, `checks`, `exclusions` | Arrays of nonempty strings |
| `kind` | `"implementation"`, `"plan"`, `"inspection"`, `"unknown"` |
| `ownership` | `"worker"`, `"coordinator"`, `"owner"`, `"unknown"` |
| `live` | `"denied"`, `"authorized"`; defaults to denied |
| `verified_depends_on` | Optional array of prerequisite IDs; must be a subset of `depends_on` |
| `closure` | Optional `"manual"` or `"coordinator_verified"`, written by the closing path |
| `closure_actor`, `closure_timestamp`, `closure_reason` | Nonempty strings required for manual closure; UTC ISO timestamp |
| `closure_evidence` | Optional evidence reference for manual closure; receipt path for verified closure |
| `owner_waiver`, `owner_qualification` | Optional nonempty owner records explaining the exact waived criterion or qualification and its authority/evidence |

The closure fields and `verified_depends_on` are optional. All other fields except
`live` are needed for a complete task contract. Missing fields
other than `schema` and `id` produce a visible draft rather than a store error.
Empty acceptance/checks/touches also produce draft reasons in `missing_fields`.
Explicit empty arrays are valid for dependencies, resources and exclusions.
Resource strings are tokens such as `live`, `exclusive` or `test-db`, not prose.

Goal fields are all mandatory: `id`, `title`, `source` are nonempty strings;
`priority` is an integer; `status` is `"unmet"`, `"partial"`, `"unverified"` or
`"met"`; `focus` is a boolean. Optional `depends_on` lists goal IDs that must be met first
(an unknown ID is refused). The reader preserves declared goal status; it does
not infer goal completion or qualify evidence.

A later task can explicitly attribute a regression with the body note `- Regression of: <ID>; commit <sha>; severity low|medium|high; found by owner|check`, where `<sha>` is the original task receipt's full integration SHA and discovery is the note's first commit, never file overlap.

## Authority and runnable boundary

`Kind`, `Ownership` and `LiveAuthorization` are enums. Missing kind/ownership map
to `UNKNOWN`, missing resources expose no claims, and missing live authorization
is `DENIED`. Unrecognized enum values or malformed authority fields invalidate
the store rather than granting permission.

`task.draft` reports incomplete contracts. `task.runnable` means the contract is
complete, open, in Now/Next, has a known kind and worker ownership, and has explicit
live authorization if it claims the `live` resource. Coordinator/owner/unknown
ownership never grants worker authority. This property does **not** evaluate
prerequisite completion, dependency cycles, resource availability, worker leases,
or the caller's rights. Consumers must gate those separately. In particular a
check string is not permission to execute that command with coordinator rights.

## Fingerprints

`record_revision` is the SHA-256 hex digest of the exact file bytes, including
frontmatter formatting and free notes. Task `contract_hash` is SHA-256 of canonical
UTF-8 JSON (sorted keys, compact separators) over scope, acceptance, checks,
depends_on, touches, resources, kind, ownership, live and exclusions,
plus `section_group`: Now/Next becomes `"runnable"`; Needs decision stays distinct.
Missing values hash as null, preserving missing versus explicit empty authority,
except `kind`, `ownership` and `live`, which hash as their defaults (`unknown`,
`unknown`, `denied`): writing a default out grants nothing new and changes no contract.
Nonempty `verified_depends_on` is also hashed; absent and empty both impose no extra
evidence gate. Closure metadata and owner waiver/qualification records are not contract
fields. Reopening clears them, and a new manual close clears prior owner exceptions.
Array order is preserved. Exclusions are included because changing a prohibition
changes the work contract.

Rank, title, short, status, Now-versus-Next, goal assignment, and free Markdown notes are
excluded from the task contract hash. Status is a transition, not contract: closing a task
(open to done) keeps the hash its verification pinned, and consumers check done and
superseded explicitly. Goal assignment and dependencies still
require consumer-side scheduling checks. Goal contract hashes cover priority,
source, status and focus, excluding title and notes.

## Selection

`task_select.order(store)` lists every selectable task: open, not a draft, in Now or
Next, dependencies done, goal not met and goal dependencies met. It sorts by the focus
goal, section, rank, goal priority, goal status (`unverified`, `partial`, `unmet`) and ID,
`next(store)` is the first that is not a planning task.
`why(store, id)` returns stable reason codes: the blocking rule (`DONE`, `SUPERSEDED`,
`NEEDS_DECISION`, `DRAFT`, `NO_GOAL`, `GOAL_MET`, `GOAL_DEPENDENCY_UNMET`,
`DEPENDENCY_UNFINISHED`, `UNKNOWN_TASK`) or `POSITION` plus the sort-key rule
(`AFTER_FOCUS`, `AFTER_SECTION`, `AFTER_RANK`, …) that put the task ahead of it there.
Authority is not a selection rule; admission applies it afterwards.

A dependency in `verified_depends_on` additionally needs a done prerequisite with an
explicit coordinator-verified closure and a matching passing receipt, or a recorded
`owner_waiver`/`owner_qualification`. Otherwise `why` returns `DEPENDENCY_UNVERIFIED`.
This applies to named dispatch, sequential execution and task-wait retries too. Ordinary
`depends_on` still accepts any done prerequisite. A superseded prerequisite satisfies neither.

**Holding a task.** Git status is never a lease, so there is no `in_progress`. A person or
an interactive session keeps the runner off an open task with
`autowork tasks hold ID --by WHO [--until YYYY-MM-DD]`, which writes the record's
`- Held by: WHO; until DATE` note and nothing else (the contract hash is unchanged);
`autowork tasks release ID` removes it. A held task is never selected (`HELD`), never
dispatched even when named, and still blocks its dependents and tasks that share its
resources or serial work; the hold ends when the note is removed or its date passes.

## Writing and `autowork tasks`

`tomllib` only reads, so `task_store` carries its own writer. `render` writes a new record
in canonical key order and ends it with exactly one newline, including records without
notes; `edit` changes only the header lines it names and keeps every other byte;
`set_note` sets one `- Label: value` line in the body. Each refuses what it
cannot reproduce (an existing header value spread over several lines, a trailing comment,
unsupported control characters, unknown keys) instead of dropping it, and checks that the
result reads back to exactly the intended values. Newlines, carriage returns and tabs in
header strings are escaped on one physical TOML line and read back unchanged.

`autowork tasks` reads at HEAD (`list`, `show`, `why`, `validate`; `--worktree` on `list`,
`show` and `validate` reads uncommitted edits through a throwaway commit that leaves the
repository's objects, index and refs alone) and edits the working tree (`add`, `field`,
`place`, `move`, `hold`, `release`, `done`, `supersede`, `goal`; `new-id` allocates an ID);
it never commits. A write
holds the repository's task lock (`<git dir>/autowork-tasks.lock`), so two writers never
interleave; refuses a file that changed since it was read, or since the `record_revision`
given as `--expect REV`; and is undone when the resulting store does not validate.
The Python command entry points and working-tree reads share that lock too. A `move`
that rebalances neighbours, or a `goal --focus` that clears another goal, compares all
inputs before writing and validates the resulting set once. Rendering or validation
failure, an I/O error or a Python interruption undoes the whole set.

Working-tree validation (including task writes and `prepare` reads of pending edits)
uses a temporary index and object database. The repository's existing objects are
read-only alternates, including in linked worktrees. New blobs, trees and proof commits
are removed on success or exception, not left loose and unreachable in the repository.
Returned records remain usable, but a working-tree result's `rev` is an ephemeral proof
ID, not a durable revision to read again. This does not remove existing objects or
change GC configuration; a process killed without cleanup may leave temporary files.

Before replacing any record, the writer flushes an undo journal at
`<git dir>/autowork-tasks.transaction`. Removing that journal commits the set. If the
process dies before then, the next locked command or working-tree read restores the
old set before continuing; committed reads still use their pinned Git snapshot.
Lock-aware readers therefore never consume a partial batch. This is not a filesystem
snapshot for direct readers/editors that bypass the lock. Undo restores or deletes a
path only when the inode it atomically claims still contains this batch's bytes;
restoration never overwrites a path recreated by an external editor. Differing external
bytes are preserved and reported. If two external versions race undo, the displaced one
stays beside the record at `.<filename>.autowork-tasks.undo`, with both paths named in
the error. Inspect and reconcile both versions, remove the saved copy from `tasks/`
only after preserving its needed content, and validate before retrying. Do not delete
a pending journal to skip recovery.

A write to the contract (the hashed fields or the goal), the section, or the status (`done`,
`supersede`) of a task whose attempt is live (a dispatched, running, reported, integrating
or integrated slot, or the sequential lease) is refused: rank, title, short and notes stay
open, and a held or interrupted attempt stays repairable. `add` writes a whole contract at once (`--resources`, `--exclusions`,
`--kind`, `--ownership`, `--sources`) and refuses a task whose goal and title match an open
or done one, naming it. `field` sets a
typed header field, or any other label as a body note (`Held by`, `Owner decision`).
`done ID --by WHO --reason TEXT [--evidence REF]` manually closes **any task kind**.
It writes `closure = "manual"`, actor, UTC timestamp, reason and the optional evidence
reference into the task record. It writes no receipt, check result or verification claim.
`list`, `show` and `why` return a `closure` object with provenance, metadata and a
`Verified`/`Manual` label (a verified record with missing or invalid evidence is explicitly
labelled `Verified (evidence missing or invalid)`, never reclassified as Manual); the fleet/TUI's All view includes closed rows showing the
receipt or manual reason. Closed rows have no queue-edit actions.

`goal` adds a goal or changes its fields, needs `--evidence` for `--status met`, and moves
focus from any other goal. Meeting a goal also requires every non-superseded owned task
to be done and qualified. Manual closure alone is not qualification. With owner authority,
record an exception using `field ID owner_waiver "WHO DATE: exact criterion, reason, risk"`
or `field ID owner_qualification "WHO DATE: qualification and evidence reference"`.
These are explicit owner attestations, not inferred authority from a body note or a
worker report. A met-goal write names each used exception in its output and Evidence
note. The task remains Manual and never acquires a receipt from this exception.
New and placed tasks take the next multiple of 1000 in their section; `move` takes the
midpoint between its new neighbours and, when no integer is left, spreads only the run of
gapless neighbours that follows, never the whole section. A written file grants no
authority beyond its typed fields, and a declared check still needs approval to run.

### Literal prose input: `--json`

For prose containing quotes, backticks, `$` (including `$(...)` or `$VAR`) or newlines,
use `--json FILE` or `--json -` on `add`, `field` and `goal`. Write the UTF-8 JSON file
with a file-writing tool, not an interpolated shell string. The command reads one JSON
object literally; it does not expand variables or execute its contents. Do not embed
prose in shell arguments, `echo`, or an unquoted heredoc.

Run these forms from the consumer repository:

```sh
autowork tasks add --json task.json
autowork tasks field TASK-ID --json field.json
autowork tasks goal GOAL-ID --json goal.json
# The same object from stdin; only the filename appears in the shell command:
autowork tasks add --json - < task.json
```

- **add:** keys match option names with hyphens replaced by underscores: `goal`,
  `title`, `short` (required), `section`, `id`, `scope`, `kind`, `ownership`, `sources`,
  `acceptance`, `checks`, `touches`, `depends_on`, `verified_depends_on`, `resources`,
  `exclusions`. Repeatable options take JSON arrays of strings, not comma-separated
  strings. Optional `notes` is the complete raw Markdown body, preserved byte for byte
  as UTF-8, including newlines and surrounding whitespace. Explicit raw bodies bypass
  canonical trailing-newline normalization; ordinary records keep it. Do not combine `notes` with
  `sources`: put the Sources line inside `notes` instead so nothing rewrites the body.
- **field:** `{"label": "scope", "value": "Keep $VAR and \n literally"}` sets a string.
  A list field takes an array (`{"label": "acceptance", "value": ["criterion"]}`),
  and `rank` takes an integer. `{"label": "notes", "value": "First line\nSecond line"}`
  replaces the **entire** Markdown body literally: read it first and retain Sources,
  holds and other existing notes. Other note labels keep their existing single-line
  behavior; use `notes` for lossless multiline prose.
- **goal:** `title`, `source`, `priority` (integer), `status`, `focus` (boolean),
  `depends_on` (array of strings), `evidence`; the goal ID remains positional.

File and stdin input have identical behavior. Unknown keys, wrong types, missing required
values, malformed/unreadable JSON and mixing JSON with value flags or field label/value
arguments are refused without writing. Repository selection and `--expect REV` remain
outside the object; with `field --json`, run in the consumer repository. Existing flags
and positional field values still work for simple input. All existing validation,
locking, in-flight and authority checks apply; JSON is data, not permission to run a check.

## Converting a repository: `autowork migrate`

`autowork migrate [repo] [--dry-run] [--no-commit] [--accept-consumers]` converts a TODO.md + goals.json
repository once; `autowork tasks prepare` runs it for Docs Sync, so no owner has to. It
refuses, writing nothing, while a worker slot is occupied (running, held, reported,
integrating or integrated), a coordinator or sequential lease is live, a task is
`in_progress`, planning files are uncommitted, or `tasks/` is already committed. A held slot
that only waits for the owner's answer to a worker-reported blocker (no live worker, no
finished commit, not a repeated quick hold) does not stop it: the runner that would take the
answer cannot run before conversion, so the proven conversion sets that attempt aside, as
`--parallel-set-aside` does, and the task dispatches fresh from its converted record. It builds
every record, reads them back through a throwaway commit and requires the same task set and
the same selection order as the current queue before writing. The proof's objects live
only in a temporary object database: `--dry-run` adds no repository objects. An actual
conversion rebuilds the proven tree in the repository before creating its durable
candidate; the throwaway proof commit is never persisted. The converted commit (records
added, TODO.md and goals.json removed with no stub, TODO.archive.md kept) is recorded as
`refs/autowork/migration` before any file changes; its paths are then staged in the working
tree and index, HEAD moves to it by compare-and-swap, and the ref is deleted. A run
interrupted at any point leaves the ref, and the next run finishes from where it stopped, or
refuses, changing nothing, when a path holds content that is neither the old nor the
converted version; a ref built on an older HEAD with nothing staged is rebuilt. With
`--no-commit` it stops after staging, and a later run (or the owner's commit) lands it. Ranks are 1000 x
the recorded human order. Typed fields keep the engine's present meaning (dependencies as
task IDs, resources as the tokens it enforces, owner-only work without a recorded live
authorization as `ownership = "owner"`, no Touches as `["**"]`); a `Live authorization` line
becomes the typed grant `live = "authorized"` only when it states one: a negative or
placeholder value (`none`, `n/a`, `pending …`, `not yet`, `TBD`, `denied`, …) refuses the
conversion, naming the task, so the source is fixed first; every other label, and
the original Ownership, Resources and Live authorization wording, is kept as a body note.
Done and superseded tasks, and archived tasks that open work depends on, become closed
records with no section or rank.

Before conversion, `--dry-run` and `tasks prepare --check` scan tracked working-tree text
and the Git snapshot retained by the transaction (HEAD, or a pending candidate) for literal
`TODO.md` or `goals.json` references (excluding those inputs and the frozen archive).
Uncommitted repairs or deletions cannot hide consumers still present in that snapshot:
commit those repairs first, or explicitly accept the retained consumers. Reports separate `consumers` (build files, CI, hooks, source, tests and other
non-documentation files) from `documentation_drift` (Markdown, reStructuredText, AsciiDoc,
Org and text files under `docs/`). Each hit gives `path`, 1-based `line` and `names`, not
the source text; retained-only hits also name their `revision`. Binary files are skipped
and symlinks are not followed; submodule contents and
untracked files are outside this scan. Documentation mentions never refuse conversion.
Other consumers do: fix them in their repository first, or explicitly accept the risk with
`autowork migrate --accept-consumers`. This flag changes no consumer code. Dry runs still
report the proposed conversion and its `refusals`; prepare reports `MIGRATION_BLOCKED`.
`prepare --force` does not accept consumers implicitly. A resumed conversion rechecks
consumers too: pass `--accept-consumers` again if any remain.

Conversion also accounts for TODO.md source lines. Known task entries map to records;
standard queue headings and archive navigation need no replacement. Generated coverage
between its unique `goals:coverage:begin`/`end` marker lines is dropped; ambiguous markers
refuse. Any other content (product checklists, milestones, owner answers, a free backlog,
comments, fenced examples, continued fields or ignored task annotations) triggers a
`CHECKLIST.md` preservation snapshot. It retains
the original TODO bytes, including queue context, with only generated coverage replaced
by empty lines: retained content stays at its original 1-based line numbers, with original
line endings. The `preserved` report names the destination and the extra-content
`line_ranges` (inclusive). A queue alone creates no snapshot. If the destination already
exists, conversion refuses and names the source ranges rather than overwriting it.
The preservation document is part of the same proven commit/staging/recovery transaction
as the task records, not an uncommitted backup. On resume, `preserved` names its path.

## Preparing a repository: `autowork tasks prepare`

`autowork tasks prepare [repo] [--check | --no-commit]` ([source](pi_autowork/task_prepare.py))
is the first step of every Docs Sync Bootstrap or Maintain, on every host. It prints one JSON
report: `state` (`legacy`, `conversion_pending`, `none`, `uncommitted`, `converted`,
`invalid`), the `actions` it took, `refusals`, tasks `in_flight`, `pending` task paths, the
store's counts, drafts and selection `order`, and `diagnostics` (`DRAFT`, `NOT_RUNNABLE`,
`LIVE_NOT_AUTHORIZED`, `UNKNOWN_DEPENDENCY`, `SUPERSEDED_DEPENDENCY`, `TOUCHES_TASK_STORE`,
`OPEN_TASK_UNDER_MET_GOAL`, `GOAL_WITHOUT_WORK`, `BROKEN_SOURCE` for a missing path or
heading anchor, `DUPLICATE_TASK`, `IN_FLIGHT`), each naming the `autowork tasks` command that
repairs it. After conversion, remaining references also appear as `LEGACY_CONSUMER` and
`LEGACY_DOCUMENTATION` diagnostics, naming the file and line to reconcile from evidence;
prepare never rewrites those files. Consumer and documentation inventories are included
before and after conversion. The capabilities handshake reports `prepare_api: 4` for
this conversion-safety contract. It converts a legacy repository and finishes a pending
conversion through `autowork migrate`'s transaction; for `none` it lists tracked documents and the headings
marked `Status: Accepted`. Everything else is judgement: it decides no intent, writes no
goal, task or field, and grants nothing. `--check` writes no file, ref, index, lock or
object; `--no-commit` stages a conversion without moving HEAD. It exits 1 when `ok` is false
(a refusal or an invalid store) and, on an unchanged repository, reports the same result.

## Integration and closure

Integration classifies a `tasks/` change by records, not paths. Rank, title, short and
notes are bookkeeping: a session that moved only by them keeps a running review. An
attempt whose task changed a contract label since dispatch (scope, acceptance, checks,
dependencies, resources, ownership, live, kind, exclusions, or a move to Needs decision)
is held as `contract_changed` and set aside, so it runs fresh; a Touches-only change does
not (Touches schedule work). A contract change during validation holds the candidate. A
worker commit that edits any task file is held for scope and never offered again: a worker
cannot grant itself or another task authority.

Session merges, worker merge adoption and planning remerges reject invented task or
goal values. Each status, Evidence note, closure/qualification field and contract
field must equal a value from a merge parent; ordinary notes may combine. Evidence
receipts must come intact from a parent. Adoption checks each step of a worker's
merge history, not just its endpoints. Rejection names the record and field and
restores the pre-merge head without moving main or accepting the worker report.
An intact parent record may replace a broken record, so ledger repairs still land.
This guard runs before the separate stale-closure reopening described below.

The verified close writes `status = "done"`, `closure = "coordinator_verified"`,
`closure_evidence = "tasks/evidence/<ID>.toml"` and `tasks/evidence/<ID>.toml` (candidate and
integration commits, tree, contract hash, checks, result, review; secrets redacted and paths
dropped) in one commit; a live follow-up becomes `<ID>-LIVE` in Needs decision. A replayed
close completes missing files and refuses differing ones, so a crash between writes resumes
to one commit, and a close whose commit exists is a no-op. After every merge into the
session the runner reopens an explicitly coordinator-verified done task whose receipt
pins another contract hash than its merged record (one side closed it, the other changed
its acceptance), before main moves. An explicit manual closure is not reopened because
of a retained receipt from an earlier attempt.

`TaskRecord.verified` requires explicit verified provenance and a schema-1 receipt naming
this task and contract hash, a passing result and review, an existing candidate commit,
and a reachable two-parent integration commit whose second parent is that candidate and
whose tree matches the existing receipt tree. Missing, malformed or stale receipts do
not qualify verified dependents or goal acceptance; `closure.evidence_valid` exposes this
without changing recorded provenance.
Unmarked historical closures are not upgraded by guessing from a receipt or Evidence note:
they display Manual with no recorded provenance/reason and need owner qualification for
verified-evidence gates. The scorecard keeps total `closed` and separately returns
`verified_closed`, `manual_closed` (including unqualified history), and `unverified_closed`
(recorded coordinator closures with missing or invalid proof); its table displays all three. Owner waivers do not inflate verified counts.

## Private lifecycle observations

The engine extends `autowork-execution/journal.jsonl` in the Git common directory;
there is no second event store. `slot_changed` records carry a `lifecycle` array,
and history/model observations use the same journal with `event = "task_lifecycle"`.
`parallel_state.lifecycle_events(common)` returns deduplicated envelopes and
`skipped` counts (`duplicate`, `torn`). `parallel_status` exposes those counts as
`journal_skipped` when nonzero; its existing interval metrics and the scorecard still use the
original slot transitions.

Each envelope has `event_id`, `timestamp` (epoch seconds), an opaque `repository`
identifier, `task_id`, `attempt_id`, `host`, `model`, and `scope` (`task` or `attempt`).
Unknown host/model information is `"unknown"`; events before an engine attempt use
`attempt_id = "unassigned"`. No prompt, command, free-text reason, credential or
absolute path is copied into an envelope. Legacy private diagnostic payloads remain
compatible and can contain local paths. Neither envelopes nor runtime identity are
added to committed task records or public closure receipts. The private validation
receipt's `context` carries the attempt/repository/host/model correlation instead.

The observed stages are `accepted`, `admitted`, `dispatched`, `held`, `resumed`,
`reviewed`, `integrated`, `closed`, and `delivered`. Holds/resumes occur only when
execution takes those paths; `reviewed` at successful integration means the required
validation passed, not that a model review ran when disabled. A fresh attempt records
`retry` and gets a new attempt ID; a paused attempt keeps its ID. Acceptance, closure
and delivery have per-task IDs, so a retry or replay cannot count another completion.
The acceptance timestamp/revision comes from the first reachable Git addition of
the task record, not an uncommitted edit. The coordinator observes committed hand
closures (`hand_closed`), contract edits during an attempt (`contract_edited`, even
if later reverted), and done records reaching main (`delivered`), including local
main when push is disabled. These are observations, not acceptance or authority gates.

Other observations include `verification_failed`, `interrupted`, `restart`,
`worker_adopted`, `replayed_close`, `blocker_answered` and `clear_held`. Actual Pi
model runs record `model_selected`, `model_retry` (provider/crash recovery), and
terminal `model_*` outcomes, correlated to the same task attempt; a fallback does
not masquerade as another task attempt. These model observations contain only
identifiers, role/outcome and provider retry counts, not run text or billing data.

A writer makes one append write and flushes it, with no extra lock wait or retry.
Telemetry I/O failure does not hold execution. Lifecycle facts saved with private
slots can be replayed after an interrupted append. A failed coordinator-release
append retains pending recovery facts in existing attempt metadata (`meta.json`),
without holding execution or changing slot state. The coordinator also reconciles
Git observations at startup/cycles and after landing. Git snapshots/history reads
run outside the execution writer lock, with an immutable-commit cache and a bounded
per-poll history budget; private slot cursors retain a frozen Git range and page
offset across restarts, including edits/reverts on merged branches. Closed and
retired attempts retain their history endpoint, excluding edits for later attempts. An
in-process journal tail index avoids rescanning history on unchanged polls. Readers skip/count duplicate
lines and incomplete JSON lines, including a torn final line; the next append starts
a new line. Complete but structurally invalid records still fail validation. Offline
fixtures cover ordering, retries, interruption/replay, adoption, manual closure,
contract edits, fallback attribution and envelope privacy; they do not qualify a
live model/provider or remote push.

## Offline verification

```sh
python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py
python3 scripts/check.py pi-autowork/engine/test_task_store.py
```

The public-seam tests use real temporary Git repositories. They cover pinned
reads/immutability/replacement refs, pending edits/renames/index preservation,
fingerprint boundaries, absent authority, corrupt-store refusal (including
symlinked store directories and numeric conversion limits) and draft visibility.
[`tests/test_task_transactions.py`](tests/test_task_transactions.py) covers concurrent
command edits to one record, validation rollback preserving an external edit, and
move/focus batches interrupted between records, during rollback or before the journal's
removal (Python interruption and abrupt process exit), followed by recovery and successful
whole-set writes. Run it with
`python3 scripts/check.py pi-autowork/tests/test_task_transactions.py`.
The closure case in `engine/test_parallel_integrate.py` covers verified provenance,
receipt-dependent selection and fleet display; `../tests/test_task_commands.py` covers
manual closure across task kinds, CLI/fleet disclosure, verified dependencies and goal
qualification. Its JSON-input case runs the documented shell command forms against files
and stdin, checks lossless scope/acceptance/body and goal-title readback, and asserts that
backtick and command-substitution payloads never create their marker files. `tests/test_scorecard.py` covers the total/verified/manual closure split.
`tests/test_task_migrate.py`, `tests/test_task_commands.py`, `tests/test_task_prepare.py`
(the Docs Sync lifecycle: bootstrap, conversion, staging, interruption, refusal, audit,
repair, concurrency and repeat runs on disposable repositories), the engine's dispatch and
integration tests and `tests/test_task_store_qualification.py` cover conversion, the CLI,
admission, closure and one runner journey on a fixture repository. None of them is
live-service acceptance. The CLI object-isolation case checks `count-objects`, index
bytes and refs across worktree validation, pending-edit preparation and task writes
in a linked checkout, plus rejected validation. Migration cases check that dry-run
proofs add no objects and an actual conversion leaves no unreachable proof commit.
Conversion regressions also exercise consumer refusal/explicit acceptance, nonblocking
documentation drift, checklist/backlog byte and line preservation, destination collision
refusal, staged recovery, task annotations/continuations and unchanged queue-only
conversion. The shared record mapper
stays independent of preservation, so engine fixture rebuilds remain repeatable. Prepare
rescans after conversion to include the new snapshot in its diagnostics immediately.
Consumer checks cover resumed transactions and uncommitted repairs that would otherwise
leave broken references in the committed conversion.

The [October 2026 object audit](../docs/plans/unreachable-objects-2026-10.md) records
remaining object-producing paths and preservation/candidate ref reachability. It does
not establish safety to re-enable automatic GC or authorize cleanup.
