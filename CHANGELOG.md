# Changelog

Notable implemented changes. Commit references identify source history, not a
claim of a tagged release, completed installation or live workflow qualification.

## Unreleased

### Changed

- A runner reuses one engine status snapshot for up to 5 seconds and drops it whenever it runs an
  engine command. Each status read was a new engine process (1.5 to 3.6 s of CPU), about 10 per
  30 seconds per runner: 3 to 5 cores across a fleet of 7 runners on a host already at full load.
- A runner commits the owner's quiet planning files (`TODO.md`, `goals.json`, `BLOCKERS.md`, the archive)
  even while other files in the main checkout are uncommitted, leaving those for the next merge. A
  repository whose `TODO.md` was untracked beside edited docs never gave its runner a plan.
- A service installed from the TUI no longer saves uv's temporary environments in its `PATH`; uv
  deleted them later and the runner exited on a `python3` that no longer existed.
- A runner on a Git submodule places its worktrees in the submodule's checkout. `git worktree list`
  names a submodule's Git directory (`.git/modules/NAME`) as its main worktree, so the session worktree
  was created inside it and main-checkout sessions were not recognized.
- Profiles that opted out of the runtime defaults (`apply_runtime_defaults: false`) still get the
  bundle's Telegram menu entries: every profile had opted out, so `/blockers` was in no bot's menu.
  Their approval, turn, injection and skill settings stay their own. `/autowork update` also deepens
  a shallow plugin clone (a pinned Hermes install) instead of stopping on its fast-forward check.
- `/autowork update` keeps a profile's skill file that it edited and that conflicts with the release,
  reports it by path (`Not updated, the profile edited them…`) and updates everything else. One
  profile's conflicting `blockers` skill stopped the whole update, so no profile received releases.
- `scripts/check.py` runs each test module in its own process, as many at once as the host has idle
  CPUs (4 to 8), and spreads the runner suite over several processes: the full check takes about
  3 minutes instead of 15. Tests no longer inherit the runner's own `PI_AUTOWORK_*` settings.
- A runner busy with its own Pi job (DOCS-MAINTAINER, toolchain provisioning, merge resolution) says so:
  `autowork ls` and the runner view show it working on that job instead of `not cycling`, which its
  stale status read as while the loop waited (TOOLSET-177-d0).
- A repository can declare its full offline check (`PI_AUTOWORK_MAIN_CHECK`). The runner runs it on
  main in the background, once per main revision, when the host has room; a red result names the
  failing tests and the commits since the last green main, and the DOCS-MAINTAINER adds one repair
  task first in Now. Status and the runner view show `main red since <commit>: N failing`
  (TOOLSET-176-98). Main is green again after the `/pending` landing: its skill has a SKILL.md and
  its query uses the shared priority guard (TOOLSET-175-2b).
- Each runner has a DOCS-MAINTAINER: when nothing runs and tasks are held for a planning cause or are not
  runnable as written, one Pi job restates them from the repository's own evidence, in a disposable
  checkout; its commit merges only if it changed planning files alone and `goals.py validate` passes. One
  run per distinct trigger set, none without a trigger; status and the runner view show its last run
  (TOOLSET-164-f1, first slice).
- A review that could not run for a missing tool says so (`fail environment — <missing>`); the runner
  installs it into `$AUTOWORK_CACHE` from the repository's setup docs and reviews the same commit once
  more, and such holds do not count toward the failure pause (TOOLSET-173-94).
- A task that must run alone drains the pool only after it has waited beside running work for
  `PI_AUTOWORK_DRAIN_AFTER` seconds (default 1800, kept across restarts from the journal); until then
  independent work keeps starting, and waiting tasks then say `draining, waited Nm` (TOOLSET-171-35).
- The memory gate needs room for one more worker only (twice `PI_AUTOWORK_MIN_FREE_MB`), however many
  run, and each runner removes `/tmp` scratch that nothing has used for two hours
  (`PI_AUTOWORK_TMP_STALE`, at most every 30 minutes per host): the double-counted reservation and
  39 GB of leftover copies had capped runners at two or three workers (TOOLSET-162-d2).
- A person's session in the main checkout no longer keeps finished work from closing unless it is
  editing TODO.md, goals.json or the archive; only failures that point at something systemic (a
  crash, an empty run, a launch or a failed review) count toward the one-hour failure pause.
