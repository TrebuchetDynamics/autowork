# Pi Autowork component

Execution defaults to SDK-backed Pi RPC. See [installation, lifecycle guarantees,
controls and explicit JSON rollback](../docs/pi-rpc.md), and the separate
[qualification evidence](../docs/research/pi-rpc-qualification-2026-10-24.md).
An already-running release is not automatically upgraded by this source change.

The `pi-autowork` runner. `scripts/pi-autowork.sh` is a thin entry point and the
service command: it finds this component and runs the stable `pi_autowork/cli.py`
adapter, which continues in the toolset release it resolves. Runner and legacy-reader
implementations live in `Src/pi_autowork/`; the generic task lifecycle (admission,
slots, integration, closure) lives in `Src/pi_autowork/engine/` and remains the only
authority for task state. The original Python paths, `bin/autowork` and shell/service
commands remain public entry points. Flat engine imports and canonical
`pi_autowork.engine` imports share the same module objects, including exception types.
Standalone `worktree_paths.py` and `checkout_lock.py`, test assets and fixture helpers
remain under `pi-autowork/engine/`. A missing selected source refuses rather than
borrowing another checkout. Git-free archives support help/read commands, not immutable
runner launches, which still require a committed Git toolset.

The Python module paths in this table are relative to `Src/`; `bin/autowork` is
relative to this component. Child commands and reloads use stable public adapters;
source checks, TUI code stamps and review fingerprints inspect actual implementations.
Runtime state lives outside the repository, under
`${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `pi_autowork/engine/task_store.py` | Read-only, pinned-commit TaskStore used by the engine and committed fleet inventory; [schema and API](task-store.md) |
| `pi_autowork/engine/parallel_integrate.py` | Integration and closure transaction authority, locks, replay and cleanup; compatibility facades compose changelog proposals after document preparation |
| `pi_autowork/engine/integration/closure_documents.py` | Read-only task, receipt and live-followup preparation returning `{path: text}`; frozen `ClosurePorts` binds current `git`, `passed`, `task_path` and `live_items` callables per facade call |
| `pi_autowork/cli.py` | Options, repository and toolset resolution (one release per run), `--status`, `--dry-run`, `--fleet`, `--set-aside`, the runner lock |
| `pi_autowork/coordinator.py` | The loop: engine lease owner, session branch and final merge, settle and close, requests, priority drift, Touches proposals and widening, health, self-update and restart, graceful stop |
| `pi_autowork/supervision/main_checks.py` | Main-check supervision behind unchanged Coordinator methods; stateless helpers use the owner's phase callbacks and current Git/planning predicates. Coordinator retains policy, state, port leases and regression mutation. Child checks use Layout's public entrypoint. |
| `pi_autowork/post_merge_barrier.py` | Opt-in revision-bound admission, verdict validation and terminal classification using the existing main-check receipt; no separate scheduler. |
| `pi_autowork/worker.py` | The engine-launched `--worker` and `--verify` modes |
| `pi_autowork/service.py` | `--install-service` / `--remove-service` for `pi-autowork@<repository>.service` |
| `pi_autowork/common.py` | Logging, Git helpers and task lifecycle words |
| `pi_autowork/pi_runtime.py` | One Pi job: existing model/fallback policy, RPC by default, explicit JSON rollback, bounded retries and provenance-aware accounting |
| `pi_autowork/pi_rpc.py` | Pinned AsyncPiClient host, immutable accepted input, session ownership, settlement, private live progress and opt-in bounded controls |
| `pi_autowork/pi_process.py` | Linux parent/descendant ownership, pidfd signalling and cleanup receipts |
| `pi_autowork/pi_events.py` | Bounded event projection, lifecycle timing and conservative usage coverage |
| `pi_autowork/accounting.py`, `scorecard.py` | Private run/owner-time accounting and read-only scorecard aggregation; unknown billing is never priced or treated as zero |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |
| `pi_autowork/processes.py` | Shared Linux process start ticks, identity-aware liveness, runner ancestry and process names |
| `pi_autowork/workspaces.py` | Mirrors `PI_AUTOWORK_LINK_PATHS` gitignored dependencies into task and review worktrees (real directories, hard-linked files) |
| `pi_autowork/task_status.py` | Pure task-state display vocabulary shared by snapshots and CLI worker lanes |
| `pi_autowork/task_snapshot.py` | Immutable committed task inventory: ordered rows, five buckets and total, goals, questions, independently observed pending paths, runtime identity/freshness and errors; display-only, never dispatch authority |
| `pi_autowork/blockers_report.py` | Plain-text read-only diagnostic report; fresh committed selection reasons separated from recorded fleet/runtime observations |
| `pi_autowork/fleet_view.py` | Every runner on the machine (tmux sessions, `pi-autowork@` services, `status.json` health), its worker lanes (engine slots in flight, the runner's latest phase line, the Pi transcript's last action), its blockers grouped by kind, recent logs, and the exact existing command behind each action; standard library only |
| `bin/autowork`, `pi_autowork/command.py` | The `autowork` command (below), standard library only |
| `pi_autowork/tui_reads.py` | UI-loop read coordinator: four physical workers, coalesced requests, lifetime/identity/epoch-bound publication and cancellation-safe resource slots |
| `pi_autowork/tui.py` | The `autowork` TUI (Textual, run through `uv`): live runners with what each needs (the owner's open BLOCKERS.md questions, else its first blocker), worker lanes, model and log, stacked full width so it reads on an 80-column terminal, a directory browser that starts services, and keys that run `autowork` commands; `--view-only` disables the keys |
| `pi_autowork/tui_web.py` | `autowork web`: serves the TUI to a browser with textual-serve, on 127.0.0.1 by default |
| `pi_autowork/questions.py` | The owner's questions block in `BLOCKERS.md`, built from the engine status without a model |
| `pi_autowork/release.py` | Safe-checkpoint test before a self-update: fleet idle, and the new release reads current state |

## Blockers report

Select a runner and press **b** or click **Blockers** in mouse/browser mode.
The read-only summary puts recorded decisions and required inputs first, links
planning questions to their committed decision task while retaining who raised
them, and warns when selectable metadata conflicts with an explicit execution
restriction in an owner note. These warnings do not change admission or authorize
execution. Genuine input/authorization holds are not advice to weaken acceptance,
checks or scope. Technical/mixed or incomplete evidence does not receive an
owner-only headline. No worker observations does not prove no active workers.
An existing dated owner deferral is already answered, not a new permission question.
Planning stops under `## Resolved` or explicitly marked `Status: RESOLVED` do not
count as questions in the fleet banner, Tasks or report. Their source history is
left untouched. The Needs-decision inventory count still includes deferred records;
its label names the section rather than demanding another owner answer.
When the evidence contains only deferred work and its waiting dependents, the default
copy is a short overview (at most five task lines), quoting each recorded owner
condition instead of a generic deferral label. Long notes are explicitly excerpted;
the complete dated owner notes stay in Details.
Missing dependent checks remain visible. Mixed holds, active work, busy integration
or incomplete sources retain the general report rather than hiding another blocker.

**d Details** expands the same frozen capture: committed selection reasons,
main-check revisions/failure IDs, dependency roots and runtime evidence. Identical
reasons are shown once with explicit references preserving each task/source link;
linked planning evidence remains in Details even when the committed question is
primary. Closed history stays in Tasks → Closed, and integrated
work awaiting closure remains visible. Observations have separate readable source
times where available; missing data or unknown freshness is not health evidence.
The committed section reads the selected repository's HEAD on each report request,
not a last-good inventory. Selection eligibility is never runtime admission.
Full producer reasons replace matching truncated questions; unavailable full
reasons remain explicitly truncated. Source: `Src/pi_autowork/blockers_report.py:build`.

