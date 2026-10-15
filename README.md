# Hermes Toolset

<p align="center">
  <img src="./assets/readme/hero.svg" width="100%" alt="Hermes Toolset: turn repository goals into verified changes, tracked in TODO.md. A TODO.md card shows a completed task, the next ready task that /autowork picks up, and a queued one.">
</p>

Plan with the agent (`/plan_with_me`), let it investigate and decide
(`/plan_for_me`), and have it execute the next ready task (`/autowork`). Plans,
priorities, acceptance checks and progress stay in your repository's TODO.md, so
the next run—yours, a teammate's or a scheduled job's—picks up where the last
one left off.

It runs in Hermes CLI and Telegram, installs into one profile or a whole fleet,
and also ships native packages for [Claude Code, Codex and Pi](docs/cross-host.md).

## How it works

<p align="center">
  <img src="./assets/readme/workflow.svg" width="100%" alt="Plan with /plan_with_me or /plan_for_me, queue the tasks in TODO.md in your priority order, execute the next ready task with /autowork, and get a report; the next run takes the next ready task.">
</p>

```text
/plan_with_me Design a caching layer for this repository
/autowork Implement the next ready task; commit locally, no push
```

1. **Plan.** `/plan_with_me` researches the repository, asks you about the choices
   only you can make, and saves the decisions and tasks. `/plan_for_me` does the
   same without the interview, recording each choice it made as the planner's call.
2. **Queue.** Accepted work becomes TODO.md tasks, in your priority order. Docs Sync
   (`/docs_sync`) keeps docs, TODO.md and its `goals.json` index consistent.
3. **Execute.** `/autowork` selects the next ready task, implements it, runs its
   checks and commits locally. It never pushes or deploys unless you say so.
4. **Repeat.** `/cron_autowork 15m` schedules Autowork. Telegram-routed jobs post
   a start message (when the start-notice script is attached) and a report each run.

A runnable task has an ID, sits under `## Now` or `## Next`, and has unique Scope,
Acceptance and Checks fields (`Verification:` also works, but not both). An
arbitrary checklist line is not a task:

```markdown
## Now

- [ ] CACHE-01 — Add bounded cache storage
  Status: open
  Scope: src/cache only; no new dependencies.
  Acceptance: entries beyond the limit are evicted oldest-first.
  Checks: `pytest tests/test_cache.py`
  Dependencies: None.
```

**TODO.md order is the priority.** To reprioritize, move whole task blocks and run
`goals.py reorder <repo>`. Until you do, Autowork's default selection stops with
`PRIORITY_DRIFT` rather than run the old order (a task you name explicitly still
runs). A `goals.json` without a recorded order reports `UNMIGRATED` until a one-time
`goals.py bootstrap-order` (dry-run first). Dependencies and focus decide which
eligible task runs; they never rewrite your order.

A typical Autowork report, illustrative rather than a test receipt:

```text
CACHE — COMPLETED; 1 TODO task completed
Task: TODO.md CACHE-01 — Add bounded cache storage.
Changed: cache implementation, tests and docs/cache.md.
Checks: cache acceptance tests passed; required review passed.
Next: CACHE-02 — Verify eviction behavior [eligible, not started].
Delivery: local commit <SHA>; not pushed, as requested.
```

**COMPLETED** means verified acceptance and closure, not just a passing build;
a verified active run reports **RUNNING**. A genuine blocker leads with **Action
needed from you:** the exact action, why, and what resumes afterward. See
[reporting](skills/autowork/references/dispatch-and-reporting.md) and the
[TODO work-center contract](skills/shared/TODO-WORKCENTER.md).

