# Pi Autowork component

The `pi-autowork` runner. `scripts/pi-autowork.sh` is a thin entry point and the
service command: it finds this component and runs `pi_autowork/cli.py`, which then
continues in the toolset release it resolves. The generic task lifecycle (admission, slots,
integration, closure) stays in the shared engine under `pi-autowork/engine`,
which is the only authority for task state. Runtime state lives outside the
repository, under `${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `engine/task_store.py` | Read-only, pinned-commit TaskStore; [schema and API](task-store.md). Not yet wired into consumers |
| `pi_autowork/cli.py` | Options, repository and toolset resolution (one release per run), `--status`, `--dry-run`, `--fleet`, `--set-aside`, the runner lock |
| `pi_autowork/coordinator.py` | The loop: engine lease owner, session branch and final merge, settle and close, requests, priority drift, Touches proposals and widening, health, self-update and restart, graceful stop |
| `pi_autowork/worker.py` | The engine-launched `--worker` and `--verify` modes |
| `pi_autowork/service.py` | `--install-service` / `--remove-service` for `pi-autowork@<repository>.service` |
| `pi_autowork/common.py` | Logging, Git helpers and task lifecycle words |
| `pi_autowork/pi_runtime.py` | Runs one Pi job: model choice and fallback, bounded retries, timeouts, redacted `runs.jsonl` records of each run's tokens and billing provenance (the production CLI path; the TOOLSET-117-cb boundary is an isolated comparison spike, not wired into this runner) |
| `pi_autowork/accounting.py`, `scorecard.py` | Private run/owner-time accounting and read-only scorecard aggregation; unknown billing is never priced or treated as zero |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |
| `pi_autowork/workspaces.py` | Mirrors `PI_AUTOWORK_LINK_PATHS` gitignored dependencies into task and review worktrees (real directories, hard-linked files) |
| `pi_autowork/fleet_view.py` | Every runner on the machine (tmux sessions, `pi-autowork@` services, `status.json` health), its worker lanes (engine slots in flight, the runner's latest phase line, the Pi transcript's last action), its blockers grouped by kind, recent logs, and the exact existing command behind each action; standard library only |
| `bin/autowork`, `pi_autowork/command.py` | The `autowork` command (below), standard library only |
| `pi_autowork/tui.py` | The `autowork` TUI (Textual, run through `uv`): live runners with what each needs (the owner's open BLOCKERS.md questions, else its first blocker), worker lanes, model and log, stacked full width so it reads on an 80-column terminal, a directory browser that starts services, and keys that run `autowork` commands; `--view-only` disables the keys |
| `pi_autowork/tui_web.py` | `autowork web`: serves the TUI to a browser with textual-serve, on 127.0.0.1 by default |
| `pi_autowork/questions.py` | The owner's questions block in `BLOCKERS.md`, built from the engine status without a model |
| `pi_autowork/release.py` | Safe-checkpoint test before a self-update: fleet idle, and the new release reads current state |

## The autowork command

`autowork` runs, watches and controls the runners on this machine. A repository's
runner is a systemd user service, `pi-autowork@<repository name>`; a target is a runner
name, a repository path or `.`. Nothing here calls a model.

| Command | What it does |
|---|---|
| `autowork` | The live TUI on a terminal (help otherwise) |
| `autowork start [dir]` | Install (if needed) and start the repository's service; refuses a directory without a committed `tasks/` store and its main branch checked out, saying what is missing (`autowork tasks prepare` converts legacy planning or reports the next step). Services run from the Pi package installed from `git:github.com/TrebuchetDynamics/autowork`; a service on another copy (a package under an older name) is moved onto it and restarted, and the others follow at their next restart |
| `autowork stop [target]` | Stop the service; workers pause and resume on the same attempt |
| `autowork restart [target] [--stop-workers]` | Reload the runner in place on its current release and settings; running workers keep running. `--stop-workers` restarts the service instead, pausing them |
| `autowork pause` / `resume [target]` | Stop the service and keep it off, also after a reboot (disable), or start it again (enable); only a paused service is listed as `paused`, any other stopped one as `not running` |
| `autowork model [target] [provider/model] [--fallback provider/model]` | Show or set this service's Pi model (checked against Pi's list), then reload it |
| `autowork models [search]` | Pi's model list (`pi --list-models`) |
| `autowork ls [--long]` | One colored line per runner; `--long` adds its workers in flight, blockers and model |
| `autowork status [target]` / `logs [-f] [target]` | The runner's full status; its journal |
| `autowork remove [target]` | Stop and remove the service; state and worktrees stay |
| `autowork run [dir]` | Run the runner in the foreground here, for debugging |
| `autowork web [--port N] [--host H] [--view-only]` | The TUI in a browser at `http://127.0.0.1:8765` (this machine only); `--view-only` disables control keys |
| `autowork blockers [dir]` | `/autowork blockers` in an agent (`AUTOWORK_AGENT`, else `claude`, else `pi`); records the session's elapsed owner minutes privately when the agent exits |
| `autowork attention MINUTES [--task ID] [--note TEXT] [target]` | Record other owner time (finite, nonnegative minutes); defaults to this repository, optionally attributed to one task. Notes stay private |
| `autowork tasks list\|validate\|new-id [target]`, `autowork tasks show\|why TASK [target]` | Read the `tasks/` store at HEAD (`validate --worktree`: uncommitted edits too) |
| `autowork tasks add\|field\|place\|move\|hold\|release\|done\|supersede\|goal ... [target]` | Edit task and goal files in the working tree, never committing: an owner answer (`field TASK "Owner decision" TEXT`, `"Blocker resolution"`), a section (`place`, optionally `--decision`), the priority (`move TASK up\|down` changes its rank), a hold (`hold --by`, `release`), a manual close (`done ID --by WHO --reason TEXT [--evidence REF]`, not verification), a new task or goal. Each write validates the whole store |
| `autowork tasks prepare [target] [--check\|--no-commit]` | What Docs Sync runs first: detect the store's state, convert or finish converting a TODO.md + goals.json repository, and report diagnostics with the command that repairs each, as JSON; `--check` writes nothing ([task store](task-store.md#preparing-a-repository-autowork-tasks-prepare)) |
| `autowork migrate [target] [--dry-run] [--no-commit]` | Convert a TODO.md + goals.json repository to `tasks/` once, in one local commit (`--no-commit`: staged); an interrupted run resumes; it refuses while work is in flight |
| `autowork scorecard [--days N] [--json] [target...]` | Per runner over the last N days (default 7): tasks closed (total, verified, manual and unverified-evidence), share of integrations held, median dispatch-to-merge time, new owner questions, measured spend and recorded owner minutes; JSON includes task/attempt usage and attribution; no model call |