**c Copy** requests the plain text of the current summary/details view, without
terminal padding. **F7** selects all; **Ctrl+C** requests copying a selection.
Textual emits OSC 52; SSH/tmux, terminal policy or browser permissions can prevent
clipboard delivery. The UI cannot acknowledge a client clipboard: paste to verify.
It does not change terminal settings or choose a host desktop clipboard backend.

If copying is unavailable, **e Export** saves the frozen current view as a unique
private UTF-8 file under `<state-root>/reports/` (normally mode 0600), showing its
exact **app-host** path—not a file on the SSH client. In browser mode it requests
a plain-text download; transfer completion is not proof the user saved/opened it.
Export is explicit, never automatic; reports may contain sensitive operational
context. Refresh, Details and Escape remain usable during a host save, and a
refresh does not change the exported capture. Source: `Src/pi_autowork/tui.py:BlockersScreen`.

**r** explicitly refreshes; **Esc** returns. Opening, refreshing and copying run no
agent, runner command or task mutation; only explicit Export writes a report copy.
Native terminal drag selection remains available.
**g Plan** opens the embedded planning console for any repository, not only setup.
Interactive repair is still
the separate `autowork blockers [dir]` command, not this report.

## The autowork command

In the TUI, Tasks defaults to **1 Open**, excluding closed history and independent
question annotations from the open count. **6 Closed** keeps completed records
available for read-only inspection; number keys or Tab/Shift+Tab switch views.
The separate snapshot diagnostics pane stays three lines high; **i Info** focuses
it for scrolling/selecting/copying the full text, and **i** returns to the rows.
Questions outside current open inventory remain in **Questions**, not Open.
Explicit **Manual** closure shows its recorded actor/time/reason and is not
coordinator-verified. Old records without a closure method show **Unknown closure**;
the display neither reopens them nor invents missing evidence. Closed-history
detail cannot change section or execute answer/repair actions. These are local
source/UI semantics, not proof an installed or remote TUI loaded this release.

`autowork` runs, watches and controls the runners on this machine. A repository's
runner is a systemd user service, `pi-autowork@<repository name>`; a target is a runner
name, a repository path or `.`. Status and inventory reads call no model; planning
and the explicit agent commands below do.

| Command | What it does |
|---|---|
| `autowork` | The live TUI on a terminal (help otherwise) |
| `autowork start [dir]` | Install (if needed) and start the repository's service; refuses a directory without a committed `tasks/` store and its main branch checked out, saying what is missing (`autowork tasks prepare` converts legacy planning or reports the next step). Services run from the Pi package installed from `git:github.com/TrebuchetDynamics/autowork`; a service on another copy (a package under an older name) is moved onto it and restarted, and the others follow at their next restart |
| `autowork stop [target]` | Stop the service; workers pause and resume on the same attempt |
| `autowork restart [target] [--stop-workers [--now]]` | Reload in place; running workers keep running. `--stop-workers` waits for in-flight merges, then restarts the service and pauses workers; `--now` interrupts immediately instead |
| `autowork pause` / `resume [target]` | Stop the service and keep it off, also after a reboot (disable), or start it again (enable); only a paused service is listed as `paused`, any other stopped one as `not running` |
| `autowork model [target] [provider/model] [--fallback provider/model]` | Show or set this service's Pi model (checked against Pi's list), then reload it |
| `autowork models [search]` | Pi's model list (`pi --list-models`); an empty catalog is an actionable error, never `No/models` |
| `autowork setup-portal --provider NAME --model ID [--endpoint URL] [--apply] [--json]` | Preview a selected Pi provider for the local Hermes Nous proxy; only `--apply` consents to configuration, never a proxy/service start |
| `autowork ls [--long]` | One colored line per runner; `--long` adds its workers in flight, blockers, open owner-question count and model |
| `autowork status [target]` / `logs [-f] [target]` | The runner's full status; its journal |
| `autowork remove [target]` | Stop and remove the service; state and worktrees stay |
| `autowork run [dir]` | Run the runner in the foreground here, for debugging |
| `autowork web [--port N] [--host H] [--view-only]` | The TUI in a browser at `http://127.0.0.1:8765` (this machine only); `--view-only` disables control keys |
| `autowork blockers [dir]` | `/autowork blockers` in an agent (`AUTOWORK_AGENT`, else `claude`, else `pi`); records the session's elapsed owner minutes privately when the agent exits |
| `autowork plan [dir]` | Embedded Pi RPC planning: autonomous discovery, task discussion/investigation, saved sessions, roadmap and explicit Review → Apply. `--interactive` chats/steers; `--list`, `--session ID`, `--history`, `--preview`, `--apply REV` resume/review locally. No service start or push; [planning guide](../docs/planning-console.md). `--legacy` retains the former external-agent planner and its owner-time accounting |
| `autowork attention MINUTES [--task ID] [--note TEXT] [target]` | Record other owner time (finite, nonnegative minutes); defaults to this repository, optionally attributed to one task. Notes stay private |
| `autowork tasks list\|validate\|new-id [target]`, `autowork tasks show\|why TASK [target]` | Read the `tasks/` store at HEAD (`validate --worktree`: uncommitted edits too) |
| `autowork tasks add\|field\|place\|move\|hold\|release\|decide\|done\|supersede\|delete\|goal ... [target]` | Edit task and goal files in the working tree, never committing: an owner answer (`field TASK "Owner decision" TEXT`, `"Blocker resolution"`), a dated direction (`decide TASK TEXT`, optionally `--section`), a section (`place`, optionally `--decision`), the priority (`move TASK up\|down` changes its rank), a hold (`hold --by`, `release`), a manual close (`done ID --by WHO --reason TEXT [--evidence REF]`, not verification), a new task or goal, or a full record removal (`delete ID`; busy or still-depended-on tasks warn but are removed). Each write validates the whole store |
| `autowork tasks prepare [target] [--check\|--no-commit]` | What Docs Sync runs first: detect the store's state, convert or finish converting a TODO.md + goals.json repository, and report diagnostics with the command that repairs each, as JSON; `--check` writes nothing ([task store](task-store.md#preparing-a-repository-autowork-tasks-prepare)) |
| `autowork migrate [target] [--dry-run] [--no-commit]` | Convert a TODO.md + goals.json repository to `tasks/` once, in one local commit (`--no-commit`: staged); an interrupted run resumes; it refuses while work is in flight |
| `autowork scorecard [--days N] [--json \| --csv] [--baseline FILE] [target...]` | Per runner and overall over 1–30 days (default 7): labelled evaluation metrics, weekly breakdown and first-to-last-week changes; JSON retains closure, held-share, questions and task/attempt accounting details; no model call |

`autowork restart --stop-workers [target]` names the batch or merge-train check,
integration review or merge resolution it is waiting for. The coordinator records
its result and finishes pending batch landings before allowing the service restart;
it starts no new merge work while the request waits. With no merge in flight, it
acknowledges the restart at its next safe point. Workers keep running until the
service actually restarts, then pause and resume on the same attempt.

The wait defaults to **30 minutes**. Set `PI_AUTOWORK_RESTART_WAIT=SECONDS` in the
calling shell to change it (finite, nonnegative seconds). Expiry exits nonzero,
names the operation still pending and leaves the service running; it never turns
into an immediate restart. Cancelling the command releases the request too.
Overlapping safe restarts are serialized within the same wait bound; each caller
checks the current runner after the earlier restart completes.
`autowork restart --stop-workers --now [target]` bypasses this protection and can
interrupt a check or lose an unread integration result. `--now` requires
`--stop-workers`. Plain `autowork restart` is unchanged.