- A runner-inferred Touches list a person edited since still gets the bounded widening, and a
  Touches placeholder such as `migrations/<new migration>` means new files under `migrations/`.
- A review no longer prunes every stale worktree registration in the repository. It unregisters only
  the scratch worktrees it made under its own `$TMPDIR`, so a session worktree the runner restores,
  or anyone else's registration, survives the review.
- Auto work no longer pins a submodule to a commit its remote does not have, or adds an untracked
  nested repository as an embedded one; it leaves that path uncommitted and says why once
  (TOOLSET-168-ff). Workers and reviewers share one toolchain cache per repository,
  `$AUTOWORK_CACHE` (`<git common dir>/autowork-execution/cache`), so an SDK one task installs is
  there for the next task and every review (TOOLSET-169-1d).
- Runners pick up a new release sooner: they check for one every 2 minutes while idle
  (`PI_AUTOWORK_UPDATE_INTERVAL`, was 10 minutes) and install a release that has waited
  10 minutes for every runner to be idle (`PI_AUTOWORK_UPDATE_WAIT`, was 30 minutes).
- `install.sh` no longer writes through a symlinked `~/.local/bin/tx` into the file it points at;
  the link is moved aside. Replaced files keep every earlier backup (`.bak`, `.bak.1`, …).
  `--no-reload`, `--bundle-only` and `--yes-deps` fail the Hermes item when profiles have their
  own plugin clone (updated by `update_bundle.py`, which cannot honor them) instead of being
  dropped. A Pi package listed as `(filtered)` counts as installed, so `autowork` links to the
  package rather than the checkout. Hermes without a Hermes home is unavailable, not a failed setup.
- Reviews no longer fill RAM-backed `/tmp`. Each review gets its own `TMPDIR` on disk, removed when it
  ends, and reviewer and worker prompts say to keep scratch and copies under `$TMPDIR` (a scratch
  checkout as `git worktree add --detach`) instead of copying whole repositories into `/tmp`.
- The runner view answers whether a runner is stuck and why, and what each worker is doing. A
  verdict line comes first (`Working — 3 of 8 workers busy`, `Waiting on you — …`, `Stuck 42m — <root>`,
  `Host busy — …`, `Restarting onto <commit>`); worker rows say in plain words what each is doing, flag
  `quiet Nm`, and Enter shows a worker's last actions; waiting tasks are grouped by cause (the runner
  writes `waiting_groups` to status.json); the log shows the last hour with each restart as one line
  and repeats counted; panes redraw only when they change. A self-update shows `restarting`, not
  `not running` (TOOLSET-166-b4).
- A validation that passes is not failed by build daemons it leaves behind. Gradle, Kotlin and Flutter
  daemons outlive a build by design; they are still killed at the boundary, and the integration tree
  is still checked, but a run that exited 0 with unchanged inputs now counts as passed. Holds an earlier
  release made this way are offered to integration once more.
- The reviewer can use what the worker provisioned. A task's docs placed its pinned SDK under the
  worker's `$TMPDIR`; the reviewer had its own and failed every check for want of it. The review prompt
  now names the worker's `$TMPDIR` (also `AUTOWORK_WORKER_TMPDIR`) for read-only use, and the changed
  reviewer re-verifies such holds once. Integration also accepts an abbreviated commit in `report.json`
  and says what differs when a report really mismatches.
- More workers run at once. A task touching a manifest, lockfile, migration or CI file
  used to run alone, and while it waited it stopped every lower-priority task, so most
  runners used one of their eight workers. It now runs beside independent work and only
  never beside other serial work; only a task without Touches or with an exclusive
  resource still runs alone (TOOLSET-160-df).
- An interrupted task resumes before fresh work on its files and owns them until it does,
  and a commit held for overlap owns nothing while it waits and is offered again once its
  files are free, so two tasks no longer hold each other for good (TOOLSET-157-cd).
- A worker that needs one to three exact files outside Touches a person wrote no
  longer waits for the owner. The runner adds those files to the task's Touches once,
  notes it in the entry, and resumes the worker in its worktree (or verifies its commit
  again). Globs, directories, coordinator files, files another live or held task
  declares, more than three files and a second request still become a question
  (TOOLSET-152-d4).
