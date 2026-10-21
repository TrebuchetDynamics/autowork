# Command and configuration reference

Exact entry points, flags, settings and environment variables this bundle reads.
Each entry names its source of truth; when they disagree, the source wins and this
page has drifted. Conversational workflow commands (`/autowork`, `/docs_sync`,
`/plan_with_me` and the rest) are listed in [workflows](workflows.md#commands);
procedures and their side effects are in [installation](installation.md).

## Terminal: `hermes autowork`

Source: [`bundle.py`](../bundle.py) `setup_parser` and `handle_cli`. Add `-p PROFILE`
after `hermes` to run from a named profile; `setup` and `update` still target every
live profile under the same Hermes root.

| Command | Flags | Effect |
| --- | --- | --- |
| `hermes autowork doctor` | `--json`; `--core` (alias `--bundle-only`) | Reports plugin load and command/skill registration, and lists profiles linked to a working checkout (`linked_profiles`; never a failure). Exit 1 unless `status` is `ready`. `--core` ignores external integration gaps. |
| `hermes autowork setup` | `--dry-run`, `--yes-deps`, `--bundle-only`, `--no-reload`, `--hermes-home ROOT` | Runs [`setup_bundle.py`](../setup_bundle.py): installs sources in [`plugins/PLUGINS.md`](../plugins/PLUGINS.md), applies [defaults](../plugins/defaults.json), finalizes every live profile. |
| `hermes autowork update` | `--check`, `--hermes-home ROOT` | Runs [`update_bundle.py`](../update_bundle.py) and waits: fast-forward-only update of every live profile. `--check` fetches and previews only. |
| `hermes autowork pin NAME` | `--dry-run`, `--unpin`, `--hermes-home ROOT` | Replaces one profile's plugin link with a clone at the same revision, saving the link; `--unpin` restores it. See [linked profiles](installation.md#linked-profiles-and-pinned-clones). |
| `hermes autowork finalize` | `--hermes-home ROOT` (required), `--bundle-only`, `--no-reload` | Verifies one profile's registrations and runtime settings and refreshes gateway commands; setup calls it per profile. |

`setup` flags:

| Flag | Meaning |
| --- | --- |
| `--dry-run` | Preview target profiles and actions without writing. CLI startup can still apply runtime defaults; see [installation](installation.md#preflight-before-fleet-writes). |
| `--yes-deps` | Consent to declared Python dependencies during native installs. |
| `--bundle-only` | Link, enable and configure only this bundle; skip external sources. |
| `--no-reload` | Defer live gateway wiring explicitly. |
| `--hermes-home ROOT` | Hermes root containing `profiles/` (default: `HERMES_HOME`, else `~/.hermes`). |

## Chat: `/autowork status`, `list` and `update`

Source: [`bundle.py`](../bundle.py) `handle_chat`, `list_commands`, `start_update`,
`update_status`, `repository_status`. Works in CLI chat and Telegram.

| Form | Effect |
| --- | --- |
| `/autowork status` | Read-only fleet summary from the existing native runner command: repositories, activity, running/waiting/held counts. No repository is guessed from the gateway's working directory. |
| `/autowork status NAME` | Read-only status for that registered runner, including repository, workers, holds and waiting reasons. A quoted absolute repository path is also supported; relative paths and options are refused. |
| `/autowork plugin status` | Bundle version, revision and profile; ready workflow commands; last update; plugin load status and setup gaps (the former status overview). |
| `/autowork list` | Every available command with its owner and Telegram spelling. |
| `/autowork list TEXT` | Commands whose name or owner contains `TEXT`, for example `/autowork list omh`. |
| `/autowork update` | Starts the all-profile updater in the background and returns immediately. |
| `/autowork update --check` | Starts an upstream check only. |
| `/autowork update status` | Summarizes the durable result from `maintenance/toolset-update/latest.json` at the Hermes root in a few lines, and lists profiles linked to a working checkout. |
| `/autowork update status full` | Shows that whole receipt as JSON. |
| `/autowork` with other arguments | Runs the Autowork skill with them as instructions, for example `/autowork update the README`. |

Repository status invokes the bundled Python runner entry point with literal argv,
no shell or model call, and a bounded wait. Failed, empty or timed-out reads report
unavailable, never a healthy empty fleet. Long output is explicitly truncated in chat;
use terminal `autowork status NAME` for the full output. This does not install, update,
start, stop, clear holds or change schedules. Named status reports provider readiness
as `not checked: read-only status`; it does not check or refresh authentication.
Plugin/gateway activation is separate from offline handler tests.

## Source-checkout scripts

Run from a clone of this repository. The shell installers are thin wrappers.

| Script | Flags | Effect |
| --- | --- | --- |
| `./install.sh` | `--all`, `--only a,b`, `--skip a,b`, `--list`, `--menu`, `--dry-run`; Hermes options for the Hermes item | The component menu ([`scripts/install_menu.py`](../scripts/install_menu.py)): Pi package, `autowork`, `tx`, Hermes, Claude Code, Codex. Without a terminal it needs `--all`, `--only` or `--skip`. |
| `bash install-plugins.sh` | Same as `hermes autowork setup`; `--help` | Public calls, including `--help`, execute `setup_bundle.py`. The source-installer usage appears only with the internal `--sources-only --help`. |
| `bash install-skills.sh` | `--dry-run`, `--hermes-home ROOT`, `--profile-home HOME` | Runs [`install_skills.py`](../install_skills.py): copies `skills/` (except retired `repo-docs` and `repo-interview`) into the default and every existing profile, or only `--profile-home`; `--hermes-home` and `--profile-home` are mutually exclusive. Never overwrites existing skill paths or changes configuration. |
| `python3 update_bundle.py` | `--hermes-home ROOT` (required), `--check`, `--profile NAME` (repeatable with `--source`), `--source CHECKOUT`, `--revision SHA`, `--native-python PATH` | All-profile update, or with `--profile`, `--source`, `--revision` and `--native-python` (all four required) a scoped deployment of a reviewed local commit; see [installation](installation.md#deploy-an-exact-local-revision-to-selected-profiles). |
| `python3 install-graphify.py` | `--hermes-home ROOT`, `--profile NAME` (both required), `--dry-run` | Installs Graphify's Hermes skill into selected existing profiles; installs the `graphifyy` tool with `uv tool install` when missing. |
| `python3 install-omh.py` | `--hermes-home ROOT`, `--profile NAME` (both required), `--dry-run` | Applies the checked-in OMH defaults to selected homes, installing `omh` with `uv tool install` when missing, and writes `plugins.entries.omh.settings.omh_home`; see [memory](memory.md). |
| `scripts/pi-autowork.sh` | `--once`, `--until-empty`, `--workers N`, `--dry-run`, `--status`, `--repo PATH`, `--interval SECONDS`, `--max-cycles N`, `--no-fallback`, `--allow-hermes`, `--install-service`, `--remove-service`, `--help` | Runs the Parallel Autowork engine with Pi workers, verified integration and a session merged into the main branch; see [continuous Autowork](cross-host.md#run-autowork-continuously). |
| `python3 scripts/check.py` | `--list`, `--timeout SECONDS` (default 600 per directory) | Runs the offline test inventory; see [testing](testing.md). |

## Repository helpers used by workflows

These ship inside the bundle and are run by skills against your project. Paths are
relative to this repository.

| Helper | Commands | Reference |
| --- | --- | --- |
| `autowork tasks` ([source](../pi-autowork/pi_autowork/task_commands.py)) | `list`, `show`, `why`, `validate`, `new-id`, `add`, `field`, `place`, `move`, `hold`, `release`, `done`, `supersede`, `goal` | `autowork tasks --help`; [task store](../pi-autowork/task-store.md) |
| `autowork migrate` ([source](../pi-autowork/pi_autowork/task_migrate.py)) | convert a TODO.md + goals.json repository to `tasks/` once | [converting a repository](../pi-autowork/task-store.md#converting-a-repository-autowork-migrate) |
| [`skills/docs-sync/scripts/docs.py`](../skills/docs-sync/scripts/docs.py) | `validate`, `check`, `stale`, `profiles` | `docs.py --help`; [role manifest](../skills/docs-sync/references/document-scaffold.md#optional-role-manifest) |

## Worker long checks: `autowork-run`

Source: [`autowork_run.py`](../pi-autowork/engine/autowork_run.py) and
[`parallel_dispatch.py`](../pi-autowork/engine/parallel_dispatch.py).
Every dispatched worker has `autowork-run` on its PATH. Run suites or builds
expected to take more than two minutes through it; run focused tests directly:

```sh
autowork-run python3 scripts/check.py path/to/test_module.py
autowork-run bash -c 'build-command && integration-command'
```

The wrapper takes a host-wide **worker** check slot before starting the literal
command and arguments, then returns its exit code (128 + signal for a signal exit).
It prints one `waiting for a worker check slot` line if queued. These slots are
separate from runner full-check slots, but use the same private host directory
and `flock` mechanism. A killed process cannot leave a stale lease; a surviving
check subprocess keeps its lease until it ends. Normal completion releases it
including when a background descendant survives.

The worker command watchdog excludes recorded queue intervals, including waits
inside a shell tool call; `PI_AUTOWORK_COMMAND_TIMEOUT` still bounds execution
after admission. The worker's overall task timeout is unchanged. Queue records
live in `$AUTOWORK_WORKER_CHECK_DIR` beside the attempt's report, and reconciliation
adds their total as `worker_check_slot_wait_seconds` to an existing worker report.
This is voluntary: commands run without the wrapper are not slot-limited.

## Main-checkout changes (Pi runner)

Source: [`coordinator.py`](../pi-autowork/pi_autowork/coordinator.py)
`commit_owner_changes`, `owner_planning_paths` and `fast_forward_main`.

The runner never stages or commits non-planning changes from the main checkout,
regardless of their age or quietness. If the session would change a dirty
non-planning path, landing waits as **Merge pending** and names the paths, even
when the edits could merge without a conflict. If the paths do not overlap,
the session merges and pushes normally, leaving the owner's working-tree and
staged changes uncommitted.

The owner-planning sweep still commits task and goal files under `tasks/` and
`BLOCKERS.md` once their
content has stayed unchanged for `PI_AUTOWORK_PLANNING_QUIET` seconds (default
`600`) and no process holds them open for writing. Unfinished Git operations
are left alone. This main-checkout boundary does not change recovery commits
of uncommitted changes in the runner's own session worktree.

## Rolling planning tasks (Pi runner)

Source: [`parallel_plan.py`](../pi-autowork/engine/parallel_plan.py),
[`maintainer.py`](../pi-autowork/pi_autowork/maintainer.py) and
[`coordinator.py`](../pi-autowork/pi_autowork/coordinator.py); accepted
[rolling planning design](plans/2026-10-18-rolling-planning.md#rolling-planning-design).

A task record may set `kind = "plan"` (with its `goal`) and a `Plan round: N of M`
note (default `1 of 10`). Once its dependencies are done, the
engine reports **ready for planning** rather than allocating a code-worker
worktree. Sequential execution also leaves it to the maintainer.

The runner handles one such entry at a time in its disposable docs-maintainer
checkout, when task work and session writes have settled. Plan For Me reads the
entry's scope, finished-batch reports, current code and remaining goal proof.
The planning commit closes that entry and saves at most **8 new tasks total**
under its goal, including any successor planning task. Owner-only gaps belong
in `Needs decision` with their question; they do not block independent work.

For an unmet goal, a batch with building tasks ends with one open `Kind: plan`
entry, `Plan round: N+1 of M`, depending on every new building task. At round M,
or with no new building task, there is no successor: `BLOCKERS.md` gets one
`### Q-<planning task ID> — Planning stopped` question naming the goal and what
remains. An indexed unmet goal retains or adds an open `Needs decision` task
for the remaining-proof/continuation question, within the same eight-task cap;
closing the plan must not leave that goal without an open task. A goal proven
met by the existing ledger rules needs neither a successor nor a stop question.
Limits, closure, goal membership and successor shape are checked before landing;
an oversized proposal fails as a whole,
never by truncation. An unchanged failed proposal is not called repeatedly.

Planning does not grant code workers access to coordinator files, add a goal
schema, or start another round without an explicit `Kind: plan` entry. Existing
maintainer repair triggers remain available in repositories without these entries.
Offline fixture checks cover scheduling and landing, not real-model plan quality.

## Plugin settings

Source: [`runtime_defaults.py`](../runtime_defaults.py),
[`plugins/defaults.json`](../plugins/defaults.json). Set them per profile with
`hermes -p PROFILE config set KEY VALUE`.

| Key | Default | Meaning |
| --- | --- | --- |
| `plugins.entries.autowork.settings.apply_runtime_defaults` | `true` | Boolean `false` stops the plugin from applying the runtime policy below on load, except the Telegram menu entries, so new bundle commands such as `/blockers` still reach the menu (`config set` stores the word `false` as a boolean). The legacy `…autowork.config.apply_runtime_defaults` is honored when `settings` lacks the key. Setup honors it too and skips the policy and skill-list settings for that profile. Set it before restoring your own values. |

While `apply_runtime_defaults` is not `false`, each plugin load writes these
values whenever they differ, preserving other settings:

| Key | Value written |
| --- | --- |
| `approvals.mode` | `off` |
| `approvals.destructive_slash_confirm` | `false` |
| `approvals.mcp_reload_confirm` | `false` |
| `agent.max_turns` | `unlimited` (no per-turn iteration cap; Hermes quick setup writes `90`) |
| `plugins.entries.autowork.allow_gateway_injection` | `true` |
| `skills.disabled` | Your entries, plus OMH skills outside `omh_keep_skills` in profiles with OMH; bundled toolset skills removed |
| `plugins.entries.autowork.omh_trim` | The OMH skill names the bundle added to `skills.disabled`, so it can remove them later |
| `platforms.telegram.extra.command_menu.priority` | Your entries first, then the workflow commands and the `ui_taste`, `beautify_github_readme`, `impeccable`, `lgtm`, `engineering` and `git_commit_push` skill commands appended; retired bundle names and `autoresearch_*` entries removed. Other menu settings such as the mode and cap are not changed ([`telegram_menu_policy.py`](../telegram_menu_policy.py)). |

Every setup, including `--bundle-only`, also clears the per-platform skill disable
lists, except in opted-out profiles. Full setup additionally applies the `omh` block of `defaults.json`
(memory mode `auto-safe`, TUI and menubar off). See [installation](installation.md#install) for the policy and
[removal](uninstall.md) to restore values.

## Environment variables

| Variable | Read by | Meaning |
| --- | --- | --- |
| `HERMES_HOME` | Setup, skill installer, `install-plugins.sh` | Default Hermes root when `--hermes-home` is absent. A named-profile home (`ROOT/profiles/NAME`) resolves to `ROOT`. Defaults to `~/.hermes`. `/autowork update` uses the running profile's Hermes root the same way. |
| `OMH_HOME` | [`install-omh.py`](../install-omh.py) | An exported or `.env` binding is preserved as the OMH store location; see [memory](memory.md). |
| `PI_AUTOWORK_MERGE_BACKLOG` | [`parallel_dispatch.py`](../pi-autowork/engine/parallel_dispatch.py) `merge_backlog`, `admit` | Finished commits waiting to merge before fresh dispatch can pause; default twice the worker count (16 for 8 workers), `0` disables. Counts slots with commits in `reported` or `integrating`, not held or already integrated work. |
| `PI_AUTOWORK_MERGE_BACKLOG_AFTER` | [`parallel_dispatch.py`](../pi-autowork/engine/parallel_dispatch.py) `merge_backlog` | Oldest finished commit's queue age in seconds before the count gate pauses fresh dispatch; default `1200`. Queue time starts at reporting, not worker launch. Nonnegative integers; invalid settings use their defaults. |
| `PI_AUTOWORK_STALE_HOURS` | [`coordinator.py`](../pi-autowork/pi_autowork/coordinator.py) `set_aside_stale` | Hours since dispatch after which a finished commit still waiting to merge (`reported`, or `integrating` with no review running) is set aside and its task runs fresh on current main; default `24`, `0` disables. Never while a review or batch runs or a batch-passed candidate waits to land. |
| `PI_AUTOWORK_OVERLAP_EVERY` | [`coordinator.py`](../pi-autowork/pi_autowork/coordinator.py) `overlap_idles` | Seconds between DOCS-MAINTAINER re-cuts of tasks waiting on another task's file while worker slots idle; default `1800`. Its Pi job holds the runner loop, so back-to-back re-cuts stopped reviews, landing and dispatch. |
| `PI_AUTOWORK_CHECK_SLOTS` | [`main_check.py`](../pi-autowork/pi_autowork/main_check.py), [`worker.py`](../pi-autowork/pi_autowork/worker.py) | Host-wide full-check concurrency per user: default CPU count divided by 8, rounded down, at least 1; `0` disables admission. Set consistently across runners. Main checks, merged-tree gates and base runs share flock slots; focused worker checks do not. A review's suites are admitted before background main checks waiting with them, each in arrival order; a main check that has waited 30 minutes is admitted in turn with reviews. Waiting reports `waiting for a check slot, N ahead` (running checks plus earlier waiters) in main/worker status. The check and integration timeout budgets exclude slot waiting; check execution keeps its full timeout (`PI_AUTOWORK_VALIDATE_TIMEOUT`, default 3600 s). Does not change `scripts/check.py`'s own job count or the dispatch resource gate. |
| `PI_AUTOWORK_WORKER_CHECK_SLOTS` | [`autowork_run.py`](../pi-autowork/engine/autowork_run.py) | Positive host-wide worker suite/build concurrency per user: default CPU count divided by 4, rounded down, at least 2. Set consistently across runners. Independent of `PI_AUTOWORK_CHECK_SLOTS`; focused tests run directly. |
| `PI_AUTOWORK_COMMAND_TIMEOUT` | [`pi_runtime.py`](../pi-autowork/pi_autowork/pi_runtime.py) | Worker tool-command execution limit, default 1800 s (capped below the overall worker timeout). `autowork-run` slot waiting is excluded; the overall task timeout is not extended. |
| `PI_AUTOWORK_QUIET_WAIT` | [`worker.py`](../pi-autowork/pi_autowork/worker.py) | Seconds a review waits for a quiet window (this repository's main check done and a host check slot free) before rerunning a merged tree's failures one at a time; default 900. Past it, the failures rerun one at a time without a slot instead of queueing behind other runners' full suites. |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_ALLOWED_USERS`, `TELEGRAM_HOME_CHANNEL` | Update menu healing, from each profile's `.env` (not the process environment) | For each distinct bot token, the chats whose leftover command lists the updater checks; see [installation](installation.md#update-all-profiles). |

Once both merge-backlog thresholds are met, fresh tasks show
`wait for N finished commits to merge`. Running workers and restartable/interrupted
work continue; no worker is stopped and the worker-count setting is unchanged.
Fresh admission resumes automatically on a later dispatch cycle once the waiting
commit count falls below the threshold (or the gate is disabled), even after a
coordinator restart. The pause stays in effect while the count remains at or above
the threshold, even if the oldest commit merges first. The runner's
[`health.py`](../pi-autowork/pi_autowork/health.py) records one pause and one resume
announcement per episode, including the recorded integration hold reason when
available. This is a wait, not a request for a decision.

## Files and state

| Path | Owner | Contents |
| --- | --- | --- |
| `ROOT/maintenance/toolset-update/latest.json` | Updater | Latest update receipt: status, revisions, profiles, local edits, backup location, and the gateway restart's state or recorded outcome (`gateway_restart`, `gateway_restart_result`). |
| `ROOT/maintenance/toolset-update/restart.json` | Updater | The last gateway restart the updater requested (process ID), or its deferred-restart waiter (process ID, latest chat-turn count), plus `covers`, the updates that restart will load; used to report progress, avoid overlapping restarts and record the outcome on each covered update. Once finished, also `finished` and the recorded `outcome`, which status shows when a later receipt replaced the covered one. |
| `ROOT/maintenance/toolset-update/pinned/NAME-*/` | `hermes autowork pin` | One pin: `record.json` (profile, link, checkout, revision), the saved `link`, and after unpinning the kept clone (`unpinned-*`). |
| `ROOT/maintenance/toolset-update/run.log` | Updater | Output of updates started with `/autowork update` and of gateway restarts the updater requests; terminal `hermes autowork update` prints to the terminal. |
| `/run/user/UID/autowork-checks-UID/` | Pi runner and worker checks | Shared per-user slot locks and runner FIFO waiter tickets, independent of repository, `$XDG_RUNTIME_DIR` and task `$TMPDIR`; falls back to `/var/tmp/autowork-checks-UID/` when the runtime directory is unavailable. Worker checks use separate `worker-slot-*` locks. `PI_AUTOWORK_CHECK_ROOT` overrides the private directory for fixtures or isolated hosts. Slot locks live with their file descriptors, including in the check subprocess: a dead check cannot leave a stale lock. Do not delete slot/mutex files while runners are active. |
| `tasks/items/`, `tasks/goals/`, `tasks/evidence/` (project) | `autowork tasks`, Autowork | The task store: one file per task and per goal, and the receipts of verified closes. `TODO.archive.md`, where it exists, is frozen history. |
| `docs/roles.json` (project, optional) | Docs Sync | Document role manifest. |
