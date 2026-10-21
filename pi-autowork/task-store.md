# TaskStore (schema 1)

`engine/task_store.py` is the one task store of the accepted
[Task Store v2 design](../docs/project.md#task-store-v2-2026-10-20): selection, dispatch,
integration, closure, the runner, the fleet view and `autowork tasks` all read `tasks/`
through it, at a pinned commit. Nothing reads TODO.md or goals.json; only
`autowork migrate` keeps a private reader of them, to convert a repository once.

## Snapshot API

- `TaskStore.at(repo, rev)` resolves a Git revision to a commit SHA once, then
  reads `tasks/items/<ID>.md` and `tasks/goals/<ID>.md` with `git ls-tree` and one
  `git cat-file --batch` call at that SHA, whatever the number of files. The returned `rev` is that pinned SHA, not the input
  branch name. Working-tree edits never become records. Git replacement refs
  are disabled so they cannot substitute content for the pinned object IDs.
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

All fields except `live` are needed for a complete task contract. Missing fields
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

**Holding a task.** Git status is never a lease, so there is no `in_progress`. A person or
an interactive session keeps the runner off an open task with
`autowork tasks hold ID --by WHO [--until YYYY-MM-DD]`, which writes the record's
`- Held by: WHO; until DATE` note and nothing else (the contract hash is unchanged);
`autowork tasks release ID` removes it. A held task is never selected (`HELD`), never
dispatched even when named, and still blocks its dependents and tasks that share its
resources or serial work; the hold ends when the note is removed or its date passes.

## Writing and `autowork tasks`

`tomllib` only reads, so `task_store` carries its own writer. `render` writes a new record
in canonical key order; `edit` changes only the header lines it names and keeps every
other byte; `set_note` sets one `- Label: value` line in the body. Each refuses what it
cannot reproduce (a value spread over several lines, a trailing comment, line breaks or
control characters, unknown keys) instead of dropping it, and checks that the result reads
back to exactly the intended values.

`autowork tasks` reads at HEAD (`list`, `show`, `why`, `validate`; `--worktree` on `list`,
`show` and `validate` reads uncommitted edits through a throwaway commit that leaves the
index and refs alone) and edits the working tree (`add`, `field`, `place`, `move`, `hold`,
`release`, `done`, `supersede`, `goal`; `new-id` allocates an ID); it never commits. A write
holds the repository's task lock (`<git dir>/autowork-tasks.lock`), so two writers never
interleave; refuses a file that changed since it was read, or since the `record_revision`
given as `--expect REV`; and is undone when the resulting store does not validate.
The Python command entry points and working-tree reads share that lock too. A `move`
that rebalances neighbours, or a `goal --focus` that clears another goal, compares all
inputs before writing and validates the resulting set once. Rendering or validation
failure, an I/O error or a Python interruption undoes the whole set.

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
`done --evidence` closes a task outside the engine (a planning task, or one whose acceptance
the evidence shows met) and keeps the evidence as its note; `goal` adds a goal or changes its
fields, needs `--evidence` for `--status met`, and moves focus from any other goal.
New and placed tasks take the next multiple of 1000 in their section; `move` takes the
midpoint between its new neighbours and, when no integer is left, spreads only the run of
gapless neighbours that follows, never the whole section. A written file grants no
authority beyond its typed fields, and a declared check still needs approval to run.

## Converting a repository: `autowork migrate`

`autowork migrate [repo] [--dry-run] [--no-commit]` converts a TODO.md + goals.json
repository once; `autowork tasks prepare` runs it for Docs Sync, so no owner has to. It
refuses, writing nothing, while a worker slot is occupied (running, held, reported,
integrating or integrated), a coordinator or sequential lease is live, a task is
`in_progress`, planning files are uncommitted, or `tasks/` is already committed. A held slot
that only waits for the owner's answer to a worker-reported blocker (no live worker, no
finished commit, not a repeated quick hold) does not stop it: the runner that would take the
answer cannot run before conversion, so the proven conversion sets that attempt aside, as
`--parallel-set-aside` does, and the task dispatches fresh from its converted record. It builds
every record, reads them back through a throwaway commit and requires the same task set and
the same selection order as the current queue before writing. The converted commit (records
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

## Preparing a repository: `autowork tasks prepare`

`autowork tasks prepare [repo] [--check | --no-commit]` ([source](pi_autowork/task_prepare.py))
is the first step of every Docs Sync Bootstrap or Maintain, on every host. It prints one JSON
report: `state` (`legacy`, `conversion_pending`, `none`, `uncommitted`, `converted`,
`invalid`), the `actions` it took, `refusals`, tasks `in_flight`, `pending` task paths, the
store's counts, drafts and selection `order`, and `diagnostics` (`DRAFT`, `NOT_RUNNABLE`,
`LIVE_NOT_AUTHORIZED`, `UNKNOWN_DEPENDENCY`, `SUPERSEDED_DEPENDENCY`, `TOUCHES_TASK_STORE`,
`OPEN_TASK_UNDER_MET_GOAL`, `GOAL_WITHOUT_WORK`, `BROKEN_SOURCE` for a missing path or
heading anchor, `DUPLICATE_TASK`, `IN_FLIGHT`), each naming the `autowork tasks` command that
repairs it. It converts a legacy repository and finishes a pending conversion through
`autowork migrate`'s transaction; for `none` it lists tracked documents and the headings
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

The verified close writes `status = "done"` and `tasks/evidence/<ID>.toml` (candidate and
integration commits, tree, contract hash, checks, result, review; secrets redacted and paths
dropped) in one commit; a live follow-up becomes `<ID>-LIVE` in Needs decision. A replayed
close completes missing files and refuses differing ones, so a crash between writes resumes
to one commit, and a close whose commit exists is a no-op. After every merge into the
session the runner reopens a done task whose receipt pins another contract hash than its
merged record (one side closed it, the other changed its acceptance), before main moves.

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
`tests/test_task_migrate.py`, `tests/test_task_commands.py`, `tests/test_task_prepare.py`
(the Docs Sync lifecycle: bootstrap, conversion, staging, interruption, refusal, audit,
repair, concurrency and repeat runs on disposable repositories), the engine's dispatch and
integration tests and `tests/test_task_store_qualification.py` cover conversion, the CLI,
admission, closure and one runner journey on a fixture repository. None of them is
live-service acceptance.