- A Touches list ending in a sentence period is read without the period, and a task
  whose Touches stay invalid waits alone instead of stopping the whole engine
  (TOOLSET-148-88). A git command that outruns its timeout on a loaded host is reported
  as `host busy`, not as an engine fault (TOOLSET-159-30). `scripts/check.py` allows
  1800 s per test directory (was 600).
- Runners update Pi's autowork package on their own again. The update waited for a
  moment when no runner on the machine had work in flight; with four busy runners that
  never came, and none had updated for hours. A new release now waits for that moment
  at most `PI_AUTOWORK_UPDATE_WAIT` (default 30 minutes), checked every 5 minutes, then
  installs anyway when it can read the current state; each runner restarts onto it and
  adopts its workers. Releases are checked every 10 minutes (was hourly).
- `install.sh --full` installs every available item without the menu (`--all` still
  works) and shows live progress (`[n/total]` per item, each command), colors on a
  terminal, a timed summary and the real failure output.
- `/blockers` filters before asking: established answers and routine recovery (an idle
  reviewed candidate awaiting integration, a failed check) become planning repairs for
  the runner; only missing product intent, scope changes, unavailable inputs or
  ungranted authority become picked questions.
- A runner's log is its events: a restart no longer prints every earlier result again,
  and waiting tasks get no `pending —` line each (the one `No task can start now` line
  covers them). The `autowork` TUI log drops systemd's unit lines and the start banner,
  shows a start or stop as one rule line, and colors results; the detail names a
  `PI_AUTOWORK_TOOLSET` override, which runs a checkout instead of the Pi package.

- `/blockers [repo|runner]` is the owner's blockers command in Hermes, Claude Code
  (`/autowork:blockers`), Codex and Pi: it starts at once with one question per
  blocked task, easiest first, answered by picking one of two to four plan changes
  (Hermes `clarify`, Claude Code `AskUserQuestion`), and plans a task that needs it
  with Plan With Me before the next. `/autowork blockers` and `/plan_with_me blockers`
  route to it in code; a Hermes `/autowork blockers` had reached the Autowork skill,
  which launched a repair session instead of asking (india). `autowork blockers`
  opens it in claude or pi.
- pi-autowork runners land and push their work (owner decision, 2026-10-16): after
  each closed task the session merges into main, Pi resolving a conflict with the
  owner's newer plan once per main revision (it was once per runner process, so a
  second conflict left the session planning from a stale TODO.md), and main is pushed
  to its upstream, fast-forward only, with one fetch-merge-retry on rejection. A merge
  that cannot land shows as the runner's blocker. Workers still cannot push;
  `PI_AUTOWORK_PUSH=0` keeps main local.

- A shared **test budget** keeps tests few and thin: one behavior change adds or extends
  at most one test at its public seam (a bug fix, one regression test), none for docs,
  config or renames, and focused tests while working instead of the whole suite after
  every edit. Pi workers get it in their prompt; the reviewer no longer asks for tests
  beyond the acceptance and fails changes that mostly repeat existing cases. Planned
  `Checks:` name focused commands, never a test count. A suite past the budget (normal
  check over 10 minutes, test modules past about 1,000 lines, near-duplicate tests)
  gets one `test-suite-optimization` audit task, which now starts with a cheap quick
  pass before any per-test coverage.
- `autowork start` moves a service onto the Pi package installed from
  `git:github.com/TrebuchetDynamics/autowork` when its unit runs another copy, such as
  the package still installed under the old hermes-toolset name: it reinstalls the
  shared unit from that package and restarts the service (workers pause and resume);
  the other services follow at their next restart, and the command names them.
- The `autowork` TUI stacks the runner table, detail, worker lanes and log full width
  (the side-by-side split left a 30-column pane on an 80-column terminal). Each runner
  shows what it needs: the owner's open questions, read from the session's BLOCKERS.md
  before it merges, else its first blocker. The detail lists the easiest questions,
  one line each, and the log leaves out the per-task `pending —` lines.
