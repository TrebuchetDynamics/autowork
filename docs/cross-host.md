# Claude Code, Codex and Pi installation

Autowork provides native packages for four hosts. Claude Code, Codex and Pi
use the portable adapters, not the Hermes plugin loader. None requires Hermes installed.
These adapters expose 12 skills: Plan With Me, Plan For Me, Docs Sync, Autowork,
Cron Autowork, Autoresearch, Engineering, Impeccable, UI Taste, Beautify GitHub README,
LGTM and Git Commit Push, which also pulls and merges. Grill Me is Plan With Me's
challenge mode, not a thirteenth skill.
Every adapter is explicit-only: Claude Code and Pi read `disable-model-invocation: true`
in its frontmatter and Codex reads `agents/openai.yaml`, so the model never starts a
workflow on its own.
Supporting protocols are bundled and loaded only when needed. Hermes profile
creation, Telegram routing,
Kanban workers, fleet setup, memory and speech integrations remain Hermes-only.

## Claude Code

Requires Claude Code with plugin marketplaces. From this checkout:

```sh
claude plugin marketplace add .
claude plugin install autowork@autowork
```

Install the published Git source with:

```sh
claude plugin marketplace add TrebuchetDynamics/autowork
claude plugin install autowork@autowork
```

Inside a session, `/plugin marketplace add TrebuchetDynamics/autowork` and
`/plugin install autowork@autowork` do the same; run `/reload-plugins` or
start a new session. Add `--scope project` to the install to record it in the
repository's `.claude/settings.json` for everyone who works there. Invoke the
namespaced skills:

```text
/autowork:plan-with-me questions only: ask one question about this project
/autowork:plan-with-me challenge this plan; read-only, no implementation
/autowork:plan-for-me investigate the next useful improvement; save the plan
/autowork:docs-sync update the docs and TODO.md
/autowork:autowork complete the next ready task; commit locally, no push
/autowork:autoresearch debug the failing test
```

The marketplace entry lists `./adapters/skills/` as the plugin's only skills folder,
so the Hermes-only skills in the repository's root `skills/` folder are never loaded;
the plugin itself ships no hooks, agents, MCP servers or settings. Claude Code copies
the whole repository into its plugin cache, so adapter links into `skills/` resolve
there. Update with `claude plugin marketplace update autowork` and then
`claude plugin update autowork@autowork`; remove with
`claude plugin uninstall autowork@autowork` (add the same `--scope` used
to install) and `claude plugin marketplace remove autowork`. Removal does not
undo repository work or delete plans.

## Codex

Requires a Codex CLI with `codex plugin` support. From this checkout:

```sh
codex plugin marketplace add .
codex plugin add autowork@autowork-marketplace
```

Install the published Git source with:

```sh
codex plugin marketplace add TrebuchetDynamics/autowork --ref main
codex plugin add autowork@autowork-marketplace
```

Start a new Codex session in your project. Invoke the namespaced native skills:

```text
$autowork:plan-with-me questions only: ask one question about this project
$autowork:plan-with-me challenge this plan; read-only, no implementation
$autowork:plan-for-me investigate the next useful improvement; save the plan
$autowork:docs-sync update the docs and TODO.md
$autowork:autowork complete the next ready task; commit locally, no push
$autowork:autoresearch debug the failing test
```

Use `$autowork:docs-sync` in Codex; the Hermes spelling `/docs_sync`
is not a Codex slash command. Adding package files to a Git repository does not
install that plugin into your Codex configuration. After installation, use the
next turn if the client refreshes skill discovery; otherwise start a new session.

Codex uses skill invocation, not Hermes slash-command registration. The adapters
are explicit-only in Codex (`allow_implicit_invocation: false` in each
`agents/openai.yaml`) so installation does not automatically invoke a workflow.
Update a Git install with `codex plugin marketplace upgrade autowork-marketplace`
(it refreshes Git marketplace snapshots only); remove with
`codex plugin remove autowork@autowork-marketplace`. Removal does not
undo repository work or delete plans. The marketplace registration remains until
`codex plugin marketplace remove autowork-marketplace`.

