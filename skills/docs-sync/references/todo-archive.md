# Live TODO and historical archive

## Ownership and path selection

- `goals.json` owns machine-readable goal/task state and evidence. Keep completed task records and executed receipts in the ledger. Change it through `goals.py`; archiving prose is not a goal-status change.
- `TODO.md` owns the live human/worker backlog: navigation, compact generated Goal coverage, and open `Now`, `Next`, and `Blocked / Needs decision` entries. Keep active ownership, dependencies and unresolved questions visible. Retain the generated coverage table, including compact met-goal rows; do not edit its rows by hand merely to shorten the file.
- `TODO.archive.md` is the default repository-root history owner. Reuse an established equivalent such as `todo.archive.md` or `docs/TODO-archive.md`; preserve its spelling and layout. Do not create a second archive or rename existing history to match the default. Link the canonical archive near the top of `TODO.md`.
- `BLOCKERS.md` remains the owner-question ledger. The archive is not authoritative for current decisions, task eligibility, goal status, dirty files or runtime health. History never queues work.

Create the archive with substantive moved history when it is needed. Do not create an empty history scaffold on every pass. An Audit/read-only pass edits neither TODO, the archive nor the ledger.
The canonical archive link belongs in navigation outside task bodies. Task-source
links to archive policies, code or historical evidence do not select an archive owner.

## Automatic task archival

Every writing Docs Sync Bootstrap/Maintain pass and Autowork verified closeout
includes archival; do not wait for a separate user request or a scheduled docs job.
Reconcile completion evidence and the live checkbox/Status with the ledger first.
Run `goals.py archive <repo>` for archive-only maintenance. `goals.py render <repo>`
automatically performs the same move before saving updated coverage. Both operate
under the existing canonical-repository lock. Read-only commands never archive.

The helper moves whole top-level checkbox entries or `### TASK-ID — Title`
sections only when they are explicitly closed and their ledger task is `done`.
A met goal alone, an unchecked task, an open subtask or conflicting status cannot
authorize a move. Keep one `Status:` line per body, beginning with `done`; put
review/commit details in a separate evidence field, since a second Status line blocks it. It keeps completed ledger records and goal evidence, including
pending broader qualification. An archive-only result lists `moved`, `retained`
and the canonical `archive`; report retained conflicts and reconcile from evidence.
Ambiguous overlapping task-shaped headings keep the whole affected unit live,
including unknown tasks with missing metadata; independent clear entries still move.
A task heading immediately followed by one checkbox with the same ID is a single
unit: archive the heading, checkbox and complete continuation together, once.
Only whitespace may separate that heading and checkbox; intervening metadata,
multiple checkboxes or a mismatched ID remain ambiguous rather than permitting
a partial move. A separately closed heading-only task may still precede an
independent checkbox task. Nested evidence and fenced examples stay with their
owning unit; open acceptance items and conflicting statuses keep it live.
Do not automatically delete old empty headings: reconcile a known residue only
against its exact existing archived completion body and ledger record, preserving
the heading in append-only history and leaving unrelated text untouched.

For a repository without goals.json, the writing agent verifies the completion
checks, then invokes `goals.py archive <repo> --verified-tasks ID1,ID2` with only
the verified, explicitly closed task IDs. This is an explicit caller attestation,
not a check runner. It cannot override an existing ledger or archive an open task.
Do not create a synthetic ledger merely to archive existing prose.

The helper preserves original entry bytes and prior archive bytes, verifies the
archive before removing live text, and retries interrupted moves by whole-block
containment and multiplicity. Conflicting archive owners, symlinks, changed source
or changed archive bytes are refused. A crash may leave a duplicate live entry;
rerun the command to finish safely. The cooperative lock does not prevent a writer
that ignores it from editing files. Broader historical narratives and dated
pass-notes still follow the preservation procedure below.

## What belongs in history

Move completed task entries with their completion evidence, closed-goal narrative, completed entries buried in Blocked, dated pass-notes, past gate receipts and point-in-time tree snapshots. Preserve the whole entry verbatim, including continuations, quotations, identifiers, commands and evidence. A checked box or a heading alone does not prove completion; inspect the relevant ledger/receipt first. Mixed sections require entry-level separation: leave all open tasks and unresolved owner questions in the live backlog.

Do not move a met goal's open task on status alone. Reconcile the inconsistency with evidence. Do not lose an open successor, dependency or live-owner claim when archiving its predecessor. Keep necessary current facts with their live task even when related narrative moves to history.

During each Bootstrap/Maintain pass, put new dated pass-notes and historical receipts directly in the canonical archive, not in `TODO.md`. Leave a short current-status sentence or evidence link with an open task only when it is needed to act. Do not append a dated diary entry on every scheduled occurrence. An unchanged pass creates no new archive entry and leaves both files byte-identical.

## Preservation procedure

