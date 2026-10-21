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