## Pi coding agent

Requires Pi with package manifests and extension commands, and Node 22 or later. From
this checkout:

```sh
pi install .
```

Install the published Git source with:

```sh
pi install git:github.com/TrebuchetDynamics/autowork
```

Use `/reload` in an existing Pi session, or start a new one inside your project.
Local installs refer to this checkout; keep it in place. The extension registers:

```text
/plan_with_me questions only: ask one question about this project
/grill_me challenge this plan; questions only, no implementation
/plan_for_me investigate the next useful improvement; save the plan
/docs_sync update the docs and TODO.md
/autowork complete the next ready task; commit locally, no push
/autoresearch_debug diagnose the failing test
```

All 13 `/autoresearch_<protocol>` commands are available. The other commands are
`/cron_autowork` (scheduling guidance through host capabilities, not a Hermes timer),
`/autoresearch`, `/engineering`, `/impeccable`, `/ui_taste`, `/beautify_github_readme`,
`/lgtm` and `/git_commit_push` (`/git_commit_push pull` or `merge <branch>` integrates
upstream changes). Native `/skill:<name>` invocation is also
available; skill names use hyphens. Command arguments remain literal prompt text.
`/grill_me` loads Plan With Me with explicit challenge mode and preserves the
request unchanged. The old standalone `grill-me` skill is no longer discoverable;
use `$autowork:plan-with-me` in Codex or `/skill:plan-with-me` in Pi with
`challenge` in the request. Autoresearch stays independent; its `plan` selector
routes to Plan For Me, which reads the pinned plan protocol directly, never back
through Autoresearch. All other selectors retain their shipped protocols.
A command entered during an active turn is queued as a follow-up, not injected as
shell code. A same-name third-party skill keeps the first one discovered and Pi
warns; same-name extension commands are all kept but renamed `/name:1`, `/name:2`
without a warning. Check `/` completions rather than assuming this package replaced them.

Use Pi's package controls (`pi list`, `pi update --extensions`, `pi remove <source>`)
for management. Removing the package leaves repository documents and commits intact.

### Run Autowork continuously

[`scripts/pi-autowork.sh`](../scripts/pi-autowork.sh) keeps Autowork running through
Pi until you stop it. It drives the toolset's own
[Parallel Autowork engine](../skills/autowork/references/parallel-workers.md): the
engine picks independent, dependency-ready tasks, runs each in its own Git worktree,
integrates results one at a time and closes a task only after it is verified. The
script supplies Pi workers, model choice and fallback, an independent review,
budgets, a session branch merged into the main branch, locking and a service.
`TODO.md` (and `goals.json` when present) stay the source of truth.

Prerequisites: Pi with this package installed (above), Node 22, `git`, `jq`,
`python3`, `flock` and `timeout`, Linux (the engine identifies workers through
`/proc`), and Pi credentials for both models.
`pi auth check --provider openai-codex --model gpt-6.1-sol` and
`pi auth check --provider openrouter --model deepseek/deepseek-v4.1-flash` should
print `ready`; set `OPENROUTER_API_KEY` or sign in through Pi. The script never
reads, prints or changes credentials.

Run it from the checkout of the repository's main branch (`main`, `master` or
`origin/HEAD`'s branch), or name that checkout; it refuses any other branch:

```sh
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --dry-run
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --status
```

It uses the autowork package Pi has installed (found with `pi list`) for the
engine and skills; the banner shows that package's path and revision. Install it from
the Git source (`pi install git:github.com/TrebuchetDynamics/autowork`) and
advance it with `pi update`: a local-path install loads whatever your working
checkout holds, unreleased commits included.