Contributors need none of this machinery: read README.md, AGENTS.md and TODO.md,
pick a ready task, make the change in ordinary Git, run its checks and submit for
review. See [contributing](docs/contributing.md#work-on-a-repository-task).

## What you can do

| Goal | Example | What happens |
| --- | --- | --- |
| Plan together | `/plan_with_me Design a caching layer` | Asks focused questions, then saves decisions and tasks. `questions only` writes nothing. |
| Challenge a plan | `/plan_with_me Challenge this cache design` | Tests assumptions before implementation. |
| Let it plan | `/plan_for_me Reduce cache latency` | Investigates, chooses an approach and saves tasks; does not implement. |
| Maintain docs and tasks | `/docs_sync Record the accepted cache design` | Updates docs and turns accepted work into tasks with acceptance and dependencies. |
| Develop | `/autowork Implement the accepted cache spec` | Executes and verifies one useful slice; no push or deploy implied. |
| Schedule development | `/cron_autowork every 30 minutes for this repo; no push` | Creates or updates one Autowork job and verifies it; with a cadence, a paused job resumes. |
| Continue approved work | `/lgtm` | Continues the agreed work without asking again, honoring limits such as "no push". |
| Deliver | `/git-commit-push only src/cache` | Validates, commits and pushes; add `no push` for local commits. |
| Integrate upstream | `/git-pull-merge` | Runs the repository's pull and merge workflow. |
| Set up a profile | `/profile-create` | Guides profile creation and shared-toolset setup. |
| Update the bundle | `/toolset update` | Updates every profile; see [updating](#updating). |
| Inspect | `/toolset list` | Lists registered commands and their owners. |

Planning saves its results by default; `read-only`, `chat-only`, `no-write` or
`--dry-run` writes nothing, and planning never starts implementation or a schedule.
Autowork uses a ready task directly and only calls bounded research for unresolved
questions. With an empty queue it inspects the repository and records a justified
task instead of inventing busywork.

**Command spelling.** Telegram uses underscores and its menu shows `/plan_with_me`,
`/plan_for_me`, `/docs_sync`, `/autowork`, `/cron_autowork`, `/ui_taste`,
`/beautify_github_readme`, `/impeccable` and `/lgtm`; other bundled commands such as `/git_commit_push` work
when typed. In CLI chat the three planning
and docs commands accept underscores or hyphens; other commands use hyphens
(`/cron-autowork`, `/autoresearch:plan`). Older spellings (`/autoresearch`,
`/autoresearch_plan`, `/autoresearch_<protocol>`) still run but are not advertised.
See [commands and workflows](docs/workflows.md).

**Bundled skills.** The workflows draw on the complete
[Impeccable design skill](skills/impeccable/SKILL.md), Uizze's
[UI Taste playbooks](skills/ui-taste/SKILL.md), the
[Beautify GitHub README](skills/beautify-github-readme/SKILL.md) skill and 25 pinned
[engineering protocols](skills/engineering/SKILL.md), loaded one technique at a
time when a task needs it. Loading a skill is not proof it was applied; application
receipts name the protocol and the actual decision or check.

## Read before installing

These defaults apply to Hermes; the [Claude Code, Codex and Pi adapters](docs/cross-host.md)
keep their hosts' settings. **They are designed for an autonomous fleet, not a
policy-neutral command bridge.**

- Full setup targets **every existing live profile**. There is no general
  `--profile` selector; `--hermes-home` selects a Hermes installation root.
- Loading the plugin sets `approvals.mode: off`, disables destructive slash-command
  and MCP-reload confirmations, removes the per-turn iteration cap
  (`agent.max_turns: unlimited`) and enables gateway injection in its owning profile.
  Explicit deny rules and Hermes hard blocks remain. Setup also clears disabled-skill lists.
- Full setup installs external integrations and selects **OMH memory with auto-safe
  capture** in separate profile stores. Conflicting stores are refused; another
  selected memory provider is left in place, and OMH memory stays off until you clear it.
- External imports are **not fully locked**. Some are pinned; others follow current
  upstream sources. Scans or missing dependencies can leave setup incomplete.
- There is **no automatic restoration of previous configuration** on uninstall.
  Back up profile configurations first; see [removal and recovery](docs/uninstall.md).

The runtime-policy opt-out prevents policy changes **during plugin loading and
setup**. Full setup still applies OMH memory defaults and external integrations;
there is currently no policy-neutral full-installation mode. See
[installation](docs/installation.md), and [memory and retained data](docs/memory.md)
before enabling memory capture.

## Install

| Path | Scope | External integrations | Policy effects |
| --- | --- | --- | --- |
| Native Hermes plugin | Selected Hermes profile | Manifest lists OMH, Ponytail and speech as advisory | Plugin load applies runtime defaults and provisions missing bundled skills |
| `bash install.sh --bundle-only` | All existing live profiles | Skips external-source setup | Applies bundle defaults except in opted-out profiles |
| `bash install.sh --yes-deps` | All existing live profiles | OMH, Ponytail, speech, Graphify | Applies defaults and OMH setup |

Command registration does not need a memory or speech service. There is currently
no separate minimal, policy-neutral Hermes package.

### Try the native plugin in one profile

These commands use the default profile; for a named profile add `-p work` after
`hermes` throughout. Native installation does not install the advisory
dependencies, and the plugin loads with a warning when they are absent.

```sh
hermes plugins install TrebuchetDynamics/hermes-toolset
hermes plugins enable hermes-toolset
hermes toolset doctor --core
```

Loading still applies the runtime policy above; this is not a policy-preserving
trial. `hermes toolset setup --yes-deps --dry-run`, then without `--dry-run`, adds
the full stack—and **expands setup to every live profile**, even when launched
with `-p PROFILE`.

### Fleet setup from source

Prerequisites: an existing Hermes installation with a configured model, Git, Bash
and Python 3.12 for setup and tests (Hermes uses its managed interpreter). Check the
[verified compatibility record](docs/testing.md#compatibility). Telegram needs its
normal Hermes bot configuration. After reviewing the effects above and backing up
configuration:

```sh
git clone https://github.com/TrebuchetDynamics/hermes-toolset.git
cd hermes-toolset
bash install.sh --bundle-only --dry-run
bash install.sh --bundle-only
```

Keep the checkout: the installed plugin links to it. Each profile reports `status`
`ready` or `incomplete`, and a separate `gateway` field (`commands_reloaded`,
`not_running`, `deferred_by_request`, `unreachable` or `reload_incomplete`). Add
external integrations later with `bash install.sh --yes-deps` (needs `uv` unless the
OMH and Graphify CLIs are installed). Note that **CLI startup can apply runtime
defaults before [preflight](docs/installation.md#preflight-before-fleet-writes),
even with `--dry-run`**; `bash install.sh --yes-deps --dry-run` previews without
booting Hermes.

## First use in your project

Open **your project**, not the Toolset checkout (keep `-p PROFILE` if you installed
into a named profile):

```sh
hermes toolset doctor --core
cd /path/to/your-project
hermes
```

`--core` checks bundled skill and command registration; missing external
integrations are listed separately. Plain `doctor` checks the full stack (`--json`
for automation). Neither runs a model or verifies live messaging. In the new chat:

```text
/toolset list
/plan_with_me questions only: help me clarify a caching improvement; ask one question, then stop
```

Expected first success: the agent asks one relevant question and changes no files.
This needs only the bundled skills and your configured model—a live smoke check you
perform, not something the automated tests prove. Then try the
[core-only requirements interview](docs/onboarding.md#core-only-requirements-interview)
or the [full-workflow exercise](docs/onboarding.md#optional-see-decisions-become-a-task),
which saves docs and a TODO.md task. See [onboarding](docs/onboarding.md) for
Telegram checks and project binding. A profile is not a filesystem sandbox.

## Updating

Run `/toolset update` in CLI chat or Telegram (`hermes toolset update` in a
terminal); `--check` previews and `status` shows the last result. It updates
**every live profile** with fast-forward updates only, and refuses while a plugin
checkout has uncommitted changes. Along the way it:

- merges edits that profiles made to their installed skills onto the release and
  lists them under `local_edits` (a real conflict stops the update before any write);
- re-applies each profile's command menu, approval and injection settings
  (`settings_healed`) and clears leftover per-chat Telegram menus that still list
  retired commands (`chat_menus_healed`);
- when anything changed and every profile is ready, requests one graceful restart
  of the running root gateway so Telegram menus refresh; in-flight turns get a
  bounded drain period and cron schedules persist. Restart profile-dedicated
  gateways yourself.

See [update behavior and recovery](docs/installation.md#update-all-profiles).
Installations from before `/autowork` replaced its older command follow the
migration procedure in [installation](docs/installation.md).

## What verification proves

| Capability | Evidence |
| --- | --- |
| Skill discovery, installer behavior and workflow helpers | Offline automated tests |
| CLI registration, skill loading and gateway origin routing | Native Hermes integration tests with captured calls |
| Live gateway command refresh | Activation receipts checked during setup |
| Actual model behavior or live Telegram delivery | Not established by those checks; requires a configured live session |

`/toolset` reports registrations, not whether every service is connected. Hermes'
own `/toolsets` lists tool groups, a different inventory. See
[testing and compatibility](docs/testing.md).

## Documentation

- [Product scope and architecture](docs/project.md) · [Work queue](TODO.md) · [Changelog](CHANGELOG.md)
- [Installation, profile scope and policy opt-out](docs/installation.md)
- [Commands, Autoresearch and the engineering workflow](docs/workflows.md)
- [Command and configuration reference](docs/reference.md) · [Troubleshooting](docs/troubleshooting.md)
- [Memory capture, inspection and existing stores](docs/memory.md)
- [Removal and recovery](docs/uninstall.md)
- [Dependencies, reproducibility and licensing](docs/dependencies.md)
- [Adding skills](docs/contributing.md) · [Testing and compatibility](docs/testing.md)

Licensed under the [MIT License](LICENSE). Bundled third-party components keep their
own licenses and attribution; see [licensing details](docs/dependencies.md#licensing).
