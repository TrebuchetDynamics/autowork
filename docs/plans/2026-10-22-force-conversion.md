# A forced conversion converts (2026-10-22)

Plan For Me, delegated by the owner; the owner's words were "make sure docs_sync force
overrules anything". Size: a small project (one outcome, four bounded slices). Facts come
from `pi-autowork/pi_autowork/task_prepare.py`, `task_migrate.py`, `fleet_view.py`,
`tui.py` and `pi-autowork/task-store.md`; every default below is the planner's call unless
marked as the owner's.

## What happened

A repository still planned in TODO.md + goals.json showed as `needs tasks` in the TUI's
browser. `autowork tasks prepare` answered `MIGRATION_BLOCKED` naming two worker slots
(one held, one running) although no worker process was alive and no runner was running;
the agent reported "needs tasks is masking a blocked format migration". The owner then
asked for `/docs_sync force` and for force to overrule anything.

Reading the code, the plain refusal was not deferred because a hidden second reason
made it non-deferrable: `_prepare` appends the tracked-consumer refusal to the list it
tests with `deferrable()` but reports only the slot refusal the conversion raised. The
runner that would drain a deferred request was not running, so a deferral would have
waited forever anyway.

## What force does today, and where it still stops

`autowork tasks prepare --force` stops the service, ends other lease holders, stops
live workers and sets every attempt aside with its work kept, commits the owner's
planning edits, converts, and restarts the service. It still answers `MIGRATION_BLOCKED`
when:

1. tracked consumers (build, CI, hook, source or test files) name TODO.md or goals.json:
   `convert_after_drain` calls `convert()` without `accept_consumers`, and the task-store
   doc says force does not accept them implicitly;
2. only one of TODO.md and goals.json exists: `detect()` calls the repository legacy,
   `refusals()` requires both files, so neither plain nor forced prepare ever converts it;
3. TODO.md's order differs from the recorded priority (`reader.Drift`), or a queue entry
   does not validate: `build()` refuses the whole conversion;
4. TODO.md content needs preservation but `CHECKLIST.md` already exists, or the content
   cannot be accounted for (an actual data-loss guard).

The TUI's browser offers Prepare and Prepare and start, never force, and labels a
legacy repository `needs tasks`.

## Decision

**Owner's decision (2026-10-22):** `/docs_sync force` overrules every wait and every
refusal that is not an actual loss of work or data. It is still the owner's explicit
word; nothing automatic uses it.

Planner's calls, each reversible by the owner:

- **Consumers are reported, not refused, under force.** A forced conversion passes
  consumer acceptance; the tracked references it converted over appear in the report's
  `LEGACY_CONSUMER` diagnostics (path and line), which Docs Sync already turns into repair
  task records. The explicit `autowork migrate --accept-consumers` stays for the plain
  route. Reason: consumer code is retained in Git and named in the report, so nothing is
  lost; the previous rule asked the owner for a second word after the first.
- **Plain prepare says everything it refuses on, and the route out.** Every refusal
  (slots, leases, claims, consumers, uncommitted planning) is listed, and `next` names
  `autowork tasks prepare --force` when no runner is running to drain a deferral.
- **Order drift and invalid queue entries do not stop a forced conversion.** Under
  force TODO.md's order wins and the drift is reported; an entry the reader cannot
  validate is left out of the converted store and its TODO.md lines are retained in
  the `CHECKLIST.md` preservation snapshot with their line ranges, named in the report.
  The legacy-order proof then covers the converted IDs only.
- **A lone legacy file is a bootstrap, not a blocked migration.** A repository with only
  one of TODO.md and goals.json is state `none`: prepare reports `NO_STORE` with the lone
  file listed as legacy content to reconcile, under force and plain alike.
- **The TUI exposes force and names the state honestly.** The browser's not-ready dialog
  gains Force (confirmed, since it stops the service and live workers), the pane shows
  every refusal and the forced step's summary (stopped, set aside, committed, commit),
  and a legacy repository is marked `legacy planning` instead of `needs tasks`.
- **Still refused under force:** a `CHECKLIST.md` collision and content that cannot be
  accounted for. Both are data-loss guards; the report names the source ranges.

Non-goals: no automatic force by a runner or schedule; no rewrite of consumer code;
no change to what a deferred conversion does when a runner is running.
Anti-goal: a forced conversion that drops a task, a worktree, a branch or TODO.md
content without naming it would make this a failure even if it converts.

## Tasks

Recorded in `tasks/` under goal `FORCE-CONVERSION` (see `autowork tasks list`): the
consumer and reporting change first, the TUI in parallel, the drift/invalid-entry and
lone-file slices next.
