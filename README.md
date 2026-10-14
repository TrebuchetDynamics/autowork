# Hermes Toolset

An opinionated toolkit for running repository work across Hermes profiles—from
questions and research to documented tasks, implementation, checks and commits.
Use the same workflows in Hermes CLI and Telegram. Install into one profile with
the native plugin manager, or deploy across your fleet with the setup tools.

**Codex and Pi are also supported** through native packages with portable workflow
adapters. See [Codex and Pi installation](docs/cross-host.md) for their install and
invocation syntax. The Hermes fleet installer below is only for Hermes.

Hermes already supports skills and plugins. This bundle adds a coordinated set of
repository workflows, automatic slash-command registration, shared installation
across profiles, and verification that gateway commands were registered. It includes
the complete [Impeccable design skill](skills/impeccable/SKILL.md) and
25 pinned [Addy engineering protocols](skills/engineering/SKILL.md), with shared
checklists, loaded one technique at a time when needed. Phase bundles are optional.

**Autowork coordinates repository development.** Supporting skills are available
on demand; installation does not load them all or require a full workflow per task.
Explicit specialist commands still work independently within their stated scope.

The main commands are **`/plan_with_me`** (ask and plan together),
**`/plan_for_me`** (investigate and decide), **`/docs_sync`** (maintain docs and
TODO.md), and **`/autowork`** (execute). Underscore and hyphen spellings work in
CLI; Telegram displays underscores. `/autoresearch_plan` remains a compatibility
command for planning.

## What you can do

| Workflow | Example in CLI chat | Result and possible changes | Readiness needed |
| --- | --- | --- | --- |
| Clarify a project | `/plan_with_me Design a caching layer` | Researches the repo, clarifies your request with focused questions, and saves the plan and tasks. Use `questions only` to avoid writes. | Core + model; file/terminal tools to save decisions |
| Challenge a plan | `/plan_with_me Challenge this cache design` | Questions assumptions before implementation. | Core + configured model |
| Maintain docs and tasks | `/docs_sync Record the accepted cache design` | Updates docs and organizes accepted work into tasks with acceptance criteria and dependencies. Does not start implementation. | File/terminal tools; graph tooling for relevant relationship analysis |
| Schedule repository work | `/cron_autowork every 30 minutes for this repo; no push` | Creates or updates a matching Autowork job and verifies its settings. | Available scheduler + verified repository/profile |
| Develop a repository | `/autowork Implement the accepted cache specification` | Reads TODO.md, calls bounded Autoresearch for unresolved planning or research questions, then executes and verifies a useful slice. Default invocation selects one task; no push/deploy implied. | Configured model + execution tools; supporting tools only when needed |
| Research and improve | `/plan_for_me Reduce cache latency` | Saves actionable plans and findings to TODO.md by default, synchronizing goals.json through docs_sync. Planning does not implement; explicit read-only requests write nothing. | Research/experiment tools for the selected protocol; file/terminal tools to record tasks |
| Continue approved work | `/lgtm` | Continues the agreed work without asking again; respects changes such as “no push.” | Tools required by the agreed work |
| Deliver changes | `/git-commit-push only src/cache` | Validates, commits and pushes the specified work. Add `no push` for local commits. | Git + repository checks; remote credentials for push |
| Integrate upstream | `/git-pull-merge` | Runs the repository's pull/merge workflow. | Git + remote access and repository checks |
| Set up a profile | `/profile-create` | Guides profile creation and shared-toolset setup. | Profile setup tools + selected integrations |
| Update the bundle | `/toolset update` | Checks upstream and updates plugin copies and bundled skills across all existing profiles. Use `/toolset update status` for the result. | Git, upstream access and clean plugin checkouts |
| Inspect capabilities | `/toolset list` | Lists registered commands and their owners; `hermes toolset doctor --json` reports missing imports. | Core; inventory does not prove workflow readiness |

**Core** means bundled commands with a configured model; `doctor --core` checks
registration, not the workflow prerequisites above.

Telegram uses underscores: `/plan_with_me`, `/docs_sync`, `/git_commit_push`,
`/plan_for_me`. Autoresearch retains all 13 subcommands plus `/autoresearch`.
See [commands and workflows](docs/workflows.md) for the full research command set.

`/autowork` is the repository-development command. Upgrade existing installations
with the migration procedure in [installation](docs/installation.md).

## A typical workflow

```text
/plan_with_me Design a caching layer for this repository
/autowork Implement that accepted specification; commit locally, no push
```

The interview asks questions and uses docs_sync to save accepted decisions and
tasks automatically; a separate docs command is unnecessary. **TODO.md is the
central work queue** for plans, user orders and progress. Its task details and
Now/Next ordering stay synchronized with the goals.json execution index; explicit
user priority changes are reconciled before task selection.

