# Changelog

Notable implemented changes. Commit references identify source history, not a
claim of a tagged release, completed installation or live workflow qualification.

## Unreleased

### Fixed

- Another live agent session in the main checkout no longer holds a commit at
  integration: the engine answers `BUSY` and the commit stays reported (or its validated
  candidate is revalidated) until the session leaves, because a busy checkout is no
  verdict. Holding it used up the last attempt of three charlie commits;
  commits held that way by earlier releases are offered again (`REOFFERED`).
- The pi-autowork reviewer is told which device, hardware, production or human checks
  the worker recorded as `pending_live` (they become the `TASK-LIVE` follow-up) and judges
  everything else offline; a required live check nobody recorded still fails. It used to
  fail offline-complete work for want of a device (flutter TASK-006).
- A task the engine will not run (for example an entry missing its Scope, Acceptance or
  Checks) shows the engine's reason instead of "awaiting dispatch" and is a `contract`
  root blocker in health and `--fleet` (flutter TASK-003).
- `PI_AUTOWORK_LINK_PATHS` dependencies are mirrored with real directories and hard-linked
  files (a copy across filesystems) instead of a directory of symlinks: `find` does not
  descend into a symlinked directory, so a repository's own self-test saw an empty
  dependency build (sierra TASK-026). Mirroring 7,000 files takes a quarter second and no
  extra disk.
- A pending final merge names the files that block it (for example uncommitted
  `TODO.md` edits in the main checkout); the message used to stop at "would be
  overwritten by merge:".
- An idle `in_progress` claim is never adopted when a TODO.md note holds it: its own
  entry, or any line naming it, says to keep it open, forbids dispatch, puts it on hold,
  or says it requires or is missing an authority or approval. sierra TASK-029 was adopted
  and merged although a planner note retained it open for a missing authority.
- `worktree_closeout.py --archive` clears a backlog of old worktrees without losing
  work: an unintegrated HEAD or uncommitted changes are saved as a commit under
  `refs/archive/worktrees/` (restore with `git worktree add DIR REF`) before the
  worktree is removed. sierra had 99 worktrees, 97 of which ordinary cleanup must keep.

- Closing a task works when the archive already holds an older entry with the same ID;
  the closed entry matching the validated contract is judged. sierra TASK-029 closed but
  then read two archived entries and retried its close every cycle.
- Integration and close no longer refuse because of a process that exited during the
  writer check (a worker's short tool run seen by the scan and gone by the attribution
  step): only a writer still alive with the same identity blocks.
- A merged task whose TODO entry someone else archived or removed afterwards is
  set aside automatically (its merge stays; nothing is queued again) instead of
  retrying its close every cycle (bravo TASK-001).
- A parallel Autowork worker can no longer get a second writer beside it in its own
  worktree (TOOLSET-116-c1). Workers carry `AUTOWORK_WORKTREE`; a worker whose launch
  was never recorded, or a child that left its process group, now keeps the slot
  running and is stopped with the group. Before, the next pass started a duplicate
  worker, and a slot was reported while a stray child still wrote. Seven adversarial
  fixtures ported from the Pi orchestrator research cover these and four cases the
  engine already handled.

- Runner health ignores a status read the engine could not answer (its state lock
  busy with a `--status` or `--fleet` reader). Such a read used to count as idle and
  restart the stall clock, so polling status could hold back a stall announcement.
- A hold during integration counts toward `PI_AUTOWORK_MAX_FAILURES` again; since
  the failure-streak fix only worker-side holds were counted.
- Git Commit Push never pushes a branch that is behind its push target, including a
  `HEAD:main` refspec push from a worktree, and fast-forwards the canonical checkout's
  local `main` after pushing the default branch from elsewhere (or reports **local
  main stale**). Autowork fetches and updates the canonical `main` before integrating
  into it. A worktree pushed to `origin/main` while the canonical `main` stayed behind,
  and the next local integration diverged from the remote.

- A task held for a person now blocks only the tasks that depend on it, not tasks
  whose declared paths overlap its own: it reruns fresh from later code and never
  merges as is. One held sierra task with wide inferred Touches held up 34 others.
- Autowork removes finished worktrees itself. Sessions created task worktrees and
  left them after merging; 10 integrated, clean worktrees had piled up in this
  repository, and a leftover `<repo>-autowork-<task>` path also blocks parallel
  dispatch of that task. The new `worktree_closeout.py` removes a worktree only when
  its HEAD is on `main`/`master` and it is clean (regenerable caches aside),
  unlocked, not owned by a parallel slot or pi-autowork, not in use by any process
  and quiet for 30 minutes, then deletes its merged branch with `git branch -d`.
  Every `owner_cycle.py --apply` task claim runs it and reports `worktree_cleanup`;
  closeout runs it for the task's own worktree.

