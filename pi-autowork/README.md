# Pi Autowork component

The `pi-autowork` runner. `scripts/pi-autowork.sh` is a thin entry point and the
service command: it finds this component and runs `pi_autowork/cli.py`, which then
continues in the toolset release it resolves. The generic task lifecycle (admission, slots,
integration, closure) stays in the shared engine under `skills/autowork/scripts`,
which is the only authority for task state. Runtime state lives outside the
repository, under `${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`.

| Module | Role |
| --- | --- |
| `pi_autowork/cli.py` | Options, repository and toolset resolution (one release per run), `--status`, `--dry-run`, `--fleet`, `--set-aside`, the runner lock |
| `pi_autowork/coordinator.py` | The loop: engine lease owner, session branch and final merge, settle and close, requests, priority drift, Touches proposals and widening, health, self-update and restart, graceful stop |
| `pi_autowork/worker.py` | The engine-launched `--worker` and `--verify` modes |
| `pi_autowork/service.py` | `--install-service` / `--remove-service` for `pi-autowork@<repository>.service` |
| `pi_autowork/common.py` | Logging, Git helpers and task lifecycle words |
| `pi_autowork/pi_runtime.py` | Runs one Pi job: model choice and fallback, bounded retries, timeouts, budget, redacted `runs.jsonl` records (a straight port of the runner's Bash; the formal worker-runtime boundary is TOOLSET-117-cb) |
| `pi_autowork/health.py` | Per-runner `status.json`, one stall announcement per episode with its root blockers, and the `--fleet` view |
| `pi_autowork/touches_inference.py` | Finds tasks without Touches, records proposed lists, and widens a list the runner inferred (`scripts/pi_autowork_touches.py` remains as a compatibility entry point) |
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
| `autowork start [dir]` | Install (if needed) and start the repository's service; refuses a directory without `TODO.md`, `goals.json` and its main branch checked out, saying what is missing. Services run from the Pi package installed from `git:github.com/TrebuchetDynamics/autowork`; a service on another copy (a package under an older name) is moved onto it and restarted, and the others follow at their next restart |
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
| `autowork field TASK LABEL VALUE [target]` | Set one field of a task's TODO.md entry, as an owner answer (`"Owner decision"`, `Status`, `"Held by"`, `"Blocker resolution"`) |
| `autowork place TASK SECTION [target] [--decision TEXT]` | Move a task to Now, Next or Needs decision in TODO.md and goals.json, optionally recording why |
| `autowork add-task --title T --short S --goal G [--section S] [--scope ...] [target]` | Add a task to TODO.md and goals.json at the top of its section |
| `autowork move TASK up\|down [target]` | Move an open task among its TODO.md group's open tasks; the runner records the order as its priority |
| `autowork scorecard [--days N] [--json] [target...]` | Per runner over the last N days (default 7): tasks closed, share of integrations held, median dispatch-to-merge time, new owner questions; no model call |

In the TUI each key is the first letter of its word, highlighted in the detail pane:
`l` (or Enter) **L**og, `p` **P**lay/**P**ause (starts a stopped service, resumes a
paused one, pauses a running one), `s` **S**top, `r` **R**estart, `m` **M**odel and
`f` **F**allback (from Pi's list, type to filter), `t` **T**asks, `u` **U**ninstall the
service, `n` **N**ew: browse directories (from `~/git`, `AUTOWORK_BROWSE_ROOT`), see which
repositories are ready or what they need, and `p` there plays one; `q` **Q**uit. The Tasks
window lists every open task in TODO.md order with its `Short:` title, state and reason;
`1`–`5` (or Tab) show All, Working, Held, Waiting or Questions; on the selected task `u`/`d`
move it **U**p or **D**own (TODO.md order is the priority), `s` to another **S**ection (Now,
Next, Needs decision), `c` **C**lears its hold, `a` sets it **A**side, `b` answers the
owner's **B**lockers in an agent, and `n` adds a **N**ew task from a form. Enter opens the
task: its question and the runner's suggested answer, its whole TODO.md entry and its
worker's last actions. Answer it there, written to the task's entry where the runner reads
it: `w` **W**rite a dated `Owner decision:`, `d` **D**efer it to Needs decision with your
reason, and for a claim `o` **O**pen it (`Status: open`) or `h` mark it **H**eld by you for a
week; a repeated quick hold takes `r` **R**esolve with the producer or decision. Stop,
restart, pause, uninstall, clear, set-aside, model changes and claim answers ask first.
Terminal text can be selected by dragging with the mouse, then copied with your
terminal's copy shortcut (often Ctrl+Shift+C). Mouse capture is off by default;
keyboard navigation and controls remain available. Use `autowork tui --mouse` to
restore clickable rows/buttons instead; hold Shift while dragging if your terminal
or tmux intercepts selection. The browser view retains mouse controls.

The TUI and web view run Textual 8.2.8 (and textual-serve 1.1.3) through `uv`.

Design: [coordinator redesign](../docs/plans/2026-10-16-pi-autowork-coordinator.md),
[component layout](../docs/plans/pi-autowork-component-layout.md). Tests run from
`python3 scripts/check.py` (`pi-autowork/tests`).