Already have an idea? Plan it first, then authorize execution:

```text
/plan_for_me Reduce cache latency; do not implement yet
/autowork Implement the next ready cache task from TODO.md; commit locally, no push
```

Autoresearch saves in-scope findings and actionable tasks by default; you do not
need to say “save.” It reuses task IDs and links supporting plans rather than
creating a competing backlog. Explicit `read-only`, `chat-only`, `no-write` or
`--dry-run` requests write nothing. Planning alone starts neither implementation
nor a recurring job.

Autowork uses a clear runnable task directly. When unresolved research or decomposition questions remain, it invokes bounded
Autoresearch. An empty queue first gets a bounded inspection; clear repairs need
no research ceremony. It records useful
work in TODO.md and retries selection in the same run. Under broad repository
scope, that can include evidenced documentation, UI/accessibility, test or refactor
work. It preserves dependencies, active workers and live-operation limits; it does
not invent tasks to inflate completion counts. See [the TODO work-center contract](skills/shared/TODO-WORKCENTER.md).

Illustrative result after an authorized task completes—not a test receipt:

```text
CACHE — COMPLETED; 1 TODO task completed
Task: TODO.md CACHE-01 — Add bounded cache storage.
Changed: cache implementation, tests and docs/cache.md.
Checks: cache acceptance tests passed; required review passed.
Next: CACHE-02 — Verify eviction behavior [eligible, not started].
Delivery: local commit <SHA>; not pushed, as requested.
```

A resumed worker is **RUNNING**, not completed. **COMPLETED** requires verified
task acceptance and closure; a passing build or successful dispatch is insufficient.
For a genuine user-dependent blocker, the report leads with **Action needed from
you:** the exact action and target, why it is needed, and what will resume afterward.
Autowork performs already-authorized repairs without asking again. These are
[reporting instructions](skills/autowork/references/dispatch-and-reporting.md),
not a guarantee that every cron occurrence completes a task.

## Read before installing

This policy applies to Hermes. [Codex/Pi adapters](docs/cross-host.md) preserve their host settings.

**The defaults are designed for an autonomous fleet, not a policy-neutral command bridge.**

- Full setup targets **every existing live profile**. There is no general
  `--profile` selector; `--hermes-home` selects a Hermes installation root.
- Loading the plugin sets `approvals.mode: off`, disables destructive slash-command
  and MCP-reload confirmations, and enables gateway injection in its owning profile.
  Explicit deny rules and Hermes hard blocks remain. Setup also clears disabled-skill lists.
- Full setup installs external integrations and selects **OMH memory with auto-safe
  capture** in separate profile stores. Conflicting providers/stores are refused.
- External imports are **not fully locked**. Some are pinned; others follow current
  upstream sources. Scans or missing dependencies can leave setup incomplete.
- There is **no automatic restoration of previous configuration** on uninstall.
  Back up profile configurations first; see [removal and recovery](docs/uninstall.md).

The runtime-policy opt-out prevents changes **during plugin loading only**.
Full setup still applies the bundle’s approval policy. There is currently no
policy-neutral full-installation mode. See [installation](docs/installation.md).
See [memory and retained data](docs/memory.md) before enabling memory capture.

## Installation choices

| Path | Scope | External integrations | Policy effects |
| --- | --- | --- | --- |
| `bash install.sh --bundle-only` | All existing live profiles | Skips external-source setup | Applies bundle defaults; not a single-profile or policy-neutral mode |
| `bash install.sh --yes-deps` | All existing live profiles | OMH, Ponytail, speech, Graphify | Applies defaults and OMH setup |
| Native Hermes plugin installation | Selected Hermes profile | Manifest declares OMH, Ponytail and speech dependencies | Plugin load applies runtime defaults and provisions missing bundled skills |

The standalone command registration code does not require a memory or speech
service to register commands. The published manifest describes the complete stack;
there is currently no separate minimal, policy-neutral Hermes package.

## Try the native plugin in one profile

These commands use the default profile. For an existing named profile, add
`-p work` after `hermes` throughout (for example, `hermes -p work toolset doctor --core`).
The manifest requires OMH, Ponytail and Hermes Speech, so native installation may
involve dependency resolution or consent even though the smoke check needs none
of those services.

```sh
hermes plugins install TrebuchetDynamics/hermes-toolset
hermes plugins enable hermes-toolset
hermes toolset doctor --core
```