| Option | Effect |
| --- | --- |
| (none) | Run until stopped; when no task is runnable, wait and check again |
| `--once` | Run one task |
| `--until-empty` | Exit when no runnable task remains |
| `--workers N` | Most tasks run at once, 1 to 8 (default 8); free memory and load decide how many start |
| `--dry-run`, `--status` | Show the repository, models, budget, session and each task's state; change nothing |
| `--repo PATH` | Work on the repository at `PATH` |
| `--interval SECONDS` | Idle check interval (default 60) |
| `--max-cycles N` | Start at most N workers, then finish |
| `--no-fallback` | Never use the fallback model |
| `--allow-hermes` | Run beside a Hermes Autowork cron job on the same repository |
| `--install-service`, `--remove-service` | Run it as a systemd user service (below) |

Environment variables tune the rest (`--help` lists them): the models, worker and
review timeouts (90 and 30 minutes), `PI_AUTOWORK_VALIDATE` (a command that must pass
on every integrated task before the review), `PI_AUTOWORK_REVIEW=0` (skip the Pi
review), retries, the failure limit, the fallback cooldown, total runtime,
`PI_AUTOWORK_MAX_COST` with `PI_AUTOWORK_COST_WINDOW` (hours, default 24), the
free memory each worker needs (`PI_AUTOWORK_MIN_FREE_MB`, default 3000) and
`PI_AUTOWORK_INFER_TOUCHES=0` (do not propose `Touches:`).