- A `pi-autowork` service records a changed TODO.md order itself (guarded
  `goals.py reorder`, committing only goals.json) and selects again, as scheduled
  Autowork runs are documented to do; before, it asked a person and waited. A refusal
  is reported once and never retried in a loop. Closing a task with a live follow-up
  now records the follow-up's place in the priority order; it used to leave a drift
  that stopped all dispatch (charlie, TASK-008). An engine error
  no longer ends a service: it is reported once, shown in health, and retried each
  interval, because systemd does not restart a deliberate exit.
- A `pi-autowork` service no longer quits on a failure streak. Holds that already
  existed when the runner started (for example after a self-restart) no longer count
  toward `PI_AUTOWORK_MAX_FAILURES`; three restarts re-counted the same old holds and
  stopped the charlie service. In continuous mode a real streak pauses
  new tasks for `PI_AUTOWORK_FAILURE_PAUSE` seconds (3600) instead of exiting.
- Docs Sync reports array/object role statuses as validation errors instead of
  crashing in set membership (TOOLSET-113-04). `validate`, `check` and `stale`
  retain role-specific diagnostics and continue reporting independent field errors.

- Profile consultations retain valid replies and subprocess exit verdicts when
  stderr contains malformed UTF-8 diagnostics (TOOLSET-112-29). Protocol stdout
  remains strict; malformed reply bytes are not accepted as repaired evidence.

- Pi's proposed `Touches:` insertion preserves existing TODO.md bytes, including
  CRLF and mixed line endings, Unicode and trailing whitespace (TOOLSET-111-b3).
  The inserted field follows the target `Scope:` line's newline and spacing.

- Offline test aggregation tolerates malformed UTF-8 subprocess diagnostics
  (TOOLSET-110-61). Replacement characters preserve readable output without losing
  passing/failing verdicts or sibling-directory summaries to a decoding exception.

- Docs Sync heading anchors remain unique across numeric-suffix collisions
  (TOOLSET-109-f1). Valid links and manifest fragments to later duplicate headings
  no longer fail when an earlier heading already uses their candidate suffix.

- Docs Sync anchor checks ignore HTML-commented headings and explicit anchors,
  including unclosed comments (TOOLSET-107-93). Hidden headings no longer consume
  visible duplicate suffixes or validate links to nonexistent rendered targets.

- Fleet collector evidence masks complete HTTP credential-header values before
  comma/semicolon field masking (TOOLSET-106-5d), including Cookie, Set-Cookie,
  Authorization and Proxy-Authorization tails. Native/legacy response diagnostics
  and source bytes remain preserved. Installed adoption is a separate scanned gate.

- The offline Pi idle-update regression compares runner PIDs rather than whole
  timestamped startup lines (TOOLSET-105-79). A deterministic display-minute change
  reproduces the former false failure without weakening restart identity checks.

- Offline test discovery skips symlinks in every maintained-directory component
  below the checkout root, not just the final directory (TOOLSET-104-cc). Linked
  workflow parents can no longer redirect discovery into external test modules;
  ordinary suites and checkout-root aliases remain supported.

- Fleet response evidence now validates native character-framed outputs, preserving
  opening blockers when an answer quotes a Response heading (TOOLSET-103-fe).
  The collector and consultation cache share the parser. Invalid/oversized native
  frames produce gaps; bounded legacy tails remain explicitly unverified.
  This source repair does not establish installation or worker recovery.

- Autowork receipt generation caches package parsing and interpreter hashes within
  a process (TOOLSET-072), while detecting package additions, removals, metadata
  edits and executable replacement. Uninspectable search paths and custom metadata
  providers use uncached discovery. Full serial performance qualification remains open.

- Fresh OMH installs pin v3.0.2, whose plugin manifest no longer excludes
  Hermes 0.22 (TOOLSET-082). Existing OMH executables and installed plugins are
  not upgraded automatically; native registration and existing-store verification
  remain separate. No memory provider or store is changed by the pin update.

### Added

