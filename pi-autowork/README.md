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
| `pi_autowork/pi_runtime.py` | Runs one Pi job: model choice and fallback, bounded retries, timeouts, budget, redacted `runs.jsonl` records (the production CLI path; the TOOLSET-117-cb boundary is an isolated comparison spike, not wired into this runner) |
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
| `autowork start [dir]` | Install (if needed) and start the repository's service; refuses a directory without a committed `tasks/` store and its main branch checked out, saying what is missing (an unconverted repository: `autowork migrate`). Services run from the Pi package installed from `git:github.com/TrebuchetDynamics/autowork`; a service on another copy (a package under an older name) is moved onto it and restarted, and the others follow at their next restart |
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
| `autowork blockers [dir]` | `/autowork blockers` in an agent (`AUTOWORK_AGENT`, else `claude`, else `pi`) |
| `autowork tasks list\|validate\|new-id [target]`, `autowork tasks show\|why TASK [target]` | Read the `tasks/` store at HEAD (`validate --worktree`: uncommitted edits too) |
| `autowork tasks add\|field\|place\|move\|hold\|release\|done\|supersede\|goal ... [target]` | Edit task and goal files in the working tree, never committing: an owner answer (`field TASK "Owner decision" TEXT`, `"Blocker resolution"`), a section (`place`, optionally `--decision`), the priority (`move TASK up\|down` changes its rank), a hold (`hold --by`, `release`), a close with evidence (`done`), a new task or goal. Each write validates the whole store |
| `autowork tasks prepare [target] [--check\|--no-commit]` | What Docs Sync runs first: detect the store's state, convert or finish converting a TODO.md + goals.json repository, and report diagnostics with the command that repairs each, as JSON; `--check` writes nothing ([task store](task-store.md#preparing-a-repository-autowork-tasks-prepare)) |
| `autowork migrate [target] [--dry-run] [--no-commit]` | Convert a TODO.md + goals.json repository to `tasks/` once, in one local commit (`--no-commit`: staged); an interrupted run resumes; it refuses while work is in flight |
| `autowork scorecard [--days N] [--json] [target...]` | Per runner over the last N days (default 7): tasks closed, share of integrations held, median dispatch-to-merge time, new owner questions; no model call |

In the TUI each key is the first letter of its word, highlighted in the detail pane:
`l` (or Enter) **L**og, `p` **P**lay/**P**ause (starts a stopped service, resumes a
paused one, pauses a running one), `s` **S**top, `r` **R**estart, `m` **M**odel and
`f` **F**allback (from Pi's list, type to filter), `t` **T**asks, `u` **U**ninstall the
service, `n` **N**ew: browse directories (from `~/git`, `AUTOWORK_BROWSE_ROOT`), see which
repositories are ready or what they need, and `p` there plays one; `q` **Q**uit. The Tasks
window lists every open task in priority order (section, then rank) with its short title, state and reason;
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
runner stopped before recording a result. A live check past its execution budget
reads `past timeout`; waiting for a check slot does not consume that budget. New
slot receipts carry the command's configured timeout; older receipts fall back to
3600 seconds. A check of an older revision reads `superseded by main at REV`.
These are read-only status warnings, not a passing check, cancellation or restart.

A task someone works on outside the runner carries a `Held by:` note
(`autowork tasks hold TASK --by WHO [--until DATE]`); the runner never starts it and asks
nothing about it. `autowork tasks release TASK` lifts the hold; a dated hold ends by itself.

The fleet lists runners with open owner questions or missing `tasks/` setup first,
then other runners; each group is alphabetical. An idle runner with open questions
reads `Waiting on you`, not `Idle`. An existing repository without `tasks/` reads
`Setup required — run autowork migrate` in its headline and Needs field.

The TUI and web view run Textual 8.2.8 (and textual-serve 1.1.3) through `uv`.

## Runner health reads

Engine status reads wait up to two seconds for the writer lock, so brief dispatch
or integration writes do not immediately fail a read. If a read still fails,
health keeps its last observed state for that one failure, with the snapshot's
original timestamp and the read error. A second consecutive failure marks health
`unavailable`; without a previous snapshot it is unavailable immediately. A
successful read clears the failure episode without resetting an unchanged state's
stall clock. In `autowork status`, an unavailable Health line shows when reads
began failing, not when the previous healthy or blocked state began.

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