A running older release without the safe-restart handshake is refused: reload it
with plain `autowork restart` first, or explicitly interrupt it with `--stop-workers
--now`. A stopped service restarts without waiting. Offline command/coordinator
fixtures cover idle, wait, timeout refusal, recorded batch results and immediate
interruption; they do not qualify a live systemd service.

Before reusing an installed or running service, `autowork start` refuses if an
explicitly supplied supported service setting differs from its saved env file
(including a setting absent there).
For example, `PI_AUTOWORK_PUSH=0 autowork start` cannot silently start a service saved
with push enabled. The error names the conflicting settings and file and prints the
`--install-service` command to apply them; run it with the requested environment.
A refusal leaves the service and its pause marker unchanged. Matching settings keep
start idempotent. Without a saved or explicitly supplied `PI_AUTOWORK_PUSH=1` grant,
automatic publication is disabled, including upstream-sync publication; local commits
and merges still proceed.

Grant automatic push once when installing a new repository's runner:

```sh
PI_AUTOWORK_PUSH=1 autowork start /path/to/my-project
```

The installer saves the grant in that repository's settings file; later cycles and
launches reuse it without asking again. It does not grant permission to another
repository, even one with the same directory name. For an existing service, use the
`--install-service --repo /path/to/my-project` command above with `PI_AUTOWORK_PUSH=1`
to grant, or `PI_AUTOWORK_PUSH=0` to revoke; reinstalling applies the settings and
reloads/restarts that service. A shell-only override is not a persisted grant.

`autowork status /path/to/my-project` (or `pi-autowork.sh --status`) shows
`Push: enabled` or `Push: disabled` after loading repository settings, with an explicitly
set environment value taking precedence. This read does not edit settings or change
service lifecycle; it describes the next launch, not an unreloaded process's environment.
Existing saved `1`/`0` settings remain enabled/disabled and are not migrated or rewritten
by a settings load or status read. No live service migration is part of this default change.

`autowork ls --json` includes a boolean `push` for each runner, and the TUI detail
pane shows `Push enabled` or `Push disabled`. Both read the saved service env file,
not the viewing shell's overrides: only `PI_AUTOWORK_PUSH=1` enables push; a missing
or other value means disabled. Like status, these are read-only settings displays,
not probes of an unreloaded process's environment. Offline command tests and the
headless TUI pilot cover these displays; they do not qualify live publication.