Before reusing an installed or running service, `autowork start` refuses if an
explicitly supplied supported service setting differs from its saved env file
(including a setting absent there).
For example, `PI_AUTOWORK_PUSH=0 autowork start` cannot silently start a service saved
with push enabled. The error names the conflicting settings and file and prints the
`--install-service` command to apply them; run it with the requested environment.
A refusal leaves the service and its pause marker unchanged. Matching settings keep
start idempotent; the default remains push enabled.

In the TUI each key is the first letter of its word, highlighted in the detail pane:
`l` (or Enter) **L**og, `p` **P**lay/**P**ause (starts a stopped service, resumes a
paused one, pauses a running one), `s` **S**top, `r` **R**estart, `m` **M**odel and
`f` **F**allback (from Pi's list, type to filter), `t` **T**asks, `u` **U**ninstall the
service, `n` **N**ew: browse directories (from `~/git`, `AUTOWORK_BROWSE_ROOT`), see which
repositories are ready or what they need, and `p` there plays one; `q` **Q**uit.
On an unready repository, Play offers **Prepare** or **Prepare and start**, which run
`autowork tasks prepare` without blocking the TUI. Prepare can commit a legacy
conversion; it displays the outcome code, refusals and next step, then refreshes
the repository's readiness and tree label. `NO_STORE` directs you to plan accepted
intent with `/docs_sync`; it creates no goals or tasks. Deferred, blocked, invalid
and toolchain outcomes are not readiness. Prepare and start asks to start only
after successful preparation and a fresh readiness check; Prepare alone never
starts a service. A deferred conversion stays unavailable until it completes.
The existing headless pilot exercises this flow on disposable repositories with
real preparation commands and faked service starts; it does not qualify a live service.
The Tasks window lists open tasks in priority order (section, then rank) with their short title, state and reason,
followed in All by closed tasks: **Verified** with the receipt, or **Manual** with the reason
(a missing/invalid verified receipt is explicitly warned, never relabelled Manual);
`1`–`5` (or Tab) show All, Working, Held, Waiting or Questions; on the selected task `u`/`d`
move it **U**p or **D**own (its rank is the priority), `s` to another **S**ection (Now,
Next, Needs decision), `c` **C**lears its hold, `a` sets it **A**side, `b` answers the
owner's **B**lockers in an agent, and `n` adds a **N**ew task from a form. Enter opens the
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
queue reads `Migration required — run /docs_sync`; an invalid store or interrupted
conversion reads `Task store needs repair`. Docs Sync prepares and reconciles the
store; `autowork migrate` remains available as direct CLI conversion recovery.

The TUI and web view run Textual 8.2.8 (and textual-serve 1.1.3) through `uv`.

## Cost and owner attention

```sh
autowork attention 15 --task CACHE-01 --note 'Reviewed behavior'
autowork attention 5 /path/to/repository   # repository-level time
autowork scorecard --days 7 --json .
```

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

Engine status reads wait up to two seconds for the writer lock, so brief dispatch
or integration writes do not immediately fail a read. If a read still fails,
health keeps its last observed state for that one failure, with the snapshot's
original timestamp and the read error. A second consecutive failure marks health
`unavailable`; without a previous snapshot it is unavailable immediately. A
successful read clears the failure episode without resetting an unchanged state's
stall clock. In `autowork status`, an unavailable Health line shows when reads
began failing, not when the previous healthy or blocked state began.

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