- The `tx autowork` TUI shows worker lanes: for the selected runner, one row per task
  in flight with its phase (from the runner's own log), attempt, time and the worker's
  last action from its Pi transcript (`bash: pytest -q`, `said: ...`, and how long
  ago), plus a `Now` column per runner. `tx autowork web` serves the same TUI to a
  browser with textual-serve 1.1.3, on 127.0.0.1:8765 by default; `--view-only`
  disables every control key. Neither calls a model.

- Answering a held task is editing its TODO.md entry: when the entry no longer matches
  the contract its attempt was dispatched with, the next cycle sets the slot aside and
  runs the task fresh (`REQUEUED`), its earlier work kept on `-set-aside-N` branches; a
  removed entry is set aside without rerunning. A new runner handles held slots in its
  first cycle. TOOLSET-120-fc (1).
- `tx autowork` opens a live TUI on a terminal: every pi-autowork runner (tmux and
  service) with its state, blockers, held tasks and log, and keys to open a session,
  start or stop a runner, install or remove its service, set aside a held task and
  answer blockers. Stop, remove and set-aside ask first. Every key runs an existing
  command; nothing calls a model. It uses Textual 8.2.8 through `uv`, so pi-autowork
  itself stays standard-library Python. `tx autowork ls` also shows `entry changed`
  blockers (the engine's `contract` kind).

- `/autowork blockers [repo|name]`: an interview that resolves what blocks a
  repository's queue with the owner, one question at a time, easiest first (effort from
  the blocker's kind: quick, decision, input, investigate; then most tasks unblocked).
  It reads the runner's BLOCKERS.md block or the engine's status, records each answer
  as TODO.md planning, commits only planning files and never manages runners.

- A commit held because review failed is reviewed again, once, whenever the runner's
  reviewer changes (its code, `PI_AUTOWORK_VALIDATE` or `PI_AUTOWORK_REVIEW`), by the runner
  itself and even with no attempt left (`--parallel-reverify`, `reviewed_by`). The same
  reviewer never gets a second try. Three charlie commits the old reviewer
  failed for want of a device are re-examined without anyone asking.
- A runner reads its repository's settings file
  (`~/.config/pi-autowork/<repository>.env`, the file `--install-service` writes) whichever
  way it is started, so `tx autowork` in tmux keeps settings such as the model,
  `PI_AUTOWORK_ALLOW_HERMES` and `PI_AUTOWORK_LINK_PATHS`. The environment still wins, and a
  file naming another repository is ignored.
- A worker blocked only by files outside `Touches:` lists them in `needs_touches`;
  when the runner had inferred those Touches it widens them and the engine resumes the
  worker in its own worktree on the same attempt (`RESUMED`), so the request is not a
  failure. Touches a person wrote are never widened. Paused slots now show as
  resuming instead of failed. (sierra TASK-024, bravo TASK-005.)
- `tmux/` (copied from pi-toolset) with `tx autowork`: run a repository's pi-autowork
  runner in tmux session `pi-autowork-<repository name>` to watch or debug it,
  `tx autowork ls` to list tmux and service runners together, and
  `tx autowork stop` to interrupt one cleanly. It runs the script the systemd unit
  runs and refuses while that repository's service is enabled; the service stays the
  primary way to run pi-autowork. This `tx` is now the maintained one, installed as
  the package's `tx` command; pi-toolset's `tx` is deprecated in its favor.
- `tx autowork` takes a runner name as well as a path, shows each runner's health in
  `ls`, and adds `status` (the runner's full status) and `logs [-f]` (the service
  journal or the tmux pane) for tmux and service runners alike.
- `tx autowork ls` says what each runner is doing: its state and for how long,
  workers running, waiting and held, the held task IDs, and for a blocked or stalled
  runner the tasks or conditions it waits on (`19 wait on TASK-036: ...`). Lines fit
  the terminal width; `--brief` keeps one line per runner.
- Every pi-autowork runner opens with `tx pi-autowork-<name>`. A tmux runner attaches;
  for a service runner the session follows its journal instead of being refused, and
  closing it leaves the service running. `tx autowork ls` shows that command per
  runner instead of the repository path.
- `tx autowork ls` is shorter: blockers are grouped by kind on one line each
  (`claimed elsewhere: TASK-028 (13), TASK-014 (4)`) with short IDs and held causes
  instead of one cut-off sentence per blocker, durations read `4h41m`, and the footer
  fits the terminal.
- `tx autowork help` (or `-h`, `--help`, or no command) prints the `tx autowork`
  commands; before, `help` was looked up as a runner name.
- `tx autowork ls` prints one colored line per runner by default (green working,
  yellow blocked, red stalled or not running, also in the header counts);
  `tx autowork ls --long` shows the blockers. `--brief` still works.

- Held tasks carry a machine-readable cause (`scope`, `overlap`, `report`,
  `conflict`, `validation`, `contract_changed`, `moved`, `blocker`, `crash`, `launch`),
  shown in `--fleet` and stall announcements. A commit held only for files outside
  Touches the runner had inferred is re-verified once after the runner widens its own
  guess (`RESCOPED`), instead of a fresh retry; Touches a person wrote are never
  widened. Touches inference moved into the `pi-autowork/` component
  (`touches_inference.py`); the old script path still works. TOOLSET-115-bf phase 5.
- `PI_AUTOWORK_LINK_PATHS` links gitignored dependencies (say a vendored source
  tree) from the main checkout into each task and review worktree, only where Git
  ignores the path, and verifies the link shows up as no change; directories become
  real directories of links because Git does not treat a symlink as a directory. The
  link is cooperative, not write-protected. sierra TASK-022 stopped twice on a missing
  ignored source tree.
- Self-update waits for a safe checkpoint: no runner on the machine has work in flight,
  and the new release, read from Git before installing, declares it can read the
  current execution state (`STATE_SCHEMA_READS` in the engine). Otherwise the update
  is deferred with the reason, logged once, and the running release stays.
- Parallel Autowork can adopt another session's `in_progress` claim once it is
  verifiably idle (`--adopt-idle-claims SECONDS`): its TODO/ledger entry, any branch
  or worktree named for the task and any agent process there all show no activity
  for that long, and no active session is in the canonical checkout. Prior work is
  never changed; the worker's prompt names it for reuse and the journal records the
  evidence (`claim_adopted`). `pi-autowork.sh` adopts after 6 hours
  (`PI_AUTOWORK_CLAIM_IDLE`, `0` never). Before, claims left by handed-off sessions
  blocked most of the sierra and bravo queues indefinitely.
- Runner health (TOOLSET-115-bf phase 3): each `pi-autowork` runner keeps a
  `status.json`, announces a stall once at warning priority with its root blockers,
  and `pi-autowork.sh --fleet` lists every runner's service, health and blockers;
  `--status` shows the same for one repository. The engine's waiting entries now
  name what holds them (`blocked_by`) and `--parallel-status --json` lists the
  `roots` of each waiting chain (held task, claim, outside condition, cycle or
  moving work). This is the first module of the `pi-autowork/` component, which
  now ships in the package together with the previously omitted Touches helper.
- `pi-autowork.sh --set-aside TASK` asks the repository's running runner, which holds
  the engine lease, to retire a stuck slot (`--parallel-set-aside`) within one cycle;
  no service stop, so live workers are not interrupted.
- Fleet collection retains up to twelve recent execution records per existing job,
  so frequent sync runs cannot evict paused development-job evidence from a
  profile-wide window. Removed jobs stay excluded; metadata remains read-only and
  does not establish output/run association, stagnation or worker recovery.

- `scripts/pi-autowork.sh` runs as many independent tasks as it can: `--workers`
  defaults to 8 (the engine limit) and free memory (3 GB per worker) and load decide
  how many start. For runnable tasks without `Touches:`, a read-only Pi pass proposes
  file paths and the runner records them, so they can run beside others instead of
  alone; `NONE` keeps a task solo for 24 hours. An idle session now merges the main
  branch rather than only fast-forwarding.
- `scripts/pi-autowork.sh` now drives the toolset's Parallel Autowork engine instead of
  picking tasks itself: up to `--workers N` (default 2, at most 4) Pi workers run
  independent tasks in their own worktrees, the engine merges each into the session
  branch, a separate read-only Pi review (after optional `PI_AUTOWORK_VALIDATE`) must
  pass before a task closes, and the session merges into the main branch at the end.
  `--status` shows each task as pending, running, implemented, verifying, integrated,
  done or failed. `PI_AUTOWORK_MAX_COST` now counts a rolling window
  (`PI_AUTOWORK_COST_WINDOW`, 24 h) across restarts and workers. With `--allow-hermes`
  the engine's lease keeps Pi and Hermes Autowork from owning tasks at the same time.
- `scripts/pi-autowork.sh` runs Autowork through the Pi coding agent one task at a time
  until stopped: it takes the next task from `goals.py next` (an empty queue costs no
  model call), runs Pi on GPT-6.1 Sol and falls back to DeepSeek V4.1 Flash on provider
  errors, confirms completion from `goals.json`, resumes interrupted tasks, holds one
  lock per repository and blocks pushes. It runs from the main branch, gives each task
  its own worktree off a session integration branch, and merges the session into the
  main branch when the queue empties or it stops (Pi resolves a conflicting merge once;
  otherwise the merge is reported pending). `--install-service` runs it as a systemd
  user service per repository (`pi-autowork@<repository name>`), stopped gracefully with SIGINT. See
  [continuous Autowork](docs/cross-host.md#run-autowork-continuously).
- Opt-in parallel Autowork (TOOLSET-085-1a to 090-2d): `/autowork --parallel N`
  runs independent tasks in headless Hermes, Codex or Pi workers, each in its own
  worktree, admitted by the tasks' new `Touches:` and `Resources:` fields. The
  coordinator merges and validates one worker branch at a time, only fast-forwards
  the canonical checkout, and closes a task only after validation. Claude Code
  coordinators need `--worker-command`; otherwise, and when a worker CLI is
  missing, Autowork runs the task sequentially as before. Sequential output is
  unchanged. Documented in
  [parallel workers](skills/autowork/references/parallel-workers.md); real model
  workers are not yet qualified (TOOLSET-091-00).
- Parallel Autowork progress via `owner_cycle.py --parallel-status [--json]`,
  with journal-derived elapsed/worker/integration/waiting metrics and a controlled
  fake-worker ABC benchmark (`scripts/bench_parallel.py`). Offline regressions
  cover concurrent independent workers and dependency-after-close ordering
  (TOOLSET-089-72); real host qualification remains separate.
- Parallel retry refill enforces worker deadlines before waiting. Task closure and
  cleanup verify the validated contract even when its checkbox was checked or its
  body was already archived; changed acceptance refuses closure.
- `/toolset update status` and `hermes toolset doctor` list profiles whose plugin links
  to a working checkout, which load its current files at any gateway restart.
  `hermes toolset pin NAME [--dry-run]` replaces one link with a clone at
  the same revision that only updates advance, saving the link; `--unpin` restores it
  (TOOLSET-079). Nothing is converted automatically.
- New task IDs end in a two-hex-digit hash after the number, such as `TOOLSET-084-a7`,
  so collaborators adding tasks on separate clones no longer create two tasks with the
  same ID. `goals.py new-id <repo>` allocates one (next number for the ledger's most
  common prefix, checked against TODO.md and its archive), and `goals.py add-task`
  allocates one when the ID is omitted. Existing IDs are unchanged.
- In profiles with OMH, plugin load (and so `/toolset update`) adds the OMH skills
  outside a measured keep list (`omh_keep_skills`, 41 of 142, including code review,
  verification, core and memory skills) to `skills.disabled`, so Hermes stops listing them
  in every prompt (TOOLSET-080). User entries stay, OMH and its memory provider are
  untouched, and setup no longer empties `skills.disabled`.
- Telegram's command menu now lists `/ui_taste`, `/beautify_github_readme`,
  `/impeccable`, `/lgtm`, `/engineering` and `/git_commit_push` after the five workflow
  commands. Hermes' default 60-entry menu was already full of built-ins, so they were
  registered but never shown; the same number of lowest-ranked built-ins move off the
  menu and still work when typed.

- `scripts/check.py` runs its test directories concurrently, cutting a full offline
  run from 242 s to about 165 s on the same machine (TOOLSET-069). Output stays whole
  per directory and in the usual order; `--jobs 1` keeps the sequential run.
- Engineering protocol `test-suite-optimization` (`route.py --protocol
  test-suite-optimization`): measure a suite's time and per-test coverage, find
  duplicate, subsumed, slow or low-value tests, and record each consolidation or
  speed-up as its own task whose acceptance keeps coverage and mutation score
  (TOOLSET-067). It is toolset-written, selected only with `--protocol`, and cannot
  shadow a pinned protocol.
- Claude Code plugin: `claude plugin marketplace add TrebuchetDynamics/hermes-toolset`
  then `claude plugin install hermes-toolset@hermes-toolset` exposes the 13 portable
  adapters as `/hermes-toolset:<skill>`. Only the adapters load; the Hermes-only root
  skills, hooks and settings do not. All adapters are now explicit-only in Claude
  Code and Pi (`disable-model-invocation: true`), matching Codex.

- Install, update and every plugin load set `agent.max_turns: unlimited` in each
  profile (unless it opted out of runtime defaults), so long Autowork and chat turns
  are no longer stopped at a per-turn iteration cap such as the `90` Hermes quick
  setup writes.
- Uizze's UI Taste skill (v0.2.0) is bundled as `/ui-taste` (`/ui_taste` in
  Telegram): an unmodified, Apache-2.0 snapshot pinned to Uizze commit `afd703a`
  with per-file hashes. It works offline; its optional paid Uizze MCP is never
  configured by Toolset. Codex (explicit-only) and Pi (`/ui_taste`) expose it too.
  The pinned files sit under `upstream/` behind a toolset adapter with a short
  trigger for Hermes' skill index, one-design-skill-per-task precedence with
  Impeccable, read-only scheduled runs, and paid Uizze tools only through an
  existing host connection.
- `/beautify-github-readme` (`/beautify_github_readme`): oil-oil's MIT-licensed
  Beautify GitHub README skill, vendored byte-exact at `d6562a5` with file hashes,
  behind a toolset adapter (scope first, README claims stay Docs Sync facts, pure SVG
  by default, no unsolicited attribution or showcase offer). Codex and Pi adapters
  included. Its README audit also catches missing dark-mode `<source srcset>` and
  reference-style images and resolves root-relative paths as GitHub does.
- A held or blocked Autowork task now goes to Plan For Me in the same run, which must
  fix it (reversible in-scope change, recorded as the planner's call) or skip it
  (split the blocked acceptance into its own open task and continue with the next
  ready task). Only genuinely unavailable external inputs are reported, once. The
  rule is in the managed cron block, so existing jobs adopt it at their next
  self-heal.

- `/toolset update` merges edits profiles made to their installed skill copies
  instead of stopping on `drift`. It merges from the closest same-path version in
  trusted history (keeping a pure addition over the release), reports each file under
  `local_edits`, and still stops before any write on a conflict or an ambiguous
  starting version.

- Docs Sync's optional document role manifest (`docs/roles.json`) and read-only
  `skills/docs-sync/scripts/docs.py validate|check`: mapped documents and anchors,
  local links, documented script paths, covered paths and unmapped baseline roles.
  `docs.py stale` lists roles whose covered paths changed after their
  `verified_at` commit. An optional repository-type `profile` (service, library,
  cli-plugin, application, infrastructure) sets the baseline roles, adding reference,
  install/upgrade, troubleshooting and user-guide baseline roles; the scaffold also
  documents a glossary role. Repositories
  without a manifest are unaffected.

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
  folder (a same-named script without the bundle marker is never replaced; the
  plugin logs a warning), and `/cron_autowork` attaches it; the finished report
  remains Hermes' normal cron delivery.
- `/cron_autowork` with a cadence resumes the matched paused job on that cadence
  (for example `/cron_autowork 5m`), unless the request says to keep it paused.
  Multi-profile refreshes and repairs still never resume a job.

- TODO.md order is the enforced human priority. goals.json records a versioned
  `priority_order`; selection ranks focus, section, recorded order, then goal
  priority. `goals.py next`, direct selection, backlog checks and retry selection
  share one guard: selection returns `PRIORITY_DRIFT` instead of the stale pick, and
  `backlog-check` reports drift as an ineligible reason.
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

### Changed

- The pi-autowork runner is now Python in the `pi-autowork/` component (`cli.py`,
  `coordinator.py`, `worker.py`, `service.py`); `scripts/pi-autowork.sh` shrank from
  about 1,200 lines of Bash to a 35-line entry point that finds the component. Options,
  output, exit codes, state files, the service unit and the engine contract are
  unchanged, and a run continues in the component of the toolset release it resolves,
  so runner and engine never mix releases. Retried tasks are now logged and counted as
  started workers (the Bash loop missed them). TOOLSET-115-bf phase 5.
- `pi-autowork.sh` runs Pi jobs through the component's `pi_runtime.py` instead of its own
  Bash: the same model choice, fallback, retries, timeouts, budget and redacted records,
  now unit-tested. The runner requires the component from the toolset release it
  resolved and exports its path, so workers and copied launchers use the same code.
- Parallel Autowork backfills: a lower-priority task starts past a higher-priority
  one that cannot start yet when it shares no path, resource or dependency with it.
  Before, one blocked task (on sierra, behind another session's `in_progress` claim)
  held back every task below it. A task that must run alone and waits on running
  work still stops lower-priority dispatch so the pool drains for it.

- `pi-autowork.sh --install-service` names units after the repository,
  `pi-autowork@<name>.service` (for example `pi-autowork@sierra`), with the path kept in
  its environment file; a unit named after the escaped path by an earlier release is
  replaced, and a name already used by another repository is refused.
- `/toolset update` no longer restarts the gateway in the middle of a chat turn. It
  restarts at once only when no chat or API turn is in flight; otherwise it reports
  `gateway_restart: deferred` and a detached waiter restarts at the first quiet
  moment within 6 hours, recording `requested`, `reloaded` or `deferred_expired`.
  It never relies on Hermes' forced drain; cron runs, which Hermes keeps in
  restart-safe workers, do not hold the restart. Updates applied while a restart is
  outstanding join it, so a burst of updates restarts the gateway once
  (`gateway_restart_covers`), and the waiter never restarts mid-update. After the
  restart, `/toolset update status` records `completed` with the new gateway PID,
  which Telegram bots resent their menus and any forced-drain interruptions, or
  `restart_failed` if the old gateway is still running. A second update or check
  started while one runs reports `busy` with that update's PID, mode and start
  (exit code 3; in chat it starts nothing) instead of a bare "already running", and
  no longer mistakes the waiter's brief lock for a running update.

- `git-pull-merge` is merged into `git-commit-push` (2.0.0): `/git-commit-push pull`,
  `sync` or `merge <branch|PR n>` runs the former pull and merge procedure, now a reference
  inside the skill, with its two helper scripts. The `/git-pull-merge` command is retired
  in Hermes, Codex, Pi and Claude Code (12 portable skills, 26 Pi commands), removed from
  Telegram menus, and `/toolset update` deletes unedited installed copies from profiles.
- `/git-commit-push` syncs by default (2.1.0): after committing it fetches and merges the
  upstream (fast-forward, else a merge commit; never rebase or stash), re-runs checks on
  the merged tree, then pushes. `no pull`, `no sync` or `ff-only` keeps the old
  push-first behavior; a pull with nothing to commit reports SYNCED.

### Fixed

- `pi-autowork.sh` never resets or cleans the session checkout any more. The Touches
  pass reads a disposable detached worktree that is removed afterwards; when
  validation or review leaves changes in the engine's integration worktree, the
  engine saves them as a patch under `autowork-execution/integration-residue/` and
  resets only that journaled, lock-held worktree (before, a tampering reviewer
  wedged every later integration unless the runner reset it). Closing commits
  exactly the files the close wrote (`files` in the `CLOSED` result) instead of
  every modified Markdown file.
- Parallel Autowork reads a worker's report instead of guessing from its process. A
  worker that stops with `blockers` is held for a person (`cause: blocker`) and is
  neither resumed nor retried; before, a deliberate stop looked like a crash and
  used up both attempts on the same wall (sierra TASK-022). Device, production,
  hardware and human checks go in the report's new `pending_live` field, which no
  longer holds offline work that passed (flutter TASK-013, held twice); closing
  the task records them once as `TASK-LIVE` under Needs decision.
- A held task with no attempt left no longer stalls the whole queue. It now blocks
  only its dependents and tasks whose declared `Touches:` or `Resources:` overlap it,
  like an `in_progress` claim, and its files no longer hold other work at
  integration. Before, one such hold kept all four fleet runners idle for seven hours.
- `Dependencies:` lines count task IDs, not the words around them: `none for this
  slice`, `T-1; not eligible until done` and `RD-8; goal gates: G1` no longer wait
  on "for", "Section" or "G1". A line that names no task still blocks.
- `owner_cycle.py --parallel-set-aside TASK` retires a slot that can never finish:
  an exhausted hold, or an integrated task whose TODO entry was rewritten after
  validation. Its worktrees and branches are kept, renamed `-set-aside-N`, and the
  task dispatches fresh. `pi-autowork.sh` does this by itself when a merged task's
  entry changed, instead of retrying the close forever.
- Parallel Autowork no longer holds every task without `Touches:` at integration: a
  task dispatched alone may change its own files (coordinator files and other
  slots' files still conflict).
- A task held for changing files outside its scope, whose fresh retry then made no
  commit, now has its first commit verified once more (`READOPTED`) instead of
  staying held: such retries usually decline to redo work the hold called out of
  scope, which stranded completed work after the scope rule was fixed.
- A continuous `pi-autowork.sh` restarts itself when its toolset is updated, instead
  of running the old script against the new engine (which exited on an engine
  outcome the old script did not know).
- Parallel Autowork closes tasks whose ID is bold or code (`- [ ] **T-1 — …**`): the
  checkbox stayed unchecked, so the task never archived. The engine also resolves the
  TODO archive as Docs Sync does (a linked `docs/TODO-archive.md`, never a task's own
  "history" link), for closing and for dependencies on archived tasks.
- `pi-autowork.sh` retries closing an integrated task on later cycles and commits a
  linked archive with the close; a failed close no longer blocks the queue.
- A deliberate stop or restart of Parallel Autowork (Ctrl+C, `systemctl stop` or
  `restart`) no longer costs a task its retry: the coordinator marks live workers
  paused (`--parallel-pause`) before interrupting them, and each resumes in its
  worktree on the same attempt. Before, an interrupted second attempt was held for
  good. A held or interrupted slot whose task is done or superseded no longer blocks a
  must-run-alone successor.
- Closing accepts a live task an earlier close left half-closed (`Status: done`, box
  unchecked) instead of refusing it as a changed contract.
- A continuous `pi-autowork.sh` also keeps itself current: while idle, at most hourly
  (`PI_AUTOWORK_UPDATE_INTERVAL`), it runs `pi update` for its toolset package, one
  runner at a time, and skips a restart onto a script that does not parse. Its
  `Touches:` pass no longer answers `NONE` for tasks that are verified on a device or
  screenshot harness, asks again after a prompt change, and retries a pass that gave no
  answer within the hour instead of a day.

- Parallel Autowork no longer lets an idle `in_progress` claim without `Touches:` stop
  every other task: such a claim is not dispatched and still blocks its dependents and
  declared overlaps, but unrelated tasks run. On sierra, 32 handed-off claims had left
  the Pi runner with nothing it could start.
- Parallel Autowork names the processes behind a "live or unknown external writer" hold
  (PID, name, checkouts touched, evidence), tells workers to report each check's final
  result only (a listed early failure held the task), and returns `SEQUENTIAL_FALLBACK`
  for Codex workers, which live qualification showed cannot commit inside Codex's
  workspace-write sandbox.
- Parallel Autowork no longer holds a worker that was interrupted or released and then
  restarted: integration expected the `-r2` branch of a held retry, so every restarted
  task failed with `unexpected worker branch`. Found while qualifying `pi-autowork.sh`.
- A gateway restart's outcome no longer disappears when another update runs before
  anyone reads the status: it is kept in `restart.json`, recorded by the next update
  before that replaces the receipt, and shown as `Last gateway restart` (TOOLSET-092-f2).
  Finishing a restart also keeps an update that joined it meanwhile.
- `/toolset` now replies with a short, actionable overview: bundle version, revision and
  profile, the workflow commands that are ready, the last update, other plugins' status
  and counts, and anything that needs setup with the command to fix it. The four lines
  of capability caveats are gone from the reply (the docs keep them).
- `/toolset update status` replies with a short summary (outcome, revisions, files
  written, local edits, healed settings and menus, gateway restart) instead of the whole
  JSON receipt, which Telegram had to split across several messages.
  `/toolset update status full` still returns the receipt.
- `/toolset update` now removes skills retired from the bundle (such as
  `git-pull-merge`) from profiles whose plugin is the shared checkout. It used to compare
  only the checkout's before and after revisions, which match when the checkout had
  already advanced, so retired copies stayed installed. Unedited copies and the folders
  they leave empty are removed; edited ones stay and are reported as `kept_retired`.
- `/toolset update` no longer looks like it skipped the gateway restart. A graceful
  restart waits for in-flight chat turns (up to 30 minutes by default); `/toolset
  update status` now shows `gateway_restart_progress` with the time left and the turns
  it is waiting on, and an update during that wait reports `pending` instead of
  starting a second, overlapping restart.

- `/toolset update status` reports a finished, refused or killed chat-started update
  correctly instead of "starting"/"running" forever, and a symlinked Hermes home
  can update from chat (TOOLSET-048).
- Setup accepts configs Hermes writes (indentless lists, `{}`, a BOM, empty sections)
  and ignores profile symlinks Hermes does not treat as live (TOOLSET-049).
- Telegram menu healing reads `.env` values like python-dotenv, skips malformed chat
  IDs and keeps healing the remaining chats when one fails (TOOLSET-050).
- `docs.py check` no longer flags footnotes, commented-out links or `~/` script paths,
  keeps underscores in code-span heading anchors and checks single-quoted link titles
  (TOOLSET-051).
- The cron self-heal helper reported its own refusals only as `ValueError`, hiding
  the cause (for example a job whose prompt lost its managed wiring). Its fixed
  refusal messages are now shown; other errors still report only their type.
- Autowork no longer refuses runnable tasks because of loose checklist lines elsewhere
  in TODO.md or `Dependencies: None.` followed by prose, and its writer detection now
  recognizes the installed `hermes` launcher (TOOLSET-043, TOOLSET-044).
- Setup honors `apply_runtime_defaults: false`: an opted-out profile keeps its own
  approval, injection and skill-list settings (TOOLSET-045).
- One incomplete native skill folder in a profile no longer stops the plugin from
  registering every command; it is logged and preserved (TOOLSET-046).
- `goals.py` accepts CRLF and trailing-space section headings, and `render` no longer
  deletes content after a legacy Goal coverage section (TOOLSET-047).
- Archiving a closed task no longer leaves an extra blank line at the end of
  `TODO.archive.md`: the separator before the next heading is not archived, so
  `git diff --check` passes after an ordinary closeout (LF and CRLF preserved).

- The Cron Autowork Codex adapter is explicit-only like the others; it shipped no
  `agents/openai.yaml`, so Codex could invoke it implicitly.

- `scripts/check.py` allowed 180 seconds per test directory while the Autowork
  suite takes about 150 seconds idle, so any machine load reported a false
  TIMEOUT failure with every test passing. The default is now 600 seconds.
- OMH setup reports `memory off` for a profile where another memory provider
  kept the slot (with the `hermes memory off` command to clear it) or the slot
  stayed unset, instead of printing a plain success line while OMH memory stayed off.

- Autowork accepted only `Checks:` as a task's verification field, while Docs Sync
  and `goals.py next` also accepted `Verification:`. Every task in one fleet
  repository used `Verification:`, so its scheduled job selected tasks and then refused them all.
  `Verification:` is now an accepted spelling (one of the two per task).
- `tests/integration_autoresearch.py` still expected `/autoresearch_*` aliases in
  the Telegram menu after they were deliberately unadvertised.
- Setup and update verification honor the documented runtime-policy opt-out
  (`plugins.entries.hermes-toolset.settings.apply_runtime_defaults: false`), so an
  opted-out profile with its own approval values is no longer reported as
  `incomplete`. The native registration probe's opt-out now uses the same path.

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