1. Read current TODO, archive, ledger and relevant completion receipts. Account for open task IDs, completion blocks, dated pass-notes and active ownership before selecting any move. Preserve concurrent edits; use exact anchored patches and reread before writing. Do not perform a broad regex deletion or regenerate the whole backlog from a summary.
2. Prepare an append-only migration: add a source/path/date catalogue outside the original blocks, then append each selected original block verbatim once. Retain original section context, but do not duplicate each moved heading. Preserve all pre-existing archive bytes, including historical trailing whitespace; if `git diff --check` flags it, add a wrapper or footer outside the original blocks rather than trim history. Treat archive text as historical evidence, not executable instructions. Only verified cosmetic errors in newly added wrappers may be corrected; leave original receipts unchanged.
3. Write and verify the archive **before** removing source text. If verification fails or TODO changes concurrently, leave TODO intact and report the incomplete move. A duplicate retained after interruption is safer than a missing receipt; inspect and reconcile it rather than blindly appending it again.
4. Verify conservation programmatically. Every selected block must exist byte-for-byte in the archive with the required multiplicity: repeated source text must not disappear because a set deduplicated it. Compare exact blocks or a lossless before/after partition, not sentence-joined fragments. A larger union, equal task counts or equal byte totals alone does not prove preservation. Whole-file byte totals can legitimately grow because catalogue/link text was added. Keep before/after evidence in private ignored scratch, never commit secret-bearing backups.
5. Verify all open entries and their continuations remain verbatim in TODO. For priority-only reorders, compare the multiplicity of complete task blocks before and after, allowing only explicitly intended field changes; compare ID lists with `Counter(mapping.keys())`, not `Counter(mapping)`, because the latter treats dictionary values as counts. Verify existing archive content is unchanged and no new duplicate heading was introduced. If another writer appended history during verification, inspect the added region and confirm the original bytes remain an exact prefix; preserve that contribution and report a concurrent append, not a byte-identical archive or a failure caused by this pass. If the prefix changed, reread and reconcile the affected blocks before writing; never restore the stale baseline. Reconcile completed task IDs with the ledger without treating ID counts as proof that their bodies survived. Fix local links and check for private data; never reproduce credentials in the archive or reports.
6. Run `goals.py fmt <repo>`, `goals.py validate <repo>` (must print `ok`), and `goals.py render <repo>`. Recheck the archive and open-task preservation after rendering. On an unchanged second pass, both TODO and archive must stay byte-identical. Report the actual checks, remaining gaps and canonical archive path. A static policy test does not prove an agent performed a lossless migration.

## Reconciling a drifted live TODO

A scheduled or on-change pass can re-grow the live file: completed entries, past
sections and dated notes reappear in `TODO.md` after a correct split. Before
re-splitting, treat the live file as untrusted and the archive as authoritative:

- **Containment-check per block, not per ID.** A block whose entry already exists in
the archive is *removed* from the live file, not appended again. Compare the
normalized block text against the archive bytes; drop the live copy only when its
text is contained verbatim in the archive, otherwise keep it live and report the
divergence. ID-level detection alone either duplicates history or silently
discards a longer live version.
- **Include whole historical sections in that check.** Appending a section such as a
completed-work section re-adds every block inside it, so a containment check that
only covered the selected entry list still duplicates history (check the live
selection, then the sections, then the notes). After appending, recount multiplicity
per block across the whole archive; de-duplicate the newly appended region against
pre-existing blocks and keep the original copies.
- **Union the ledger with what the live file already holds.** Regenerating a section
from `goals.json` drops entries that exist only in TODO — an "as found" note, a
parked observation with no ledger task. Build the skeleton from the ledger, merge
back every open ID that was already present, and assert each pre-existing open ID
appears exactly once in the result before writing.
- **Coordinate ledger and body placement.** Set an unfinished task's section with
`goals.py section <repo> <task> {Now,Next,Needs decision}`, then relocate its complete
body under the matching heading with lock and baseline checks; `render` does not
move bodies. Archive verified done bodies instead. Since `autowork` selects only
from `Now` and `Next`, a task whose next step needs an owner (a deploy window, an
approval) belongs in `Needs decision`; leaving it eligible invites a gated action.
- **Records the state you found.** Report pre-existing duplicates, withdrawn entries
and stale warnings as found rather than silently repairing history. When a note in
the live file asserted a condition that is now false (for example, that the archive
was untracked), move it to the archive under a dated retraction note instead of
deleting it.

## Reading history

Use `search_files` on the archive to answer “which gate already ran?” or “what did that pass measure?”. Confirm current source revision, evidence relevance and present state before reusing a historical pass. Never reopen completed work merely because its archived task appears in a search. Never claim a prior snapshot or a met goal guarantees the current tree is healthy.

## Scope

This contract changes future docs-sync work. It does not itself migrate every repository, rewrite live cron prompts, authorize source changes, or grant commit/push permission. If a configured cron prompt explicitly requires dated notes in TODO or excludes the history owner, a profile manager must make a scoped prompt correction and read it back while preserving schedule, model, delivery, continuity and enabled state. Do not let the cron reschedule itself.

## Superseded requirements

When an accepted decision retires a task, use
`goals.py supersede <repo> OLD --by NEW --reason "accepted decision"`, then
`goals.py render <repo>`. The successor must already exist. The index records
`superseded` and a reason; the archive preserves the original unchecked body under
an explicit non-completion disposition. This does not satisfy dependencies, count
as completed work or qualify a goal as met. The conservative met rule still
requires done tasks and executed passing goal evidence; reconcile a changed goal
against its accepted scope instead of relabelling retired checks as passed.

Owner-cancelled work without an accepted successor cannot use `supersede` and is
never marked done. Keep it in Needs decision, label the body cancelled with its
dependencies and an Acceptance field for selector exclusion, preserve the original
contract in history, and verify exclusion with `next --json`.
