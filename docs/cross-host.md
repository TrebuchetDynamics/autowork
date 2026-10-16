# Claude Code, Codex and Pi installation

Hermes Toolset provides native packages for four hosts. Claude Code, Codex and Pi
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
claude plugin install hermes-toolset@hermes-toolset
```

Install the published Git source with:

```sh
claude plugin marketplace add TrebuchetDynamics/hermes-toolset
claude plugin install hermes-toolset@hermes-toolset
```

Inside a session, `/plugin marketplace add TrebuchetDynamics/hermes-toolset` and
`/plugin install hermes-toolset@hermes-toolset` do the same; run `/reload-plugins` or
start a new session. Add `--scope project` to the install to record it in the
repository's `.claude/settings.json` for everyone who works there. Invoke the
namespaced skills:

```text
/hermes-toolset:plan-with-me questions only: ask one question about this project
/hermes-toolset:plan-with-me challenge this plan; read-only, no implementation
/hermes-toolset:plan-for-me investigate the next useful improvement; save the plan
/hermes-toolset:docs-sync update the docs and TODO.md
/hermes-toolset:autowork complete the next ready task; commit locally, no push
/hermes-toolset:autoresearch debug the failing test
```

The marketplace entry lists `./adapters/skills/` as the plugin's only skills folder,
so the Hermes-only skills in the repository's root `skills/` folder are never loaded;
the plugin itself ships no hooks, agents, MCP servers or settings. Claude Code copies
the whole repository into its plugin cache, so adapter links into `skills/` resolve
there. Update with `claude plugin marketplace update hermes-toolset` and then
`claude plugin update hermes-toolset@hermes-toolset`; remove with
`claude plugin uninstall hermes-toolset@hermes-toolset` (add the same `--scope` used
to install) and `claude plugin marketplace remove hermes-toolset`. Removal does not
undo repository work or delete plans.

## Codex

Requires a Codex CLI with `codex plugin` support. From this checkout:

```sh
codex plugin marketplace add .
codex plugin add hermes-toolset@hermes-toolset-marketplace
```

Install the published Git source with:

```sh
codex plugin marketplace add TrebuchetDynamics/hermes-toolset --ref main
codex plugin add hermes-toolset@hermes-toolset-marketplace
```

Start a new Codex session in your project. Invoke the namespaced native skills:

```text
$hermes-toolset:plan-with-me questions only: ask one question about this project
$hermes-toolset:plan-with-me challenge this plan; read-only, no implementation
$hermes-toolset:plan-for-me investigate the next useful improvement; save the plan
$hermes-toolset:docs-sync update the docs and TODO.md
$hermes-toolset:autowork complete the next ready task; commit locally, no push
$hermes-toolset:autoresearch debug the failing test
```

Use `$hermes-toolset:docs-sync` in Codex; the Hermes spelling `/docs_sync`
is not a Codex slash command. Adding package files to a Git repository does not
install that plugin into your Codex configuration. After installation, use the
next turn if the client refreshes skill discovery; otherwise start a new session.

Codex uses skill invocation, not Hermes slash-command registration. The adapters
are explicit-only in Codex (`allow_implicit_invocation: false` in each
`agents/openai.yaml`) so installation does not automatically invoke a workflow.
Update a Git install with `codex plugin marketplace upgrade hermes-toolset-marketplace`
(it refreshes Git marketplace snapshots only); remove with
`codex plugin remove hermes-toolset@hermes-toolset-marketplace`. Removal does not
undo repository work or delete plans. The marketplace registration remains until
`codex plugin marketplace remove hermes-toolset-marketplace`.

## Pi coding agent

Requires Pi with package manifests and extension commands, and Node 22 or later. From
this checkout:

```sh
pi install .
```

Install the published Git source with:

```sh
pi install git:github.com/TrebuchetDynamics/hermes-toolset
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
use `$hermes-toolset:plan-with-me` in Codex or `/skill:plan-with-me` in Pi with
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

[`scripts/pi-autowork.sh`](../scripts/pi-autowork.sh) runs Autowork through Pi
one task at a time until you stop it. Pi does one bounded task per run; the script
picks the task, chooses the model, and checks the result in the repository.
`TODO.md` and `goals.json` stay the source of truth.

Prerequisites: Pi with this package installed (above), Node 22, `git`, `jq`,
`python3`, `flock`, `setsid` and `timeout`, and Pi credentials for both models.
`pi auth check --provider openai-codex --model gpt-6.1-sol` and
`pi auth check --provider openrouter --model deepseek/deepseek-v4.1-flash` should
print `ready`; set `OPENROUTER_API_KEY` or sign in through Pi. The script never
reads, prints or changes credentials.

Run it from the checkout of the repository's main branch (`main`, `master` or
`origin/HEAD`'s branch), or name that checkout; it refuses any other branch:

```sh
/path/to/hermes-toolset/scripts/pi-autowork.sh --dry-run
/path/to/hermes-toolset/scripts/pi-autowork.sh
/path/to/hermes-toolset/scripts/pi-autowork.sh --repo ~/git/my-project --until-empty
```