Loading it still applies the runtime policy above. This is not a policy-preserving
trial, and native installation alone does not perform full external setup.
Continue at [first use](#first-use-in-your-project); the source path below is an
alternative for fleet setup or local development.

## Fleet setup from source

Prerequisites: an existing Hermes installation with a configured model, Git,
Bash and Python 3.12 for setup/tests (Hermes uses its managed interpreter). Use the [verified compatibility record](docs/testing.md#compatibility)
to check your environment. Telegram also needs its normal Hermes bot configuration.

After reviewing the effects above and backing up configuration:

```sh
git clone https://github.com/TrebuchetDynamics/hermes-toolset.git
cd hermes-toolset
bash install.sh --bundle-only --dry-run
bash install.sh --bundle-only
```

This starts with the bundled workflows and skips external-source setup. Keep the
checkout: the installed plugin links to it. Profile `status` is `ready` or
`incomplete`. The separate `gateway` field reports `commands_reloaded`,
`not_running`, `deferred_by_request`, `unreachable` or `reload_incomplete`.

## First use in your project

Open **your project**, not the Toolset checkout. These commands use default; if
you installed into a named profile, keep `-p PROFILE` after `hermes` in both commands.

```sh
hermes toolset doctor --core
cd /path/to/your-project
hermes
```

Core readiness checks bundled skill/command registration. Missing external
integrations are listed separately and do not fail `--core`. Plain `doctor` checks
the full stack; add `--json` for automation. Neither mode runs a model or verifies
live messaging. In the new CLI chat, try:

```text
/toolset list
/plan_with_me questions only: help me clarify a caching improvement; ask one question, then stop
```

Expected first success: the agent asks one relevant question and changes no files.
This uses the bundled interview skill and your configured model; it does not need
OMH, speech, Graphify or a worker. It is a live smoke check you perform, not a claim
that automated registration tests exercised the model. Resolve any missing skill
or model error before attempting implementation workflows.

Next, use the [core-only requirements interview](docs/onboarding.md#core-only-requirements-interview)
to produce a useful decision summary in chat. The separate
[full-workflow exercise](docs/onboarding.md#optional-see-decisions-become-a-task)
saves docs and a TODO.md task; it requires file/terminal tools; Graphify is relevant to relationship analysis.

The bundled engineering pack is available without external skill imports. Autowork,
Autoresearch and Docs Sync use its planning, implementation, debugging and review
methods while keeping TODO.md as the shared queue. Application receipts identify
the protocol revision and actual decision/check; loading a skill is not proof of use.

Before upgrading, note that **CLI startup can apply runtime defaults before
[preflight](docs/installation.md#preflight-before-fleet-writes), even with `--dry-run`**.
Use `bash install.sh --yes-deps --dry-run` from a source checkout to preview without
booting Hermes. Full setup needs `uv` unless OMH and Graphify CLIs are installed.

To add the full stack after native installation (no checkout needed):
**This expands setup to every live profile**, even when launched with `-p PROFILE`.

```sh
hermes toolset setup --yes-deps --dry-run
hermes toolset setup --yes-deps
```

From a source checkout, apply with `bash install.sh --yes-deps`.
Later failures can still leave partial setup; read the outcome.

For subsequent bundle updates, use `/toolset update` in CLI chat or Telegram;
`/toolset update --check` previews availability and `/toolset update status` shows
the result. Terminal equivalent: `hermes toolset update`. This targets **all live
profiles**, preserves local conflicts and uses fast-forward updates only. See
[update behavior and recovery](docs/installation.md#update-all-profiles).

See [onboarding](docs/onboarding.md) for Telegram checks, project binding and updates.
A profile is not a filesystem sandbox.

## What verification proves

| Capability | Evidence |
| --- | --- |
| Skill discovery, installer behavior and workflow helpers | Offline automated tests |
| CLI registration, skill loading and gateway origin routing | Native Hermes integration tests with captured calls |
| Live gateway command refresh | Activation receipts checked during setup |
| Actual model behavior or live Telegram delivery | Not established by those checks; requires a configured live session |

`/toolset` reports registrations, not whether every service is connected.
Hermes `/toolsets` reports enabled tool groups, a different inventory.
[Testing and compatibility](docs/testing.md) explains checks, exclusions and limits.

## Documentation

- [Product scope and architecture](docs/project.md) · [Work queue](TODO.md) · [Changelog](CHANGELOG.md)

- [Installation, profile scope and policy opt-out](docs/installation.md)
- [Commands, Autoresearch and the engineering workflow](docs/workflows.md)
- [Memory capture, inspection and existing stores](docs/memory.md)
- [Removal and recovery](docs/uninstall.md)
- [Dependencies, reproducibility and licensing](docs/dependencies.md)
- [Adding skills](docs/contributing.md) · [Testing and compatibility](docs/testing.md)

Licensed under the [MIT License](LICENSE). Bundled third-party components retain
their own licenses and attribution; see [licensing details](docs/dependencies.md#licensing).