The default way to run pi-autowork is a **systemd user service** per repository,
managed with the `autowork` command ([pi-autowork](../pi-autowork/README.md#the-autowork-command)).
Bare `autowork` opens the live TUI, where `d` browses directories and starts a
service for a repository that has `TODO.md` and `goals.json` on its main branch:

```sh
autowork start                 # from the repository: install (if needed) and start its service
autowork                       # the TUI: every runner, its workers, blockers and log
autowork ls                    # one line per runner
autowork logs -f my-project    # follow its journal
autowork pause my-project      # stop it and keep it off (also after a reboot); resume starts it
autowork model my-project openai-codex/gpt-6-luna   # this service's Pi model (autowork models)
autowork remove my-project     # stop and remove the service; state and worktrees stay
```

`autowork start` runs the script's own installer, which you can also call directly
(run it from the repository, or add `--repo PATH`):

```sh
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --install-service
~/.pi/agent/git/github.com/TrebuchetDynamics/autowork/scripts/pi-autowork.sh --remove-service
```

Each repository gets `pi-autowork@<repository name>.service`, for example
`pi-autowork@my-project` for `~/git/my-project`. The script writes one template unit,
`~/.config/systemd/user/pi-autowork@.service`, and `~/.config/pi-autowork/<name>.env`
holding the repository path, the installing shell's `PATH`, `--workers`,
`--allow-hermes`, `--no-fallback` and any `PI_AUTOWORK_*` settings, then enables and
starts the unit. It refuses a name another repository's service already uses, and
replaces a unit an earlier release named after the escaped path.
Stopping sends SIGINT, the runner's Ctrl+C. Crashes and kills restart after a
minute; the runner's own exits (failures, another runner, needs attention) do not.
Without user lingering (`loginctl enable-linger $USER`) the service stops at logout.

`autowork run` runs a repository's runner in the foreground of the current terminal
for debugging; the per-repository runner lock keeps it and the service off one
repository at once. Each service has its own model (`PI_AUTOWORK_PRIMARY` and
`PI_AUTOWORK_FALLBACK` in its settings file, set with `autowork model`), so one
repository can run on `openai-codex/gpt-6-luna` and another on
`openrouter/deepseek/deepseek-v4.1-flash`; a reinstall keeps the chosen model.
Reinstall after changing settings. The runner keeps itself current: while it has no
task in flight, at most once per `PI_AUTOWORK_UPDATE_INTERVAL` seconds (default 600;
`0` turns it off) it checks for a new release and runs `pi update` for its autowork
package, one runner at a time across repositories. It installs only a release that,
read from Git first, declares it can read the current execution state. It prefers a
moment when no runner on the machine has work in flight, but waits for one at most
`PI_AUTOWORK_UPDATE_WAIT` seconds (default 1800) from when the release was first seen,
looking again every 5 minutes; busy runners rarely all pause at once, and they would
otherwise never update. It logs why it waits once. When the toolset revision changed, by that or any other update,
a running runner restarts itself on the new release at its next cycle and resumes its
session; an update whose script does not parse is logged and the running code kept.
Remembered `NONE` answers from the `Touches:` pass belong to the prompt that produced
them, so a changed prompt asks those tasks again, and a pass that gave no answer is
retried within the hour.

Touches the runner inferred are a guess. When a worker's commit is held only for
changing files outside them, the runner widens its own guess to those files once and
the engine verifies the same commit again; Touches a person wrote or edited are never
widened, and the hold then waits for a person with its cause shown by `--fleet`. The
same applies when a worker stops to ask for files outside its inferred Touches: the
runner widens them and the worker resumes in its worktree with its changes intact.
Touches inferred by older runs are recognized from the runner's own commits.

When the reviewer changes (its code, `PI_AUTOWORK_VALIDATE` or `PI_AUTOWORK_REVIEW`), the
runner sends every commit an earlier reviewer held back for review once, by itself,
even a task with no attempt left; the same reviewer never reviews a commit twice.

A held task is answered by editing its TODO.md entry (scope, Touches, acceptance,
dependencies or a decision line): the runner notices the changed entry and runs the
task fresh, keeping its earlier work on `-set-aside-N` branches. No command is needed.

Tasks other sessions marked `in_progress` are left alone until they are verifiably
idle for `PI_AUTOWORK_CLAIM_IDLE` seconds (6 hours; `0` never adopts): no change to
the task's entry, branches or worktrees and no live agent working there. An active session in
the main checkout holds off only claims whose `Touches:` files it holds open (or
claims without `Touches:`). The runner
then takes the task over (never one a TODO.md note holds: kept open, on hold, not to be
dispatched, or awaiting an authority or approval), logs `adopted an idle claim`, and its worker is pointed at
any earlier work to reuse, which it never modifies.

When TODO.md's order changed since goals.json recorded it, a runner records the new
order in its session (`goals.py reorder` with the expected revision, committing only
goals.json) and selects again; if that is refused it reports why and waits. In
service mode an engine error never ends the runner: it is reported once, shown by
`--fleet`, and checked again each interval.

A fresh task worktree has none of the main checkout's gitignored files. List any a
task needs (comma-separated, repository-relative) in `PI_AUTOWORK_LINK_PATHS` in the
repository's settings: before a worker or reviewer starts, each is mirrored from the
main checkout (real directories, hard-linked files, so tools such as `find` see an
ordinary tree), but only where Git ignores it and the mirror shows up as no change.
Hard links share file contents, so the copy is cooperative, not write-protected: a
tool that edits a file in place edits the original. List only what tasks read.

Per-repository settings live in `~/.config/pi-autowork/<repository>.env`
(`PI_AUTOWORK_ENV_DIR`), the file `--install-service` writes. Every launcher reads it:
the service, `autowork run` and a terminal; variables already set in the environment
win. Disabling a service (`systemctl --user disable --now pi-autowork@<name>`) keeps it.

The runner follows the plan, not a clock: while it waits (queue empty, everything
blocked, or a failure pause), a change to `TODO.md`, `goals.json`, `BLOCKERS.md`, the
TODO archive or a new commit on the main branch ends the wait within seconds, once the
change has been quiet for `PI_AUTOWORK_PLAN_SETTLE` seconds (default 3). The log says
`TODO.md changed; checking now`, and the next cycle dispatches newly runnable tasks
and re-queues answered held ones. `--interval` is only the longest wait. Watching is
file status checks once a second; it calls no model.

Planning never blocks delivery: when the main checkout's only uncommitted changes are
planning files (TODO.md, goals.json, BLOCKERS.md, the TODO archive), untouched for
`PI_AUTOWORK_PLANNING_QUIET` seconds (600) and open for writing nowhere, the runner
commits exactly those as `docs(tasks): owner planning (pi-autowork)` before its merge.
Any other uncommitted file keeps the merge pending, and the message says why the
planning was left alone.

Questions for the owner live in the repository's `BLOCKERS.md`, in a block the runner
maintains under `## Active` (between `<!-- pi-autowork:questions:start -->` and
`<!-- pi-autowork:questions:end -->`), never in a chat. Each names the task, what it
needs and exactly how to answer, easiest first; `/blockers` (also `/autowork blockers`)
treats these entries as evidence, reconciles routine planning issues and asks only
for genuinely missing owner decisions or inputs. It preserves candidate work and
existing integration authority instead of asking which session should own delivery.
Resolving an entry means editing the task's TODO.md entry; the question leaves the block once its cause is gone. Writing the block costs no model call.

`pi-autowork.sh --fleet` shows every runner on the machine in one line each: its
service state, health (`working`, `blocked`, `stalled`, `paused`, `idle`, or `not
running`/`not cycling` when the process is gone or silent) and, when it cannot
progress, the root blockers: a held task, another session's claim, an outside
condition or a dependency cycle, each with how many tasks it holds up. `--status`
shows the same health for one repository. A runner with nothing running while work
waits for `PI_AUTOWORK_STALL_AFTER` seconds (1800) logs one `STALLED` line with
those roots, at warning priority in the journal, and again only if they change.

A task a worker reported blockers for, or one held with no attempt left, waits for a
person and blocks only the tasks that depend on it. Once its cause is
resolved, `pi-autowork.sh --repo PATH --set-aside TASK` asks that repository's
running runner to retire the slot: its earlier work stays on `-set-aside-N`
branches and worktrees, and the task runs fresh.

How it works:

- **Tasks and workers.** Each cycle the engine plans the queue: a task runs beside
  others only when it declares `Touches:` paths that do not overlap theirs, shares no
  `Resources:` and has its dependencies closed; anything else runs alone, and TODO.md
  priority decides order. An empty queue costs no model call, and nothing asks
  Autowork to invent work. A task another session marked `in_progress` is never
  dispatched and holds back tasks that depend on it or declare overlapping `Touches:`,
  but not unrelated ones. So that most tasks can run in parallel, the runner asks a
  read-only Pi pass to plan the file scope of each runnable task that lacks
  `Touches:` and records the paths it proposes in the session branch; the engine then
  holds any change outside them. Scope means the files a task edits, so device- or
  screenshot-verified work still gets paths. A task answered `NONE` (it edits no
  repository file, or files across most of the repository; the log shows the reason)
  runs alone and is asked again after 24 hours. A task without `Touches:` may
  change any file except the coordinator's and other slots'. When tasks remain but none can start, the log says `No task
  can start now` with the reasons; the runner keeps waiting, and `--once` or
  `--until-empty` exit 1 instead of 0. Each worker is `pi-autowork.sh --worker`: Pi with an
  explicit provider and model, `--no-approve`, the engine's one-task prompt and a
  session per task attempt. Workers never pick tasks or edit `TODO.md`,
  `TODO.archive.md`, `goals.json` or `CHANGELOG.md`; only the coordinator does.
- **Verified integration.** A worker's commit and report are claims. The engine
  merges each reported task into the session branch one at a time and runs
  `pi-autowork.sh --verify`: `PI_AUTOWORK_VALIDATE` if set, then a separate read-only
  Pi review that runs the task's checks against its acceptance; a reviewer that
  changes any file fails. Only then is the task closed and its TODO update committed.
  A failed review, a conflict or a file outside `Touches:` holds the task; it keeps
  its worktree and gets one fresh retry, and a second failure stays held. If the
  retry of a scope hold makes no commit, the first commit is verified once more.
- **Task states.** `--status` and the log show each task as `pending`, `running`,
  `implemented` (reported), `verifying`, `integrated`, `done` or `failed` (held,
  interrupted or released, with the reason), mapped from the engine's slot states;
  the TODO.md and `goals.json` contracts do not change.
- **Session, merged at the end.** The engine works on an integration branch
  `pi-autowork/<session>` in a worktree under the state directory. After each closed
  task (once nothing else is in flight), and when the queue drains or the runner
  stops, the main branch is merged into it and the main checkout fast-forwards; a
  drained session's worktree and branch are removed. A new main commit (an owner's
  plan) is also merged into an idle session at once, so the runner plans from it. If
  `main` moved and conflicts, Pi resolves the merge with Git Commit Push, once per
  main revision; otherwise, or when your uncommitted changes in the main checkout
  would be overwritten, the runner reports `Merge pending`, shows it as its blocker in
  `autowork` and keeps the branch for the next attempt.
- **Push.** After a merge the runner pushes main to its upstream (`main@{u}`):
  fast-forward only, never forced. A rejected push fetches the upstream, merges it
  into the session, fast-forwards main and tries once more; a failure is logged once
  and the next merge retries. A main without an upstream is left local. Workers and
  Pi tools still cannot push. `PI_AUTOWORK_PUSH=0` turns pushing off.
- **Models.** `openai-codex/gpt-6.1-sol` first; the script switches to
  `openrouter/deepseek/deepseek-v4.1-flash` for 30 minutes when the primary is
  unauthenticated or a run ends on a provider error (read from Pi's JSON events, even
  when Pi exits 0), never because a test failed. The fallback resumes the same Pi
  session, so partial work is reconciled rather than redone. All workers share the
  cooldown.
- **Budget.** `runs.jsonl` records every Pi run (workers, reviews and merges, from
  every process). `PI_AUTOWORK_MAX_COST` limits the reported cost within the last
  `PI_AUTOWORK_COST_WINDOW` hours, so a restart does not reset it; at the limit no new
  worker or Pi run starts and running workers finish.
- **Hermes.** By default the runner refuses a repository that a Hermes Autowork cron
  job also works on. With `--allow-hermes`, the two share the engine's repository
  lease: while Pi's coordinator holds it, Hermes Autowork's claim returns `BUSY`, and
  while Hermes holds a task the runner waits. They never own the same task or write
  the ledger at once; ledger edits also go through `goals.py`'s repository lock. A
  Hermes job that commits or merges outside Autowork can still move `main`, which
  the end-of-session merge handles as above.
- **Safety.** One runner per repository (a `flock` lock); a second one exits with
  status 3. Your uncommitted changes in the main checkout are never touched. Pushes
  from the runner's and workers' Git commands are blocked; this is a guard, not a
  security boundary, and does not cover other tools such as `gh`. Pi runs with
  `--no-approve`, so a repository's own Pi extensions do not load; its `AGENTS.md`
  still does.
- **Stopping and recovery.** Ctrl+C (and a service stop or restart) first marks the
  running workers paused, then interrupts their process groups, merges finished work
  into the main branch and exits 130 within seconds. On the next start the engine
  reconciles: a paused worker resumes in its worktree on the same attempt, so a stop
  never spends a task's retry or holds its second attempt; other interrupted or
  released tasks restart once in the same worktree, a dead worker with a commit is
  integrated, and live workers are adopted rather than duplicated.

State lives outside the repository, in
`${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`: `runner.log`,
`runs.jsonl` (one record per Pi run: role, task, provider, model, seconds, retries,
fallback reason, tokens, reported cost, redacted error), Pi sessions, `session.json`
and `worktrees/` (the session's integration worktree and the engine's task
worktrees). The engine's slots and journal live under `.git/autowork-execution/`.
Raw Pi output, which contains prompts and code, is not kept. Reported cost uses Pi's
catalog prices; for a subscription provider such as `openai-codex` it is an
estimate, not a bill.

Exit status: 0 done, 1 stopped on a failure or blocker, 2 setup error, 3 another
runner is active, 4 needs attention (merge pending, repository busy, priority drift,
an engine refusal or a Hermes job), 130 stopped.

## Behavior and verification

The adapters ask native questions, inspect files, maintain TODO.md, and execute
through available host tools. Autowork coordinates a useful slice in the current
session; it does not create timers or promise background workers after the session
ends.

Opt-in [parallel workers](../skills/autowork/references/parallel-workers.md)
(`--parallel N`) start one headless worker per independent task. Linux only:

| Coordinator host | Parallel workers | Worker command |
| --- | --- | --- |
| Hermes | Yes, built-in template | `hermes chat --query-file … --oneshot --in WORKTREE --run-budget …` |
| Codex | Yes, built-in template | `codex exec -C WORKTREE --sandbox workspace-write --add-dir GIT_COMMON_DIR -` |
| Pi | Yes, built-in template | `pi -p @PROMPT` |
| Claude Code | Only with `--worker-command` | none built in; otherwise `SEQUENTIAL_FALLBACK` |
| Other or undetected | Only with `--worker-host` or `--worker-command` | otherwise `SEQUENTIAL_FALLBACK` |

Templates add no approval or sandbox bypass flags, and a missing worker CLI also
falls back to sequential execution. These templates are checked against each CLI's
`--help` and with fake workers offline; real model workers are not yet qualified. Existing goals.json is synchronized through bundled helpers when applicable.
Python 3 is needed for those helpers; a questions-only interview needs no Python.

No package installs external integrations, modifies approval policies, copies
credentials, or changes model/memory settings. Host permissions and repo instructions
still apply. Installing the package exposes skills, not proof of an executed workflow.
Host-specific commands in vendored research protocols are adapted to
native tools; the portable host contract wins over foreign runtime instructions.

Offline checks:

```sh
python3 -m pip install -r requirements-test.txt
python3 -m unittest discover -s tests -p test_portable_package.py
node --test tests/portable_pi.test.mjs
claude plugin validate . --strict   # needs the Claude Code CLI
```

Validated locally with Claude Code 2.1.300: `claude plugin validate . --strict`
passed, and a marketplace add and install into an isolated configuration directory
listed exactly the 13 adapter skills (no root `skills/` entries, hooks, agents or MCP
servers) with all adapter links resolving in the installed copy. No Claude Code model
session has run a workflow from it yet.

Validated locally with Codex CLI 0.162.1 and Pi 1.2.0: native marketplace/plugin
and Pi installation into isolated temporary homes, Codex app-server skill discovery
and Pi's installed resource loader discovered 11 portable skills and Pi loaded 25
commands, including `/grill_me` compatibility and all 13 research selectors. That run
predates UI Taste, Beautify GitHub README and the Git Pull Merge merge into Git Commit
Push: the package now ships 12 skills and 26 Pi commands, checked offline by `tests/portable_pi.test.mjs`; no live Codex or Pi
install has been rerun. Archive extraction tests check installed references, literal
arguments and queued commands without checkout files. No credentials or configured live accounts are used. These are
tested versions, not an established minimum-version guarantee.
These checks do not prove model output quality, Git delivery or Telegram execution.
The model smoke test is the questions-only invocation above: one useful question,
no repository edits. Follow it with planning and a bounded disposable-repo task
when you want to qualify end-to-end behavior with your configured model.

Host documentation: [Claude Code plugins](https://code.claude.com/docs/en/plugins/manifest-reference),
[Claude Code marketplaces](https://code.claude.com/docs/en/plugins/marketplace-reference),
[Codex plugin schema](https://github.com/openai/codex/blob/main/codex-rs/core-plugins/src/manifest.rs),
[Pi packages](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/packages.md),
[Pi extensions](https://github.com/earendil-works/pi/blob/main/packages/coding-agent/docs/extensions.md).