A copy placed in another repository works on that repository from any directory.

The runner uses the hermes-toolset package Pi has installed (found with `pi list`)
for both Autowork and its queue helper, so each run loads the same skills Pi does;
the banner shows that package's path and revision. Install it from the Git source
(`pi install git:github.com/TrebuchetDynamics/hermes-toolset`) and advance it with
`pi update`: a local-path install (`pi install .`) loads whatever your working
checkout holds, unreleased commits included. Without an installed package the runner
loads Autowork from its own checkout with `--skill` and warns.

| Option | Effect |
| --- | --- |
| (none) | Run until stopped; when no task is runnable, wait and check again |
| `--once` | Run at most one task |
| `--until-empty` | Exit when no runnable task remains |
| `--dry-run` | Show the repository, models, queue and lock; change nothing |
| `--repo PATH` | Work on the repository at `PATH` |
| `--interval SECONDS` | Idle check interval (default 60) |
| `--max-cycles N` | Stop after N Pi runs |
| `--no-fallback` | Never use the fallback model |

Environment variables tune the rest, listed by `--help`: the models
(`PI_AUTOWORK_PRIMARY`, `PI_AUTOWORK_FALLBACK`), per-run timeout (90 minutes),
retries (3), consecutive failures before exiting (3), fallback cooldown
(30 minutes), total runtime and reported cost.

How it works:

- **Queue.** Before each run it asks `goals.py next` for the next runnable task, so
  an empty queue costs no model call; it never asks Autowork to find new work.
  Continuous and `--until-empty` runs need `goals.json`; in a TODO-only repository
  only `--once` works, and Autowork picks the task. A changed TODO.md order
  (priority drift) or an unreadable ledger is reported, not treated as an empty queue.
- **Worktrees, merged at the end.** A session starts an integration branch
  `pi-autowork/<session>` from the main branch, in its own worktree under the state
  directory, and reads the queue there. Each task runs in a fresh worktree branched
  from it; Pi is told to commit there and not merge. A finished task (or a partial
  one with commits) joins the integration branch, so its dependents become runnable.
  When the queue empties or the runner stops, the main branch is merged into the
  integration branch, then the main branch fast-forwards to it and the worktrees and
  branches are removed. If that merge conflicts (another writer committed to main),
  Pi resolves it once per session with Git Commit Push; otherwise, or when your
  uncommitted changes in the main checkout would be overwritten, the runner reports
  `Merge pending`, keeps the branch and retries at the next end. Nothing is pushed.
- **One task per run.** Pi is told to execute exactly that task, commit and close
  it. A task counts as done only when its `goals.json` says so. A run that commits
  but leaves the task open continues it next time; a run with no commit skips the
  task until `TODO.md` or `goals.json` changes. Unfinished work stays in its task
  worktree for review while the runner moves on to other tasks.
- **Models.** Every run names the provider and model: `openai-codex/gpt-6.1-sol`
  first. The script switches to `openrouter/deepseek/deepseek-v4.1-flash` for
  30 minutes when the primary is unauthenticated or a run ends on a provider error
  (Pi's JSON events report it even when Pi exits 0), never because a test failed.
  The fallback resumes the same task in the same Pi session, so partial work is
  reconciled rather than redone.
- **Safety.** One runner per repository (a `flock` lock); a second one exits with
  status 3. Your uncommitted changes in the main checkout are never touched; tasks
  run in worktrees. It will not start while a Hermes Autowork cron job targets the
  same repository
  (set `PI_AUTOWORK_ALLOW_HERMES=1` to override). Pushes from Pi's Git commands are
  blocked for the run; this is a guard, not a security boundary, and does not cover
  other tools such as `gh`. Pi runs with `--no-approve`, so a repository's own Pi
  extensions do not load; its `AGENTS.md` still does.
- **Stopping.** Ctrl+C lets the current Pi run end (a second Ctrl+C forces it),
  merges finished tasks into the main branch, keeps the interrupted task's worktree
  and exits 130; the next start resumes that task in the same worktree and session.

State lives outside the repository, in
`${XDG_STATE_HOME:-~/.local/state}/pi-autowork/<repository key>/`: `runner.log`,
`runs.jsonl` (one record per run: task, provider, model, seconds, commits, retries,
fallback reason, tokens, reported cost, redacted error), Pi sessions, and
`session.json` for an unmerged session, `worktrees/` (the integration worktree and
any kept task worktrees), and `inflight.json` while a task is unfinished. Raw Pi output, which contains prompts
and code, is not kept. Reported cost uses Pi's catalog prices; for a subscription
provider such as `openai-codex` it is an estimate, not a bill.

Exit status: 0 done, 1 stopped on a failure or blocker, 2 setup error, 3 another
runner is active, 4 needs attention (merge pending, priority drift, ledger error or
Hermes job), 130 stopped.

## Behavior and verification

The adapters ask native questions, inspect files, maintain TODO.md, and execute
through available host tools. Autowork coordinates a useful slice in the current
session; it does not create timers or promise background workers after the session
ends. Existing goals.json is synchronized through bundled helpers when applicable.
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