In the TUI each key is the first letter of its word, highlighted in the detail pane:
`l` (or Enter) **L**og, `p` **P**lay/**P**ause (starts a stopped service, resumes a
paused one, pauses a running one), `s` **S**top, `r` **R**estart, `m` **M**odel
(from Pi's list, type to filter), `t` **T**asks, `g` **Plan**, `u` **U**ninstall the
service, `n` **N**ew: browse directories (from `~/git`, `AUTOWORK_BROWSE_ROOT`), see which
repositories are ready or what they need, and `p` there plays one; `q` **Q**uit.
The fleet has no Fallback or Nous Portal controls. Fallback remains visible in
runner details; configure it with `autowork model --fallback` and use
`autowork setup-portal` for opt-in provider setup.
On an unready repository, Play offers **Prepare**, **Prepare and start**, **Plan**,
**Force** and **Cancel**. Prepare runs `autowork tasks prepare` without blocking the
TUI and can commit a legacy conversion; it displays the outcome code, every refusal
and the next step, then refreshes the repository's readiness and tree label.
`NO_STORE` directs you to plan accepted intent with `/docs_sync`; it creates no goals
or tasks. Deferred, blocked, invalid
and toolchain outcomes are not readiness. Prepare and start asks to start only
after successful preparation and a fresh readiness check; Prepare alone never
starts a service. A deferred conversion stays unavailable until it completes.
**Force** first asks for confirmation: it stops the service and live workers, sets
attempts aside with worktrees, branches and files kept, commits planning edits,
converts, and restarts a previously active service. Escape cancels without running
anything; Yes runs `autowork tasks prepare --force <repo>` through the same background
worker. The pane shows the forced step's `stopped`, `set_aside`, `landed`, `committed`
and `commit` fields when present, alongside every refusal and the next step. For a
long report, Tab focuses the pane; End or Page Down scrolls to the rest.
The directory tree marks legacy or interrupted conversions **legacy planning**, not
**needs tasks**; a repository without planning still reads **needs tasks**.
The headless pilot exercises preparation on disposable repositories, with faked
service starts and forced service/worker effects; it does not qualify a live service.
The Tasks window lists open tasks in priority order (section, then rank) with their short title, state and reason.
`1`–`6` (or Tab) show Open, Active, Blocker, Waiting, Questions or Closed. Closed
history shows **Verified** with the receipt, or **Manual** with the reason
(a missing/invalid verified receipt is explicitly warned, never relabelled Manual).
On the selected task `u`/`d`
move it **U**p or **D**own (its rank is the priority), `s` to another **S**ection (Now,
Next, Needs decision), `c` **C**lears its hold, `a` sets it **A**side, `e` **Decide** records
an owner direction without AI, `g` **Discuss** and `v` **Investigate** open the planning
console scoped to that task, and `n` adds a **N**ew task from a form. Enter opens the
task: its question and the runner's suggested answer, its whole task record and its
worker's last actions. Answer it there, written to the task's record where the runner reads
it: `w` **W**rite a dated `Owner decision:` note, `d` **D**efer it to Needs decision with your
reason; a repeated quick hold takes `r` **R**esolve with the producer or decision. Stop,
restart, pause, uninstall, clear, set-aside and model changes ask first.
Terminal text can be selected by dragging with the mouse, then copied with your
terminal's copy shortcut (often Ctrl+Shift+C). Mouse capture is off by default;
keyboard navigation and controls remain available. Use `autowork tui --mouse` to
restore clickable rows/buttons instead; hold Shift while dragging if your terminal
or tmux intercepts selection. The browser view retains mouse controls.

### Fleet task inventory and freshness

Fleet counts, task rows and Waiting/Blocker details use one committed `tasks/`
snapshot per repository and refresh generation. Each committed open ID contributes
once to Active, Mergeable, Waiting, Blocker or Decision, whose sum is Total.
Ordinary ready work is Waiting (`ready; awaiting dispatch`); Needs decision comes
from the committed section. Stopped dependency waits are Blocker. Uncommitted
records and planning-branch records do not enlarge this inventory.

Runtime observations must name the same repository and compatible current/admitted
contracts. Missing legacy identity, duplicate/orphan observations and mismatched or
stale slot activity are annotations, not additional tasks or evidence of Active or
Mergeable work. Session/canonical revision divergence is disclosed. Questions for
closed or noninventory IDs remain visible as annotations in the Questions view.
The task record body is labelled as independently read working-tree content.

The Inventory line shows revision, generation, capture age and separate execution
freshness; pending paths and questions are independently observed working data.
A valid empty store has zero counts. Unavailable or invalid inventory shows `?`
and `unknown / unavailable`, not zero. Failed refreshes can retain last-good
inventory with its original revision/capture age, visibly stale. Pending-path read
failure means unknown, never clean. In the Tasks window, unavailable inventory
shows `?` for every view count and an unavailable placeholder rather than a verified
empty list. Essential freshness, revision and capture age stay visible separately
from bounded, scrollable diagnostics and wrapping view labels, including at 80 columns,
without displacing the task table. In this window, `i` (**Inventory**) toggles focus
between the task table and diagnostics; Page Down/End reads long errors. Verified
empty keeps zero counts; stale last-good rows keep their counts and original
revision/age with the acquisition error visible. The rendered pilot opens all three
states in wide and narrow viewports, checks painted cells/layout bounds, and scrolls
a long acquisition error through its final line.

A confirmed TUI **Delete** (`x` or Delete) uses the repository path captured before
confirmation, not a runner-name lookup. After command success, rows, closed history,
counts and detail/actions update on the next UI-loop update, without waiting for a
reader, timer or commit. Inventory diagnostics label this display-only adjustment
**deletion pending commit**; the original committed snapshot, dependency/admission
authority, worker activity and independent questions remain unchanged. Failures or
cancelled confirmation do not remove rows. Old or failed reads cannot resurrect the
record. Fresh off-loop working-tree and committed observations retire the adjustment
when deletion is committed or the record is restored. A recreation absent from HEAD
is disclosed as a pending record, never added to committed inventory. External CLI
edits retain the normal observation cadence; the TUI never commits deletions.

The TUI runs `collect_for_tui` off the event loop and publishes its `FleetSnapshot`
envelope atomically, including acquisition errors. Its labelled preparation diagnostics can be
reused for less than 30 seconds, invalidated by observed revision, dirty-file,
settings or environment changes. Explicit refresh and action/preparation return
invalidate the audit. Cached diagnostics supply neither task membership nor Start
authority: confirmed Start still reads readiness afresh. CLI/full readiness stays
uncached; service-enabled queries have a ten-second bound.

Fleet, journal, task-detail, goals, directory-readiness, model-catalog and code-update
reads share a four-worker coordinator. Each resource has one physical read and at
most one replaceable pending request. Timer polls do not invalidate a slower active
read; selection changes, action/interactive return and screen closure discard obsolete
results. Cancelling a subscription does not free its running thread's resource slot.
Only the UI loop publishes results and touches widgets. Resize, task filters and
worker-log wrap use cached data. Directory labels are loaded separately from the
selected repository's readiness; confirmed Start always requests fresh readiness.
Model discovery is fresh per opening and uses the selected service's provider context.
Read failures retain last-good data with a stale/unavailable diagnostic and allow retry.

Offline checks in `tests/test_tui_reads.py`, `tests/test_task_snapshot.py`,
`tests/test_fleet_view.py` and `tests/test_health.py`, plus the headless
`tests/tui_pilot.py`, cover these boundaries. The pilot acknowledges keys and closes
screens while reader providers are held by Events, before releasing them. Its
immediate-deletion case runs the real CLI on a private fixture with timers disabled
and the fleet reader blocked, then checks stale-result rejection, restore and
pending-only recreation. These checks do not qualify SSH transport latency, a live
service or execution through a provider.

The main-check line in runner status and the TUI reads the current check receipt,
not just the runner's cached health snapshot. A missing process or a reused PID
(with different process start ticks) reads `main check interrupted`, even if the
runner stopped before recording a result. A process without recorded start ticks
cannot be verified live and also reads `interrupted`. A verified live check reads
`running`; one queued for admission reads `waiting for a check slot`. A live check
past its execution budget reads `overdue` and `past timeout`; waiting does not
consume that budget. New slot receipts carry the command's configured timeout;
older receipts fall back to 3600 seconds. Each line names the checked revision;
a check of an older revision also reads `superseded by main at REV`.
A green result reads `main check passed at REV` for that revision only. If HEAD
has advanced, it reads `Last green: OLD · HEAD: NEW · verification pending`.
These are read-only displays: rendering never signals, cancels or restarts a check.

### Opt-in post-merge admission

`PI_AUTOWORK_POST_MERGE_POLICY=revision-barrier` requires an explicit
`PI_AUTOWORK_MAIN_CHECK` repository command and a positive
`PI_AUTOWORK_POST_MERGE_TIMEOUT` of at most 900 seconds (default 900, excluding
host check-slot wait). The default `async` policy is unchanged. Service installs
persist these settings without replacing unrelated saved grants; the CLI also
loads them on terminal launches.

The selected policy runs the command on exact canonical main through existing
main-check supervision, leases and restart adoption. Every further canonical
landing waits for a completed zero-exit green verdict bound to that revision and
attempt. Planning-only commits, batch tree receipts and an older green cannot
release it. Clean landings also use the existing index-lock/ref-CAS path so a
concurrent main advance cannot spend stale admission. Dirty-main guards remain;
owner planning files are not auto-committed in this mode. Deferred legacy conversion
is refused: migrate explicitly outside the runner before activation. Candidate/review gates
and isolated worker implementation continue unchanged. Automatic regression
reverts are disabled for this policy, including jobs adopted while enabling it.

The command writes schema-1 JSON at the absolute
`AUTOWORK_POST_MERGE_VERDICT` path (`<runner-state>/post-merge-verdict.json`).
It must echo `AUTOWORK_POST_MERGE_REVISION` and `AUTOWORK_POST_MERGE_RUN_ID`,
set boolean `complete: true`, and provide `status` and `failures`. Green requires
exit 0 and no failures; red requires exit 1 and nonempty named failures. The
supervisor's matching terminal receipt is also required. See the
[exact schema, environment, timeout and recovery contract](../docs/cross-host.md#revision-bound-post-merge-barrier).
This is bounded-command qualification, not a full-suite or live pass.

Red creates/deduplicates a revision-keyed repair through supported task writes in
the session, never by repairing canonical source or automatically reverting.
Pending repair incidents survive later checks/restarts and refused task commits;
repair Checks use candidate-specific variables and a private verdict path. Bounded
green receipts cannot substitute for full-suite base evidence, even with matching
command strings. No subsequent runner merge, including a repair merge, is permitted while red.
A real source repair requires separately authorized checked recovery; the resulting
external main advance is checked afresh. For transient failure, the runner CLI's
`--recheck-main --repo /path/to/project` requests a fresh attempt without cancelling
an adopted job, changing attempts or granting green. Terminal broken/red evidence
otherwise remains held; a dead job without a receipt is retried. The normal main
receipt/log/evidence files retain diagnostics; restart does not reset admission.

`tests/test_post_merge_barrier.py`, `tests/test_main_check.py` and
`tests/test_supervision_main_checks.py` provide offline seams, including import
isolation/DAG checks. These fixtures do not activate an installed service or qualify
a consumer's touched-project command, time bound, model execution or live hardware.

Manual closure is available for implementation, plan and inspection tasks, but writes no
receipt or passing-check claim. It alone qualifies neither a goal nor a prerequisite
explicitly listed in `verified_depends_on`. An authorized owner can record
`owner_waiver` or `owner_qualification` through `tasks field`; a met-goal write names
these exceptions. See [closure provenance and owner qualification](task-store.md#writing-and-autowork-tasks).

A task someone works on outside the runner carries a `Held by:` note
(`autowork tasks hold TASK --by WHO [--until DATE]`); the runner never starts it and asks
nothing about it. `autowork tasks release TASK` lifts the hold; a dated hold ends by itself.

The fleet lists runners with open owner questions or task-store setup/repair first,
then other runners; each group is alphabetical. An idle runner with open questions
reads `Waiting on you`, not `Idle`. The headline and Needs field follow the
read-only `autowork tasks prepare --check` result: no store reads
`Setup required — run /docs_sync`; a legacy TODO.md + goals.json
queue reads `Migration required — Force converts legacy planning`; an invalid store
or interrupted conversion reads `Task store needs repair`. Docs Sync prepares and
reconciles the store; `autowork migrate` remains available as direct CLI conversion recovery.

The TUI and web view run Textual 8.2.8 (and textual-serve 1.1.3) through `uv`.

## Questions

The fleet reads owner questions from `BLOCKERS.md`, preferring the runner's session
worktree until it merges into the repository. It lists both engine-generated
questions inside `<!-- pi-autowork:questions:start -->` / `<!-- pi-autowork:questions:end -->`
and maintainer sections headed `### Q-<planning task ID> — Planning stopped` outside
that block. Planning stops appear after engine questions as kind `decision`, effort
`decision`, unblocking one goal-continuation task. Their need includes the `Task:`
and `Question:` lines; a prose-only section uses its body instead.

`autowork ls --long` counts both kinds. The TUI shows both in the runner's question
detail and the Tasks window's Questions filter. A stop question stays visible under
its planning task ID even after that planning task closes; this does not reopen it
or add to the open-task count. Listing or refreshing questions never rewrites
`BLOCKERS.md` or answers a question. The engine still writes only its marked block.
Offline coverage in `tests/test_fleet_view.py` exercises mixed and planning-only
session files, CLI counts, the TUI's question-row filter and unchanged file bytes;
it does not qualify a live runner or terminal session.

## Retained attempt files

The stale `/tmp` sweep (`PI_AUTOWORK_TMP_STALE`) preserves scratch allocated to
unfinished engine slots, including held and interrupted attempts with no live
worker. It reads current slots for all registered runners, including stopped
runners, rather than relying on cached health; incomplete reservation discovery
defers the sweep. Released, closed and set-aside slots no longer reserve scratch;
close and set-aside also remove their allocated temp directories directly.

When a task runs fresh after set-aside, its prompt lists earlier task branches
and any retained set-aside worktrees with their uncommitted paths. These files
are not restored automatically: inspect them and reuse only work relevant to the
current task, without modifying the retained worktree.

## Nous Portal setup (opt-in)

Pi remains the executor; Hermes owns the Portal login and subscription proxy.
Installing Autowork does not configure this route. With a current Hermes supporting
`hermes proxy` and Pi's compatible-endpoint `models.json` format:

```sh
# Replace with an exact model ID available on your Portal plan (may contain /).
MODEL_ID='model-from-your-plan'
autowork setup-portal --provider nous-local --model "$MODEL_ID"
# Review the proposal, then explicitly consent to that provider edit only:
autowork setup-portal --provider nous-local --model "$MODEL_ID" --apply
```

Portal setup is CLI-only; the fleet TUI has no setup shortcut. Without `--apply`,
the command only previews the proposal and leaves configuration bytes unchanged.
`--json` exposes the path, provider/model, endpoint, prerequisite diagnostics,
proxy state and applied flag to automation.

The default endpoint is `http://127.0.0.1:8645/v1`. `--endpoint` accepts only literal
`127.0.0.1` or `[::1]` HTTP addresses with a port and `/v1`; no remote hosts,
credentials, queries or redirects. Setup reads only local `/health`, without an
Authorization header or environment HTTP proxy. It does **not** request the upstream
model catalog, authenticate, refresh credentials, start/stop anything or call a model.
`available` means the expected Nous proxy reports stored authentication, **not** that
refresh, model access, billing or inference succeeded. Missing Pi/Hermes executables,
unavailable proxy, missing login and incompatible health responses have separate
messages. An unavailable proxy does not prevent preparing configuration for later use.

Only the selected provider under `${PI_CODING_AGENT_DIR:-~/.pi/agent}/models.json`
is prepared, using `openai-completions`, a non-secret `local-proxy-placeholder` key
and the exact model ID. Real credentials stay in Hermes. Other providers and settings
are preserved as JSON values (formatting may change). Existing models in that provider
are retained; changing its endpoint affects **all** its models. Only an existing entry
with this placeholder, compatible API and supported structure can be updated. Retained
model entries support `id`, `name`, `reasoning`, `input`, `contextWindow`, `maxTokens`
and complete nonnegative `cost` metadata. Other model fields, including `baseUrl`,
`api` and executable `headers`, are refused rather than silently overriding the
selected provider route. Provider-level `modelOverrides` are also refused. The same
validation runs before runtime model selection, including after manual config edits.
Conflicting keys/headers/API settings, malformed/duplicate-key JSON, symlinked files and edits since
the displayed proposal refuse without replacement. Writes use a private temporary file,
fsync and atomic replacement; repeated identical application preserves the file bytes.
No Pi defaults or runner model choices are changed by setup.

Use the same **absolute** `PI_CODING_AGENT_DIR` for setup and service installation
if you do not use Pi's default directory. The installer saves it and preserves it
on reinstall; foreground runners load it from repository settings unless explicitly
overridden. CLI/TUI service-model selection uses the saved directory, so it validates
against that service's catalog. An existing service without a saved directory uses
Pi's default directory, not the model picker's shell override. Relative agent directories
are refused to prevent resolution differences between setup and services.
Setup itself always targets the calling process's Pi
directory, displayed in the proposal; it never edits an unrelated service/profile.
Existing services need explicit reinstallation to adopt a different directory.

Starting a runner is a **separate operation that makes model calls**. For a new
service, set `PI_AUTOWORK_PRIMARY="nous-local/$MODEL_ID"` and
`PI_AUTOWORK_NO_FALLBACK=1` when running `autowork start /path/to/project`, or supply
an explicit available `PI_AUTOWORK_FALLBACK` instead. No Codex/OpenRouter login is
required for a proxy-only choice. Existing services use `autowork model` and the
supported installer for changed service settings. A missing proxy on a prepared
entry is diagnosed before worker/model selection, never delegated to workers for
repeated configuration approvals.

Offline coverage: `tests/test_autowork_command.py`, `pi-autowork/tests/test_portal.py`
and the headless `tui_pilot.py` use disposable configurations and health-only stubs;
no real proxy, auth, service lifecycle or inference is qualified. For manual
prerequisites and the separately opt-in live probe, see
[the cross-host guide](../docs/cross-host.md#nous-portal-through-the-local-proxy).
Contracts verified against [Hermes subscription proxy documentation](https://hermes-agent.nousresearch.com/docs/user-guide/features/subscription-proxy),
[Hermes health implementation](https://github.com/NousResearch/hermes-agent/blob/3a9d585e4f1a60588237587a72d365d187094c74/hermes_cli/proxy/server.py)
and [Pi compatible endpoints](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/models.md#configure-a-compatible-endpoint)
(Pi 1.3.0 installed documentation); earlier Pi versions are not newly qualified.

## Affected landing checks

When a repository declares `python3 scripts/check.py` as its full check, batch and
single-candidate gates run `scripts/check.py --affected BASE..HEAD` on the merged
tree. The command prints the selected test modules and the reason for each:
changed tests, transitive repository Python importers (including lazy imports and
package re-exports), and code naming a changed path. It also runs the available
tree guard, Docs Sync document check and working-tree task-store validation.
`--list` previews the selection without running checks.

Unresolved paths, shared fixtures, checker/shard-map changes, CI and packaging
inputs select the full offline inventory. Non-test files under the check inventory
directories are conservatively treated as shared inputs too. Custom full-check
commands retain their existing behavior; optimistic landing still skips unsupported custom full gates,
while the affected checker runs before landing, including its conservative full
fallback when needed.

Private state retains the selection, reasons, range and core in
`full-check/tree-<tree>.json`, carries it through batch verdicts and records each
accepted supported landing in `landing-check/<task>.json`. A batch receipt names
the selection for the combined candidate tree, not only one task's changes. The
core list is a plan: consult the producing log to confirm which tools existed and ran.

Under the default asynchronous policy, main still runs the declared **full** suite
after landing, with existing regression attribution and repair/revert handling.
The [opt-in post-merge policy](#opt-in-post-merge-admission) instead qualifies its
explicit bounded command; it must not be read as a full-suite result. Only a passing full-inventory receipt for
the same tree and command can replace main's check. An affected-only pass cannot
mark main or its base green. Offline fixtures in `tests/test_check.py`,
`tests/test_pi_autowork.py` and `pi-autowork/tests/test_main_check.py` cover selection,
landing receipts and this full-main boundary; they do not establish live qualification.

## Passing batch prefixes

After a batch's merged chain passes its existing gate, a contiguous passing prefix
can land while tail reviews continue in detached checkouts. Each complete candidate
still receives its own policy decision and independent review when required. A missing
or failed predecessor blocks early prefix landing; the terminal batch uses the existing
hold/reverification paths. Integration and closure remain serial engine operations.
Neither affected checks nor optimistic landing can qualify main's full suite.

The private batch channel publishes complete records by temporary write, flush/fsync
and atomic rename under `state/batch/<unpredictable-generation>/`. Admission identity
(task, engine attempt, contract and candidate), batch base, prefix tree, producing
check selection/command and review policy must match the current owned producer.
The coordinator reserves each accepted record once before promoting it to the engine's
one-use verdict channel. An old producer cannot publish into a replacement generation.
An independent merge-train car is invalidated as soon as a prefix moves its base.

Stopping invalidates the generation before replacement. The existing birth-bound
runtime supervisor must prove descendant cleanup; missing or false persisted cleanup
proof stops replacement, including after restart. Restart never adopts unconsumed
generations. A verdict consumed before integration may need ordinary verification
again; integrated work uses engine receipt recovery
and idempotent closure, not another landing. The terminal result excludes prefixes
already integrated by that producer.

Offline batch-prefix fixtures in `tests/test_pi_autowork.py` cover a fast A landing
before blocked B in optimistic and affected-gated modes, plus incomplete, stale and
replayed publication. The train fixture in `pi-autowork/tests/test_worker_tmp.py`
covers producer exit during prefix landing and independent-car invalidation. These
are control-flow checks, not live-service qualification or a measured latency benefit.

## Selective review pilot

Model review remains on by default. `PI_AUTOWORK_REVIEW=auto` is an opt-in,
conservative pilot: skip the model only for small **ordinary prose** changes whose
committed task checks are already proved by a successful, source/log-bound gate.
It does not skip the gate, change full-main checks, grant publication, or treat a
timeout as a pass. Review findings about style, preferred abstractions, repetitive
tests or table-driven organization are advisory unless they demonstrate a concrete
defect or violate an explicit task requirement. Acceptance failures, regressions,
security issues and credible data-loss risks still block.

The pilot inspects the full candidate diff from the session baseline (first
parent) of the engine's two-parent integration merge, not the task's `touches` or
a worker's risk label. Ordinary commits and other unsupported merge shapes retain
review: their first-parent diff cannot establish the authorized candidate range.
Eligible files are ordinary `.md` and `.rst` files in
`docs/`, plus root `README.md` and `CHANGELOG.md`, at most ten files and 400
added/deleted lines. Deletions, renames, special file modes, sensitive paths/text
(including review, security, authority, planning and contract language), and
executable markup retain review. **Tests, source code and configuration always
retain review** in this first version; path names alone cannot prove them safe.

The task contract must be unchanged from the parent. Any review mention in the
task conservatively retains review. Repository instruction files may contain only
full-check declarations matching the executed command; any other instruction text
retains review rather than guessing which obligations it creates. CODEOWNERS,
indirect instruction files, and tasks requiring live/manual/owner acceptance also
retain review. Every declared task check must exactly match the gate's full
command, with a complete successful
result and no recorded skips; uncovered commands, affected-only selections,
missing/legacy evidence and unknown inventory retain review. Optimistic landing
without a pre-landing gate therefore still invokes the reviewer in `auto` mode.
Unknown setting values also retain review. Explicit `PI_AUTOWORK_REVIEW=0` remains
the broader operator opt-out; it is not the selective policy and is not recommended
as a fleet-wide speed shortcut.

Each decision records its reason, mode, policy version, commit and tree under the
private state's `review-policy/<task>.json`. Single and batch paths share the
policy. Skipping requires a clean checkout and exact-tree evidence: a later batch
step's passing gate cannot prove an earlier step passes. A skipped-review batch
verdict is invalidated by tree, policy, mode or validation-command drift; it cannot
reuse the broader docs/task drift allowance.
A skip is a policy decision, not an independent model approval.

For a pilot, record `autowork scorecard --days 7 <target>` before enabling `auto` in
one repository's saved service settings and reloading at a safe point. After a
week compare dispatch-to-integration time, repeated attempts, regressions and
owner attention; inspect decision records to see how often review was actually
skipped. Return to `PI_AUTOWORK_REVIEW=1` if quality worsens. Enabling this on a
running service is a separate operator action; installing the code does not opt
existing services in. Offline fixtures cover the policy and receipt boundaries,
not live model compliance or a measured throughput improvement.

## Cost and owner attention

```sh
autowork attention 15 --task CACHE-01 --note 'Reviewed behavior'
autowork attention 5 /path/to/repository   # repository-level time
autowork scorecard --days 30 --json .
autowork scorecard --days 30 --csv . > evaluation.csv
autowork scorecard --days 30 --baseline /private/baseline.json .
```

### Evaluation report

Text, `--json` and `--csv` render the same evaluation metrics. JSON adds
`runners.<name>.evaluation` and `overall`, while retaining the existing runner
counters and `usage`. Each evaluation contains `summary`, `weeks`, `change`,
`baseline`, `baseline_change` and separate `phase_diagnostics`. Each metric has
`value`, `unit` and `status`:
`measured`, `estimate` or `missing`; missing JSON values are `null`, CSV values
are empty, and text says `missing`. Metadata (names, window bounds and week
numbers) is not a metric. CSV is long-form: one row per scope, runner, period
and metric, with the same labels and values as JSON. Periods are `summary`,
`week-1` onward, `change`, `baseline`, `baseline_change` and
`phase_diagnostics.<row>`. CSV also includes `cohort`, `identity` and `rules`
columns for diagnostic rows (empty for other periods).

Weeks are consecutive seven-day intervals from the window's start, oldest first;
the final week can be shorter (two days for a 30-day window). Boundaries are epoch
seconds: start inclusive, end exclusive except the final end. Changes are absolute
last-week minus first-week values, not relative percentages; percentage changes
use percentage points. A single-week window compares that week with itself.
Overall metrics pool task counts, duration samples and denominators across unique
repositories; runner medians and percentages are never averaged. Repeated targets
for one repository count once.

| Metric | Definition and limits |
| --- | --- |
| `verified_tasks`, `verified_tasks_per_day` | Distinct currently closed tasks with valid coordinator receipts and a close transition in the window, divided by actual period days. A reopened/reclosed task counts once in its latest close's week. A lifecycle close observation dates that transition when available; otherwise its Git timestamp does. Conversion itself closes nothing. |
| `manual_closed`, `owner_interventions` | Manual/legacy hand closes are separate, never verified. Each counts as one intervention even without telemetry. Other interventions are explicit `blocker_answered`, `contract_edited` and `hand_closed` facts, not retries or inferred Git authorship. |
| `unattended_completion_percentage` | Percentage of verified completions with no recorded lifecycle intervention or positive task-attributed owner time before closure, including observations before the window. Requires accepted/dispatch/close telemetry for every counted task. Unattributed positive owner time overlapping a task's lifecycle, or invalid attention records, makes this unknown. Manual closes enter neither numerator nor denominator. |
| `accepted_to_delivered_{median,p95}_minutes` | First acceptance to first delivery for each verified completion in the period; delivery is observed by the coordinator, not inferred from a candidate commit. |
| `dispatch_to_integrated_{median,p95}_minutes` | First dispatch to first integration, including retry delays. Both duration metrics are missing if any verified completion lacks ordered endpoints. p95 uses nearest rank, with no extrapolation for small cohorts. |
| `cost_per_verified_task_usd`, `owner_minutes_per_verified_task` | All window spend / recorded owner time divided by verified completions, including unattributed overhead and work not yet completed. Missing billing or missing attention for a verified task leaves the corresponding ratio missing. These are period ratios, not lifetime task bills; costs just before a week's boundary remain in that earlier week. |
| `recovery_success_rate` | Fraction of observed restart/interruption episodes followed by `worker_adopted`/`resumed` for the same task and attempt by the report end. A success means execution recovered, not that the task subsequently passed. Episodes belong to their trigger's week; no episodes means missing. |
| `regression_rate` | Fraction of the period's verified completion cohort with at least one explicit receipt-linked regression discovered during the selected window, observed through the report end. Multiple notes/reverts for one task count once. Older deliveries' discoveries remain visible in runner `regressions`, but do not inflate the completion cohort's rate. This is observed attribution, not proof that all regressions were found. |

With no verified completion, all rates and per-task ratios are **missing**, not
zero. Counts (including manual closes and interventions) remain measured. A
measured unattended result means no *recorded* intervention, not proof of complete
human-activity coverage. Recorded owner time is likewise not an inferred total.
An undated torn attention record cannot be proved outside a task's lifecycle, so
it conservatively leaves unattended results missing. Missing values propagate into
changes; no guessed zero fills a gap.

An optional private baseline file is a JSON object with finite nonnegative values:

```json
{"cost_per_verified_task_usd": 5, "owner_minutes_per_verified_task": 15}
```

`baseline.metrics` labels these owner-supplied values `estimate`, beside the
unchanged measured summary metrics. `baseline_change` is measured summary minus
baseline, also labelled `estimate` (or `missing` when measurement is unavailable).
Without `--baseline`, every format says `no baseline` and comparison values are
missing. Keep baseline files and exported reports private; they can reveal
repository names and operating costs. No evaluation output proves a live 30-day
run; [the evaluation plan](../docs/evaluation.md#30-day-evaluation) keeps that separate.

### Observed phase diagnostics

`evaluation.phase_diagnostics` (also under `overall`) is an observed-subset
report, not a replacement for strict whole-cohort summary timing. Each row has
`cohort`, `identity`, `rules` and `metrics`; text and CSV expose the same labels,
values and coverage. Rows are:

| Row | Identity and endpoints |
| --- | --- |
| `task_accepted_to_dispatched` | Task: first acceptance → first dispatch; retries collapsed. |
| `task_dispatched_to_integrated` | Task: first dispatch → first integration, including retry waits. |
| `attempt_running_to_reported` | Task + attempt: first running → first reported. |
| `attempt_reported_to_integrating` | Task + attempt: first reported → first integrating. |
| `attempt_integrating_to_integrated` | Task + attempt: first integrating → first integrated; may include holds. |
| `attempt_integrated_to_closed` | Task + attempt: first integrated → observed closed, matched to that attempt's ID. |
| `all_attempt_exposure` | Separate all-outcome cohort: first running → first reported. |

The six phase rows select tasks whose **latest receipt-valid verified close** lies
in the report window, using the same closure dating as the summary. Task rows
collapse retries; attempt rows retain distinct `(task_id, attempt_id)` keys for
those tasks, including failed/retry attempts. All retained lifecycle and slot-state
endpoints through cutoff can resolve a pair: starts may predate the window. Slot
records without an attempt ID (or with `unknown`/`unassigned`) do not create
invented attempts. A task-scoped close without an attempt ID cannot supply an
attempt's close endpoint.

Each row reports `eligible`, `observed_pairs`, `missing_start`,
`missing_end_terminal`, `right_censored`, `reversed`, `median_minutes` and
`p95_minutes`. Choose the first timestamp of each endpoint kind, not a later
convenient pair: a reversed first pair stays excluded even when a later end would
be ordered. Classify missing start first. A start without an end is terminal-missing
only if a later attempt of the same task (by first observation) or a closed state
is observed through cutoff at/after the phase start; otherwise it is
right-censored. Task rows also use later-attempt evidence when no close endpoint
is retained. A historical close cannot terminate newer work. A held/interrupted
attempt can resume, so those states alone do not mean terminal failure. For phase
rows, eligible equals the sum of observed, missing-start, terminal-missing,
right-censored and reversed counts. Median and nearest-rank p95 use only observed
pairs; empty samples have missing values, never fabricated zero latency.

`all_attempt_exposure` instead selects first-running starts in the inclusive
`[window_start, cutoff]` interval **across all outcomes**, including open and manually
closed tasks. `missing_start` counts observed attempt keys without running;
`left_excluded` counts starts before the window. Both are outside this row's
`eligible` count. Sum only ordered pairs whose first report is also in the window,
without clipping or extrapolation. `observed_completed_attempt_span_hours` is that
sum in hours (missing without pairs). Parallel spans can overlap or include
suspension: these are **attempt-span hours, never runner uptime**. The report does
not derive deliveries/runner-hour from them. Missing delivered facts or explicit
runner-availability intervals remain missing evidence, not inferred throughput.

See the [phase cohort contract](../docs/evaluation.md#phase-cohort-and-endpoint-contract).
Offline identity/coverage, missing-delivery and format-parity fixtures are in
`pi-autowork/tests/test_scorecard.py`; they do not qualify live delivery or uptime.

### Accounting details

The scorecard's JSON `usage` contains `tasks`, each with `attempts`, `roles`
(worker, reviewer, coordinator), `host_models`, token totals, billing and
`owner_minutes`. Runtime roles `verify` map to reviewer; merge, triage,
provision and maintainer map to coordinator. Repository-wide merge and maintainer
jobs stay unattributed rather than becoming invented tasks. New runs carry a unique `run_id`
and the engine `attempt_id` when available. Replayed IDs count once; distinct
retry runs add spend but not another verified or delivered task. Older records
without attempt/host metadata retain explicit `unknown` attribution. Records
missing a task or role count under `unattributed`, never disappear. Torn records
and replayed IDs are counted in `diagnostics`, with separate invalid-run and
invalid-attention counts. Unreadable run records invalidate the complete window
bill and cost-per-task ratios, but retain the valid measured subtotal.

`input_tokens`, `output_tokens` and `tokens` are observed counts, or `null` when
missing. `cost_usd` is `null` and `cost_status` is `missing` if any run lacks
provider-reported billing; `measured_cost_usd` retains the known subtotal, not
an estimate of the missing spend. `unknown_cost_tasks` lists tasks with missing
billing/usage. Subscription usage reports tokens with cost unknown. Pi's ordinary
`usage.cost` is catalog-derived, **not provider billing**, so neither it nor older
unlabelled `runs.jsonl` costs establish measured spend. Only amounts explicitly
labelled `cost_source: provider_reported` by a billing-aware adapter are accepted;
stock Pi output without that provenance remains unknown. There are no pricing
tables, billing API calls or budget changes here.

`cost_per_verified_task_usd` and `cost_per_delivered_task_usd` divide the window's
total spend by distinct verified closures and lifecycle delivery observations,
respectively. A retry does not add a completion. Missing billing, missing usage
for a counted completion, or a zero denominator leaves the ratio `null`.
The measured subtotal includes unattributed runs so their spend cannot vanish.

`owner_minutes` means **recorded** time, not complete coverage: unrecorded time
stays unknown. A task with no attention record reports `null`, never zero.
`autowork blockers` measures wall-clock time until its agent exits (including
idle time and failed/interrupted sessions); it records repository-level time,
not a guessed division among tasks. A forcibly killed wrapper cannot record its
duration. Other time must be logged with `autowork attention`; avoid logging the
same blocker session twice. `unattributed_owner_minutes` keeps repository-level
time separate. `interventions` counts the lifecycle categories `blocker_answered`,
`contract_edited` and `hand_closed`, without inferring human activity from model
retries or commit authorship.

Usage and attention logs live only in private runner state (`runs.jsonl` and
`attention.jsonl` under the repository's state key), including optional notes.
No usage records or attention logs belong in Git. These are offline accounting
facilities, not evidence that a live task was delivered or that a bill was paid.

## Runner health reads

`runner.json` and the runner's own `job.json` record both the PID and its Linux
process start ticks (`start_time`), separately from the wall-clock start time.
Status, fleet health and update-checkpoint reads require matching ticks and a
non-zombie process; a reused PID reads `not running`, and cannot keep an old job
current. Status also requires the runner lock to be held. Older records without
start ticks cannot establish liveness and read `not running` until the runner
writes a new record on startup or reload. These reads do not change the records.
Offline health and CLI fixtures cover matching, mismatched and missing identity;
main-check and ancestry fixtures exercise the same shared process helper. These
checks do not qualify recovery after a real host crash or live service restart.

An unusable repository (not Git, detached HEAD or a non-main branch), missing
runner tools or invalid `--workers` stops startup with exit **4 (needs attention)**.
The service does not restart this exit every minute. The reason is saved outside
the repository and remains visible in `autowork status <name>` and the TUI's
headline, Needs and Blocker detail, ahead of generic setup or start-service advice,
even if the checkout's `.git` is unavailable. Fix the named condition,
then use `autowork start <name>`; a successful startup clears the saved setup stop.
Read-only status and dry runs do not replace it. Generated units also suppress
restart for bootstrap/usage exit 2 (for example when Python cannot launch); such
pre-Python errors remain in the service journal. Reinstall the service to update
an older unit's exit-2 handling.

Startup compares the configured repository's Git common directory and toplevel
with independent probes that remove inherited `GIT_*` variables. A mismatched
`GIT_DIR` or `GIT_WORK_TREE` stops before repository writes; remove the inherited
variables and start again. The check runs before release snapshot creation, even
when the configured repository is the toolset itself. Release snapshot Git commands
also ignore inherited `GIT_*`, and runner descendants do not inherit Git routing,
index or config overrides.

Offline regression coverage in `tests/test_pi_autowork.py` checks setup exits
against the generated unit and injects Git routing into disposable repositories.
`tests/test_autowork_command.py` checks saved reasons through status, fleet reads
and the TUI display helpers, including escaped service names and a checkout
without `.git`. `tests/test_task_store_qualification.py` verifies exit 4 before
migration and successful task execution after conversion. These do not qualify a
live systemd service.

Engine JSON status includes `task_source`: the resolved `workspace`,
`repository_identity` (the resolved Git common directory, shared by linked
worktrees), pinned committed `revision`, and `observed_at` (Unix seconds). All
current task records in one answer come from that revision. Each task row exposes
its current `contract_hash` separately from the attempt's `admitted_contract_hash`;
a missing record or legacy attempt identity is `null`, never filled from the other
hash. These diagnostic fields do not grant authority or change task/attempt schemas.
Revision discovery ignores inherited Git routing and replacement refs.

The coordinator reuses status for at most five seconds, only for the same resolved
workspace and source revision, and drops it after its engine mutations. Health
preserves `task_source` and uses its `observed_at` for `snapshot_at` and snapshot
age, including cached writes and failed-read recovery; `updated_at` is only the
health-file write time. Legacy source fields and observation times remain unknown
when absent, rather than borrowing a new write time. Offline producer/cache/health
fixtures cover these contracts; they do not prove a deployed runner loaded this
source or qualify SSH responsiveness.

Engine status reads wait up to two seconds for the writer lock, so brief dispatch
or integration writes do not immediately fail a read. If a read still fails,
health keeps its last observed state for that one failure, with the snapshot's
original timestamp and the read error. A second consecutive failure marks health
`unavailable`; without a previous snapshot it is unavailable immediately. A
successful read clears the failure episode without resetting an unchanged state's
stall clock. In `autowork status`, an unavailable Health line shows when reads
began failing, not when the previous healthy or blocked state began.

`autowork status` lists every unfinished task, with running, integrating, reported,
held and waiting tasks first, in that order. Rows retain the task, lifecycle and
reason columns; closed tasks appear as one finished-task count after the rows.
If the engine read fails (for example, while another process holds `writer.lock`),
status keeps the read error visible and lists saved `status.json` task rows with
that snapshot's age. The age uses the last successful observation, not the latest
failed read; missing timestamps are labelled `age unknown`. These read-only
fallbacks do not refresh the snapshot or establish that a saved worker is still live.
Saved rows lack pause metadata, so interrupted/released tasks retain those raw states
instead of being labelled failed. Offline CLI fixtures cover active-first rows and
the held-lock fallback.

## Session merge recovery

Before merging main, the coordinator tries to commit edits left in its own session.
If Git refuses a bookkeeping commit, the warning includes Git's output (including
hook diagnostics). When all staged paths are runner bookkeeping (`BLOCKERS.md`,
task-store files or frozen history), it unstages those paths without changing their
working contents so unrelated main fixes can merge. The edits stay in the session
for a later commit; they are not landed uncommitted. A refused work commit still
holds the landing. Repository hooks are never disabled for this recovery.

A merge refusal without unmerged paths is reported as `Merge pending` with Git's
message, not as an unknown-file conflict. Only actual unmerged paths trigger the
Pi conflict resolver. Overlapping uncommitted bookkeeping can still prevent the
merge; its contents and session worktree are kept for retry.

If a merge invents a task/goal status, Evidence or closure value, or synthesizes a
contract field absent from both parents, the runner rejects it before landing or
adoption. The diagnostic names the record and field; the pre-merge head is restored
and main stays unchanged. Resolve by selecting parent values, combining only ordinary
notes; record intentional task transitions separately. See the
[merge and closure rules](task-store.md#integration-and-closure).

## Isolated runtime comparison

The [TOOLSET-117-cb spike](spikes/runtime-comparison/README.md) compares the current
CLI path, pinned AgwaB `runSubagent` headless execution and experimental pi-durable
on identical offline fixtures. It defines launch/observe/stop/resume and explicit
replay capabilities without changing the default worker. Measurements and limits
are in the [research comparison](../docs/research/pi-autowork-reference-architectures.md#worker-runtime-comparison-toolset-117-cb).
Do not configure services to load the spike; adoption requires an owner decision.

Design: [coordinator redesign](../docs/plans/2026-10-16-pi-autowork-coordinator.md),
[component layout](../docs/plans/pi-autowork-component-layout.md). Tests run from
`python3 scripts/check.py` (`pi-autowork/tests`).
