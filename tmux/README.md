# tmux profile

Portable tmux assets and the `tx` tmux-session launcher.

This is the maintained `tx`. It started as a copy of
[pi-toolset `tmux/`](https://github.com/TrebuchetDynamics/pi-toolset/tree/main/tmux)
at `4a2dbe5` and adds `tx autowork` (below); pi-toolset's `tx` is deprecated in its
favor. Installing this one (`./install.sh`, or the package's `tx` command) replaces a
`tx` installed from pi-toolset; every pi-toolset command works the same.

## `tx autowork`: pi-autowork in tmux

`tx`/tmux is the default way to run pi-autowork. Run `tx autowork start` from
the repository to start or attach to its runner. `tx autowork` also gives one
place to see every runner. A systemd user service is an optional alternative
(`pi-autowork.sh --install-service`; see [cross-host](../docs/cross-host.md#run-autowork-continuously)).

| Command | What it does |
|---|---|
| `tx autowork` | The live TUI (on a terminal): every runner with its state and what it is doing now, its worker lanes (each task in flight: phase, attempt, time, and the worker's last action, such as `bash: pytest -q`, with how long ago), blockers, held tasks and log; keys open a session, start or stop a runner, install or remove its service, set aside a held task (`x`) and answer blockers (`b`, `/autowork blockers` in `TX_AUTOWORK_AGENT`, else `claude` or `pi`). Stop, remove and set-aside ask first |
| `tx autowork start [name\|repo\|.]` | Open/start the runner; defaults to the current Git repository, including from a subdirectory; follows the journal if a service owns it |
| `tx autowork web [--port N] [--host H] [--view-only]` | The same TUI in a web browser, at `http://127.0.0.1:8765` by default (this machine only; reach it through an SSH tunnel or a private network). `--view-only` serves it with every control key disabled, for a shared screen or network |
| `tx pi-autowork-<name>` or `tx autowork <name\|repo\|.>` | Open the runner's session `pi-autowork-<name>`: attach, or start a tmux runner; for a service runner the session follows its journal |
| `tx autowork ls [--long]` | One colored line per runner, tmux and service: state and for how long, workers running, waiting and held; `--long` adds its `tx pi-autowork-<name>` command and what it waits on |
| `tx autowork status [name\|repo\|.]` | The runner's full status: tasks, workers, blockers (`pi-autowork.sh --status`) |
| `tx autowork logs [-f] [name\|repo\|.]` | Recent output: the service journal, or the tmux pane; `-f` follows the journal or attaches |
| `tx autowork stop <name\|repo\|.>` | Ctrl+C a tmux runner, wait for it to stop cleanly, close the session |

```sh
tx autowork                   # the live TUI
tx autowork ls                # what is running, and how it is doing
tx pi-autowork-sierra          # open sierra's runner session
tx autowork status india       # why india is stalled
tx autowork start             # run this repository in tmux (also: tx autowork .)
tx autowork stop my-project
```

- The browser view runs `textual-serve` 1.1.3: each tab gets its own copy of the TUI on this
  machine, with the same keys and confirmations. Binding beyond `127.0.0.1` without
  `--view-only` warns, since anyone who reaches the page can stop runners.
- The TUI runs through `uv run --with textual==8.2.8` (Textual is fetched into uv's
  cache once, nothing is installed globally) from the runner's own release, reads the
  same state as `ls` every few seconds and calls no model. Without a terminal, `uv` or a
  release that has it, and with `TX_AUTOWORK_TUI=0`, `tx autowork` prints its help.
- A target is a runner name (`sierra`), a repository path, or `.`. A name is found
  through its tmux session or its service settings (`~/.config/pi-autowork/<name>.env`).
- Every runner has session `pi-autowork-<repository name>`, the name its service
  uses too (`pi-autowork@<repository name>`); `.` and `:` become `_`. `ls` prints the
  `tx pi-autowork-<name>` command for each. An existing session is attached, not
  started again; a session holding another repository is refused. A configured `tx`
  alias of the same name wins over the session.
- It runs the script the systemd unit runs (`ExecStart` of
  `~/.config/systemd/user/pi-autowork@.service`), else `../scripts/pi-autowork.sh`
  next to `tx`; `PI_AUTOWORK_SCRIPT` overrides both.
- When `pi-autowork@<name>` is enabled or active, the service runs the repository,
  so the session follows its journal (`journalctl --user -fu ...`) instead of
  starting a second runner; `stop` closes that view and leaves the service running
  (stop the service with `systemctl --user stop`). Once the service is disabled, the
  next `tx autowork <name>` replaces the view with a tmux runner. The runner's own
  per-repository lock keeps two runners off one repository regardless.
- `stop` sends Ctrl+C: the runner pauses live workers so they resume on the same
  attempt, merges finished work and exits; `tx` waits for it (up to
  `TX_AUTOWORK_STOP_TIMEOUT` seconds, default 300) before closing the session. The
  pane stays open after the runner exits on its own, so its last lines remain.
- `ls` reads each runner's `status.json` under `~/.local/state/pi-autowork` (the same
  record as `pi-autowork.sh --fleet`), so it is instant; it needs `jq`. States are
  green (working), yellow (blocked, paused) or red (stalled, not running); lines are cut
  to the terminal width, so it reads on a phone:

  ```text
  pi-autowork runners: 4 (1 working, 3 stalled)
    charlie  tmux     stalled 34m     0 running, 10 waiting, 5 held
    bravo            tmux     stalled 1h17m   0 running, 53 waiting, 6 held
    india                   tmux     stalled 5h16m   0 running, 23 waiting
    sierra                  tmux     working 16m     1 running, 40 waiting, 5 held
  More: tx autowork ls --long   tx autowork status <name>   tx pi-autowork-<name>
  ```

  `tx autowork ls --long` adds each runner's command and what it waits on:

  ```text
  pi-autowork runners: 4 (1 working, 1 blocked, 2 stalled)

  india  tmux  stalled 4h41m
    tx pi-autowork-india  0 running, 23 waiting
    outside Now/Next: TASK-036 (19), TASK-035 (5)

  sierra  tmux  blocked 5m
    tx pi-autowork-sierra  0 running, 40 waiting, 6 held
    held: TASK-023 blocker (2), TASK-021 blocker (2), TASK-026 blocker (1), TASK-020 blocker (1)
    claimed elsewhere: TASK-028 (13), TASK-014 (4), TASK-038 (2), TASK-039 (1)

  (n) = waiting tasks that depend on it. More: tx autowork status <name>
  ```

  Blockers are grouped by kind: `held` (with its cause: `blocker`, `validation`,
  `bad report`, ...), `claimed elsewhere` (another session's claim), `outside Now/Next`
  (a decision or condition outside the queue) and `dependency cycle`. Long IDs are
  shortened; `tx autowork status <name>` has the full reasons.

## Files

- `tmux.conf` — tmux configuration. Install as `~/.tmux.conf`.
- `style.tmux` — local style overrides. Installed as `~/.tmux/style.tmux` only when missing.
- `git-status.sh` — optional status-bar git segment. Prints the branch name in green when clean and red when changed/untracked.
- `short-path.sh` — optional status-bar path segment. Prints only the last two path folders, e.g. `/tmp/git/pi-package-development-goal` -> `git/pi-package-development-goal`.
- `tx` — installable helper for starting, attaching, listing, and killing configured tmux sessions.
- `install.sh` — installer for the config, status helpers, and `tx`.

## Install

From this directory:

```sh
./install.sh
```

If `tx` is already on your `PATH` from an npm install/link, you can also run:

```sh
tx install
```

Defaults:

- tmux config -> `~/.tmux.conf`
- local style -> `~/.tmux/style.tmux` (kept if it already exists)
- status helpers -> `~/.tmux/git-status.sh` and `~/.tmux/short-path.sh`
- `tx` -> `~/.local/bin/tx`

Existing targets are backed up as `*.bak.<timestamp>` by default. Disable backups with:

```sh
TX_INSTALL_BACKUP=0 ./install.sh
```

Override install locations when needed. When `TMUX_HELPER_DIR` is set, the installed tmux config is rewritten to invoke helper scripts from that directory:

```sh
TMUX_CONF_TARGET=/tmp/tmux.conf \
TMUX_HELPER_DIR=/tmp/tmux \
TX_BIN_DIR=/tmp/bin \
./install.sh
```

Reload tmux:

```sh
tmux source-file ~/.tmux.conf
```

## Runtime flow

- `install.sh` copies the shared assets into user locations: `tmux.conf`, helper scripts, optional local style, and the `tx` launcher.
- `tmux.conf` shows the status bar at the bottom with the session, short current path, git branch/status, zoom state, and host. Periodic refresh remains disabled.
- `tx` reads session aliases from its config file, starts or switches to the matching tmux session, and uses the alias as the tmux session name.
- `style.tmux` stores per-machine colors and is sourced by `tmux.conf` from `~/.tmux/style.tmux`.

## Helper-script contract

The shared config calls `short-path.sh` and `git-status.sh` in the status bar. The installer places both helpers under `~/.tmux` (or `TMUX_HELPER_DIR`) and rewrites `tmux.conf` to that helper path.

Each helper takes one argument: the current pane path from `#{pane_current_path}`. `git-status.sh` prints the branch in green when clean and red when changed/untracked; outside git repos it prints nothing.

For very slow SSH/mobile links, periodic helper calls are disabled by default. To simplify the status further in `~/.tmux/local.tmux`:

```tmux
set -g status-left '#[bg=#{@primary_color},fg=#{@primary_text_color},bold] #S '
set -g status-left-length 40
```

## npm/bin install

The repository package declares:

```json
{ "bin": { "tx": "tmux/tx" } }
```

So `tx` is available when this package (hermes-toolset) is installed or linked by npm. The tmux config and status helper scripts still require `tx install`, `./install.sh`, or manual copying.

## Screen resizing

The profile does not set tmux resize options. It leaves `window-size` and `aggressive-resize` at tmux built-in defaults. This is intentional: forcing a manual window size can make mobile SSH clients repaint worse.

Inspect attached client sizes with:

```sh
tmux list-clients -F '#{client_name} #{client_session} #{client_width}x#{client_height} #{client_tty}'
```

If resize/redraw feels slow in a phone SSH app such as Termius, first close old SSH tabs and detach stale tmux clients:

```sh
tmux detach-client -a
tmux list-clients -F '#{client_name} #{client_session} #{client_width}x#{client_height} #{client_tty}'
```

The goal is one attached client, or at least no stale phone clients at very different sizes.

Avoid this as a default fix:

```sh
# Usually worse on mobile; use only as a temporary experiment.
tmux set -g window-size manual
```

Return to normal resize behavior with:

```sh
tmux set -g window-size latest
```

## Mobile controls

The prefix remains tmux's standard `Ctrl-b`, which works with Termius's extra-key row. Useful phone-friendly bindings:

- `Ctrl-b r` — force a full redraw after a reconnect or orientation change.
- `Ctrl-b v` — enter copy mode; press `v` to select and `y` to copy.
- `Ctrl-b Page Up` — enter scrollback; then use `Page Up`/`Page Down` and `q` to exit.
- `Ctrl-b m` — toggle mouse/touch scrolling for the current tmux server.
- `Ctrl-b t` — toggle the status bar when session details are useful.

Mouse mode remains off by default so Termius can handle native touch selection. The status bar keeps path and git details visible at narrow widths. Synchronized output (`terminal-features` sync) is **disabled by default** because mishandled end-of-frame markers can drop whole frames on some mobile SSH clients; re-enable it by uncommenting the two `terminal-features` lines in `tmux.conf`. Detach and reconnect once after installing so tmux recalculates client terminal features.

## Local/mobile overrides

The shared config sources `~/.tmux/local.tmux` at the end when it exists. Use this file for machine-specific settings only after stale-client cleanup is not enough.

The defaults keep history large, avoid idle status refreshes, and allow slightly slower mobile key sequences:

```tmux
set -g status on
set -g status-interval 0
set -g bell-action none
set -g history-limit 5000
set -sg escape-time 100
set -g repeat-time 750
```

Test one extra setting at a time so rollback is easy:

```tmux
# Optional if your local terminal needs truecolor more than low-byte output.
# set -as terminal-overrides ',xterm-256color:RGB'

# Optional if you prefer phone drag/scroll through tmux instead of the SSH app.
# set -g mouse on
```

Rollback to shared defaults:

```sh
rm -f ~/.tmux/local.tmux
tmux set -g window-size latest
tmux source-file ~/.tmux.conf
```

Keep resize overrides out of shared config unless there is a measured, cross-client reason. The shared profile intentionally leaves tmux resize behavior at defaults.

## User-facing colors

Per-machine colors live in `~/.tmux/style.tmux`, sourced by `~/.tmux.conf`:

```tmux
set -g @primary_color '#06d6a0'
set -g @primary_text_color '#101820'
```

The installer creates this file only when missing, so each PC can keep local colors while updating the shared tmux config. These colors affect the tmux session name and hostname. The current git branch is shown by `~/.tmux/git-status.sh`: green when clean, red when changed or untracked.

## tx config

`tx` reads sessions from:

```text
$TX_CONFIG
$XDG_CONFIG_HOME/tx/session.config
~/.config/tx/session.config

If the legacy `sessions.conf` already exists and `session.config` does not, `tx` keeps using the legacy file.
```

Create a starter config:

```sh
tx init
```

Add the current directory with an explicit alias:

```sh
tx add ga
tx add . ga
```

Add an explicit directory with an explicit alias. Alias-first and directory-first forms are both accepted:

```sh
tx add ga ~/git/agent
tx add ~/git/agent ga
```

Prompt for an alias while adding the current directory or another directory:

```sh
tx add .
tx add ~/git/agent
```

If the target directory already has a config row, the new alias is appended to that row's comma-separated alias list.

Inspect, rename, remove, and use:

```sh
tx config
tx ls
tx doctor
tx which ga
tx edit asul azul
tx remove oldalias
tx ga
```

The installer writes shell completion files for Bash, Fish, and Zsh. It also appends a small Bash source line to `~/.bashrc` when that file exists, so new Bash shells complete aliases automatically. For the current shell, run:

```sh
source ~/.local/share/bash-completion/completions/tx
```

Manual completion output is also available:

```sh
tx completion bash
tx completion zsh
tx completion fish
```

Config format:

```text
WORK=~/git
ga,gormes=$WORK/agent
```

Alias prefixes are accepted. Exact aliases win; otherwise the shortest matching alias wins, with alphabetical order used as a tie-breaker.

`tx ls` groups aliases by target directory to save vertical space. Running aliases are green; stopped or missing aliases are red. No status words are printed in the alias list. Colors are enabled by default for SSH terminals; use `TX_COLOR=auto` for TTY-only color, `TX_COLOR=never` to disable, or `NO_COLOR=1` to disable.
