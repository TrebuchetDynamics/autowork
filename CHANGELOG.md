# Changelog

Notable implemented changes. Commit references identify source history, not a
claim of a tagged release, completed installation or live workflow qualification.

## Unreleased

### Added

- Docs Sync's optional document role manifest (`docs/roles.json`) and read-only
  `skills/docs-sync/scripts/docs.py validate|check`: mapped documents and anchors,
  local links, documented script paths, covered paths and unmapped baseline roles.
  `docs.py stale` lists roles whose covered paths changed after their
  `verified_at` commit. Repositories without a manifest are unaffected.

- Planning craft shared by `/plan_with_me` and `/plan_for_me`, adapted from
  obra/superpowers `brainstorming` and mattpocock/skills `grilling` and
  `domain-modeling`: sizing (a clear task skips the interview), facts-versus-decisions,
  anti-goals, stated planner's calls, precise terms with ADRs only for hard-to-reverse
  surprising trade-offs, and a builder check that has a fresh reader list what
  Autowork would still have to guess before tasks are reported ready.
  `/plan_with_me` offers to skip the questions, asks describing questions before
  options, works in short rounds worded so "yes" accepts the recommendations, and
  plays each part back with guesses marked; its special cases moved to a reference.

- Telegram-routed Autowork jobs announce each run's start. The plugin copies the
  bundle's `autowork-start-notice.py` cron script into every profile's `scripts/`
  folder, and `/cron_autowork` attaches it; the finished report remains Hermes'
  normal cron delivery.
- `/cron_autowork` with a cadence resumes the matched paused job on that cadence
  (for example `/cron_autowork 5m`), unless the request says to keep it paused.
  Multi-profile refreshes and repairs still never resume a job.

- TODO.md order is the enforced human priority. goals.json records a versioned
  `priority_order`; selection ranks focus, section, recorded order, then goal
  priority. `goals.py next`, direct selection, backlog checks and retry selection
  share one guard that returns `PRIORITY_DRIFT` instead of the stale pick.
  `goals.py reorder` reconciles; `goals.py bootstrap-order` is the one-time,
  dry-run-first migration; it keeps tasks within their `###` groups, refuses a
  changed first pick and reports deeper eligible-order changes. Unrecorded ledgers keep legacy order with a visible
  `UNMIGRATED` flag. Fleet migration is a separate pending task.

- Automatic completed-task archival during `goals.py render`, plus an archive-only
  command. Whole closed bodies move to the established archive under the canonical
  lock; open bodies and ledger history remain (`08701bd`).
- Opt-in maintenance repair prompt generation with one bounded consultation/repair
  batch, preserved paused jobs and explicit product/live-operation exclusions.
  Cron command-discovery guidance separates live registration from message retry
  and scheduling; neither prompt generation nor registration proves execution
  (`d136ccd`).

- `/cron_autowork` creates or updates repository-bound Autowork schedules with
  duplicate checks, preserved paused state and explicit budget/delivery limits.
  Codex/Pi adapters report unavailable scheduling instead of emulating a daemon.

- Native Codex marketplace/plugin packaging and a Pi package with portable workflow
  adapters and package checks (`bcb72c5`).
- Adaptive document-role scaffold for Docs Sync (`a16b754`).
- Verification of explicitly declared writer-registration prerequisites (`d422ea4`).

### Fixed

- An idle interactive agent session left open in a repository no longer blocks
  Autowork indefinitely. Sessions block only their own checkout and only while
  active (terminal use within 30 minutes, running commands or an open writable
  repository file); an active one gets an isolated worktree branch instead of a
  dead end. `owner_cycle.py REPO --writers` reports the classification read-only.
- `/toolset update` clears leftover chat-scoped Telegram menus that still list
  retired commands such as `/autogoal`; Telegram preferred them over the lists
  Hermes refreshes, so restarts never removed them (`chat_menus_healed`).

- Completed-task archival keeps sibling priority-group headings in the live TODO
  while retaining deeper evidence subsections with their owning task (`586337f`).

- Telegram menus no longer advertise compatibility commands (`/autoresearch`,
  `/autoresearch_plan`, `/autoresearch_<protocol>`); they stay typeable. The menu
  policy removes those entries from existing profile priorities. `/toolset update`
  now verifies each profile's re-applied settings, reports `settings_healed`, and
  requests one graceful gateway restart when anything changed so menus refresh.

- A task body no longer absorbs the next task's own `### ID` heading into its last
  field, which made a following heading read as an unresolved dependency.

