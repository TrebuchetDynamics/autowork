# Read-only TaskStore (schema 1)

`engine/task_store.py` implements the reader portion of the accepted
[Task Store v2 design](../docs/project.md#task-store-v2-2026-10-20).
It is not yet wired into engine consumers. The current runner still uses
TODO.md/goals.json; this reader adds no writer, CLI or migration.

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
the rule the TODO.md queue uses. `next(store)` is the first that is not a planning task.
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

`autowork tasks` reads at HEAD (`list`, `show`, `why`, `validate`; `validate --worktree`
checks uncommitted edits through a throwaway commit that leaves the index and refs alone)
and edits the working tree (`add`, `field`, `place`, `move`, `supersede`, `new-id`); it
never commits and never writes TODO.md or goals.json. A write refuses a file that changed
since it was read and is undone when the resulting store does not validate. `field` sets a
typed header field, or any other label as a body note (`Held by`, `Owner decision`).
New and placed tasks take the next multiple of 1000 in their section; `move` takes the
midpoint between its new neighbours and, when no integer is left, spreads only the run of
gapless neighbours that follows, never the whole section. A written file grants no
authority beyond its typed fields, and a declared check still needs approval to run.

## Converting a repository: `autowork migrate`

`autowork migrate [repo] [--dry-run]` converts a TODO.md + goals.json repository once. It
refuses, writing nothing, while a worker slot is occupied (running, held, reported,
integrating or integrated), a coordinator or sequential lease is live, a task is
`in_progress`, planning files are uncommitted, or `tasks/` already exists. It builds every
record, reads them back through a throwaway commit and requires the same task set and the
same selection order as the current queue before writing; then it removes TODO.md and
goals.json (no stub), keeps TODO.archive.md, and makes one local commit. Ranks are 1000 x
the recorded human order. Typed fields keep the engine's present meaning (dependencies as
task IDs, resources as the tokens it enforces, owner-only work without a recorded live
authorization as `ownership = "owner"`, no Touches as `["**"]`); a `Live authorization` line
becomes the typed grant `live = "authorized"` only when it states one: a negative or
placeholder value (`none`, `n/a`, `pending …`, `not yet`, `TBD`, `denied`, …) refuses the
conversion, naming the task, so the source is fixed first; every other label, and
the original Ownership, Resources and Live authorization wording, is kept as a body note.
Done and superseded tasks, and archived tasks that open work depends on, become closed
records with no section or rank.

## Offline verification

```sh
python3 -m unittest discover -s pi-autowork/engine -p test_task_store.py
python3 scripts/check.py pi-autowork/engine/test_task_store.py
```

The six public-seam tests use real temporary Git repositories. They cover pinned
reads/immutability/replacement refs, pending edits/renames/index preservation,
fingerprint boundaries, absent authority, corrupt-store refusal (including
symlinked store directories and numeric conversion limits) and draft visibility.
They do not prove migration, consumer integration, command execution or
live-service acceptance.