- Renamed from hermes-toolset to **Autowork** (0.3.0), with no compatibility layer:
  the GitHub repository `TrebuchetDynamics/autowork`, the plugin in Hermes, Claude Code,
  Codex and Pi, its command namespace (`/autowork:plan-with-me`, skills `autowork:NAME`),
  its Hermes settings key (`plugins.entries.autowork`) and the maintenance commands:
  `/toolset …` is now `/autowork update|status|list` and `hermes toolset …` is
  `hermes autowork …`. Other `/autowork` arguments still run the next task. Existing
  installations must be removed and installed again; see
  [the rename note](README.md#renamed-from-hermes-toolset). TOOLSET-121-3d.

### Fixed

- Auto work commits and merges all work: before each merge the runner commits whatever
  is left uncommitted in its session worktree, and in the main checkout it commits every
  quiet change no process holds open (not only planning files); untracked files that
  look like secrets stay untracked. bravo's session had refused every merge for
  hours over a failed close's uncommitted TODO.md edits ("conflicts with main in: .").
- A task close is all or nothing: a close that fails after writing TODO.md, goals.json
  or the archive restores them and stays retryable. Its read-back checks that the task
  moved to the archive instead of comparing bodies the archiver and the contract parser
  cut at different headings, which failed TASK-010's close.
- A worker that wrote no `report.json` is held as that, not as "pending_live must be a
  list of strings", and `pending_live` in any shape (a string, objects, empty entries)
  becomes its text instead of holding a finished commit and rerunning the task (india
  TASK-011).
- The TUI runs pause, stop, restart, start and model changes in the background and
  reports when they finish. They ran on its event loop, so a restart, which waits for
  the runner to stop gracefully (30 s for bravo, up to 150 s), froze the whole
  TUI as if it had crashed.
- With both packages installed in Pi, the runner runs from the one installed from
  `git:github.com/TrebuchetDynamics/autowork`; it took the first Autowork package Pi
  listed, the copy under the old hermes-toolset name, so services moved onto the
  renamed package still ran the old one.
- `autowork ls` and the TUI label a TODO entry the engine cannot run as written
  `not runnable`; they said `entry changed`, which reads as a rerun already pending.
  A runner whose worker or reviewer acted in the last 10 minutes shows `working`: the
  status written before a long verification had kept it `stalled` (sierra TASK-026).
- A plan commit made while a runner's cycle ran (its scan, merge or session cleanup)
  ends the following wait; the plan watch compared against the start of the wait and
  missed it until `--interval` passed (india).
- A runner whose remaining tasks all wait (on the owner, a dependency or the resource
  gate) merges its session into the main branch while it waits, so the owner's
  questions in BLOCKERS.md and finished tasks reach the repository; they had stayed on
  the session branch until the queue emptied (india, for hours). A merge that cannot
  happen is retried only once the session, the main branch or its checkout changes.
- A held task's `-r2` retry that a runner stop paused and the next start resumed is
  verified on its `-r2` branch; the engine had held it as "unexpected worker branch"
  (sierra TASK-026). A commit an earlier release held that way is offered for verification
  again once.
- A pi-autowork service that finds another runner holding its repository (an old tmux
  runner, a manual run) waits for that runner to exit instead of exiting 3, which
  systemd never restarts; bravo's service had stayed down after its tmux runner
  ended. Interactive and `--once` runs still exit 3.
- `autowork ls` and the TUI say `paused` only for a service paused with `autowork
  pause` (which now leaves `<name>.paused` beside its settings file; `resume` and
  `start` remove it). Any other stopped service shows `not running`.
- An active agent session in the main checkout no longer holds off every idle-claim
  adoption: it blocks only claims whose `Touches:` files it holds open for writing (and
  claims without `Touches:`, whose files are unknown). Two owner sessions in sierra had
  stopped all adoption. TOOLSET-120-fc (3).
- A session in the main checkout blocks a runner's integration only when the merge
  changes a file that session holds open for writing or has left uncommitted there;
  unrelated sessions no longer hold verified work (sierra TASK-026 waited an hour).
  Sessions inside another task's worktree, and integration into the main checkout
  itself, keep the strict rule. TOOLSET-120-fc gap 6.
- While a verified commit waits for such a session, the runner no longer logs
  verifying/implemented every cycle, and health counts that wait as no progress: with
  nothing else running it is a stall naming the session. The Touches pass no longer
  logs a priority-drift refusal every cycle. (charlie.)
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
- README image audits skip image examples in confirmed single-line backtick spans,
  including mixed prose (TOOLSET-116-fc). Literal backticks in HTML, autolinks,
  destinations and quoted or multiline link titles cannot hide adjacent images.
  Indexed delimiter lookup and a single-pass literal-region scanner preserve
  conservative auditing for multiline code and ambiguous markup; this is not full
  CommonMark compatibility.

- Setup preflight validates runtime installation-facts structures before selecting
  an interpreter (TOOLSET-115-aa). Malformed mappings and non-string or empty
  environment paths return the existing safe admission error instead of crashing
  or interpreting an empty path relative to the working directory.

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

- An idle pi-autowork runner reacts to the plan: a change to `TODO.md`, `goals.json`,
  `BLOCKERS.md`, the TODO archive or the main branch ends its wait within seconds
  (after `PI_AUTOWORK_PLAN_SETTLE`, default 3, of quiet), so a new task or an answered
  question starts at once instead of after `--interval`. Only file status checks; no
  model call.

- `/plan_with_me blockers [repo|name]` works through what blocks the queue from the
  same list as `/autowork blockers`, easiest first, one question at a time; when an
  answer needs replanning (split or rescope a task, add a task or dependency, change
  acceptance) it plans that question with Plan With Me's planning craft and saves it
  through Docs Sync before the next one. `/autowork blockers` stays the quick path:
  answer, record in TODO.md, the runner re-queues.

- `install.sh` installs every component from one checkbox menu, all checked by
  default (TOOLSET-123-de): the Pi package, the `autowork` command (linked to the Pi
  package's release), `tx` (keeping an existing `~/.tmux.conf`), the Hermes plugin,
  the Claude Code plugin and the Codex plugin, each through its host's own command; a
  missing host CLI is skipped and said. `--all`, `--only`, `--skip`, `--list` and
  `--dry-run` work without the menu. No compatibility layer is kept: the Hermes-only setup is `install-plugins.sh`, `tx autowork` is gone, `tx` is
  pi-toolset's launcher unchanged, and the `autowork` command and TUI no longer handle
  tmux runners.

- The runner keeps the owner's questions in the repository's `BLOCKERS.md`, under
  `## Active` between `<!-- pi-autowork:questions:start -->` and `…:end -->`: one entry per
  held task no attempt can finish, unadoptable claim, unrunnable entry, outside condition
  or dependency cycle, with type, effort, how many tasks it unblocks, the worker's or
  engine's words and the exact answer. Built without a model, committed alone on the
  session branch only when it changes; text outside the markers is untouched.
  `/autowork blockers` answers them. TOOLSET-120-fc (2).
- The `autowork` command (TOOLSET-122-27) runs, watches and controls pi-autowork
  runners, with a systemd user service per repository as the default way to run:
  `autowork start [dir]` installs (if needed) and starts a service, idempotently, and
  refuses a directory without `TODO.md`, `goals.json` and its main branch, naming what
  is missing; `stop`, `restart`, `pause`/`resume` (stopped and kept off across
  reboots), `remove`, `run` (foreground, for debugging), `ls [--long]`, `status`,
  `logs [-f]`, `web` and `blockers`. Each service has its own Pi model:
  `autowork model <target> provider/model [--fallback provider/model]`, checked against
  Pi's list (`autowork models`), and kept across reinstalls. Bare `autowork` opens the
  TUI, now with a directory browser that marks repositories ready and starts their
  service, a full-screen log view, pause, restart and a model picker. Paused services
  stay listed. `tx autowork` and the tmux runners are gone (`tx autowork` points to
  `autowork` for one release); `tx` stays the tmux session launcher.

- The `tx autowork` TUI shows worker lanes: for the selected runner, one row per task
  in flight with its phase (from the runner's own log), attempt, time and the worker's
  last action from its Pi transcript (`bash: pytest -q`, `said: ...`, and how long
  ago), plus a `Now` column per runner. `tx autowork web` serves the same TUI to a
  browser with textual-serve 1.1.3, on 127.0.0.1:8765 by default; `--view-only`
  disables every control key. Neither calls a model.

- Planning never blocks delivery: a runner commits the main checkout's uncommitted
  planning files (TODO.md, goals.json, BLOCKERS.md, the TODO archive) before its final
  merge when nothing else is uncommitted, they have rested `PI_AUTOWORK_PLANNING_QUIET`
  seconds and no process holds them open for writing. Otherwise the pending-merge message
  says why they were left alone. TOOLSET-120-fc (4).
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