- Partial worktree-claim updates preserve their unique historical workspace and
  existing ownership metadata. Conflicting aliases, duplicate JSON fields,
  ambiguous histories and owner changes are refused instead of permitting task
  takeover (`07a9f68`).

- Verification commands now remap repository-root arguments into the frozen
  candidate checkout. Receipt directories are created before check execution,
  avoiding lost successful results from missing parent directories. Timed-out
  finish-task acceptance commands and interrupted validation terminate their POSIX
  process group so child writers cannot continue after the helper exits.

- Ready autonomous tasks prepare their native handoff without an unnecessary
  research pass; saved failure evidence still requires reconciliation. A recorded
  goal handoff with notification failure remains queued with a transport warning,
  rather than being misreported as failed admission. New handoffs can archive the
  legacy nested continuation receipt without losing its original history.

- Autowork keeps pending closeout visible across unchanged calls, detects ended
  review runs on stale cards, and refreshes asynchronous state before waiting reports.
  Batch guidance separates required completion from optional hardening and aligns
  the shared cycle with authorized same-occurrence continuation. These offline
  checks do not establish live scheduler throughput or completed product delivery.

- New Autowork cards stop automatic failure retries at the first failed attempt
  and verify that policy in native readback. Handoff receipts distinguish per-run
  turn allocation from unavailable cumulative native enforcement; existing cards
  and consumed budgets remain unchanged.

- Autowork distinguishes a planning receipt with no supported change from a repair
  ready to resume, preserves invalid receipts for inspection, and exposes terminal
  run state even when its card still says running. Recovery keeps the original
  task and consumed budget; these checks do not implement native accounting repair.

### Changed

- Autowork executes and recovers repository tasks directly from TODO.md and its
  synchronized goals.json index. Historical Kanban cards are not admission, review
  or deployment prerequisites; actual process/workspace ownership, explicit limits,
  required checks and independent review remain. Superseded native-only work keeps
  its failed/unchecked history rather than being reported complete. Isolated
  no-agent scheduler proof remains distinct from model and Telegram qualification.

- Reconciled guidance that profiles had edited into installed skill copies back
  into Autowork, Cron Autowork, Docs Sync, Git Commit Push, Git Pull Merge, Plan
  With Me, Plan For Me and Autoresearch. Generic rules were condensed upstream;
  Kanban-card, profile-specific and pinned-vendor edits were not ported. Installed
  copies still need a successful update before profiles use the new text.

- Plan For Me now has its own matching skill directory and identity; Autoresearch
  remains independently registered. Plan With Me and Docs Sync no longer register
  the old repo-interview/repo-docs aliases. Autoresearch compatibility commands
  remain available (`60bbc70`); this supersedes the earlier alias-retention behavior
  recorded below.

- Renamed bundled source folders to `docs-sync` and `plan-with-me`; old command
  spellings remain aliases, while retired local snapshots are excluded from discovery
  and installation. Updated helper, package and documentation references.

- Planning workflows share one incremental handoff: resume decisions, scope open
  questions to dependent tasks, batch affected docs, reuse unchanged validation
  and return to authorized Autowork execution without another planning cycle.

- Compact reconciliation bounds routine readback and retains repeated-blockage
  observations without changing worker retry budgets or runtime ownership.

- Autowork resumes its saved reconciliation projection before discovery, reports
  changed evidence fields, and prioritizes unfinished closeout. Check receipts
  support run-or-reuse and omit terminal display IDs from execution and identity.

- Reconciliation preserves new run/outcome reports even when card status is unchanged,
  and gives phase-specific observation, recovery and integration follow-up hints.

- Writer-registration checks recover omitted terminal task context from an exact
  original handoff; conflicting context and stale registration remain rejected.

- Autowork scopes connected work as coherent delivery batches, carries that rule
  into worker/cron prompts, and reports delivered slices separately from parent
  task completion. Required review, input freshness and explicit limits remain.

- Hermes skill discovery publishes Plan With Me, Plan For Me and Docs Sync;
  previous command spellings remain compatibility aliases (`bcb72c5`).
- Grill Me becomes a challenge mode in the Hermes plugin catalog; portable
  catalog alignment remains tracked in [TODO.md](TODO.md) (`bcb72c5`).
- Autowork routes stalled preparation to bounded planning, persists findings and
  retries execution within existing authority (`bcb72c5`). This is a workflow
  contract and tested helper behavior, not proof of live task completion.
- Local coordination and workflow references use current Autowork authority and
  names (`2377918`).
